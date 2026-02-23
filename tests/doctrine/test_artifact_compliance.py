"""Integration checks for in-repo doctrine artifacts.

Validates that directive/styleguide/toolguide files in src/doctrine:
1. Conform to their schemas
2. Resolve key cross-artifact references
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator  # type: ignore[import-untyped]

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCTRINE_DIR = REPO_ROOT / "src" / "doctrine"
SCHEMA_DIR = DOCTRINE_DIR / "schemas"


def _load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    assert isinstance(data, dict), f"{path}: expected mapping root"
    return data


def _schema_validator(schema_name: str) -> Draft202012Validator:
    schema_path = SCHEMA_DIR / f"{schema_name}.schema.yaml"
    schema = _load_yaml(schema_path)
    return Draft202012Validator(schema)


def _error_message(file_path: Path, error) -> str:
    pointer = "/" + "/".join(str(part) for part in error.path) if error.path else "/"
    return f"{file_path.relative_to(REPO_ROOT)} path={pointer} message={error.message}"


ARTIFACT_GLOBS: dict[str, tuple[Path, str]] = {
    "directive": (DOCTRINE_DIR / "directives", "*.directive.yaml"),
    "styleguide": (DOCTRINE_DIR / "styleguides", "**/*.styleguide.yaml"),
    "toolguide": (DOCTRINE_DIR / "toolguides", "*.toolguide.yaml"),
}


def _artifact_cases() -> list[tuple[str, Path]]:
    cases: list[tuple[str, Path]] = []
    for artifact_type, (base_dir, pattern) in ARTIFACT_GLOBS.items():
        for artifact_path in sorted(base_dir.glob(pattern)):
            cases.append((artifact_type, artifact_path))
    return cases


_ARTIFACT_CASES = _artifact_cases()
_ARTIFACT_IDS = [f"{kind}:{path.relative_to(REPO_ROOT)}" for kind, path in _ARTIFACT_CASES]


@pytest.mark.parametrize(
    ("artifact_type", "artifact_path"), _ARTIFACT_CASES, ids=_ARTIFACT_IDS
)
def test_artifact_files_validate_schema(artifact_type: str, artifact_path: Path) -> None:
    validator = _schema_validator(artifact_type)
    payload = _load_yaml(artifact_path)
    errors = sorted(validator.iter_errors(payload), key=str)
    assert not errors, "\n".join(_error_message(artifact_path, error) for error in errors)


@pytest.fixture(scope="module")
def tactic_ids() -> set[str]:
    ids: set[str] = set()
    for tactic_path in sorted((DOCTRINE_DIR / "tactics").glob("*.tactic.yaml")):
        tactic = _load_yaml(tactic_path)
        tactic_id = tactic.get("id")
        if isinstance(tactic_id, str) and tactic_id:
            ids.add(tactic_id)
    return ids


@pytest.mark.parametrize(
    "directive_path",
    sorted((DOCTRINE_DIR / "directives").glob("*.directive.yaml")),
    ids=lambda p: str(p.relative_to(REPO_ROOT)),
)
def test_directive_tactic_refs_resolve(
    directive_path: Path, tactic_ids: set[str]
) -> None:
    directive = _load_yaml(directive_path)
    unresolved = []
    for tactic_ref in directive.get("tactic_refs", []):
        if tactic_ref not in tactic_ids:
            unresolved.append(tactic_ref)
    assert not unresolved, (
        f"{directive_path.relative_to(REPO_ROOT)} unresolved tactic_refs: "
        f"{unresolved} (known tactic ids: {sorted(tactic_ids)})"
    )


@pytest.mark.parametrize(
    "toolguide_path",
    sorted((DOCTRINE_DIR / "toolguides").glob("*.toolguide.yaml")),
    ids=lambda p: str(p.relative_to(REPO_ROOT)),
)
def test_toolguide_guide_path_exists(toolguide_path: Path) -> None:
    toolguide = _load_yaml(toolguide_path)
    guide_path = toolguide["guide_path"]
    assert isinstance(guide_path, str), (
        f"{toolguide_path.relative_to(REPO_ROOT)} guide_path must be a string"
    )

    target = (REPO_ROOT / guide_path).resolve()
    try:
        target.relative_to(REPO_ROOT.resolve())
    except ValueError as exc:
        raise AssertionError(
            f"{toolguide_path.relative_to(REPO_ROOT)} guide_path escapes repo: {guide_path}"
        ) from exc

    assert target.is_file(), (
        f"{toolguide_path.relative_to(REPO_ROOT)} guide_path not found: {guide_path}"
    )
