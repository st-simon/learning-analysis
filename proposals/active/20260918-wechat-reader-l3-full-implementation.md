# 微信公众号文章读取：L3 正式实现提案

- ID：20260918-wechat-reader-l3-full-implementation
- Proposal policy version: 1.2
- Impact level: high
- Impact triggers: architecture, auth-secrets, deployment-infrastructure, sensitive-data, migration-replacement
- Proposal readiness: required
- Status: verified
- Approval scope: full-implementation
- Core gate: passed
- Cost gate: not-applicable
- Contradiction gate: clear
- Outcome confirmation: confirmed
- Confirmation source: 用户已明确三层需求，L3 为个人 Mac 上供 ChatGPT App/Web 便捷读取公众号 URL；并于 2026-09-20 明确批准本提案并要求实施
- Assumption freshness gate: current
- External evidence gate: passed
- Rollback gate: ready
- Implementation verification: stage-gated
- 更新日期：2026-09-20
- 项目：learning-analysis
- 分支：`codex/gce-reader-implementation`
- Security/Ops：required；涉及本地常驻进程、浏览器扩展、配对 secret、文章正文内存态和用户登录生命周期

## Background

Gate 0 已证明浏览器优先路线对 3/3 篇真实公众号文章可行，并完成 ChatGPT App/Web 真实文章传输。Gate 1A-R 已证明精确扩展身份、一次点击、早/晚点击协调、25 秒同次工具调用等待和真实 App 文章返回。Gate 1B 已证明用户级 LaunchAgent 能无 root 启动 tunnel/MCP，在一次受控终止后恢复到新实例，并在恢复前后完成固定 App 探针；随后完整卸载且无运行残留。

现有实现仍是验证形态：capture bridge 是独立临时进程；扩展位于 `spike/` 且需要临时 `install_config.js`；Gate 1B lifecycle 只监督 tunnel/MCP；首次状态查询可能早于 ready；没有正式的一键安装、升级、自然登录验收和用户级卸载体验。

## Purpose

把已验证的 L3 Mac 路线从多个手工启动的 spike 收敛为一个可安装、可观察、可恢复、可卸载的个人使用版本。正式实现不扩大到 Windows、公开分发、Chrome Web Store、云端正文中转或无人值守抓取。

## User Need And Core Outcome

用户完成一次安装后，在 Mac 已登录且 Chrome、ChatGPT App 或 Web 可用时：

1. 在 ChatGPT 中提交一个公开微信公众号文章 URL；
2. 正常打开该 URL，必要时只点击一次固定 Chrome 扩展；
3. 同一次工具调用自动返回标题、正文 Markdown、表格、图注和图片引用；
4. 正文只在当前浏览器、本机内存和本次 MCP 响应中流转，不上传 Cookie，不持久化正文；
5. 失败时返回可操作的阶段与错误分类，不回退到复制、粘贴、打印、上传正文或云端抓取。

Outcome state: `confirmed`。本提案仅实现三层需求中的 L3；L2 跨 Mac/PC 与 L1 GitHub 少量用户分发另行提案。

## Necessary Conditions

| ID | Necessary condition | Type | State | Evidence / treatment |
|---|---|---|---|---|
| C2-1 | 同次工具调用等待和一次扩展点击可完成真实文章返回 | required | met | Gate 1A-R P6/P8/P13/P14/P15 |
| C2-2 | 用户级 tunnel/MCP 可自动启动、恢复并完整卸载 | required | met | Gate 1B P7A/P7B/P9A/P9B/P17 |
| C2-3 | 扩展只能在用户手势后读取当前 tab，权限保持 `activeTab` + `scripting` | required | met | Gate 1A 实测与 Chrome 官方文档 |
| C2-5 | 配对 secret 不进入 Git、plist、argv、日志或正文响应，安装/轮换/卸载有明确所有权 | required | met | Gate 1A token边界与 Gate 1B secret边界；正式 installer 需回归 |
| C2-6 | 登录后服务在 45 秒内 ready，且 App/Web 无需终端命令即可发现工具 | required | met | 本机 launchd 文档 + Gate 1B bootstrap/recovery；F4 真实自然登录作为最终产品验收 |
| C2-7 | 正文默认不落盘、不进入日志或云端存储 | required | met | Gate 0/1A 内存态合同与日志检查；正式实现需回归 |

