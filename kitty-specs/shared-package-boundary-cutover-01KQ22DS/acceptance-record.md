# Mission Acceptance Record — shared-package-boundary-cutover-01KQ22DS

This document records passive baseline measurements and acceptance evidence
captured after the post-merge mission-review cycle. Each entry is a
point-in-time observation; dates are local (UTC offset noted by `date -u`
where applicable).

The original entries from 2026-04-25 (mission-merge time) recorded
deviations against three Required NFRs. Those NFRs were closed in the
post-merge `post-merge/shared-package-boundary-cutover-01KQ22DS-nfr-closure`
branch. The closure data follows each baseline.

## NFR-001 — Test coverage of post-cutover code

Scope: `src/specify_cli/next/_internal_runtime/` (the internalized runtime
package introduced by WP01 of this mission).

Tooling: `pytest --cov=src/specify_cli/next/_internal_runtime` over the
runtime parity + decision/runtime-bridge/query-mode unit suites plus the
two new coverage suites (the tests that actually exercise the internalized
runtime — `tests/next/`).

### Baseline (mission-merge, 2026-04-25)

50% (1383 statements, 685 missed) — measured via:

```bash
pytest tests/next/test_internal_runtime_parity.py \
       tests/next/test_decision_unit.py \
       tests/next/test_runtime_bridge_unit.py \
       tests/next/test_query_mode_unit.py \
       --cov=src/specify_cli/next/_internal_runtime
```

Per-module breakdown at the baseline:

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

### Closure (post-merge, 2026-04-25)

**92%** (1386 statements, 117 missed) — measured via:

```bash
pytest tests/next/test_internal_runtime_parity.py \
       tests/next/test_decision_unit.py \
       tests/next/test_runtime_bridge_unit.py \
       tests/next/test_query_mode_unit.py \
       tests/next/test_internal_runtime_coverage.py \
       tests/next/test_internal_runtime_engine_coverage.py \
       --cov=src/specify_cli/next/_internal_runtime
```

Per-module breakdown at closure:

| Module | Stmts | Miss | Cover |
| --- | --- | --- | --- |
| `__init__.py` | 6 | 0 | 100% |
| `contracts.py` | 30 | 0 | 100% |
| `discovery.py` | 149 | 6 | 96% |
| `emitter.py` | 3 | 0 | 100% |
| `engine.py` | 502 | 61 | 88% |
| `events.py` | 47 | 0 | 100% |
| `lifecycle.py` | 3 | 0 | 100% |
| `models.py` | 5 | 0 | 100% |
| `planner.py` | 84 | 5 | 94% |
| `raci.py` | 61 | 4 | 93% |
| `schema.py` | 265 | 13 | 95% |
| `significance.py` | 231 | 28 | 88% |

The two modules that sit at 88% (`engine.py`, `significance.py`) have
remaining gaps in (a) defensive `@model_validator` branches that fire only
on malformed snapshots written by future-incompatible runtimes, and (b)
the WP05 soft-gate post-answer `SoftGateDecision` construction inside an
audit-step end-to-end flow whose cutoff sensitivity makes it environment-
dependent. Aggregate is well above the 90% NFR floor.

**Verdict: PASS — 92%, exceeds NFR-001 90% threshold.**

Tests added:

- `tests/next/test_internal_runtime_coverage.py` — ~110 unit tests
- `tests/next/test_internal_runtime_engine_coverage.py` — ~30 unit tests

The coverage suite includes a guard test that scans the runtime source
tree for stray `spec_kitty_runtime` imports, locking the cross-repo
boundary into the per-PR test surface.

## NFR-002 — mypy strict verification of internalized runtime

Scope: `src/specify_cli/next/_internal_runtime/` under `mypy --strict`.

### Baseline (mission-merge, 2026-04-25)

FAIL — 32 errors across 5 files (12 source files checked). Dominant
categories: missing `provider`/`model`/`tool` named arguments to
`RuntimeActorIdentity` constructions in `engine.py`; `Literal[...]`
mismatches for `SoftGateDecision.action` and `RACIRoleBinding.actor_type`;
`attr-defined` re-export gaps in `events.py`; missing `types-PyYAML`
stubs (`discovery.py`).

