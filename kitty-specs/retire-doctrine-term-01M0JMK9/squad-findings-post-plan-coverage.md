# Adversarial Squad Findings — Post-Plan Spec-Coverage Review

**Mission**: retire-doctrine-term-01M0JMK9
**Point-cut**: post-plan (second squad; first ran `squad-findings-post-plan.md` with the soundness question)
**Question**: *Does plan.md fully answer spec.md's "what?" — i.e., does every FR, NFR, constraint, edge case, and success criterion in spec.md have a concrete "how" (mechanism, artifact, procedure) in plan.md and its Phase-1 artifacts? Where are the gaps?*
**Date**: 2026-08-21

## Squad & method

| Lens | Profile | Load status |
|------|---------|-------------|
| Scope / sequencing / traceability | `planner-priti` | activated, loaded via CLI |
| Anti-laziness / contract-vs-implementation | `reviewer-renata` | activated, loaded via CLI |
| Structure / seams / artifact interlocks | `architect-alphonso` | activated, loaded via CLI |
| Live evidence / falsification | `debugger-debbie` | activated, loaded via CLI |

All delegates read-only. Charter context `--action plan` (DIR-001..DIR-013, software-dev-default) loaded for all passes.
**Harness note**: this harness (pi) has no subagent dispatch tool, so the four lenses ran as sequential
structured passes with profiles loaded via CLI — not parallel subagents. Evidence re-verified live at
HEAD `58f448046` (branch `feat/retire-doctrine-term`) on 2026-08-21.

**Method**: Lens 1 built the full spec→plan traceability matrix (all 4 user stories + acceptance
scenarios, 9 edge cases, FR-001..FR-011, NFR-001..NFR-003, C-001..C-005, SC-001..SC-004, 6 assumptions).
Lens 2 checked each "how" for fake-ability (pointer-that-does-not-land = not an answer). Lens 3 checked
artifact interlocks. Lens 4 re-derived every load-bearing factual claim against the repo and cross-checked
plan positions against the resolved decision records in `decisions/`.

---

## Lens 1 — Planner Priti (scope / sequencing / traceability)

Applied: profile initialization (planner; decomposition, sequencing, dependency mapping; no
implementation); canonical verbs applied to the spec→plan traceability matrix.

**Traceability result**: 10 of 11 FRs, all 3 NFRs, all 5 constraints, all 4 success criteria, and 7 of
9 edge cases have a concrete "how" in plan.md + Phase-1 artifacts (contracts/, data-model.md,
research.md, quickstart.md). The two gaps below.

- **[HIGH — FOLDED] Operator-typed identifier classification contradicts a resolved decision.**
  Spec edge case 8 requires the ADR to classify operator-typed identifiers (profile IDs, directive
  IDs, skill names) explicitly — "in scope with aliases, or out of scope as a named exception."
  `contracts/adr-content-contract.md` item 4 and plan.md IC-01(b) both state: *plan position: out of
  scope as a named exception* — for the whole class **including skill names**. But resolved decision
  moment `specify.compatibility.alias-policy` (`decisions/DM-01M0JN29JGRA2GVEJJ89JZH3R2.md`) asks
  explicitly about "executable user-facing surfaces (**CLI command/flag names, skill names**)" and the
  operator answered: deprecate in 3.x (hidden aliases + warnings), zero user-visible doctrine by 4.0.
  The operator-approved stack shape (`DM-01M0JWDEMKXQ5CMAE9PFEK8GF9`) likewise fixes "M4 =
  skills/agent artifacts **with legacy alias skills**." So the plan's ADR checklist position
  (skill names never renamed) contradicts both a resolved operator decision and the approved M4 shape
  (skill names renamed with aliases, removed at 4.0). Consequence: the IC-01 implementer following
  the checklist would author an ADR — the program's canonical authority — that forbids M4's core work;
  M4 then depends on an undecided item (NFR-003: "0 missions depend on an undecided item").
  **Fold**: ADR contract item 4 + plan.md IC-01(b) now state the split explicitly — skill names in
  scope with aliases (per the resolved decision + approved M4 shape); profile IDs and directive IDs
  out of scope as a named exception (stable DRG node identifiers, analogous to `mission_id`;
  surrounding prose renamed). No new decision introduced — the fold aligns the plan with what the
  operator already decided. Flagged for operator confirmation at PR review.
