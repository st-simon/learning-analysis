(function installCaptureFlow(globalObject) {
  "use strict";

  const PENDING_ENDPOINT = "http://127.0.0.1:18431/pending";
  const DEFAULT_TIMEOUT_MS = 20_000;
  const DEFAULT_POLL_MS = 250;

  class CaptureFlowError extends Error {
    constructor(code) {
      super(code);
      this.name = "CaptureFlowError";
      this.code = code;
    }
  }

  function normalizeSourceUrl(value) {
    let sourceUrl;
    try {
      sourceUrl = new URL(value);
    } catch (_error) {
      throw new CaptureFlowError("URL");
    }
    if (
      sourceUrl.protocol !== "https:" ||
      sourceUrl.hostname !== "mp.weixin.qq.com" ||
      !sourceUrl.pathname.startsWith("/s/") ||
      sourceUrl.username ||
      sourceUrl.password ||
      (sourceUrl.port && sourceUrl.port !== "443")
    ) {
      throw new CaptureFlowError("URL");
    }
    sourceUrl.hash = "";
    return sourceUrl.toString();
  }

  async function responseStatus(response) {
    try {
      return (await response.json()).status;
    } catch (_error) {
      throw new CaptureFlowError("SEND");
    }
  }

  async function waitForPending(sourceUrl, options) {
    const {
      token,
      extensionId,
      fetchImpl = globalObject.fetch.bind(globalObject),
      sleepFn = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds)),
      nowFn = () => Date.now(),
      timeoutMs = DEFAULT_TIMEOUT_MS,
      pollMs = DEFAULT_POLL_MS,
    } = options || {};
    if (!token || !extensionId) throw new CaptureFlowError("AUTH");
    if (!(timeoutMs > 0) || !(pollMs > 0) || pollMs > timeoutMs) {
      throw new CaptureFlowError("SEND");
    }

    const normalizedUrl = normalizeSourceUrl(sourceUrl);
    const endpoint = new URL(PENDING_ENDPOINT);
    endpoint.searchParams.set("url", normalizedUrl);
    const startedAt = nowFn();

    while (nowFn() - startedAt < timeoutMs) {
      let response;
      try {
        response = await fetchImpl(endpoint.toString(), {
          method: "GET",
          headers: {
            Authorization: `Bearer ${token}`,
            "X-Learning-Analysis-Extension-Id": extensionId,
            Accept: "application/json",
          },
          cache: "no-store",
        });
      } catch (_error) {
        throw new CaptureFlowError("SEND");
      }

      if (response.status === 200) {
        if (await responseStatus(response) !== "PENDING_READY") {
          throw new CaptureFlowError("SEND");
        }
        return normalizedUrl;
      }
      if (response.status === 401 || response.status === 403) {
        throw new CaptureFlowError("AUTH");
      }
      if (response.status === 400) {
        throw new CaptureFlowError("URL");
      }
      if (response.status !== 404 || await responseStatus(response) !== "NO_PENDING") {
        throw new CaptureFlowError("SEND");
      }

      const remaining = timeoutMs - (nowFn() - startedAt);
      if (remaining <= 0) break;
      await sleepFn(Math.min(pollMs, remaining));
    }
    throw new CaptureFlowError("TIME");
  }

  async function runCaptureFlow(sourceUrl, options) {
    const {extractFn, submitFn} = options || {};
    if (typeof extractFn !== "function" || typeof submitFn !== "function") {
      throw new CaptureFlowError("SEND");
    }
    const normalizedUrl = await waitForPending(sourceUrl, options);
    let capture;
    try {
      capture = await extractFn();
    } catch (_error) {
      throw new CaptureFlowError("PAGE");
    }
    if (
      !capture ||
      normalizeSourceUrl(capture.source_url) !== normalizedUrl
    ) {
      throw new CaptureFlowError("PAGE");
    }
    try {
      await submitFn(capture);
    } catch (error) {
      if (error instanceof CaptureFlowError) throw error;
      throw new CaptureFlowError("SEND");
    }
    return capture;
  }

  const api = {
    CaptureFlowError,
    normalizeSourceUrl,
    runCaptureFlow,
    waitForPending,
  };
  globalObject.CaptureFlow = api;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
})(globalThis);
