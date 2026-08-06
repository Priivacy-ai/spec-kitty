"""WP02 / census rows 10 AND 11 — ``read_primary_meta``'s two reads fail closed.

Census rows 10 and 11 of
``kitty-specs/meta-fail-closed-3162-01KZ7FSQ/contracts/routing-manifest.md`` §1.4
are **two** ``load_meta`` calls inside ONE function,
``specify_cli.missions._read_path_resolver.read_primary_meta``:

* row 10 — ``load_meta(primary_dir) or {}`` (``:846``), the first read;
* row 11 — ``load_meta(canonical_dir) or {}`` (``:862``), the canonicalize-on-miss
  re-read taken when the topology-blind compose misses the primary dir.

They share **one** ledger row whose count is ``2``. Both are REFUSE-raw on the
signature default (``on_malformed="raise"``); WP02 routes each **individually**
onto ``specify_cli.core.paths.load_meta_fail_closed`` (FR-001).

The fold is the danger here, and it fails the gate DOWNWARD
-----------------------------------------------------------
``contracts/headroom-allocation.md`` §4: collapsing rows 10 and 11 into one read,
or hoisting a local helper around them, takes the lane's routed census from 129 to
128 — still inside the admissible band ``[127, 130]`` and green against all three
clauses of ``test_routed_load_meta_floor`` — and a second fold anywhere reaches
**126, which is RED** (clause 2, ``len(routed) > FLOOR``, is strict). The ledger
cannot catch a fold either: its ``grew`` arm fires on *more* live calls than a
row's count, and a fold produces *fewer*. So the fold is caught here, by the
``exactly two`` assertion, rather than only at integration.

``or {}`` is preserved verbatim at both sites (``C-001`` — no arm changes):
``load_meta_fail_closed`` hard-codes ``allow_missing=True`` and so returns ``None``
on absence exactly as ``load_meta`` did on the signature default, which keeps
``or {}`` meaning what it means today.

What is provable for row 11, and what is not
--------------------------------------------
Row 10's corrupt-file arm is driven end to end below. **Row 11's corrupt-file arm
is structurally unreachable**, and T011 step 2's prescribed fixture (a
non-composed handle — bare ``mid8`` or full ULID — with a corrupt primary
``meta.json``) does not reach ``:862``. Measured: the ``:862`` re-read's target is
``_canonicalize_handle``'s ``resolved.feature_dir``, and canonicalization runs
through ``specify_cli.context.mission_resolver._build_index``, which indexes with
``load_meta(entry, on_malformed="none")`` (``mission_resolver.py:176``) and
**skips** any dir whose ``meta.json`` is corrupt. A corrupt meta therefore makes
the handle unresolvable, ``_canonicalize_handle`` returns ``None``, and ``:862``
never executes — ``read_primary_meta`` returns ``({}, False)`` having never read
the corrupt file. The accept-sets of the two readers are identical (both reject
exactly "not a JSON object"), so no content can be valid for the indexer and
corrupt for the re-read. Verified for the composed handle, the bare ``mid8``, the
full ULID and the bare human slug.

Row 11 is therefore proved by (a) an execution trace showing the ``:862`` read is
performed BY ``load_meta_fail_closed`` on a real file through a public entry — a
behavioural proof, not a structural one, and not a patch — and (b) the
``exactly two`` AST assertion. Its refusal-on-corruption arm is unreachable
defensive hardening, recorded as such rather than asserted with a fixture that
silently tests row 10 instead.
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
import traceback
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from types import FrameType
from typing import Any

import pytest

from specify_cli.core.paths import MissionMetaReadError
from specify_cli.missions import _read_path_resolver as resolver_mod
from specify_cli.missions._read_path_resolver import (
    MissionSelectorAmbiguous,
    read_primary_meta,
)

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

#: Truncated, syntactically invalid JSON — a REAL corrupt file.
_CORRUPT_META = '{"mission_id":'

# Production-shaped identity (Mission Identity Model 083+).
_MISSION_ID = "01KVN754TY9CVJ8G10ERTMPVRH"
_MID8 = _MISSION_ID[:8]
_HUMAN_SLUG = "wp02-rows1011-probe"
_MISSION_SLUG = f"{_HUMAN_SLUG}-{_MID8}"

#: Census target, taken from the **imported** module's own ``__file__`` so the AST
#: census and the behavioural drive read the same tree by construction.
_RESOLVER_SRC = Path(resolver_mod.__file__)

#: The two reader names the execution trace distinguishes.
_ROUTED_READER = "load_meta_fail_closed"
_UNROUTED_READER = "load_meta"


def _git(repo_root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo_root), *args], check=True, capture_output=True, text=True
    )


def _build_mission(repo_root: Path, *, meta: str | None, dir_name: str = _MISSION_SLUG) -> Path:
    """Create ``kitty-specs/<dir_name>/`` in a real git repo, with *meta* content."""
    _git(repo_root, "init", "-q")
    _git(repo_root, "config", "user.email", "wp02-rows1011@example.test")
    _git(repo_root, "config", "user.name", "WP02 Rows1011 Probe")
    _git(repo_root, "commit", "--allow-empty", "-qm", "init")

    feature_dir = repo_root / "kitty-specs" / dir_name
    feature_dir.mkdir(parents=True)
    if meta is not None:
        (feature_dir / "meta.json").write_text(meta, encoding="utf-8")
    return feature_dir


def _valid_meta() -> str:
    return json.dumps({"mission_id": _MISSION_ID, "mid8": _MID8})


def direct_call_names(module_path: Path, func_name: str) -> Counter[str]:
    """Count calls by EXACT callee name inside *func_name*'s own body.

    Nested ``def`` / ``async def`` / ``lambda`` bodies are excluded. Callee names
    are exact, never substrings: ``load_meta_fail_closed`` counts under its own
    key and never increments ``load_meta``.
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


