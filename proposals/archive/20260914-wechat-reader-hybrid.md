# 微信公众号文章自动读取：分层产品目标与来源门控提案

- ID：20260914-wechat-reader-hybrid
- Proposal policy version: 1.2
- Impact level: high
- Impact triggers: architecture, trust-boundary, external-service, auth-secrets, deployment-infrastructure, sensitive-data, migration-replacement, route-invalidating-uncertainty
- Proposal readiness: required
- Status: verified
- Approval scope: spike-only
- Core gate: passed
- Cost gate: not-applicable
- Contradiction gate: clear
- Outcome confirmation: confirmed
- Confirmation source: 用户在 2026-09-15 明确三层产品需求及“不得手动复制、打印正文”硬约束，并在 2026-09-16 批准本次 Proposal 修订
- Assumption freshness gate: current-at-close
- External evidence gate: sufficient-for-spike-conclusion
- Rollback gate: ready
- Implementation verification: stage-gated
- 授权说明：用户于 2026-09-16 批准并完成本文限定的 Gate 0 spike；未批准 full implementation、部署、正式插件切换或外部资源处置
- 更新日期：2026-09-16
- 项目：learning-analysis
- 分支：codex/gce-reader-implementation（历史分支名；进入实现前另行决定是否迁移）
- Security/Ops：required；涉及浏览器页面内容、本地服务、远程 MCP、第三方正文处理、现有云端 Secret 和公网入口

## 背景

原路线将 Cloudflare Worker + Jina 公共 Reader 设为远程公众号抓取主通道。真实验证证明 OAuth、MCP 初始化和工具发现可以工作，但测试公众号文章被 Jina/微信环境验证阻断；加入 Jina API key 只改变限流表现，没有使正文可读。用户自己的 Chrome 可打开同一 URL，本地 Reader 历史上曾成功读取一篇公众号文章。

这证明认证和云端运行不是当前首要问题。首先必须验证的是：在不绕过微信公众号访问控制的前提下，能否把用户输入的 URL 自动转换成可分析正文。原提案仍过早选择了“本地 Reader + 人工复制 Markdown”路径；用户现已明确，任何要求手动复制、粘贴或打印网页内容的方案均不可接受。

## Purpose

以“只输入 URL 即自动取得可分析正文”为共同产品核心，先证伪来源、浏览器自动提取和 ChatGPT App/Web 连接三个承重假设，再从 Mac 个人版逐级验证到个人跨平台版和可开源分发版。不得为了降低实现难度而把人工搬运正文重新定义为可接受结果。

## User Need And Core Outcome

### 用户需求与优先级

需求按理想程度从高到低排列，但共享同一个自动读取核心。较高层级失败时不得自动降级；必须用证据说明失败条件，并由用户决定是否接受下一层级。

### L1：开源、少量用户、本地运行

在 GitHub 开源插件及必要的本地组件，供少数用户下载安装。用户在自己的电脑上向 ChatGPT 提交微信公众号 URL，系统以便捷、低成本方式自动取得正文并交给 ChatGPT 分析。

### L2：个人使用、Mac 与 PC、App 与 Web

只供用户个人使用。在 Mac 或 PC 上，无论使用 ChatGPT App 还是 Web，提交微信公众号 URL 后均可自动取得正文并进入分析流程。

### L3：个人使用、Mac、App 与 Web

只供用户在 Mac 上使用。在 ChatGPT App 或 Web 中提交微信公众号 URL 后自动取得正文并进入分析流程。

### 三层共同硬约束

- 用户的任务输入只应是公众号 URL；来源受限时最多允许一次明确的“打开/授权自动提取”操作。
- 不得要求用户复制正文、粘贴 Markdown、打印网页、上传网页文件或手工整理内容。
- 不绕过 CAPTCHA，不使用住宅代理、IP 轮换、指纹伪装或验证码自动化。
- 不读取或传输 Cookie、登录令牌、localStorage、浏览历史及其他认证材料。
- 目标新增经常性费用为 USD 0；任何预期正费用必须单独给出用量、计算、权威来源和核验日期并获批。

### 可观察的核心结果

一次成功读取必须满足：

