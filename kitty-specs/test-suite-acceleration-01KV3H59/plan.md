# Implementation Plan: Test Suite Acceleration

**Branch**: `feat/test-suite-acceleration` | **Date**: 2026-06-14 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/test-suite-acceleration-01KV3H59/spec.md`
**Evidence source**: [`architecture/test-suite-acceleration-plan.md`](../../architecture/test-suite-acceleration-plan.md) (43-agent verified audit)

## Summary

Make the ~1,457-file pytest suite run much faster in CI and locally with **zero
loss of coverage quality**. The technical approach is settled by the verified
audit: (1) introduce **per-worker home/state isolation** so parallel workers
never share the real `~/.spec-kitty/queue.db` — this is the master enabler;
(2) flip the single-process CI fast-shards to file-pinned parallel execution
(`-n auto --dist loadfile`), one shard at a time behind a stability ratchet,
charter first; (3) enable a safe local multi-process default; (4) remove
item-explosion and redundant execution (FSM parity matrix, ULID volume,
migration de-dup, AST/DRG caching, templated git repo) — each behind a
collection-equivalence and (where behavior is restructured) mutation/equivalence
safeguard. A coverage-safety harness (collection-count equivalence + run-twice
ratchet + a guard that fails if any test touches the real home under xdist)
gates every risky change.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: pytest ≥ 9, pytest-xdist ≥ 3.8 (`-n auto --dist loadfile`, already in production on integration shards), pytest-asyncio, pytest-cov, pytest-timeout; GitHub Actions (`.github/workflows/ci-quality.yml`)
**Storage**: Filesystem — per-worker temp `HOME`/`XDG`/`LOCALAPPDATA` dirs; the hazard under remediation is the shared real SQLite `~/.spec-kitty/queue.db`
**Testing**: pytest is both the tool and the subject. Safeguards: collection-node-count equivalence, run-twice/run-thrice stability ratchet, mutation/equivalence checks for restructured tests, an architectural guard asserting no test mutates real `Path.home()/.spec-kitty` under xdist
**Target Platform**: Linux (CI `ubuntu-latest`), macOS, Windows — isolation must cover `HOME`, `USERPROFILE`, `LOCALAPPDATA`
**Project Type**: single (CLI package + its test suite + CI workflow definitions)
**Performance Goals**: ≥ 2× local full-suite wall-clock on a ≥4-core machine (NFR-001); charter shard ~9 min → ≤ 5 min (NFR-002); ≥ 60 s/push CPU removed by the safe-now wave alone (NFR-003)
**Constraints**: zero coverage decrease & no dropped tests (C-001, NFR-004, NFR-007); file-pinned distribution only, never bare `--dist load` (C-003); volume-sensitive guards retained nightly/env-gated (C-004); no production signature changes for tests (C-006); integrity/idempotency/freshness tests excluded from caching (C-007); all changes land via PR to `origin/main` (C-002)
**Scale/Scope**: ~1,457 test files, 33 conftest.py (~4,730 lines of fixtures), ~20 CI jobs; 315 subprocess-using files, 233 real-`git init` files, 32 `time.sleep` calls

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter present at `.kittify/charter/charter.md`. Plan-action directives:
DIRECTIVE_001, _003 (Decision Documentation), _010 (Specification Fidelity),
_024, _037.

| Gate | Status | Notes |
|------|--------|-------|
| Specification Fidelity (DIRECTIVE_010) | PASS | Plan maps 1:1 to spec FR/NFR/C; deviations would be documented. |
| Decision Documentation (DIRECTIVE_003) | PASS | Key decisions captured in `research.md` with rationale + alternatives. |
| New-code coverage ≥ 90% | PASS (by design) | Added fixtures/helpers ship with focused tests (IC-07); product coverage cannot drop (C-001). |
| `mypy --strict` + `ruff`, complexity ≤ 15 | PASS (by design) | NFR-006; new helpers are small and typed. |
| Terminology Canon (Mission, not feature) | PASS | Prose uses "Mission"; no new `feature*` aliases introduced. |
| No direct push to `origin/main` | PASS | Lands via PR (C-002). |
| Loopback/local-only semantics preserved | PASS | Daemon/port tests kept in a serial pass (FR-005), not forced parallel. |

No charter violations → Complexity Tracking section omitted.

## Project Structure

### Documentation (this mission)

```
kitty-specs/test-suite-acceleration-01KV3H59/
├── plan.md              # This file
├── research.md          # Phase 0 — settled decisions + rationale
├── data-model.md        # Phase 1 — test-infra construct shapes & invariants
├── quickstart.md        # Phase 1 — how to validate speed + coverage-neutrality
├── contracts/           # Phase 1 — behavioral contracts (isolation, equivalence, local command)
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

