# Post-TASKS Adversarial Review — Reviewer Renata (fakeable-DoD + red-first/anti-mutant lens)

**Mission:** gate-read-surface-completion-01KVW9B0 · **Branch:** feat/gate-read-surface-completion
**Reviewer:** reviewer-renata (DIRECTIVE_041 primary; 030/024/001/032)
**Scope:** anti-laziness pass over the 10 WP prompts. Read-only. Not committed.

Directives applied: **041** (tests-as-scaffold / reject-friction), **030** (gate green +
force real path), **024** (locality — out-of-map edit governance), **001** (no dead seam),
**032** (composed-`<slug>-<mid8>` fidelity).

Live spot-checks performed (line refs in the WPs are largely accurate):
- `resolve_planning_read_dir` @ `_read_path_resolver.py:1244`; `_ARTIFACT_TYPE_TO_KIND` @
  `mission.py:1106`, `_artifact_kind_for` raises-on-unmapped @ `:1120/:1124`. ✔ seam exists.
- `setup_plan` @ `mission.py:2044`; `_find_feature_directory` @ `:2203`; `spec_file =
  feature_dir / "spec.md"` @ `:2224`. ✔ residual confirmed.
- `record_analysis` @ `:1898`; placement_ref @ `:1951`; primary write anchor present. ✔
- helpers: `_resolve_mission_dir_name_primary_anchored` @ `:1269` (spec says 1288),
  `_primary_anchored_feature_dir` @ `:1327` (spec says 1308) — **drifted ~20 lines; symbols
  correct, line numbers stale** (low risk; implementers grep by symbol).
- `resolve_mid8` (branch_naming.py): **returns `""` iff `mission_id is None`** (or <8 chars).
- `_read_mission_mid8` @ `mission_type.py:633` reads `load_meta(meta_path.parent)` → ignores
  `full.json`/`bare.json` filenames. ✔ WP09 diagnosis verified (fixture drift, product correct).
- `_dependency_reachability` @ `ownership/validation.py:127`; `_COORD_RESIDUE_FILENAMES` @
  `artifacts.py:113`; `ANALYSIS_REPORT` COORD-partition @ `:35/109`. ✔

---

## Per-WP fakeability verdict