1. 用户在 ChatGPT App 或 Web 中只提交一个 `mp.weixin.qq.com/s/...` URL。
2. 系统自动选择已获准的来源机制；必要时只要求用户做一次明确的浏览器授权动作，不要求处理正文。
3. 返回与浏览器页面一致的标题和非空正文 Markdown，保留可提取的段落、表格、图注及图片引用。
4. 验证码页、“环境异常”页、空文、标题壳或明显截断内容不得标记为成功。
5. 结果包含来源通道、失败阶段、状态、错误码、字符数、请求 ID 和已知缺失项。
6. 插件不持久保存正文、Cookie 或凭据；正文只为本次读取和 ChatGPT 分析而传输。

各层级的额外结果：

| 层级 | 必须额外观察到的结果 |
|---|---|
| L3 | Mac 上 ChatGPT App 与 Web 均能完成端到端读取；安装完成后日常使用不需要终端命令 |
| L2 | 同一用户在 Mac 和 PC 上均达到 L3 结果；凭据与设备路由不需要复制正文来协助 |
| L1 | 新用户可从 GitHub 独立安装、授权、读取和卸载；无需获得维护者的个人 Secret 或人工介入 |

## Necessary Conditions

### 必要条件与当前证据状态

| 必要条件 | 适用层级 | 当前证据与影响 | 状态 |
|---|---|---|---|
| 用户 Chrome 能正常打开当前公开公众号文章 | L1–L3 | 已验证至少一篇；尚不能外推到不同文章类型 | `met` |
| 现有 Reader 转发入口存在 | L1–L3 候选路线 | `127.0.0.1:17831` 由 SSH 监听，只证明本机转发入口存在，不证明后端位于本机或使用家庭网络出口 | `met` |
| Reader 后端位置、版本和抓取引擎可被确认 | H1 解释前提 | H0 已确认本机 Colima OSS Reader、固定镜像摘要、源码修订和 Puppeteer 依赖；外部出口地址未主动探测，不作为结论 | `met` |
| Reader 后端当前健康并能稳定取得公众号正文 | L1–L3 候选路线 | 只有一个历史成功样本；若为假，淘汰“Reader 直接读取”主通道 | `unverified` |
| 正常浏览器会话中的页面可被自动提取为完整文档 | L1–L3 浏览器路线 | 浏览器可打开不等于 DOM 可稳定提取；若为假，浏览器自动提取路线停止 | `unverified` |
| 自动提取无需读取或传输认证材料 | L1–L3 | 必须通过权限检查和运行时证据确认；若为假，该实现不可接受 | `unverified` |
| ChatGPT App 能调用本机读取组件并取得正文 | L2–L3 | 现有 tunnel 曾可见，但完整真实文章链路尚未通过 | `unverified` |
| ChatGPT Web 能调用用户电脑上的读取组件并取得正文 | L1–L3 | 连接方式、客户端支持和正文传输路径均需实测；是承重假设 | `unverified` |
| Windows 能安装并运行同一自动读取核心 | L1–L2 | 当前只掌握 Mac 环境；未验证 Windows 打包、浏览器集成和生命周期 | `unverified` |
| 少量外部用户能独立安装且不共享维护者 Secret | L1 | 尚无分发、设备注册、升级和卸载证据 | `unverified` |
| Jina 公共 SaaS 可作为公众号主读取通道 | 旧远程路线 | 测试文章被环境验证阻断；依赖该条件的主路线已淘汰 | `unmet` |
| 本机关闭时仍由纯云端自动读取公众号正文 | L1–L3 的云端候选 | 当前没有合规可靠的云端来源机制；不得作为承诺 | `unmet` |

## Constraints And Quality Gates

### 约束、阈值与失败边界

### 体验边界

- 安装后正常读取只需提交 URL。
- 若必须利用用户已经获准访问的浏览器页面，最多增加一次“打开并授权自动提取”的动作。
- 任何要求用户接触、复制、粘贴、打印或上传正文的流程直接判定失败，不作为降级方案。
- 自动通道失败时返回清晰错误和下一步；没有合规自动通道时，本次读取失败，而不是要求用户手工搬运内容。

### 来源成功阈值

- 标题与 Chrome 页面一致。
- 正文不是验证页，具有开头、主体和结尾，无明显截断。
- 字符数、表格、图注和图片引用均有检查结果；无法保留时必须显式报告。
- Gate 0 的三篇样本必须 3/3 成功，才可把相应机制从 `unverified` 改为 `verified-for-spike`；这不等于达到发布可靠性。

### 安全与数据边界

