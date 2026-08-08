---
work_package_id: WP06
title: Dedicated stress CI lane + right-size the mis-pooled durability test
dependencies: []
requirement_refs:
- FR-012
planning_base_branch: hardening/verdict-seam-facade-followup
merge_target_branch: hardening/verdict-seam-facade-followup
branch_strategy: Planning artifacts for this mission were generated on hardening/verdict-seam-facade-followup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into hardening/verdict-seam-facade-followup unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-verdict-seam-boundary-hardening-01KZG179
base_commit: 4d48fcf66ca7e71cc466a8dd812f324361ec6721
created_at: '2026-08-08T11:28:46.805588+00:00'
subtasks:
- T023
- T024
- T025
phase: Phase 2 - Parallel hardening
history:
- at: '2026-08-08T09:55:00Z'
  actor: system
  action: Prompt generated from plan.md IC-05
agent_profile: implementer-ivan
authoritative_surface: .github/workflows/ci-quality.yml
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- .github/workflows/ci-quality.yml
- pytest.ini
- tests/status/test_emit_durability.py
role: implementer
tags: []
task_type: implement
tracker_refs:
- '3256'
---

# Work Package Prompt: WP06 – Stress CI lane

## ⚡ Do This First: Load Agent Profile

Load `implementer-ivan` and behave per its guidance before parsing the rest of this prompt.

## Goal

`test_emit_durability.py::test_two_concurrent_distinct_verdicts_are_both_durable` is `@stress` (two real fork processes, 30s timeouts) but rides the **fast** xdist pool because its module carries `pytestmark = [pytest.mark.fast]` and **no CI job selects `-m stress`**. Add a dedicated serial stress lane and right-size the test out of the fast pool. **CI-infra; independent parallel lane.**

## Subtasks

### T023 — Add a dedicated stress CI job
In `.github/workflows/ci-quality.yml`, add a serial job (mirror `timing-nfr-serial` ~L2177) that selects `-m "stress and not windows_ci" -n0` and runs POSIX-only (fork). Give it a generous `--timeout`. It serves the whole `tests/stress/` family (`test_concurrent_emits.py` already carries `stress`) plus the durability test once T024 lands.

### T024 — Right-size the durability test out of the fast pool
`test_two_concurrent_distinct_verdicts_are_both_durable` is the **sole** test in `tests/status/test_emit_durability.py` (the module-level `pytestmark = [pytest.mark.fast]` at ~L67 applies only to it). So the clean, in-ownership fix is to **change that module-level mark from `fast` to `stress`** (or otherwise drop the `fast` sweep) so the `fast-tests-status` selector (`-m "fast and not windows_ci and not (git_repo or integration)"`) no longer collects it while `-m stress` does. **Stay within `owned_files`** — do NOT re-home the file under `tests/stress/` (that path is not owned by this WP; a move would need `tests/stress/**` added to ownership first). Confirm with `pytest --collect-only -m stress -q` (collects it) and `pytest --collect-only -m "fast and not windows_ci and not (git_repo or integration)" tests/status/ -q` (does not).

### T025 — Correct the marker wording + coordinate #3235
- Fix the inaccurate `pytest.ini:47` `stress` marker description ("excluded from the fast suite" — currently false for this test).
- **Coordinate with #3235** (P0 concurrency data-loss, same test family): if the durability test moves/renames, leave a comment/pointer so #3235's repro is not stranded. Do NOT fix #3235 here (separate durability bug).

## Branch Strategy
Independent parallel lane off `hardening/verdict-seam-facade-followup`; merges back to same.

## Definition of Done
- A `-m stress -n0` serial CI job exists in `ci-quality.yml` (POSIX-only) and collects the intended tests.
- The durability test is no longer collected by the fast-pool selector (verified via `--collect-only`).
- `pytest.ini` stress-marker wording corrected; #3235 pointer left.
- No production code changed; `ruff`/`mypy` clean on the touched Python test file.

## Reviewer Guidance
Verify the two `--collect-only` invocations prove the test moved lanes (in `stress`, out of `fast`). Confirm the new job mirrors the serial `-n0` pattern (not `-n auto`). Confirm the `pytest.ini` wording now matches reality and the #3235 pointer is present.

## Risks
- Only relocating the marker without adding the `-m stress` job leaves it inert — both T023 and T024 are required.
- Stranding #3235's repro if the test is renamed without a pointer.
