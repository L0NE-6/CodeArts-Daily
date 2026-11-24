<div align="center">

<sub><strong>L0NE-6 · DAILY SIGNAL</strong></sub>

# 🛠️ CodeArts Daily

**CodeArts 每日福利与新人注册礼领取，以 delivery → claim → confirm → delivery 回读闭环确认到账。**

> 当前版本：**v1.0.6**（2026-11-04） · 核心能力：PKCE + DPoP 登录、HMAC 签名、凭据续期、福利确认、幂等限流

[简体中文](README.md) · [English](docs/README.en.md) · [繁體中文](docs/README.zh-Hant.md) · [日本語](docs/README.ja.md) · [한국어](docs/README.ko.md) · [Português (BR)](docs/README.pt-BR.md)

<p>
  <img src="https://img.shields.io/github/v/release/L0NE-6/CodeArts-Daily?style=for-the-badge&label=Release&color=2ea44f&logo=github" alt="Release" />
  <img src="https://img.shields.io/github/stars/L0NE-6/CodeArts-Daily?style=for-the-badge&label=Stars&color=FFC75F&logo=github" alt="Stars" />
  <img src="https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.8+" />
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20Qinglong-4EAA25?style=for-the-badge&logo=linux&logoColor=white" alt="Platform" />
  <img src="https://img.shields.io/github/license/L0NE-6/CodeArts-Daily?style=for-the-badge&label=License&color=F472B6" alt="License" />
  <a href="https://github.com/L0NE-6/CodeArts-Daily/releases"><img src="https://img.shields.io/badge/Download-Releases-2ea44f?style=for-the-badge&logo=github" alt="Download" /></a>
</p>