- 只接受允许域名的公开 HTTPS URL，拒绝凭据、自定义端口和私有网络目标。
- 浏览器权限最小化到当前用户动作和 `mp.weixin.qq.com` 页面；不得读取跨站历史或认证存储。
- 浏览器自动提取只读取已由正常 Chrome 导航完成并渲染的当前页面 DOM，不自行发起新的文章 `fetch`、XHR 或后台抓取请求。
- 日志只记录时间、请求 ID、通道、阶段、错误码、上游状态、耗时、字符数和 URL 哈希，不记录正文与完整 URL。
- Gate 0 不新增云端持久化，不修改现有正式插件，不处置现有外部资源。

### 成本边界

- Gate 0 外部服务预算为 USD 0，不开通付费计划，不创建可能产生费用的新资源。
- 本地计算、既有电脑和既有免费资源只作为当前可用资源，不据此承诺未来多用户免费。
- L1/L2 若需要持续远程控制面、隧道或身份服务，必须在 full-implementation 提案中重新核验免费额度和超额成本。

## Verified Resources And Gaps

### 已验证资源

- 当前项目已有 Python MCP `read_url` 接口、本地适配器、测试和 stdio 启动入口。
- 现有 Platform tunnel 曾在 ChatGPT 中可见，但需客户端常驻。
- Cloudflare 验证 Worker 的 OAuth、MCP 初始化和工具发现已通过。
- 用户的 Chrome 能直接打开至少一篇被 Jina SaaS 阻断的公众号文章。
- 项目已有 URL 白名单、私网目标拒绝、无 Cookie/任意 header 输入等安全边界。

### 能力缺口

- `127.0.0.1:17831` 当前是 SSH 转发入口；其后端位置、版本、抓取引擎和网络出口尚未确认，因此不能称为已验证的“本地网络 Reader”。
- 尚未证明 Reader 后端当前对多篇公众号文章稳定。
- 尚无自动浏览器正文提取组件；人工复制不再是候选机制。
- 尚未验证 ChatGPT Web 到本机组件的完整调用和回传路径。
- 尚未验证 Windows 运行、打包和浏览器集成。
- 尚无面向外部用户的安装器、设备授权、更新、卸载和支持边界。
- Python 依赖尚未完全锁定；当前配置和 tunnel 凭据不能直接分发给其他用户。

## Candidate Mechanisms

以下只是机制候选，不在 Gate 0 前锁定工具名、扩展形态或供应商：

1. **Reader 直接读取**：本机 MCP 将 URL 交给当前 SSH 转发的 Reader 后端；后端位置、抓取引擎和网络出口先由 H0 确认，不预设它从本机网络访问。
2. **浏览器自动提取**：由浏览器扩展、原生消息桥或等价的最小权限组件，在用户正常打开并完成渲染的页面上只读 DOM；组件不重新请求文章，用户不复制正文。
3. **本地 MCP + 安全出站隧道**：让 ChatGPT App/Web 调用在线设备上的本地读取组件。
4. **个人远程控制面**：只传递 URL、设备状态和短期读取结果，把任务路由到用户当前在线的 Mac 或 PC。
5. **可分发的本地套件**：将读取核心、浏览器集成、MCP 连接和安装/卸载流程打包，在每位用户本机运行。

纯云端 Jina/数据中心浏览器抓取不再作为当前主机制；住宅代理、指纹伪装和验证码自动化被永久排除。

## Path Comparison

| 路线 | 可达层级 | URL 后日常动作 | 主要优点 | 承重缺口 | 当前结论 |
|---|---|---|---|---|---|
| A. 本地 Reader + MCP/tunnel | L3，可能扩展至 L2/L1 | 0 次 | 结构简单、隐私较好 | 微信来源成功率、Web 调用、本地生命周期 | Gate 0 候选 |
| B. 浏览器自动提取 + 本地桥 + MCP/tunnel | L3，可能扩展至 L2/L1 | 0–1 次授权 | 利用用户正常浏览器环境，不搬运正文 | DOM 提取、权限边界、客户端回传 | Gate 0 候选 |
| C. A+B 自动切换的本地套件 | 最有可能逐级达到 L3→L2→L1 | 0–1 次 | 正常情况 URL 直达，反爬时自动转浏览器 | 同时依赖 A/B 的接口与生命周期 | 通过 Gate 0 后才可推荐 |
| D. 个人远程控制面 + 多设备本地套件 | L2，可能成为 L1 基础 | 0–1 次 | App/Web 与设备解耦 | 身份、在线设备路由、费用、正文传输 | Phase 2 候选 |
| E. 纯云端抓取 | 理论上 L1/L2 | 0 次 | 用户端最简单 | 来源条件已被当前证据推翻 | 淘汰 |
| F. 手动复制、打印或上传正文 | 不适用 | 多次 | 无需工程实现 | 违反用户硬约束 | 永久排除 |

