# L3 readiness evidence

更新日期：2026-09-17

本文只记录 Gate 1A 的脱敏证据。不得写入正文、完整文章 URL、安装令牌、Tunnel key 或浏览器认证材料。Gate 1B 未获批准，不在本文执行范围。

## P8

- Assumption: H8，扩展 ID 和每安装令牌稳定配对，错误 Origin 或令牌被拒绝。
- State: passed.
- Limits: 最多两次 Chrome 重载；不扩大扩展权限；不保存正文。
- Local evidence:
  - Manifest公开key确定的扩展ID为 `bpannmkojgebmphkkngpnhkfcgfpnbhn`；自动测试重新推导得到同一ID。
  - 扩展权限仍仅为 `activeTab`、`scripting` 和 `http://127.0.0.1:18431/*`。
  - 每安装令牌只存在于Git忽略的本机文件，两个文件权限均为 `0600`；配置命令不输出令牌。
  - 正确Origin+令牌可提交；错误Origin返回 `FORBIDDEN_ORIGIN`；错误令牌返回 `UNAUTHORIZED`。
  - 协调器通过等待完成、超时、取消、并发URL隔离和单次消费测试。
  - Mac原生loopback集成通过；初次失败归因为测试客户端继承SOCKS代理环境，设置 `trust_env=False` 后通过，未更改系统代理。
- Chrome evidence: 用户于2026-09-17加载unpacked扩展，初始ID为 `bpannmkojgebmphkkngpnhkfcgfpnbhn`；点击卡片重载图标两次后，ID两次均保持一致。
- Decision: pass; H8 verified for the Gate 1A unpacked installation. Recheck when the manifest key, extension directory or packaging method changes.

## P6

- Assumption: H6，ChatGPT App/Web 的同一次工具调用至少提供25秒有效等待窗口，并可在一次浏览器授权后返回。
- State: failed at ChatGPT App real-article probe.
- Limits: 每个客户端依次一次5秒控制、一次25秒fixture；首个失败即停止。双端fixture均通过后，最多复用1篇公开文章各一次；不重试。
- Preflight: tunnel-client `0.0.14` fetched `learning-analysis` metadata and reached both `/healthz` and `/readyz`; the current MCP tool list includes `gate1a_wait_probe` in local smoke verification.
- App discovery evidence:
  - 用户在 ChatGPT 桌面 App 新对话发起5秒控制后，客户端返回 `gate1a_wait_probe is not available in the currently exposed tool schema`。
  - 该错误发生后，tunnel-client 没有收到新的命令或工具调用；因此请求未进入 tunnel、MCP server 或5秒等待逻辑。
  - OpenAI 官方说明：已批准 MCP 应用使用冻结的工具与输入快照，服务端更新不会自动启用；需要在应用设置中刷新操作，新操作默认不自动启用。
- Approved refresh evidence:
  - 用户批准后，仅对现有应用执行一次“刷新”操作；页面确认“操作已刷新”。
  - 刷新后的操作清单出现`gate1a_wait_probe`，分类为“读取”，可见性为`public`；输入架构仅含必填整数`delay_seconds`。
  - 刷新期间tunnel收到发现请求并完成`tools/list`；刷新后`/readyz`仍返回`ready`。
  - 现有endpoint、认证、权限和生产路由未修改；tunnel恢复`live`/`ready`，未调用Cloudflare Worker或Jina。
- App 5-second control evidence:
  - 用户返回：`status=ok`、`probe_id=gate1a-wait-v1`、`delay_seconds=5`、`elapsed_ms=5001`、`fixture=local-mcp-no-network`、`network_used=false`、`persistent_write=false`。
  - tunnel-client同时记录一次转发到本地MCP的`CallToolRequest`。
- App 25-second fixture evidence:
  - 用户在同一ChatGPT桌面App对话返回：`status=ok`、`probe_id=gate1a-wait-v1`、`delay_seconds=25`、`elapsed_ms=25001`、`fixture=local-mcp-no-network`、`network_used=false`、`persistent_write=false`。
  - tunnel-client同时记录一次转发到本地MCP的`CallToolRequest`。
- Web 5-second control evidence:
  - 用户在Chrome的ChatGPT Web新对话返回：`status=ok`、`probe_id=gate1a-wait-v1`、`delay_seconds=5`、`elapsed_ms=5001`、`fixture=local-mcp-no-network`、`network_used=false`、`persistent_write=false`。
  - tunnel-client同时记录一次转发到本地MCP的`CallToolRequest`。
- Web 25-second fixture evidence:
  - 用户在同一ChatGPT Web对话返回：`status=ok`、`probe_id=gate1a-wait-v1`、`delay_seconds=25`、`elapsed_ms=25000`、`fixture=local-mcp-no-network`、`network_used=false`、`persistent_write=false`。
  - tunnel-client同时记录一次转发到本地MCP的`CallToolRequest`。
- App real-article evidence:
  - 用户按步骤在ChatGPT桌面App调用`read_rendered_url`并在Chrome执行一次扩展授权；客户端返回`status=error`，其余请求字段为空。
  - tunnel-client记录`CallToolRequest`；本地MCP向loopback协调器发出带request ID的25秒等待请求。
  - loopback在约25062ms返回HTTP 408，MCP分类为`CAPTURE_TIMEOUT`；因此调用已到达等待逻辑，但等待窗口内没有捕获被协调器接受。
  - 用户确认点击后扩展徽标为红色`ERR`，排除“扩展收到2xx但协调器随后丢失结果”；失败位于页面提取或POST提交路径。
  - 当前扩展会把提取、CORS、Origin/令牌、URL匹配及无pending request统一显示为徽标`ERR`，且bridge关闭访问日志；现有证据不能最终区分这些子原因。
  - 代码审查暴露一个不依赖本次具体时序即可成立的竞态：扩展POST仅在MCP已为同一URL登记pending request后才会被接受；用户“发送提示后立即点击”不能保证模型已实际发起工具调用，过早点击会得到`CAPTURE_NOT_FOUND`，且单次用户授权不会在pending建立后自动重放。
- Decision: P6 failed under the approved no-retry rule. Fixture等待矩阵通过，但真实文章的App同次授权返回失败；Web真实文章探针未运行，H6对当前实现判为`falsified`。
- Follow-up requirement: 若另行提案继续路线A，必须先消除点击/pending竞态（例如扩展在一次点击后有界等待pending就绪，或采用等价的一次性握手），并让扩展/bridge输出脱敏阶段错误码；未完成前不得重跑真实文章探针。
- Boundary: 用户于2026-09-17批准窄范围修订：只刷新该应用的工具快照并启用新增的只读fixture工具，不改endpoint、认证、其他权限或生产路由；不以已有工具暗藏fixture作为规避方案。

## Gate 1A decision

- State: blocked; P8 passed, P6 failed, H6 falsified for the current implementation.
- Gate 1B and full implementation remain unapproved.
- Cleanup evidence:
  - 用户于2026-09-17确认已从Chrome移除测试扩展。
  - tunnel-client与loopback bridge均已停止；端口63770和18431无监听进程。
  - 测试未保存文章正文，未调用Cloudflare Worker或Jina，费用为USD 0。
  - 用户明确批准后，两个Git忽略的测试配对文件与两个`/private/tmp`二进制副本均已永久删除；专用临时目录已移除。
