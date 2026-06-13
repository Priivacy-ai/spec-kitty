# debugger-debbie — Adversarial lenience-safety probe of PR #1920

**PR:** `fix(accept): honor --lenient for mission path conventions (#1892)` — tip `07aa0710b`
**Branch:** `upstream/fix/1892-lenient-path-conventions` (reviewed as `1920-debby`)
**Scope of probe:** Does `--lenient` (`strict_metadata=False`) over-soften — i.e. weaken any gate beyond mission path conventions?
**Mode:** READ-ONLY. Op `01KV0T72ETKNZ990ZKCNZ947W7`.

## What the PR changes (one seam)

`acceptance/__init__.py::collect_feature_summary` (lines 1137-1175). Previously `validate_mission_paths(..., strict=True)` raised `PathValidationError` unconditionally, so path conventions blocked accept even under `--lenient`. Now:

- `validate_mission_paths(..., strict=False)` is called (pure, non-raising; computes the same `missing_paths` regardless of `strict` — verified in `validators/paths.py`).
- Blocking decision moved to the call site, owned by `strict_metadata`:
  - `strict_metadata=True` → `path_violations.append(...)` (BLOCKS via `ok`/`outstanding`). **Unchanged behavior.**
  - `strict_metadata=False` → `path_convention_warning` (non-blocking).

## Findings

| # | Severity | Probe | Finding |
|---|----------|-------|---------|
| 1 | PASS | Scope of leniency | `strict_metadata` gates EXACTLY two things: pre-existing WP-frontmatter checks (agent/assignee/shell_pid, lines 1102-1108) and the new path-convention block (lines 1160-1167). It does NOT leak into other gates. |
| 2 | PASS | git_dirty / #1908 / #1883 | `git_dirty` (incl. accept-owned filtering) computed unconditionally (lines 1038-1079). Not influenced by `strict_metadata`. Still in `ok` (line 201). |
| 3 | PASS | acceptance-matrix verdict | Verdict check lives in `activity_issues` ("Acceptance matrix verdict is", line 1015) via `_check_lane_gates`/`_check_workflow_run_evidence` — computed unconditionally (lines 1180-1189). Still in `ok` (line 197). |
| 4 | PASS | Required-fields still enforced | `test_required_fields_still_enforced` PASSES. Under `strict_metadata=True` missing shell_pid still flagged. (Note: lenient also softens WP-metadata checks — but that is the PRE-EXISTING documented meaning of `--lenient` = "Skip strict metadata validation", not introduced here.) |
| 5 | PASS | missing_artifacts / unchecked_tasks / needs_clarification / all_done | All computed unconditionally and remain in `ok` regardless of lenient. |
| 6 | PASS | Partial missing_paths | Validator classifies each path independently; gate fires on `if path_result.missing_paths:` so partial misses are handled (warn lenient / block strict). |
| 7 | PASS | Empty missing_paths under lenient | `if path_result.missing_paths:` is False → `path_convention_warning` stays None → no spurious warning. |
| 8 | PASS | Non-software-dev / no paths | Guarded by `if mission and mission.config.paths:` + validator early-return on empty `required_paths`. No misbehavior. |
| 9 | PASS | Default-path integrity | Default (`lenient=False` → `strict_metadata=True`) keeps `path_violations` populated → `ok`=False → `accept.py` exits non-zero (lines 326/328). Test asserts `strict.path_violations` non-empty. No accidental default softening. |
| 10 | **LOW** | Warning visibility | The downgraded `path_convention_warning` is appended to `summary.warnings`, which is emitted ONLY in `--json` (`to_dict()`, line 265). The human console path `_print_acceptance_summary` renders lanes / `outstanding()` / `optional_missing` but NOT `warnings`, and `outstanding()` (line 205) excludes `warnings`. So an operator running `accept --lenient` WITHOUT `--json` does not see the path-convention shortfall surfaced. Pre-existing limitation of the `warnings` channel (the generic "Path conventions not satisfied." string was likewise console-invisible except via the `path_violations` bucket); the PR does not regress it but inherits it. NOT blocking. |

## Test evidence

- `test_lenient_downgrades_path_conventions_to_warning` — PASS (strict blocks via `path_violations`; lenient surfaces via `warnings`, `path_violations == []`).
- `test_required_fields_still_enforced` — PASS.
- One unrelated FAIL in same file (`test_accept_command_reports_approved_wps_without_closing`): caused by `logged_out_on_connected_teamspace` auth/env error; the PR does not touch that test (`git show` grep = 0). Pre-existing, environmental.

## Verdict

**lenience scoped correctly: YES**

`--lenient` softens only (a) the path-convention block (the intended #1892 fix) and (b) WP-frontmatter metadata checks (the pre-existing, documented meaning of the flag). The #1908 git_dirty/accept-owned gate, acceptance-matrix verdict, missing-artifact, unchecked-task, needs-clarification, and all-done gates are all computed unconditionally and remain blocking under `--lenient`. No security-relevant or correctness gate leaks. Default path stays strict-blocking and exits non-zero.

## Must-fix list

(none blocking)

### Optional / nice-to-have
- **[LOW, #10]** Surface `summary.warnings` (including the path-convention warning) in the human console output of `accept` (e.g. in `_print_acceptance_summary`), so `accept --lenient` operators not using `--json` see what was downgraded. This is a pre-existing visibility gap that the PR makes slightly more relevant; reasonable as a follow-up, not a merge blocker.
