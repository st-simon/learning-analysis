# Learning Analysis：混合读取架构

更新日期：2026-09-16；状态：Gate 0 已验证；L3 正式化就绪 proposal 待审批，尚未批准 full implementation、部署或正式切换。

## 产品优先级

第一工作流和验收标准见 [PROJECT_GOAL.md](PROJECT_GOAL.md)。架构必须先解决微信公众号来源访问能力，再考虑跨设备、云端认证或长期运行。

## 当前设计压力

`read_url` 的调用方需要的是可信文章文档，不应知道浏览器提取、内存协调、进程生命周期或 tunnel 细节。Gate 0 证明这些层可以连通，但当前 spike 仍由两个手工进程和一个临时扩展组成，且调用必须发生在捕获之后；正式化压力是把复杂度收进一个可监督、可配对、可等待的本机接口。

## 推荐 seam 与接口

内部统一结果：

```text
ArticleResult
  status: SOURCE_OK | ACTION_REQUIRED_BROWSER | SOURCE_ERROR
  source_channel: local_reader | browser_assisted | remote_validation
  stage: validate | connect | send | receive | parse | extract
  error_code: SOURCE_NETWORK | SOURCE_RATE_LIMIT | SOURCE_ANTI_BOT |
              SOURCE_AUTH | SOURCE_PARSE | SOURCE_EMPTY | SOURCE_TOO_LARGE
  request_id, source_url, title, markdown, characters, warnings, limitations
```

对外只保留一个用户意图：

- `read_url(url)`：建立有界内存请求，等待用户最多一次浏览器授权并返回 `ArticleResult`。若等待或来源失败，返回明确错误，不要求用户提交正文。

`read_rendered_url` 仅作为迁移期诊断接口；正式插件默认不要求调用方理解或选择它。

调用方不能指定代理、Cookie、任意 header、抓取引擎或供应商。通道选择属于服务内部策略。

## 适配器边界

### LocalReaderSource

Gate 0 探针为 `inconclusive`：Mac TUN/Fake-IP 使主机和 Reader 容器都得到保留地址，入口安全检查在 Reader 实际出站前终止，因此没有验证 Reader 或微信访问能力。它不进入当前 L3 主路线，也没有被永久淘汰；除非后续新提案能让安全判断与实际 Reader 出口边界一致并保持 SSRF 防护，否则不再调用或修改。

### BrowserAssistedSource / CaptureCoordinator

从用户已经正常打开并完成渲染的 Chrome 页面自动提取 DOM 内容。正式候选由 `CaptureCoordinator` 统一管理 request ID、URL hash、deadline、精确扩展身份、每安装令牌、单次消费和内存清除。组件只读当前页面，不自行发起文章 fetch/XHR；用户最多执行一次授权动作，不复制、粘贴、打印或上传正文。不得读取或上传 Cookie、localStorage、登录令牌和浏览历史。

### RemoteJinaSource

仅作为已完成的历史验证适配器冻结。现有 Cloudflare Worker 不再扩展公众号抓取能力，不作为生产主通道。停用 Worker、撤销 GitHub OAuth App 或 Jina key 属于单独的外部状态变更，需明确批准。

## 方案比较

| 方案 | 优点 | 限制 | 结论 |
|---|---|---|---|
| 单一远端 Jina SaaS | 跨设备、维护少 | 已被测试文章的微信环境验证阻断 | 不作为主路线 |
| 本地 Reader 单通道 | URL 直达、隐私较好 | 依赖本机和当前网络，稳定性待复验 | Gate 0 候选 |
| 本地 Reader + 浏览器辅助 | 合规利用用户已获准页面，失败路径清晰 | 被拦截时需要用户一次操作 | 推荐主路线 |
| 浏览器扩展 + 云端临时中转 | 可跨设备 | 新增正文传输、认证、TTL存储和攻击面 | Phase 2 另提案 |
| 住宅代理/指纹伪装 | 可能提高抓取率 | 规避访问控制、费用和合规风险 | 排除 |

## 环境摘要

- Mac：Apple Silicon `arm64`，macOS 15.0；可用磁盘约 207 GiB。
- RAM 容量在当前受限检查中未确认；Gate 0 不做资源规格或容量承诺。
- Python 3.13.7；项目使用 `.venv`，依赖范围记录于 `requirements.txt`，当前没有完全锁定的 Python lock 文件。
- Node 24.15.0、npm 11.13.0；Cloudflare 适配器使用 `package-lock.json`。
- `127.0.0.1:17831` 当前由 SSH 监听；实际后端健康、版本和出口仍需单独检查。
- 因此“本地 Reader”当前只表示本地转发入口，不证明 Reader 后端位于本机或使用家庭网络出口；H0 必须先确认该边界。
- 项目不直接调用 LLM；模型选择和生成质量由 ChatGPT/Codex 分析层承担，因此本项目无需模型角色表。

