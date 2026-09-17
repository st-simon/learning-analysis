# 微信公众号文章读取：Gate 1A-R 单击竞态修复与受控重测提案

- ID：20260917-wechat-reader-gate1a-race-fix
- Proposal readiness: required
- Proposal policy version: 1.2
- Impact level: high
- Impact triggers: architecture, trust-boundary, sensitive-data, route-invalidating-uncertainty
- Status: verified
- Approval scope: spike-only
- Core gate: passed
- Cost gate: not-applicable
- Contradiction gate: clear
- Outcome confirmation: confirmed
- Confirmation source: 用户于 2026-09-17 批准竞态修复，并于 2026-09-18 明确批准加入 tunnel 四项机器预检及恢复一次 R3 额度的窄范围修订
- Assumption freshness gate: recheck-required
- External evidence gate: passed
- Rollback gate: ready
- Implementation verification: stage-gated
- 更新日期：2026-09-18
- 项目：learning-analysis
- 分支：codex/gce-reader-implementation（沿用当前分支，不创建新分支）
- Security/Ops：required；涉及已渲染网页正文、loopback 入口、扩展身份和本地运行令牌

## User Need And Core Outcome

用户在 ChatGPT App 中提交一个微信公众号 URL 后，只需在 Chrome 中对已经打开并正常显示的文章点击扩展一次；无论这次点击略早于还是晚于工具开始等待，系统都应在同一次读取调用中自动返回文章，不要求再次点击、再次发消息、复制正文或使用终端。

本 proposal 只申请修复并验证 Gate 1A 已暴露的时序缺陷，不批准产品化、后台常驻、Web 端重测、Reader/Jina 路线恢复或 Cloudflare 路线变更。

## Necessary Conditions

| ID | Necessary condition | Type | State | Evidence |
|---|---|---|---|---|
| C1 | 用户的一次点击在 pending 登记之前或之后发生，都能与同一 URL 的当前请求可靠会合 | required | met | 早/晚点击、超时、重复响应和跨 URL 隔离测试通过；真实 Chrome 有界等待通过 |
| C2 | 会合必须精确绑定规范化 URL、配对扩展身份和每安装令牌，且只消费一次 | required | met | 缺失 Origin 的真实 Chrome 0.1.2 请求已通过精确扩展 ID + 随机 token 鉴权；错误组合矩阵与一次消费测试通过 |
| C3 | 用户能从脱敏、分阶段错误中区分“等待请求”“页面不符”“配对失败”“提交失败”和“超时” | required | met | 自动分类测试通过，真实 Chrome 已分别观察 `AUTH` 与 `TIME` |
| C4 | 正文不落盘、不进入日志、不提前缓存在桥中，也不发送到 Cloudflare/Jina | required | met | 现有路线为本机内存传输；新方案必须保持该边界 |
| C5 | 本地门槛通过后，一次 App 真实文章测试在同一次调用中返回结果 | required | met | P15 全绿后，恢复的单次 App 调用与一次扩展点击成功返回 rendered DOM 结果 |

## Constraints And Quality Gates

- 用户日常输入仍只有 URL；浏览器侧最多一次明确点击。
- 不接受复制、打印、保存、上传正文，也不接受失败后让用户再说“继续”。
- 只允许 `https://mp.weixin.qq.com/s/...`，按规范化 URL 精确会合。
- 浏览器扩展继续只使用 `activeTab`、`scripting` 和固定 loopback 权限；不得新增 Cookie、历史、存储、代理或常驻站点权限。
- 新 readiness 接口不得接收或返回标题、正文、图片、Cookie、完整 token 或诊断堆栈。
- 正文只在用户点击后、确认对应 pending 已就绪时提取，并立即提交；不得建立早到正文缓存。
- 日志和错误只记录阶段、脱敏错误码、耗时与请求关联标识；不得记录正文、完整 URL、令牌或敏感 header。
- 不调用、不修改 Cloudflare Worker、GitHub OAuth App、Jina SaaS、Jina key 或独立 Jina 容器。
- 不改变 MCP 工具 schema、插件连接、正式路由或后台启动方式。
- 预算 USD 0；最多一篇用户已提供的公开文章、一次 App 真实读取；失败即停，不重试。
- Web 端、Gate 1B、LaunchAgent、发布和多用户分发均不在本 proposal 范围。

## Verified Resources And Gaps

