# Adversarial merge-review synthesis — Naming/Identity Routing Rider

**Date:** 2026-06-16. **Squad:** debugger-debbie (behavioral equivalence) · paula-patterns (anti-patterns)
· reviewer-renata (test integrity). All opus, profile-loaded, red-teaming the **merged** tree
(`feat/naming-rider-3-2-1`, HEAD `2a112b318`). Inputs: `debbie-behavioral.md`, `paula-antipatterns.md`,
`renata-test-integrity.md`.

## Headline: the mission is SOUND as merged
- **Committed tree CLEAN** (paula): 0 unaccounted `mid8` slices (7 baseline = 5 seam homes + 2 doctor
  tolerances); no silent-empty / dead-code / synthetic-fixture; `resolution.py:171` read-path byte-equal.
- **Tests CONSTRAIN** (renata): mutation-tested every load-bearing claim ("revert the impl, does it still
  pass?") — all bite. Ratchet **non-defeatable + correctly accounted** (independently re-derived the
  baseline; negative control fires). #1888 verify-and-close genuine (`validation.py` byte-unchanged).
- **Operator's slug-tail hypothesis FALSIFIED** (debbie): when `mission_id` is present (≥8), `resolve_mid8`
  returns `mission_id[:8]` and never consults the slug tail — divergent/matching/absent tails all
  byte-equal. 12/16 sites confirmed equivalent.
- **Working-tree contamination** during the run (scanner.py revert, context.py `if False` guard) was
  **sibling red-team experiments** in the shared checkout, not mission defects — reverted; HEAD always
  correct. *(Lesson: parallel red-teamers in one checkout cross-contaminate; the committed-tree analysis
  is authoritative.)*

## Two genuine findings

### A — short-`mission_id` byte-parity divergence (debbie) — DECISION REQUIRED
4 sites where the **old** code did an **unguarded** `mission_id[:8]` and the new route declines to `""`
for a **short (1–7 char) truthy** `mission_id`:

| Site | Severity | Old → New | Impact |
|------|----------|-----------|--------|
| `status/aggregate.py:256` | **MEDIUM** | short → `""` | `MissionStatus.save()` flips *commit* → **raise `MissionMetadataUnavailable`** (control-flow) — reproduced |
| `context/mission_resolver.py:163` | LOW | short → `""` | display-only (resolution matches on `mission_id`, not `mid8`) |
| `dashboard/scanner.py:445` | LOW | short → `None` | registry `mid8` field |
| `doctrine_synthesizer/apply.py:746,832` | LOW | short → `""` | retrospective event-payload field |

**Reachability:** short `mission_id` is **malformed** — real ULIDs are 26 chars, no mint path produces
<8, no read-side length validation — so reachable only from hand-edited/corrupt/test-fixture meta, **not
the golden production path**. (Such literals do exist in the test corpus.)

**The fork (NFR-001 scope):**
- **(a) Preserve exact parity** — add `or mission_id[:8]` absorbers at the 4 sites (the doctor.py pattern).
  *Cost:* reintroduces 4 banned `[:8]` slices → +4 ratchet allow-list entries (allow-list GROWS), and
  keeps the *truncate-a-corrupt-id-and-proceed* behavior.
- **(b) Declare an intended carve-out (RECOMMENDED)** — malformed short id → decline/`""`/`None`/fail-loud
  is the *better* behavior (consistent with emit-don't-guess + fail-closed), and keeps the ratchet clean
  (no slice reintroduction). *Do:* add short-`mission_id` regression tests pinning the new behavior at the
  4 sites; document the carve-out in spec NFR-001 ("byte-parity for well-formed ids; malformed short ids
  decline/fail-loud by design"). The MEDIUM `aggregate.save()` raise becomes intended fail-loud-on-corruption.

### B — stale name-compose allow-list (renata) — will FIX (clean hygiene)
The *name-compose* ratchet's `_ALLOWED_SITES` still lists 3 entries WP05 already routed
(`mission_creation.py:321`, `worktree.py:367/370`) — its hygiene check only verifies `lineno <= line_count`,
not that the line is still an offender, opening a **3-line false-negative window**. Fix: drop the 3 stale
entries + add a name-compose baseline cross-check (mirroring the short-id ratchet's baseline). Low-risk,
clearly correct.

## Net
Mission is releasable. **A** is a malformed-input-only NFR-001 fork (operator's call; recommend the
carve-out). **B** is a clean ratchet-hygiene fix to apply regardless. Neither is a golden-path defect.
