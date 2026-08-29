"""Focused tests for the WP06 (charter-sync-sonar-remediation) mechanical fixes.

Covers the non-mechanical slices called out in ``post-tasks-squad-findings.md``
(WP06 corrections) that need their own characterization/equivalence coverage
rather than being folded into an existing suite:

- S107 params-object for ``emit_token_usage_recorded`` (two-layer: the
  ``EventEmitter`` method in ``sync/emitter.py`` and the singleton wrapper
  in ``sync/events.py``), proving the bundled ``TokenUsageMetadata`` object
  produces the exact same event payload as the pre-refactor flat-kwargs call.
- S107 params-object for ``emit_wp_status_changed`` (``sync/events.py``),
  proving the keyword-only ``metadata=`` object call style threads through
  to the emitted event, including via the production SaaS fan-out chain
  that forwards ``**kwargs`` blindly (the ``metadata=`` object rides that
  passthrough as a single flat keyword), plus the guard rail that a former
  flat tail-field keyword (e.g. ``force=``) is now rejected.
- S5779 characterization for ``_ensure_dashboard_sync_daemon``'s
  ``intent_local_only`` branch: replacing ``raise AssertionError(...)``
  (caught by the surrounding ``except Exception``) with a direct
  ``logger.warning(...)`` must produce the identical observable outcome —
  same log message, no exception escaping, normal return.
- S6353 match-equivalence for ``migration_target_token``'s sanitizer regex:
  ``\\W`` compiled with ``re.ASCII`` must match exactly the same character
  set as the original explicit ``[^A-Za-z0-9_]`` (also ``re.ASCII``) it
  replaced, across ASCII allow-listed characters, ASCII punctuation, and
  non-ASCII (accented Latin, CJK, digits) input.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

from specify_cli.sync.daemon import DaemonStartOutcome
from specify_cli.sync.emitter import EventEmitter, TokenUsageMetadata
from specify_cli.sync.events import (
    WPStatusChangeMetadata,
    _ensure_dashboard_sync_daemon,
)
from specify_cli.sync.migrate_journal import migration_target_token


# ---------------------------------------------------------------------------
# S107 — emit_token_usage_recorded (two-layer params object)
# ---------------------------------------------------------------------------


class TestTokenUsageMetadataParamsObject:
    """``TokenUsageMetadata`` threads through EventEmitter unchanged."""

    def test_metadata_object_produces_same_payload_as_flat_kwargs_did(
        self, emitter: EventEmitter
    ) -> None:
        """Bundled metadata yields identical payload fields to the pre-refactor call."""
        cid = emitter.generate_causation_id()
        event = emitter.emit_token_usage_recorded(
            mission_id="01JTJ8M3Z3ZV4A6J3B1Q4JQ8RM",
            input_tokens=1200,
            output_tokens=300,
            total_tokens=1500,
            estimated_cost_usd=0.036,
            source="runtime-usage",
            metadata=TokenUsageMetadata(
                run_id="run-analytics-001",
                step_id="implement",
                wp_id="WP03",
                phase_name="implementation",
                actor={"actor_id": "codex", "actor_type": "llm"},
                provider="openai",
                model="gpt-5.4",
                causation_id=cid,
            ),
        )
        assert event is not None
        payload = event["payload"]
        assert payload["mission_id"] == "01JTJ8M3Z3ZV4A6J3B1Q4JQ8RM"
        assert payload["input_tokens"] == 1200
        assert payload["output_tokens"] == 300
        assert payload["total_tokens"] == 1500
        assert payload["estimated_cost_usd"] == 0.036
        assert payload["source"] == "runtime-usage"
        assert payload["run_id"] == "run-analytics-001"
        assert payload["step_id"] == "implement"
        assert payload["wp_id"] == "WP03"
        assert payload["phase_name"] == "implementation"
        assert payload["actor"] == {"actor_id": "codex", "actor_type": "llm"}
        assert payload["provider"] == "openai"
        assert payload["model"] == "gpt-5.4"
        assert event["causation_id"] == cid

    def test_omitted_metadata_defaults_to_required_fields_only(
        self, emitter: EventEmitter
    ) -> None:
        """No ``metadata=`` behaves like every optional field was ``None`` before."""
        event = emitter.emit_token_usage_recorded(
            mission_id="01JTJ8M3Z3ZV4A6J3B1Q4JQ8RM",
            input_tokens=10,
            output_tokens=5,
            total_tokens=15,
            estimated_cost_usd=0.001,
            source="runtime-usage",
        )
        assert event is not None
        payload = event["payload"]
        for optional_field in (
            "run_id",
            "step_id",
            "wp_id",
            "phase_name",
            "actor",
            "provider",
            "model",
        ):
            assert optional_field not in payload

    def test_events_wrapper_threads_metadata_through_to_emitter(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The singleton wrapper in ``sync/events.py`` forwards ``metadata`` unchanged."""
        from specify_cli.sync import events as events_mod

        mock_emitter = MagicMock()
        mock_emitter.emit_token_usage_recorded.return_value = {"event_id": "evt-1"}
        monkeypatch.setattr(events_mod, "get_emitter", lambda: mock_emitter)
        monkeypatch.setattr(
            events_mod, "_ensure_dashboard_sync_daemon_for_active_project", lambda **_: None
        )
        monkeypatch.setattr(events_mod, "_publish_event_via_sync_daemon", lambda *a, **k: None)
        monkeypatch.setattr(events_mod, "_request_dashboard_sync", lambda *a, **k: None)

        metadata = TokenUsageMetadata(run_id="run-1")
        events_mod.emit_token_usage_recorded(
            mission_id="m1",
            input_tokens=1,
            output_tokens=1,
            total_tokens=2,
            estimated_cost_usd=0.0,
            source="test",
            metadata=metadata,
        )

        mock_emitter.emit_token_usage_recorded.assert_called_once_with(
            mission_id="m1",
            input_tokens=1,
            output_tokens=1,
            total_tokens=2,
            estimated_cost_usd=0.0,
            source="test",
            metadata=metadata,
        )


