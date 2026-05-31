---
work_package_id: WP07
title: Consistency Check Implementation
dependencies:
- WP03
- WP04
requirement_refs:
- FR-011
- FR-012
tracker_refs: []
planning_base_branch: pr/charter-doctrine-mission-type-configuration
merge_target_branch: pr/charter-doctrine-mission-type-configuration
branch_strategy: Planning artifacts for this mission were generated on pr/charter-doctrine-mission-type-configuration. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/charter-doctrine-mission-type-configuration unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-charter-pack-activation-layer-01KSYE4V
base_commit: 22934670e9f6723c3bd058a779fd4ce2b11921bd
created_at: '2026-05-31T14:19:40.561406+00:00'
subtasks:
- T030
- T031
- T032
- T033
agent: "claude:sonnet-4-6:reviewer-renata:reviewer"
shell_pid: "95404"
history:
- at: '2026-05-31T11:44:22Z'
  event: created
  actor: claude
agent_profile: python-pedro
authoritative_surface: src/charter/consistency_check.py
execution_mode: code_change
owned_files:
- src/charter/consistency_check.py
- tests/charter/test_consistency_check.py
role: implementer
tags: []
---

## Do This First: Load Agent Profile

Before reading anything else, load the implementer profile:

```
/ad-hoc-profile-load python-pedro
```

You are implementing as **python-pedro** (Python implementer). Work precisely, fix
only what is described, run validation after each subtask, and do not touch files
outside the `owned_files` list above.

---

## Objective

Implement `run_consistency_check(ctx: ProjectContext) -> ConsistencyReport` in
`src/charter/consistency_check.py`. The function inspects the project's activated
artifact IDs against the doctrine, the DRG edge graph, and the activation sets
themselves for duplicate and kind-violation defects. The result is a frozen
`ConsistencyReport` dataclass consumed by `charter pack consistency-check` (WP06)
and by tests.

WP template scanning is **explicitly out of scope** for this WP.

This WP depends on WP04 (for `CharterPackManager`, `YAML_KEY_MAP`, `default.yaml`,
and `DoctrineReader`) and WP03 (for `ProjectContext` and `require_pack_context()`).
Both must be in `approved` or `done` before you start.

---

## Context

`charter pack consistency-check` (registered in WP06) calls
`run_consistency_check(ctx)` and formats the returned `ConsistencyReport` for the
user. The report surfaces three categories of problems:

1. **Unknown references** — an activated ID is not present in the project's doctrine
   for that kind. This is the most common defect after partial pack imports or manual
   config edits.

2. **Missing from doctrine** — an activated ID is referenced by another activated
   artifact via a DRG edge, but the referenced ID does not appear in its own
   activation set. The report suggests running `charter activate <kind> <id>` or
   using `--cascade`.

3. **Kind violations** — an ID appears in the wrong kind's activation set (e.g., a
   directive ID listed under `activated_tactics`).

Duplicate detection is a subset of kind violations: if the same ID appears twice in
a set, it is recorded as a `kind_violations` entry.

**Performance**: the function MUST complete on the built-in doctrine pack within 2
seconds on developer hardware (NFR-003). Avoid repeated full-doctrine loads; load
once at the start of the function.

---

## Branch Strategy

```
planning_base_branch: pr/charter-doctrine-mission-type-configuration
merge_target_branch:  pr/charter-doctrine-mission-type-configuration
```

All commits go directly onto `pr/charter-doctrine-mission-type-configuration`. Do not
create additional git branches.

---

## Requirement Refs

FR-011, FR-012, NFR-003

---

## Subtasks

---

### T030 — Create `consistency_check.py` with ConsistencyReport and basic unknown-reference check

**Requirement refs**: FR-011, NFR-003

**Files**:
- `src/charter/consistency_check.py` (new)

**Steps**:

