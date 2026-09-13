import {test} from 'node:test';
import assert from 'node:assert/strict';
import {authorize} from '../src/auth.mjs';
function fixture() {
  const records=new Map(); let granted;
  const flows={async createFlow(id,binding,phase,data){records.set(id,{binding,phase,data});return true;},
    async takeFlow(id,binding,phase){const r=records.get(id);if(r?.binding!==binding||r?.phase!==phase)return null;records.delete(id);return r.data;}};
  return {env:{PUBLIC_ORIGIN:'https://reader.example',OWNER_GITHUB_ID:'123',GITHUB_CLIENT_ID:'test-client',GITHUB_CLIENT_SECRET:'test-only-secret',
    ARTICLE_QUOTA:{idFromName:()=>'',get:()=>flows},OAUTH_PROVIDER:{
      parseAuthRequest:async()=>({clientId:'client',scope:['articles:read'],redirectUri:'https://client.example/callback',codeChallenge:'abc',codeChallengeMethod:'S256'}),
      lookupClient:async()=>({clientName:'<script>client</script>'}),
      completeAuthorization:async(args)=>{granted=args;return {redirectTo:'https://client.example/callback?code=test'};},
    }}, getGranted:()=>granted};
}
async function consent(env) {
  const response=await authorize(new Request(env.PUBLIC_ORIGIN+'/authorize'),env);
  const cookie=response.headers.get('set-cookie').split(';')[0];
  const html=await response.text();
  assert(!html.includes('<script>')); assert(html.includes('&lt;script&gt;'));
  return {cookie,state:/name="state" value="([^"]+)"/.exec(html)[1]};
}
test('consent is bound to browser, same origin and one-time server state',async()=>{
  const {env}=fixture();const {cookie,state}=await consent(env);
  const post=(cookie,headers)=>new Request(env.PUBLIC_ORIGIN+'/authorize',{method:'POST',headers,body:new URLSearchParams({state})});
  assert.equal((await authorize(post(cookie,{cookie,'Sec-Fetch-Site':'cross-site'}),env)).status,403);
  assert.equal((await authorize(post('bad',{cookie:'bad'}),env)).status,400);
  assert.equal((await authorize(post(cookie,{cookie}),env)).status,200);
  assert.equal((await authorize(post(cookie,{cookie}),env)).status,400);
});
test('callback requires owner identity and never stores GitHub access token in grant',async()=>{
  for(const userId of [123,999]){
    const {env,getGranted}=fixture();const {cookie,state}=await consent(env);
    const response=await authorize(new Request(env.PUBLIC_ORIGIN+'/authorize',{method:'POST',headers:{cookie,origin:env.PUBLIC_ORIGIN},body:new URLSearchParams({state})}),env);
    const github=new URL(response.headers.get('location'));
    assert.equal(github.origin,'https://github.com');assert.equal(github.searchParams.get('scope'),'read:user');
    assert.equal(github.searchParams.get('code_challenge_method'),'S256');
    let calls=0;
    const fetcher=async(destination)=>{calls++;return Response.json(destination.endsWith('access_token')?{access_token:'upstream-secret'}:{id:userId});};
    const callback=new Request(env.PUBLIC_ORIGIN+'/callback?'+new URLSearchParams({state:github.searchParams.get('state'),code:'test'}),{headers:{cookie}});
    assert.equal((await authorize(callback,env,{fetcher})).status,userId===123?302:403);
    assert.equal(calls,2);
    assert(!JSON.stringify(getGranted()||{}).includes('upstream-secret'));
    assert.equal((await authorize(callback,env,{fetcher})).status,400);
    assert.equal(calls,2);
  }
});

test('consent failure categories are fixed and never echo request secrets',async()=>{
  const {env}=fixture();const {cookie,state}=await consent(env);
  const post=(headers,body)=>authorize(new Request(env.PUBLIC_ORIGIN+'/authorize',{
    method:'POST',headers,body:new URLSearchParams(body)}),env);
  const missingCookie=await post({}, {state});
  assert.match(await missingCookie.text(),/CONSENT_COOKIE_MISSING/);
  const missingState=await post({cookie},{});
  assert.match(await missingState.text(),/CONSENT_STATE_MISSING/);
  const unknown=await post({cookie},{state:'private-state-value'});
  const text=await unknown.text();
  assert.match(text,/CONSENT_STATE_UNAVAILABLE/);
  assert.ok(!text.includes('private-state-value'));assert.ok(!text.includes(cookie));
  const accepted=await post({cookie},{state});
  assert.equal(accepted.status,200);
  assert.match(accepted.headers.get('Content-Security-Policy'),/form-action 'self';/);
  const github=accepted.headers.get('Location');
  assert.equal(new URL(github).origin,'https://github.com');
  assert.ok((await accepted.text()).includes(github.replaceAll('&','&amp;')));
  assert.match(await (await post({cookie},{state})).text(),/CONSENT_STATE_UNAVAILABLE/);
});
