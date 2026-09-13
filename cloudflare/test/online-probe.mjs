import assert from 'node:assert/strict';

const origin = (process.env.ONLINE_ORIGIN ||
  'https://learning-analysis-validation.learning-analysis-worker.workers.dev').replace(/\/$/, '');
const jsonHeaders = {'Content-Type':'application/json'};

async function request(path, options={}) {
  return fetch(origin + path, {...options, redirect:'manual'});
}

function cookieValue(response) {
  const value=response.headers.get('set-cookie') || '';
  const match=value.match(/__Host-reader-flow=([^;]+)/);
  assert.ok(match, 'consent response must set the browser flow cookie');
  return match[1];
}

const health=await request('/healthz');
assert.equal(health.status,200,'healthz');
const healthBody=await health.json();
assert.equal(healthBody.status,'alive');

const anonymous=await request('/mcp',{method:'POST',headers:jsonHeaders,
  body:JSON.stringify({jsonrpc:'2.0',id:1,method:'tools/list'})});
assert.equal(anonymous.status,401,'anonymous MCP must be rejected');

const metadata=await request('/.well-known/oauth-protected-resource');
assert.equal(metadata.status,200,'OAuth metadata');
const metadataBody=await metadata.json();
assert.equal(metadataBody.resource,origin+'/mcp');
assert.deepEqual(metadataBody.scopes_supported,['articles:read']);

const registration=await request('/oauth/register',{method:'POST',headers:jsonHeaders,
  body:JSON.stringify({client_name:'online-probe',redirect_uris:['https://example.com/callback'],
    grant_types:['authorization_code'],response_types:['code'],token_endpoint_auth_method:'none'})});
assert.equal(registration.status,201,'dynamic client registration');
const client=await registration.json();
assert.equal(typeof client.client_id,'string');

const authorize=new URL('/authorize',origin);
const verifier='probe-verifier-012345678901234567890123456789012345678901234567890123';
const challenge=Buffer.from(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(verifier))).toString('base64url');
authorize.search=new URLSearchParams({response_type:'code',client_id:client.client_id,
  redirect_uri:'https://example.com/callback',scope:'articles:read',resource:origin+'/mcp',state:'online-probe',
  code_challenge:challenge,code_challenge_method:'S256'}).toString();
const consent=await fetch(authorize,{redirect:'manual',signal:AbortSignal.timeout(15000),
  headers:{'Sec-Fetch-Site':'cross-site','Sec-Fetch-Dest':'document'}});
const consentText=await consent.text();
assert.equal(consent.status,200,`authorization consent page (${consentText.slice(0,120)})`);
const state=consentText.match(/name="state" value="([^"]+)"/)?.[1];
assert.ok(state,'consent page must contain server-side state');
const flowCookie=cookieValue(consent);

const submit=await request('/authorize',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded',
  Cookie:`__Host-reader-flow=${flowCookie}`},body:new URLSearchParams({state}).toString()});
assert.equal(submit.status,200,'consent submit must offer a GET continuation');
assert.match(await submit.text(),/继续 GitHub 登录/);
const location=new URL(submit.headers.get('location'));
assert.equal(location.origin,'https://github.com');
assert.equal(location.pathname,'/login/oauth/authorize');
assert.equal(location.searchParams.get('redirect_uri'),origin+'/callback');

console.log(JSON.stringify({origin,health:health.status,anonymousMcp:anonymous.status,
  metadata:metadata.status,registration:registration.status,consent:consent.status,
  consentSubmit:submit.status,redirectHost:location.host}));
