---
work_package_id: WP02
title: PackContext Three-State Extension
dependencies: []
requirement_refs:
- FR-031
- FR-039
tracker_refs: []
planning_base_branch: pr/charter-doctrine-mission-type-configuration
merge_target_branch: pr/charter-doctrine-mission-type-configuration
branch_strategy: Planning artifacts for this mission were generated on pr/charter-doctrine-mission-type-configuration. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/charter-doctrine-mission-type-configuration unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-charter-pack-activation-layer-01KSYE4V
base_commit: e2ef44089ea3e9c01168e48345c12b21899113ff
created_at: '2026-05-31T13:16:53.385303+00:00'
subtasks:
- T007
- T008
- T009
- T010
agent: "claude:sonnet-4-6:python-pedro:implementer"
shell_pid: "4073577"
history:
- at: '2026-05-31T11:44:22Z'
  event: created
  actor: claude
agent_profile: python-pedro
authoritative_surface: src/charter/pack_context.py
execution_mode: code_change
owned_files:
- src/charter/pack_context.py
- tests/charter/test_pack_context.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load the implementer profile:

```
/ad-hoc-profile-load python-pedro
```

You are implementing as **python-pedro** (Python implementer). Work precisely, make
only the changes described, validate after each subtask, and do not touch files
outside the `owned_files` list above.

---

## Objective

Extend `PackContext` — the frozen dataclass that carries all charter activation
state — from 2 `activated_*` fields to 10. The 8 new fields represent per-kind
activation sets for the remaining artifact kinds (directives, tactics, styleguides,
toolguides, paradigms, procedures, agent profiles, and mission step contracts). All
fields use **three-state semantics**: `None` (key absent from config — all built-ins
available), `frozenset()` (key present but empty list — nothing activated), or a
non-empty `frozenset[str]` (specific IDs activated).

This WP also fixes a pre-existing two-state bug in the existing two readers
(`_read_activated_kinds`, `_read_activated_mission_types`) where `[]` incorrectly
fell back to all built-ins instead of returning `frozenset()`.

This WP has no declared dependencies and runs in parallel with WP01. WP03 and
later WPs consume the new fields added here.

---

## Context

`PackContext` is defined in `src/charter/pack_context.py` as a
`@dataclass(frozen=True)`. It is **not** a Pydantic model. Do not use `Field()`,
validators, or any Pydantic construct in this file.

The current two `activated_*` fields are:
- `activated_kinds: frozenset[str] | None` — controls which artifact kind categories
  are activated at all
- `activated_mission_types: frozenset[str] | None` — controls which mission type
  IDs are activated

Both currently have a bug (FR-039): their reader functions guard with
`isinstance(raw, list) and raw`, meaning an empty list `[]` returns `None` (the
all-built-ins sentinel) rather than `frozenset()` (the explicitly-empty sentinel).
This WP fixes that bug and deletes the test that encoded the wrong behavior.

The 8 new fields follow the three-state contract consistently from the start.
Subsequent WPs (WP03, WP08, WP09, WP10) depend on these fields existing with
correct semantics.

---

## Branch Strategy

```
planning_base_branch: pr/charter-doctrine-mission-type-configuration
merge_target_branch:  pr/charter-doctrine-mission-type-configuration
```

All commits go directly onto `pr/charter-doctrine-mission-type-configuration` in
the lane worktree allocated by `finalize-tasks`. Do not create additional git
branches. Commit after completing T007+T008 together (they are a unit), then after
T009, then after T010.

---

## Subtasks

---

### T007 — Add 8 new `activated_*` fields to `PackContext` dataclass

**Requirement**: FR-031

**Purpose**: Extend the `PackContext` frozen dataclass with 8 new per-kind
activation fields, all defaulting to `None` (three-state: absent = all built-ins).

**Files**:
- `src/charter/pack_context.py`

**Steps**:

1. Open `src/charter/pack_context.py`. Find the `PackContext` dataclass definition.
   Locate the existing field:
   ```python
   activated_mission_types: frozenset[str] | None = None
   ```

2. Immediately after `activated_mission_types`, add the 8 new fields in this exact
   order:
   ```python
   activated_directives: frozenset[str] | None = None
   activated_tactics: frozenset[str] | None = None
   activated_styleguides: frozenset[str] | None = None
   activated_toolguides: frozenset[str] | None = None
   activated_paradigms: frozenset[str] | None = None
   activated_procedures: frozenset[str] | None = None
   activated_agent_profiles: frozenset[str] | None = None
   activated_mission_step_contracts: frozenset[str] | None = None
   ```

