# Assessment: Inverting charter authority (charter.yaml authoritative, charter.md generated companion)

**Date:** 2026-07-18
**Trigger:** Operator reopened the C-001 fence, proposing (deterministic-first): make `charter.yaml` the authoritative structured "what is active?" source and `charter.md` a *generated/companion rationale* artifact it references.
**Method:** 4-lens profile-loaded read-only squad (architect-alphonso, paula-patterns, reviewer-renata, curator-carla).
**Outcome:** 3-of-4 → do NOT invert inside #2773; invert (if at all) as a separate ADR-backed decision after #2773. 1 dissent (paula → invert now).

---

## The load-bearing correction (all four converged here)

The proposal conflates **three distinct authority surfaces** that recorded doctrine keeps separate (carla's decomposition):

| Surface | What it is | Where it lives today | Owning ticket |
|---|---|---|---|
| **A. Activation ledger** — "what is active?" | `activated_*` lists | `.kittify/config.yaml` (structured, deterministic) + `answers.yaml selected_*` | #2519 (disjoint-ledger reconciler) |
| **B. Compiled resolving bundle** | governance/directives/metadata/**references**.yaml | `.kittify/charter/*.yaml` (derived) | **#2773 (this mission)** — fold B → one `charter.yaml` |
| **C. Human prose policy** | curated governing-principle rationale | `.kittify/charter/charter.md` (~30 KB, hand-authored) | #2772 (protect from clobber) |

**"What is active?" is already structured and deterministic — surface A, in `config.yaml activated_*` (`config.yaml:19…197`), not `charter.md`.** `compile_charter` sources activation from `config.activated_*`, *never* from `charter.md` or `interview.selected_*` (`compiler.py:295-328`). So the operator's deterministic-first goal *for activation* is already met.

**`charter.yaml` (from #2773) is surface B — a DERIVED resolving bundle.** It cannot become "the authoritative source" without ceasing to be derived. The genuinely NEW ask is therefore about surface **C**: flip the human *authoring* surface for governance prose from markdown to structured, and render `charter.md` from it.

---

## Why "charter.md generated" is the crux blocker (renata, alphonso)

- Curated rationale prose is **not mechanically derivable** from structured YAML. charter.md is ~30 KB; the entire structured extract (governance 761 B + directives 3.2 KB + metadata 419 B) ≈ 4.3 KB — the prose is ~7× the projection and unrecoverable from it.
- If `charter.md` becomes a render of `charter.yaml`, then `write_compiled_charter`'s `charter_path.write_text(compiled.markdown)` (`compiler.py:421`) becomes the **normal** compile path — recreating the **#2772 P0 clobber (a 1237-line curated-prose destruction) as designed behavior**, not just a `--force` accident.
- The reverse migration (parse existing `charter.md` prose → authoritative `charter.yaml`) depends on the exact **hybrid/AI, non-deterministic** prose-extraction the inversion claims to eliminate: this repo's `metadata.yaml` shows `extraction_mode: hybrid`, 32 AI-assisted sections. That migration is lossy and non-idempotent → violates #2773's own **NFR-003 (idempotent migration)** and **C-003 (fail-loud, no silent fallback)**.

### The three readings of "generated companion"
- **(a)** `charter.md` = hand-authored companion the yaml merely *references* (NOT generated). **Viable** — but this is verbatim the already-scoped **#2772** end-state; the word "generated" is a misnomer.
- **(b)** `charter.md` = truly generated from rationale fields inside `charter.yaml`. **Non-viable** — authoring 30 KB of prose inside YAML block scalars is diff-hostile/whitespace-fragile, and it recreates the #2772 clobber as normal behavior. **Blocker-grade.**
- **(c)** structured knobs authored structurally (retire the hybrid/AI extractor — a *real* deterministic-first win); `charter.md` a co-equal hand-curated prose artifact, neither derived from nor extracted into the other. **Legitimate but a much larger mission** — deletes the extractor pipeline and re-homes governance authoring. Sequence after #2773 + #2772; never merge into either.

---

## Recorded-intent reconciliation (carla)

The operator's instinct splits across axes:
- **Resolving authority** ("charter.yaml authoritative for resolving; charter.md never a resolving input") → **EXTENSION / already intended.** Confirmed by #2772, #2773 "intended effect", and the recorded lean.
- **Authoring direction** ("charter.md generated *from* charter.yaml") → **REVERSAL of a documented invariant.** `docs/context/charter-overview.md:20`: "charter.md is the runtime policy **source**… synthesis **reads that file**"; `docs/context/governance-files.md`: charter.md = Human, edit-directly = Yes; YAML "derived only from charter.md."
- **Merging the A activation ledger into charter.yaml** → **NEW ground.** ADR 2026-07-15-1 (Proposed) routes "what is active" to `config` + `src/charter/packs/default.yaml`, *not* the compiled bundle.

**Governance risk of folding into #2773: HIGH** — changing the single canonical *authoring* source (prose→structured) is a structural-boundary change requiring an ADR; it contradicts #2773's own C-001 ("charter.md remains authored") and the "curated reference" framing #2772/#2773 pin.

---

## Also surfaced (independent of the inversion)

- **#2773 spec tightening (alphonso):** FR-005 says "re-point *all* consumers to charter.yaml sections," but the policy-summary + critical-section consumers read `charter.md` **prose** (`context.py:273,1023`; `compact.py:135`). Since #2773 does NOT retire `charter.md` (only the four B-files), those consumers are untouched — FR-005/SC-002 wording should scope to "the four subsumed files" and state `charter.md` is not retired. Clarity fix, not a blocker.
- **Optional cheap rider (alphonso):** design the new `charter.yaml` schema with *room* to later hold prose sections, so a future inversion/#2772 doesn't force a second C-004 schema bump. Near-zero cost; carla/renata prefer strictly-as-is to keep #2773 bounded.
- **Ownership debt (paula):** two activation writers into config.yaml (`commit_plan` vs `merge_defaults` `pack_manager.py:703-755`, the latter unvalidated) and the 3-vs-4 bundle file-set are separate seams the inversion does NOT fix — candidates for the #2519 reconciler, not #2773.

---

## Verdicts

| Lens | Verdict |
|---|---|
| architect-alphonso | INVERT-AS-SEPARATE-MISSION (after #2773) + cheap schema-roominess rider in #2773 |
| paula-patterns | INVERT-NOW-IN-2773 (dissent) — reframe; fold merge_defaults + 3-vs-4 |
| reviewer-renata | KEEP-CURRENT-SPEC for #2773 (would BLOCK inverting-in-2773); sound residue = #2772; drop "generated" |
| curator-carla | INVERT-AS-SEPARATE-MISSION + ADR; #2773 proceeds as-specced |

## Recommendation (synthesis)

1. **Proceed with #2773 as-specced** — the bounded, shippable resolving-bundle consolidation (surface B). Apply the FR-005/SC-002 clarity fix; optionally fold the schema-roominess rider.
2. **The inversion is a genuinely new decision → its own ADR.** The narrow real question: *should the human authoring surface for governance prose flip from `charter.md` (markdown) to `charter.yaml` (structured), retiring the hybrid/AI extractor (deterministic-first), and should `charter.yaml` also absorb the A activation ledger?* Sequence after #2773 (needs charter.yaml to exist) and revisit #2772's pinned "charter.md authored" invariant.
3. **Keep #2772 (P0 clobber) on its own track** — it protects curated prose users depend on today; if the inversion is later accepted it supersedes #2772. No timeline conflict.
4. **The real deterministic-first win hiding in the proposal** is renata's reading (c): retiring the non-deterministic hybrid/AI prose-extractor. Name it in the ADR as the actual target — it is not captured by any current ticket.

---

## Round 2 — Dialectic + empirical resolution (2026-07-18)

Operator reopened with two inputs: run a dialectics squad, and the binding correction that **`answers.yaml` is provenance-only** (zero runtime impact; reading `selected_*` for behaviour is a bug → `config.yaml activated_*` is the sole activation authority). See [[reference-answers-yaml-provenance-only]].

**Thesis (pro-invert, architect):** reframed to reading (c) — seed `charter.yaml` from the existing **triad** (yaml→yaml, deterministic, = #2773's own FR-006 migration), keep `charter.md` hand-authored, delete the single clobber writer, retire the scraper. Verified two facts.
**Antithesis (pro-defer, reviewer):** conceded resolving-authority is already delivered by #2773; held that the bootstrap migration is lossy — but that rested on the "AI extractor" premise.

**Verified facts (orchestrator-confirmed):**
- `extractor.py:807 extract_with_ai` returns `{}`, **zero callers**, no LLM imports → prose→triad extraction is 100% deterministic regex; `"hybrid"` label is cosmetic. The antithesis's "32 AI-assisted sections ⇒ non-idempotent migration" is a **mislabel** — migration is deterministic.
- charter.md content writers in src/: `compiler.py:421` (the `--force` clobber) + `generator.py:62 write_charter`; normal derive path writes only the triad.

**Neutral empirical investigation (the converged falsifier):** does any *behavioral* consumer read `charter.md` prose not already in the triad?
- **Answer: effectively NO behavioral loss** for the disputed proposition. All prose reads (`context.py:274 _extract_policy_summary`, `context.py:1023/2754/2784 render_critical_section_bodies`, `compact.py:138 extract_section_anchors`) flow into **DISPLAY** (agent-facing bootstrap/context text), not decisions. The triad loaders (`sync.py:307/356`) read the **triad YAML**, not prose, at resolve time.
- **One orthogonal caveat:** `language_scope.py:101-103` tier-3 reads charter.md free-text for doctrine language-scoping (a real gate via `scoping.py:62-69`) — but its authoritative source is `references.yaml` (structured, from the interview, precedence tier-1); charter.md is a degraded last-resort fallback. It is **not** produced by the scraper and **not** in the triad, so seeding charter.yaml from the triad neither captures, loses, nor needs it. It stays as-is (note as a follow-up: migrate that fallback off charter.md prose to references.yaml-only).

**Resolution:** the "lossy migration" blocker is **void**. Seeding `charter.yaml` from the triad is deterministic and lossless (satisfies NFR-003). The inversion's remaining cost is **not** a data-migration problem — it is (a) a governance/authoring-UX structural change (operators author structured fields) that warrants an ADR, and (b) the C-004 **schema-shape decision**, which is expensive-to-reverse and must be made **once**.

**Reconciled recommendation (Option X — reshape #2773 to be authoring-ready now; stage the deletion):**
1. **Short ADR** records the end-state: `charter.yaml` = authoritative structured source (governance/directives/activation-ref/catalog); `charter.md` = hand-authored curated companion, never a resolving input, never clobbered; the prose→triad scraper is retired. Plus the `answers.yaml`=provenance-only + `config.yaml`=sole-activation facts. This is the operator's philosophy call, now empirically de-risked.
2. **Reshape #2773**: build `charter.yaml` with governance/directives/catalog as **first-class authorable fields** (schema-roominess becomes load-bearing) + fold the 1-line clobber guard (`compiler.py:421`). Flip C-001 from "charter.md stays authored / inversion OUT" to "charter.yaml is the authorable structured source; charter.md is a curated companion; extractor retirement STAGED." Migration stays deterministic yaml→yaml (triad→charter.yaml). **Rationale: avoids a second C-004 schema bump + migration rewrite on the same brand-new file — exactly the split/drift/stopgap churn epic #2519 exists to kill.**
3. **Fast-follow (own mission, same ADR):** delete `extractor.py` + `sync()` backward scrape, re-home the authoring UX, re-point the DISPLAY prose-consumers, migrate the language tier-3 fallback. Extractor can keep populating legacy during transition.
4. **#2772** (clobber P0): folded (the guard) / superseded (charter.md stops being written by the derive path once the extractor retires).

**Why reshape rather than keep-bounded + separate mission:** the only expensive-to-reverse artifact is the `charter.yaml` schema (C-004). Shipping a derived-from-prose schema we already know we'll re-cut for the inversion would re-create the churn the epic is closing. Deciding it authored-ready once is the canonical-sources / one-seam move.
