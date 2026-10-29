# 更新日志

## v1.0.4（2026-10-29）

- `save_store` 不再吞掉凭据写入异常：改为临时文件 + `os.replace` 原子落盘，失败时抛出 `CredentialStoreError`，避免半截文件覆盖旧凭据。
- 续期成功后若新凭据落盘失败，账号立即标记终态并抛出 `TerminalCredentialError`：服务端已消耗一次性 `refresh_token`，本地旧 token 永久失效，继续重试只会得到 `STS5.1806`，必须重新登录。
- `STS5.1806`（`error_code` / `error_msg` 两条腿）以及 `refresh token has been used` 归为终态；终态标记写入 `codearts_credentials.json`，后续运行直接跳过该账号。
- `ensure_fresh` 不再把终态异常吞成「自动续期失败后继续用旧凭据」；主流程单独报告「终态：需重新登录」。
- 成功续期路径保持不变；新增 8 项离线回归测试，覆盖写盘失败、STS5.1806 两条报文腿、成功续期与普通 5xx 非终态，测试总数 13 项。
- 实证来源：[iJetLi/dsh-providers-hub@7167acb0](https://github.com/iJetLi/dsh-providers-hub/commit/7167acb0)。

## v1.0.3（2026-10-22）

- 福利列表与领取渠道从 `IDE` 切换到桌面客户端口径 `DESKTOP`，并按桌面客户端方式签名包含 `Host`。
- 领取响应改为解析 `userBenefitId` / `user_benefit_id` / `benefitId` / `id`，不再强制要求回传 `campaignId`。
- 确认请求改为最新合同的 `{"userBenefitId": ...}`；不再用 `campaignId` 冒充确认 ID。
- 请求头语言改为 `zh-cn`，delivery 请求补充 `x-snap-traceid`；响应兼容 `code=0/200` 与 `data/result`。
- 新幂等键改为 UUID；旧台账中的 `idempotentKey` 原样复用。台账版本从 v2 自动迁移到 v3。
- 已领取但缺少 `userBenefitId` 时 fail closed，不重放 claim，不猜测确认 ID。
- 新增 5 项离线测试，覆盖桌面请求头、claim/confirm 合同、无 campaignId 响应、缺 ID 防误领和台账迁移。

## v1.0.2（2026-10-10）

- **新人注册礼接入签到链路**：与每日福利共用领取执行体，幂等键先落盘、领取后回读活动列表确认；学生认证 / 邀请好友不提供自动领取入口。
- **清单口径统一**：查询、领取、回读使用同一套筛选逻辑；任务标题按活动类映射中文（每日签到 / 用户登录送积分 / 新用户注册礼 / 学生认证 / 邀请好友），认不出的回退原文。
- **本地领取台账**：每天最多 6 次写尝试、两次间隔至少 10 分钟，新增 `--force` 可跳过限流；一次性福利结清后记本机，不再重复查询。
- **报错提示优化**：「无福利档案」类报错补充说明（官方建档后稍后重试即可）。

## v1.0.1（2026-10-09）

- Actions 工作流默认改为**仅手动触发**：上游仓库不再空跑定时任务。
- fork 后如需定时，取消 `.github/workflows/daily.yml` 里 `schedule:` 的注释即可。
- README 同步补充 fork 启用定时的说明。

## v1.0.0（2026-10-09）

- 首个公开版本
- 首个版本：CodeArts 每日福利领取 + PKCE/DPoP 登录工具，支持多账号与凭据自动续期。

> 每个版本单独发布 Release，历史版本保留可下载。