### 已验证资源

- Gate 0 已证明 Chrome 已渲染 DOM 可读取 3 篇真实公众号文章。
- App/Web 的 5 秒和 25 秒本地无网络 fixture 均能在同一次工具调用中返回。
- 固定扩展 ID、精确 Origin、每安装令牌及错误凭据拒绝已在 Gate 1A 验证。
- 上一次 App 真实文章失败时，本地 MCP 已进入 25 秒等待，但没有捕获被协调器接受。
- 失败后的扩展、进程、令牌、安装配置和临时目录已清理。

### 能力缺口

- 当前协调器只接受 pending 已登记后的提交，缺少“请求已就绪”的最小握手。
- 扩展会立即提取并提交，提交过早时没有等待或重试机制。
- 扩展把所有失败折叠为 `ERR`，无法确认失败发生于页面、鉴权、会合还是提交阶段。
- 尚未用确定性测试覆盖“点击先发生、pending 后出现”的顺序。

## Candidate Mechanisms

### A. 先等待 pending 就绪，再提取并提交（推荐）

用户点击后，扩展只轮询一个经过 Origin/token 验证的 readiness 接口。接口仅回答该规范化 URL 当前是否存在 pending。确认就绪后，扩展才读取 DOM 并提交一次正文。

### B. 在本机桥缓存早到正文

扩展立即提取，若 pending 尚未出现则把正文按 TTL 暂存，待工具调用开始后再消费。

### C. 保持当前实现，要求第二次点击或第二条消息

把时序协调交给用户；第一次失败后再次触发读取或捕获。

## Path Comparison

| Route | C1 单击可靠 | C2 精确会合 | C3 可诊断 | C4 不缓存正文 | C5 同次返回 | 结论 |
|---|---|---|---|---|---|---|
| A. readiness 后提取 | 满足设计目标 | 可沿用现有配对并按 URL 查询 | 可按阶段分类 | 是 | 待实测 | 推荐 |
| B. 缓存早到正文 | 可实现 | 需额外 TTL/所有权/清理协议 | 可实现 | 否 | 待实测 | 淘汰；扩大隐私与陈旧正文风险 |
| C. 第二次操作 | 否 | 不变 | 弱 | 是 | 否 | 淘汰；违反已确认用户结果 |

## Load-Bearing Assumptions

| ID | Claim | Consequence if false | Evidence state | Volatility | Verified at | Recheck by / trigger | Cheapest falsification probe | Stop condition | Affected route |
|---|---|---|---|---|---|---|---|---|---|
| H10 | 在用户停留于同一文章标签页期间，Chrome `activeTab` 授权可覆盖有界等待；扩展 service worker 能在不超过20秒的轮询中继续执行 | 无法安全采用“先等候、后提取” | verified | volatile | 2026-09-17 | Chrome/Manifest 变化时 | 官方文档核验后，运行一次不读取正文的有界 readiness fixture | 授权提前撤销、worker 中止或必须新增宽权限 | A |
| H11 | 早点击后 pending 延迟出现时，扩展最终只提交一次；晚点击仍立即提交 | 核心竞态未修复或产生重复消费 | verified | stable | 2026-09-17 | 协调器或扩展时序逻辑变化时 | 用可控延迟覆盖 click-before-pending、pending-before-click、永不 pending 和重复响应 | 任一顺序丢失、重复提交或跨 URL 会合 | A |
| H12 | Chrome extension service worker 的 loopback 请求会携带可精确校验的扩展 Origin，从而保持 Origin/token/URL 三重边界 | 无法按已批准安全模型识别浏览器调用来源 | contradicted | volatile | 2026-09-17 | Chrome、Manifest 或传输机制变化时 | 真实 Chrome R2 点击并记录脱敏 method/origin class | 实际 `GET /pending` 的 Origin 缺失，当前实现正确返回403 | A |
| H13 | R0-R2 通过后，一次 App 真实文章测试可在同一次调用、一次点击内成功返回 | 用户体验仍不成立 | verified | volatile | 2026-09-18 | Platform、tunnel-client、Chrome 或 MCP 变化时 | 先机器核验 tunnel live/ready，再只运行一次 App 真实文章测试 | P15通过后恢复的一次App调用和一次点击返回成功 | A/L3 |
| H14 | Origin 缺失时，精确 `chrome.runtime.id` 头与随机安装 token 能维持配对边界；非空错误 Origin 始终被拒 | loopback 可能接受错误浏览器来源或配置串线 | verified | stable | 2026-09-17 | 扩展ID、header合同或token机制变化时 | 缺失Origin下的正确/错误ID/token矩阵 + 真实Chrome R2 | 任一错误组合被接受或真实扩展仍被拒 | A修订路线 |
| H15 | R3 前可以机器化证明预期 tunnel-client 进程、控制面成功轮询、`health/ready` 与 App 固定探针均属于同一活动实例 | 无法区分产品失败与未启动/错实例的测试环境失败 | verified | volatile | 2026-09-18 | 每次真实文章测试前 | PID/URL 文件 + `tunnel-client health --require-control-plane-poll --json` + App `gate0_transport_probe` 与本机转发证据 | 四项任一不通过即不得加载扩展或消耗文章额度 | A修订路线 |