## Load-Bearing Assumptions

### 承重假设与最便宜的证伪实验

| ID | Claim | Consequence if false | Evidence state | Volatility | Verified at | Recheck by / trigger | Cheapest falsification probe | Stop condition | Affected route |
|---|---|---|---|---|---|---|---|---|---|
| H0 | 当前 SSH 转发的 Reader 后端身份和访问方式可被确认 | 无法判断 H1 是否与 Jina SaaS 重复，也不能把结果归因于本地网络 | `verified` | volatile | 2026-09-16 | Colima、容器ID、镜像摘要、端口映射或启动命令变化时 | 不读取文章，只检查已批准的本地配置、进程边界、健康信息和版本证据 | 无法确认时把后端记为 unknown，跳过 H1 | A |
| H2 | 正常 Chrome 页面可在不复制正文的情况下自动提取完整文档 | B/C 不成立 | `verified` | volatile | 2026-09-16 | 微信页面结构、Chrome版本或提取机制变化时 | 仅在 Mac 上制作最小、可丢弃的自动 DOM 提取 spike，对同3篇文章各执行一次 | 需要 Cookie 导出、正文复制、越权权限或任一篇无法完整提取 | B、C、L3 |
| H3a | ChatGPT App 能通过 Platform tunnel 调用本地 MCP | App 端 L3 不成立 | `verified` | volatile | 2026-09-16 | ChatGPT App、tunnel-client或连接配置变化时 | 只用固定无敏感测试结果做一次 App 端到端调用，不接触 Reader 或 Worker | 必须手工搬运内容或无法连接 | App、L3 |
| H3b | ChatGPT Web 能通过同一 Platform tunnel 调用本地 MCP | Web 端 L3 不成立 | `verified` | volatile | 2026-09-16 | ChatGPT Web、tunnel-client、tunnel能力或连接配置变化时 | 只用固定无敏感测试结果做一次 Web 端到端调用，不接触 Reader 或 Worker | 必须手工搬运内容或无法连接；不得启用 Worker 补洞 | Web、L3 |
| H3c | H2 的真实文章结果能经本地 MCP 和 Platform tunnel 返回 App/Web | L3 的真实工作流不成立 | `verified` | volatile | 2026-09-16 | H2、MCP结果契约或tunnel配置变化时 | H2 通过后，选1篇文章分别做一次 App 和 Web 端到端调用 | 任一客户端不能取得正文或发生未批准持久化 | B、C、L3 |
| H1 | Reader 直接读取可作为零浏览器动作的快速通道 | A 不能成为主通道，但不阻断 B 达到 L3 | `unverified` | volatile | not-run | Reader版本、后端、出口或微信策略变化时 | H0 可解释后只测试1篇；仅首篇成功时才对其余2篇各调用一次 | 首篇出现 CAPTCHA、环境异常、空文或明显截断即停止，不重复 | A、C |
| H4 | 同一套核心可在 Windows 上达到 Mac 结果 | L2/L1 暂不成立 | `unverified` | volatile | not-run | 进入L2或Windows/浏览器版本变化时 | Gate 0核心通过后，在一台用户PC上做一次干净安装和3篇样本复验 | 需要重写核心或引入未批准付费/高权限组件 | L2、L1 |
| H5 | 外部用户可独立、安全安装和授权 | L1 不成立 | `unverified` | volatile | not-run | 进入L1或安装、授权、分发方式变化时 | L2通过后，由2名试用者按文档完成干净安装、读取和卸载 | 需要维护者Secret、远程人工配置或正文搬运 | L1 |

## Spike Evidence

下表是结构化证据索引。`not-run` 表示尚未获得执行授权或尚未进入对应层级，不得作为成功证据。

