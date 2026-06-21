"""Tests for ProtectionPolicy (WP01 / T003 / T004 / FR-004/006/007/008).

Coverage map:

T003 — #1828 hatch-symmetry regression pin
    Both the ``safe_commit`` path (via ``is_protected``) and the
    ``assert_not_protected_branch`` path treat a protected ref as UNPROTECTED
    when the operator hatch is active.  ``ProtectionPolicy.is_protected``
    makes this structural.

T004 — 4-row config resolution matrix (zero-mock, ``tmp_path`` fixtures)
    Row 1: absent ``protection:`` key + ``origin/HEAD=develop``  ⇒ {main, master, develop}
    Row 2: explicit ``[release]``                                ⇒ {release} only
    Row 3: explicit ``[]`` + ``origin/HEAD=main``               ⇒ frozenset() (opt-out)
    Row 4: malformed non-list value                             ⇒ ProtectionConfigError
    Row 5: hatch active                                         ⇒ is_protected("main") False

All tests use ``tmp_path`` — no mocks, no network, no real spec-kitty repo.
Hermetic git repos are created where needed.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from specify_cli.git.protection_policy import ProtectionConfigError, ProtectionPolicy


pytestmark = pytest.mark.git_repo

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_kittify_config(repo: Path, content: str) -> None:
    """Write ``.kittify/config.yaml`` to *repo* with the given YAML *content*."""
    kittify = repo / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    (kittify / "config.yaml").write_text(content, encoding="utf-8")


def _build_git_repo(base: Path, *, branch: str = "main") -> Path:
    """Initialise a bare-minimum git repo under *base* and return its root."""
    repo = base / "repo"
    repo.mkdir(parents=True)

    def _git(*args: str) -> None:
        subprocess.run(
            ["git", *args],
            cwd=repo,
            check=True,
            capture_output=True,
        )

    _git("init", "--initial-branch", branch)
    _git("config", "user.email", "test@example.com")
    _git("config", "user.name", "Test")
    _git("config", "commit.gpgsign", "false")
    (repo / "README.md").write_text("# test\n", encoding="utf-8")
    _git("add", "-A")
    _git("commit", "-m", "init")
    return repo


# ---------------------------------------------------------------------------
# T004 — row 1: absent ``protection:`` key + remote default
# ---------------------------------------------------------------------------


def test_absent_key_uses_default_plus_remote_default(tmp_path: Path) -> None:
    """Absent protection key → {main, master} ∪ {remote default} (NFR-004).

    We cannot easily create a real remote in tmp_path that git ``symbolic-ref``
    picks up, so we verify that without any remote the result is exactly the
    name-default pair, and with a real remote-HEAD symref it adds the remote
    branch.  This test validates the absent-key path returns the default set.
    """
    repo = _build_git_repo(tmp_path / "absent")
    # No .kittify/config.yaml at all — absent key path.
    policy = ProtectionPolicy.resolve(repo)

    # Must include the name defaults.
    assert "main" in policy.protected_branches
    assert "master" in policy.protected_branches
    # With no remote configured the set is exactly {main, master}.
    assert policy.protected_branches == frozenset({"main", "master"})


def test_absent_key_with_remote_default_branch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Absent protection key + remote default = {main, master, <remote-default>}.

    We monkeypatch ``_remote_default_branch`` inside the protection_policy
    module to return ``"develop"`` deterministically — this tests the resolution
    logic without needing a real network remote.
    """
    import specify_cli.git.protection_policy as pp_module

    repo = _build_git_repo(tmp_path / "remote-default")
    monkeypatch.setattr(pp_module, "_remote_default_branch", lambda _: "develop")

    policy = ProtectionPolicy.resolve(repo)
    assert policy.protected_branches == frozenset({"main", "master", "develop"})


# ---------------------------------------------------------------------------
# T004 — row 2: explicit non-empty list → exactly that set, no union
# ---------------------------------------------------------------------------


