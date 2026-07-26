---
title: "Test-Quality Doctrine — Artefact Series Proposal"
description: "Curator-facing proposal (doctrine-daphne) for the test-slicing/mocking-boundary doctrine series: a Tests-as-Scaffold paradigm, DIRECTIVE_041 disambiguation, checklist→asset moves, exemplar assets, and the full DRG edge map — augment-heavy, create-light."
doc_status: draft
updated: '2026-07-26'
related:
- docs/plans/doctrine/test_quality/mocking-boundary-and-test-slicing-research.md
- docs/plans/doctrine/index.md
---
# Test-Quality Doctrine — Artefact Series Proposal

**Author:** doctrine-daphne (curator scout) + operator refinements
**Date:** 2026-07-26
**Companion to:** [Research findings](mocking-boundary-and-test-slicing-research.md)
**Feeds:** [#2935](https://github.com/Priivacy-ai/spec-kitty/issues/2935)

This is a **design proposal for a curator**, not the artefacts themselves. It supersedes
§8 of the research findings (which recommended a single new artifact from a false-uniqueness
premise — see the reconciliation note below). No files are created by this document.

---

## Guiding correction — augment-heavy, not create-heavy

An overlap audit against the pack's existing testing doctrine found that most of the
research doc's load is **already carried** by wired, activatable authority:

- `styleguide:test-desiderata-and-boundaries` — the 12 desiderata + boundary-by-responsibility.
- `tactic:test-boundaries-by-responsibility` — the operative "mock only at the border" rule.
- `tactic:function-over-form-testing` — the interaction→outcome assertion shift.
- `tactic:connascence-analysis` — the connascence lens the research calls its backbone.
- `directive:DIRECTIVE_041` "Tests as Scaffold, Not Friction" (`enforcement: required`) — already binds "assert the observable contract, not the internal call graph."

So the series is **augment-heavy, create-light**. This also resolves the external review's
finding #1 (PR #2936): the research doc's "currently unwritten" framing (§6) and its
"create a new binding artifact" recommendation (§8) overclaimed uniqueness; the correct move
is to reconcile and extend the existing wired authority, creating only the genuine deltas.

The genuine deltas: (1) the **positive** allow-list of legitimate mock seams as a citable
rule; (2) the specific failure mode — mocking internal SUT logic to pin a call-contract,
which manufactures a production-unreachable state; (3) a remediation **procedure**
("unfake a test"); (4) the **mindset** currently mis-homed inside a directive.

---

## The operator's topology refinements (applied)

1. **"Tests as Scaffold, Not Friction" is a paradigm (mindset), not a directive.** Create a
   new paradigm; disambiguate `DIRECTIVE_041` so the binding rule stays a directive and the
   mindset/why moves to the paradigm, relinked via `refines`.
2. **Test Desiderata is a complementary checklist that is part of the paradigm** — relinked,
   not re-kinded (it stays a styleguide; its enumerated list becomes an asset).
3. **Checklists → assets.** The `asset` kind is a loose-contract blob (markdown/python via a
   `*.asset.yaml` sidecar), resolved-only, referenced via `requires` edges (working precedent:
   `directive:DIRECTIVE_042 --requires--> asset:common-docs-structural-lint`). Move duplicated
   checklists (the desiderata list; the Quad-A definition) into shared assets.
4. **Exemplar assets for exhaustive examples.** Short good/bad snippets stay inline; the full
   UserRegistration slicing case and the #2934 before/after become exemplar assets, referenced
   from the good artefacts (never emitted from anti-pattern nodes — those are `rejects` targets
   only).

---

## Proposed series

### Create

- **`paradigm:tests-as-scaffold-not-friction`** [activatable] — the mindset: tests protect
  change; the false-confidence (mocked-out behaviour) / false-friction (implementation-coupled
  assertions) duality; Beck's desiderata as the value system; connascence framing; the
  policy-choice honesty clause. Carries the migrated `DIRECTIVE_041.intent`.
- **`directive:DIRECTIVE_047` — Mock Only at the Responsibility Border** [activatable,
  `required`] — the positive allow-list (other-domain / filesystem / DB / rare system-logic) +
  the manufactured-state failure mode. `requires` DIRECTIVE_041; does not restate it.
- **`procedure:unfake-an-over-mocked-test`** [activatable] — the six-step remediation.
- **`anti_pattern:mock-internal-sut-logic`** [resolved-only], **`anti_pattern:assert-on-mock-interactions`** [resolved-only]
  — nodes in `anti_pattern.graph.yaml`, `rejects` targets only.
- **Assets** [resolved-only]: `asset:test-desiderata-checklist`, `asset:quad-a-test-structure`,
  `asset:exemplar-slicing-user-registration`, `asset:exemplar-2934-unfake-merge-test` (markdown
  blobs under `assets/built-in/` + `*.asset.yaml` sidecars).

### Augment (edit, no new node)

- `DIRECTIVE_041` — move `intent` (mindset) into the paradigm; shrink to a pointer; add
  `--refines--> paradigm`.
- `styleguide:test-desiderata-and-boundaries` — add the "Isolated ≠ isolate-via-mocks" and
  Gold-Plating traps + the connascence-of-a-mock line; extract the desiderata list to the asset.
- `styleguide:testing-principles` / `python-conventions` / `java-conventions` — extract the
  shared Quad-A **definition** to the asset; keep language-specific code examples inline.
- `tactic:test-boundaries-by-responsibility` — add the rare system-logic exception + a
  `failure_modes` entry; `rejects` the internal-mock anti-pattern; `suggests` the slicing exemplar.
- `tactic:function-over-form-testing` — add the #2934 one-liner; `rejects` the interaction-assert smell.

---

## DIRECTIVE_041 disambiguation (stays vs moves)

- **Stays in the directive** (binding surface): `enforcement`, `scope`, all `procedures`,
  `integrity_rules`, `validation_criteria`, `references`.
- **Moves to the paradigm** (mindset): the long `intent` block ("Tests must protect change,
  not obstruct it… tests that pass for the wrong reason are friction…"). Replace 041's `intent`
  with a one-line pointer to the paradigm.
- **Relink relation: `refines`** (directive sharpens the mindset into an enforceable rule).
  Not `specializes_from` (that is agent_profile→agent_profile lineage only). Not `requires`
  (a hard cascade-prerequisite; the rule can operate as a checklist independently) — unless the
  curator wants the paradigm auto-pulled whenever an action scopes 041, in which case `requires`
  is the documented fallback trade-off. **This is the first `refines` edge in the built-in
  graph** — confirm it round-trips through the org→DRG bridge on regeneration.

---

## DRG edge map (source --relation--> target)

Paradigm hub:
- `paradigm:tests-as-scaffold-not-friction --requires--> styleguide:test-desiderata-and-boundaries`
- `paradigm:… --suggests--> styleguide:testing-principles`, `tactic:connascence-analysis`,
  `asset:quad-a-test-structure`, `asset:exemplar-slicing-user-registration`
- `paradigm:… --rejects--> anti_pattern:mock-internal-sut-logic`, `anti_pattern:assert-on-mock-interactions`

Directives:
- `directive:DIRECTIVE_041 --refines--> paradigm:tests-as-scaffold-not-friction`
- `directive:DIRECTIVE_047 --refines--> paradigm:tests-as-scaffold-not-friction`
- `directive:DIRECTIVE_047 --requires--> directive:DIRECTIVE_041`
- `directive:DIRECTIVE_047 --suggests--> tactic:test-boundaries-by-responsibility`,
  `tactic:function-over-form-testing`, `styleguide:test-desiderata-and-boundaries`,
  `asset:exemplar-2934-unfake-merge-test`
- `directive:DIRECTIVE_047 --rejects--> anti_pattern:mock-internal-sut-logic`, `anti_pattern:assert-on-mock-interactions`

Procedure:
- `procedure:unfake-an-over-mocked-test --requires--> tactic:test-boundaries-by-responsibility`
- `procedure:… --suggests--> directive:DIRECTIVE_047`, `tactic:function-over-form-testing`, `asset:exemplar-2934-unfake-merge-test`
- `procedure:… --rejects--> anti_pattern:mock-internal-sut-logic`

Tactics / checklist-asset edges:
- `tactic:test-boundaries-by-responsibility --rejects--> anti_pattern:mock-internal-sut-logic`; `--suggests--> asset:exemplar-slicing-user-registration`
- `tactic:function-over-form-testing --rejects--> anti_pattern:assert-on-mock-interactions`
- `styleguide:test-desiderata-and-boundaries --requires--> asset:test-desiderata-checklist`
- `styleguide:testing-principles --requires--> asset:test-desiderata-checklist`, `asset:quad-a-test-structure`
- `styleguide:python-conventions --requires--> asset:quad-a-test-structure`
- `styleguide:java-conventions --requires--> asset:quad-a-test-structure`

Every resolved-only node (asset / anti_pattern) has ≥1 inbound edge from an activatable node — no orphans.

---

## Capability-awareness (intent dominates)

The sibling doctrine PR #2918 surfaced that **asset support is not end-to-end** in some usages:
`type: asset` used as a *field inside a tactic* is schema-rejected, and manifests under
`assets/<subdir>/built-in/**` are missed by the extractor (which scans `assets/built-in/**`).
Per the operator's steer — *fix the root cause, do not greenwash by relabeling assets→templates;
intent dominates over current capability* — this proposal is deliberately built on the **working**
asset pattern to avoid those traps by construction:

- assets are referenced via **`requires`/`suggests` DRG edges** (working precedent exists), not a
  `type: asset` field inside a tactic body;
- asset blobs live at **`assets/built-in/<file>`** (the path the extractor scans), not a subdir.

Residual verification the curator must still run (do NOT relabel to dodge them):
1. Confirm the extractor picks up the four new `assets/built-in/*.md` blobs.
2. Confirm CLI/canonical-validator **parity** — `spec-kitty doctrine validate` must reject the
   same things the strict canonical tests reject (the #2918 review found a parity gap).
3. If any of this reveals a genuine asset-support gap, closing it is **in-scope prerequisite
   work**, not a reason to downgrade the artefacts.

---

## Load-time / validation risks

1. Asset **path containment** — relative, under `assets/`, no `..`/symlink escape (all use `built-in/<file>`).
2. Asset **mime/extension consistency** — `text/markdown ↔ .md`; never declare markdown on a `.py`.
3. **Resolved-only** discipline — assets/anti-patterns are never charter-activated; enter context only via inbound edges.
4. **URN/kind prefix** must equal kind; confirm `DIRECTIVE_047` is free (max present is 046).
5. `enhances`/`overrides` are **not** usable on assets/anti-patterns — dedup is via `requires`→asset edges.
6. Anti-pattern nodes **emit no edges** — route exemplar references through the good artefacts.
7. `refines` **first use** — verify round-trip on regeneration.
8. The 041 split must not author an accidental `in_tension_with` — the relation is `refines` (aligned, not competing).
9. Add each anti-pattern/asset **node** in the same change as its referencing edges; regenerate the compiled graph; validate to zero errors.

---

## Build order for the curator

1. Asset blobs + sidecars; asset nodes in `asset.graph.yaml`.
2. Paradigm; migrate `041.intent` → paradigm; shrink 041's intent to a pointer.
3. `DIRECTIVE_047` + `procedure:unfake-an-over-mocked-test`; two anti-pattern nodes.
4. Excise the desiderata list + language-neutral Quad-A definition from the styleguides (keep language-specific examples inline).
5. Author all edges; regenerate `graph.yaml`; run the reference/cross-edge audit + pack validation to zero errors; confirm the *Clear Test Boundaries* URL.
