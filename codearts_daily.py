#!/usr/bin/env python3
"""
🛠️ CodeArts 每日福利领取 - 青龙脚本
------------------------------------------------------------

📌 功能
   CodeArts 每日福利 + 新人注册礼（不是签到，是 ops 交付三步式）：
   1. GET  {base}/v1/ops/delivery?channel=IDE   读活动列表（只读）
   2. POST {base}/v1/ops/claim                   领取 USER_LOGIN / NEW_USER_REGISTER 类活动
   3. POST {base}/v1/ops/confirm                 确认到账
   4. GET  delivery 回读，状态变 CONFIRMED/CONSUMED 才算成功

   · 新人注册礼是一次性奖励，与每日福利共用同一套领取执行体；学生认证 / 邀请好友不自动领；
   · 幂等键先落盘再发写请求，本地台账限制每天最多 6 次写尝试、间隔 10 分钟（--force 可跳过）；
   · 活动标题按活动类映射中文；查询与回读同源，避免「受理了但没到账」被当成成功。

   base = https://snap-access.cn-north-4.myhuaweicloud.com
   请求使用华为云 SDK-HMAC-SHA256 签名（AK/SK/STS，区域 API 不带 Host）。

🔑 环境变量
   CODEARTS_CREDENTIALS  【必填】多账号用换行或 & 分隔（JSON 凭据必须每条独占一行；AK|SK|STS 简写可用 & 串接）：
     {
       "access_key_id": "...", "secret_access_key": "...", "security_token": "...",
       "expiration": "2026-09-27T16:17:00.327Z",
       "refresh_token": "...",
       "domain_id": "...", "user_name": "...",
       "oauth_context": {
         "pkce_pair": {"code_verifier": "..."},
         "dpop_key_pair": {"private_key_jwk": {"kty":"EC","crv":"P-256","x":"...","y":"...","d":"..."}}
       }
     }
   也支持简化写法（无自动续期）：AK|SK|STS
   凭据可从对应客户端的登录态文件或抓包结果中提取，也可用 tools/codearts_login.py 登录获取。
   配置了 refresh_token + PKCE + DPoP 私钥时，脚本会在到期前自动续期，
   续期结果写入 codearts_credentials.json（需 pip install cryptography）。

   推送通道（均可选）：PUSHPLUS_TOKEN / BARK_URL / WECOM_WEBHOOK / DINGTALK_WEBHOOK / DINGTALK_SECRET

⌨️ 命令
   python codearts_daily.py               领取每日福利
   python codearts_daily.py --preview     只读活动列表，不发写请求
   python codearts_daily.py --only 2      只跑第 2 个账号
   python codearts_daily.py --force       忽略本地写请求限流（当天最多 6 次 / 间隔 10 分钟）
   python codearts_daily.py --no-notify   不推送

📄 依赖：requests（自动续期另需 cryptography）
"""
import base64
import hashlib
import hmac
import json
import os
import sys
import time
from datetime import datetime, timezone
from urllib.parse import urlsplit

import requests

import urllib3
urllib3.disable_warnings()

try:
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

BASE = "https://snap-access.cn-north-4.myhuaweicloud.com"
DELIVERY_PATH = "/v1/ops/delivery?channel=IDE"
CLAIM_PATH = "/v1/ops/claim"
CONFIRM_PATH = "/v1/ops/confirm"
TOKEN_URL = "https://sts.cn-north-4.myhuaweicloud.com/v1/oauth2/tokens"
CLIENT_ID = "vscode-codebot"
REFRESH_LEAD_SECONDS = 15 * 60
SIGN_ALGORITHM = "SDK-HMAC-SHA256"
EMPTY_BODY_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
STORE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "codearts_credentials.json")
LEDGER_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "codearts_welfare_ledger.json")
LEDGER_VERSION = 2
MAX_ATTEMPTS_PER_DAY = 6
MIN_ATTEMPT_GAP_SECONDS = 10 * 60
BEIJING_OFFSET_SECONDS = 8 * 60 * 60

ONLY = None
PREVIEW_ONLY = False
NO_NOTIFY = False
FORCE = False


def log(msg):
    print("%s %s" % (time.strftime("[%H:%M:%S]"), msg), flush=True)


def mask(text, keep=6):
    text = str(text or "")
    if len(text) <= keep + 4:
        return text
    return text[:keep] + "****" + text[-4:]


