# Issue matrix — naming-identity-routing-rider-01KV7SFD

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.
Terminalized at mission acceptance (2026-06-16): every row carries a terminal verdict.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2000 | mission-identity compose-routing via dir-name seam | fixed | WP05 routes the two composes through `mission_dir_name`/`resolve_mid8` (lane-e) + WP01 seam demotion (`resolve_mid8` sole public door); byte-parity frozen-literal tests; ratchet (WP02) confirms zero unaccounted consumers repo-wide |
| #1971 | locate_project_root tail — single-authority convergence | verified-already-fixed | WP06 #1971-tail: `tests/specify_cli/core/test_locate_project_root_convergence.py` — 6 divergent-input tests prove the 3 entries converge on `core/paths.py`; deferred-import shims untouched |
| #1888 | phantom-path ownership validation existence check | verified-already-fixed | WP06 verify-and-close: existence check already landed (991162c0a, `validate_glob_matches`); `tests/specify_cli/ownership/test_validation_existence.py` — 5 phantom-path tests pass on HEAD with NO code change |
| #2008 | command-surface validation & docs/prompt drift (#2007 Focus A) | fixed | WP07: 15 SOURCE drift refs repointed (doctrine list/show → real surfaces; plan-prompt `--action`/`--mission`) + command-snippet CI guard in `test_docs_cli_reference_parity.py` (empty-frozenset ratchet, scans live Typer surface) |
| #1890 | coordination worktree repair surface (hint) | deferred-with-followup | WP07 repointed the `worktree repair` hint → `doctor workspaces --fix` + documented the CLI-surface contract; the dedicated repair-command surface remains the #2007 C4 follow-on |
| #1891 | implement/review action JSON contract | deferred-with-followup | WP07 documented the text-only `agent action implement/review` vs internal `implement --json` contract (CLI Surface Contract section); the `--json` code-add is the read-path follow-on (assignee retained) |
| #1899 | mid8 seam — original cluster (closed) | verified-already-fixed | CLOSED via PR #2001 (3.2.0); residual tracked as #2000 (no independent tail) — see scope-review/priti-ticket-focus.md |
| #2001 | spec-kitty-cli 3.2.0 release | verified-already-fixed | Historical reference — merged release PR that shipped the seam this mission adopts |
| #2007 | Epic: 3.2.0 training bugs (Robert) | deferred-with-followup | This mission delivered Focus A (command-contract-drift guard, #2008); the read-path/error-fidelity class is the named follow-on (sub-issues #2009/#2010/#2011) |
| #1993 | coord-aware `_lanes_feature_dir` extraction | deferred-with-followup | Scope review retired the `resolve_lanes_dir` idea (would violate C-001; lanes.json already centralized); the real coord-aware target → follow-on mission |
| #1900 | coord write-side ratchet | deferred-with-followup | Coord write-side, gated on coord-merge-stabilization; out of this mission's bounded scope (C-005) → follow-on |
| #1832 | `agent action implement` — no workspace resolved | deferred-with-followup | Read-path class → #2007 C3 (#2010) read-path resolver unification follow-on (C-005) |
| #1716 | coordination topology authority | deferred-with-followup | Write-side topology keystone → #2007 / #2010-2011 follow-on; out of bounded scope (C-005) |
| #1827 | merge post-merge baseline circular failure | deferred-with-followup | Re-test-first item; read-path/merge follow-on (C-005) |
| #1619 | unify execution context / runtime-state SSOT (epic) | deferred-with-followup | Advanced by the mid8-routing + ratchet; the `ExecutionContext` builder-hardening is the follow-on (C-005) |
| #12 | #2007 read-path bug-inventory item (finalize-tasks generic-error flatten) | deferred-with-followup | #2007 read-path class → #2010 follow-on (C-005); not in this mission's bounded scope |
| #14 | #2007 read-path bug-inventory item (STATUS_READ_PATH_NOT_FOUND) | deferred-with-followup | #2007 read-path class → #2010 follow-on (C-005) |
| #15 | #2007 read-path bug-inventory item (`next` hides real failure) | deferred-with-followup | #2007 read-path class → #2010 follow-on (C-005) |
| #10 | #2007 bug-inventory item (finalize glob warn-vs-error) | deferred-with-followup | Already-fixed-on-HEAD per debbie triage; tracked under #2007 → #2010 follow-on (C-005) |
| #11 | #2007 bug-inventory item (finalize coord-surface read) | deferred-with-followup | Already-fixed-on-HEAD per debbie triage; tracked under #2007 → #2010 follow-on (C-005) |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
