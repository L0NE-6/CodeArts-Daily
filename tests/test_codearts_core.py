import ast
import json
import os
import unittest
from pathlib import Path


SOURCE_PATH = Path(__file__).resolve().parents[1] / "codearts_daily.py"
SOURCE = SOURCE_PATH.read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)
FUNCTIONS = {
    node.name: node
    for node in TREE.body
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
}


def load_functions(*names, **globals_):
    namespace = {"__builtins__": __builtins__, **globals_}
    body = [FUNCTIONS[name] for name in names]
    module = ast.Module(body=body, type_ignores=[])
    exec(compile(module, str(SOURCE_PATH), "exec"), namespace)
    return namespace


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text="{}"):
        self.status_code = status_code
        self.payload = payload or {}
        self.text = text

    def json(self):
        return self.payload


class CodeArtsCoreTests(unittest.TestCase):
    def test_welfare_request_uses_desktop_headers_and_code_200(self):
        captured = {}

        def sign_request(method, url, headers, body_bytes, credential, include_host=False):
            captured["headers"] = dict(headers)
            captured["include_host"] = include_host
            return dict(headers, Authorization="signed")

        def request(method, url, headers=None, data=None, timeout=20):
            captured["url"] = url
            return FakeResponse(payload={"code": 200, "result": {"items": [1]}})

        module = load_functions(
            "welfare_request",
            BASE="https://example.test",
            sign_request=sign_request,
            request=request,
            json_of=lambda response: response.payload,
            benefit_hint=lambda text: "",
            json=json,
        )
        result = module["welfare_request"](
            {}, "GET", "/v1/ops/delivery?channel=DESKTOP",
            extra_headers={"x-snap-traceid": "trace-id"})
        self.assertEqual({"items": [1]}, result)
        self.assertTrue(captured["include_host"])
        self.assertEqual("zh-cn", captured["headers"]["X-Language"])
        self.assertEqual("trace-id", captured["headers"]["x-snap-traceid"])

    def test_claim_and_confirm_use_user_benefit_id(self):
        calls = []

        def welfare_request(credential, method, path, body=None, extra_headers=None):
            calls.append((method, path, body, extra_headers))
            if path.endswith("/claim"):
                return {"userBenefitId": "benefit-42"}
            return {}

        module = load_functions(
            "first_text", "claim_one", "confirm_one",
            CLAIM_PATH="/v1/ops/claim",
            CONFIRM_PATH="/v1/ops/confirm",
            OPS_CHANNEL="DESKTOP",
            welfare_request=welfare_request,
        )
        campaign = {"id": 123, "key": "123"}
        benefit_id = module["claim_one"]({}, campaign, "idem-1")
        self.assertEqual("benefit-42", benefit_id)
        self.assertEqual("DESKTOP", calls[0][2]["channel"])
        self.assertEqual("idem-1", calls[0][2]["idempotentKey"])

        module["confirm_one"]({}, benefit_id)
        self.assertEqual("/v1/ops/confirm", calls[1][1])
        self.assertEqual({"userBenefitId": "benefit-42"}, calls[1][2])
        self.assertNotIn("campaignId", calls[1][2])

    def test_claim_response_does_not_require_campaign_id(self):
        module = load_functions(
            "first_text", "claim_one",
            CLAIM_PATH="/v1/ops/claim",
            OPS_CHANNEL="DESKTOP",
            welfare_request=lambda *args, **kwargs: {
                "user_benefit_id": 987,
                "status": "GRANTED",
            },
        )
        self.assertEqual("987", module["claim_one"](
            {}, {"id": 1, "key": "1"}, "idem"))

    def test_confirm_fails_closed_without_user_benefit_id(self):
        module = load_functions(
            "first_text", "confirm_campaign", "display_title",
            confirm_one=lambda *args: (_ for _ in ()).throw(
                AssertionError("confirm must not be called")),
            TITLE_BY_TYPE={"USER_LOGIN": "用户登录送积分"},
        )
        with self.assertRaisesRegex(RuntimeError, "缺少 userBenefitId"):
            module["confirm_campaign"](
                {}, {"type": "USER_LOGIN", "title": "每日福利"}, {"claimed": True})

    def test_v2_ledger_migrates_to_v3(self):
        module = load_functions(
            "fresh_ledger", "ledger_of",
            LEDGER_VERSION=3,
            MAX_ATTEMPTS_PER_DAY=6,
            beijing_day=lambda: "2026-10-22",
        )
        store = {"accounts": {"uid": {"ledger": {
            "version": 2,
            "day": "2026-10-22",
            "attempts": 1,
            "lastAttemptMs": 123,
            "accepted": False,
            "campaigns": {"1": {"claimed": True, "idempotentKey": "old-key"}},
        }}}}
        ledger = module["ledger_of"](store, "uid")
        self.assertEqual(3, ledger["version"])
        self.assertEqual(1, ledger["attempts"])
        self.assertEqual("old-key", ledger["campaigns"]["1"]["idempotentKey"])

    def test_save_store_propagates_write_failure(self):
        def failing_open(*args, **kwargs):
            raise OSError("disk full")

        module = load_functions(
            "save_store", "CredentialStoreError",
            open=failing_open,
            json=json,
            os=os,
            STORE_FILE=str(Path(__file__).with_name("never-written-store.json")),
        )
        with self.assertRaisesRegex(module["CredentialStoreError"], "disk full"):
            module["save_store"]({"account": {"access_key_id": "ak"}})

    def test_refresh_persist_failure_marks_terminal_immediately(self):
        credential = {
            "access_key_id": "old-ak",
            "secret_access_key": "old-sk",
            "security_token": "old-sts",
            "refresh_token": "old-rt",
            "code_verifier": "verifier",
            "dpop_jwk": {"d": "private"},
            "domain_id": "domain-1",
        }

        module = load_functions(
            "refresh_credential", "TerminalCredentialError",
            dpop_proof=lambda *args: "proof",
            request=lambda *args, **kwargs: FakeResponse(200, {
                "credentials": {
                    "access_key_id": "new-ak",
                    "secret_access_key": "new-sk",
                    "security_token": "new-sts",
                    "refresh_token": "new-rt",
                    "expiration": "2026-10-29T12:00:00Z",
                }
            }),
            json_of=lambda response: response.payload,
            first_text=lambda *values: next(
                (value for value in values if isinstance(value, str) and value), ""),
            persist=lambda credential: (_ for _ in ()).throw(
                RuntimeError("disk full")),
            log=lambda message: None,
            TOKEN_URL="https://example.test/token",
            CLIENT_ID="client",
        )
        with self.assertRaisesRegex(module["TerminalCredentialError"], "落盘失败"):
            module["refresh_credential"](credential)
        self.assertTrue(credential.get("terminal"))
        self.assertEqual("refresh_persist_failed", credential.get("terminal_reason"))

    def _refresh_module(self, response, persisted):
        return load_functions(
            "refresh_credential", "TerminalCredentialError",
            "refresh_token_terminal", "mark_terminal", "first_text",
            dpop_proof=lambda *args: "proof",
            request=lambda *args, **kwargs: response,
            json_of=lambda answer: answer.payload,
            persist=lambda credential: persisted.append(dict(credential)),
            log=lambda message: None,
            json=json,
            TOKEN_URL="https://example.test/token",
            CLIENT_ID="client",
        )

    def test_sts5_1806_error_code_is_terminal(self):
        persisted = []
        credential = {
            "access_key_id": "ak", "secret_access_key": "sk",
            "security_token": "sts", "refresh_token": "rt",
            "code_verifier": "verifier", "dpop_jwk": {"d": "private"},
        }
        module = self._refresh_module(FakeResponse(400, {
            "error_code": "STS5.1806",
            "error_msg": "refresh token rejected",
        }, text='{"error_code":"STS5.1806"}'), persisted)
        with self.assertRaisesRegex(module["TerminalCredentialError"], "STS5.1806"):
            module["refresh_credential"](credential)
        self.assertTrue(credential.get("terminal"))
        self.assertEqual("STS5.1806", credential.get("terminal_reason"))
        self.assertTrue(persisted[-1].get("terminal"))

    def test_sts5_1806_message_leg_is_terminal(self):
        persisted = []
        credential = {
            "access_key_id": "ak", "secret_access_key": "sk",
            "security_token": "sts", "refresh_token": "rt",
            "code_verifier": "verifier", "dpop_jwk": {"d": "private"},
        }
        module = self._refresh_module(FakeResponse(400, {
            "error_msg": "invalid refresh token: 'the refresh token has been used'",
        }), persisted)
        with self.assertRaises(module["TerminalCredentialError"]):
            module["refresh_credential"](credential)
        self.assertTrue(credential.get("terminal"))
        self.assertTrue(persisted[-1].get("terminal"))

    def test_successful_refresh_persists_without_terminal(self):
        persisted = []
        credential = {
            "access_key_id": "old-ak", "secret_access_key": "old-sk",
            "security_token": "old-sts", "refresh_token": "old-rt",
            "code_verifier": "verifier", "dpop_jwk": {"d": "private"},
            "domain_id": "domain-1", "user_name": "user",
        }
        module = self._refresh_module(FakeResponse(200, {
            "credentials": {
                "access_key_id": "new-ak",
                "secret_access_key": "new-sk",
                "security_token": "new-sts",
                "refresh_token": "new-rt",
                "expiration": "2026-10-29T12:00:00Z",
            }
        }), persisted)
        fresh = module["refresh_credential"](credential)
        self.assertEqual("new-ak", fresh["access_key_id"])
        self.assertEqual("new-rt", fresh["refresh_token"])
        self.assertFalse(fresh.get("terminal"))
        self.assertFalse(persisted[-1].get("terminal"))

    def test_transient_refresh_error_is_not_terminal(self):
        persisted = []
        credential = {
            "access_key_id": "ak", "secret_access_key": "sk",
            "security_token": "sts", "refresh_token": "rt",
            "code_verifier": "verifier", "dpop_jwk": {"d": "private"},
        }
        module = self._refresh_module(FakeResponse(500, {
            "error": "server_error", "message": "temporary"
        }), persisted)
        with self.assertRaises(RuntimeError):
            module["refresh_credential"](credential)
        self.assertFalse(credential.get("terminal"))
        self.assertEqual([], persisted)

    def test_apply_store_restores_terminal_state(self):
        module = load_functions(
            "apply_store",
            identity_of=lambda credential: "account-1",
            load_store=lambda: {"account-1": {
                "access_key_id": "ak", "terminal": True,
                "terminal_reason": "STS5.1806",
            }},
        )
        credential = {"access_key_id": "old", "domain_id": ""}
        self.assertTrue(module["apply_store"](credential))
        self.assertTrue(credential["terminal"])
        self.assertEqual("STS5.1806", credential["terminal_reason"])

    def test_ensure_fresh_does_not_swallow_terminal(self):
        module = load_functions(
            "ensure_fresh", "TerminalCredentialError",
            expires_within=lambda credential, seconds: True,
            refresh_credential=lambda credential: (_ for _ in ()).throw(
                AssertionError("must not refresh")),
            REFRESH_LEAD_SECONDS=900,
            log=lambda message: None,
        )
        credential = {"terminal": True, "terminal_reason": "STS5.1806"}
        with self.assertRaisesRegex(module["TerminalCredentialError"], "STS5.1806"):
            module["ensure_fresh"](credential)


if __name__ == "__main__":
    unittest.main()
