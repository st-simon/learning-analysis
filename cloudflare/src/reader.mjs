export const MAX_RESPONSE = 4_000_000;
export const ALLOWED_HOSTS = new Set(['example.com', 'www.iana.org', 'mp.weixin.qq.com']);
export class ReadError extends Error {
  constructor(code) { super(code); this.code = code; }
}

export function validateUrl(value) {
  if (typeof value !== 'string' || value.length > 8192 || /[\s\\\u0000-\u001f\u007f]/u.test(value))
    throw new ReadError('INVALID_URL');
  let url;
  try { url = new URL(value); } catch { throw new ReadError('INVALID_URL'); }
  if (url.protocol !== 'https:' || url.username || url.password || url.port || url.hash ||
      !ALLOWED_HOSTS.has(url.hostname)) throw new ReadError('INVALID_URL');
  return url.href;
}

export async function boundedText(response, max = MAX_RESPONSE) {
  const length = response.headers.get('content-length');
  if (length && Number(length) > max) {
    await response.body?.cancel();
    throw new ReadError('RESPONSE_TOO_LARGE');
  }
  if (!response.body) throw new ReadError('EMPTY_ARTICLE');
  const reader = response.body.getReader();
  const chunks = [];
  let size = 0;
  try {
    for (;;) {
      const {done, value} = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > max) { await reader.cancel(); throw new ReadError('RESPONSE_TOO_LARGE'); }
      chunks.push(value);
    }
  } finally { reader.releaseLock(); }
  const bytes = new Uint8Array(size);
  let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
  return new TextDecoder('utf-8', {fatal: true}).decode(bytes);
}

export async function readArticle(input, {fetcher = fetch, timeoutMs = 45_000} = {}) {
  const url = validateUrl(input);
  const controller = new AbortController();
  let timer;
  const timedOut = new Promise((_, reject) => {
    timer = setTimeout(() => { controller.abort(); reject(new ReadError('READ_TIMEOUT')); }, timeoutMs);
  });
  const operation = async () => {
    // Fixed upstream and headers: no tokens, cookies, proxies or paid model options.
    const response = await fetcher('https://r.jina.ai/', {
      method: 'POST', redirect: 'manual', signal: controller.signal,
      headers: {'Content-Type': 'application/json', Accept: 'application/json', DNT: '1'},
      body: JSON.stringify({url, respondWith: 'markdown', assertStatusCode: 200}),
    });
    if ([401, 403].includes(response.status)) throw new ReadError('ACCESS_RESTRICTED');
    if (response.status === 429) throw new ReadError('UPSTREAM_RATE_LIMIT');
    if (response.status >= 300 && response.status < 400) throw new ReadError('UPSTREAM_REDIRECT');
    if (!response.ok) throw new ReadError('UPSTREAM_ERROR');
    let payload;
    try { payload = JSON.parse(await boundedText(response)); }
    catch (error) { if (error instanceof ReadError) throw error; throw new ReadError('INVALID_RESPONSE'); }
    if (payload?.code !== undefined && payload.code !== 200) throw new ReadError('UPSTREAM_ERROR');
    const data = payload?.data;
    if (!data || typeof data !== 'object' || Array.isArray(data)) throw new ReadError('INVALID_RESPONSE');
    const content = data.content;
    if (typeof content !== 'string' || !content.trim()) throw new ReadError('EMPTY_ARTICLE');
    if (typeof data.title !== 'string' || typeof data.url !== 'string') throw new ReadError('INVALID_RESPONSE');
    const warning = data.warning ?? payload.warning ?? '';
    if (typeof warning !== 'string') throw new ReadError('INVALID_RESPONSE');
    const restricted = /captcha|验证码|访问受限|环境异常|access denied|verify you are human/i;
    if (restricted.test(data.title + warning) || (content.length < 2000 && restricted.test(content)))
      throw new ReadError('ACCESS_RESTRICTED');
    let source;
    try { source = validateUrl(data.url); } catch { throw new ReadError('UNSAFE_SOURCE'); }
    return {status: 'ok', title: data.title, source_url: source, markdown: content,
      characters: Array.from(content).length, saved_file: null, archive_id: null, warnings: warning,
      limitations: 'Images are references, not OCR. Extraction may omit inaccessible content.'};
  };
  try { return await Promise.race([operation(), timedOut]); }
  catch (error) { throw error instanceof ReadError ? error : new ReadError('UPSTREAM_UNAVAILABLE'); }
  finally { clearTimeout(timer); controller.abort(); }
}

export async function executeRead(input, {quota, fetcher, requestId = crypto.randomUUID(), timeoutMs} = {}) {
  try { validateUrl(input); }
  catch { return {status: 'error', error_code: 'INVALID_URL', request_id: requestId}; }
  let lease;
  try {
    lease = await quota.acquire(requestId);
    if (!lease.allowed) return {status: 'error', error_code: lease.code, request_id: requestId,
      message: 'Request not queued or retried. Daily limit resets at 00:00 UTC.'};
    return {...await readArticle(input, {fetcher, timeoutMs}), request_id: requestId};
  } catch (error) {
    return {status: 'error', error_code: error instanceof ReadError ? error.code : 'QUOTA_UNAVAILABLE',
      request_id: requestId, message: 'Article could not be read. No automatic retry.'};
  } finally {
    if (lease?.allowed) {
      // An abandoned lease expires; a release error must not replay an article.
      try { await quota.release(requestId); } catch { /* lease expires after 60 seconds */ }
    }
  }
}
