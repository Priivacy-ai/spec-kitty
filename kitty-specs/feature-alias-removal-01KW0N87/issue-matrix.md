# Issue matrix — feature-alias-removal-01KW0N87

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #1060 | Legacy cleanup: remove hidden --feature aliases from the CLI surface | in-mission | WP01 hard-removes `--feature` from implement.py + merge.py and standardizes the merge no-selector terminal to exit 2 (commit 3eef359 / T001–T006); remaining 6 in-scope commands land in WP02–WP06. Reaches terminal `fixed` at mission done. |
| #1985 | Prior removal of --feature alias from 10 internal/agent-facing commands | verified-already-fixed | spec.md Background: PR #1985 already removed the alias (and the `hidden_feature_option` helper) from the internal/agent commands; this mission verifies that baseline and extends to the user-facing surface. |
| #1059 | Compatibility inventory and sunset policy | deferred-with-followup | Explicitly out of scope per spec.md C-002 — separate workstream tracked by issue #1059; this mission builds no inventory/sunset mechanism. |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
