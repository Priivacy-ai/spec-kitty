---
work_package_id: WP02
title: Widen dossier-emitter positional-call guard (FR-001–FR-004)
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- NFR-003
planning_base_branch: fix/dossier-guard-reexport-analyze-cleanup-3676
merge_target_branch: fix/dossier-guard-reexport-analyze-cleanup-3676
branch_strategy: Planning artifacts for this mission were generated on fix/dossier-guard-reexport-analyze-cleanup-3676. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/dossier-guard-reexport-analyze-cleanup-3676 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-dossier-guard-reexport-analyze-cleanup-01M0NHRT
base_commit: a513bcf27bc2678ab280e3462dbd9e8d14760b06
created_at: '2026-08-23T00:15:43.635413+00:00'
subtasks:
- T006
- T007
- T008
- T009
history: []
agent_profile: python-pedro
authoritative_surface: tests/architectural/test_dossier_emitter_positional_guard.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- tests/architectural/test_dossier_emitter_positional_guard.py
role: implementer
tags: []
tracker_refs: []
---

# WP02 — Widen dossier-emitter positional-call guard (FR-001–FR-004)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Close the two detection gaps issue #3676 names — gaps that the guard's own module docstring in `tests/architectural/test_dossier_emitter_positional_guard.py` currently documents as deliberately deferred design scope, not as bugs:

1. **Attribute-chain positional calls** — `dossier.emit_artifact_indexed(...)` (callee is `ast.Attribute`, not `ast.Name`).
2. **Aliased-import positional calls** — `from ...dossier.events import emit_artifact_indexed as ei; ei(...)` (callee IS `ast.Name`, but `.id == "ei"`, not one of the four guarded names).

Prove the widening with RED-first fixtures (charter C-011, ATDD-first — binding). Update the module docstring so it no longer frames these two shapes as deferred/nonexistent (FR-003, SC-008). Introduce zero new false positives against the real `src/` tree or the existing negative-control fixtures (NFR-003).

This WP does **not** touch `src/specify_cli/dossier/__init__.py`, `src/specify_cli/analysis_report.py`, `src/specify_cli/cli/commands/agent/mission_record_analysis.py`, or either `tests/specify_cli/test_analysis_report*.py` file — those belong to the mission's other three WPs (IC-02, IC-03). Your `owned_files` is exactly one file: `tests/architectural/test_dossier_emitter_positional_guard.py`.

## Mission-wide baseline — confirm before your first commit

This mission's baseline capture command spans all five touched test files and must run **once, before the FIRST implementation commit of the WHOLE MISSION** (not per-WP). This WP is one of four independent WPs in this mission; WP01 is sequenced first and owns primary responsibility for capturing this baseline.

