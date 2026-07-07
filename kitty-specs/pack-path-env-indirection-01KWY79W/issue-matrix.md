# Issue Matrix — Pack-Path Portability & Language-Scope Authority (01KWY79W)

Driver: #2437 (pack-path env-var indirection). #2395 (language-scope authority) folded in as WP02.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2437 | Org pack `local_path` portability via env-var indirection | fixed | WP01 136d44ec8 — `${SPEC_KITTY_PACK_HOME}` expansion at `effective_root()`; fail-closed `OrgPackEnvVarUnsetError`; round-trip preserves template; 79 targeted tests GREEN (reviewer-renata approved) |
| #2395 | Language-scope drift: interview answers preferred over compiled charter | fixed | WP02 5df51d5cf — `active_languages` persisted at compile time; `infer_repo_languages` reads compiled field first; corrected regression test asserts charter wins on disagreement (reviewer-renata approved) |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission`.

## Out-of-scope notes
- **#2213** — seam-disagreement over which caller invokes `infer_repo_languages`; explicitly excluded per spec C-002.
