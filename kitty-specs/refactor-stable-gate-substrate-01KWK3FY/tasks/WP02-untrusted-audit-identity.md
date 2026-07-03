---
work_package_id: WP02
title: Untrusted-path audit identity redesign
dependencies: []
requirement_refs:
- FR-004
tracker_refs: []
planning_base_branch: tidy/gate-substrate
merge_target_branch: tidy/gate-substrate
branch_strategy: Planning artifacts for this mission were generated on tidy/gate-substrate. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into tidy/gate-substrate unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
- T010
- T011
phase: Phase 1 - Parallel substrate work
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1771313"
history:
- at: '2026-07-03T06:37:42Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/architectural/untrusted_path_audit/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- tests/architectural/untrusted_path_audit/audit.py
- tests/architectural/untrusted_path_audit/inventory.md
- tests/architectural/test_untrusted_path_containment.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP02 – Untrusted-path audit identity redesign

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## ⚠️ IMPORTANT: Review Feedback

Check the `review_ref` field in the event log before starting; address all feedback.

---

## Objectives & Success Criteria

Kill the #2306 failure class at its origin (spec FR-004, untrusted sub-stream): the
audit's undercount tripwire identifies rows by the composite
`(rel_path, enclosing_qualname, token)` instead of raw `rel:line`; the duplicated
raw-line compare in the containment test converts too; and the NEW overcount/ghost-row
guard makes deleted sinks impossible to leave silently documented. Success = the audit
triad: line-only drift green; undocumented sink red; ghost row red — PLUS the exact
#2306 historical shape (documented sink shifted one line) green.

## Context & Constraints