3. Because `PackContext` is `frozen=True`, all new fields must have default values
   (they do: `= None`). No other dataclass configuration is needed.

4. Verify the class still instantiates correctly with no arguments:
   ```bash
   cd /home/stijn/Documents/_code/SDD/fork/spec-kitty
   python -c "
   from charter.pack_context import PackContext
   from pathlib import Path
   pc = PackContext(pack_roots=(Path('.'),), repo_root=Path('.'))
   print('activated_directives:', pc.activated_directives)
   print('activated_agent_profiles:', pc.activated_agent_profiles)
   print('activated_mission_step_contracts:', pc.activated_mission_step_contracts)
   "
   ```
   Expected: all three print `None`.

**Validation**:
```bash
cd /home/stijn/Documents/_code/SDD/fork/spec-kitty
python -m mypy src/charter/pack_context.py --strict 2>&1 | tail -5
```
Expected: no errors on this file (or only pre-existing errors unrelated to the new
fields — but ideally zero).

---

### T008 — Add 8 per-kind reader functions + hook into `from_config()`

**Requirement**: FR-031

**Purpose**: Each of the 8 new fields needs a dedicated reader function that
deserializes the raw YAML value using the three-state contract. Hook all 8 readers
into `from_config()` so loading a config YAML populates the new fields.

**Files**:
- `src/charter/pack_context.py`

**Steps**:

1. Find the existing reader functions `_read_activated_kinds` and
   `_read_activated_mission_types` in `src/charter/pack_context.py`. Study their
   structure — you will follow the same pattern but with the three-state fix already
   applied (do not add `and raw`).

2. Add 8 new reader functions, one per kind, following this template exactly.
   Use `"activated_directives"` as the config key for `_read_activated_directives`,
   and so on — the config key must match the YAML key that operators write in
   `config.yaml`:

   ```python
   def _read_activated_directives(data: dict[str, Any]) -> frozenset[str] | None:
       raw = data.get("activated_directives")
       if raw is None:
           return None                              # absent key → all built-ins
       if isinstance(raw, list):
           return frozenset(str(x) for x in raw)   # [] → frozenset(), [x,y] → frozenset({x,y})
       return None                                  # malformed value → safe fallback
   ```

   Write the same pattern for all 8:
   - `_read_activated_directives` → key `"activated_directives"`
   - `_read_activated_tactics` → key `"activated_tactics"`
   - `_read_activated_styleguides` → key `"activated_styleguides"`
   - `_read_activated_toolguides` → key `"activated_toolguides"`
   - `_read_activated_paradigms` → key `"activated_paradigms"`
   - `_read_activated_procedures` → key `"activated_procedures"`
   - `_read_activated_agent_profiles` → key `"activated_agent_profiles"`
   - `_read_activated_mission_step_contracts` → key `"activated_mission_step_contracts"`

   Place these functions in the same section as the existing readers (near
   `_read_activated_kinds` and `_read_activated_mission_types`).

3. Find the `from_config()` class method. Locate where `activated_mission_types` is
   passed to the constructor (it will read:
   `activated_mission_types=_read_activated_mission_types(data),`). Immediately
   after it, add all 8 new reader calls:
   ```python
   activated_directives=_read_activated_directives(data),
   activated_tactics=_read_activated_tactics(data),
   activated_styleguides=_read_activated_styleguides(data),
   activated_toolguides=_read_activated_toolguides(data),
   activated_paradigms=_read_activated_paradigms(data),
   activated_procedures=_read_activated_procedures(data),
   activated_agent_profiles=_read_activated_agent_profiles(data),
   activated_mission_step_contracts=_read_activated_mission_step_contracts(data),
   ```

4. Smoke test `from_config()` with a minimal config:
   ```bash
   cd /home/stijn/Documents/_code/SDD/fork/spec-kitty
   python -c "
   import tempfile, pathlib, yaml
   from charter.pack_context import PackContext

   cfg = {'activated_directives': ['dir-001', 'dir-002'], 'activated_tactics': []}
   with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
       yaml.dump(cfg, f)
       name = f.name

   pc = PackContext.from_config(pathlib.Path(name), repo_root=pathlib.Path('.'))
   print('directives:', pc.activated_directives)   # frozenset({'dir-001', 'dir-002'})
   print('tactics:', pc.activated_tactics)          # frozenset()
   print('styleguides:', pc.activated_styleguides)  # None
   "
   ```

