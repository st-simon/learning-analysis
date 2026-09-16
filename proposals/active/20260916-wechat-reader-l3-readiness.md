# 微信公众号文章读取：L3 正式化就绪提案

- ID：20260916-wechat-reader-l3-readiness
- Proposal policy version: 1.2
- Impact level: high
- Impact triggers: architecture, trust-boundary, auth-secrets, deployment-infrastructure, sensitive-data, migration-replacement, route-invalidating-uncertainty
- Proposal readiness: required
- Status: proposed
- Approval scope: spike-only
- Core gate: pending
- Cost gate: not-applicable
- Contradiction gate: clear
- Outcome confirmation: confirmed
- Confirmation source: 用户于 2026-09-15 明确 L1/L2/L3 分层需求和禁止手工搬运正文；2026-09-16 批准 Gate 0 后续 proposal
- Assumption freshness gate: recheck-required
- External evidence gate: passed
- Rollback gate: ready
- Implementation verification: stage-gated
- 更新日期：2026-09-16
- 项目：learning-analysis
- 分支：codex/gce-reader-implementation（历史名称；本提案不创建或切换分支）
- Security/Ops：required；涉及浏览器页面内容、本机常驻进程、运行密钥、远程 MCP 和安装/卸载

## Background

Gate 0 已完成并验证路线 B 的来源与传输可行性：3 篇真实公众号文章均由正常 Chrome 已渲染 DOM 自动提取成功；其中 1 篇 22,084 字文章经本地 MCP 与 Platform tunnel 在 ChatGPT App/Web 返回一致结果。扩展只使用 `activeTab`、`scripting` 和固定 loopback 权限，没有读取 Cookie、历史或浏览器存储；正文仅存在于进程内存。

Reader 直读的唯一探针在主机 DNS 安全检查阶段被 `198.18.0.0/15` 合成地址拦截，未进入 Jina，也未触达微信。补充核验表明该探针以 Mac 主机普通进程运行，并非 Codex 沙箱请求；但 Mac 的 DNS 与路由经 `utun`/Fake-IP 机制把目标解析为 `198.18.0.210`，Jina 容器也得到同一地址。因此该结果只能判为 `inconclusive`：它暴露了“主机入口安全判断”和“Reader 实际出口环境”不一致，不能证明 Reader 或微信访问失败。Reader 不进入当前 L3 主路线，也没有被永久淘汰；若重启该路线，必须另提案验证实际出口边界并保持 SSRF 防护。Cloudflare + Jina SaaS 路线继续冻结，不作为来源或回退。

Gate 0 仍是人工启动的 disposable spike。它没有证明日常使用无需终端、进程能自动恢复、扩展身份能稳定绑定，也没有证明一次 ChatGPT 工具调用可以等待用户在 Chrome 授权后自动返回。因此不能直接把 spike 宣称为 L3 产品。

## Purpose

用最小、可逆、零费用的两阶段正式化就绪 Gate 验证 L3 剩余承重条件。当前只申请 Gate 1A：先验证同次调用等待窗口与扩展配对；Gate 1A 通过后必须停下汇报，Gate 1B 的后台生命周期与恢复测试需另行批准。Gate 1A、Gate 1B 均通过后，才另行提交 `full-implementation` proposal。不得把“用户点击扩展后还需复制正文、重新提交正文或切换到旧 Reader”作为通过。

## User Need And Core Outcome

### L3 核心结果

用户在 Mac 的 ChatGPT App 或 Web 中提交一个公众号 URL。若需要浏览器来源，系统最多要求一次明确的 Chrome 授权动作；随后同一次读取流程自动返回标准文章结果。安装完成后，日常使用不需要终端命令，不复制、打印、保存或上传正文。

### 确认状态

`confirmed`。来源是用户已经确认的 L3 需求、禁止人工搬运正文的硬约束，以及 Gate 0 对真实文章的验收。

### 本提案成功输出

一份结构化 Gate 1A 证据，证明或证伪：

