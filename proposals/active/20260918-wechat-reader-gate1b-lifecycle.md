# 微信公众号文章读取：Gate 1B 用户级后台生命周期验证提案

- ID：20260918-wechat-reader-gate1b-lifecycle
- Proposal policy version: 1.2
- Impact level: high
- Impact triggers: architecture, auth-secrets, deployment-infrastructure, route-invalidating-uncertainty
- Proposal readiness: required
- Status: verified
- Approval scope: spike-only
- Core gate: passed
- Cost gate: not-applicable
- Contradiction gate: clear
- Outcome confirmation: confirmed
- Confirmation source: 用户于 2026-09-18 明确“批准该 Gate 1B proposal”
- Assumption freshness gate: current
- External evidence gate: passed
- Rollback gate: ready
- Implementation verification: stage-gated
- 更新日期：2026-09-18
- 项目：learning-analysis
- 分支：codex/gce-reader-implementation（沿用当前分支）
- Security/Ops：required；涉及用户级后台进程、控制面密钥、本地日志和 LaunchAgent 安装

## Background

Gate 1A-R 已验证：在 Platform tunnel、loopback bridge 和浏览器扩展均已正确启动时，ChatGPT App 可在同一次 `read_rendered_url` 调用和一次扩展点击内返回已渲染公众号正文。第一次 R3 因 tunnel-client 未启动而无效，说明“功能正确”不等于“运行时始终可用”。修订后的四项预检与真实 R3 均通过，但当前仍依赖手工终端启动 tunnel 和 bridge。

原 L3 readiness proposal 将 Gate 1B 单独定义为用户级 LaunchAgent 生命周期与受监督恢复验证。ai-infra 已证明本机 LaunchAgent 安装、状态检查和卸载模式可行，但其每日定时任务不是长驻网络服务，不能直接证明本项目的 KeepAlive、退避、密钥和重复实例边界。

## Purpose

用一个可完全卸载的用户级 LaunchAgent spike，证明现有 tunnel-client 与其 MCP 子进程可以在不使用 root、不把密钥写入 plist、不中转文章正文的前提下自动启动，并在一次受控杀死后恢复到可调用固定探针的状态。

本 proposal 不把当前插件宣称为产品化可用。当前 loopback capture bridge 仍是独立临时进程；把它并入 MCP 运行时或纳入正式监督属于后续 L3 full-implementation proposal。

## User Need And Core Outcome

最终需求是：只要用户已登录 Mac 且 ChatGPT/Codex 正常使用，文章读取插件不应因为忘记手工启动 tunnel 而不可用。

Gate 1B 的可观察核心结果为：安装 disposable LaunchAgent 后，用户域中的 tunnel-client 自动进入 `live/ready`，ChatGPT App 固定探针成功；杀死受监督进程一次后，launchd 生成新 PID，重新进入 `live/ready`，同一固定探针再次成功；卸载后服务、plist、临时文件和日志全部不存在。

结果状态：`confirmed`。来源为用户持续要求插件在 ChatGPT/Codex 运行时可用，并于 2026-09-18 要求继续下一步。

## Necessary Conditions

| ID | Necessary condition | Type | State | Evidence |
|---|---|---|---|---|
| C1B-1 | 仅以当前用户身份安装到 `gui/$UID`，不使用 root 或系统级 daemon | required | met | macOS 15 当前用户域可用，`~/Library/LaunchAgents` 已存在 |
| C1B-2 | plist 和日志不包含控制面 API key、文章正文、完整文章 URL 或浏览器配对令牌 | required | met | 静态合同、权限检查及卸载前值扫描通过 |
| C1B-3 | 同一配置最多运行一个 tunnel-client 实例，健康地址和 PID 可机器定位 | required | met | launchd、PID/URL文件与官方health在初始及恢复实例一致 |
| C1B-4 | 一次受控杀死后能在有界时间内恢复新 PID、控制面 poll、health/ready 和固定 App 探针 | required | met | PID 24681恢复为25377，health/ready/poll及App探针通过 |
| C1B-5 | 卸载后无服务、plist、进程、端口、临时文件或测试日志残留 | required | met | B5服务、文件、进程及测试端口残留均为零 |

## Constraints And Quality Gates

