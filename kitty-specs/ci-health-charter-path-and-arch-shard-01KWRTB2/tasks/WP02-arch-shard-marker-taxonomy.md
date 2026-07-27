---
work_package_id: WP02
title: Arch-shard marker taxonomy + assignment table
dependencies: []
requirement_refs:
- FR-004
- FR-005
tracker_refs: []
planning_base_branch: tidy/ci-docs-charter-path-and-arch-adversarial-shard
merge_target_branch: tidy/ci-docs-charter-path-and-arch-adversarial-shard
branch_strategy: Planning artifacts for this mission were generated on tidy/ci-docs-charter-path-and-arch-adversarial-shard. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into tidy/ci-docs-charter-path-and-arch-adversarial-shard unless the human explicitly redirects the landing branch.
subtasks:
- T003
- T004
- T005
- T006
- T007
phase: Phase 1 - CI health fixes
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1775340"
history:
- at: '2026-07-05T10:59:34Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/_arch_shard_map.py
create_intent:
- tests/_arch_shard_map.py
- tests/architectural/test_arch_shard_marker_completeness.py
execution_mode: code_change
model: ''
owned_files:
- pytest.ini
- tests/_arch_shard_map.py
- tests/conftest.py
- tests/architectural/test_arch_shard_marker_completeness.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP02 – Arch-shard marker taxonomy + assignment table

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

## Review Feedback

*[If this WP was returned from review, the reviewer feedback reference appears in the Activity Log below or in the status event log.]*

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`,````bash`

---

## Objectives & Success Criteria

- The `arch-adversarial` CI job is today a single-shard matrix covering 802 tests across `tests/adversarial`, `tests/architectural`, `tests/architecture`, `tests/lint`, measured at 14.4 min. This WP builds the **marker mechanism** the next WP (WP03) will use to split it into 3 shards — the mechanism itself, not the workflow change.
- Success = three new `arch_shard_1/2/3` markers exist, registered canonically; a single-source assignment table maps every test-file/whole-directory unit under the 4 pole roots to exactly one shard; a collection-time hook applies the marker from that table; and a new completeness guard proves the partition is total (no gaps, no double-assignment, union = full pre-split universe).

## Context & Constraints

- Charter: `.kittify/charter/charter.md`.
- Mission plan: `kitty-specs/ci-health-charter-path-and-arch-shard-01KWRTB2/plan.md` (Concern B / IC-02), `research.md` (R2, R3), `data-model.md` (the concrete 216/215/215 assignment table — this is your seed data, not a suggestion to redesign), `spec.md` (FR-004, FR-005).
- **Operator decision (binding)**: N=3 shards minimum, whole-test-file/whole-directory slicing (never split a single file across shards), routed via dedicated pytest markers — not raw `--ignore` path lists (Decision Moment `DM-01KWRWB0PPF5TQPNYF5D07XY3W`).
- `tests/architectural/_gate_coverage.py` already models every CI selection gate generically as `Gate(paths, ignores, marker_expr)` and compiles `marker_expr` through pytest's own `Expression` engine — marker-expression-based shard selection is a first-class, already-supported case in this codebase's CI model. You are not inventing a new kind of thing; you are populating an existing pattern with new marker names.
- **Do not add a second `pytest_collection_modifyitems` function to `tests/conftest.py`.** One already exists (around line 198, applying `windows_ci` skip logic and the quarantine chokepoint). Pytest does not support two functions of the same name in one module — you must **extend the existing function's body**, not add a new one.
- pytest.ini's `markers` list (starting around line 14) is the single source of truth for marker registration (`test_marker_registry_single_source.py`, #2034) — do not add a competing `[tool.pytest.ini_options]` markers list to `pyproject.toml`.

## Branch Strategy

