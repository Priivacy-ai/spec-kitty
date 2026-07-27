# Phase 1 Data Model: Post-Merge Reliability And Release Hardening

**Mission**: 068-post-merge-reliability-and-release-hardening
**Date**: 2026-04-07

This document defines the dataclasses, event shapes, and configuration schemas introduced by the mission. Every type listed here is consumed by at least one FR.

---

## WP01 — Stale-assertion analyzer

### `StaleAssertionFinding`

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

Confidence = Literal["high", "medium", "low"]

@dataclass(frozen=True)
class StaleAssertionFinding:
    test_file: Path                # absolute path to the test file
    test_line: int                 # 1-indexed line of the suspect assertion
    source_file: Path              # absolute path to the source file that changed
    source_line: int               # 1-indexed line of the changed source identifier
    changed_symbol: str            # the identifier or literal that changed
    confidence: Confidence         # "high" | "medium" | "low" — never "definitely_stale"
    hint: str                      # one-line human-readable explanation
```

**Validation rules**:
- `confidence` MUST be one of the three literal values; the analyzer SHALL NEVER produce a `definitely_stale` value (FR-003).
- `hint` is a single line, no newlines.
- All paths are absolute (per CLAUDE.md path-reference rule).

**Source**: produced by `run_check(...)` in `src/specify_cli/post_merge/stale_assertions.py`.

### `StaleAssertionReport`

```python
@dataclass(frozen=True)
class StaleAssertionReport:
    base_ref: str
    head_ref: str
    repo_root: Path
    findings: list[StaleAssertionFinding]
    elapsed_seconds: float          # for NFR-001 self-reporting
    files_scanned: int
    findings_per_100_loc: float     # for NFR-002 self-monitoring
```

**Validation rules**:
- `findings` MAY be empty.
- `elapsed_seconds` and `files_scanned` are populated for self-reporting; the CLI subcommand and the merge runner both display these.
- `findings_per_100_loc` is computed against the diff size between `base_ref` and `head_ref`; used by FR-022 to detect when WP01 is exceeding NFR-002.

---

## WP02 — Merge strategy + status-events safe_commit

### `MergeStrategy`

```python
from enum import Enum

class MergeStrategy(str, Enum):
    MERGE = "merge"
    SQUASH = "squash"
    REBASE = "rebase"
```

**Resolution order** (FR-005, FR-006, FR-008):
1. CLI flag `--strategy` (highest precedence)
2. `.kittify/config.yaml` `merge.strategy` key
3. Default: `MergeStrategy.SQUASH` (per C-001)

### `MergeConfig` (extends existing `.kittify/config.yaml` schema)

The existing config schema gains a new `merge` section:

```yaml
# .kittify/config.yaml
merge:
  strategy: squash    # one of: merge | squash | rebase
```

**Schema rules**:
- `merge.strategy` is optional; absence means "use the squash default."
- If present, value MUST be one of `merge`, `squash`, `rebase`. Any other value SHALL produce a startup error from the merge command (not silent fallback).
- Read via existing `ruamel.yaml` infrastructure.

### Status event shape (canonical, unchanged — what FR-019 commits)

The `done` events that FR-019 must commit have the canonical shape established by spec-kitty 3.0+:

```python
# One JSONL line per event in kitty-specs/<mission>/status.events.jsonl
{
    "actor": "merge",
    "at": "2026-04-07T07:32:00+00:00",
    "event_id": "01HXYZ...",
    "evidence": null,
    "execution_mode": "worktree",
    "feature_slug": "068-post-merge-reliability-and-release-hardening",
    "force": false,
    "from_lane": "for_review",
    "reason": null,
    "review_ref": null,
    "to_lane": "done",
    "wp_id": "WP01"
}
```

**WP02's responsibility**: ensure these events, written by `_mark_wp_merged_done`, are persisted to git via `safe_commit` before any subsequent step that could discard the working tree.

### Push-error parser token list (FR-009)

```python
LINEAR_HISTORY_REJECTION_TOKENS: tuple[str, ...] = (
    "merge commits",       # GitHub default
    "linear history",      # GitHub branch protection
    "fast-forward only",   # generic linear-history rejection
    "GH006",               # GitHub error code for branch-protection rejection
    "non-fast-forward",    # generic git rejection
)
```

**Matching rule**: case-insensitive substring match against captured `git push` stderr. If any token matches, emit the remediation hint pointing at `--strategy squash` and the `merge.strategy` config key. If no token matches, fail open (no hint emitted).

---

## WP03 — Diff-coverage validation report

### `DiffCoverageValidationReport`

```python
@dataclass(frozen=True)
class DiffCoverageValidationReport:
    validated_at_commit: str        # commit SHA at validation time
    workflow_path: Path             # absolute path to ci-quality.yml
    sample_pr_description: str      # what large PR was used as the validation sample
    critical_path_threshold: float  # current enforced threshold
    full_diff_threshold: float      # advisory threshold
    enforced_surface_correct: bool  # does the enforce/advisory split match policy intent?
    findings: list[str]             # list of policy mismatches if any
    decision: Literal["close_with_evidence", "tighten_workflow"]
    rationale: str                  # one-paragraph explanation
```

**Storage**: written to `kitty-specs/068-post-merge-reliability-and-release-hardening/wp03-validation-report.md` (markdown rendering of the dataclass) per FR-010. Used to drive the FR-011 / FR-012 fork.

---

## WP04 — Release prep payload

### `ReleasePrepPayload`

```python
@dataclass(frozen=True)
class ReleasePrepPayload:
    channel: Literal["alpha", "beta", "stable"]
    current_version: str            # e.g., "3.1.0a7"
    proposed_version: str           # e.g., "3.1.0a8" or "3.1.0b1"
    changelog_block: str            # multi-line markdown ready to paste into CHANGELOG.md
    mission_slug_list: list[str]    # missions included in this release window
    target_branch: str              # always "main" for spec-kitty core
    structured_inputs: dict[str, str]  # name->value pairs for the release tag/PR workflow
