"""WP02 / census row 5 — ``runtime_bridge_io._workflow_runtime_template`` fails closed.

Census row 5 of ``kitty-specs/meta-fail-closed-3162-01KZ7FSQ/contracts/routing-manifest.md``
§1.4: ``runtime.next.runtime_bridge_io._workflow_runtime_template`` reads
``meta.json`` through ``specify_cli.mission_metadata.load_meta`` on the signature
default (``on_malformed="raise"``) with **no** handler — the REFUSE-raw arm. WP02
routes it onto ``specify_cli.core.paths.load_meta_fail_closed`` (FR-001).

Fixture correction to the WP02 prompt, measured
-----------------------------------------------
T008 step 1 prescribes "a ``tmp_path`` repo root with ``kitty-specs/<slug>-<mid8>/
meta.json`` written corrupt", driven through ``get_or_start_run``. **That fixture
never reaches census row 5.** ``_workflow_runtime_template`` resolves the mission
dir on its own first line via ``runtime_bridge._resolve_runtime_feature_dir``,
which routes through ``specify_cli.missions._read_path_resolver.read_primary_meta``
— census rows 10/11. A corrupt PRIMARY ``meta.json`` therefore raises out of
``read_primary_meta`` (``_read_path_resolver.py:846``) and row 5's own read is
never executed. Measured traceback on the unrouted tree:

    get_or_start_run            @ runtime_bridge_io.py:499
    _workflow_runtime_template  @ runtime_bridge_io.py:376   <- the RESOLVE, not the read
    _resolve_runtime_feature_dir@ runtime_bridge.py:1138
    resolve_handle_to_read_path @ _read_path_resolver.py:966
    read_primary_meta           @ _read_path_resolver.py:846 <- census row 10 fires here

Row 5's read at ``:380`` is reachable only when the resolved read-surface dir is a
DIFFERENT directory from the primary one — i.e. a **coord topology**: a valid
primary ``meta.json`` declaring ``coordination_branch`` plus a materialized
``.worktrees/<slug>-<mid8>-coord/`` whose own ``meta.json`` is corrupt. That is
the fixture built below, and it does reach ``:380`` through the public entry.

Proofs: behavioural (a ``load_meta_fail_closed`` frame in ``core/paths.py`` plus
``__cause__`` preservation) **and** structural (an exact-callee-name AST
call-count assertion over the routed function's own body). ``C-001``: the
``if meta is None: return None, None`` arm and the ``workflow_id is None`` arm are
unchanged, pinned by the negative controls.
"""

from __future__ import annotations

import ast
import json
import subprocess
import traceback
from collections import Counter
from pathlib import Path

import pytest

from runtime.next import runtime_bridge_io as io_seam
from specify_cli.core.paths import MissionMetaReadError

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

#: Truncated, syntactically invalid JSON — a REAL corrupt file.
_CORRUPT_META = '{"workflow_id":'

# Production-shaped identity (Mission Identity Model 083+): a real 26-char ULID
# with the first 8 chars as the mid8 disambiguator, and the real on-disk
# ``kitty-specs/<slug>-<mid8>/`` layout.
_MISSION_ID = "01KVN754TY9CVJ8G10ERTMPVRH"
_MID8 = _MISSION_ID[:8]
_MISSION_SLUG = f"wp02-row05-probe-{_MID8}"
_COORD_BRANCH = f"kitty/mission-{_MISSION_SLUG}"
_MISSION_TYPE = "software-dev"
_TEMPLATE_KEY = "software-dev"

#: Census target, taken from the **imported** module's own ``__file__`` so the AST
#: census and the behavioural drive read the same tree by construction.
_BRIDGE_IO_SRC = Path(io_seam.__file__)


def _git(repo_root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo_root), *args], check=True, capture_output=True, text=True
    )


def _build_coord_topology(repo_root: Path, *, coord_meta: str | None) -> None:
    """Build a coord-topology mission whose COORD-surface meta is *coord_meta*.

    The primary ``meta.json`` is always valid and declares ``coordination_branch``,
    so ``read_primary_meta`` (census rows 10/11) succeeds and the read-path seam
    resolves the materialized coord worktree as the read surface. Row 5's own read
    then lands on the coord dir — the only dir whose content row 5 can observe.
    """
    _git(repo_root, "init", "-q")
    _git(repo_root, "config", "user.email", "wp02-row05@example.test")
    _git(repo_root, "config", "user.name", "WP02 Row05 Probe")
    _git(repo_root, "commit", "--allow-empty", "-qm", "init")
    _git(repo_root, "branch", _COORD_BRANCH)

    primary = repo_root / "kitty-specs" / _MISSION_SLUG
    primary.mkdir(parents=True)
    (primary / "meta.json").write_text(
        json.dumps(
            {
                "mission_id": _MISSION_ID,
                "mid8": _MID8,
                "coordination_branch": _COORD_BRANCH,
            }
        ),
        encoding="utf-8",
    )

    coord = repo_root / ".worktrees" / f"{_MISSION_SLUG}-coord" / "kitty-specs" / _MISSION_SLUG
    coord.mkdir(parents=True)
    if coord_meta is not None:
        (coord / "meta.json").write_text(coord_meta, encoding="utf-8")