Before your own first commit in this WP: check `kitty-specs/dossier-guard-reexport-analyze-cleanup-01M0NHRT/tracer-tooling-friction.md` for an F-0N entry recording that the mission-wide baseline was already captured. If it is **not** present, run it yourself now and record the result in `tracer-tooling-friction.md` (append, never overwrite; otherwise follow the existing entries' format) **before proceeding** to T006.

**Concurrency note (all four WPs in this mission are `dependencies: []` / `parallel_group: 0` and may be dispatched to genuinely concurrent worktrees):** `tracer-tooling-friction.md` is a single shared file that is intentionally NOT listed in any WP's `owned_files`/lane `write_scope` — this was investigated during the fix pass that added this note: adding it there would make `_globs_overlap`'s exact-path-equality rule treat every WP pair as write-scope-overlapping, and `compute_lanes`/`validate_ownership` would then either collapse all four independent lanes into one or reject the manifest outright as an ownership conflict at `finalize-tasks --validate-only` — both strictly worse than the race this note addresses, since either would destroy this mission's intentional four-way parallelism. Because two WPs racing this check-then-act baseline capture could both independently conclude "not present" and append competing entries, if YOU are the WP that finds the baseline genuinely not yet captured, append it under a fresh UTC-timestamped heading — `## F-<UTC-timestamp, e.g. 2026-08-23T00:12:04Z> — <title>` — instead of a guessed sequential `F-0N` number, so two genuinely concurrent appends cannot collide on the same heading even without a file lock or inter-agent coordination. Do not renumber or touch any other WP's entry. **(Added round-2, TASKS-FRESH-003.)** The timestamp only guarantees the appended section's *heading text* won't collide — it does NOT prevent a literal `git` merge conflict on this shared, untracked-by-any-lane file when two WP branches that both appended to it are combined; that conflict remains possible and expected under real concurrency. Whoever lands second and hits it must resolve by **keeping both entries** (never discarding one) — a normal two-way content merge on an append-only file, not a conflict requiring judgment about which append "wins."

Reproduce the exact command (plan.md, "Baseline" section):

```bash
pytest tests/architectural/test_dossier_emitter_positional_guard.py \
       tests/dossier/test_events.py \
       tests/architectural/test_no_dead_symbols.py \
       tests/specify_cli/test_analysis_report.py \
       tests/specify_cli/test_analysis_report_charter_yaml_staleness.py -q
```

**Disposition rule** (restated, binding — spec.md's corrected precedence: charter > operator standing orders > CLAUDE.md, §486 now binds absolutely):

- Red genuinely inside issue #3284's known ~23-failures-+2-errors set → cite #3284, file nothing.
- Red **outside** #3284's set → file a new GitHub issue (charter §486) — this is charter-compelled, **not** optional, and **not** an operator-escalation candidate for this specific case.

## Context

(a) This WP is **IC-01** in plan.md's Implementation Concern Map — fully independent of IC-02 (the CLI re-export trim, `src/specify_cli/dossier/__init__.py`) and IC-03 (the commit-subject fix and path-relativization, `mission_record_analysis.py` / `analysis_report.py` / the two `test_analysis_report*.py` files). `dependencies: []` in the frontmatter reflects this — nothing in this WP waits on the other three WPs, and nothing in the other three WPs waits on this one.

(b) spec.md's §106 change-scope reconciliation and plan.md's own §106 table both cite this file's inclusion the same way — spec.md: *"the guard's own docstring itself documents the two gaps this mission closes"*; plan.md's §106 table: *"#3676's own named defect; the guard's docstring itself documents the two gaps this mission closes."* This is your file's entire justification for being in scope — no other rationale is needed or should be invented.

(c) The module's own docstring today (`tests/architectural/test_dossier_emitter_positional_guard.py` lines 22-37, "What this guard deliberately does NOT cover") explicitly frames both gaps as intentional, accepted scope boundaries:

> "Attribute-chain calls (`module.emit_artifact_indexed(...)`) — the four emitters are always called as bare module-level names in `src/` today, never via a qualified attribute access, so this guard does simple `Name`-based matching only, not full call-graph/import resolution."
>
> "Aliased imports (`from ... import emit_artifact_indexed as ei`) — an alias would not match the name set and would silently escape detection; none exist in `src/` today (spec.md's own readiness probe verified this), so widening the detector to handle aliasing is explicitly deferred until a real aliased call site exists."

This mission's premise (from #3676) is that **this framing itself is the defect** — the docstring is documenting an accepted gap that is actually a hole a future caller could fall through (Grounding Correction 1: `specify_cli/dossier/__init__.py` re-exports the four `emit_*` names, so `import specify_cli.dossier as dossier; dossier.emit_artifact_indexed(...)` is already a valid, real Python call shape any future caller could use — a *potential*, not currently-exercised, shape). Your job is to close the gap, not merely re-word the docstring's disclaimer.

### Subtask T006: RED-first — add two new positive-control fixtures, confirm RED against the pre-widening detector

**Purpose**: charter C-011 ATDD-first (binding) — prove the current detector misses both shapes *before* widening it. Without this step there is no evidence the widening did anything; without it landing as its own commit before any implementation change, a reviewer cannot check out "one commit before GREEN" and reproduce RED.

**Steps**:

Add two new test functions to `tests/architectural/test_dossier_emitter_positional_guard.py`, following the **exact** fixture idiom `test_detector_flags_planted_positional_call` (current lines 149-176) already uses: a throwaway `tmp_path` file written via `.write_text(...)`, scanned via `_find_positional_emitter_calls((planted,))`, asserting exactly one violation with the correct `path`/`lineno`/`func_name`.

1. **Attribute-chain fixture.** Plant a file containing:

   ```python
   result = dossier.emit_artifact_indexed("m", "k", "c", "p", "h", 1)
   ```

   (six bare positional arguments — spec.md's own canonical example; callee is `ast.Attribute`, not `ast.Name`). Assert `_find_positional_emitter_calls` reports **exactly one** violation identifying that call: correct `path` (the planted file), correct `lineno`, and `func_name == "emit_artifact_indexed"`.

   Per spec.md's Edge Cases section (first bullet): the widened detector must match on the **final** attribute name (`.attr` of the outermost `ast.Attribute` node) regardless of chain depth — this mirrors the existing bare-`Name` detector's already-accepted false-positive-risk boundary (the same boundary `test_detector_ignores_unrelated_same_name_free_function` documents and tests), extended to the attribute-chain shape. You do not need a nested-chain (`a.b.dossier.emit_x(...)`) fixture in this WP — the spec only requires the single-level shape be proven; the docstring in T008 states the final-attribute-name rule explicitly so the general case is documented even though only the one-level case is fixture-proven.

2. **Aliased-import fixture.** Plant a file containing:

   ```python
   from ...dossier.events import emit_artifact_indexed as ei

   result = ei("m", "k", "c", "p", "h", 1)
   ```

   (callee IS `ast.Name`, but `.id == "ei"`, not one of the four guarded names). Assert `_find_positional_emitter_calls` reports **exactly one** violation correctly attributed to `emit_artifact_indexed` (the alias's resolved original name) — not silently passed through as an unrecognized name, and not attributed to the alias `"ei"` itself.

   Per spec.md's Edge Cases section (second bullet): this is **syntactic** import-alias resolution only — matching an `ast.ImportFrom` alias to its original name within the same file, not full data-flow/reassignment tracking. A later `ei = something_else` reassignment is explicitly out of scope for detection; your fixture must not attempt to test that case (T008's docstring update states this boundary explicitly instead).

Run both new tests against the **current** (pre-widening) `_call_target_name` (lines 92-96 today — only handles bare `ast.Name`, returns `None` otherwise) and confirm **both FAIL (RED)**. This is the whole point of the subtask: if either passes before you touch the detector, something is wrong with the fixture (most likely: your planted source accidentally resolves to a bare-Name call, or your assertion is vacuously true) — fix the fixture before proceeding, do not proceed with a fixture that was never actually RED.

Commit this as **its own commit**, before any implementation commit, with a `test(dossier-guard):` scoped conventional-commit subject (e.g. `test(dossier-guard): add RED-first fixtures for attribute-chain and aliased-import calls`).

**Files**: `tests/architectural/test_dossier_emitter_positional_guard.py` (append two test functions).

**Validation**: `pytest tests/architectural/test_dossier_emitter_positional_guard.py -q -k "attribute_chain or aliased_import"` (or whatever the actual chosen test names are — name them so this `-k` filter, or an equivalent one, actually selects both) shows both new tests **RED**. Confirm and record this before proceeding to T007 — do not widen the detector first and then write "proving" tests after the fact; the commit boundary in T009 depends on this ordering being real, not narrated.

### Subtask T007: GREEN — widen the detector to resolve attribute-chain final names and single-level import aliases

**Purpose**: implement the actual fix. Widen `_call_target_name` (or the surrounding scan logic in `_violations_in_tree` / `_find_positional_emitter_calls` — whichever the current implementation structures the resolution in; read the real code first, do not assume the split) to:

(a) For an `ast.Call` whose `func` is an `ast.Attribute`: resolve to `.attr` (the final attribute name), regardless of chain depth.

(b) For an `ast.Call` whose `func` is an `ast.Name`: additionally resolve single-level import aliases by scanning the module's `ast.ImportFrom` nodes for an `alias.asname` matching the call's `.id`, mapping back to `alias.name` (the original guarded emitter name), before comparing against the four guarded names in `_GUARDED_EMITTERS`.

**Steps**:

1. Read the current `_call_target_name` (lines 92-96) and its caller `_violations_in_tree` (lines 99-110) before writing anything — do not guess the shape. Note that `_violations_in_tree` currently only has access to a single `node: ast.Call` at a time via `ast.walk(tree)`; resolving import aliases (part (b) above) requires scanning the whole `tree` for `ast.ImportFrom` nodes, so you will likely need to either (i) pre-build an alias→original-name map once per file before walking, or (ii) extend `_violations_in_tree`'s signature to also receive the parsed `tree` (it already does) and build the map there. Either approach is acceptable; pick whichever keeps `_call_target_name` a simple, focused function per the module's existing style — do not over-engineer a general import-resolution framework for what the spec bounds to a single-level, same-file alias lookup.

2. Extend the resolution minimally to cover both new shapes while **preserving the existing bare-`ast.Name` behavior exactly** — the four pre-existing tests must still pass unmodified (byte-for-byte; do not touch their assertions).

3. Re-run the two T006 tests and confirm both now **PASS (GREEN)**.

4. Re-run the four pre-existing tests — `test_src_tree_has_no_positional_dossier_emitter_calls`, `test_detector_flags_planted_positional_call`, `test_detector_does_not_flag_keyword_only_call`, `test_detector_ignores_unrelated_same_name_free_function` — and confirm all four remain **GREEN** (NFR-003). This is the concrete proof the widening introduces zero new false positives against the real `src/` tree (`test_src_tree_has_no_positional_dossier_emitter_calls` re-scans all of `src/` with the widened detector) and against the existing negative-control fixture (`test_detector_ignores_unrelated_same_name_free_function`, which plants an unrelated free function sharing no guarded name — the widened attribute-chain matching must not start flagging unrelated `.emit_x`-shaped attribute access).

**Files**: `tests/architectural/test_dossier_emitter_positional_guard.py` — the detector logic only. Note: this is a test-scanning AST guard, so "implementation" and "test file" are genuinely the same file here; there is no separate `src/` module to edit for this WP.

**Validation**: `pytest tests/architectural/test_dossier_emitter_positional_guard.py -q` — all 6 tests (4 pre-existing + 2 new) pass, 0 failures.

### Subtask T008: GREEN — update the module docstring (FR-003/SC-008)

**Purpose**: the module's own docstring (lines 1-42 today, specifically the "What this guard deliberately does NOT cover" section at lines 22-37) currently frames attribute-chain and aliased-import calls as deferred/out-of-scope design decisions. Post-widening this is false and actively misleading to a future maintainer, and must be corrected.

**Steps**:

Rewrite the relevant docstring section (the module docstring, lines 1-42 today — exact line numbers will shift once T006/T007 are landed, so locate it by content, not by line number) to describe:

- What the **widened** detector DOES cover: bare `Name` calls (unchanged from before), attribute-chain calls matched on the final attribute name regardless of chain depth, and single-level import-alias resolution (same-file `ast.ImportFrom` alias → original name).
- Its remaining **true** boundary, stated explicitly rather than silently assumed (per spec.md's Edge Cases section):
  - Still `src/` only (unchanged — `tests/` remains out of scope for the same reason as before: legitimate throwaway positional calls in test fixtures).
  - Still no full call-graph/data-flow resolution beyond those three shapes.
  - **Alias reassignment after binding is out of scope** — e.g. `ei = emit_artifact_indexed_alias; ei = something_else` is not tracked; the detector does syntactic same-file `ImportFrom`-alias matching, not data-flow tracking.
  - **Dynamic/reflective dispatch is out of scope** — `getattr(module, "emit_artifact_indexed")(...)`, a dispatch-dict table keyed by name, or a `functools.partial`-wrapped emitter are all invisible to this detector; it performs syntactic AST matching only, never runtime reflection tracking.

Mechanically required check: after this edit, run

```bash
grep -n 'explicitly deferred\|none exist in \`\`src/\`\` today' tests/architectural/test_dossier_emitter_positional_guard.py
```

This **must** return zero matches (SC-008). Run this grep yourself as part of this subtask and confirm the empty result — do not merely claim the docstring no longer says these things.

**Files**: `tests/architectural/test_dossier_emitter_positional_guard.py` (docstring only — no logic change in this subtask).

**Validation**: the SC-008 grep above returns zero matches; the docstring accurately and specifically describes the post-widening detector's real coverage and its two newly-explicit boundaries (alias reassignment, dynamic dispatch).

### Subtask T009: Verify — full green run, RED/GREEN commit-boundary check

**Purpose**: close out the WP with concrete, run evidence — not a narrative claim that RED-first happened, but something a reviewer can independently reproduce.

**Steps**:

(a) Run `pytest tests/architectural/test_dossier_emitter_positional_guard.py -q` and confirm all 6 tests pass, 0 failures (SC-001, SC-002).

(b) Confirm the RED-first commit boundary is real and checkable: `git log --oneline` (scoped to this WP's branch/worktree) must show the T006 RED-first commit strictly before the T007/T008 GREEN commit(s). A reviewer must be able to check out the commit immediately before the GREEN implementation commit and re-run the two new tests to reproduce RED, then check out final and reproduce GREEN. Actually perform this check yourself before marking the WP done — `git checkout <commit-before-GREEN> -- tests/architectural/test_dossier_emitter_positional_guard.py` (or equivalent), re-run the two new tests, confirm RED, then restore to your final state and confirm GREEN again.

(c) Re-run the SC-008 docstring grep one more time to confirm it still returns zero matches after any final touch-ups made during T009's own checks.

**Files**: none new — verification only.

**Validation**: all pytest runs green; the RED→GREEN commit boundary is verifiable via `git log`/checkout as described above; T009 completion recorded via `spec-kitty agent tasks mark-status T009 --status done`.

## §591 ATDD-First Discipline (C-011, binding) — explicit statement for this WP

RED-first commit (T006) adds the two new positive-control fixtures (attribute-chain, aliased-import), confirmed RED against the CURRENT (pre-widening) `_call_target_name`, as its own commit BEFORE any implementation commit. GREEN implementation commit (T007, T008) widens the detector + updates the docstring, re-confirms GREEN + the four pre-existing tests still green. The review squad will check out the commit immediately before the GREEN commit and re-run the two new tests expecting RED, then check out final expecting GREEN.

## §106 change-scope reconciliation for this WP

Per spec.md's §106 section and plan.md's own §106 table (restated, not re-derived): this file is touched because it is "#3676's own named defect; the guard's own docstring documents the two gaps this mission closes." Tracker reference: #3676.

## Definition of Done

- [ ] Mission-wide baseline confirmed captured — either an existing F-0N entry found in `tracer-tooling-friction.md`, or (if absent) captured here and recorded under a fresh UTC-timestamped heading per the "Mission-wide baseline" section's concurrency note, before your first commit.
- [ ] RED-first commit landed as its own commit, before any implementation commit, with both new tests (attribute-chain, aliased-import) confirmed RED against the pre-widening detector.
- [ ] GREEN commit(s) landed: detector widened to resolve attribute-chain final names and single-level import aliases; docstring updated (FR-003).
- [ ] All 6 tests in `tests/architectural/test_dossier_emitter_positional_guard.py` pass (`pytest tests/architectural/test_dossier_emitter_positional_guard.py -q` — 0 failures).
- [ ] SC-008 grep (`grep -n 'explicitly deferred\|none exist in \`\`src/\`\` today' tests/architectural/test_dossier_emitter_positional_guard.py`) returns zero matches.
- [ ] No false positives introduced against the real `src/` tree (`test_src_tree_has_no_positional_dossier_emitter_calls` green) or the existing negative controls (`test_detector_ignores_unrelated_same_name_free_function`, `test_detector_does_not_flag_keyword_only_call` both green).
- [ ] RED→GREEN commit boundary independently verified via `git log`/checkout, not merely asserted.

## Risks

A too-eager attribute-chain matcher could introduce false positives against real `src/` code that uses unrelated `.emit_x`-shaped attribute access on unrelated objects (e.g. some other object's `.emit_artifact_indexed`-named method that has nothing to do with the dossier emitters). Mitigated by re-running `test_src_tree_has_no_positional_dossier_emitter_calls` and `test_detector_ignores_unrelated_same_name_free_function` after the widening (NFR-003) — this is exactly what T007's validation step checks, and it is the same false-positive-risk boundary the existing bare-`Name` detector already accepts and documents (matching purely on name, not on any deeper semantic check of what the object actually is).

## Reviewer Guidance

Reviewers should specifically:

- Re-run the RED-first commit boundary check: checkout the commit immediately before the GREEN commit, confirm the two new tests are RED; checkout final, confirm GREEN.
- Confirm the docstring no longer contains either forbidden phrase (`explicitly deferred`, `` none exist in ``src/`` today ``) — run the SC-008 grep yourself, don't take the WP's word for it.
- Confirm the four pre-existing tests (`test_src_tree_has_no_positional_dossier_emitter_calls`, `test_detector_flags_planted_positional_call`, `test_detector_does_not_flag_keyword_only_call`, `test_detector_ignores_unrelated_same_name_free_function`) are byte-for-byte unmodified — only two new tests plus the docstring should have changed; no existing test logic altered.

## Implementation command

```bash
spec-kitty agent action implement WP02 --agent claude
```
