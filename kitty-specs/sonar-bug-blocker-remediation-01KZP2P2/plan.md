# Implementation Plan: Sonar BUG and BLOCKER Remediation

**Branch**: `fix/sonar-bug-blocker-remediation` | **Date**: 2026-08-10 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/sonar-bug-blocker-remediation-01KZP2P2/spec.md`

## Summary

Remediate all 34 OPEN/CONFIRMED SonarCloud **BUG** and 7 **BLOCKER** issues at the root — no
suppressions. The work cleaves cleanly along a mechanical/investigate seam: the assertion and
parametrize defects (S5863/S5779/S8998) are largely mechanical test-integrity fixes, while the
security and control-flow defects (S2083 path-injection, S3516 always-same-return, S2583
always-true) require per-case investigation to distinguish a real bug from an intentional-but-smelly
construct (or a trusted-local false positive). The exact per-issue file:line inventory is in
[research/sonar-inventory.txt](./research/sonar-inventory.txt).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: pytest, ruff, mypy (existing toolchain only — no new dependencies)
**Storage**: N/A
**Testing**: existing pytest suite; scoped per-changed-file runs; red-first evidence for every recoverable-intent assertion fix (NFR-003); marker-convention + baselines respected for any new test file
**Target Platform**: Linux CI + cross-platform CLI
**Project Type**: single
**Performance Goals**: N/A (correctness/maintainability remediation)
**Constraints**: zero new suppression comments (`# noqa` / `# type: ignore` / `NOSONAR`) — NFR-001; trusted-local path exemption for S2083 requires a recorded rationale, not artificial sanitization (C-001); every new branch/helper gets a test in the same change (C-002)
**Scale/Scope**: 41 issues (34 BUG + 7 BLOCKER) across ~27 files (src + tests); HIGH-severity maintainability issues explicitly out of scope (C-003)

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Real fixes over suppression (charter Sonar Expectations)**: PASS — NFR-001 forbids new suppressions; every issue is fixed at the root or, for a genuine false positive, carries a written rationale (not a `NOSONAR`).
- **Test-first / red-first (DIRECTIVE_034; tests-as-scaffold-not-friction)**: PASS — NFR-003 requires red-first evidence for recoverable-intent assertion fixes; a corrected assertion must fail against the defect it replaces.
- **Loopback/local-only special case (charter Sonar Expectations)**: PASS — C-001 preserves safe trusted-local path semantics with a recorded rationale rather than forcing HTTPS/sanitization theatre.
- **New branch requires a test (Sonar new-code coverage)**: PASS — C-002.
- **Campsite / scope discipline**: PASS — C-003 bounds scope to the enumerated 41; HIGH maintainability is a separate per-module effort.

No charter violations. No Complexity Tracking entries required.

## Project Structure

### Documentation (this mission)

```
kitty-specs/sonar-bug-blocker-remediation-01KZP2P2/
├── plan.md                    # This file
├── spec.md
├── research/
│   ├── sonar-inventory.txt    # Exact per-issue file:line list (the 41)
│   └── ...                    # Phase 0 outputs
├── research.md                # Phase 0 approach/decisions
├── quickstart.md              # Phase 1: how to verify the remediation
├── checklists/requirements.md
└── tasks.md                   # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

Remediation touches existing files only — no new modules. Affected surfaces by concern:

```
src/
├── charter/pack_manager.py                         # S3516
├── specify_cli/
│   ├── cli/commands/{charter/lint.py, init.py, sync.py, _command_surface_doctor.py}  # S5779, S3516
│   ├── sync/events.py                              # S5779
│   ├── core/file_lock.py                           # S3516
│   ├── status/reducer.py                           # S3516
│   ├── merge/bookkeeping_projection.py             # S2083 ×2
│   └── skills/verifier.py                          # S2083
├── runtime/next/runtime_bridge.py                  # S2583
└── specify_cli/compat/remediation.py               # S2583

