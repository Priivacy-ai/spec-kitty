"""Consumed packaging invariants for the published CLI distribution."""

from __future__ import annotations

import ast
import copy
import re
import tomllib
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PYPROJECT = _REPO_ROOT / "pyproject.toml"
_SRC = _REPO_ROOT / "src"
_SHARED_PACKAGES = ("spec-kitty-events", "spec-kitty-tracker")
_RETIRED_PACKAGE = "spec-kitty-runtime"
_SHIPPED_TREES = ("specify_cli", "runtime")
_DEP_NAME_TERMINATORS = "[=<>!~;@ "
# The one sanctioned [tool.uv.sources] override (controller-qa on #58): a
# pinned-rev git source of the EXPERIMENTAL events repo while 8.0.0 awaits an
# index (EXPERIMENTAL-spec-kitty-planning#31). Pinned-rev keeps uv.lock
# reproducible; the git host is the programme's forge. Everything else — path,
# editable, branch revs, other hosts, any tracker/runtime source — stays a
# violation.
_EVENTS_SOURCE_REPO_URL = "https://github.int.exe.xyz/spec-kitty/EXPERIMENTAL-spec-kitty-events"
_FULL_SHA_REV = re.compile(r"^[0-9a-f]{40}$")


def _load_pyproject() -> dict[str, Any]:
    return tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))


def _dep_name(entry: str) -> str:
    for index, char in enumerate(entry):
        if char in _DEP_NAME_TERMINATORS:
            return entry[:index].strip()
    return entry.strip()


def _is_sanctioned_events_git_pin(source: Any) -> bool:
    """True for exactly the sanctioned pinned-rev git source of the events repo."""
    if not isinstance(source, dict):
        return False
    if set(source) - {"git", "rev"}:
        return False
    return source.get("git") == _EVENTS_SOURCE_REPO_URL and isinstance(source.get("rev"), str) and bool(_FULL_SHA_REV.match(source["rev"]))


def _metadata_violations(data: dict[str, Any]) -> list[str]:
    dependencies = data.get("project", {}).get("dependencies", [])
    by_name = {_dep_name(entry): entry for entry in dependencies}
    failures: list[str] = []
    for package in _SHARED_PACKAGES:
        entry = by_name.get(package)
        if entry is None:
            failures.append(f"missing consumed dependency {package}")
        elif "==" in entry:
            failures.append(f"exact runtime pin for {package}: {entry}")
    if _RETIRED_PACKAGE in by_name:
        failures.append(f"retired dependency present: {by_name[_RETIRED_PACKAGE]}")

    sources = data.get("tool", {}).get("uv", {}).get("sources", {})
    for package in (*_SHARED_PACKAGES, _RETIRED_PACKAGE):
        if package not in sources:
            continue
        if package == "spec-kitty-events" and _is_sanctioned_events_git_pin(sources[package]):
            continue
        failures.append(f"committed local source for {package}: {sources[package]!r}")
    return failures


def _imported_first_party_packages(src_root: Path) -> set[str]:
    first_party = {child.name for child in src_root.iterdir() if child.is_dir() and any(child.rglob("*.py"))}
    imported: set[str] = set()
    for shipped_tree in _SHIPPED_TREES:
        for path in (src_root / shipped_tree).rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    names = [node.module]
                else:
                    continue
                imported.update(name.split(".", 1)[0] for name in names if name.split(".", 1)[0] in first_party)
    return imported


def _missing_wheel_packages(data: dict[str, Any], src_root: Path) -> set[str]:
    configured = {Path(path).name for path in data["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"]}
    return _imported_first_party_packages(src_root) - configured


def test_published_metadata_uses_consumable_shared_dependencies() -> None:
    """Published metadata must remain installable outside the checkout."""
    data = _load_pyproject()
    assert data["project"]["dependencies"]
    assert _metadata_violations(data) == []

    exact_pin = copy.deepcopy(data)
    exact_pin["project"]["dependencies"] = [
        "spec-kitty-events==6.1.0" if _dep_name(entry) == "spec-kitty-events" else entry for entry in exact_pin["project"]["dependencies"]
    ]
    assert _metadata_violations(exact_pin)

    local_source = copy.deepcopy(data)
    local_source.setdefault("tool", {}).setdefault("uv", {}).setdefault("sources", {})["spec-kitty-tracker"] = {"path": "../spec-kitty-tracker", "editable": True}
    assert _metadata_violations(local_source)