- 仅验证 ChatGPT App，不测试 Web。
- 仅调用 `gate0_transport_probe`；文章调用次数为 0，不加载浏览器扩展。
- 不启动或测试 loopback capture bridge，不读取公众号 URL 或正文。
- 不调用、不修改 Cloudflare Worker、Jina SaaS、Jina key 或独立 Jina 容器。
- 不修改 tunnel ID、插件 endpoint、ChatGPT 连接、工具 schema 或权限。
- 不将 API key 写入 plist、命令参数、日志、证据或 Git；wrapper 只从权限为 `0600` 的现有 `.env` 加载。
- LaunchAgent 标签固定为 `com.junxia.learning-analysis.gate1b`，防止误碰其他服务。
- 使用 `gui/$UID`、`launchctl bootstrap/bootout/kickstart/print`；不使用已弃用的 `load/unload`。
- 启动或恢复最多等待 45 秒；状态检查最多 3 次，间隔不超过 10 秒。
- 只允许一次受控 kill/recovery；恢复失败立即停止，不第二次杀死。
- 不强制注销、重启 Mac 或模拟系统登录；`RunAtLoad` 只在用户域 bootstrap 时验证。真实登录启动保留为 full implementation 后的自然重启验收。
- 时间上限 90 分钟；费用 USD 0。

## Verified Resources And Gaps

- macOS 15.0、arm64、当前 UID 501；`gui/501` launchd 域可查询。
- `~/Library/LaunchAgents` 已存在，Gate 1B 标签当前不存在。
- tunnel-client `0.0.14+0f870e50` 已通过 Gate 1A 的 PID、控制面 poll、health/ready 与 App 固定探针验证。
- `.env` 与 `runtime/learning-analysis.yaml` 权限均为 `0600`；二进制为 `0755`。
- ai-infra 提供定时 LaunchAgent 的参考安装/卸载结构，但没有长驻 KeepAlive、密钥 wrapper、PID/URL 交叉核验或杀死恢复证据。
- 验证后状态：已新增受版本控制的安全生命周期入口、自动测试和 Gate 1B 证据文件；disposable plist 由入口动态生成且已卸载，不保留运行态。

## Candidate Mechanisms

候选机制包括：由 launchd 监督 tunnel-client 并让 tunnel-client 管理 MCP 子进程；由自建 shell supervisor 同时管理 tunnel 与 capture bridge；使用两个独立 LaunchAgent；或立即把 bridge 合并进 MCP 后整体常驻。先按必要条件和边界比较，再选择最小可证伪路线。

## Path Comparison

| Route | Mechanism | Advantages | Risks / gaps | Decision |
|---|---|---|---|---|
| A | 用户级 LaunchAgent 监督 tunnel-client；tunnel-client 管理 MCP 子进程 | 贴合既有架构、无需 root、可完整卸载、验证成本最低 | 仍未监督独立 capture bridge；需防 crash loop 与密钥泄露 | 推荐用于 spike |
| B | 一个 shell supervisor 同时管理 tunnel 与 capture bridge | 更接近当前完整运行栈 | 自建监督逻辑复杂，重复 launchd 能力；扩大 Gate 1B | 不采用 |
| C | 两个 LaunchAgent 分别监督 tunnel 与 bridge | 组件隔离、各自恢复 | 顺序、共享 token、清理和竞态复杂；尚未决定正式架构 | 延后 |
| D | 立即把 bridge 合并进 MCP 并正式常驻 | 最接近最终产品 | 同时改变架构与运维，Gate 1B 无法隔离生命周期风险 | 仅后续 full implementation proposal |

## Load-Bearing Assumptions

