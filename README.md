<div align="center">

# 🛠️ CodeArts Daily

**CodeArts 每日福利领取 · PKCE + DPoP 登录 · 单文件青龙脚本 · 多账号**

<img src="https://img.shields.io/github/v/release/L0NE-6/CodeArts-Daily?style=flat-square&label=Release&color=2ea44f" />
<img src="https://img.shields.io/github/stars/L0NE-6/CodeArts-Daily?style=flat-square&label=Stars&color=FFC75F" />
<img src="https://img.shields.io/badge/Python-3.8%2B-3776AB?style=flat-square&logo=python&logoColor=white" />
<img src="https://img.shields.io/badge/%E9%9D%92%E9%BE%99%E9%9D%A2%E6%9D%BF-%E5%8D%95%E6%96%87%E4%BB%B6%E8%BF%90%E8%A1%8C-4EAA25?style=flat-square" />
<img src="https://img.shields.io/badge/GitHub%20Actions-%E6%94%AF%E6%8C%81-2088FF?style=flat-square&logo=githubactions&logoColor=white" />
<img src="https://img.shields.io/badge/%E5%A4%9A%E8%B4%A6%E5%8F%B7-%E6%8D%A2%E8%A1%8C%E6%88%96%20%26%20%E5%88%86%E9%9A%94-8957E5?style=flat-square" />
<img src="https://img.shields.io/badge/License-MIT-F472B6?style=flat-square" />

</div>

---

## ✨ 这是什么

CodeArts 每日福利领取：活动列表 → 领取 → 确认 → 回读验证，四个环节都通过才算成功，避免「已受理但没到账」。凭据到期前自动续期，长期无人值守。

顺带把**新人注册礼**这类一次性奖励也接入同一条领取链路：能领就领，领完记档，不会反复骚扰上游。

> 🎯 一句话：**配好 Token，剩下的交给它。**
>
> 📦 单文件自包含：不需要额外模块，青龙上传脚本、填好环境变量就能跑。
>
> ☁️ 除了青龙，也可以直接跑在 **GitHub Actions** 上，零服务器定时执行（见下文部署方式二）。

核心特性：

- ✅ **四步闭环**：桌面口径 delivery → claim → userBenefitId confirm → 回读验证
- 🔐 **PKCE + DPoP 登录**：官方授权流，本地回调自动换凭据
- ♻️ **凭据自动续期**：到期前 15 分钟自动换新并落盘
- 🧯 **续期终态保护**：一次性 refresh_token 续期成功后若落盘失败，账号立即标记终态并要求重新登录；`STS5.1806` 同样按终态处理，避免静默死号
- 🎁 **新人注册礼**：与每日福利共用领取执行体，一次性奖励自动补领，领完记本机不重查
- 🧾 **本地幂等台账**：幂等键先落盘、写请求限流（每天 6 次 / 间隔 10 分钟）、回读确认才记成功
- 🔁 **台账平滑升级**：v1.0.2 的 v2 台账会自动迁移到 v3，旧幂等键继续复用
- 👥 **多账号** + 📢 **多渠道推送** + 🐧 **青龙 / Actions 双部署**

## 📦 文件说明

| 文件 | 作用 |
|---|---|
| `codearts_login.py` | PKCE + DPoP 网页登录，输出凭据 JSON |
| `codearts_daily.py` | 每日福利领取（多账号、自动续期） |

## ⬇️ 下载

