# 🛠️ CodeArts Daily

CodeArts 일일 혜택과 일회성 신규 가입 보상을 자동으로 받습니다. claim과 confirm 후 혜택 목록을 다시 읽어, 요청이 접수된 것만으로 완료라고 보고하지 않습니다.

[简体中文](../README.md) · [English](README.en.md) · [繁體中文](README.zh-Hant.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Português (BR)](README.pt-BR.md)

**현재 버전:** v1.0.6

전체 중국어 문서는 [../README.md](../README.md)에서 확인하세요.

## 주요 기능

- 데스크톱 계약인 `delivery → claim → confirm → delivery 재조회`를 사용합니다.
- Huawei Cloud `SDK-HMAC-SHA256`으로 서명하고 데스크톱 `Host` 헤더를 포함합니다.
- 로컬 자동 콜백을 사용하는 PKCE + DPoP 로그인을 지원합니다.
- 만료 전에 자격 증명을 갱신하고 원자적으로 저장합니다.
- 사용된 refresh token, 저장 실패 또는 `STS5.1806`을 종단 상태로 처리합니다.
- 멱등 키를 먼저 저장하고 하루 최대 6회, 최소 10분 간격으로 쓰기 요청을 제한합니다.

## Qinglong 최소 설정

```bash
python3 -m pip install -r requirements.txt
```

`codearts_daily.py`를 업로드하고 `CODEARTS_CREDENTIALS`를 설정한 뒤 작업을 만듭니다.

```text
40 8 * * * task codearts_daily.py
```

자격 증명은 로컬에서 생성합니다.

```bash
python codearts_login.py
python codearts_login.py --paste --no-browser
python codearts_login.py --note main
```

콜백은 `127.0.0.1`에서 수신합니다. Qinglong이 원격 서버에 있어도 로그인 도구는 로컬에서 실행하세요.

## GitHub Actions

**Settings → Secrets and variables → Actions**에서 다음 Secrets를 만듭니다.

```text
CODEARTS_CREDENTIALS
PUSHPLUS_TOKEN          # 선택
BARK_URL                # 선택
WECOM_WEBHOOK           # 선택
DINGTALK_WEBHOOK        # 선택
DINGTALK_SECRET         # 선택
```

그다음 **Actions → CodeArts Daily → Run workflow**에서 수동 실행합니다. 기본값은 수동 실행이며, 예약 실행이 필요하면 `.github/workflows/daily.yml`의 `schedule:` 주석을 해제하세요. cron은 UTC 기준입니다.

## 핵심 환경 변수

| 변수 | 형식과 용도 |
| :--- | :--- |
| `CODEARTS_CREDENTIALS` | 한 줄 JSON. refresh token, PKCE, DPoP 개인 키가 있으면 자동 갱신 가능 |
| `CODEARTS_CREDENTIALS` | `AK\|SK\|STS`도 수령할 수 있지만 약 1시간 후 만료되며 갱신할 수 없음 |
| `PUSHPLUS_TOKEN`, `BARK_URL`, `WECOM_WEBHOOK`, `DINGTALK_WEBHOOK`, `DINGTALK_SECRET` | 선택 알림 채널 |
| `QL_URL`, `QL_TOKEN` | 선택 Qinglong 알림 주소와 구버전 패널 토큰 |

계정은 줄바꿈 또는 `&`로 구분합니다. 각 JSON은 반드시 한 줄에 하나씩 두세요.

## 성공 기준과 개인정보

재조회 상태가 `CONFIRMED` 또는 `CONSUMED`일 때만 성공입니다. `CLAIMED` 상태인데 `userBenefitId`가 없으면 claim을 다시 보내거나 확인 ID를 추측하지 않고 중단합니다.

`codearts_credentials.json`에는 AK/SK/STS, refresh token, PKCE, DPoP 개인 키가 들어 있습니다. `codearts_welfare_ledger.json`에는 멱등 키와 제한 상태가 저장됩니다. 두 파일 모두 Git에서 제외됩니다. Issue에 인증 정보를 공개하지 마세요.

## 사용 범위 및 재배포 안내

이 프로젝트의 공식 버전은 무료입니다. 저장소, 스크립트, 배포 안내와 Release 다운로드를 포함합니다.

저자의 명시적 서면 허가 없이 이 프로젝트를 유료 자료, 내부판, 독점판, 회원 혜택, 유료 강의, 유료 배포 또는 업데이트 서비스로 재포장하지 마세요. 무관한 계정, 그룹, 채널에 옮겨 트래픽이나 유입을 유도하거나, 저자 및 저작권 표시를 삭제하고 원작으로 주장하거나, 저자 이름, 아바타, QR 코드, 프로젝트 이름으로 공식 승인을 가장하는 행위도 금지됩니다.

위반 시 삭제 요청이 이뤄질 수 있으며, 저자는 업데이트를 중단하거나 저장소를 보관 또는 삭제할 수 있습니다. 전체 규칙은 [NOTICE.md](../NOTICE.md)를 확인하세요.

## 링크

- [Releases](https://github.com/L0NE-6/CodeArts-Daily/releases)
- [Issues](https://github.com/L0NE-6/CodeArts-Daily/issues)
- [소스와 전체 중국어 문서](../README.md)