def test_events_git_source_must_be_the_sanctioned_pinned_rev() -> None:
    """[tool.uv.sources] admits exactly the pinned-rev git source of the events repo.

    The sanctioned shape (controller-qa on #58, interim to planning#31) is a
    full-SHA rev pin on the programme's forge URL, with no extra keys. Every
    other override — branch rev, foreign host, editable/path forms, extra
    keys, or any source for spec-kitty-tracker — stays a violation.
    """
    data = _load_pyproject()
    sources = data.get("tool", {}).get("uv", {}).get("sources", {})
    # The committed source must itself be the sanctioned shape.
    assert _is_sanctioned_events_git_pin(sources.get("spec-kitty-events"))
    assert _metadata_violations(data) == []

    def _with_events_source(source: dict[str, Any]) -> list[str]:
        mutated = copy.deepcopy(data)
        mutated.setdefault("tool", {}).setdefault("uv", {}).setdefault("sources", {})["spec-kitty-events"] = source
        return _metadata_violations(mutated)

    branch_rev = dict(sources["spec-kitty-events"], rev="main")
    assert _with_events_source(branch_rev)

    short_rev = dict(sources["spec-kitty-events"], rev="9fe7073")
    assert _with_events_source(short_rev)

    foreign_host = dict(sources["spec-kitty-events"], git="https://github.com/spec-kitty/EXPERIMENTAL-spec-kitty-events.git")
    assert _with_events_source(foreign_host)

    editable_extra = dict(sources["spec-kitty-events"], editable=True)
    assert _with_events_source(editable_extra)

    assert _with_events_source({"path": "../spec-kitty-events"})


def test_wheel_contains_every_first_party_runtime_import() -> None:
    """A clean wheel must contain every first-party package shipped code imports."""
    data = _load_pyproject()
    imported = _imported_first_party_packages(_SRC)
    assert imported
    assert _missing_wheel_packages(data, _SRC) == set()

    omitted = copy.deepcopy(data)
    victim = sorted(imported)[0]
    packages = omitted["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"]
    omitted["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"] = [path for path in packages if Path(path).name != victim]
    assert _missing_wheel_packages(omitted, _SRC) == {victim}


def _dependency_line(name: str) -> str:
    """Return the raw ``pyproject.toml`` line declaring dependency ``name``.

    ``tomllib`` discards comments, so the inline justification comment (e.g.
    ``# HTTP client for batch sync``) can only be checked against the raw text.
    """
    for line in _PYPROJECT.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith(f'"{name}') or stripped.startswith(f"'{name}"):
            return line
    raise AssertionError(f"no pyproject.toml dependency line found for {name!r}")


def test_requests_dependency_comment_names_its_real_retained_consumer() -> None:
    """R3-T1 (m1-contract-drafts/R3.md §2.7): ``requests`` is kept because
    ``doctrine/sources/{https_source,api_source}.py`` import it — a
    consumer unrelated to the retired batch-sync/dossier transport
    (``delivery/receivers.py``, R2's physical-deletion scope). The stale
    "batch sync" justification comment must not survive the transport
    module's eventual removal and mislead a future reader into deleting a
    dependency the doctrine-pack fetchers still need (§2.7 false-positive
    guard, D1).
    """
    line = _dependency_line("requests")
    assert "batch sync" not in line.lower(), (
        f"requests' pyproject.toml comment still cites the retired batch-sync "
        f"transport as its reason to exist: {line!r}"
    )

    # The dependency itself must stay declared — doctrine-pack HTTP/API
    # sources are retained, non-transport consumers (§2.7).
    doctrine_sources = _SRC / "specify_cli" / "doctrine" / "sources"
    consumers = [
        path
        for path in ("https_source.py", "api_source.py")
        if "import requests" in (doctrine_sources / path).read_text(encoding="utf-8")
    ]
    assert consumers == ["https_source.py", "api_source.py"], (
        "expected both doctrine-source fetchers to import requests directly; "
        f"found: {consumers}"
    )
