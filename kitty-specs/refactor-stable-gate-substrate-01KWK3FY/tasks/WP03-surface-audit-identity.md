---
work_package_id: WP03
title: Surface-resolution audit identity redesign
dependencies: []
requirement_refs:
- FR-004
tracker_refs: []
planning_base_branch: tidy/gate-substrate
merge_target_branch: tidy/gate-substrate
branch_strategy: Planning artifacts for this mission were generated on tidy/gate-substrate. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into tidy/gate-substrate unless the human explicitly redirects the landing branch.
subtasks:
- T012
- T013
- T014
- T015
phase: Phase 1 - Parallel substrate work
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1755024"
history:
- at: '2026-07-03T06:37:42Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/architectural/surface_resolution_audit/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- tests/architectural/surface_resolution_audit/audit.py
- tests/architectural/surface_resolution_audit/inventory.md
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP03 – Surface-resolution audit identity redesign

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

The surface twin of WP02 (spec FR-004, surface sub-stream) with two extras: BOTH row
types convert (`ResolutionRow` Check-2 at audit.py:526-534 AND the `SelectionRow`
"Check 4" at :549-561), and the audit module's PUBLIC SHAPE is preserved. **Squad
correction (rev 3 — the original split-brain premise was FALSE on this tree)**: the
resolver test does NOT read inventory.md — it imports `discover_rows` (:164) and
derives composite keys from the LIVE scan (:457/:464/:498); its seeds live in the
test file itself (docstring :15-19/:90-96 states the independence explicitly). The
REAL coupling this WP must not break is CODE: `ResolutionRow`/`SelectionRow` field
names (`rel_path`, `line`, `call_name`, `handle_source` / `rel_path`, `line`,
`call_name`, `in_seam_file`) and the `discover_rows()` signature. Success = the audit
triad for both row types (via real seams) + `test_single_mission_surface_resolver.py`
green and UNMODIFIED — which proves the public-shape guard, nothing more.

## Context & Constraints

Read FIRST:
- `contracts/audit-identity-contract.md` — rules 1-6; this WP owns rule 2's last two
  sites; rule 4 is REINTERPRETED per the rev-3 squad correction (public-shape guard,
  not inventory reconciliation).
- `research.md` D3 + **D9 errata** (current-tree truth: Check-2 :526-534 with raw
  compare :528; SelectionRow Check-4 :549-561, fields :353-356; the resolver test's
  independence).
- WP02's prompt for the shared recipe (identity, tag, overcount, triad) — the twins
  stay separate files but the DESIGN is identical; follow WP02's conventions exactly
  (same column naming, same tag syntax, same header language) so a future
  consolidation is mechanical.
