"""WP05 / T029 — the ``status_transition.py`` write-target drain PROOF.

This is the OWNED home of the T029 drain decision (the WP05 ``create_intent``
test). It historically pinned ``_resolve_write_target``'s FALLBACK arm
``return coord_branch or _current_branch(repo_root)`` — the last surviving
git-HEAD write-target selector, reached only when
:func:`mission_runtime.resolve_placement_only` cannot resolve the mission (the
pre-meta create window / an ad-hoc fixture whose placement is unresolvable) —
with a **LEFT** verdict: a negative-probe proved the arm reachable (via a
blank/whitespace mission slug forcing ``resolve_placement_only`` to raise), so
the deferred #1716 selector was kept and allow-listed rather than drained.

**Verdict update (coord-write-placement-closure-01KYCF83 / WP04 / T017 /
FR-003): DRAINED.** The deferred #1716 ladder item this file's original
verdict left open is exactly what WP04 was scoped to close. The fallback no
longer reads the ambient checkout HEAD at all: ``_resolve_write_target``'s
except arm now short-circuits to ``coord_branch`` when present, else resolves
the SAME CWD-invariant ``target_branch`` the placement port itself consults
(:func:`specify_cli.core.paths.get_feature_target_branch`) — never
``_current_branch``. The negative-probe below is re-run against the NEW
selector: it proves ``_current_branch`` is **no longer invoked** even under
the arm's genuine reaching condition (a blank/whitespace slug forcing
``resolve_placement_only`` to raise) — the live evidence backing the DRAINED
verdict. ``_current_branch`` itself is left defined (two unrelated test
modules — ``test_simple_case_flat_topology.py`` /
``test_characterization_write_target.py`` — still import it as a comparison
oracle proving the write-target resolver is CWD-invariant), but it now has
**zero production call sites**.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.architectural._ratchet_keys import code_tokens_by_line

pytestmark = [pytest.mark.architectural, pytest.mark.git_repo]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_STATUS_TRANSITION_REL = "src/specify_cli/coordination/status_transition.py"

#: The retired selector token (#1716), normalized the same way
#: ``code_tokens_by_line`` tokenizes real CODE lines (space-joined tokens). Its
#: absence from every CODE line (never docstrings/comments, which legitimately
#: still quote the retired shape as history) is the drain proof.
_DRAINED_SELECTOR = "coord_branch or _current_branch"


def _init_repo(repo: Path) -> None:
    import subprocess

    def _git(*args: str) -> None:
        subprocess.run(
            ["git", *args],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        )

    _git("init", "-q", "-b", "lane-negprobe")
    _git("config", "user.email", "t@example.invalid")
    _git("config", "user.name", "Test")
    _git("config", "commit.gpgsign", "false")
    (repo / "README.md").write_text("seed\n", encoding="utf-8")
    _git("add", "README.md")
    _git("commit", "-q", "-m", "init")


def test_drained_selector_token_no_longer_present_in_source() -> None:
    """The retired ``coord_branch or _current_branch`` selector is GONE from CODE.

    Direct proof the drain happened: no real CODE line (as tokenized by
    ``code_tokens_by_line`` -- docstrings/comments are not code tokens) in
    ``status_transition.py`` matches the retired shape. The updated
    ``_resolve_write_target`` docstring legitimately still QUOTES the retired
    selector as history (mirroring this ratchet's own
    ``test_ratchet_ignores_prose_quoting_a_prior_walk`` convention in
    ``test_no_write_side_rederivation.py``), so this must scan tokens, not raw
    text. A regression re-introducing the inline
    ``coord_branch or _current_branch(repo_root)`` CODE shape (un-draining
    #1716) would flip this back to present and RED here.
    """
    source = (_REPO_ROOT / _STATUS_TRANSITION_REL).read_text(encoding="utf-8")
    offending_lines = [
        (lineno, code)
        for lineno, code in code_tokens_by_line(source).items()
        if _DRAINED_SELECTOR in code
    ]
    assert not offending_lines, (
        f"{_STATUS_TRANSITION_REL} still contains the retired {_DRAINED_SELECTOR!r} "
        f"selector in CODE -- the #1716 drain (WP04/T017) has regressed: {offending_lines!r}"
    )


@pytest.mark.git_repo
@pytest.mark.parametrize("unresolvable_slug", ["", "   "])
def test_negative_probe_no_longer_reaches_current_branch_when_placement_unresolvable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    unresolvable_slug: str,
) -> None:
    """NEGATIVE-PROBE (re-run post-drain): the genuine reaching condition no
    longer invokes ``_current_branch``.

    The reaching condition is ``resolve_placement_only`` raising (an
    unresolvable mission slug) with ``coord_branch=None`` so the selector's
    first operand cannot short-circuit. Pre-drain, this invoked
    ``_current_branch`` (the ambient git-HEAD read); post-drain it must
    resolve via the CWD-invariant ``get_feature_target_branch`` fallback
    instead, and ``_current_branch`` must never be called.
    """
    from specify_cli.coordination import status_transition as st

    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)

    calls: list[Path] = []
    original = st._current_branch

    def _spy(repo_root: Path) -> str:
        calls.append(repo_root)
        return original(repo_root)

    monkeypatch.setattr(st, "_current_branch", _spy)

    # coord_branch=None -> the drained arm must resolve WITHOUT consulting
    # _current_branch. get_feature_target_branch raises ValueError for a
    # blank/whitespace slug (assert_safe_path_segment) — that is the correct,
    # fail-loud closure of the #1716 arm for a genuinely-unresolvable mission,
    # not a silent ambient-HEAD guess.
    with pytest.raises(ValueError):
        st._resolve_write_target(repo, unresolvable_slug, None)

    assert not calls, (
        "the drained #1716 fallback must NEVER invoke _current_branch, even "
        "under its genuine reaching condition (resolve_placement_only raising "
        f"+ coord_branch=None); got calls={calls!r}"
    )


@pytest.mark.git_repo
def test_fallback_still_short_circuits_to_coord_branch_when_present(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The OTHER half of the fallback contract survives the drain unchanged.

    When the unresolvable-mission arm has a coord branch in hand, the selector
    returns it directly and never consults ``_current_branch`` OR
    ``get_feature_target_branch`` — this was true before the drain and stays
    true after.
    """
    from specify_cli.coordination import status_transition as st

    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)

    called = False

    def _spy(repo_root: Path) -> str:
        nonlocal called
        called = True
        return "should-not-be-used"

    monkeypatch.setattr(st, "_current_branch", _spy)

    result = st._resolve_write_target(repo, "", "kitty/mission-coord-ref")

    assert result == "kitty/mission-coord-ref"
    assert not called, "the HEAD selector must NOT be consulted when coord_branch is truthy"


@pytest.mark.git_repo
def test_real_unresolvable_slug_never_reaches_the_except_arm_at_all(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The genuine create-window shape (a real, non-blank slug, no meta.json
    yet) resolves entirely on the ``try`` path -- it never reaches the
    drained except arm in the first place.

    ``resolve_placement_only`` degrades internally for a real-but-unresolvable
    mission slug (its own ``get_feature_target_branch`` call swallows the
    missing-meta case), so ``_resolve_write_target`` never raises here and
    ``status_transition._current_branch`` is never invoked -- matching
    ``test_resolve_write_target_helper_no_meta_degrades_to_branch``
    (``test_status_transition_adoption.py``). Only a SYNTHETICALLY
    unresolvable slug (blank/whitespace, asserted above) or a coord-worktree-
    without-mission-dir refusal reaches the drained except arm at all.
    """
    from specify_cli.coordination import status_transition as st

    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)

    calls: list[Path] = []
    original = st._current_branch

    def _spy(repo_root: Path) -> str:
        calls.append(repo_root)
        return original(repo_root)

    monkeypatch.setattr(st, "_current_branch", _spy)

    st._resolve_write_target(repo, "no-such-mission-01kydraintest", None)

    assert not calls, "the try path must not consult status_transition._current_branch either"