1. App/Web 工具调用能在同一次调用的有效等待窗口内接收一次浏览器授权后的结果；
2. 扩展具有稳定身份且只有配对实例能向本机桥提交正文；
3. Gate 1A 测试完成后可完整清理，不遗留正文、后台项或临时权限。

Mac 用户级后台进程的登录启动、崩溃恢复、tunnel ready 与完整卸载属于 Gate 1B，不在本次批准范围内。

## Necessary Conditions

| 必要条件 | 证据 | 状态 |
|---|---|---|
| Chrome 已渲染 DOM 能产生可分析正文 | Gate 0 三篇 3/3，通过标题、长度和图片引用核验 | `met` |
| ChatGPT App/Web 能通过 Platform tunnel 调用本地 MCP | 固定探针和一篇真实文章双端通过 | `met` |
| 浏览器组件不读取 Cookie、历史或认证存储 | Gate 0 manifest 与运行行为通过 | `met` |
| 单次工具调用可等待用户授权并自动返回 | Gate 0 使用“先捕获、后读取”，尚未验证等待路径 | `unverified` |
| 扩展 ID 与本机提交凭据在重载后稳定 | disposable 扩展未建立正式配对 | `unverified` |
| Mac 登录后无需终端即可保持服务可用 | 当前进程由人工启动；延期到 Gate 1B | `unverified` |
| Reader 直读可作为快速通道 | 探针未到达 Reader；Mac TUN/Fake-IP 与安全检查边界不一致，当前不属于 L3 依赖 | `unverified` |
| 本机关闭时仍可读取 | 无合规云端来源；该条件不属于 L3 路线 | `unmet` |

## Constraints And Quality Gates

- 日常输入只有 URL；浏览器来源最多一次明确授权动作。
- 任何正文复制、打印、文件上传、Cookie 导出或认证材料传输均为失败。
- 仅允许 `https://mp.weixin.qq.com/s/...`；拒绝凭据、自定义端口和其他目标。
- 正文只在本机内存与本次 MCP 响应中存在；日志、Git、磁盘缓存和云端不保存正文或完整 URL。
- 本地入口只绑定 `127.0.0.1`；正式候选必须校验精确扩展 ID 和每安装随机令牌。
- 不自动重试 CAPTCHA、反爬、解析失败或超时；不切换代理、IP、供应商或浏览器指纹。
- Gate 1A 预算 USD 0；不创建账户、付费资源、云存储或公网服务。
- `.env` 当前权限为 `0644`，在任何后台启动验证前必须改为 `0600`，且不得输出内容。
- Cloudflare Worker、GitHub OAuth App、Jina key 和独立 Jina 容器均不访问、不修改、不删除。

## Verified Resources And Gaps

### 已验证资源

- Python 3.13.7、项目 `.venv`、21 项测试和 MCP smoke。
- OpenAI `tunnel-client` 0.0.14，本机二进制哈希和 App/Web 实测已记录。
- 现有 Platform tunnel `learning-analysis`；运行密钥只存在本机配置。
- Chrome Manifest V3 `activeTab` + `scripting` 的 disposable 实现与 3 篇真实样本。
- Mac arm64、macOS 15.0、约 207 GiB 可用磁盘。

### 能力缺口

- 没有等待/完成协调器，当前 `read_rendered_url` 只能读取已经捕获的内存结果。
- 捕获桥与 MCP 是两个手工启动进程，生命周期和状态分裂。
- Gate 0 只检查任意 `chrome-extension://` Origin；正式版需要精确扩展身份和令牌。
- 未建立安装、启用、健康检查、升级、卸载和故障提示。
- Python 依赖只有范围约束，没有完全可复现 lock。
- 当前 Codex/ChatGPT 旧对话可能缓存工具定义；正式升级需明确“新对话重新发现”行为。

## Candidate Mechanisms

候选机制限于本机浏览器来源及其安全传输，不重新引入 Reader、云端抓取或人工正文搬运。A 是首选，B 只在 A 被证伪后另行提案；C–E 不进入本次 Gate 1A。

