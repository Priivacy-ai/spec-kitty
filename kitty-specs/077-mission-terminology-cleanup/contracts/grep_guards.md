# Contract: CI Grep Guards for Terminology Drift

**Mission**: `077-mission-terminology-cleanup`
**Surface**: `tests/contract/test_terminology_guards.py` (new file)
**Owner**: Scope A (`#241`), specifically WPA6 + WPA7
**Authority**: FR-022, C-011, spec §12.2

## Purpose

These grep guards exist to prevent the canonical terminology drift from returning. They are **not** historical-artifact rewriters: they **must not** scan `kitty-specs/**` (mission specs and history) or `architecture/**` (ADRs and initiative records). Historical artifacts are append-only history; rewriting them is forbidden by C-011.

The guards run in CI as part of the standard pytest suite. When a future PR re-introduces a forbidden pattern in a live first-party surface, the guard fires and the build fails.

## Scope

Per spec FR-022, the guards scan **live first-party surfaces** including the top-level project files. Historical artifacts and runtime state are explicitly excluded.

| Path | Scanned? | Why |
|---|---|---|
| `src/specify_cli/cli/commands/**/*.py` | Yes | Live CLI command surface |
| `src/specify_cli/orchestrator_api/**/*.py` | Yes (read-only verification) | Verifies orchestrator-api stays canonical (C-010) |
| `src/doctrine/skills/**/*.md` | Yes | Live doctrine skills |
| `docs/**/*.md` | Yes | Live first-party docs of every kind; `docs/migration/**` is excluded separately |
| `README.md` (top-level) | Yes | Live primary user-facing doc — explicitly in scope per FR-022 |
| `CONTRIBUTING.md` (top-level) | Yes | Live contributor doc — explicitly in scope per FR-022 |
| `CHANGELOG.md` (top-level) | **Partial** — only the "Unreleased" section above the first `## [<version>]` heading | Historical version entries are excluded by FR-022's "CHANGELOG-style historical entries" carve-out. The "Unreleased" section is live; everything below the first version heading is frozen history. |
| `docs/migration/**/*.md` | **No** | Migration docs are *required* to mention the deprecated flags by name (this is where the warning text points) |
| `kitty-specs/**` | **No** | Historical mission artifacts; FR-022, C-011 |
| `architecture/**` | **No** | Historical ADRs and initiatives; FR-022, C-011 |
| `.kittify/**` | **No** | Runtime state |
| `tests/**` | **No** | Tests legitimately mention forbidden patterns to assert against them |
| `kitty-specs/077-mission-terminology-cleanup/**` | **No** | This mission's own artifacts mention forbidden patterns by necessity |

## Guard Definitions

### Guard 1: No `--mission-run` for tracked-mission selection in live CLI command files

```python
def test_no_mission_run_alias_in_tracked_mission_selectors():
    """Live CLI command files must not declare --mission-run as an alias for tracked-mission selection.

    Authority: FR-002, FR-003, spec §12.2.
    Excludes runtime/session command files (which may legitimately accept --mission-run).
    """
    # Pseudocode:
    for path in glob("src/specify_cli/cli/commands/**/*.py"):
        if "runtime" in path or "session" in path:
            continue  # Runtime/session commands legitimately use --mission-run
        content = read(path)
        # Match: typer.Option(..., "--mission-run", ...) where "--mission-run" is not the canonical primary
        # Allow only if the surrounding parameter's name implies runtime/session context.
        for match in re.finditer(r'typer\.Option\([^)]*"--mission-run"[^)]*\)', content):
            param_context = _surrounding_param_name(content, match)
            if not _is_runtime_session_param(param_context):
                fail(f"{path}: --mission-run used as tracked-mission selector alias at offset {match.start()}")
```

### Guard 2: No "Mission run slug" in tracked-mission CLI help text

```python
def test_no_mission_run_slug_help_text_in_cli_commands():
    """Live CLI command help text must not say 'Mission run slug' for tracked-mission selectors.

    Authority: FR-008, spec §12.2.
    """
    for path in glob("src/specify_cli/cli/commands/**/*.py"):
        content = read(path)
        if "Mission run slug" in content:
            fail(f"{path}: contains 'Mission run slug' help text; tracked-mission selectors must say 'Mission slug'")
```

