---
work_package_id: WP03
title: docs-freshness CI wiring + safety-structure test
dependencies:
- WP02
requirement_refs:
- FR-001
- FR-005
- FR-006
- FR-007
planning_base_branch: docs/3253-docs-gaps
merge_target_branch: docs/3253-docs-gaps
branch_strategy: Planning artifacts for this mission were generated on docs/3253-docs-gaps. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/3253-docs-gaps unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
- T015
history:
- at: '2026-08-08T10:45:09Z'
  actor: claude
  event: created
agent_profile: python-pedro
authoritative_surface: .github/workflows/docs-freshness.yml
create_intent:
- tests/docs/test_docs_freshness_invariant.py
execution_mode: code_change
owned_files:
- .github/workflows/docs-freshness.yml
- .github/workflows/docs-pages.yml
- tests/docs/test_docs_freshness_invariant.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else:

```
/ad-hoc-profile-load python-pedro
```

Confirm which initialization/boundaries/directives you applied (TDD/red-first;
pytest+ruff+mypy before handoff; Python-implementation lane). Then proceed.

## Objective

This WP is the **sole owner** of `.github/workflows/docs-freshness.yml`. It (a) wires the
WP02 slash-command gate into CI (FR-001), (b) does the tidy-first PYTHONPATH hoist (B0),
(c) encodes the docs-freshness safety structure as a repo-readable test (FR-005), (d)
cross-references the invariant comment (FR-006), and (e) records the docs-pages deploy-side
note (FR-007).

## Context

- **Depends on WP02**: the slash gate script + the backfilled doc must exist before the CI
  step is wired, or the step reds CI on the un-backfilled doc. Start WP03 only after WP02
  is approved/merged into the lane base.
- **PYTHONPATH hoist (B0)**: four steps currently carry `PYTHONPATH: .` (`docs-freshness.yml:61-92`).
  Hoist **only** `PYTHONPATH` to a job-level `env:`. Leave `SPEC_KITTY_ENABLE_SAAS_SYNC` /
  `NO_UPGRADE_CHECK` on their single step (job-level `env` applies to every step). Behavior-preserving.
- **FR-005 assertion is absence-from-an-allowlist**: the `paths:` filter (`:29-39`) is a
  positive allowlist — there is **no** `!tests/**` exclusion pattern. Assert
  "allowlist present AND does not contain `tests/**` or `kitty-specs/**`", plus an unfiltered
  `push:main` backstop (`:40-41`) and the invariant comment (`:15-27`). **Do NOT** hardcode
  `required == {drift-detector}` — that conflicts with `ui-e2e.yml`'s "Required-check
  contract" comment and cannot observe the live GitHub setting anyway (operator-confirmed
  non-required, C-003).
- `ruamel.yaml` is already a project dependency — structured YAML parsing is fine (not
  restricted to stdlib) if it reads cleaner than regex.

## Subtasks

### T011 — Tidy-first: hoist `PYTHONPATH` to job-level (B0)
**Steps**:
1. Add a job-level `env: { PYTHONPATH: . }` to the docs-freshness job.
2. Remove the per-step `PYTHONPATH: .` from the four steps that carry it; leave every other per-step env (SAAS/upgrade toggles) untouched.
**Validation**: behavior-preserving — the existing steps still resolve modules; land as a discrete first commit.

### T012 — Wire the slash-command gate CI step (FR-001)
**Steps**:
1. Add a step invoking `python scripts/docs/check_slash_command_freshness.py` (relies on the job-level PYTHONPATH from T011).
2. Place it alongside the sibling doc-consistency gate steps; ensure a non-zero exit fails the job.
**Validation**: with the backfilled doc (WP02), the step exits 0; a locally-mutated registry/doc makes it exit non-zero.

### T013 — Safety-structure test (FR-005)
**Steps**:
1. New file `tests/docs/test_docs_freshness_invariant.py`.
2. Parse `.github/workflows/docs-freshness.yml` (may use `ruamel.yaml`).
3. Assert: (a) the PR `paths:` allowlist is present AND contains neither `tests/**` nor `kitty-specs/**` (absence-from-allowlist); (b) an unfiltered `push:` trigger with `branches:[main]` and no `paths:` key exists (the backstop); (c) the documented safety-invariant comment is present.
4. Explicit comment in the test: it does NOT and cannot observe live GitHub branch protection.
**Validation**: passes on the current workflow; fails if any property is removed.

### T014 — Cross-reference the invariant comment (FR-006)
**Steps**:
1. In `docs-freshness.yml`, extend the existing invariant comment block to reference the T013 test by path, reusing the "Required-check contract" comment idiom found in `ui-e2e.yml`.
2. Do NOT re-add already-present prose — only add the test cross-reference so comment and test co-evolve.
**Validation**: comment names the test file; no duplicated invariant prose.

### T015 — [P] docs-pages seo_verify note (FR-007)
**Steps**:
1. In `.github/workflows/docs-pages.yml`, add a short comment near the `seo_verify` step recording that it runs **push-only (`main`/`2.x`), no `pull_request` trigger** — the deploy-side analogue of the item-3 gap. Intentionally verification-free.
**Validation**: comment is factually correct (triggers are `push: [main, 2.x]`).

## Branch Strategy

- **Planning/base branch**: `docs/3253-docs-gaps`. **Final merge target**: `docs/3253-docs-gaps`.
- Execution worktree per computed lane from `lanes.json`; enter what `spec-kitty implement WP03` resolves. WP03 is Lane B, **after WP02**.

## Test Strategy (ATDD, C-006)

Red-first for T013: the negative assertion (e.g. a fixture workflow missing the backstop)
must be RED before the test's helper exists and GREEN against the real workflow. Because the
gate step (T012) and its behavior depend on WP02, capture the CI-step red-first evidence as a
recorded failing run (importing/invoking the not-yet-wired step). Targeted:
`pytest tests/docs/test_docs_freshness_invariant.py`. ruff + mypy clean.

## Definition of Done

- Slash-command gate runs in CI and stays green on the backfilled doc (FR-001 end-to-end with WP02).
- PYTHONPATH hoisted job-level; other per-step envs untouched (behavior-preserving).
- `test_docs_freshness_invariant.py` asserts the three safety properties (SC-005); non-vacuous.
- Invariant comment cross-references the test (FR-006); docs-pages note added (FR-007).
- `docs-freshness.yml` edits all land here — no other WP touches it.

## Risks / Reviewer guidance

- **Reviewer**: confirm ONLY `PYTHONPATH` was hoisted (SAAS/upgrade envs still per-step);
  the FR-005 test asserts *absence-from-allowlist* (not a non-existent `!` pattern) and does
  NOT hardcode the required-check set; the CI step is ordered after WP02's backfill so it
  cannot red on the 12/15 doc. Verify no duplicated invariant prose (FR-006 is a cross-ref).
