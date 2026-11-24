# 🛠️ CodeArts Daily

Automates CodeArts daily benefits and the one-time new-user registration gift. The script claims, confirms, then rereads the benefit list, so an accepted request is never reported as a completed reward.

[简体中文](../README.md) · [English](README.en.md) · [繁體中文](README.zh-Hant.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Português (BR)](README.pt-BR.md)

**Current version:** v1.0.6

For the complete Chinese documentation, see [../README.md](../README.md).

## Highlights

- Uses the desktop contract `delivery → claim → confirm → delivery reread`.
- Signs requests with Huawei Cloud `SDK-HMAC-SHA256`, including the desktop `Host` header.
- Supports PKCE and DPoP login with an automatic local callback.
- Renews expiring credentials and writes them atomically.
- Treats a consumed refresh token, a failed credential write, or `STS5.1806` as terminal.
- Applies idempotency keys and local write limits: at most 6 attempts per day, 10 minutes apart.

## Qinglong Quick Start

```bash
python3 -m pip install -r requirements.txt
```

Upload `codearts_daily.py`, add `CODEARTS_CREDENTIALS`, and create a task:

```text
40 8 * * * task codearts_daily.py
```

Create credentials on the local machine:

```bash
python codearts_login.py
python codearts_login.py --paste --no-browser
python codearts_login.py --note main
```

The login callback listens on `127.0.0.1`; run the login tool locally even when Qinglong is remote.

## GitHub Actions

Create these repository secrets under **Settings → Secrets and variables → Actions**:

```text
CODEARTS_CREDENTIALS
PUSHPLUS_TOKEN          # optional
BARK_URL                # optional
WECOM_WEBHOOK           # optional
DINGTALK_WEBHOOK        # optional
DINGTALK_SECRET         # optional
```

Then open **Actions → CodeArts Daily → Run workflow**. The workflow is manual by default; enable the commented schedule in `.github/workflows/daily.yml` if needed. Cron uses UTC.

## Key Environment Variables

| Variable | Format and meaning |
| :--- | :--- |
| `CODEARTS_CREDENTIALS` | One-line JSON. JSON credentials must occupy one line per account and support renewal when refresh token, PKCE, and DPoP private key are present. |
| `CODEARTS_CREDENTIALS` | `AK\|SK\|STS` also works for receiving benefits but cannot renew and normally expires after about one hour. |
| `PUSHPLUS_TOKEN`, `BARK_URL`, `WECOM_WEBHOOK`, `DINGTALK_WEBHOOK`, `DINGTALK_SECRET` | Optional notification channels |
| `QL_URL`, `QL_TOKEN` | Optional Qinglong notification endpoint and legacy panel token |

Use newlines or `&` between accounts. Keep each JSON object on its own line.

## Success and Privacy

A benefit is successful only when the reread state becomes `CONFIRMED` or `CONSUMED`. Claim and confirm responses alone do not prove delivery. If a `CLAIMED` item has no `userBenefitId`, the script stops rather than replaying the claim or guessing an ID.

`codearts_credentials.json` contains access keys, refresh token, PKCE material, and a DPoP private key; `codearts_welfare_ledger.json` contains local idempotency and rate-limit state. Both are ignored by Git. Do not publish either file or paste secrets into an issue.

## Usage and redistribution

Official versions of this project are free, including the repository, scripts, deployment instructions, and Releases.

Without explicit written permission from the author, do not repackage the project as a paid resource, internal or exclusive edition, membership benefit, paid course, paid deployment, or update service; do not repost it to unrelated accounts, groups, or channels for traffic or lead generation; do not remove author or copyright notices or claim the work as your own; do not use the author's name, avatar, QR codes, or project name to imply official endorsement.

Violations may result in a takedown request. The author may pause updates, archive, or remove the repository. See [NOTICE.md](../NOTICE.md) for the complete rules.

## Project Links

- [Releases](https://github.com/L0NE-6/CodeArts-Daily/releases)
- [Issues](https://github.com/L0NE-6/CodeArts-Daily/issues)
- [Source and complete Chinese guide](../README.md)
