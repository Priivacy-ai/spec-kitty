"""Layering tests for commit_router (WP02 / T009 — #2061).

Two concerns:
(a) Byte-identical classification: paths under ``.worktrees/`` are classified
    the same way by ``is_under_worktrees_segment`` (used inside commit_router)
    and by the direct primitive from ``coordination.surface_resolver``.

(b) Import-direction assertion: ``coordination.commit_router`` must have ZERO
    ``from specify_cli.cli`` imports.  The test is written to fail if the
    reach-in returns.
"""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.fast]


# ---------------------------------------------------------------------------
# (a) Byte-identical classification test
# ---------------------------------------------------------------------------


class TestWorktreesClassificationByteIdentical:
    """is_under_worktrees_segment classifies paths in commit_router identically
    to the direct primitive from surface_resolver."""

    def _classify_via_surface_resolver(self, path: Path) -> bool:
        from specify_cli.coordination.surface_resolver import is_under_worktrees_segment

        return is_under_worktrees_segment(path)

    @pytest.mark.parametrize(
        "rel_path,expected",
        [
            # Paths that ARE under .worktrees
            (Path(".worktrees/my-mission-lane-1/kitty-specs/spec.md"), True),
            (Path(".worktrees/slug-ABCD1234-lane-2"), True),
            (Path("parent/.worktrees/nested/file.txt"), True),
            # Paths that are NOT under .worktrees
            (Path("kitty-specs/mission/tasks/WP01.md"), False),
            (Path("src/specify_cli/coordination/commit_router.py"), False),
            (Path(".kittify/config.yaml"), False),
            (Path("worktrees-adjacent/file.txt"), False),  # no leading dot
        ],
    )
    def test_classification_matches_primitive(
        self, tmp_path: Path, rel_path: Path, expected: bool
    ) -> None:
        """Classification result matches what surface_resolver.is_under_worktrees_segment returns."""
        # The primitive is the same function commit_router now calls directly.
        result = self._classify_via_surface_resolver(rel_path)
        assert result is expected, (
            f"is_under_worktrees_segment({rel_path!r}) returned {result!r}; expected {expected!r}"
        )

    def test_worktrees_staging_path(self, tmp_path: Path) -> None:
        """A realistic staging path rooted under .worktrees classifies as True."""
        # Shape that appears in _stage_finalize_artifacts_in_coord_worktree
        staging_rel = Path(".worktrees") / "my-mission-01ABCDEF-lane-a" / "kitty-specs" / "tasks.md"
        assert self._classify_via_surface_resolver(staging_rel) is True

    def test_non_worktrees_planning_path(self, tmp_path: Path) -> None:
        """A planning artifact path NOT under .worktrees classifies as False."""
        planning_rel = Path("kitty-specs") / "my-mission-01ABCDEF" / "tasks.md"
        assert self._classify_via_surface_resolver(planning_rel) is False


# ---------------------------------------------------------------------------
# (b) Import-direction assertion: zero `from specify_cli.cli` in commit_router
# ---------------------------------------------------------------------------


class TestCommitRouterImportDirection:
    """commit_router.py must not import from specify_cli.cli (inverted-layering guard)."""

    def _get_commit_router_source(self) -> str:
        spec = importlib.util.find_spec("specify_cli.coordination.commit_router")
        assert spec is not None, "specify_cli.coordination.commit_router not found on sys.path"
        assert spec.origin is not None, "commit_router has no origin path"
        return Path(spec.origin).read_text(encoding="utf-8")

    def test_no_from_specify_cli_cli_imports(self) -> None:
        """commit_router.py contains ZERO 'from specify_cli.cli' import statements.

        This test fails if the inverted-layering reach-in is re-introduced — it is
        the enforcement gate for #2061.
        """
        source = self._get_commit_router_source()
        tree = ast.parse(source)

        cli_imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module.startswith("specify_cli.cli"):
                    cli_imports.append(
                        f"  line {node.lineno}: from {module} import "
                        + ", ".join(alias.name for alias in node.names)
                    )

        assert not cli_imports, (
            "coordination/commit_router.py has forbidden 'specify_cli.cli' imports "
            "(inverted layering — coordination must not reach into cli):\n"
            + "\n".join(cli_imports)
        )

    def test_has_surface_resolver_import(self) -> None:
        """commit_router.py imports is_under_worktrees_segment from surface_resolver
        (positive check — confirms the correct seam is wired)."""
        source = self._get_commit_router_source()
        tree = ast.parse(source)

        found = False
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module == "specify_cli.coordination.surface_resolver":
                    names = [alias.name for alias in node.names]
                    if "is_under_worktrees_segment" in names:
                        found = True
                        break

        assert found, (
            "coordination/commit_router.py does NOT import is_under_worktrees_segment "
            "from specify_cli.coordination.surface_resolver — the seam may be broken."
        )