| Probe ID | Assumption ID | Environment | Expected falsifier | Observed result | Evidence path | Decision |
|---|---|---|---|---|---|---|
| P0 | H0 | 当前 Mac、Colima 与现有 SSH 转发，只读检查 | 无法确认后端位置、镜像版本、抓取入口或浏览器依赖 | 确认为本机 Colima 中的 Jina OSS Reader；镜像摘要、源码修订、端口、命令和 Puppeteer依赖已记录，外部出口未探测 | `docs/gate0-evidence.md#p0` | `passed` |
| P2 | H2 | 当前 Mac、正常 Chrome、3篇用户提供文章 | 需要正文搬运、认证材料、越权权限，或任一篇提取不完整 | 3/3 真实文章自动提取成功；正文、图片引用和本地 MCP 结果已核验；无正文搬运或持久化 | `docs/gate0-evidence.md#p2-preflight` | `passed` |
| P3A | H3a | ChatGPT App、Platform tunnel、本地 MCP、固定无敏感结果 | 无法调用或需要人工搬运结果 | 返回固定探针，明确 `network_used=false`、`persistent_write=false` | `docs/gate0-evidence.md#p3a` | `passed` |
| P3B | H3b | ChatGPT Web、同一 Platform tunnel、本地 MCP、固定无敏感结果 | 无法调用或需要人工搬运结果 | 返回固定探针，明确 `network_used=false`、`persistent_write=false` | `docs/gate0-evidence.md#p3b` | `passed` |
| P3C | H3c | H2成功文章、本地 MCP、Platform tunnel、App/Web | 任一客户端不能取得文章结果或发生未批准持久化 | ChatGPT App/Web 均返回22,084字符并与P2一致；无网络抓取或持久化 | `docs/gate0-evidence.md#p3c-real-article-transport` | `passed` |
| P1 | H1 | H0可解释的Reader后端、最多3篇文章 | 首篇出现反爬页、空文或明显截断 | 主机DNS安全检查因非公网合成地址返回UNSAFE_DESTINATION；未到达Reader，按一次上限停止 | `docs/gate0-evidence.md#p1` | `inconclusive` |
| P4 | H4 | 用户PC，进入L2后执行 | 无法达到Mac结果或需要未批准高权限/付费组件 | deferred | `docs/l2-evidence.md#p4` | `not-run` |
| P5 | H5 | 两名外部试用者，进入L1后执行 | 需要维护者Secret、远程人工配置或正文搬运 | deferred | `docs/l1-evidence.md#p5` | `not-run` |

## External Claims Evidence

当前 `External evidence gate: pending`。以下时变外部能力只作为待验证条件，不作为 Gate 0 批准依据；在进入 `full-implementation` 前必须用当时的官方资料和真实客户端证据补齐。

| Claim ID | Claim | Volatility | Authoritative source | Verified at | Recheck by / trigger |
|---|---|---|---|---|---|
| X1 | ChatGPT App 当前可使用既有 Platform tunnel 调用本地 MCP | volatile | OpenAI 官方 `openai/tunnel-client` onboarding/configuration；P3A 实测 | 2026-09-16 | ChatGPT App、tunnel-client 或 tunnel 配置变化时 |
| X2 | ChatGPT Web 当前可通过同一 Platform tunnel 调用本地 MCP | volatile | OpenAI 官方 `openai/tunnel-client` onboarding/configuration；P3B 实测 | 2026-09-16 | ChatGPT Web、tunnel-client 或 tunnel 配置变化时 |
| X3 | 当前 tunnel 认证和分发方式可支持未来L2/L1 | volatile | pending；本次 Gate 0 不采用该结论 | not-run | 进入L2或L1提案前 |

## Spike Limits

用户已于 2026-09-16 批准执行 H0、H2、H3a–H3c 和条件式 H1 的最小 Gate 0 spike。H4、H5、full implementation、部署、正式插件切换和外部资源处置不在本次授权内。

Gate 0 必须同时满足以下上限：

- Time limit: 一个工作时段，最多 4 小时；到时停止并报告现状。
- Cost limit: USD 0；不升级套餐、不添加付款方式、不创建新付费资源。
- Data limit: 仅使用用户指定的 3 篇公开公众号文章和一个无敏感固定测试页；不把正文、Cookie或凭据写入 Git 或持久日志。
- Retry limit: H2 对每篇文章最多自动提取一次；H3a/H3b 固定样本各一次，H3c 真实文章在 App/Web 各一次；H1 首篇最多一次且只有成功后才测试其余两篇；没有自动重试。
- **改动**：只允许最小可丢弃测试入口、证据结构和自动 DOM 提取 spike；不建设正式扩展、安装器、远程控制面或公开服务。
- Exit condition: 证据矩阵完成、任一安全边界被触发或时间上限到达时立即停止；不得继续进入完整实现。