## 配置、隐私与安全

- `.env*`、`.dev.vars*`、日志、归档和构建产物保持 Git 忽略；Secret 不进入代码、测试输出或聊天。
- URL 必须是允许域名的公开 HTTPS 地址；拒绝凭据、自定义端口和私有网络目标。
- 浏览器辅助只提取当前页面正文；发送前展示来源、标题和字符数，由用户确认。
- 默认不云端归档正文。若未来需要跨设备中转，必须定义加密、最短 TTL、删除语义和访问审计，并单独审批。
- 不自动重试反爬、CAPTCHA、403 或环境异常；不切换代理或供应商规避限制。

## 标准符合性

- `.gitignore` 已覆盖 `.env*`、`.dev.vars*`、归档、日志、构建目录和本地依赖。
- Cloudflare Node 依赖有 `package-lock.json`；Python 依赖目前只有版本范围，尚未形成完全可复现的 lock。
- 项目当前缺少可提交的 `.env.example`；Gate 0 不新增 Secret，若后续新增本地配置，必须先补占位模板且不得包含真实值。
- `README.md`、`TASKS.md`、`DECISIONS.md`、项目目标和架构文档均存在；代码目录沿用现有小型项目结构，不为文档重构强制搬迁。

## 可观测性

每个读取事件记录结构化、非敏感字段：时间、`request_id`、通道、阶段、错误码、上游状态、耗时、字符数和是否需要用户动作。不得记录正文、Secret、Cookie；完整 URL 默认只在当前请求内使用，持久日志使用允许域名与 URL 哈希。

阶段和原因分开保存。例如：`stage=extract`、`error_code=SOURCE_ANTI_BOT`，避免把 HTTP 403、API key 认证失败和 CAPTCHA 混为同一问题。

## 测试与阶段门槛

1. **Gate 0：来源与传输可行性**——先做 H0 后端身份检查和 App/Web 固定样本传输，再用3篇真实文章优先验证浏览器自动提取；Reader直读只做条件探针；既有远端失败只登记不重试。
2. **单元测试**——URL边界、文档校验、错误分类、敏感字段排除。
3. **本地原生运行时**——真实本地入口、固定样本、明确阶段；不依赖浅层 mock 宣称可用。
4. **协议测试**——无浏览器地验证 MCP 请求/响应和动作提示。
5. **浏览器 UX**——只验证用户提取体验，不用浏览器排查协议错误。
6. **真实客户端**——ChatGPT/Codex 端到端调用。
7. **有限真实数据**——明确调用上限、每次新状态、不自动重试。

任一阶段未过，不进入下一阶段。安全逻辑修改前必须捕获可复现的状态、阶段和非敏感响应证据。

## 已完成：Gate 0 可行性切片

Gate 0 已完成以下证据：

- 本机 Colima Reader 身份已确认，但直读探针被 Mac TUN/Fake-IP 与入口安全检查的边界错位提前终止，结果不具备来源可用性结论。
- Platform tunnel 的 App/Web 固定探针与真实文章传输通过。
- Chrome DOM 自动提取对3篇真实文章达到3/3。
- 正文只存在于内存和本次 MCP 响应，Cloudflare Worker 零调用。

## 下一阶段：L3 正式化就绪 Gate

在 full implementation 前分两段验证承重条件。Gate 1A 已验证 App/Web 同次调用等待、一次授权后自动返回和精确扩展配对。Gate 1B 已在另行批准后验证 disposable 用户级 LaunchAgent：初始启动、一次受监督恢复、恢复前后 App 固定探针和完整卸载均通过；该验证没有让 capture bridge 常驻，也没有验证自然登录/重启。

## 当前条件分支

- 浏览器自动提取与App/Web传输已通过：路线达到L3可行性门槛。
- Reader直读未到达后端：证据为 `inconclusive`，当前延期，不阻断浏览器主路线，也不作为回退。
- Gate 1A 与 disposable Gate 1B 已全部通过：下一步只能另行提交 L3 `full-implementation` proposal，不得把 spike 直接转为生产安装。
- 任一正式化承重条件失败：L3保持可行但未产品化；不退回人工搬运正文或云抓取。

## 开放问题

- 用户更重视 URL 直达，还是跨设备使用；二者可能需要不同的 Phase 2。
- 浏览器自动提取正式版采用书签脚本、扩展还是原生消息桥；Gate 0 后再选，人工复制不在候选内。
- 文章正文是否允许短期经过 Cloudflare；当前默认答案为否。
- 现有 Cloudflare Worker、GitHub OAuth App 和 Jina key何时停用或撤销；需要单独批准。
- Python 应用依赖是否在实现前改为可复现 lock；不得与 Gate 0 逻辑改动混做。