| WP | Fakeable? | The gap | The fix |
|----|-----------|---------|---------|
| WP01 chokepoint+retire | **PARTIAL** | T005 tests the **new helper** `_planning_read_dir`/`_primary_anchored_feature_dir`, not a real command. The DoD's red-first is "stash edits, assert SPEC→primary fails" — but the clean-`mission.py` helper *doesn't exist yet*, so "red" = ImportError, which captures nothing (MEMORY: ImportError-red ≠ red-first). Retirement DoD ("dead code removed / narrowed") is structurally checkable but no test forces the retired helper's `None`-on-no-handle + ambiguity-propagation through a caller. | Add an assertion that an EXISTING caller of the retired helper still returns the same dir (behavioral, not structural). For red-first, prove RED by **reverting the helper body to the pre-retirement primary-anchor call** (not by deleting the new helper). The cross-command behavioral net is deferred to WP10 — acceptable IF WP10 actually drives all 4 commands (see WP10). |
| WP02 setup-plan | **NO** (strong) | T006 drives the real `setup_plan` entry point, asserts RED=`SPEC_FILE_MISSING` pre-fix / GREEN post-fix, mandates composed `<slug>-<mid8>` primary dir + real ULID. Anti-mutant assertion present (T008). | — (model WP; the others should mirror it). One residual: ensure the assertion is on **observable command outcome** (phase advanced / not-blocked), not on an internal resolved-dir spy, else it drifts toward white-box. |
| WP03 accept gate | **NO** (strong) | T013 asserts BOTH planning→primary AND status→coord in ONE coord fixture, red-first via the accept entry point, composed dir, flattened regression, explicit mutant-revert comments. This is the anti-mutant gold standard. | — One risk the DoD under-pins: "resolve once via `kind=SPEC` and reuse" (T009) could mask a per-kind misclassification (e.g. quickstart). Require the test to read at least 2 distinct planning artifacts so a single-kind shortcut can't pass. |
| WP04 map-req + record-analysis collapse | **YES (record-analysis leg)** | T017 says prove the collapse "via a spy/mock on the resolver, or by asserting read dir == seam result". **Asserting `read_dir == resolve_planning_read_dir(...)` is tautological** (it pins the implementation to itself, green-before-and-after if the collapse is a pure refactor with no behavior change). The map-req leg (T014) is sound (real entry, RED=can't-find-WP-files). The record-analysis "double-resolution collapse" has **no observable behavior delta** to assert — it's a dedup, so a behavior test can't go red on the un-collapsed code. | Reframe T017: the collapse is **behavior-neutral**, so the honest proof is (a) the map-req behavioral red-first test (kept) + (b) a **count/structural assertion** that record-analysis no longer calls `primary_feature_dir_for_mission` for the read leg (AST, like WP06) — and label it as a dedup guard, NOT a red-first behavioral test. Do not let the spy-on-resolver tautology stand as the FR-009 proof. |
| WP05 allowlist + meta-sweep | **PARTIAL** | Allowlist leg (T021.1) is sound: real preflight, RED=meta.json-blocks pre-fix, **plus the G-5 invariant test (stale spec.md still blocks)** — kills the over-allowlist mutant. The **sweep leg (T021.2)** is a pure AST "zero inline `json.loads(...meta...)` remains" scan — structural, fakeable by definition (a refactor with no behavior change; green-after, and "red" only means the old string is present). | Allowlist leg: keep. Sweep leg: acceptable AS a structural ratchet IF it (a) asserts the **3 named modules** explicitly and (b) asserts `load_meta` is *called* (not just that the literal is absent — someone could inline a different reader). Frame it as a hygiene ratchet, not a behavioral guard. |
| WP06 literal-ban ratchet | **PARTIAL** | T024 anti-mutant proof is **"a docstring + a recorded manual proof"** OR an optional synthetic-AST unit test. A manual recorded proof is **not a gate** — it rots and can't be re-run. A ratchet whose non-vacuity rests on a logged manual mutation is exactly the friction-test smell DIRECTIVE_041 rejects. | **Make the synthetic-AST self-test mandatory, not "if feasible"**: feed the scanner a violating AST snippet (string), assert it flags; feed a clean snippet, assert it passes. That makes non-vacuity a runnable assertion, not a log entry. Also pin the **enumerated file set** in the test so adding a new gate command without scanning it fails. |
| WP07 next mid8 (Lane B) | **PARTIAL — FACTUAL ERROR** | T025.1 says model empty-mid8 via "a mission_id that **equals the slug** / cannot derive a mid8". **Wrong:** verified `resolve_mid8` returns `""` **iff `mission_id is None`** (or <8 chars) — a mission_id equal to the slug is ≥8 chars and yields `slug[:8]`, NOT empty. A fixture built on the WP's stated condition would NOT reproduce the bug → **false-green guard.** Red-proof-by-revert (T026) is correct in principle. | Correct T025.1: the empty-mid8 condition is **`mission_id absent/None`** (meta.json with no `mission_id`, or a pre-083 legacy mission). Mock `git worktree add` and assert the malformed `kitty/mission--lane-` branch is never passed. Without this fix the implementer reproduces nothing. |
| WP08 ownership overlap (Lane B) | **NO** (strong) | T027 positive (dep-ordered → pass) + negative control (independent pair → still errors) + revert-proof (T028). Negative control kills the "always allow" mutant. Drives `validate_ownership` with `_wp_dependencies` (real path), canonical factory, real ULID. | — (well-formed). Confirm the entry point is the **finalize-tasks --validate-only** CLI surface, not just `validate_ownership(...)` directly — the WP allows both; prefer the CLI to match NFR-002 "pre-existing entry point". |
| WP09 mid8 fixture re-pin (Lane B) | **NO** | T029/T030 re-pin to `meta.json` (canonical factory, real ULID), assert **actual mid8 values** per scenario (not just truthy), keep product untouched. Diagnosis verified live. T030.2 records the old-fixture-returns-empty sanity proof. | — (textbook failing-test remediation). Confirm "canonical factory" resolves to a real suite factory and not a re-handrolled dict (the WP says reuse — reviewer must check at impl). |
| WP10 closeout (reviewer) | **PARTIAL** | T031 is the real cross-command two-surface net (good). **But its non-vacuity depends on WP04's record-analysis leg actually having an observable PLANNING read to assert** — and record-analysis's planning-read collapse has no behavior delta (see WP04). If `record_analysis` reads no planning artifact behaviorally, T031's "for each gate command incl record_analysis assert planning==primary" is vacuous for that command. T033 arch-sweep + T034 verdicts are adjudication, not fakeable. | Scope T031's per-command assertion to commands with a **real, observable planning read** (setup_plan, accept, map_requirements). For record_analysis, assert the **status/allowlist** behavior instead, or drop it from the planning-read matrix. Otherwise WP10 ships a vacuous assertion for one of its four commands. |

---

## Check 1 — Red-first via PRE-EXISTING entry point (NFR-002)

- **Pass (real command):** WP02 (`setup_plan`), WP03 (accept gate), WP04 map-req leg
  (`map_requirements`), WP05 allowlist leg (`record_analysis` preflight), WP07 (`next`),
  WP08 (`finalize-tasks --validate-only`), WP10 T031 (all entry points).
- **Fail / weak:**
  - **WP01** tests the new helper, not a command — red is ImportError on clean code
    (captures nothing). Must prove RED by reverting the helper *body*.
  - **WP04 record-analysis leg** asserts `read_dir == seam_result` — tautological, no
    pre-existing entry-point behavior delta (it's a dedup).
  - **WP05 sweep leg** + **WP06** non-vacuity rest on AST/structural scans and (WP06) a
    *manual* mutation log — not a runnable red-first behavioral assertion.

## Check 2 — Composed-`<slug>-<mid8>` hazard (WP02 setup-plan, WP03 accept)

- **WP02:** ✔ T006.3 mandates `gate-read-surface-completion-01kvw9b0` + real ULID
  `01KVW9B0XFXPKTBE77QT3KRSW8`, explicitly flags the bare-slug false-green. Review guidance
  demands red-run evidence.
- **WP03:** ✔ T013.6 + risk + review guidance all require the composed dir; rejects bare-slug.
- Both honor the hazard correctly. (WP01/WP04/WP10 also carry the composed-dir requirement.)

## Check 3 — Anti-mutant: BOTH planning→primary AND status→coord (WP06/WP10)

- **WP10 T031** is the canonical two-mutant kill (planning==primary AND status==coord in one
  coord fixture, with explicit revert→RED comments). **WP03 T013** also does both in one
  fixture for the accept gate. Strong.
- **Caveat:** WP06 is the *structural* ratchet, not a behavioral two-surface guard — it does
  NOT assert primary/coord refs; it bans literals. That's correct for FR-010, but it means the
  behavioral anti-mutant burden falls entirely on WP03+WP10. Acceptable since WP10 depends on
  all WPs and asserts both partitions.
- **Vacuity risk:** WP10's record_analysis cell (see WP04/WP10 verdicts) — fix or drop.

## Check 4 — Lane B (WP07/08/09): revert product to prove RED

- **WP07:** ✔ T026 reverts the `runtime_bridge.py` guard (local, uncommitted) to prove RED —
  but the **fixture won't trigger it** under the WP's stated empty-mid8 condition (Check above).
  Revert-proof is correct; the scenario seed is wrong. Fix the condition or the revert proves
  nothing because the test is green-before-and-after for the wrong reason.
- **WP08:** ✔ T028 reverts `_dependency_reachability` exemption → RED; plus a negative control
  that doesn't depend on the revert. Robust (two independent non-vacuity proofs).
- **WP09:** N/A (test-remediation, not a product-guard lock) — but T030.2's "old fixture →
  empty for all three" IS the equivalent red-first sanity proof. ✔

---

## Highest-risk fakeable DoD

**WP04, record-analysis double-resolution collapse (T016/T017, FR-009).** It is the only
behavior-neutral "fix" dressed as a red-first behavioral WP. Its prescribed proof —
`assert read_dir == resolve_planning_read_dir(...)` or a spy on the resolver — is a
**tautology**: it pins the implementation to itself and is green-before-and-after a pure
dedup, so it captures nothing and cannot go RED on un-collapsed code. An implementer can mark
it done with a vacuous assertion that "proves" the collapse it just wrote. **Fix:** reframe the
record-analysis leg as an explicit **structural dedup guard** (AST: record_analysis read leg no
longer calls `primary_feature_dir_for_mission` / no manual coord-then-primary sequence), label
it NOT a red-first behavioral test, and let the map-requirements leg carry the only genuine
behavioral red-first in WP04. This cascades into **WP10 T031**, whose "assert planning==primary
for record_analysis" is correspondingly vacuous and must be scoped out or replaced with a
status/allowlist assertion.

**Runner-up: WP07's factually-wrong empty-mid8 condition** ("mission_id equals the slug") —
a guard built on it is a confident false-green that the revert-proof won't catch, because the
test never exercises the `mid8 == ""` branch.