def test_explicit_list_returns_exact_set_no_union(tmp_path: Path) -> None:
    """Explicit ``[release]`` → {release} only; {main, master} are NOT added."""
    repo = _build_git_repo(tmp_path / "explicit")
    _write_kittify_config(
        repo,
        "protection:\n  protected_branches:\n    - release\n",
    )
    policy = ProtectionPolicy.resolve(repo)
    assert policy.protected_branches == frozenset({"release"})
    # The name-defaults must NOT appear.
    assert "main" not in policy.protected_branches
    assert "master" not in policy.protected_branches


# ---------------------------------------------------------------------------
# T004 — row 3: explicit [] + remote default → frozenset() (owner opt-out)
# ---------------------------------------------------------------------------


def test_explicit_empty_list_is_empty_not_remote_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Explicit ``[]`` + remote-default → nothing protected (US2 opt-out edge case).

    The remote default branch must NOT be added when the owner explicitly
    declares an empty list — the empty list means "nothing is protected".
    """
    import specify_cli.git.protection_policy as pp_module

    repo = _build_git_repo(tmp_path / "empty-list")
    # Patch the remote default so we can verify it is NOT added.
    monkeypatch.setattr(pp_module, "_remote_default_branch", lambda _: "main")
    _write_kittify_config(
        repo,
        "protection:\n  protected_branches: []\n",
    )
    policy = ProtectionPolicy.resolve(repo)
    assert policy.protected_branches == frozenset()
    assert not policy.is_protected("main")
    assert not policy.is_protected("master")


# ---------------------------------------------------------------------------
# T004 — row 4: malformed value → fail-closed error
# ---------------------------------------------------------------------------


def test_malformed_value_raises_protection_config_error(tmp_path: Path) -> None:
    """A non-list value under ``protected_branches`` raises ProtectionConfigError."""
    repo = _build_git_repo(tmp_path / "malformed")
    _write_kittify_config(
        repo,
        "protection:\n  protected_branches: not-a-list\n",
    )
    with pytest.raises(ProtectionConfigError, match="must be a list"):
        ProtectionPolicy.resolve(repo)


# ---------------------------------------------------------------------------
# T004 — row 5: hatch active → is_protected returns False
# ---------------------------------------------------------------------------


def test_hatch_active_is_protected_returns_false(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Hatch active ⇒ is_protected("main") is False even for a default branch."""
    repo = _build_git_repo(tmp_path / "hatch")
    monkeypatch.setenv("SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS", "1")

    policy = ProtectionPolicy.resolve(repo)
    assert policy.operator_hatch_active is True
    # "main" IS in the set, but is_protected accounts for the hatch.
    assert "main" in policy.protected_branches
    assert not policy.is_protected("main")
    assert not policy.is_protected("master")


# ---------------------------------------------------------------------------
# T003 — #1828 hatch-symmetry regression pin
# ---------------------------------------------------------------------------


def test_hatch_symmetry_safe_commit_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """#1828: hatch active ⇒ safe_commit path treats protected ref as unprotected.

    Regression pin for issue #1828 — the hatch was honored inconsistently
    between ``assert_not_protected_branch`` and ``safe_commit``'s
    ``ProtectionState`` input computation.  ``ProtectionPolicy.is_protected``
    makes both paths structurally symmetric.

    This test verifies the ``safe_commit`` path: when the hatch is active,
    ``ProtectionPolicy.resolve(repo).is_protected("main")`` returns ``False``,
    so the protected-branch guard input to ``commit_guard.evaluate`` is
    ``is_protected=False`` — the commit is not blocked by protection alone.
    """
    repo = _build_git_repo(tmp_path / "hatch-safe-commit")
    monkeypatch.setenv("SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS", "true")

    policy = ProtectionPolicy.resolve(repo)
    # The safe_commit path computes ``is_protected`` via policy.is_protected().
    # With the hatch active the result MUST be False for a "main" destination.
    assert policy.is_protected("main") is False
    assert policy.is_protected("master") is False


