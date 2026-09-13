import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {startClientProbe} from './client-probe.mjs';

test('loopback client binds state and PKCE, initializes MCP, discovers tools without article calls',async()=>{
  const origin='https://learning-analysis-validation.learning-analysis-worker.workers.dev';
  const logs=[],methods=[];let redirect,challenge,tokenCalls=0;
  const probe=await startClientProbe({report:line=>logs.push(line),fetcher:async(url,options)=>{
    assert.equal(options.redirect,'manual');assert.ok(options.signal);
    switch(new URL(url).pathname) {
      case '/.well-known/oauth-authorization-server':return Response.json({authorization_endpoint:origin+'/authorize',
        token_endpoint:origin+'/oauth/token',registration_endpoint:origin+'/oauth/register'});
      case '/oauth/register':redirect=JSON.parse(options.body).redirect_uris[0];return Response.json({client_id:'fixture'},{status:201});
      case '/oauth/token': {
        tokenCalls++;const form=new URLSearchParams(options.body);
        assert.equal(form.get('redirect_uri'),redirect);
        assert.equal(createHash('sha256').update(form.get('code_verifier')).digest('base64url'),challenge);
        return Response.json({access_token:'private-fixture-token',token_type:'Bearer'});
      }
      case '/mcp': {
        assert.equal(options.headers.Authorization,'Bearer private-fixture-token');
        const body=JSON.parse(options.body);methods.push(body.method);
        if(body.method==='notifications/initialized')return new Response(null,{status:202});
        const result=body.method==='initialize'?{protocolVersion:'2025-03-26',serverInfo:{name:'fixture'}}:{tools:[{name:'read_url'}]};
        return Response.json({jsonrpc:'2.0',id:body.id,result});
      }
      default:throw new Error('Unexpected request');
    }
  }});
  try {
    const page=await (await fetch(probe.localOrigin)).text();
    const auth=new URL(/href="([^"]+)"/.exec(page)[1].replaceAll('&amp;','&'));
    challenge=auth.searchParams.get('code_challenge');
    assert.equal((await fetch(redirect+'?state=wrong&code=fixture')).status,400);
    assert.equal(tokenCalls,0);
    const callback=new URL(redirect);callback.search=new URLSearchParams({state:auth.searchParams.get('state'),code:'fixture-code'});
    assert.equal((await fetch(callback)).status,200);
    assert.deepEqual(methods,['initialize','notifications/initialized','tools/list']);
    assert.equal(tokenCalls,1);assert.equal(JSON.parse(logs[0]).status,'passed');
    assert.ok(!logs.join('').includes('private-fixture-token'));
    assert.ok(!logs.join('').includes('fixture-code'));
  } finally {probe.close();}
});
