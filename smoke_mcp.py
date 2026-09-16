import asyncio, sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    p=StdioServerParameters(command=sys.executable,args=[str(Path(__file__).with_name("server.py"))])
    async with stdio_client(p) as (r,w):
        async with ClientSession(r,w) as s:
            await s.initialize(); tools=await s.list_tools(); names={x.name for x in tools.tools}
            assert names=={"read_url","read_rendered_url","gate0_transport_probe"}
            assert all(x.annotations.readOnlyHint for x in tools.tools)
            probe=await s.call_tool("gate0_transport_probe",{})
            assert "gate0-transport-v1" in str(probe) and "network_used" in str(probe)
            result=await s.call_tool("read_url",{"url":"file:///etc/passwd"}); assert "could not be read" in str(result)
            rendered=await s.call_tool("read_rendered_url",{"url":"file:///etc/passwd"}); assert "INVALID_SOURCE_URL" in str(rendered)
            print("PASS MCP handshake, no-network Gate 0 probe, read-only discovery, unsafe URL rejection")
            if "--live" in sys.argv:
                result=await s.call_tool("read_url",{"url":"https://example.com"}); assert "Example Domain" in str(result); print("PASS live Jina extraction and archive")
asyncio.run(asyncio.wait_for(main(),60))
