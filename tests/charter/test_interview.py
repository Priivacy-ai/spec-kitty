"""Scope: mock-boundary tests for charter interview persistence — no real git."""

from pathlib import Path

import pytest

from ruamel.yaml import YAML

from charter.activation.interview import (
    MINIMAL_QUESTION_ORDER,
    QUESTION_ORDER,
    _existing_directives_from,
    _load_existing_answers,
    _load_packaged_defaults,
    _merge_required_directives,
    _prefill_answer_defaults,
    apply_answer_overrides,
    apply_org_charter_pre_fill_to_answers,
    default_interview,
    read_interview_answers,
    write_interview_answers,
)

pytestmark = pytest.mark.fast


def test_default_interview_minimal_uses_minimal_question_set() -> None:
    """Minimal profile populates exactly the MINIMAL_QUESTION_ORDER keys."""
    # Arrange / Act
    interview = default_interview(mission="software-dev", profile="minimal")
    # Assumption check
    assert len(MINIMAL_QUESTION_ORDER) > 0
    # Assert
    assert interview.mission == "software-dev"
    assert interview.profile == "minimal"
    assert set(interview.answers.keys()) == set(MINIMAL_QUESTION_ORDER)
    assert interview.selected_paradigms == []
    assert interview.selected_directives == []
    assert interview.available_tools == ["git", "spec-kitty"]


def test_default_interview_comprehensive_includes_full_questions() -> None:
    """Comprehensive profile includes all QUESTION_ORDER keys."""
    # Arrange / Act
    interview = default_interview(mission="software-dev", profile="comprehensive")
    # Assumption check
    assert len(QUESTION_ORDER) >= len(MINIMAL_QUESTION_ORDER)
    # Assert
    assert interview.profile == "comprehensive"
    assert set(QUESTION_ORDER).issubset(set(interview.answers.keys()))


def test_interview_roundtrip_yaml(tmp_path: Path) -> None:
    """Write then read preserves all interview fields."""
    # Arrange
    interview = default_interview(mission="software-dev", profile="minimal")
    interview = apply_answer_overrides(interview, agent_profile="reviewer", agent_role="reviewer")
    path = tmp_path / "answers.yaml"
    # Assumption check
    assert not path.exists()
    # Act
    write_interview_answers(path, interview)
    loaded = read_interview_answers(path)
    # Assert
    assert loaded is not None
    assert loaded.mission == interview.mission
    assert loaded.profile == interview.profile
    assert loaded.answers == interview.answers
    assert loaded.selected_paradigms == interview.selected_paradigms
    assert loaded.agent_profile == "reviewer"
    assert loaded.agent_role == "reviewer"


def test_apply_answer_overrides_updates_answers_and_lists() -> None:
    """apply_answer_overrides replaces answers, paradigms, directives, and tools."""
    # Arrange
    base = default_interview(mission="software-dev", profile="minimal")
    # Assumption check
    assert base.answers.get("project_intent") != "Keep workflows deterministic."
    # Act
    updated = apply_answer_overrides(
        base,
        answers={"project_intent": "Keep workflows deterministic."},
        selected_paradigms=["test-first"],
        selected_directives=["TEST_FIRST"],
        available_tools=["git", "pytest"],
    )
    # Assert
    assert updated.answers["project_intent"] == "Keep workflows deterministic."
    assert updated.selected_paradigms == ["test-first"]
    assert updated.selected_directives == ["TEST_FIRST"]
    assert updated.available_tools == ["git", "pytest"]


@pytest.mark.parametrize(
    "phrase",
    [
        "I want Lynn Cole's rules.",
        "I want to do it like Lynn Cole.",
        "Use the Lynn Cole.",
        "Agents write too much code.",
        "AI code is bloated.",
        "Avoid agentic code bloat.",
    ],
)
def test_apply_answer_overrides_selects_lynn_cole_doctrine_aliases(phrase: str) -> None:
    base = default_interview(mission="software-dev", profile="minimal")

    updated = apply_answer_overrides(
        base,
        answers={"project_intent": phrase},
    )

    assert "DIRECTIVE_039" in updated.selected_directives
    assert "deep-module-design" in updated.selected_paradigms


