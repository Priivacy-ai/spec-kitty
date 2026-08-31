# Quickstart — Charter Contract Cleanup Tranche 1

**Mission:** `charter-contract-cleanup-tranche-1-01KQATS4`
**Repo:** `/Users/robert/spec-kitty-dev/spec-kitty-20260428-193814-MFDsf5/spec-kitty`

This document is the reproducible recipe for verifying the mission's contracts on the feature branch before opening the PR.

---

## 0. Working Directory

```bash
cd /Users/robert/spec-kitty-dev/spec-kitty-20260428-193814-MFDsf5/spec-kitty
git status --short --branch
```

The mission expects the agent to land work on feature branch `fix/charter-827-contract-cleanup` (created by `/spec-kitty.implement` at lane time). All commands below run from the repo root checkout in either the planning branch (`main`) or the implementation worktree, as appropriate.

---

## 1. Required Local Test Gate (NFR-001)

These five commands must all exit `0` before the PR is opened. Run from the implementation worktree.

```bash
# 1. Charter epic golden-path E2E (covers FR-006, FR-007, FR-010 verifications)
uv run pytest tests/e2e/test_charter_epic_golden_path.py -q

# 2. Charter synthesize JSON contract suite (covers FR-001, FR-002, FR-003, FR-004, FR-005)
uv run pytest \
  tests/agent/cli/commands/test_charter_synthesize_cli.py \
  tests/integration/test_json_envelope_strict.py \
  tests/integration/test_charter_synthesize_fresh.py -q

# 3. Regression-guard suite (covers FR-009 verification — verify, do NOT rewrite)
uv run pytest \
  tests/next/test_retrospective_terminus_wiring.py \
  tests/retrospective/test_gate_decision.py \
  tests/doctrine_synthesizer/test_path_traversal_rejection.py -q

# 4. Strict-typing executor test (covers FR-008)
uv run --extra test --extra lint pytest \
  tests/cross_cutting/test_mypy_strict_mission_step_contracts.py -q

# 5. Lint
uv run ruff check src tests
```

Capture each terminal block in the PR description as evidence (SC-006).

---

## 2. Strict Type Check on Touched Runtime Code (NFR-004)

```bash
uv run mypy --strict src/specify_cli/cli/commands/charter.py
# Run for write_pipeline only if it was modified for FR-003:
uv run mypy --strict src/charter/synthesizer/write_pipeline.py
uv run mypy --strict src/specify_cli/mission_step_contracts/executor.py
```

All three (or two, if `write_pipeline.py` was not touched) must exit `0`.

---

## 3. `PROJECT_000` Regression Sweep (FR-005)

This is a code-level sanity check that the placeholder is not user-visible:

```bash
# 1. No --json envelope path emits the placeholder. Inspect call sites in charter.py.
rg -n "PROJECT_000" src/specify_cli/cli/commands/charter.py

# 2. The placeholder may remain in internal staging code; ensure none of those values
#    flow into the envelope or any user-facing string formatter.
rg -n 'f".*PROJECT_000\b' src tests
rg -n '"PROJECT_000"' src tests
```

The expectation: zero matches under user-facing CLI/output code paths. Internal-only token usage (e.g. an internal default in a SynthesisRequest constructor that is never serialized) is fine.

---

## 4. Hosted-Surface Command Rule (NFR-005, C-005)

Any command that touches hosted auth, tracker, SaaS sync, or sync behaviour MUST be invoked with the env var set:

```bash
SPEC_KITTY_ENABLE_SAAS_SYNC=1 <command>
```

The local test gate above does NOT touch hosted surfaces, so it does not need the env var. Any new test added by this mission that does touch a hosted surface must encode the env var in the test fixture (or reject the run when it is unset).

---

## 5. CI Verification

After pushing the feature branch, monitor checks:

```bash
gh pr checks --watch
```

Expectations on the head commit:

- `e2e-cross-cutting` job exits with status 0; no `python -m mypy: not found` log lines.
- All other previously-green checks remain green (NFR-002).
- If the `Protect Main Branch` failure persists and is reproducible from product code, fix it in this PR. If it is release-process hygiene only, file/update a GitHub issue and link it from the PR description (FR-013).

---

## 6. Issue Hygiene (post-merge)

Run after the PR is merged (FR-011, R-010):

```bash
# Use keyring scopes if GITHUB_TOKEN has limited scopes (per CLAUDE.md)
unset GITHUB_TOKEN

# #844 — close or comment with evidence (FR-006/FR-007 land)
gh issue close 844 --comment "Closed by PR #<merged-pr>: golden-path E2E now asserts non-null/resolvable prompt files for issued actions and non-empty reason for blocked decisions."

# #827 — comment, do NOT close (Tranche 3 external + plain-English remain)
gh issue comment 827 --body "Tranche 1 (product-repo cleanup) merged in PR #<merged-pr>: Charter --json envelope contract, dry-run path parity, golden-path prompt-file assertion, mypy CI hygiene. Remaining: Tranche 3 external E2E in spec-kitty-end-to-end-testing, plain-English acceptance in spec-kitty-plain-english-tests."

# #848 — update if the mypy/uv-lock/environment situation is resolved or reclassified
gh issue comment 848 --body "Resolved by PR #<merged-pr>: e2e-cross-cutting CI job now installs the lint extra; tests/cross_cutting/test_mypy_strict_mission_step_contracts.py runs and passes there."

# #828 — do NOT close (docs mission remains)
# #469 — do NOT touch (Phase 7 out of scope)
```

---

## 7. Quick Reference — Files Touched (planning estimate)

This is a planning estimate only; the implementation phase finalises the concrete diff.

| Likely-modified file | Why |
|---|---|
| `src/specify_cli/cli/commands/charter.py` | FR-001, FR-002, FR-003, FR-004, FR-005 |
| `src/charter/synthesizer/write_pipeline.py` | FR-003 only if the staged-artifact return shape needs to grow |
| `tests/agent/cli/commands/test_charter_synthesize_cli.py` | New / hardened assertions for FR-001, FR-002 |
| `tests/integration/test_json_envelope_strict.py` | New / hardened FR-001 strict-stdout regression test |
| `tests/integration/test_charter_synthesize_fresh.py` | FR-002 envelope shape on fresh-project seed |
| `tests/charter/synthesizer/test_<…>.py` (new or modified) | FR-003, FR-004, FR-005 path parity |
| `tests/e2e/test_charter_epic_golden_path.py` | FR-006, FR-007 |
| `.github/workflows/ci-quality.yml` | FR-008 (single-line install change in `e2e-cross-cutting`) |

Files explicitly NOT modified (regression guards, FR-009/FR-010 verify-only):

- `src/specify_cli/next/runtime_bridge.py`
- `src/charter/retrospective/schema.py`
- `tests/next/test_retrospective_terminus_wiring.py`
- `tests/retrospective/test_gate_decision.py`
- `tests/doctrine_synthesizer/test_path_traversal_rejection.py`
- `_parse_first_json_object` and `_run_next_and_assert_lifecycle` helpers in the golden-path E2E (unless the FR-006/FR-007 hardening unavoidably touches them, in which case the change is minimal and the existing assertions are preserved).

(unless verification fails, in which case the failing item becomes a new in-scope item per C-003.)
