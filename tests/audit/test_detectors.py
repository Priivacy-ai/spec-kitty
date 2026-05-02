"""Tests for src/specify_cli/audit/detectors.py (T010).

12 test cases covering:
- detect_legacy_keys (T001-T004)
- detect_forbidden_keys (T005-T006)
- detect_corrupt_jsonl (T007-T010)
- check_unknown_keys from shape_registry (T011-T012, included here for convenience)
"""

from __future__ import annotations

import json
from pathlib import Path

from specify_cli.audit.detectors import (
    FORBIDDEN_KEYS,
    LEGACY_KEYS,
    STATUS_EVENT_ONLY_LEGACY_KEYS,
    detect_corrupt_jsonl,
    detect_forbidden_keys,
    detect_legacy_keys,
)
from specify_cli.audit.models import Severity
from specify_cli.audit.shape_registry import check_unknown_keys


# ---------------------------------------------------------------------------
# detect_legacy_keys
# ---------------------------------------------------------------------------


class TestDetectLegacyKeys:
    def test_detect_legacy_keys_feature_slug(self) -> None:
        """A dict with 'feature_slug' produces one LEGACY_KEY finding."""
        findings = detect_legacy_keys({"feature_slug": "x"}, "meta.json")
        assert len(findings) == 1
        assert findings[0].code == "LEGACY_KEY"
        assert findings[0].severity == Severity.WARNING
        assert findings[0].artifact_path == "meta.json"
        assert "feature_slug" in (findings[0].detail or "")

    def test_detect_legacy_keys_multiple(self) -> None:
        """A dict with 3 legacy keys produces 3 findings."""
        obj = {
            "feature_slug": "a",
            "feature_number": 1,
            "mission_key": "k",
            "irrelevant": "v",
        }
        findings = detect_legacy_keys(obj, "meta.json")
        assert len(findings) == 3
        codes = {f.code for f in findings}
        assert codes == {"LEGACY_KEY"}

    def test_detect_legacy_keys_no_match(self) -> None:
        """A clean dict returns no findings."""
        findings = detect_legacy_keys({"mission_id": "abc", "friendly_name": "Foo"}, "meta.json")
        assert findings == []

    def test_detect_legacy_keys_extra_keys_event_rows(self) -> None:
        """work_package_id is flagged when extra_keys=STATUS_EVENT_ONLY_LEGACY_KEYS."""
        findings = detect_legacy_keys(
            {"work_package_id": "WP01"},
            "status.events.jsonl",
            extra_keys=STATUS_EVENT_ONLY_LEGACY_KEYS,
        )
        assert len(findings) == 1
        assert findings[0].code == "LEGACY_KEY"
        assert "work_package_id" in (findings[0].detail or "")

    def test_detect_legacy_keys_work_package_id_not_flagged_without_extra(self) -> None:
        """work_package_id is NOT flagged without extra_keys (correct for WP frontmatter)."""
        findings = detect_legacy_keys({"work_package_id": "WP01"}, "tasks/WP01.md")
        assert findings == []


# ---------------------------------------------------------------------------
# detect_forbidden_keys
# ---------------------------------------------------------------------------


class TestDetectForbiddenKeys:
    def test_detect_forbidden_keys_event_type(self) -> None:
        """'event_type' produces a FORBIDDEN_KEY finding."""
        findings = detect_forbidden_keys({"event_type": "Foo"}, "status.events.jsonl")
        assert len(findings) == 1
        assert findings[0].code == "FORBIDDEN_KEY"
        assert findings[0].severity == Severity.WARNING
        assert "event_type" in (findings[0].detail or "")

    def test_detect_forbidden_keys_event_name(self) -> None:
        """'event_name' produces a FORBIDDEN_KEY finding."""
        findings = detect_forbidden_keys({"event_name": "bar"}, "status.events.jsonl")
        assert len(findings) == 1
        assert findings[0].code == "FORBIDDEN_KEY"
        assert "event_name" in (findings[0].detail or "")

    def test_detect_forbidden_keys_clean_dict(self) -> None:
        """A dict with no forbidden keys returns no findings."""
        findings = detect_forbidden_keys({"actor": "claude", "to_lane": "claimed"}, "status.events.jsonl")
        assert findings == []


# ---------------------------------------------------------------------------
# detect_corrupt_jsonl
# ---------------------------------------------------------------------------