Read FIRST (mission dir = kitty-specs/refactor-stable-gate-substrate-01KWK3FY/):
- `contracts/audit-identity-contract.md` — ALL six rules binding; this WP owns the
  untrusted half (rules 1-3, 5-6; rule 2's first two sites).
- `research.md` D3 + **D9 errata** (current-tree truth): Check-2 = audit.py:379-389,
  the convert-target is the LOCATOR compare `f"{rel_path}:{line}"` at :383 (NOT the
  3-part `SinkRow.key()`); Check-3 starts :391 (untouched); the duplicated compare
  confirmed at test_untrusted_path_containment.py:328.
- `data-model.md` — the row identity, `[inventory-only]` tag semantics, triad contract.
- The composite primitive: `tests/architectural/_ratchet_keys.composite_key_from_file`.

Constraints: the audits are TWINS but this WP touches ONLY the untrusted one (WP03 owns
the surface twin — do not "helpfully" consolidate; contract preamble records why);
inventory stays reviewer-readable; the discovery side (`discover_rows()` AST scan) is
the live authority and is NOT redesigned — only the COMPARISON identity changes.

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: tidy/gate-substrate
- **Merge target branch**: tidy/gate-substrate

## Subtasks & Detailed Guidance

### Subtask T007 – SinkRow identity + audit.py Check-2 → composite

- **Steps**:
  1. `SinkRow` gains a derived composite identity: `key()` returns
     `(rel_path, enclosing_qualname, token)` where qualname+token come from
     `composite_key_from_file(src_root / rel_path, line)` — computed for DISCOVERED
     rows from their live line, and for INVENTORY rows from the stored columns (see
     T009 for what the inventory stores).
  2. Check-2 (undercount) compares composite sets; the failure message keeps the live
     `rel:line` locator for discovered sinks (fresh from the scan).
  3. Fail-closed: an inventory row whose stored identity cannot be parsed aborts the
     audit naming the row.
- **Files**: `tests/architectural/untrusted_path_audit/audit.py`.

### Subtask T008 – Convert the duplicated compare in the containment test

- **Steps**: `test_untrusted_path_containment.py:328` region duplicates the raw
  `f"{sink.rel_path}:{sink.line}"` logic — convert it to consume the SAME composite
  `key()` the audit now uses (import/reuse, do not re-duplicate; the duplication
  itself stays — consolidating the twins is out of scope, but WITHIN this file pair
  the test should call the audit's own identity function).
- **Files**: `tests/architectural/test_untrusted_path_containment.py`.

### Subtask T009 – Re-key inventory.md; `[inventory-only]` tag support

- **Steps**:
  1. Extend the inventory row format: each row gains the qualname + token columns
     (tool-derived — write a recorded converter like WP01's, or emit-on-miss from the
     audit itself); the existing `line` column becomes the locator (header comment
     documents it as non-authoritative).
  2. Keep the human columns (untrusted_source, sink_op, notes) untouched; render
     tokens compactly (truncate with an ellipsis marker if > ~60 chars, storing a
     prefix long enough to stay unique per (path, qualname) — document the rule).
  3. `[inventory-only]` tag in the notes column exempts a row from T010's overcount
     check; each tagged row must name the change that removed its sink (data-model
     rule). Zero tagged rows expected at conversion time.
  4. Update the inventory header: Design-P semantics + freshen procedure.
- **Files**: `tests/architectural/untrusted_path_audit/inventory.md` (+ recorded
  converter in the mission dir).

### Subtask T010 – NEW overcount/ghost-row check (via PURE seams)

- **Steps** (squad hardening — the overcount check is VACUOUSLY green at conversion;
  its theater leg is its only non-vacuity proof, so the theater must drive the real
  path):
  1. Extract PURE comparison seams `check_undercount(discovered_keys, inventory_keys)
     -> list[str]` and `check_overcount(discovered_keys, inventory_keys) -> list[str]`
     in audit.py; `main()` MUST call these seams (no duplicate inline logic).
  2. Overcount semantics: every inventory row (minus `[inventory-only]`) must match a
     live discovered sink → RED naming the ghost row + removal guidance.
- **Files**: `audit.py`.

### Subtask T011 – Theater triad + the #2306 regression case; validation

- **Steps**:
  1. Triad driving the REAL path (squad hardening): either through the pure
     `check_undercount`/`check_overcount` seams that `main()` itself calls, or by
     monkeypatching `audit.INVENTORY_PATH` + `audit.discover_rows` and invoking
     `main()` (asserting non-zero exit + the offending row named). A theater test
     asserting against a helper `main()` does not call is a REVIEW REJECT:
     (a) line-only drift of a documented sink → green; (b) undocumented sink → red;
     (c) ghost row → red.
  2. **The #2306 case by name**: reproduce the historical failure shape — a documented
     sink whose implementation shifted exactly one line (the `_mt_warn_worktree_kitty_specs`
     pattern) — assert green, with a comment citing #2306.
  3. Validation: full `pytest tests/architectural/test_untrusted_path_containment.py`
     + a full `tests/architectural/` neighbor sweep; mypy --strict on audit.py + the
     test together; ruff; whole-tree mypy unchanged at zero.
- **Files**: the test file (new theater functions).

## Test Strategy

```bash
export PATH="$PWD/.venv/bin:$PATH"; PYTHONPATH="$PWD/src"
PWHEADLESS=1 pytest tests/architectural/test_untrusted_path_containment.py -q -p no:cacheprovider
PWHEADLESS=1 pytest tests/architectural/ -q -p no:cacheprovider
python -m mypy --strict tests/architectural/untrusted_path_audit/audit.py tests/architectural/test_untrusted_path_containment.py
ruff check tests/architectural/untrusted_path_audit/ tests/architectural/test_untrusted_path_containment.py
```

## Risks & Mitigations

- **Token truncation collisions** (the compact-rendering rule): the converter verifies
  stored prefixes stay unique per (path, qualname); abort otherwise and lengthen.
- **Inventory readability regression**: keep the table structure; tokens go in ONE new
  column; reviewers judged this file readable at 30 rows — preserve that.
- **Scope creep into the twin**: WP03 owns surface_resolution_audit — any shared
  improvement idea goes into the tracer as follow-up material, not code.

## Review Guidance

- Run the triad + the named #2306 case; verify they drive the audit's real check
  functions.
- Spot-re-derive 3 inventory rows' tokens against the live tree.
- Verify the containment test consumes the audit's identity function (no third
  hand-rolled compare).
- Confirm zero surface_resolution_audit diffs.

## Activity Log

> Append at the END, chronological. Format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`

- 2026-07-03T06:37:42Z – system – Prompt created.
- 2026-07-03T07:11:55Z – claude:opus:python-pedro:implementer – shell_pid=1660876 – Assigned agent via action command
- 2026-07-03T07:47:58Z – claude:opus:python-pedro:implementer – shell_pid=1660876 – FR-004 untrusted-audit identity redesign complete. Composite (rel_path,qualname,token) identity via composite_key_from_file replaces raw rel:line in audit Check-2 AND the duplicated containment-test compare (:328); NEW overcount/ghost guard added. PURE check_undercount/check_overcount seams that main() calls; theater triad + #2306 case by name + 2 main()-level non-vacuity tests. inventory re-keyed to 7 cols (line=non-authoritative locator), 5 known-FN rows tagged [inventory-only], stale dup review/cycle.py:225 dropped -> 29 rows (24 discovered+5 inv-only). Validation: audit exit 0; containment 12 passed; full tests/architectural/ 615 passed/4 skipped; ruff clean; mypy --strict clean on both touched files. Deviation: 5 inventory-only tags (not zero) — 5 pre-existing known-FN rows the matcher cannot AST-discover; tag semantics broadened+documented. surface_resolution_audit untouched (WP03).
- 2026-07-03T07:49:09Z – claude:opus:reviewer-renata:reviewer – shell_pid=1771313 – Started review via action command
- 2026-07-03T07:58:08Z – user – shell_pid=1771313 – Review passed (reviewer-renata). FR-004 composite (rel_path,qualname,token) identity replaces raw rel:line in audit Check-2 AND the ex-duplicated containment compare (:328, now consumes audit's own check_undercount/build_*_key_map — no third impl). PURE check_undercount/check_overcount seams; main() calls both (no inline dup); two main()-level monkeypatch tests (inject undocumented sink / drop live sink) prove seam wiring through the real path — invert-test: if main() bypassed the seams they'd return 0 and both tests would fail. #2306 case pinned to live worktree_kitty/st.mission_slug at tasks_move_task.py:206 (+1 shift, cites #2306, green). Ghost-red fires through real main() (test_main_flags_ghost, green). 3 tokens spot-re-derived on lane tree match exactly incl. truncated review/cycle.py:231 (61ch, prefix unique per path+qualname). Validation: audit exit 0 (29 rows=24 discovered+5 inv-only), containment 12 passed, full tests/architectural/ 615 passed/4 skipped, mypy --strict clean on both owned files (46 whole-tree errs pre-existing in unrelated tests, not owned files), ruff clean. Diff scope clean: zero src/, surface_resolution_audit untouched, no --feature, no positive-literal scans, dropped dup review/cycle.py:225 justified in inventory header. ADJUDICATION [inventory-only] broadening (implementer deviation from data-model 'zero tags'): ACCEPT. All 5 tagged rows (mission_metadata.py:458 FR-009 meta.json write; aggregate.py:514/:762/:763 cross-fn diagnostics; decision.py:470 cross-fn load_meta) verified genuinely AST-undiscoverable — each sink absorbs the slug as a resolver-call arg or joins a constant filename, so discover_rows()'s one-hop-local taint cannot reach them; teaching the matcher cross-function taint is explicitly out of WP scope. Tag stays NARROW: each row names its reason (all pass test_inventory_only_rows_carry_a_documented_reason >20ch), overcount still fires on any untagged ghost (proven by DROPPING the stale review/cycle.py:225 dup rather than tagging it). CLOSEOUT NOTE: data-model.md should update the [inventory-only] semantics from 'intentionally-removed sink' to also cover 'known-false-negative class'; audit.py docstring + inventory header + T009 note already document the broadening.
