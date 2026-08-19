"""AST guard: no module may EARLY-BIND a patched ``sync`` seam callee.

Wave-4 ``sync.py`` de-god (mission ``sync-cli-degod-wave4-01M0B0MX``) relocates
private bodies out of ``specify_cli.cli.commands.sync`` into cohesive
``specify_cli.sync.*`` seam modules. ~79 tests keep those callees under test via
``monkeypatch.setattr("...cli.commands.sync.<name>", <double>)``; the
deduplicated callee set is the live co-gate
:data:`SYNC_MONKEYPATCH_SEAM_NAMES` in the WP02 golden harness.

A ``monkeypatch.setattr`` rebinds the **module attribute**
``sync.<name>``. Any module that captures the ORIGINAL object with a top-level
``from ...cli.commands.sync import <name>`` early-binds a local name the patch
can never see -- silently defeating the seam. This guard parses the ``src`` tree
and FAILS if any relocated shell (or any other production module) early-binds a
seam name off the ``sync`` command module. The ALLOWED direction -- the husk
re-export block re-importing a relocated private FROM a ``specify_cli.sync.*``
seam module back INTO the host -- does not match (its target is not the ``sync``
command module), so it is exempt.

Rule the guard locks in (WP03 T007, INV-4 / WP-translation guard #2): reach a
patched callee by ATTRIBUTE ACCESS on the host module object
(``sync_module.<name>`` / ``getattr``), never by an early-bound ``import``.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tests.characterization.test_sync_cli_safe import SYNC_MONKEYPATCH_SEAM_NAMES

pytestmark = [pytest.mark.architectural, pytest.mark.fast]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_ROOT = _REPO_ROOT / "src"

# The host module OWNS these names; it does not early-bind them from itself, and
# its husk re-export block imports FROM seam modules (a different target). Skip
# it so the guard only polices *consumers* of the seam.
_HOST_RELATIVE = "specify_cli/cli/commands/sync.py"

# The dotted module every forbidden early-bind resolves to.
_SYNC_COMMAND_MODULE = "specify_cli.cli.commands.sync"

_SEAM_NAMES = frozenset(SYNC_MONKEYPATCH_SEAM_NAMES)


def _resolve_import_module(file_path: Path, node: ast.ImportFrom, src_root: Path) -> str | None:
    """Resolve an ``ImportFrom`` node to its absolute dotted module, or ``None``.

    Absolute imports return ``node.module`` verbatim. Relative imports
    (``level > 0``) are resolved against the importing file's package so a
    ``from ...cli.commands.sync import _foo`` inside ``specify_cli.sync`` still
    resolves to the concrete target.
    """
    if node.level == 0:
        return node.module

    package_parts = list(file_path.relative_to(src_root).with_suffix("").parts)
    # Drop the module's own leaf; a module file's ``level == 1`` means "this
    # package", ``level == 2`` means the parent package, and so on.
    package_parts = package_parts[:-1]
    ascend = node.level - 1
    if ascend > len(package_parts):
        return None
    base_parts = package_parts[: len(package_parts) - ascend] if ascend else package_parts
    if node.module:
        base_parts = [*base_parts, *node.module.split(".")]
    return ".".join(base_parts) if base_parts else None


def _early_bind_violations(src_root: Path) -> dict[str, list[int]]:
    """Map ``src``-relative path -> line numbers that early-bind a seam name."""
    violations: dict[str, list[int]] = {}
    for path in sorted(src_root.rglob("*.py")):
        relative = path.relative_to(src_root).as_posix()
        if relative == _HOST_RELATIVE:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        hits: list[int] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            resolved = _resolve_import_module(path, node, src_root)
            if resolved != _SYNC_COMMAND_MODULE:
                continue
            if any(alias.name in _SEAM_NAMES for alias in node.names):
                hits.append(node.lineno)
        if hits:
            violations[relative] = hits
    return violations


def test_seam_set_is_the_wp02_co_gate() -> None:
    """The guard binds the real WP02 seam-callee set, not a local guess."""
    assert _SEAM_NAMES, "SYNC_MONKEYPATCH_SEAM_NAMES must be non-empty"
    # Anchor on two representative callees so a rename of the source tuple is caught.
    assert "get_vcs" in _SEAM_NAMES
    assert "_check_server_connection" in _SEAM_NAMES


def test_no_production_module_early_binds_a_sync_seam() -> None:
    """No ``src`` module early-binds a patched ``sync`` seam callee (INV-4)."""
    assert _SRC_ROOT.is_dir()
    assert _early_bind_violations(_SRC_ROOT) == {}


def test_guard_detects_a_planted_early_bind(tmp_path: Path) -> None:
    """Positive control: a forbidden early-bind is caught; the allowed
    re-import direction (from a ``specify_cli.sync.*`` seam module) is not."""
    src = tmp_path / "src"
    seam_name = next(iter(_SEAM_NAMES))

    offender = src / "specify_cli" / "sync" / "sync_status.py"
    offender.parent.mkdir(parents=True, exist_ok=True)
    offender.write_text(
        f"from specify_cli.cli.commands.sync import {seam_name}\n",
        encoding="utf-8",
    )

    # Allowed: the husk re-export direction (host <- seam module) targets the
    # seam module, NOT the sync command module, so it must NOT be flagged.
    allowed = src / "specify_cli" / "sync" / "sync_authority.py"
    allowed.write_text(
        f"from specify_cli.sync.sync_status import {seam_name}\n",
        encoding="utf-8",
    )

    # Allowed: the late-bound convention (module import + attribute access).
    late_bound = src / "specify_cli" / "sync" / "sync_render.py"
    late_bound.write_text(
        "import specify_cli.cli.commands.sync as sync_module\n"
        f"sync_module.{seam_name}()\n",
        encoding="utf-8",
    )

    violations = _early_bind_violations(src)
    assert violations == {"specify_cli/sync/sync_status.py": [1]}