def direct_call_names(module_path: Path, func_name: str) -> Counter[str]:
    """Count calls by EXACT callee name inside *func_name*'s own body.

    Nested ``def`` / ``async def`` / ``lambda`` bodies are excluded. Callee names
    are exact, never substrings: ``load_meta_fail_closed`` counts under its own
    key and never increments ``load_meta``, so a fold cannot hide behind a
    substring match.
    """
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    target: ast.FunctionDef | ast.AsyncFunctionDef | None = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == func_name:
            target = node
            break
    assert target is not None, f"{func_name} is not defined in {module_path}"

    counts: Counter[str] = Counter()
    stack: list[ast.AST] = list(ast.iter_child_nodes(target))
    while stack:
        node = stack.pop()
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda):
            continue
        if isinstance(node, ast.Call):
            callee = node.func
            if isinstance(callee, ast.Name):
                counts[callee.id] += 1
            elif isinstance(callee, ast.Attribute):
                counts[callee.attr] += 1
        stack.extend(ast.iter_child_nodes(node))
    return counts


def assert_raised_from_the_routed_seam(exc: MissionMetaReadError) -> None:
    """Assert *exc* was raised BY ``load_meta_fail_closed`` (anti-``SC-001``)."""
    frames = traceback.extract_tb(exc.__traceback__)
    seam = [f for f in frames if f.name == "load_meta_fail_closed"]
    assert seam, (
        "no 'load_meta_fail_closed' frame in the traceback — the typed error did "
        "not come from the routed seam (SC-001 cheat shape). frames="
        f"{[f.name for f in frames]}"
    )
    assert seam[0].filename.replace("\\", "/").endswith("core/paths.py"), (
        f"the load_meta_fail_closed frame is not core/paths.py: {seam[0].filename}"
    )
    assert isinstance(exc.__cause__, ValueError), (
        f"the decode ValueError was not preserved as __cause__; got {exc.__cause__!r}"
    )
    assert not isinstance(exc, ValueError), (
        "MissionMetaReadError must NOT be a ValueError, or existing 'except "
        "ValueError' arms would absorb the fail-closed refusal"
    )


def test_census_row05_corrupt_meta_raises_typed_error_through_get_or_start_run(
    tmp_path: Path,
) -> None:
    """Census row 5 via the public entry ``runtime_bridge_io.get_or_start_run``."""
    _build_coord_topology(tmp_path, coord_meta=_CORRUPT_META)

    with pytest.raises(MissionMetaReadError) as excinfo:
        io_seam.get_or_start_run(_MISSION_SLUG, tmp_path, _MISSION_TYPE)

    assert_raised_from_the_routed_seam(excinfo.value)
    # The read that raised must be row 5's own, not census row 10's: the frame
    # immediately above the seam is _workflow_runtime_template, and no
    # read_primary_meta frame is present at all.
    names = [f.name for f in traceback.extract_tb(excinfo.value.__traceback__)]
    assert "_workflow_runtime_template" in names, names
    assert "read_primary_meta" not in names, (
        "the refusal came from census rows 10/11, not census row 5 — the fixture "
        f"shadowed row 5's own read. frames={names}"
    )


def test_census_row05_corrupt_meta_raises_typed_error_through_ephemeral_query_run(
    tmp_path: Path,
) -> None:
    """Second probe: ``_start_ephemeral_query_run``, row 5's other caller."""
    _build_coord_topology(tmp_path, coord_meta=_CORRUPT_META)

    with pytest.raises(MissionMetaReadError) as excinfo:
        io_seam._start_ephemeral_query_run(_MISSION_SLUG, _MISSION_TYPE, tmp_path)

    assert_raised_from_the_routed_seam(excinfo.value)


def test_census_row05_is_routed_exactly_once_and_is_not_folded() -> None:
    """Census row 5's structural proof — the per-site call-count assertion."""
    counts = direct_call_names(_BRIDGE_IO_SRC, "_workflow_runtime_template")
    assert counts["load_meta_fail_closed"] == 1, (
        "_workflow_runtime_template must hold EXACTLY ONE load_meta_fail_closed("
        f") call in its own body; found {counts['load_meta_fail_closed']}"
    )
    assert counts["load_meta"] == 0, (
        "_workflow_runtime_template still calls load_meta( directly; census row 5 "
        f"is not routed. count={counts['load_meta']}"
    )


def test_census_row05_module_carries_no_local_typed_raise() -> None:
    """The module must not manufacture the typed error itself (anti-``SC-001``)."""
    source = _BRIDGE_IO_SRC.read_text(encoding="utf-8")
    assert "raise MissionMetaReadError" not in source, (
        "runtime_bridge_io.py raises MissionMetaReadError locally — that is the "
        "SC-001 cheat, not routing through the seam"
    )


def test_census_row05_negative_control_absent_meta_returns_none_pair(
    tmp_path: Path,
) -> None:
    """``NFR-001`` absent-file arm: a missing ``meta.json`` keeps ``(None, None)``."""
    _build_coord_topology(tmp_path, coord_meta=None)
    assert io_seam._workflow_runtime_template(
        _MISSION_SLUG, _MISSION_TYPE, tmp_path, _TEMPLATE_KEY
    ) == (None, None)


def test_census_row05_negative_control_valid_meta_returns_none_pair(
    tmp_path: Path,
) -> None:
    """``C-001``: a valid ``meta.json`` without ``workflow_id`` keeps its arm."""
    _build_coord_topology(tmp_path, coord_meta=json.dumps({"mission_id": _MISSION_ID}))
    assert io_seam._workflow_runtime_template(
        _MISSION_SLUG, _MISSION_TYPE, tmp_path, _TEMPLATE_KEY
    ) == (None, None)