- **Strategy**: this WP owns `pytest.ini`, `tests/_arch_shard_map.py` (new), `tests/conftest.py`, `tests/architectural/test_arch_shard_marker_completeness.py` (new) — disjoint from WP01's single doc file. WP03 depends on this WP completing first.
- **Planning base branch**: `tidy/ci-docs-charter-path-and-arch-adversarial-shard`
- **Merge target branch**: `tidy/ci-docs-charter-path-and-arch-adversarial-shard`

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

## Subtasks & Detailed Guidance

### T003 – Register the three new markers in `pytest.ini`

- **Purpose**: Canonical registration so `--strict-markers` doesn't reject `arch_shard_1/2/3` and so the markers are discoverable the same way every other marker in this repo is.
- **Steps**:
  1. Open `pytest.ini`, find the `markers =` block (starts ~line 14).
  2. Add three new entries, each with a one-line description in the same style as existing entries (e.g. `docs_scoped`, `windows_ci`):
     ```
     arch_shard_1: arch-adversarial pole shard 1 of 3 (mission ci-health-charter-path-and-arch-shard-01KWRTB2, #2397) — assignment table in tests/_arch_shard_map.py
     arch_shard_2: arch-adversarial pole shard 2 of 3 (mission ci-health-charter-path-and-arch-shard-01KWRTB2, #2397) — assignment table in tests/_arch_shard_map.py
     arch_shard_3: arch-adversarial pole shard 3 of 3 (mission ci-health-charter-path-and-arch-shard-01KWRTB2, #2397) — assignment table in tests/_arch_shard_map.py
     ```
  3. Do not touch `[tool.pytest.ini_options]` in `pyproject.toml` (must stay markers-free per `test_marker_registry_single_source.py`).
- **Files**: `pytest.ini`.
- **Parallel?**: Yes, independent of T004.
- **Notes**: Keep alphabetical/thematic placement consistent with the surrounding entries if the file has an implicit ordering; otherwise append near `docs_scoped`/`windows_ci` since those are the other CI-topology-routing markers.

### T004 – Create the single-source shard-assignment table

- **Purpose**: One committed, editable source of truth for "which shard does this test-file/directory belong to" — the hook (T006) reads it; nothing else should duplicate it.
- **Steps**:
  1. Create `tests/_arch_shard_map.py` with a module docstring explaining its purpose and citing this mission.
  2. Define a `dict[str, int]` (or equivalent frozen mapping) keyed by **repo-root-relative path** (either a specific `.py` file under `tests/architectural/`, or one of the three whole directories `tests/adversarial`, `tests/architecture`, `tests/lint`), valued by shard number (1, 2, or 3).
  3. Seed it from the **exact** assignment already computed in `data-model.md` (216/215/215 split) — copy the three lists verbatim, do not re-derive a different split. If a new test file exists under `tests/architectural/` that isn't in `data-model.md`'s table (added between planning and now), assign it to whichever shard is currently lightest and note the addition in your Activity Log.
  4. Expose a small helper function, e.g. `shard_for(relpath: str) -> int | None`, that: (a) returns the exact shard for a whole-directory unit if the path starts with one of the three directory prefixes, (b) returns the exact shard for an exact file match otherwise, (c) returns `None` for anything outside the 4 pole roots (the hook must not mark unrelated tests).
- **Files**: `tests/_arch_shard_map.py` (new).
- **Parallel?**: Yes, independent of T003.
- **Notes**: Keep this file pure data + one lookup function — no pytest imports, no side effects, so it stays trivially unit-testable and reviewable as "just a table."

### T005 – Author the completeness guard, RED-first

