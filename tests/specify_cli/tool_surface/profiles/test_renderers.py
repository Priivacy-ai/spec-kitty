"""Unit tests for ``tool_surface.profiles.renderers``."""

from __future__ import annotations

from pathlib import Path

from doctrine.agent_profiles.profile import AgentProfile
from specify_cli.tool_surface.profiles.amazon_q_renderer import AmazonQProfileRenderer
from specify_cli.tool_surface.profiles.augment_renderer import AugmentProfileRenderer
from specify_cli.tool_surface.profiles.codex_renderer import (
    FORMAT_CODEX_AGENT,
    CodexProfileRenderer,
)
from specify_cli.tool_surface.profiles.renderers import (
    ClaudeCodeProfileRenderer,
    CopilotProfileRenderer,
    ProfileRenderer,
    get_renderer,
    native_name_violation,
)

import pytest

pytestmark = [pytest.mark.unit]


def make_test_profile(slug: str = "architect-alphonso") -> AgentProfile:
    """Build a minimal valid :class:`AgentProfile` for renderer tests."""
    return AgentProfile.model_validate(
        {
            "profile-id": slug,
            "name": slug.replace("-", " ").title(),
            "description": "A test profile: with a colon.",
            "roles": ["architect"],
            "purpose": "Test purpose line.",
            "specialization": {
                "primary-focus": "testing renderers",
                "avoidance-boundary": "anything else",
            },
        }
    )


def test_claude_code_renderer_satisfies_protocol() -> None:
    assert isinstance(ClaudeCodeProfileRenderer(), ProfileRenderer)


def test_claude_code_renderer_output_path() -> None:
    profile = make_test_profile(slug="architect-alphonso")
    renderer = ClaudeCodeProfileRenderer()
    path = renderer.output_path("claude", profile, Path("/project"))
    assert path == Path("/project/.claude/agents/architect-alphonso.md")


def test_claude_code_renderer_can_render() -> None:
    renderer = ClaudeCodeProfileRenderer()
    assert renderer.can_render("claude") is True
    assert renderer.can_render("copilot") is False


def test_claude_code_renderer_produces_yaml_frontmatter() -> None:
    profile = make_test_profile()
    body = ClaudeCodeProfileRenderer().render(profile)
    lines = body.splitlines()
    assert lines[0] == "---"
    assert "name: architect-alphonso" in lines
    assert lines.index("---", 1) > 0  # closing frontmatter delimiter present
    # Free-text description with a colon is quoted so YAML stays valid.
    assert 'description: "A test profile: with a colon."' in lines
    assert "roles: [architect]" in lines


def test_copilot_renderer_output_path() -> None:
    profile = make_test_profile(slug="researcher-robbie")
    renderer = CopilotProfileRenderer()
    path = renderer.output_path("copilot", profile, Path("/project"))
    assert path == Path("/project/.github/agents/researcher-robbie.agent.md")


def test_copilot_renderer_handles_vscode() -> None:
    renderer = CopilotProfileRenderer()
    assert renderer.can_render("copilot") is True
    assert renderer.can_render("vscode") is True
    assert renderer.can_render("claude") is False


def test_copilot_renderer_produces_agent_md_frontmatter() -> None:
    profile = make_test_profile(slug="researcher-robbie")
    body = CopilotProfileRenderer().render(profile)
    assert body.startswith("---\n")
    assert "name: researcher-robbie" in body
    assert profile.purpose in body


# ---------------------------------------------------------------------------
# Codex renderer (WP02)
# ---------------------------------------------------------------------------


def test_get_renderer_returns_codex_renderer_for_codex() -> None:
    renderer = get_renderer("codex")
    assert isinstance(renderer, CodexProfileRenderer)


def test_get_renderer_returns_codex_renderer_for_codex_cli() -> None:
    assert isinstance(get_renderer("codex-cli"), CodexProfileRenderer)


# ---------------------------------------------------------------------------
# Augment renderer (WP03)
# ---------------------------------------------------------------------------


def test_get_renderer_returns_augment_renderer_for_auggie() -> None:
    renderer = get_renderer("auggie")
    assert isinstance(renderer, AugmentProfileRenderer)


def test_get_renderer_returns_augment_renderer_for_augment() -> None:
    assert isinstance(get_renderer("augment"), AugmentProfileRenderer)