def routed_call_arguments(module_path: Path, func_name: str) -> list[str]:
    """Return the first positional argument NAME of each routed call, in source order.

    Pins that the two routed calls are the two ORIGINAL reads — one on
    ``primary_dir`` (census row 10) and one on ``canonical_dir`` (census row 11) —
    rather than two calls on the same directory, which a mechanical
    duplicate-to-satisfy-the-count edit would produce.
    """
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    target: ast.FunctionDef | ast.AsyncFunctionDef | None = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == func_name:
            target = node
            break
    assert target is not None, f"{func_name} is not defined in {module_path}"

    calls: list[tuple[int, str]] = []
    for node in ast.walk(target):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == _ROUTED_READER
            and node.args
            and isinstance(node.args[0], ast.Name)
        ):
            calls.append((node.lineno, node.args[0].id))
    return [name for _, name in sorted(calls)]


def trace_reader_calls(fn: Callable[..., Any], *args: Any) -> tuple[Any, Counter[str]]:
    """Run *fn* and count entries into each ``meta.json`` reader function.

    Uses :func:`sys.setprofile` — an observation of the real call stack, not a
    patch. The readers keep their real bodies and read real files, so this is a
    behavioural proof that the routed seam was entered, usable where the corrupt
    file cannot be placed (census row 11).
    """
    seen: Counter[str] = Counter()

    def _profile(frame: FrameType, event: str, _arg: Any) -> None:
        if event == "call" and frame.f_code.co_name in (_ROUTED_READER, _UNROUTED_READER):
            seen[frame.f_code.co_name] += 1

    sys.setprofile(_profile)
    try:
        result = fn(*args)
    finally:
        sys.setprofile(None)
    return result, seen


def assert_raised_from_the_routed_seam(exc: MissionMetaReadError) -> None:
    """Assert *exc* was raised BY ``load_meta_fail_closed`` (anti-``SC-001``)."""
    frames = traceback.extract_tb(exc.__traceback__)
    seam = [f for f in frames if f.name == _ROUTED_READER]
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


# --------------------------------------------------------------------------- #
# Census row 10 — the first read, ``load_meta(primary_dir) or {}`` at ``:846``
# --------------------------------------------------------------------------- #


def test_census_row10_corrupt_primary_meta_raises_typed_error_from_the_seam(
    tmp_path: Path,
) -> None:
    """Census row 10: a composed handle whose primary ``meta.json`` is corrupt."""
    _build_mission(tmp_path, meta=_CORRUPT_META)

    with pytest.raises(MissionMetaReadError) as excinfo:
        read_primary_meta(tmp_path, _MISSION_SLUG)

    assert_raised_from_the_routed_seam(excinfo.value)
    names = [f.name for f in traceback.extract_tb(excinfo.value.__traceback__)]
    assert "read_primary_meta" in names, names


