# Post-Tasks Adversarial Squad — Glossary Pack Doctrine Kind (Mission A)

Date: 2026-07-21 (after rebase onto upstream/main + `/spec-kitty.analyze`). Two lenses reviewed the
WORK-PACKAGE decomposition against the real code: anti-laziness (reviewer-renata) and
ownership/implementability (paula-patterns). Verdict entering: **task set ~85% ready — two HIGH
vacuity gaps + one unowned exact-set test would let a green suite ship a real defect.** All findings
folded below.

## Analysis findings (from `/spec-kitty.analyze`, verdict ready) — folded into spec.md

- **I1 (MEDIUM)** — spec.md FR-004 used pre-squad naming (`src/doctrine/glossaries/`,
  `DoctrineService.glossaries`). → **Fixed**: `glossary_packs` (plural==dir==accessor).
- **I2 (MEDIUM)** — spec.md FR-005 schema omitted `see_also`/`introduced_in_mission`. → **Fixed**:
  FR-005 now lists every seed field + `confidence` float.
- **U3 (LOW)** — spec.md FR-011 "graph fragment" too generic. → **Fixed**: notes generated +
  doctrine-root-located.

## Ownership lens — enum-addition footgun hunt

- **H1 (HIGH) — unowned hard exact-set break.** `tests/doctrine/test_artifact_kinds.py:18-31` asserts
  `{m.value for m in ArtifactKind} == {…11 literal values…}`; adding `GLOSSARY_PACK` turns it RED and
  no WP owned it. → **Fixed**: added to WP01 `owned_files`; T005 mandates updating the expected set.
- **Cleared (survive the addition, verified):** `test_kind_mapping_totality.py` (exempt partials),
  `test_nodekind_artifactkind.py` (subset), `test_kind_vocabulary.py` (no hard count),
  `test_surface_calibration.py`, `test_kind_cascade_exhaustive.py`,
  `test_charter_kind_tokens_derived_from_exclusion_set` (derive-both-sides). WP04's exact-set tests
  (`test_pack_context`, `test_pack_manager*`) correctly owned. Dependency chain serial, acyclic, **zero
  owned-file overlap**.
- **M1 (MEDIUM) — WP05 latent forced unowned edit.** `doctor doctrine --json` serialises via
  `_emit_doctrine_json` (`_profile_health_render.py`, passthrough of `report.to_dict()`). WP05 is
  in-scope only if glossary health is **nested** inside the report. → **Fixed**: T025 mandates nesting;
  `_profile_health_render.py` added to `owned_files` as a fallback.
- **M2 (MEDIUM) — WP05 stale path.** T025 body said `src/doctrine/_doctrine_health.py` (nonexistent).
  → **Fixed**: `src/specify_cli/cli/commands/_doctrine_health.py`.
- **L1 (LOW)** — `test_path_ref_resolver.py:173` `len(_PATH_KIND_PATTERNS)==7` breaks only if WP03 adds
  a `_PATH_KIND_PATTERNS` entry; the prompt already warns against it. Kept.

## Anti-laziness lens — WP vacuity/completeness

- **F1 (HIGH) — WP05 doctor 3-layer seam.** MODEL→COLLECT→RENDER; only MODEL was instructed, so JSON
  could stay silent. → **Fixed**: T025 now covers all three layers (COLLECT `_attach_pack_health` is
  the load-bearing one).
- **F2 (HIGH) — WP03 parity non-vacuity.** Extra fields on only 1/2/3 of 104 terms; a pack-side parity
  check misses a dropped sparse field. → **Fixed**: T016 mandates a **seed-driven** full-key assertion
  (every seed term × every populated seed key ⇒ present-and-equal in pack), explicitly covering the
  `see_also`/`introduced_in_mission` occurrences.
- **F3 (MEDIUM) — WP04 T022 RED-first not credible** (wiring precedes the guard extension →
  green-on-arrival). → **Fixed**: RED-first anchor named as the positive default-on assertion authored
  before T019 (or a witnessed revert-to-red).
- **F4 (MEDIUM) — C-003 seed-unchanged instruction-only.** → **Fixed**: T017 adds a hard seed
  file-integrity guard (content pin / diff-scope), so a lossy migration can't edit the seed to fake
  parity.
- **F5 (MEDIUM) — WP02 import-boundary false-negative risk** (`glossary` substring collides with
  `glossary_packs`). → **Fixed**: T011 mandates AST module-boundary matching + a proof-of-failure.
- **F6 (LOW) — SC-005 covered but untraced.** SC-005 (guards fail when broken) is delivered by the
  negative-control arms (T001 URN, T012 resolution, T022 default-on). Traceability noted here;
  requirement-ref frontmatter only retains FR/NFR/C, so it is tracked via the guards, not a ref.

## Net

All HIGH + MEDIUM findings folded into spec.md and the WP prompts; ownership re-validated. The task set
is now implement-ready. Two structural facts reaffirmed by the squad: the dependency chain is serial
with zero owned-file overlap, and the enum/NodeKind addition's only hard exact-set break
(`test_artifact_kinds.py`) is now owned by WP01.