## Spike Evidence

| Probe ID | Assumption ID | Environment | Expected falsifier | Observed result | Evidence path | Decision |
|---|---|---|---|---|---|---|
| P10 | H10 | 当前 Chrome 152、unpacked 扩展、loopback readiness fixture | 等待中授权失效、worker 被终止或需要新增权限 | 真实点击显示蓝色 `WAIT`，约20秒后准确结束为红色 `TIME`；未新增权限、未读取正文 | `docs/gate1a-race-fix-evidence.md#p10` | passed |
| P11 | H11 | 纯本地确定性 coordinator/extension 协议测试 | 早点击丢失、重复提交、跨 URL 会合或无界等待 | 6项扩展流程测试、30项Python回归与真实loopback协议集成通过 | `docs/gate1a-race-fix-evidence.md#p11` | passed |
| P12 | H12 | loopback 合同、安全与脱敏日志测试 + 真实 Chrome 152 请求 | 错误凭据可查询/提交，浏览器不提供承重身份信号，或错误输出泄露敏感数据 | 自动合同测试通过；真实 `GET /pending` 连续返回 `FORBIDDEN_ORIGIN`，脱敏分类为 `origin_class=MISSING` | `docs/gate1a-race-fix-evidence.md#p12` | failed |
| P13 | H13 | ChatGPT App、现有 Platform tunnel、1篇公开文章 | 不能在同次调用和一次点击内返回 | 首次因tunnel缺失而inconclusive；P15修订后恢复的一次调用约5.9秒成功，扩展绿色OK，返回rendered_dom且零持久化 | `docs/gate1a-race-fix-evidence.md#p13` | passed |
| P14 | H14 | 应用合同、Node扩展流程、真实loopback集成与Chrome 152 | 错误ID/token/Origin被接受，或真实扩展无法鉴权 | 自动矩阵、34项Python、6项JavaScript、MCP smoke及无Origin loopback集成均通过；真实Chrome 0.1.2 从 `WAIT` 到 `TIME`，不再出现 `AUTH` | `docs/gate1a-race-fix-evidence.md#p14` | passed |
| P15 | H15 | 本机 tunnel-client 0.0.14、现有 Platform tunnel、ChatGPT App 固定无网络探针 | 任一实例身份、控制面轮询、health/ready 或端到端固定调用缺失 | PID、控制面成功poll、同实例health/ready通过；App固定JSON成功且同实例记录CallToolRequest转发 | `docs/gate1a-race-fix-evidence.md#p15` | passed |

## External Claims Evidence

核验日期为 2026-09-17。外部文档只支持机制可测，不替代当前版本的运行证据。

