# Learning Analysis Capture

Chrome Manifest V3 source for the local Learning Analysis capture extension. A
user toolbar click grants `activeTab` access to the current page, extracts only
the already-rendered `#js_content` DOM, and posts the result to the loopback
capture runtime embedded in the MCP process.

Permissions are limited to `activeTab`, `scripting`, and `http://127.0.0.1:18431/*`. The extension does not request cookies, browsing history, storage, background access to WeChat, proxy control, or arbitrary network destinations.

The public manifest key fixes the extension ID. The lifecycle installer copies
the three runtime source files into the private
`runtime/learning-analysis/extension` directory and generates an untracked
`install_config.js` containing the random per-install token. Load that private
runtime directory in Chrome; never add or print `install_config.js`.

The click flow shows `WAIT` until the matching MCP request is
pending, then extracts and submits the article exactly once. Waiting is bounded
at 20 seconds and does not read or cache article content. Terminal badges are
`OK`, `PAGE`, `AUTH`, `URL`, `TIME`, or `SEND`; they intentionally omit URLs,
tokens, response bodies, and stack traces.

Chrome 152 omits `Origin` on the extension service worker's host-permitted
loopback fetches. Each readiness and capture request therefore includes the
public `chrome.runtime.id` in `X-Learning-Analysis-Extension-Id` as an instance
binding signal, while the random per-install token remains the authentication
secret. A non-empty Origin must still match the fixed extension origin exactly;
an absent Origin is accepted only with the exact extension ID header and token.

Loading remains an explicit browser action: enable Developer mode, choose
**Load unpacked**, and select the private runtime extension directory emitted by
`learning_analysis_lifecycle.py install`. Do not load this source directory,
because it intentionally contains no install token.