## Constraints And Quality Gates

- 日常文章调用只允许公众号 URL；每篇最多一次明确的扩展点击，不要求手工搬运正文。
- 只读取已经由用户正常打开并渲染的当前页面 DOM；不绕过 CAPTCHA、环境验证、登录限制或站点安全控制。
- 不调用 Jina SaaS、Cloudflare Worker、独立 Jina 容器或 Reader 直读作为自动回退。
- 不上传 Cookie、浏览器凭据、历史记录或其他 tab 内容。
- 正文最大 4 MB/既有字符上限；等待窗口 25 秒；安装与恢复 ready 上限 45 秒；无自动文章重试。
- 正文零持久化；运行日志只记录阶段、错误分类、请求 ID、耗时、版本与健康状态。
- 新增经常性费用 USD 0；任何 Web Store 账号、签名、托管或付费服务另行审批。
- 真实验收最多 2 篇当前公开文章，每篇一次；任一安全边界失败立即停止真实数据验证。

## Verified Resources And Gaps

已验证资源：Python 3.13 项目环境、FastMCP stdio server、Platform tunnel、固定 tunnel ID、Chrome 152 Manifest V3 扩展、稳定扩展 ID、loopback capture 协议、用户级 launchd、Gate 1A/1B 自动测试与证据。

当前缺口：

- `server.py` 通过 HTTP 再调用独立 `browser_capture_server.py`，协调器不属于 MCP 生命周期；
- lifecycle 安装器只准备 tunnel/MCP，不准备正式扩展目录与 capture token；
- 扩展是 spike 名称与版本，安装配置是临时文件；
- status 没有内建 45 秒有界等待，短暂未 ready 被折叠为泛化错误；
- 没有真实自然登录、升级/重装和最终生产卸载证据。

## Candidate Mechanisms

候选机制包括：MCP进程内嵌capture runtime、两个独立LaunchAgent、Chrome Native Messaging host，以及Chrome Web Store分发。先按L3个人Mac目标比较，不把L1分发需求提前带入。

## Path Comparison

| Route | Mechanism | Advantages | Risks / costs | Decision |
|---|---|---|---|---|
| A | MCP 进程内嵌 capture runtime；tunnel-client 仍由单一 LaunchAgent 监督 | 一棵进程树、一个内存协调器、无双服务启动竞态；最大复用已验证协议 | 需重构 HTTP adapter 与直接调用 seam | 推荐 |
| B | tunnel 与 capture bridge 各一个 LaunchAgent | 组件隔离 | 双服务顺序、token共享、恢复和清理竞态；扩大运维面 | 不采用 |
| C | Chrome Native Messaging host | 浏览器身份边界更原生，可移除 loopback bearer | 新增 host 注册与消息桥，仍需与 MCP 协调；未被当前证据覆盖 | L2/L1 再评估 |
| D | Chrome Web Store 扩展 + 自动更新 | 少量用户分发体验最好 | 外部账号、审核、隐私披露和更新治理；超出个人 L3 | L1 再评估 |

### Preliminary recommendation

推荐 Route A：MCP进程内嵌capture runtime，由现有tunnel-client和单一用户LaunchAgent监督。该路线复用全部Gate证据，减少一个长期进程和一组跨进程状态，不改变Platform tunnel或浏览器读取边界。

### Proposed seam and technology

推荐 Route A。新增深模块 `CaptureRuntime`，调用者只需要：

- `start()` / `stop()`：绑定固定 loopback 地址并管理线程；
- `request_capture(url, request_id, timeout)`：MCP 工具直接在同一协调器登记并等待；
- `health()`：返回不含正文、URL或 secret 的本地 readiness；
- loopback adapter 仅向扩展暴露 `/pending`、`/capture`、`/healthz`，负责精确 Origin/扩展 ID/bearer 校验。

