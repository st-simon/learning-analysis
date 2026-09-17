# Gate 1A readiness spike

This spike verifies exact Chrome-extension identity, a per-install loopback token,
and same-call waiting. It does not install a LaunchAgent or change the production
plugin route.

Run `python spike/l3-readiness/configure_extension.py` before loading
`spike/browser-source-extension` as an unpacked extension. The command creates a
random local token when needed and writes the ignored `install_config.js` with
mode `0600`; it never prints the token. The manifest public key fixes the expected
extension ID at `bpannmkojgebmphkkngpnhkfcgfpnbhn`.
