"""Tests for ``specify_cli.doctrine.pack_validator``.

These tests build minimal, schema-valid artifact fixtures in ``tmp_path`` and
exercise :func:`validate_pack` against each of the documented error categories.
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest
from ruamel.yaml import YAML

from specify_cli.doctrine.pack_validator import (
    ValidationResult,
    _check_profile_skipped_diagnostics,
    render_validation_result,
    validate_pack,
)

_yaml = YAML(typ="safe")
_yaml.default_flow_style = False


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


pytestmark = [pytest.mark.unit, pytest.mark.fast]

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


def _write_asset_manifest(
    pack_dir: Path,
    *,
    artifact_id: str | None,
    mime: str | None = "image/png",
    path_value: str | None = "branding/acme-logo.png",
    title: str | None = "Acme brand logo (PNG)",
    filename: str | None = None,
    drop_id: bool = False,
    subdir: str | None = None,
) -> Path:
    """Write a ``*.asset.yaml`` sidecar manifest under ``pack_dir/assets/``.

    Realistic, production-shaped defaults (a real PNG-shaped manifest) —
    callers override individual fields to exercise a single failure mode.

    ``subdir``, when given, nests the manifest one directory below
    ``assets/`` (e.g. ``assets/<subdir>/x.asset.yaml``) — the ADR-mandated
    org-pack manifest layout (FR-003) that ``AssetRepository`` already
    recurses into.
    """
    assets = pack_dir / "assets" / subdir if subdir else pack_dir / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    payload: dict[str, str] = {}
    if not drop_id and artifact_id is not None:
        payload["id"] = artifact_id
    if mime is not None:
        payload["mime"] = mime
    if path_value is not None:
        payload["path"] = path_value
    if title is not None:
        payload["title"] = title
    name = filename or f"{(artifact_id or 'manifest').lower()}.asset.yaml"
    manifest_path = assets / name
    _yaml.dump(payload, manifest_path)
    return manifest_path


def _write_agent_profile_yaml(
    pack_dir: Path,
    *,
    filename: str,
    content: str,
) -> Path:
    """Write a raw ``*.agent.yaml`` file under ``pack_dir/agent_profiles/``.

    Takes a pre-formatted YAML string (rather than a dict payload, unlike the
    other ``_write_*`` helpers here) so callers can author fixtures whose
    exact on-disk shape matters (e.g. the deprecated scalar ``role:`` field,
    which a dict-based writer using ``roles:`` could not represent).
    """
    agent_profiles = pack_dir / "agent_profiles"
    agent_profiles.mkdir(parents=True, exist_ok=True)
    path = agent_profiles / filename
    path.write_text(content, encoding="utf-8")
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

    def test_drg_fragment_stray_top_level_key_reports_structured_issue(
        self, tmp_path: Path
    ) -> None:
        # A DRG fragment declaring a top-level key ``DRGGraph`` does not define
        # raises ``DRGGraphSchemaError`` at the load boundary (T009, NFR-006).
        # ``validate_pack`` must surface this as a structured ``ValidationIssue``
        # (category ``schema_invalid``) rather than let the exception escape as
        # an uncaught traceback (#3062).
        drg = tmp_path / "drg"
        drg.mkdir()
        (drg / "010-stray-key.graph.yaml").write_text(
            textwrap.dedent(
                """\
                schema_version: "1.0"
                generated_at: STATIC
                generated_by: test
                nodes: []
                edges: []
                not_a_real_field: surprise
                """
            ),
            encoding="utf-8",
        )

        result = validate_pack(tmp_path)

        assert result.ok is False
        schema_errors = [
            e
            for e in result.errors
            if e.artifact_type == "drg" and e.category == "schema_invalid"
        ]
        assert schema_errors, result.errors
        assert "not_a_real_field" in schema_errors[0].message
        assert schema_errors[0].file == str(drg / "010-stray-key.graph.yaml")

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

    def test_built_in_id_collision_advisory(self, tmp_path: Path) -> None:
        # Use a known shipped directive id so the advisory fires.  If shipped
        # doctrine is absent in this environment, the test simply has no
        # advisory to assert (validation should still pass) — keep the test
        # tolerant of stripped envs.
        _write_directive(tmp_path, artifact_id="DIRECTIVE_001")

        result = validate_pack(tmp_path)

        assert result.ok is True, result.errors
        # Advisory presence depends on whether shipped doctrine is on disk.
        # FR-013 (WP06): reworded message uses "field-merge" wording and
        # surfaces both ``enhances`` and ``overrides`` recommendations.
        for advisory in result.advisories:
            if advisory.artifact_id == "DIRECTIVE_001":
                assert advisory.category == "same_id_collision"
                assert "field-merge" in advisory.message
                assert "enhances: DIRECTIVE_001" in advisory.message
                assert "overrides: DIRECTIVE_001" in advisory.message
                break

    def test_returns_validation_result_type(self, tmp_path: Path) -> None:
        result = validate_pack(tmp_path)
        assert isinstance(result, ValidationResult)
        # ``to_dict`` is part of the public surface used by the CLI.
        payload = result.to_dict()
        assert set(payload.keys()) == {"ok", "errors", "advisories"}


# ---------------------------------------------------------------------------
# WP06: intent-aware collision message tests (FR-011, FR-012, FR-013)
# ---------------------------------------------------------------------------


# A canonical shipped tactic id used by the WP06 test matrix. The auto-emit
# and intent-aware passes resolve against the live shipped doctrine on disk,
# so the id must point at an actual built-in tactic.
_BUILT_IN_TACTIC_ID = "adversarial-qa-handoff"


def _write_tactic(
    pack_dir: Path,
    *,
    artifact_id: str,
    overrides: str | None = None,
    enhances: str | None = None,
) -> Path:
    """Write a minimal, schema-valid tactic YAML file with optional augmentation fields."""
    tactics = pack_dir / "tactics"
    tactics.mkdir(parents=True, exist_ok=True)
    body_lines = [
        'schema_version: "1.0"',
        f"id: {artifact_id}",
        f"name: {artifact_id.title().replace('-', ' ')}",
    ]
    if overrides is not None:
        body_lines.append(f"overrides: {overrides}")
    if enhances is not None:
        body_lines.append(f"enhances: {enhances}")
    body_lines.extend(
        [
            "steps:",
            "  - title: Single test step",
        ]
    )
    path = tactics / f"{artifact_id}.tactic.yaml"
    path.write_text("\n".join(body_lines) + "\n", encoding="utf-8")
    return path


def _write_drg_intent(pack_dir: Path, *, artifact_id: str, relation: str) -> Path:
    drg = pack_dir / "drg"
    drg.mkdir(parents=True, exist_ok=True)
    path = drg / "intent.graph.yaml"
    path.write_text(
        textwrap.dedent(
            f"""\
            schema_version: '1.0'
            generated_at: STATIC
            generated_by: test
            nodes: []
            edges:
              - source: tactic:{artifact_id}
                target: tactic:{artifact_id}
                relation: {relation}
            """
        ),
        encoding="utf-8",
    )
    return path


@pytest.mark.unit
class TestIntentAwareCollision:
    """WP06 precedence table — `enhances` / `overrides` advisory + error logic.

    Tests assume the live shipped doctrine is on disk (the worktree's
    ``src/doctrine/.../built-in`` tree). The shared fixture
    :data:`_BUILT_IN_TACTIC_ID` points at a known built-in. When the shipped
    root cannot be resolved the intent-aware pass degrades to a no-op and the
    tests skip themselves explicitly.
    """

    def _has_built_in_doctrine(self) -> bool:
        try:
            from charter.catalog import resolve_doctrine_root
        except ModuleNotFoundError:
            return False
        try:
            return (resolve_doctrine_root() / "tactics" / "built-in").is_dir()
        except (RuntimeError, OSError):
            return False

    def test_enhances_suppresses_collision_advisory(self, tmp_path: Path) -> None:
        """Case 4: declared `enhances` against a valid built-in -> no advisory."""
        if not self._has_built_in_doctrine():
            pytest.skip("shipped doctrine not on disk in this environment")

        _write_tactic(tmp_path, artifact_id=_BUILT_IN_TACTIC_ID)
        _write_drg_intent(
            tmp_path,
            artifact_id=_BUILT_IN_TACTIC_ID,
            relation="enhances",
        )

        result = validate_pack(tmp_path)

        assert result.ok is True, result.errors
        collision_advisories = [
            a
            for a in result.advisories
            if a.artifact_id == _BUILT_IN_TACTIC_ID
            and a.category == "same_id_collision"
        ]
        assert collision_advisories == [], (
            "Declared `enhances` must suppress same_id_collision advisory."
        )

    def test_overrides_suppresses_collision_advisory(self, tmp_path: Path) -> None:
        """Case 4: declared `overrides` against a valid built-in -> no advisory."""
        if not self._has_built_in_doctrine():
            pytest.skip("shipped doctrine not on disk in this environment")

        _write_tactic(tmp_path, artifact_id=_BUILT_IN_TACTIC_ID)
        _write_drg_intent(
            tmp_path,
            artifact_id=_BUILT_IN_TACTIC_ID,
            relation="overrides",
        )

        result = validate_pack(tmp_path)

        assert result.ok is True, result.errors
        collision_advisories = [
            a
            for a in result.advisories
            if a.artifact_id == _BUILT_IN_TACTIC_ID
            and a.category == "same_id_collision"
        ]
        assert collision_advisories == [], (
            "Declared `overrides` must suppress same_id_collision advisory."
        )

    def test_same_id_collision_uses_reworded_wording(self, tmp_path: Path) -> None:
        """Case 5: same-ID collision, no declaration -> reworded advisory.

        Message MUST mention `field-merge` and recommend BOTH
        `enhances: <id>` and `overrides: <id>`.
        """
        if not self._has_built_in_doctrine():
            pytest.skip("shipped doctrine not on disk in this environment")

        _write_tactic(tmp_path, artifact_id=_BUILT_IN_TACTIC_ID)

        result = validate_pack(tmp_path)

        matched = [
            a
            for a in result.advisories
            if a.artifact_id == _BUILT_IN_TACTIC_ID
            and a.category == "same_id_collision"
        ]
        assert matched, (
            "Same-ID collision without declared intent MUST produce an "
            f"advisory. Saw advisories: {result.advisories}"
        )
        msg = matched[0].message
        assert "field-merge" in msg, msg
        assert f"enhances: {_BUILT_IN_TACTIC_ID}" in msg, msg
        assert f"overrides: {_BUILT_IN_TACTIC_ID}" in msg, msg

    def test_intent_conflict_when_both_fields_set(self, tmp_path: Path) -> None:
        """Case 1: both `overrides` and `enhances` declared -> `intent_conflict` ERROR."""
        _write_tactic(
            tmp_path,
            artifact_id="rogue-tactic",
            overrides="foo",
            enhances="bar",
        )

        result = validate_pack(tmp_path)

        assert result.ok is False
        conflict_errors = [
            e for e in result.errors if e.category == "intent_conflict"
        ]
        assert conflict_errors, (
            f"Both-fields-set MUST emit `intent_conflict`. Errors: {result.errors}"
        )
        assert conflict_errors[0].artifact_id == "rogue-tactic"
        assert "mutually exclusive" in conflict_errors[0].message

    def test_enhances_unknown_target_errors(self, tmp_path: Path) -> None:
        """Case 3: `enhances` references unknown built-in -> `unknown_target` ERROR."""
        if not self._has_built_in_doctrine():
            pytest.skip("shipped doctrine not on disk in this environment")

        _write_tactic(
            tmp_path,
            artifact_id="org-only-tactic",
            enhances="totally-bogus-id",
        )

        result = validate_pack(tmp_path)

        assert result.ok is False
        unknown_errors = [
            e for e in result.errors if e.category == "unknown_target"
        ]
        assert unknown_errors, (
            f"Unknown `enhances` target MUST emit `unknown_target`. "
            f"Errors: {result.errors}"
        )
        assert "totally-bogus-id" in unknown_errors[0].message
        assert "enhances" in unknown_errors[0].message

    def test_overrides_unknown_target_errors(self, tmp_path: Path) -> None:
        """Case 2: `overrides` references unknown built-in -> `unknown_target` ERROR."""
        if not self._has_built_in_doctrine():
            pytest.skip("shipped doctrine not on disk in this environment")

        _write_tactic(
            tmp_path,
            artifact_id="org-only-tactic",
            overrides="totally-bogus-id",
        )

        result = validate_pack(tmp_path)

        assert result.ok is False
        unknown_errors = [
            e for e in result.errors if e.category == "unknown_target"
        ]
        assert unknown_errors, (
            f"Unknown `overrides` target MUST emit `unknown_target`. "
            f"Errors: {result.errors}"
        )
        assert "totally-bogus-id" in unknown_errors[0].message
        assert "overrides" in unknown_errors[0].message

    def test_json_output_includes_new_categories(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """T038: `category` field surfaces in JSON output for the new error kinds."""
        _write_tactic(
            tmp_path,
            artifact_id="rogue-tactic",
            overrides="a",
            enhances="b",
        )

        result = validate_pack(tmp_path)
        render_validation_result(result, json_output=True)
        captured = capsys.readouterr().out
        import json as _json

        payload = _json.loads(captured.strip())
        assert payload["ok"] is False
        categories = {e.get("category") for e in payload["errors"]}
        assert "intent_conflict" in categories, payload


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


# ---------------------------------------------------------------------------
# WP04: ASSET sidecar manifest validation (T014-T018)
# ---------------------------------------------------------------------------


class TestAssetManifestValidation:
    """ASSET (``*.asset.yaml``) sidecar manifest + safety contract.

    The referenced blob is never scanned; only the sidecar manifest is
    schema-validated (T014), plus a separate containment (T016) and mime
    (T017) safety pass. Global id-uniqueness across packs is explicitly
    OUT of scope here (WP03's merge scan).
    """

    def test_valid_manifest_passes(self, tmp_path: Path) -> None:
        """A well-formed, contained, mime-consistent manifest is clean."""
        _write_asset_manifest(
            tmp_path,
            artifact_id="acme-brand-logo-png",
            mime="image/png",
            path_value="branding/acme-logo.png",
            title="Acme brand logo (PNG)",
        )

        result = validate_pack(tmp_path)

        assert result.ok is True, result.errors
        assert result.errors == []

    def test_missing_id_fails_schema(self, tmp_path: Path) -> None:
        _write_asset_manifest(
            tmp_path,
            artifact_id=None,
            drop_id=True,
            filename="acme-logo-no-id.asset.yaml",
        )

        result = validate_pack(tmp_path)

        assert result.ok is False
        assert any(
            issue.artifact_type == "assets" and issue.category == "schema_invalid"
            for issue in result.errors
        ), result.errors

    def test_blank_id_fails_schema(self, tmp_path: Path) -> None:
        _write_asset_manifest(
            tmp_path,
            artifact_id="",
            filename="acme-logo-blank-id.asset.yaml",
        )

        result = validate_pack(tmp_path)

        assert result.ok is False
        assert any(
            issue.artifact_type == "assets" and issue.category == "schema_invalid"
            for issue in result.errors
        ), result.errors

    def test_path_escape_via_dotdot_rejected(self, tmp_path: Path) -> None:
        """T016: an escaping ``path`` is rejected as ``asset_path_escape``."""
        _write_asset_manifest(
            tmp_path,
            artifact_id="acme-logo-escape",
            mime="image/png",
            path_value="../../../etc/passwd",
        )

        result = validate_pack(tmp_path)

        assert result.ok is False
        escape_errors = [
            e for e in result.errors if e.category == "asset_path_escape"
        ]
        assert escape_errors, result.errors
        assert escape_errors[0].artifact_id == "acme-logo-escape"

    def test_absolute_path_rejected(self, tmp_path: Path) -> None:
        """T016: an absolute ``path`` is also rejected as ``asset_path_escape``."""
        _write_asset_manifest(
            tmp_path,
            artifact_id="acme-logo-absolute",
            mime="image/png",
            path_value="/etc/passwd",
        )

        result = validate_pack(tmp_path)

        assert result.ok is False
        escape_errors = [
            e for e in result.errors if e.category == "asset_path_escape"
        ]
        assert escape_errors, result.errors
        assert escape_errors[0].artifact_id == "acme-logo-absolute"

    def test_malformed_mime_rejected(self, tmp_path: Path) -> None:
        """T017: ``mime`` without a ``type/subtype`` shape is rejected."""
        _write_asset_manifest(
            tmp_path,
            artifact_id="acme-logo-badmime",
            mime="notamimetype",
            path_value="branding/acme-logo.png",
        )

        result = validate_pack(tmp_path)

        assert result.ok is False
        mime_errors = [e for e in result.errors if e.category == "asset_mime_invalid"]
        assert mime_errors, result.errors
        assert mime_errors[0].artifact_id == "acme-logo-badmime"

    def test_mime_extension_mismatch_rejected(self, tmp_path: Path) -> None:
        """T017: declared ``mime`` disagreeing with the path extension is rejected."""
        _write_asset_manifest(
            tmp_path,
            artifact_id="acme-logo-mismatch",
            mime="image/png",
            path_value="branding/acme-logo.txt",
        )

        result = validate_pack(tmp_path)

        assert result.ok is False
        mime_errors = [e for e in result.errors if e.category == "asset_mime_invalid"]
        assert mime_errors, result.errors
        assert mime_errors[0].artifact_id == "acme-logo-mismatch"

    def test_nested_asset_manifest_violation_is_caught(self, tmp_path: Path) -> None:
        """FR-003 AC-1: a schema-violating manifest nested one level below
        ``assets/`` (``assets/<pack>/x.asset.yaml`` — the ADR-mandated org-pack
        layout ``AssetRepository`` already recurses into) is caught by
        ``pack validate``, not silently skipped. Before FR-003, ``_scan_files``
        only recurses for ``styleguides``, so this manifest was never scanned
        and this assertion failed.
        """
        _write_asset_manifest(
            tmp_path,
            artifact_id="acme-logo-nested-badmime",
            mime="notamimetype",
            path_value="branding/acme-logo.png",
            subdir="acme-pack",
        )

        result = validate_pack(tmp_path)

        assert result.ok is False
        mime_errors = [e for e in result.errors if e.category == "asset_mime_invalid"]
        assert mime_errors, result.errors
        assert mime_errors[0].artifact_id == "acme-logo-nested-badmime"
        assert "acme-pack" in mime_errors[0].file

    def test_nested_asset_manifest_valid_passes(self, tmp_path: Path) -> None:
        """FR-003 AC-2: a valid nested manifest passes with no false positive —
        it participates in the existing containment/mime checks exactly like a
        top-level asset would."""
        _write_asset_manifest(
            tmp_path,
            artifact_id="acme-brand-logo-nested-png",
            mime="image/png",
            path_value="branding/acme-logo.png",
            subdir="acme-pack",
        )

        result = validate_pack(tmp_path)

        assert result.ok is True, result.errors
        assert result.errors == []

    def test_no_assets_directory_is_a_noop(self, tmp_path: Path) -> None:
        """FR-003 AC-4: an absent ``assets/`` directory produces no error and no
        behavior change. ``validate_pack``'s registry loop guard
        (``if not type_dir.is_dir(): continue``) predates FR-003 and is left
        untouched by it — this proves the guard path actually executes for the
        absent-directory case (not merely that nothing crashes) by asserting no
        ``assets``-typed issue is ever produced when ``assets/`` never existed.
        """
        _write_directive(tmp_path, artifact_id="ACME-001")
        assert not (tmp_path / "assets").exists()

        result = validate_pack(tmp_path)

        assert result.ok is True, result.errors
        assert not any(
            issue.artifact_type == "assets"
            for issue in (*result.errors, *result.advisories)
        ), (result.errors, result.advisories)

    def test_multiple_assets_independent(self, tmp_path: Path) -> None:
        """Multiple manifests in one pack are each validated independently."""
        _write_asset_manifest(
            tmp_path,
            artifact_id="acme-brand-logo-png",
            mime="image/png",
            path_value="branding/acme-logo.png",
        )
        _write_asset_manifest(
            tmp_path,
            artifact_id="acme-brand-font-woff2",
            mime="font/woff2",
            path_value="branding/acme-brand.woff2",
        )

        result = validate_pack(tmp_path)

        assert result.ok is True, result.errors


class TestProfileSkippedDiagnostics:
    """FR-002: ``pack validate`` surfaces ``AgentProfileRepository``'s
    post-merge profile-skip diagnostics inline (``skipped_profiles()``),
    not only via the separate, undocumented ``spec-kitty doctor doctrine
    --json`` command.

    This is additive wiring (AC-4), not a new validation engine: the checks
    here exercise the REAL, shipped built-in ``analyst-annie`` profile
    (``packs/built-in/agent_profiles/analyst-annie.agent.yaml``) as the
    merge target, per this WP's Reviewer Guidance — no fake built-in
    directory is fabricated.
    """

    _ANALYST_ANNIE_ROLE_CONFLICT_YAML = textwrap.dedent(
        """\
        profile-id: analyst-annie
        role: implementer
        name: Override
        purpose: test purpose
        specialization:
          primary-focus: test focus
        """
    )

    def test_post_merge_skip_surfaces_as_profile_skipped_issue(
        self, tmp_path: Path
    ) -> None:
        """AC-1: a profile that passes ``AgentProfile.model_validate`` in
        isolation (proven standalone-valid by
        ``tests/doctrine/test_agent_profile_model_field.py``'s
        ``TestDeprecatedScalarRoleStandaloneValid``, T008) but is recorded
        via ``AgentProfileRepository``'s ``_record_skip`` during merge-time
        load (the deprecated scalar ``role:`` colliding with the real
        built-in ``analyst-annie``'s already-resolved ``roles:``) causes
        ``pack validate`` to include a ``profile_skipped`` ``ValidationIssue``
        in ``result.errors``.

        Before this WP, ``pack_validator.py`` never calls
        ``AgentProfileRepository``/``skipped_profiles()`` at all, so this
        assertion fails — the only surface for this diagnostic today is the
        separate ``spec-kitty doctor doctrine --json`` command.
        """
        profile_path = _write_agent_profile_yaml(
            tmp_path,
            filename="analyst-annie.agent.yaml",
            content=self._ANALYST_ANNIE_ROLE_CONFLICT_YAML,
        )

        result = validate_pack(tmp_path)

        skipped_issues = [
            issue for issue in result.errors if issue.category == "profile_skipped"
        ]
        assert skipped_issues, result.errors
        issue = skipped_issues[0]
        assert issue.severity == "error"
        assert issue.artifact_type == "agent_profiles"
        assert issue.artifact_id == "analyst-annie"
        assert issue.file == str(profile_path)
        assert "role" in issue.message and "roles" in issue.message

    def test_helper_calls_repository_skipped_profiles_directly(
        self, tmp_path: Path
    ) -> None:
        """AC-4: the helper reuses ``AgentProfileRepository.skipped_profiles()``
        directly rather than hand-rolling a second skip-detection heuristic.

        Patches the source location the helper's lazy, function-local import
        binds to (``doctrine.agent_profiles.repository.AgentProfileRepository``
        — matching this file's existing precedent of lazy in-function
        imports, and what ``scripts/check_patch_targets.py`` expects). This
        assertion is non-vacuous: it fails if the call is removed or replaced
        with an inline reimplementation, since only an actual invocation of
        the mocked method satisfies ``assert_called_once``.
        """
        agent_profiles_dir = tmp_path / "agent_profiles"
        agent_profiles_dir.mkdir()

        with patch(
            "doctrine.agent_profiles.repository.AgentProfileRepository.skipped_profiles"
        ) as mock_skipped_profiles:
            mock_skipped_profiles.return_value = []
            issues = _check_profile_skipped_diagnostics(tmp_path, set())

        mock_skipped_profiles.assert_called_once_with()
        assert issues == []
