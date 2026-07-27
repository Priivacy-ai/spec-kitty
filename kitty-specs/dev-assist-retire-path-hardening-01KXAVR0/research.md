# Phase 0 Research — Dev-Assist Retirement + Path-Validation Hardening

## R1 — Path-validation vectors are LIVE, not stale (resolves spec Assumption + FR-001 scope)

**Method**: ran `pytest tests/adversarial/test_path_validation.py -rxX` (read-only). The tests use imperative `pytest.xfail()` fired only when the validator *accepts* a malicious path, so XFAIL ⇒ live vuln, PASS ⇒ already-rejected.

**Result**: **17 XFAILED, 0 XPASSED**, 7 passed, 5 skipped. Every malicious-path class is live:
- Directory traversal (6 cases: `../kitty-specs/`, `../../../etc/passwd`, `./kitty-specs/`, `docs/../../kitty-specs/`, `docs/../../../`, `a/b/c/../../../../kitty-specs/`)
- Empty / whitespace / slash-normalizing-to-empty (6 cases incl. `/`, `///`, tabs, newline)
- Dot-only paths, symlink-into-kitty-specs, home (`~`), absolute, null-byte.

**Root cause** (`src/specify_cli/mission.py:618 validate_deliverables_path`): after `strip().rstrip("/")` it only checks (a) `startswith(kitty-specs)`, (b) literal `research`/`research/`, (c) `startswith("/")`. It never checks for `..` components, empty result, null bytes, `~`, dot-only, or resolves symlinks; the kitty-specs check is case-sensitive. So `../kitty-specs/` (no `kitty-specs` prefix), `""` (empty after strip), `~`, and a symlink all return `(True, "")`.

**Implication**: FR-001 is genuine security hardening (harden the validator to reject all classes: normalize + reject `..`/escape, empty, null byte, `~`, dot-only, absolute-after-normalize, and resolve symlinks to confirm containment), not merely de-xfailing stale tests. There is **no** verified-already-fixed vector; the spec's stale-xfail edge case does not occur here.

## R2 — Coverage-verification method for dev-assist retirement (FR-003/FR-004, NFR-002, C-002)

**Method** (validated on the runtime-bridge family): the standing family guard `tests/runtime/test_bridge_compat_surface.py::test_guard_b_identity_reexport_for_relocated_symbols` iterates `ALL_COMPAT_SYMBOLS` (50 symbols) and asserts every relocated symbol is a native delegate or identity re-export. A per-file candidate is a *true duplicate* only if its symbol set ⊆ `ALL_COMPAT_SYMBOLS`. Verified programmatically (load the test modules' symbol tuples, check subset membership):
- `test_bridge_cores.py:75` (5 syms), `test_bridge_retrospective.py:102` (9), `test_bridge_composition.py:89` (8) — **fully covered ⇒ RETIRE**.
- `test_bridge_io.py:104` (13 syms; 2 public — `build_operational_context_for_claim`, `get_or_start_run` — NOT in baseline) — **partial ⇒ NARROW** to `_PUBLIC_RELOCATED_NAMES`.
- `test_bridge_cores.py:67` (5 unpatched helpers, none in baseline) — **unique ⇒ KEEP**.
- Inert: `test_bridge_parity.py:1248 test_nfr006_timing_seed` — consumer deleted in #2558 ⇒ **RETIRE**.

The same membership check is the required gate for every sibling-family retirement (doctor/mission/merge): identify the standing guard, prove symbol-set (or set-equality) subsumption before deletion. This *is* the C-002 "coverage before deletion" enforcement.

## R3 — Compat-battery consolidation target shape (FR-005)

`test_bridge_compat_surface.py` (runtime-bridge) and `test_mission_shim_reexports.py::test_mission_reexports_required_symbol` (~50 symbols) are the proven consolidated shape: one per-family guard iterating the family's full relocated-symbol set. FR-005 replicates this for merge (8 fragmented `*_seam.py` batteries) and tasks (6 `*_seam.py` identity batteries), retiring the tautological byte-identical-literal pins (`test_constants_seam.py`) and the ~118 `assert_called` internal-call-graph interception proofs, while keeping the behavioural orchestration/ports tests and folding the unique private-symbol re-export coverage into the consolidated guard. Invariant: the consolidated symbol set must be a strict **superset** of the union of the retired batteries (NFR-002).

## R4 — Anti-vacuity enforcement (NFR-001, NFR-002, SC-004)

Every retirement/fix must be paired with a planted-regression proof: (a) after FR-001, reintroducing an accepted-malicious-path makes the strict suite fail; (b) after any retirement, a planted silent copy-instead-of-delegate re-export still trips the retained standing guard. This guards against retiring real coverage or shipping a fix the tests can't police.

## Open questions / deferred
- None blocking. The case-variant vector's exploitability depends on filesystem case-sensitivity; the fix normalizes case for the kitty-specs containment check regardless (defensive), so no clarification needed.
