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

---

## F-04 — cross-lane dependency CODE is not propagated to dependents (implement claim gates status only)

**Severity:** High (a dependent WP can run against a codebase missing its dependency's changes → false-green or merge surprises). **Phase:** lane orchestration. **Status:** Mitigated by explicit orchestration; tooling gap to file. **Domain:** execution lanes.

### Root cause
`spec-kitty agent action implement WP##` (claim path in `cli/commands/agent/workflow.py`) uses `_dependency_lanes` **only to gate** — it checks each dependency is `approved`/`done` (`dependency_readiness_for_wp`) and then merges the **mission branch** into the lane. But approved WP *code* stays on its **lane branch** and is never promoted to the mission branch (verified: `src/mission_runtime/` from approved WP02 has **0 files** on `kitty/mission-…-01KTG6P9`). So a dependent WP in a *different lane* gets the mission branch (status/coordination only), not its dependency's code.

- **Same lane == same code** holds (shared lane branch/worktree): the lane-b chain WP02→WP03→WP04→… inherits each other's commits. ✓
- **Cross-lane dependencies do NOT**: lane-a is not an ancestor of lane-b (verified `git merge-base --is-ancestor` → false; WP01's full-sequence ratchet = 0 markers on lane-b).

### Cross-lane join points in THIS mission (must merge dependency lane → dependent lane before dispatch)
1. **WP04 (lane-b) ← WP01 (lane-a)** — merge `…-lane-a` into `…-lane-b` after WP01 approved + WP03 done, before claiming WP04.
2. **WP09 (lane-c) ← WP08 (lane-b)** — merge `…-lane-b` into `…-lane-c` after WP08 approved, before claiming WP09.
3. **WP10 (lane-b) ← WP09 (lane-c)** — merge `…-lane-c` into `…-lane-b` after WP09 approved, before claiming WP10.

(All other dependencies are intra-lane-b and need no action. `git merge` is idempotent on commits, so re-merging at final `spec-kitty merge` is safe.)

### Mitigation (orchestration discipline for this mission)
At each join point, with the dependent lane's worktree idle: `git -C <dependent-lane-worktree> merge <dependency-lane-branch>`, resolve any conflict (cross-lane deps generally touch disjoint files), confirm the dependency's code/markers are present, THEN claim+dispatch the dependent. Tracked as explicit loop tasks so a join is never skipped.

### Upstream gap worth filing
The claim flow should integrate approved cross-lane dependency code automatically: after the dependency-readiness gate, merge each dependency's resolved lane branch into the dependent's lane branch (not only the mission branch). Needs a regression test: a 2-lane fixture where lane-B WP depends on a lane-A WP and must see lane-A's code at claim. Without it, "approved unblocks dependents immediately" silently gives dependents a stale base.

---

## F-05 — coordination branch (and ALL lanes) forked from a STALE feat snapshot

**Severity:** High (every WP is implemented against an out-of-date target base). **Phase:** discovered during lane-base verification. **Status:** RESOLVED — lanes rebased onto feat + re-reviewed (operator chose "rebase lanes onto feat now"). **Domain:** coordination-branch / rebase.

### What
The coordination/mission branch `kitty/mission-…-01KTG6P9` (the base all lane branches fork from) is **240 commits behind `feat/execution-state-strangler`** (the mission's declared `planning_base_branch` == `merge_target_branch`). Real `src/` divergence: **77 files, ~2,886 insertions / 769 deletions** — including the very files this mission strangles:
- `status/transitions.py` (−342: the FSM Randy-Reducer reduction), `status/wp_state.py` (313-line diff), `aggregate.py`, `emit.py`, `validate.py`, `models.py` (genesis lane), `__init__.py`.
- An **entire other mission** merged into feat after the fork: `session_presence/` + `m_3_3_0_session_presence_*` migrations.
- The `spec-kitty-events` major bump **5.2.0 → 6.0.0** (genesis lane) — hence the lane `test_uv_lock_pin_drift` failure.

### Why it happened
The coordination branch was created at first finalize from feat *before* feat received: the late FSM-PR-#1775 review reductions, the events-6.0.0 bump, the session-presence merge, and this session's tooling commits. The 2026-06-08 feat rebase-onto-FSM rewrote feat history (merge-base is now the old `3.2.0rc38` release), so the coordination branch shares only that ancient base.

### Impact
WP01/02/03 are approved **but built on the stale base**. WP02's `mission_runtime/` is net-new (low conflict), but WP03 deleted `core/execution_context.py` and migrated callers against the *old* caller set — feat may have new callers of that module that WP03 didn't migrate (→ dangling imports after a rebase), and feat's reduced `transitions.py`/`wp_state.py` will conflict with later WPs (WP07/WP08) coded against the un-reduced versions. Deferring to the final `spec-kitty merge` would produce a large, error-prone conflict across core status files, with WPs having been coded against stale APIs.

### Remediation (operator decision pending)
Fix the base now while only 3 WPs are done (cheap) rather than at final merge (expensive). Options: (A) rebase the lane branches onto current feat + re-validate WP01/02/03; (B) re-finalize from feat tip (recreate coordination + lanes) and re-apply the 3 WPs; (C) continue and reconcile at merge (NOT recommended). Re-validation must re-check WP03's single-resolver + no-dangling-import invariants against feat's newer caller set.

### Resolution (2026-06-08) — Option A executed via merges (not history-rewriting rebases)
Backups taken first: `backup/{coord,lane-a,lane-b}-stale-20260608`. Then merged `feat` into the coordination branch and both lane branches (merge keeps feat an ancestor → clean final lane→feat merge; no force-push). All conflicts were confined to `kitty-specs/` (resolved: status files → coord's live versions, `findings.md` → feat's superset); **all `src/` code merged cleanly**. Results:
- **coord** `55e9c5dfa` — 0 src files differ from feat; status authority intact.
- **lane-a** `ed4d7fb1a` — WP01 ratchet **9 passed** on feat base; ratchet still bites.
- **lane-b** `ee327b429` — WP02+WP03 **22 architectural passed**; `execution_context.py` deletion held; **single resolver (1)**; **no dangling imports** from feat's newer callers; `test_uv_lock_pin_drift` now PASSES (events 6.0.0).
- **Re-reviews** (reviewer-renata; WP01 sonnet, WP02+WP03 opus) both **PASS — approvals hold**. The 31 broader-suite failures were proven pre-existing by baseline reproduction on pure-feat (none reference the relocation surface). Minor doc smells fixed in `4b52a86d7` (see S-03). Cross-lane note: lane-b still lacks WP01's ratchet (WP01 is not on feat), so the WP04 pre-merge guard (lane-a→lane-b) still applies.

---

## F-06 — lane auto-rebase can't handle mission-introduced `kitty-specs/` docs or sparse status conflicts

**Severity:** High (blocked the next WP claim after the F-05 rebase). **Phase:** WP04 claim. **Status:** RESOLVED — lane-b rebuilt as coord+code. **Domain:** coordination-branch / lane auto-rebase.

### Symptom
After the F-05 rebase, claiming WP04 failed the implement-time lane auto-rebase (`spec-kitty agent action implement` runs `git merge <coord>` inside the lane worktree, per `src/specify_cli/lanes/auto_rebase.py`) two ways in sequence:
1. `LANE_AUTO_REBASE_FAILED: no classifier rule matched … findings.md` → Manual → refused.
2. `LANE_AUTO_REBASE_FAILED: could not read conflicted file … status.json: FileNotFoundError` — lane worktrees are **sparse-checkout** (status files not materialized); when such a file conflicts, the classifier's `read_text()` throws before it can even classify.

### Root cause (and answer to "are mission/spec files ignored by the guard?")
**No — they are not specially ignored.** The auto-rebase conflict classifier (`src/specify_cli/merge/conflict_classifier.py`, `RULES`) auto-resolves exactly FOUR file types: `pyproject.toml` deps, `__init__.py` imports, `urls.py` lists, `uv.lock`. **Everything else** (`spec.md`, `plan.md`, `tasks.md`, `status.json`, `status.events.jsonl`, `meta.json`, WP files, and our `findings.md`/`smells_discovered.md`) falls through to `R-DEFAULT-MANUAL` → halt.

The reason mission/spec/status files don't normally break the auto-rebase is **not** that they're ignored — it's that they **never conflict** in a healthy lane: a normal lane never modifies `kitty-specs/` (a guard warns against it), so the coord→lane merge fast-takes coord's version with no conflict region for the classifier to see. The **F-05 `feat`→lane rebase merge violated that** — feat carries the mission's `kitty-specs/` docs, so merging feat into the lanes made the lane "modify" them, turning every one into a 3-way conflict. Our dossier files were simply **first in line** to halt the classifier; `status.json` (and `tasks.md`, WP files, `meta.json`) would each halt it too. They are not uniquely cursed — so the right fix is general (no `kitty-specs/` modifications on the lane at all), not "special-case the two new docs."

### Fix applied
Rebuilt **lane-b = current coord head + the four WP CODE commits cherry-picked** (`55a83e38f` WP01, `9398cca0a` WP02, `67a8d3dd4` WP03, `4b52a86d7` docstring) — **zero `kitty-specs/` modifications** on the lane. Verified: `git diff coord -- kitty-specs/` = 0; 27 architectural tests pass; single resolver; deletion held. The auto-rebase merge is now clean and WP04 claimed successfully. Backup: `backup/lane-b-prerebuild-20260608`.

### Lesson / upstream gaps
- The correct way to rebase a lane onto a moved base is **coord-head + cherry-picked code commits**, NOT a wholesale `feat`→lane merge (which drags `kitty-specs/` into the lane). The F-05 coord resync (merge feat→coord) was fine; the lane resync should have been code-only from the start.
- Upstream: (a) the auto-rebase classifier should treat **any** conflicted `kitty-specs/<mission>/` path (doc *or* status) as coordination-owned (theirs-wins) instead of halting — its `RULES` set only covers `pyproject.toml`/`__init__.py`/`urls.py`/`uv.lock`; (b) it must resolve **sparse/skip-worktree** conflicted files from the index/blob, not `read_text()` the (absent) worktree path — current behavior is a hard `FileNotFoundError`.

---

## F-07 — #1772 Bug 0 reproduced IN THIS MISSION's own planning commit (tracked nested `.worktrees/`)

**Severity:** High (would have polluted feat at merge). **Phase:** discovered during the WP09→WP10 cross-lane merge. **Status:** RESOLVED (untracked) + dogfood evidence for WP14/FR-035. **Domain:** `.worktrees/` hygiene (#1772 Bug 0).

### What
The mission's planning-artifacts commit `05953c5ad` staged **37 tracked files under `.worktrees/execution-state-canonical-surface-01KTG6P9-coord/kitty-specs/…`** — gitignored *nested duplicates* of the coordination worktree's own `kitty-specs/`. This is **exactly #1772 Bug 0** ("finalize/recovery `git add` flows staged tracked `.worktrees/` content") — reproduced by our own finalize, on our own mission. Spread: coord 37, lane-a 33, lane-b 37, lane-c 37; **feat = 0** (clean). The cross-lane merges propagated it between lanes; surfaced when the lane-c→lane-b merge reported `create mode 100644 .worktrees/…-coord/…`.

### Why it matters
`.worktrees/` is gitignored (`.gitignore:58`) — these were force-/erroneously-added at finalize. Because feat is clean, leaving them would have **newly polluted feat at the final lane→feat merge** with 37 junk files (and the nested-coord path is the same double-resolution shape FR-036 targets).

### Fix applied
`git rm -r --cached .worktrees/` on coord + lane-a + lane-b + lane-c (untrack only; on-disk worktree content preserved); committed per branch (lane-b: `aeb1ccb82`). Verified: 0 tracked `.worktrees/` on all four; boundary test + mission_runtime intact on lane-b (5 passed).

### Dogfood value for WP14 (FR-035)
This is live proof for WP14's FR-035 work: (1) the finalize/recovery `git add` MUST exclude `.worktrees/` (the guard that would have prevented `05953c5ad`); (2) the `spec-kitty doctor` check MUST flag pre-existing tracked `.worktrees/` — point it at this exact reproduction as a fixture/case. The mission both *fixes the flow* and *had to clean up the bug's output in its own branches*.

---

## SYNTHESIS — toward a stable "codependent lanes" solution (distilled from F-04/F-05/F-06)

This mission required a lot of **manual git/lane juggling** that the tooling should own. Captured here as design signal — the concrete operations done by hand, their trigger, and what a stable solution must guarantee. The throughline: **the tool models lane *status* dependencies but not lane *code* topology**, and it conflates **code** (lane-owned, merges to target) with **status/planning** (coord-owned), so any base movement or cross-lane dependency forces hand surgery.

### The manual operations performed this session (each is a gap)
| # | Manual op done by hand | Trigger | Tool gap (F-ref) |
|---|------------------------|---------|------------------|
| 1 | `git merge lane-a → lane-b` before claiming WP04 | WP04 (lane-b) depends on WP01 (lane-a); claim gates on dependency *status* only, never propagates dependency *code* across lanes | F-04 |
| 2 | `git merge feat → coord` (resolve `kitty-specs/` conflicts: status→coord, findings→feat) | coord forked from a stale `feat` snapshot (240 commits / 77 src files behind) | F-05 |
| 3 | `git merge feat → lane-a`, `feat → lane-b` (sparse `status.json` needed index-level `--theirs`/`restore`) | same stale base; lanes had to pick up feat's reduced FSM surfaces + events 6.0.0 | F-05 |
| 4 | Rebuild **lane-b = coord-head + cherry-pick(WP01,WP02,WP03,docstring)** | the feat→lane *merge* dragged `kitty-specs/` into the lane → every doc/status file became a conflict → auto-rebase `R-DEFAULT-MANUAL` halt (and sparse `status.json` → `FileNotFoundError`) | F-06 |
| 5 | Mirror every planning-artifact edit to **both** `feat` and the coord branch | coord-vs-primary split: the implement/review gates read the coord worktree, the PR reads `feat` | F-01 (coord double-write) |
| 6 | Pending: `lane-b → lane-c` (before WP09), `lane-c → lane-b` (before WP10) | the remaining cross-lane joins | F-04 |

### What a stable solution must guarantee
1. **Code dependencies are first-class, not just status.** When WP-B depends on WP-A in another lane, claiming WP-B must integrate WP-A's *code* (merge the dependency's resolved lane branch), not only check that WP-A is `approved`. "approved unblocks dependents immediately" is a lie if the dependent gets a stale tree.
2. **Lanes are `coord-base + code-only`, by construction.** A lane should *never* carry `kitty-specs/` modifications. Enforce it (the guard already *warns*; make the lane lifecycle make it *true*), so coord→lane merges always fast-take coord's version and never conflict. The clean-rebuild recipe (reset to coord head, cherry-pick the code commits) is the canonical "re-base a lane" primitive — the tool should expose it as one command.
3. **One command to re-anchor a whole mission onto a moved target.** When `feat` advances (or is rebased), there should be a single `spec-kitty mission rebase` that: merges target→coord (code), keeps coord's status, and re-derives every lane as coord+code. Today this is ~8 hand-run merges/cherry-picks with bespoke conflict calls.
4. **The auto-rebase classifier must not halt on coord-owned files** (treat any `kitty-specs/<mission>/` path as theirs-wins) and must read **sparse** conflicted files from the index/blob.
5. **Detect staleness early.** A lane/coord that has fallen behind the target should be flagged at claim time (or by `doctor`), not discovered by a reviewer noticing missing upstream code (this mission found it only via manual `git merge-base` archaeology — F-05).

### Recommended next step
File a single tracker epic ("codependent-lane topology: code-aware rebase") gathering F-04/F-05/F-06, with the 5 guarantees above as acceptance criteria and a 2-lane + coord-topology fixture (lane-B depends on lane-A; target advances mid-mission) as the regression bed.

---

## F-08 — WP approval recorded on the coordination branch never propagated to the merged feature branch

**Severity:** High (a fully-approved WP appears unreviewed/in-review on the branch that actually merges). **Phase:** closeout (post-lane-merge, flagged by the operator noticing WP14 "For Review"). **Status:** Reconciled manually. **Domain:** coord-vs-primary status split ([[project_lane_loop_status_desync]], #1589) — the exact failure class this mission targets, dogfooded one last time at its own closeout.

### What
After the lane→feat merge + PR open, the operator observed **WP14 still showing "For Review"**. The canonical truth diverged by surface:
- **Coordination worktree** (`.worktrees/<mission>-coord/.../status.events.jsonl`): WP14 = **approved** — a real `in_review → approved` event by the operator (cycle-2 verdict, event `01KTKJ0TWA9B68X69GGW5ZWCFT`, full review evidence).
- **Primary feat checkout** (the tracked `kitty-specs/<mission>/status.events.jsonl` that the PR merges): WP14 = **in_review** — the approve event was **absent**.

So the WP was genuinely approved, but only on the coordination branch; the merged feature branch's tracked event log lagged by exactly one (the terminal) event.

### Why it happened
The approve transition was emitted *after* the lane branches were built/merged, and it landed on the **coordination branch** (where `move-task` writes, because `meta.json` declares `coordination_branch`). The lane→feat merge carried WP14's **code** but not the coordination branch's subsequent **status event**. Two consequences compounded the confusion:
1. **Reader split:** `spec-kitty agent tasks status` / `get_status_read_root()` read the **coord** surface (showed WP14 advanced), while `materialize(primary_feature_dir)` read the **primary** log (in_review). The two disagreed silently.
2. **`move-task` couldn't fix it:** because `move-task` also targets the coord surface (already approved), re-running it returned `Illegal transition: approved -> approved` — it cannot repair the primary log it isn't writing to.

### Reconciliation applied
Copied the **exact** coord approve event (preserving `event_id`, `actor`, `at`, and review `evidence`) into the primary feat `status.events.jsonl` and re-materialized `status.json`. All 14 WPs then read `approved` on the merged surface. (Also hit the **S-06** stale `review-cycle-2.md verdict=rejected` artifact, which blocked a normal `move-task --to approved`; that is the cosmetic cross-cycle artifact bug, not a live rejection.)

### Upstream gaps worth filing (extends the F-04/F-05/F-06 SYNTHESIS)
1. **Terminal status events on the coordination branch must propagate to the feature branch at merge.** `spec-kitty merge` (or the lane→feat integration) should fold the coordination branch's WP lifecycle events into the merged feature log, so the branch that ships carries the same canonical state the board shows. Today code and status integrate on different paths.
2. **Surface-divergence detector.** `doctor` should flag when the coord surface and the primary feature-dir log disagree on any WP's terminal lane (approved/done), instead of leaving it for a human to notice a "For Review" chip on an approved WP.
3. **`move-task` should be able to repair the primary log**, or at least error with the *real* diagnosis ("primary log is N events behind the coordination branch for WP14") rather than a bare `Illegal transition: approved -> approved`.
