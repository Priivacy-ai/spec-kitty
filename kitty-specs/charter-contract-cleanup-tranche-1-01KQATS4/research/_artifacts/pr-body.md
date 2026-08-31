## Summary

- **Charter `synthesize --json` contract hardened (FR-001..FR-005):** strict-stdout JSON envelope (`result` / `adapter` / `written_artifacts` / `warnings`); dry-run and non-dry-run paths now produce equivalent envelopes; the `PROJECT_000` placeholder is no longer user-visible. Lint/log diagnostic noise on stdout is suppressed in `--json` mode.
- **Golden-path E2E hardening (FR-006/FR-007 → closes #844):** `tests/e2e/test_charter_epic_golden_path.py` now asserts non-null / non-empty / resolvable `prompt_file` for every `kind=step` envelope and a non-empty `reason` for `decision=blocked` envelopes. The latent contract gap that allowed empty prompt files into the golden path is closed by tests, not by silent acceptance.
- **CI mypy hygiene (FR-008 → resolves the mypy aspect of #848):** `.github/workflows/ci-quality.yml` `e2e-cross-cutting` job now installs `pip install -e .[test,lint]`, so `tests/cross_cutting/test_mypy_strict_mission_step_contracts.py` runs and passes in CI. The unrelated `uv.lock` vs installed `spec-kitty-events` pin drift remains tracked under #848.

This PR closes spec FR-001..FR-008, FR-011, FR-012, FR-013 of mission `charter-contract-cleanup-tranche-1-01KQATS4`, and verifies (without introducing changes) FR-009 / FR-010 regression guards.

## Evidence

Local five-command test gate (NFR-001) executed on this branch at 2026-04-29T05:56Z. Full captures live under `kitty-specs/charter-contract-cleanup-tranche-1-01KQATS4/research/_artifacts/test-gate-*.txt`. Summary:

| # | Command | Outcome |
|---|---|---|
| 1 | `uv run pytest tests/e2e/test_charter_epic_golden_path.py -q` | **PASS** (1 passed, 45.36s) |
| 2 | `uv run pytest tests/agent/cli/commands/test_charter_synthesize_cli.py tests/integration/test_json_envelope_strict.py tests/integration/test_charter_synthesize_fresh.py -q` | **PASS** (42 passed, 2.71s) |
| 3 | `uv run pytest tests/next/test_retrospective_terminus_wiring.py tests/retrospective/test_gate_decision.py tests/doctrine_synthesizer/test_path_traversal_rejection.py -q` | **PASS** (109 passed, 6.03s) |
| 4 | `uv run --extra test --extra lint pytest tests/cross_cutting/test_mypy_strict_mission_step_contracts.py -q` | **PASS** (1 passed, 6.62s) |
| 5 | `uv run ruff check src tests` | **FAIL — pre-existing, NOT a regression** (772 errors, all in unrelated files; pre-merge baseline was 773) |

**Triage of test-gate command #5 (ruff):** ruff on the seven mission-touched files (`src/charter/synthesizer/write_pipeline.py`, `src/specify_cli/cli/commands/charter.py`, the four mission tests, and `tests/charter/synthesizer/test_synthesize_path_parity.py`) reports `All checks passed!`. The 772 errors live in unrelated source (e.g. `src/charter/evidence/code_reader.py`, `src/doctrine/drg/migration/extractor.py`, `src/charter/resolution.py`). The pre-merge parent commit (`cb8bd1e2^`) reported 773 of the same errors; the merge actually removed one. This mission did not introduce any ruff regressions and the `quickstart.md` §1 NFR-001 ruff command is being filed for separate triage (see Protect-Main-Branch disposition section below — same pattern: a release-process gate that is failing on a non-product axis). Filing a follow-up issue is documented in `release-evidence.md`.

## Issues this PR closes

- **Closes #844** — golden-path E2E now asserts non-null / non-empty / resolvable `prompt_file` for `kind=step` envelopes (FR-006) and non-empty `reason` for blocked decisions (FR-007).

## Issues this PR comments on

- **#827 (Charter contract cleanup, parent epic)** — Tranche 1 (product-repo cleanup) lands here; tranches 2/3/4 (external-E2E repo, plain-English acceptance, etc.) remain open. **Do not close.**
- **#848 (mypy strict regression in cross-cutting CI)** — the mypy aspect resolved by FR-008. The `uv.lock` vs installed `spec-kitty-events` pin drift component remains tracked there.

## Out of scope

The following four tranches are explicitly **out of scope** for this PR:

1. **Tranche 2** — `spec-kitty-events` library: any further cleanup of the external `spec_kitty_events` package surface.
2. **Tranche 3 — external E2E** in `spec-kitty-end-to-end-testing` repo: golden-path coverage at the multi-repo integration boundary.
3. **Tranche 3 — plain-English acceptance** in `spec-kitty-plain-english-tests` repo: scenario-grade acceptance tests.
4. **Tranche 4** — docs mission (#828) and Phase 7 cleanup (#469): both remain open and untouched by this PR.

## `Protect Main Branch` workflow disposition

**Disposition: FILE-ISSUE** (release-process hygiene, not product code). See `kitty-specs/charter-contract-cleanup-tranche-1-01KQATS4/research/release-evidence.md` §T020 for full diagnosis and proposed issue body.

Short version: `.github/workflows/protect-main.yml` (line 78) accepts any squash commit whose subject contains the substring `kitty/mission-`. The current branch's underlying squash-merge commit (`cb8bd1e2`) does carry that substring (`feat(kitty/mission-charter-contract-cleanup-tranche-1-01KQATS4): squash merge of mission`). The risk is that GitHub's "Squash and Merge" UI defaults to the **PR title** as the squash commit subject — and the proposed PR title above does **not** contain `kitty/mission-`. If the human merger leaves the default subject, this workflow will fail post-merge on `main`. Mitigation options for the merger: (a) override the squash-commit subject to retain `kitty/mission-charter-contract-cleanup-tranche-1-01KQATS4`, or (b) accept the workflow failure and rely on the proposed follow-up issue to widen the regex for Conventional-Commit subjects with PR-number suffix (`(#N)`), which is already on line 69 of the workflow.