def split_accounts(raw):
    out = []
    for chunk in (raw or "").splitlines():
        chunk = chunk.strip()
        if not chunk or chunk.startswith("#"):
            continue
        if chunk.startswith("{"):
            out.append(chunk)          # JSON 凭据每条独占一行，不按 & 拆
        else:
            out.extend(part.strip() for part in chunk.split("&") if part.strip())
    return out


def request(method, url, headers=None, body=None, data=None, timeout=20, retries=3):
    last = None
    for attempt in range(retries):
        try:
            session = requests.Session()
            session.trust_env = False
            return session.request(method, url, headers=headers or {}, json=body,
                                   data=data, timeout=timeout, verify=False)
        except Exception as error:
            last = error
            if attempt + 1 < retries:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError("请求失败: %s" % last)


def json_of(response):
    try:
        return response.json()
    except Exception:
        return {}


def first_text(*values):
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, (int, float)):
            return str(value)
    return ""


TITLE_BY_TYPE = {
    "DAILY_CLAIM": "每日签到",
    "USER_LOGIN": "用户登录送积分",
    "NEW_USER_REGISTER": "新用户注册礼",
    "STUDENT_CERTIFIED": "学生认证",
    "INVITE_USER": "邀请好友",
}


def display_title(campaign):
    """活动标题按活动类映射中文；认不出的类回退上游原文（再空才回退 type）。"""
    mapped = TITLE_BY_TYPE.get(campaign.get("type") or "")
    if mapped:
        return mapped
    return (campaign.get("title") or campaign.get("type") or "活动").strip()


# ---------- 华为云 SDK-HMAC-SHA256 签名 ----------

def sha256_hex(data):
    return hashlib.sha256(data).hexdigest()


def hmac_sha256_hex(key, message):
    return hmac.new(key, message.encode("utf-8"), hashlib.sha256).hexdigest()


def encode_component(raw):
    safe = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.!~*'()"
    out = []
    for byte in raw:
        if byte in safe:
            out.append(chr(byte))
        else:
            out.append("%%%02X" % byte)
    return "".join(out)




def unescape(raw, plus_as_space):
    # Go 按字节处理：非 ASCII 字符先展开成 UTF-8 字节再逐个处理
    data = raw.encode("utf-8") if isinstance(raw, str) else raw
    out = bytearray()
    index = 0
    while index < len(data):
        byte = data[index]
        if byte == 0x25:                       # '%'
            if index + 2 >= len(data):
                return None
            try:
                out.append(int(data[index + 1:index + 3].decode("ascii"), 16))
            except ValueError:
                return None
            index += 3
        elif byte == 0x2B and plus_as_space:   # '+'
            out.append(0x20)
            index += 1
        else:
            out.append(byte)
            index += 1
    return bytes(out)


def canonical_uri(path_bytes):
    if not path_bytes:
        return "/"
    segments = [encode_component(segment) for segment in path_bytes.split(b"/")]
    escaped = "/".join(segments)
    if not escaped.endswith("/"):
        escaped += "/"
    return escaped


def query_pairs(raw_query):
    pairs = []
    for part in raw_query.split("&"):
        if not part or ";" in part:
            continue
        key, _, value = part.partition("=")
        key_bytes = unescape(key, True)
        value_bytes = unescape(value, True)
        if key_bytes is None or value_bytes is None:
            continue
        pairs.append((key_bytes, value_bytes))
    return pairs


def canonical_query_string(raw_query):
    pairs = query_pairs(raw_query)
    if not pairs:
        return ""
    pairs.sort(key=lambda item: (encode_component(item[0]), item[1]))
    return "&".join("%s=%s" % (encode_component(key), encode_component(value)) for key, value in pairs)