从 `spike-only` 扩大到 `full-implementation` 必须根据 Gate 0 证据更新提案并取得新的明确批准。

## 本提案范围

- 记录三层产品目标、共同硬约束和可观察结果。
- 建立 H0、H2、H3a–H3c 和条件式 H1 的 Gate 0 证据矩阵、测试标准和退出条件。
- 将“自动浏览器提取”作为候选机制，彻底移除人工复制/打印正文路线。
- 保留统一结果字段作为候选契约，但不在证据前锁定 `submit_article` 等具体接口。
- 为后续 L3、L2、L1 逐级验收定义门槛。

## 非目标

- 本阶段不发布插件、不开发正式浏览器扩展、不切换生产连接。
- 不假定本地 Reader、ChatGPT Web 本地连接或 Windows 支持已经可用。
- 不建设新的云抓取服务，不继续扩展 Jina SaaS 的公众号适配。
- 不实现 OCR、图片托管、全文知识库、移动端扩展、多用户后台或批量爬取。
- 不读取登录专属、付费墙或非公开内容。
- 不在本提案中删除 Cloudflare Worker、撤销 GitHub OAuth App 或 Jina key。

## Recommended Route

### Gate 0 通过后的条件推荐

若 H2 与 H3a–H3c 通过，L3 的自动浏览器读取主路线成立，可提出路线 B 的 `full-implementation` 提案。若条件式 H1 也达到 3/3，再把 Reader 直接读取作为零浏览器动作的可选快速通道，提出路线 C；H1 不是 L3 的通过前提。该推荐只是条件结论，不是当前架构批准。

若 H1 首篇失败而 H2、H3a–H3c 通过，则后续提案只考虑浏览器自动提取主通道，不再消耗其余两篇 H1 调用。若 H2 或 H3a–H3c 失败，L3 即被阻断；不得退回人工复制正文，也不得临时启用 Cloudflare Worker 补洞。L3 未通过前不进入 Windows 和开源分发。

通过顺序采用共同能力逐级上升：

1. Gate 0：先确认链路身份，再验证 Mac 浏览器自动来源与 App/Web 的 Platform tunnel 传输；Reader 直读只做条件探针。
2. L3：Mac 个人版达到发布质量。
3. L2：在用户 PC 上完成跨平台和个人多设备验证。
4. L1：完成无维护者介入的开源分发、小范围外部试用和安全审查。

任何层级不能达到时，只能在用户明确接受降级后把下一层作为正式目标。

## Architecture And Technology

Gate 0 前只保留最小候选边界，不锁定正式产品技术：

```text
H3 获准测试链路
ChatGPT App/Web
        ↓
Platform tunnel
        ↓
本地 MCP
        ├─ 浏览器自动提取（H2，核心候选）
        └─ SSH 转发的 Reader 后端（H1，可选快速通道）

Gate 0 冻结链路
ChatGPT → Cloudflare Worker → r.jina.ai
```

- **读取核心**：继续以 URL 输入和标准文章结果为稳定边界；Reader 或浏览器 DOM 只是内部来源适配器。
- **浏览器边界**：候选为最小权限扩展、原生消息桥或等价机制；必须自动提取，不能要求用户搬运正文。
- **客户端边界**：H3 只测试 ChatGPT App/Web → Platform tunnel → 本地 MCP；不经过 Cloudflare Worker。个人控制面属于后续候选，不在 Gate 0 建设。
- **分发边界**：L3 先解决 Mac 生命周期；L2 再增加 Windows；L1 最后加入安装签名、升级、卸载和外部用户设备授权。
- **云端边界**：现有 Cloudflare Worker 保持绝对冻结，Gate 0 对其零请求；纯云端来源已淘汰，未来控制面不得承担绕过来源限制的职责。

候选结果字段可继续使用 `status`、`source_channel`、`stage`、`error_code`、`request_id`、`source_url`、`title`、`markdown`、`characters`、`warnings` 和 `limitations`。具体工具名、浏览器实现和远程传输协议需在 Gate 0 后的实施提案中确定。

## Implementation Gates

- Pass criterion: H0 有明确结论；H2 自动 DOM 提取对 3 篇文章达到 3/3；H3a/H3b 的固定样本和 H3c 的真实文章在 ChatGPT App/Web 均通过。H1 无论成功或失败都只决定是否增加 Reader 快速通道，不阻断 L3。
- Stop condition: 任一候选需要复制/打印/上传正文、读取或传输认证材料、绕过访问控制、产生未批准费用，或达到 Gate 0 时间/调用上限时立即停止。