# ---------------------------------------------------------------------------
# Amazon Q renderer (WP03)
# ---------------------------------------------------------------------------


def test_get_renderer_returns_amazon_q_renderer_for_q() -> None:
    renderer = get_renderer("q")
    assert isinstance(renderer, AmazonQProfileRenderer)


def test_get_renderer_returns_amazon_q_renderer_for_amazon_q() -> None:
    assert isinstance(get_renderer("amazon-q"), AmazonQProfileRenderer)


# ---------------------------------------------------------------------------
# Existing registry lookups
# ---------------------------------------------------------------------------


def test_get_renderer_returns_claude_for_claude() -> None:
    renderer = get_renderer("claude")
    assert isinstance(renderer, ClaudeCodeProfileRenderer)


def test_get_renderer_returns_copilot_for_copilot_and_vscode() -> None:
    assert isinstance(get_renderer("copilot"), CopilotProfileRenderer)
    assert isinstance(get_renderer("vscode"), CopilotProfileRenderer)


def test_get_renderer_returns_none_for_unknown_tool() -> None:
    assert get_renderer("unknown_tool_xyz") is None


def test_get_renderer_returns_none_for_non_capable_harness() -> None:
    # Windsurf has no native agent primitive; get_renderer must return None.
    assert get_renderer("windsurf") is None



# ---------------------------------------------------------------------------
# CodexProfileRenderer tests
# ---------------------------------------------------------------------------


def test_codex_renderer_satisfies_protocol() -> None:
    assert isinstance(CodexProfileRenderer(), ProfileRenderer)


def test_codex_renderer_format_key() -> None:
    assert CodexProfileRenderer().format_key == FORMAT_CODEX_AGENT
    assert FORMAT_CODEX_AGENT == "codex-agent"


def test_codex_renderer_can_render() -> None:
    renderer = CodexProfileRenderer()
    assert renderer.can_render("codex") is True
    assert renderer.can_render("codex-cli") is True
    assert renderer.can_render("codex-agent") is True
    assert renderer.can_render("claude") is False
    assert renderer.can_render("unknown") is False


def test_codex_renderer_output_path() -> None:
    profile = make_test_profile(slug="architect-alphonso")
    renderer = CodexProfileRenderer()
    path = renderer.output_path("codex", profile, Path("/project"))
    assert path == Path("/project/.codex/agents/architect-alphonso.toml")


def test_codex_renderer_output_path_codex_cli_alias() -> None:
    profile = make_test_profile(slug="researcher-robbie")
    renderer = CodexProfileRenderer()
    path = renderer.output_path("codex-cli", profile, Path("/project"))
    assert path == Path("/project/.codex/agents/researcher-robbie.toml")


def test_codex_renderer_produces_valid_toml_with_required_fields() -> None:
    import tomllib

    profile = make_test_profile(slug="architect-alphonso")
    body = CodexProfileRenderer().render(profile)
    doc = tomllib.loads(body)
    assert "name" in doc
    assert "description" in doc
    assert "developer_instructions" in doc


def test_codex_renderer_name_from_profile_name() -> None:
    profile = make_test_profile(slug="architect-alphonso")
    body = CodexProfileRenderer().render(profile)
    assert "Architect Alphonso" in body


def test_codex_renderer_description_from_profile_description() -> None:
    profile = make_test_profile(slug="architect-alphonso")
    body = CodexProfileRenderer().render(profile)
    assert "A test profile: with a colon." in body


def test_codex_renderer_developer_instructions_from_purpose() -> None:
    profile = make_test_profile(slug="architect-alphonso")
    body = CodexProfileRenderer().render(profile)
    assert "Test purpose line." in body


def test_codex_renderer_skips_absent_optional_fields() -> None:
    """Optional fields (model, sandbox_mode) absent from the profile are not emitted."""
    import tomllib

    profile = make_test_profile(slug="architect-alphonso")
    body = CodexProfileRenderer().render(profile)
    doc = tomllib.loads(body)
    assert "model" not in doc
    assert "model_reasoning_effort" not in doc
    assert "sandbox_mode" not in doc


