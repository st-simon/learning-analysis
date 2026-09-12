import OAuthProvider from '@cloudflare/workers-oauth-provider';
import {WorkerEntrypoint} from 'cloudflare:workers';
import {mcpResponse} from './mcp.mjs';
import {authorize} from './auth.mjs';
export {ArticleQuota} from './quota-object.mjs';

class ReaderAPI extends WorkerEntrypoint {
  async fetch(request) {
    const quota=this.env.ARTICLE_QUOTA.get(this.env.ARTICLE_QUOTA.idFromName('owner'));
    return mcpResponse(request,{ownerId:this.env.OWNER_GITHUB_ID,props:this.ctx.props,quota});
  }
}
let cachedOrigin, provider;
export default {
  async fetch(request,env,ctx) {
    // Fail closed until the operator configures the real canonical origin and identity.
    let origin;
    try { origin=new URL(env.PUBLIC_ORIGIN); } catch { return new Response('Not configured',{status:503}); }
    if (origin.protocol!=='https:' || origin.origin!==env.PUBLIC_ORIGIN ||
      !env.GITHUB_CLIENT_ID || !env.GITHUB_CLIENT_SECRET || !/^\d+$/.test(env.OWNER_GITHUB_ID||''))
      return new Response('Not configured',{status:503});
    const url=new URL(request.url);
    if (url.origin!==env.PUBLIC_ORIGIN) return new Response('Unexpected host',{status:400});
    // Browser form submissions may arrive with a rewritten Origin on workers.dev.
    // Keep the exact-host check above and reject explicit cross-site fetches.
    if (request.headers.get('sec-fetch-site')==='cross-site')
      return new Response('Unexpected origin',{status:403});
    if (url.pathname==='/healthz') return Response.json({status:'alive',reader_verified:false});
    if (!provider || cachedOrigin!==env.PUBLIC_ORIGIN) {
      cachedOrigin=env.PUBLIC_ORIGIN;
      provider=new OAuthProvider({apiRoute:'/mcp',apiHandler:ReaderAPI,
        defaultHandler:{fetch:authorize},authorizeEndpoint:'/authorize',tokenEndpoint:'/oauth/token',
        clientRegistrationEndpoint:'/oauth/register',clientRegistrationTTL:86400,
        scopesSupported:['articles:read'],allowPlainPKCE:false,allowImplicitFlow:false,
        accessTokenTTL:3600,resourceMatchOriginOnly:false,
        resourceMetadata:{resource:env.PUBLIC_ORIGIN+'/mcp',authorization_servers:[env.PUBLIC_ORIGIN],scopes_supported:['articles:read']},
      });
    }
    try { return await provider.fetch(request,env,ctx); }
    catch { return new Response('Request could not be completed',{status:503}); }
  },
};
