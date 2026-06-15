"""WP17 unit tests — ``charter context --include`` selector routing.

Pins the behaviour of :func:`charter.context.build_charter_context_include`
after WP17 routed the selector kind through the canonical
:meth:`doctrine.artifact_kinds.ArtifactKind.from_operator_token` resolver
(WP01) and wired ``template:<mission>/<name>`` through WP18's
:func:`doctrine.template_catalog.resolve_template_by_id` (FR-022/023/024/034).

Coverage:

* ``agent-profile:<id>`` (hyphen) resolves to the ``agent_profile`` renderer
  in both the human-text and JSON-context entry points (the original bug —
  the hyphenated operator token used not to resolve).
* Sibling hyphenated kinds (``mission-step-contract``) resolve.
* Canonical underscore + lowercase tokens still resolve.
* ``template:<mission>/<name>`` renders the resolved template content; a
  malformed template ID fails closed with a structured ``ValueError``.
* Unknown selector kinds fail closed with the canonical vocabulary error
  (no silent fallback), and ``mission-type`` is rejected explicitly.
* The CLI ``--include`` help advertises ``agent-profile`` and ``template``.

The doctrine-service-backed kinds are exercised against a stub service so the
test isolates the routing seam; the template include runs against the real
doctrine-bundled missions tree.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import charter.context as context_module
from charter.pack_context import CharterPackConfigError
from charter.context import build_charter_context_include


pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# Stub doubles for the DoctrineService repositories
# ---------------------------------------------------------------------------


class _StubRepo:
    """Minimal repository stub mirroring ``BaseDoctrineRepository.get``."""

    def __init__(self, items: dict[str, Any] | None = None) -> None:
        self._items = items or {}

    def get(self, item_id: str) -> Any | None:  # noqa: ANN401 — duck-typed
        return self._items.get(item_id)

    def get_provenance(self, item_id: str) -> str | None:
        return None


class _StubService:
    """DoctrineService stand-in carrying the kinds WP17 routes."""

    def __init__(
        self,
        *,
        directives: _StubRepo | None = None,
        tactics: _StubRepo | None = None,
        styleguides: _StubRepo | None = None,
        toolguides: _StubRepo | None = None,
        paradigms: _StubRepo | None = None,
        procedures: _StubRepo | None = None,
        agent_profiles: _StubRepo | None = None,
        mission_step_contracts: _StubRepo | None = None,
    ) -> None:
        self.directives = directives or _StubRepo()
        self.tactics = tactics or _StubRepo()
        self.styleguides = styleguides or _StubRepo()
        self.toolguides = toolguides or _StubRepo()
        self.paradigms = paradigms or _StubRepo()
        self.procedures = procedures or _StubRepo()
        self.agent_profiles = agent_profiles or _StubRepo()
        self.mission_step_contracts = mission_step_contracts or _StubRepo()


class _DummyAgentProfile:
    def __init__(self, *, name: str, purpose: str, roles: list[str]) -> None:
        self.name = name
        self.purpose = purpose
        self.roles = roles


class _DummyStep:
    def __init__(self, *, title: str, id_: str | None = None, description: str = "") -> None:
        self.title = title
        self.id = id_
        self.description = description


class _DummyContract:
    def __init__(self, *, action: str, mission: str, steps: list[_DummyStep]) -> None:
        self.action = action
        self.mission = mission
        self.steps = steps


def _patch_service(monkeypatch: pytest.MonkeyPatch, service: _StubService) -> None:
    """Route ``build_charter_context_include`` onto a stub doctrine service."""
    monkeypatch.setattr(
        context_module,
        "_build_doctrine_service",
        lambda repo_root, *, org_roots=None: service,
    )


# ---------------------------------------------------------------------------
# agent-profile selector (FR-022/023) — the original bug
# ---------------------------------------------------------------------------


class TestAgentProfileInclude:
    def test_hyphenated_agent_profile_resolves(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        profile = _DummyAgentProfile(
            name="Python Pedro",
            purpose="Implement Python work with TDD discipline.",
            roles=["implementer"],
        )
        _patch_service(
            monkeypatch,
            _StubService(agent_profiles=_StubRepo({"python-pedro": profile})),
        )

        text = build_charter_context_include(tmp_path, "agent-profile:python-pedro")

        assert "Agent profile python-pedro: Python Pedro" in text

    def test_underscore_agent_profile_resolves(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        profile = _DummyAgentProfile(
            name="Python Pedro", purpose="p", roles=["implementer"]
        )
        _patch_service(
            monkeypatch,
            _StubService(agent_profiles=_StubRepo({"python-pedro": profile})),
        )

        text = build_charter_context_include(tmp_path, "agent_profile:python-pedro")

        assert "Agent profile python-pedro: Python Pedro" in text

    def test_mixed_case_kind_resolves(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        profile = _DummyAgentProfile(
            name="Python Pedro", purpose="p", roles=["implementer"]
        )
        _patch_service(
            monkeypatch,
            _StubService(agent_profiles=_StubRepo({"python-pedro": profile})),
        )

        text = build_charter_context_include(tmp_path, "Agent-Profile:python-pedro")

        assert "Agent profile python-pedro: Python Pedro" in text

    def test_unknown_agent_profile_id_fails_closed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_service(monkeypatch, _StubService())

        with pytest.raises(ValueError, match="No agent_profile found"):
            build_charter_context_include(tmp_path, "agent-profile:nope")


# ---------------------------------------------------------------------------
# Sibling hyphenated kinds (FR-024)
# ---------------------------------------------------------------------------


class TestSiblingHyphenKinds:
    def test_mission_step_contract_hyphen_resolves(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        contract = _DummyContract(
            action="implement",
            mission="software-dev",
            steps=[_DummyStep(title="Run focused tests", id_="s1")],
        )
        _patch_service(
            monkeypatch,
            _StubService(
                mission_step_contracts=_StubRepo({"implement-contract": contract})
            ),
        )

        text = build_charter_context_include(
            tmp_path, "mission-step-contract:implement-contract"
        )

        assert "Mission step contract implement-contract: implement" in text


# ---------------------------------------------------------------------------
# template selector (FR-034) — resolved through WP18 against the real tree
# ---------------------------------------------------------------------------


class TestTemplateInclude:
    def test_template_include_renders_content(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("SPEC_KITTY_TEMPLATE_ROOT", raising=False)
        monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "empty-global-home"))

        text = build_charter_context_include(
            tmp_path, "template:software-dev/spec-template.md"
        )

        # The header names the mission-qualified id and the resolved tier; the
        # exact tier depends on the host (package_default vs a global mirror),
        # so assert on the stable prefix rather than a fixed tier.
        first_line = text.splitlines()[0]
        assert first_line.startswith(
            "Template software-dev/spec-template.md (tier: "
        )
        # The resolved template body is appended after the header line.
        assert len(text.splitlines()) > 1
        assert "Mission Specification" in text

    def test_missing_template_fails_closed(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="No template found"):
            build_charter_context_include(
                tmp_path, "template:software-dev/does-not-exist.md"
            )

    def test_malformed_template_id_fails_closed(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Malformed template selector"):
            build_charter_context_include(tmp_path, "template:no-slash-here")

    def test_template_include_surfaces_pack_config_errors(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        def _raise_pack_config_error(_repo_root: Path) -> Path | None:
            raise CharterPackConfigError("broken pack config")

        monkeypatch.setattr(context_module, "resolve_project_root", _raise_pack_config_error)

        with pytest.raises(CharterPackConfigError, match="CHARTER_PACK_CONFIG_INVALID"):
            build_charter_context_include(
                tmp_path, "template:software-dev/spec-template.md"
            )


# ---------------------------------------------------------------------------
# Unknown / unsupported selectors — fail closed, no silent fallback
# ---------------------------------------------------------------------------


class TestUnknownSelectors:
    def test_unknown_kind_fails_closed(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Unknown artifact kind token"):
            build_charter_context_include(tmp_path, "bogus-kind:whatever")

    def test_mission_type_selector_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="mission-type"):
            build_charter_context_include(tmp_path, "mission-type:software-dev")

    def test_malformed_selector_without_separator(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="<kind>:<id>"):
            build_charter_context_include(tmp_path, "not-a-selector")


# ---------------------------------------------------------------------------
# JSON entry point parity (FR-022/023) — agent-profile renders via the CLI
# ---------------------------------------------------------------------------


class TestJsonEntryPoint:
    def test_agent_profile_renders_in_json_context(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from typer.testing import CliRunner

        from specify_cli.cli.commands.charter import charter_app
        import specify_cli.cli.commands.charter as charter_pkg

        profile = _DummyAgentProfile(
            name="Python Pedro", purpose="p", roles=["implementer"]
        )
        _patch_service(
            monkeypatch,
            _StubService(agent_profiles=_StubRepo({"python-pedro": profile})),
        )
        monkeypatch.setattr(charter_pkg, "find_repo_root", lambda: tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            charter_app,
            ["context", "--include", "agent-profile:python-pedro", "--json"],
        )

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["success"] is True
        assert payload["include"] == "agent-profile:python-pedro"
        assert "Agent profile python-pedro: Python Pedro" in payload["context"]


# ---------------------------------------------------------------------------
# CLI help advertises the new kinds (FR-024)
# ---------------------------------------------------------------------------


class TestIncludeHelp:
    def test_help_advertises_agent_profile_and_template(self) -> None:
        from typer.testing import CliRunner

        from specify_cli.cli.commands.charter import charter_app

        # Force a wide terminal so Rich/typer does not truncate the option
        # help text mid-word before our advertised kinds appear.
        runner = CliRunner()
        result = runner.invoke(
            charter_app,
            ["context", "--help"],
            env={"COLUMNS": "400", "TERM": "dumb"},
        )

        assert result.exit_code == 0, result.output
        normalized = " ".join(result.output.split())
        assert "agent-profile" in normalized
        assert "template" in normalized
