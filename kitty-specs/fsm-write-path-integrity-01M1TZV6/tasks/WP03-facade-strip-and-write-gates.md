---
work_package_id: WP03
title: Facade Strip + Write Gates
dependencies:
- WP01
requirement_refs:
- FR-010
- FR-011
planning_base_branch: missions/coreloop-proto-missions
merge_target_branch: missions/coreloop-proto-missions
branch_strategy: Planning artifacts for this mission were generated on missions/coreloop-proto-missions. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into missions/coreloop-proto-missions unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-fsm-write-path-integrity-01M1TZV6
base_commit: 7b90adcfdaf4ab5ef5229fa466bb6091f5769a07
created_at: '2026-09-06T13:22:29.137981+00:00'
subtasks:
- T015
- T016
- T017
- T018
- T019
phase: Wave 1 - Durability gates
agent: claude
history:
- at: '2026-09-06T11:57:59Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/status/
create_intent:
- src/specify_cli/status/_unsafe.py
- tests/architectural/test_status_unsafe_allowlist.py
- tests/architectural/test_status_events_writes_gate.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/status/__init__.py
- src/specify_cli/status/_unsafe.py
- tests/architectural/test_status_unsafe_allowlist.py
- tests/architectural/test_status_events_writes_gate.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP03 – Facade Strip + Write Gates

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

Check the `review_ref` field in the event log. Address every item before completion and log what changed.

## Review Feedback

*[Populated by the reviewer via the status event log.]*

---

## Objectives & Success Criteria

