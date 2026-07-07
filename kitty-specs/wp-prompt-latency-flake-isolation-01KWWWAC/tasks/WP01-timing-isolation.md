---
work_package_id: WP01
title: Timing-isolate the WP-prompt latency tests
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
tracker_refs: []
planning_base_branch: fix/latency-nfr-isolation
merge_target_branch: fix/latency-nfr-isolation
branch_strategy: Planning artifacts for this mission were generated on fix/latency-nfr-isolation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/latency-nfr-isolation unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
agent: "claude"
shell_pid: "1408659"
history:
- 'Created by planner for #2032 tasks phase'
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- tests/architectural/test_wp_prompt_build_latency.py
- .github/workflows/ci-quality.yml
role: implementer
tags: []
task_type: implement
---

# WP01 – Timing-isolate the WP-prompt latency tests (closes #2032)

## ⚡ Do This First: Load Agent Profile
`/ad-hoc-profile-load` → `python-pedro` (implementer, Sonnet-5). Read `spec.md` (FR-001..005, C-001/002) + `plan.md`. Study the canonical pattern: `pytest.ini:49` (`timing` marker), `tests/git/test_protection_config_honoring.py:508` (`@pytest.mark.timing` usage), `ci-quality.yml:2488-2522` (the `restart-daemon-nfr-timing` `-m timing` job), and the `not timing` exclusion idiom at `ci-quality.yml:2418`.

## Objective
Move the two `test_wp_prompt_build_latency.py` tests off the parallel `-n auto --dist loadfile` arch pole (where CPU contention corrupts the single cold wall-clock sample) into the dedicated non-parallel `-m timing` job — using the **existing canonical `timing` marker**. Do NOT invent a marker, do NOT touch `pyproject.toml` (forbidden), do NOT mirror the C-SERIAL/port pattern, do NOT use `xdist_group` (inert under `--dist loadfile`).

## Changes
- **T001 — `tests/architectural/test_wp_prompt_build_latency.py`**: add `@pytest.mark.timing` to BOTH tests (module already has `pytestmark = [architectural, git_repo]` — add `timing`, or per-test). Replace the single cold `time.perf_counter()` sample with a **warm-up call + one warm sample** (or median-of-3): call `_build_wp_prompt(...)` once to warm caches/imports, then measure the next call(s); assert the warm elapsed < budget. Keep the **wall-clock** oracle (the build does `subprocess.run` + `read_text` — CPU-time would miss a blocking regression). The budget can be tightened from 10.0 now it's isolated, but keep sane margin over the ~1.5s warm baseline.
- **T002 — `.github/workflows/ci-quality.yml`**: (a) add `and not timing` to the arch-adversarial pole selector at **`:1816`** (`-m '${{ matrix.shard }} and not windows_ci and (git_repo or integration or architectural)'` → append `and not timing`) AND the sibling branch at **`:1667`** — so the tests are NOT collected on the parallel shard (verify BOTH branches; leaving one un-edited leaves the flake on that path). (b) add a **NEW always-on serial step/job** for the latency file: gate it **`if: always()`** (mirror the arch pole at `:1707` — NOT a `cli`/change-filter gate), running `-n0 -m timing tests/architectural/test_wp_prompt_build_latency.py`. **Do NOT reuse/extend the `restart-daemon-nfr-timing` job (`:2488`)** — its `if:` gates on `needs.changes.outputs.cli` (the `cli` filter `:200-203` = `src/specify_cli/cli/**` only), but the code under test is `src/runtime/next/**` (→ `core_misc`), so that job would **SKIP on the very prompt-builder PRs the NFR guards** → silent coverage loss (violates SC-003). The new step must run on **every PR** (as the always-on arch pole does today), just serially. If the aggregator/census (`:3456`+, `ci_topology_census.json`) needs the new job registered to keep the fail-closed gate consistent, do that too.
- **T003 — non-vacuous proof**: prove the NFR still bites — temporarily insert a `time.sleep(BUDGET+1)` into the measured path (or monkeypatch), confirm the test REDS, then revert. Confirm no double-run (the tests appear in the timing job, NOT the arch shard). Confirm `test_arch_shard_marker_completeness.py` stays green (the file remains registered in `_arch_shard_map.py` — do NOT remove it from the map).

## DoD
- Both tests carry `@pytest.mark.timing`; warm-up + warm sample; wall-clock; sane budget.
- Arch selectors (`:1667` + `:1816`) have `and not timing`; a NEW **always-on** (`if: always()`) serial `-m timing` step runs the latency file **on every PR** (NOT the cli-gated `restart-daemon-nfr-timing` job) — paste the step's `if:` condition + the collection proof.
- Seeded-delay red-first proof (test reds with the delay, green without).
- `test_arch_shard_marker_completeness.py` green; no `pyproject.toml` change.
- `PWHEADLESS=1 uv run pytest tests/architectural/test_wp_prompt_build_latency.py -m timing -q` green; `ruff` + `mypy --strict` clean on the test file; no new suppressions.

## Commit
`git add tests/architectural/test_wp_prompt_build_latency.py .github/workflows/ci-quality.yml && git commit -m "test(architectural): timing-isolate WP-prompt latency NFR from the parallel shard — closes #2032"`

## Report back
The marker addition; the warm-measurement change + new budget; BOTH selector edits (`:1667` + `:1816`) with the exact lines; how the `-m timing` job now collects the latency file (paste `pytest --collect-only -m timing` proof that it's included); the seeded-delay red-first evidence; no-double-run + completeness-gate confirmation; ruff+mypy; lane commit SHA. If the `-m timing` job cannot be made to collect the file cleanly, STOP and report the CI-wiring blocker.

## Activity Log

- 2026-07-07T00:33:56Z – claude – shell_pid=1408659 – Assigned agent via action command
