# Contracts — Charter Contract Cleanup Tranche 1

This directory carries the user-visible contracts the mission introduces or hardens. Each file is normative; tests and PR-time review check against them.

| Contract | File | Owns |
|---|---|---|
| Charter synthesize JSON envelope | [synthesis-envelope.schema.json](./synthesis-envelope.schema.json) | Stable shape of `spec-kitty charter synthesize ... --json` stdout. Required fields, dry-run/non-dry-run parity, `PROJECT_000` exclusion |
| Golden-path envelope assertions | [golden-path-envelope-assertions.md](./golden-path-envelope-assertions.md) | What `tests/e2e/test_charter_epic_golden_path.py` asserts about issued-action and blocked-decision envelopes |
| `e2e-cross-cutting` mypy availability | [ci-job-mypy-availability.md](./ci-job-mypy-availability.md) | The CI environment contract for `tests/cross_cutting/test_mypy_strict_mission_step_contracts.py` |

Cross-references:

- [spec.md](../spec.md) — mission spec (FRs, NFRs, acceptance criteria)
- [research.md](../research.md) — Phase 0 decisions and rationale
- [data-model.md](../data-model.md) — data shapes the contracts reference
- [quickstart.md](../quickstart.md) — verification recipe