`read_rendered_url` 不再通过 HTTP GET 调用自己的 bridge。tunnel-client 启动 MCP；MCP 启动 capture runtime；任何 MCP 重启都会原子地重建协调器和 loopback server。扩展继续使用 Manifest V3 `activeTab` + `scripting`，点击时完成 pending 检查、DOM 提取和一次提交，不保留正文状态。

## Interface Alternatives

| Shape | Caller knowledge | Testability | Decision |
|---|---|---|---|
| MCP 直接使用 `CaptureCoordinator`，HTTP server 也直接操作它 | 调用者知道线程、pending状态和认证细节 | 单元测试容易，但知识泄漏到多个调用者 | 不采用 |
| `CaptureRuntime` 封装协调、loopback adapter、启动与关闭 | MCP 只知道一次请求接口；HTTP细节留在模块内 | 可用同一公共接口做单元、集成和真实调用 | 采用 |
| 保留 `fetch_capture()` HTTP 自调用 | 变更最小 | 仍保留不必要本机网络跳转和token读取失败面 | 仅迁移期兼容，不作为最终 seam |

## Load-Bearing Assumptions

| ID | Claim | Consequence if false | Evidence state | Volatility | Verified at | Recheck by / trigger | Cheapest falsification probe | Stop condition | Affected route |
|---|---|---|---|---|---|---|---|---|---|
| H18 | 用户级 `KeepAlive` LaunchAgent 可在当前 Mac 自动启动并恢复 tunnel/MCP | L3仍需手工终端启动 | verified | volatile | 2026-09-18 | macOS、plist或tunnel-client变化时 | disposable安装后核对launchd、PID与ready | 需要root、重复实例或45秒未ready | A |
| H19 | `activeTab` + `scripting` 可在一次扩展点击后仅访问当前tab | 最小权限浏览器路线不可用 | verified | volatile | 2026-09-18 | Chrome major或manifest权限变化时 | 真实Chrome点击并检查权限与注入结果 | 出现更宽权限或无手势读取 | A |
| H20 | MV3 service worker休眠/恢复不破坏一次点击流程 | 扩展在日常空闲后不可靠 | verified | volatile | 2026-09-18 | Chrome或扩展状态模型变化时 | service worker空闲后完成一次点击 | 依赖易失全局状态或无法恢复 | A |
| H21 | Platform tunnel能把App/Web调用路由到本机stdio MCP | 两个目标客户端无法使用本机组件 | verified | volatile | 2026-09-18 | tunnel-client、工具schema或插件连接变化时 | 两端固定探针后再运行真实文章 | 任一客户端发现失败或未到本机 | A |
| H22 | 固定扩展ID与本地配对token能拒绝错误Origin、ID与token | 任意本地网页或扩展可能注入正文 | verified | stable | 2026-09-18 | manifest key、token或认证逻辑变化时 | 自动身份矩阵与真实错误token probe | 任一错误身份被接受 | A |

## Spike Evidence

| Probe ID | Assumption ID | Environment | Expected falsifier | Observed result | Evidence path | Decision |
|---|---|---|---|---|---|---|
| E18 | H18 | macOS 15 `gui/501` | 无root不能启动或kill后不恢复 | PID 24681恢复为25377，health/ready/poll通过 | `docs/gate1b-lifecycle-evidence.md#p9a` | passed |
| E19 | H19 | Chrome 152、固定ID扩展 | 点击不能临时读取当前tab或需更宽权限 | 一次点击完成真实文章，manifest仅activeTab+scripting | `docs/gate1a-race-fix-evidence.md#p14` | passed |
| E20 | H20 | Chrome 152 MV3 service worker | 空闲/唤醒后流程状态丢失 | 早/晚点击协调均通过，事件局部流程无正文持久态 | `docs/gate1a-race-fix-evidence.md#p14` | passed |
| E21 | H21 | ChatGPT App/Web、Platform tunnel | 工具不可发现或调用不到本机 | App/Web固定与真实文章调用通过；恢复前后实例匹配 | `docs/gate1b-lifecycle-evidence.md#p9b` | passed |
| E22 | H22 | 自动身份矩阵与真实Chrome | 错误Origin、ID或token被接受 | 错误身份全部拒绝，精确身份成功 | `docs/gate1a-race-fix-evidence.md#p14` | passed |

