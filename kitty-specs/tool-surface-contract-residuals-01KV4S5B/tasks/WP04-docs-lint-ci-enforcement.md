---
work_package_id: WP04
title: Docs-contract lint CI enforcement (#1942)
dependencies:
- WP01
requirement_refs:
- FR-005
tracker_refs:
- '1942'
planning_base_branch: feat/tool-surface-contract-residuals
merge_target_branch: feat/tool-surface-contract-residuals
branch_strategy: Planning artifacts for this mission were generated on feat/tool-surface-contract-residuals. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/tool-surface-contract-residuals unless the human explicitly redirects the landing branch.
created_at: '2026-06-15T05:20:00+00:00'
subtasks:
- T014
- T015
- T016
- T017
agent: "claude:sonnet:reviewer-renata:reviewer"
shell_pid: "3905871"
history:
- date: '2026-06-15'
  action: created
  actor: claude
agent_profile: python-pedro
authoritative_surface: tests/specify_cli/tool_surface/test_docs.py
create_intent: []
execution_mode: code_change
owned_files:
- tests/specify_cli/tool_surface/test_docs.py
- .github/workflows/ci-quality.yml
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Load your assigned profile via `/ad-hoc-profile-load` (profile: **python-pedro**, role: implementer). Then return here.

## Objective

Close #1942: make the docs-contract lint an **actually-enforced** CI gate. The linter (`tool_surface/docs.py`) is correct, but `test_docs.py` is `unit`-marked and **no CI shard collects it** (a double invisibility: the `unit` marker is excluded by every shard's `-m` selector AND there is no `tool_surface` path-filter entry). Prove enforcement adversarially (`quality-gate-verification` + `atdd-adversarial-acceptance`, DIRECTIVE_030).

## Context

- `.github/workflows/ci-quality.yml` shards select by BOTH a `dorny/paths-filter` (changed files → which shard runs) AND a pytest `-m` marker (`fast` vs `git_repo or integration or architectural`).
- `unit` matches neither selector, and there is no `tests/specify_cli/tool_surface/**` / `src/specify_cli/tool_surface/**` path-filter entry. Both must be fixed (research D-3).

## Subtasks (ATDD — adversarial test first)

### T014 — RED: adversarial docs-drift negative test (must DISCRIMINATE drift from noise)
In `tests/specify_cli/tool_surface/test_docs.py`, add a test that injects an **unregistered** `.agents/skills/spec-kitty.*` path reference into a temp docs tree and asserts the linter emits a finding **whose `.finding == docs.FINDING_UNREGISTERED_PATH`** (import the real constant — value `"UNREGISTERED_PATH"`, `docs.py:30`; do NOT match an invented prose string and do NOT assert merely `len(findings) > 0`, which would pass on incidental errors). Add the **paired discrimination assertion**: the same injection using a *registered* surface path yields **zero** findings. This proves the gate fails on drift *and only on drift*.

### T015 — Re-mark the test
Change `tests/specify_cli/tool_surface/test_docs.py` `pytestmark` from `[pytest.mark.unit]` to `[pytest.mark.integration]`. Confirm the marker-correctness architectural test still passes.

### T016 — Wire the path filter to the RUN-CONDITION glob (not just "a shard")
**⚠️ adversarial-review correction:** the `integration-tests-core-misc` job's `if:` gates on `needs.changes.outputs.core_misc`. Re-marking + a cosmetically-named filter that the `if:` never reads re-creates #1942 exactly. In `.github/workflows/ci-quality.yml`, add `src/specify_cli/tool_surface/**` and `tests/specify_cli/tool_surface/**` to the **`core_misc` paths-filter list** (the `core_misc:` block near line 166 — the glob the job's `if:` actually evaluates). Do not invent a new filter name that nothing consumes.