| ID | Claim | Consequence if false | Evidence state | Volatility | Verified at | Recheck by / trigger | Cheapest falsification probe | Stop condition | Affected route |
|---|---|---|---|---|---|---|---|---|---|
| H7A | 当前用户可通过 `launchctl bootstrap gui/$UID` 启动一个 `RunAtLoad` LaunchAgent，无需 root | Mac L3 后台启动路线不可用 | verified | volatile | 2026-09-18 | macOS 或 plist 变化时 | 安装 disposable agent，核对 launchctl service 与 PID | 需要 root、系统域或额外权限 | A |
| H7B | wrapper 可从 `0600` `.env` 加载 key，而 plist、进程参数和日志均不暴露值 | 后台化破坏秘密边界 | verified | stable | 2026-09-18 | wrapper/plist/logging 变化时 | 静态检查 plist/argv/log，使用占位模式测试错误输出 | 任一秘密值或原始环境被输出 | A |
| H9A | `KeepAlive` + 有界退避可在一次 kill 后启动新 tunnel PID，并恢复 control-plane poll 与 ready | 服务仍需人工启动 | verified | volatile | 2026-09-18 | tunnel-client、launchd 或 macOS 变化时 | kill 一次受监督 PID，45秒内检查新PID和官方health命令 | 无新PID、crash loop、重复实例或超时 | A |
| H9B | 恢复后的 App 固定探针确实由新实例转发到本地 MCP | health ready 不代表用户链路恢复 | verified | volatile | 2026-09-18 | App、tunnel-client 或插件变化时 | 恢复后调用一次 `gate0_transport_probe` 并匹配本机转发证据 | App失败或调用未到新实例 | A |
| H17 | bootout + 文件删除可完整卸载，不影响其他 tunnel、插件或用户服务 | spike 留下持久运行态 | verified | stable | 2026-09-18 | install/uninstall脚本变化时 | 卸载后检查label、PID、端口、plist、runtime和日志 | 任一残留或误停其他服务 | A |

## Spike Evidence

| Probe ID | Assumption ID | Environment | Expected falsifier | Observed result | Evidence path | Decision |
|---|---|---|---|---|---|---|
| P7A | H7A | macOS 15 用户域、disposable LaunchAgent | 需要root、无法bootstrap或未RunAtLoad | 用户域无root安装成功；PID 24681进入running，官方health与第2次status通过 | `docs/gate1b-lifecycle-evidence.md#p7a` | passed |
| P7B | H7B | plist模板、wrapper、脱敏日志 | key进入plist/argv/log或文件权限过宽 | 10项合同测试、plist lint、秘密名扫描与0600/0700权限检查通过 | `docs/gate1b-lifecycle-evidence.md#p7b` | passed |
| P9A | H9A | 受监督 tunnel-client 0.0.14 | kill后无新PID、重复实例、未ready或crash loop | 唯一一次kill后由PID 24681恢复为25377；新实例health/ready/poll与status通过 | `docs/gate1b-lifecycle-evidence.md#p9a` | passed |
| P9B | H9B | ChatGPT App固定探针、新tunnel实例 | App失败或调用未由新实例转发 | B2由PID 24681实例转发；B4由恢复PID 25377新实例转发，固定JSON均成功 | `docs/gate1b-lifecycle-evidence.md#p9b` | passed |
| P17 | H17 | uninstall与post-rollback检查 | 任一服务、进程、端口、文件或日志残留 | label、plist、runtime、日志、进程和测试端口全部无残留 | `docs/gate1b-lifecycle-evidence.md#p17` | passed |

## External Claims Evidence

| Claim ID | Claim | Volatility | Authoritative source | Verified at | Recheck by / trigger |
|---|---|---|---|---|---|
| X1B | 当前 macOS `launchctl` 支持用户域 `bootstrap`、`bootout`、`kickstart` 和 `print` | volatile | macOS 15 本机 `launchctl help` | 2026-09-18 | macOS 升级时 |
| X2B | tunnel-client 0.0.14 支持 PID 文件、health URL 文件和 `health --require-control-plane-poll --json` | volatile | 本机版本化 CLI help 与 Gate 1A P15 实测 | 2026-09-18 | tunnel-client升级时 |
| X3B | ai-infra 已有用户 LaunchAgent 安装、状态和卸载参考 | stable | `projects/ai-infra/deploy/launchd`、`scripts/*launchd.sh`、`docs/SCHEDULING.md` | 2026-09-18 | ai-infra生命周期脚本变化时 |

## Recommended Route

推荐 Route A：用户级 LaunchAgent 只监督 tunnel-client，由 tunnel-client 继续管理 MCP 子进程。它能用最小变更验证后台启动、秘密边界、单实例、受控恢复和卸载，同时不把 capture bridge 架构决策偷渡进生命周期 spike。Route A 通过只证明控制通路可被可靠监督；文章链路常驻仍需后续 full implementation proposal。

## Architecture And Technology

Gate 1B 采用 macOS 15 用户域 launchd、固定 label `com.junxia.learning-analysis.gate1b`、tunnel-client 0.0.14、现有 stdio FastMCP server，以及 Git 忽略的 `runtime/gate1b/` 与 `logs/gate1b/`。tracked plist 只作为模板；installer 写入当前项目绝对路径，wrapper 从 `0600` `.env` 加载 secret，并以 `exec` 交给 tunnel-client。PID、health URL、launchctl service 和 CLI health 共同定义实例身份。

