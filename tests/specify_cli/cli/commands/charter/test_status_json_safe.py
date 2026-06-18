"""WP03 / FR-005 + FR-008a — ``charter status --json`` must be JSON-safe.

Two contracts under test on the read-only ``charter status`` surface:

1. **FR-005 (C2-b, live):** ``charter status --json`` previously raised
   ``TypeError: Object of type datetime is not JSON serializable`` when the
   bundle ``metadata.yaml`` carried an *unquoted* ISO datetime under the key the
   collector actually reads — ``timestamp_utc`` (or ``extracted_at``).
   ``YAML(typ="safe")`` parses an unquoted ISO datetime to a ``datetime``
   object, which then leaked into ``json.dumps(payload, ...)`` and crashed.

   ⚠️ **Fixture coordinates (squad-pedro):** the collector maps
   ``metadata.get("timestamp_utc") or metadata.get("extracted_at")`` onto the
   payload's ``last_sync`` field (``_status_collectors.py``). The crashing input
   key is therefore ``timestamp_utc`` — a fixture keyed on a literal
   ``last_sync`` would be IGNORED and the RED step would silently pass.

2. **FR-008a (pin):** C2-a (status side-effect-free) already landed
   (``f892894e2``). T022 pins it: the status read path invokes NO mutator
   (``ensure_charter_bundle_fresh`` / ``GlossaryEntityPageRenderer.generate_all``)
   so it cannot silently re-drift.

Captured-red evidence (live-evidence discipline)
-------------------------------------------------
Against unmodified ``_status_collectors.py`` the full ``charter status --json``
command path exits non-zero with the JSON error payload::

    {"error": "Object of type datetime is not JSON serializable",
     "result": "error", "success": false}

After the FR-005 fix the same fixture yields exit 0, valid JSON, and a
string-typed ``last_sync`` (F9 — not merely "didn't crash").
"""

from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

import specify_cli.cli.commands.charter as charter_pkg
from specify_cli.cli.commands.charter import charter_app

runner = CliRunner()

pytestmark = [pytest.mark.fast]

#: Realistic, production-shaped ISO timestamp written *unquoted* so
#: ``YAML(typ="safe")`` yields a ``datetime`` object (the crash trigger).
_UNQUOTED_ISO_TIMESTAMP = "2026-06-15T12:30:45.512874+00:00"


def _build_charter_bundle(repo_root: Path) -> None:
    """Seed a topology-true charter bundle with an unquoted ``timestamp_utc``.

    The bundle carries:
    * a compatible ``bundle_schema_version`` (so ``_assert_bundle_compatible``
      passes and the command reaches the serialization path);
    * an *unquoted* ISO datetime under ``timestamp_utc`` — the exact key the
      collector reads into ``last_sync`` — guaranteeing the datetime object
      reaches ``json.dumps`` on unmodified code.
    """
    charter_dir = repo_root / ".kittify" / "charter"
    charter_dir.mkdir(parents=True, exist_ok=True)
    (charter_dir / "charter.md").write_text("# Charter\n", encoding="utf-8")
    (charter_dir / "metadata.yaml").write_text(
        dedent(
            f"""\
            bundle_schema_version: 2
            charter_hash: "sha256:{'0' * 64}"
            timestamp_utc: {_UNQUOTED_ISO_TIMESTAMP}
            """
        ),
        encoding="utf-8",
    )
    for name in ("governance.yaml", "directives.yaml", "references.yaml"):
        (charter_dir / name).write_text("schema_version: '1'\n", encoding="utf-8")
    (repo_root / ".kittify" / "doctrine").mkdir(parents=True, exist_ok=True)


@pytest.fixture()
def charter_repo(tmp_path: Path) -> Path:
    """A project root with a charter bundle carrying an unquoted datetime."""
    _build_charter_bundle(tmp_path)
    return tmp_path


def _invoke_status_json(repo_root: Path) -> object:
    """Invoke ``charter status --json`` with the heavy collectors stubbed.

    Only the ``charter_sync`` sub-payload (which carries the datetime) is left
    real, so the datetime crash — and its fix — is the *sole* variable. The
    synthesis / org-layer / governance / freshness collectors are stubbed to
    deterministic JSON-safe dicts to avoid unrelated topology requirements.
    The serialization line under test (``json.dumps(payload, ...)`` in
    ``status.py``) is exercised end-to-end via the real CLI command.
    """
    with (
        patch.object(charter_pkg, "find_repo_root", return_value=repo_root),
        patch.object(
            charter_pkg, "_collect_synthesis_status", return_value={"stub": True}
        ),
        patch(
            "specify_cli.cli.commands.charter.status._collect_org_layer_status",
            return_value={"packs": [], "has_built_in": True},
        ),
        patch(
            "specify_cli.cli.commands.charter.status."
            "_collect_governance_reference_status",
            return_value={"available": True, "references": [], "warnings": []},
        ),
        patch("specify_cli.charter_freshness.compute_freshness") as compute_freshness,
    ):
        compute_freshness.return_value.to_dict.return_value = {}
        return runner.invoke(charter_app, ["status", "--json"], catch_exceptions=False)