### T017 — Prove COLLECTION, not just marking (enforceable)
- Local: clean tree → `pytest tests/specify_cli/tool_surface/test_docs.py -q` passes; injected drift → it FAILS with `FINDING_UNREGISTERED_PATH`.
- **Proof-of-collection (required artifact):** demonstrate that a change touching **only** `tool_surface/**` sets `changes.outputs.core_misc == 'true'` so `integration-tests-core-misc` RUNS (not skipped) — via a `dorny/paths-filter` dry-run against a tool_surface-only diff, or a scratch commit that touches only `tool_surface/**` and shows the job non-skipped. Paste the evidence (the `core_misc` boolean / job status) into the handoff. "Mapped to a shard" is insufficient; the `changes.outputs.core_misc` input is the load-bearing wiring (NFR-004).

## Branch Strategy

Planning/merge branch: **`feat/tool-surface-contract-residuals`** (PR → `main`). Lane worktree from `lanes.json`. `safe-commit --to-branch feat/tool-surface-contract-residuals`; status transitions from primary CWD.

## Definition of Done

- The docs-lint test is `integration`-marked AND `tool_surface/**` is in the **`core_misc` filter list** so `integration-tests-core-misc`'s `if:` actually fires (no double invisibility).
- Proof-of-collection artifact in the handoff: a tool_surface-only change makes `changes.outputs.core_misc == 'true'` / the job non-skipped (NFR-004 — collection proven, not assumed).
- The negative test asserts `docs.FINDING_UNREGISTERED_PATH` for the injected path AND a registered path yields zero findings (discriminates drift from noise).
- `ci-quality.yml` edit follows the existing filter/job pattern; no other shard's collection broken.
- #1942 "CI-collected fail-on-drift" acceptance criterion met.

## Risks

- Re-marking without the path filter (or vice versa) leaves the gate uncollected — both are required.
- A too-broad path filter could pull the test into the wrong shard or run it spuriously; scope to `tool_surface/**`.

## Reviewer Guidance

Recommended reviewer: **reviewer-renata** (standard). Verify the negative test genuinely fails on drift, the chosen shard's marker selector + path filter actually collect the test (trace the yaml, don't trust the marker change alone), and no existing shard is disrupted. Resolves **#1942** → terminal issue-matrix verdict (`fixed`).

## Activity Log

- 2026-06-15T06:05:06Z – claude:opus:python-pedro:implementer – shell_pid=3887319 – Assigned agent via action command
- 2026-06-15T06:10:30Z – claude:opus:python-pedro:implementer – shell_pid=3887319 – core_misc filter wiring: added 'src/specify_cli/tool_surface/**' + 'tests/specify_cli/tool_surface/**' to the core_misc paths-filter (ci-quality.yml ~L170/L174), the glob integration-tests-core-misc's if: actually evaluates. Test re-marked unit->integration so the specify-cli-rest shard (marker 'git_repo or integration or architectural') collects it. Proof-of-collection: simulated dorny/paths-filter over a tool_surface-only diff -> changes.outputs.core_misc=='true' (dashboard-only control=='false'); specify-cli-rest exact path+marker selector collects all 16 test_docs.py nodes. Discrimination: injected unregistered path -> 1 finding, .finding==FINDING_UNREGISTERED_PATH('UNREGISTERED_PATH'); registered path same injection -> 0 findings. marker-correctness + path-filter architectural tests pass; ruff+mypy clean.
- 2026-06-15T06:10:58Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=3905871 – Started review via action command
- 2026-06-15T06:13:21Z – user – shell_pid=3905871 – All DoD criteria met. core_misc filter: src/specify_cli/tool_surface/** + tests/specify_cli/tool_surface/** added at lines 173-175 of ci-quality.yml — the glob needs.changes.outputs.core_misc reads. Test re-marked unit→integration; specify-cli-rest shard (-m 'git_repo or integration or architectural', paths=tests/specify_cli) collects all 16 test_docs.py nodes (collection verified by dry-run). Negative test asserts findings[0].finding == FINDING_UNREGISTERED_PATH (constant 'UNREGISTERED_PATH', docs.py:30), not a prose string, not len>0. Paired discrimination test: registered path (spec-kitty.advise) yields zero findings — drift-specific gate confirmed. Marker-correctness architectural test passes. Ruff + mypy clean. Only the 2 owned files changed in the WP04 commit. No --feature terminology violations. #1942 resolved.