**Validation**:
```bash
cd /home/stijn/Documents/_code/SDD/fork/spec-kitty
python -m mypy src/charter/pack_context.py --strict 2>&1 | tail -5
pytest tests/charter/test_pack_context.py -x -v 2>&1 | tail -20
```
Both must pass. (Some tests added in T010 will be new; existing passing tests must
remain passing after T007+T008.)

---

### T009 — Fix FR-039: remove `and raw` guards; delete stale two-state test

**Requirement**: FR-039

**Purpose**: The existing `_read_activated_kinds` and `_read_activated_mission_types`
readers contain `and raw` guards that map an empty list `[]` to `None` (the
all-built-ins sentinel). This is wrong: an explicit `[]` must map to `frozenset()`
(the nothing-activated sentinel). Fix the guards and delete the test that encodes
the old wrong behavior.

**Files**:
- `src/charter/pack_context.py`
- `tests/charter/test_pack_context.py`

**Steps**:

1. Open `src/charter/pack_context.py`. Find `_read_activated_kinds` (around line
   197). The current code reads:
   ```python
   if isinstance(raw, list) and raw:
   ```
   Remove `and raw` so it becomes:
   ```python
   if isinstance(raw, list):
   ```
   This means an empty list `[]` now returns `frozenset()` instead of `None`.

2. Find `_read_activated_mission_types` (around line 210). Apply the identical fix:
   remove `and raw` from the `isinstance(raw, list) and raw:` guard.

3. Open `tests/charter/test_pack_context.py`. Search for the test named
   `test_empty_activated_kinds_uses_builtin_fallback` (or any test that asserts that
   `activated_kinds=[]` results in the built-in fallback set, not an empty
   frozenset). Delete that test entirely.
   ```bash
   grep -n "empty_activated_kinds" \
       /home/stijn/Documents/_code/SDD/fork/spec-kitty/tests/charter/test_pack_context.py
   ```
   Delete the entire test function (from `def test_empty_activated_kinds...` through
   its closing line).

4. Also search for any similar test covering `activated_mission_types`:
   ```bash
   grep -n "activated_mission_types.*builtin\|builtin.*activated_mission_types\|empty.*mission_types" \
       /home/stijn/Documents/_code/SDD/fork/spec-kitty/tests/charter/test_pack_context.py
   ```
   If a test asserts that an empty list for `activated_mission_types` falls back to
   built-ins, delete it too. Deleting is correct — it encodes wrong behavior. Do NOT
   update it to pass by changing the assertion; the correct action is deletion.

5. Verify the change is semantically correct:
   ```bash
   cd /home/stijn/Documents/_code/SDD/fork/spec-kitty
   python -c "
   import tempfile, pathlib, yaml
   from charter.pack_context import PackContext

   # Empty list must now produce frozenset(), not None
   cfg = {'activated_kinds': []}
   with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
       yaml.dump(cfg, f)
       name = f.name

   pc = PackContext.from_config(pathlib.Path(name), repo_root=pathlib.Path('.'))
   assert pc.activated_kinds == frozenset(), f'Expected frozenset(), got {pc.activated_kinds}'
   print('PASS: empty list → frozenset()')
   "
   ```

**ATDD enforcement**: `test_empty_activated_kinds_uses_builtin_fallback` MUST NOT
exist in the file after this subtask. Keeping it (even in a commented-out form)
is not acceptable — it encodes a behavioral contract that is now wrong and could
mislead future maintainers.

**Validation**:
```bash
cd /home/stijn/Documents/_code/SDD/fork/spec-kitty
grep -n "empty_activated_kinds_uses_builtin" tests/charter/test_pack_context.py
```
Expected: no output (test is gone).

```bash
pytest tests/charter/test_pack_context.py -x -v 2>&1 | tail -20
```
Expected: all remaining tests pass.

---

### T010 — Write/extend `test_pack_context.py` for three-state coverage

**Requirement**: FR-031, FR-039

**Purpose**: Add explicit tests that lock in the three-state contract for the new
per-kind fields and for the fixed existing fields. These tests serve as the ATDD
gate for all downstream WPs that consume the new fields.

**Files**:
- `tests/charter/test_pack_context.py`

**Steps**:

1. Open `tests/charter/test_pack_context.py`. Find a suitable location to add new
   tests — either at the end of the file or grouped with related `activated_*`
   tests.

2. Add tests for `activated_directives` covering all three states. Use `tmp_path`
   (pytest fixture) or a `tempfile` approach consistent with the existing test style
   in the file. Check how existing tests create a config file and call
   `PackContext.from_config()` — follow that exact pattern:

   ```python
   def test_activated_directives_absent_returns_none(tmp_path):
       """Absent key → None (all built-ins available)."""
       cfg = {}  # no "activated_directives" key
       config_file = tmp_path / "config.yaml"
       config_file.write_text(yaml.dump(cfg))
       pc = PackContext.from_config(config_file, repo_root=tmp_path)
       assert pc.activated_directives is None

   def test_activated_directives_empty_list_returns_empty_frozenset(tmp_path):
       """[] → frozenset() (explicitly nothing activated)."""
       cfg = {"activated_directives": []}
       config_file = tmp_path / "config.yaml"
       config_file.write_text(yaml.dump(cfg))
       pc = PackContext.from_config(config_file, repo_root=tmp_path)
       assert pc.activated_directives == frozenset()

   def test_activated_directives_populated_returns_frozenset(tmp_path):
       """Non-empty list → frozenset of IDs."""
       cfg = {"activated_directives": ["dir-001", "dir-002"]}
       config_file = tmp_path / "config.yaml"
       config_file.write_text(yaml.dump(cfg))
       pc = PackContext.from_config(config_file, repo_root=tmp_path)
       assert pc.activated_directives == frozenset({"dir-001", "dir-002"})
   ```

3. Repeat the same three-test pattern for `activated_agent_profiles`:
   ```python
   def test_activated_agent_profiles_absent_returns_none(tmp_path): ...
   def test_activated_agent_profiles_empty_list_returns_empty_frozenset(tmp_path): ...
   def test_activated_agent_profiles_populated_returns_frozenset(tmp_path): ...
   ```

4. Add a structural test that verifies all 10 `activated_*` fields exist on
   `PackContext` with the correct type:
   ```python
   def test_packcontext_has_all_ten_activated_fields(tmp_path):
       """Structural guard: all 10 activated_* fields exist with correct defaults."""
       config_file = tmp_path / "config.yaml"
       config_file.write_text("{}")
       pc = PackContext.from_config(config_file, repo_root=tmp_path)

       # Existing fields
       assert pc.activated_kinds is None
       assert pc.activated_mission_types is None

       # New fields (all default to None when key is absent)
       assert pc.activated_directives is None
       assert pc.activated_tactics is None
       assert pc.activated_styleguides is None
       assert pc.activated_toolguides is None
       assert pc.activated_paradigms is None
       assert pc.activated_procedures is None
       assert pc.activated_agent_profiles is None
       assert pc.activated_mission_step_contracts is None
   ```

5. Add a test that verifies the FR-039 fix on the existing `activated_kinds` field
   (the fix applied in T009):
   ```python
   def test_activated_kinds_empty_list_returns_frozenset_not_builtin_fallback(tmp_path):
       """FR-039 regression: [] must produce frozenset(), not built-in fallback."""
       cfg = {"activated_kinds": []}
       config_file = tmp_path / "config.yaml"
       config_file.write_text(yaml.dump(cfg))
       pc = PackContext.from_config(config_file, repo_root=tmp_path)
       assert pc.activated_kinds == frozenset()
       assert pc.activated_kinds is not None  # extra clarity: frozenset() != None
   ```

6. Ensure all new tests are marked correctly. Check the existing test marks in the
   file (look for `@pytest.mark.fast`, `@pytest.mark.doctrine`, etc.) and apply the
   same marks to all new tests. If existing tests use no marks, add none. Consistency
   is the goal.

**Validation**:
```bash
cd /home/stijn/Documents/_code/SDD/fork/spec-kitty
pytest tests/charter/test_pack_context.py -x -v 2>&1 | tail -30
```
Expected: all tests in the file pass. The count should have increased by at least
8 new tests (3 for `activated_directives`, 3 for `activated_agent_profiles`, 1
structural, 1 FR-039 regression). The deleted test from T009 should not appear.

```bash
pytest tests/charter/test_pack_context.py -v --collect-only 2>&1 | grep "activated"
```
Verify the new test names appear and the deleted test name does not.

---

## Definition of Done