[🚫 使用边界](#usage-policy) · [✨ 30 秒速览](#overview) · [🧭 这是什么](#what-is-this) · [🔁 工作原理](#protocol) · [🔑 凭据](#credentials) · [🚀 本地](#local) · [🐧 青龙](#qinglong) · [☁️ Actions](#actions) · [⌨️ CLI](#cli-output) · [🧾 结果码](#result-codes) · [✅ 成功判据](#success) · [🧪 测试](#tests) · [🧱 设计原则](#design) · [🔒 隐私](#privacy) · [📁 目录](#layout) · [📦 版本](#release) · [⚠️ 免责声明](#disclaimer) · [☕ 赞赏](#donate) · [💬 反馈与 Star](#feedback)

</div>

---

<a id="usage-policy"></a>
## 🚫 使用边界与转载声明

> [!IMPORTANT]
> **官方版本永久免费。** 未经作者书面许可，禁止付费包装、搬运引流、冒充作者，或使用作者身份与二维码制造官方授权假象。

本项目仓库、脚本、部署说明和 Release 下载始终免费公开。未经作者明确书面许可，禁止将其包装为付费资源、内部版、独家版、会员权益、收费课程、付费部署或包更新服务；禁止搬运到其他账号、群组、频道、网盘、电商或付费平台进行涨粉、截流、倒卖和引流。

如需商业合作、品牌授权、联合分发或使用作者名义提供付费服务，请先取得作者明确书面授权。完整规则见 [NOTICE.md](NOTICE.md)。

---

<a id="overview"></a>
## ✨ 30 秒速览

| 维度 | 说明 |
| :--- | :--- |
| **做什么** | 领取 CodeArts 每日福利，并补领可自动处理的新人注册礼。 |
| **输入** | `CODEARTS_CREDENTIALS`：可续期的单行 JSON，或 `AK\|SK\|STS` 简写。 |
| **输出** | 分账号领取报告，按活动显示实际金额、确认状态、终态和失败原因。 |
| **部署** | Windows、Linux、青龙面板、GitHub Actions。 |
| **依赖** | `requests`、`cryptography`。 |
| **成功判据** | delivery 回读状态为 `CONFIRMED` 或 `CONSUMED`，不是 claim/confirm 的受理回执。 |

---

<a id="what-is-this"></a>
## 🧭 这是什么

仓库包含网页登录工具和福利领取脚本：

- `codearts_login.py`：PKCE + DPoP 授权登录，生成本地凭据 JSON。
- `codearts_daily.py`：读取活动列表、领取每日福利和新人注册礼、确认到账、续期凭据。

每日福利和新人注册礼分别提交、分别回读。学生认证、邀请好友等不进入自动领取链路。脚本对写请求使用幂等键和本地限流，避免重复领取和高频重试。

---

<a id="protocol"></a>
## 🔁 协议、工作原理与回读

Ops API 基址为 `https://snap-access.cn-north-4.myhuaweicloud.com`，STS 换票地址为 `https://sts.cn-north-4.myhuaweicloud.com/v1/oauth2/tokens`。

```text
GET  /v1/ops/delivery?channel=DESKTOP
POST /v1/ops/claim
POST /v1/ops/confirm
GET  /v1/ops/delivery?channel=DESKTOP
```

请求使用 `SDK-HMAC-SHA256` 签名，并按桌面客户端口径包含 `Host`。领取结果必须再次读取 delivery，只有活动状态变成 `CONFIRMED` 或 `CONSUMED` 才算到账。

凭据包含 refresh token、PKCE 材料和 DPoP 私钥。续期在到期前 15 分钟触发，成功写入临时文件后原子替换。一次性 refresh token 已被消费、写入失败或返回 `STS5.1806` 时进入终态，后续运行不再重试旧凭据。

---

<a id="credentials"></a>
## 🔑 凭据与环境变量

| 变量 | 格式 | 说明 |
| :--- | :--- | :--- |
| `CODEARTS_CREDENTIALS` | 单行 JSON | 推荐；包含 refresh token、PKCE 与 DPoP 私钥，可续期 |
| `CODEARTS_CREDENTIALS` | `AK\|SK\|STS` | 可领取，约 1 小时到期，不能自动续期 |
| `PUSHPLUS_TOKEN` / `BARK_URL` | Token / URL | 可选推送 |
| `WECOM_WEBHOOK` | Webhook 或 key | 企业微信 |
| `DINGTALK_WEBHOOK` / `DINGTALK_SECRET` | Webhook / 密钥 | 钉钉 |
| `QL_URL` / `QL_TOKEN` | 面板地址 / 旧版 Token | 青龙通知 |

多账号使用换行或 `&` 分隔。JSON 凭据必须每个账号独占一行；简写形式可以用 `&` 串接。

登录：

```bash
python -m pip install cryptography
python codearts_login.py
python codearts_login.py --paste --no-browser
python codearts_login.py --note 主号
```

登录参数：

| 参数 | 作用 |
| :--- | :--- |
| `--paste` | 手动粘贴回调地址或授权码 |
| `--no-browser` | 不自动打开浏览器 |
| `--no-verify` | 跳过换取凭据后的校验 |
| `--note 主号` | 写入账号备注 |
| `--port 8765` | 指定本地回调端口 |

---

<a id="local"></a>
## 🚀 本地快速开始

```bash
python -m pip install -r requirements.txt
```

先只读查看活动：

```bash
python codearts_daily.py --preview
```

执行领取：

```bash
python codearts_daily.py
python codearts_daily.py --only 1
```

需要临时跳过本地写请求限流时：

```bash
python codearts_daily.py --force
```

---

<a id="qinglong"></a>
## 🐧 青龙面板

```bash
python3 -m pip install -r requirements.txt
```

将 `codearts_daily.py` 上传到青龙，把凭据 JSON 放入 `CODEARTS_CREDENTIALS`，再创建任务：

```text
# 每天北京时间 08:40
40 8 * * * task codearts_daily.py
```

青龙运行在远程服务器时，请在本地电脑运行 `codearts_login.py`，再把输出 JSON 填入面板。登录回调指向 `127.0.0.1`，远程面板不能直接接收本机回调。

---

<a id="actions"></a>
## ☁️ GitHub Actions

工作流位于 [`.github/workflows/daily.yml`](.github/workflows/daily.yml)。当前只启用 `workflow_dispatch`，定时段保持注释；示例 cron `40 0 * * *` 对应北京时间 08:40。

| Secret | 必填 | 说明 |
| :--- | :---: | :--- |
| `CODEARTS_CREDENTIALS` | 是 | 单行 JSON；多个账号每个账号一行 |
| `PUSHPLUS_TOKEN` / `BARK_URL` | 可选 | PushPlus / Bark |
| `WECOM_WEBHOOK` | 可选 | 企业微信 |
| `DINGTALK_WEBHOOK` / `DINGTALK_SECRET` | 可选 | 钉钉与加签 |

Actions 不保留本地凭据文件和台账。refresh token 轮换后需要重新更新 Secret；长期运行优先使用可持久化目录。

---

<a id="cli-output"></a>
## ⌨️ CLI 与输出

| 命令 | 作用 |
| :--- | :--- |
| `python codearts_daily.py` | 完整领取并回读 |
| `python codearts_daily.py --preview` | 只读活动列表，不发写请求 |
| `python codearts_daily.py --force` | 跳过本地写请求限流 |
| `python codearts_daily.py --only 2` | 只处理第二个账号 |
| `python codearts_daily.py --no-notify` | 关闭本轮推送 |

输出按账号分块，显示每日福利、新人注册礼、实际金额、确认状态和终态错误。进程正常结束不代表每个账号都成功，必须查看逐账号报告。

---

<a id="result-codes"></a>
## 🧾 结果码

| 结果 | 含义 |
| :--- | :--- |
| `CONFIRMED` | 活动已确认到账 |
| `CONSUMED` | 活动已消费或完成，按到账处理 |
| `CLAIMED` | 已领取但尚未确认，需要继续 confirm 与回读 |
| `HTTP 200 + 空 body` | 会话过期，账号进入终态 |
| `STS5.1806` | refresh token 已使用或失效，必须重新登录 |
| 日任务进程退出码 `0` | 进程正常结束；逐账号结论以报告为准 |
| 登录退出码 `0` / `1` / `130` | 成功 / 失败 / 用户中断 |

---

<a id="success"></a>
## ✅ 成功判据

一次活动领取成功必须同时满足：

1. delivery 中存在对应活动记录。
2. claim 返回可确认的 `userBenefitId`。
3. confirm 请求完成。
4. 再次读取 delivery 后，状态为 `CONFIRMED` 或 `CONSUMED`。

claim/confirm 仅返回 `code: 0` 只是受理。缺少 `userBenefitId` 时脚本停止确认，不重放 claim，也不拿 `campaignId` 代替。

---

<a id="tests"></a>
## 🧪 测试

```bash
python -m unittest discover -s tests -v
python -m py_compile codearts_daily.py codearts_login.py
git diff --check
```

现有 21 项离线测试覆盖桌面请求头、claim/confirm 关联、缺少 benefit ID 时关闭确认、v2→v3 台账迁移、写盘失败、终态凭据、`STS5.1806`、空 200 响应、401 分类和 OAuth client_id 往返。

---

<a id="design"></a>
## 🧱 设计原则

- **先读后写**：默认从 delivery 获取真实活动状态。
- **回读定成败**：claim/confirm 受理不直接宣布成功。
- **终态保护**：一次性 refresh token 消费后停止使用旧凭据。
- **原子落盘**：新凭据完整写入后才替换旧文件。
- **幂等与限流**：幂等键先落盘，每天最多 6 次写尝试，间隔至少 10 分钟。
- **账号隔离**：单账号失败不阻断其他账号。

---

<a id="privacy"></a>
## 🔒 隐私与数据边界

| 文件 | 内容 | 提交 |
| :--- | :--- | :---: |
| `codearts_credentials.json` | 续期后的完整凭据、DPoP 私钥 | 否 |
| `codearts_welfare_ledger.json` | 幂等键、限流计数、一次性福利状态 | 否 |

仓库不含真实账号材料。DPoP 私钥与 refresh token 同等敏感；提交 Issue 前必须移除凭据、AK/SK/STS、私钥和本机路径。

---

<a id="layout"></a>
## 📁 目录结构

```text
CodeArts-Daily/
├── .github/workflows/daily.yml
├── assets/
├── docs/
├── tests/
├── codearts_daily.py
├── codearts_login.py
├── CHANGELOG.md
├── LICENSE
├── NOTICE.md
├── requirements.txt
└── README.md
```

---

<a id="release"></a>
## 📦 版本与发布

- 当前版本：`v1.0.6`，续期时保留凭据中的 OAuth client_id。
- 历史版本保留在 [Releases](https://github.com/L0NE-6/CodeArts-Daily/releases)。
- 每次发布包含完整包、脚本单文件和校验文件。
- 变更记录见 [CHANGELOG.md](CHANGELOG.md)。

---

<a id="disclaimer"></a>
## ⚠️ 免责声明

本项目用于个人学习与合法自动化实践。使用者应自行确认账号、服务条款和部署环境；因误配置、凭据泄露、服务策略变化或账号异常产生的风险由使用者自行承担。

---

<a id="donate"></a>
## ☕ 支持与投喂：微信与支付宝赞赏码

脚本完全免费，赞赏纯自愿，不影响任何功能。

<p align="center">
  <img src="assets/donate-wechat.png" width="260" alt="微信赞赏码" />
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
  <img src="assets/donate-alipay.jpg" width="260" alt="支付宝收款码" />
</p>

<p align="center"><sub>微信支付（左） · 支付宝（右）</sub></p>

> [!WARNING]
> 收款码仅用于向作者自愿赞赏。任何第三方以代下载、代部署、内部资源、会员群或官方授权为由收费，均与作者无关。

---

<a id="feedback"></a>
## 💬 反馈与贡献：Star History

- [Issues](https://github.com/L0NE-6/CodeArts-Daily/issues)
- [Pull Requests](https://github.com/L0NE-6/CodeArts-Daily/pulls)
- [Releases](https://github.com/L0NE-6/CodeArts-Daily/releases)

<a href="https://star-history.com/#L0NE-6/CodeArts-Daily&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=L0NE-6/CodeArts-Daily&type=Date&theme=dark" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=L0NE-6/CodeArts-Daily&type=Date&theme=light" />
    <img alt="CodeArts Daily Star History" src="https://api.star-history.com/svg?repos=L0NE-6/CodeArts-Daily&type=Date&theme=light" />
  </picture>
</a>

<div align="center">

[⭐ Star](https://github.com/L0NE-6/CodeArts-Daily) · [🍴 Fork](https://github.com/L0NE-6/CodeArts-Daily/fork) · L0NE-6 · DAILY SIGNAL

</div>