| Claim ID | Claim | Volatility | Authoritative source | Verified at | Recheck by / trigger |
|---|---|---|---|---|---|
| X10 | `activeTab` 的临时访问在用户停留于该页面期间有效，并在离开或关闭页面时撤销 | volatile | [Chrome activeTab](https://developer.chrome.com/docs/extensions/develop/concepts/activeTab) | 2026-09-17 | Chrome 权限模型或 Manifest 版本变化时 |
| X11 | Manifest V3 service worker 通常会在约30秒空闲后终止；事件和扩展 API 调用会重置空闲计时，单次 `fetch()` 响应超过30秒也可能导致终止 | volatile | [Chrome extension service worker lifecycle](https://developer.chrome.com/docs/extensions/develop/concepts/service-workers/lifecycle) | 2026-09-17 | Chrome 生命周期规则变化时；实现必须把总等待限制在20秒并实测 |

## Recommended Route

选择 A：增加一个只暴露布尔 readiness 的窄接口，让扩展在单次用户点击后先等待匹配 pending，再提取并提交。该方案修复确定性的时序缺口，同时保持正文不缓存、权限不扩大和一次用户动作的目标。

不采用 B，因为它在 pending 之前处理并保存完整正文，新增陈旧数据、清理、内存和隐私风险；不采用 C，因为它直接违反“同一次读取流程、最多一次点击”的核心结果。

### R2 contradiction and required amendment

2026-09-17 的真实 Chrome 152 R2 证伪了“extension service worker loopback `fetch()` 总会携带 `Origin`”这一承重假设。Chrome 官方文档确认扩展 service worker 在声明 `host_permissions` 后可以直接执行跨源 `fetch()`，但没有承诺请求一定携带可供服务端认证的 `Origin`。实际请求为 `GET /pending`、token 配置一致、扩展 ID 正确，但 `Origin` 缺失，因此当前服务端按批准模型正确拒绝。

建议的最小修订尚未获批准：

1. 扩展在 readiness 与 capture 请求中增加 `X-Learning-Analysis-Extension-Id: chrome.runtime.id`；
2. 服务端仍强制随机安装 token、固定 loopback、URL allowlist 和一次消费；
3. `Origin` 非空时必须精确匹配，任何其他网页 Origin 即使带自定义头也拒绝；
4. 仅在 `Origin` 缺失、扩展 ID 头精确匹配且 token 正确时接受请求；
5. 自定义扩展 ID 头不是秘密，身份认证仍由每安装随机 token 提供；它只用于防止配置串线和保留明确实例绑定；
6. R0/R1 必须新增缺失 Origin + 正确/错误 ID/token 的矩阵，真实 R2 通过后才恢复 R3。

替代路线是 Native Messaging，以浏览器 `allowed_origins` 获得更强的原生扩展绑定，但会新增权限、host manifest、安装流程和接口，不属于本 proposal 的窄修订。直接取消 Origin 检查而只保留 token 也不采用。

## Architecture And Technology

候选交互如下：

```text
ChatGPT App 调用 read_rendered_url(url)
  -> 本地 CaptureCoordinator 登记 pending(url, deadline)
     <- 扩展单击后轮询 GET /pending?url=...
        <- 仅返回 PENDING_READY 或 NO_PENDING
     <- PENDING_READY 后扩展才读取当前 DOM
     <- POST /capture 一次
  -> 同一次 MCP 调用返回 ArticleResult
```

拟新增接口为扩展专用的 authenticated loopback endpoint，例如：

```text
GET /pending?url=<normalized-url>
Origin: chrome-extension://<exact-id>
Authorization: Bearer <install-token>

200 {"status":"PENDING_READY"}
404 {"status":"NO_PENDING"}
```

接口响应不包含 request ID、标题、正文或完整 URL。扩展点击后显示 `WAIT`，每约250毫秒查询一次，总等待不超过20秒；pending 就绪后才提取并提交一次。终态 badge 使用有限的阶段码，例如 `OK`、`PAGE`、`AUTH`、`URL`、`TIME`、`SEND`，代码含义写入 README；不向 badge 或日志写正文和完整 URL。

`read_rendered_url` 的 MCP schema 与返回合同不变。该 spike 不把内部 readiness 接口暴露为 MCP 工具。

## Implementation Gates

| Stage | Pass criterion | Stop condition | Evidence |
|---|---|---|---|
| Gate R0：确定性回归 | 先用测试稳定重现“点击早于 pending 被丢弃”，再证明早/晚点击、超时、重复响应和跨 URL 隔离全部通过 | 不能稳定复现旧故障，或修复需要正文缓存/第二次动作 | P11、测试输出、最小 diff |
| Gate R1：合同与安全 | readiness 和 capture 均执行精确 Origin/token/URL 校验；未授权请求被拒；日志与错误通过脱敏检查 | 新权限、敏感信息泄露、正文持久化或未授权状态查询 | P12、安全矩阵、日志审计 |
| Gate R2：Chrome 有界等待 | 同一标签页的一次点击可显示 `WAIT` 并在 pending 出现后进入确定终态；ID 保持既有值；不新增权限 | worker/activeTab 在20秒内失效、ID漂移、需重载以外操作或出现笼统 `ERR` | P10、manifest diff、badge 状态记录 |
| Gate R2.5：Tunnel 四项预检 | PID 文件指向活动实例；控制面至少一次成功 poll；同一实例 `/healthz` 与 `/readyz` 通过；App `gate0_transport_probe` 返回固定 JSON 且本机记录一次转发 | 任一项缺失、不属于同一实例、需要刷新 schema/改变连接，或 fixture 未到达本机 | P15、`tunnel-client health --require-control-plane-poll --json`、脱敏转发时间线 |
| Gate R3：一次 App 真实文章 | 一篇文章在同一次 App 调用中、一次扩展点击后返回 `status=ok`，并保持 `network_used=false`、`persistent_write=false` | 任一失败、超时、第二次动作、错误无法定位或边界违规；不重试 | P13、脱敏原始结果与时间线 |

阶段必须顺序执行。R0-R2.5 任一失败，不得安装扩展或运行 R3。R2.5 的固定探针不读取文章、不消耗 R3 额度。R3 无论通过或失败都立即停止并汇报；不得顺带测试 Web 或进入 Gate 1B。

## Fallback, Rollback, And Exit

- Rollback trigger: 任一 Gate 失败、边界违规、到达时间/重试上限或出现未批准外部状态变化。
- Last known stable state: Gate 1A `blocked-clean`；扩展已移除，本地进程、令牌、安装配置和临时目录均已清理。
- Reversible effects: 本 proposal 的代码、测试、临时扩展加载、本地进程和临时令牌。
- Irreversible effects: none；不创建云资源、不写入正文、不修改正式插件连接。
- Fallback route: 保持当前项目为已验证来源能力但未通过日常 L3 体验的开发状态；不声称可用。
- Degraded user outcome: 没有自动公众号读取服务；用户仍可正常在 Chrome 查看文章，但本项目不提供人工正文搬运回退。
- Required approval: 本 proposal 获明确批准后才可实现；任何删除现有代码、改变正式路由或扩大权限需另行批准。
- Post-rollback verification: 扩展不在 Chrome 中、相关端口不监听、临时 token/config 不存在、Cloudflare/Jina 状态未变、Git 工作区只保留可审查的项目文件变更。

## Spike Limits

- Time limit: 最多90分钟有效执行时间；优先完成 R0-R2，时间不足时不启动 R3。
- Cost limit: USD 0。
- Data limit: R0-R2.5 仅用无正文 fixture；批准修订后 R3 恢复最多1篇用户新提供的公开文章，正文不落盘。
- Retry limit: 每个确定性测试可在修复周期中重复；tunnel 四项预检必须全绿；浏览器人工状态检查最多两次；恢复后的 R3 真实文章严格一次，失败不重试。
- Exit condition: R3 获得一次明确 pass/fail，或任何前置 Gate 失败、达到90分钟、发生边界违规时立即停止。

## Cost Evidence

不适用。全部工作使用现有本机环境、现有 Chrome、现有 tunnel 与本地测试；不得启用付费服务。

## Scope

本 proposal 获批后只授权：

1. 为早点击/pending 竞态添加确定性回归测试；
2. 增加最小 readiness 查询和扩展侧有界等待；
3. 增加脱敏、分阶段错误分类；
4. 更新 spike 文档与证据；
5. R0-R2 全部通过后，恢复一次临时测试环境并运行一次 App 真实文章验收；
6. 验收后立即清理临时运行状态并汇报。

## Non-goals

- 不恢复 Reader/Jina 直读，不研究微信反爬绕过。
- 不调用或修改 Cloudflare Worker、OAuth、Secret 或远端部署。
- 不测试 Web 端，不执行 Gate 1B，不安装 LaunchAgent。
- 不合并、发布、打包或上架扩展。
- 不修改插件工具 schema、公开 `read_url` 路由或 ChatGPT 连接配置。
- 不提交或推送 Git；除非用户另行明确要求。
- 不扩大到 Windows、多用户或开源分发。

## Ownership And Affected Paths

- Repository: `/Users/junxia/codex-projects/projects/learning-analysis`
- Branch: `codex/gce-reader-implementation`
- Candidate implementation paths:
  - `browser_capture.py`
  - `browser_capture_server.py`
  - `spike/browser-source-extension/service_worker.js`
  - `spike/browser-source-extension/README.md`
  - `test_browser_capture.py`
  - 必要的新测试文件（若现有测试文件不能保持清晰边界）
- Evidence paths:
  - `docs/gate1a-race-fix-evidence.md`
  - 本 proposal
- Explicitly excluded:
  - 已安装 Jina repository/container
  - Cloudflare Worker 与 GitHub OAuth App
  - 用户浏览器 Cookie、历史、Profile 数据和扩展存储

## Security/Ops Classification

`required`。新增 loopback readiness 接口属于本机信任边界变化；必须复用精确扩展 Origin、随机安装令牌、URL allowlist、loopback-only 绑定和日志脱敏。正文持久化、外部网络请求、宽权限及静默自动抓取均禁止。

## Risks And Mitigations

| Risk | Mitigation |
|---|---|
| readiness 轮询被其他本机页面探测 | 精确 Origin + token + URL allowlist；未授权请求统一拒绝，不透露 pending 细节 |
| 用户点击后切换或导航标签页 | activeTab 页面变化立即返回 `PAGE`；不从其他标签页读取，不重试 |
| pending 在接近期限时出现造成提交与 MCP 超时竞争 | 扩展等待上限20秒，短于25秒调用窗口；R0 覆盖临界时间并保留安全余量 |
| service worker 生命周期导致轮询中断 | 轮询期间使用短请求和扩展 API 更新 badge；R2 以当前 Chrome 实测，失败即停止 |
| 多个相同 URL 请求产生歧义 | 同一规范化 URL 同时只允许一个 active pending；并发冲突返回脱敏 `CONFLICT` 并停止 |
| 错误分类泄露内部细节 | 固定枚举码；用户可见消息与日志均不包含正文、完整 URL、token 或堆栈 |

## Validation Plan

1. 先新增失败测试，证明当前实现会丢弃早到点击；保留其失败输出作为 R0 基线。
2. 用最小接口实现 red-green 修复，覆盖早/晚顺序、20秒上限、跨 URL、重复提交、取消和并发冲突。
3. 运行现有测试与 MCP smoke，确保等待 fixture、已有 capture 合同和工具返回无回归。
4. 运行 Origin/token/URL 安全矩阵，并检查日志中不存在正文、完整 URL 和令牌。
5. 静态审查 manifest 权限未扩大；临时加载扩展后核对 ID，并用无正文 fixture 验证 `WAIT` 到阶段终态。
6. 只有 R0-R2 全部通过，才请求用户准备一篇已打开的公众号文章并执行一次 R3。
7. R3 后清理扩展、进程、token/config 与临时目录，记录端口和文件不存在的证据。

## Done Criteria

本 spike 只有同时满足以下条件才可标记 `verified`：

- R0-R2 的确定性、合同、安全和 Chrome 有界等待证据全部通过；
- R3 一次 App 真实文章在同次调用、一次点击中返回成功；
- 返回明确记录 `source_channel=rendered_dom`、`network_used=false`、`persistent_write=false`；
- 没有正文、完整 URL、令牌或敏感日志落盘；
- 临时扩展、进程、密钥和配置完成清理；
- 证据文档记录时间线、版本、结果与残余风险；
- 未执行 Web、Gate 1B、Cloudflare/Jina 或任何非本提案动作。

第一次 R3 因执行前未确认 tunnel-client 在线而失败，保留证据且不得把 R0-R2 通过等同于用户结果完成。用户于 2026-09-18 批准窄范围修订：必须先通过机器可判定的 tunnel process、control-plane connection、health/ready 和固定 fixture 四项前置门槛，才恢复一次新的真实文章额度。

## State Transition Plan

用户已于 2026-09-17 明确批准原 proposal；R2 真实浏览器证据随后证伪 H12。用户又于同日批准“缺失 Origin + 精确扩展 ID 头 + 随机 token”的最小安全修订，R2 随后通过。第一次 R3 因遗漏 tunnel-client 在线核验而未到达本地 bridge，清理已完成。用户于 2026-09-18 批准 tunnel 四项预检与一次 R3 重验额度；P15 与恢复后的 R3 均通过，临时文件、进程和扩展已清理并完成回归核验，当前为 `verified`。不进入 Web 或 Gate 1B；归档与 Git 交付可在用户明确授权 commit/push 时完成。