- **READ-ONLY dependency**: `tests/architectural/test_single_mission_surface_resolver.py`
  — its `_RAW_JOIN_SITES` seeds read this inventory's line column. It must remain
  green with ZERO diffs (its family is Design-S by its own twin-guard design — see
  research D1; not this mission's to change).

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: tidy/gate-substrate
- **Merge target branch**: tidy/gate-substrate

## Subtasks & Detailed Guidance

### Subtask T012 – ResolutionRow + SelectionRow checks → composite

- **Steps**:
  1. Both row dataclasses gain the composite `key()` = `(rel_path, qualname, token)`
     via `composite_key_from_file` (same recipe as WP02's SinkRow).
  2. `main()` Check-2 (ResolutionRow, :529 region) AND the SelectionRow check (:549
     region) compare composite sets; messages keep live `rel:line` locators.
  3. Fail-closed parse of stored identities.
- **Files**: `tests/architectural/surface_resolution_audit/audit.py`.

### Subtask T013 – Re-key the surface inventory; preserve the module's public shape

- **Steps**:
  1. Re-key BOTH tables (ResolutionRow + SelectionRow) per the WP02 conventions:
     qualname+token columns added (tool-derived, recorded converter), `line` column
     retained as the non-authoritative locator.
  2. **Public-shape guard (the REAL coupling)**: do NOT rename or drop any
     `ResolutionRow`/`SelectionRow` field (the resolver test reads `row.rel_path`,
     `row.line`, `row.call_name`, `row.handle_source` off live `discover_rows()`
     output) and do NOT change `discover_rows()`'s signature. Adding methods (e.g.
     the composite `key()`) is fine.
  3. Header documents Design-P semantics + the freshen procedure.
  4. Proof: run `tests/architectural/test_single_mission_surface_resolver.py` green
     with `git diff` on that file EMPTY — this proves the public-shape/code coupling
     held (it says nothing about the inventory, by design).
- **Files**: `tests/architectural/surface_resolution_audit/inventory.md` (+ recorded
  converter).

### Subtask T014 – NEW overcount/ghost-row check (surface)

- **Steps**: Same as WP02's T010, for BOTH row types; `[inventory-only]` tag honored;
  zero tagged rows expected at conversion.
- **Files**: `audit.py`.

### Subtask T015 – Theater triad + resolver-test unmodified proof; validation

- **Steps**:
  1. The triad (drift-green / undocumented-red / ghost-red) for BOTH row types,
     driving the REAL path per the WP02 rule: pure `check_undercount`/`check_overcount`
     seams that `main()` calls, or monkeypatched `main()` invocation — helper-only
     theater is a REVIEW REJECT.
  2. The public-shape proof: `git diff tests/architectural/test_single_mission_surface_resolver.py`
     EMPTY + that file's suite green — pasted into the Activity Log.
  3. Validation: full `tests/architectural/` sweep; mypy --strict on audit.py (+ any
     test file that hosts the theater — check where the surface audit's tests live and
     put the triad beside them); ruff; whole-tree mypy unchanged at zero.
- **Files**: audit.py + the hosting test file.

## Test Strategy

```bash
export PATH="$PWD/.venv/bin:$PATH"; PYTHONPATH="$PWD/src"
PWHEADLESS=1 pytest tests/architectural/test_single_mission_surface_resolver.py -q -p no:cacheprovider  # UNMODIFIED green
PWHEADLESS=1 pytest tests/architectural/ -q -p no:cacheprovider
python -m mypy --strict tests/architectural/surface_resolution_audit/audit.py
ruff check tests/architectural/surface_resolution_audit/
```

## Risks & Mitigations

- **Breaking the resolver test's CODE coupling**: the tempting "line is now
  non-authoritative, drop/rename the field" move breaks `row.line` access in the
  resolver test — fields are frozen public shape; if the resolver test reds, you
  changed the module's importable surface: STOP and restore it.
- **The second table (SelectionRow) forgotten**: rule-2 explicitly names it; the
  triad parametrizes over both row types.
- **Convention drift from WP02**: follow WP02's exact column naming/tag syntax (both
  land in parallel — coordinate via the contract, which fixes the conventions; when in
  doubt the contract wins, not the sibling's in-flight choices).

## Review Guidance

- The resolver-test unmodified-green proof (empty diff + green run) is the headline.
- Triad drives real check functions, both row types.
- Spot-re-derive 3 rows per table.
- Conventions match the contract (and WP02's, once both are up).

## Activity Log

> Append at the END, chronological. Format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`

- 2026-07-03T06:37:42Z – system – Prompt created.
- 2026-07-03T07:12:03Z – claude:opus:python-pedro:implementer – shell_pid=1660876 – Assigned agent via action command
- 2026-07-03T07:42:27Z – claude:opus:python-pedro:implementer – shell_pid=1660876 – IC-03 surface-audit re-key complete. Both row types (ResolutionRow Check-2 + SelectionRow Check-4) now compare the (rel_path,qualname,token) composite via composite_key_from_file; NEW overcount/ghost tripwire (both types) via pure check_undercount/check_overcount seams main() calls; [inventory-only] tag + fail-closed parse. Inventory re-keyed via recorded converter rekey_inventory.py (tool-derived tokens; line non-authoritative). Public shape preserved (key()->str, fields, discover_rows sig unchanged) — test_single_mission_surface_resolver.py UNMODIFIED (empty diff) + green (18 passed). Theater triad (test_surface_resolution_audit.py, 16 tests) drives real path. Tallies: 33 sink rows (routed=14/topology-blind=17/raw-bypass=2), 3 read-SELECTION rows (all seam-internal). Gates: full tests/architectural/ 624 passed/4 skipped; mypy --strict clean; ruff clean; zero src/ changes.
- 2026-07-03T07:43:39Z – claude:opus:reviewer-renata:reviewer – shell_pid=1755024 – Started review via action command
- 2026-07-03T07:53:04Z – user – shell_pid=1755024 – Review passed: public-shape guard held (ResolutionRow/SelectionRow fields + key()->str untouched, composite_key() added as NEW method, discover_rows() sig unchanged); test_single_mission_surface_resolver.py EMPTY diff + 18 passed. Both row types drive real check_undercount/check_overcount seams via main() (no inline dup); triad non-vacuous (drift-green/undocumented-red/ghost-red + FR-006a external-red isolated). Converter tool-derived + --check idempotent (fresh). Zero [inventory-only] tags; 6/6 spot re-derivations match. Full tests/architectural/ 624 passed/4 skipped; mypy --strict clean (3 files); ruff clean. Zero src/ changes; WP02 lane files untouched.
