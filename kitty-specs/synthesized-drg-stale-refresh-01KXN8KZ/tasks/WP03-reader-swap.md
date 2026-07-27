---
work_package_id: WP03
title: Reader swap (self-contained red→green)
dependencies:
- WP02
requirement_refs:
- C-002
- C-004
- FR-001
- FR-002
- FR-004
- FR-005
- FR-006
- FR-007
- NFR-004
- NFR-005
- NFR-006
tracker_refs: []
planning_base_branch: fix/2681-synthesized-drg-stale
merge_target_branch: fix/2681-synthesized-drg-stale
branch_strategy: Planning artifacts for this mission were generated on fix/2681-synthesized-drg-stale. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/2681-synthesized-drg-stale unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
- T017
- T018
- T019
- T020
- T021
phase: Phase 3 - Reader swap (content-identity freshness)
assignee: ''
agent: "claude"
shell_pid: "2867801"
shell_pid_created_at: "1784222042.1"
history:
- at: '2026-07-16T12:49:44Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/charter_runtime/freshness/
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/charter_runtime/freshness/computer.py
- tests/specify_cli/charter_freshness/test_computer.py
- tests/integration/test_charter_status_freshness.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP03 – Reader swap (self-contained red→green)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent status` or the Activity Log below).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `<div>`, `<script>`
Use language identifiers in code blocks: ```python, ```bash

---

## Objectives & Success Criteria

WP03 rewrites the freshness reader from a timestamp comparison to a
content-identity comparison — the change that unblocks #2681. It is
**self-contained red→green**: its red-first tests are RED on WP03's base
(the still-mtime reader gives the WRONG verdict) and GREEN on WP03's own
final commit (the content-hash reader). The load-bearing per-WP red pins are
**AS-1** (fresh survives mtime perturbation — the still-mtime reader wrongly
reports `stale`) and **AS-5** (the #2681 full repro — the still-mtime reader
leaves the DRG stuck `stale`). By this WP, WP01 (schema/helper) and WP02
(writers persist real values) are already in place, so the reader has
something real to compare against.

**Definition of Done** (each item ties to the plan's traceability table):

- [ ] `_compute_synthesized_drg`'s comparison block (`computer.py:411-441`)
      is replaced with a stored-vs-current `bundle_content_hash` comparison:
      `None` on either side, or mismatch → `stale`; equal → `fresh`.
      Satisfies FR-001, FR-002, AS-1, AS-2.
- [ ] `compute_bundle_content_hash` imported **lazily** inside the function
      (LD-3 / NFR-002/003 — no new eager import on the `spec-kitty next` hot
      path).
- [ ] Dead code removed: `manifest_exists` (`:352`) + `bundle_ts` (`:412`).
- [ ] PRESERVED branches untouched byte-for-byte: `built_in_only`
      (+residue), `not graph_exists` → legacy-seed + `missing`,
      `synced_bundle.state != "fresh"` precedence, and the parse-failure
      early-return semantics. Satisfies FR-004, FR-006, C-002, AS-6.
- [ ] Module docstring "Detection rules" corrected (FR-007 internal).
- [ ] Per-WP red→green: AS-1 + AS-5 red-first pins are RED on WP03's base and
      GREEN on WP03's final commit — commit red first, confirm red, then land
      the reader swap.
- [ ] The genuine-content-change remediation e2e (SC-003/AS-3 full proof) is
      GREEN (both `synthesize` and `resynthesize` clear genuine drift to
      `fresh`). Satisfies **C-004** (both remediation commands corrected —
      neither left broken behind a new escape-hatch; the writer half was
      wired in WP02, the reader half + e2e proof land here).
- [ ] **NFR-006**: the AS-1/AS-5 red-first repros use REALISTIC past-dated
      `created_at` (NOT the `2099-…` sentinel — the future-dated test is
      explicitly excluded as the guard, T018/T019) and are verified RED on
      the still-mtime reader (WP03 base) and GREEN after the reader swap, for
      BOTH the `synthesize` and `resynthesize` entry points. Satisfies
      NFR-006.
- [ ] The flaky `test_freshness_state_fresh_when_all_artifacts_aligned`
      assertion is tightened to `== "fresh"`.
- [ ] `mypy --strict` + `ruff check` clean; ≥90% new-line coverage.

## Context & Constraints

**Read first**:

- `kitty-specs/synthesized-drg-stale-refresh-01KXN8KZ/plan.md` — WP03
  section + the Charter Check "Architectural alignment / LD-3" row.
- `kitty-specs/synthesized-drg-stale-refresh-01KXN8KZ/data-model.md` — the
  "Behavior change: read-side comparison" section (the EXACT contract).
- `kitty-specs/synthesized-drg-stale-refresh-01KXN8KZ/research.md` — facts
  #1, #2, #3, #4, #19, #20, #21, #22, #23.
- `kitty-specs/synthesized-drg-stale-refresh-01KXN8KZ/spec.md` — FR-001,
  FR-002, AS-1..6, the fail-posture + upstream-bundle-precedence Edge Cases.
- The three tracer files — append implementation notes as you work.

**Exact replacement** (data-model.md, verbatim contract):

```python
current_hash = compute_bundle_content_hash(repo_root)   # lazy import
stored_hash = manifest.bundle_content_hash if manifest is not None else None
if stored_hash is None or current_hash is None or stored_hash != current_hash:
    → stale (remediation="spec-kitty charter synthesize")