def sdk_date_now():
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def sign_request(method, url, headers, body_bytes, credential, include_host=False):
    """返回应发出去的头集合（含 Authorization），按上游 SDK-HMAC-SHA256 规范签名。"""
    if not credential.get("access_key_id") or not credential.get("secret_access_key"):
        raise RuntimeError("凭据不完整：缺少 access key 或 secret key")

    items = []          # [(name, value)]，同名大小写无关覆盖、位置不变

    def put(name, value):
        lower = name.lower()
        for index, (existing, _) in enumerate(items):
            if existing.lower() == lower:
                items[index] = (existing, value)
                return
        items.append((name, value))

    for name, value in (headers or {}).items():
        put(name, value)
    if credential.get("security_token"):
        put("X-Security-Token", credential["security_token"])
    if credential.get("domain_id"):
        put("X-Domain-Id", credential["domain_id"])
    if not any(name.lower() == "x-sdk-date" for name, _ in items):
        put("X-Sdk-Date", sdk_date_now())

    parsed = urlsplit(url)
    authority = parsed.netloc
    if include_host:
        put("Host", authority)

    date = next(value for name, value in items if name.lower() == "x-sdk-date")
    canonical = sorted(((name.lower(), value.strip()) for name, value in items), key=lambda item: item[0])
    canonical_headers = "".join("%s:%s\n" % (name, value) for name, value in canonical)
    signed_headers = ";".join(name for name, _ in canonical)

    payload_hash = sha256_hex(body_bytes)
    override = next((value for name, value in canonical if name == "x-sdk-content-sha256" and value), None)
    if override:
        payload_hash = override
    elif method.upper() not in ("PUT", "PATCH", "POST"):
        payload_hash = EMPTY_BODY_SHA256

    path_bytes = unescape(parsed.path, False)
    if path_bytes is None:
        raise RuntimeError("URL 路径转义非法")
    canonical_request = "\n".join([
        method.upper(), canonical_uri(path_bytes), canonical_query_string(parsed.query),
        canonical_headers, signed_headers, payload_hash,
    ])
    string_to_sign = "\n".join([SIGN_ALGORITHM, date, sha256_hex(canonical_request.encode("utf-8"))])
    signature = hmac_sha256_hex(credential["secret_access_key"].encode("utf-8"), string_to_sign)
    put("Authorization", "%s Access=%s, SignedHeaders=%s, Signature=%s"
        % (SIGN_ALGORITHM, credential["access_key_id"], signed_headers, signature))

    return {name: value for name, value in items}


# ---------- 凭据解析 / 存储 / 续期 ----------

def normalize_credential(raw):
    oauth = raw.get("oauth_context") if isinstance(raw.get("oauth_context"), dict) else {}
    pkce = oauth.get("pkce_pair") if isinstance(oauth.get("pkce_pair"), dict) else {}
    dpop = oauth.get("dpop_key_pair") if isinstance(oauth.get("dpop_key_pair"), dict) else {}
    jwk = dpop.get("private_key_jwk") if isinstance(dpop.get("private_key_jwk"), dict) else {}
    return {
        "access_key_id": first_text(raw.get("access_key_id"), raw.get("accessKeyId"), raw.get("ak")),
        "secret_access_key": first_text(raw.get("secret_access_key"), raw.get("secretAccessKey"), raw.get("sk")),
        "security_token": first_text(raw.get("security_token"), raw.get("securityToken"), raw.get("sts")),
        "expiration": first_text(raw.get("expiration"), raw.get("expires_at"), raw.get("expiresAt")),
        "refresh_token": first_text(raw.get("refresh_token"), raw.get("refreshToken")),
        "domain_id": first_text(raw.get("domain_id"), raw.get("domainId")),
        "user_name": first_text(raw.get("user_name"), raw.get("userName")),
        "code_verifier": first_text(pkce.get("code_verifier"), raw.get("code_verifier")),
        "dpop_jwk": jwk,
        "note": first_text(raw.get("note")),
    }


def parse_accounts(raw):
    accounts = []
    for index, line in enumerate(split_accounts(raw), 1):
        try:
            if line.startswith("{"):
                credential = normalize_credential(json.loads(line))
            else:
                parts = [part.strip() for part in line.split("|")]
                credential = normalize_credential({
                    "access_key_id": parts[0] if len(parts) > 0 else "",
                    "secret_access_key": parts[1] if len(parts) > 1 else "",
                    "security_token": parts[2] if len(parts) > 2 else "",
                    "refresh_token": parts[3] if len(parts) > 3 else "",
                })
        except Exception as error:
            log("⚠️ 第 %d 行凭据解析失败，已跳过: %s" % (index, error))
            continue
        if not credential["access_key_id"] or not credential["secret_access_key"]:
            log("⚠️ 第 %d 行缺少 AK/SK，已跳过" % index)
            continue
        credential["note"] = credential["note"] or ("账号%d" % index)
        accounts.append(credential)
    return accounts


def identity_of(credential):
    return (credential.get("domain_id") or credential.get("user_name")
            or credential.get("access_key_id"))[:64]


