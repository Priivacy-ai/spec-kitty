"""T017 — prompt-emptiness gate for the mission-steps/ step-authority layout.

Every ``MissionStep.prompt_template`` is a **required** field (see
``doctrine.missions.models.MissionStep`` docstring): a step with no authored
prompt yet must still point at a real file, but that file must not stay
permanently blank -- an empty/dummy prompt is a genuine content gap, not a
valid terminal state.

WP05 (``mission-step-authority-01KXNZMT``) seeds **16** blank placeholder
``prompt.md`` files while giving ``documentation`` (7 sequence steps),
``research`` (5), and ``plan`` (4) the same ``mission-steps/<type>/<step>/``
layout ``software-dev`` already has (T014/T015/T016). No prompt content is
invented here (C-004, DD-06) -- a blank file plus a *named, documented* red is
the correct disposition for a missing prompt; S-C (a later WP) fills the 16
placeholders with real content.

Each of the 16 gaps is asserted individually via ``pytest.mark.xfail(strict=False)``
so:

* the gap is **named** and **visible** in test output/collection (not folded
  into a single parametrized "expected failures" blob),
* the overall gate stays **green** (an xfail is not a suite failure) so this
  WP does not block on content only S-C is scoped to author,
* the moment S-C fills a given prompt, that step's xfail becomes an
  ``XPASS`` -- a visible signal (not a silent hard-pass) that the gap has
  been closed and the ``xfail`` marker for that step should be deleted.

``retrospect`` (documentation, research) is out of scope for this gate: it is
authored with ``in_action_sequence: false`` (never part of the dispatched
action sequence NFR-006 protects) and is not one of the 16 steps WP05's
content census names. Its placeholder prompt is seeded for model validity
(``MissionStep.prompt_template`` is required) but intentionally not asserted
here -- scoping the emptiness gate to the dispatch-relevant 16 keeps this
test's "exactly 16 named gaps" contract precise instead of silently growing.

FR-005, FR-013 (S-B, mission-step-authority-01KXNZMT WP05, T017).
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.fast, pytest.mark.doctrine]

_TESTS_DIR = Path(__file__).parent
_REPO_ROOT = Path(__file__).parents[3]
_MISSION_STEPS_ROOT = _REPO_ROOT / "src" / "doctrine" / "missions" / "mission-steps"

# The exact 16 prompt-less steps WP05's content census identified
# (documentation 7 + research 5 + plan 4). This is the pinned, named gap
# list -- S-C closes it step by step.
_SEEDED_BLANK_STEPS: tuple[tuple[str, str], ...] = (
    ("documentation", "discover"),
    ("documentation", "audit"),
    ("documentation", "design"),
    ("documentation", "generate"),
    ("documentation", "validate"),
    ("documentation", "publish"),
    ("documentation", "accept"),
    ("research", "scoping"),
    ("research", "methodology"),
    ("research", "gathering"),
    ("research", "synthesis"),
    ("research", "output"),
    ("plan", "specify"),
    ("plan", "research"),
    ("plan", "plan"),
    ("plan", "review"),
)

# A prompt counts as "empty/dummy" if it has no meaningful content: zero
# bytes, or nothing but whitespace / a placeholder TODO marker.
_DUMMY_MARKERS = ("TODO", "PLACEHOLDER", "FIXME")


def _is_empty_or_dummy(prompt_path: Path) -> bool:
    if not prompt_path.is_file():
        return True
    text = prompt_path.read_text(encoding="utf-8").strip()
    if not text:
        return True
    return any(marker in text for marker in _DUMMY_MARKERS)


def _prompt_path(mission_type: str, step_id: str) -> Path:
    return _MISSION_STEPS_ROOT / mission_type / step_id / "prompt.md"


# ---------------------------------------------------------------------------
# The 16 named, accepted-red gaps.
# ---------------------------------------------------------------------------


class TestSeededBlankPromptsAreNamedGaps:
    """Each of the 16 seeded blanks is individually named and marked xfail.

    xfail(strict=False): the gate stays green while S-C has not yet filled
    the prompt; the moment content lands, this reports XPASS instead of
    silently passing, which is the visible signal to delete the marker.
    """

    @pytest.mark.parametrize(
        ("mission_type", "step_id"),
        _SEEDED_BLANK_STEPS,
        ids=[f"{mt}/{sid}" for mt, sid in _SEEDED_BLANK_STEPS],
    )
    @pytest.mark.xfail(
        reason=(
            "WP05 seeds a blank placeholder prompt.md (C-004: no content "
            "invented); S-C is scoped to author real prompt content for "
            "this step."
        ),
        strict=False,
    )
    def test_prompt_is_not_empty(self, mission_type: str, step_id: str) -> None:
        prompt_path = _prompt_path(mission_type, step_id)
        assert prompt_path.is_file(), f"expected prompt.md at {prompt_path}"
        assert not _is_empty_or_dummy(prompt_path), (
            f"{mission_type}/{step_id}: prompt.md at {prompt_path} is empty "
            "or a dummy placeholder"
        )


class TestSeededBlankPromptsAreVerifiablyBlank:
    """Anti-vacuity guard: prove the 16 xfails above are exercising a real gap.

    An ``xfail`` that never actually fails proves nothing (it would pass
    silently either way). This class asserts, without the xfail marker, that
    each of the 16 files genuinely is empty today -- so the xfail above is
    verified to be exercising a live gap rather than a marker nobody checked.
    """

    @pytest.mark.parametrize(
        ("mission_type", "step_id"),
        _SEEDED_BLANK_STEPS,
        ids=[f"{mt}/{sid}" for mt, sid in _SEEDED_BLANK_STEPS],
    )
    def test_seeded_prompt_is_zero_bytes(self, mission_type: str, step_id: str) -> None:
        prompt_path = _prompt_path(mission_type, step_id)
        assert prompt_path.is_file(), f"expected prompt.md at {prompt_path}"
        assert prompt_path.stat().st_size == 0, (
            f"{mission_type}/{step_id}: prompt.md at {prompt_path} is no "
            "longer zero-bytes -- S-C has filled this gap; delete the "
            "matching xfail entry in TestSeededBlankPromptsAreNamedGaps "
            "(and this entry) for this step"
        )


class TestSeededBlankListIsExhaustive:
    """The named 16 is exactly the set of blank prompts under the 3 types.

    Guards against silent drift: a future edit that adds another blank
    prompt.md under documentation/research/plan (in the dispatch-relevant
    sequence, i.e. excluding retrospect) must also add it to
    ``_SEEDED_BLANK_STEPS`` here, or this test fails loudly instead of the
    gap going unnoticed.
    """

    _SEQUENCE_STEPS_BY_TYPE: dict[str, tuple[str, ...]] = {
        "documentation": (
            "discover",
            "audit",
            "design",
            "generate",
            "validate",
            "publish",
            "accept",
        ),
        "research": ("scoping", "methodology", "gathering", "synthesis", "output"),
        "plan": ("specify", "research", "plan", "review"),
    }

    def test_named_gap_count_is_exactly_sixteen(self) -> None:
        assert len(_SEEDED_BLANK_STEPS) == 16  # golden-count: cardinality-is-contract

    def test_named_gaps_cover_every_sequence_step_and_no_more(self) -> None:
        expected = {
            (mission_type, step_id)
            for mission_type, step_ids in self._SEQUENCE_STEPS_BY_TYPE.items()
            for step_id in step_ids
        }
        assert set(_SEEDED_BLANK_STEPS) == expected

    def test_every_sequence_step_prompt_is_currently_blank(self) -> None:
        """Every dispatch-relevant sequence step's prompt is blank today.

        Reads the filesystem directly (not the named list) so this test
        fails if a sequence step's prompt is populated without also being
        removed from ``_SEEDED_BLANK_STEPS`` above.
        """
        for mission_type, step_ids in self._SEQUENCE_STEPS_BY_TYPE.items():
            for step_id in step_ids:
                prompt_path = _prompt_path(mission_type, step_id)
                is_blank = _is_empty_or_dummy(prompt_path)
                named = (mission_type, step_id) in _SEEDED_BLANK_STEPS
                assert is_blank == named, (
                    f"{mission_type}/{step_id}: blank={is_blank} but "
                    f"named-as-seeded-blank={named} -- update "
                    "_SEEDED_BLANK_STEPS to match reality"
                )
