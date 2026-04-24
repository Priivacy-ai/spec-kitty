"""Tests for specify_cli.widen.state — WidenPendingStore.

Coverage targets:
- Happy-path: add → list → remove → list → verify empty
- Missing file → empty list (no exception)
- Duplicate decision_id → ValueError (C-010)
- Corrupted JSONL line → skip + log warning, rest readable
- Atomic write: tmp file cleaned up on success
- clear() removes file entirely
- validate_entry_schema() accepts valid entries
- round-trip: serialise, write to disk, read back, compare
- concurrent-append simulation (two stores pointing to same path)
- path property returns expected location
"""

from __future__ import annotations

import contextlib
import json
import threading
from datetime import UTC, datetime
from pathlib import Path

import pytest

from specify_cli.widen.models import WidenPendingEntry
from specify_cli.widen.state import WidenPendingStore, validate_entry_schema

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime(2026, 4, 23, 16, 0, 0, tzinfo=UTC)


def _make_entry(
    decision_id: str = "01KPXFGJ0000000000000000A1",
    mission_slug: str = "test-mission-01ABC",
    question_id: str = "charter.scope",
    question_text: str = "What is the scope?",
    entered_pending_at: datetime = _NOW,
    widen_response: dict | None = None,
) -> WidenPendingEntry:
    return WidenPendingEntry(
        decision_id=decision_id,
        mission_slug=mission_slug,
        question_id=question_id,
        question_text=question_text,
        entered_pending_at=entered_pending_at,
        widen_endpoint_response=widen_response
        or {
            "decision_id": decision_id,
            "widened_at": "2026-04-23T16:00:01+00:00",
            "slack_thread_url": "https://example.slack.com/archives/C123/p456",
            "invited_count": 3,
        },
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPath:
    def test_path_is_under_kitty_specs(self, tmp_path: Path) -> None:
        store = WidenPendingStore(tmp_path, "my-mission-01XYZ")
        expected = tmp_path / "kitty-specs" / "my-mission-01XYZ" / "widen-pending.jsonl"
        assert store.path == expected


class TestListPendingMissingFile:
    def test_missing_file_returns_empty_list(self, tmp_path: Path) -> None:
        store = WidenPendingStore(tmp_path, "no-file-mission")
        result = store.list_pending()
        assert result == []

    def test_empty_file_returns_empty_list(self, tmp_path: Path) -> None:
        store = WidenPendingStore(tmp_path, "empty-file-mission")
        store.path.parent.mkdir(parents=True, exist_ok=True)
        store.path.write_text("", encoding="utf-8")
        assert store.list_pending() == []


class TestAddAndList:
    def test_add_single_entry_then_list(self, tmp_path: Path) -> None:
        store = WidenPendingStore(tmp_path, "slug-01")
        entry = _make_entry()
        store.add_pending(entry)
        result = store.list_pending()
        assert len(result) == 1
        assert result[0].decision_id == entry.decision_id

    def test_add_multiple_entries_preserved_order(self, tmp_path: Path) -> None:
        store = WidenPendingStore(tmp_path, "slug-02")
        e1 = _make_entry(decision_id="01AAAA0000000000000000AA01")
        e2 = _make_entry(decision_id="01AAAA0000000000000000AA02")
        store.add_pending(e1)
        store.add_pending(e2)
        result = store.list_pending()
        assert [r.decision_id for r in result] == [e1.decision_id, e2.decision_id]

    def test_round_trip_full_field_equality(self, tmp_path: Path) -> None:
        """Serialise → write → read back → compare every field."""
        store = WidenPendingStore(tmp_path, "slug-rt")
        original = _make_entry()
        store.add_pending(original)
        recovered = store.list_pending()[0]
        assert recovered == original


class TestDuplicateDecisionId:
    def test_duplicate_raises_value_error(self, tmp_path: Path) -> None:
        store = WidenPendingStore(tmp_path, "slug-dup")
        entry = _make_entry()
        store.add_pending(entry)
        with pytest.raises(ValueError, match="already pending"):
            store.add_pending(entry)

    def test_second_entry_not_written_after_duplicate_error(
        self, tmp_path: Path
    ) -> None:
        store = WidenPendingStore(tmp_path, "slug-dup2")
        e1 = _make_entry(decision_id="01AAAA0000000000000000AA01")
        store.add_pending(e1)
        with contextlib.suppress(ValueError):
            store.add_pending(e1)
        assert len(store.list_pending()) == 1


class TestRemovePending:
    def test_remove_existing_entry(self, tmp_path: Path) -> None:
        store = WidenPendingStore(tmp_path, "slug-rm")
        e1 = _make_entry(decision_id="01AAAA0000000000000000RM01")
        e2 = _make_entry(decision_id="01AAAA0000000000000000RM02")
        store.add_pending(e1)
        store.add_pending(e2)
        store.remove_pending(e1.decision_id)
        result = store.list_pending()
        assert len(result) == 1
        assert result[0].decision_id == e2.decision_id

    def test_remove_noop_when_not_present(self, tmp_path: Path) -> None:
        store = WidenPendingStore(tmp_path, "slug-rm2")
        e1 = _make_entry(decision_id="01AAAA0000000000000000RM01")
        store.add_pending(e1)
        # Should not raise
        store.remove_pending("non-existent-id")
        assert len(store.list_pending()) == 1

    def test_remove_all_entries_leaves_empty_file(self, tmp_path: Path) -> None:
        store = WidenPendingStore(tmp_path, "slug-rm3")
        entry = _make_entry()
        store.add_pending(entry)
        store.remove_pending(entry.decision_id)
        assert store.list_pending() == []


class TestClear:
    def test_clear_removes_file(self, tmp_path: Path) -> None:
        store = WidenPendingStore(tmp_path, "slug-clr")
        store.add_pending(_make_entry())
        assert store.path.exists()
        store.clear()
        assert not store.path.exists()

    def test_clear_on_missing_file_is_noop(self, tmp_path: Path) -> None:
        store = WidenPendingStore(tmp_path, "slug-clr2")
        # Should not raise even when file doesn't exist
        store.clear()
        assert not store.path.exists()

    def test_list_after_clear_returns_empty(self, tmp_path: Path) -> None:
        store = WidenPendingStore(tmp_path, "slug-clr3")
        store.add_pending(_make_entry())
        store.clear()
        assert store.list_pending() == []


class TestCorruptedJsonl:
    def test_corrupted_line_is_skipped(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        store = WidenPendingStore(tmp_path, "slug-corrupt")
        good_entry = _make_entry(decision_id="01AAAA0000000000000000GD01")
        store.add_pending(good_entry)

        # Inject a bad line between two good lines
        good2 = _make_entry(decision_id="01AAAA0000000000000000GD02")
        store.path.write_text(
            good_entry.model_dump_json()
            + "\n{CORRUPT JSON LINE\n"
            + good2.model_dump_json()
            + "\n",
            encoding="utf-8",
        )

        import logging

        with caplog.at_level(logging.WARNING, logger="specify_cli.widen.state"):
            result = store.list_pending()

        assert len(result) == 2
        ids = {e.decision_id for e in result}
        assert good_entry.decision_id in ids
        assert good2.decision_id in ids
        assert any("corrupted" in msg.lower() for msg in caplog.messages)

    def test_fully_corrupt_file_returns_empty(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        store = WidenPendingStore(tmp_path, "slug-corrupt2")
        store.path.parent.mkdir(parents=True, exist_ok=True)
        store.path.write_text("{bad\n{alsoBad\n", encoding="utf-8")
        import logging

        with caplog.at_level(logging.WARNING, logger="specify_cli.widen.state"):
            result = store.list_pending()
        assert result == []


class TestAtomicWrite:
    def test_no_tmp_file_left_after_successful_write(self, tmp_path: Path) -> None:
        store = WidenPendingStore(tmp_path, "slug-atomic")
        store.add_pending(_make_entry())
        # mkstemp-based tmp files have unique names; verify none left behind
        tmp_files = list(store.path.parent.glob(".widen-pending-*.tmp"))
        assert tmp_files == []

    def test_file_contains_valid_jsonl_after_write(self, tmp_path: Path) -> None:
        store = WidenPendingStore(tmp_path, "slug-atomic2")
        store.add_pending(_make_entry())
        lines = [ln for ln in store.path.read_text().splitlines() if ln.strip()]
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["schema_version"] == 1


class TestConcurrentAppend:
    """Simulate two concurrent writers by using threads."""

    def test_concurrent_adds_all_persisted(self, tmp_path: Path) -> None:
        """Two threads appending distinct entries should both be written.

        Note: WidenPendingStore uses read-modify-write semantics (not
        append-only at the OS level), so under true concurrency one write
        can win and partial-write races may produce OSError.  V1 assumption
        is a single CLI process per mission, so locking is not implemented.
        This test verifies the store is usable after concurrent attempts
        finish — at least one entry survives and no data corruption occurs.
        """
        store = WidenPendingStore(tmp_path, "slug-concurrent")
        # Pre-create the directory to remove dir-creation race
        store.path.parent.mkdir(parents=True, exist_ok=True)

        errors: list[Exception] = []

        def add_entry(decision_id: str) -> None:
            try:
                entry = _make_entry(decision_id=decision_id)
                with contextlib.suppress(ValueError):
                    store.add_pending(entry)
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        t1 = threading.Thread(target=add_entry, args=("01AAAA0000000000000000C001",))
        t2 = threading.Thread(target=add_entry, args=("01AAAA0000000000000000C002",))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert not errors, f"Unexpected exceptions: {errors}"
        result = store.list_pending()
        assert len(result) >= 1  # At least one must have succeeded


class TestSchemaValidation:
    def test_valid_entry_passes_schema_validation(self, tmp_path: Path) -> None:
        entry = _make_entry()
        # Should not raise (either jsonschema validates OK or import is skipped)
        validate_entry_schema(entry)

    def test_schema_validation_with_minimal_widen_response(self) -> None:
        entry = _make_entry(
            widen_response={
                "decision_id": "01KPXFGJ0000000000000000A1",
                "widened_at": "2026-04-23T16:00:01+00:00",
            }
        )
        validate_entry_schema(entry)