# ---------------------------------------------------------------------------
# _normalize_last_sync unit branches (diff-coverage gap closeout — #2028)
# ---------------------------------------------------------------------------


class TestNormalizeLastSync:
    """Direct unit coverage of ``_normalize_last_sync`` branches."""

    def test_none_passes_through(self) -> None:
        """``None`` returns ``None`` unchanged (the ``value is None`` branch)."""
        from specify_cli.cli.commands.charter._status_collectors import (
            _normalize_last_sync,
        )

        assert _normalize_last_sync(None) is None

    def test_datetime_coerced_to_iso_string(self) -> None:
        """A ``datetime`` is coerced to its ISO 8601 string form."""
        from datetime import UTC, datetime

        from specify_cli.cli.commands.charter._status_collectors import (
            _normalize_last_sync,
        )

        value = datetime(2026, 6, 15, 12, 30, 45, tzinfo=UTC)
        assert _normalize_last_sync(value) == value.isoformat()

    def test_string_passes_through_as_str(self) -> None:
        """An already-string timestamp passes through via ``str(value)``."""
        from specify_cli.cli.commands.charter._status_collectors import (
            _normalize_last_sync,
        )

        assert _normalize_last_sync("2026-06-15T12:30:45+00:00") == (
            "2026-06-15T12:30:45+00:00"
        )


# ---------------------------------------------------------------------------
# T020 + T021 — datetime serialization
# ---------------------------------------------------------------------------


class TestCharterStatusJsonSafe:
    """FR-005: ``charter status --json`` survives an unquoted datetime."""

    def test_status_json_emits_string_last_sync(self, charter_repo: Path) -> None:
        """Exit 0, valid JSON, and ``last_sync`` serialized as a *string* (F9).

        T020 captured-red: on unmodified ``_status_collectors.py`` the command
        emits ``{"error": "Object of type datetime is not JSON serializable",
        ...}`` and exits 1. T021 makes this green by normalizing the datetime to
        an ISO string before it enters the payload.
        """
        result = _invoke_status_json(charter_repo)

        assert result.exit_code == 0, (
            "charter status --json should succeed on an unquoted-datetime "
            f"bundle; got exit {result.exit_code}:\n{result.stdout}"
        )

        payload = json.loads(result.stdout)
        assert payload["result"] == "success", payload

        last_sync = payload["charter_sync"]["last_sync"]
        assert isinstance(last_sync, str), (
            "last_sync must be a JSON-safe string (F9 — not merely "
            f"non-crashing); got {type(last_sync)!r}: {last_sync!r}"
        )
        # The normalized value must carry the original instant (ISO 8601).
        assert "2026-06-15T12:30:45" in last_sync, last_sync

    def test_full_status_payload_json_round_trips(self, charter_repo: Path) -> None:
        """The emitted JSON parses back to a dict with the charter_sync section."""
        result = _invoke_status_json(charter_repo)

        assert result.exit_code == 0, result.stdout
        reparsed = json.loads(result.stdout)
        assert isinstance(reparsed, dict)
        assert "charter_sync" in reparsed


# ---------------------------------------------------------------------------
# T022 — C2-a pin: status read path invokes no mutator (FR-008a / NFR-006)
# ---------------------------------------------------------------------------


class TestCharterStatusNoMutator:
    """FR-008a: pin the already-landed side-effect-free status read path.

    If a mutator (``ensure_charter_bundle_fresh`` / ``generate_all``) is
    reintroduced into ``_collect_charter_sync_status``, these tests fail — the
    monkeypatched mutators raise on invocation, so a clean run proves they were
    never called.
    """

    def test_collector_does_not_call_ensure_charter_bundle_fresh(
        self, charter_repo: Path
    ) -> None:
        from specify_cli.cli.commands.charter._status_collectors import (
            _collect_charter_sync_status,
        )

        def _boom(*_args: object, **_kwargs: object) -> object:
            raise AssertionError(
                "status read path must NOT call ensure_charter_bundle_fresh "
                "(C2-a / NFR-006 — read-only consumer)"
            )

        with patch("charter.sync.ensure_charter_bundle_fresh", _boom):
            result = _collect_charter_sync_status(charter_repo)

        assert result["available"] is True, result

    def test_collector_does_not_call_generate_all(self, charter_repo: Path) -> None:
        from specify_cli.cli.commands.charter._status_collectors import (
            _collect_charter_sync_status,
        )

        def _boom(*_args: object, **_kwargs: object) -> object:
            raise AssertionError(
                "status read path must NOT call "
                "GlossaryEntityPageRenderer.generate_all "
                "(C2-a / NFR-006 — read-only consumer)"
            )

        with patch(
            "glossary.entity_pages.GlossaryEntityPageRenderer.generate_all",
            _boom,
        ):
            result = _collect_charter_sync_status(charter_repo)

        assert result["available"] is True, result
