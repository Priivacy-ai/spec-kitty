---
work_package_id: WP03
title: Docs + changelog
dependencies:
- WP02
requirement_refs:
- NFR-003
planning_base_branch: remediation/symbolkey-source-module-3552
merge_target_branch: remediation/symbolkey-source-module-3552
branch_strategy: Planning artifacts for this mission were generated on remediation/symbolkey-source-module-3552. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into remediation/symbolkey-source-module-3552 unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
- T017
history:
- at: '2026-08-18T18:20:00+00:00'
  actor: claude
  note: WP created by /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: docs/changelog/CHANGELOG.md
create_intent: []
execution_mode: code_change
owned_files:
- docs/changelog/CHANGELOG.md
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Load your profile: `/ad-hoc-profile-load python-pedro` (or `spec-kitty agent profile show python-pedro` + `spec-kitty charter context --action implement --json`). Plain-language, impact-first changelog style; run the terminology guard after prose edits.

## Objective

Record the change for consumers and confirm the one adjacent gate the plan flagged. Test-infra only — **no `pyproject.toml` version bump**.

## Context

- Canonical changelog is `docs/changelog/CHANGELOG.md` (root `CHANGELOG.md` is a symlink). Add under `[Unreleased]` in the right section (Changed/Fixed), matching the existing **bold lead sentence + before→after** style.
- `test_ratchet_positional_anchor_ban.py` was flagged for a confirmatory check: the squad confirmed it bans positional int anchors, unrelated to a `source_module=` kwarg — expect **no** change needed.

## Subtasks

### T015 — CHANGELOG entry
Add a consumer/developer-focused entry: a bold lead naming the impact (dead-symbol allowlist provenance is now a machine field, not a parsed comment — refreshing a dead symbol no longer depends on comment hygiene), then before→after in plain language. Reference `#3552` and the mission. Note it's dev-facing test infrastructure only.

### T016 — Confirm the anchor-ban gate
Verify `test_ratchet_positional_anchor_ban.py` passes unchanged with `source_module=` kwargs present:
```bash
PWHEADLESS=1 uv run pytest tests/architectural/test_ratchet_positional_anchor_ban.py -q
```
Record the result in the WP notes. If (unexpectedly) it reds, STOP and report — do not force a change.

### T017 — Verify
```bash
PWHEADLESS=1 uv run pytest tests/architectural/test_no_legacy_terminology.py -q
npx --yes markdownlint-cli2@0.18.1 --config .markdownlint-cli2.jsonc docs/changelog/CHANGELOG.md
```
Terminology green; markdownlint 0 errors on the changelog (fix the whole file if the touch surfaces pre-existing MD049, per the landing runbook).

## Branch Strategy

Planning base and merge target are both `remediation/symbolkey-source-module-3552`. Depends on WP02; branches from its completed base; worktree per `lanes.json`.

## Definition of Done

- CHANGELOG entry added under `[Unreleased]`, consumer-focused, references `#3552`, no version bump.
- `test_ratchet_positional_anchor_ban.py` confirmed green unchanged.
- Terminology guard green; markdownlint 0 on the changelog.

## Reviewer guidance

Check the entry leads with impact (not implementation), matches existing changelog style, and that no version bump was introduced.
