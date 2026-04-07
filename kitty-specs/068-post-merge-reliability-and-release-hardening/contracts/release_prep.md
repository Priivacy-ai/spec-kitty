# Contract: WP04 Release Prep CLI

**Owns**: FR-013, FR-014, FR-015, FR-023 + NFR-004

## CLI surface

**Command path**: `spec-kitty agent release prep`

**File**: `src/specify_cli/cli/commands/agent/release.py` (currently a stub; WP04 populates it)

```python
"""Release packaging commands for AI agents."""
import typer
from pathlib import Path
from rich.console import Console
from specify_cli.release.payload import build_release_prep_payload
from specify_cli.release.payload import ReleasePrepPayload, ReleaseChannel

app = typer.Typer(
    name="release",
    help="Release packaging commands for AI agents",
    no_args_is_help=True,
)
console = Console()

@app.command("prep")
def prep(
    channel: ReleaseChannel = typer.Option(..., "--channel", help="Release channel: alpha | beta | stable"),
    repo_root: Path = typer.Option(Path("."), "--repo", help="Repository root"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON instead of human-readable text"),
) -> None:
    """Prepare release artifacts (changelog draft, version bump, structured inputs)."""
    payload = build_release_prep_payload(
        channel=channel,
        repo_root=repo_root.resolve(),
    )
    if json_output:
        import json as _json
        from dataclasses import asdict
        console.print_json(_json.dumps(asdict(payload)))
    else:
        # Rich rendering: version diff, changelog block, mission slug list, structured inputs table
        ...
```

## Internal package

**Module tree**: `src/specify_cli/release/` (**locked decision** — not optional)

```
src/specify_cli/release/
├── __init__.py
├── changelog.py    # build_changelog_block(missions: list[Path]) -> str
├── version.py      # propose_version(current: str, channel: ReleaseChannel) -> str
└── payload.py      # build_release_prep_payload(channel, repo_root) -> ReleasePrepPayload
```

The package split is committed at plan time. Three concerns (changelog, version, payload) cleanly map to three modules. The "if it stays small enough, inline it" optimization is rejected as a deferred decision the WP04 implementer would face at code time and resent.

## Library functions

```python
# src/specify_cli/release/changelog.py
from pathlib import Path

def build_changelog_block(repo_root: Path, since_tag: str | None = None) -> tuple[str, list[str]]:
    """Build a draft changelog block from kitty-specs/ artifacts.

    Returns:
      (changelog_markdown, mission_slug_list)

    Algorithm:
      1. Find missions in kitty-specs/ accepted since `since_tag` (or since the most recent
         git tag if not specified)
      2. For each mission, read meta.json and spec.md to get title and friendly name
      3. For each mission, walk its tasks/ directory for accepted WP files and extract titles
      4. Render a markdown block grouping missions and their WPs

    No network calls. Uses git locally to determine the previous tag.
    """
```

```python
# src/specify_cli/release/version.py
from typing import Literal

ReleaseChannel = Literal["alpha", "beta", "stable"]

def propose_version(current: str, channel: ReleaseChannel) -> str:
    """Compute the next version string per channel.

    Examples:
      propose_version("3.1.0a7", "alpha") == "3.1.0a8"
      propose_version("3.1.0a7", "beta")  == "3.1.0b1"
      propose_version("3.1.0a7", "stable") == "3.1.0"
      propose_version("3.1.0", "stable")   == "3.1.1"

    Bump-level rules:
      - alpha: increments alpha number (3.1.0a7 → 3.1.0a8)
      - beta: starts a fresh beta line if current is alpha (3.1.0a7 → 3.1.0b1),
        otherwise increments beta number (3.1.0b1 → 3.1.0b2)
      - stable: drops the prerelease suffix if current is alpha/beta
        (3.1.0a7 → 3.1.0); otherwise **always proposes a patch bump**
        (3.1.0 → 3.1.1)

    Stable→stable always proposes a patch bump. Minor or major bumps
    require manual editing of pyproject.toml before running release prep.
    This matches spec-kitty's actual release cadence (mostly alpha
    increments and patches); a `--bump-level` parameter would be dead
    weight 99% of the time and is intentionally omitted.
    """
```

```python
# src/specify_cli/release/payload.py
from dataclasses import dataclass
from pathlib import Path
from .version import ReleaseChannel

@dataclass(frozen=True)
class ReleasePrepPayload:
    channel: ReleaseChannel
    current_version: str
    proposed_version: str
    changelog_block: str
    mission_slug_list: list[str]
    target_branch: str
    structured_inputs: dict[str, str]

def build_release_prep_payload(
    channel: ReleaseChannel,
    repo_root: Path,
) -> ReleasePrepPayload:
    """Assemble the full release-prep payload.

    Reads:
      - pyproject.toml for current version
      - kitty-specs/ for missions since previous tag
      - .git for the previous tag

    Returns: a fully-populated ReleasePrepPayload ready to render or serialize.
    Performance: ≤ 5 seconds wall-clock on a mission with up to 16 WPs (NFR-004).
    """
```

## Local-only constraint (FR-014)

Every code path in WP04's package SHALL be testable without network access. Specifically:

- `build_changelog_block` reads `kitty-specs/` and `git tag --list` only.
- `propose_version` reads `pyproject.toml` only.
- `build_release_prep_payload` orchestrates the above; no GitHub API, no PyPI checks.

Network-touching steps (creating the actual release PR, pushing the tag, monitoring the workflow) are **out of scope per FR-023**. Maintainers do those steps manually with the `structured_inputs` payload as a guide.

## #457 close-comment scope-cut (FR-023)

When WP04 closes #457, the comment SHALL document exactly:

**Automated by this mission**:
- Changelog draft (via `build_changelog_block`)
- Version bump proposal (via `propose_version`)
- Structured release-prep payload (`structured_inputs`)
- JSON output mode for downstream automation

**Still manual**:
- PR creation (use `gh pr create` with the changelog block)
- Tag push (use `git tag -a vX.Y.Z -m "..." && git push origin vX.Y.Z`)
- Release workflow monitoring (use `gh run watch`)

If #457's reporter requests automation of the still-manual steps, those SHALL be filed as a follow-up issue.

## Test surface

**File**: `tests/cli/commands/agent/test_release_prep.py`

| Test | FR / NFR | Asserts |
|---|---|---|
| `test_prep_command_emits_text_by_default` | FR-013 | running `prep` produces a rich-formatted summary |
| `test_prep_command_emits_json_with_flag` | FR-015 | `--json` produces a parseable JSON document with all fields |
| `test_changelog_built_from_local_artifacts_only` | FR-014 | the test runs successfully with no network access (NFR-005) |
| `test_payload_no_github_api_calls` | FR-014, C-002 | a `requests.get`/`urlopen` mock asserts zero network calls |
| `test_propose_version_alpha_increments_alpha` | FR-013 | `3.1.0a7` + alpha → `3.1.0a8` |
| `test_propose_version_alpha_to_beta_starts_beta1` | FR-013 | `3.1.0a7` + beta → `3.1.0b1` |
| `test_propose_version_alpha_to_stable` | FR-013 | `3.1.0a7` + stable → `3.1.0` |
| `test_runs_within_5s_for_16_wps` | NFR-004 | benchmark fails if elapsed > 5s on a synthetic 16-WP mission |
| `test_close_comment_scope_cut_documented` | FR-023 | the rendered output (or a separate close-comment helper) lists automated vs manual steps |
