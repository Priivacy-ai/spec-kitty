"""WP04 / SC-007 — the two behaviours inside ``resolution.py:517``'s ``try`` that
are NOT the ``meta.json`` read, plus the never-``except Exception`` rule across all
six ``C-002`` handlers.

Mission ``meta-fail-closed-3162-01KZ7FSQ``.

``_mid8_from_primary_meta``'s ``try`` is the only one of the four routed degrade
sites that wraps **more than the read**: ``_compose_primary_feature_dir`` and
``_canonicalize_primary_read_handle`` are inside it. That makes two extra
behaviours load-bearing, and both are pinned here as **assertions** rather than
narrated in a comment.
"""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path

import pytest

from mission_runtime.resolution import _mid8_from_primary_meta
from specify_cli.missions._read_path_resolver import MissionSelectorAmbiguous

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

_REPO_ROOT = Path(__file__).resolve().parents[2]

#: The SIX handlers C-002 governs, keyed by (module path, enclosing symbol).
#: Keyed by SYMBOL, never by line number: five commits move lines in this lane.
_C002_HANDLERS = [
    ("src/mission_runtime/resolution.py", "_mid8_from_primary_meta"),
    ("src/mission_runtime/resolution.py", "_resolve_coordination_branch"),
    ("src/mission_runtime/resolution.py", "_resolve_mission_id"),
    ("src/specify_cli/decisions/service.py", "_resolve_mission_id"),
    ("src/specify_cli/missions/_resolve_planning_branch.py", "load_mission_target_branch"),
    ("src/specify_cli/upgrade/feature_meta.py", "load_feature_meta"),
]


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True)


def _make_root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir(parents=True)
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "wp04-sc007@example.test")
    _git(root, "config", "user.name", "WP04 SC007")
    _git(root, "commit", "--allow-empty", "-qm", "init")
    (root / ".kittify").mkdir()
    (root / "kitty-specs").mkdir()
    return root


# --------------------------------------------------------------------------
# SC-007 (a) -- the traversal guard, asserting the OUTCOME
# --------------------------------------------------------------------------


@pytest.mark.parametrize("unsafe_slug", ["..evil", "a..b", "evil/../x", ".hidden", "foo/bar"])
def test_sc007a_traversal_guard_still_degrades_to_empty_string(
    tmp_path: Path, unsafe_slug: str
) -> None:
    """A path-traversal slug must keep degrading to ``""`` -- assert the OUTCOME.

    ``_compose_primary_feature_dir`` raises a **real** ``ValueError`` from
    ``assert_safe_path_segment`` (``core/paths.py:40``, reached via
    ``_read_path_resolver.py:1307``) *inside* ``_mid8_from_primary_meta``'s
    ``try``. ``SC-007`` requires that behaviour be unchanged by the routing, so
    the handler at ``resolution.py:523`` is the TUPLE
    ``except (ValueError, MissionMetaReadError)`` and must never be narrowed.

    **Do not rewrite this as ``pytest.raises(ValueError)``.** That form is the
    documented cheat: it is red at baseline and *green after a narrowing*, so it
    would report ``SC-007`` satisfied while silently deleting the very
    degrade-to-``""`` behaviour this test exists to protect. Measured: with the
    handler narrowed to ``MissionMetaReadError`` alone, ``..evil`` raises
    ``ValueError: Not a safe path segment: '..evil' -- value must not contain '..'``
    instead of returning ``""``. Asserting the return value is what makes this
    test sensitive to the narrowing; asserting the raise inverts it.
    """
    result = _mid8_from_primary_meta(_make_root(tmp_path), unsafe_slug)

    assert result == "", (
        "SC-007(a) violated: the path-traversal guard inside "
        "_mid8_from_primary_meta's try (src/mission_runtime/resolution.py, "
        "handler at the `except (ValueError, MissionMetaReadError)` tuple) must "
        f"keep degrading an unsafe segment to the empty string, got {result!r}. "
        "A narrowed handler raises ValueError here instead."
    )


# --------------------------------------------------------------------------
# SC-007 (b) -- MissionSelectorAmbiguous still propagates
# --------------------------------------------------------------------------


def test_sc007b_ambiguous_handle_propagates_out_of_mid8_from_primary_meta(
    tmp_path: Path,
) -> None:
    """An ambiguous mission handle must raise **out of** ``_mid8_from_primary_meta``.

    ``MissionSelectorAmbiguous`` is deliberately a plain ``Exception``
    (``src/specify_cli/missions/_read_path_resolver.py:49``), **not** a
    ``ValueError``, and is raised by ``_canonicalize_primary_read_handle``
    *inside* the same ``try`` as the routed read. It must keep propagating --
    neither swallowed nor converted into the ``""`` sentinel.

    This is the assertion form of the in-code note at
    ``src/mission_runtime/resolution.py`` (the ``MissionSelectorAmbiguous`` note,
    which is a **separate** fact from the traversal-``ValueError`` note directly
    above it -- the two must be cited separately). A comment claiming the note
    "still holds" is not evidence; this is.

    It is also what makes ``except Exception`` at that handler unacceptable: a
    broadened catch would swallow this refusal and silently return ``""`` for an
    ambiguous handle, reintroducing the no-silent-fallback regression the
    mission-identity model (WP07 of #083) exists to prevent.
    """
    root = _make_root(tmp_path)
    shared_mid8 = "01KWP04A"
    for name, mission_id in (
        ("alpha", "01KWP04AMBIGX111111111111X"),
        ("beta", "01KWP04AMBIGX222222222222X"),
    ):
        mission_dir = root / "kitty-specs" / f"{name}-{shared_mid8}"
        mission_dir.mkdir(parents=True)
        (mission_dir / "meta.json").write_text(
            f'{{"mission_id": "{mission_id}", "mission_slug": "{name}"}}', encoding="utf-8"
        )
        (mission_dir / "spec.md").write_text("# ambiguity probe\n", encoding="utf-8")

    with pytest.raises(MissionSelectorAmbiguous) as excinfo:
        _mid8_from_primary_meta(root, shared_mid8)

    message = str(excinfo.value)
    assert shared_mid8 in message
    assert f"alpha-{shared_mid8}" in message and f"beta-{shared_mid8}" in message, (
        "SC-007(b): MissionSelectorAmbiguous propagated but did not name both "
        f"candidate missions, so the refusal is not diagnosable: {message!r}"
    )


