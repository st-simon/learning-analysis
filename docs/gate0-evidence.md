# Gate 0 Evidence

该文件只保存脱敏的结构化验证证据，不保存文章正文、完整文章 URL、Cookie、Secret 或浏览器认证材料。

## P0

- Assumption ID: H0
- Date: 2026-09-16
- Environment: 当前 Mac；Colima `aarch64`；Docker runtime；macOS Virtualization.Framework
- Probe type: 只读本地进程、容器、镜像和依赖检查；零文章调用；零 Cloudflare Worker 请求
- Expected falsifier: 无法确认 `127.0.0.1:17831` 的后端位置、镜像版本、抓取入口或浏览器依赖
- Observed result:
  - 端口由 Colima SSH 复用连接转发，不是远程云主机 SSH。
  - 容器名：`jina-reader-validation`。
  - 镜像：`ghcr.io/jina-ai/reader:oss`。
  - 镜像摘要：`sha256:8cc9a5cf6dc9c240235fccc0026661de74b6e13c21b36e6a86b3281b9ef10f28`。
  - OCI源码修订：`1574bfd380d249c86c82db4dace0d9c8fe17e2b1`。
  - 入口：`node build/stand-alone/crawl.js`。
  - 端口：本机 `127.0.0.1:17831` 映射到容器 `8081/tcp`。
  - 容器网络：Docker bridge；镜像依赖包含 Puppeteer `^24.42.0`。
  - 容器未配置 Docker healthcheck；进程运行不等于文章来源可用。
  - 未调用外部 IP 服务测量出口地址，因此不声称已验证具体公网出口。
- Decision: passed
- Effect: H1 与 Jina SaaS 不是同一运行池，保留一次条件式 Reader 探针；H1仍不是L3阻断条件。
- Recheck trigger: Colima、容器ID、镜像摘要、端口映射或启动命令发生变化。

## P3 transport preflight

- Date: 2026-09-16
- Environment: 当前 Mac；OpenAI `tunnel-client` v0.0.14；既有 `learning-analysis` Platform tunnel；本地 FastMCP stdio server
- Probe type: 固定无敏感工具的本地协议测试、官方 `doctor`、ChatGPT Web 工具清单刷新；零文章调用；零 Cloudflare Worker 请求
- Observed result:
  - 官方发布资产 `tunnel-client-v0.0.14-darwin-arm64.zip` 的 SHA-256 为 `b540493c5bdbcdbb755700c8e2e16597e28b1569e425007e0f73111047bd6a64`，与 GitHub release digest 一致。
  - 二进制只安装到 Git 忽略的项目目录 `runtime/bin/`，未写入系统目录。
  - `doctor` 通过配置来源、tunnel ID、运行密钥引用、stdio MCP 命令和回环健康监听检查。
  - tunnel metadata 返回名称 `learning-analysis`，客户端进入 started 状态。
  - ChatGPT Web 刷新后发现 `gate0_transport_probe` 和 `read_url` 两个工具；固定探针声明无输入。
  - 客户端先发送当前 Python MCP SDK 尚不支持的 `server/discover`，随后回退到标准初始化与 `tools/list` 并成功完成工具发现；记录为兼容性告警。
- Decision: transport discovery passed; P3A and P3B passed
- Recheck trigger: tunnel-client、Python MCP SDK、tool schema、tunnel ID 或 ChatGPT 插件版本变化。

## P3A

- Assumption ID: H3a
- Date: 2026-09-16
- Environment: ChatGPT App；既有 `learning-analysis` Platform tunnel；本机 `tunnel-client` v0.0.14；本地 FastMCP stdio server
- Probe type: 用户在 App 的既有对话中发送一次固定无敏感请求，明确禁止调用 `read_url` 或访问文章
- Expected falsifier: ChatGPT App 无法发现或调用固定探针、需要搬运工具结果，或调用发生网络访问/持久化写入
- Observed result:
  - ChatGPT App 返回 `status=ok`、`probe_id=gate0-transport-v1`、`fixture=local-mcp-no-network`。
  - 返回值明确为 `network_used=false`、`persistent_write=false`。
  - 未传输文章 URL 或正文；未调用 Reader；未调用 Cloudflare Worker。
- Decision: passed
- Recheck trigger: ChatGPT App、tunnel-client、tunnel ID、插件版本或探针契约变化。