class TestDetectCorruptJsonl:
    def test_detect_corrupt_jsonl_valid_file(self, tmp_path: Path) -> None:
        """A file with all valid JSONL lines returns no findings."""
        f = tmp_path / "events.jsonl"
        f.write_text(
            json.dumps({"actor": "claude", "to_lane": "claimed"}) + "\n"
            + json.dumps({"actor": "human", "to_lane": "approved"}) + "\n",
            encoding="utf-8",
        )
        findings = detect_corrupt_jsonl(f, "status.events.jsonl")
        assert findings == []

    def test_detect_corrupt_jsonl_corrupt_line(self, tmp_path: Path) -> None:
        """One bad line produces exactly one CORRUPT_JSONL finding with correct line number."""
        f = tmp_path / "events.jsonl"
        f.write_text(
            json.dumps({"actor": "claude"}) + "\n"
            "not valid json\n"
            + json.dumps({"actor": "human"}) + "\n",
            encoding="utf-8",
        )
        findings = detect_corrupt_jsonl(f, "status.events.jsonl")
        assert len(findings) == 1
        assert findings[0].code == "CORRUPT_JSONL"
        assert findings[0].severity == Severity.ERROR
        # Line 2 is the corrupt line
        assert "line 2" in (findings[0].detail or "")

    def test_detect_corrupt_jsonl_stops_at_first_corrupt(self, tmp_path: Path) -> None:
        """Two corrupt lines: only the first is reported (stop-at-first semantics)."""
        f = tmp_path / "events.jsonl"
        f.write_text(
            "bad json line\n"
            "also bad\n",
            encoding="utf-8",
        )
        findings = detect_corrupt_jsonl(f, "status.events.jsonl")
        # Must return exactly ONE finding regardless of how many bad lines exist.
        assert len(findings) == 1
        assert "line 1" in (findings[0].detail or "")

    def test_detect_corrupt_jsonl_blank_lines_ignored(self, tmp_path: Path) -> None:
        """Blank / whitespace-only lines are skipped silently."""
        f = tmp_path / "events.jsonl"
        f.write_text(
            "\n"
            "   \n"
            + json.dumps({"ok": True}) + "\n"
            "\n",
            encoding="utf-8",
        )
        findings = detect_corrupt_jsonl(f, "status.events.jsonl")
        assert findings == []

    def test_detect_corrupt_jsonl_nonexistent_file(self, tmp_path: Path) -> None:
        """A missing file returns an empty list (not an exception)."""
        missing = tmp_path / "does_not_exist.jsonl"
        findings = detect_corrupt_jsonl(missing, "status.events.jsonl")
        assert findings == []


# ---------------------------------------------------------------------------
# check_unknown_keys (from shape_registry)
# T011–T012
# ---------------------------------------------------------------------------


class TestCheckUnknownKeys:
    def test_check_unknown_keys_known_key(self) -> None:
        """A key that is in the known set produces no findings."""
        findings = check_unknown_keys("meta.json", {"mission_id": "abc"}, "meta.json")
        assert findings == []

    def test_check_unknown_keys_unknown_key(self) -> None:
        """An unrecognised key that is not legacy or forbidden produces an UNKNOWN_SHAPE finding."""
        findings = check_unknown_keys(
            "meta.json",
            {"totally_new_field": "value"},
            "meta.json",
        )
        assert len(findings) == 1
        assert findings[0].code == "UNKNOWN_SHAPE"
        assert findings[0].severity == Severity.INFO
        assert "totally_new_field" in (findings[0].detail or "")

    def test_check_unknown_keys_legacy_key_not_unknown(self) -> None:
        """A legacy key present in the dict does NOT produce an UNKNOWN_SHAPE finding.

        The legacy key is covered by detect_legacy_keys(); check_unknown_keys()
        should not double-report it as UNKNOWN_SHAPE.
        """
        # Pick any legacy key
        legacy_key = next(iter(LEGACY_KEYS))
        findings = check_unknown_keys("meta.json", {legacy_key: "x"}, "meta.json")
        # Must not contain UNKNOWN_SHAPE for this key
        unknown_findings = [f for f in findings if f.code == "UNKNOWN_SHAPE"]
        assert unknown_findings == []

    def test_check_unknown_keys_forbidden_key_not_unknown(self) -> None:
        """A forbidden key present does NOT produce an UNKNOWN_SHAPE finding either."""
        forbidden_key = next(iter(FORBIDDEN_KEYS))
        findings = check_unknown_keys("meta.json", {forbidden_key: "x"}, "meta.json")
        unknown_findings = [f for f in findings if f.code == "UNKNOWN_SHAPE"]
        assert unknown_findings == []

    def test_check_unknown_keys_unregistered_artifact_type(self) -> None:
        """An artifact type not in the registry returns empty (not an error)."""
        findings = check_unknown_keys("some_new_artifact", {"anything": "x"}, "some_file")
        assert findings == []
