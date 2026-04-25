# Mission Acceptance Record — shared-package-boundary-cutover-01KQ22DS

This document records passive baseline measurements and acceptance evidence
captured after the post-merge mission-review cycle. Each entry is a
point-in-time observation; dates are local (UTC offset noted by `date -u`
where applicable).

## NFR-001 — Test coverage of post-cutover code

Scope: `src/specify_cli/next/_internal_runtime/` (the internalized runtime
package introduced by WP01 of this mission).

Tooling: `pytest --cov=src/specify_cli/next/_internal_runtime` over the
runtime parity + decision/runtime-bridge/query-mode unit suites (the tests
that actually exercise the internalized runtime — `tests/next/`).

- Coverage as of 2026-04-25: 50% (1383 statements, 685 missed) — measured via `pytest tests/next/test_internal_runtime_parity.py tests/next/test_decision_unit.py tests/next/test_runtime_bridge_unit.py tests/next/test_query_mode_unit.py --cov=src/specify_cli/next/_internal_runtime`.

Per-module breakdown at the same observation:

| Module | Stmts | Miss | Cover |
| --- | --- | --- | --- |
| `__init__.py` | 6 | 0 | 100% |
| `contracts.py` | 30 | 12 | 60% |
| `discovery.py` | 149 | 101 | 32% |
| `emitter.py` | 3 | 3 | 0% |
| `engine.py` | 500 | 302 | 40% |
| `events.py` | 46 | 16 | 65% |
| `lifecycle.py` | 3 | 3 | 0% |
| `models.py` | 5 | 5 | 0% |
| `planner.py` | 84 | 33 | 61% |
| `raci.py` | 61 | 30 | 51% |
| `schema.py` | 265 | 51 | 81% |
| `significance.py` | 231 | 129 | 44% |

This is a baseline only — no coverage floor is being asserted for
`_internal_runtime` in this measurement. Floor assertions remain on the
broader CLI surface via existing CI gates.

## NFR-002 — mypy strict verification of internalized runtime

Scope: `src/specify_cli/next/_internal_runtime/` under `mypy --strict`.

- mypy --strict as of 2026-04-25: FAIL — 32 errors across 5 files (12 source files checked). Dominant categories: missing `provider`/`model`/`tool` named arguments to `RuntimeActorIdentity` constructions in `engine.py`; `Literal[...]` mismatches for `SoftGateDecision.action` and `RACIRoleBinding.actor_type`; `attr-defined` re-export gaps in `events.py`; missing `types-PyYAML` stubs (`discovery.py`).

This is captured as a baseline; remediation is **not** in scope for this
post-merge follow-up branch. The errors are recorded so a future hardening
mission has a starting list. The runtime is functionally correct — the
parity tests pass — but it does not yet satisfy `--strict` static
verification.

## NFR-003 — `spec-kitty next` end-to-end latency

Scope: cold-process invocation of `spec-kitty next --agent test --mission
clean-install-fixture-01KQ22XX --json` against the bundled
`tests/fixtures/clean_install_fixture_mission` fixture.

Methodology: 5 sequential runs from a Python harness using
`subprocess.run` + `time.perf_counter()`, on macOS (Darwin 24.6.0,
CPython 3.14.0), against an editable-installed CLI.

- Latency as of 2026-04-25: mean **0.527s**, min 0.519s, max 0.543s, n=5. Individual runs (s): 0.543, 0.526, 0.519, 0.520, 0.526.

This is comfortably below the WP-level NFR target (the CI clean-install
job uses a 5-minute timeout for the full venv-build + install + run; the
hot-path command itself is sub-second).
