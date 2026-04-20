---
work_package_id: WP05
title: Architectural Tests — Schema Validation and Shim Scanner
dependencies:
- WP01
- WP04
requirement_refs:
- FR-010
- FR-011
- NFR-002
planning_base_branch: kitty/mission-migration-shim-ownership-rules-01KPDYDW
merge_target_branch: kitty/mission-migration-shim-ownership-rules-01KPDYDW
branch_strategy: Planning artifacts for this feature were generated on kitty/mission-migration-shim-ownership-rules-01KPDYDW. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-migration-shim-ownership-rules-01KPDYDW unless the human explicitly redirects the landing branch.
subtasks:
- T009
- T010
agent: "claude"
shell_pid: "1348851"
history:
- date: '2026-04-19'
  event: created
agent_profile: python-implementer
authoritative_surface: tests/architectural/
execution_mode: code_change
mission_id: 01KPDYDWVF8W838HNJK7FC3S7T
mission_slug: migration-shim-ownership-rules-01KPDYDW
owned_files:
- tests/architectural/test_shim_registry_schema.py
- tests/architectural/test_unregistered_shim_scanner.py
tags: []
---

# WP05 — Architectural Tests — Schema Validation and Shim Scanner

## Objective

Add two pytest files to `tests/architectural/` that enforce the registry contract: one validates every entry in the live registry against the schema, and one scans `src/specify_cli/` via AST to ensure no unregistered shim goes undetected.

## Context

`tests/architectural/conftest.py` provides:
- `repo_root` fixture: `Path(__file__).resolve().parents[2]` (two levels up from `tests/architectural/`)
- `evaluable` and `landscape` fixtures (pytestarch-based; not needed here)

The scanner must use AST inspection — **not import** — because importing a shim triggers its `DeprecationWarning` and pollutes test output.

Both tests must run in ≤500 ms (NFR-002 covers the schema test; the scanner is expected to be similar).

## Branch Strategy

- **Working branch**: `kitty/mission-migration-shim-ownership-rules-01KPDYDW`
- **Merge target**: `main`
- Run: `spec-kitty agent action implement WP05 --agent <name>`

> **Agent guideline**: Load the assigned agent profile (`agent_profile: python-implementer`) from
> `src/doctrine/agent_profiles/shipped/python-implementer.agent.yaml` before starting work.
> Apply the profile's `initialization-declaration`, `success-definition`, and `self-review-protocol`
> (pytest, mypy --strict, ruff check) before moving to for_review.

---

## Subtask T009 — Write `tests/architectural/test_shim_registry_schema.py`

**Purpose**: FR-011 — assert every entry in the live registry (`architecture/2.x/shim-registry.yaml`) conforms to the schema, and assert that known-invalid entries trigger the correct `RegistrySchemaError`.

**Test structure**:

```python
"""FR-011: Shim registry YAML schema validation."""
from __future__ import annotations

import copy
from pathlib import Path

import pytest
from specify_cli.compat.registry import RegistrySchemaError, validate_registry

REGISTRY_PATH = Path(__file__).resolve().parents[2] / "architecture" / "2.x" / "shim-registry.yaml"

VALID_ENTRY: dict = {
    "legacy_path": "specify_cli.example",
    "canonical_import": "example",
    "introduced_in_release": "3.2.0",
    "removal_target_release": "3.3.0",
    "tracker_issue": "#615",
    "grandfathered": False,
}


def _make(overrides: dict) -> dict:
    """Return a fresh copy of VALID_ENTRY with overrides applied."""
    entry = copy.deepcopy(VALID_ENTRY)
    entry.update(overrides)
    return entry


class TestLiveRegistry:
    """The live registry must pass schema validation."""

    def test_live_registry_is_valid(self) -> None:
        from ruamel.yaml import YAML
        yaml = YAML(typ="safe")
        with REGISTRY_PATH.open() as fp:
            data = yaml.load(fp)
        validate_registry(data)  # must not raise


class TestValidEntry:
    def test_full_valid_entry_passes(self) -> None:
        validate_registry({"shims": [VALID_ENTRY]})

    def test_entry_with_notes_passes(self) -> None:
        validate_registry({"shims": [_make({"notes": "some note"})]})

    def test_umbrella_canonical_import_passes(self) -> None:
        validate_registry({"shims": [_make({"canonical_import": ["a.b", "c.d"]})]})

    def test_grandfathered_with_notes_passes(self) -> None:
        validate_registry({"shims": [_make({"grandfathered": True, "notes": "legacy"})]})

    def test_extension_rationale_passes(self) -> None:
        validate_registry({"shims": [_make({
            "removal_target_release": "3.4.0",
            "extension_rationale": "needed more time",
        })]})


@pytest.mark.parametrize("missing_key", [
    "legacy_path", "canonical_import", "introduced_in_release",
    "removal_target_release", "tracker_issue", "grandfathered",
])
def test_missing_required_field_raises(missing_key: str) -> None:
    entry = copy.deepcopy(VALID_ENTRY)
    del entry[missing_key]
    with pytest.raises(RegistrySchemaError) as exc_info:
        validate_registry({"shims": [entry]})
    assert missing_key in str(exc_info.value)


@pytest.mark.parametrize("bad_entry,expected_fragment", [
    (_make({"legacy_path": "bad path!"}), "legacy_path"),
    (_make({"canonical_import": "bad import!"}), "canonical_import"),
    (_make({"introduced_in_release": "not-semver"}), "introduced_in_release"),
    (_make({"removal_target_release": "v3.3.0"}), "removal_target_release"),
    (_make({"tracker_issue": "issue 42"}), "tracker_issue"),
    (_make({"grandfathered": "true"}), "grandfathered"),  # string instead of bool
    (_make({"removal_target_release": "3.1.0"}), "removal_target_release"),  # < introduced
    (_make({"extension_rationale": ""}), "extension_rationale"),  # empty string
    (_make({"canonical_import": []}), "canonical_import"),  # empty list
])
def test_invalid_entry_raises(bad_entry: dict, expected_fragment: str) -> None:
    with pytest.raises(RegistrySchemaError) as exc_info:
        validate_registry({"shims": [bad_entry]})
    assert expected_fragment in str(exc_info.value)


def test_duplicate_legacy_paths_raise() -> None:
    entries = [copy.deepcopy(VALID_ENTRY), copy.deepcopy(VALID_ENTRY)]
    with pytest.raises(RegistrySchemaError) as exc_info:
        validate_registry({"shims": entries})
    assert "legacy_path" in str(exc_info.value).lower()


def test_non_list_shims_raise() -> None:
    with pytest.raises(RegistrySchemaError):
        validate_registry({"shims": "not-a-list"})


def test_missing_shims_key_raises() -> None:
    with pytest.raises(RegistrySchemaError):
        validate_registry({})
```

**Files**:
- `tests/architectural/test_shim_registry_schema.py` (new, ~100 lines)

**Validation**:
- [ ] All parametrized invalid cases raise `RegistrySchemaError` with the correct field name in the message
- [ ] Live registry with `shims: []` passes
- [ ] `pytest tests/architectural/test_shim_registry_schema.py -v` exits 0
- [ ] Runtime ≤500 ms (NFR-002)

---

## Subtask T010 — Write `tests/architectural/test_unregistered_shim_scanner.py`

**Purpose**: FR-010 — assert that every module under `src/specify_cli/` carrying `__deprecated__ = True` appears in the shim registry. Detect both annotation-form and plain assignment-form.

**Implementation approach**:

The scanner must handle two assignment forms:
```python
__deprecated__ = True          # plain assignment
__deprecated__: bool = True    # annotated assignment
```

Use `ast.parse` — never import the module.