def load_store():
    try:
        with open(STORE_FILE, encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_store(store):
    try:
        with open(STORE_FILE, "w", encoding="utf-8") as handle:
            json.dump(store, handle, ensure_ascii=False, indent=2)
    except Exception as error:
        log("⚠️ 凭据存储写入失败: %s" % error)


def apply_store(credential):
    saved = load_store().get(identity_of(credential))
    if not isinstance(saved, dict):
        return False
    for key in ("access_key_id", "secret_access_key", "security_token", "expiration",
                "refresh_token", "domain_id", "user_name", "code_verifier"):
        if saved.get(key):
            credential[key] = saved[key]
    if isinstance(saved.get("dpop_jwk"), dict) and saved["dpop_jwk"]:
        credential["dpop_jwk"] = saved["dpop_jwk"]
    return True


def persist(credential):
    store = load_store()
    store[identity_of(credential)] = {key: credential.get(key) for key in (
        "access_key_id", "secret_access_key", "security_token", "expiration",
        "refresh_token", "domain_id", "user_name", "code_verifier")}
    store[identity_of(credential)]["dpop_jwk"] = credential.get("dpop_jwk") or {}
    store[identity_of(credential)]["at"] = int(time.time())
    save_store(store)


def expires_within(credential, seconds):
    text = credential.get("expiration", "")
    if not text:
        return True
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%f%z",
                "%Y-%m-%dT%H:%M:%S%z"):
        try:
            moment = datetime.strptime(text.replace("+00:00", "Z"), fmt)
            if moment.tzinfo is None:
                moment = moment.replace(tzinfo=timezone.utc)
            return moment.timestamp() - time.time() < seconds
        except ValueError:
            continue
    return True


