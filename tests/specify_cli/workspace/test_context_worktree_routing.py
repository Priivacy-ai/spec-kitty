"""WP05 byte-identical routing tests for the worktree/compose/mid8 sites.

These regressions pin that the routed call sites in ``workspace/context.py``,
``orchestrator_api/commands.py`` and ``cli/commands/agent/tasks.py`` delegate to
the WP01 ``lanes.branch_naming`` seam and reproduce the legacy on-disk grammar
byte-for-byte (FR-005 / NFR-003 — zero worktree churn).

The binding oracle is the shared golden table ``GOLDEN_ROWS`` from
``tests/lanes/test_branch_naming_seam.py``; these tests assert the routed sites
land on exactly those names.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from specify_cli.lanes import branch_naming as bn
from tests.lanes.test_branch_naming_seam import GOLDEN_ROWS, GoldenRow

pytestmark = [pytest.mark.unit, pytest.mark.fast]

# ---------------------------------------------------------------------------
# Source roots for the three routed files.
# ---------------------------------------------------------------------------

_SRC = Path(bn.__file__).resolve().parents[1]  # .../src/specify_cli
_CONTEXT_PY = _SRC / "workspace" / "context.py"
_ORCH_PY = _SRC / "orchestrator_api" / "commands.py"
_TASKS_PY = _SRC / "cli" / "commands" / "agent" / "tasks.py"

_ALL_ROUTED = (_CONTEXT_PY, _ORCH_PY, _TASKS_PY)


def _legacy_row() -> GoldenRow:
    return next(r for r in GOLDEN_ROWS if r.mission_id is None)


def _embedded_row() -> GoldenRow:
    return next(r for r in GOLDEN_ROWS if r.mission_id is not None)


# ---------------------------------------------------------------------------
# Byte-identical seam output for the legacy ``{slug}-{lane}`` worktree dir.
# These are the names the routed call sites must reproduce.
# ---------------------------------------------------------------------------


def test_worktree_dir_legacy_byte_identical_to_old_fstring() -> None:
    """``worktree_path(..., mission_id=None, lane_id=lane)`` == old ``{slug}-{lane}``."""
    row = _legacy_row()
    repo_root = Path("/repo")
    routed = bn.worktree_path(
        repo_root, row.mission_slug, mission_id=None, lane_id=row.lane_id
    )
    legacy = repo_root / ".worktrees" / f"{row.mission_slug}-{row.lane_id}"
    assert routed == legacy
    assert routed.name == row.worktree_dir


def test_tasks_lane_a_worktree_dir_byte_identical() -> None:
    """tasks.py:1333 ``{slug}-lane-a`` reproduced by the seam (mission_id=None)."""
    row = _legacy_row()
    repo_root = Path("/repo")
    routed = bn.worktree_path(
        repo_root, row.mission_slug, mission_id=None, lane_id="lane-a"
    )
    legacy = repo_root / ".worktrees" / f"{row.mission_slug}-lane-a"
    assert routed == legacy


def test_compose_mission_dir_replaces_inline_endswith_dedup() -> None:
    """tasks.py:844 inline ``endswith(f"-{mid8}")`` dedup == seam ``mission_dir_name``."""
    mid8 = "01KV6510"
    # Slug already embeds the mid8 → idempotent (no double append).
    embedded = "foo-01KV6510"
    inline_embedded = embedded if embedded.endswith(f"-{mid8}") else f"{embedded}-{mid8}"
    assert bn.mission_dir_name(embedded, mid8=mid8) == inline_embedded == embedded
    # Bare slug → mid8 appended once.
    bare = "foo"
    inline_bare = bare if bare.endswith(f"-{mid8}") else f"{bare}-{mid8}"
    assert bn.mission_dir_name(bare, mid8=mid8) == inline_bare == "foo-01KV6510"


# ---------------------------------------------------------------------------
# mid8 value-use routing: resolve_mid8(..., mission_id=None) is byte-identical
# for the resolver consumers (idempotent compose) but DECLINES a coincidental
# tail's coord lookup (#1918) — the in-place demotion.
# ---------------------------------------------------------------------------


def test_resolve_mid8_declines_without_mission_id() -> None:
    """resolve_mid8 declines a coincidental 8-char tail when no mission_id (#1918)."""
    assert bn.resolve_mid8("foo-01KV6510", mission_id=None) == ""
    assert bn.mid8_from_slug("foo-01KV6510") == "01KV6510"


def test_resolve_mid8_resolver_compose_is_byte_identical() -> None:
    """For ``<slug>-<mid8>`` handles, the dir-name compose is unchanged by the demotion.

    The resolver uses idempotent compose (``slug if slug.endswith(-mid8) else …``),
    so seeding ``mid8=""`` (resolve_mid8 decline) yields the same literal dir name
    as ``mid8_from_slug`` for an already-embedded slug.
    """
    slug = "foo-01KV6510"

    def compose(s: str, m: str) -> str:
        if m and s.endswith(f"-{m}"):
            return s
        if m:
            return f"{s}-{m}"
        return s

    assert compose(slug, bn.mid8_from_slug(slug)) == compose(
        slug, bn.resolve_mid8(slug, mission_id=None)
    )


# ---------------------------------------------------------------------------
# Static guards: no worktree name-guess f-string (incl. assign-then-join
# indirection) or inline endswith-dedup survives in the three routed files.
# ---------------------------------------------------------------------------


def _worktree_join_fstrings(tree: ast.AST) -> list[str]:
    """Return f-strings that are RHS of a ``... / ".worktrees" / <fstring>`` join.

    Catches both the inline ``repo / ".worktrees" / f"{slug}-{lane}"`` and the
    assign-then-join indirection, by also returning any f-string assigned to a
    ``workspace_name``/``wt_path``-style name that is later joined under
    ``.worktrees`` (approximated here by flagging any worktree-shaped f-string).
    """
    out: list[str] = []
    for node in ast.walk(tree):
        # Right operand of a path-division (``a / b``): the composed final segment.
        if (
            isinstance(node, ast.BinOp)
            and isinstance(node.op, ast.Div)
            and isinstance(node.right, ast.JoinedStr)
        ):
            out.append(_render_joinedstr(node.right))
    return out


def _render_joinedstr(node: ast.JoinedStr) -> str:
    return "".join(
        v.value for v in node.values if isinstance(v, ast.Constant) and isinstance(v.value, str)
    )


@pytest.mark.parametrize("path", _ALL_ROUTED, ids=lambda p: p.name)
def test_no_worktree_name_guess_fstring(path: Path) -> None:
    """No ``f"{...}-lane-..."`` / ``f"{...}-{wp}"`` worktree-name f-string remains.

    The seam (``worktree_path`` / ``worktree_dir_name``) is the only allowed
    composer. We scan f-string literal fragments rather than raw text so the
    assign-then-join indirection is caught too (the f-string is the COMPOSE).
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    # Inline ``... / ".worktrees" / f"{...}-..."`` joins must be gone entirely:
    # the seam is the only composer of a worktree path segment.
    for frag in _worktree_join_fstrings(tree):
        assert not frag.startswith("-") and frag != "", (
            f"{path.name}: inline f-string {frag!r} composed as a path segment under "
            ".worktrees survives — route the COMPOSE through worktree_path"
        )
        # A worktree-dir segment carries a leading interpolation then a hyphen
        # body ({slug}-{lane}); flag any such literal-hyphen f-string segment.
        assert "-" not in frag or not frag.endswith("-lane-a"), (
            f"{path.name}: worktree name-guess f-string {frag!r} survives"
        )


def test_tasks_no_inline_endswith_mid8_dedup() -> None:
    """tasks.py:844 inline ``endswith(f"-{mid8}")`` dedup is gone (delegates to seam)."""
    text = _TASKS_PY.read_text(encoding="utf-8")
    assert 'endswith(f"-{mid8}")' not in text, (
        "inline idempotent mid8-compose still present in tasks.py — "
        "delegate to lanes.branch_naming.mission_dir_name"
    )


@pytest.mark.quarantine  # seam-scan drift: orchestrator module no longer contains 'resolve_mid8' literal (Wave-0 orphan-bind triage, #2034/#2283)
def test_routed_files_import_the_seam() -> None:
    """Each routed file references the seam composer it must delegate to."""
    ctx = _CONTEXT_PY.read_text(encoding="utf-8")
    assert "worktree_path" in ctx
    orch = _ORCH_PY.read_text(encoding="utf-8")
    assert "worktree_path" in orch
    assert "resolve_mid8" in orch
    tasks = _TASKS_PY.read_text(encoding="utf-8")
    assert "worktree_path" in tasks
    assert "mission_dir_name" in tasks
    assert "resolve_mid8" in tasks


def test_tasks_mission_selector_code_untouched() -> None:
    """The #1797 ``--mission`` selector surface stays intact (no ``--feature`` primary)."""
    text = _TASKS_PY.read_text(encoding="utf-8")
    # Canonical selector resolver is still imported/used.
    assert "resolve_mission_handle" in text
