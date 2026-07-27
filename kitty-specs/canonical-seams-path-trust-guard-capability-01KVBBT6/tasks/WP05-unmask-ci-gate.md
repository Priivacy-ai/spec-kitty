---
work_package_id: WP05
title: Un-mask the architectural CI gate
dependencies: []
requirement_refs:
- FR-007
- NFR-004
tracker_refs:
- '#2023'
planning_base_branch: feat/canonical-seams-path-trust-guard-capability
merge_target_branch: feat/canonical-seams-path-trust-guard-capability
branch_strategy: Planning artifacts for this mission were generated on feat/canonical-seams-path-trust-guard-capability. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/canonical-seams-path-trust-guard-capability unless the human explicitly redirects the landing branch.
subtasks:
- T020
- T021
- T022
- T023
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3678708"
history:
- 2026-06-17 created (/spec-kitty.tasks)
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent:
- tests/architectural/test_ci_architectural_gate_coverage.py
execution_mode: code_change
owned_files:
- .github/workflows/ci-quality.yml
- tests/architectural/test_ci_architectural_gate_coverage.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Then read:
1. `kitty-specs/canonical-seams-path-trust-guard-capability-01KVBBT6/spec.md` — **FR-007, NFR-004**, **C-002**
   (guard-mechanism only).
2. `kitty-specs/canonical-seams-path-trust-guard-capability-01KVBBT6/research.md` — **§(e)/D-4** the exact mask
   mechanism (filter gap + the `:1357-1371` short-circuit).
3. The #2017 log (comment-4733897389) and #2023 — the live driver (the `_repo_root_for_lifecycle_log` regression
   that passed `fast-tests-status` but skipped the architectural shard).

## Objective

