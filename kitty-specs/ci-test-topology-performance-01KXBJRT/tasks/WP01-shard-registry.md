---
work_package_id: WP01
title: Shard substrate → N-group registry
dependencies: []
requirement_refs:
- FR-002
tracker_refs: []
planning_base_branch: feat/ci-test-topology-performance
merge_target_branch: feat/ci-test-topology-performance
branch_strategy: Planning artifacts for this mission were generated on feat/ci-test-topology-performance. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/ci-test-topology-performance unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 1 - Substrate
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1254317"
shell_pid_created_at: "1783883745.81"
history:
- at: '2026-07-12T17:43:44Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/_arch_shard_map.py
create_intent:
- tests/_next_shard_map.py
- tests/architectural/test_next_shard_marker_completeness.py
execution_mode: code_change
model: ''
owned_files:
- tests/_arch_shard_map.py
- tests/_next_shard_map.py
- tests/conftest.py
- tests/architectural/test_arch_shard_marker_completeness.py
- tests/architectural/test_next_shard_marker_completeness.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Shard substrate → N-group registry

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

Check the `review_ref` field in the event log (`spec-kitty agent status`) before starting; address all feedback and log what changed in the Activity Log.

---

## Objectives & Success Criteria

FR-002 / C-003 / D-044 enabler: generalize the single-pole `tests/_arch_shard_map.py`
into an **N-group registry** (data-model E1) so `arch` (today's only pole) and
`next` (the new `integration-tests-next` pole) are two rows of *one* mechanism,
not a cloned second one.

Done means:

- `tests/_arch_shard_map.py` exposes a group-keyed registry — `group → roots,
  shard_count, marker_prefix, assignment` — with `arch`'s existing 3-shard
  assignment preserved **byte-for-byte** (no relpath moves shards).
- `tests/conftest.py`'s `pytest_collection_modifyitems` hook applies
  `<marker_prefix>_<n>` to every collected item under *any* registered group's
  roots, driven by iterating the registry, not a second hardcoded call site.
- A new `next` group is registered: `roots = ("tests/next", "tests/specify_cli/
  next", "tests/runtime")` (the exact paths `integration-tests-next` runs today,
  `.github/workflows/ci-quality.yml:2335`), `shard_count = 3`, `marker_prefix =
  "next_shard"`, and a **placeholder** balanced assignment — rebalanced later
  from WP06's `--durations=25` evidence (T014); do not treat it as final.
- `test_arch_shard_marker_completeness.py` proves GC-1 for `arch` is unaffected
  (still green, still driven by the registry).
- New `test_next_shard_marker_completeness.py` proves GC-1 for `next` (total
  partition + union = full pre-split universe over the 3 `next` roots).

**Independent test**: arch completeness guard green + `next` collectable via
`pytest --collect-only -q -m next_shard_1`.

## Context & Constraints

- Read FIRST: `data-model.md` §E1, `contracts/guard-contracts.md` §GC-1,
  `plan.md` §IC-01, `tasks.md` T001–T005.
- Today: `ARCH_SHARD_FILE_MAP` (per-file, `tests/architectural/*.py`),
  `ARCH_SHARD_DIR_MAP` (whole-dir units for `tests/adversarial`,
  `tests/architecture`, `tests/lint`), `POLE_ROOTS`, `shard_for(relpath) -> int
  | None`. `tests/conftest.py:19` imports it as `arch_shard_for`, called from
  `_apply_arch_shard_marker` (conftest.py:219-235) inside
  `pytest_collection_modifyitems` (conftest.py:202-216).
  `test_arch_shard_marker_completeness.py` imports `shard_map.POLE_ROOTS` /
  `shard_map.shard_for` (lines 35, 49-54) and reuses
  `_gate_coverage.collect_universe()` for its one shared `--collect-only` pass
  — keep reusing that helper.
- Only 4 files reference this module's public names: itself, `conftest.py`,
  `test_arch_shard_marker_completeness.py`, and a docstring-only mention in
  `tests/unit/test_descriptor_resolver.py` (explicitly needs no entry — do not
  touch it).
- **No cloning (D-044/C-003)**: `next` is a new row in the *same*
  registry/hook/guard engine. Prefer extracting the three assertion functions
  in `test_arch_shard_marker_completeness.py` into group-parametrized helpers
  (`group: str`) that `test_next_shard_marker_completeness.py` imports and
  calls with `group="next"` — proving both files are driven by one registry.
- Dependency root for WP02 (T006), WP06 (T014, T017), WP09 — this WP has no
  dependencies of its own.

## Branch Strategy

- **Strategy**: Coord-topology mission (`meta.json` `topology: "coord"`).
  Planning artifacts live on primary; implementation happens in the lane
  worktree `spec-kitty implement WP01` creates/reuses.
- **Planning base branch**: `feat/ci-test-topology-performance`
- **Merge target branch**: `feat/ci-test-topology-performance`

## Subtasks & Detailed Guidance

### Subtask T001 – Refactor `_arch_shard_map.py` into an N-group registry

- **Purpose**: Make `arch` a data row (data-model E1: `group`, `roots`,
  `shard_count`, `marker_prefix`, `assignment`).
- **Steps**: Introduce a `ShardGroup` dataclass/`TypedDict` with those 5
  fields; build `SHARD_GROUPS: dict[str, ShardGroup]` keyed `"arch"`/`"next"`.
  Assemble the `arch` row's `assignment` from the exact existing
  `_ARCH_SHARD_{1,2,3}_{DIRS,FILES}` tuples — pure reshaping, keep the
  provenance comments. Keep a public `shard_for(group: str, relpath: str) ->
  int | None` mirroring today's resolution order (dir roots, then file map,
  else `None` — never a fallback default shard).