This mission edits test infrastructure and CI definitions, not product `src/`:

```
tests/
├── conftest.py                  # root: add per-worker home/state isolation fixture (IC-02)
├── <pkg>/conftest.py            # 33 conftests: dedupe shared fixtures, add templated-repo + cached read-only fixtures (IC-03, IC-05)
├── status/test_transitions.py   # FSM parity matrix collapse (IC-03)
├── charter/test_integration.py  # timing-floor → timeout conversion (IC-01)
└── _support/ (new)              # shared coverage-safety helpers: collection-equivalence, ratchet (IC-07)

.github/workflows/
└── ci-quality.yml               # flip fast-shards to -n auto --dist loadfile; status re-route; slow-test de-dup (IC-01, IC-04)

pyproject.toml / pytest.ini      # markers, addopts (-v removal), volume env-gates (IC-01)
architecture/test-suite-acceleration-plan.md   # authoritative evidence (read-only reference)
docs / CLAUDE.md                 # documented local parallel command (IC-06; updated during implement, not plan)
```

**Structure Decision**: Single-project layout. All changes live under `tests/`,
`.github/workflows/`, and build config (`pyproject.toml`/`pytest.ini`). No
product `src/` behavior changes. A new `tests/_support/` module hosts the
coverage-safety helpers so they are importable and unit-testable.

## Implementation Concern Map

> Concerns are architectural areas, not work packages. `/spec-kitty.tasks` will
> translate these into executable WPs (one IC may become several WPs).

### IC-01 — Safe-now coverage-neutral quick wins

- **Purpose**: Land the wave-1 wins that need no parallelism dependency, removing ≥60s/push immediately at zero coverage risk.
- **Relevant requirements**: FR-006, FR-007, FR-008, FR-013; NFR-003.
- **Affected surfaces**: `tests/charter/test_integration.py` (timing→`@pytest.mark.timeout`), ULID volume test (+ `SPEC_KITTY_ULID_VOLUME_FULL` env-gate), migration perf `@slow` de-dup in `ci-quality.yml` (specify-cli-heavy `and not slow`), 2 sync sleeper no-ops, `-v` removal from `pytest.ini` addopts.
- **Sequencing/depends-on**: none (independent first wave).
- **Risks**: must keep functional asserts when converting timing floors; de-dup must not orphan the 3 specify_cli NFR guards — collection-count gate required.

### IC-02 — Per-worker home/state isolation (master enabler)

- **Purpose**: Give each xdist worker a distinct home/config/state dir so parallel runs never share or truncate the real `~/.spec-kitty/queue.db`.
- **Relevant requirements**: FR-002; SC-006; C-005.
- **Affected surfaces**: `tests/conftest.py` (worker-id-keyed autouse fixture patching `Path.home` + `HOME`/`USERPROFILE`/`LOCALAPPDATA`/`XDG_*`); retain existing intra-worker queue-wipe fixtures; audit import-time `SPEC_KITTY_DIR` reads.
- **Sequencing/depends-on**: none. **Gates IC-04, IC-05, IC-06.**
- **Risks**: must key off xdist worker-id (NOT session-only, which re-collides); a regression test must prove two workers resolve distinct homes and never touch real state.

