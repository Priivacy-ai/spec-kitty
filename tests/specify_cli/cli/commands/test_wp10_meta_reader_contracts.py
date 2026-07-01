"""WP10 — contract tests for the cluster-2a meta-reader conversions (FR-006c).

Each test asserts the OBSERVABLE RETURN VALUE of the converted site for the
(missing, malformed) behaviors present in the owned files — NOT the internal
call-graph (CT4 / DIRECTIVE_041).

Two distinct contracts:

* **Contract A** (``on_malformed="none"`` sites) — ``_read_mission_mid8`` and
  ``_delete_legacy_coordination_branch`` in ``cli/commands/mission_type.py``:
  a missing **or** malformed ``meta.json`` returns ``None`` from
  ``load_meta``, which the callers treat as an empty/absent result
  (``""`` / no-op).

* **Contract B** (``allow_missing=False, on_malformed="raise"`` site) —
  ``read_documentation_state`` in ``doc_analysis/doc_state.py``:
  a missing file raises ``FileNotFoundError``; a malformed file raises
  ``ValueError``.

Fixtures use production-shaped data: a real 26-char ULID mission_id and an
8-char mid8 (per testing-principles).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# Production-shaped identity constants (real 26-char ULID + 8-char mid8).
_MISSION_ID = "01KVRJ6PWPTENONTRACTTEST00"  # 26 chars
_MID8 = "01KVRJ6P"  # first 8 chars of mission_id
_MISSION_SLUG = f"topology-cleanup-{_MID8}"

pytestmark = [pytest.mark.unit, pytest.mark.fast]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_feature_dir(tmp_path: Path) -> Path:
    """Return a mission directory with a valid meta.json."""
    feature_dir = tmp_path / f"kitty-specs/{_MISSION_SLUG}"
    feature_dir.mkdir(parents=True)
    meta = {
        "slug": _MISSION_SLUG,
        "mission_slug": _MISSION_SLUG,
        "mission_id": _MISSION_ID,
        "mid8": _MID8,
        "friendly_name": "Topology Cleanup Test Mission",
        "mission_type": "software-dev",
        "target_branch": "feat/single-authority-topology-cleanup",
        "created_at": "2026-06-23T00:00:00+00:00",
    }
    (feature_dir / "meta.json").write_text(
        json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return feature_dir


# ---------------------------------------------------------------------------
# Contract A — on_malformed="none" sites (_read_mission_mid8,
#              _delete_legacy_coordination_branch)
# ---------------------------------------------------------------------------


class TestContractA_NoneOnMissingOrMalformed:
    """Contract A: missing or malformed meta.json → mid8 reader returns ''.

    These tests assert the observable RETURN VALUE of ``_read_mission_mid8``
    (and implicitly ``_delete_legacy_coordination_branch``) — not the
    load_meta call arguments.
    """

    def test_missing_meta_returns_empty_mid8(self, tmp_path: Path) -> None:
        """Contract A / missing: absent meta.json → _read_mission_mid8 returns ''.

        Negative control: a present meta.json with mission_id returns a
        non-empty mid8, proving the missing-file path is distinct.
        """
        from specify_cli.cli.commands.mission_type import _read_mission_mid8

        feature_dir = tmp_path / f"kitty-specs/{_MISSION_SLUG}"
        feature_dir.mkdir(parents=True)
        meta_path = feature_dir / "meta.json"
        # meta.json deliberately absent.

        # Observable contract: missing → returns empty string.
        assert _read_mission_mid8(meta_path) == ""

        # Negative control: present meta with mission_id → non-empty mid8.
        meta_path.write_text(
            json.dumps({"mission_id": _MISSION_ID}, indent=2) + "\n",
            encoding="utf-8",
        )
        assert _read_mission_mid8(meta_path) != ""

    def test_malformed_meta_returns_empty_mid8(self, tmp_path: Path) -> None:
        """Contract A / malformed: invalid JSON → _read_mission_mid8 returns ''.

        Negative control: valid JSON with mission_id returns a non-empty mid8.
        """
        from specify_cli.cli.commands.mission_type import _read_mission_mid8

        feature_dir = tmp_path / f"kitty-specs/{_MISSION_SLUG}"
        feature_dir.mkdir(parents=True)
        meta_path = feature_dir / "meta.json"
        meta_path.write_text("{ not: valid json }", encoding="utf-8")

        # Observable contract: malformed → returns empty string.
        assert _read_mission_mid8(meta_path) == ""

        # Negative control: valid JSON with mission_id → non-empty mid8.
        meta_path.write_text(
            json.dumps({"mission_id": _MISSION_ID}, indent=2) + "\n",
            encoding="utf-8",
        )
        assert _read_mission_mid8(meta_path) != ""


# ---------------------------------------------------------------------------
# Contract B — allow_missing=False, on_malformed="raise" site
#              (read_documentation_state)
# ---------------------------------------------------------------------------


class TestContractB_RaiseOnMissingOrMalformed:
    """Contract B: missing meta.json → FileNotFoundError; malformed → ValueError.

    These tests assert the observable raised exception of
    ``read_documentation_state`` — the only cluster-2a site that uses
    the strict raise-on-error contract.
    """

    def test_missing_meta_raises_file_not_found(self, tmp_path: Path) -> None:
        """Contract B / missing: absent meta.json → FileNotFoundError.

        Negative control: a present meta.json with mission_type=documentation
        returns a non-None state (proving the missing-file path is distinct).
        """
        from specify_cli.doc_analysis.doc_state import read_documentation_state

        meta_file = tmp_path / "meta.json"
        # meta.json deliberately absent.

        # Observable contract: missing → raises FileNotFoundError.
        with pytest.raises(FileNotFoundError):
            read_documentation_state(meta_file)

        # Negative control: documentation mission with state present → not None.
        meta_file.write_text(
            json.dumps(
                {
                    "slug": _MISSION_SLUG,
                    "mission_slug": _MISSION_SLUG,
                    "mission_id": _MISSION_ID,
                    "friendly_name": "Test",
                    "mission_type": "documentation",
                    "target_branch": "main",
                    "created_at": "2026-06-23T00:00:00+00:00",
                    "documentation_state": {
                        "iteration_mode": "initial",
                        "divio_types_selected": [],
                        "generators_configured": [],
                        "target_audience": "developers",
                        "last_audit_date": None,
                        "coverage_percentage": 0.0,
                    },
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        assert read_documentation_state(meta_file) is not None

    def test_malformed_meta_raises_value_error(self, tmp_path: Path) -> None:
        """Contract B / malformed: invalid JSON → ValueError.

        Negative control: valid JSON with mission_type=software-dev returns
        None (non-doc mission), confirming the malformed branch is distinct.
        """
        from specify_cli.doc_analysis.doc_state import read_documentation_state

        meta_file = tmp_path / "meta.json"
        meta_file.write_text("{ this is not json at all !!! }", encoding="utf-8")

        # Observable contract: malformed → raises ValueError.
        with pytest.raises(ValueError):
            read_documentation_state(meta_file)

        # Negative control: valid JSON, non-doc mission → None (no exception).
        meta_file.write_text(
            json.dumps(
                {
                    "slug": _MISSION_SLUG,
                    "mission_slug": _MISSION_SLUG,
                    "mission_id": _MISSION_ID,
                    "friendly_name": "Test",
                    "mission_type": "software-dev",
                    "target_branch": "main",
                    "created_at": "2026-06-23T00:00:00+00:00",
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        assert read_documentation_state(meta_file) is None
