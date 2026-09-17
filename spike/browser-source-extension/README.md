# Gate 0 browser source

Disposable Chrome Manifest V3 spike for H2. A user toolbar click grants `activeTab` access to the current page, extracts only the already-rendered `#js_content` DOM, and posts the result to the loopback capture bridge.

Permissions are limited to `activeTab`, `scripting`, and `http://127.0.0.1:18431/*`. The extension does not request cookies, browsing history, storage, background access to WeChat, proxy control, or arbitrary network destinations.

Gate 1A adds a public manifest key that fixes the extension ID and an ignored
`install_config.js` containing the local per-install token. Generate that file
with `python spike/l3-readiness/configure_extension.py`; never commit or print it.

Gate 0 loading is intentionally manual because browser security policy blocks automated access to `chrome://extensions`: enable Developer mode, choose **Load unpacked**, and select this directory. Remove the disposable extension after Gate 0 unless a later full-implementation proposal is approved.