- **Files**: `tests/_arch_shard_map.py`. **Parallel?**: No — T002/T003 depend
  on this shape.
- **Notes**: Module stays pure data + lookup — no pytest import, no side
  effects.

### Subtask T002 – Update `conftest.py`'s shard hook to iterate registered groups

- **Purpose**: One hook drives every group, not one hardcoded arch call.
- **Steps**: Generalize `_apply_arch_shard_marker` (conftest.py:219-235) into
  `_apply_shard_markers(item)` iterating `SHARD_GROUPS.values()`, applying
  `pytest.mark.<marker_prefix>_<n>` when a shard resolves. Update the
  `pytest_collection_modifyitems` call site (conftest.py:215). Leave the
  existing `windows_ci`/`quarantine` marking (conftest.py:210-214) untouched.
- **Files**: `tests/conftest.py`. **Parallel?**: No — depends on T001.
- **Notes**: A test outside every group's roots gets **zero** shard markers —
  this is exactly what GC-1 checks.

### Subtask T003 – Parametrize `test_arch_shard_marker_completeness.py` over the registry

- **Purpose**: Prove `arch`'s GC-1 invariants are registry-driven; stay green
  (regression guard).
- **Steps**: Extract the three test bodies (`test_pole_root_universe_is_
  nonempty`, `test_every_pole_root_test_has_exactly_one_shard_marker`,
  `test_shard_union_equals_full_pole_root_universe`) into helpers taking
  `group: str`; keep this file's tests calling them with `group="arch"` — same
  names, same `arch_shard_1/2/3` markers, same pole roots.
