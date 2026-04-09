"""CI grep guards for canonical terminology drift.

These guards prevent the Mission Type / Mission / Mission Run terminology
boundary from drifting back to legacy selector vocabulary. They are scoped
to live first-party surfaces only.

Explicitly does not scan:
- `kitty-specs/**` (historical mission artifacts)
- `architecture/**` (historical ADRs and initiative records)
- `.kittify/**` (runtime state)
- `tests/**` (tests legitimately mention forbidden patterns)
- `docs/migration/**` (migration docs must name deprecated flags)
- historical version sections of `CHANGELOG.md`
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

CLI_COMMAND_GLOBS = ("src/specify_cli/cli/commands/**/*.py",)
DOCTRINE_SKILL_GLOBS = ("src/doctrine/skills/**/*.md",)
AGENT_DOC_GLOBS = ("docs/**/*.md",)
TOP_LEVEL_DOCS = ("README.md", "CONTRIBUTING.md")
FORBIDDEN_SCAN_ROOTS = ("kitty-specs/", "architecture/", ".kittify/", "tests/", "docs/migration/")


def _glob(pattern: str) -> list[Path]:
    return sorted(REPO_ROOT.glob(pattern))


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _iter_typer_option_blocks(content: str):
    """Yield `(offset, block)` tuples for each `typer.Option(...)` call."""
    pattern = re.compile(r"typer\.Option\((?:[^()]|\([^()]*\))*\)", re.DOTALL)
    for match in pattern.finditer(content):
        yield match.start(), match.group(0)


def _extract_help(option_block: str) -> str:
    """Extract the `help=` string from a typer.Option block when present."""
    match = re.search(r'help\s*=\s*"([^"]*)"', option_block)
    if match:
        return match.group(1)
    match = re.search(r"help\s*=\s*'([^']*)'", option_block)
    return match.group(1) if match else ""


def _extract_changelog_unreleased(path: Path) -> str:
    """Return the portion of CHANGELOG.md above the first version heading."""
    content = _read(path)
    match = re.search(r"^## \[\d+\.\d+\.\d+", content, flags=re.MULTILINE)
    if match is None:
        return content
    return content[: match.start()]


def _live_doc_scan_targets() -> list[tuple[Path, str]]:
    """Return live first-party docs that must stay terminology-clean."""
    scan_targets: list[tuple[Path, str]] = []
    for path_pattern in AGENT_DOC_GLOBS:
        for path in _glob(path_pattern):
            relative_path = path.relative_to(REPO_ROOT).as_posix()
            if relative_path.startswith("docs/migration/"):
                continue
            scan_targets.append((path, _read(path)))
    for top_level in TOP_LEVEL_DOCS:
        path = REPO_ROOT / top_level
        if path.exists():
            scan_targets.append((path, _read(path)))
    changelog_path = REPO_ROOT / "CHANGELOG.md"
    if changelog_path.exists():
        scan_targets.append((changelog_path, _extract_changelog_unreleased(changelog_path)))
    return scan_targets


def _surrounding_param_name(content: str, offset: int) -> str:
    """Best-effort extraction of the enclosing parameter name."""
    window = content[max(0, offset - 300):offset]
    matches = list(re.finditer(r"([A-Za-z_][A-Za-z0-9_]*)\s*:\s*[^=\n]+=\s*$", window, re.MULTILINE))
    if matches:
        return matches[-1].group(1)
    matches = list(re.finditer(r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*$", window, re.MULTILINE))
    return matches[-1].group(1) if matches else ""


def _is_runtime_session_param(param_name: str) -> bool:
    lowered = param_name.lower()
    return any(token in lowered for token in ("runtime", "session", "run_id", "run"))


def _line_number(content: str, offset: int) -> int:
    return content.count("\n", 0, offset) + 1


def test_no_mission_run_alias_in_tracked_mission_selectors():
    """Live CLI command files must not declare --mission-run for mission selection.

    Authority: spec.md FR-002, FR-003.
    """
    pattern = re.compile(r"typer\.Option\((?:[^()]|\([^()]*\))*\"--mission-run\"(?:[^()]|\([^()]*\))*\)", re.DOTALL)
    for path_pattern in CLI_COMMAND_GLOBS:
        for path in _glob(path_pattern):
            content = _read(path)
            for match in pattern.finditer(content):
                param_name = _surrounding_param_name(content, match.start())
                if _is_runtime_session_param(param_name):
                    continue
                line = _line_number(content, match.start())
                pytest.fail(
                    f"{path.relative_to(REPO_ROOT)}:{line}: --mission-run used as a tracked-mission selector. "
                    "Authority: spec.md FR-002/FR-003. Fix: use --mission instead."
                )


def test_no_mission_run_slug_help_text_in_cli_commands():
    """Tracked-mission CLI help text must not say 'Mission run slug'.

    Authority: spec.md FR-008.
    """
    for path_pattern in CLI_COMMAND_GLOBS:
        for path in _glob(path_pattern):
            content = _read(path)
            if "Mission run slug" not in content:
                continue
            line = _line_number(content, content.index("Mission run slug"))
            pytest.fail(
                f"{path.relative_to(REPO_ROOT)}:{line}: contains 'Mission run slug'. "
                "Authority: spec.md FR-008. Fix: say 'Mission slug'."
            )


def test_no_visible_feature_alias_in_cli_commands():
    """--feature is acceptable only as a hidden=True alias.

    Authority: spec.md FR-005 and charter terminology canon.
    """
    for path_pattern in CLI_COMMAND_GLOBS:
        for path in _glob(path_pattern):
            content = _read(path)
            for offset, option_block in _iter_typer_option_blocks(content):
                if '"--feature"' not in option_block:
                    continue
                if "hidden=True" in option_block:
                    continue
                line = _line_number(content, offset)
                pytest.fail(
                    f"{path.relative_to(REPO_ROOT)}:{line}: --feature declared without hidden=True. "
                    "Authority: spec.md FR-005 and charter terminology canon. "
                    "Fix: declare --feature only as a hidden deprecated alias."
                )


def test_no_mission_run_instructions_in_doctrine_skills():
    """Doctrine skills must teach --mission for tracked-mission selection.

    Authority: spec.md FR-009.
    """
    forbidden_patterns = (
        r"--mission-run\s+\d{3}",
        r"--mission-run\s+<slug>",
        r"--mission-run\s+<mission",
    )
    for path_pattern in DOCTRINE_SKILL_GLOBS:
        for path in _glob(path_pattern):
            content = _read(path)
            for pattern in forbidden_patterns:
                for match in re.finditer(pattern, content):
                    line = _line_number(content, match.start())
                    pytest.fail(
                        f"{path.relative_to(REPO_ROOT)}:{line}: doctrine skill instructs --mission-run. "
                        "Authority: spec.md FR-009. Fix: use --mission."
                    )


def test_no_mission_run_instructions_in_agent_facing_docs():
    """Live docs must teach --mission for tracked-mission selection.

    Authority: spec.md FR-010 and FR-022.
    """
    forbidden_patterns = (
        r"--mission-run\s+\d{3}",
        r"--mission-run\s+<slug>",
        r"--mission-run\s+<mission",
    )

    for path, content in _live_doc_scan_targets():
        for pattern in forbidden_patterns:
            for match in re.finditer(pattern, content):
                line = _line_number(content, match.start())
                pytest.fail(
                    f"{path.relative_to(REPO_ROOT)}:{line}: doc instructs --mission-run. "
                    "Authority: spec.md FR-010/FR-022. Fix: use --mission."
                )


def test_no_feature_flag_in_live_first_party_docs():
    """Live docs must not document --feature as a live CLI option.

    Authority: spec.md FR-005, FR-022, and the charter terminology canon.
    """
    forbidden_patterns = (
        r"--feature\s+<slug>",
        r"--feature\s+\d{3}",
        r"--feature\s+[a-z][a-z0-9-]*",
        r"\|\s*`--feature[\s|<>`]",
    )

    for path, content in _live_doc_scan_targets():
        for pattern in forbidden_patterns:
            for match in re.finditer(pattern, content):
                line = _line_number(content, match.start())
                snippet = content[max(0, match.start() - 25):match.end() + 25]
                pytest.fail(
                    f"{path.relative_to(REPO_ROOT)}:{line}: documents --feature as a live CLI option: {snippet!r}. "
                    "Authority: spec.md FR-005/FR-022 and charter terminology canon. "
                    "Fix: use --mission or link to docs/migration/feature-flag-deprecation.md."
                )


def test_no_removed_orchestrator_api_command_names_in_live_docs():
    """Live docs must not teach removed host orchestrator-api subcommands.

    Authority: spec.md FR-010, FR-022.
    """
    forbidden_patterns = (
        r"spec-kitty orchestrator-api feature-state\b",
        r"spec-kitty orchestrator-api accept-feature\b",
        r"spec-kitty orchestrator-api merge-feature\b",
    )
    for path, content in _live_doc_scan_targets():
        for pattern in forbidden_patterns:
            for match in re.finditer(pattern, content):
                line = _line_number(content, match.start())
                pytest.fail(
                    f"{path.relative_to(REPO_ROOT)}:{line}: doc teaches removed orchestrator-api command. "
                    "Authority: spec.md FR-010/FR-022. Fix: use mission-state/accept-mission/merge-mission."
                )


def test_no_mission_used_to_mean_mission_type_in_cli_commands():
    """CLI command files must not declare --mission with mission-type semantics.

    Authority: spec.md FR-021.
    """
    for path_pattern in CLI_COMMAND_GLOBS:
        for path in _glob(path_pattern):
            content = _read(path)
            for offset, option_block in _iter_typer_option_blocks(content):
                if '"--mission"' not in option_block:
                    continue
                help_text = _extract_help(option_block).lower()
                if "mission type" not in help_text and "mission key" not in help_text:
                    continue
                if '"--mission-type"' in option_block:
                    continue
                line = _line_number(content, offset)
                pytest.fail(
                    f"{path.relative_to(REPO_ROOT)}:{line}: --mission declared with mission-type semantics. "
                    "Authority: spec.md FR-021. Fix: use --mission-type as canonical and keep --mission only as a hidden alias."
                )


def test_reference_examples_match_runtime_requirements():
    """Reference docs must not teach invocation patterns that now hard-fail.

    Authority: spec.md FR-010, FR-013, FR-022.
    """

    cli_reference = _read(REPO_ROOT / "docs/reference/cli-commands.md")
    assert "spec-kitty next --json" not in cli_reference
    assert "bare call (no `--agent`)" not in cli_reference

    agent_reference = _read(REPO_ROOT / "docs/reference/agent-subcommands.md")
    forbidden_example_lines = (
        r"^spec-kitty agent mission accept$",
        r"^spec-kitty agent mission accept --json$",
        r"^spec-kitty agent tasks mark-status T001 --status done$",
        r"^spec-kitty agent tasks status$",
        r"^spec-kitty agent tasks status --json$",
        r"^spec-kitty agent tasks list-tasks --json$",
        r"^spec-kitty agent tasks list-tasks --lane doing --json$",
        r"^spec-kitty agent tasks add-history WP01 --note \"Completed implementation\" --json$",
        r"^spec-kitty agent tasks finalize-tasks --json$",
        r"^spec-kitty agent tasks map-requirements --wp WP04 --refs FR-001,FR-002$",
        r"^spec-kitty agent tasks map-requirements --batch '\{\"WP01\":\[\"FR-001\"\],\"WP02\":\[\"FR-003\"\]\}' --json$",
        r"^spec-kitty agent tasks map-requirements --wp WP01 --refs FR-005 --replace$",
        r"^spec-kitty agent tasks validate-workflow WP01 --json$",
        r"^spec-kitty agent tasks list-dependents WP13$",
        r"^spec-kitty agent action implement WP01 --agent claude$",
        r"^spec-kitty agent action implement WP02 --agent claude$",
        r"^spec-kitty agent action implement --agent gemini$",
        r"^spec-kitty agent action review WP01 --agent claude$",
        r"^spec-kitty agent action review --agent gemini$",
        r"^spec-kitty agent status emit WP01 --to claimed --actor claude$",
        r"^spec-kitty agent status materialize$",
        r"^spec-kitty agent status materialize --json$",
        r"^spec-kitty agent status doctor$",
        r"^spec-kitty agent status doctor --stale-claimed-days 3 --json$",
        r"^spec-kitty agent status validate$",
        r"^spec-kitty agent status validate --json$",
        r"^spec-kitty agent status reconcile --dry-run$",
    )
    for pattern in forbidden_example_lines:
        assert re.search(pattern, agent_reference, flags=re.MULTILINE) is None


def test_orchestrator_api_envelope_width_unchanged():
    """The orchestrator-api envelope must remain the canonical 7-key shape.

    Authority: spec.md C-010.
    """
    from specify_cli.orchestrator_api.envelope import make_envelope

    envelope = make_envelope("test-cmd", success=True, data={})
    expected_keys = {
        "contract_version",
        "command",
        "timestamp",
        "correlation_id",
        "success",
        "error_code",
        "data",
    }
    assert set(envelope.keys()) == expected_keys, (
        f"Orchestrator-api envelope keys must remain exactly {expected_keys}; got {set(envelope.keys())}. "
        "Authority: spec.md C-010."
    )
    assert len(envelope) == 7, (
        f"Orchestrator-api envelope must remain exactly 7 keys; got {len(envelope)}. "
        "Authority: spec.md C-010."
    )


def test_grep_guards_do_not_scan_historical_artifacts():
    """Verify the grep guard scope excludes historical artifacts.

    Authority: spec.md FR-022 and C-011.
    """
    for group in (CLI_COMMAND_GLOBS, DOCTRINE_SKILL_GLOBS, AGENT_DOC_GLOBS):
        for pattern in group:
            normalized = pattern.replace("\\", "/")
            for forbidden in FORBIDDEN_SCAN_ROOTS:
                assert forbidden not in normalized, (
                    f"Guard scan pattern {pattern!r} must not target {forbidden!r}. "
                    "Authority: spec.md FR-022/C-011."
                )

    assert "CHANGELOG.md" not in AGENT_DOC_GLOBS, (
        "CHANGELOG.md must be handled through _extract_changelog_unreleased(), not a raw glob. "
        "Authority: spec.md FR-022."
    )
