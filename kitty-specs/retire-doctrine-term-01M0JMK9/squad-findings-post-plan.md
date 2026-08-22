# Adversarial Squad Findings — Post-Plan Review

**Mission**: retire-doctrine-term-01M0JMK9
**Point-cut**: post-plan (plan review before `/spec-kitty.tasks`)
**Question**: *Is this plan sound, complete, and implementable — what must be fixed before we task?*
**Date**: 2026-08-21

## Squad & method

| Lens | Profile | Load status |
|------|---------|-------------|
| Structure / seams / topology | `architect-alphonso` | activated, loaded via CLI |
| Anti-laziness / contract-vs-implementation | `reviewer-renata` | activated, loaded via CLI |
| Doctrine integrity / ADR conventions | `doctrine-daphne` | **degraded** — not activated in this project's charter; inspected via `spec-kitty agent profile show doctrine-daphne --all` (no overlays/lineage applied) |
| Live evidence / coverage | `debugger-debbie` | activated, loaded via CLI |

All delegates read-only. **Harness note**: this harness (pi) has no subagent dispatch tool, so the four
lenses ran as sequential structured passes with profiles loaded via CLI — not parallel subagents.
Each pass is grounded in live repo evidence re-verified 2026-08-21 against the committed plan
(commit `b06d09b7`, branch `feat/retire-doctrine-term`).

---

## Lens 1 — Architect Alphonso (structure / seams / topology)

Applied: profile initialization (architect; design/evaluate/decide/model/specify; no implementation
code); canonical verbs applied to the IC chain, artifact interlocks, and stack shape.

- **[MEDIUM — FOLDED]** `kitty-ops/` taxonomy gap: the surface taxonomy (S1–S9, X1–X3) did not cover
  `kitty-ops/` — the Op event journals (15 tracked `.jsonl` files contain "doctrine" as quoted event
  content, verified live). Without a classification rule those hits would be *unclassified* and fail
  SC-002's "0 unclassified" pass condition. **Fold**: X2 (`legacy-marked-historical`) now explicitly
  includes `kitty-ops/` Op event journals as immutable operational snapshots (data-model.md §1).
- **[MEDIUM — FOLDED]** M1 `change_mode` ambiguity: the schema said "M1 mixed (bulk-edit glossary/
  bundle + code guard arming)", but a mission carries one `change_mode` — leaving "mixed" unresolved
  would make M1's spec require a new decision, violating FR-010 (M1 must be spec-ready with 0 new
  decisions). **Fold**: M1 is `change_mode: bulk_edit`; its occurrence map covers the glossary +
  bundle renames; the guard-arming WP is additive code, not a rename occurrence (data-model.md §3 +
  contracts/stacked-plan-schema.md).
- **[PASS]** IC chain covers every FR: FR-001..FR-005/FR-011 → IC-01; FR-006/FR-007/NFR-001 → IC-02;
  FR-008/C-004 → IC-03; FR-009/FR-010/NFR-003 → IC-04; SC-001..SC-004 → IC-05 + quickstart.md.
  Artifact interlocks are mechanical (contracts/ schemas pin the formats; stable OC-## IDs are the
  interface between inventory → stacked plan → waves). Atomic authority flip is structurally sound:
  the C1 conflict window is closed by construction (I0 → I1 is a single PR boundary).

## Lens 2 — Reviewer Renata (anti-laziness / contract-vs-implementation)

Applied: profile initialization (reviewer; quality gate, not implementer); every plan claim checked
for verifiability and fake-ability.

- **[MEDIUM — FOLDED]** Evidence count errors (two): plan artifacts said "56 skill directories" at
  `src/doctrine/skills/` — live count is **55** skill directories (+ README.md; the earlier tally
  counted the README). And "AGENTS.md (9 doctrine lines)" — live count is **10** case-insensitive.
  Both are evidence claims in a plan whose whole value is evidence; wrong numbers would propagate
  into the inventory's baseline. **Fold**: corrected in research.md (R7, R8/C3) and data-model.md
  (S4, S9).