### Guard 3: No visible `--feature` declarations in CLI command files

```python
def test_no_visible_feature_alias_in_cli_commands():
    """--feature is acceptable only as a hidden=True alias.

    Authority: Charter §Terminology Canon hyper-vigilance rules,
    spec §11.1 (hidden deprecated alias), Charter Reconciliation in plan.md.
    """
    for path in glob("src/specify_cli/cli/commands/**/*.py"):
        content = read(path)
        for option_block in _iter_typer_option_blocks(content):
            if '"--feature"' not in option_block:
                continue
            if "hidden=True" not in option_block:
                fail(f"{path}: --feature declared without hidden=True; charter requires hidden secondary alias only")
```

### Guard 4: No `--mission-run` instructions in live doctrine skills

```python
def test_no_mission_run_instructions_in_doctrine_skills():
    """Doctrine skills must teach --mission for tracked-mission selection.

    Authority: FR-009, spec §12.2.
    Scope: src/doctrine/skills/**/*.md only.
    Excludes: kitty-specs/**, architecture/**, .kittify/**, this mission's own artifacts.
    """
    forbidden_patterns = [
        r"--mission-run\s+\d{3}",  # --mission-run 077-foo (tracked-mission slug pattern)
        r"--mission-run\s+<slug>",
        r"--mission-run\s+<mission",
    ]
    for path in glob("src/doctrine/skills/**/*.md"):
        content = read(path)
        for pattern in forbidden_patterns:
            for match in re.finditer(pattern, content):
                fail(f"{path}: doctrine skill instructs --mission-run for tracked-mission selection at offset {match.start()}")
```

### Guard 5: No `--mission-run` instructions in live agent-facing docs

```python
def test_no_mission_run_instructions_in_agent_facing_docs():
    """Live docs must teach --mission for tracked-mission selection.

    Authority: FR-010, FR-022, spec §12.2.
    Scope: docs/**, top-level README.md, top-level CONTRIBUTING.md, and the
    Unreleased section of top-level CHANGELOG.md.
    EXCLUDES: docs/migration/** (migration docs may name --feature and
    --mission-run by necessity).
    """
    forbidden_patterns = [
        r"--mission-run\s+\d{3}",
        r"--mission-run\s+<slug>",
        r"--mission-run\s+<mission",
    ]
    scan_targets: list[Path] = []
    for glob_pattern in ["docs/**/*.md"]:
        scan_targets.extend(_glob(glob_pattern))
    scan_targets = [
        path for path in scan_targets
        if not path.relative_to(REPO_ROOT).as_posix().startswith("docs/migration/")
    ]
    for top_level in ["README.md", "CONTRIBUTING.md"]:
        path = REPO_ROOT / top_level
        if path.exists():
            scan_targets.append(path)
    # CHANGELOG.md: only the Unreleased section above the first version header.
    changelog_path = REPO_ROOT / "CHANGELOG.md"
    if changelog_path.exists():
        scan_targets.append(("changelog-unreleased", changelog_path))

    for target in scan_targets:
        if isinstance(target, tuple) and target[0] == "changelog-unreleased":
            content = _extract_changelog_unreleased(target[1])
            path = target[1]
        else:
            path = target
            content = _read(path)
        for pattern in forbidden_patterns:
            for match in re.finditer(pattern, content):
                fail(f"{path}: instructs --mission-run for tracked-mission selection at offset {match.start()}")
```

### Guard 5b: No live `--feature` instructions in first-party docs

