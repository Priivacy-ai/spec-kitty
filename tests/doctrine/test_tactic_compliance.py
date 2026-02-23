"""Integration tests for tactic schema and content compliance.

Validates all tactic files in src/doctrine/tactics/ for:
A. Schema validity against tactic.schema.yaml
B. Reference resolution — every referenced artifact must exist
C. Token discipline — step-level references repeated in >=70% of steps
   should be elevated to root-level references
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator  # type: ignore[import-untyped]

DOCTRINE_DIR = Path(__file__).resolve().parents[2] / "src" / "doctrine"
SCHEMA_DIR = DOCTRINE_DIR / "schemas"
TACTICS_DIR = DOCTRINE_DIR / "tactics"

# Artifact type → (directory, glob pattern) for resolution scanning.
# Styleguides use recursive glob because subdirectories are allowed.
ARTIFACT_DIRS: dict[str, list[tuple[Path, str]]] = {
    "tactic": [(TACTICS_DIR, "*.tactic.yaml")],
    "styleguide": [
        (DOCTRINE_DIR / "styleguides", "*.styleguide.yaml"),
        (DOCTRINE_DIR / "styleguides", "**/*.styleguide.yaml"),
    ],
    "directive": [(DOCTRINE_DIR / "directives", "*.directive.yaml")],
    "toolguide": [(DOCTRINE_DIR / "toolguides", "*.toolguide.yaml")],
}

# Threshold: if a reference appears in this fraction of steps or more,
# it should be a root-level reference instead (token discipline).
ELEVATION_THRESHOLD = 0.70


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    assert isinstance(data, dict), f"{path}: expected mapping root"
    return data


def _tactic_schema() -> Draft202012Validator:
    schema = _load_yaml(SCHEMA_DIR / "tactic.schema.yaml")
    return Draft202012Validator(schema)


def _collect_tactic_files() -> list[Path]:
    return sorted(TACTICS_DIR.glob("*.tactic.yaml"))


def _build_artifact_index() -> dict[str, set[str]]:
    """Scan all doctrine directories and return {type: {id, ...}}."""
    index: dict[str, set[str]] = {}
    for artifact_type, locations in ARTIFACT_DIRS.items():
        ids: set[str] = set()
        for directory, pattern in locations:
            if not directory.exists():
                continue
            for path in directory.glob(pattern):
                try:
                    data = _load_yaml(path)
                    if "id" in data:
                        ids.add(data["id"])
                except Exception:
                    continue
        index[artifact_type] = ids
    return index


def _extract_step_references(
    tactic: dict,
) -> list[tuple[int, str, dict]]:
    """Return (step_index, step_title, reference) for every step-level ref."""
    results = []
    for i, step in enumerate(tactic.get("steps", [])):
        for ref in step.get("references", []):
            results.append((i, step.get("title", f"step-{i}"), ref))
    return results


def _extract_root_references(tactic: dict) -> list[dict]:
    return tactic.get("references", [])


# ---------------------------------------------------------------------------
# Parametrize across all tactic files
# ---------------------------------------------------------------------------

_tactic_files = _collect_tactic_files()
_tactic_ids = [f.stem.replace(".tactic", "") for f in _tactic_files]


@pytest.fixture(scope="module")
def artifact_index() -> dict[str, set[str]]:
    return _build_artifact_index()


# ---------------------------------------------------------------------------
# A. Schema validity
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tactic_path", _tactic_files, ids=_tactic_ids)
def test_tactic_schema_valid(tactic_path: Path) -> None:
    """Every tactic file must validate against tactic.schema.yaml."""
    validator = _tactic_schema()
    tactic = _load_yaml(tactic_path)
    errors = sorted(validator.iter_errors(tactic), key=str)
    messages = []
    for err in errors:
        pointer = "/" + "/".join(str(p) for p in err.path) if err.path else "/"
        messages.append(f"  {pointer}: {err.message}")
    assert not errors, f"{tactic_path.name} schema errors:\n" + "\n".join(messages)


# ---------------------------------------------------------------------------
# B. Reference resolution
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tactic_path", _tactic_files, ids=_tactic_ids)
def test_references_resolve(
    tactic_path: Path, artifact_index: dict[str, set[str]]
) -> None:
    """Every reference (root and step) must point to an existing artifact."""
    tactic = _load_yaml(tactic_path)
    unresolved = []

    for ref in _extract_root_references(tactic):
        ref_type = ref.get("type", "unknown")
        ref_id = ref.get("id", "missing")
        known_ids = artifact_index.get(ref_type, set())
        if ref_id not in known_ids:
            unresolved.append(
                f"  root reference: type={ref_type} id={ref_id}"
                f" (known {ref_type} ids: {sorted(known_ids) or 'none'})"
            )

    for step_idx, step_title, ref in _extract_step_references(tactic):
        ref_type = ref.get("type", "unknown")
        ref_id = ref.get("id", "missing")
        known_ids = artifact_index.get(ref_type, set())
        if ref_id not in known_ids:
            unresolved.append(
                f"  step {step_idx} ({step_title}): type={ref_type} id={ref_id}"
                f" (known {ref_type} ids: {sorted(known_ids) or 'none'})"
            )

    assert not unresolved, (
        f"{tactic_path.name} has unresolved references:\n" + "\n".join(unresolved)
    )


# ---------------------------------------------------------------------------
# C. Token discipline — step refs repeated >=70% should be root-level
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tactic_path", _tactic_files, ids=_tactic_ids)
def test_step_references_not_over_duplicated(tactic_path: Path) -> None:
    """References appearing in >=70% of steps should be elevated to root."""
    tactic = _load_yaml(tactic_path)
    steps = tactic.get("steps", [])
    total_steps = len(steps)

    if total_steps == 0:
        return

    # Count how many distinct steps each (type, id) pair appears in.
    ref_step_sets: dict[tuple[str, str], set[int]] = {}
    for step_idx, _, ref in _extract_step_references(tactic):
        key = (ref.get("type", ""), ref.get("id", ""))
        ref_step_sets.setdefault(key, set()).add(step_idx)

    # Build set of root-level ref keys (already elevated — no violation).
    root_keys = {
        (ref.get("type", ""), ref.get("id", ""))
        for ref in _extract_root_references(tactic)
    }

    violations = []
    for (ref_type, ref_id), step_indices in ref_step_sets.items():
        ratio = len(step_indices) / total_steps
        if ratio >= ELEVATION_THRESHOLD and (ref_type, ref_id) not in root_keys:
            pct = int(ratio * 100)
            violations.append(
                f"  ({ref_type}, {ref_id}) appears in {len(step_indices)}/{total_steps}"
                f" steps ({pct}%) — elevate to root-level references"
            )

    assert not violations, (
        f"{tactic_path.name} has step references that should be elevated to root"
        f" (>={int(ELEVATION_THRESHOLD * 100)}% threshold):\n"
        + "\n".join(violations)
    )


# ---------------------------------------------------------------------------
# D. No redundant step refs — root-level refs must not repeat in steps
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tactic_path", _tactic_files, ids=_tactic_ids)
def test_root_references_not_repeated_in_steps(tactic_path: Path) -> None:
    """A reference declared at root level must not also appear in steps."""
    tactic = _load_yaml(tactic_path)

    root_keys = {
        (ref.get("type", ""), ref.get("id", ""))
        for ref in _extract_root_references(tactic)
    }

    if not root_keys:
        return

    redundant = []
    for step_idx, step_title, ref in _extract_step_references(tactic):
        key = (ref.get("type", ""), ref.get("id", ""))
        if key in root_keys:
            redundant.append(
                f"  step {step_idx} ({step_title}): ({key[0]}, {key[1]})"
                f" is already a root-level reference — remove from step"
            )

    assert not redundant, (
        f"{tactic_path.name} has step references that duplicate root-level refs:\n"
        + "\n".join(redundant)
    )