- **Purpose**: Prove the partition is total (every test under the 4 pole roots gets exactly one `arch_shard_N` marker) and that the union equals the pre-split universe — by construction, not convention. This is the guard that closes the FR-005 gap the post-plan brownfield squad flagged.
- **Steps**:
  1. **Before** T006 wires the hook, write `tests/architectural/test_arch_shard_marker_completeness.py` and run it — it MUST fail at this point (no `arch_shard_*` marks exist yet on any collected test). Confirm the failure reason is "missing marker," not a collection error or import error — a red test for the wrong reason doesn't count as red-first.
  2. The guard should, in outline:
     - Use a single `--collect-only` pass (reuse `tests/architectural/_gate_coverage.py`'s `collect_universe()` helper if it fits, to avoid a second full collection walk — check its signature first).
     - For every collected test whose file path falls under `tests/adversarial`, `tests/architectural`, `tests/architecture`, or `tests/lint`, assert it carries **exactly one** of `arch_shard_1`/`arch_shard_2`/`arch_shard_3` (fail loudly, naming the offending node ID(s), on zero or on more than one).
     - Assert the union of the three marker-selected sets equals the full set collected under the 4 roots (no test falls outside all three).
  3. Record the RED failure output (test name + reason) in your Activity Log before proceeding to T006.
- **Files**: `tests/architectural/test_arch_shard_marker_completeness.py` (new).
- **Parallel?**: No — must be authored and confirmed RED before T006 makes it green; but you may draft it in parallel with T003/T004 as long as you don't run T006 first.
- **Notes**: Mirror the RED-first discipline documented in `test_arch_pole_deserialized.py`'s own docstring ("Authored FAILING against today's topology") — this repo has a strong convention for pinning that provenance in the module docstring. Do the same here.

### T006 – Extend the existing collection hook

- **Purpose**: Wire T004's table into real marker application at collection time, scoped to the 4 pole roots only.
- **Steps**:
  1. Open `tests/conftest.py` and locate the existing `pytest_collection_modifyitems(items: list[pytest.Item]) -> None:` function (around line 198). **Add to its body** — do not define a second function with the same name.
  2. Inside the existing loop over `items` (or a new loop in the same function, your choice, as long as it's the same function), for each item: derive its repo-root-relative test-file path, look it up via T004's `shard_for()` helper, and if it returns a shard number, `item.add_marker(pytest.mark.arch_shard_<N>)` (dynamically select the right mark object — do not hardcode three near-identical `if` branches if you can express it as one lookup + `getattr(pytest.mark, f"arch_shard_{n}")` or an explicit small dict of the three mark objects).
  3. Confirm nothing outside the 4 pole roots gets a mark (T004's `shard_for()` returning `None` for those paths is what guarantees this — do not add a fallback default shard).
  4. Run T005's guard again — it should now be GREEN. If it isn't, the failure output should tell you exactly which node IDs are unmarked or double-marked; fix `tests/_arch_shard_map.py` or the hook logic, not the guard.
- **Files**: `tests/conftest.py`.
- **Parallel?**: No — depends on T004 (needs the table) and gates T005 turning green.
- **Notes**: Keep the added logic small and close to the existing quarantine/windows_ci logic in style (a short loop, no new abstractions beyond what's needed).

### T007 – Local shard-reproduction verification

- **Purpose**: Prove the markers reproduce a genuine, disjoint, complete partition — not just that the completeness guard's own accounting says so, but that real `pytest -m` invocations behave as expected.
- **Steps**:
  1. Run each of the three shard-selection commands (adapt from `quickstart.md`, using `--collect-only -q` for speed):
     ```bash
     pytest tests/adversarial tests/architectural tests/architecture tests/lint -m 'arch_shard_1 and not windows_ci and (git_repo or integration or architectural)' --collect-only -q
     pytest tests/adversarial tests/architectural tests/architecture tests/lint -m 'arch_shard_2 and not windows_ci and (git_repo or integration or architectural)' --collect-only -q
     pytest tests/adversarial tests/architectural tests/architecture tests/lint -m 'arch_shard_3 and not windows_ci and (git_repo or integration or architectural)' --collect-only -q
     ```
  2. Confirm the three collected-count totals are each in the same ballpark as `data-model.md`'s 216/215/215 (exact test counts may differ slightly from the def-count proxy used for planning — that's expected; flag it in your Activity Log if any shard is wildly imbalanced, e.g. >2x another, as a heads-up for a future rebalance, but do not block this WP on it).
  3. Confirm zero overlap: no node ID should appear in more than one shard's collection output (spot-check, or diff the three `--collect-only` outputs).
  4. Confirm the sum of the three equals the full pre-split selection's collected count (`pytest tests/adversarial tests/architectural tests/architecture tests/lint -m 'not windows_ci and (git_repo or integration or architectural)' --collect-only -q`).
- **Files**: none changed (verification only).
- **Parallel?**: No — final verification step, depends on T005/T006.
- **Notes**: This is the same reproduction rule FR-004 requires locally and in CI — if it doesn't reproduce cleanly here, WP03's workflow-level split will inherit the same problem.

## Test Strategy

- `tests/architectural/test_arch_shard_marker_completeness.py` (new, T005) is the primary deliverable test — author RED-first, verify GREEN after T006.
- No other new tests are required for this WP; T007 is manual/local verification, not a new automated test (WP03's guards cover the workflow-level assertions).

## Risks & Mitigations

- **Risk**: Accidentally defining a second `pytest_collection_modifyitems` in `tests/conftest.py` (pytest silently only keeps one — or errors, depending on how it's structured — either way this is a real footgun). **Mitigation**: grep for the function name before editing; extend, don't duplicate.
- **Risk**: The hook marks tests outside the 4 pole roots. **Mitigation**: T004's `shard_for()` returning `None` outside those roots, and T005's guard scoping its assertions to exactly those 4 roots, together catch this.
- **Risk**: `test_marker_job_completeness.py`'s live re-derivation doesn't yet see `arch_shard_1/2/3` as ROUTED-BY-MARKER (no CI job selects them yet — that's WP03). **Mitigation**: this is expected and fine at WP02 time (WP03 wiring the workflow's `-m` expression is what makes them ROUTED-BY-MARKER); do not modify `test_marker_job_completeness.py`'s ledger in this WP.

## Review Guidance

- Confirm `test_arch_shard_marker_completeness.py`'s RED-first failure output is documented in the Activity Log (not just claimed).
- Confirm `tests/conftest.py` has exactly one `pytest_collection_modifyitems` function after this WP, with the new logic integrated into it (diff should show an addition inside the existing function, not a new function).
- Confirm `tests/_arch_shard_map.py`'s table matches `data-model.md`'s assignment (or documents any deviation with a stated reason).
- Confirm `pytest.ini`'s three new marker entries follow the existing description style.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

### How to Add Activity Log Entries

**When adding an entry**:

1. Scroll to the bottom of this Activity Log section
2. **APPEND the new entry at the END** (do NOT prepend or insert in middle)
3. Use exact format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`
4. Timestamp MUST be current time in UTC (check with `date -u "+%Y-%m-%dT%H:%M:%SZ"`)
5. Agent ID should identify who made the change (claude-sonnet-4-5, codex, etc.)

**Format**:

```
- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <brief action description>
```

**Common mistakes (DO NOT DO THIS)**:

- Adding new entry at the top (breaks chronological order)
- Using future timestamps (causes acceptance validation to fail)
- Inserting in middle instead of appending to end

**Why this matters**: The acceptance system reads the LAST activity log entry as the current state. If entries are out of order, acceptance will fail even when the work is complete.

**Initial entry**:

- 2026-07-05T10:59:34Z – system – Prompt created.

---

### Updating Status

Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task WP02 --to <status>` to change WP status.
- 2026-07-05T11:27:46Z – claude:opus:python-pedro:implementer – shell_pid=1745713 – Assigned agent via action command
- 2026-07-05T11:43:29Z – claude:opus:python-pedro:implementer – shell_pid=1745713 – T003/T004 done: registered arch_shard_1/2/3 in pytest.ini; created tests/_arch_shard_map.py seeded verbatim from data-model.md's 216/215/215 table (89 architectural files + 3 whole-directory pole roots); verified programmatically the 89-file table matches exactly the 89 non-infra .py files present in tests/architectural/ today (zero drift).
- 2026-07-05T11:43:36Z – claude:opus:python-pedro:implementer – shell_pid=1745713 – T005 RED-FIRST: authored tests/architectural/test_arch_shard_marker_completeness.py (reuses _gate_coverage.collect_universe(), no second collection walk) BEFORE wiring T006's hook. Ran it: 2 failed, 1 passed. test_pole_root_universe_is_nonempty passed (real tests exist under the 4 roots); test_every_pole_root_test_has_exactly_one_shard_marker failed with '861 pole-root test(s) carry NO arch_shard_N marker'; test_shard_union_equals_full_pole_root_universe failed with '861 pole-root test(s) are collected but selected by NO arch_shard_N marker'. Failure reason confirmed as missing-marker (not a collection/import error) -- RED for the right reason.
- 2026-07-05T11:43:42Z – claude:opus:python-pedro:implementer – shell_pid=1745713 – T006: extended the EXISTING pytest_collection_modifyitems in tests/conftest.py (grepped first -- confirmed only one definition, still exactly one after) via a new helper _apply_arch_shard_marker(item) called inside the existing per-item loop; looks up shard_for() and applies getattr(pytest.mark, f'arch_shard_{shard}') dynamically, no fallback default shard. First re-run of the guard still had 3 residual failures: the guard's own new test file wasn't yet in data-model.md's table (created after planning). Per data-model.md's documented gap rule, added it to arch_shard_2 (lightest by file count, 29 vs 30/30) with an inline rationale comment. Second re-run: GREEN -- 3 passed in 71.15s.
- 2026-07-05T11:43:49Z – claude:opus:python-pedro:implementer – shell_pid=1745713 – T007 local shard-reproduction verification (--collect-only -q over tests/adversarial tests/architectural tests/architecture tests/lint): shard_1=248, shard_2=241, shard_3=316; sum=805 exactly matches the full pre-split selection's collected count (805/861, 56 deselected). Zero overlap confirmed via sorted node-ID diffs across all 3 pairs (0 common lines each). Heads-up (non-blocking): real per-test counts drift further from the 216/215/215 def-count proxy than planned -- shard_3 is ~1.31x shard_2, well under the >2x rebalance trigger; no rebalance performed, table remains a single editable source for a cheap post-merge rebalance per R2/data-model.md.
- 2026-07-05T11:43:55Z – claude:opus:python-pedro:implementer – shell_pid=1745713 – Lint sweep: ruff check tests/_arch_shard_map.py tests/conftest.py tests/architectural/test_arch_shard_marker_completeness.py -> All checks passed! mypy --strict tests/_arch_shard_map.py -> Success (bonus check; confirmed via .github/workflows/ci-quality.yml that the blocking mypy gate only covers src/specify_cli src/charter src/doctrine, so tests/ is outside the enforced mypy surface). Committed as beb476003. All 5 subtasks (T003-T007) marked done.
- 2026-07-05T11:44:06Z – claude:opus:python-pedro:implementer – shell_pid=1745713 – Ready for review: markers registered, assignment table + hook wired, completeness guard authored RED-first and now GREEN, shard counts verified balanced with zero overlap
- 2026-07-05T11:44:41Z – claude:opus:reviewer-renata:reviewer – shell_pid=1775340 – Started review via action command
- 2026-07-05T11:51:59Z – user – shell_pid=1775340 – Review passed: markers/table/hook/guard verified live — completeness guard GREEN (3 passed), shard collect-only counts 248+241+316=805 exactly match full selection, zero overlap confirmed, table matches data-model.md verbatim plus one documented gap-fill addition, exactly one pytest_collection_modifyitems in conftest.py, pyproject.toml untouched, ruff/mypy clean, FR-004/FR-005 genuinely satisfied.