```python
"""FR-010: Every __deprecated__ module in src/specify_cli/ must be registered."""
from __future__ import annotations

import ast
from pathlib import Path

import pytest
from ruamel.yaml import YAML

SRC_SPECIFY_CLI = Path(__file__).resolve().parents[2] / "src" / "specify_cli"
REGISTRY_PATH = Path(__file__).resolve().parents[2] / "architecture" / "2.x" / "shim-registry.yaml"


def _module_path_to_legacy_path(py_file: Path, src_root: Path) -> str:
    """Convert a .py file path to a dotted import path."""
    rel = py_file.relative_to(src_root)
    parts = list(rel.parts)
    # strip .py or __init__.py
    if parts[-1] == "__init__.py":
        parts = parts[:-1]
    else:
        parts[-1] = parts[-1].removesuffix(".py")
    return ".".join(parts)


def _has_deprecated_true(source: str) -> bool:
    """Return True if the module has a module-level __deprecated__ = True."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    for node in ast.iter_child_nodes(tree):
        # Plain: __deprecated__ = True
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "__deprecated__"
            and isinstance(node.value, ast.Constant)
            and node.value.value is True
        ):
            return True
        # Annotated: __deprecated__: bool = True
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "__deprecated__"
            and node.value is not None
            and isinstance(node.value, ast.Constant)
            and node.value.value is True
        ):
            return True
    return False


def _scan_deprecated_modules(src_root: Path) -> set[str]:
    """Return set of legacy_path strings for all shim modules found."""
    found: set[str] = set()
    for py_file in src_root.rglob("*.py"):
        source = py_file.read_text(encoding="utf-8")
        if _has_deprecated_true(source):
            found.add(_module_path_to_legacy_path(py_file, src_root.parent))
    return found


def _load_registry_paths() -> set[str]:
    """Return set of legacy_path strings from the live registry."""
    yaml = YAML(typ="safe")
    with REGISTRY_PATH.open() as fp:
        data = yaml.load(fp)
    return {entry["legacy_path"] for entry in (data.get("shims") or [])}


class TestShimScanner:
    def test_no_unregistered_shims(self) -> None:
        """All __deprecated__ modules must appear in the registry."""
        found = _scan_deprecated_modules(SRC_SPECIFY_CLI)
        registered = _load_registry_paths()
        unregistered = found - registered
        assert not unregistered, (
            f"Unregistered shims detected — add them to architecture/2.x/shim-registry.yaml:\n"
            + "\n".join(f"  {p}" for p in sorted(unregistered))
        )

    def test_scanner_detects_plain_assignment(self, tmp_path: Path) -> None:
        """Scanner picks up __deprecated__ = True in plain assignment form."""
        fake = tmp_path / "fake_shim.py"
        fake.write_text("__deprecated__ = True\n")
        found = _has_deprecated_true(fake.read_text())
        assert found

    def test_scanner_detects_annotated_assignment(self, tmp_path: Path) -> None:
        """Scanner picks up __deprecated__: bool = True in annotated form."""
        fake = tmp_path / "fake_shim.py"
        fake.write_text("__deprecated__: bool = True\n")
        found = _has_deprecated_true(fake.read_text())
        assert found

    def test_scanner_ignores_false(self, tmp_path: Path) -> None:
        """Scanner does not flag __deprecated__ = False."""
        fake = tmp_path / "not_a_shim.py"
        fake.write_text("__deprecated__ = False\n")
        assert not _has_deprecated_true(fake.read_text())

    def test_scanner_ignores_non_module_level(self, tmp_path: Path) -> None:
        """Scanner ignores __deprecated__ inside a function or class."""
        fake = tmp_path / "not_a_shim.py"
        fake.write_text("def foo():\n    __deprecated__ = True\n")
        assert not _has_deprecated_true(fake.read_text())
```

**Files**:
- `tests/architectural/test_unregistered_shim_scanner.py` (new, ~100 lines)

**Validation**:
- [ ] `test_no_unregistered_shims` passes (zero shims at mission start)
- [ ] Synthetic `__deprecated__ = True` file is detected by the scanner
- [ ] `pytest tests/architectural/test_unregistered_shim_scanner.py -v` exits 0

---

## Definition of Done

- [ ] `tests/architectural/test_shim_registry_schema.py` written and passing
- [ ] `tests/architectural/test_unregistered_shim_scanner.py` written and passing
- [ ] Both tests complete in ≤500 ms
- [ ] Both files pass `mypy --strict`
- [ ] `pytest tests/architectural/ -v` exits 0 (no regressions to existing `test_layer_rules.py`)

## Risks

- The `conftest.py` `repo_root` fixture uses `parents[2]` from within `tests/architectural/`. Verify the path resolves correctly (`tests/architectural/test_X.py` → `parents[0]` = `tests/architectural/`, `parents[1]` = `tests/`, `parents[2]` = repo root).
- `ast.parse` on files with encoding declarations: use `py_file.read_text(encoding="utf-8")` or detect the encoding header. Most files in this repo use UTF-8.

## Activity Log

- 2026-04-19T13:27:30Z – claude – shell_pid=1346305 – Started implementation via action command
- 2026-04-19T13:29:54Z – claude – shell_pid=1346305 – 44 tests pass: schema validation (38) + AST scanner (6). ruff clean.
- 2026-04-19T13:30:59Z – claude – shell_pid=1348851 – Started review via action command
- 2026-04-19T13:31:10Z – claude – shell_pid=1348851 – Review passed: 44 tests, 1.0s runtime. Both assignment forms detected. Zero unregistered shims confirmed.
