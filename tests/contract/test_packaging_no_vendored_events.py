"""Wheel-shape and filesystem assertions: no vendored spec-kitty-events tree.

Per FR-003 / FR-012 / FR-019 / C-002 of mission
shared-package-boundary-cutover-01KQ22DS, the CLI must not vendor or mirror
a copy of ``spec-kitty-events`` under ``specify_cli/spec_kitty_events/``.
The events package is consumed exclusively via the public PyPI dependency
``spec-kitty-events``.

This module provides two layers of mechanical enforcement:

1. ``test_vendored_events_tree_does_not_exist_on_disk`` (fast unit gate, no
   marker): a one-stat check that the directory is gone from the source
   tree. Catches the cheapest reintroduction (someone re-creates the
   directory but the files are not yet imported, so the import-graph rule
   in ``tests/architectural/test_shared_package_boundary.py`` would not
   fire).

2. ``test_wheel_does_not_contain_vendored_spec_kitty_events`` (distribution
   gate, marked ``distribution`` + ``contract``): builds the wheel and
   asserts the resulting archive does not contain
   ``specify_cli/spec_kitty_events/`` paths. This is FR-019's
   verification - the most expensive but most authoritative check.

See ADR ``architecture/2.x/adr/2026-04-25-1-shared-package-boundary.md``
for the rationale and ``kitty-specs/shared-package-boundary-cutover-01KQ22DS/spec.md``
for the constraint definitions.
"""
from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_vendored_events_tree_does_not_exist_on_disk() -> None:
    """C-002 / FR-003: ``src/specify_cli/spec_kitty_events/`` must not exist.

    This is the cheapest possible enforcement of the deletion: a one-stat
    check. The wheel-shape assertion
    (``test_wheel_does_not_contain_vendored_spec_kitty_events``) is the full
    distribution gate; this is the fast-gate companion that runs on every
    PR.

    Catches the case where a contributor re-creates the directory but the
    files are not yet imported (so the import-graph rule in
    ``tests/architectural/test_shared_package_boundary.py`` would not
    fire).
    """
    vendored = REPO_ROOT / "src" / "specify_cli" / "spec_kitty_events"
    assert not vendored.exists(), (
        f"Vendored events tree was reintroduced at {vendored}. "
        "Per FR-003 / C-002 of mission "
        "shared-package-boundary-cutover-01KQ22DS, the CLI must consume "
        "events through the public spec_kitty_events PyPI package only. "
        "Remove the directory and import from spec_kitty_events instead."
    )


@pytest.fixture(scope="module")
def built_wheel(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build a wheel into a tmp dir and return its path.

    Module-scoped because the wheel build is expensive (~tens of seconds);
    we reuse the same artifact across every distribution-marker test in
    this module.
    """
    tmp = tmp_path_factory.mktemp("wheel-build")
    subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(tmp)],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
    )
    wheels = list(tmp.glob("spec_kitty_cli-*.whl"))
    assert len(wheels) == 1, f"expected exactly one wheel, found {wheels}"
    return wheels[0]


@pytest.mark.distribution
def test_wheel_does_not_contain_vendored_spec_kitty_events(
    built_wheel: Path,
) -> None:
    """FR-019 / C-002: built wheel must not ship a vendored events tree.

    This is the authoritative enforcement: even if the source tree was
    perfectly clean, a misconfigured ``[tool.hatch.build.targets.wheel]``
    glob could still pull files into the wheel. The wheel inspection
    catches that case directly.
    """
    with zipfile.ZipFile(built_wheel) as z:
        offending = [
            name
            for name in z.namelist()
            if "specify_cli/spec_kitty_events/" in name
        ]
    assert not offending, (
        f"Wheel {built_wheel.name} contains vendored events paths: "
        f"{offending[:5]}{'...' if len(offending) > 5 else ''}. "
        "Per C-002 / FR-019 of mission "
        "shared-package-boundary-cutover-01KQ22DS, the CLI must not vendor "
        "or mirror the events package. Check "
        "[tool.hatch.build.targets.wheel] in pyproject.toml for stray "
        "globs that pull in specify_cli/spec_kitty_events/ paths."
    )
