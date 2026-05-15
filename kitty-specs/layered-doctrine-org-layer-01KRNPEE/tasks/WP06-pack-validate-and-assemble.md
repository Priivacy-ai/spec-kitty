---
work_package_id: WP06
title: doctrine pack validate and pack assemble
dependencies:
- WP05
requirement_refs:
- C-007
- FR-012
- FR-013
- NFR-003
planning_base_branch: feat/org-doctrine-layer
merge_target_branch: feat/org-doctrine-layer
branch_strategy: All planning and implementation targets feat/org-doctrine-layer. Worktree branch allocated by finalize-tasks lane computation.
subtasks:
- T027
- T028
- T029
- T030
- T031
- T032
agent: codex
history:
- date: '2026-05-15'
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/doctrine/pack_validator.py
execution_mode: code_change
owned_files:
- src/specify_cli/doctrine/pack_validator.py
- src/specify_cli/doctrine/pack_assembler.py
- tests/specify_cli/doctrine/test_pack_validator.py
- tests/specify_cli/doctrine/test_pack_assembler.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Implement `pack_validator.py` (`validate_pack()`) and `pack_assembler.py`
(`assemble_pack()`). Fill in the `pack validate` and `pack assemble` CLI subcommand
implementations that were stubbed in WP05. After this WP, pack authors and doctrine
maintainers can validate and assemble packs from the command line.

---

## Context

WP05 created `doctrine.py` with stub functions that import from `pack_validator` and
`pack_assembler`. This WP creates those modules. The CLI wiring in `doctrine.py` is
**not** modified by this WP (ownership belongs to WP05); this WP only creates the
implementation files that the stubs call into.

See `contracts/pack-layout.md` for the normative pack layout and validation rules.

The validator needs the shipped DRG to check URN existence for DRG extensions. Load it via
`load_validated_graph(repo_root=Path("."), org_root=None)` with a real project root if
available, or with a minimal shipped-only graph if no repo root is detected.

---

## Branch Strategy

- **Planning/base branch**: `feat/org-doctrine-layer`
- **Merge target**: `feat/org-doctrine-layer`
- **Implement command**: `spec-kitty agent action implement WP06 --agent codex`

---

## Subtask T027 — Implement `pack_validator.py`

**File**: `src/specify_cli/doctrine/pack_validator.py`

```python
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class ValidationIssue:
    severity: str           # "error" | "advisory"
    artifact_type: str      # "directives", "drg", etc.
    artifact_id: str | None
    file: str
    message: str

@dataclass
class ValidationResult:
    ok: bool
    errors: list[ValidationIssue] = field(default_factory=list)
    advisories: list[ValidationIssue] = field(default_factory=list)

def validate_pack(pack_dir: Path) -> ValidationResult:
    """Validate a doctrine pack directory."""
    ...
```

**Validation steps** (in order):

1. **Directory existence**: `pack_dir` must exist and be a directory. If not, return
   immediately with a single error.

2. **Artifact schema validation**: For each known artifact type directory that exists:
   - Load each `*.{type}.yaml` file with `ruamel.yaml`.
   - Validate against the appropriate Pydantic model (import the relevant `Repository`
     and use its `_schema` class).
   - Collect schema violations as errors with `severity="error"`.

3. **ID uniqueness within pack**: Across all files in each artifact type directory, no two
   files may declare the same `id`. Collect duplicate IDs as errors.

4. **DRG extension validation**: If `drg/` exists:
   - Load all `*.graph.yaml` fragments with `load_graph_or_dir(pack_dir / "drg")`.
   - Load the shipped graph with `load_graph_or_dir(resolve_doctrine_root())`.
   - Merge org artifacts into a temporary `DoctrineService` to build the set of known URNs.
   - For each DRG edge in the pack's graph extensions: verify both source and target URNs
     exist in `shipped_graph.nodes` ∪ `pack_artifact_urns`. Dangling URNs → error.
   - Check that no extension node modifies an existing shipped node's `kind`. → error.

5. **Advisory: shipped ID collision**: For each artifact ID in the pack, if the same ID
   exists in the shipped set (loaded from `resolve_doctrine_root()`), emit an advisory.

6. **Advisory: duplicate DRG edges**: If two fragment files add the same edge
   (same source URN, target URN, relation), emit advisory.

Return `ValidationResult(ok=len(errors) == 0, errors=errors, advisories=advisories)`.

---

## Subtask T028 — Implement `pack_assembler.py`

**File**: `src/specify_cli/doctrine/pack_assembler.py`

```python
@dataclass
class ConflictItem:
    artifact_type: str
    artifact_id: str
    conflicting_packs: list[str]   # pack directory names

@dataclass
class AssemblyResult:
    ok: bool
    artifacts_written: int
    conflicts: list[ConflictItem] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

def assemble_pack(
    input_packs: list[Path],
    output_dir: Path,
    *,
    force: bool = False,
) -> AssemblyResult:
    """Merge multiple input packs into output_dir."""
    ...
```

**Assembly steps**:

1. **Conflict detection** (before writing anything):
   - For each artifact type, build a dict `{artifact_id: source_pack_name}` as packs are
     processed in order.
   - If an artifact ID appears in more than one pack: record a `ConflictItem`.
   - DRG conflict: if the same edge (source+target+relation) appears in multiple packs'
     graph extensions: record a `ConflictItem` with `artifact_type="drg"`.

2. **If conflicts exist and `force=False`**: return `AssemblyResult(ok=False, conflicts=conflicts)`.
   Do NOT write any output.