# ---------------------------------------------------------------------------
# S107 — emit_wp_status_changed (optional-tail params object, legacy-kwarg shim)
# ---------------------------------------------------------------------------


class TestWPStatusChangeMetadataParamsObject:
    """``WPStatusChangeMetadata`` bundles the optional tail behind a single
    keyword-only ``metadata=`` parameter (mirrors ``emit_token_usage_recorded``'s
    ``TokenUsageMetadata`` shape)."""

    def test_metadata_object_call_style_produces_expected_payload(
        self, emitter: EventEmitter, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The ``metadata=`` object threads its fields through to the emitted payload."""
        from specify_cli.sync import events as events_mod

        monkeypatch.setattr(events_mod, "get_emitter", lambda: emitter)
        monkeypatch.setattr(
            events_mod, "_ensure_dashboard_sync_daemon_for_active_project", lambda **_: None
        )
        monkeypatch.setattr(events_mod, "_publish_event_via_sync_daemon", lambda *a, **k: None)
        monkeypatch.setattr(events_mod, "_request_dashboard_sync", lambda *a, **k: None)

        cid = emitter.generate_causation_id()
        event = events_mod.emit_wp_status_changed(
            "WP01",
            "planned",
            "in_progress",
            metadata=WPStatusChangeMetadata(
                force=True, reason="operator override", causation_id=cid
            ),
        )

        assert event is not None
        assert event["payload"]["force"] is True
        assert event["payload"]["reason"] == "operator override"
        assert event["causation_id"] == cid

    def test_kwargs_forwarding_chain_threads_metadata_object(
        self, emitter: EventEmitter, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The production ``**kwargs``-forwarding fan-out chain is unaffected.

        Mirrors how ``status/emit.py`` -> ``status/adapters.fire_saas_fanout``
        -> ``sync/__init__._saas_fanout_handler`` calls this function: the
        ``metadata=`` object arrives as a single flat keyword via a
        ``**kwargs`` passthrough, alongside the other flat keywords.
        """
        from specify_cli.sync import events as events_mod

        monkeypatch.setattr(events_mod, "get_emitter", lambda: emitter)
        monkeypatch.setattr(
            events_mod, "_ensure_dashboard_sync_daemon_for_active_project", lambda **_: None
        )
        monkeypatch.setattr(events_mod, "_publish_event_via_sync_daemon", lambda *a, **k: None)
        monkeypatch.setattr(events_mod, "_request_dashboard_sync", lambda *a, **k: None)

        def _saas_fanout_handler_shim(**kwargs: Any) -> None:
            events_mod.emit_wp_status_changed(**kwargs)

        _saas_fanout_handler_shim(
            wp_id="WP03",
            from_lane="planned",
            to_lane="in_progress",
            actor="user",
            metadata=WPStatusChangeMetadata(
                causation_id=emitter.generate_causation_id(),
                policy_metadata={"k": "v"},
                force=False,
                reason=None,
                review_ref=None,
                execution_mode=None,
                evidence=None,
                occurred_at="2026-08-10T20:00:00Z",
            ),
        )
        # Reaching here without a TypeError is the assertion: the forwarding
        # chain's kwargs calling convention is preserved.

    def test_unexpected_keyword_argument_raises(self, emitter: EventEmitter) -> None:
        from specify_cli.sync import events as events_mod

        with pytest.raises(TypeError, match="unexpected keyword argument"):
            events_mod.emit_wp_status_changed(
                "WP01", "planned", "in_progress", not_a_real_field="oops"
            )

    def test_individual_tail_field_keyword_now_rejected(self, emitter: EventEmitter) -> None:
        """A former flat tail-field keyword (e.g. ``force=``) is no longer
        accepted now that the ``**legacy_metadata_kwargs`` bag is removed;
        callers must bundle it into ``metadata=`` instead."""
        from specify_cli.sync import events as events_mod

        with pytest.raises(TypeError, match="unexpected keyword argument"):
            events_mod.emit_wp_status_changed(
                "WP01",
                "planned",
                "in_progress",
                force=True,
            )


# ---------------------------------------------------------------------------
# S5779 — _ensure_dashboard_sync_daemon intent_local_only characterization
# ---------------------------------------------------------------------------


class TestEnsureDashboardSyncDaemonIntentLocalOnly:
    """The unreachable ``intent_local_only`` branch logs and returns, never raises."""

    def _prime_reachable_state(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, skipped_reason: str
    ) -> Path:
        from specify_cli.sync import events as events_mod

        repo_root = tmp_path / "repo"
        (repo_root / ".kittify").mkdir(parents=True)

        monkeypatch.setattr(events_mod, "sync_active", lambda: True)

        token_manager = MagicMock()
        token_manager.is_authenticated = True
        monkeypatch.setattr(
            "specify_cli.auth.get_token_manager", lambda: token_manager
        )

        outcome = DaemonStartOutcome(started=False, skipped_reason=skipped_reason, pid=None)
        monkeypatch.setattr(
            "specify_cli.sync.daemon.ensure_sync_daemon_running", lambda **_: outcome
        )
        return repo_root

    def test_intent_local_only_logs_warning_and_does_not_raise(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        repo_root = self._prime_reachable_state(
            tmp_path, monkeypatch, skipped_reason="intent_local_only"
        )

        with caplog.at_level(logging.WARNING, logger="specify_cli.sync.events"):
            _ensure_dashboard_sync_daemon(repo_root)  # same observable outcome: normal return, no exception

        messages = [record.message for record in caplog.records]
        assert any(
            "intent_local_only reached in REMOTE_REQUIRED path" in message
            for message in messages
        )
        assert any(
            message.startswith("Could not ensure global sync daemon:")
            for message in messages
        )

    def test_other_skip_reasons_still_reach_their_own_branch(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Regression guard: the S5779 fix only touches the intent_local_only arm."""
        repo_root = self._prime_reachable_state(
            tmp_path, monkeypatch, skipped_reason="policy_manual"
        )

        with caplog.at_level(logging.DEBUG, logger="specify_cli.sync.events"):
            _ensure_dashboard_sync_daemon(repo_root)

        messages = [record.message for record in caplog.records]
        assert any("manual mode" in message for message in messages)
        assert not any("intent_local_only" in message for message in messages)


# ---------------------------------------------------------------------------
# S6353 — migration_target_token regex match-equivalence (\W + re.ASCII)
# ---------------------------------------------------------------------------


# The exact pattern migration_target_token replaced (S6353): an explicit
# ASCII allowlist compiled with re.ASCII. Kept here, private to the test
# module, purely as the equivalence oracle -- production code now uses
# the concise `\W` form.
_ORIGINAL_NON_IDENTIFIER_CHARS = re.compile(r"[^A-Za-z0-9_]", re.ASCII)


class TestMigrationTargetTokenRegexEquivalence:
    """``\\W`` + ``re.ASCII`` must sanitize identically to the original allowlist."""

    @pytest.mark.parametrize(
        "raw",
        [
            "plain-ascii-token",
            "under_score",
            "MixedCase123",
            "with spaces and\ttabs",
            "punctuation!@#$%^&*()",
            "café-équipe",
            "日本語トークン",
            "emoji-🎉-token",
            "٣٤٥",  # Arabic-Indic digits -- \w under Unicode default would match, ASCII must not
            "",
            "___",
            "a" * 200,
        ],
    )
    def test_matches_original_allowlist_pattern_for_every_case(self, raw: str) -> None:
        expected = _ORIGINAL_NON_IDENTIFIER_CHARS.sub("_", raw)
        actual = migration_target_token(raw)
        assert actual == expected
        assert actual.isascii()

    def test_ascii_word_characters_are_preserved(self) -> None:
        token = migration_target_token("abcXYZ_019")
        assert token == "abcXYZ_019"

    def test_non_ascii_folds_to_underscore_not_unicode_word_semantics(self) -> None:
        # Without re.ASCII, \W would treat "é" as a word character (\w) and
        # leave it untouched -- the exact accented-Latin leak this sanitizer
        # exists to prevent.
        token = migration_target_token("café")
        assert token == "caf_"
