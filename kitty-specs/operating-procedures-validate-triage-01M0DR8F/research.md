# Research: Operating-Procedures Validate, Triage, Data-Drive

**Date**: 2026-08-19 · **Mission**: operating-procedures-validate-triage-01M0DR8F

## Census (ground truth, upstream/main @ `1f89ac01f`)

Measured by parsing `packs/built-in/agent_profiles/*.agent.yaml` and resolving each
`collaboration.operating-procedures` entry against the built-in node universe:

| Bucket | Count | Meaning |
|--------|-------|---------|
| Real procedure | 6 | resolves to a `procedure:` node |
| Wrong-kind | 8 | resolves to a real node of the wrong kind (every one a `tactic:`) |
| Fictional | 36 | resolves to no node at all |
| **Total** | **50** | across 16 profiles |

Shipped-graph baseline (from `extract_artifact_edges(packs/built-in)`):
`agent_profile → procedure` edges today = **4** (`doctrine-daphne→onboard-external-agent-to-pack`,
`researcher-robbie→spike-timebox-policy`, `lexical-larry→glossary-maintenance-workflow`,
`minutes-maker-mahad→meeting-minutes-pipeline`). Of these, only the first two are
operating-procedures-sourced; larry/mahad are prose-sourced (their profiles carry **no**
`operating-procedures` field). RECONCILE inbound edges today = **2** (DIRECTIVE_024, DIRECTIVE_025).

## Seam map (from code investigation)

| Concern | Seam | Notes |
|---------|------|-------|
| Op-proc field | `doctrine/agent_profiles/profile.py:161` `CollaborationContract.operating_procedures: list[str]` | schema-validated shape only; values unchecked |
| Profile load | `doctrine/agent_profiles/repository.py` `AgentProfileRepository.list_all()`, `.skipped_profiles()` | fail-soft; DRG available via `self._drg` |
| Load diagnostics | `doctrine/agent_profiles/diagnostics.py` `SkippedProfile` | precedent for a structured diagnostic |
| Extractor | `doctrine/drg/migration/extractor.py:624` `extract_artifact_edges` (`# noqa: C901`) | agent-profile block (826–870) reads only `context-sources.directives` + `tactic-references`; procedure nodes minted at 797–819; curated hand-pins at 264 (`_CURATED_ARTIFACT_EDGES`), op-proc pins = edges 5 (`researcher-robbie`) + the WP09 daphne pin |
| Validation | `doctrine/drg/validator.py:360` `assert_valid` | dangling refs, dup triples, requires-cycles, profile-edge symmetry, rejects/anti_pattern |
| Procedure node set | `{n.urn for n in graph.nodes if n.kind is NodeKind.PROCEDURE}` | no dedicated helper; kind = `NodeKind.PROCEDURE`; urn via `artifact_to_urn("procedure", id)` |
| Doctor surface | `specify_cli/cli/commands/_doctrine_collect.py:197` `_collect_profile_health`; mutate-report seam `_run_cross_grain_check` (376) | append to `report.org_drg["errors"]` to flip `healthy` false + structured finding key |
| Graph regen | `spec-kitty doctrine regenerate-graph [--check]` (`specify_cli/cli/commands/doctrine.py:211`) | NOT `spec-kitty regen`; `--check` byte-compares |
| Freshness golden | `tests/architectural/test_doctrine_regenerate_graph_roundtrip.py` | hard-fails if committed graph stale |
| Count pins | `tests/doctrine/drg/migration/test_extractor_projection.py` | pins node/edge/orphan counts — must update for the +10 delta |
| Gate archetype | `tests/architectural/test_no_authored_applies_edge.py` | the "no authored X edge" / empty-set gate to mirror |

**Chosen validator seam.** A pure function `resolve_operating_procedures(profiles, procedure_urns) -> list[UnresolvedOpProc]` in a new module `doctrine/agent_profiles/operating_procedures.py`. It is imported by (a) the extractor/graph build (both under `doctrine/`), (b) the `doctor` collector (`specify_cli` importing `doctrine` is allowed — the forbidden direction is `charter → specify_cli`). This keeps a single authority for "does an op-proc entry resolve to a real procedure node".

## Decisions

### Decision 1 — Wire, do not deprecate
`operating-procedures` becomes a first-class **data-driven** edge source. **Rationale**: #3352 is
"data-drive those edges"; 6 refs are legitimately authored and deprecation would strand them.
The dead-entry diagnostic ships regardless. **Alternatives rejected**: deprecate/rename the field
(loses authored intent, still needs the diagnostic, larger blast radius).

