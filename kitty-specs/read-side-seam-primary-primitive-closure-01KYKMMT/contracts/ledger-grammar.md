# Contract: Ledger Grammar and Per-Site Index

Binding contract for **FR-008 / FR-009** (IC-02). This is a **hard prerequisite** (C-009):
no classification row for a newly censused primitive may be written until these hold.

## Why this is a prerequisite, not a finishing touch

The originally-prescribed "per-primitive sub-tables" shape was **executed** against the real
parser. Result: only the **first** table under a parsed heading is read; the second
primitive's rows vanish; and the reconciliation test stays **green**. That is a silently
vacuous gate — the exact failure a previous landing pass had to repair on this same gate.
Adding rows first would bake it in.

## G1 — Parse constraints (normative)

| Rule | Failure it prevents |
|---|---|
| Exactly **one** table under each machine-parsed heading | second table silently dropped |
| Parsed headings kept **verbatim** (located by exact full-line match) | section not found → parses empty |
| Verdict / `rel_path` / `qualname` remain at their **current leading column positions** | positional readers silently skip or mis-read rows |
| A `primitive` discriminator is **appended as a trailing column** | a leading/middle insertion breaks the positional contract; appending fails loudly if mis-specified |
| No duplicate key within a counts table | duplicate keys overwrite silently, last-wins |
| Non-numeric cells in count columns are an error, not a skip | silent row skipping |

## G2 — Index grammar (per-site addressing)

The stay-lenient index is keyed per **site**, not per function. It MUST be able to address
several censused sites inside one qualname — a known case carries **four** (one existing
primitive plus three of the newly censused one).

- The key gains a discriminator (trailing `primitive` + site token, or an equivalent
  composite) so each site is distinct.
- The **uniqueness assertion MUST be updated in the same change** as the key shape;
  otherwise it reds by construction.
- Acceptance fixture: the known four-site qualname.

## G3 — New gate assertions (this is what makes the grammar enforceable)

1. **Row-count reconciliation** — parsed row count **equals** the summed per-primitive
   census. A dropped table or shifted column makes this red rather than parse-empty.
2. **Per-primitive mutation** — mutating a row belonging to **each** primitive
   independently MUST red the gate. A single-primitive mutation test would pass while the
   second primitive is unenforced.
3. **Counts scoping** — reconciliation covers the **live residual / lenient** totals, which
   are the figures the gate parses. The historical pre-migration totals are **preserved and
   labelled as an audit record**, never rewritten to satisfy a check.

## G4 — Acceptance

| Check | How verified |
|---|---|
| G1 holds | the reconciliation and mutation tests above, plus a review of the section shapes |
| G2 holds | the four-site qualname is representable and the uniqueness assertion passes |
| Mutation reds per primitive | scratch-copy mutation per primitive, each expected red |
| Historical totals intact | the pre-migration figures still present and labelled |
| Ordering respected | no new classification row exists in any commit before the commit that lands G1–G3 |