- **[MEDIUM — FOLDED] Cross-repo deferral has no named home.** Spec assumption 5: sibling-repo
  user-facing surfaces (e.g. the spec-kitty-saas dashboard) are "deferred with rationale, not
  silently dropped." No plan artifact names where that deferral is recorded: the inventory schema's
  audit covers `git ls-files` (this repo only), so cross-repo surfaces never appear as rows, and
  neither the inventory schema nor the stacked-plan schema has a slot for them. Silent drop is
  exactly what the spec forbids. **Fold**: `contracts/inventory-schema.md` gains Section 5
  (out-of-repo surfaces — deferred with rationale, outside the audit arithmetic); data-model.md §4
  updated to match.

**Concession**: this lens does not judge whether the "how" mechanisms are technically sound (Lens 3/4
territory) — only that every "what" has an answer with a named home.

## Lens 2 — Reviewer Renata (anti-laziness / contract-vs-implementation)

Applied: profile initialization (reviewer; quality gate, not implementer); every plan "how" checked
for fake-ability — a pointer that does not land in a named artifact is not an answer.

- **[MEDIUM — FOLDED] Spec edge case 1's ADR-side requirement is missing from the checklist.**
  Edge case 1: "The ADR **must disambiguate** 'charter' the term from `src/charter/` the code
  surface, and the inventory must not conflate occurrences of that word in that package's
  user-facing strings with the doctrine layer." The inventory half lands (data-model S7 captures the
  `src/charter/context_renderers/bootstrap_text.py` "Action Doctrine" heading; X1 + OC-I3 keep
  identifiers out). The ADR half does **not**: `contracts/adr-content-contract.md` items 1–9 contain
  no disambiguation requirement, and quickstart check 3's five-item self-sufficiency test never asks
  for it. The content contract is IC-01's checklist ("the ADR must state, each self-contained") — an
  absent item is an un-answered "what." **Fold**: ADR contract item 2 now requires the
  disambiguation; quickstart check 3 gains item 6 ("charter" the term ≠ `src/charter/` the code
  surface) and its pass condition moves to all six.
- **[LOW — FOLDED] Edge case 7's "old→new map" is not named.** The spec says harnesses that route on
  skill names "need the old→new map." The plan's mechanism (legacy alias skills, M4/I4) is real and
  the alias skills are the executable form of the map — but no artifact records the mapping itself,
  so a harness integrator has to reverse-engineer it from 7 alias skills. **Fold**: M4's entry
  (plan.md stacked table, `contracts/stacked-plan-schema.md`, data-model I4) now states the old→new
  map is recorded in M4's artifacts.
