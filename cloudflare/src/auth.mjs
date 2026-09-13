import {boundedText} from './reader.mjs';
const cookieName='__Host-reader-flow';
const nonce=()=>crypto.randomUUID()+crypto.randomUUID();
const escapeHtml=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const headers={'Cache-Control':'no-store','Referrer-Policy':'no-referrer','X-Content-Type-Options':'nosniff',
  'Content-Security-Policy':"default-src 'none'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'"};
const bindingOf=request=>request.headers.get('cookie')?.split(';').map(s=>s.trim()).find(s=>s.startsWith(cookieName+'='))?.slice(cookieName.length+1);
const cookie=value=>`${cookieName}=${value}; Path=/; Secure; HttpOnly; SameSite=Lax; Max-Age=600`;
// An external POST redirect is blocked by form-action 'self' in Chrome.
// Keep that policy and let the user continue with a regular GET link instead.
const redirect=(url,binding)=>new Response(`<!doctype html><meta charset="utf-8"><title>继续 GitHub 登录</title><h1>同意已确认</h1><p><a href="${escapeHtml(url)}">继续 GitHub 登录</a></p>`,
  {status:200,headers:{...headers,'Content-Type':'text/html; charset=utf-8',Location:url,'Set-Cookie':cookie(binding)}});
// Fixed public categories only: never include request values, upstream bodies or exceptions.
const problem=(status=400,reason='AUTH_REQUEST_INVALID')=>new Response(`Authorization could not be completed. [${reason}]`,{status,headers});

export async function authorize(request, env, {fetcher=fetch}={}) {
  const url=new URL(request.url);
  const flows=env.ARTICLE_QUOTA.get(env.ARTICLE_QUOTA.idFromName(env.AUTH_STATE_ID||'owner'));
  try {
    if (url.pathname==='/authorize' && request.method==='GET') {
      const auth=await env.OAUTH_PROVIDER.parseAuthRequest(request);
      if (!auth.scope.includes('articles:read') || auth.codeChallengeMethod!=='S256' || !auth.codeChallenge)
        return problem();
      const client=await env.OAUTH_PROVIDER.lookupClient(auth.clientId);
      if (!client) return problem();
      const id=nonce(), binding=nonce();
      if (!await flows.createFlow(id,binding,'consent',{auth})) return problem(429);
      const label=escapeHtml(client.clientName||auth.clientId);
      const destination=escapeHtml(auth.redirectUri);
      return new Response(`<!doctype html><html lang="zh"><meta charset="utf-8"><title>文章读取授权</title><h1>允许读取公开文章？</h1><p>客户端：${label}</p><p>回调地址：${destination}</p><p>仅允许本人使用。文章经 Jina 和 Cloudflare 处理，每天最多10次；不保存正文。</p><form method="post" action="/authorize"><input type="hidden" name="state" value="${id}"><button>同意并使用 GitHub 登录</button></form><p>不同意请关闭本页。</p></html>`,
        {headers:{...headers,'Content-Type':'text/html; charset=utf-8','Set-Cookie':cookie(binding)}});
    }
    if (url.pathname==='/authorize' && request.method==='POST') {
      if (request.headers.get('sec-fetch-site')==='cross-site') return problem(403,'CONSENT_CROSS_SITE');
      const form=new URLSearchParams(await boundedText(request,32768));
      const binding=bindingOf(request), id=form.get('state');
      if (!binding) return problem(400,'CONSENT_COOKIE_MISSING');
      if (!id) return problem(400,'CONSENT_STATE_MISSING');
      const flow=await flows.takeFlow(id,binding,'consent');
      if (!flow) return problem(400,'CONSENT_STATE_UNAVAILABLE');
      const state=nonce(), verifier=nonce();
      const digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(verifier));
      const challenge=btoa(String.fromCharCode(...new Uint8Array(digest))).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
      if (!await flows.createFlow(state,binding,'github',{...flow,verifier})) return problem(429,'AUTH_CAPACITY');
      const github=new URL('https://github.com/login/oauth/authorize');
      github.search=new URLSearchParams({client_id:env.GITHUB_CLIENT_ID,redirect_uri:env.PUBLIC_ORIGIN+'/callback',
        scope:'read:user',state,code_challenge:challenge,code_challenge_method:'S256'}).toString();
      return redirect(github.href,binding);
    }
    if (url.pathname==='/callback' && request.method==='GET') {
      const binding=bindingOf(request), state=url.searchParams.get('state'), code=url.searchParams.get('code');
      if (!binding || !state || !code || code.length>2048) return problem();
      const flow=await flows.takeFlow(state,binding,'github');
      if (!flow) return problem();
      const exchange=await fetcher('https://github.com/login/oauth/access_token',{
        method:'POST',redirect:'manual',signal:AbortSignal.timeout(10000),
        headers:{Accept:'application/json','Content-Type':'application/x-www-form-urlencoded'},
        body:new URLSearchParams({client_id:env.GITHUB_CLIENT_ID,client_secret:env.GITHUB_CLIENT_SECRET,
          code,redirect_uri:env.PUBLIC_ORIGIN+'/callback',code_verifier:flow.verifier}).toString()});
      if (!exchange.ok) return problem(502);
      const token=JSON.parse(await boundedText(exchange,32768));
      if (typeof token.access_token!=='string') return problem(502);
      const identity=await fetcher('https://api.github.com/user', {redirect:'manual',signal:AbortSignal.timeout(10000),
        headers:{Authorization:'Bearer '+token.access_token,Accept:'application/vnd.github+json','User-Agent':'learning-analysis'}});
      if (!identity.ok) return problem(502);
      const user=JSON.parse(await boundedText(identity,32768));
      if (String(user.id)!==env.OWNER_GITHUB_ID) return problem(403);
      const {redirectTo}=await env.OAUTH_PROVIDER.completeAuthorization({request:flow.auth,
        userId:String(user.id),metadata:{label:'Personal article reader'},scope:['articles:read'],
        props:{userId:String(user.id),scopes:['articles:read']}});
      // Never persist or forward the upstream GitHub access token to an MCP client.
      return new Response(null,{status:302,headers:{...headers,Location:redirectTo,
        'Set-Cookie':`${cookieName}=; Path=/; Secure; HttpOnly; SameSite=Lax; Max-Age=0`}});
    }
    return problem(404);
  } catch { return problem(400,'AUTH_PROCESSING_FAILED'); }
}