## Path Comparison

| 机制 | 用户动作 | 安全/复杂度 | 结论 |
|---|---:|---|---|
| A. 精确配对的 loopback 协调器 + `activeTab` | 每次最多点击扩展一次 | 已有实测基础；需稳定 ID、随机令牌和有界等待 | 推荐 Gate 1A |
| B. Chrome Native Messaging + 本机 host | 每次最多点击一次 | 原生允许精确 `allowed_origins`，但新增 host manifest、`nativeMessaging` 权限和跨进程接口 | 保留为 A 失败后的替代，不并行实现 |
| C. 持久 `mp.weixin.qq.com` host permission + 自动 content script | 日常 0 次 | 权限更宽，会在公众号页面常驻；尚无必要 | L3 不采用 |
| D. 两阶段“捕获后再说继续” | 点击一次并再次发消息 | 技术稳，但不满足“同一次流程自动返回”的已确认结果 | 仅在用户重新接受降级后讨论 |
| E. 云端临时中转 | 0–1 次 | 新增正文传输、身份、TTL 和费用边界 | L2/L1 另提案；L3 排除 |

## Proposed Seam And Interface

正式候选只向调用方暴露一个深接口：

```text
read_url(url) -> ArticleResult
```

内部 `CaptureCoordinator` 隐藏以下行为：

```text
begin(url, request_id, deadline)
accept(capture, extension_id, install_token)
wait(request_id) -> ArticleResult | ACTION_REQUIRED_BROWSER | timeout/error
```

调用方不得选择 Reader、代理、Cookie、header 或供应商。`read_rendered_url` 仅作为迁移期诊断接口，正式插件默认只展示 `read_url`。正文校验和错误分类集中在协调器中，不复制到扩展、MCP 和测试调用方。

候选运行结构：

```text
ChatGPT App/Web
  -> OpenAI Platform tunnel
    -> tunnel-client（用户级后台项）
      -> 本地 MCP / CaptureCoordinator（同一进程）
        <- 127.0.0.1 + 精确扩展ID + 每安装令牌
          <- Chrome activeTab 扩展 <- 已渲染公众号 DOM
```

## Load-Bearing Assumptions

| ID | Claim | Consequence if false | Evidence state | Volatility | Verified at | Recheck by / trigger | Cheapest falsification probe | Stop condition | Affected route |
|---|---|---|---|---|---|---|---|---|---|
| H6 | App/Web 的同一次工具调用至少提供25秒有效等待窗口，并能在一次浏览器授权后返回 | 平台提前终止，URL 后仍需第二次消息，核心体验不成立 | `unverified` | volatile | not-run | Gate 1A 批准后、实现前；Platform或tunnel-client变化时 | App/Web 各运行5秒控制和25秒无正文 fixture；首个失败即停止。双端均通过后，各用1次真实文章并要求用户在20秒内授权 | 任一客户端超时、断开、要求第二次调用，或25秒fixture失败；不重试 | A/L3 |
| H8 | 扩展 ID 和每安装令牌可稳定配对，其他 Origin/令牌被拒绝 | loopback 可被非配对来源提交 | `unverified` | stable | not-run | manifest key、安装路径或扩展打包方式变化时 | 固定公开 manifest key；重载两次核对 ID；正确/错误 Origin 与 token 契约测试 | 身份漂移或未授权提交被接受 | A/L3 |

## Spike Evidence

| Probe ID | Assumption ID | Environment | Expected falsifier | Observed result | Evidence path | Decision |
|---|---|---|---|---|---|---|
| P6 | H6 | ChatGPT App/Web、Platform tunnel、5秒/25秒 fixture + 最多1篇文章 | 25秒等待调用断开、超时或不能自动返回 | not-run | `docs/l3-readiness-evidence.md#p6` | `not-run` |
| P8 | H8 | unpacked 扩展、loopback 契约 | ID漂移或错误凭据可提交 | not-run | `docs/l3-readiness-evidence.md#p8` | `not-run` |

