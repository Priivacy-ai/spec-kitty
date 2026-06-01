# Implementation Plan: P0 Test Failure Resolution — Release Blockers 1298-1305

**Branch**: `kitty/mission-p0-test-failure-resolution-1298-1305-01KT1R2G` | **Date**: 2026-06-01 | **Spec**: [spec.md](spec.md)  
**Input**: `kitty-specs/p0-test-failure-resolution-1298-1305-01KT1R2G/spec.md`

## Summary

Fix four P0 test-failure clusters that are blocking the 3.2.0 release. Work is strictly
sequential: WP01 refreshes the test baseline on current `main` to confirm which issues still
reproduce; each subsequent WP fixes exactly one cluster in priority order
(#1301 → #1305 → #1304 → #1303), adds targeted regression coverage, and verifies with a
focused test run before the next WP begins.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: pytest, mypy (--strict), ruamel.yaml, typer, rich; `spec_kitty_events` (external PyPI, version pinned in `uv.lock`)  
**Storage**: Filesystem only — YAML frontmatter in Markdown, JSONL event logs, JSON meta files  
**Testing**: `PWHEADLESS=1 pytest` for full-suite; targeted `pytest <module> -q` per cluster; mypy --strict for type gate  
**Target Platform**: Linux / macOS (CI via GitHub Actions)  
**Project Type**: Single Python package (`src/specify_cli/`)  
**Performance Goals**: N/A — this is a correctness-and-stability mission  
**Constraints**: Net failure count after all fixes ≤ refreshed baseline; no new mypy --strict errors; ≥ 90% line coverage for any new code paths; each fix is scoped to its issue cluster only

## Charter Check

- **DIRECTIVE_001 (Architectural Integrity)** — Each fix touches an isolated subsystem. No cross-subsystem abstractions are added. ✓
- **DIRECTIVE_003 (Decision Documentation)** — The sequential execution order and root-cause rationale are documented in `research.md`. ✓
- **DIRECTIVE_010 (Specification Fidelity)** — Every fix is traceable to an FR in `spec.md`. ✓
- **DIRECTIVE_024 (Locality of Change)** — Each WP changes only the files belonging to its issue cluster. ✓
- **DIRECTIVE_037 (Living Documentation Sync)** — If any fix changes externally observable behavior, the corresponding test description is updated to match. ✓

No charter violations.

## Project Structure

### Documentation (this feature)

```
kitty-specs/p0-test-failure-resolution-1298-1305-01KT1R2G/
├── spec.md          # Specification
├── plan.md          # This file
├── research.md      # Phase 0 — root-cause analysis per cluster
└── tasks.md         # Phase 2 output (/spec-kitty.tasks)
```

### Source Code (affected paths per cluster)

```
# Cluster #1301 — shared-package/events drift
src/specify_cli/spec_kitty_events/       # must NOT exist after fix (vendored copy removed)
tests/sync/                              # test_events.py, test_lifecycle_readiness.py,
                                         # test_daemon_intent_gate.py
tests/sync/tracker/                      # test_origin_integration.py
tests/contract/                          # test_handoff_fixtures.py,
                                         # test_packaging_no_vendored_events.py,
                                         # test_example_round_trip.py (YAML codeblock)
pyproject.toml / uv.lock                 # version pin (if re-sync is needed)

# Cluster #1305 — next CLI exit-code regressions
src/specify_cli/next/                    # decide_next dispatch / exit-code logic
tests/next/                              # test_next_command_integration.py,
                                         # test_query_mode_unit.py

# Cluster #1304 — doctrine/glossary anchor drift
glossary/contexts/                       # anchor files for doctrine-pack,
                                         # platform-darwin--platform-linux
src/specify_cli/doctrine/ (or glossary/) # five-paradigm-parallel-debugging tactic YAML
tests/doctrine/                          # test_glossary_link_integrity.py,
                                         # test_tactic_compliance.py

# Cluster #1303 — charter synthesizer non-determinism
src/specify_cli/charter_lint/synthesizer/ # or equivalent synthesizer path
src/specify_cli/path_guard.py             # write-primitive chokepoint
tests/charter/synthesizer/               # test_bundle_validate_extension.py (5 tests)
```

**Structure Decision**: Single-project layout (`src/specify_cli/`). No new directories are created; fixes modify existing files within each cluster's established module boundaries.

## Work Package Sequence

All WPs are sequential. Each depends on the one before it.

| WP | Title | Cluster | Key deliverable |
|----|-------|---------|-----------------|
| WP01 | Baseline Refresh | #1298 | Documented current-main failure count + still-reproducing cluster list |
| WP02 | Shared-Package Events Drift Fix | #1301 | `tests/sync/` + `tests/contract/` green |
| WP03 | `next` CLI Exit-Code Fix | #1305 | `tests/next/` green |
| WP04 | Doctrine / Glossary Anchor Fix | #1304 | `tests/doctrine/` green |
| WP05 | Charter Synthesizer Determinism Fix | #1303 | `tests/charter/synthesizer/` green |

## Execution Rules

- WP01 must complete and its output (still-reproducing set) must be reviewed before WP02 begins.
- Each WP after WP01: run targeted tests to reproduce the cluster, identify root cause from source, implement minimal fix, add/update regression test, run targeted tests to verify green, then run a broader relevant test slice.
- No WP bundles fixes from a different cluster.
- Commits are issue-scoped (`fix(#NNNN): ...` style).

## Complexity Tracking

No charter violations require justification.
