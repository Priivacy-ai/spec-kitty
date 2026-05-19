"""Tests for ``specify_cli.doctrine.pack_validator``.

These tests build minimal, schema-valid artifact fixtures in ``tmp_path`` and
exercise :func:`validate_pack` against each of the documented error categories.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from specify_cli.doctrine.pack_validator import (
    ValidationResult,
    render_validation_result,
    validate_pack,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _write_directive(
    pack_dir: Path,
    *,
    artifact_id: str,
    filename: str | None = None,
    title: str = "Example",
    drop_title: bool = False,
) -> Path:
    """Write a minimal, schema-valid directive YAML file."""
    directives = pack_dir / "directives"
    directives.mkdir(parents=True, exist_ok=True)
    body_lines = [
        'schema_version: "1.0"',
        f"id: {artifact_id}",
    ]
    if not drop_title:
        body_lines.append(f"title: {title}")
    body_lines.extend(
        [
            "intent: A short description.",
            "enforcement: advisory",
        ]
    )
    name = filename or f"{artifact_id.lower()}.directive.yaml"
    path = directives / name
    path.write_text("\n".join(body_lines) + "\n", encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestValidatePack:
    def test_nonexistent_pack_dir(self, tmp_path: Path) -> None:
        result = validate_pack(tmp_path / "does-not-exist")
        assert result.ok is False
        assert len(result.errors) == 1
        assert "not found" in result.errors[0].message

    def test_empty_pack(self, tmp_path: Path) -> None:
        # A pack with no artifact files at all is valid.
        result = validate_pack(tmp_path)
        assert result.ok is True
        assert result.errors == []

    def test_valid_pack_single_type(self, tmp_path: Path) -> None:
        _write_directive(tmp_path, artifact_id="ACME-001")
        _write_directive(tmp_path, artifact_id="ACME-002")

        result = validate_pack(tmp_path)

        assert result.ok is True, result.errors
        assert result.errors == []

    def test_schema_violation(self, tmp_path: Path) -> None:
        _write_directive(
            tmp_path,
            artifact_id="ACME-003",
            drop_title=True,
        )

        result = validate_pack(tmp_path)

        assert result.ok is False
        assert any(
            issue.artifact_type == "directives" for issue in result.errors
        )

    def test_duplicate_id(self, tmp_path: Path) -> None:
        _write_directive(
            tmp_path,
            artifact_id="ACME-004",
            filename="first.directive.yaml",
        )
        _write_directive(
            tmp_path,
            artifact_id="ACME-004",
            filename="second.directive.yaml",
        )

        result = validate_pack(tmp_path)

        assert result.ok is False
        duplicate_errors = [
            e for e in result.errors if "duplicate id" in e.message
        ]
        assert len(duplicate_errors) == 1
        assert duplicate_errors[0].artifact_id == "ACME-004"

    def test_dangling_drg_edge(self, tmp_path: Path) -> None:
        # A pack with a DRG fragment that points at a URN nobody knows about.
        drg = tmp_path / "drg"
        drg.mkdir()
        (drg / "010-broken.graph.yaml").write_text(
            textwrap.dedent(
                """\
                schema_version: "1.0"
                generated_at: STATIC
                generated_by: test
                nodes: []
                edges:
                  - source: directive:does-not-exist
                    target: directive:also-missing
                    relation: requires
                """
            ),
            encoding="utf-8",
        )

        result = validate_pack(tmp_path)

        assert result.ok is False
        dangling = [
            e
            for e in result.errors
            if e.artifact_type == "drg" and "dangling" in e.message.lower()
        ]
        assert dangling, result.errors

    def test_drg_edge_resolves_against_pack_artifacts(
        self, tmp_path: Path
    ) -> None:
        # Edge URNs that resolve to the pack's own directives must NOT error.
        _write_directive(tmp_path, artifact_id="ACME-100")
        _write_directive(tmp_path, artifact_id="ACME-101")
        drg = tmp_path / "drg"
        drg.mkdir()
        (drg / "010-edges.graph.yaml").write_text(
            textwrap.dedent(
                """\
                schema_version: "1.0"
                generated_at: STATIC
                generated_by: test
                nodes: []
                edges:
                  - source: directive:ACME-100
                    target: directive:ACME-101
                    relation: requires
                """
            ),
            encoding="utf-8",
        )

        result = validate_pack(tmp_path)

        assert result.ok is True, result.errors

    def test_duplicate_drg_edge_advisory(self, tmp_path: Path) -> None:
        _write_directive(tmp_path, artifact_id="ACME-200")
        _write_directive(tmp_path, artifact_id="ACME-201")
        drg = tmp_path / "drg"
        drg.mkdir()
        edge_yaml = textwrap.dedent(
            """\
            schema_version: "1.0"
            generated_at: STATIC
            generated_by: test
            nodes: []
            edges:
              - source: directive:ACME-200
                target: directive:ACME-201
                relation: requires
            """
        )
        (drg / "010-a.graph.yaml").write_text(edge_yaml, encoding="utf-8")
        (drg / "020-b.graph.yaml").write_text(edge_yaml, encoding="utf-8")

        result = validate_pack(tmp_path)

        # The duplicate is advisory, not fatal.
        assert result.ok is True, result.errors
        advisories = [
            a for a in result.advisories if "duplicate edge" in a.message
        ]
        assert advisories

    def test_shipped_id_collision_advisory(self, tmp_path: Path) -> None:
        # Use a known shipped directive id so the advisory fires.  If shipped
        # doctrine is absent in this environment, the test simply has no
        # advisory to assert (validation should still pass) — keep the test
        # tolerant of stripped envs.
        _write_directive(tmp_path, artifact_id="DIRECTIVE_001")

        result = validate_pack(tmp_path)

        assert result.ok is True, result.errors
        # Advisory presence depends on whether shipped doctrine is on disk.
        for advisory in result.advisories:
            if advisory.artifact_id == "DIRECTIVE_001":
                assert "shipped" in advisory.message
                break

    def test_returns_validation_result_type(self, tmp_path: Path) -> None:
        result = validate_pack(tmp_path)
        assert isinstance(result, ValidationResult)
        # ``to_dict`` is part of the public surface used by the CLI.
        payload = result.to_dict()
        assert set(payload.keys()) == {"ok", "errors", "advisories"}


class TestRenderValidationResult:
    def test_json_output(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _write_directive(tmp_path, artifact_id="ACME-300")
        result = validate_pack(tmp_path)
        render_validation_result(result, json_output=True)
        captured = capsys.readouterr().out
        # The first non-empty line must be JSON.
        import json as _json

        payload = _json.loads(captured.strip())
        assert payload["ok"] is True

    def test_human_output_lists_errors_and_summary(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _write_directive(
            tmp_path, artifact_id="ACME-400", drop_title=True
        )
        result = validate_pack(tmp_path)
        render_validation_result(result, json_output=False)
        captured = capsys.readouterr().out
        assert "Error" in captured
        assert "Pack validation:" in captured
