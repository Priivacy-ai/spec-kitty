# Mission Findings & Retro Notes — execution-state-canonical-surface-01KTG6P9

Tracked findings surfaced during this mission, recorded for **mission review / retrospective**.
Each entry: what happened, root cause, how it was resolved, and the upstream gap worth fixing.

---

## F-01 — `occurrence_map.yaml` blocked `implement` start twice (planning-artifact defect)

**Severity:** Medium (workflow blocker, not data integrity). **Phase:** start of implement loop (pre-WP01). **Status:** Resolved.

When driving `spec-kitty agent action implement WP01` the claim stalled at **Validate planning state** twice, both inside `kitty-specs/<mission>/occurrence_map.yaml` (this mission is `change_mode: bulk_edit`, so the map is a hard gate).

### Symptom 1 — invalid YAML
The 25 occurrence rows were authored with `;`-separated inline pairs:
```yaml
- submodule: status.models  ; count: 38 ; decision: PROMOTE ; reason: ...
```
The colon after `count` is parsed as a mapping-value indicator → `mapping values are not allowed here`, line 25 col 48. The whole file failed to load.

**Fix:** rewrote each row as a proper YAML mapping (`submodule`/`count`/`decision`/`reason` keys), quoting colon-bearing reasons.

### Symptom 2 — schema non-conformance
After the YAML parsed, the **bulk-edit gate** (`src/specify_cli/bulk_edit/gate.py` → `validate_occurrence_map` + `check_admissibility`) rejected the map:
- `target.operation: rewrite_import` is not in the schema enum `{rename, remove, deprecate}`.
- `import_paths.action: rewrite` is not in `{rename, manual_review, do_not_change, rename_if_user_visible}`.
- Only 3 of the **8 required standard categories** were present (admissibility requires all 8).
- Top-level used `exemptions`; the schema key is `exceptions`, and each entry needs an `action`.

**Fix:** rewrote the map to the canonical schema (`src/doctrine/schemas/occurrence-map.schema.yaml`): `operation: rename`; all 8 categories present; valid per-category actions; `exceptions` with `do_not_change`. Per-submodule PROMOTE/ROUTE/REVIEW/PRIVATE governance was preserved under `import_paths.occurrences` (allowed because `category_entry.additionalProperties: true`). Verified against `validate_occurrence_map`, `check_admissibility`, and the JSON schema — all green.

### Design decision worth reviewing — `manual_review` over `do_not_change`
The **review-time** diff check (`bulk_edit/diff_check.py`) is *path-heuristic*, not AST: it classifies each changed file into ONE category by path and **BLOCKS** if that category is `do_not_change`. This mission is a *structural refactor* that legitimately edits `cli/commands/*.py` (WP14: merge.py, doctor.py), `src/*.py`, tests, and configs. The heuristic-emittable categories (code_symbols, cli_commands, tests_fixtures, user_facing_strings, serialized_keys) were therefore set to **`manual_review`** (warns; reviewer-renata adjudicates) rather than `do_not_change`, which would spuriously block real WPs. `logs_telemetry` stayed `do_not_change` (never renamed; also never emitted by the heuristic). **Reviewers must confirm no serialized key / CLI name / telemetry key was actually renamed** — the map intentionally does not enforce that mechanically because the path heuristic is too coarse for a structural refactor.

