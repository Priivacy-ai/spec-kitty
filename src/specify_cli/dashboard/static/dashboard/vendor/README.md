# Vendored dashboard assets

## marked.min.js

- **Upstream:** <https://cdn.jsdelivr.net/npm/marked@11.1.1/marked.min.js>
  (npm `marked@11.1.1`, MIT license — <https://github.com/markedjs/marked>)
- **Integrity:** `sha384-zbcZAIxlvJtNE3Dp5nxLXdXtXyxwOdnILY1TDPVmKFhl4r4nSUG1r8bcFXGVa4Te`
  (the same digest `templates/index.html` declared for the CDN copy via its old
  `integrity` attribute; verified with `openssl dgst -sha384 -binary … | openssl base64`)
- **Why vendored:** the dashboard sends `Content-Security-Policy: script-src 'self'`
  (`specify_cli/dashboard/csp.py`), which blocks the CDN `<script>` — `marked` was
  undefined at runtime, so every `marked.parse(...)` call in `dashboard.js` threw and
  markdown rendering (including the WP prompt modal) silently died. Self-hosting under
  `/static/…` satisfies `'self'`.

To upgrade, replace the file, re-verify the digest above, and update the
`<script src>` tag in `templates/index.html` if the filename changes.