# --------------------------------------------------------------------------
# SC-007 (c) -- no `except Exception` at any of the six C-002 handlers
# --------------------------------------------------------------------------


def _handler_clauses(module_rel: str, symbol: str) -> list[ast.ExceptHandler]:
    """Every ``except`` clause inside *symbol*'s own body in *module_rel*."""
    path = _REPO_ROOT / module_rel
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    targets = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == symbol
    ]
    # golden-count: cardinality-is-contract
    # Every element of `targets` is an ast.FunctionDef whose `.name` is `symbol` by
    # construction of the filter above, so the elements are indistinguishable and a
    # member-set equality carries strictly LESS information than the count. The
    # contract here is uniqueness of the definition. Escape hatch per
    # test_golden_count_ban's documented policy; folded by WP08.
    assert len(targets) == 1, (  # golden-count: cardinality-is-contract
        f"expected exactly one definition of {symbol!r} in {module_rel}, found {len(targets)}"
    )
    return [n for n in ast.walk(targets[0]) if isinstance(n, ast.ExceptHandler)]


def _caught_names(handler: ast.ExceptHandler) -> list[str]:
    node = handler.type
    if node is None:
        return ["<bare except>"]
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, ast.Tuple):
        return [e.id for e in node.elts if isinstance(e, ast.Name)]
    return [ast.dump(node)]


def test_sc007c_no_bare_or_broad_except_at_any_of_the_six_c002_handlers() -> None:
    """None of the six ``C-002`` handlers may catch ``Exception`` or be bare.

    Enumerated by **symbol**, not line number, over all six -- including the two
    modules this work package does not own (``decisions/service.py``,
    ``missions/_resolve_planning_branch.py``), which are read **read-only** here.

    ``except Exception`` at ``_mid8_from_primary_meta`` would swallow
    ``MissionSelectorAmbiguous`` (a plain ``Exception``); at the others it would
    absorb unrelated failures the fail-closed doctrine requires stay visible.
    """
    offenders: list[str] = []
    inspected = 0

    for module_rel, symbol in _C002_HANDLERS:
        for handler in _handler_clauses(module_rel, symbol):
            inspected += 1
            names = _caught_names(handler)
            if "Exception" in names or "BaseException" in names or "<bare except>" in names:
                offenders.append(f"{module_rel}::{symbol} line {handler.lineno} catches {names}")

    print(
        f"SC-007(c) INPUT: {len(_C002_HANDLERS)} handlers enumerated by symbol, "
        f"{inspected} except-clauses inspected"
    )
    # Content equality, not `len(_C002_HANDLERS) == 6`: a bare cardinality passes
    # when one governed handler is swapped for another, which is exactly the edit
    # C-002 exists to catch (FR-014 / test_golden_count_ban's `convert` class —
    # the `len(Lane) == 10` -> exact-member-set exemplar). Folded by WP08.
    assert frozenset(_C002_HANDLERS) == frozenset(
        {
            ("src/mission_runtime/resolution.py", "_mid8_from_primary_meta"),
            ("src/mission_runtime/resolution.py", "_resolve_coordination_branch"),
            ("src/mission_runtime/resolution.py", "_resolve_mission_id"),
            ("src/specify_cli/decisions/service.py", "_resolve_mission_id"),
            (
                "src/specify_cli/missions/_resolve_planning_branch.py",
                "load_mission_target_branch",
            ),
            ("src/specify_cli/upgrade/feature_meta.py", "load_feature_meta"),
        }
    ), "C-002 governs exactly these six (module, symbol) handlers"
    assert not offenders, (
        "SC-007(c) violated -- `except Exception` / bare `except` at a C-002 handler:\n  "
        + "\n  ".join(offenders)
    )


def test_sc007c_each_of_the_six_handlers_names_mission_meta_read_error() -> None:
    """All six ``C-002`` handlers must catch ``MissionMetaReadError`` by name.

    The complement of the check above: not merely "not too broad" but "wide
    enough". ``MissionMetaReadError`` is a ``RuntimeError`` subclass
    (``core/paths.py:506``), so a handler left on ``ValueError`` alone silently
    stops absorbing corruption once its read is routed -- the stranded-arm defect
    class this mission exists to close.
    """
    missing: list[str] = []
    for module_rel, symbol in _C002_HANDLERS:
        names = {n for handler in _handler_clauses(module_rel, symbol) for n in _caught_names(handler)}
        if "MissionMetaReadError" not in names:
            missing.append(f"{module_rel}::{symbol} catches {sorted(names)}")

    print(f"SC-007(c) complement INPUT: {len(_C002_HANDLERS)} handlers checked")
    assert not missing, (
        "handler(s) do not name MissionMetaReadError, so a routed read's corruption "
        "escapes them:\n  " + "\n  ".join(missing)
    )
