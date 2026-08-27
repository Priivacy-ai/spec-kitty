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
_UV_LOCK = _REPO_ROOT / "uv.lock"
_SRC = _REPO_ROOT / "src"
_SHARED_PACKAGES = ("spec-kitty-events", "spec-kitty-tracker")
_RETIRED_PACKAGE = "spec-kitty-runtime"
_SHIPPED_TREES = ("specify_cli", "runtime")
_DEP_NAME_TERMINATORS = "[=<>!~;@ "
# The sanctioned direct references (controller-qa on #58, PROGRAM.md §2's
# wheel-installability exception): pinned-rev git dependencies on the shared
# packages (EXPERIMENTAL-spec-kitty-planning#31). [tool.uv.sources] does not travel
# into the wheel's Requires-Dist, so the pin must live in the dependency
# itself; the host must always be github.com, never the exe.dev
# github.int.exe.xyz forge proxy (laptops cannot resolve that proxy). Any
# [tool.uv.sources] override stays
# a violation, as does any other direct reference (foreign host, branch rev,
# short SHA, path/editable form).
_SHARED_SOURCE_REPO_URLS = {package: f"https://github.com/spec-kitty/EXPERIMENTAL-{package}" for package in _SHARED_PACKAGES}
_SANCTIONED_SHARED_GIT_DEPS = {
    package: re.compile(rf"^{package} @ git\+{re.escape(url)}@(?P<rev>[0-9a-f]{{40}})$") for package, url in _SHARED_SOURCE_REPO_URLS.items()
}


def _load_pyproject() -> dict[str, Any]:
    return tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))


def _load_uv_lock() -> dict[str, Any]:
    return tomllib.loads(_UV_LOCK.read_text(encoding="utf-8"))


def _dep_name(entry: str) -> str:
    for index, char in enumerate(entry):
        if char in _DEP_NAME_TERMINATORS:
            return entry[:index].strip()
    return entry.strip()


def _is_sanctioned_shared_git_dependency(package: str, entry: str) -> bool:
    """True for the sanctioned pinned-rev git dependency on a shared package."""
    return bool(_SANCTIONED_SHARED_GIT_DEPS[package].match(entry.strip()))


def _is_direct_reference(entry: str) -> bool:
    return " @ " in entry


def _metadata_violations(data: dict[str, Any]) -> list[str]:
    dependencies = data.get("project", {}).get("dependencies", [])
    by_name = {_dep_name(entry): entry for entry in dependencies}
    failures: list[str] = []
    for package in _SHARED_PACKAGES:
        entry = by_name.get(package)
        if entry is None:
            failures.append(f"missing consumed dependency {package}")
        elif _is_sanctioned_shared_git_dependency(package, entry):
            pass
        elif "==" in entry:
            failures.append(f"exact runtime pin for {package}: {entry}")
        elif _is_direct_reference(entry):
            failures.append(f"unsanctioned direct reference for {package}: {entry}")
    if _RETIRED_PACKAGE in by_name:
        failures.append(f"retired dependency present: {by_name[_RETIRED_PACKAGE]}")

    sources = data.get("tool", {}).get("uv", {}).get("sources", {})
    for package in (*_SHARED_PACKAGES, _RETIRED_PACKAGE):
        if package in sources:
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


@pytest.mark.parametrize("package", _SHARED_PACKAGES)
def test_shared_dependency_and_lock_use_the_sanctioned_pinned_git_reference(package: str) -> None:
    """Each shared dependency admits exactly one sanctioned direct reference.

    The sanctioned shape (controller-qa fix round on #58, interim to
    planning#31; PROGRAM.md §2's wheel-installability exception) is a
    full-SHA rev pin on ``github.com``, declared directly in
    ``dependencies`` — never in ``[tool.uv.sources]``, which does not travel
    into the wheel's ``Requires-Dist``. Every other shape — a
    ``[tool.uv.sources]`` override, a branch rev, a short SHA, the
    exe.dev forge host, or an editable/path form — stays a violation.
    """
    data = _load_pyproject()
    dependencies = data["project"]["dependencies"]
    by_name = {_dep_name(entry): entry for entry in dependencies}
    # The committed dependency must itself be the sanctioned shape.
    assert _is_sanctioned_shared_git_dependency(package, by_name[package])
    assert _metadata_violations(data) == []

    def _with_dependency(new_entry: str) -> list[str]:
        mutated = copy.deepcopy(data)
        mutated["project"]["dependencies"] = [new_entry if _dep_name(entry) == package else entry for entry in dependencies]
        return _metadata_violations(mutated)

    repo_url = _SHARED_SOURCE_REPO_URLS[package]
    rev_match = _SANCTIONED_SHARED_GIT_DEPS[package].match(by_name[package])
    assert rev_match is not None
    rev = rev_match.group("rev")

    lock = _load_uv_lock()
    locked_package = next(item for item in lock["package"] if item["name"] == package)
    assert locked_package["source"] == {"git": f"{repo_url}?rev={rev}#{rev}"}

    cli = next(item for item in lock["package"] if item["name"] == "spec-kitty-cli")
    locked_requirement = next(item for item in cli["metadata"]["requires-dist"] if item["name"] == package)
    assert locked_requirement == {"name": package, "git": f"{repo_url}?rev={rev}"}

    branch_rev = f"{package} @ git+{repo_url}@main"
    assert _with_dependency(branch_rev)

    short_rev = f"{package} @ git+{repo_url}@{rev[:7]}"
    assert _with_dependency(short_rev)

    foreign_host = f"{package} @ git+{repo_url.replace('github.com', 'github.int.exe.xyz')}@{rev}"
    assert _with_dependency(foreign_host)

    path_form = f"{package} @ file:///opt/checkouts/{package}"
    assert _with_dependency(path_form)

    # A [tool.uv.sources] override is never sanctioned, even alongside the
    # correct direct reference — it is committed local resolution metadata.
    with_source_override = copy.deepcopy(data)
    with_source_override.setdefault("tool", {}).setdefault("uv", {}).setdefault("sources", {})[package] = {
        "git": repo_url,
        "rev": rev,
    }
    assert _metadata_violations(with_source_override)


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