Close the architectural-gate mask: make `integration-tests-core-misc (architectural)` run the **full**
`tests/architectural/**` suite whenever a guarded write-side surface changes — not only when
`tests/architectural/**` itself changes. Guard-mechanism only (C-002): do NOT change what any architectural test
asserts. Independent WP. (#2023 under #1931.)

## Subtasks

### T020 — Widen the `core_misc` path filter
In `.github/workflows/ci-quality.yml`, the `core_misc` filter (~:174) carries `tests/architectural/**`. The guarded
surfaces `src/specify_cli/status/**` + `src/specify_cli/coordination/**` are in the **`status` filter (~:142-146,
drives `fast-tests-status`)** AND in the `execution_context` filter (~:220, whose sole architectural inclusion is
the single file `test_execution_context_parity.py` ~:225) — but they are **NOT in `core_misc`**, which is the only
filter that drives the full `integration-tests-core-misc (architectural)` shard. (`core/worktree.py` — confirm
which filters currently match it.) So a `status/**` edit runs `fast-tests-status` but the short-circuit at
`:1357-1371` runs only the parity file for execution-context-only changes → the rest of `tests/architectural/**`
is skipped. (The squad corrected the earlier "only in execution_context" framing — they're in `status` too; the
point is none of those filters drives the architectural shard.)
- **Add** `src/specify_cli/status/**`, `src/specify_cli/coordination/**`, and `src/specify_cli/core/worktree.py`
  to the `core_misc` filter so any edit to a guarded write-side surface sets `core_misc=true` → the full
  architectural shard runs (the `:1357` short-circuit only fires when `core_misc != true`).
- Prefer the filter-widening over editing the short-circuit (smaller, clearer blast radius). Keep YAML valid;
  preserve existing filter entries.

### T021 — Meta-test: guarded-surface → architectural-shard coverage (drift-proof, RED-first)
Create `tests/architectural/test_ci_architectural_gate_coverage.py`. **Author it BEFORE T020** so it fails RED
(the globs are absent) before the widening makes it GREEN.
- Parse `.github/workflows/ci-quality.yml` (YAML), locate the `core_misc` filter's path globs.
- Assert each **guarded surface** (`src/specify_cli/status/`, `src/specify_cli/coordination/`,
  `src/specify_cli/core/worktree.py`, `tests/architectural/`) is covered by a glob in `core_misc`.
- **Also assert the short-circuit cannot re-mask:** parse the `:1357` shell guard condition and assert that a
  `status/**` change (→ `core_misc=true`) does NOT satisfy the `core_misc != 'true' && execution_context == 'true'`
  short-circuit — i.e. the full architectural run is reached. Glob-membership ALONE is insufficient (it stays GREEN
  even if the short-circuit later re-masks) — this second assertion is what makes NFR-004 real.
- **Key on filter-name + path-glob membership — NOT line numbers** (the meta-test must itself be drift-proof). A
  future filter edit that drops a guarded surface OR re-introduces the mask MUST turn this RED.
- **Also pin `tests/architectural/**` stays in `core_misc`** (a regression that drops it would silently stop the
  shard running on its own guard edits) and **assert the fix is scoped, not over-broad** — `src/**` (or any
  whole-`src` glob) is NOT in `core_misc` (over-broadening would run the heavy shard on every change; the squad
  flagged this as the anti-goal to gate against, not just reviewer-advise).
- `pytestmark = [pytest.mark.architectural]` so it runs in the shard.

### T022 — Executable falsification: the lifecycle_events scenario (NO "documented check")
- Add an EXECUTABLE assertion (not a handoff note): the `core_misc` glob set matches
  `src/specify_cli/status/lifecycle_events.py` (verified to exist on HEAD, `_repo_root_for_lifecycle_log`), i.e.
  that change now sets `core_misc=true` and the `test_no_write_side_rederivation` ratchet would run. This is the
  original regression as the falsification case — strike any "or a documented check" alternative.

### T023 — Quality gate
- `ruff`+`mypy` clean on the new meta-test (≤15, no suppressions).
- The new meta-test green locally; the widened workflow YAML lints/parses.

## Branch Strategy

Planning/merge base `feat/canonical-seams-path-trust-guard-capability` (PR → main). Worktree per lane from
`lanes.json`. **No dependencies — parallel with WP01/WP03/WP06.**

## Definition of Done

- [ ] `core_misc` filter includes `status/**`, `coordination/**`, `core/worktree.py`.
- [ ] Meta-test asserts guarded-surface→architectural-shard coverage, keyed on filter-name + path-glob (not lines).
- [ ] The lifecycle_events scenario is covered as the falsification case.
- [ ] `ruff`+`mypy` clean; meta-test green; YAML valid.

## Risks / reviewer guidance

- **Don't over-broaden the filter** — adding the three guarded surfaces is enough; do not add all of `src/**`
  (would run the heavy shard on every change). Reviewer: confirm the additions are scoped to the guarded surfaces.
- **The meta-test must be drift-proof itself** (NFR-004) — reviewer: verify it keys on path-glob membership, not
  line numbers or positional YAML structure, so it can't silently rot.
- Guard-mechanism only (C-002): no architectural test's assertions change here.

## Activity Log

- 2026-06-17T20:16:58Z – claude:sonnet:python-pedro:implementer – shell_pid=3633670 – Assigned agent via action command
- 2026-06-17T20:27:31Z – claude:sonnet:python-pedro:implementer – shell_pid=3633670 – Ready for review: added src/specify_cli/status/** and src/specify_cli/coordination/** to core_misc filter (2 globs; core/worktree.py already covered by core/**). New meta-test tests/architectural/test_ci_architectural_gate_coverage.py (5 tests, RED-first before T020, all GREEN after). ruff exit 0, mypy exit 0. YAML valid. Force flag needed due to lane-e worktree status desync (planning repo canonical state: in_progress).
- 2026-06-17T20:28:43Z – claude:opus:reviewer-renata:reviewer – shell_pid=3678708 – Started review via action command
- 2026-06-17T20:35:34Z – user – shell_pid=3678708 – Review passed (opus/reviewer-renata): code-clean; matrix verdicts filled