```python
def test_no_feature_flag_in_live_first_party_docs():
    """Live first-party docs must not document --feature as a
    current/canonical CLI option.

    Authority: FR-005, FR-022, charter §Terminology Canon hyper-vigilance.
    Scope: docs/**, top-level README.md, top-level CONTRIBUTING.md, and the
    Unreleased section of top-level CHANGELOG.md.
    EXCLUDES: docs/migration/** (migration docs name --feature by necessity)
    and historical version sections of CHANGELOG.md.

    A future PR that legitimately needs to mention --feature in a live top-level
    doc (e.g., to point users at the migration doc) must do so by linking to
    docs/migration/feature-flag-deprecation.md, not by documenting --feature
    as a usable option. The guard fails on raw `--feature <slug>`,
    `--feature ` followed by a slug-like token, and `--feature` inside an
    Options table column.
    """
    forbidden_patterns = [
        r"--feature\s+<slug>",
        r"--feature\s+\d{3}",
        r"--feature\s+[a-z][a-z0-9-]*",  # `--feature` followed by a slug-like token
        r"\|\s*`--feature[\s|<>`]",       # `--feature` cell in a markdown options table
    ]
    scan_targets: list[Path | tuple[str, Path]] = []
    for path in _glob("docs/**/*.md"):
        if path.relative_to(REPO_ROOT).as_posix().startswith("docs/migration/"):
            continue
        scan_targets.append(path)
    for top_level in ["README.md", "CONTRIBUTING.md"]:
        path = REPO_ROOT / top_level
        if path.exists():
            scan_targets.append(path)
    changelog_path = REPO_ROOT / "CHANGELOG.md"
    if changelog_path.exists():
        scan_targets.append(("changelog-unreleased", changelog_path))

    for target in scan_targets:
        if isinstance(target, tuple) and target[0] == "changelog-unreleased":
            content = _extract_changelog_unreleased(target[1])
            path = target[1]
        else:
            path = target
            content = _read(path)
        for pattern in forbidden_patterns:
            for match in re.finditer(pattern, content):
                snippet = content[max(0, match.start() - 30):match.end() + 30]
                fail(
                    f"{path}: documents --feature as a live CLI option at "
                    f"offset {match.start()}: {snippet!r}\n"
                    f"Authority: spec §11.1, charter §Terminology Canon. "
                    f"Replace with --mission or link to docs/migration/feature-flag-deprecation.md."
                )
```

### Helper: extract the Unreleased section from CHANGELOG.md

```python
def _extract_changelog_unreleased(path: Path) -> str:
    """Return the portion of CHANGELOG.md above the first `## [<version>]` heading.

    The `## [Unreleased]` section (if present) and any preamble are returned;
    historical version entries are excluded per FR-022.
    """
    content = _read(path)
    # Match `## [<version>]` where <version> looks like 1.2.3 or 1.2.3a4
    match = re.search(r"^## \[\d+\.\d+\.\d+", content, flags=re.MULTILINE)
    if match is None:
        # No version headings yet — the whole file is "unreleased"
        return content
    return content[: match.start()]
```

### Guard 6: Inverse drift — `--mission` not used to mean blueprint/template

```python
def test_no_mission_used_to_mean_mission_type_in_cli_commands():
    """CLI command files must not declare --mission with help text that names a mission type.

    Authority: FR-021, spec §8.1.2, spec §12.2.
    The check is heuristic: if a typer.Option declares --mission and its help string
    contains 'mission type' or 'mission key', that is the inverse-drift bug. Such
    sites must instead declare --mission-type as canonical with --mission as a
    hidden alias.
    """
    for path in glob("src/specify_cli/cli/commands/**/*.py"):
        content = read(path)
        for option_block in _iter_typer_option_blocks(content):
            if '"--mission"' not in option_block:
                continue
            help_text = _extract_help(option_block)
            if any(phrase in help_text.lower() for phrase in ["mission type", "mission key"]):
                if '"--mission-type"' not in option_block:
                    fail(f"{path}: --mission declared with mission-type semantics but no --mission-type canonical parameter present")
```

### Guard 7: Orchestrator-api envelope width unchanged (read-only verification)

```python
def test_orchestrator_api_envelope_width_unchanged():
    """The orchestrator-api 7-key envelope must not be widened by this or any future mission.

    Authority: C-010, spec §10.1 item 10.

    The expected key set is verified against the canonical implementation at
    src/specify_cli/orchestrator_api/envelope.py::make_envelope at HEAD
    35d43a25 (validated baseline 54269f7c). If make_envelope is intentionally
    changed in a future PR, this guard's expected_keys must be updated in the
    SAME PR after a documented C-010 amendment.
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
        f"Orchestrator-api envelope keys must remain exactly {expected_keys}; "
        f"got {set(envelope.keys())}. C-010 forbids widening."
    )
    # Reinforce the count check too, in case a future change replaces a key
    # rather than adding one (still a contract change that needs review).
    assert len(envelope) == 7, (
        f"Orchestrator-api envelope must remain exactly 7 keys; got {len(envelope)}."
    )
