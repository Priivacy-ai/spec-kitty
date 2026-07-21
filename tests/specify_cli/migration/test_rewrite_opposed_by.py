"""Tests for migration/rewrite_opposed_by.py — WP07 (T034-T037).

Covers the contract at
``kitty-specs/doctrine-tension-edges-01KY1WPC/contracts/migrate-opposed-by.md``:

- T037-1: ``--dry-run`` reports planned rewrites and writes nothing.
- T037-2: A real run rewrites ``opposed_by`` entries to ``in_tension_with``/
  ``rejects`` edges and removes the ``opposed_by`` key from the source YAML.
- T037-3: A second run against the now-migrated pack is a no-op (idempotent).
- T037-4: An unclassifiable entry produces the T036 diagnostic and a non-zero
  exit code, not a raw Pydantic traceback.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from typer.testing import CliRunner

from specify_cli.migration.rewrite_opposed_by import (
    RewriteResult,
    rewrite_opposed_by_pack,
)

pytestmark = [pytest.mark.unit, pytest.mark.fast]


# ---------------------------------------------------------------------------
# Fixtures — a small synthetic pack with a mix of tension-style and
# rejection-style opposed_by entries.
# ---------------------------------------------------------------------------


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _make_tension_pack(tmp_path: Path) -> Path:
    """Two peer directives that oppose each other (both real artifacts)."""
    pack_root = tmp_path / "pack"
    _write_yaml(
        pack_root / "directives" / "DIRECTIVE_A.directive.yaml",
        {
            "id": "DIRECTIVE_A",
            "title": "A",
            "opposed_by": [
                {
                    "type": "directive",
                    "id": "DIRECTIVE_B",
                    "reason": "A and B compete on the same decision.",
                }
            ],
        },
    )
    _write_yaml(
        pack_root / "directives" / "DIRECTIVE_B.directive.yaml",
        {"id": "DIRECTIVE_B", "title": "B"},
    )
    return pack_root


def _make_rejection_pack(tmp_path: Path) -> Path:
    """A paradigm rejects a bare anti-pattern label (no artifact of its own)."""
    pack_root = tmp_path / "pack"
    _write_yaml(
        pack_root / "paradigms" / "good-paradigm.paradigm.yaml",
        {
            "id": "good-paradigm",
            "title": "Good Paradigm",
            "opposed_by": [
                {
                    "type": "paradigm",
                    "id": "bad-practice",
                    "reason": "Bad Practice is the failure mode this rejects.",
                }
            ],
        },
    )
    return pack_root


def _make_mixed_pack(tmp_path: Path) -> Path:
    """One tension entry (peer exists) + one rejection entry (no peer)."""
    pack_root = tmp_path / "pack"
    _write_yaml(
        pack_root / "directives" / "DIRECTIVE_A.directive.yaml",
        {
            "id": "DIRECTIVE_A",
            "title": "A",
            "opposed_by": [
                {
                    "type": "directive",
                    "id": "DIRECTIVE_B",
                    "reason": "A and B compete.",
                }
            ],
        },
    )
    _write_yaml(
        pack_root / "directives" / "DIRECTIVE_B.directive.yaml",
        {"id": "DIRECTIVE_B", "title": "B"},
    )
    _write_yaml(
        pack_root / "paradigms" / "good-paradigm.paradigm.yaml",
        {
            "id": "good-paradigm",
            "title": "Good Paradigm",
            "opposed_by": [
                {
                    "type": "paradigm",
                    "id": "bad-practice",
                    "reason": "Bad Practice is rejected.",
                }
            ],
        },
    )
    return pack_root


def _make_unclassifiable_pack(tmp_path: Path) -> Path:
    """A target id exists under a DIFFERENT declared type -- ambiguous."""
    pack_root = tmp_path / "pack"
    _write_yaml(
        pack_root / "directives" / "DIRECTIVE_A.directive.yaml",
        {
            "id": "DIRECTIVE_A",
            "title": "A",
            "opposed_by": [
                {
                    "type": "paradigm",  # declared type
                    "id": "mystery-id",
                    "reason": "Ambiguous target.",
                }
            ],
        },
    )
    # "mystery-id" exists, but as a TACTIC, not the declared paradigm.
    _write_yaml(
        pack_root / "tactics" / "mystery-id.tactic.yaml",
        {"id": "mystery-id", "title": "Mystery"},
    )
    return pack_root


# ---------------------------------------------------------------------------
# T037-1: --dry-run writes nothing
# ---------------------------------------------------------------------------


class TestDryRun:
    def test_dry_run_reports_without_writing(self, tmp_path: Path) -> None:
        pack_root = _make_mixed_pack(tmp_path)
        directive_a = pack_root / "directives" / "DIRECTIVE_A.directive.yaml"
        paradigm = pack_root / "paradigms" / "good-paradigm.paradigm.yaml"
        before_a = directive_a.read_text(encoding="utf-8")
        before_p = paradigm.read_text(encoding="utf-8")

        result = rewrite_opposed_by_pack(pack_root, dry_run=True)

        assert len(result.rewritten) == 2
        assert not result.has_errors

        # Source files untouched.
        assert directive_a.read_text(encoding="utf-8") == before_a
        assert paradigm.read_text(encoding="utf-8") == before_p

        # No graph fragments written.
        assert not (pack_root / "directive.graph.yaml").exists()
        assert not (pack_root / "paradigm.graph.yaml").exists()

    def test_dry_run_classifies_tension_and_rejection_correctly(self, tmp_path: Path) -> None:
        pack_root = _make_mixed_pack(tmp_path)
        result = rewrite_opposed_by_pack(pack_root, dry_run=True)

        relations = {(r.source_id, r.target_id): r.relation for r in result.rewritten}
        assert relations[("DIRECTIVE_A", "DIRECTIVE_B")] == "in_tension_with"
        assert relations[("good-paradigm", "bad-practice")] == "rejects"


# ---------------------------------------------------------------------------
# T037-2: a real run rewrites correctly and removes opposed_by
# ---------------------------------------------------------------------------


class TestRealRun:
    def test_tension_entry_rewritten_and_opposed_by_removed(self, tmp_path: Path) -> None:
        pack_root = _make_tension_pack(tmp_path)
        result = rewrite_opposed_by_pack(pack_root, dry_run=False)

        assert len(result.rewritten) == 1
        entry = result.rewritten[0]
        assert entry.relation == "in_tension_with"
        assert not entry.created_anti_pattern_node

        # opposed_by removed from the source YAML.
        directive_a = pack_root / "directives" / "DIRECTIVE_A.directive.yaml"
        data = yaml.safe_load(directive_a.read_text(encoding="utf-8"))
        assert "opposed_by" not in data
        assert data["id"] == "DIRECTIVE_A"  # rest of the file preserved

        # Canonical single edge written, lex-smaller URN as source (C-002).
        graph_path = pack_root / "directive.graph.yaml"
        assert graph_path.exists()
        graph_data = yaml.safe_load(graph_path.read_text(encoding="utf-8"))
        edges = graph_data["edges"]
        assert len(edges) == 1
        assert edges[0]["source"] == "directive:DIRECTIVE_A"
        assert edges[0]["target"] == "directive:DIRECTIVE_B"
        assert edges[0]["relation"] == "in_tension_with"

    def test_rejection_entry_creates_anti_pattern_node_and_edge(self, tmp_path: Path) -> None:
        pack_root = _make_rejection_pack(tmp_path)
        result = rewrite_opposed_by_pack(pack_root, dry_run=False)

        assert len(result.rewritten) == 1
        entry = result.rewritten[0]
        assert entry.relation == "rejects"
        assert entry.created_anti_pattern_node

        paradigm = pack_root / "paradigms" / "good-paradigm.paradigm.yaml"
        data = yaml.safe_load(paradigm.read_text(encoding="utf-8"))
        assert "opposed_by" not in data

        graph_path = pack_root / "paradigm.graph.yaml"
        graph_data = yaml.safe_load(graph_path.read_text(encoding="utf-8"))
        anti_nodes = [n for n in graph_data["nodes"] if n["kind"] == "anti_pattern"]
        assert len(anti_nodes) == 1
        assert anti_nodes[0]["urn"] == "anti_pattern:bad-practice"

        edges = graph_data["edges"]
        assert len(edges) == 1
        assert edges[0]["source"] == "paradigm:good-paradigm"
        assert edges[0]["target"] == "anti_pattern:bad-practice"
        assert edges[0]["relation"] == "rejects"


# ---------------------------------------------------------------------------
# T037-3: idempotency -- second run against real output is a no-op
# ---------------------------------------------------------------------------


class TestIdempotency:
    def test_second_run_is_noop(self, tmp_path: Path) -> None:
        pack_root = _make_mixed_pack(tmp_path)

        first = rewrite_opposed_by_pack(pack_root, dry_run=False)
        assert len(first.rewritten) == 2

        directive_graph_after_first = (pack_root / "directive.graph.yaml").read_text(
            encoding="utf-8"
        )
        paradigm_graph_after_first = (pack_root / "paradigm.graph.yaml").read_text(
            encoding="utf-8"
        )

        second = rewrite_opposed_by_pack(pack_root, dry_run=False)

        assert second.rewritten == []
        assert not second.has_errors

        # Graph fragments are byte-identical -- no duplicate edges/nodes appended.
        assert (
            pack_root / "directive.graph.yaml"
        ).read_text(encoding="utf-8") == directive_graph_after_first
        assert (
            pack_root / "paradigm.graph.yaml"
        ).read_text(encoding="utf-8") == paradigm_graph_after_first

    def test_dry_run_after_real_run_reports_nothing_pending(self, tmp_path: Path) -> None:
        pack_root = _make_tension_pack(tmp_path)
        rewrite_opposed_by_pack(pack_root, dry_run=False)

        result = rewrite_opposed_by_pack(pack_root, dry_run=True)
        assert result.rewritten == []
        assert not result.has_errors


# ---------------------------------------------------------------------------
# T037-4: unclassifiable entry -> diagnostic, not a crash
# ---------------------------------------------------------------------------


class TestUnclassifiable:
    def test_ambiguous_type_mismatch_is_unclassifiable(self, tmp_path: Path) -> None:
        pack_root = _make_unclassifiable_pack(tmp_path)

        # Must not raise -- returns a structured result.
        result: RewriteResult = rewrite_opposed_by_pack(pack_root, dry_run=False)

        assert result.has_errors
        assert len(result.unclassifiable) == 1
        entry = result.unclassifiable[0]
        assert entry.source_id == "DIRECTIVE_A"
        assert entry.target_id == "mystery-id"
        assert "mystery-id" in entry.message
        assert "ambiguous" in entry.message.lower()

        # Nothing rewritten, and the source file's opposed_by is left intact
        # (no partial/lossy migration of a file with an unresolved entry).
        assert result.rewritten == []
        directive_a = pack_root / "directives" / "DIRECTIVE_A.directive.yaml"
        data = yaml.safe_load(directive_a.read_text(encoding="utf-8"))
        assert "opposed_by" in data

    def test_malformed_entry_missing_id_is_unclassifiable_not_a_crash(
        self, tmp_path: Path
    ) -> None:
        pack_root = tmp_path / "pack"
        _write_yaml(
            pack_root / "directives" / "DIRECTIVE_A.directive.yaml",
            {
                "id": "DIRECTIVE_A",
                "opposed_by": [{"type": "directive", "reason": "no id given"}],
            },
        )

        result = rewrite_opposed_by_pack(pack_root, dry_run=False)

        assert result.has_errors
        assert len(result.unclassifiable) == 1
        assert "invalid or missing type/id" in result.unclassifiable[0].message

    def test_cli_exits_nonzero_with_diagnostic_not_traceback(self, tmp_path: Path) -> None:
        from specify_cli import app

        pack_root = _make_unclassifiable_pack(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            app, ["migrate", "rewrite-opposed-by", "--pack", str(pack_root)]
        )

        assert result.exit_code == 1
        # No raw Pydantic ValidationError traceback leaks to the operator.
        assert "ValidationError" not in (result.stdout or "")
        assert "Traceback" not in (result.stdout or "")
        assert "ambiguous" in (result.stdout or "").lower()

    def test_cli_dry_run_json_reports_rewrites(self, tmp_path: Path) -> None:
        from specify_cli import app

        pack_root = _make_tension_pack(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            app,
            ["migrate", "rewrite-opposed-by", "--pack", str(pack_root), "--dry-run", "--json"],
        )

        assert result.exit_code == 0
        assert "in_tension_with" in result.stdout
        assert not (pack_root / "directive.graph.yaml").exists()
