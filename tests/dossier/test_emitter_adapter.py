"""Tests for the dossier emitter adapter (inversion of dossier→sync).

Exercises the real registration path end-to-end (no patching of
fire_dossier_event itself) so that an unregistered adapter cannot
silently pass these tests.
"""

from __future__ import annotations

import pytest

from specify_cli.dossier import emitter_adapter
from specify_cli.dossier.emitter_adapter import (
    fire_dossier_event,
    register_dossier_emitter,
    reset_dossier_emitter,
)
from specify_cli.dossier.events import emit_artifact_indexed

VALID_HASH = "a" * 64


@pytest.fixture(autouse=True)
def _isolate_registration() -> None:
    """Reset the module-level registration before and after each test."""
    reset_dossier_emitter()
    yield
    reset_dossier_emitter()


class TestFireDossierEventDirect:
    """Direct tests of fire_dossier_event against a registered callable."""

    def test_no_emitter_registered_returns_none(self) -> None:
        result = fire_dossier_event(
            event_type="X",
            aggregate_id="agg",
            aggregate_type="MissionDossier",
            payload={"k": "v"},
        )
        assert result is None

    def test_registered_emitter_receives_kwargs_and_routes_return(self) -> None:
        captured: list[dict] = []

        def fake_emitter(**kwargs: object) -> dict:
            captured.append(dict(kwargs))
            return {"event_id": "e-1", **kwargs}

        register_dossier_emitter(fake_emitter)
        result = fire_dossier_event(
            event_type="MissionDossierArtifactIndexed",
            aggregate_id="042:input.spec",
            aggregate_type="MissionDossier",
            payload={"mission_slug": "042"},
        )

        assert result is not None
        assert result["event_id"] == "e-1"
        assert result["event_type"] == "MissionDossierArtifactIndexed"
        assert len(captured) == 1
        assert captured[0]["aggregate_type"] == "MissionDossier"

    def test_emitter_exception_returns_none_does_not_raise(self) -> None:
        def boom(**kwargs: object) -> dict:
            raise RuntimeError("emitter blew up")

        register_dossier_emitter(boom)
        result = fire_dossier_event(
            event_type="X",
            aggregate_id="agg",
            aggregate_type="MissionDossier",
            payload={},
        )
        assert result is None

    def test_register_replaces_existing_emitter(self) -> None:
        first_calls: list[str] = []
        second_calls: list[str] = []

        def first(**kwargs: object) -> dict:
            first_calls.append("called")
            return {"who": "first"}

        def second(**kwargs: object) -> dict:
            second_calls.append("called")
            return {"who": "second"}

        register_dossier_emitter(first)
        register_dossier_emitter(second)

        fire_dossier_event(
            event_type="X",
            aggregate_id="a",
            aggregate_type="MissionDossier",
            payload={},
        )

        assert first_calls == []
        assert second_calls == ["called"]


class TestEmitArtifactIndexedThroughAdapter:
    """End-to-end: emit_artifact_indexed must route through the adapter.

    This proves that the adapter wiring inside dossier/events.py is real,
    without patching ``fire_dossier_event`` itself. If a future refactor
    bypasses the adapter, this test fails loudly.
    """

    def test_no_emitter_registered_drops_silently(self) -> None:
        # Adapter cleared by autouse fixture
        assert emitter_adapter._emitter is None

        result = emit_artifact_indexed(
            mission_slug="042-feat",
            artifact_key="input.spec",
            artifact_class="input",
            relative_path="spec.md",
            content_hash_sha256=VALID_HASH,
            size_bytes=100,
            required_status="optional",
        )
        assert result is None  # silent drop is correct behavior

    def test_registered_emitter_receives_correctly_shaped_event(self) -> None:
        captured: list[dict] = []

        def fake_emitter(**kwargs: object) -> dict:
            captured.append(dict(kwargs))
            return {"event_id": "e-2", "event_type": kwargs["event_type"]}

        register_dossier_emitter(fake_emitter)

        result = emit_artifact_indexed(
            mission_slug="042-feat",
            artifact_key="input.spec",
            artifact_class="input",
            relative_path="spec.md",
            content_hash_sha256=VALID_HASH,
            size_bytes=100,
            required_status="required",
        )

        assert result is not None
        assert result["event_id"] == "e-2"
        assert len(captured) == 1
        call = captured[0]
        assert call["event_type"] == "MissionDossierArtifactIndexed"
        assert call["aggregate_id"] == "042-feat:input.spec"
        assert call["aggregate_type"] == "MissionDossier"
        payload = call["payload"]
        assert payload["mission_slug"] == "042-feat"
        assert payload["artifact_key"] == "input.spec"
