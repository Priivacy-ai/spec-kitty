# Design Decisions

> Capture the rationale that would otherwise evaporate.

**Prompting questions**
- What decision was made?
- What alternatives were considered?
- What was the rationale — why this option over the others?

---

## Entries

<!-- YYYY-MM-DD — Decision: [what]. Alternatives: [what else]. Rationale: [why this one]. -->

- 2026-07-19 — **Decision:** bundle all three items, including the deep #2373 no-op-stability fix
  (decision `01KXW0PN2KDS5M5GR9CMDPWV5F`). **Alternatives:** (a) dead-code + a render-cleanliness
  guard, closing #2373 as already-remediated-by-#2773; (c) pure dead-code, defer #2373 entirely.
  **Rationale:** operator chose to fix the *real* residual churn (preflight/freshness) now rather
  than only guard the already-fixed render path — a genuine reliability win over a cosmetic close.

- 2026-07-19 — **Decision:** delete `charter.generator` now despite it being a deliberately-retained
  #2773 WP03 wrapper. **Alternatives:** keep it as a documented shim. **Rationale:** research
  confirmed zero live callers AND cleared the landmine — `charter generate` emits `charter.yaml` via
  `write_compiled_charter`, `charter.md` is hand-authored, nothing bootstraps an initial `charter.md`
  from it, so the "initial-draft builder" role it once held no longer exists.

- 2026-07-19 — **Decision:** shrink the arch dead-code baselines DOWNWARD and remove all three
  `charter.extractor` allowlist entries in the same change. **Alternatives:** leave the allowlists,
  green-wash upward. **Rationale:** removing the module without deleting the allowlist entries turns
  the gates stale-red (`test_no_dead_modules`) and dangling-red (`test_no_dead_symbols`); the ratchet
  only permits downward moves, and green-washing upward violates C-003.

- 2026-07-19 — **Decision:** keep the 4 `write_compiled_charter` symlink-guard tests in
  `test_generator.py`; only remove the generator import line + the 4 generator-API tests.
  **Alternatives:** delete the whole file with the module. **Rationale:** those 4 tests cover the
  LIVE compiler, not the dead generator — deleting them to "go green" would drop real coverage (C-003:
  never delete a test to go green).

- 2026-07-19 — **Decision:** confine doctrine regeneration to explicit write commands / genuine-change
  gating rather than making `.kittify/doctrine/**` on-demand-only. **Alternatives:** stop materializing
  the artifacts and load on demand. **Rationale:** many readers load doctrine from disk
  (drg loader, `_drg_helpers`, freshness computer, preflight, lint); on-demand-only would touch every
  reader and balloon the blast radius (C-005). Fix the freshness-misfire instead.

- 2026-07-19 — **Decision:** collapse WP04 from a behavioral freshness fix to a GUARD-ONLY WP.
  **Alternatives:** verify-then-collapse (burn a cycle proving the negative); drop WP04 entirely.
  **Rationale:** the post-tasks squad (debugger-debbie) refuted the premise with high confidence —
  #2373's residual churn is already dead at HEAD (#2732 content-hash freshness + #1912 promote guards
  + #2773), the red-first repro cannot reproduce (built_in_only + doctrine-masked checkout), and the
  proposed signal re-homing would *cause* over-suppression (INV-2 violation). A guard pins the
  already-correct behavior without theater; #2373 closes as verified-already-fixed.

- 2026-07-19 — **Decision:** WP02 owns a FOURTH gate surface (chokepoint `_CARVE_OUTS`).
  **Alternatives:** discover it as a red at implement time. **Rationale:** paula-patterns found
  `test_chokepoint_coverage.py:61` asserts `src/charter/extractor.py` exists; deleting the module
  without dropping the carve-out fails a gate under `tests/charter/` (outside the arch-gate dir the
  WP originally verified) — folding it into WP02's atomic edit prevents a guaranteed red.