1. Read the following files before writing a line:
   - `src/charter/pack_manager.py` — understand `CharterPackManager`, `YAML_KEY_MAP`,
     and how activation sets are read.
   - `src/charter/pack_context.py` — understand `PackContext` fields for the 9 kinds.
   - WP03 delivery for `ProjectContext.require_pack_context()` — understand how to
     obtain a `PackContext` from a `ProjectContext`.

2. Create `src/charter/consistency_check.py`. Start with the module docstring and
   imports, then define `ConsistencyReport`:

   ```python
   """Charter pack consistency check — validates activated artifact IDs (FR-011)."""

   from __future__ import annotations

   import json
   from dataclasses import dataclass, field

   from charter.pack_context import PackContext
   from charter.invocation_context import ProjectContext


   @dataclass(frozen=True)
   class ConsistencyReport:
       """Result of a consistency check against activated doctrine artifacts.

       Attributes:
           coherent: True when no unknown references, missing cross-references,
               kind violations, or duplicates were found.
           unknown_references: IDs activated for a kind that do not exist in doctrine.
           missing_from_doctrine: IDs referenced by DRG edges but absent from the
               target kind's activation set.
           kind_violations: IDs that appear in the wrong kind's activation set, or
               duplicate IDs within a single activation set.
           suggestions: Human-readable resolution instructions for each finding.
       """

       coherent: bool
       unknown_references: list[str] = field(default_factory=list)
       missing_from_doctrine: list[str] = field(default_factory=list)
       kind_violations: list[str] = field(default_factory=list)
       suggestions: list[str] = field(default_factory=list)

       def to_json(self) -> str:
           """Serialise to a JSON string (FR-011 JSON output surface)."""
           return json.dumps(
               {
                   "coherent": self.coherent,
                   "unknown_references": self.unknown_references,
                   "missing_from_doctrine": self.missing_from_doctrine,
                   "kind_violations": self.kind_violations,
                   "suggestions": self.suggestions,
               },
               indent=2,
           )
   ```

3. Implement the main function signature:

   ```python
   def run_consistency_check(ctx: ProjectContext) -> ConsistencyReport:
       """Run a full consistency check for the project's activated charter pack.

       Checks:
         - Unknown references (activated IDs absent from doctrine).
         - Cross-kind DRG edge references (referenced IDs absent from their kind's set).
         - Kind violations and duplicate IDs within activation sets.

       WP template scanning is explicitly out of scope.

       Args:
           ctx: The project context, used to resolve PackContext and doctrine.

       Returns:
           A frozen ConsistencyReport with coherence flag and categorised findings.
       """
   ```

4. In the function body, start with basic unknown-reference detection:

   a. `pack_context = ctx.require_pack_context()` — obtain the `PackContext`.

   b. Load the project's doctrine reader once. Use
      `CharterPackManager().list_available(ctx, kind)` (delivered by WP04) to retrieve
      the full set of known doctrine IDs for a given kind. Read
      `src/charter/pack_manager.py` first to confirm the exact signature and return
      type. If the method name differs from `list_available`, adapt — do not guess.

   c. For each CLI kind name in `YAML_KEY_MAP` (all 9):
      - Get the activated IDs for this kind from `pack_context` (use the relevant
        field). If the field is `None`, skip this kind (no explicit activation →
        backward-compat; nothing to validate).
      - Get the full set of known IDs for this kind from doctrine.
      - For each activated ID **not** in the known set:
        - Append `f"{kind}/{activated_id}"` to `unknown_references`.
        - Append `f"{kind}/{activated_id}: Not found in doctrine. Run 'charter deactivate {kind} {activated_id}' to remove."` to `suggestions`.

   d. After collecting all findings:
      ```python
      coherent = not (unknown_references or missing_from_doctrine or kind_violations)
      return ConsistencyReport(
          coherent=coherent,
          unknown_references=unknown_references,
          missing_from_doctrine=missing_from_doctrine,
          kind_violations=kind_violations,
          suggestions=suggestions,
      )
      ```