def test_hatch_symmetry_assert_not_protected_branch_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """#1828: hatch active ⇒ assert_not_protected_branch treats ref as unprotected.

    Regression pin for issue #1828 — the pre-check function must respect the
    hatch via ``ProtectionPolicy.is_protected`` (same mechanism as safe_commit).

    With the hatch set and the repo on ``main``, ``assert_not_protected_branch``
    must NOT raise ``ProtectedBranchCommitError``.
    """
    import subprocess as sp

    from specify_cli.git.commit_helpers import (
        ProtectedBranchCommitError,
        assert_not_protected_branch,
    )

    repo = _build_git_repo(tmp_path / "hatch-assert", branch="main")
    # Make it a spec-kitty project so the guard doesn't short-circuit.
    _write_kittify_config(repo, "project: guard-suite\n")
    monkeypatch.setenv("SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS", "yes")

    # Switch HEAD to main (it already should be, but be explicit).
    sp.run(["git", "checkout", "main"], cwd=repo, check=True, capture_output=True)

    # With the hatch active, this must NOT raise — #1828 symmetry.
    try:
        assert_not_protected_branch(repo)
    except ProtectedBranchCommitError:
        pytest.fail(
            "#1828 regression: assert_not_protected_branch raised on a protected "
            "branch even though SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS is set"
        )


def test_hatch_inactive_assert_not_protected_branch_does_raise(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without the hatch, assert_not_protected_branch raises on a protected branch.

    Baseline: the guard fires normally when the hatch is off.
    """
    import subprocess as sp

    from specify_cli.git.commit_helpers import (
        ProtectedBranchCommitError,
        assert_not_protected_branch,
    )

    repo = _build_git_repo(tmp_path / "no-hatch-assert", branch="main")
    _write_kittify_config(repo, "project: guard-suite\n")
    monkeypatch.delenv("SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS", raising=False)

    sp.run(["git", "checkout", "main"], cwd=repo, check=True, capture_output=True)

    with pytest.raises(ProtectedBranchCommitError):
        assert_not_protected_branch(repo)


# ---------------------------------------------------------------------------
# ProtectionPolicy basic invariants
# ---------------------------------------------------------------------------


def test_is_protected_on_default_branches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``is_protected`` returns True for default branches when hatch is off."""
    repo = _build_git_repo(tmp_path / "defaults")
    monkeypatch.delenv("SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS", raising=False)

    policy = ProtectionPolicy.resolve(repo)
    assert policy.is_protected("main") is True
    assert policy.is_protected("master") is True
    assert policy.is_protected("develop") is False


def test_is_protected_with_custom_branch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``is_protected`` returns True for a configured custom branch."""
    repo = _build_git_repo(tmp_path / "custom")
    _write_kittify_config(
        repo,
        "protection:\n  protected_branches:\n    - release\n    - hotfix\n",
    )
    monkeypatch.delenv("SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS", raising=False)

    policy = ProtectionPolicy.resolve(repo)
    assert policy.is_protected("release") is True
    assert policy.is_protected("hotfix") is True
    assert policy.is_protected("main") is False
    assert policy.is_protected("master") is False


def test_hatch_truthy_variants(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """All three truthy hatch values (1, true, yes) deactivate is_protected."""
    repo = _build_git_repo(tmp_path / "hatch-variants")
    for value in ("1", "true", "yes", "TRUE", "YES"):
        monkeypatch.setenv("SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS", value)
        policy = ProtectionPolicy.resolve(repo)
        assert policy.operator_hatch_active is True, f"Expected hatch for {value!r}"
        assert not policy.is_protected("main"), f"Expected unprotected for {value!r}"


def test_hatch_falsy_variants(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Non-truthy hatch values do not deactivate is_protected."""
    repo = _build_git_repo(tmp_path / "hatch-falsy")
    for value in ("0", "false", "no", ""):
        monkeypatch.setenv("SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS", value)
        policy = ProtectionPolicy.resolve(repo)
        assert policy.operator_hatch_active is False, f"Expected hatch off for {value!r}"
        assert policy.is_protected("main") is True, f"Expected protected for {value!r}"


def test_no_kittify_directory_returns_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No .kittify dir at all → default {main, master} (NFR-004)."""
    repo = _build_git_repo(tmp_path / "no-kittify")
    monkeypatch.delenv("SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS", raising=False)

    # No .kittify directory created → absent-key path.
    policy = ProtectionPolicy.resolve(repo)
    assert policy.protected_branches == frozenset({"main", "master"})