3. **Merge artifact files** (only if no conflicts or `force=True`):
   - Create `output_dir` (fail if exists and non-empty, unless `force=True`).
   - For each input pack (in order), copy all artifact files into `output_dir/<type>/`.
   - When `force=True` and ID conflict exists: last pack wins (log advisory).

4. **Merge DRG extensions**: Concatenate all `*.graph.yaml` fragment files from all input
   packs' `drg/` directories into `output_dir/drg/`. Re-number files to maintain order.

5. **Validate assembled output**: Call `validate_pack(output_dir)`. If validation fails:
   `shutil.rmtree(output_dir)` and return `AssemblyResult(ok=False, ...)`.

6. Return `AssemblyResult(ok=True, artifacts_written=total_count)`.

**`--conflicts-out` support**: If a `conflicts_out: Path` is provided, write the
`AssemblyResult.conflicts` list to that path as JSON before returning.

---

## Subtask T029 — Fill in `pack validate` subcommand

**File**: `src/specify_cli/doctrine/pack_validator.py` (rendering helpers only — CLI wire
already exists in `doctrine.py` from WP05)

Add `render_validation_result(result: ValidationResult, *, json_output: bool)` helper:

```python
def render_validation_result(result: ValidationResult, *, json_output: bool = False) -> None:
    """Print validation result to stdout."""
    ...
```

Human output format:
```
✓ pack/directives/acme-001.directive.yaml — OK
✗ pack/directives/acme-002.directive.yaml — Error: missing required field 'title'
⚠ advisory: artifact ID 'DIR-003' overrides a shipped artifact
Pack validation: 1 error, 1 advisory
```

JSON output format:
```json
{"ok": false, "errors": [...], "advisories": [...]}
```

Exit code: 0 if `ok=True` (advisories do not affect exit code), 1 if `ok=False`.

The CLI function in `doctrine.py` calls `render_validation_result(result, json_output=json_output)`
and then raises `typer.Exit(0 if result.ok else 1)`.

---

## Subtask T030 — Fill in `pack assemble` subcommand

**File**: `src/specify_cli/doctrine/pack_assembler.py` (rendering helpers only)

Add `render_assembly_result(result, *, conflicts_out, json_output)` helper.

Human output format:
```
Assembled 3 packs → output_dir/ (47 artifacts)
```

Or on conflict:
```
✗ Conflict: artifact ID 'sec-001' in both 'security-pack' and 'compliance-pack'
Resolve conflicts and re-run, or use --force to let last pack win.
```

Write `conflicts_out` JSON if the option is provided:
```json
[{"artifact_type": "directives", "artifact_id": "sec-001", "conflicting_packs": ["security-pack", "compliance-pack"]}]
```

Exit code: 0 on success, 1 on conflict or error.

---

## Subtask T031 — Unit tests for `pack_validator.py`

**File**: `tests/specify_cli/doctrine/test_pack_validator.py`

Build minimal pack fixtures in `tmp_path`:

| Test | Pack contents | Expected |
|---|---|---|
| `test_valid_pack_single_type` | 2 valid directives | `ok=True`, no errors |
| `test_schema_violation` | 1 directive missing required field | 1 error, `ok=False` |
| `test_duplicate_id` | 2 directive files with same `id` | 1 error, `ok=False` |
| `test_dangling_drg_edge` | `drg/` with edge referencing non-existent URN | 1 error, `ok=False` |
| `test_shipped_id_collision_advisory` | Artifact ID matching a shipped directive | 1 advisory, `ok=True` |
| `test_empty_pack` | Pack dir with no artifact files, no drg/ | `ok=True`, 0 artifacts (empty is valid) |
| `test_nonexistent_pack_dir` | Path doesn't exist | 1 error, `ok=False` |

---

## Subtask T032 — Unit tests for `pack_assembler.py`

**File**: `tests/specify_cli/doctrine/test_pack_assembler.py`

| Test | Input packs | Expected |
|---|---|---|
| `test_single_pack` | 1 pack, 3 directives | `ok=True`, output has 3 directives |
| `test_two_packs_no_conflict` | pack-A: dir-001, pack-B: dir-002 | `ok=True`, output has both |
| `test_id_conflict_blocks` | pack-A and pack-B both have dir-001 | `ok=False`, `conflicts` non-empty |
| `test_force_resolves_conflict` | Same as above, `force=True` | `ok=True`, last-pack-wins |
| `test_drg_conflict` | Two packs with same DRG edge | conflict recorded |
| `test_conflicts_out_written` | ID conflict + `conflicts_out` path | JSON file written |
| `test_assembled_pack_validated` | Valid inputs | `validate_pack()` called on output |

---

## Definition of Done

- [ ] `validate_pack()` detects all error categories from `contracts/pack-layout.md`
- [ ] `assemble_pack()` blocks on conflict unless `force=True`
- [ ] Both rendering helpers produce human-readable and JSON output
- [ ] All tests in `test_pack_validator.py` and `test_pack_assembler.py` pass
- [ ] `spec-kitty doctrine pack validate <path>` exits 0 on valid pack, 1 on errors
- [ ] `spec-kitty doctrine pack assemble <output> <input...>` exits 0 on success

## Risks

- The validator loads the shipped DRG to check URN existence; this requires
  `resolve_doctrine_root()` to be available in the test environment. Use a fixture
  that provides a minimal shipped DRG directory for testing.
- `assemble_pack()` calls `validate_pack()` on the output; if validation fails, it must
  clean up the partial output directory before returning.

## Reviewer Guidance

1. Confirm `ok=True` with advisories (no errors) exits 0.
2. Confirm conflicts are NOT silently ignored: exit 1 and clear conflict report.
3. Confirm assembled output passes `validate_pack()` before `assemble_pack()` returns True.