**Validation**:
```bash
cd /home/stijn/Documents/_code/SDD/fork/spec-kitty
python -c "
from charter.consistency_check import ConsistencyReport, run_consistency_check
r = ConsistencyReport(coherent=True)
print('coherent:', r.coherent)
print('json:', r.to_json()[:40])
print('import ok')
"
```
Expected: prints `coherent: True` and a JSON snippet, no errors.

---

### T031 — Cross-kind DRG-edge reference validation

**Requirement refs**: FR-012

**Files**:
- `src/charter/consistency_check.py`

**Steps**:

1. Read `src/charter/drg.py` to understand:
   - The `filter_graph_by_activation()` function (or equivalent) that returns a
     filtered DRG containing only edges involving activated nodes.
   - How to iterate over DRG edges to find cross-kind references.
   - The kinds that carry DRG edges (Pattern A: `directive`, `tactic`, `styleguide`,
     `toolguide`).

2. Extend `run_consistency_check()` with DRG edge traversal. After the
   unknown-reference loop, add:

   ```python
   # Cross-kind DRG-edge reference validation (FR-012)
   # Pattern A kinds carry edges to other kinds in the DRG.
   _DRG_SOURCE_KINDS = {"directive", "tactic", "styleguide", "toolguide"}

   # Load the DRG: read src/charter/context.py (_load_action_doctrine_bundle) and
   # src/charter/drg.py to find the correct load path available in this charter
   # module. filter_graph_by_activation is in charter.drg.
   # Example pattern (adapt to actual API):
   #   from charter.drg import filter_graph_by_activation
   #   drg = _load_drg_for_consistency_check(ctx)  # helper you define after reading the API
   activated_drg = filter_graph_by_activation(drg, pack_context)

   for edge in activated_drg.edges():
       source_kind = edge.source_kind
       target_kind = edge.target_kind
       target_id = edge.target_id
       source_id = edge.source_id

       if source_kind not in _DRG_SOURCE_KINDS:
           continue

       # Get the target kind's activation set (None = all, frozenset = explicit)
       target_activated = _get_activation_set(pack_context, target_kind)
       if target_activated is None:
           # None means all built-ins are active — reference is satisfied
           continue

       if target_id not in target_activated:
           entry = f"{target_kind}/{target_id}"
           if entry not in missing_from_doctrine:
               missing_from_doctrine.append(entry)
               suggestions.append(
                   f"{target_kind}/{target_id}: Referenced by "
                   f"{source_kind}/{source_id} but not activated. "
                   f"Run 'charter activate {target_kind} {target_id}' "
                   f"or add --cascade when activating the source."
               )
   ```

   Replace `ctx.require_drg()`, `filter_graph_by_activation`, `edge.source_kind`,
   etc. with the actual API delivered by WP03/WP04. If the DRG API differs materially
   from this pseudocode, adapt the traversal logic while preserving the same finding
   categories and suggestion format.

   Add a helper `_get_activation_set(pack_context: PackContext, kind: str) -> frozenset[str] | None`
   that maps CLI kind names to `PackContext` fields and returns the field value.

**Validation**:
```bash
cd /home/stijn/Documents/_code/SDD/fork/spec-kitty
python -c "
from charter.consistency_check import run_consistency_check
print('run_consistency_check callable:', callable(run_consistency_check))
"
```
Expected: `True`. DRG traversal path will be exercised fully by T033 tests.

---

### T032 — Kind-violation and duplicate detection

**Requirement refs**: FR-011

**Files**:
- `src/charter/consistency_check.py`

**Steps**:

1. Extend `run_consistency_check()` with two additional checks. Add these loops after
   the DRG-edge block from T031 (still before the final `ConsistencyReport` construction):

   **Duplicate detection**:
   ```python
   # Duplicate detection: same ID appearing more than once within a kind's set.
   # (frozensets are unique by definition; this catches list-based config paths)
   for kind in YAML_KEY_MAP:
       activated = _get_activation_set(pack_context, kind)
       if activated is None:
           continue
       # Count occurrences — frozensets deduplicate automatically;
       # if the raw config is a list, check the raw list instead.
       raw_list = _get_raw_activation_list(pack_context, kind)  # helper below
       seen: set[str] = set()
       for item in (raw_list or []):
           if item in seen:
               kind_violations.append(
                   f"{kind}/{item}: Duplicate entry in activation set."
               )
           seen.add(item)
   ```

   **Kind-violation detection** (ID belongs to wrong kind):
   ```python
   # Build a lookup: for each doctrine ID, which kind does it belong to?
   # Then check each activated ID against its declared kind.
   all_ids_by_kind: dict[str, set[str]] = {}
   for k in YAML_KEY_MAP:
       all_ids_by_kind[k] = set(_get_doctrine_ids(ctx, k))

   for kind in YAML_KEY_MAP:
       activated = _get_activation_set(pack_context, kind)
       if activated is None:
           continue
       for artifact_id in activated:
           # Check if the ID actually exists in any OTHER kind's set
           for other_kind, other_ids in all_ids_by_kind.items():
               if other_kind == kind:
                   continue
               if artifact_id in other_ids and artifact_id not in all_ids_by_kind.get(kind, set()):
                   kind_violations.append(
                       f"{kind}/{artifact_id}: ID belongs to kind '{other_kind}', "
                       f"not '{kind}'."
                   )
                   break  # report once per misplaced ID
   ```

2. Add the helper `_get_raw_activation_list(pack_context: PackContext, kind: str) -> list[str] | None`
   that returns the raw list from `PackContext` for a given kind (before deduplication
   into a frozenset). If `PackContext` already stores frozensets, this helper can
   return `list(frozenset)` for the duplicate check — duplicates in that case are
   structurally impossible and the loop is a no-op.

3. Add `_get_doctrine_ids(ctx: ProjectContext, kind: str) -> list[str]` that returns
   all known IDs for a kind from the project's doctrine by calling
   `CharterPackManager().list_available(ctx, kind)`. Reuse the same loader
   from T030 (load once, pass the result around) to avoid a second full scan.

**Validation**:
```bash
cd /home/stijn/Documents/_code/SDD/fork/spec-kitty
python -c "
from charter.consistency_check import ConsistencyReport
r = ConsistencyReport(
    coherent=False,
    kind_violations=['directive/foo: Duplicate entry in activation set.'],
    suggestions=[],
)
assert r.coherent is False
assert 'Duplicate' in r.kind_violations[0]
print('kind_violations shape ok')
"
```
Expected: `kind_violations shape ok`.

---

### T033 — Tests with planted violations

**Requirement refs**: FR-011, FR-012, NFR-003

**Files**:
- `tests/charter/test_consistency_check.py` (new)

**Steps**:

1. Create `tests/charter/test_consistency_check.py`. Use `pytest` with `tmp_path`.

2. For each test that needs a real `ProjectContext`, create a minimal project fixture:
   - `.kittify/config.yaml` with the desired activation keys.
   - Rely on the built-in doctrine (available via the installed package) unless a
     specific "planted violation" requires a synthetic one. For synthetic violations,
     mock `CharterPackManager().get_doctrine_ids()` or equivalent to return a
     controlled set.