def test_codex_renderer_profile_with_empty_description_falls_back_to_purpose() -> None:
    """When description is empty, developer_instructions still uses purpose."""
    import tomllib

    data = {
        "profile-id": "analyst-alice",
        "name": "Analyst Alice",
        "description": "",
        "roles": ["analyst"],
        "purpose": "Analyse things thoroughly.",
        "specialization": {
            "primary-focus": "analysis",
            "avoidance-boundary": "(none declared)",
        },
    }
    profile = AgentProfile.model_validate(data)
    body = CodexProfileRenderer().render(profile)
    doc = tomllib.loads(body)
    assert doc["developer_instructions"] == "Analyse things thoroughly."


# ---------------------------------------------------------------------------
# Issue #2103 — tomli_w must not be a module-level import. It is pulled in
# during command registration, so a stale install missing the (declared)
# dependency would brick every CLI command at import time. It is imported
# lazily inside render() instead, with an actionable error.
# ---------------------------------------------------------------------------


def test_codex_renderer_does_not_import_tomli_w_at_module_level() -> None:
    """A module-level ``import tomli_w`` would bind it as a module attribute;
    the lazy import inside ``render()`` does not. Guards the #2103 regression."""
    from specify_cli.tool_surface.profiles import codex_renderer

    assert not hasattr(codex_renderer, "tomli_w")


def test_codex_render_missing_tomli_w_raises_actionable_error(monkeypatch) -> None:
    """When ``tomli_w`` is unavailable, ``render()`` fails with guidance to
    reinstall/upgrade — not an opaque ``ModuleNotFoundError`` traceback."""
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "tomli_w":
            raise ModuleNotFoundError("No module named 'tomli_w'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    profile = make_test_profile(slug="architect-alphonso")
    with pytest.raises(ModuleNotFoundError, match="upgrade spec-kitty"):
        CodexProfileRenderer().render(profile)


# ---------------------------------------------------------------------------
# Codex optional-field passthrough (WP08 — covers the *present* branches of
# codex_renderer._optional_fields, which the absent-only tests above miss).
# AgentProfile is a frozen pydantic model with no native model/sandbox fields,
# so the renderer reads these via getattr(); we inject them with
# object.__setattr__ to exercise the passthrough path the same way a profile
# variant carrying these attributes would.
# ---------------------------------------------------------------------------


def _with_codex_extras(profile: AgentProfile, **extras: object) -> AgentProfile:
    """Attach Codex optional attributes the renderer reads via ``getattr``."""
    for key, value in extras.items():
        object.__setattr__(profile, key, value)
    return profile


def test_codex_renderer_emits_model_when_present() -> None:
    import tomllib

    profile = _with_codex_extras(
        make_test_profile("architect-alphonso"), model="claude-sonnet-4-6"
    )
    doc = tomllib.loads(CodexProfileRenderer().render(profile))
    assert doc["model"] == "claude-sonnet-4-6"


def test_codex_renderer_emits_reasoning_effort_when_present() -> None:
    import tomllib

    profile = _with_codex_extras(
        make_test_profile("architect-alphonso"), model_reasoning_effort="high"
    )
    doc = tomllib.loads(CodexProfileRenderer().render(profile))
    assert doc["model_reasoning_effort"] == "high"


def test_codex_renderer_emits_sandbox_mode_when_present() -> None:
    import tomllib

    profile = _with_codex_extras(
        make_test_profile("architect-alphonso"), sandbox_mode="workspace-write"
    )
    doc = tomllib.loads(CodexProfileRenderer().render(profile))
    assert doc["sandbox_mode"] == "workspace-write"


def test_codex_renderer_emits_all_optional_fields_together() -> None:
    import tomllib

    profile = _with_codex_extras(
        make_test_profile("architect-alphonso"),
        model="gpt-5",
        model_reasoning_effort="medium",
        sandbox_mode="read-only",
    )
    doc = tomllib.loads(CodexProfileRenderer().render(profile))
    assert doc["model"] == "gpt-5"
    assert doc["model_reasoning_effort"] == "medium"
    assert doc["sandbox_mode"] == "read-only"


def test_codex_renderer_falsy_model_is_not_emitted() -> None:
    """An empty-string model is falsy and must be skipped (boundary branch)."""
    import tomllib

    profile = _with_codex_extras(make_test_profile("architect-alphonso"), model="")
    doc = tomllib.loads(CodexProfileRenderer().render(profile))
    assert "model" not in doc


def test_codex_renderer_falsy_sandbox_mode_none_is_not_emitted() -> None:
    """``sandbox_mode`` uses an ``is not None`` guard; ``None`` is skipped."""
    import tomllib

    profile = _with_codex_extras(
        make_test_profile("architect-alphonso"), sandbox_mode=None
    )
    doc = tomllib.loads(CodexProfileRenderer().render(profile))
    assert "sandbox_mode" not in doc


# ---------------------------------------------------------------------------
# Idempotency — re-rendering the same profile yields byte-identical output
# (FR-037 / WP08 Definition of Done).
# ---------------------------------------------------------------------------


def test_claude_code_renderer_is_idempotent() -> None:
    profile = make_test_profile("architect-alphonso")
    renderer = ClaudeCodeProfileRenderer()
    assert renderer.render(profile) == renderer.render(profile)


def test_codex_renderer_is_idempotent() -> None:
    profile = make_test_profile("architect-alphonso")
    renderer = CodexProfileRenderer()
    assert renderer.render(profile) == renderer.render(profile)


def test_copilot_renderer_is_idempotent() -> None:
    profile = make_test_profile("researcher-robbie")
    renderer = CopilotProfileRenderer()
    assert renderer.render(profile) == renderer.render(profile)


# ---------------------------------------------------------------------------
# Provenance footer — rendered Markdown carries the generator marker so a
# reader can tell the file is generated, not hand-authored (FR-037).
# ---------------------------------------------------------------------------


def test_claude_code_renderer_has_provenance_footer() -> None:
    body = ClaudeCodeProfileRenderer().render(make_test_profile())
    assert "spec kitty agent profile" in body.lower()
    assert "do not edit by hand" in body.lower()


# ---------------------------------------------------------------------------
# output_path with a dotted / special-character profile_id (T039 guidance) —
# the id flows straight into the filename, so a versioned id must round-trip.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "renderer, expected",
    [
        (ClaudeCodeProfileRenderer(), "/project/.claude/agents/my-analyst.v2.md"),
        (CopilotProfileRenderer(), "/project/.github/agents/my-analyst.v2.agent.md"),
        (CodexProfileRenderer(), "/project/.codex/agents/my-analyst.v2.toml"),
    ],
)
def test_output_path_preserves_dotted_profile_id(
    renderer: ProfileRenderer, expected: str
) -> None:
    profile = make_test_profile("my-analyst.v2")
    tool_key = renderer.format_key.removesuffix("-agent")
    path = renderer.output_path(tool_key, profile, Path("/project"))
    assert path == Path(expected)


