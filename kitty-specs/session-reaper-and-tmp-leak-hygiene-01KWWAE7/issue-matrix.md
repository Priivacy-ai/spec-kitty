# Issue matrix — session-reaper-and-tmp-leak-hygiene-01KWWAE7

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #1842 | Test quality: state leaks (reaper + /tmp namespacing + LC-6 tombstone) | fixed | WP01 `625b5d4e` (controller-gated session reaper + N1 test-homes sweep) + WP02 `2aa9d296` (/tmp namespacing) + WP03 `48ea09fc` (LC-6 tombstone); all 3 WPs approved |
| #1634 | E2E tests leak live `test-feature-*` missions/branches | fixed | LC-1 self-heals via WP01's session reaper (`5784dddd`/`625b5d4e`) + retired `.gitignore:143-144` masks (reap-then-assert); reviewer mutation-proved both directions |
| #959 | Review-prompts shared `/tmp` prefix (LC-7) | verified-already-fixed | Re-audit (`d63ec2152`): `prompt_metadata.py:95-123` namespaces under `spec-kitty-review-prompts/{repo}-{sha}/`; 0 flat refs remain — no work needed |
| #2181 | Frozen `/tmp`-literal ratchet | verified-already-fixed | Ratchet `test_no_tmp_paths_in_tests.py` + `tmp_ratchet_baseline.txt` (99 grandfathered) already landed; this mission builds on it; 99-file burn-down deferred to follow-up |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
