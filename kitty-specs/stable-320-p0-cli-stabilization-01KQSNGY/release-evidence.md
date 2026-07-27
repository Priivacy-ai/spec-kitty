# Release Evidence: 3.2.0 Stable P0 CLI Stabilization

Mission: `stable-320-p0-cli-stabilization-01KQSNGY`
Evidence date: 2026-05-04

## Scope

This evidence maps to GitHub issues #967, #904, #968, and #964. WP01-WP04 were
approved before WP05, so focused implementation evidence was collected from the
approved lane worktrees. The official merged-branch validation is expected after
`spec-kitty merge` lands the approved lanes onto `main`.

## #967 Status Hang Stabilization

Command:

```bash
uv run pytest tests/status -q --timeout=30
```

Worktree: `.worktrees/stable-320-p0-cli-stabilization-01KQSNGY-lane-a`

Outcome: pass, `577 passed in 4.43s`.

Notes:

- The test process exited successfully under the 30-second timeout.
- A non-fatal final-sync diagnostic was printed: `sync.final_sync_lock_unavailable`; queued events are left for the daemon. This is consistent with WP01's bounded shutdown behavior and did not affect pytest exit status.

## #904 Review Verdict Consistency Gate

Command:

```bash
uv run pytest \
  tests/review/test_artifacts.py \
  tests/post_merge/test_review_artifact_consistency.py \
  tests/specify_cli/cli/commands/agent/test_tasks.py \
  -q --timeout=30
```

Worktree: `.worktrees/stable-320-p0-cli-stabilization-01KQSNGY-lane-b`

Outcome: pass, `34 passed in 1.74s`.

Coverage:

- Latest review-cycle artifact parsing.
- Rejected-verdict fail-closed behavior before terminal WP mutation.
- Durable override metadata for explicit supersession.
- Post-merge review artifact consistency regression coverage.

## #968 Retired Checklist Command Cleanup

Command:

```bash
uv run pytest \
  tests/specify_cli/shims/test_registry.py \
  tests/specify_cli/shims/test_generator.py \
  tests/specify_cli/runtime/test_agent_commands_routing.py \
  tests/runtime/test_doctor_command_file_health.py \
  tests/specify_cli/skills/test_command_installer.py \
  -q --timeout=30
```

Worktree: `.worktrees/stable-320-p0-cli-stabilization-01KQSNGY-lane-c`

Outcome: pass, `235 passed in 1.57s`.

Coverage:

- `checklist` is absent from active command registries.
- Generated command surfaces and command-skill installer inventory match the active command list.
- Runtime doctor/count diagnostics align with the active command count.

## #964 Generated Skill Frontmatter

Command:

```bash
uv run pytest \
  tests/specify_cli/skills/test_command_renderer.py \
  tests/specify_cli/skills/test_installer.py \
  tests/specify_cli/skills/test_verifier.py \
  tests/runtime/test_agent_skills.py \
  tests/specify_cli/docs/test_readme_governance.py \
  tests/specify_cli/skills/test_command_installer.py \
  -q --timeout=30
```

Worktree: `.worktrees/stable-320-p0-cli-stabilization-01KQSNGY-lane-d`

Outcome: pass, `149 passed in 1.45s`.

Coverage:

- Fresh Codex/global `spec-kitty.advise/SKILL.md` generation from a plain Markdown source now gains YAML frontmatter.
- Canonical skill installer, repair, and global bootstrap paths normalize missing `SKILL.md` frontmatter.
- Existing frontmatter is preserved byte-for-byte.
- The checked-in `.agents/skills/spec-kitty.advise/SKILL.md` repro now starts with YAML frontmatter and its command-skills manifest hash was updated.

## Broad Gates

Ruff:

```bash
uv run ruff check src tests
```

Outcome: pass after removing one stale unused import from `tests/review/test_cycle.py`.

Mypy strict:

```bash
uv run mypy --strict src/specify_cli src/charter src/doctrine
```

Outcome: fail on current baseline, tracked as #971.

Summary of failure class:

- Missing third-party stubs for `yaml`, `toml`, `jsonschema`, `psutil`, `requests`, and `re2`.
- Existing strict typing errors in status, review, sync, doctor, and agent retrospect paths.

This mission records the failing type gate rather than treating it as a clean release signal. The focused regression tests above are the acceptance evidence for the four scoped P0 issues.

## Hosted Sync Note

Commands that touched Spec Kitty workflow/status sync on this computer were run with `SPEC_KITTY_ENABLE_SAAS_SYNC=1`. Focused pytest commands were local/offline unless their code under test emitted non-fatal sync diagnostics.

## Post-Merge PR Branch Validation

After `spec-kitty merge` landed the approved lanes onto
`kitty/pr/stable-320-p0-cli-stabilization-01KQSNGY-to-main`, the following
merged-branch checks passed:

```bash
uv run pytest tests/status -q --timeout=30
# 577 passed in 4.91s

uv run pytest \
  tests/review/test_artifacts.py \
  tests/post_merge/test_review_artifact_consistency.py \
  tests/specify_cli/cli/commands/agent/test_tasks.py \
  tests/post_merge/test_stale_assertions.py \
  -q --timeout=30
# 52 passed in 3.89s

uv run pytest \
  tests/specify_cli/shims/test_registry.py \
  tests/specify_cli/shims/test_generator.py \
  tests/specify_cli/runtime/test_agent_commands_routing.py \
  tests/runtime/test_doctor_command_file_health.py \
  tests/specify_cli/skills/test_command_installer.py \
  tests/specify_cli/skills/test_command_renderer.py \
  tests/specify_cli/skills/test_installer.py \
  tests/specify_cli/skills/test_verifier.py \
  tests/runtime/test_agent_skills.py \
  tests/specify_cli/docs/test_readme_governance.py \
  -q --timeout=30
# 342 passed in 1.73s

uv run ruff check src tests
# All checks passed

uv run spec-kitty agent tests stale-check --base 63c91ecd --head HEAD --json
# findings: []
```

The initial merge stale-assertion advisory reported false positives for tests
that intentionally assert retired `checklist` surfaces are absent, plus
acceptance-mode tests that use `mode="checklist"` for a different domain
concept. The PR branch now includes a stale-check analyzer fix for negative
membership assertions and test constant cleanup for unrelated acceptance-mode
uses; rerunning the stale check for the merge range returns no findings.