- **[PASS]** Every other "how" lands: FR-011's four sub-parts are all pinned in ADR contract item 7
  (Charter Bundle entry; disambiguation from Doctrine Pack + other bundle senses; "bundle" generic
  fix; Doctrine Domain replacement) — M1 executes rather than re-decides. NFR-001's audit is a
  mechanical procedure with an exact command and an arithmetic pass condition (not "reviewer says it
  looks complete"). C-004's per-surface verification is one named mechanism per out-of-root class
  (data-model §1: S4/S5/S6/S8/S9), checked by quickstart check 7. R9's bulk-edit gate interaction
  (`--acknowledge-not-bulk-edit` with rationale) is concrete, not hand-waved.
- **[PASS]** No fakeable assertions found in this pass: every PASS claim above was re-derived live
  (see Lens 4). The one count error found is factual, not structural.

**Concession**: anti-laziness on the *downstream* missions' DoDs is out of scope here — they don't
exist yet; the stacked-plan schema's `open_items` field is the control, and M1's zero-open-items
requirement (SM-I2) is real.

## Lens 3 — Architect Alphonso (structure / seams / artifact interlocks)

Applied: profile initialization (architect; design/evaluate/decide/model/specify; no implementation
code); canonical verbs applied to the IC chain and artifact interlocks.

- **[HIGH — FOLDED, convergent with Lens 1] No interlock between ADR contract item 4 and M4's
  `retires` list.** Structurally, the plan has two artifacts that must agree on operator-typed
  identifier treatment — `contracts/adr-content-contract.md` (what the ADR records) and
  `contracts/stacked-plan-schema.md` M4 + data-model I4 (what M4 does) — and nothing cross-checks
  them. The fold (explicit split in item 4, citing the resolved decision) makes the agreement
  checkable: M4's `retires` list (skill-name classes) must match the ADR's in-scope-with-aliases
  classification. The stacked-plan schema's `open_items` field remains the standing control for any
  future drift.
- **[PASS]** IC chain is complete and correctly sequenced: IC-01 (ADR) → IC-02 (inventory, cites
  ADR scope decisions) → IC-03 (methodology, cites inventory evidence) → IC-04 (stacked plan,
  follows methodology ordering) → IC-05 (verification). Every FR/NFR/C/SC maps to at least one IC
  (matrix in Lens 1); no orphan requirement.
- **[PASS]** The atomic authority flip is structurally sound: I0→I1 is a single PR boundary, so the
  C1 conflict window (guard forbids old word before replacement is canonical) is closed by
  construction, not by discipline. INV-I2 (no conflict window) is the invariant that makes M1
  atomic, and it is stated.
- **[PASS]** Stable OC-## IDs are the correct interface between inventory → stacked plan → waves
  (OC-I2: immutable, splittable, never reassigned) — downstream missions cite IDs, not
  descriptions, so prose drift cannot break the chain.

**Concession**: this lens does not re-verify factual claims (Lens 4) and does not judge whether the
stacked shape is optimal — it is operator-approved (decision `01M0JWDEMKXQ5CMAE9PFEK8GF9`) and
granularity is fixed.

## Lens 4 — Debugger Debbie (live evidence / falsification)

Applied: profile initialization (investigator; falsifier discipline); every load-bearing factual
claim in the plan re-derived against the repo at HEAD `58f448046`.

- **[LOW — FOLDED] ADR count error (third across two squad runs).** research.md R10: "10 ADRs in
  `docs/adr/3.x/` carry 'doctrine' in their titles." Live: **11** (`ls docs/adr/3.x/ | grep -ci
  doctrine` = 11), of which 10 are retain-as-legacy + 1 is the amended ADR (`2026-07-15-1`).
  data-model.md X2's phrasing ("10 … except the amended one") is correct, so R10 and X2 also
  disagree with each other. **Fold**: R10 corrected to "11 … of which 10 retain-as-legacy + the
  amended one." Pattern note: this is the third evidence-count error across two squad runs (56→55
  skill dirs, 9→10 AGENTS.md lines, now 10→11 ADRs) — evidence counts in plan artifacts are not
  being mechanically re-derived at commit time. Not load-bearing (the inventory's mechanical audit
  is the authority), but in a mission whose value is evidence, wrong numbers propagate.
- **[PASS]** 7 `spk-doctrine-*` skill dirs at `src/doctrine/skills/` (data-model S4) — re-derived:
  bulk-edit, charter, glossary, profile-load, semantic-compression, show-me, spdd-reasons.
- **[PASS]** "Action Doctrine" heading lives in `src/charter/context_renderers/bootstrap_text.py`
  (S7) — re-derived at lines 4/85/100/121/133.
- **[PASS]** Guard state (R2): `_FORBIDDEN_TERMS = ("cere"+"mony", "status"-"writing")` — "doctrine"
  is NOT currently forbidden; `_SCAN_ROOTS = ("src", "tests", "docs")`. The plan's claim that
  arming is new machinery (no per-file exemption mechanism for active surfaces) holds.
- **[PASS]** Glossary state (R6): `docs/context/doctrine.md` has "Doctrine Domain" (line 17) and
  "Doctrine Pack" (line 297); **no "Charter Bundle" heading exists** — FR-011's gap is real.
- **[PASS]** CI consumer (S8/R5): `.github/workflows/ci-quality.yml:4055` runs
  `/tmp/clean-venv/bin/spec-kitty doctor doctrine --json > /tmp/doctor.json || true` — the
  same-wave-update requirement is load-bearing.
- **[PASS]** ADR conventions (R1): latest 3.x ADR is `2026-08-20-1-cascade-kind-complete-relation-set.md`
  (plan's "N = next free number" claim holds); exactly 5 `status: Superseded` ADRs (frontmatter
  convention confirmed).
- **[PASS — new check]** Decision records: `DM-01M0JN29JGRA2GVEJJ89JZH3R2` (alias policy) and
  `DM-01M0JWDEMKXQ5CMAE9PFEK8GF9` (stack shape) both `resolved`, operator-approved 2026-08-21 —
  the basis for Lens 1's HIGH finding.

**Concession**: file-count evidence (429/731/430/103/51) was verified by the first squad at
`b06d09b7`; the delta to `58f448046` is mission artifacts only (kitty-specs/), which cannot change
those counts. Not re-derived this pass — stated as inherited, not re-proven.

---

## Synthesis & verdict

**Convergence**: Lenses 1 and 3 independently flagged the operator-typed identifier contradiction
(from scope/traceability and from interlock angles respectively) — convergent evidence, not a single
opinion. No divergence requiring second-opinion adjudication; no irreconcilable positions.

**Answer to the question**: The plan **substantially but not fully** answers spec.md's "what?".
Every FR, NFR, constraint, and success criterion has a concrete, live-verified "how" — except:

| # | Sev | Gap (spec "what" → missing/contradicted "how") | Status |
|---|-----|-----------------------------------------------|--------|
| 1 | HIGH | Edge case 8 / FR-004: ADR checklist position (skill names out of scope) contradicts resolved alias-policy decision + approved M4 shape | FOLDED (split stated; operator to confirm at PR review) |
| 2 | MEDIUM | Edge case 1: ADR-side `src/charter/` disambiguation absent from content contract + self-sufficiency test | FOLDED (contract item 2 + quickstart check 3 item 6) |
| 3 | MEDIUM | Assumption 5: cross-repo deferral "with rationale, not silently dropped" had no named home | FOLDED (inventory schema Section 5) |
| 4 | LOW | Edge case 7: old→new skill map not named as an artifact | FOLDED (M4 entries) |
| 5 | LOW | R10 ADR count 10 → live 11 (third count error across two runs) | FOLDED (R10 corrected) |

**Verdict**: **Plan is task-ready after the folds.** No finding blocks M1's spec-readiness
(FR-010/SC-004 hold — M1 is untouched by finding 1). Finding 1 must be confirmed by the operator at
PR review because it re-states a resolved decision rather than making a new one. The recurring
count-error pattern (finding 5) suggests the tasks phase should include a mechanical re-derivation
of every evidence number in the inventory WP (the audit already does this by design — NFR-001).

**Folded changes**: `contracts/adr-content-contract.md` (item 2 + item 4),
`contracts/inventory-schema.md` (Section 5), `contracts/stacked-plan-schema.md` (M4 row),
plan.md (IC-01(b) + M4 stacked-table row), data-model.md (§4 structure, I4), quickstart.md
(check 3 item 6 + pass condition), research.md (R10 count).