## External Claims Evidence

| Claim ID | Claim | Volatility | Authoritative source | Verified at | Recheck by / trigger |
|---|---|---|---|---|---|
| X18 | `KeepAlive=true` 会持续保持job并隐含一次启动；用户LaunchAgent位于 `~/Library/LaunchAgents` | volatile | macOS 15 本机 `launchd.plist(5)` | 2026-09-18 | macOS升级时；真实登录仍为F4验收 |
| X19 | `activeTab` 在用户调用扩展后临时授予当前tab访问，`scripting` 可据此注入脚本 | volatile | [Chrome activeTab/privacy](https://developer.chrome.com/docs/extensions/develop/security-privacy/user-privacy)、[Scripting API](https://developer.chrome.com/docs/extensions/reference/api/scripting) | 2026-09-18 | Chrome major或manifest权限变化时 |
| X20 | MV3 extension service worker会休眠，事件可重新唤醒；全局状态不能作为持久状态 | volatile | [Chrome Extension service worker lifecycle](https://developer.chrome.com/docs/extensions/develop/concepts/service-workers/lifecycle) | 2026-09-18 | Chrome或扩展状态模型变化时 |
| X21 | unpacked扩展需在 `chrome://extensions` 开启开发者模式并选择目录 | volatile | [Chrome Hello World / Load unpacked](https://developer.chrome.com/docs/extensions/get-started/tutorial/hello-world) | 2026-09-18 | Chrome安装UI或分发规则变化时 |

## Recommended Route

推荐 Route A：MCP进程内嵌capture runtime，由现有tunnel-client和单一用户LaunchAgent监督。该路线复用全部Gate证据，减少一个长期进程和一组跨进程状态，不改变Platform tunnel或浏览器读取边界。

## Architecture And Technology

正式架构采用Python 3.13、FastMCP stdio、进程内 `CaptureRuntime`、固定loopback HTTP adapter、Manifest V3私有扩展、现有Platform tunnel和macOS用户级LaunchAgent。安装器生成Git忽略的私有扩展配置和随机配对token；MCP直接调用runtime接口，只有扩展穿过loopback认证边界。

## Scope

- 把 capture coordinator、认证和 loopback adapter 收敛为 MCP 进程内 `CaptureRuntime`。
- 将验证扩展迁移为正式本地扩展源码；保持稳定ID、最小权限和一次点击模型。
- 扩展 installer/lifecycle：创建私有运行目录、原子生成/轮换配对token和扩展配置、安装用户LaunchAgent、内建45秒ready等待、明确错误分类。
- 提供 `install`、`status`、`doctor`、`upgrade/reinstall`、`uninstall` 的用户入口和文档。
- 验证 App/Web、真实自然登录、一次恢复、升级和完整卸载。
- 更新架构、决策、任务、README、测试与证据；保留历史Gate证据。

## Non-Goals

- Windows、跨设备正文中转、移动端、Chrome Web Store或GitHub公开发布。
- 自动打开/控制微信页面、无人值守抓取、CAPTCHA处理、代理或浏览器指纹绕过。
- Reader/Jina/Cloudflare自动回退、OCR、图片下载/托管、知识库或批量读取。
- 撤销现有Cloudflare/GitHub/Jina资源；需单独批准。
- 修改外部Jina仓库/容器或Platform tunnel ID。

## Implementation Gates

| Stage | Pass criterion | Stop condition | Evidence |
|---|---|---|---|
| F0 基线冻结 | 现有44 Python/6 Node/MCP smoke通过，端口和LaunchAgent无残留 | 基线失败或出现未知运行实例 | 版本、测试与runtime preflight |
| F1 进程内runtime | TDD实现`CaptureRuntime`；单进程stdio+loopback、并发/取消/关闭/认证测试通过 | stdio阻塞、正文持久化、错误身份被接受、端口关闭不净 | 新自动与进程集成测试 |
| F2 正式安装器 | install/status/doctor安全且幂等；私有extension/token；45秒ready；无secret或第二bridge进程 | 需要root、宽权限、泛化错误、重复实例 | plist、argv、权限、health与日志检查 |
| F3 disposable端到端 | App/Web固定探针通过；App读取第1篇当前文章，同次调用+一次点击、`rendered_dom`、零持久化 | schema、身份或等待失败；不进入真实文章 | 本机实例、客户端JSON与脱敏日志 |
| F4 自然登录验收 | 用户批准后注销/登录或重启一次；45秒内自动ready；App固定探针与Web第2篇当前文章成功 | 未自动启动、需手工命令、重复实例或数据泄漏 | 登录后launchd、doctor、App探针与Web文章 |
| F5 升级与卸载 | 原位升级/安全重装后完整卸载；服务、进程、端口、plist、token、runtime/log为零 | 误删其他文件、旧token仍有效、任一运行残留 | upgrade、uninstall与post-cleanup清单 |
| F6 正式安装 | F0-F5全通过后安装最终版本；doctor、工具发现和证据文档完整 | 前序失败或用户撤回生产安装 | 最终版本、健康状态与证据报告 |

实施结果（2026-09-20）：F0-F6 全部通过，状态为 `verified`。证据见
`docs/l3-full-implementation-evidence.md`。

阶段严格顺序执行。失败时只诊断当前阶段的一项假设；不得通过浏览器重试掩盖协议、认证或生命周期失败。真实文章在固定探针、工具发现和身份矩阵全部通过后才允许使用。

## User-Provided Actions During Implementation

用户不需要提供密码或API key，但需要在明确验收点完成：

1. 在 Chrome 开发者模式中一次加载正式私有扩展目录并固定到工具栏；
2. 提供最多2个当前公开公众号文章 URL；
3. 在 F4 前确认一个可注销/登录或重启的时间点；
4. 在 F5 卸载验收时从 Chrome 移除 unpacked 扩展，之后由F6重新加载最终目录。

若用户不批准真实注销/登录，代码可到 `implemented`，但 proposal 不得进入 `verified`，也不得声称登录自动启动已验证。

## Ownership And Affected Paths

- Runtime/interface：`browser_capture.py`、`browser_capture_server.py`（迁移期后删除或降为薄adapter）、`server.py`
- Lifecycle/installer：`gate1b_lifecycle.py` 将重命名或演进为正式 lifecycle 模块与用户CLI
- Extension：从 `spike/browser-source-extension/` 迁移到正式项目路径；生成的token配置只进入Git忽略的私有runtime目录
- Tests：现有 Python/Node tests 加进程级集成、installer、upgrade、doctor和uninstall测试
- Docs：`README.md`、`TASKS.md`、`DECISIONS.md`、`docs/PROJECT_GOAL.md`、`docs/ARCHITECTURE.md`、新实施证据
- Local-only：`~/Library/LaunchAgents/<final-label>.plist`、项目Git忽略的runtime/log/token/extension build
- 不修改：独立Jina仓库/容器、Cloudflare Worker、GitHub OAuth App、Jina key、Platform tunnel ID

## Security And Privacy Review

Security/Ops classification: `required`。

- 正式扩展仅保留 `activeTab`、`scripting` 和固定 loopback host 权限；不申请cookies、tabs历史、webRequest、downloads或广泛站点权限。
- manifest、源代码和生成目录不得包含控制面key；capture token为本机随机值，目录0700、文件0600，安装或升级时按明确策略轮换。
- loopback server固定 `127.0.0.1:18431`，拒绝非精确Origin/扩展ID/token；响应`Cache-Control: no-store`。
- 文章内容只存在于页面DOM、内存协调器和MCP响应；日志、错误、health、doctor、测试证据不得含正文、完整URL、token或Cookie。
- 扩展页面内容按不可信输入处理；Markdown仅作为后续分析材料，不执行页面内指令。
- installer仅操作固定label和精确owned paths；kill/upgrade/uninstall前核对PID、可执行文件和服务身份。

## Reliability And Observability

- `status --wait 45` 与 installer 共享有界ready逻辑，区分 `SERVICE_ABSENT`、`STARTING`、`MCP_UNREADY`、`CONTROL_PLANE_UNREADY`、`CAPTURE_UNREADY`、`CONFIG_INVALID`，不再统一折叠。
- health/doctor只输出版本、阶段、PID、端口、ready和脱敏错误码；不输出环境变量或完整请求数据。
- 启动失败无无限重试；沿用launchd throttle，并检测短时连续退出。
- 每次文章调用保留单一request ID和阶段耗时；正文不进入日志。
- 扩展badge保留 `WAIT/OK/AUTH/URL/TIME/PAGE/SEND`，文档映射到用户可执行动作。

## Validation Plan

- TDD薄切片：先写单进程runtime失败测试，再实现；每个生命周期行为先写合同测试。
- 自动层：Python单元/进程集成、Node扩展流程、MCP smoke、plist lint、secret/正文扫描、proposal readiness。
- 原生层：真实loopback端口、tunnel health/ready/control-plane poll、固定工具发现。
- 浏览器层：错误ID/token/Origin拒绝，service worker空闲后一次点击，早/晚点击各一次。
- 客户端层：App和Web先固定探针，再各一篇有界真实文章；总文章上限2。
- 生命周期层：一次受控kill、一次真实自然登录、一次upgrade/reinstall、一次完整uninstall和最终正式install。
- 最终报告必须区分自动、原生、浏览器、App/Web、自然登录和卸载各层证据。

## Fallback, Rollback, And Exit

- Rollback trigger: 任一安全边界失败、错误身份被接受、正文/secret落盘或入日志、重复实例、45秒未ready、App/Web不一致、自然登录失败、卸载残留或达到文章/重试上限。
- Last known stable state: commit `40e7f34`；Gate 1A/1B代码与证据已验证，disposable运行态已清理，当前无后台服务。
- Reversible effects: 项目代码、用户LaunchAgent、私有extension runtime、capture token与本地日志；均有精确owned path。
- Irreversible effects: 无；不改云资源、不改tunnel ID、不处理浏览器Cookie。
- Fallback route: bootout正式label，停止精确PID，删除owned runtime/token/log/plist；用户从Chrome移除unpacked扩展；Git回到最后稳定commit。必要时仍可按Gate 1A手工启动验证组件，但不得宣称正式可用。
- Degraded user outcome: 插件暂时不可用，而不是回退到手工复制正文或云抓取。
- Required approval: 代码内阶段失败可自动执行精确rollback；真实注销/重启、云资源清理、tunnel/插件连接变更需用户另行明确确认。
- Post-rollback verification: label、PID、端口、plist、runtime/token/log为零，Chrome扩展由用户确认移除，Git无临时文件，其他服务不受影响。

## Alternatives Considered

- 继续维持两个手工进程：无法满足登录后可用与恢复目标。
- 两个LaunchAgent：比单进程runtime增加状态和token协调，没有用户价值。
- 先做Chrome Web Store：会把L1分发风险带入L3个人使用，违反最小范围。
- 回到Jina/Cloudflare：来源反爬证据不支持，且改变隐私和成本边界。

## Done Criteria

- 一个正式安装入口完成私有扩展配置与用户LaunchAgent安装，无root、无secret泄漏；
- MCP进程直接拥有capture runtime，不存在第二个手工bridge进程；
- Mac自然登录后45秒内自动ready，doctor与App固定探针通过；
- App和Web各完成一篇有界真实文章，同次调用、最多一次点击、`rendered_dom`、零持久化；
- 错误身份、token、Origin、URL和超时均准确分类并被拒绝；
- 一次恢复、一次升级/重装、一次完整卸载和最终正式安装全部通过；
- 文档、证据、测试和安全扫描完整，proposal转为`verified`；
- 未声称Windows、公开分发、Web Store、云抓取或无人值守能力。

## State Transition Plan

当前为 `verified`：用户已明确批准，F0-F6 全部通过，包括正式安装、App/Web、两篇有界真实文章、自然登录、升级/轮换、完整卸载和最终重装。任一承重证据未来被推翻则停止依赖路线并转为 `blocked` 或 `superseded`，先完成精确rollback再提交替代方案。
