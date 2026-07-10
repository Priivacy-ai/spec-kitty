"""T013/T027 (#2524 class) regression: ``charter activate``/``deactivate``
mutate ONLY ``.kittify/config.yaml`` ``activated_*`` -- never
``.kittify/charter/interview/answers.yaml`` -- and the compiled charter
reference set (:func:`charter.compiler.compile_charter`, the source
``references.yaml`` is written from) tracks that mutation directly, with no
dangling reference left behind on deactivate.

Also pins the SPDD-no-flip guard (squad D1, WP03 context): switching the
reference-set derivation source from ``interview.selected_*`` to
``config.activated_*`` (WP02) must not spuriously change SPDD/REASONS
auto-activation for this project's real dogfood charter.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from charter.compiler import compile_charter
from charter.extractor import Extractor, write_extraction_result
from charter.interview import default_interview, read_interview_answers
from charter.pack_context import PackContext
from doctrine.service import DoctrineService
from doctrine.spdd_reasons.activation import clear_activation_cache, is_spdd_reasons_active
from specify_cli.cli.commands.charter import charter_app

pytestmark = [pytest.mark.fast, pytest.mark.doctrine]

REPO_ROOT = Path(__file__).resolve().parents[2]
BUILT_IN_DOCTRINE_ROOT = REPO_ROOT / "src" / "doctrine"
ANSWERS_PATH = REPO_ROOT / ".kittify" / "charter" / "interview" / "answers.yaml"

runner = CliRunner()

# A real built-in styleguide with no directive-closure edge reaching it (one
# of the #2524 baseline danglers WP02 T026 fixed via direct-root activation).
# Narrowing `activated_styleguides` to an explicit empty list, then activating
# only this id, proves the whole activate -> config.yaml -> compiled-set
# pipeline independent of the shipped default pack (which already includes
# it, so an unnarrowed fixture would make the transition non-observable).
_TARGET_KIND = "styleguide"
_TARGET_ID = "aggregate-design-rules"
_TARGET_REFERENCE_ID = "STYLEGUIDE:aggregate-design-rules"


@pytest.fixture()
def project_root(tmp_path: Path) -> Path:
    """A project with EVERY kind explicitly narrowed to empty.

    An explicit ``[]`` (present-but-empty) is load-bearing here: it is NOT
    the same three-state value as an absent key (which means "all built-ins
    active" -- including every OTHER kind's direct-root URNs, any of which
    could reach ``aggregate-design-rules`` via a transitive ``suggests``
    edge and mask the very activate/deactivate transition this test exists
    to observe). Every kind must be narrowed, not just directives/tactics/
    styleguides: with no config key at all, ``activated_agent_profiles`` and
    ``activated_procedures`` also default to "all built-ins active" and seed
    the same BFS as additional direct roots (mirrors
    ``tests/charter/test_config_sourced_derivation.py::test_direct_root_styleguide_resolves_with_no_directive_selected``,
    scaled to every kind for this CLI-level, real-doctrine-corpus test).
    """
    kittify = tmp_path / ".kittify"
    kittify.mkdir()
    (kittify / "config.yaml").write_text(
        "activated_directives: []\n"
        "activated_tactics: []\n"
        "activated_styleguides: []\n"
        "activated_toolguides: []\n"
        "activated_paradigms: []\n"
        "activated_procedures: []\n"
        "activated_agent_profiles: []\n"
        "activated_mission_step_contracts: []\n",
        encoding="utf-8",
    )
    return tmp_path


def _compiled_reference_ids(project_root: Path) -> set[str]:
    pack_context = PackContext.from_config(project_root)
    doctrine_service = DoctrineService(built_in_root=BUILT_IN_DOCTRINE_ROOT)
    compiled = compile_charter(
        mission="software-dev",
        interview=default_interview(mission="software-dev"),
        repo_root=project_root,
        doctrine_service=doctrine_service,
        pack_context=pack_context,
    )
    return {reference.id for reference in compiled.references}


def _answers_path(project_root: Path) -> Path:
    return project_root / ".kittify" / "charter" / "interview" / "answers.yaml"


def _activate(project_root: Path) -> object:
    return runner.invoke(
        charter_app,
        ["activate", "--repo-root", str(project_root), _TARGET_KIND, _TARGET_ID],
        catch_exceptions=False,
    )


def _deactivate(project_root: Path) -> object:
    return runner.invoke(
        charter_app,
        ["deactivate", "--repo-root", str(project_root), _TARGET_KIND, _TARGET_ID],
        catch_exceptions=False,
    )


class TestActivateResolvesNoAnswersEdit:
    """T013 (#2524 class): ``charter activate`` makes the artefact resolve
    with NO ``answers.yaml`` edit."""

    def test_target_absent_before_activation(self, project_root: Path) -> None:
        assert _TARGET_REFERENCE_ID not in _compiled_reference_ids(project_root)

    def test_activate_resolves_with_no_answers_edit(self, project_root: Path) -> None:
        answers_path = _answers_path(project_root)
        assert not answers_path.exists(), "fixture assumption: no interview answers file at all"

        result = _activate(project_root)
        assert result.exit_code == 0, result.output

        # #2524 class: activation is a config.yaml-only mutation -- it never
        # creates or edits an interview answers.yaml.
        assert not answers_path.exists(), "charter activate must not write/edit answers.yaml"

        assert _TARGET_REFERENCE_ID in _compiled_reference_ids(project_root), (
            "activated artefact must resolve in the compiled reference set with no answers.yaml edit"
        )


class TestDeactivateDropsNoAnswersEdit:
    """T027 (spec Acceptance Scenario 2): ``charter deactivate`` makes the
    artefact stop resolving, with NO ``answers.yaml`` edit and no dangling
    reference left behind."""

    def test_deactivate_drops_resolution_with_no_answers_edit(self, project_root: Path) -> None:
        answers_path = _answers_path(project_root)

        activate_result = _activate(project_root)
        assert activate_result.exit_code == 0, activate_result.output
        assert _TARGET_REFERENCE_ID in _compiled_reference_ids(project_root)

        deactivate_result = _deactivate(project_root)
        assert deactivate_result.exit_code == 0, deactivate_result.output

        assert not answers_path.exists(), "charter deactivate must not write/edit answers.yaml"

        reference_ids = _compiled_reference_ids(project_root)
        assert _TARGET_REFERENCE_ID not in reference_ids, (
            "deactivated artefact must stop resolving in the compiled reference set"
        )

        # No dangling reference remains: the deactivated artefact's id is not
        # cited anywhere in the compiled markdown either (nothing left over
        # for a `test_no_new_charter_reference_danglers`-style guard to trip
        # on for THIS artefact).
        pack_context = PackContext.from_config(project_root)
        doctrine_service = DoctrineService(built_in_root=BUILT_IN_DOCTRINE_ROOT)
        compiled = compile_charter(
            mission="software-dev",
            interview=default_interview(mission="software-dev"),
            repo_root=project_root,
            doctrine_service=doctrine_service,
            pack_context=pack_context,
        )
        assert f"`{_TARGET_ID}`" not in compiled.markdown


class TestSpddActivationDoesNotFlip:
    """T027 SPDD-no-flip guard (squad D1): config-sourced derivation (WP02)
    must not spuriously flip SPDD/REASONS auto-activation for THIS project's
    real dogfood charter.

    ``generate.py`` runs ``sync_charter`` right after ``compile_charter``;
    the compiler's ``## Governance Activation`` render feeds
    ``governance.yaml`` ``doctrine.selected_*``, which
    :func:`doctrine.spdd_reasons.activation.is_spdd_reasons_active` keys on
    (paradigm ``structured-prompt-driven-development``, tactics
    ``reasons-canvas-fill``/``reasons-canvas-review``, or directive
    ``DIRECTIVE_038``).
    """

    def setup_method(self) -> None:
        clear_activation_cache()

    def test_config_sourced_compile_keeps_spdd_active(self, tmp_path: Path) -> None:
        interview = read_interview_answers(ANSWERS_PATH)
        assert interview is not None, "expected the project's real interview answers to load"

        # Fixture/sanity assumption: the real dogfood interview ALSO selects
        # DIRECTIVE_038 directly (the retired answers-sourced path was
        # already SPDD-active) -- this test proves the config-sourced switch
        # (WP02) does not turn that False, which would be a silent SPDD
        # deactivation regression on this project's own charter.
        assert "DIRECTIVE_038" in interview.selected_directives

        doctrine_service = DoctrineService(built_in_root=BUILT_IN_DOCTRINE_ROOT)
        pack_context = PackContext.from_config(REPO_ROOT)
        compiled = compile_charter(
            mission=interview.mission,
            interview=interview,
            repo_root=REPO_ROOT,
            doctrine_service=doctrine_service,
            pack_context=pack_context,
        )

        extraction = Extractor().extract(compiled.markdown)
        write_extraction_result(extraction, tmp_path / ".kittify" / "charter")

        clear_activation_cache()
        assert is_spdd_reasons_active(tmp_path) is True, (
            "config-sourced compilation must not flip SPDD auto-activation off for "
            "the dogfood charter, which activates the SPDD paradigm/tactics/directive "
            "directly in .kittify/config.yaml"
        )
