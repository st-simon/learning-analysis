import asyncio, sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    p=StdioServerParameters(command=sys.executable,args=[str(Path(__file__).with_name("server.py"))])
    async with stdio_client(p) as (r,w):
        async with ClientSession(r,w) as s:
            await s.initialize(); tools=await s.list_tools(); assert [x.name for x in tools.tools]==["read_url"]
            assert tools.tools[0].annotations.readOnlyHint
            result=await s.call_tool("read_url",{"url":"file:///etc/passwd"}); assert "could not be read" in str(result)
            print("PASS MCP handshake, read-only discovery, unsafe URL rejection")
            if "--live" in sys.argv:
                result=await s.call_tool("read_url",{"url":"https://example.com"}); assert "Example Domain" in str(result); print("PASS live Jina extraction and archive")
asyncio.run(asyncio.wait_for(main(),60))