def test_census_row10_corrupt_primary_meta_refuses_through_the_wider_seam(
    tmp_path: Path,
) -> None:
    """Census row 10 through ``resolve_handle_to_read_path``, the wider public seam."""
    _build_mission(tmp_path, meta=_CORRUPT_META)

    with pytest.raises(MissionMetaReadError) as excinfo:
        resolver_mod.resolve_handle_to_read_path(tmp_path, _MISSION_SLUG)

    assert_raised_from_the_routed_seam(excinfo.value)


# --------------------------------------------------------------------------- #
# Census row 11 — the canonicalize-on-miss re-read, ``load_meta(canonical_dir)``
# at ``:862``
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("handle", [_MID8, _MISSION_ID], ids=["bare-mid8", "full-ulid"])
def test_census_row11_canonicalize_on_miss_reread_goes_through_the_routed_seam(
    tmp_path: Path, handle: str
) -> None:
    """Census row 11: the ``:862`` re-read is performed BY ``load_meta_fail_closed``.

    A non-composed handle (bare ``mid8`` / full ULID) makes the topology-blind
    compose at ``:846`` miss, so the canonicalize-on-miss branch executes and
    ``:862`` re-reads the real primary dir. Both reads must be entered through the
    routed seam: ``load_meta_fail_closed`` is entered TWICE (once per census row),
    which is the behavioural signature of two routed sites and would read ``1``
    under a fold and ``0`` before routing.
    """
    _build_mission(tmp_path, meta=_valid_meta())

    (meta, declares_coordination), seen = trace_reader_calls(
        read_primary_meta, tmp_path, handle
    )

    assert meta == {"mission_id": _MISSION_ID, "mid8": _MID8}, meta
    assert declares_coordination is False
    assert seen[_ROUTED_READER] == 2, (
        "read_primary_meta must enter load_meta_fail_closed exactly TWICE — census "
        "row 10 (the primary compose, a miss here) and census row 11 (the "
        f"canonicalize-on-miss re-read). Got {seen[_ROUTED_READER]}; "
        f"full reader trace={dict(seen)}"
    )


def test_census_row11_corrupt_meta_arm_is_structurally_unreachable(
    tmp_path: Path,
) -> None:
    """Pin WHY census row 11's corrupt-file arm cannot be driven by a fixture.

    ``:862``'s target is ``_canonicalize_handle``'s resolved ``feature_dir``, and
    canonicalization indexes with ``load_meta(entry, on_malformed="none")``
    (``context/mission_resolver.py:176``), which SKIPS a corrupt ``meta.json``. So
    a corrupt meta makes the handle unresolvable and ``:862`` never runs. This test
    pins that observable contract, so if the canonicalizer ever grows a corruption-
    tolerant index the assertion goes red and row 11's arm becomes testable.

    Note this is NOT a fail-open at ``:846``/``:862``: the corrupt file is never
    read at all on this path, and ``({}, False)`` is the honest "no primary meta
    resolved for this handle" answer.
    """
    _build_mission(tmp_path, meta=_CORRUPT_META)

    for handle in (_MID8, _MISSION_ID, _HUMAN_SLUG):
        result, seen = trace_reader_calls(read_primary_meta, tmp_path, handle)
        assert result == ({}, False), (
            f"handle {handle!r} unexpectedly resolved past the corrupt meta: {result!r}"
        )
        assert seen[_ROUTED_READER] == 1, (
            f"handle {handle!r}: expected exactly ONE routed read (the primary "
            "compose miss) with the canonicalize-on-miss re-read never reached; "
            f"got {seen[_ROUTED_READER]} (trace={dict(seen)})"
        )


# --------------------------------------------------------------------------- #
# Structural proof — the anti-fold assertion for the count-2 ledger row
# --------------------------------------------------------------------------- #


def test_rows1011_are_two_distinct_routed_calls_and_are_not_folded() -> None:
    """The binding budget control for the count-2 ledger row: EXACTLY TWO calls."""
    counts = direct_call_names(_RESOLVER_SRC, "read_primary_meta")
    assert counts[_ROUTED_READER] == 2, (
        "read_primary_meta must hold EXACTLY TWO load_meta_fail_closed() calls in "
        "its own body — census row 10 (primary_dir) and census row 11 "
        "(canonical_dir). One means the two reads were FOLDED, which takes the "
        "lane's routed census to 128 and walks toward the RED 126. Got "
        f"{counts[_ROUTED_READER]}"
    )
    assert counts[_UNROUTED_READER] == 0, (
        "read_primary_meta still calls load_meta( directly; census rows 10/11 are "
        f"not both routed. count={counts[_UNROUTED_READER]}"
    )


