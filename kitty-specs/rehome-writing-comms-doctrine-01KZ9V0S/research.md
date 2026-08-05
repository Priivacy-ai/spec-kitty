# Phase 0 Research: Rehome & Complete Writing-Comms Doctrine

Grounded against current `main` (`1051c430d`) via three independent read-only research lenses
(DRG+gates, routing+incumbents, WS2 content) plus two direct verifications. Cited line
references were captured by the lenses; treat them as accurate-as-of-research and re-confirm
at the touch-point during implement.

---

## D-01 — DRG wiring is GENERATED from frontmatter, not hand-authored

**Decision.** The mission authors artifact **frontmatter references** and runs
`spec-kitty doctrine regenerate-graph` to (re)mint the per-kind
`packs/built-in/<kind>.graph.yaml` fragments; it does **not** hand-edit node/edge YAML in the
built-in layer. A `regenerate-graph --check` freshness gate fails CI if the committed
fragments are stale, so the regenerated fragments are committed.

**Rationale.** Verified directly: `spec-kitty doctrine regenerate-graph` exists ("Regenerate
the shipped DRG graph source deterministically"); the checked-in fragments carry
`generated_by: drg-migration-v1` headers; the extractor (`src/doctrine/drg/migration/extractor.py`,
driven by `src/specify_cli/cli/commands/doctrine.py:210-296`) reads artifact frontmatter and
merges only a small hand overlay (`in_tension_with`/`reconciles_tension`/`rejects` edges +
`anti_pattern` nodes). Edge minting rules:
- **Directives / procedures / tactics**: top-level `references: [{type, id, when?}]` → tactic
  refs default `suggests`; directive/procedure refs → `requires` when mandating else `suggests`.
- **Styleguides / toolguides**: `references:` as a `list[str]` file-path form → `suggests`.
- **Agent profiles**: the extractor reads **only** `context-sources.directives` (→ `requires`)
  and `tactic-references` (→ `requires`). It does **NOT** read the top-level
  `directive-references` field. So a profile's DRG reachability edges come from
  `context-sources.directives` / `tactic-references`; `directive-references` is a display /
  shipped-profiles-gate field only.
- **specializes_from** profile lineage is curated in `_CURATED_ARTIFACT_EDGES`, not a field.

**Correction of prior drift.** My PR #2918 comment (2026-08-05) and an over-reading of the
CLAUDE.md `specializes_from` note said "extractor retired #2950, edges hand-authored." That
conflated two layers: the **built-in** layer is *generated* (this decision); the *hand-authored*
`urn:profile:`-endpoint hazard guarded by `_resolve_edge_endpoint` (`src/doctrine/drg/merge.py`)
applies to **org-pack** fragments, which are a different surface. #2950 (`873832aa1`) was the
built-in relocation, not an extractor retirement.

**Alternatives considered.** Hand-authoring fragments — rejected: it fights the generator and
would fail `regenerate-graph --check`.

**Implication for artifacts.** Each of the 7 profiles needs BOTH `directive-references` (for
the shipped-profiles gate, D-04) AND `context-sources.directives` (to mint the DRG `requires`
edges that confer reachability, NFR-001).

---

## D-02 — `type: asset` tactic reference is schema-valid

**Decision.** Keep `writing-audience-catalog.tactic.yaml`'s `references` entry as `type: asset`
(no relabel to `template` — no greenwashing, per C-004). Confirm the full
`doctrine validate` (including reference *resolution*) empirically at implement, once the 5
audience assets exist at `packs/built-in/assets/audiences/`.

**Rationale.** Verified directly: `TacticReference.type` is typed as the full `ArtifactKind`
enum with no `Literal` restriction (`src/doctrine/tactics/models.py:51`), and `asset` is an
`ArtifactKind` member. So the schema accepts `type: asset`. This matches the on-record A4
finding in the PR comment (materialised 21/21 OK). The DRG-lens's "restricted permitted set"
claim was a misread of the model. Residual risk: reference *resolution* needs the asset to
resolve at its canonical path — cheap to prove at implement.

**Alternatives considered.** Relabel `asset`→`template` (zohar's original CI-appeasement
suggestion) — rejected by the operator on-record ("fix the root cause, don't relabel"); the
root cause is already fixed upstream (enum membership).

---

## D-03 — Routing fix: narrow the primary role on the 3 colliding profiles

**Decision.** On the three profiles whose *primary* role (`roles[0]`) collides with an
incumbent, replace the generic primary role with a narrow custom role:
- `diagram-daisy`: `roles[0]` `designer` → `diagram-author`
- `comms-cleo`: `roles[0]` `curator` → `communicator`
- `synthesizer-sam`: `roles[0]` `curator` → `synthesizer`

**Rationale.** `ActionRouter.route()` (`src/specify_cli/invocation/router.py:220-385`) resolves
profile_hint → canonical-verb→role candidate set → domain-keyword filter → **priority
tiebreaker (higher wins)**. `AgentProfile.role` returns `roles[0]` only
(`src/doctrine/agent_profiles/profile.py:337-339`), and candidate expansion filters on `.role`.
With no discriminating context the domain-keyword step contributes nothing, so a bare canonical
verb selects among *all profiles sharing that primary role* by priority. The real, reproducible
collisions are exactly two role buckets:
- **DESIGNER** (verbs design/mockup/prototype/wireframe): `diagram-daisy@60` beats
  `designer-dagmar@50`.
- **CURATOR** (verbs curate/classify/organize/tag/validate/verify): `comms-cleo@55` and
  `synthesizer-sam@50` beat `doctrine-daphne@48` / `curator-carla@40`.

Replacing `roles[0]` with a non-canonical custom role removes the profile from the
canonical-verb candidate set entirely, so the incumbent wins **independent of priority** and
with no deactivation-fragility — exactly what the 4 already-safe new profiles (analyst-annie,
lexical-larry, minutes-maker-mahad, scribe-sally) already do.

**Sharpening of the review finding.** The "researcher shadowing" claim does NOT reproduce:
`comms-cleo`/`synthesizer-sam` carry `researcher` only as a *secondary* role, so `.role` is
`curator` and they never enter the RESEARCHER bucket. `analyst-annie@60` is harmless (primary
role `analyst` is non-canonical). Priority alone is not the vector — the generic `roles[0]` is.

**Alternatives considered.** (b) Lower priority below incumbent — rejected: fragile (profiles
stay in the candidate set; win if an incumbent is deactivated; must clear `daphne@48` not just
`carla@40`). (c) Add discriminating domain keywords — rejected as the sole fix: L3 never fires
with no context, so it cannot fix the no-context case.

**Red-first tests.** `tests/specify_cli/invocation/test_router.py`, using `_make_mock_registry`
+ `ActionRouter(registry).route(text)`. Two negative regressions (bare "design…" → dagmar; bare
"classify…" → carla/daphne — RED before fix) plus a positive test (diagram-from-brief → daisy).

---

## D-04 — Shipped-profiles contract: 16 frontmatter fields to author

**Decision.** Author the missing contract fields so all 7 profiles pass
`tests/doctrine/test_shipped_profiles.py`, and register the 7 ids in `EXPECTED_PROFILE_IDS`.

**Rationale.** Every non-sentinel profile must declare (each asserted non-empty): (1)
`collaboration.canonical-verbs`, (2) `collaboration.output-artifacts`, (3) `mode-defaults`, (4)
every mode's `use-case`, (5) `context-sources.doctrine-layers`, (6) `directive-references`; plus
≥1 role, non-empty purpose/name/specialization.primary_focus, schema-valid, no scalar `role:`.
The pr-2918 profiles miss **16** fields: all 7 miss `canonical-verbs`; `diagram-daisy` +
`scribe-sally` miss `output-artifacts`; `scribe-sally` misses `mode-defaults`; all but
`synthesizer-sam` miss `doctrine-layers`. Note the routing fix (D-03) changes `roles[0]` to a
custom role — assert-safe (the gate only requires ≥1 role, not a canonical one).

**Alternatives considered.** Register ids without authoring the fields (what commit `519032608`
did) — rejected: it deliberately surfaced the 16 failures; the mission must close them.

---

## D-05 — Pinned-count gates: two definite updates, reachability empirical

**Decision.** Update `test_pack_relocation_doctor_gate.py`: `EXPECTED_PROFILE_COUNT 18 → 25`,
and recompute the `(node_count, edge_count) == (324, 892)` tuple *after* `regenerate-graph`
(it moves by +21 nodes and whatever edges mint). Update `EXPECTED_PROFILE_IDS` (+7) in
`test_shipped_profiles.py`. For `tests/doctrine/drg/test_reachability.py`, **recompute
empirically** — do not pre-edit literals.

**Rationale.** `EXPECTED_GLOSSARY_TERM_COUNT = 108` is unchanged (no glossary edits). The
reachability pins are computed as `_activated() − reachable` from the repo's *explicit*
`.kittify/charter/charter.yaml` `activated_*` lists; `agent_profile`/`asset` are not activation
kinds and never appear in the pins, and the new profiles mint zero edges toward the pins. So the
reachability literals change **only if** the mission activates the new directives/procedures/
styleguides/tactic in the dogfood charter. Default: do **not** activate them (keeps the mission
scoped to shipping the doctrine, not dogfooding-activating it), so reachability pins stay put —
but verify by running the module's five traversal calls and diffing. Any pin move needs a
matching ledger row in `docs/plans/doctrine/delivery-reachability-wiring-table.md`
(`TestProfileRescuesHaveLedgerCoverage`).

**Alternatives considered.** Speculatively editing reachability frozensets — rejected: false
churn; the gate is self-measuring.

---

## D-06 — WS2 content reconciliations (per blocker)

All six reproduce (one partially). Minimal, evidence-grounded dispositions:

1. **diagram-daisy false Directive-031 attribution** (reproduces, worse). Directive 031
   (`packs/built-in/directives/031-context-aware-design.directive.yaml`) is entirely about
   bounded-context ubiquitous language — zero diagram/C4 policy; and the ban *contradicts*
   existing doctrine (`reference-architectural-patterns.tactic.yaml`, and
   `use-c4-model-techniques.directive.yaml` is deliberately notation/pattern-neutral). **Fix:**
   remove the `directive-references` 031 block and strike the hexagon/three-tier/utility ban from
   `purpose`; the capability-deployable/BFF convention is org-specific, not built-in doctrine.

2. **minutes-maker-mahad over-claims enforcement** (reproduces). No minutes schema / validator /
   VTT parser / publisher ships anywhere in `src/` or `packs/`. **Fix:** reword enforcement verbs
   ("enforces … hard pre-publish gate", "publishes via authenticated API", "schema-valid") to
   agent-discipline language ("checks that every action item has a named owner before handing off
   for publishing"; "a structured minutes shape"). **And** state as doctrine the trust boundaries
   the procedure implies: consent/provenance, retention, prompt-injection handling (transcript is
   untrusted input — data-in/structure-out), least-privilege publish credential, human approval
   preview before publish.

3. **Directive 050 post-exposure** (partial — one integrity rule is already pre-exposure; no
   existing directive overlaps, 050 fills a real gap). **Fix:** re-anchor the operative procedure
   on connector-side injection / pre-model redaction / least privilege (link
   `secure-design-checklist`); keep "strip from error text" as an explicit defense-in-depth
   *fallback* for third-party error strings, so the procedure agrees with its own pre-exposure
   integrity rule.

4. **Directive 049 must-vs-advisory** (reproduces — `enforcement: advisory` but "must" intent;
   only `minutes-maker-mahad` of 7 wires the declaration). **Fix (default):** narrow intent/
   validation language from "must declare / states its role" to "should open with a short
   role/scope declaration", matching the advisory field and shipped reality. (No runtime gate
   enforces self-introduction, so wiring all 7 would be aspirational; narrowing is the truthful
   minimal change.)

5. **Authority overlaps.**
   - **5a lexical-larry vs curator-carla** (real ownership collision). curator-carla owns the
     glossary (`glossary-management`, `glossary-index`, owns `glossary/**/*`). **Fix:** make
     Carla the single glossary authority and Larry the diagnostic/analyst feeder (Larry emits
     conflict/delta reports for Carla to accept; both must not claim `glossary-curator`
     ownership). The `glossary-maintenance-workflow` procedure is a well-behaved *composer* of
     existing tactics — keep it. Directive 048 vs 018: add a one-line cross-reference boundary
     (018 = version the artifact you author; 048 = read the current version of what you consume).
   - **5b diagram-daisy vs mermaid/plantuml toolguides** (embedded convention duplication).
     **Fix:** trim diagram-daisy's inline tool matrix to *reference*
     `mermaid-diagramming`/`plantuml-diagramming` toolguides + `use-c4-model-techniques`.
   - **5c Directive 047 vs writing-audience README** (direct self-contradiction: 047's
     `references` wire to `stakeholder-persona-template`/`stakeholder-alignment` that the PR's
     own audience README says must *not* be wired to the writing-audience concept). **Fix:**
     repoint 047's `references` to `writing-audience-catalog` (its own concept) and drop the two
     stakeholder references, honoring the README's boundary.

**Alternatives considered.** Deferring WS2 to a follow-up and landing WS1 only — rejected: the
routing regression (D-03) and the false attribution would ship live; a landed regression is worse
than a queued contribution (per the on-record decision).

---

## Cross-cutting: scope boundary (C-003)

The trust-boundary (blocker 2) and credential (blocker 3) work is closed **in doctrine** — the
procedure/directive *state* the requirements and the profile stops *claiming* unshipped
enforcement. Building a meeting-minutes runtime/validator/publisher, or a runtime credential
redactor, is explicitly out of scope (a separate follow-up mission if wanted). This keeps the
mission a doctrine-authoring effort sized like the rest.
