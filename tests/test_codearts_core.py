import ast
import json
import unittest
from pathlib import Path


SOURCE_PATH = Path(__file__).resolve().parents[1] / "codearts_daily.py"
SOURCE = SOURCE_PATH.read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)
FUNCTIONS = {
    node.name: node
    for node in TREE.body
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
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


if __name__ == "__main__":
    unittest.main()