```

### Guard 8: Historical-artifact safety check (the meta-guard)

```python
def test_grep_guards_do_not_scan_historical_artifacts():
    """Verify the grep guards' scope excludes historical artifacts.

    Authority: FR-022, C-011.
    This test fails if any of the guard functions in this file accidentally
    scan kitty-specs/, architecture/, .kittify/, or CHANGELOG.md.

    Implementation: introspect the path globs declared at the top of each guard
    function and assert none of them resolve into the forbidden roots.
    """
    forbidden_roots = ["kitty-specs/", "architecture/", ".kittify/", "CHANGELOG.md"]
    # Inspect each guard's declared globs and fail if any glob would match a forbidden path.
```

## File Structure

```python
# tests/contract/test_terminology_guards.py
"""CI grep guards for canonical terminology drift.

These guards prevent the Mission Type / Mission / Mission Run terminology
boundary from drifting back to legacy selector vocabulary. They are scoped
to LIVE first-party surfaces only.

EXPLICITLY DOES NOT SCAN (per FR-022, C-011):
  - kitty-specs/** (historical mission artifacts)
  - architecture/** (historical ADRs and initiative records)
  - .kittify/** (runtime state)
  - tests/** (tests legitimately mention forbidden patterns)
  - CHANGELOG.md (historical change log)
  - docs/migration/** (migration docs explain the deprecation by name)

Authority:
  - spec.md FR-022, C-010, C-011
  - spec.md §12.2 Documentation and Skill Tests
  - charter.md §Terminology Canon hyper-vigilance rules
"""
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

# ---------- Helpers ----------

def _glob(pattern: str) -> list[Path]:
    return list(REPO_ROOT.glob(pattern))

def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def _iter_typer_option_blocks(content: str):
    """Yield each typer.Option(...) call's text."""
    # ... implementation ...

# ---------- Guards ----------

def test_no_mission_run_alias_in_tracked_mission_selectors():
    ...

def test_no_mission_run_slug_help_text_in_cli_commands():
    ...

def test_no_visible_feature_alias_in_cli_commands():
    ...

def test_no_mission_run_instructions_in_doctrine_skills():
    ...

def test_no_mission_run_instructions_in_agent_facing_docs():
    ...

def test_no_feature_flag_in_live_top_level_docs():
    ...

def test_no_mission_used_to_mean_mission_type_in_cli_commands():
    ...

def test_orchestrator_api_envelope_width_unchanged():
    ...

def test_grep_guards_do_not_scan_historical_artifacts():
    ...
```

The full guard count is **9** test functions (the original 8 plus Guard 5b for top-level project docs).

## Failure Messages

Every guard's failure message must:
1. Name the file path that triggered the failure.
2. Name the offset or line number of the offending content.
3. Cite the FR or C number from the spec that the failure violates.
4. Suggest the canonical replacement.

Example:
```
FAILED tests/contract/test_terminology_guards.py::test_no_visible_feature_alias_in_cli_commands

src/specify_cli/cli/commands/agent/tasks.py:842: --feature declared without hidden=True

Authority: spec.md FR-005, charter §Terminology Canon hyper-vigilance.
Fix: declare --feature as a separate typer.Option with hidden=True, then call
resolve_selector() from the function body. See contracts/selector_resolver.md
for the canonical pattern.
```

## What These Guards Do NOT Do

- They do not modify any file. They are read-only.
- They do not auto-fix. A human (or a future agent under explicit instruction) must fix flagged sites.
- They do not enforce documentation completeness. They only enforce that *if* a doc mentions tracked-mission selection, it does so with canonical vocabulary.
- They do not scan historical artifacts. C-011 forbids this. Guard 8 verifies the scope is correct.

## Maintenance

Future PRs that legitimately need to introduce a new pattern (e.g., a new alias for a different reason) must update both the guard and the contract test in the same PR. Reviewers should treat any PR that adds an `# noqa` or skip marker on these guards with extreme suspicion — the whole point is to prevent silent drift.