## External Claims Evidence

核验日期均为 2026-09-16；这些资料支持 Gate 1A 机制选择及 Gate 1B 的延期边界，不替代真实运行证据。

| Claim ID | Claim | Volatility | Authoritative source | Verified at | Recheck by / trigger |
|---|---|---|---|---|---|
| X1 | `activeTab` 只在用户手势后临时授予当前标签页访问，并可配合 `scripting` | volatile | [Chrome activeTab](https://developer.chrome.com/docs/extensions/develop/concepts/activeTab) | 2026-09-16 | Chrome权限模型或Manifest版本变化时 |
| X2 | 跨域 loopback `fetch` 需要对应 host permission | volatile | [Chrome cross-origin requests](https://developer.chrome.com/docs/extensions/develop/concepts/network-requests) | 2026-09-16 | Chrome扩展网络模型变化时 |
| X3 | Native Messaging 支持 `allowed_origins` 绑定扩展并要求本机host manifest | volatile | [Chrome Native Messaging](https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging) | 2026-09-16 | Native Messaging协议或安装位置变化时 |
| X4 | 个人可加载unpacked扩展；Mac/Windows面向他人的自托管扩展受限 | volatile | [Chrome distribution](https://developer.chrome.com/docs/extensions/how-to/distribute) | 2026-09-16 | 进入L1或Chrome分发政策变化时 |
| X5 | 登录用户级后台进程可由LaunchAgent管理启动和恢复 | volatile | [Apple Service Management](https://developer.apple.com/documentation/servicemanagement) | 2026-09-16 | macOS目标版本或打包方式变化时 |
| X6 | 官方tunnel-client通过出站长轮询接收命令并回传MCP结果 | volatile | [OpenAI tunnel protocol](https://github.com/openai/tunnel-client/blob/master/docs/protocol.md) | 2026-09-16 | tunnel-client、MCP SDK或协议变化时 |
| X7 | 单次命令可携带动态 `response_timeout`；该期限覆盖MCP连接、读写和结果回传，progress通知不会重置；官方没有公布当前ChatGPT固定秒数 | volatile | [OpenAI tunnel protocol](https://github.com/openai/tunnel-client/blob/master/docs/protocol.md) | 2026-09-16 | Platform或tunnel-client协议变化时；Gate 1A必须实测所需等待窗口，不能把文档示例值当作产品上限 |

## Recommended Route

推荐 A：精确配对的 loopback `CaptureCoordinator` + `activeTab` + 现有 Platform tunnel。该路线复用 Gate 0 已验证的最小权限和传输，不新增云端正文中转。当前 Gate 1A 只验证 H6/H8；任一失败即停止 A。H6/H8 通过后仍不得进入正式实现，必须另行批准 Gate 1B 的生命周期验证。不得自动切换 Native Messaging、放宽权限或接受两阶段用户流程。

## Architecture And Technology

Gate 1A 只构建隔离 fixture，不形成正式产品。Gate 1A 通过后，Gate 1B 才可在单独批准下验证用户级 LaunchAgent 与受监督 tunnel 恢复。两阶段全部通过后，后续 full implementation 才把 capture bridge 合并进 MCP 进程，由 tunnel-client 启动同一运行时，并使用用户级 LaunchAgent 监督 tunnel-client。公开接口保持 `read_url(url) -> ArticleResult`；浏览器、等待和配对细节封装在 `CaptureCoordinator` 中。

## Spike Limits

本 proposal 当前只申请 `spike-only` Gate 1A；尚不申请 Gate 1B 或 `full-implementation`。

- Time limit: Gate 1A 最多90分钟有效执行时间；达到上限立即停止。Gate 1B 另设最多90分钟，只有在 Gate 1A 汇报后经用户新批准才可启动。
- Cost limit: USD 0；不新增账户、套餐、付款方式或云资源。
- Data limit: fixture 优先；最多复用1篇用户已提供的公开文章，不保存正文或完整URL。
- Retry limit: P6 在 App/Web 各运行一次5秒控制和一次25秒 fixture，任一步失败即停止该客户端后续探针；双端均通过后，真实文章各一次。P8 最多两次重载。失败后记录，不重复点击或重启。
- Change limit: Gate 1A 只允许隔离的 coordinator spike、测试扩展、证据文档和必要的 `.env` 权限修复；不安装 LaunchAgent。
- External-state limit: 不调用 Cloudflare Worker/Jina，不改正式插件连接，不删除 OAuth、Secret、Worker 或容器。
- Exit condition: 任一安全边界触发、H6/H8失败、出现未批准持久化/费用，或达到时间与重试上限时立即停止。Gate 1A 通过后也必须停止并汇报，不得顺带执行 Gate 1B。

## Implementation Gates

- Gate 1A pass criterion: P6/P8 均为 `passed`；App/Web 均通过25秒等待 fixture，并在同一次调用内完成真实文章授权与返回；未授权提交全部被拒绝。
- Stop condition: 任一安全边界、未授权提交、正文持久化、App/Web等待失败或预算上限触发时立即停止。

### Gate 1A execution steps

1. 建立纯内存 `CaptureCoordinator` fixture 和确定性等待测试；先证明超时、取消、并发隔离和单次消费。
2. 为 spike 扩展加入稳定公开 ID 材料、每安装随机令牌和精确 Origin 校验；错误 Origin/token 必须先于浏览器测试被拒绝。
3. P6：App/Web 各先完成5秒控制，再完成25秒 fixture；任一步失败即停止。双端均通过后，复用1篇公开文章各完成一次“工具调用等待→用户在20秒内点击→同次返回”。
4. 更新证据矩阵并清理 Gate 1A 测试扩展和进程；通过或失败均停止并向用户汇报。

每个阶段必须先通过前一阶段；浏览器不用于诊断协议或进程问题。

### Deferred Gate 1B（不在当前批准范围）

- H7：disposable 用户级 LaunchAgent 可在登录后启动并恢复 tunnel-client + MCP，且无需 root。
- H9：tunnel-client 在受监督重启后恢复 health/ready、工具发现和固定调用。
- Gate 1B 需在 Gate 1A 通过后提交独立执行边界、90分钟上限、一次杀死/恢复和完整卸载标准，并取得新批准。

## Ownership And Affected Paths

- Proposal：`proposals/active/20260916-wechat-reader-l3-readiness.md`
- Gate 1A spike：`spike/l3-readiness/`（新建、可整体删除）
- 证据：`docs/l3-readiness-evidence.md`（脱敏，不含正文/完整URL）
- 仅必要时复用：`browser_capture.py`、`browser_capture_server.py`、`server.py`、测试文件
- 本地运行态：Gate 1A 仅涉及 `runtime/`、`.env`；`~/Library/LaunchAgents/` 只属于未来 Gate 1B，均不进入 Git
- 不修改：独立 Jina 仓库/容器、Cloudflare Worker、GitHub OAuth App、Jina Secret

## Security/Ops

分类：`required`。

- Gate 1A 开始前将 `.env` 权限收紧到 `0600`，只验证权限不读取或打印值。
- 扩展保持 `activeTab`、`scripting` 和固定 `http://127.0.0.1:<port>/*`；不申请 cookies、history、storage、proxy 或 `<all_urls>`。
- 配对令牌随机生成、仅本机保存、日志永不输出；Origin 必须精确匹配稳定扩展 ID。
- 请求按 `request_id + URL hash` 隔离，正文单次消费并在 deadline/成功/取消后清除。
- 日志只含时间、请求 ID、阶段、错误码、耗时、字符数和 URL hash。
- Gate 1A 不安装 LaunchAgent；Gate 1B 若获批，LaunchAgent 必须以当前用户运行、不使用 root，并可完整停止和卸载。

## Risks And Mitigations

- **平台动态工具调用期限**：官方协议允许每条命令携带 `response_timeout`，但未公布当前ChatGPT固定秒数；P6用5秒控制与25秒最低可用窗口分别在App/Web实测，progress不视为延长期限，失败即停止，不用二次消息冒充自动完成。
- **loopback 来源伪造**：精确 Origin + 安装令牌 + schema/size/URL 校验；不依赖 Origin 单独认证。
- **正文跨请求串线**：request ID、URL hash、deadline 和单次消费；并发测试必须先通过。
- **后台进程看似存在但 tunnel 未 ready**：留给 Gate 1B 分别检查 process、health、ready、tools/list 和固定调用；Gate 1A 不对此作通过声明。
- **扩展升级导致 ID 或权限漂移**：固定公开 ID 材料；权限快照作为回归门槛。
- **L1 分发被高估**：Chrome 官方限制已记录；本提案只验证个人 Mac，不承诺 GitHub 一键安装给他人。

## Validation Plan

1. 单元：协调器状态机、超时、取消、并发、一次消费、URL/大小限制、Origin/token 拒绝。
2. 本地集成：扩展→loopback→协调器→MCP，同一进程且无磁盘正文。
3. 协议：MCP initialize/tools/list、固定探针、5秒/25秒等待 fixture。
4. 客户端：App/Web 各运行5秒控制与25秒fixture；通过后各一次同一真实文章等待流程。
5. 安全检查：敏感文件权限、Git忽略、日志字段、扩展权限和零 Worker/Jina 请求。
6. Gate 1B（另批）：LaunchAgent 安装、启动、一次恢复、ready、卸载和残留检查。

## Fallback, Rollback, And Exit

- Rollback trigger: 任一 Gate 1A 失败、安全边界触发、出现正文持久化、工具调用串线、未授权提交或用户要求停止。
- Last known stable state: Gate 0 已验证的 disposable 手动捕获 + `read_rendered_url`；正式插件尚未切换。
- Reversible effects: 删除 `spike/l3-readiness/`，卸载测试扩展并停止测试进程；Gate 1A 不创建 LaunchAgent，正式连接保持不变。
- Irreversible effects: 已发生的有限 App/Web 调用和浏览器页面加载不能撤回；不产生账号、付费或云端持久资源。
- Fallback route: 返回明确不可用状态并停止；不启用 Reader、Cloudflare 或人工正文搬运。
- Degraded user outcome: L3仍停留在已证明可行但未产品化的 Gate 0 状态。
- Required approval: Gate 1A 清理不需额外批准；Gate 1B、Native Messaging、放宽浏览器权限、启用云端中转或进入 full implementation 均需新批准。
- Post-rollback verification: 无测试扩展或测试进程、无正文文件、Git无Secret、Worker/Jina零新增调用；Gate 1A 不应创建测试 LaunchAgent。

## Done Criteria

- P6/P8 均有结构化证据与明确 decision。
- App/Web 均通过25秒fixture，并在同一次工具调用内完成“等待用户在20秒内完成一次授权→返回真实文章”。
- 未授权 Origin/token 均被拒绝；扩展权限未扩大。
- 无正文/完整URL持久化、无Secret输出、无Cloudflare/Jina调用、费用为USD 0。
- 输出 `Gate 1B ready` 或明确 blocked 结论，并停止等待新批准；不得把 Gate 1A 通过写成 `full-implementation ready`。

## State Transition Plan

`proposed -> approved (Gate 1A spike-only) -> in_progress -> verified -> archived`

- 用户批准后才执行 Gate 1A。
- 任一承重假设失败：转 `blocked`，不得进入 full implementation。
- P6/P8 全部通过：本提案转 `verified`，另建或修订 Gate 1B proposal 并等待明确批准。
- 只有 Gate 1B 也通过后，才可另建 L3 `full-implementation` proposal。
- 不允许从本提案直接跳到正式安装、生产插件切换、Windows 或外部用户分发。
