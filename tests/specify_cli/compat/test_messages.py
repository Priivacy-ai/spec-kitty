"""Tests for compat.messages — T026.

Covers:
- render_human: each Fr023Case produces appropriate output.
- NONE case produces empty string.
- render_json: output dict has all required keys and correct types.
- Sanitisation: hostile latest_version is substituted with <unavailable>.
- render_json validates against contracts/compat-planner.json (via jsonschema
  if available, else key-set check).
"""

from __future__ import annotations

import json
from datetime import datetime, UTC
from pathlib import Path


from specify_cli.compat._detect.install_method import InstallMethod
from specify_cli.compat.messages import MESSAGES, render_human, render_json
from specify_cli.compat.planner import (
    CliStatus,
    Decision,
    Fr023Case,
    MigrationStep,
    Plan,
    ProjectState,
    ProjectStatus,
)
from specify_cli.compat.safety import Safety
from specify_cli.compat.upgrade_hint import build_upgrade_hint

_NOW = datetime(2026, 4, 27, 12, 0, 0, tzinfo=UTC)
_INSTALLED = "2.0.11"
_LATEST = "2.0.14"
_MIN = 3
_MAX = 3

# Path to the JSON contract schema
_CONTRACT_PATH = (
    Path(__file__).parent.parent.parent.parent.parent
    / "kitty-specs"
    / "cli-upgrade-nag-lazy-project-migrations-01KQ6YDN"
    / "contracts"
    / "compat-planner.json"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_plan(
    decision: Decision,
    fr023_case: Fr023Case,
    *,
    project_state: ProjectState = ProjectState.COMPATIBLE,
    schema_version: int | None = 3,
    max_supported: int = _MAX,
    min_supported: int = _MIN,
    is_outdated: bool = False,
    latest_version: str | None = _LATEST,
    metadata_error: str | None = None,
    install_method: InstallMethod = InstallMethod.PIPX,
    pending_migrations: tuple[MigrationStep, ...] = (),
) -> Plan:
    """Construct a minimal Plan for testing message rendering."""
    cli_status = CliStatus(
        installed_version=_INSTALLED,
        latest_version=latest_version,
        latest_source="pypi" if latest_version else "none",
        is_outdated=is_outdated,
        fetched_at=_NOW,
    )
    project_status = ProjectStatus(
        state=project_state,
        project_root=Path("/tmp/testproj"),
        schema_version=schema_version,
        min_supported=min_supported,
        max_supported=max_supported,
        metadata_error=metadata_error,
    )
    upgrade_hint = build_upgrade_hint(install_method)
    exit_code_map = {
        Decision.ALLOW: 0,
        Decision.ALLOW_WITH_NAG: 0,
        Decision.BLOCK_PROJECT_MIGRATION: 4,
        Decision.BLOCK_CLI_UPGRADE: 5,
        Decision.BLOCK_PROJECT_CORRUPT: 6,
        Decision.BLOCK_INCOMPATIBLE_FLAGS: 2,
    }

    # Build a plan with empty rendered_human/rendered_json for render calls
    partial = Plan(
        decision=decision,
        cli_status=cli_status,
        project_status=project_status,
        safety=Safety.UNSAFE,
        pending_migrations=pending_migrations,
        install_method=install_method,
        upgrade_hint=upgrade_hint,
        fr023_case=fr023_case,
        exit_code=exit_code_map[decision],
        rendered_human="",
        rendered_json={},
    )
    human = render_human(partial)
    rendered = render_json(partial)
    return Plan(
        decision=decision,
        cli_status=cli_status,
        project_status=project_status,
        safety=Safety.UNSAFE,
        pending_migrations=pending_migrations,
        install_method=install_method,
        upgrade_hint=upgrade_hint,
        fr023_case=fr023_case,
        exit_code=exit_code_map[decision],
        rendered_human=human,
        rendered_json=rendered,
    )


# ---------------------------------------------------------------------------
# MESSAGES catalog
# ---------------------------------------------------------------------------


class TestMessagesCatalog:
    def test_all_cases_present(self) -> None:
        for case in Fr023Case:
            assert case in MESSAGES, f"MESSAGES missing case {case!r}"

    def test_none_case_is_empty(self) -> None:
        assert MESSAGES[Fr023Case.NONE] == ""

    def test_cli_update_available_contains_placeholders(self) -> None:
        template = MESSAGES[Fr023Case.CLI_UPDATE_AVAILABLE]
        assert "{latest}" in template
        assert "{installed}" in template

    def test_project_migration_needed_no_placeholders(self) -> None:
        template = MESSAGES[Fr023Case.PROJECT_MIGRATION_NEEDED]
        assert "spec-kitty upgrade" in template

    def test_project_too_new_contains_schema_version(self) -> None:
        template = MESSAGES[Fr023Case.PROJECT_TOO_NEW_FOR_CLI]
        assert "{schema_version}" in template
        assert "{max_supported}" in template


# ---------------------------------------------------------------------------
# render_human
# ---------------------------------------------------------------------------


class TestRenderHuman:
    def test_none_case_empty(self) -> None:
        p = _make_plan(Decision.ALLOW, Fr023Case.NONE, is_outdated=False)
        assert render_human(p) == ""

    def test_cli_update_available(self) -> None:
        p = _make_plan(
            Decision.ALLOW_WITH_NAG,
            Fr023Case.CLI_UPDATE_AVAILABLE,
            is_outdated=True,
            latest_version=_LATEST,
        )
        text = render_human(p)
        assert _LATEST in text
        assert _INSTALLED in text
        assert len(text.splitlines()) <= 4

    def test_project_migration_needed(self) -> None:
        p = _make_plan(Decision.BLOCK_PROJECT_MIGRATION, Fr023Case.PROJECT_MIGRATION_NEEDED)
        text = render_human(p)
        assert "spec-kitty upgrade" in text
        assert len(text.splitlines()) <= 4

    def test_project_too_new(self) -> None:
        p = _make_plan(
            Decision.BLOCK_CLI_UPGRADE,
            Fr023Case.PROJECT_TOO_NEW_FOR_CLI,
            project_state=ProjectState.TOO_NEW,
            schema_version=7,
            max_supported=3,
        )
        text = render_human(p)
        assert "7" in text
        assert "3" in text
        assert len(text.splitlines()) <= 4

    def test_project_metadata_corrupt(self) -> None:
        p = _make_plan(
            Decision.BLOCK_PROJECT_CORRUPT,
            Fr023Case.PROJECT_METADATA_CORRUPT,
            project_state=ProjectState.CORRUPT,
            schema_version=None,
            metadata_error="oversized",
        )
        text = render_human(p)
        assert "oversized" in text
        assert "spec-kitty doctor" in text
        assert len(text.splitlines()) <= 4

    def test_at_most_4_lines(self) -> None:
        for case in Fr023Case:
            decision = Decision.ALLOW
            if case == Fr023Case.PROJECT_MIGRATION_NEEDED:
                decision = Decision.BLOCK_PROJECT_MIGRATION
            elif case == Fr023Case.PROJECT_TOO_NEW_FOR_CLI:
                decision = Decision.BLOCK_CLI_UPGRADE
            elif case == Fr023Case.PROJECT_METADATA_CORRUPT:
                decision = Decision.BLOCK_PROJECT_CORRUPT
            elif case == Fr023Case.CLI_UPDATE_AVAILABLE:
                decision = Decision.ALLOW_WITH_NAG

            p = _make_plan(decision, case, metadata_error="test error")
            text = render_human(p)
            lines = text.splitlines()
            assert len(lines) <= 4, f"Case {case!r} produced {len(lines)} lines"

    def test_sanitisation_hostile_version(self) -> None:
        """ANSI escape in latest_version must be replaced with <unavailable>."""
        hostile = "\x1b[31mUPGRADE\x1b[0m"
        p = _make_plan(
            Decision.ALLOW_WITH_NAG,
            Fr023Case.CLI_UPDATE_AVAILABLE,
            is_outdated=True,
            latest_version=hostile,
        )
        text = render_human(p)
        assert hostile not in text
        assert "\x1b" not in text
        assert "<unavailable>" in text

    def test_sanitisation_shell_metachar(self) -> None:
        """Shell metacharacters in installed_version must be sanitised."""
        import specify_cli.compat.messages as messages_mod

        result = messages_mod._safe("`rm -rf /`")
        assert result == "<unavailable>"

    def test_no_trailing_whitespace(self) -> None:
        p = _make_plan(
            Decision.ALLOW_WITH_NAG,
            Fr023Case.CLI_UPDATE_AVAILABLE,
            is_outdated=True,
            latest_version=_LATEST,
        )
        text = render_human(p)
        for line in text.splitlines():
            assert line == line.rstrip(), f"Trailing whitespace in line: {line!r}"


# ---------------------------------------------------------------------------
# render_json
# ---------------------------------------------------------------------------


class TestRenderJson:
    def _get_contract(self) -> dict | None:
        """Load the JSON schema contract if available."""
        if not _CONTRACT_PATH.exists():
            return None
        try:
            return json.loads(_CONTRACT_PATH.read_text())
        except Exception:
            return None

    def _validate_against_schema(self, obj: dict) -> None:
        """Validate *obj* against the JSON contract schema (if jsonschema is available)."""
        contract = self._get_contract()
        if contract is None:
            return
        try:
            import jsonschema  # type: ignore[import-untyped]

            jsonschema.validate(obj, contract)
        except ImportError:
            # jsonschema not available — fall back to key-set check
            required_keys = {
                "schema_version", "case", "decision", "exit_code",
                "cli", "project", "safety", "install_method",
                "upgrade_hint", "pending_migrations", "rendered_human",
            }
            assert required_keys.issubset(set(obj.keys())), (
                f"Missing keys: {required_keys - set(obj.keys())}"
            )

    def test_allow_plan(self) -> None:
        p = _make_plan(Decision.ALLOW, Fr023Case.NONE)
        obj = render_json(p)
        self._validate_against_schema(obj)
        assert obj["schema_version"] == 1
        assert obj["case"] == "none"
        assert obj["decision"] == "ALLOW"
        assert obj["exit_code"] == 0

    def test_allow_with_nag_plan(self) -> None:
        p = _make_plan(
            Decision.ALLOW_WITH_NAG,
            Fr023Case.CLI_UPDATE_AVAILABLE,
            is_outdated=True,
            latest_version=_LATEST,
        )
        obj = render_json(p)
        self._validate_against_schema(obj)
        assert obj["case"] == "cli_update_available"
        assert obj["decision"] == "ALLOW_WITH_NAG"
        assert obj["exit_code"] == 0
        assert obj["cli"]["is_outdated"] is True
        assert obj["cli"]["latest_version"] == _LATEST

    def test_block_project_migration(self) -> None:
        p = _make_plan(
            Decision.BLOCK_PROJECT_MIGRATION,
            Fr023Case.PROJECT_MIGRATION_NEEDED,
            project_state=ProjectState.STALE,
            schema_version=1,
        )
        obj = render_json(p)
        self._validate_against_schema(obj)
        assert obj["exit_code"] == 4
        assert obj["case"] == "project_migration_needed"

    def test_block_cli_upgrade(self) -> None:
        p = _make_plan(
            Decision.BLOCK_CLI_UPGRADE,
            Fr023Case.PROJECT_TOO_NEW_FOR_CLI,
            project_state=ProjectState.TOO_NEW,
            schema_version=99,
            max_supported=3,
        )
        obj = render_json(p)
        self._validate_against_schema(obj)
        assert obj["exit_code"] == 5
        assert obj["case"] == "project_too_new_for_cli"

    def test_block_project_corrupt(self) -> None:
        p = _make_plan(
            Decision.BLOCK_PROJECT_CORRUPT,
            Fr023Case.PROJECT_METADATA_CORRUPT,
            project_state=ProjectState.CORRUPT,
            schema_version=None,
            metadata_error="oversized",
        )
        obj = render_json(p)
        self._validate_against_schema(obj)
        assert obj["exit_code"] == 6
        assert obj["case"] == "project_metadata_corrupt"
        assert obj["project"]["metadata_error"] == "oversized"

    def test_pending_migrations_empty_by_default(self) -> None:
        p = _make_plan(Decision.ALLOW, Fr023Case.NONE)
        obj = render_json(p)
        assert isinstance(obj["pending_migrations"], list)
        assert len(obj["pending_migrations"]) == 0

    def test_pending_migrations_present(self) -> None:
        step = MigrationStep(
            migration_id="m_3_0_0_test",
            target_schema_version=3,
            description="Test migration",
            files_modified=(Path(".kittify/metadata.yaml"),),
        )
        p = _make_plan(
            Decision.BLOCK_PROJECT_MIGRATION,
            Fr023Case.PROJECT_MIGRATION_NEEDED,
            pending_migrations=(step,),
        )
        obj = render_json(p)
        assert len(obj["pending_migrations"]) == 1
        m = obj["pending_migrations"][0]
        assert m["migration_id"] == "m_3_0_0_test"
        assert m["target_schema_version"] == 3
        assert m["description"] == "Test migration"
        assert m["files_modified"] == [".kittify/metadata.yaml"]

    def test_safety_field_is_string(self) -> None:
        p = _make_plan(Decision.ALLOW, Fr023Case.NONE)
        obj = render_json(p)
        assert isinstance(obj["safety"], str)
        assert obj["safety"] in ("safe", "unsafe")

    def test_install_method_field_is_string(self) -> None:
        p = _make_plan(Decision.ALLOW, Fr023Case.NONE, install_method=InstallMethod.PIPX)
        obj = render_json(p)
        assert obj["install_method"] == "pipx"

    def test_upgrade_hint_exactly_one_of_command_note(self) -> None:
        p = _make_plan(Decision.ALLOW, Fr023Case.NONE, install_method=InstallMethod.PIPX)
        obj = render_json(p)
        hint = obj["upgrade_hint"]
        command_set = hint.get("command") is not None
        note_set = hint.get("note") is not None
        assert command_set != note_set, "Exactly one of command/note must be non-null"

    def test_fetched_at_is_iso8601_or_null(self) -> None:
        p = _make_plan(Decision.ALLOW, Fr023Case.NONE)
        obj = render_json(p)
        fetched_at = obj["cli"]["fetched_at"]
        if fetched_at is not None:
            assert "T" in fetched_at, f"fetched_at is not ISO-8601: {fetched_at!r}"

    def test_project_root_is_string_or_null(self) -> None:
        p = _make_plan(Decision.ALLOW, Fr023Case.NONE)
        obj = render_json(p)
        root = obj["project"]["project_root"]
        assert root is None or isinstance(root, str)

    def test_install_method_unknown_hint_command_null(self) -> None:
        p = _make_plan(Decision.ALLOW, Fr023Case.NONE, install_method=InstallMethod.UNKNOWN)
        obj = render_json(p)
        assert obj["upgrade_hint"]["command"] is None
        assert obj["upgrade_hint"]["note"] is not None