def test_apply_answer_overrides_does_not_duplicate_lynn_cole_aliases() -> None:
    base = default_interview(mission="software-dev", profile="minimal")

    updated = apply_answer_overrides(
        base,
        answers={"project_intent": "Use Lynn Cole's agent coding rules."},
        selected_paradigms=["deep-module-design"],
        selected_directives=["DIRECTIVE_039"],
    )

    assert updated.selected_directives == ["DIRECTIVE_039"]
    assert updated.selected_paradigms == ["deep-module-design"]


def test_apply_answer_overrides_updates_agent_identity_fields() -> None:
    base = default_interview(mission="software-dev", profile="minimal")

    updated = apply_answer_overrides(
        base,
        agent_profile="architect",
        agent_role="reviewer",
    )

    assert updated.agent_profile == "architect"
    assert updated.agent_role == "reviewer"


def test_load_packaged_defaults_returns_empty_when_resource_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "charter.activation.interview.importlib.resources.files",
        lambda package: (_ for _ in ()).throw(FileNotFoundError("missing")),
    )

    defaults = _load_packaged_defaults()

    assert defaults == {
        "answers": {},
        "selected_paradigms": [],
        "selected_directives": [],
        "selected_tactics": [],
        "available_tools": [],
    }


def test_load_packaged_defaults_returns_empty_on_invalid_yaml(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class StubResource:
        def joinpath(self, name: str) -> "StubResource":
            assert name == "defaults.yaml"
            return self

        def read_text(self, encoding: str = "utf-8") -> str:
            assert encoding == "utf-8"
            return "answers: ["

    monkeypatch.setattr("charter.activation.interview.importlib.resources.files", lambda package: StubResource())

    defaults = _load_packaged_defaults()

    assert defaults["answers"] == {}
    assert defaults["selected_paradigms"] == []


def test_load_packaged_defaults_returns_empty_when_yaml_is_not_mapping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class StubResource:
        def joinpath(self, name: str) -> "StubResource":
            assert name == "defaults.yaml"
            return self

        def read_text(self, encoding: str = "utf-8") -> str:
            assert encoding == "utf-8"
            return "- not-a-mapping\n"

    monkeypatch.setattr("charter.activation.interview.importlib.resources.files", lambda package: StubResource())

    defaults = _load_packaged_defaults()

    assert defaults["answers"] == {}
    assert defaults["available_tools"] == []


# --- apply_org_charter_pre_fill_to_answers decomposition helpers ---
# (S3776 cognitive-complexity refactor: interview.py:apply_org_charter_pre_fill_to_answers)


def test_load_existing_answers_missing_file_returns_empty_dict(tmp_path: Path) -> None:
    """A missing answers file degrades to an empty dict, not an error."""
    yaml = YAML()
    result = _load_existing_answers(tmp_path / "does-not-exist.yaml", yaml)
    assert result == {}


def test_load_existing_answers_malformed_yaml_returns_empty_dict(tmp_path: Path) -> None:
    """Syntactically-broken YAML degrades to an empty dict per the pre-existing contract."""
    path = tmp_path / "answers.yaml"
    path.write_text("answers: [", encoding="utf-8")
    yaml = YAML()
    result = _load_existing_answers(path, yaml)
    assert result == {}


def test_load_existing_answers_non_mapping_yaml_returns_empty_dict(tmp_path: Path) -> None:
    """A YAML file that decodes to a non-mapping (e.g. a list) also degrades to empty."""
    path = tmp_path / "answers.yaml"
    path.write_text("- not-a-mapping\n", encoding="utf-8")
    yaml = YAML()
    result = _load_existing_answers(path, yaml)
    assert result == {}


def test_load_existing_answers_valid_mapping_returned(tmp_path: Path) -> None:
    """A valid mapping file is loaded as-is."""
    path = tmp_path / "answers.yaml"
    path.write_text("project_intent: ship it\n", encoding="utf-8")
    yaml = YAML()
    result = _load_existing_answers(path, yaml)
    assert result == {"project_intent": "ship it"}


def test_prefill_answer_defaults_sets_missing_keys_only() -> None:
    """Only keys absent from ``existing`` are set; present keys are preserved."""
    existing: dict[str, object] = {"project_intent": "already set"}
    prefilled = _prefill_answer_defaults(
        existing, {"project_intent": "should not overwrite", "quality_gates": "ci must pass"}
    )
    assert prefilled == 1
    assert existing["project_intent"] == "already set"
    assert existing["quality_gates"] == "ci must pass"


def test_prefill_answer_defaults_no_defaults_returns_zero() -> None:
    existing: dict[str, object] = {}
    assert _prefill_answer_defaults(existing, {}) == 0
    assert existing == {}


def test_existing_directives_from_list_value() -> None:
    existing = {"selected_directives": ["DIRECTIVE_001", "DIRECTIVE_002"]}
    assert _existing_directives_from(existing) == ["DIRECTIVE_001", "DIRECTIVE_002"]


def test_existing_directives_from_csv_string_value() -> None:
    existing = {"selected_directives": "DIRECTIVE_001, DIRECTIVE_002"}
    assert _existing_directives_from(existing) == ["DIRECTIVE_001", "DIRECTIVE_002"]


def test_existing_directives_from_missing_key_returns_empty_list() -> None:
    assert _existing_directives_from({}) == []


def test_existing_directives_from_unexpected_type_returns_empty_list() -> None:
    """A non-list, non-str value (e.g. int) falls back to an empty list."""
    assert _existing_directives_from({"selected_directives": 42}) == []


def test_merge_required_directives_appends_missing_only() -> None:
    existing: dict[str, object] = {"selected_directives": ["DIRECTIVE_001"]}
    new_required = _merge_required_directives(existing, ["DIRECTIVE_001", "DIRECTIVE_002"])
    assert new_required == ["DIRECTIVE_002"]
    assert existing["selected_directives"] == ["DIRECTIVE_001", "DIRECTIVE_002"]


def test_merge_required_directives_no_new_directives_leaves_existing_untouched() -> None:
    existing: dict[str, object] = {"selected_directives": ["DIRECTIVE_001"]}
    new_required = _merge_required_directives(existing, ["DIRECTIVE_001"])
    assert new_required == []
    assert existing["selected_directives"] == ["DIRECTIVE_001"]


def test_apply_org_charter_pre_fill_writes_defaults_and_directives(tmp_path: Path) -> None:
    """End-to-end characterization: both prefill and directive messages emitted, file written."""
    answers_path = tmp_path / "answers.yaml"
    messages = apply_org_charter_pre_fill_to_answers(
        answers_path=answers_path,
        interview_defaults={"project_intent": "ship reliably"},
        required_directives=["DIRECTIVE_039"],
    )
    assert len(messages) == 2
    assert any("directives" in m for m in messages)
    assert any("interview defaults" in m for m in messages)
    assert answers_path.exists()
    persisted = YAML(typ="safe").load(answers_path.read_text(encoding="utf-8"))
    assert persisted["project_intent"] == "ship reliably"
    assert persisted["selected_directives"] == ["DIRECTIVE_039"]


def test_apply_org_charter_pre_fill_noop_when_nothing_to_apply(tmp_path: Path) -> None:
    """No interview_defaults/required_directives args -> empty messages, no file written."""
    answers_path = tmp_path / "answers.yaml"
    messages = apply_org_charter_pre_fill_to_answers(
        answers_path=answers_path,
        interview_defaults={},
        required_directives=[],
    )
    assert messages == []
    assert not answers_path.exists()


def test_apply_org_charter_pre_fill_preserves_existing_values(tmp_path: Path) -> None:
    """Existing answers are never reverted to org defaults on re-run; only missing keys fill in."""
    answers_path = tmp_path / "answers.yaml"
    answers_path.write_text("project_intent: project-specific choice\n", encoding="utf-8")

    messages = apply_org_charter_pre_fill_to_answers(
        answers_path=answers_path,
        interview_defaults={"project_intent": "org default", "quality_gates": "ci gate"},
        required_directives=[],
    )

    assert messages == ["Pre-filled 1 interview defaults from org charter."]
    persisted = YAML(typ="safe").load(answers_path.read_text(encoding="utf-8"))
    assert persisted["project_intent"] == "project-specific choice"
    assert persisted["quality_gates"] == "ci gate"