else:
    → fresh
```

Replaces the ENTIRE block `computer.py:411-441` (the `bundle_ts` parse
through the `manifest_ts + 1.0 < bundle_ts` comparison and its two returns).
The lines ABOVE it (`graph_mtime_iso = _mtime_iso(graph_path)` at `:400`, the
`synced_bundle.state != "fresh"` precedence at `:402-409`) are PRESERVED. No
timestamp parsing survives — the old `ValueError` early-return that guarded a
malformed `synced_bundle.last_change` has no input to guard anymore (both
comparands are hashes); it is removed with the cascade (the precedence branch
above already handles a non-fresh/absent `last_change`).

**Per-WP red-first honesty** (so `/analyze` finds no new dilution): AS-1 and
AS-5 are UNAMBIGUOUSLY red on the still-mtime reader (AS-1: reports `stale`
when it should report `fresh`; AS-5: the exact #2681 deadlock). Author those
first and confirm red — they are WP03's load-bearing per-WP red→green proof.
AS-2 and some remediation-e2e assertions MAY coincidentally pass on the mtime
reader (editing content also bumps mtime); they pin the requirement precisely
but are not the red-first proof. Label each test with its role.

## Branch Strategy

- **Strategy**: single-branch topology — no worktree/lane split.
- **Planning base branch**: `fix/2681-synthesized-drg-stale`
- **Merge target branch**: `fix/2681-synthesized-drg-stale`

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

## Subtasks & Detailed Guidance

### Subtask T015 – Rewrite the comparison block to content-hash

- **Purpose**: The core fix.
- **Steps**:
  1. In `computer.py`'s `_compute_synthesized_drg` (`:337-443`), confirm the
     code above `:411` is untouched (manifest/graph loads, `built_in_only`
     branch, `not graph_exists` branch, `graph_mtime_iso`, the
     `synced_bundle` precedence branch).
  2. Replace `:411-443` (the `try: bundle_ts = ...` through the final `return
     ... "fresh"`) with:
     ```python
     from charter.bundle import compute_bundle_content_hash  # noqa: PLC0415 — LD-3 lazy import
     current_hash = compute_bundle_content_hash(repo_root)
     stored_hash = manifest.bundle_content_hash if manifest is not None else None
     if stored_hash is None or current_hash is None or stored_hash != current_hash:
         return FreshnessSubState(
             state="stale",
             last_change=graph_mtime_iso,
             remediation="spec-kitty charter synthesize",
         )
     return FreshnessSubState(state="fresh", last_change=graph_mtime_iso, remediation=None)
     ```
  3. The lazy import stays INSIDE the function (LD-3 — matches `:130-132`,
     `:143-148`, `:200-202`; the module docstring documents why: avoid a
     >500ms eager import onto `spec-kitty next` startup, NFR-002/003).
  4. `graph_mtime_iso` unchanged (display value only).
- **Files**: `src/specify_cli/charter_runtime/freshness/computer.py`
- **Parallel?**: No — the central change.

### Subtask T016 – Remove dead `manifest_exists` and `bundle_ts`

- **Steps**:
  1. Remove `manifest_exists = manifest is not None` (`:352`) — only used by
     the deleted cascade.
  2. Confirm `bundle_ts` is gone (it was inside the T015-deleted block).
  3. `grep -n "bundle_ts\|manifest_exists" computer.py` → zero matches. Run
     `ruff` to catch any newly-unused import (keep `datetime`/`UTC` — still
     used by `_mtime_iso`/`_latest_mtime`).
- **Files**: `src/specify_cli/charter_runtime/freshness/computer.py`
- **Parallel?**: No — sequential cleanup after T015.

### Subtask T017 – Correct the module docstring (FR-007 internal)

- **Steps**:
  1. Replace the `synthesized_drg.state = "stale"` bullet (`:9-12`,
     describing the defective mtime rule) with the content-hash rule from
     `contracts/synthesized-drg-freshness-rule.md`'s "Corrected rule text",
     adapted to the terse bullet style (content comparison over the four
     `.kittify/charter/` bundle files; missing `bundle_content_hash` treated
     as mismatch → `stale`, self-heals in one remediation run).
  2. Leave the `missing`/`built_in_only` bullets unchanged (FR-004/FR-006,
     C-002). Leave the LD-3 + "never invalid" paragraphs unchanged.
- **Files**: `src/specify_cli/charter_runtime/freshness/computer.py`
- **Parallel?**: Yes — doc-only.

### Subtask T018 – Red-first: AS-1 + AS-2 reader unit tests

- **Purpose**: WP03's load-bearing per-WP red→green pins (AS-1 unambiguous).
- **Steps** — commit RED first (against WP03 base = still-mtime reader),
  confirm red for AS-1, then T015 turns it green:
  1. In `tests/specify_cli/charter_freshness/test_computer.py`, extend
     `_seed_manifest` (or add a helper) with a `bundle_content_hash` param.
     Ensure all 4 bundle files are seeded (`_seed_bundle_files` writes 3 +
     `_write_metadata` writes metadata.yaml — call both).
  2. **AS-1** (`test_synthesized_drg_fresh_after_mtime_only_bump`): seed
     charter+metadata+4 bundle files+graph; compute the REAL
     `bundle_content_hash` via `charter.bundle.compute_bundle_content_hash`;
     seed a manifest with that value + a REALISTIC past-dated `created_at`
     (e.g. `"2026-01-01T00:00:00+00:00"`, NOT `2099-…`); `os.utime` the
     bundle files forward (content unchanged). Assert `synthesized_drg.state
     == "fresh"`. Label `# RED on the still-mtime reader (reports stale);
     GREEN after T015 — WP03's load-bearing per-WP red pin`.
  3. **AS-2** (`..._stale_when_bundle_content_genuinely_changed`): seed a
     "fresh" manifest (stored hash matches), then genuinely edit one bundle
     file's CONTENT without re-seeding the manifest; assert `state ==
     "stale"`. Label `# AS-2 pin (fact #22); may coincidentally pass on the
     mtime base — its regression power activates with the content-hash
     reader`.
- **Files**: `tests/specify_cli/charter_freshness/test_computer.py`
- **Parallel?**: Yes, alongside T019/T020.

### Subtask T019 – Red-first: AS-5 #2681 full repro + genuine-content-change remediation e2e

- **Purpose**: The canonical #2681 red (AS-5) + the full SC-003/AS-3
  remediation-clears proof.
- **Steps** — commit RED first, confirm red, then green after T015:
  1. **AS-5** — reproduce the exact spec.md sequence for BOTH entry points:
     synthesize once (with 4 bundle files seeded) → let a no-op-stable run
     occur → advance the bundle mtime (content unchanged, e.g. `os.utime`) →
     confirm the still-mtime reader reports `stale` (documents the defect) →
     run `synthesize` remediation → assert `fresh`; separately (fresh
     fixture) run `resynthesize` remediation → assert `fresh`. This is the
     canonical #2681 red pin (RED on the mtime reader — it leaves the DRG
     stuck `stale` after the no-op run). Home it in `test_computer.py` (unit,
     seeding manifests directly) and/or `test_charter_status_freshness.py`
     (integration via the `charter status` surface) as fits.
  2. **Genuine-content-change remediation e2e** (SC-003/AS-3 full proof):
     seed a fresh DRG → edit `governance.yaml` CONTENT → assert `stale` →
     run `synthesize` → assert `fresh`; repeat the `stale` →
     `resynthesize` → `fresh` cycle. This proves the WRITER-recompute (WP02)
     AND the reader (WP03) compose end-to-end — the reader half of what WP02's
     T013 proved on the writer half.
  3. Reuse `test_orchestrator_resynthesize.py`'s helpers only via the
     surfaces WP03 owns (`test_computer.py`/`test_charter_status_freshness.
     py`) — do NOT edit `test_orchestrator_resynthesize.py` (WP02-owned).
- **Files**: `tests/specify_cli/charter_freshness/test_computer.py`,
  `tests/integration/test_charter_status_freshness.py`
- **Parallel?**: Yes, alongside T018/T020.

### Subtask T020 – Tighten the flaky assertion + preserved-branch pins

- **Steps**:
  1. In `tests/integration/test_charter_status_freshness.py`, change
     `test_freshness_state_fresh_when_all_artifacts_aligned`'s `assert ...
     in {"fresh", "stale"}` → `== "fresh"` (research fact #21 — the loose
     assertion is a live SYMPTOM of the bug). Extend `_write_manifest` to
     seed a real `bundle_content_hash` (via the WP01 helper against this
     fixture's own bundle files) so the tightened assertion is a genuine
     pin, GREEN after T015.
  2. Audit the preserved-branch tests (`test_synthesized_drg_built_in_only_
     when_manifest_declares_it` `:213`, `..._for_legacy_fresh_seed` `:223`,
     `..._residue_reports_built_in_only` `:241`, `..._missing_when_no_graph_
     no_manifest` `:204`) — confirm each still passes unmodified. Add a
     direct `synced_bundle.state != "fresh"` → `synthesized_drg == "stale"`
     precedence pin if none exists. Comment each: "preserved by the #2681
     fix — a regress here means T015 touched a branch it should not have."
- **Files**: `tests/integration/test_charter_status_freshness.py`,
  `tests/specify_cli/charter_freshness/test_computer.py`
- **Parallel?**: Yes, alongside T018/T019.

### Subtask T021 – WP03 regression validation

- **Steps**:
  1. Confirm AS-1 + AS-5 were verified RED-first and are now GREEN.
  2. Confirm the remediation e2e (T019.2) is GREEN for both `synthesize` and
     `resynthesize`.
  3. Confirm every preserved-branch pin still passes.
  4. `grep` confirm `bundle_ts`/`manifest_exists` are gone.
- **Files**: (validation only)
- **Parallel?**: No — final subtask.

## Test Strategy

```bash
pytest tests/specify_cli/charter_freshness/test_computer.py -q
pytest tests/integration/test_charter_status_freshness.py -q
# keep green (not WP03-owned — WP02 already made them green):
pytest tests/charter/synthesizer/test_orchestrator_resynthesize.py \
    tests/integration/test_charter_synthesize_built_in_only.py \
    tests/architectural/test_no_op_stable_writes.py -q