### Closure (post-merge, 2026-04-25)

**0 errors / 12 source files checked.** Tooling: `mypy 1.20.2` with
`pydantic 2.13.3` (the pydantic mypy plugin is not used because
`pydantic.mypy` is incompatible with mypy 1.20+ on Python 3.14; fixes
were applied at call sites instead, since the plugin's removal of those
errors would otherwise have been spurious.) `types-PyYAML` is already
declared as an optional/dev dependency in `pyproject.toml`.

```bash
$ mypy --strict src/specify_cli/next/_internal_runtime/
Success: no issues found in 12 source files
```

Files modified for fixes:

- `src/specify_cli/next/_internal_runtime/events.py` — explicit `__all__` for re-exports.
- `src/specify_cli/next/_internal_runtime/engine.py` — explicit `provider=None,
  model=None, tool=None` at all five `RuntimeActorIdentity` call sites; type-narrowed
  loops in `_find_step_by_id`; `cast(...)` of the SoftGate `action` and `actor_type`
  to their `Literal` types.
- `src/specify_cli/next/_internal_runtime/raci.py` — `cast(...)` of the
  unresolved-role fallback in `_resolve_actor` to `Literal["responsible",
  "accountable"]`.
- `src/specify_cli/next/_internal_runtime/significance.py` — parameterized bare
  `dict` annotations on payload models as `dict[str, Any]`; dropped a now-unused
  `# type: ignore[arg-type]`.

**Verdict: PASS — 0 errors.**

## NFR-003 — `spec-kitty next` end-to-end latency

Scope: cold-process invocation of `spec-kitty next --agent test --mission
clean-install-fixture-01KQ22XX --json` against the bundled
`tests/fixtures/clean_install_fixture_mission` fixture.

Methodology: 5 sequential runs from a Python harness using
`subprocess.run` + `time.perf_counter()`, on macOS (Darwin 24.6.0,
CPython 3.14.0), against an editable-installed CLI.

### Baseline (mission-merge, 2026-04-25)

Post-cutover only: mean 0.527s, min 0.519s, max 0.543s, n=5. Individual
runs (s): 0.543, 0.526, 0.519, 0.520, 0.526. **No pre-cutover comparison
was captured at the time**, so the spec's "≤20% regression vs pre-cutover
baseline" requirement could not be verified at merge time.

### Closure (post-merge, 2026-04-25)

A pre-cutover worktree was set up at `cbe62677` (`docs: define shared
package boundaries`, the immediate-pre-mission `main` checkpoint) with
`spec-kitty-runtime` installed alongside `spec-kitty-events==4.0.0`, the
same fixture copied in, and the same 5-run harness used to capture the
baseline.

| Side | sha | runs (s) | median (s) |
| --- | --- | --- | --- |
| pre-cutover | `cbe62677` | 0.723, 0.715, 0.748, 0.794, 0.745 | **0.745** |
| post-cutover | `post-merge/.../nfr-closure` | 0.800, 0.663, 0.714, 0.667, 0.688 | **0.688** |

**Delta:** `(0.688 - 0.745) / 0.745 = -7.7%` — i.e. the post-cutover code
is *faster*, not slower; well within the 20% tolerance window in the
favourable direction.

**CI gate:**

- New baseline file: `kitty-specs/shared-package-boundary-cutover-01KQ22DS/nfr-003-baseline.json` (pinned pre-cutover median + tolerance).
- New script: `scripts/check_nfr_003_latency.py` runs 5 fresh `spec-kitty next` invocations against the fixture and fails if `current_median > pre_cutover_median * (1 + tolerance_pct/100)` (default 20%).
- New CI step: `.github/workflows/ci-quality.yml` `clean-install-verification` job appends `python scripts/check_nfr_003_latency.py` after the existing fixture-validation step.

**Verdict: PASS — −7.7% (improvement).**
