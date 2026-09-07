# Contract — P1 dead-code census oracle (E3) + CI-integrity oracle (E5)

## P1 census oracle
- **Input:** live `src/**` + retirement gates + importer graph → per-surface `{status: dead|live, evidence}`.
- **Authorizes:** (a) a base-red (#3284) drop iff its subject is census-`dead`; (b) coverage-denominator exclusion of census-`dead` surfaces.
- **Non-vacuity (DIR-043):** MUST fail if it evaluates an empty set. A **self-mutation negative test** plants a dead-code shard / retired-import and asserts the census flags it and the exclusion gate fires.
- **Bidirectional guardrail (post-plan squad — the loophole is two-sided):**
  - *False-negative (rubber-stamp):* a base-red (#3284) may be dropped as "dead" ONLY with **independent evidence** (retirement-gate ref / ADR / zero-importer-AND-not-dynamically-reached), never self-certification; each of the 23 drops is individually evidenced and reviewer-verifiable.
  - *False-positive (mis-mark live as dead):* a **"known-live is never dead"** guard protects surfaces reachable only dynamically (entry points, plugin/registry dispatch, `getattr`/import-string, CLI wiring) whose static importer-count is 0 — these are NOT droppable; a positive-side negative test plants a live-but-importer-0 surface and asserts the census refuses to mark it `dead`.
- **Boundary:** census-`dead` behavioral tests are excluded from CI; the enforcement allowlists (`test_no_dead_symbols`/`test_no_dead_modules`/`test_no_retired_subsystems`) that *quote* dead surfaces are **always-on** and out of scope of exclusion. A committed membership (E4) prevents relabeling either way.

## CI-integrity (collection-completeness) oracle
- **Input:** the **real on-disk** reinstated workflow YAML (not a literal snippet).
- **Assertion:** no test is selected by zero gates; the enumerated must-run gates are all wired; the two-authority routing model is internally consistent.
- **Non-vacuity:** carries a floor + a **planted-orphan negative test** (a test wired to no group reds the oracle). Fixes the zero-producer/inert-slot bare-name false-pass (#2967).
- **Runtime vs static:** the oracle proves *wiring*; each gate's *runtime* execution is evidenced by its own job result (SC-004), never inferred from the static oracle.

## Gate-selection authority (#2476)
- A single importable function is the one authority for "which tests/gates a change selects", reused by both CI routing and local pre-PR parity — not a second parser.