3. Write the following test functions:

   **`test_coherent_when_all_activated_ids_exist_in_doctrine`**
   - Build a project context where `activated_directives` contains only IDs that
     genuinely exist in the built-in doctrine (use real IDs from `default.yaml`).
   - Call `run_consistency_check(ctx)`.
   - Assert `report.coherent is True`.
   - Assert `report.unknown_references == []`.
   - Mark: `@pytest.mark.doctrine` (reads built-in doctrine).

   **`test_unknown_reference_detected`**
   - Set `activated_directives: ["totally-fake-directive-zzz"]` in config.
   - Call `run_consistency_check(ctx)`.
   - Assert `"totally-fake-directive-zzz"` appears in some entry of
     `report.unknown_references`.
   - Assert `report.coherent is False`.
   - Mark: `@pytest.mark.doctrine`.

   **`test_suggestion_contains_resolution_command`**
   - Same setup as `test_unknown_reference_detected`.
   - Assert that at least one suggestion string contains `"charter deactivate"`.
   - Mark: `@pytest.mark.doctrine`.

   **`test_none_kind_skipped`**
   - Create a project context where `activated_directives` field is `None` (no
     explicit activation key in config).
   - Assert `run_consistency_check(ctx)` does not raise and `report.unknown_references`
     contains no `"directive/"` entries.
   - Mark: `@pytest.mark.fast` if mockable, `@pytest.mark.doctrine` if not.

   **`test_coherent_false_when_incoherent`**
   - Plant an unknown ID in any activated kind.
   - Assert `report.coherent is False`.
   - Mark: `@pytest.mark.doctrine`.

   **`test_run_consistency_check_returns_report_object`**
   - Call `run_consistency_check(ctx)` on a minimal valid project.
   - Assert `isinstance(report, ConsistencyReport)`.
   - Assert `isinstance(report.coherent, bool)`.
   - Assert `isinstance(report.unknown_references, list)`.
   - Mark: `@pytest.mark.doctrine`.

4. Add a performance guard as a pytest fixture or inline timing assertion for the
   doctine-level tests (NFR-003, < 2 seconds):

   ```python
   import time

   def test_run_consistency_check_completes_within_2s(real_ctx):
       start = time.perf_counter()
       run_consistency_check(real_ctx)
       elapsed = time.perf_counter() - start
       assert elapsed < 2.0, f"consistency check took {elapsed:.2f}s (limit: 2s)"
   ```

   Mark: `@pytest.mark.doctrine`.

**Validation**:
```bash
cd /home/stijn/Documents/_code/SDD/fork/spec-kitty
pytest tests/charter/test_consistency_check.py -x -v
```
Expected: all tests pass, no errors. If WP03/WP04 mocks are needed for any test,
the mock must be removed once the real implementation is present — do not commit
stubs that silently skip real behavior.

---

## Definition of Done

Before marking WP07 as `for_review`:

- [ ] `pytest tests/charter/test_consistency_check.py -x` — all tests pass.
- [ ] `ConsistencyReport.coherent` is `False` when `unknown_references`,
  `missing_from_doctrine`, or `kind_violations` is non-empty.
- [ ] WP template scanning is NOT implemented (explicitly deferred to follow-on mission).
- [ ] `run_consistency_check` completes in < 2 seconds against the built-in doctrine
  (manual `time pytest tests/charter/test_consistency_check.py -k completes_within`
  or the dedicated timing test).
- [ ] `ruff check src/charter/consistency_check.py` — no lint errors.
- [ ] `mypy src/charter/consistency_check.py --strict` — no type errors.
- [ ] No files outside `owned_files` were modified.

## Activity Log

- 2026-05-31T14:19:41Z – claude:sonnet-4-6:python-pedro:implementer – shell_pid=6774 – Assigned agent via action command
- 2026-05-31T14:30:56Z – claude:sonnet-4-6:python-pedro:implementer – shell_pid=6774 – Ready for review: ConsistencyReport + run_consistency_check implemented with unknown-reference detection (FR-011), cross-kind DRG edge validation (FR-012), duplicate/kind-violation detection, and performance test < 2s (NFR-003). All 7 tests pass. Ruff and mypy strict clean.
- 2026-05-31T14:31:19Z – claude:sonnet-4-6:reviewer-renata:reviewer – shell_pid=95404 – Started review via action command
- 2026-05-31T14:35:18Z – claude:sonnet-4-6:reviewer-renata:reviewer – shell_pid=95404 – Moved to planned