不想用 git？直接到 **[Releases](https://github.com/L0NE-6/CodeArts-Daily/releases)** 下载：

- 完整包 zip（脚本 + 登录工具 + README + Actions 工作流 + 收款码）
- 各脚本单文件（青龙只需要上传签到脚本）
- `SHA256SUMS.txt` 完整性校验

## 🚀 部署方式一：青龙面板（三步）

| 步骤 | 操作 |
| :---: | :--- |
| 1 | 安装依赖：`pip install -r requirements.txt`（或 `pip3 install requests`） |
| 2 | 把签到脚本上传到青龙「脚本管理」，或把仓库放进脚本目录 |
| 3 | 「环境变量」里添加 Token，新建定时任务（见下方 cron 示例） |

```cron
40 8 * * * python codearts_daily.py
```

## ☁️ 部署方式二：GitHub Actions（可选，默认手动触发）

1. Fork 本仓库（或直接使用本仓库，Secrets 只能配在你自己的仓库里）。
2. 打开 **Settings → Secrets and variables → Actions**，添加下表里的 Secrets。
3. 打开 **Actions** 标签页，选择 `CodeArts Daily`，点 **Run workflow** 手动跑一次验证。
4. 默认只支持**手动触发**（上游仓库不跑定时，避免空跑）；fork 后想定时，把 `.github/workflows/daily.yml` 里 `schedule:` 两行取消注释（cron 用 UTC，北京时间减 8 小时），之后就会按该时间自动执行。

| Secret | 对应环境变量 | 必填 |
|---|---|---|
| `CODEARTS_CREDENTIALS` | CODEARTS_CREDENTIALS | 必填（单行 JSON） |
| `PUSHPLUS_TOKEN` / `BARK_URL` / `WECOM_WEBHOOK` / `DINGTALK_WEBHOOK` / `DINGTALK_SECRET` | 同名推送变量 | 可选 |

> 公开仓库的 Secrets 是加密的，日志里不会回显；脚本也不会把 Token 写进仓库文件。

## 🔑 获取 Token

```bash
pip install cryptography
python codearts_login.py
```

浏览器完成登录后，本地回调自动换回凭据，输出一行 JSON，粘贴进 `CODEARTS_CREDENTIALS`。

- 端口被占用或回调不便：加 `--paste`，手动粘贴回调地址。
- **青龙在服务器上时**：登录回调指向 `127.0.0.1`，请在本地电脑跑登录工具，再把 JSON 填进面板。
- 输出的 JSON 包含 refresh_token 与 DPoP 私钥，是自动续期的必要材料，请按密码级别保管。

## 🧩 环境变量（支持多账号）

> 多账号用 **换行** 或 **`&`** 分隔，两种可以混用。`|` 是单条账号内部的字段分隔符，备注里不要再写 `|`。

| 环境变量 | 单条格式 | 说明 |
|---|---|---|
| `CODEARTS_CREDENTIALS` | 单行 JSON（推荐，可自动续期）；或 `AK\|SK\|STS` 简写 | JSON 必须每条独占一行；简写可用 `&` 串接 |

## ⌨️ 命令行参数

| 参数 | 作用 |
|---|---|
| `--preview` | 只读活动列表，不发领取请求 |
| `--force` | 忽略本地写请求限流（当天最多 6 次 / 间隔 10 分钟） |
| `--only 2` | 只跑第 2 个账号 |
| `--no-notify` | 关闭推送 |

## 📊 运行效果示例

```text
[08:40:01] 👤 [1] 主号  AK=AKID****abcd
[08:40:04]    ✅ 福利已确认到账：1 个活动，共 100（本次提交 1 笔）
[08:40:05] 账号1 主号: ✅ 福利已确认到账：1 个活动，共 100

领取时如果既有每日福利又有新人注册礼，会一次性提交并在回读后一起汇报：

```text
[08:40:04]    ✅ 福利已确认到账：每日福利 1000；新人注册礼 4000（本次提交 2 笔）
[08:40:05] 账号1 主号: ✅ 福利已确认到账：每日福利 1000；新人注册礼 4000
```
```

## 🗂️ 数据文件说明

| 文件 | 内容 | 是否提交 |
|---|---|---|
| `codearts_credentials.json` | 续期后的凭据（含 DPoP 私钥） | 已忽略 |
| `codearts_welfare_ledger.json` | 领取台账（幂等键 / 限流计数 / 一次性福利结清标记，不含凭据） | 已忽略 |

> 以上文件已在 `.gitignore` 中排除，**不要手动提交**。

## ❓ 常见问题

- **为什么必须回读验证？** `claim`/`confirm` 只代表受理，回读状态变成 CONFIRMED 才算真的到账。
- **新人注册礼会自动领吗？** 会，它和每日福利共用同一套领取链路，一次性领取；学生认证、邀请好友不自动领。
- **为什么有时候提示「本地限流」？** 领取是写请求，台账限制每天最多 6 次、两次间隔至少 10 分钟；需要立刻重试时加 `--force`。
- **`AK|SK|STS` 简写能自动续期吗？** 不能，只有含 refresh_token + DPoP 私钥的 JSON 才能续期。
- **JSON 能一行填多个吗？** 不行，JSON 必须每条独占一行；简写形式可以用 `&` 串接。
- **提示「终态 / 需重新登录」是什么意思？** 一次性 `refresh_token` 被服务端消耗后，若新凭据落盘失败，或 STS 返回 `STS5.1806`（token 已被使用），本地已无法再续期；脚本会当场标记终态并停止重试，请用 `codearts_login.py` 重新登录。

## 📁 目录结构

```text
CodeArts-Daily/
├── codearts_login.py
├── codearts_daily.py
├── assets/
├── .github/workflows/daily.yml
├── CHANGELOG.md
├── LICENSE
├── README.md
└── requirements.txt
```

## 📦 版本与发布

- 当前版本：`v1.0.5`（2026-10-30）。
- 每次更新单独发一个 Release：`v1.0.0` → `v1.0.1` …，历史版本保留可下载。
- 每个 Release 附带：完整包 zip + 各脚本单文件 + `SHA256SUMS.txt`。
- 下载页：<https://github.com/L0NE-6/CodeArts-Daily/releases>

## 🔒 隐私说明

- 脚本**不含任何账号、手机号、Token 或设备信息**，全部由环境变量（或 GitHub Secrets）注入。
- 运行期生成的数据文件（见「数据文件说明」）已被 `.gitignore` 排除：凭据文件含登录材料，台账只含领取记录，都不会进入仓库。
- 请勿把 Token 写进脚本、提交到仓库或发到 Issue 里。

## ⚠️ 免责声明

本项目仅供**学习与个人自动化**使用。请遵守对应平台的服务条款，使用风险自负。

## ☕ 支持与投喂

脚本是**完全免费、无广告、无功能限制**的，仓库与发布包也不含你的任何数据。
如果它确实帮你省了时间，欢迎请我喝杯咖啡 —— **纯自愿，不影响任何功能**。

<p align="center">
  <img src="assets/donate-wechat.png" width="240" alt="微信赞赏码" />
  &nbsp;&nbsp;&nbsp;&nbsp;
  <img src="assets/donate-alipay.jpg" width="240" alt="支付宝收款码" />
</p>
<p align="center"><sub>💚 微信支付（左） &nbsp;|&nbsp; 💙 支付宝（右）</sub></p>

> 💡 **不花钱也能帮上忙**：点个 ⭐ Star、提一个带日志的 Issue、发一个 Pull Request，或者把脚本分享给需要的朋友。

## 💬 反馈与贡献

- 提交 [Issue](https://github.com/L0NE-6/CodeArts-Daily/issues)：报 bug、提需求
- 发起 [Pull Request](https://github.com/L0NE-6/CodeArts-Daily/pulls)：直接贡献代码

> 提 Issue 时附上**运行日志**和**复现步骤**，定位会快很多。

---

<div align="center">
  <sub>🛠️ 如果这个脚本帮到你，点个 <b>Star</b> 支持一下，或者到 <a href="#-支持与投喂">支持与投喂</a> 请我喝杯咖啡 ✨</sub>
</div>