# ---------------------------------------------------------------------------
# Parametric coverage across ALL FIVE renderers (FR-038 / WP08 DoD): each
# renderer's own tool_key is accepted, output_path is a non-None Path, and
# render() returns a non-empty str.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "renderer, tool_key",
    [
        (ClaudeCodeProfileRenderer(), "claude"),
        (CopilotProfileRenderer(), "copilot"),
        (CodexProfileRenderer(), "codex"),
        (AugmentProfileRenderer(), "auggie"),
        (AmazonQProfileRenderer(), "q"),
    ],
)
def test_all_renderers_render_non_empty_str(
    renderer: ProfileRenderer, tool_key: str
) -> None:
    profile = make_test_profile("architect-alphonso")
    assert renderer.can_render(tool_key) is True
    path = renderer.output_path(tool_key, profile, Path("/project"))
    assert isinstance(path, Path)
    rendered = renderer.render(profile)
    assert isinstance(rendered, str)
    assert len(rendered) > 50


# --- #1940 native-name validity (drives the profile-name-invalid condition) ---


def test_native_name_violation_accepts_clean_id() -> None:
    """A canonical kebab-case id is legal for the native filename."""
    assert native_name_violation("architect-alphonso") is None


@pytest.mark.parametrize(
    "bad_id",
    [
        "bad/slash",  # path separator escapes the agents dir
        "bad\\back",  # Windows separator
        "..",  # path traversal
        "with space",  # whitespace is illegal in the native filename
        "tab\tchar",  # control char
        "",  # empty id has no filename stem
    ],
)
def test_native_name_violation_flags_illegal_ids(bad_id: str) -> None:
    """Ids illegal for ``.claude/agents/<id>.md`` return a violation reason."""
    reason = native_name_violation(bad_id)
    assert reason is not None
    assert isinstance(reason, str) and reason
