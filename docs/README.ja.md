# 🛠️ CodeArts Daily

CodeArts の日次特典と一度限りの新規登録特典を自動取得します。claim と confirm の後で特典一覧を再取得するため、「受理された」だけでは成功扱いにしません。

[简体中文](../README.md) · [English](README.en.md) · [繁體中文](README.zh-Hant.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Português (BR)](README.pt-BR.md)

**現在のバージョン：** v1.0.6

完全な中国語ドキュメントは [../README.md](../README.md) を参照してください。

## 主な機能

- デスクトップ版の `delivery → claim → confirm → delivery 再取得` フローを使用します。
- Huawei Cloud の `SDK-HMAC-SHA256` で署名し、デスクトップ版と同じ `Host` ヘッダーを含めます。
- 自動ローカルコールバックを伴う PKCE + DPoP ログインに対応します。
- 期限前に認証情報を更新し、アトミックに保存します。
- 使用済み refresh token、保存失敗、`STS5.1806` を終端状態として扱います。
- 冪等キーを先に保存し、1 日 6 回まで、10 分以上の間隔で書き込みを制限します。

## Qinglong 最小構成

```bash
python3 -m pip install -r requirements.txt
```

`codearts_daily.py` をアップロードし、`CODEARTS_CREDENTIALS` を設定してタスクを作成します。

```text
40 8 * * * task codearts_daily.py
```

認証情報はローカルで取得します。

```bash
python codearts_login.py
python codearts_login.py --paste --no-browser
python codearts_login.py --note main
```

コールバックは `127.0.0.1` で待ち受けます。Qinglong がリモートでもログインツールはローカルで実行してください。

## GitHub Actions

**Settings → Secrets and variables → Actions** で次を作成します。

```text
CODEARTS_CREDENTIALS
PUSHPLUS_TOKEN          # 任意
BARK_URL                # 任意
WECOM_WEBHOOK           # 任意
DINGTALK_WEBHOOK        # 任意
DINGTALK_SECRET         # 任意
```

その後 **Actions → CodeArts Daily → Run workflow** から手動実行します。既定では手動のみです。スケジュールを使う場合は `.github/workflows/daily.yml` の `schedule:` を有効にしてください。cron は UTC です。

## 主要な環境変数

| 変数 | 形式と用途 |
| :--- | :--- |
| `CODEARTS_CREDENTIALS` | 1 行 JSON。refresh token、PKCE、DPoP 秘密鍵が含まれる場合は自動更新可能 |
| `CODEARTS_CREDENTIALS` | `AK\|SK\|STS` でも取得できますが、約 1 時間で期限切れになり更新できません |
| `PUSHPLUS_TOKEN`、`BARK_URL`、`WECOM_WEBHOOK`、`DINGTALK_WEBHOOK`、`DINGTALK_SECRET` | 任意の通知設定 |
| `QL_URL`、`QL_TOKEN` | 任意の Qinglong 通知先と旧パネルトークン |

複数アカウントは改行または `&` で区切ります。各 JSON は 1 行ずつ配置してください。

## 成功判定とプライバシー

再取得した状態が `CONFIRMED` または `CONSUMED` の場合だけ成功です。`CLAIMED` なのに `userBenefitId` がない場合は、claim を再送せず確認 ID も推測しません。

`codearts_credentials.json` には AK/SK/STS、refresh token、PKCE、DPoP 秘密鍵が含まれます。`codearts_welfare_ledger.json` には冪等キーと制限状態が入ります。どちらも Git 対象外です。Issue に認証情報を貼らないでください。

## 利用範囲と再配布について

本プロジェクトの公式版は無料です。リポジトリ、スクリプト、デプロイ手順、Release ダウンロードを含みます。

作者の明示的な書面許可なく、本プロジェクトを有料リソース、内部版、限定版、会員特典、有料講座、有料デプロイ、更新販売として再パッケージしないでください。無関係なアカウント、グループ、チャンネルへ転載して集客や誘導を行うこと、作者・著作権表示を削除して自作と主張すること、作者名・アバター・QR コード・プロジェクト名を使って公式承認を装うことも禁止します。

違反時は削除要請の対象となる場合があります。作者は更新の停止、リポジトリのアーカイブまたは削除を行うことがあります。完全な規則は [NOTICE.md](../NOTICE.md) を参照してください。

## リンク

- [Releases](https://github.com/L0NE-6/CodeArts-Daily/releases)
- [Issues](https://github.com/L0NE-6/CodeArts-Daily/issues)
- [ソースと完全な中国語ガイド](../README.md)