## Scope

- 新增 Gate 1B proposal、证据文档与生命周期测试。
- 新增安全 wrapper、plist 模板、install/uninstall/status 脚本。
- 在 `~/Library/LaunchAgents/` 安装一个固定标签的 disposable plist。
- 运行初始启动、一次 kill/recovery、恢复后固定 App 探针和完整卸载。
- 更新 README、TASKS、ARCHITECTURE 和 DECISIONS 中与 Gate 1B 直接相关的状态。

## Non-Goals

- 不让 capture bridge 常驻，不运行真实文章或浏览器扩展。
- 不验证真实注销/登录、重启、睡眠唤醒、断网恢复、跨设备或 Windows。
- 不进入 full implementation，不切换正式工具默认路线。
- 不添加依赖、不修改 Jina/Cloudflare、不产生费用。
- 不清理历史 Cloudflare/OAuth/Jina 资源。

## Proposed Approach

1. 先用测试定义生成 plist、wrapper 参数、权限、标签隔离和卸载后的可观察合同。
2. wrapper 设置 `umask 077`，验证 `.env` 为普通文件且权限不宽于 `0600`，在不输出内容的情况下加载环境，然后 `exec` 固定路径 tunnel-client。
3. plist 使用 `RunAtLoad=true`、`KeepAlive=true`、`ThrottleInterval=10`、`ProcessType=Background`，标准输出/错误写入 Git 忽略的专用 Gate 1B 日志；不含秘密或正文。
4. installer 从模板生成当前项目绝对路径，先拒绝已存在的同标签服务，再原子写入 `~/Library/LaunchAgents`，使用 `bootstrap gui/$UID`；不使用 sudo。
5. 通过 PID/health URL 文件、`launchctl print` 与官方 tunnel health 命令验证同一实例。
6. 记录初始 App 固定探针；只杀死一次已核对 PID，等待新 PID 后重新验证 health/ready/control-plane poll 和 App 固定探针。
7. uninstaller 使用 `bootout gui/$UID/<label>`，只删除固定 plist 和 Gate 1B 自有 runtime/log 文件；随后执行完整残留检查。

## Implementation Gates

| Stage | Pass criterion | Stop condition | Evidence |
|---|---|---|---|
| B0 静态与确定性测试 | plist/wrapper/install/uninstall 合同测试通过；无secret、无root、固定label/路径边界 | 需要硬编码key、宽权限、不可限定删除目标 | P7B、测试输出、diff |
| B1 用户域启动 | bootstrap后单一PID，launchctl状态正确，同实例live/ready且control-plane poll成功 | 需要sudo、重复实例、未ready、日志泄露 | P7A/P7B |
| B2 初始端到端探针 | App固定JSON成功，且本机记录由当前实例转发 | schema刷新、连接变更、未到本机 | P9B基线 |
| B3 一次恢复 | kill一次后45秒内出现新PID，同实例live/ready/poll成功 | 超时、crash loop、重复实例或第二次kill需求 | P9A |
| B4 恢复后端到端探针 | App固定JSON再次成功且由新实例转发 | App失败或未到新实例 | P9B |
| B5 完整卸载 | label、PID、端口、plist、runtime、测试日志均不存在，其他服务未受影响 | 任一残留或误删/误停 | P17 |

阶段必须顺序执行。B0-B2 任一失败不得 kill；B3/B4 任一失败立即进入 B5 清理，不重试。B5 无论前序结果如何都必须执行。

## Ownership And Affected Paths

- Proposal：`proposals/active/20260918-wechat-reader-gate1b-lifecycle.md`
- 实现代码：`gate1b_lifecycle.py`（生成plist并提供run/install/status/kill-once/uninstall）
- plist：运行时动态生成到固定用户路径；B5后不保留
- 测试：`test_gate1b_lifecycle.py`
- 证据：`docs/gate1b-lifecycle-evidence.md`
- 文档：`README.md`、`TASKS.md`、`docs/ARCHITECTURE.md`、`DECISIONS.md`
- 本机临时状态：`runtime/gate1b/`、`logs/gate1b/`、`~/Library/LaunchAgents/com.junxia.learning-analysis.gate1b.plist`
- 不修改：Jina仓库/容器、Cloudflare目录与远端资源、GitHub OAuth App、正式插件连接

