"""#1971-tail convergence regression test — three locate_project_root entries.

Issue #1971 asserted a SPECIFY_REPO_ROOT / worktree split-brain across the three
``locate_project_root`` entry points:

- ``specify_cli.core.__init__``        (re-exports via project_resolver)
- ``specify_cli.core.project_resolver``  (deferred-delegation shim)
- ``specify_cli.core.paths``             (authoritative implementation)

This test file DISPROVES the split-brain by asserting that all three entries
return **identical resolved Path values** under each of the three conditions
that matter: SPECIFY_REPO_ROOT set, worktree .git-file pointer, .kittify walk.

Design constraint: each test uses a **divergent input** — an input whose
structure would expose drift if any entry were NOT delegating to the paths.py
authority. A test that only asserts "all three return the same type" or "all three
exist" is a tautology and must be rejected (POST-TASKS-SYNTHESIS.md).

What counts as a divergent input: for the worktree case, ``start`` points inside
a worktree directory; a simple-walk (non-authority) resolver would return the
worktree root, whereas the authority follows the .git pointer to the main repo.
For the env-var case, SPECIFY_REPO_ROOT points at a directory that is NOT the
walk-up .kittify root; a caller ignoring the env var would return a different Path.

DO NOT touch the intentional deferred-import shims in project_resolver.py —
reverting them is the documented #1971 regression.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# Three entry points — import all three explicitly to test convergence.
import specify_cli.core as core_init_module
import specify_cli.core.paths as paths_module
import specify_cli.core.project_resolver as resolver_module

pytestmark = [pytest.mark.unit, pytest.mark.fast]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_main_repo(root: Path) -> Path:
    """Create a minimal spec-kitty main-repo layout (git dir + .kittify)."""
    (root / ".git").mkdir(parents=True, exist_ok=True)
    (root / ".kittify").mkdir(parents=True, exist_ok=True)
    return root


def _make_worktree(worktree_path: Path, main_repo: Path) -> Path:
    """Create a git worktree directory that points back to main_repo.

    The worktree's .git file uses the ``gitdir:`` pointer pointing at
    ``<main_repo>/.git/worktrees/<worktree_name>`` — the topology that
    :func:`~specify_cli.core.paths._is_worktree_gitdir` recognises.
    """
    worktree_path.mkdir(parents=True, exist_ok=True)
    wt_name = worktree_path.name
    # Simulate: main/.git/worktrees/<name>
    wt_gitdir = main_repo / ".git" / "worktrees" / wt_name
    wt_gitdir.mkdir(parents=True, exist_ok=True)
    # Write the .git pointer file in the worktree
    git_file = worktree_path / ".git"
    git_file.write_text(f"gitdir: {wt_gitdir}\n", encoding="utf-8")
    return worktree_path


# ---------------------------------------------------------------------------
# Condition 1: SPECIFY_REPO_ROOT set (env-var override)
# ---------------------------------------------------------------------------


class TestConvergenceEnvVar:
    """All three entries must return the same Path when SPECIFY_REPO_ROOT is set."""

    def test_env_root_all_three_entries_agree(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Divergent input: SPECIFY_REPO_ROOT points at a directory that is NOT
        the walk-up .kittify root.  An entry ignoring the env var would return
        the ambient (walk-up) root — not the env-var root.  All three must return
        the env-var root.
        """
        # Ambient checkout: has .kittify, would be the walk-up result if env var ignored.
        ambient = tmp_path / "ambient-repo"
        _make_main_repo(ambient)

        # Explicit root: exists, NO .kittify — chosen to diverge from the walk-up result.
        explicit_root = tmp_path / "explicit-root"
        explicit_root.mkdir()

        monkeypatch.setenv("SPECIFY_REPO_ROOT", str(explicit_root))

        # Calls start from the ambient repo; the env var must win.
        start = ambient
        result_paths = paths_module.locate_project_root(start=start)
        result_resolver = resolver_module.locate_project_root(start=start)
        result_init = core_init_module.locate_project_root(start=start)

        # All three must agree on the same Path object value.
        assert result_paths == result_resolver == result_init, (
            f"Split-brain detected under SPECIFY_REPO_ROOT:\n"
            f"  paths.locate_project_root    = {result_paths!r}\n"
            f"  resolver.locate_project_root = {result_resolver!r}\n"
            f"  __init__.locate_project_root = {result_init!r}"
        )

        # Must be the env-var root (not the ambient walk-up root).
        expected = explicit_root.resolve()
        assert result_paths == expected, (
            f"Expected SPECIFY_REPO_ROOT={explicit_root!r} to be returned; "
            f"got {result_paths!r}.  Entry ignoring env var would return {ambient.resolve()!r}."
        )
        assert result_paths != ambient.resolve(), (
            "All three entries must return the env-var root, NOT the ambient walk-up root."
        )


# ---------------------------------------------------------------------------
# Condition 2: Worktree .git-file pointer
# ---------------------------------------------------------------------------


