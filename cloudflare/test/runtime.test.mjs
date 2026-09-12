import {test} from 'node:test';
import assert from 'node:assert/strict';
import {Miniflare, convertV4MiniflareOptions, Response as MFResponse} from 'miniflare';
import {mkdtemp, rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';

test('actual Workers runtime: OAuth, private MCP, quota persistence and no anonymous upstream', {timeout:45000}, async()=>{
  const root=await mkdtemp(join(tmpdir(),'reader-worker-test-'));
  const origin='https://reader.example'; let calls=0;
  const options=convertV4MiniflareOptions({modules:true,scriptPath:'dist/index.js',
    compatibilityDate:'2026-09-11',compatibilityFlags:['nodejs_compat','global_fetch_strictly_public'],
    cf:false,kvNamespaces:['OAUTH_KV'],resourcePersistencePath:root,
    durableObjects:{ARTICLE_QUOTA:{className:'ArticleQuota',useSQLite:true}},
    bindings:{PUBLIC_ORIGIN:origin,OWNER_GITHUB_ID:'123',GITHUB_CLIENT_ID:'test-client',GITHUB_CLIENT_SECRET:'test-only-secret'},
    outboundService:async request=>{
      const url=new URL(request.url);
      if(url.href==='https://github.com/login/oauth/access_token') return new MFResponse(JSON.stringify({access_token:'mock-token'}));
      if(url.href==='https://api.github.com/user') return new MFResponse(JSON.stringify({id:123}));
      if(url.origin==='https://r.jina.ai'){
        calls++; assert.equal(request.headers.get('dnt'),'1');assert.equal(request.headers.get('authorization'),null);
        return new MFResponse(JSON.stringify({code:200,data:{title:'Test article',url:'https://example.com/',content:'Test正文 ![photo](https://example.com/photo.png)'}}));
      }
      throw Error('Unexpected outbound request: '+url.origin);
    }});
  let mf;
  const jsonHeaders={'Content-Type':'application/json',Accept:'application/json, text/event-stream'};
  try {
    mf=new Miniflare(options);
    const anonymous=await mf.dispatchFetch(origin+'/mcp',{method:'POST',headers:jsonHeaders,body:'{}'});
    assert.equal(anonymous.status,401);assert.equal(calls,0);
    const forged=await mf.dispatchFetch(origin+'/mcp',{method:'POST',headers:{...jsonHeaders,Authorization:'Bearer forged'},body:'{}'});
    assert.equal(forged.status,401);assert.equal(calls,0);
    const foreign=await mf.dispatchFetch(origin+'/mcp',{method:'POST',headers:{...jsonHeaders,'Sec-Fetch-Site':'cross-site'},body:'{}'});
    assert.equal(foreign.status,403);assert.equal(calls,0);
    const metadata=await mf.dispatchFetch(origin+'/.well-known/oauth-protected-resource');
    assert.equal((await metadata.json()).resource,origin+'/mcp');
    const reg=await mf.dispatchFetch(origin+'/oauth/register',{method:'POST',headers:jsonHeaders,body:JSON.stringify({
      client_name:'Test client',redirect_uris:['https://client.example/callback'],token_endpoint_auth_method:'none',
      grant_types:['authorization_code','refresh_token'],response_types:['code']})});
    assert.equal(reg.status,201); const client=await reg.json();
    const verifier='a'.repeat(64);
    const challenge=Buffer.from(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(verifier))).toString('base64url');
    const params=new URLSearchParams({client_id:client.client_id,redirect_uri:'https://client.example/callback',response_type:'code',
      scope:'articles:read',state:'client-state',resource:origin+'/mcp',code_challenge:challenge,code_challenge_method:'S256'});
    const consent=await mf.dispatchFetch(origin+'/authorize?'+params);
    assert.equal(consent.status,200);
    const cookie=consent.headers.get('set-cookie').split(';')[0];
    const state=/name="state" value="([^"]+)"/.exec(await consent.text())[1];
    const login=await mf.dispatchFetch(origin+'/authorize',{method:'POST',redirect:'manual',headers:{cookie,origin},body:new URLSearchParams({state}).toString()});
    assert.equal(login.status,302);
    const github=new URL(login.headers.get('location'));
    const callback=await mf.dispatchFetch(origin+'/callback?'+new URLSearchParams({state:github.searchParams.get('state'),code:'mock-code'}),{redirect:'manual',headers:{cookie}});
    assert.equal(callback.status,302);
    const returned=new URL(callback.headers.get('location'));
    const token=await mf.dispatchFetch(origin+'/oauth/token',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},
      body:new URLSearchParams({grant_type:'authorization_code',client_id:client.client_id,code:returned.searchParams.get('code'),
        redirect_uri:'https://client.example/callback',code_verifier:verifier,resource:origin+'/mcp'}).toString()});
    assert.equal(token.status,200);const credentials=await token.json();
    const headers={...jsonHeaders,Authorization:'Bearer '+credentials.access_token};
    const list=await mf.dispatchFetch(origin+'/mcp',{method:'POST',headers,body:JSON.stringify({jsonrpc:'2.0',id:1,method:'tools/list'})});
    assert.equal((await list.json()).result.tools[0].name,'read_url');
    const read=()=>mf.dispatchFetch(origin+'/mcp',{method:'POST',headers,body:JSON.stringify({jsonrpc:'2.0',id:2,method:'tools/call',params:{name:'read_url',arguments:{url:'https://example.com'}}})});
    for(let i=0;i<10;i++) assert.equal((await (await read()).json()).result.structuredContent.status,'ok');
    assert.equal(calls,10);
    await mf.dispose();mf=new Miniflare(options);
    const eleventh=await (await read()).json();
    assert.equal(eleventh.result.structuredContent.error_code,'DAILY_LIMIT');assert.equal(calls,10);
    const ns=await mf.getDurableObjectNamespace('ARTICLE_QUOTA');
    const fresh=ns.get(ns.idFromName('parallel-test'));
    const concurrent=await Promise.all(Array.from({length:5},(_,i)=>fresh.acquire(String(i))));
    assert.equal(concurrent.filter(x=>x.allowed).length,1);
  } finally { await mf?.dispose();await rm(root,{recursive:true,force:true}); }
});
