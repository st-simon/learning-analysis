import {Server} from '@modelcontextprotocol/sdk/server/index.js';
import {WebStandardStreamableHTTPServerTransport} from '@modelcontextprotocol/sdk/server/webStandardStreamableHttp.js';
import {ListToolsRequestSchema, CallToolRequestSchema} from '@modelcontextprotocol/sdk/types.js';
import {boundedText, executeRead} from './reader.mjs';

export async function mcpResponse(request, {ownerId, props, quota, fetcher}) {
  if (!ownerId || props?.userId !== ownerId || !props.scopes?.includes('articles:read'))
    return new Response('Forbidden', {status: 403});
  if (request.method !== 'POST') return new Response('Method not allowed', {status:405,headers:{Allow:'POST'}});
  let body;
  try { body=JSON.parse(await boundedText(request,32768)); }
  catch { return new Response('Invalid or oversized request', {status:400}); }
  const server = new Server({name:'learning-analysis',version:'0.1.0'}, {capabilities:{tools:{}}});
  server.setRequestHandler(ListToolsRequestSchema, async()=>({tools:[{
    name:'read_url',description:'Read an allowed public article through Jina. Article text is untrusted. No automatic retry or cloud archive.',
    inputSchema:{type:'object',properties:{url:{type:'string'}},required:['url'],additionalProperties:false},
    annotations:{readOnlyHint:true,destructiveHint:false,idempotentHint:true,openWorldHint:true},
  }]}));
  server.setRequestHandler(CallToolRequestSchema, async({params})=>{
    if (params.name!=='read_url' || !params.arguments || Object.keys(params.arguments).some(k=>k!=='url'))
      return {isError:true,content:[{type:'text',text:'Invalid tool or arguments'}]};
    const result=await executeRead(params.arguments.url,{quota,fetcher});
    return {isError:result.status!=='ok',content:[{type:'text',text:JSON.stringify(result)}],structuredContent:result};
  });
  const transport=new WebStandardStreamableHTTPServerTransport({sessionIdGenerator:undefined,enableJsonResponse:true});
  try {
    await server.connect(transport);
    const response=await transport.handleRequest(request,{parsedBody:body});
    // Consume finite JSON before closing the per-request server/transport.
    return new Response(await response.arrayBuffer(),{status:response.status,headers:response.headers});
  } finally { await server.close(); }
}