def test_rows1011_routed_calls_keep_their_own_directory_arguments() -> None:
    """The two routed calls are the two ORIGINAL reads, not one read duplicated."""
    assert routed_call_arguments(_RESOLVER_SRC, "read_primary_meta") == [
        "primary_dir",
        "canonical_dir",
    ]


def test_resolver_module_carries_no_local_typed_raise() -> None:
    """The module must not manufacture the typed error itself (anti-``SC-001``)."""
    source = _RESOLVER_SRC.read_text(encoding="utf-8")
    assert "raise MissionMetaReadError" not in source, (
        "_read_path_resolver.py raises MissionMetaReadError locally — that is the "
        "SC-001 cheat, not routing through the seam"
    )


def test_declares_coordination_branch_keeps_its_silent_by_contract_reader() -> None:
    """The ``on_malformed="none"`` read at ``:113`` is NOT this mission's site.

    ``_declares_coordination_branch`` is a ``silent-by-contract`` site with its own
    ledger row that must survive WP02. Its in-function ``load_meta`` import and its
    ``on_malformed="none"`` call stay exactly as they are; routing it would change
    an arm (``C-001``).
    """
    counts = direct_call_names(_RESOLVER_SRC, "_declares_coordination_branch")
    assert counts[_UNROUTED_READER] == 1, (
        "_declares_coordination_branch's silent-by-contract load_meta("
        'on_malformed="none") read was changed; it is not WP02\'s site. '
        f"count={counts[_UNROUTED_READER]}"
    )
    assert counts[_ROUTED_READER] == 0, (
        "_declares_coordination_branch was routed onto the fail-closed reader — "
        "that flips a silent-by-contract arm (C-001) and spends routed headroom"
    )


# --------------------------------------------------------------------------- #
# Negative controls — ``C-001`` / ``NFR-001``
# --------------------------------------------------------------------------- #


def test_negative_control_valid_primary_meta_returns_meta_and_topology(
    tmp_path: Path,
) -> None:
    """``C-001``: valid primary meta still returns ``(meta, declares_coordination)``."""
    _build_mission(tmp_path, meta=_valid_meta())
    assert read_primary_meta(tmp_path, _MISSION_SLUG) == (
        {"mission_id": _MISSION_ID, "mid8": _MID8},
        False,
    )


def test_negative_control_declared_coordination_branch_is_reported(
    tmp_path: Path,
) -> None:
    """``C-001``: the ``coordination_branch`` arm is unchanged."""
    _build_mission(
        tmp_path,
        meta=json.dumps(
            {
                "mission_id": _MISSION_ID,
                "mid8": _MID8,
                "coordination_branch": f"kitty/mission-{_MISSION_SLUG}",
            }
        ),
    )
    meta, declares_coordination = read_primary_meta(tmp_path, _MISSION_SLUG)
    assert declares_coordination is True
    assert meta["coordination_branch"] == f"kitty/mission-{_MISSION_SLUG}"


def test_negative_control_absent_primary_meta_returns_empty_pair(
    tmp_path: Path,
) -> None:
    """``NFR-001`` absent-file arm: no primary meta still returns ``({}, False)``."""
    _build_mission(tmp_path, meta=None)
    assert read_primary_meta(tmp_path, _MISSION_SLUG) == ({}, False)


def test_negative_control_ambiguous_handle_still_propagates(tmp_path: Path) -> None:
    """``MissionSelectorAmbiguous`` is a plain ``Exception`` and must NOT be caught.

    It is raised inside ``read_primary_meta``'s canonicalization path. WP02 adds no
    ``except`` clause at all, so the refusal must still propagate — an
    ``except Exception`` anywhere near the routed sites would swallow it.
    """
    _build_mission(tmp_path, meta=_valid_meta(), dir_name=f"alpha-{_MID8}")
    second = tmp_path / "kitty-specs" / f"beta-{_MID8}"
    second.mkdir(parents=True)
    (second / "meta.json").write_text(
        json.dumps({"mission_id": f"{_MID8}ZZZZZZZZZZZZZZZZZZ"[:26], "mid8": _MID8}),
        encoding="utf-8",
    )

    with pytest.raises(MissionSelectorAmbiguous):
        read_primary_meta(tmp_path, _MID8)
