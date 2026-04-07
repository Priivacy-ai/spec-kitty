---
work_package_id: WP04
title: Release-Prep CLI
dependencies: []
requirement_refs:
- FR-013
- FR-014
- FR-015
- FR-023
- NFR-004
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-068-post-merge-reliability-and-release-hardening
base_commit: e361b104cbecf8fb24bf8c9f504d0f0868c14492
created_at: '2026-04-07T09:18:26.328723+00:00'
subtasks:
- T019
- T020
- T021
- T022
- T023
shell_pid: "62643"
agent: "claude:sonnet:reviewer:reviewer"
history:
- at: '2026-04-07T08:46:34Z'
  actor: claude
  action: created
authoritative_surface: src/specify_cli/release/
execution_mode: code_change
mission_number: '068'
mission_slug: 068-post-merge-reliability-and-release-hardening
owned_files:
- src/specify_cli/release/**
- src/specify_cli/cli/commands/agent/release.py
- tests/release/test_release_prep.py
priority: P1
status: planned
---

# WP04 — Release-Prep CLI

## Objective

Resolve issue [Priivacy-ai/spec-kitty#457](https://github.com/Priivacy-ai/spec-kitty/issues/457) by populating the existing `agent/release.py` stub with a real `prep` subcommand. The command produces a draft changelog from local `kitty-specs/` artifacts (no GitHub API calls), proposes a version bump per release channel, and emits both rich text and JSON. Documents the scope-cut in the #457 close comment so the issue can actually close.

## Context

`src/specify_cli/cli/commands/agent/release.py` is currently a stub typer app that's already registered at `agent/__init__.py:20` as a public CLI surface (`spec-kitty agent release` returns help text today). WP04 populates the stub with the `prep` subcommand. The implementation lives in a new `src/specify_cli/release/` package that splits cleanly into three modules: `version.py`, `changelog.py`, `payload.py`. **The package split is locked at plan time** — no inlining decision at code time.

**Key spec references**:
- FR-013: `prep --channel {alpha,beta,stable}` produces (a) draft changelog block, (b) proposed version bump, (c) inputs for the release tag/PR workflow
- FR-014: built from local artifacts only; NO network calls
- FR-015: text + JSON output modes
- FR-023: #457 close comment documents what's automated vs still-manual; manual gaps file follow-up issues
- NFR-004: ≤ 5 seconds wall-clock on a 16-WP mission
- C-002: NO GitHub API calls
- NFR-005: zero network calls in tests

**Key planning references**:
- `contracts/release_prep.md` for full signatures, the locked package split, and `propose_version` semantics including stable→stable patch rule
- `data-model.md` for `ReleasePrepPayload` shape
- `research.md` Decision 2 for the rationale (existing stub is registered, populate it)

## Branch Strategy

- **Planning/base branch**: `main`
- **Final merge target**: `main`
- **Execution worktree**: allocated by `spec-kitty implement WP04` and resolved from `lanes.json`.

To start work:
```bash
spec-kitty implement WP04
```

## Subtasks

### T019 — Create `release/version.py` with `propose_version` per locked rules

**Purpose**: Pure-functions module for version-string manipulation. Lands first because it's testable in isolation.

**Files**:
- New: `src/specify_cli/release/__init__.py`
- New: `src/specify_cli/release/version.py`

**Steps**:
1. Create `src/specify_cli/release/__init__.py` (re-exports added incrementally as later subtasks land)
2. Create `src/specify_cli/release/version.py` with:
   - `ReleaseChannel = Literal["alpha", "beta", "stable"]`
   - `propose_version(current: str, channel: ReleaseChannel) -> str` per the locked rules from `contracts/release_prep.md`:
     - alpha → increment alpha number (`3.1.0a7` → `3.1.0a8`)
     - beta → start fresh beta line if current is alpha (`3.1.0a7` → `3.1.0b1`); otherwise increment beta number (`3.1.0b1` → `3.1.0b2`)
     - stable → drop prerelease suffix if current is alpha/beta (`3.1.0a7` → `3.1.0`); otherwise patch bump (`3.1.0` → `3.1.1`)
3. **Locked**: stable→stable always proposes a patch bump. NO `--bump-level` parameter. Minor/major bumps require manual `pyproject.toml` editing. Document this in the docstring.
4. Use simple regex or `packaging.version` for parsing — no exotic dependency.

**Validation**: `python -c "from specify_cli.release.version import propose_version; print(propose_version('3.1.0a7', 'alpha'))"` returns `"3.1.0a8"`.

### T020 — Implement `release/changelog.py` `build_changelog_block`

**Purpose**: Build a draft changelog block from `kitty-specs/` artifacts and `git tag --list` only. Zero network access.

**Files**:
- New: `src/specify_cli/release/changelog.py`

**Steps**:
1. Define `build_changelog_block(repo_root: Path, since_tag: str | None = None) -> tuple[str, list[str]]`
2. Algorithm:
   - If `since_tag` is None, find the most recent tag matching `v*` via `git tag --list 'v*' --sort=-creatordate | head -1`
   - Find missions in `kitty-specs/` whose `meta.json` `created_at` is after `since_tag`'s commit date OR whose tasks contain accepted WPs since that date (use git log + meta.json `created_at` as the cheap proxy)
   - For each mission, read `meta.json` for `friendly_name` and `mission_number`
   - For each mission, read `spec.md` for the title/intent
   - For each mission, walk `tasks/WP*.md` and look at the frontmatter `status` field for accepted WPs
   - Render as a markdown block grouped by mission, with each WP listed under its mission heading
3. Return `(changelog_markdown, mission_slug_list)` where `mission_slug_list` is the slugs of missions included
4. **NO network calls**. NO `gh` invocations. Only `git tag --list` and filesystem reads.

**Files**: `src/specify_cli/release/changelog.py`

**Validation**: a synthetic kitty-specs/ fixture with 2 missions produces a changelog block listing both with their WPs.

### T021 — Implement `release/payload.py` `build_release_prep_payload`

**Purpose**: Orchestrate version + changelog + structured inputs into a single `ReleasePrepPayload` dataclass.

**Files**:
- New: `src/specify_cli/release/payload.py`

**Steps**:
1. Define `ReleasePrepPayload` dataclass per `data-model.md` (channel, current_version, proposed_version, changelog_block, mission_slug_list, target_branch, structured_inputs)
2. Define `build_release_prep_payload(channel: ReleaseChannel, repo_root: Path) -> ReleasePrepPayload`:
   - Read current version from `pyproject.toml` (use `tomllib` from stdlib in Python 3.11+)
   - Call `propose_version(current_version, channel)`
   - Call `build_changelog_block(repo_root)`
   - Build `structured_inputs` dict containing the values needed for the GitHub release tag/PR workflow:
     - `version`: proposed_version
     - `tag_name`: `f"v{proposed_version}"`
     - `release_title`: a derived title (e.g., `f"v{proposed_version} - <first mission name>"` or just `f"Release v{proposed_version}"`)
     - `release_notes_body`: the changelog_block (markdown)
     - `mission_slug_list`: comma-separated for the workflow input
   - `target_branch`: read from `meta.json` for the most recent mission (or hardcode `"main"` for spec-kitty)
3. Return the populated `ReleasePrepPayload`

**Files**: `src/specify_cli/release/payload.py`

**Validation**: `build_release_prep_payload("alpha", Path("."))` against the spec-kitty repo returns a populated payload with version `3.1.0a8` (or whatever's next from current).

### T022 — Populate `agent/release.py` stub with `prep` subcommand

**Purpose**: Replace the stub typer app with a real `prep` subcommand. Wire to the library functions. Update the stale comment.

**Files**:
- Modified: `src/specify_cli/cli/commands/agent/release.py`

**Steps**:
1. Read the current stub:
   ```python
   """Release packaging commands for AI agents."""
   import typer
   app = typer.Typer(name="release", help="Release packaging commands for AI agents", no_args_is_help=True)
   # Deep implementation in WP05
   ```
2. Replace it with a real implementation:
   ```python
   """Release packaging commands for AI agents."""
   import json as _json
   from dataclasses import asdict
   from pathlib import Path
   import typer
   from rich.console import Console
   from specify_cli.release.payload import build_release_prep_payload
   from specify_cli.release.version import ReleaseChannel

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
           console.print_json(_json.dumps(asdict(payload)))
       else:
           # Rich rendering: version table, changelog block, structured inputs
           ...
   ```
3. **Critical**: do NOT remove the `app = typer.Typer(...)` line or change `name="release"`. The registration in `agent/__init__.py:20` references it. WP04 does NOT touch `agent/__init__.py`.
4. The stale comment "Deep implementation in WP05" is now wrong (it referred to a prior mission's planning). Replace it with a brief docstring at module level explaining what `prep` does.

**Files**: `src/specify_cli/cli/commands/agent/release.py`

**Validation**: `spec-kitty agent release prep --help` returns the new help text. `spec-kitty agent release prep --channel alpha --json | jq .proposed_version` returns the expected next version string.

### T023 — Test suite covering FR-013/014/015/015a + NFR-004 + zero-network assertion

**Purpose**: Lock the WP04 contract.

**Files**:
- New: `tests/release/__init__.py`
- New: `tests/release/test_release_prep.py`

**Tests** (per `contracts/release_prep.md` test surface table):
- `test_prep_command_emits_text_by_default` — `spec-kitty agent release prep --channel alpha` produces a rich-formatted summary
- `test_prep_command_emits_json_with_flag` — `--json` produces a parseable JSON document with all `ReleasePrepPayload` fields
- `test_changelog_built_from_local_artifacts_only` — a synthetic fixture with no network access produces the changelog
- `test_payload_no_github_api_calls` — mock `urllib.request.urlopen`, `requests.get`, and any `gh` subprocess invocation to raise on call; assert the test passes
- `test_propose_version_alpha_increments_alpha` — `3.1.0a7` + alpha → `3.1.0a8`
- `test_propose_version_alpha_to_beta_starts_beta1` — `3.1.0a7` + beta → `3.1.0b1`
- `test_propose_version_beta_increments_beta` — `3.1.0b1` + beta → `3.1.0b2`
- `test_propose_version_alpha_to_stable` — `3.1.0a7` + stable → `3.1.0`
- `test_propose_version_stable_to_stable_patches` — `3.1.0` + stable → `3.1.1`
- `test_runs_within_5s_for_16_wps` — NFR-004 benchmark: build a synthetic 16-WP mission fixture and assert `build_release_prep_payload` returns within 5 seconds
- `test_close_comment_scope_cut_documented` — FR-023: a separate helper (or the rendered `--text` output) lists automated steps (changelog, version bump, payload) and still-manual steps (PR creation, tag push, workflow monitoring)

**Validation**: `pytest tests/release/test_release_prep.py -v` exits zero. Zero network calls.

## Test Strategy

Tests are required by the spec (FR-013/014/015/015a, NFR-004, NFR-005). The zero-network assertion (`test_payload_no_github_api_calls`) is critical — it locks FR-014/C-002 mechanically.

## Definition of Done

- [x] `src/specify_cli/release/` package exists with `version.py`, `changelog.py`, `payload.py`
- [x] `propose_version` implements all locked rules including stable→stable patch
- [x] `build_changelog_block` reads `kitty-specs/` and `git tag --list` only — no network
- [x] `build_release_prep_payload` returns a fully-populated `ReleasePrepPayload`
- [x] `agent/release.py` stub populated with the `prep` subcommand (text + JSON modes)
- [x] Stale "Deep implementation in WP05" comment removed/replaced
- [x] `agent/__init__.py` is NOT modified (the existing `release` registration still works)
- [x] All FR-013/014/015/015a tests pass
- [x] NFR-004 benchmark within 5s on synthetic 16-WP mission
- [x] Zero network calls (mocked)
- [x] `mypy --strict` passes
- [x] `ruff` clean
- [ ] #457 closed with the FR-023 scope-cut comment listing automated vs manual steps

## Risks

- **Don't delete the stub registration**: `agent/__init__.py:20` references `release.app`. If you rename the typer app or change `name="release"`, the registration breaks. Just populate the stub in place.
- **Network leak**: any accidental `requests.get`, `urllib.urlopen`, `gh` subprocess, or `httpx.get` will violate FR-014. The mock-based test (`test_payload_no_github_api_calls`) is the safety net — make sure it actually fails when network is attempted.
- **Version parsing edge cases**: pre-release versions can have many shapes (e.g., `3.1.0rc1`, `3.1.0.dev1`). The locked rules cover alpha/beta/stable. If you encounter `rc` or `dev` in current_version, raise a clear error rather than guessing.
- **Don't add `--bump-level`**: the locked decision is no parameter. Stable→stable always patches. Minor/major bumps require manual editing. If a future maintainer wants minor/major support, file a follow-up issue.

## Reviewer Guidance

- Verify the `release/` package split is committed (not inlined into `agent/release.py`)
- Verify `agent/release.py` still has `app = typer.Typer(name="release", ...)` matching the existing registration
- Run `unset GITHUB_TOKEN && spec-kitty agent release prep --channel alpha` and confirm it succeeds without network
- Verify the JSON output round-trips through `json.loads` and `dataclasses.asdict`
- Check that `propose_version` docstring documents the stable→stable patch rule
- Verify the #457 close comment exists with the FR-023 scope-cut breakdown

## Next steps after merge

Once WP04 lands, the maintainer can run `spec-kitty agent release prep --channel alpha` to prepare the next 068 release without manually reconstructing version/changelog inputs.

## Activity Log

- 2026-04-07T09:23:30Z – unknown – shell_pid=42381 – Claimed by claude orchestrator
- 2026-04-07T09:33:59Z – unknown – shell_pid=42381 – Ready for review: release-prep CLI implemented with full test suite. 28/28 tests pass, ruff and mypy clean on release package. PYTHONPATH=src python -m specify_cli agent release prep --help works. Zero network calls verified via mock.
- 2026-04-07T09:34:38Z – claude:sonnet:reviewer:reviewer – shell_pid=62643 – Started review via action command
