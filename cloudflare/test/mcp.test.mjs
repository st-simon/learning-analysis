import {test} from 'node:test';
import assert from 'node:assert/strict';
import {mcpResponse} from '../src/mcp.mjs';
const request=method=>new Request('https://reader.example/mcp',{method:'POST',headers:{'Content-Type':'application/json',Accept:'application/json, text/event-stream'},body:JSON.stringify({jsonrpc:'2.0',id:1,method,params:method==='initialize'?{protocolVersion:'2025-11-25',capabilities:{},clientInfo:{name:'test',version:'1'}}:{}})});
test('anonymous, wrong owner and wrong scope cannot read or discover',async()=>{
  for (const props of [undefined,{userId:'other',scopes:['articles:read']},{userId:'123',scopes:[]}]) {
    assert.equal((await mcpResponse(request('tools/list'),{ownerId:'123',props})).status,403);
  }
});
test('stateless MCP initialize and tools discovery work without a session',async()=>{
  const settings={ownerId:'123',props:{userId:'123',scopes:['articles:read']}};
  const init=await mcpResponse(request('initialize'),settings);
  assert.equal(init.status,200); assert.equal(init.headers.get('mcp-session-id'),null);
  const list=await mcpResponse(request('tools/list'),settings);
  assert.equal((await list.json()).result.tools[0].name,'read_url');
});