class TestConvergenceWorktreeGitFile:
    """All three entries must follow the worktree .git pointer to the main repo."""

    def test_worktree_start_all_three_entries_agree(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Divergent input: start is inside a worktree directory.

        A simple-walk implementation (not following the .git pointer) would return
        the worktree root; the authority follows the pointer and returns the main
        repo root.  All three must agree on the main repo root.
        """
        monkeypatch.delenv("SPECIFY_REPO_ROOT", raising=False)

        main_repo = _make_main_repo(tmp_path / "main-repo")
        worktree = _make_worktree(tmp_path / "worktrees" / "my-feature", main_repo)

        start = worktree

        result_paths = paths_module.locate_project_root(start=start)
        result_resolver = resolver_module.locate_project_root(start=start)
        result_init = core_init_module.locate_project_root(start=start)

        # All three must agree.
        assert result_paths == result_resolver == result_init, (
            f"Split-brain detected for worktree .git pointer:\n"
            f"  paths.locate_project_root    = {result_paths!r}\n"
            f"  resolver.locate_project_root = {result_resolver!r}\n"
            f"  __init__.locate_project_root = {result_init!r}"
        )

        # Must be the MAIN repo root — not the worktree root.
        expected = main_repo.resolve()
        assert result_paths == expected, (
            f"Expected main repo {expected!r}; got {result_paths!r}. "
            f"A simple-walk resolver would return the worktree root "
            f"{worktree.resolve()!r} instead."
        )
        assert result_paths != worktree.resolve(), (
            "All three entries must return the MAIN repo root, not the worktree root."
        )


# ---------------------------------------------------------------------------
# Condition 3: .kittify walk (baseline, no env var, no worktree)
# ---------------------------------------------------------------------------


class TestConvergenceKittifyWalk:
    """.kittify walk: all three entries must return the same root."""

    def test_kittify_walk_all_three_entries_agree(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Baseline: start in a nested subdirectory; .kittify is in the ancestor.

        The divergent element here is the start directory being nested: a resolver
        that only checks ``start`` (not walking up) would return None, while the
        authority walks up and finds .kittify.  All three must agree on the ancestor.
        """
        monkeypatch.delenv("SPECIFY_REPO_ROOT", raising=False)

        repo_root = tmp_path / "my-project"
        _make_main_repo(repo_root)
        # Nested subdir — divergent from the root itself.
        nested = repo_root / "src" / "specify_cli" / "core"
        nested.mkdir(parents=True)

        start = nested

        result_paths = paths_module.locate_project_root(start=start)
        result_resolver = resolver_module.locate_project_root(start=start)
        result_init = core_init_module.locate_project_root(start=start)

        # All three must agree.
        assert result_paths == result_resolver == result_init, (
            f"Split-brain detected for .kittify walk:\n"
            f"  paths.locate_project_root    = {result_paths!r}\n"
            f"  resolver.locate_project_root = {result_resolver!r}\n"
            f"  __init__.locate_project_root = {result_init!r}"
        )

        expected = repo_root.resolve()
        assert result_paths == expected, (
            f"Expected repo root {expected!r} from nested start; got {result_paths!r}."
        )


# ---------------------------------------------------------------------------
# Pinned: benign __init__.py no-arg signature divergence
# ---------------------------------------------------------------------------


class TestPinnedNoArgSignature:
    """Pin: all three accept the no-arg call (start=None, defaults to cwd).

    This is not a split-brain — it is expected behaviour: each entry falls back
    to Path.cwd() when ``start`` is not provided.  The test pins this so a future
    refactor cannot accidentally strip the default-argument.
    """

    def test_no_arg_call_accepted_by_all_three(self) -> None:
        """All three entries must accept a no-arg call without raising TypeError."""
        import inspect

        sig_paths = inspect.signature(paths_module.locate_project_root)
        sig_resolver = inspect.signature(resolver_module.locate_project_root)
        sig_init = inspect.signature(core_init_module.locate_project_root)

        for name, sig in [
            ("paths.locate_project_root", sig_paths),
            ("project_resolver.locate_project_root", sig_resolver),
            ("core.__init__.locate_project_root", sig_init),
        ]:
            param = sig.parameters.get("start")
            assert param is not None, f"{name} must have a 'start' parameter."
            assert param.default is None, (
                f"{name} 'start' parameter must default to None "
                f"(benign no-arg call semantics). Got: {param.default!r}"
            )


# ---------------------------------------------------------------------------
# Pinned: deferred-import shim integrity (DO NOT modify)
# ---------------------------------------------------------------------------


class TestDeferredImportShimIntegrity:
    """Pin that project_resolver uses a deferred import, not a duplicate impl.

    The deferred import in project_resolver.py is intentional — it prevents
    import-cycle issues when specify_cli.core is first loaded.  Reverting it
    to a module-level import is the documented #1971 regression.

    This test checks the shim at the SOURCE level: the function body must
    contain the deferred import, not a local copy of the resolution algorithm.
    """

    def test_project_resolver_contains_deferred_import(self) -> None:
        """project_resolver.locate_project_root must use a deferred import pattern."""
        import inspect

        src = inspect.getsource(resolver_module.locate_project_root)

        assert "from specify_cli.core.paths import locate_project_root" in src, (
            "project_resolver.locate_project_root must use the documented deferred "
            "import pattern. Reverting to a direct impl or module-level import is "
            "the #1971 regression. Source:\n" + src
        )

    def test_project_resolver_does_not_duplicate_walk_logic(self) -> None:
        """project_resolver must NOT contain a local copy of the walk-up algorithm.

        If ``for candidate in`` or ``os.getenv("SPECIFY_REPO_ROOT")`` appears in
        the function body, someone re-inlined the duplicate impl — that's the
        split-brain #1971 warned about.
        """
        import inspect

        src = inspect.getsource(resolver_module.locate_project_root)

        assert "for candidate in" not in src, (
            "project_resolver.locate_project_root must NOT contain the walk-up loop. "
            "All walk logic must live in paths.py. Duplicate found in source:\n" + src
        )
        assert 'os.getenv("SPECIFY_REPO_ROOT")' not in src, (
            "project_resolver.locate_project_root must NOT read SPECIFY_REPO_ROOT itself. "
            "That belongs in paths.py. Source:\n" + src
        )
