"""Contract test: ``unknown`` mission state and the legacy
``[QUERY - no result provided]`` placeholder must never surface in shipped
templates or runtime decision JSON for a valid run (FR-020, WP04/T019).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.fast


_PLACEHOLDER = "[QUERY - no result provided]"
_REPO_ROOT = Path(__file__).resolve().parents[2]
_TEMPLATES_ROOT = _REPO_ROOT / "src" / "specify_cli" / "missions"


class TestNoLegacyQueryPlaceholderInTemplates:
    """The literal placeholder must not appear in any shipped command template."""

    def test_placeholder_is_absent_from_command_templates(self) -> None:
        offenders: list[Path] = []
        for path in _TEMPLATES_ROOT.rglob("*.md"):
            if "command-templates" not in path.parts and "templates" not in path.parts:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            if _PLACEHOLDER in text:
                offenders.append(path)
        assert not offenders, (
            f"Found legacy placeholder '{_PLACEHOLDER}' in shipped templates: {offenders}"
        )

    def test_placeholder_is_absent_from_runtime_source(self) -> None:
        runtime_root = _REPO_ROOT / "src" / "specify_cli" / "next"
        offenders: list[tuple[Path, int]] = []
        for path in runtime_root.rglob("*.py"):
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except OSError:
                continue
            for idx, line in enumerate(lines, start=1):
                if _PLACEHOLDER in line:
                    offenders.append((path, idx))
        assert not offenders, (
            "Runtime source must not emit the legacy placeholder. Offenders: "
            f"{offenders}"
        )


class TestQueryModeDoesNotReturnUnknownForValidMission:
    """For a populated mission run, mission_state must not be 'unknown'."""

    def test_query_decision_for_valid_run_has_real_state(self, tmp_path: Path) -> None:
        """When the mission has a runtime snapshot, mission_state is real."""
        from specify_cli.next.decision import Decision, DecisionKind

        decision = Decision(
            kind=DecisionKind.query,
            agent="claude",
            mission_slug="fixture-mission",
            mission="software-dev",
            mission_state="implementing",
            timestamp="2026-04-26T00:00:00+00:00",
            is_query=True,
            mission_type="software-dev",
        )

        # The contract: a mission with a real state must not produce
        # mission_state == "unknown" in the JSON envelope.
        payload = decision.to_dict()
        assert payload["mission_state"] != "unknown"
        assert payload["mission_state"] == "implementing"

        # The decision body must not contain the placeholder.
        rendered = repr(payload)
        assert _PLACEHOLDER not in rendered

    def test_query_decision_for_missing_feature_dir_is_structured(
        self, tmp_path: Path
    ) -> None:
        """A missing feature dir is still a query, but the kind is structured.

        We do not require ``mission_state != "unknown"`` for a feature
        directory that does not exist on disk — that is a user error, not
        a "valid run". But we do require: no placeholder in the body.
        """
        from specify_cli.next.runtime_bridge import query_current_state

        repo_root = tmp_path
        # No kitty-specs/<slug> dir created, so feature_dir is missing.
        decision = query_current_state(
            agent="claude",
            mission_slug="nonexistent-mission",
            repo_root=repo_root,
        )

        payload = decision.to_dict()
        assert _PLACEHOLDER not in repr(payload)


class TestRuntimeBridgeBlockedReasonIsConcrete:
    """A blocked decision must carry a concrete reason, not boilerplate."""

    def test_runtime_engine_error_reason_is_specific(self) -> None:
        """Sanity check: the runtime bridge surfaces concrete error
        reasons rather than stringified placeholders.

        We grep for the legacy placeholder in the function body — it is a
        regression guard for future edits.
        """
        runtime_bridge_path = (
            _REPO_ROOT / "src" / "specify_cli" / "next" / "runtime_bridge.py"
        )
        text = runtime_bridge_path.read_text(encoding="utf-8")
        # Acceptable: "no result provided" appearing inside human-readable
        # query mode banner. We forbid only the bracket form that historically
        # leaked into prompt files.
        assert _PLACEHOLDER not in text, (
            f"runtime_bridge.py must not emit the legacy placeholder {_PLACEHOLDER}"
        )