User Story 3 (P2). The gates make WP01/WP02/WP06 durable: without them the census decays (this mission's own census corrected a stale in-code claim and dropped a false positive).

Done means (SC-004):

1. The six `append_event*` names are no longer exported from `specify_cli.status` (`src/specify_cli/status/__init__.py:518-537`); they live in `src/specify_cli/status/_unsafe.py` behind `ALLOWED_CALLERS`.
2. `tests/architectural/test_status_unsafe_allowlist.py`: every `src/` module importing `_unsafe` is in `ALLOWED_CALLERS`; `ALLOWED_CALLERS ⊆ BASELINE` (shrink-only); non-vacuity floor.
3. `tests/architectural/test_status_events_writes_gate.py`: any write-mode open on a path ending `status.events.jsonl` outside `status/store.py` fails the build; positive census asserts the expected allowed sites are found; non-vacuity floor; `feature_status_lock` composition-site census (R14).
4. A synthetic out-of-pipeline writer reds each gate (proved by the floor tests); a gate whose scan matches zero writers reds itself.
5. The census-gate-rule note for #3895 is drafted in `design-notes/WP03-gates.md` (first instance of the rule; the operator posts it).

## Context & Constraints

- Spec US3, FR-010, FR-011, SC-004. Contract `contracts/write-gates.md` (all sections — it specifies the scanner rules and the floors). Data model §7.
- **Depends on WP01**: the allowlist is seeded from the fixed census. If WP06 has not landed when you start, `coordination/status_transition.py` may still hold `_prepare_event`; that does not affect raw appends (the transactional doors write via `BookkeepingTransaction`, family ③). Seed from what imports the primitives *now* and re-verify after WP06 lands (it must not add importers).
- Precedent for AST arch-gates: `tests/architectural/test_protection_resolver_call_sites.py` (call-site ratchet), `tests/architectural/test_status_module_boundary.py` (import scan, exemptions, shrinking ledger). Copy their scanning helpers' shape; do not import test helpers across files unless a shared `tests/architectural/_ast_helpers.py` already exists (check; if not, keep helpers local).
- **Non-vacuity is mandatory** (report 27 §3.3 pattern): a gate that matches nothing is a failing gate.
- Do not touch `status/store.py`; do not touch the writer modules (WP01 owns them) — the import repoint in T016 is a mechanical one-line change per file and is the ONE exception, logged as out-of-map with rationale "FR-010 repoint to _unsafe".
- Runtime ledger (`tests/architectural/test_layer_rules.py`): if any `src/runtime/**` module imports the primitives, the repoint must keep the same first-level subpackage edge (it will — `status` stays `status`).

## Branch Strategy

- **Strategy**: Planning artifacts were generated on missions/coreloop-proto-missions; completed changes must merge back into missions/coreloop-proto-missions.
- **Planning base branch**: missions/coreloop-proto-missions
- **Merge target branch**: missions/coreloop-proto-missions

Execution worktrees are allocated per computed lane from `lanes.json`; enter yours with `spec-kitty implement WP03`.

## Subtasks & Detailed Guidance

### Subtask T015 – Create `status/_unsafe.py`

- **Purpose**: FR-010 — explicit, enumerated raw-append access.
- **Steps**:
  1. Module docstring: why it exists (FSM sole authority; raw appends bypass validation), what is allowed (WP01 census families), the shrink-only rule, and the WP03 gate that enforces it.
  2. Re-export from `specify_cli.status.store`: `append_event`, `append_event_verified`, `append_event_stream_atomic_verified`, `append_events_atomic_verified`, `append_primary_checkout_event_verified`, `append_primary_checkout_events_atomic_verified` (confirm the exact six at `__init__.py:518-537` and `store.py:292-560`; include `append_raw_rows_atomic`, `append_annotations_atomic_verified`, and `append_event_stream_log` (used by `coordination/transaction.py:36`) — the set is "every raw append primitive a non-store module needs"; modules inside `status/` may keep importing `store` directly).
  3. `ALLOWED_CALLERS: frozenset[str]` of dotted module paths. Seed by running: `grep -rln "append_event\|append_raw_rows_atomic\|append_annotations_atomic_verified\|append_events_atomic" src --include='*.py'` and keeping only real importers (not docstring mentions — check each). Expected set (verify): `specify_cli.status.emit`, `specify_cli.status.lifecycle_events`, `specify_cli.coordination.transaction`, `specify_cli.retrospective.lifecycle_events`, `specify_cli.retrospective.events`, `specify_cli.migration.verdict_provenance_backfill`, `specify_cli.migration.backfill_runtime_state`, plus any `status/` sibling (`bootstrap.py`, `migrate*.py`) that appends. Every entry gets a one-line justification comment naming its census family.
- **Files**: `src/specify_cli/status/_unsafe.py` (new).
- **Parallel?**: No.

### Subtask T016 – Strip the facade; repoint importers

- **Purpose**: The public facade no longer offers raw appends.
- **Steps**:
  1. Remove the six names from `__all__` and from the import block in `status/__init__.py` (there is a provenance comment near `:518` referencing WP02 of `verdict-seam-boundary-hardening-01KZG179` — keep a short note pointing to `_unsafe` so the history is not lost).
  2. Repoint every allowed importer to `from specify_cli.status._unsafe import …` (one line each; out-of-map, rationale logged).
  3. `tests/`: any test importing the primitives from the facade must repoint too (grep `tests/` — allow tests to import `_unsafe` freely; the gate scans `src/` only).
  4. Run `tests/architectural/test_status_module_boundary.py` — the "residual allow-list" there may reference the facade names; adjust only if it reds and only minimally (out-of-map, rationale).
- **Files**: `src/specify_cli/status/__init__.py`, one-line repoints.
- **Parallel?**: No.

### Subtask T017 – Allowlist gate with non-vacuity floor

- **Purpose**: Shrink-only enforcement.
- **Steps**: `tests/architectural/test_status_unsafe_allowlist.py` (new):
  1. `BASELINE = frozenset({...})` committed in the test = the T015 set.
  2. `test_unsafe_importers_are_allowlisted`: AST-walk `src/**/*.py`; collect modules with `ImportFrom` whose module is `specify_cli.status._unsafe` (or `Import` of it); assert set ⊆ `ALLOWED_CALLERS`. **Bypass closure (analysis finding I1)**: ALSO treat any module *outside* `src/specify_cli/status/` that imports an `append_*` name from `specify_cli.status.store` directly as an `_unsafe` importer — `coordination/transaction.py:36` does exactly this (`append_event_stream_log`) and is exempt from `test_status_module_boundary.py`, so the facade strip alone cannot see it. Either repoint it to `_unsafe` (and add `append_event_stream_log` to T015's re-export list) or have the scanner count it; the test must fail if a boundary-exempt module gains a direct `store` append import.
  3. `test_allowlist_is_shrink_only`: `ALLOWED_CALLERS ⊆ BASELINE`.
  4. `test_allowlist_entries_are_live`: every `ALLOWED_CALLERS` entry actually imports `_unsafe` (stale entry ⇒ fail).
  5. Floors: `test_allowlist_gate_is_not_vacuous` — build a synthetic module source string that imports `_unsafe`, feed it to the same scanner function (factor the scanner to accept `(path, source)` pairs), assert the scanner reports it as a violation when its module path is not allowed; and assert `len(importers_found) >= 1` on the real tree.
- **Files**: `tests/architectural/test_status_unsafe_allowlist.py`.
- **Parallel?**: Yes (with T018).

### Subtask T018 – AST writes-gate with non-vacuity floor + lock-composition census

- **Purpose**: FR-011 / R14.
- **Steps**: `tests/architectural/test_status_events_writes_gate.py` (new), per `contracts/write-gates.md` §2–§3:
  1. Scanner: for each `src/**/*.py`, find `Call` nodes that are `open(...)`, `Path(...).open/write_text/write_bytes(...)`, `os.open(...)`; resolve the path argument statically (string constant, f-string joined parts, `Path(...) / "status.events.jsonl"`, or a `Name` assigned from such an expression in the same function); classify the mode (`"a"`, `"w"`, `O_APPEND|O_WRONLY|O_TRUNC`); a match is "path ends with `status.events.jsonl`" AND write mode. Allowed only in `src/specify_cli/status/store.py`.
  2. `test_no_out_of_store_writes`: violations == ∅.
  3. `test_store_writes_are_found` (positive census): the scanner finds ≥1 allowed write in `store.py` (exact expected count is fine but brittle; assert ≥1 and that each found site is in `store.py`).
  4. `test_writes_gate_is_not_vacuous`: synthetic source `p = root / "status.events.jsonl"; open(p, "a")` ⇒ one violation reported.
  5. Lock-composition census (R14): collect every `feature_status_lock(` call site in `src/`; assert the set of *modules* equals the expected census (`status/emit.py`, `status/lifecycle_events.py`, `coordination/transaction.py`, the four WP01 writer modules, `review/cycle.py`, `cli/commands/agent/tasks_verdict_persistence.py`, `merge/…` if WP01 added one, and any others you find — build the list from the tree and comment each). A new composition site anywhere else ⇒ fail with a message pointing to `contracts/emit-pipeline.md` §2.
  6. Unresolvable dynamic paths are NOT a pass: count them and assert the count equals a committed expected number (0 today unless you find some); explain in the test docstring.
- **Files**: `tests/architectural/test_status_events_writes_gate.py`.
- **Parallel?**: Yes.

### Subtask T019 – #3895 note draft + C-009 cleanup

- **Purpose**: Governance follow-through.
- **Steps**:
  1. `design-notes/WP03-gates.md`: the census-gate rule stated generally ("every enumerated census of writers/callers that a mission fixes ships an architectural gate seeded from that census, with a non-vacuity floor"), this WP as its first instance, the two gate nodeids, and the exact text to post on #3895 (the operator posts; do not call `gh` yourself unless the orchestrator instructs).
  2. Confirm no transitional xfail/red-first markers remain in your files.
  3. Run the full targeted suite (below) and record counts.
- **Files**: design note.
- **Parallel?**: No.

## Test Strategy

```bash
make test-fast
.venv/bin/pytest tests/status tests/specify_cli/status -q
.venv/bin/pytest tests/architectural/test_status_unsafe_allowlist.py tests/architectural/test_status_events_writes_gate.py tests/architectural/test_status_module_boundary.py tests/architectural/test_layer_rules.py -q
.venv/bin/ruff check src/specify_cli/status tests/architectural && .venv/bin/mypy src/specify_cli/status/_unsafe.py
```

## Risks & Mitigations

- **Vacuous gate** → floors in the same PR (T017/T018 step 5/4).
- **Brittle static path resolution** → assert the *unresolvable* count explicitly so silent misses are visible.
- **Repoint breaks an importer WP01 renamed** → land after WP01; if WP06 renames anything, re-verify (WP06 must not add raw appends).

## Review Guidance

- Facade: `from specify_cli.status import append_event` must now raise `ImportError` (add that as a test).
- Both floors present and green; both gates green on the real tree with ≥1 positive match.
- Allowlist entries each justified; no entry that does not import `_unsafe`.
- Lock-composition census lists exactly the shells + census writers.

## Activity Log

> **CRITICAL**: chronological order, oldest first. Format: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <action>`.

- 2026-09-06T11:57:59Z – system – Prompt created.
- 2026-09-06T14:04:11Z – claude – shell_pid=94026 – T015: created src/specify_cli/status/_unsafe.py re-exporting the 8 store append primitives with ALLOWED_CALLERS (8 modules) seeded from the real importers by AST scan, one census-family line each
- 2026-09-06T14:04:13Z – claude – shell_pid=94026 – T016: stripped the 8 raw append names from status/__init__ import block and __all__ with a provenance note; repointed 5 src importers (status_service x3 lines, retrospective/events, retrospective/lifecycle_events, migration/verdict_provenance_backfill, migration/backfill_runtime_state) and 14 test files to specify_cli.status._unsafe. Out-of-map (FR-010 repoint to _unsafe): those 5 src files. transaction.py NOT edited: at HEAD it imports the status_service wrapper, not the store; I1 closed by the scanner counting store/facade/wrapper doors and enumerating status_service + transaction
- 2026-09-06T14:04:14Z – claude – shell_pid=94026 – T016 out-of-map: tests/architectural/test_status_module_boundary.py carves out specify_cli.status._unsafe as the sanctioned door in _is_bypass_import/_is_status_submodule_name plus one pin test (otherwise SR-2 forces all five writers onto its exemption ledger); tests/architectural/test_no_dead_symbols.py gains category _CATEGORY_C_FSM_WRITE_PATH_UNSAFE_DOOR for _unsafe::ALLOWED_CALLERS (gate-facing) and _unsafe::append_event (contract re-export, test-only importers, module-path tier)
- 2026-09-06T14:04:16Z – claude – shell_pid=94026 – T017: tests/architectural/test_status_unsafe_allowlist.py — 4 door shapes scanned (I1 rule), BASELINE shrink-only, live-entry check, store append_* surface pinned, facade ImportError pin, 10-shape synthetic floor
- 2026-09-06T14:04:18Z – claude – shell_pid=94026 – T018: tests/architectural/test_status_events_writes_gate.py — AST write-site scanner incl. os.replace destinations, static path resolution incl. same-module call-site parameter resolution; store positive census (Path.open a + os.replace); 6-entry shrink-only out-of-store ledger; unresolved event-named pin (3) + known-dynamic pin (3); 13-module feature_status_lock census; 15-case synthetic floor. Gate surfaced two unlocked writers not in the WP01 census: decisions/emit.py:110 raw open(a) append (FINDING) and migration/rebuild_state.py:766 whole-log rewrite; ledgered with rationale, reported for follow-up
- 2026-09-06T14:04:20Z – claude – shell_pid=94026 – T019: design note written to the orchestrator scratch path (planning artifacts refused on lane branches) with the #3895 census-gate-rule text; no transitional markers in WP03 files. Baseline-red: test_ruff_format_enforcement is red on the merge-base (5 WP01 test files, none touched here)