### Coord-topology friction (the failure class this mission exists to fix)
The implement claim validates the **coordination worktree** copy of the artifact
(`.worktrees/<mission>-coord/kitty-specs/.../occurrence_map.yaml`), not just the
primary checkout. The fix had to be committed on **both** the mission branch
(`feat/execution-state-strangler`) **and** the coordination branch
(`kitty/mission-<slug>`). This is the same coord-vs-primary split (#1589/#1772)
the mission targets — it surfaced here at the *planning-artifact* layer.

### Upstream gaps worth filing
1. **Bulk-edit planning let an invalid `occurrence_map.yaml` through to `implement`.** The map should be validated against the canonical schema at authoring time (`/spec-kitty.plan` bulk-edit step, or `finalize-tasks`), not first discovered as an implement-claim stall. The `validate_against_schema` + `check_admissibility` functions already exist — wire them into the planning/finalize gate so the failure is loud and early.
2. **`occurrence_map.schema.yaml` has no example of the rich `occurrences` form.** The starter template (`src/doctrine/templates/occurrence-map-template.yaml`) only shows the minimal `{ action: ... }` per category, so an author hand-rolling per-submodule governance easily invents an invalid shape. Add a commented example of the `additionalProperties:true` extra-fields pattern.
3. **Planning-artifact fixes on coord-topology missions require a manual double-commit** (primary + coord branch). Consider a helper that syncs a corrected planning artifact to the coordination branch, or have the implement claim read the primary checkout for planning artifacts.

**Commits:** `3fe19b869` / `fc8d343ba` (YAML), `febeee4ee` (+ coord mirror) (schema).

---

## F-02 — bulk-edit **review** diff-compliance gate used the wrong head ref (coord-topology false-block)

**Severity:** High (false-blocks every bulk-edit WP review on a coord-topology mission). **Phase:** WP02 review claim. **Status:** Fixed in product source. **Domain:** coord-vs-primary split (#1589/#1772 class).

### Symptom
`spec-kitty agent action review WP02` failed the bulk-edit diff-compliance gate (FR-007/FR-008) listing ~hundreds of "unclassified / forbidden surface touched" files that WP02 never modified — other missions' `status.events.jsonl`, `.gitkeep`, `uv.lock`, `.github/`, `.worktrees/…-coord/…`, plus `status_transition.py` (an intended `do_not_change` exemption flagged as a violation).

### Root cause
`src/specify_cli/cli/commands/agent/workflow.py` (review path) called `check_review_diff_compliance(..., repo_root=main_repo_root, base_ref=<mission_branch>, head_ref="HEAD")`. The diff runs in the **main repo checkout**, whose `HEAD` is the mission's **target branch** (`feat/execution-state-strangler`). So the gate computed `git diff <mission_branch>..feat-tip` = **458 files** of unrelated target-branch delta, instead of the WP's actual lane diff. Correct diff `<mission_branch>..<lane_branch>` = **10 files**.

### Fix
Use the WP's resolved lane branch as the head ref:
```python
_head_ref = review_workspace.branch_name or "HEAD"   # fall back to HEAD only for repo_root / direct-to-target
```
`ResolvedWorkspace.branch_name` is the lane branch for `lane_workspace` and `None` for `repo_root` (planning/direct-to-target, where the changes genuinely are on HEAD). After the fix the gate sees the real 10-file diff: 0 violations, 10 non-blocking `manual_review` warnings.

### Secondary fix (occurrence map)
Even the correct 10-file lane diff includes the mission's own auto-committed artifacts (`kitty-specs/<m>/status.events.jsonl` is unclassified because the path heuristic matches `\.json$` not `.jsonl`; plus `.gitkeep`). Added a `kitty-specs/**` → `manual_review` exception: these are tooling-managed planning/status artifacts on every lane branch, carrying no `specify_cli.status.*` import to rewrite, so they are legitimately outside the bulk-edit surface (non-blocking surfacing).

### Upstream gaps worth filing
1. **Review diff-compliance head-ref bug** is a coordination-topology defect in `workflow.py` — fixed here in source, but it has **no regression test**. Add one: a coord-topology bulk-edit fixture where review-from-main-checkout must diff the lane branch, not the target tip. (Adjacent to WP14's #1772 path/status-surface hardening.)
2. **The path heuristic misses `.jsonl`** (`diff_check.py` `serialized_keys` matches `\.json$` only). `status.events.jsonl` — the canonical status log — is classified *unclassified* and would block any WP that touches it without an exception. Either add `\.jsonl$` to `serialized_keys` or have the diff check ignore the mission's own `kitty-specs/<m>/` status artifacts by construction.

**Commits:** see `feat/execution-state-strangler` — workflow.py head-ref fix + occurrence_map `kitty-specs/**` exception (+ coord mirror).

---

## F-03 — issue-matrix accept gate fires per-WP; added `in-mission` verdict (operator decision)

**Severity:** Medium (workflow gate too strict for multi-WP missions). **Phase:** WP02 approval. **Status:** Resolved (product vocabulary extended). **Operator decision:** 2026-06-08.

### Symptom
`move-task WP02 --to approved` was blocked: `issue-matrix.md` is checked on **every** per-WP `approved`/`done` transition (`_issue_matrix_approval_blocker`, no `--force` bypass), requiring a terminal verdict for every `#NNNN` referenced in `spec.md`. But 7 of the 12 referenced issues are fixed by **later WPs in this same mission** that hadn't run yet — and the allowed verdicts (`fixed` / `verified-already-fixed` / `deferred-with-followup`) had no honest value for "being fixed by this mission, not done yet". Marking them `fixed` would be false; `deferred-with-followup` reads as punted-out-of-mission. Since WP03+ depend on WP02 being `approved`, the whole lane chain was wedged behind the first approval.

### Resolution — new `in-mission` verdict (operator-chosen, highest-signal)
Extended the closed-set verdict vocabulary with `in-mission`: the issue is being closed by a later WP in *this* mission. Semantics:
- **Accepted at per-WP `approved`** — a dependency chain is not blocked on issues its own downstream WPs will close.
- **Rejected on the `done` transition** (mission merge/acceptance) — every issue must reach a terminal verdict (`fixed` / `verified-already-fixed` / `deferred-with-followup`) before the mission lands. The approval blocker is now `target_lane`-aware.

Touched (all `ruff`+`mypy` clean, tests added + green, terminology guard green):
- `cli/commands/review/_issue_matrix.py` — `IssueMatrixVerdict.IN_MISSION`.
- `cli/commands/agent/tasks.py` — `_issue_matrix_approval_blocker(target_lane=…)` rejects `in-mission` only at `done`; call site passes `target_lane`.
- `tasks/issue_matrix.py` scaffold doc, `cli/commands/review/ERROR_CODES.md`, `status/doctor.py` recommendation, and doctrine `spec-kitty-mission-review` / `spec-kitty-implement-review` SKILL.md.
- Tests: `test_issue_matrix_validator.py` (in-mission valid + no handle needed), `test_tasks_helpers.py` (passes at approved, blocks at done, clears when terminal).

### Mission matrix rebuilt
`issue-matrix.md` collapsed to a single table (was 2 — schema violation) with: `#1667/#1756/#1753` → `verified-already-fixed`; `#1666/#1619` (epics) → `deferred-with-followup`; `#1673/#1664/#1672/#1663/#1757/#1754/#1772` → `in-mission` (owning WP recorded). **Each `in-mission` row must be flipped to `fixed` as its WP lands** — and all must be terminal before merge (the `done` gate enforces this).

### Upstream gap worth filing
The per-WP `approved` issue-matrix gate is arguably mis-scoped for multi-WP missions even with `in-mission` — consider gating only at mission accept/`done` by default. The `in-mission` verdict is the pragmatic fix; the deeper scoping question remains.
