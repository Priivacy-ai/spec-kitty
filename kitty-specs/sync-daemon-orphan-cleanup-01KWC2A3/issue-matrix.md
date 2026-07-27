# Issue matrix — sync-daemon-orphan-cleanup-01KWC2A3

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2261 | Sync daemon orphan cleanup (mission source bug · P1) | fixed | Scope-marker primary kill authority + FR-008 demotion of exe-identity (WP02 `owner.py` reaper), classifier (WP01 `classification.py`), classified `auth doctor`/`--reset --force` (WP05). Proven end-to-end by WP06 live version matrix (3.2.2/3.2.3/3.2.4 same-scope stale daemons reaped, no redundant spawn) and WP07 cross-family boundary matrix. |
| #1071 | Older same-`$HOME` singleton leak — in scope (FR-012, SC-006) | fixed | Reconfirmed resolved by the new scope-marker authority via automated same-`$HOME` reconfirmation test `tests/sync/test_issue_1071_singleton_reconfirmation.py` (WP08): stale same-scope daemons reaped, exactly one recorded singleton survives, cross-`$HOME` left untouched, PID-level no-leak. Runbook recommends closing #1071 citing this test. |
| #1868 | Broader daemon-identity authority workstream | deferred-with-followup | Out of scope per spec.md C-007 ("do not attempt to resolve every daemon-identity seam from issue #1868"). **Follow-up handle: issue [#1868](https://github.com/Priivacy-ai/spec-kitty/issues/1868)** — the broader daemon-identity authority workstream is the tracking issue for the deferred seams; this mission delivered only the narrow sync-daemon orphan-cleanup slice. |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