mypy --strict src/specify_cli/charter_runtime/freshness/computer.py
ruff check src/specify_cli/charter_runtime/freshness/computer.py \
    tests/specify_cli/charter_freshness/test_computer.py \
    tests/integration/test_charter_status_freshness.py
```

## Risks & Mitigations

- Touching a PRESERVED branch while cleaning up nearby code. Mitigation:
  T020's preserved-branch pins.
- Eager-importing `charter.bundle` at module scope → NFR-002/003 regression.
  Mitigation: match the existing lazy-import pattern exactly.
- Leaving `manifest_exists`/`bundle_ts` half-removed → `NameError`.
  Mitigation: T016's grep verification.
- A test labeled red-first that never actually goes red (vacuous).
  Mitigation: confirm AS-1 + AS-5 red against the WP03-base reader first.

## Review Guidance

- Diff `computer.py` vs `planning_base_branch` — the ONLY changed regions:
  the docstring bullet (T017), the `manifest_exists` line (T016), and the
  `:411-443` block (T015). No other line differs.
- Confirm the lazy-import placement + `# noqa: PLC0415` convention.
- Confirm AS-1 + AS-5 were verified RED on the WP03-base reader before going
  green (WP03's per-WP red→green proof) — reject if the red step was skipped.
- Confirm the corrected docstring matches
  `contracts/synthesized-drg-freshness-rule.md` in substance.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

### How to Add Activity Log Entries

**When adding an entry**:

1. Scroll to the bottom of this Activity Log section
2. **APPEND the new entry at the END** (do NOT prepend or insert in middle)
3. Use exact format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`
4. Timestamp MUST be current time in UTC (check with `date -u "+%Y-%m-%dT%H:%M:%SZ"`)
5. Agent ID should identify who made the change (claude-sonnet-4-5, codex, etc.)

**Initial entry**:

- 2026-07-16T12:49:44Z – system – Prompt created.

---

### Updating Status

Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task <WPID> --to <status>` to change WP status.
- 2026-07-16T17:14:09Z – claude – shell_pid=2867801 – Assigned agent via action command
- 2026-07-16T17:59:08Z – claude – shell_pid=2867801 – WP03 fc679f573 terminal #2681 reader swap; gate PASSED (renata+debbie, live repro + no-false-fresh probes, 0 blocker/major/medium)
- 2026-07-16T17:59:13Z – user – shell_pid=2867801 – WP03 fc679f573 terminal #2681 reader swap; gate PASSED (renata+debbie, live repro + no-false-fresh probes, 0 blocker/major/medium)
- 2026-07-16T19:27:07Z – user – shell_pid=2867801 – mission complete; adversarial gates passed; #2681 fixed
