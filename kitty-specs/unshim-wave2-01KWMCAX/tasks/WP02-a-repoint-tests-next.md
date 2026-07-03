---
work_package_id: WP02
title: 'A-repoint cluster 1: tests/next/ (proof-heavy)'
dependencies:
- WP01
requirement_refs:
- FR-002
tracker_refs:
- '#'
- '2'
- '2'
- '9'
- '1'
planning_base_branch: tidy/unshim-wave2
merge_target_branch: tidy/unshim-wave2
branch_strategy: Planning artifacts for this mission were generated on tidy/unshim-wave2. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into tidy/unshim-wave2 unless the human explicitly redirects the landing branch.
subtasks:
- T004
- T005
- T006
phase: Phase 1 - Sequential DAG
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2859363"
history:
- at: '2026-07-03T17:18:34Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/next/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- tests/next/
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP02 – A-repoint cluster 1: tests/next/ (proof-heavy)

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

Spec FR-002 (IC-02, cluster 1): re-point the `tests/next/` directory — **18 files,
243 plain-import refs, 125 patch-string sites** (the mission's proof-heavy block) —
from `specify_cli.next*` to `runtime.next*`. Success = zero legacy refs in
`tests/next/`, all 125 ledger rows carry proofs, suite green.

Read FIRST: spec.md Stream A census; occurrence_map.yaml is the BINDING site list
(`tests_fixtures.patch_string_sites` filtered to your files + `import_paths.plain_import_files_next`).
NOTE: many patch-string targets sit on WRAPPED CONTINUATION LINES (83 mission-wide) —
grep single-line and you WILL miss sites; work from the ledger, not from grep.

## Subtasks & Detailed Guidance

### Subtask T004 – Plain-import re-points (243 refs)
- Mechanical `specify_cli.next` → `runtime.next` in import statements only. Wrong re-points fail loud at collection — run each file after editing.

### Subtask T005 – 125 patch-string sites + proofs
- Per ledger row: rewrite the target string to the canonical namespace the CONSUMER resolves (for `runtime_bridge` symbols exercised through `next_cmd`, remember the seam now lives at `runtime.next.runtime_bridge`); then prove interception per site: existing/added call-consumption assertion OR red-first bogus-target flip. **Ledger protocol (FR-002)**: every patch-string site you rewrite gets its proof recorded TWICE: (a) a row in this WP file's Activity Log table `file:line → new target → proof form (assertion file::test | red-first flip) → outcome`, and (b) the orchestrator syncs your table into `occurrence_map.yaml`'s `interception_proof` fields on the planning branch at approval (the lane guard blocks kitty-specs edits on lanes — do NOT edit the map yourself from the lane). A site without a proof row is a review reject; bulk sed is a review reject.
- Batch by file; run each file's tests after its batch.

### Subtask T006 – Gates
- `PWHEADLESS=1 pytest tests/next/ -q` green; `grep -rn "specify_cli\.next" tests/next/` empty (paste); ruff diff-scoped; commit with the proof-table pointer in the handoff note.

## Test Strategy
```bash
export PATH="$PWD/.venv/bin:$PATH"
PWHEADLESS=1 pytest tests/next/ -q -p no:cacheprovider
grep -rn "specify_cli.next" tests/next/ || echo CLEAN
```

## Risks & Mitigations
- Silent no-op mocks: the shim STILL EXISTS in your WP (deletion is WP04) so a wrong target may pass via alias identity — the red-first flip (bogus target → red) is the only reliable proof form for sites without call assertions.

## Review Guidance
- Sample ≥10 ledger rows across ≥5 files: re-derive the target, check the proof evidence exists and is load-bearing.
- Any patch-string in the diff without a ledger proof row = reject. Bulk sed shape (single mechanical commit with no proof table) = reject.

## Activity Log

> Append at the END, chronological. Format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`

- 2026-07-03T17:18:34Z – system – Prompt created.
- 2026-07-03T18:04:37Z – claude:opus:python-pedro:implementer – shell_pid=2800175 – Assigned agent via action command
- 2026-07-03T18:24:10Z – claude:opus:python-pedro:implementer – shell_pid=2800175 – FR-002 tests/next re-point: 18 files, 373 refs specify_cli.next->runtime.next. 125 patch-string proof rows in /tmp/wave2-proofs-WP02.yaml. Interception: 26/26 target classes RED-flip proven (bogus-attr on canonical runtime.next path -> named test FAIL, suffix restored -> green); 99 sites cite enclosing-test consumption assertions. KEY: specify_cli.next.runtime_bridge IS the same module object as runtime.next.runtime_bridge (sys.modules alias) so old-path flip is a no-op -> bogus-attr flip is the only valid proof form (matches ledger Risks note). Gates: tests/next 497 passed; arch shim gates (shim_registry_schema+unregistered_shim_scanner) 44 passed; residual specify_cli.next CLEAN (multi-line/AST-checked); diff-scoped ruff exit 0; mypy src Success 1058 files.
- 2026-07-03T18:24:48Z – claude:opus:reviewer-renata:reviewer – shell_pid=2859363 – Started review via action command
- 2026-07-03T18:33:55Z – user – shell_pid=2859363 – Review PASSED (forced past #2324 shared-file guard: the only blocking dirt is occurrence_map.yaml + WP03/WP06 task files = WP03's parallel in-flight proof-sync, 72/72 added interception_proof lines WP03-labeled, ZERO WP02 content; not committing/reverting another WP's work). Verified: aliasing a is b=True so bogus-attr flip is the correct proof form; 3 non-first-site adversarial flips RED on canonical runtime.next module (test_mission_run_back_reference.py:398 _map_runtime_decision; test_query_mode_unit.py:96 query_current_state; test_prompt_file_invariant.py:77 build_prompt), baselines green, tree restored clean, per-class extrapolation holds; commit 1c51f6733 diff pure 373/373 (only specify_cli.next->runtime.next), no BOGUSFLIP residue, residual specify_cli.next=[]; WP02 own commit disjoint (18 tests/next/ files; the 4 src/test_selector files are WP01 dep-propagation e2ad484ef, no WP03 tests/specify_cli/next); gates green: tests/next 497 passed, arch shim pair 44 passed, ruff clean.
