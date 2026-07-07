"""WP05 / T029 — the ``status_transition.py:336`` write-target drain PROOF.

This is the OWNED home of the T029 drain decision (the WP05 ``create_intent``
test). The ``:336`` line is the ``_resolve_write_target`` FALLBACK arm
``return coord_branch or _current_branch(repo_root)`` — the last surviving git-HEAD
write-target selector, reached only when
:func:`mission_runtime.resolve_placement_only` cannot resolve the mission (the
pre-meta create window / an ad-hoc fixture whose placement is unresolvable).

T029 mandates a **negative-probe**: the "DEAD → drain" verdict is valid ONLY if an
explicit attempt to REACH ``:336`` via its genuine reaching condition
(``resolve_placement_only`` forced to raise) proves the arm is never taken even
then. A happy-path "ran create → first-write once, didn't hit it" run proves
NOTHING — ``resolve_placement_only`` succeeds for a clean coord mission and
FR-002/FR-003 mint topology AT CREATE, structurally biasing every happy-path run
toward "never hit".

**Verdict (witnessed live evidence): LEFT — the arm is REACHABLE.**

The negative-probe below forces the genuine reaching condition (a blank /
whitespace mission slug, which makes ``resolve_placement_only`` raise
``ActionContextError``) with ``coord_branch=None`` (so the ``coord_branch or …``
short-circuit cannot mask the selector), and observes that ``_current_branch`` IS
called and its value IS returned — i.e. ``:336`` is taken. Because the negative-
probe REACHES the arm, the DEFAULT verdict holds: **LEAVE the line + keep WP00's
re-keyed allow-list entry**. We do NOT drain (a speculative drain would re-open
the create-window write bug — the load-bearing-workaround trap, Risk #2) and we
do NOT re-pin a dead line (it is provably live).

If a future change genuinely retires the arm, this test is the regression that
must be revisited together with the WP00 allow-list-entry removal — they move as
a pair, gated on this negative-probe flipping to "not reached".
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.architectural._ratchet_keys import composite_key

pytestmark = [pytest.mark.architectural, pytest.mark.git_repo]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_STATUS_TRANSITION_REL = "src/specify_cli/coordination/status_transition.py"
# write-surface-coherence WP02 / T031: the required STATUS_STATE kind threading in
# ``_resolve_write_target`` shifted the deferred HEAD-selector fallback arm from
# :336 to :343 (the ``coord_branch or _current_branch`` line); the #1842
# workspace-context tombstone cancel hook then shifted it :343 → :347. The numeral
# in the docstrings/test names is descriptive history; this constant is the live
# anchor. (This drift-on-line-shift is exactly what #2072 exists to eliminate.)
_ALLOW_LISTED_LINE = 347
_DEFERRED_SELECTOR = "coord_branch or _current_branch"


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


@pytest.mark.git_repo
@pytest.mark.parametrize("unresolvable_slug", ["", "   "])
def test_negative_probe_reaches_336_fallback_when_placement_unresolvable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    unresolvable_slug: str,
) -> None:
    """NEGATIVE-PROBE: force ``:336``'s genuine reaching condition and prove it IS taken.

    The reaching condition is ``resolve_placement_only`` raising (an unresolvable
    mission slug) with ``coord_branch=None`` so the selector's first operand
    cannot short-circuit. We instrument ``_current_branch`` (the ``:336`` git-HEAD
    selector) and assert it is invoked and its value returned — i.e. the fallback
    arm is REACHED. This is the live evidence backing the LEFT verdict (the arm is
    not dead; a drain would be a regression).
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

    # coord_branch=None → the ``coord_branch or …`` short-circuit cannot mask the
    # selector, so reaching :336 MUST invoke _current_branch.
    result = st._resolve_write_target(repo, unresolvable_slug, None)

    assert calls, (
        "negative-probe did NOT reach status_transition.py:336 — the genuine "
        "reaching condition (resolve_placement_only raising + coord_branch=None) "
        "must invoke _current_branch. If this assertion flips to 'not reached', "
        "the arm may finally be drainable; re-run the full T029 negative-probe "
        "before removing the WP00 allow-list entry."
    )
    assert result == original(repo) == "lane-negprobe", (
        "the :336 fallback must return the current HEAD branch (_current_branch) "
        f"when the mission is unresolvable; got {result!r}"
    )


@pytest.mark.git_repo
def test_336_short_circuits_to_coord_branch_when_present(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The ``:336`` selector returns ``coord_branch`` (not HEAD) when one is in hand.

    Pins the OTHER half of the fallback contract: when the unresolvable-mission
    arm has a coord branch, the ``coord_branch or _current_branch`` selector
    returns the coord branch and does NOT consult HEAD. This is why a happy-path
    run with a coord branch never witnesses the HEAD selector — and exactly why a
    happy-path run is an INSUFFICIENT deadness proof (Risk #2).
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


def test_allow_list_still_carries_the_336_selector_after_left_verdict() -> None:
    """The WP00 re-keyed allow-list still pins ``:336`` — the LEFT verdict's invariant.

    The negative-probe proved ``:336`` reachable, so the verdict is LEAVE: WP00's
    content-addressed allow-list entry MUST remain (a drain would remove it). This
    asserts the composite key for the deferred selector still resolves to the live
    ``coord_branch or _current_branch`` line, so a silent retirement of the entry
    (which would un-defer a still-live arm) is caught here too.
    """
    source = (_REPO_ROOT / _STATUS_TRANSITION_REL).read_text(encoding="utf-8")
    _qualname, token_line = composite_key(source, _ALLOW_LISTED_LINE)
    assert _DEFERRED_SELECTOR in token_line, (
        f"{_STATUS_TRANSITION_REL}:{_ALLOW_LISTED_LINE} no longer holds the "
        f"deferred HEAD selector (got {token_line!r}); the WP05 LEFT verdict "
        "assumes the allow-listed line is still the live :336 fallback. Re-run "
        "the T029 negative-probe before re-grounding or removing the entry."
    )
