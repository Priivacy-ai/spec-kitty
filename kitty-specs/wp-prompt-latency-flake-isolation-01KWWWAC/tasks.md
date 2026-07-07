# Work Packages: Isolate the WP-prompt latency NFR tests from parallel-execution flake

**Mission**: `wp-prompt-latency-flake-isolation-01KWWWAC` | **Issue**: Closes #2032 (M4 of #1931) | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

## Subtask Format: `[Txxx] Description (WP)`

## Path Conventions
Repo-root-relative. Single cohesive WP — the marker, the arch-selector exclusion, and the `-m timing` job wiring must land together (a marker without the timing-job wiring silently drops the tests; a selector exclusion without the marker is a no-op).

| Subtask | Description | WP | Requirement |
| --- | --- | --- | --- |
| T001 | Mark both latency tests `@pytest.mark.timing` (canonical, `pytest.ini:49`); warm-up + single warm sample (or median-of-3); keep wall-clock; sane budget | WP01 | FR-001, FR-002 |
| T002 | Add `and not timing` to the arch selectors (`ci-quality.yml:1667` + `:1816`); add a NEW **always-on** serial `-m timing` step (`if: always()`, `-n0`) — NOT the cli-gated `restart-daemon-nfr-timing` job (skips on `src/runtime/next/**` PRs) | WP01 | FR-001, FR-004 |
| T003 | Non-vacuous proof: a seeded `time.sleep` in the build path still reds the gate; confirm no double-run + completeness gate green | WP01 | FR-005 |

---

## Work Package WP01: Timing-isolate the latency tests (Priority: P1)
**Prompt**: `/tasks/WP01-timing-isolation.md`
**Goal**: The two `test_wp_prompt_build_latency.py` tests leave the parallel `-n auto` arch pole (via `@pytest.mark.timing` + `and not timing`) and run in the dedicated non-parallel `-m timing` job, with a warm-sample wall-clock measurement — eliminating the CPU-contention flake while keeping the NFR meaningful.
### Included Subtasks
- [ ] T001 Mark + warm measurement (WP01)
- [ ] T002 Arch-selector exclusion + timing-job wiring (WP01)
- [ ] T003 Non-vacuous proof + no double-run (WP01)
### Dependencies
None (single WP).
### Risks & Mitigations
- Double-run (parallel + timing job) → selector `and not timing` + the timing job land together.
- Tests silently dropped → confirm the `-m timing` job actually collects the latency file (not just the restart-daemon file).
- Forbidden marker registration → use `pytest.ini`'s existing `timing`, never `pyproject.toml`.