```

**Validation rules**:
- `channel` MUST be one of the three literals.
- `proposed_version` MUST be derivable from `current_version` + `channel` per existing version-bump rules.
- `mission_slug_list` is built by scanning `kitty-specs/` for missions accepted since the previous release tag (commit-walked locally — no network calls per FR-014).
- `changelog_block` is built from each mission's `meta.json`, `spec.md` title, and accepted-WP titles. Format mirrors existing `CHANGELOG.md` style.
- `structured_inputs` is JSON-serializable; consumed by `gh release create` or the existing release workflow.

### CLI output mode (FR-015)

The same `ReleasePrepPayload` is rendered two ways:
- **Text mode** (default): rich-formatted, human-readable, includes diffs against current `pyproject.toml` version.
- **JSON mode** (`--json`): the dataclass serialized via `dataclasses.asdict`, ready for downstream automation.

---

## WP05 — Recovery extension + verification + ledger

### `scan_recovery_state` — new keyword parameter (function surface, not a dataclass)

`scan_recovery_state` currently accepts `(repo_root, mission_slug)`. WP05 extends it with an optional source-of-truth parameter that controls whether to consult status events:

```python
def scan_recovery_state(
    repo_root: Path,
    mission_slug: str,
    *,
    consult_status_events: bool = True,   # NEW: defaults to True
) -> RecoveryState:
    ...
```

When `consult_status_events=True` (the default after FR-021 lands), the function:
1. Reads `kitty-specs/<mission>/status.events.jsonl`
2. Materializes the lane snapshot for every WP
3. For WPs whose lane is `done` and whose lane branches are absent, marks them as "merged-and-deleted" rather than "missing"
4. For downstream WPs whose dependencies are all `done`, returns "ready to start from target branch tip"

The existing live-branch path remains valid for in-progress missions where lane branches still exist.

### `implement` command — new `--base` CLI flag (typer Option, not a dataclass)

```python
# spec-kitty implement WP## [--base <ref>]
@app.command()
def implement(
    wp_id: str,
    base: Optional[str] = typer.Option(None, "--base", help="Explicit base ref for the lane workspace (default: auto-detect)"),
) -> None:
    ...
```

Validation:
- `--base` accepts any valid git ref the local repo can resolve.
- When omitted, the existing auto-detect logic runs (unchanged).
- When provided, the lane workspace is created with `git worktree add --branch <new-branch> <path> <base>`.

### `RecoveryVerificationEntry`

```python
@dataclass(frozen=True)
class RecoveryVerificationEntry:
    failure_shape: str              # short identifier for the failure mode being verified
    issue_id: str                   # "#415" or "#416"
    status: Literal["fixed_by_current_main", "fixed_by_this_mission", "residual_gap"]
    evidence_path: Path             # absolute path to the test, log, or diff that proves the status
    regression_test: Path | None    # absolute path to the regression test, if one was added
    notes: str                      # one-paragraph context
```

**Storage**: a list of these is written to `kitty-specs/068-post-merge-reliability-and-release-hardening/wp05-verification-report.md` per FR-016.

### `MissionCloseLedgerRow`

```python
@dataclass(frozen=True)
class MissionCloseLedgerRow:
    issue_id: str                                # e.g., "#454"
    decision: Literal["closed_with_evidence", "narrowed_to_followup"]
    reference: str                               # PR URL, commit SHA, or follow-up issue link
    notes: str                                   # one-paragraph context
```

**Storage**: a list of these is rendered as a markdown table at `kitty-specs/068-post-merge-reliability-and-release-hardening/mission-close-ledger.md` per C-005 and the entity definition. Required for DoD-4 to be mechanically checkable: every issue in the Tracked GitHub Issues table SHALL have exactly one row in this ledger.

---

## State transitions (no new ones)

This mission does NOT introduce new lane states or new event shapes. The 7-lane state machine documented in `CLAUDE.md` is unchanged. The FR-019 fix is purely a persistence-time change (commit what's already being written) — it does not alter what is written.

---

## Cross-reference: FR → dataclass

| FR | Dataclass(es) |
|---|---|
| FR-001, FR-003, FR-004 | `StaleAssertionFinding`, `StaleAssertionReport` |
| FR-002 | `StaleAssertionFinding` (worked-example shape encoded in confidence rules) |
| FR-005, FR-006, FR-007, FR-008 | `MergeStrategy`, `MergeConfig` |
| FR-009 | `LINEAR_HISTORY_REJECTION_TOKENS` |
| FR-010, FR-011, FR-012 | `DiffCoverageValidationReport` |
| FR-013, FR-014, FR-015 | `ReleasePrepPayload` |
| FR-023 | `ReleasePrepPayload.structured_inputs` (carries the close-comment scope-cut metadata) |
| FR-016, FR-017 | `RecoveryVerificationEntry` |
| FR-018 | `MissionCloseLedgerRow` |
| FR-019, FR-020 | Status event shape (canonical, unchanged) |
| FR-021 | `scan_recovery_state` keyword parameter (function surface), `implement --base` typer option (CLI surface), `RecoveryState.ready_to_start_from_target` (new field) |
| FR-022 | `StaleAssertionReport.findings_per_100_loc` (self-monitoring threshold) |
| C-005 | `MissionCloseLedgerRow` (the constraint mandates the ledger; the dataclass is the row schema) |