### 后续实施步骤与阶段门槛

以下步骤均不由当前 `spike-only` 范围授权：

1. 根据 Gate 0 结果修订路线、接口和威胁模型，申请 `full-implementation` 批准。
2. 实现 L3 最小产品：自动来源、统一结果、生命周期、App/Web 真实客户端。
3. 以不少于 10 篇不同当前文章进行多日有限真实数据验收；阈值与样本构成在实施提案中确认。
4. L3 通过后，单独验证 Windows 打包、浏览器集成和同一用户多设备授权，决定是否进入 L2。
5. L2 通过后，完成开源许可证、Secret 隔离、安装/更新/卸载、最小权限说明和两名外部试用者干净安装，决定是否进入 L1。
6. 每个层级分别批准上线、回滚和旧资源处置，不把技术验证等同于发布批准。

## Fallback, Rollback, And Exit

- Rollback trigger: Gate 0 触发任何安全边界、出现未批准外部调用或费用、需要手工搬运正文、测试组件无法在上限内隔离，或用户要求停止。
- Last known stable state: 当前 Python MCP、本地适配器和既有 Platform tunnel 保持不变；Cloudflare验证Worker已部署但冻结；正式插件连接尚未切换到新路线。
- Reversible effects: 停止并移除隔离的本地 spike 进程与实验文件，撤销临时浏览器权限，恢复测试前本地配置；证据文档保留脱敏结论。
- Irreversible effects: 预计无持久基础设施或账户变更；已发生的有限文章请求和临时网络传输不能撤回，但不得被插件持久保存。
- Fallback route: 返回明确的自动读取不可用错误并停止；不启用 Cloudflare Worker，不改用人工复制、打印或上传正文。
- Degraded user outcome: 用户提交的公众号 URL 暂时不能被插件读取，L3保持未实现。
- Required approval: 停止或回滚 spike 不需要额外批准；修改正式插件、调用或处置云资源、增加费用、转向新传输路线均需用户另行明确批准。
- Post-rollback verification: 确认实验进程停止、临时权限撤销、正式插件和既有连接未改变、Worker零请求边界未被突破，并运行项目状态与脱敏日志检查。

## 所有权与受影响路径

- 产品目标与架构：`docs/PROJECT_GOAL.md`、`docs/ARCHITECTURE.md`；批准 Gate 0 前需同步移除人工复制路线。
- 本提案归档路径：`proposals/archive/20260914-wechat-reader-hybrid.md`；后续活跃提案为 `proposals/active/20260916-wechat-reader-l3-readiness.md`。
- Gate 0 证据：`docs/` 下独立、可提交的脱敏矩阵；正文与 Secret 不进入 Git。
- 本地读取候选：`reader.py`、`server.py` 及对应测试；仅在获批范围内修改。
- 浏览器自动提取：当前尚无正式路径；spike 获批后使用隔离的实验路径，不直接形成生产扩展。
- Cloudflare：冻结；除另行批准的停用或凭据撤销外不继续开发。
- 独立安装的 Jina 仓库或容器：不修改。

## Security/Ops

分类：`required`。

- Gate 0 开始前形成最小权限清单：允许域名、浏览器页面权限、本地端口、进程和正文流向。
- 自动浏览器提取不得读取认证存储；若浏览器平台无法证明这一边界，相关路线停止。
- 本地服务只绑定 loopback；任何 tunnel 或远程控制面必须使用出站连接、短期授权、设备撤销和最小权限。
- 正文发送前可显示来源、标题和字符数供用户确认，但不得要求用户操作正文。
- L3 正式实现前完成威胁模型；L2 增加设备注册与撤销；L1 增加供应链、发布签名、升级和漏洞响应审查。
- 现有 Cloudflare Worker、GitHub OAuth App 和 Jina key 在 Gate 0 期间保持绝对冻结；不得访问 Worker 的 `/healthz`、OAuth、MCP 或文章接口。H3 只走 Platform tunnel；Gate 0 报告必须提出继续保留或停用云资源的单独决策。

## 风险与缓解