### Decision 2 — Validator contract is procedure-kind
An entry must resolve to a real **procedure** node (not merely any node). **Rationale**: the field is
`operating-procedures`; making it procedure-kind converts BOTH the 36 fictional and the 8 wrong-kind
(44) to loud failures. A weaker "any node" contract would pass the 8 at load and let the emission
guard silently drop them — reintroducing exactly the silent-drop this program kills (fail-loud thesis,
#3410). **Alternatives rejected**: "any real node" (leaves the 8 silently dropped downstream).

### Decision 3 — Loud via (a) empty-set gate test, (b) doctor diagnostic, (c) build raise
- (a) `tests/architectural/test_operating_procedures_resolve.py` asserts the built-in unresolved set is ∅ — the WP09 archetype (RED at 44 pre-triage, GREEN post-triage). This is WP01's ATDD artifact.
- (b) `doctor doctrine --json` reports the unresolved set (soft, discoverable).
- (c) `extract_artifact_edges` raises on any unresolved **built-in** op-proc entry (fail-closed) — added in WP02, after triage makes built-in clean, so the build stays green. Org/project tiers are not hard-failed (C-006); their emission is guarded instead.

### Decision 4 — Data-drive, guarded to procedure-kind
The extractor emits `agent_profile --requires--> procedure` for each op-proc entry whose target resolves
to an existing procedure node; non-procedure/absent targets emit nothing (guard). Retire the two
op-proc-sourced hand-pins (`researcher-robbie→spike-timebox-policy`, `doctrine-daphne→onboard-external-agent-to-pack`);
keep the two prose-sourced pins (`lexical-larry`, `minutes-maker-mahad`).

### Decision 5 — RECONCILE third trigger edge
Add `tactic:change-apply-smallest-viable-diff --suggests--> directive:RECONCILE_CHANGE_SCOPE_TENSIONS`.
The reconciler's `scope:` names three triggers; the first two have inbound `suggests` edges, the tactic
one is unwired. Target is a real tactic node; relation matches the two existing edges.

## Triage disposition table (all 44 non-resolving entries)

**Legend**: KEEP = real, becomes data-driven; MIGRATE = move wrong-kind tactic to `tactic-references`;
DELETE-redundant = wrong-kind tactic already in `tactic-references`, drop the op-proc entry;
DELETE = fictional, no real target (repoint = doctrine authoring, out of scope C-007).

### 6 REAL → KEEP (data-driven procedure edges; ⚡ = net-new emission, 📌 = was hand-pinned)
| Profile | Entry | Disposition |
|---------|-------|-------------|
| architect-alphonso | drill-down-documentation | KEEP ⚡ |
| doctrine-daphne | onboard-external-agent-to-pack | KEEP 📌 (retire pin) |
| java-jenny | test-first-bug-fixing | KEEP ⚡ |
| planner-priti | adversarial-squad-deployment | KEEP ⚡ |
| researcher-robbie | spike-timebox-policy | KEEP 📌 (retire pin) |
| reviewer-renata | adversarial-squad-deployment | KEEP ⚡ |

### 8 WRONG-KIND (all tactics)
| Profile | Entry (tactic) | Disposition |
|---------|-------|-------------|
| frontend-freddy | tdd-red-green-refactor | MIGRATE → tactic-references |
| frontend-freddy | bug-fixing-checklist | DELETE-redundant (already in tactic-references) |
| java-jenny | acceptance-test-first | MIGRATE → tactic-references |
| java-jenny | tdd-red-green-refactor | MIGRATE → tactic-references |
| node-norris | tdd-red-green-refactor | MIGRATE → tactic-references |
| node-norris | bug-fixing-checklist | DELETE-redundant (already in tactic-references) |
| python-pedro | tdd-red-green-refactor | MIGRATE → tactic-references |
| reviewer-renata | reverse-speccing | DELETE-redundant (already in tactic-references + context-sources) |

### 36 FICTIONAL → DELETE
architect-alphonso: architecture-review-checklist, adr-template ·
curator-carla: glossary-review-process, doctrine-update-workflow ·
debugger-debbie: five-paradigm-dispatch, convergence-synthesis, dormant-mask-enumeration ·
designer-dagmar: design-review-checklist, accessibility-audit-process ·
frontend-freddy: self-review-quality-gate, code-review-checklist, test-coverage-requirement ·
implementer-ivan: code-review-checklist, test-coverage-requirement ·
java-jenny: self-review-quality-gate, code-review-checklist, test-coverage-requirement ·
node-norris: self-review-quality-gate, code-review-checklist, test-coverage-requirement ·
paula-patterns: architecture-scout-dispatch, release-vs-long-term-synthesis, boundary-ownership-triage ·
planner-priti: dependency-validation-process, capacity-estimation-guide ·
python-pedro: self-review-quality-gate, code-review-checklist, test-coverage-requirement ·
randy-reducer: semantic-compression-workflow, behavior-preserving-refactor, equivalence-verification ·
researcher-robbie: research-template ·
retrospective-facilitator: retrospective-facilitation-protocol ·
reviewer-renata: code-review-checklist, security-review-process, language-driven-design-review

**Repoint candidates considered and rejected** (kept as DELETE to stay in scope): `curator-carla:glossary-review-process`
→ `glossary-maintenance-workflow`, and `debugger-debbie`'s three → `disciplined-defect-diagnosis`. Both are
*plausible* enrichments but repointing a fictional name to an existing procedure is a doctrine-semantics
authoring call (new reachability, moves golden counts), which C-007 defers. The triage WP reviewer may
elect to adopt either repoint; the default is DELETE. If adopted, it is accounted in the graph-delta review.

## Graph delta (NFR-002 accounting)

| Change | Edges |
|--------|-------|
| Net-new real op-proc → procedure (architect, java-jenny, planner, reviewer) | +4 |
| Retire 2 op-proc hand-pins, re-derive same 2 edges | 0 (net) |
| Keep 2 prose hand-pins | 0 |
| Migrate 5 wrong-kind tactics → tactic-references (agent_profile→tactic requires) | +5 |
| RECONCILE third trigger edge (tactic→directive suggests) | +1 |
| **Net** | **+10 edges** |

Target nodes all pre-exist (real procedures/tactics/directive) → **0 new nodes**. Zero dangling edges
(guard + triage guarantee resolvability). `test_extractor_projection.py` pinned counts and the
`regenerate-graph --check` golden are updated to the new correct values with this table as the rationale.

## Supply-chain / adversarial evidence

**No dependency added, upgraded, or removed.** The supply-chain planning check (DIRECTIVE_051) is
therefore N/A for this mission — no registry/lifecycle-script/LTS surface to examine. An adversarial
review pass runs at the post-tasks point-cut and pre-merge (charter standing order #1); contested
findings are dispositioned in the mission's squad-findings artifact, not here.