## P3B

- Assumption ID: H3b
- Date: 2026-09-16
- Environment: ChatGPT Web；既有 `learning-analysis` Platform tunnel；本机 `tunnel-client` v0.0.14；本地 FastMCP stdio server
- Probe type: 在既有“文章分析归纳”对话中发送一次固定无敏感请求，明确禁止调用 `read_url` 或访问文章
- Expected falsifier: ChatGPT Web 无法发现或调用固定探针、需要人工搬运结果，或调用发生网络访问/持久化写入
- Observed result:
  - ChatGPT Web 显示已调用工具，并返回 `status=ok`、`probe_id=gate0-transport-v1`、`fixture=local-mcp-no-network`。
  - 返回值明确为 `network_used=false`、`persistent_write=false`。
  - tunnel-client 同时记录一次转发到本地 MCP 的 `CallToolRequest`。
  - 未传输文章 URL 或正文；未调用 Reader；未调用 Cloudflare Worker。
- Decision: passed
- Recheck trigger: ChatGPT Web、tunnel-client、tunnel ID、插件版本或探针契约变化。

## P2 preflight

- Date: 2026-09-16
- Environment: 当前 Mac；Chrome Manifest V3 disposable spike；本机回环桥 `127.0.0.1:18431`；本地 MCP
- Probe type: 单元测试、MCP smoke test、扩展语法/manifest 检查，以及一份无敏感假文章的真实回环提交与读取
- Security boundary:
  - 扩展权限仅为 `activeTab`、`scripting` 和固定回环地址；未请求 Cookie、历史、storage、代理或公众号后台权限。
  - 捕获必须由一次工具栏点击触发，只读取当前页面已经渲染的 DOM，不发起公众号 fetch/XHR。
  - 网页 Origin 不能提交捕获；仅 `chrome-extension://` Origin 可提交。
  - MCP 读取需要本机 0600 随机令牌；正文只保存在桥进程内存。
- Observed result:
  - 21 项 Python 测试通过；MCP handshake/smoke test 通过；扩展 JavaScript 语法和 manifest JSON 校验通过。
  - 假文章由扩展 Origin 提交后，本地读取路径按 URL 取回，返回 `source_channel=rendered_dom`、`network_used=false`、`persistent_write=false`。
  - Chrome 安全策略禁止自动化访问 `chrome://extensions`；扩展加载必须由用户在浏览器管理页亲自完成，不采用绕过手段。
- Decision: pass; code/loopback contract and all 3 real-article captures passed
- Recheck trigger: 扩展权限、回环端口、令牌边界、Chrome 或公众号 DOM 变化。

### P2 real article 1

- Date: 2026-09-16
- Source URL SHA-256: `2027640671f8a10821f82a9b0f795ff6462ccf7a49784c40eb6299caa97a4327`
- User authorization: 用户在已正常渲染的 Chrome 文章页点击一次 disposable 扩展；扩展返回绿色 `OK`。
- Observed result:
  - 标题：`经营分析最常用的10个财务比率指标：看懂盈利、偿债、周转和经营效率`
  - Markdown 字符数：10,902；图片引用：32；Markdown 表格行：0。
  - 本机捕获返回 `source_channel=rendered_dom`、`network_used=false`、`persistent_write=false`。
  - 本地 MCP `read_rendered_url` 返回成功，字符数与内存捕获完全一致。
- Boundary: 该结果证明真实 Chrome DOM → 本机内存桥 → 本地 MCP；当前 Codex 任务仅暴露旧 `read_url` 工具，因此尚未把本任务内的远端插件调用记为 P3C 通过。
- Decision: pass for article 1; continue with two distinct current articles before closing P2.

### P2 real article 2

- Date: 2026-09-16
- Source URL SHA-256: `b01d8d029db4a9c9d3d00760fb0a204fcbc82a20a29f563cdc6770e0bcbf0f86`
- User authorization: 用户在已正常渲染的 Chrome 文章页点击一次 disposable 扩展；扩展返回绿色 `OK`。
- Observed result:
  - 标题：`GitHub 6.7万 Star，一个多 Agent 协作、手机远程指挥的开源神器！`
  - Markdown 字符数：5,137；图片引用：12；Markdown 表格行：0。
  - 本机捕获返回 `source_channel=rendered_dom`、`network_used=false`、`persistent_write=false`。
  - 本地 MCP `read_rendered_url` 返回成功，字符数与内存捕获完全一致。