### IC-03 — Item-explosion & redundant read-only work removal

- **Purpose**: Cut collected-item explosion and per-test rebuilds of read-only state without losing assertions.
- **Relevant requirements**: FR-008, FR-009; C-007; NFR-007.
- **Affected surfaces**: FSM parity matrix collapse (`tests/status/test_transitions.py`, accumulate-all + count assert); shared migrated-project fixture for the 3 identical read-only migration asserts (counter/rollback/dry-run excluded); cached whole-tree AST (architectural) + DRG graph (doctrine) behind module/session fixtures, excluding idempotency/existence/freshness tests.
- **Sequencing/depends-on**: IC-01 (slow-test de-dup lands first); uses IC-07 safeguards.
- **Risks**: fixture sharing must be read-only; mutation test required for the FSM collapse; integrity tests must be carved out.

### IC-04 — CI fast-shard parallelization rollout

- **Purpose**: Flip single-process fast-shards to file-pinned parallel execution, collapsing the critical path.
- **Relevant requirements**: FR-003, FR-004, FR-005, FR-012; NFR-002, NFR-005.
- **Affected surfaces**: `ci-quality.yml` fast shards (charter first, then doctrine, cli, sync, agent, status); exclude tiny `release` shard; daemon/real-port sync tests to a serial pass; status re-route (inversion + collection gate + trigger widening).
- **Sequencing/depends-on**: charter sub-flip needs IC-01 timing fix; cli/sync/agent + status need IC-02; every flip gated by IC-07 ratchet.
- **Risks**: `--dist loadfile` only; per-shard run-twice ratchet; re-measure the 9→5 min claim, don't assume.

### IC-05 — Structural fixtures & hygiene

- **Purpose**: Replace repeated real `git init` with a templated baseline repo and finish the lower-leverage structural cleanups.
- **Relevant requirements**: FR-010; C-004, C-006.
- **Affected surfaces**: templated bare-repo fixture (clone-per-test) gated by execution-allowlist (not grep-by-symbol), preserving bespoke unborn/detached/bare/worktree setups; collect-only consolidation (architectural); sync concurrency-loop trims with a retained high-volume nightly variant; xfail strictness hygiene.
- **Sequencing/depends-on**: IC-02 (parallel-safe); split AST-cache vs template-clone into separate commits.
- **Risks**: allowlist must cover transitive callers; concurrency trims must keep a ≥50 nightly variant.

### IC-06 — Local parallel default & contributor docs

- **Purpose**: Make safe local multi-process runs the documented default.
- **Relevant requirements**: FR-001, FR-011; NFR-001; SC-001.
- **Affected surfaces**: documented command `PWHEADLESS=1 pytest tests/ -n auto --dist loadfile -p no:cacheprovider` + serial daemon-pass caveat; `CLAUDE.md`/docs update (during implement).
- **Sequencing/depends-on**: IC-02 + the charter timing fix proven green under `-n auto`; publish only after IC-04 charter flip is green.
- **Risks**: must document the serial pass for port/daemon tests.

### IC-07 — Coverage-safety harness (cross-cutting)

- **Purpose**: Provide the safeguards that make every reduction/flip provably coverage-neutral.
- **Relevant requirements**: C-001; NFR-005, NFR-007; FR-004, FR-012.
- **Affected surfaces**: `tests/_support/` helpers — per-shard collection-node-count equivalence (serial vs xdist), run-twice/run-thrice ratchet harness, an architectural guard failing on real-home mutation under xdist; mutation/equivalence check recipe for restructured tests.
- **Sequencing/depends-on**: lands alongside/just before IC-03 and IC-04 (they consume it).
- **Risks**: the harness itself needs unit tests (it is new code under the 90% gate).
