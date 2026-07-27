# Contract: WP02 Merge Strategy + Status-Events Safe Commit

**Owns**: FR-005, FR-006, FR-007, FR-008, FR-009, FR-019, FR-020 + NFR-003

## CLI surface (FR-005, FR-006)

**File**: `src/specify_cli/cli/commands/merge.py`

The existing `--strategy` typer parameter is currently declared but discarded before reaching the lane-merge implementation. WP02 wires it through.

```python
import typer
from specify_cli.lanes.merge import run_lane_based_merge
from specify_cli.config import load_merge_config
from specify_cli.lanes.merge import MergeStrategy

@app.command()
def merge(
    feature: str = typer.Option(None, "--feature"),
    strategy: Optional[MergeStrategy] = typer.Option(
        None,
        "--strategy",
        help="Merge strategy: merge | squash | rebase. Default: squash for mission→target.",
    ),
    resume: bool = typer.Option(False, "--resume"),
    abort: bool = typer.Option(False, "--abort"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Run a feature merge with explicit strategy support."""

    # Resolution order: CLI flag > config > default(SQUASH)
    resolved_strategy = (
        strategy
        or load_merge_config(repo_root).strategy
        or MergeStrategy.SQUASH
    )

    run_lane_based_merge(
        feature=feature,
        repo_root=repo_root,
        strategy=resolved_strategy,
        ...,
    )
```

**Key contract**: `--strategy` is no longer silently discarded. The flag value flows from the CLI into `_run_lane_based_merge` and determines the git command sequence used for the **mission→target** step.

## Lane→mission semantics (FR-007)

Lane→mission merges retain their existing **merge-commit** behavior. They are local, never hit branch protection, and are valuable as preserved lane structure on the mission branch.

**Implementation**: the strategy parameter passed to `run_lane_based_merge` applies ONLY to the final mission→target step. The internal `_merge_lane_into_mission` helper continues to use `git merge` (no-fast-forward) regardless of the strategy parameter.

## Project config (FR-008)

**File**: `.kittify/config.yaml` (existing file, new `merge` section)

```yaml
merge:
  strategy: squash    # one of: merge | squash | rebase
```

**Module**: `src/specify_cli/config.py` (existing) gains a `MergeConfig` accessor:

```python
from dataclasses import dataclass
from pathlib import Path
from specify_cli.lanes.merge import MergeStrategy

@dataclass
class MergeConfig:
    strategy: MergeStrategy | None = None

def load_merge_config(repo_root: Path) -> MergeConfig:
    """Read .kittify/config.yaml and return the merge section."""
    ...
```

**Validation**: if `merge.strategy` is present but not one of the three allowed values, `load_merge_config` raises a startup error (not silent fallback).

## Push-error parser (FR-009)

**Module**: `src/specify_cli/cli/commands/merge.py` (new helper)

```python
LINEAR_HISTORY_REJECTION_TOKENS: tuple[str, ...] = (
    "merge commits",
    "linear history",
    "fast-forward only",
    "GH006",
    "non-fast-forward",
)

def _is_linear_history_rejection(stderr: str) -> bool:
    """Return True if git push stderr indicates a linear-history rejection."""
    haystack = stderr.lower()
    return any(token.lower() in haystack for token in LINEAR_HISTORY_REJECTION_TOKENS)

def _emit_remediation_hint(console: Console) -> None:
    console.print(
        "\n[yellow]Push rejected by linear-history protection.[/yellow]\n"
        "Try [cyan]spec-kitty merge --strategy squash[/cyan], or set "
        "[cyan]merge.strategy: squash[/cyan] in [cyan].kittify/config.yaml[/cyan].\n"
    )
```

**Fail-open rule**: if `stderr` does not match any token, NO hint is emitted. This prevents misleading hints on unrelated push failures.

**Backstop role**: with squash as the default (FR-006), this parser is a backstop for users who explicitly opt into `--strategy merge`. It is NOT expected to fire on the default path.

## Status-events safe_commit fix (FR-019)

**File**: `src/specify_cli/cli/commands/merge.py` inside `_run_lane_based_merge`

**Insertion point**: after the per-WP `_mark_wp_merged_done` loop and before the worktree-removal step.

```python
from specify_cli.git import safe_commit

# ... (existing _mark_wp_merged_done loop) ...

# FR-019: Persist the done events to git so they survive any subsequent
# external merge rebuild (e.g., reset+squash for protected linear-history).
safe_commit(
    repo_path=main_repo,
    files_to_commit=[
        feature_dir / "status.events.jsonl",
        feature_dir / "status.json",
    ],
    commit_message=f"chore({mission_slug}): record done transitions for merged WPs",
    allow_empty=False,
)

# ... (existing worktree-removal step) ...
```

**Out of scope** (per spec "Scope (preempting 'what about MergeState?')" subsection):
- `.kittify/runtime/merge/<mission_id>/state.json` — intentionally ephemeral
- The `cleanup_merge_workspace`/`clear_state` calls at the end — runtime state, not the cause of the loss

## Regression test (FR-020)

**File**: `tests/cli/commands/test_merge_status_commit.py`

```python
import subprocess
from pathlib import Path
from specify_cli.cli.commands.merge import _run_lane_based_merge

def test_done_events_committed_to_git(synthetic_mission_repo):
    """FR-020: after _run_lane_based_merge returns, the done events for every
    merged WP are present in git history at HEAD, not just on disk."""
    repo, mission_slug, wps = synthetic_mission_repo  # fixture creates 2+ WPs

    # Run the merge end-to-end
    _run_lane_based_merge(...)

    # The proof: read status.events.jsonl from git, not from the working tree
    result = subprocess.run(
        ["git", "show", f"HEAD:kitty-specs/{mission_slug}/status.events.jsonl"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    events = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    done_wps = {e["wp_id"] for e in events if e["to_lane"] == "done"}

    assert done_wps == set(wps), (
        f"Expected done events for every merged WP. "
        f"Got {done_wps}, expected {set(wps)}. "
        f"This regression would mean FR-019's safe_commit step was missed."
    )
```

This test proves FR-019's contract directly: events are durably committed at the time the merge command returns. It does NOT use `git reset --hard HEAD` because that's a no-op for a file that's already at HEAD (the previous draft of FR-020 had this logical hole; the simpler direct assertion is mechanically correct).

## Test surface

| Test | FR / NFR | Asserts |
|---|---|---|
| `test_strategy_flag_flows_through` | FR-005 | `--strategy squash` passed to CLI reaches `_run_lane_based_merge` |
| `test_default_strategy_is_squash` | FR-006 | no flag, no config → squash applied |
| `test_lane_to_mission_uses_merge_commit` | FR-007 | `--strategy squash` does NOT change lane→mission semantics |
| `test_config_yaml_strategy_honored` | FR-008 | `merge.strategy: rebase` in config produces a rebase merge |
| `test_invalid_config_strategy_raises` | FR-008 | `merge.strategy: bogus` raises a startup error, not silent fallback |
| `test_push_rejection_emits_hint_for_known_tokens` | FR-009 | each of the 5 token strings triggers the remediation hint |
| `test_push_rejection_fails_open_for_unknown` | FR-009 | unrelated stderr does NOT emit a hint |
| `test_done_events_committed_to_git` | FR-019, FR-020 | end-to-end FR-020 regression |
| `test_protected_linear_history_succeeds_default` | NFR-003 | squash default succeeds against `require_linear_history = true` integration test |