- **[PASS]** Quickstart runbook is executable: check 4's audit command was actually run —
  `git ls-files | xargs git grep -ic 'doctrine'` completes in ~10 s, total 54,003 hits (no ARG_MAX
  issue at this repo size). Checks 1–3, 5–7 are all mechanically checkable with named pass
  conditions; none is fake-able by assertion alone (SC-001 requires a named independent reviewer).
- **[PASS]** Exit-gate honesty: `setup-plan` reports `plan_substantive: true` on real Technical
  Context values (Language/Version + all peer fields populated or explicitly N/A with reason), not
  placeholders. Supply-chain section is documented-N/A (no dependency changes), not silent.

## Lens 3 — Doctrine Daphne (doctrine integrity / ADR conventions) — degraded mode

Applied: profile inspected via `--all` (no overlays/lineage); ADR conventions, terminology
consistency, and DIRECTIVE_048 checked against live repo state.

- **[PASS]** ADR conventions: template exists (`docs/architecture/adr-template.md`); dated naming
  `2026-08-21-N-...` is next after live latest `2026-08-20-1`; registration via
  `python -m scripts.docs.freshen_adr_inventory` updates both the era index row and the
  page-inventory lockfile (the `docs-freshness` gate enforces both); the `Superseded` status
  convention is frontmatter-based (5 live examples). The plan's amendment mechanics for
  `2026-07-15-1` (status frontmatter only, body untouched) match the C-003 carve-out exactly.
- **[PASS]** Terminology consistency: all plan artifacts use "charter bundle" (not the retired
  "charter.md file" sense) after the post-spec fold; the reasons-canvas stale references were
  updated in the same pass. DIRECTIVE_048 respected — this mission's artifacts live in
  `kitty-specs/` (guard-excluded) and quote the retired term only as subject matter.
- **[PASS]** Bundle authority: M1's update path (edit `charter.yaml`, regenerate — never hand-edit
  `charter.md`) is consistent with ADR `2026-07-18-1`; the Terminology Canon line content is fixed
  by the ADR (contracts/adr-content-contract.md item 8), so M1 executes rather than re-decides.

## Lens 4 — Debugger Debbie (live evidence / coverage)

Applied: profile initialization (investigator; falsifier discipline); every factual claim in the
plan re-verified against the repo at base 2026-08-21.

- **[MEDIUM — FOLDED]** Same two count errors as Lens 2 (56→55 skill dirs; AGENTS.md 9→10 lines) —
  independently re-derived: `ls -d src/doctrine/skills/*/ | wc -l` = 55;
  `grep -ic doctrine AGENTS.md` = 10. Folds applied (see Lens 2).
- **[PASS]** File-count evidence verified: `src` 429, `tests` 731, `docs` 430, `packs` 103,
  `.kittify` 51 files contain the term case-insensitively (all match plan.md Technical Context).
- **[PASS]** CI consumer claim verified: `.github/workflows/ci-quality.yml:4055` is exactly
  `/tmp/clean-venv/bin/spec-kitty doctor doctrine --json > /tmp/doctor.json || true` (with the
  JSON assertion following) — the same-wave-update requirement is load-bearing, not hypothetical.
- **[PASS]** Glossary + bundle evidence verified: `docs/context/doctrine.md` = 685 lines /
  124 doctrine lines; `.kittify/charter/` counts = charter.yaml 53, charter.md 13, graph.yml 2,
  interview/answers.yaml 9 (all match).
- **[PASS]** Canonical-source claims verified: `src/doctrine/directives/` is Python code
  (models.py, repository.py) while `packs/built-in/directives/` holds the YAML artifacts;
  `src/doctrine/hatch_build.py` ships `packs/built-in` into site-packages — so the plan's
  "packs/ = canonical YAML source, src/doctrine/<kind>/ = code" split is correct.

---

## Verdict

**Plan is task-ready.** 4 findings, all folded (2 MEDIUM factual corrections, 1 MEDIUM taxonomy
gap, 1 MEDIUM change_mode ambiguity); no HIGH findings; no unresolved items. The plan's load-bearing
claims (guard mechanics, bundle topology, CI consumer, canonical sources, audit command) are all
verified against live evidence.

**Folded changes**: research.md (R7, R8/C3 counts), data-model.md (S4/S9 counts, X2 + kitty-ops/,
M1 change_mode), contracts/stacked-plan-schema.md (M1 change_mode).