- **Files**: `tests/architectural/test_arch_shard_marker_completeness.py`.
  **Parallel?**: No — depends on T002 (RED until the hook applies markers,
  mirroring the file's own authored-failing discipline).
- **Notes**: Do not weaken either invariant while parametrizing.

### Subtask T004 – Add `_next_shard_map.py` (3-leg `next` registration)

- **Purpose**: Register `next` as the second data row (FR-002).
- **Steps**: New module registering `SHARD_GROUPS["next"]` (or the data
  `_arch_shard_map.py`'s builder merges in — keep `_arch_shard_map.py` arch-
  only, let this sibling own the `next` row). `roots = ("tests/next",
  "tests/specify_cli/next", "tests/runtime")`; `shard_count = 3`;
  `marker_prefix = "next_shard"`. Populate `assignment` with a **placeholder**
  balance (round-robin or a `def test_` count proxy, like arch's own greedy
  bin-pack) covering every eligible file — comment it as provisional pending
  WP06's durations evidence (T014).
- **Files**: `tests/_next_shard_map.py` (NEW). **Parallel?**: No — depends on
  T001's registry shape.
- **Notes**: Every relpath under the 3 roots lands in exactly one shard.
  Exclude `tests/specify_cli/` broadly — only its `next` subdirectory (the
  sibling `specify-cli-rest` shard already `--ignore`s it, ci-quality.yml:1622).

### Subtask T005 – Add `test_next_shard_marker_completeness.py`

- **Purpose**: GC-1 for the `next` group (FR-002).
- **Steps**: New file, `pytestmark = [pytest.mark.architectural]`, importing
  T003's group-parametrized helpers, calling them with `group="next"`. Keep a
  vacuity guard so an empty registration can never pass silently.
- **Files**: `tests/architectural/test_next_shard_marker_completeness.py`
  (NEW). **Parallel?**: `[P]` — independent of T003 once shared helpers exist.
- **Notes**: Must be RED until T002's hook applies `next_shard_N` markers.

## Test Strategy

```bash
PWHEADLESS=1 uv run pytest tests/architectural/test_arch_shard_marker_completeness.py -q
PWHEADLESS=1 uv run pytest tests/architectural/test_next_shard_marker_completeness.py -q

# Sanity: markers are actually collectable
uv run pytest --collect-only -q -m next_shard_1 tests/next tests/specify_cli/next tests/runtime
uv run pytest --collect-only -q -m arch_shard_1 tests/adversarial tests/architectural tests/architecture tests/lint

# Byte-stability spot-check: diff should be structural only, no relpath moving shard
git diff -- tests/_arch_shard_map.py

ruff check tests/_arch_shard_map.py tests/_next_shard_map.py tests/conftest.py \
  tests/architectural/test_arch_shard_marker_completeness.py \
  tests/architectural/test_next_shard_marker_completeness.py
uv run mypy tests/_arch_shard_map.py tests/_next_shard_map.py
```

## Risks & Mitigations

- **Silent arch reassignment during refactor.** Keep the original tuples
  verbatim; run the completeness guard before/after each step; eyeball the
  `git diff`.
- **`next` placeholder mistaken for final.** WP06/T014 rebalances from real
  durations; WP09 audits skew (NFR-006). Comment the placeholder as
  provisional; a complete, disjoint split is the bar now, not a balanced one.
- **Two guard engines instead of one (violates D-044/C-003).** The T003
  extraction into shared helpers is the concrete artifact to check for.
- **Hook scope creep.** A bug that stops respecting `roots` would silently
  mis-mark unrelated tests — keep the `shard_for(...) is None` assertion in
  both completeness guards.

## Review Guidance

- Arch assignment byte-for-byte unchanged (`git diff` reads as a pure reshape).
- `test_next_shard_marker_completeness.py` reuses the arch file's helpers, not
  a parallel copy (D-044/C-003 gate).
- `conftest.py` hook has zero hardcoded group names left (`for group in
  SHARD_GROUPS.values()`, not two near-identical `if` branches).
- Both completeness guards pass; `--collect-only -m next_shard_1` returns
  items (not vacuously empty).
- `next` placeholder documented as provisional (comment referencing WP06/T014).

## Activity Log

> Append at the END, chronological. Format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`

- 2026-07-12T17:43:44Z – system – Prompt created.
- 2026-07-12T18:56:02Z – claude:sonnet:python-pedro:implementer – shell_pid=1147954 – Assigned agent via action command
- 2026-07-12T19:14:57Z – claude:sonnet:python-pedro:implementer – shell_pid=1147954 – Ready: ruff check 0 issues (5 touched .py files); mypy tests/_arch_shard_map.py tests/_next_shard_map.py 0 issues (conftest.py/test files' mypy errors are pre-existing, outside my diff); pytest tests/architectural/test_arch_shard_marker_completeness.py tests/architectural/test_next_shard_marker_completeness.py -q -> 6 passed in 169.27s; arch pole still green + non-vacuous (368/326/353=1047 total, matches full pre-split universe, no gaps/dupes); next pole collectable+balanced (424/?/? of 1339, non-vacuous); git diff on _arch_shard_map.py shows byte-stable reshape (only 1 new line added: the new completeness-guard file itself, no existing relpath moved shard).
- 2026-07-12T19:15:48Z – claude:opus:reviewer-renata:reviewer – shell_pid=1254317 – Started review via action command
- 2026-07-12T19:26:26Z – user – shell_pid=1254317 – Review passed: registry generalized (not cloned), arch pole byte-stable + 1047 collect verified, next markers non-vacuous