- **浏览器可打开但自动提取不可行**：H2 先做最小证伪；失败即停止，不退回人工搬运正文。
- **ChatGPT Web 无法安全访问本机结果**：H3b 用固定样本先验证 Platform tunnel；失败则 L3 blocked，不用 Worker 或未批准云服务掩盖问题。
- **Reader 后端被误称为本地**：H0 先确认 SSH 终点、版本、引擎和出口；无法确认时跳过 H1，不把未知后端结果归因于 Mac 本地网络。
- **历史 Reader 成功不可复现**：H1 只先读一篇，失败立即停止；成功才扩展到其余两篇，不外推单篇历史结果。
- **开源目标扩大安全和支持成本**：先完成 L3 和 L2，再以两名外部试用者验证安装与 Secret 隔离。
- **免费假设失真**：Gate 0 严格 USD 0；未来外部服务费用按官方来源和真实用量重新计算。
- **公众号 DOM 或策略变化**：结果包含阶段和错误分类；发布前建立有限回归样本，但不绕过新的访问限制。
- **范围滑移**：各层级分别提案和批准，Gate 未过不进入下一阶段。

## 验证计划

### Gate 0 证据矩阵

三篇样本应分别覆盖普通长文、含多图文章、含表格或复杂排版文章，并且测试当日均可由用户 Chrome 正常打开。每篇记录：

- 通道、阶段、状态、耗时、字符数和错误码；
- 标题以及正文开头、主体、结尾的人工一致性结论，但不把正文写入 Git；
- 表格、图注、图片引用的保留情况；
- 是否发生用户正文操作、是否请求浏览器敏感权限；
- App/Web 传输是否端到端完成。

执行顺序和最长时间分配：

1. **H0，最多30分钟**：不读取文章，确认 SSH 转发后端的可识别信息；不能确认则记录 unknown 并跳过 H1。
2. **H3a/H3b，最多30分钟**：App/Web 分别通过 Platform tunnel 读取一次固定无敏感结果；不调用 Worker。
3. **H2，最多2小时**：优先完成只读已渲染 DOM 的自动提取 spike，并对3篇文章各执行一次。
4. **H3c，最多30分钟**：选择1篇 H2 成功文章，在 App/Web 分别完成一次真实端到端返回。
5. **H1与报告，最多30分钟**：H0 可解释时先读1篇；仅首篇成功才读其余2篇，然后完成证据矩阵和结论。

### 后续分层验证

- L3：单元、真实本地运行时、MCP 协议、自动浏览器 UX、ChatGPT App/Web 和有限真实数据。
- L2：Windows 干净安装、Mac/PC 一致性、设备切换、授权撤销和故障恢复。
- L1：两名外部试用者独立安装、无维护者 Secret、升级/卸载、最小权限和文档可用性。

Mock 只能证明契约和错误处理，不能证明公众号来源可用。真实来源测试不得自动重试或通过更换代理规避限制。

## 完成定义

### Gate 0 spike 完成

- H0、H2、H3a–H3c 均产生可复核证据并更新状态；H1 产生“跳过”“首篇即停”或“扩展至3篇”的有条件结论；
- 三篇证据矩阵完整，失败结果包含来源、阶段和具体原因；
- 全程没有复制、粘贴、打印或上传正文，也没有传输 Cookie 或凭据；
- H3 全程只使用 Platform tunnel 和本地 MCP，Cloudflare Worker 保持零请求；
- 没有新费用、生产插件切换或未批准外部资源变更；
- 已输出推荐路线或明确的 blocked 结论，并停止等待新的实施批准。

### 各产品层级完成

- L3：Mac 的 ChatGPT App 与 Web 均达到自动读取结果，日常不需要终端或正文操作。
- L2：用户的 Mac 与 PC 均达到 L3 标准，设备授权和撤销可控。
- L1：少量外部用户能从 GitHub 独立完成安装、授权、读取、更新和卸载，不使用维护者个人 Secret。

只有达到相应层级全部条件，才能声称该层级完成；低层级通过不能证明高层级完成。

## 状态迁移

本提案已按 `spike-only` 范围完成并转为 `verified`：

- H2 与 H3a–H3c 支持自动浏览器路线：保持提案记录；根据 H1 是否成功决定 B 或 C，再另行提交 `full-implementation` 修订，等待新批准；
- 承重假设被推翻且无其他合规自动路线：转 `blocked`；
- 被新路线替代：转 `superseded`；
- 只有获批层级完成全部实现和验证后，才可转 `implemented`、`verified`，最后 `archived`。

原 `20260911-gce-reader-production` 已因来源可行性假设被证据推翻而转 `superseded`。保留历史记录，不把已部署资源或历史成本从决策链中抹去。
