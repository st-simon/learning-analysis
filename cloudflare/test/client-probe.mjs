import {createServer} from 'node:http';
import {randomBytes, createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';

const workerOrigin='https://learning-analysis-validation.learning-analysis-worker.workers.dev';
const htmlHeaders={'Content-Type':'text/html; charset=utf-8','Cache-Control':'no-store',
  'Referrer-Policy':'no-referrer','Content-Security-Policy':"default-src 'none'; frame-ancestors 'none'; base-uri 'none'"};

export async function startClientProbe({fetcher=fetch, report=console.log, timeoutMs=300000}={}) {
  const verifier=randomBytes(32).toString('base64url'), state=randomBytes(32).toString('base64url');
  const challenge=createHash('sha256').update(verifier).digest('base64url');
  let phase='setup', consumed=false, localOrigin, authorizationUrl, clientId, timer;
  const request=async(path,options={})=>fetcher(workerOrigin+path,
    {...options,redirect:'manual',signal:AbortSignal.timeout(15000)});
  const json=async(path,options,expected=200)=>{
    const response=await request(path,options);
    if(response.status!==expected) throw new Error('HTTP_'+response.status);
    return response.json();
  };
  const finish=()=>{clearTimeout(timer);server.close();server.closeIdleConnections();};
  const server=createServer(async(req,res)=>{
    const reply=(status,body)=>{res.writeHead(status,htmlHeaders);res.end(body);};
    if(req.headers.host!==new URL(localOrigin).host || req.method!=='GET') return reply(400,'Invalid request');
    const url=new URL(req.url,localOrigin);
    if(url.pathname==='/') {
      if(!authorizationUrl) return reply(503,'Preparing');
      return reply(200,`<!doctype html><meta charset="utf-8"><title>Reader client verification</title><h1>文章读取：客户端验证</h1><p>本次只验证登录与工具发现，不读取文章。授权数据仅存于本机内存，五分钟后自动结束。</p><a href="${authorizationUrl.replaceAll('&','&amp;')}">开始 GitHub 授权</a>`);
    }
    if(url.pathname!=='/callback') return reply(404,'Not found');
    if(url.searchParams.getAll('state').length!==1 || url.searchParams.get('state')!==state)
      return reply(400,'Invalid state');
    if(consumed) return reply(409,'Already consumed');
    consumed=true;
    try {
      phase='callback';
      const code=url.searchParams.get('code');
      if(url.searchParams.has('error') || !code || code.length>2048 || url.searchParams.getAll('code').length!==1)
        throw new Error('Invalid callback');
      phase='token';
      const credentials=await json('/oauth/token',{method:'POST',
        headers:{'Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams({
          grant_type:'authorization_code',client_id:clientId,code,redirect_uri:localOrigin+'/callback',
          code_verifier:verifier,resource:workerOrigin+'/mcp'}).toString()});
      if(typeof credentials.access_token!=='string' || credentials.token_type?.toLowerCase()!=='bearer')
        throw new Error('Invalid token response');
      const headers={'Content-Type':'application/json',Accept:'application/json, text/event-stream',
        Authorization:'Bearer '+credentials.access_token};
      const rpc=async(id,method,params)=>{
        const data=await json('/mcp',{method:'POST',headers,body:JSON.stringify({jsonrpc:'2.0',id,method,params})});
        if(data.error || data.id!==id || !data.result) throw new Error('Invalid RPC');
        return data.result;
      };
      phase='initialize';
      const init=await rpc(1,'initialize',{protocolVersion:'2025-03-26',capabilities:{},
        clientInfo:{name:'learning-analysis-client-probe',version:'1.0.0'}});
      if(!init.protocolVersion || !init.serverInfo) throw new Error('Invalid initialize');
      headers['MCP-Protocol-Version']=init.protocolVersion;
      phase='initialized';
      const notified=await request('/mcp',{method:'POST',headers,
        body:JSON.stringify({jsonrpc:'2.0',method:'notifications/initialized'})});
      if(notified.status!==202) throw new Error('Invalid notification response');
      phase='tools/list';
      const result=await rpc(2,'tools/list');
      if(!Array.isArray(result.tools) || !result.tools.some(t=>t.name==='read_url')) throw new Error('Missing tool');
      let article;
      if(process.env.PILOT_URL) {
        phase='article';
        const call=await rpc(3,'tools/call',{name:'read_url',arguments:{url:process.env.PILOT_URL}});
        const structured=call.structuredContent;
        if(!structured || typeof structured.status!=='string') throw new Error('Invalid article result');
        article={status:structured.status,error_code:structured.error_code||null,
          characters:typeof structured.content==='string'?structured.content.length:0};
      }
      reply(200,`<!doctype html><meta charset="utf-8"><h1>验证通过</h1><p>OAuth、MCP 初始化和 read_url 工具发现通过；文章调用为 ${article?1:0}。可以关闭此页。</p>`);
      report(JSON.stringify({status:'passed',tokenExchange:true,initialize:true,readUrlDiscovered:true,
        articleCalls:article?1:0,article}));
    } catch {
      reply(502,'Verification failed. Return to Codex for the failed stage.');
      report(JSON.stringify({status:'failed',phase}));
    } finally { finish(); }
  });
  await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(0,'127.0.0.1',resolve);});
  localOrigin='http://127.0.0.1:'+server.address().port;
  try {
    phase='metadata';
    const meta=await json('/.well-known/oauth-authorization-server');
    if(meta.authorization_endpoint!==workerOrigin+'/authorize' || meta.token_endpoint!==workerOrigin+'/oauth/token' ||
      meta.registration_endpoint!==workerOrigin+'/oauth/register') throw new Error('Unexpected endpoints');
    phase='registration';
    const client=await json('/oauth/register',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({client_name:'Reader local verification',redirect_uris:[localOrigin+'/callback'],
        grant_types:['authorization_code'],response_types:['code'],token_endpoint_auth_method:'none'})},201);
    if(typeof client.client_id!=='string') throw new Error('Invalid client');
    clientId=client.client_id;
    const auth=new URL(meta.authorization_endpoint);
    auth.search=new URLSearchParams({response_type:'code',client_id:clientId,redirect_uri:localOrigin+'/callback',
      scope:'articles:read',resource:workerOrigin+'/mcp',state,code_challenge:challenge,code_challenge_method:'S256'}).toString();
    authorizationUrl=auth.href;
    phase='waiting-for-user';
    timer=setTimeout(()=>{report(JSON.stringify({status:'expired',phase}));finish();},timeoutMs);
    return {localOrigin,close:finish};
  } catch {finish();throw new Error('Client probe setup failed at '+phase);}
}

if(process.argv[1] && import.meta.url===pathToFileURL(process.argv[1]).href) {
  try {const probe=await startClientProbe();console.log('OPEN_LOCAL_PAGE '+probe.localOrigin);}
  catch(error) {console.error(error.message);process.exitCode=1;}
}
