import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readArticle, executeRead, validateUrl, boundedText} from '../src/reader.mjs';

const url = 'https://mp.weixin.qq.com/s/test';
const article = {code: 200, data: {title: 'Article', url, content: '正文\n\n![图](https://example.com/photo.png)\n\n|A|B|\n|-|-|\n|1|2|'}};
const reply = value => new Response(JSON.stringify(value));
test('URL boundary rejects scheme, port, userinfo, suffix hosts and control characters', () => {
  for (const target of ['http://example.com', 'https://127.0.0.1', 'https://example.com.evil.test',
    'https://x@example.com', 'https://example.com:444', 'https://example.com/#x',
    'https://example.com/\n', 'https://example.com\\@evil.test']) assert.throws(() => validateUrl(target));
  assert.equal(validateUrl('https://example.com'), 'https://example.com/');
});
test('fixed upstream, DNT, no credentials, and image/table preservation', async () => {
  const result = await readArticle(url, {fetcher: async (destination, options) => {
    assert.equal(destination, 'https://r.jina.ai/');
    assert.equal(options.redirect, 'manual');
    assert.equal(options.headers.DNT, '1');
    assert.equal(options.headers.Authorization, undefined);
    assert.deepEqual(JSON.parse(options.body), {url, respondWith: 'markdown', assertStatusCode: 200});
    return reply(article);
  }});
  assert.equal(result.markdown, article.data.content);
  assert.equal(result.saved_file, null);
});
test('HTTP restrictions and redirects never retry', async () => {
  for (const [status, code] of [[403,'ACCESS_RESTRICTED'],[429,'UPSTREAM_RATE_LIMIT'],[302,'UPSTREAM_REDIRECT'],[503,'UPSTREAM_ERROR']]) {
    let calls = 0;
    await assert.rejects(readArticle(url, {fetcher: async () => {calls++; return new Response('', {status});}}), {code});
    assert.equal(calls, 1);
  }
});
test('empty, malformed, unsafe-source and challenge responses fail explicitly', async () => {
  for (const [body, code] of [[{},'INVALID_RESPONSE'], [{data:{...article.data,content:''}},'EMPTY_ARTICLE'],
    [{data:{...article.data,url:'http://169.254.169.254'}},'UNSAFE_SOURCE'],
    [{data:{...article.data,content:'请完成验证码后继续'}},'ACCESS_RESTRICTED']]) {
    await assert.rejects(readArticle(url, {fetcher:async()=>reply(body)}), {code});
  }
});
test('chunked oversized response is cancelled', async () => {
  let cancelled = false;
  const stream = new ReadableStream({pull(c) {c.enqueue(new Uint8Array(6));}, cancel(){cancelled=true;}});
  await assert.rejects(boundedText(new Response(stream), 10), {code:'RESPONSE_TOO_LARGE'});
  assert.equal(cancelled, true);
});
test('timeout aborts a stalled upstream exactly once', async () => {
  let signal, calls = 0;
  await assert.rejects(readArticle(url, {timeoutMs:10, fetcher:async(_, options)=>{
    calls++; signal=options.signal; return new Promise(()=>{});
  }}), {code:'READ_TIMEOUT'});
  assert.equal(signal.aborted, true);
  assert.equal(calls, 1);
});
test('quota rejection and quota failure prevent upstream reads', async () => {
  let calls=0;
  const fetcher=async()=>{calls++; return reply(article);};
  for (const acquire of [async()=>({allowed:false,code:'DAILY_LIMIT'}),async()=>{throw Error('secret');}]) {
    const result=await executeRead(url,{quota:{acquire},fetcher});
    assert.equal(result.status,'error');
    assert.equal(JSON.stringify(result).includes('secret'),false);
  }
  assert.equal(calls,0);
});
test('failed read consumes attempt and releases lease without retry', async () => {
  let attempts=0, released=0;
  const quota={async acquire(){attempts++;return {allowed:true};},async release(){released++;}};
  const result=await executeRead(url,{quota,fetcher:async()=>new Response('',{status:403})});
  assert.equal(result.error_code,'ACCESS_RESTRICTED');
  assert.equal(attempts,1); assert.equal(released,1);
});