def b64url(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def b64url_decode(text):
    text += "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text)


def dpop_proof(jwk, method, url):
    try:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
    except Exception:
        raise RuntimeError("缺少 cryptography 库，无法生成 DPoP proof（pip install cryptography）")
    scalar = int.from_bytes(b64url_decode(jwk.get("d", "")), "big")
    key = ec.derive_private_key(scalar, ec.SECP256R1())
    numbers = key.public_key().public_numbers()
    x = numbers.x.to_bytes(32, "big")
    y = numbers.y.to_bytes(32, "big")
    header = {"alg": "ES256", "typ": "dpop+jwt",
              "jwk": {"kty": "EC", "crv": "P-256", "x": b64url(x), "y": b64url(y)}}
    payload = {"htm": method.upper(), "htu": url, "iat": int(time.time()),
               "jti": os.urandom(32).hex()}
    signing_input = "%s.%s" % (
        b64url(json.dumps(header, separators=(",", ":"), ensure_ascii=False).encode("utf-8")),
        b64url(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")),
    )
    der = key.sign(signing_input.encode("ascii"), ec.ECDSA(hashes.SHA256()))
    r, s = decode_dss_signature(der)
    raw = r.to_bytes(32, "big") + s.to_bytes(32, "big")
    return "%s.%s" % (signing_input, b64url(raw))


def refresh_credential(credential):
    if not credential.get("refresh_token") or not credential.get("code_verifier"):
        raise RuntimeError("凭据缺少 refresh_token 或 code_verifier，无法续期")
    jwk = credential.get("dpop_jwk") or {}
    if not jwk.get("d"):
        raise RuntimeError("凭据缺少 DPoP 私钥（oauth_context.dpop_key_pair.private_key_jwk）")
    proof = dpop_proof(jwk, "POST", TOKEN_URL)
    form = {
        "client_id": CLIENT_ID,
        "code_verifier": credential["code_verifier"],
        "grant_type": "refresh_token",
        "refresh_token": credential["refresh_token"],
    }
    response = request("POST", TOKEN_URL,
                       headers={"Content-Type": "application/x-www-form-urlencoded",
                                "Accept": "application/json", "DPoP": proof},
                       data=form, timeout=30)
    payload = json_of(response)
    if response.status_code < 200 or response.status_code >= 300:
        detail = first_text(payload.get("error_description"), payload.get("error"),
                            payload.get("message")) or ("HTTP %s" % response.status_code)
        raise RuntimeError("令牌请求被拒: %s" % detail)
    data = payload.get("credentials") if isinstance(payload.get("credentials"), dict) else payload

    def read(name):
        value = data.get(name)
        if isinstance(value, str):
            return value.strip()
        value = payload.get(name)
        return value.strip() if isinstance(value, str) else ""

    fresh = {
        "access_key_id": read("access_key_id"),
        "secret_access_key": read("secret_access_key"),
        "security_token": read("security_token"),
        "expiration": first_text(read("expiration"), read("expires_at")),
        "refresh_token": read("refresh_token") or credential["refresh_token"],
    }
    if not fresh["access_key_id"] or not fresh["secret_access_key"] or not fresh["security_token"]:
        raise RuntimeError("令牌响应缺少 AK/SK/STS")
    for key in ("domain_id", "user_name", "code_verifier", "dpop_jwk", "note"):
        fresh[key] = credential.get(key, "" if key != "dpop_jwk" else {})
    persist(fresh)
    log("   🔄 凭据已续期并保存")
    return fresh


def ensure_fresh(credential):
    if not expires_within(credential, REFRESH_LEAD_SECONDS):
        return credential
    if credential.get("refresh_token") and credential.get("code_verifier") and (credential.get("dpop_jwk") or {}).get("d"):
        try:
            return refresh_credential(credential)
        except Exception as error:
            log("   ⚠️ 自动续期失败: %s" % error)
            return credential
    log("   ⚠️ 凭据已临近到期且未配置完整续期材料，直接尝试（失败请重新登录获取新凭据）")
    return credential


# ---------- 本地台账（幂等键 + 写请求限流） ----------

def beijing_day(now_ms=None):
    """北京时间意义上的「今天」：上游活动周期是 UTC+8 零点。"""
    moment = (now_ms if now_ms is not None else int(time.time() * 1000)) / 1000.0 + BEIJING_OFFSET_SECONDS
    return time.strftime("%Y-%m-%d", time.gmtime(moment))


def load_ledger_store():
    try:
        with open(LEDGER_FILE, encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_ledger_store(store):
    try:
        with open(LEDGER_FILE, "w", encoding="utf-8") as handle:
            json.dump(store, handle, ensure_ascii=False, indent=2)
        return True
    except Exception as error:
        log("⚠️ 领取台账写入失败: %s" % error)
        return False


def fresh_ledger():
    return {"version": LEDGER_VERSION, "day": beijing_day(), "attempts": 0, "lastAttemptMs": 0,
            "accepted": False, "campaigns": {}, "newbieSettled": False}


def ledger_of(store, identity):
    """读台账并归一到北京时间「今天」。

    读不懂的台账一律拒绝（版本不对 / 日期越界 / attempts 越界）：当成空台账重来
    会把上一轮的幂等键丢掉，崩溃后重试会被上游当成另一笔领取。
    """
    ledger = fresh_ledger()
    entry = (store.get("accounts") or {}).get(identity)
    if not isinstance(entry, dict):
        return ledger
    ledger["newbieSettled"] = entry.get("newbieSettled") is True
    stored = entry.get("ledger")
    if stored is None:
        return ledger
    day = stored.get("day") if isinstance(stored, dict) else None
    attempts = stored.get("attempts") if isinstance(stored, dict) else None
    if (not isinstance(stored, dict) or stored.get("version") != LEDGER_VERSION
            or not isinstance(day, str) or not isinstance(attempts, int)
            or not 0 <= attempts <= MAX_ATTEMPTS_PER_DAY):
        raise RuntimeError("本地领取台账无效，未发送领取请求（可删除 codearts_welfare_ledger.json 后重试）")
    today = beijing_day()
    if day > today:
        raise RuntimeError("系统日期（%s）早于领取记录（%s），先纠正时钟再领取" % (today, day))
    if day < today:
        return ledger
    ledger["day"] = day
    ledger["attempts"] = attempts
    ledger["lastAttemptMs"] = stored.get("lastAttemptMs") if isinstance(stored.get("lastAttemptMs"), int) else 0
    ledger["accepted"] = stored.get("accepted") is True
    campaigns = stored.get("campaigns")
    if isinstance(campaigns, dict):
        ledger["campaigns"] = {key: value for key, value in campaigns.items() if isinstance(value, dict)}
    return ledger


def persist_ledger(store, identity, ledger):
    accounts = store.setdefault("accounts", {})
    entry = accounts.get(identity)
    if not isinstance(entry, dict):
        entry = {}
    entry["ledger"] = {key: ledger.get(key) for key in (
        "version", "day", "attempts", "lastAttemptMs", "accepted", "campaigns")}
    entry["newbieSettled"] = ledger.get("newbieSettled") is True
    entry["at"] = int(time.time())
    accounts[identity] = entry
    if not save_ledger_store(store):
        raise RuntimeError("领取台账写入失败，为避免重复领取已中止（检查脚本目录写权限）")


def gap_remaining_seconds(ledger):
    last = ledger.get("lastAttemptMs") or 0
    if not isinstance(last, int) or last <= 0:
        return 0
    elapsed = max(0, int(time.time() * 1000) - last)
    return max(0, MIN_ATTEMPT_GAP_SECONDS - elapsed // 1000)


# ---------- ops 请求与领取流程 ----------

def welfare_request(credential, method, path, body=None):
    """一次 ops 请求：签名 GET/POST + code==0 的 envelope 判定。"""
    url = BASE + path
    headers = {"Content-Type": "application/json", "Agent-Type": "PromptCenter", "X-Language": "en-us"}
    payload = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8") if body is not None else b""
    signed = sign_request(method, url, headers, payload, credential, include_host=False)
    response = request(method, url, headers=signed, data=payload if body is not None else None, timeout=20)
    text = response.text[:300]
    if response.status_code != 200:
        raise RuntimeError("ops 接口返回 HTTP %s: %s%s" % (response.status_code, text, benefit_hint(text)))
    parsed = json_of(response)
    if parsed.get("code") != 0:
        raise RuntimeError("ops 接口未确认成功（需要 code=0，实际 %s）%s" % (parsed.get("code"), benefit_hint(text)))
    return parsed.get("data")


def benefit_hint(text):
    """「无福利档案」类报错给一句人话：官方建档后重试即可。"""
    lowered = (text or "").lower()
    for token in ("4004", "benefit not found", "档案", "不存在"):
        if token in lowered:
            return "（该账号尚未开通福利档案；官方客户端登录/首次使用时会自动建档，稍后重试即可）"
    return ""


def fetch_deliveries(credential):
    data = welfare_request(credential, "GET", DELIVERY_PATH)
    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list):
        raise RuntimeError("福利接口没有返回 items 字段")
    campaigns = []
    for item in items:
        if not isinstance(item, dict):
            continue
        campaigns.append({
            "id": item.get("campaignId"),
            "key": str(item.get("campaignId")) if item.get("campaignId") is not None else "",
            "type": item.get("type") or "",
            "title": item.get("title") or "",
            "claimable": item.get("claimable") is True,
            "status": item.get("status") or "",
            "amount": item.get("benefitAmount") or 0,
            "unit": item.get("benefitUnit") or "",
        })
    return campaigns


def is_daily_login(campaign):
    return campaign["type"] == "USER_LOGIN" and campaign["unit"] == "CREDIT" and bool(campaign["key"])


def is_confirmed(campaign):
    return (not campaign["claimable"]) and campaign["status"] in ("CONFIRMED", "CONSUMED")


def is_newbie_gift(campaign):
    """新人注册礼：一次性奖励，与每日福利共用领取执行体；学生认证 / 邀请好友不自动领。"""
    return campaign["type"] == "NEW_USER_REGISTER" and bool(campaign["key"])


def has_work(campaign):
    """这一条还有活要干吗（能领，或领了没确认）。"""
    return campaign["claimable"] or campaign["status"] == "CLAIMED"


def claim_one(credential, campaign, idempotent_key):
    """领一笔（campaignId 原样带回，不改类型）；响应 id 对不上就不进入 confirm 阶段。"""
    data = welfare_request(credential, "POST", CLAIM_PATH,
                           {"campaignId": campaign["id"], "idempotentKey": idempotent_key, "channel": "IDE"})
    returned = str(data.get("campaignId")) if isinstance(data, dict) else ""
    if returned != campaign["key"]:
        raise RuntimeError("领取响应活动 ID 不匹配（要 %s，回 %s），未进入确认阶段" % (campaign["key"], returned))


def do_checkin(credential):
    credential = ensure_fresh(credential)
    identity = identity_of(credential)
    store = load_ledger_store()
    ledger = ledger_of(store, identity)

    campaigns = fetch_deliveries(credential)
    daily = [item for item in campaigns if is_daily_login(item)]
    newbie = [item for item in campaigns if is_newbie_gift(item)]

    if PREVIEW_ONLY:
        rows = []
        for item in daily:
            rows.append("%s:%s(%s)" % (display_title(item), item["status"] or "可领取", item["amount"]))
        for item in newbie:
            state = "已确认" if is_confirmed(item) else (item["status"] or "可领取")
            rows.append("%s:%s(%s)" % (display_title(item), state, item["amount"]))
        return False, "仅预览（--preview）: " + ("; ".join(rows) if rows else "当前没有福利活动"), credential

    # 新人礼是一次性奖励：结清记本机后不再重查（与每日链共用同一份台账与限流）
    daily_work = [item for item in daily if has_work(item)]
    newbie_work = [] if ledger.get("newbieSettled") else [item for item in newbie if has_work(item)]
    todo = daily_work + newbie_work

    if not todo:
        if daily and all(is_confirmed(item) for item in daily):
            extra = "；新人注册礼已确认" if newbie and all(is_confirmed(item) for item in newbie) else ""
            return False, "今日福利已确认到账" + extra, credential
        return False, "当前没有可领取的福利活动", credential

    now_ms = int(time.time() * 1000)
    if not FORCE:
        if ledger["attempts"] >= MAX_ATTEMPTS_PER_DAY:
            return False, "本地限流：今日已提交 %d 次，跳过本轮（--force 可强制重试）" % ledger["attempts"], credential
        wait = gap_remaining_seconds(ledger)
        if wait > 0:
            return False, "本地限流：距上次提交不足 10 分钟（约 %d 秒后重试，--force 可跳过）" % wait, credential

    ledger["attempts"] += 1
    ledger["lastAttemptMs"] = now_ms
    ledger["accepted"] = False
    persist_ledger(store, identity, ledger)   # 幂等键先落盘再发写请求

    submitted = []
    for item in todo:
        key = item["key"]
        progress = ledger["campaigns"].get(key) or {}
        if item["status"] == "CLAIMED":
            progress["claimed"] = True
        if not progress.get("claimed") and item["claimable"]:
            if not progress.get("idempotentKey"):
                progress["idempotentKey"] = "claim_%s_%d" % (key, now_ms)
            ledger["campaigns"][key] = progress
            persist_ledger(store, identity, ledger)
            claim_one(credential, item, progress["idempotentKey"])
            progress["claimed"] = True
            ledger["campaigns"][key] = progress
            persist_ledger(store, identity, ledger)
        if progress.get("claimed"):
            # 已领但未确认：只补 confirm，不重复发 claim
            welfare_request(credential, "POST", CONFIRM_PATH, {"campaignId": item["id"]})
        submitted.append(item)
        time.sleep(1.0)

    # 回读二次确认：claim / confirm 都只回 code:0，那是「受理」不是「到账」
    verified = fetch_deliveries(credential)
    missing = []
    for item in submitted:
        matched = any(seen["key"] == item["key"] and seen["type"] == item["type"] and is_confirmed(seen)
                      for seen in verified)
        if matched:
            progress = ledger["campaigns"].get(item["key"]) or {}
            progress["confirmed"] = True
            ledger["campaigns"][item["key"]] = progress
        else:
            missing.append(display_title(item))
    if missing:
        persist_ledger(store, identity, ledger)
        return False, "请求已提交，但官方活动列表尚未确认到账：%s（稍后重跑会补确认）" % "、".join(missing), credential

    ledger["accepted"] = True
    verified_newbie = [item for item in verified if is_newbie_gift(item)]
    if verified_newbie and all(is_confirmed(item) for item in verified_newbie):
        ledger["newbieSettled"] = True   # 一次性福利结清后记本机，下次不再重查
    persist_ledger(store, identity, ledger)

    parts = []
    done_daily = [item for item in verified if is_daily_login(item) and is_confirmed(item)]
    if done_daily:
        parts.append("每日福利 %s" % sum(float(item["amount"] or 0) for item in done_daily))
    done_newbie = [item for item in verified_newbie if is_confirmed(item)]
    if done_newbie:
        parts.append("新人注册礼 %s" % sum(float(item["amount"] or 0) for item in done_newbie))
    return True, "福利已确认到账：%s（本次提交 %d 笔）" % ("；".join(parts) or "已确认", len(submitted)), credential


# ---------- 推送 ----------

def post_json(url, payload, timeout=20):
    session = requests.Session()
    session.trust_env = False
    return session.post(url, json=payload, timeout=timeout, verify=False)


def _env(name):
    return os.environ.get(name, "").strip()


def notify_pushplus(title, content):
    token = _env("PUSHPLUS_TOKEN")
    if not token:
        return False
    try:
        text = (content[:18000] + "\n...(已截断)") if len(content) > 18000 else content
        answer = post_json("https://www.pushplus.plus/send",
                           {"token": token, "title": title, "content": text, "template": "txt"})
        return str(json_of(answer).get("code")) == "200"
    except Exception:
        return False


def notify_bark(title, content):
    endpoint = _env("BARK_URL").rstrip("/")
    if not endpoint:
        return False
    try:
        answer = post_json(endpoint, {"title": title, "body": content, "group": "CodeArts"})
        return json_of(answer).get("code") == 200
    except Exception:
        return False


def notify_wecom(title, content):
    hook = _env("WECOM_WEBHOOK")
    if not hook:
        return False
    if not hook.startswith("http"):
        hook = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=" + hook
    try:
        answer = post_json(hook, {"msgtype": "text",
                                  "text": {"content": ("%s\n%s" % (title, content))[:2000]}})
        return json_of(answer).get("errcode") == 0
    except Exception:
        return False


def notify_dingtalk(title, content):
    hook = _env("DINGTALK_WEBHOOK")
    if not hook:
        return False
    try:
        secret = _env("DINGTALK_SECRET")
        if secret:
            stamp = str(int(time.time() * 1000))
            digest = hmac.new(secret.encode(), ("%s\n%s" % (stamp, secret)).encode(),
                              hashlib.sha256).digest()
            hook += ("&" if "?" in hook else "?") + "timestamp=%s&sign=%s" % (
                stamp, requests.utils.quote(base64.b64encode(digest)))
        answer = post_json(hook, {"msgtype": "text",
                                  "text": {"content": "%s\n%s" % (title, content)}})
        return json_of(answer).get("errcode") == 0
    except Exception:
        return False


def notify_ql(title, content):
    try:
        from notify import send as panel_send
        panel_send(title, content)
        return True
    except Exception:
        pass
    endpoint = _env("QL_URL").rstrip("/")
    token = _env("QL_TOKEN")
    if not endpoint or not token:
        return False
    try:
        session = requests.Session()
        session.trust_env = False
        answer = session.post(endpoint + "/api/system/notify?token=" + token,
                              json={"title": title, "content": content}, timeout=15, verify=False)
        return str(json_of(answer).get("code")) in ("0", "200")
    except Exception:
        return False


def notify_all(title, content):
    handlers = (notify_pushplus, notify_bark, notify_wecom, notify_dingtalk, notify_ql)
    if not any(handler(title, content) for handler in handlers):
        log("（未配置推送渠道，本次只记录日志）")


# ---------- 主流程 ----------

def main():
    global ONLY, PREVIEW_ONLY, NO_NOTIFY, FORCE
    args = sys.argv[1:]
    if "--preview" in args:
        PREVIEW_ONLY = True
    if "--force" in args:
        FORCE = True
    if "--no-notify" in args:
        NO_NOTIFY = True
    if "--only" in args:
        try:
            ONLY = int(args[args.index("--only") + 1])
        except Exception:
            ONLY = None

    accounts = parse_accounts(os.environ.get("CODEARTS_CREDENTIALS", ""))
    if not accounts:
        log("❌ 未配置 CODEARTS_CREDENTIALS（多条用换行或 & 分隔；每条: JSON 或 AK|SK|STS）")
        return

    log("╔════════════════════════════════════╗")
    log("║ 🛠️ CodeArts 每日福利领取           ║")
    log("╚════════════════════════════════════╝")
    log("👥 账号数: %d  base: %s" % (len(accounts), BASE))

    report = []
    for index, credential in enumerate(accounts, 1):
        if ONLY and index != ONLY:
            continue
        apply_store(credential)
        log("👤 [%d] %s  AK=%s" % (index, credential["note"], mask(credential["access_key_id"])))
        try:
            success, message, _ = do_checkin(credential)
            log("   %s %s" % ("✅" if success else "ℹ️", message))
            report.append("账号%d %s: %s %s" % (index, credential["note"], "✅" if success else "ℹ️", message))
        except Exception as error:
            log("   ❌ 异常: %s" % error)
            report.append("账号%d %s: ❌ %s" % (index, credential["note"], error))
        time.sleep(2)

    summary = "🛠️ CodeArts 福利领取报告\n" + "\n".join(report) + "\n🕐 " + time.strftime("%Y-%m-%d %H:%M")
    log(summary)
    if not NO_NOTIFY and not PREVIEW_ONLY:
        notify_all("🛠️ CodeArts 福利领取报告", summary)


if __name__ == "__main__":
    main()
