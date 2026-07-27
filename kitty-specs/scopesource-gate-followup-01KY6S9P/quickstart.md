# Quickstart / Validation — ScopeSource gate follow-up

How to prove the mission is done. All commands use `PYTHONPATH=$(pwd)/src`. Base: merged `main` `eb06ca176`.

## 0. Baseline-red-gotcha check (before attributing any failure)

Confirm the gate-family tests are green (or record their pre-existing red) on the merge-base, so a failure isn't misattributed to this mission's diff (#2825):

```bash
PYTHONPATH=$(pwd)/src python -m pytest \
  tests/architectural/test_no_dead_symbols.py \
  tests/architectural/test_golden_count_ban.py \
  tests/specify_cli/cli/commands/agent/test_tasks_compat_surface.py -q -p no:cacheprovider
```

## 1. WP-C correctness — the reason the mission exists (US1 / SC-001 / SC-004)

The dual-impl / dual-parse-mode parity test (IC-12, FR-010) is the headline proof:

```bash
# Must NOT raise NEW_FAILURES in any of the 4 combinations
#   {GateCoverageScopeSource, DeclaredCommandScopeSource} × {worktree-relative JUnit, FAIL-text}
# and a deliberately mismatched pair MUST raise GateOutcome.SOURCE_MISMATCH (warn, fail-open)
PYTHONPATH=$(pwd)/src python -m pytest tests/review/ -k "parity or source_mismatch or teardown" -q -p no:cacheprovider
```

- **SC-001**: a repo with a non-pytest (worktree-relative-artifact) `review.test_command` runs the gate over a zero-new-failure change **without** a false `NEW_FAILURES` block.
- **SC-004**: a source/parse-mode mismatch surfaces `GateOutcome.SOURCE_MISMATCH` (never a silent block, never `NO_COVERAGE`).
- **FR-008 (B1)**: the baseline artifact is read/relocated **before** worktree teardown — the regression test reproduces the pre-fix disjoint-namespace bug red-first.
- **FR-009**: mismatched parse-mode (same class, same command) triggers the identity check; a legacy artifact without `source_identity` degrades to `UNVERIFIED_BASELINE`, never `KeyError`; the read goes through #2874's `_resolve_workflow_read_dir(kind=WORK_PACKAGE_TASK)` seam.
- **FR-012**: the anti-narrowing guard asserts baseline runs the whole command (no head per-file targets appended).

## 2. WP-A cleanup — behavior-preserving (US2 / SC-002 / SC-003)

```bash
# Behaviour-preservation goldens (captured pre-mission, replayed) over BOTH paths:
PYTHONPATH=$(pwd)/src python -m pytest tests/review/ tests/specify_cli/cli/commands/agent/ -k "golden or override_tier or compat_surface" -q -p no:cacheprovider
```

- **SC-002**: the live `for_review` gate AND the override tier produce byte-identical verdicts + metadata before/after (NFR-001 registry golden + NFR-006 override-tier golden, non-circular).
- **SC-003**: ~450 LoC of dead duplicate removed; the compat golden is **157→156**; the 8 verdict-diff tests are *migrated* (not lost); dead-symbol / compat-surface / census-parity / ratchet gates green.
- **IC-01**: the pre-deletion audit proves the census branch is the sole live `scope_source=None` caller.

## 3. WP-B contract — internal hygiene (US3 / SC-005)

```bash
PYTHONPATH=$(pwd)/src python -m pytest tests/review/test_scope_source.py -q -p no:cacheprovider
```

- **SC-005**: `GateCoverageScopeSource` implements exactly one narrowing method (`scope_breakdown`, inheriting `file_to_scope` from `ScopeBreakdownMixin`); the two decisions are separate predicates backed by **different** signals — a synthetic source satisfies `exposes_scope_breakdown` XOR `empty_scope_is_coverage_gap` (proves the weld is gone, not renamed).

## 4. Whole-suite gates

```bash
PYTHONPATH=$(pwd)/src ruff check src/ && PYTHONPATH=$(pwd)/src python -m mypy src/specify_cli/review src/specify_cli/cli/commands/agent
PYTHONPATH=$(pwd):$(pwd)/src python scripts/generate_contextive_glossaries.py check   # if any prose edited
```

Zero ruff/mypy issues, ≥90% new-code coverage, complexity ≤15/function (NFR-002/003).