- Decision: pass for article 2; one distinct current article remains before closing P2.

### P2 real article 3

- Date: 2026-09-16
- Source URL SHA-256: `a0144ae7ff9c44c9fb5e4a98b40e0d97a2779a609eec6e7e2620b55eb2603af0`
- User authorization: 用户在已正常渲染的 Chrome 文章页点击一次 disposable 扩展；扩展返回绿色 `OK`。
- Observed result:
  - 标题：`万字详解GPT-6 Astra，Sebastian Raschka带你读懂循环Transformer与隐藏的思维链`
  - Markdown 字符数：22,084；图片引用：28；Markdown 表格行：0。
  - 本机捕获返回 `source_channel=rendered_dom`、`network_used=false`、`persistent_write=false`。
  - 本地 MCP `read_rendered_url` 返回成功，字符数与内存捕获完全一致。
- Decision: pass for article 3; P2 closes at 3/3 passed.

## P3C real article transport

- Date: 2026-09-16
- Source URL SHA-256: `a0144ae7ff9c44c9fb5e4a98b40e0d97a2779a609eec6e7e2620b55eb2603af0`
- ChatGPT App observed result:
  - `status=ok`
  - 标题与 P2 本地捕获一致。
  - `characters=22084`，与 P2 本地捕获一致。
  - `source_channel=rendered_dom`、`network_used=false`、`persistent_write=false`。
- ChatGPT Web observed result:
  - `status=ok`
  - 标题与 P2 本地捕获一致。
  - `characters=22084`，与 P2 本地捕获一致。
  - `source_channel=rendered_dom`、`network_used=false`、`persistent_write=false`。
- Decision: pass; App and Web each returned the same real rendered article through Platform tunnel with no persistent write.

## P1

- Assumption ID: H1
- Date: 2026-09-16
- Probe type: 对第1篇样本执行唯一一次本地 Reader 直读入口调用；强制 `READER_ARCHIVE_MODE=none`。
- Observed result:
  - 返回 `UNSAFE_DESTINATION`，无标题、正文、图片或归档文件。
  - 主机解析器把 `mp.weixin.qq.com` 解析为 `198.18.0.210`；该地址属于非公网基准测试网段，触发入口 DNS 安全检查。
  - 后续只读核验确认原探针使用 Mac 主机权限运行，并非 Codex 沙箱网络；macOS 正常解析器和 Jina 容器均返回 `198.18.0.210`，路由指向本机 `utun` 的 Fake-IP 网关。
  - 请求在进入本地 Jina Reader 前终止，因此该结果既不是微信反爬结果，也不能证明 Reader 可用。
- Retry decision: 按 Gate 0 首篇最多一次的限制停止；未绕过安全检查，未测试另外2篇。
- Decision: inconclusive and stopped; 该证据只证明主机入口安全判断与 Reader 实际出口环境不一致，不能证明 Reader 或微信拒绝访问。Reader快速通道不进入当前L3路线；后续若重启必须另行提案，令DNS安全判断与实际Reader出口环境一致且不削弱SSRF防护。

## Gate 0 decision

- H0 passed；H2 passed（3/3）；H3a/H3b/H3c passed。
- H1 inconclusive，不阻断L3；浏览器已渲染 DOM 是唯一获得真实来源证据的主路线。
- Gate 0 acceptance criterion is met for L3 feasibility. Full implementation、正式插件切换、生命周期服务、安装器和Windows/外部用户验证仍需新的提案与明确批准。

## Pending probes

| Probe | State | Bound |
|---|---|---|
| P3A / H3a | passed | ChatGPT App 已返回固定无敏感结果；Platform tunnel；零 Worker 请求 |
| P3B / H3b | passed | ChatGPT Web 已返回固定无敏感结果；Platform tunnel；零 Worker 请求 |
| P2 / H2 | passed | 3/3 真实文章通过；各自动提取一次；不复制正文 |
| P3C / H3c | passed | ChatGPT App/Web 均返回同一真实文章，且与P2结果一致 |
| P1 / H1 | inconclusive | Mac TUN/Fake-IP使主机和容器均解析到保留地址；入口安全检查先于Reader终止，未测试Reader或微信，未重试 |
