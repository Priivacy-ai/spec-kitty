# Contract: Placement Layering (what the architecture page must state)

Binding contract for **FR-018 / FR-020** (IC-09). The page is
`docs/architecture/artifact-placement-seam.md`. This contract fixes *what must be true of
the page*, not its prose.

## C1 — Required content

The page MUST contain, each as a named section:

1. **What "routing" means here** — the placement sense: mapping an artifact **kind** plus
   the mission's **topology** to a `TopologySurface`. It MUST point at the glossary's
   `Routing` disambiguation for the other senses rather than restating them.
2. **The layer table** — one row per layer (L0 entry, L1 partition classification,
   L2a declared decision, L2b affirmative decision, L3 discovery/assembly, L4 translation),
   each naming its **owning module** and what it is aware of. See `data-model.md` §1.
3. **Both composition roots** — the read root and the write root, shown as separate roots
   reached through one seam object (INV-4).
4. **The compliance taxonomy** — compliant tier-1 / delegating-but-lenient /
   semi-compliant / non-compliant, with the shape of each (`data-model.md` §1).
5. **Honest bounds** — the surface members with no production producer, and the frozenset
   still carrying a retired word as residual rename debt (INV-5). Named, not laundered.
6. **Citations** — ADR `2026-06-24-1` (kind-and-topology-aware placement) and ADR
   `2026-07-23-1` (`TopologySurface` vocabulary + the forbidden-conditioning rule) as the
   governing decisions.

## C2 — Required accuracy (the load-bearing corrections)

- **The L2 split is deliberate and MUST be shown as two functions.** The declared decision
  is materialization-blind *so that it can disagree with an already-resolved stamp*; that
  divergence is what allows the existing surface-cannot-hold guard to fire. Describing "one
  decision module" is a defect.
- **Translation MUST NOT be described as assembling a path.** It selects an
  already-discovered location and refuses when absent. Assembly belongs to L3. Getting this
  wrong teaches readers to strangle through L4 and re-add discovery at the call site — the
  misappropriation the page exists to prevent.
- **Every code-shape claim MUST carry a `module:symbol` citation** so drift is detectable by
  reading, and so a future rename shows up as a broken citation rather than silent rot.

## C3 — Prohibitions

- MUST NOT restate normative rules the ADRs own (the placement invariant, the
  forbidden-conditioning rule, alias retirement) — link to them. The page is
  **explanatory**.
- MUST NOT introduce a synonym for a concept the glossary already names (`TopologySurface`,
  `PRIMARY partition`, `COORD partition`).
- MUST NOT be named `*-routing.md` — the word is already overloaded across ≥10 senses.

## C4 — The competing authority MUST be narrowed in the same slice

`docs/architecture/branch-target-routing.md` currently asserts per-artifact-kind placement
rules (the new page's core claim) under a branch-sense title, in vocabulary the glossary
retires, with no read path. In the same slice it MUST be reduced to the **branch** sense and
link to the new page for placement. Leaving both is the two-authority failure this mission
exists to end.

## C5 — Acceptance

| Check | How verified |
|---|---|
| Sections C1.1–C1.6 present | docs test asserting the named sections and the citations |
| Layer table matches the code | reviewer reads each row's cited `module:symbol` |
| No prohibited synonym; terminology guard green | terminology + glossary-canonical-terms gates |
| Registered and discoverable | `docs/architecture/index.md` entry; both gated registries regenerated; links resolve; `check_docs_freshness --ci` zero errors |
| Competing page narrowed | the old page no longer asserts kind-level placement rules, no longer uses the retired alias, and links out (SC-017) |
| Comprehension | a reader who has not followed the programme can state the three questions in User Story 7's Independent Test |