- [ ] `pytest tests/charter/test_pack_context.py -x` exits 0 (all tests pass)
- [ ] `test_empty_activated_kinds_uses_builtin_fallback` does NOT appear anywhere in
      `tests/charter/test_pack_context.py` (confirmed via `grep`)
- [ ] `PackContext` has exactly 10 `activated_*` fields (2 existing + 8 new), all
      `frozenset[str] | None`, all defaulting to `None`
- [ ] `_read_activated_kinds` and `_read_activated_mission_types` no longer contain
      `and raw` guards — empty list maps to `frozenset()`
- [ ] All 8 new reader functions follow the three-state contract: absent→`None`,
      `[]`→`frozenset()`, `[x,y]`→`frozenset({x,y})`
- [ ] All 8 new readers are called in `from_config()` and populate the dataclass
- [ ] Three-state tests exist for at least `activated_directives` (3 tests) and
      `activated_agent_profiles` (3 tests)
- [ ] Structural test `test_packcontext_has_all_ten_activated_fields` passes
- [ ] FR-039 regression test for `activated_kinds` with empty list passes
- [ ] `ruff check src/charter/pack_context.py tests/charter/test_pack_context.py`
      passes (no new lint errors)
- [ ] `python -m mypy src/charter/pack_context.py --strict` passes

---

## Risks

- **`from_config()` signature drift.** If `PackContext.from_config()` uses
  `**kwargs` or a builder pattern rather than direct constructor arguments, the
  approach in T008 step 3 may need adaptation. Read `from_config()` fully before
  adding arguments.
- **Frozen dataclass field ordering.** In Python, `@dataclass(frozen=True)` with
  default values must have all fields with defaults placed after fields without
  defaults. The 8 new fields all have `= None` defaults, so they are safe to append
  after any non-default field. If you accidentally place them before a field without
  a default, Python will raise a `TypeError` at class definition time. Run the
  import probe in T007 step 4 to catch this immediately.
- **YAML import in tests.** If `tests/charter/test_pack_context.py` does not already
  import `yaml`, add `import yaml` (PyYAML) at the top. Check the existing imports
  first; if ruamel.yaml is used, use `from ruamel.yaml import YAML` and the
  appropriate write API to stay consistent.
- **`from_config()` does not accept `repo_root` as a keyword argument.** Inspect the
  actual signature of `PackContext.from_config()` before writing tests. If the
  second positional argument has a different name or is optional, adjust the test
  calls accordingly. All new tests should call the factory the same way existing
  tests call it.
- **Deleted test leaves a gap.** Deleting `test_empty_activated_kinds_uses_builtin_fallback`
  removes an assertion about fallback behavior. The T010 FR-039 regression test
  (`test_activated_kinds_empty_list_returns_frozenset_not_builtin_fallback`) is the
  replacement. Ensure that replacement test is written and passing before deleting
  the old test, so there is never a gap in coverage.

---

## Reviewer Guidance

Reviewers must verify:

1. **Three-state contract is complete**: `grep "and raw" src/charter/pack_context.py`
   returns no output. Both fixed readers use only `isinstance(raw, list):` without a
   truthiness guard.

2. **Deleted test is gone**: `grep "uses_builtin_fallback" tests/charter/test_pack_context.py`
   returns no output.

3. **10 fields on dataclass**: In `src/charter/pack_context.py`, count all
   `activated_*` fields in the `PackContext` class body. There should be exactly 10:
   `activated_kinds`, `activated_mission_types`, `activated_directives`,
   `activated_tactics`, `activated_styleguides`, `activated_toolguides`,
   `activated_paradigms`, `activated_procedures`, `activated_agent_profiles`,
   `activated_mission_step_contracts`.

4. **All readers wired in `from_config()`**: `grep "activated_" src/charter/pack_context.py`
   should show all 8 new reader calls inside the `from_config()` method body.

5. **Structural test passes**: The test
   `test_packcontext_has_all_ten_activated_fields` must be present and PASSED.

6. **FR-039 regression test passes**: The test
   `test_activated_kinds_empty_list_returns_frozenset_not_builtin_fallback` must be
   present and PASSED.

7. **mypy strict passes** on `src/charter/pack_context.py` — check CI output or run
   locally.

## Activity Log

- 2026-05-31T13:16:53Z – claude:sonnet-4-6:python-pedro:implementer – shell_pid=4073577 – Assigned agent via action command