## Security/Ops Classification

分类：`required`。API key 只从现有 `0600` `.env` 进入进程环境；不复制到 plist 或新 secret 文件。所有 Gate 1B runtime/log 文件用 `umask 077` 创建并保持 Git 忽略。日志只允许阶段、状态、PID、版本、耗时和脱敏请求类型；不记录环境、header、token、正文或完整文章 URL。kill 前必须由 PID 文件、launchctl service 和进程可执行路径三重确认目标；uninstall 只允许固定 label 和精确路径。

## Risks And Mitigations

- **Crash loop**：`ThrottleInterval=10`，一次 kill 后只观察一个恢复周期；连续失败立即 bootout。
- **秘密泄露**：不把 `.env` 传给 shell trace，不打印环境；测试检查 plist、argv、日志和Git状态。
- **重复实例**：installer 拒绝已加载 label；PID、health URL 与 launchctl PID必须一致。
- **错误杀进程**：kill 前核对 fixed label、PID文件、launchctl PID和 tunnel-client executable；任何不一致即停止。
- **过度结论**：bootstrap RunAtLoad 不等同于真实注销/登录；报告明确保留该限制。
- **只恢复 tunnel、不恢复文章链路**：Gate 1B 明确不证明 capture bridge 常驻；full implementation 必须解决这一架构缺口。

## Validation Plan

- Shell/plist 静态测试与 Python 合同测试。
- `plutil -lint` 验证生成 plist。
- `launchctl print gui/$UID/<label>` 验证服务域与 PID。
- `tunnel-client health --pid-file ... --url-file ... --require-control-plane-poll --json` 验证同一实例。
- ChatGPT App 前后各一次 `gate0_transport_probe`；不使用文章数据。
- kill/recovery 只执行一次；记录旧/新 PID 是否不同，不记录 secret。
- 卸载后检查 label、进程、监听端口、plist、runtime/log 和 Git 状态。

## Fallback, Rollback, And Exit

- Rollback trigger: 任一 Gate 失败、秘密/正文出现在输出、重复实例、需要root、超时或达到90分钟。
- Last known stable state: Gate 1A-R `verified`；没有后台服务、扩展、bridge、token 或临时配置。
- Reversible effects: disposable plist、Gate 1B scripts/template、runtime/log 与用户域 service。
- Irreversible effects: none；不改云资源、不改正式插件连接、不处理文章正文。
- Fallback route: bootout固定label并删除精确Gate 1B文件，恢复Gate 1A-R后的clean状态。
- Degraded user outcome: 插件仍需手工启动 tunnel；不得声称后台可用。
- Required approval: 用户批准本 proposal 后才可创建/安装 LaunchAgent、kill测试进程和卸载；任何真实登录/重启、capture bridge常驻或正式切换需另行批准。
- Post-rollback verification: label不可查询、无相关PID/监听端口、plist/runtime/log不存在、其他服务正常、Git仅保留可审查源文件。

## Spike Limits

- Time limit: 90分钟有效执行时间。
- Cost limit: USD 0。
- Data limit: 0篇文章，仅固定无网络探针。
- Retry limit: 确定性测试可修复后重跑；bootstrap最多1次清理后重试；kill/recovery严格1次；App固定探针每阶段1次。
- Exit condition: B5清理完成，或安全边界/时间上限触发；通过后也必须停止，不进入full implementation。

## Done Criteria

- B0-B5 全部有脱敏证据并通过；
- 初始与恢复后的固定 App 探针均由对应 tunnel 实例转发；
- 一次 kill 后新 PID 在45秒内恢复且无重复实例；
- plist、argv、日志、Git均无secret、正文或完整文章 URL；
- 完整卸载与残留检查通过；
- 明确声明未验证真实登录/重启与 capture bridge 常驻；
- 不执行 Web、文章读取、Jina、Cloudflare 或正式插件切换。

## State Transition Plan

用户已于 2026-09-18 明确批准本 proposal。B0-B5 已全部通过，当前转为 `verified` 并停止；disposable LaunchAgent 与全部运行残留已移除。Gate 1B 通过不自动授权 L3 full implementation；下一阶段必须提交独立 proposal，解决 capture bridge 合并/监督、自然登录验收和日常安装体验。
