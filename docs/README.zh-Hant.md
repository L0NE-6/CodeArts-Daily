# 🛠️ CodeArts Daily

自動領取 CodeArts 每日福利與一次性新人註冊禮。腳本依序執行 claim、confirm 與活動列表回讀，不會把「已受理」誤報成「已到帳」。

[简体中文](../README.md) · [English](README.en.md) · [繁體中文](README.zh-Hant.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Português (BR)](README.pt-BR.md)

**目前版本：** v1.0.6

完整中文文件請見 [../README.md](../README.md)。

## 核心能力

- 使用桌面端口徑 `delivery → claim → confirm → delivery 回讀`。
- 以華為雲 `SDK-HMAC-SHA256` 簽名，並包含桌面端要求的 `Host` 標頭。
- 支援 PKCE + DPoP 網頁登入與本機自動回呼。
- 到期前自動續期，並以原子方式寫入憑證。
- 一次性 refresh token 已消耗、落盤失敗或出現 `STS5.1806` 時，立即標記終態。
- 冪等鍵先落盤；每日最多 6 次寫入嘗試，間隔至少 10 分鐘。

## 青龍最短配置

```bash
python3 -m pip install -r requirements.txt
```

上傳 `codearts_daily.py`、設定 `CODEARTS_CREDENTIALS`，然後建立任務：

```text
40 8 * * * task codearts_daily.py
```

在本機取得憑證：

```bash
python codearts_login.py
python codearts_login.py --paste --no-browser
python codearts_login.py --note 主號
```

登入回呼監聽 `127.0.0.1`；即使青龍在遠端伺服器，也應在本機執行登入工具。

## GitHub Actions

在 **Settings → Secrets and variables → Actions** 建立：

```text
CODEARTS_CREDENTIALS
PUSHPLUS_TOKEN          # 選填
BARK_URL                # 選填
WECOM_WEBHOOK           # 選填
DINGTALK_WEBHOOK        # 選填
DINGTALK_SECRET         # 選填
```

再從 **Actions → CodeArts Daily → Run workflow** 手動執行。工作流預設僅手動觸發；如需排程，請取消 `.github/workflows/daily.yml` 中 `schedule:` 兩行註解。cron 使用 UTC。

## 關鍵環境變數

| 變數 | 格式與用途 |
| :--- | :--- |
| `CODEARTS_CREDENTIALS` | 單行 JSON；含 refresh_token、PKCE 與 DPoP 私鑰時可自動續期 |
| `CODEARTS_CREDENTIALS` | `AK\|SK\|STS` 可以領取，但約一小時後到期且無法續期 |
| `PUSHPLUS_TOKEN`、`BARK_URL`、`WECOM_WEBHOOK`、`DINGTALK_WEBHOOK`、`DINGTALK_SECRET` | 選填推送 |
| `QL_URL`、`QL_TOKEN` | 選填青龍通知位址與舊版面板 Token |

多帳號使用換行或 `&` 分隔；每個 JSON 必須獨立一行。

## 成功判據與隱私

回讀狀態為 `CONFIRMED` 或 `CONSUMED` 才算成功。若活動已是 `CLAIMED` 卻缺少 `userBenefitId`，腳本會停止，不會重放 claim 或猜測確認 ID。

`codearts_credentials.json` 含 AK/SK/STS、refresh_token、PKCE 與 DPoP 私鑰；`codearts_welfare_ledger.json` 含冪等鍵與限流狀態。兩者都已被 Git 忽略，請勿在 Issue 公開。

## 使用邊界與轉載聲明

本專案的官方版本免費，包括倉庫、腳本、部署說明與 Release 下載。

未經作者明確書面許可，不得將本專案包裝為付費資源、內部版、獨家版、會員權益、收費課程、付費部署或包更新服務；不得搬運到無關帳號、群組或頻道進行漲粉、截流或引流；不得刪除作者與版權資訊後冒充原創；不得使用作者暱稱、頭像、收款碼或專案名稱製造官方授權背書假象。

違規時，作者可要求下架相關內容，並可暫停更新、封存或刪除倉庫。完整規則見 [NOTICE.md](../NOTICE.md)。

## 專案連結

- [Releases](https://github.com/L0NE-6/CodeArts-Daily/releases)
- [Issues](https://github.com/L0NE-6/CodeArts-Daily/issues)
- [原始碼與完整中文文件](../README.md)