tests/
└── (~20 files across cross_cutting, sync, doctrine, specify_cli, architectural, …)  # S5863 ×16, S5779 ×10, S8998 ×2
```

**Structure Decision**: Single project; in-place edits to the files enumerated in
[research/sonar-inventory.txt](./research/sonar-inventory.txt). No structural change.

## Implementation Concern Map

> Concerns are not work packages. `/spec-kitty.tasks` maps these to WPs. The operator has
> pre-agreed a two-WP split: a **mechanical** WP (IC-03/IC-04/IC-05) and an **investigate** WP
> (IC-01/IC-02). IC-06 is cross-cutting verification folded into both.

### IC-01 — Path-injection containment (security)

- **Purpose**: Ensure filesystem paths are never built unsafely from externally-influenced data, closing the 3 S2083 BLOCKER hotspots.
- **Relevant requirements**: FR-001; C-001.
- **Affected surfaces**: `src/specify_cli/merge/bookkeeping_projection.py:212,346`, `src/specify_cli/skills/verifier.py:402`.
- **Sequencing/depends-on**: none.
- **Risks**: distinguishing a real traversal vector from a trusted-local path (mission/repo-internal data). Where trusted-local, keep semantics + record rationale (C-001); where reachable from external input, validate/contain and test the rejection path.

### IC-02 — Degenerate control flow (correctness)

- **Purpose**: Fix or redesign control flow Sonar proves is degenerate — methods that always return the same value (4× S3516) and conditions that can never be false (2× S2583).
- **Relevant requirements**: FR-002, FR-003.
- **Affected surfaces**: `src/charter/activation/pack_manager.py:559`, `src/specify_cli/cli/commands/_command_surface_doctor.py:164`, `src/specify_cli/core/file_lock.py:271`, `src/specify_cli/status/reducer.py:751`, `src/runtime/next/runtime_bridge.py:1497`, `src/specify_cli/compat/remediation.py:445`.
- **Sequencing/depends-on**: none.
- **Risks**: some may be intentional (protocol-conforming constant return / defensive guard). Each needs a judgment call: real bug → correct with a behavioral test; intentional → remove the smell (drop vacuous return, adjust signature, make invariant explicit) with a test — never a suppression.

### IC-03 — Tautological assertions (test integrity)

- **Purpose**: Restore real coverage for the 16 S5863 assertions that compare a value to itself.
- **Relevant requirements**: FR-004; NFR-003.
- **Affected surfaces**: ~13 test files (see inventory; incl. `tests/sync/*`, `tests/specify_cli/tool_surface/profiles/test_renderers.py` ×3, `tests/doctrine/missions/test_step_projection.py`, …).
- **Sequencing/depends-on**: none.
- **Risks**: recovering the intended comparison from test context; where unrecoverable, remove with rationale (edge case) rather than guess.

### IC-04 — Swallowed assertions (test + src integrity)

- **Purpose**: Restructure the 14 S5779 sites so an `assert` is not caught by its own `except AssertionError`.
- **Relevant requirements**: FR-005.
- **Affected surfaces**: 4 src (`charter/lint.py:127`, `init.py:838`, `cli/commands/sync.py:1129`, `sync/events.py:78`) + 10 tests.
- **Sequencing/depends-on**: none.
- **Risks**: the src sites need care — moving the assertion out of the handler must preserve the intended error translation/recovery, not just delete the guard.

### IC-05 — Empty parametrize (test integrity)

- **Purpose**: Make the 2 S8998 parametrized tests actually execute.
- **Relevant requirements**: FR-006.
- **Affected surfaces**: `tests/architectural/test_compat_shims.py:96,104`.
- **Sequencing/depends-on**: none.
- **Risks**: determine whether real cases exist (add them) or the parametrize is vestigial (remove so the test runs).

### IC-06 — Verification & non-regression (cross-cutting)

- **Purpose**: Prove the remediation is real and complete — no suppressions added, affected tests green, ruff/mypy clean, and the Sonar surface cleared.
- **Relevant requirements**: NFR-001, NFR-002, NFR-004; SC-001..004.
- **Affected surfaces**: mission diff (suppression scan), scoped pytest, `ruff`/`mypy`, post-merge SonarCloud re-scan.
- **Sequencing/depends-on**: follows IC-01..IC-05 (folded into each WP's DoD + a final aggregate check).
- **Risks**: SonarCloud re-scan is post-merge (like a gate-unmask) — pair the code fix with the verification method and record any residual false-positive rationale in the PR body.
