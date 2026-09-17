const assert = require("node:assert/strict");
const test = require("node:test");

const {
  CaptureFlowError,
  normalizeSourceUrl,
  runCaptureFlow,
  waitForPending,
} = require("./capture_flow.js");

function response(status, payload) {
  return {
    ok: status >= 200 && status < 300,
    status,
    async json() {
      return payload;
    },
  };
}

test("normalizes only supported WeChat article URLs", () => {
  assert.equal(
    normalizeSourceUrl("https://mp.weixin.qq.com/s/article-id#fragment"),
    "https://mp.weixin.qq.com/s/article-id",
  );
  assert.throws(
    () => normalizeSourceUrl("https://example.com/s/article-id"),
    (error) => error instanceof CaptureFlowError && error.code === "URL",
  );
});

test("an early click waits for pending readiness without sending article content", async () => {
  const requests = [];
  const replies = [
    response(404, {status: "NO_PENDING"}),
    response(404, {status: "NO_PENDING"}),
    response(200, {status: "PENDING_READY"}),
  ];
  let now = 0;

  await waitForPending("https://mp.weixin.qq.com/s/article-id", {
    token: "test-token",
    extensionId: "abcdefghijklmnopabcdefghijklmnop",
    timeoutMs: 2000,
    pollMs: 250,
    nowFn: () => now,
    sleepFn: async (milliseconds) => {
      now += milliseconds;
    },
    fetchImpl: async (url, options) => {
      requests.push({url, options});
      return replies.shift();
    },
  });

  assert.equal(requests.length, 3);
  for (const request of requests) {
    assert.equal(request.options.method, "GET");
    assert.equal(request.options.body, undefined);
    assert.equal(request.options.headers.Authorization, "Bearer test-token");
    assert.equal(
      request.options.headers["X-Learning-Analysis-Extension-Id"],
      "abcdefghijklmnopabcdefghijklmnop",
    );
    assert.match(request.url, /^http:\/\/127\.0\.0\.1:18431\/pending\?url=/);
  }
});

test("a late click proceeds immediately when pending already exists", async () => {
  let sleeps = 0;
  await waitForPending("https://mp.weixin.qq.com/s/article-id", {
    token: "test-token",
    extensionId: "abcdefghijklmnopabcdefghijklmnop",
    fetchImpl: async () => response(200, {status: "PENDING_READY"}),
    sleepFn: async () => {
      sleeps += 1;
    },
  });
  assert.equal(sleeps, 0);
});

test("waiting is bounded and reports a stage-specific timeout", async () => {
  let now = 0;
  await assert.rejects(
    waitForPending("https://mp.weixin.qq.com/s/article-id", {
      token: "test-token",
      extensionId: "abcdefghijklmnopabcdefghijklmnop",
      timeoutMs: 500,
      pollMs: 250,
      nowFn: () => now,
      sleepFn: async (milliseconds) => {
        now += milliseconds;
      },
      fetchImpl: async () => response(404, {status: "NO_PENDING"}),
    }),
    (error) => error instanceof CaptureFlowError && error.code === "TIME",
  );
});

test("authentication failures are not collapsed into a generic error", async () => {
  await assert.rejects(
    waitForPending("https://mp.weixin.qq.com/s/article-id", {
      token: "wrong-token",
      extensionId: "abcdefghijklmnopabcdefghijklmnop",
      fetchImpl: async () => response(401, {status: "error"}),
    }),
    (error) => error instanceof CaptureFlowError && error.code === "AUTH",
  );
});

test("the article is extracted and submitted exactly once after pending is ready", async () => {
  const events = [];
  const replies = [
    response(404, {status: "NO_PENDING"}),
    response(200, {status: "PENDING_READY"}),
  ];
  let now = 0;

  await runCaptureFlow("https://mp.weixin.qq.com/s/article-id", {
    token: "test-token",
    extensionId: "abcdefghijklmnopabcdefghijklmnop",
    nowFn: () => now,
    sleepFn: async (milliseconds) => {
      now += milliseconds;
    },
    fetchImpl: async () => {
      events.push("pending");
      return replies.shift();
    },
    extractFn: async () => {
      events.push("extract");
      return {
        source_url: "https://mp.weixin.qq.com/s/article-id",
        title: "A",
        markdown: "body",
        source_channel: "rendered_dom",
      };
    },
    submitFn: async () => {
      events.push("submit");
    },
  });

  assert.deepEqual(events, ["pending", "pending", "extract", "submit"]);
});
