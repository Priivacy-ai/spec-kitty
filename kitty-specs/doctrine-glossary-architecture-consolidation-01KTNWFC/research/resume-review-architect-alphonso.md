# Resume Architecture Review — Architect Alphonso

**Mission:** `doctrine-glossary-architecture-consolidation-01KTNWFC`
**Reviewer:** architect-alphonso
**Date:** 2026-06-11
**Branch:** `feat/doctrine-glossary-consolidation-01KTNWFC`
**Scope:** Re-validate the mission's architecture against the significant decisions that landed while the mission was PAUSED (now upstream PR #1850), before implementation starts.

---

## 0. Method & verification

I read `spec.md` (FR-001..012, NFR, C-001..005, SC-1..7), `plan.md` (IC-01..09, structure decision), `data-model.md`, `contracts/charter-extends-and-drg-regen.md`, and skimmed every WP (WP01-06, WP08-11; **WP07 does not exist** — the tasks fan-out maps 9 ICs onto 10 WP files, skipping the WP07 number). I then verified each of the seven decisions directly in the tree rather than trusting the summary. Verification results:

| # | Decision | Verified in tree | Touches this mission? |
|---|----------|------------------|------------------------|
| 1 | Guard coherence (`core/commit_guard.evaluate`, `GuardCapability`, 5 channels deleted, ADR addendum "Step 7 delivered") | ✅ `src/specify_cli/core/commit_guard.py:132 def evaluate`; addendum present at `2026-06-03-2…md:116` ("(c) Step 7 delivered"); `GuardCapability` live across coordination/policy | Indirectly (C4 + Ops ADR content) |
| 2 | Placement / status-surface single authorities | ✅ `primary_feature_dir_for_mission`, `resolve_placement_only`, `resolve_status_surface_with_anchor` all resolve in `coordination/surface_resolver.py`, `missions/_read_path_resolver.py`, `mission_runtime/resolution.py` | Indirectly (C4 container/component) |
| 3 | DRG provenance is a declared `provenance: str \| None` field; `object.__setattr__` sidecar deleted | ✅ `src/doctrine/drg/models.py:98,126` declared field; `merge.py:197` comment "former `object.__setattr__` sidecar" | **Directly** — WP09/WP10 subject matter |
| 4 | `mission_runtime` canonical surface; `CommitTarget(ref, kind)` | ✅ `CommitTarget(ref, kind)` canonical per addendum (b); `mission_runtime` package-root import gate | Indirectly (C4 + Ops ADR) |
| 5 | Tiered coding standards (#1843, DDD core/supporting/glue) deferred | ⚠️ tickets unreadable (repo issues disabled on this fork) — taken on the summary's word; no tier-taxonomy artifact in `src/doctrine/` yet | **Directly** — doctrine artifact layout (WP04/05/10) |
| 6 | #1805 (architecture vs docs + C4) and #1839 (deterministic diagrams) overlap WP02/WP03 | ⚠️ tickets unreadable; #1805 is the *named source FR* of FR-005/006 (already folded), #1839 is net-new | **Directly** — WP02/WP03 |
| 7 | Occurrence-map reverted bulk_edit → reference-rewrite checklist (remediation O1); #1815 limitation | ✅ `occurrence_map.yaml` header records the O1 revert + "Mechanism gap filed upstream"; `meta.json` carries no `change_mode` | **Directly** — WP01/WP02 |

**Two tree facts that dominate the findings below (not in the summary):**

- **A top-level `glossary/` already exists and is already the charter authority path.** `glossary/` (+ `contexts/`, `README.md`, `historical-terms.md`, ~16 context files) was created back at **#1636** (`d6c2afa8b`), long before this mission. `.kittify/charter/governance.yaml:34` and `charter.md:316` already cite `glossary/contexts/` — **not** `architecture/glossary/`. `architecture/glossary/` is already drained to a lone `README.md`. So IC-01/WP01's "promote glossary to top-level" is **largely already done**; the residual is reconcile + content refresh, not a move.
- **Charter authority paths cite a path that ADRs do not land in.** `governance.yaml` lists `architecture/2.x/adr/` and `architecture/adrs/`, but the live ADR home is `architecture/3.x/adr/` (38 ADRs incl. the addendum). This is a real, pre-existing drift that WP02 *must* fix and the spec only half-captures.

---

## 1. Per-FR / per-WP adjudication

Classification: **HOLDS** / **NEEDS-AMENDMENT** / **SUPERSEDED** / **CONFLICTS**.

### Doctrine authoring stream (FR-001..004 → WP04/WP05)

- **FR-001 procedure / FR-002 tactics (WP04)** — **HOLDS, with a tier-taxonomy reservation.** Pure authoring into `src/doctrine/{procedures,tactics}/` (both dirs exist). No collision with decisions 1-4. See Finding F3 (#1843) for the one shape constraint to honour.
- **FR-003 styleguide / FR-004 toolguide (WP05)** — **NEEDS-AMENDMENT.** The styleguide encodes architecture conventions and the toolguide encodes gh/GraphQL mechanics. Two amendments: (a) the styleguide's "functional-epic-vs-meta-tracker" and "no ticket list in epic body" rules must be reconciled with the now-canonical tracker hierarchy (per operator memory, the #1619 tree post-2026-06-09 cleanup) so the authored doctrine matches the live tree, not the pre-cleanup state the `work/` traces captured; (b) terminology guard (C-003) bites hardest here — "Feature" as a GitHub issue-type term must be quoted/escaped so `test_no_legacy_terminology.py` passes (the spec flags this; keep it as a DoD line, not a hope).

### Architecture restructure stream (FR-005..007 → WP02/WP03/WP06)

- **FR-005 architecture-vs-docs boundary + `vision/` (WP02)** — **NEEDS-AMENDMENT (two corrections).**
  1. **Glossary promotion is mostly already done** (#1636). WP02/WP01 must be re-scoped from "move glossary to top-level" to "**reconcile the two glossary homes** (`glossary/` vs `architecture/glossary/`) into one and delete the residual `architecture/glossary/README.md` or convert it to a pointer." Otherwise the mission re-litigates a settled move and risks *re-forking* the very surface C-005 forbids.
  2. **Charter authority-path fix must target the real ADR home.** WP02 owns `.kittify/charter/**`; its DoD must update `governance.yaml` / `charter.md` to drop/repoint `architecture/2.x/adr/` + `architecture/adrs/` toward the living `architecture/` + `architecture/3.x/adr/`. The plan's Charter-Check bullet flags the self-referential update but names the wrong stale paths.
- **FR-006 C4 refresh (WP03)** — **NEEDS-AMENDMENT.** The C4 *level structure* decision (hand-authored Markdown+Mermaid, numbered 01/02/03) **HOLDS**, but the **domain model the diagrams must depict has materially changed** since the spec: the container/component model now has to render the **post-decisions-1-4 canonical surfaces** — `core.commit_guard.evaluate` as the single protected-branch decision behind the `git.commit_helpers` facade; `GuardCapability` asserted-at-surface; `mission_runtime` (`resolve_action_context`, `CommitTarget(ref,kind)`, `ProtectionState`) as the canonical runtime-context boundary; and the single placement/status authorities (`resolve_placement_only`, `resolve_status_surface_with_anchor`, `primary_feature_dir_for_mission`). WP03's "Source of truth" list cites the execution-state ADRs but **not their 2026-06-10 addendum** — add it, or the refreshed C4 will depict the superseded `(worktree_root, destination_ref)` `CommitTarget` and the retired `execution_context.py` home.
- **FR-007 Ops ADR (WP06)** — **HOLDS.** Lands in `architecture/3.x/adr/` (exists, 38 ADRs). No naming collision (no MissionStep-named ADR; MissionStep retirement was in the doctrine-service *facade contract*, not the ADR tree — see F4). The "one shared Op primitive, not two" framing is fully consistent with the decision-1/4 "single authority" through-line. One enhancement: cross-link the Ops ADR to the `2026-06-03-*` execution-state ADRs + addendum so the Op record's commit path is described in terms of the canonical `CommitTarget`/guard, not a parallel sketch.

### Charter / DRG / glossary code stream (FR-008..011 → WP08/WP09/WP10/WP01)

- **FR-008 charter `extends:` (WP08)** — **HOLDS.** Contract C1 already mandates resolution through `charter.activation_engine` (plan/commit) + `charter.cascade`, "no parallel resolver" — exactly the consolidation posture the placement/guard decisions reinforce. `src/charter/` exists. No amendment.
- **FR-009 DRG generator/freshness (WP09) + re-curation (WP10)** — **NEEDS-AMENDMENT (decision 3).** Decision 3 *already shipped* the provenance model the spec implicitly assumed was open: `DRGNode/DRGEdge.provenance: str | None` is a declared field; the `object.__setattr__` sidecar is gone. WP09/WP10 must be amended to (a) **build on the declared field, not reintroduce a sidecar**, and (b) state that the "symmetric profile-edge detection" and re-curation operate over `src/doctrine/drg/` (models/merge/loader) — the WPs' `owned_files` say `src/doctrine/drg/**` and `src/doctrine/graph.yaml`, which are correct, but the WP prose predates the provenance landing and should cite `models.py`'s declared field as the contract. Also note `specializes_from` is a **DRG edge** (per CLAUDE.md C-009), so "symmetric profile-edge detection" must treat lineage as graph edges, not per-profile fields.
- **FR-010 glossary content refresh + FR-011 scope defer (WP01)** — **HOLDS on content; NEEDS-AMENDMENT on the "promote" framing** (see FR-005.1). The content refresh and the explicit `GlossaryScope` defer are clean and unaffected by decisions 1-7. WP01's body still says "consolidate the scattered glossary locations into a top-level surface" as if from scratch — re-word to "reconcile against the already-promoted `glossary/`."

### Validation (FR-012 → WP11)

- **FR-012 #391 doctrine usage-test (WP11)** — **HOLDS.** Pure tracker dogfood; unaffected by decisions 1-7. One caution carried from operator memory: #391 sits in a tracker hierarchy that was already restructured (#391 = debt root with #1797 sanitization). WP11 must apply the **current** tree state, not the `work/`-trace snapshot, or it will reparent against a stale topology.

### Constraints / NFR / SC

- **C-005 (no parallel mechanisms)** — **STRENGTHENED, and now partially at risk from the mission itself.** Decisions 1, 2, 4 are all instances of C-005 applied to runtime (one guard authority, one placement authority, one runtime-context surface). The mission's *doctrine* leg is consistent with this. **But** the dual glossary homes (`glossary/` + `architecture/glossary/`) mean the mission must *finish* a consolidation #1636 started, and the dual ADR authority paths (`2.x/adr` + `adrs` + de-facto `3.x/adr`) mean WP02 must collapse three references to one. If WP01/WP02 execute their "move" framing literally they could *create* a second glossary home — the precise C-005 violation. Re-scope to "reconcile," not "move."
- **NFR / SC** — **HOLD.** No threshold is invalidated by decisions 1-7.

---

## 2. Specific adjudications requested

### 2a. WP02/WP03 vs #1805 and #1839 — ownership

- **#1805 (architecture vs docs restructure + C4 drilldown refresh, unparented):** **FOLD INTO MISSION — already done in substance.** #1805 is the *named source* of FR-005 and FR-006 (`spec.md:31-32`), and the operator explicitly chose "full #1805 scope" in-mission (`spec.md:80`). Recommendation: **proceed; on merge, close #1805 as delivered-by-this-mission** and add an explicit `Closes #1805` cross-reference in WP02/WP03 DoD. No carve-out needed. Risk if ignored: #1805 lingers as an orphan duplicate of work this mission ships.
- **#1839 (deterministic py2puml/mermaid diagrams, multi-level, hotspot overlay):** **CARVE OUT — keep as a ticket; do NOT fold.** This is **net-new tooling** (generated diagrams), which directly contradicts R-04's deliberate decision to **keep hand-authored Markdown+Mermaid and defer the generated-C4 swap to #1812**. #1839 is the same class of work as #1812. Recommendation: WP03 stays hand-authored; **cross-reference #1839/#1812 in the WP03/architecture README as the deferred "generated-C4" successor**, and reconcile the two tickets (#1839 likely supersedes or duplicates #1812 — flag for the operator). Folding #1839 in would reverse a ratified mission decision (R-04) mid-flight.
  - **Operator decision needed:** is #1839 the same intent as #1812 (dedup), and does the generated-C4 swap stay deferred? (My recommendation: yes, stay deferred; this mission ships the hand-authored refresh #1839 will later regenerate.)

### 2b. Must the target layout reserve room for #1843's tier taxonomy?

**Yes — and it is cheap to do.** #1843 plans a DDD-tiered rigour taxonomy (core / supporting / glue) for doctrine artifacts + CI. This mission *consolidates the doctrine architecture* (WP04/05/10 author procedure/tactic/styleguide/toolguide and re-curate the DRG). Two non-foreclosure constraints:

1. **Do not bake a flat, tier-blind artifact schema that #1843 would have to break.** The authored doctrine artifacts and the re-curated DRG should leave a **tier/criticality dimension addable as an optional field/edge** — i.e. don't assert "all doctrine artifacts are peers" in a way that a later tier attribute contradicts. The existing `provenance: str | None` optional-field pattern (decision 3) is the model to follow: add tier later as an optional declared field, never a sidecar.
2. **Keep the styleguide (WP05) silent on per-tier rigour** rather than authoring a conflicting "one rigour for all" rule that #1843 must later overturn.

This is a **reservation, not an implementation** — #1843's analysis is deferred, and FR scope here must not balloon. Recommendation: add one line to WP04/WP05/WP10 DoD: *"artifact/DRG schema additions remain tier-taxonomy-compatible (#1843): any criticality dimension is an optional declared field, not a structural assumption."*

### 2c. Do any planned moves collide with mission_runtime / -gate or the charter-facade contract tables (MissionStep retired yesterday)?

**No structural collision — confirmed by tree inspection — but two content obligations.**

- **No move collides with `mission_runtime` or the guard.** This mission moves/authors **docs and doctrine YAML**; `src/mission_runtime/**`, `src/specify_cli/core/commit_guard.py`, and the `git.commit_helpers` facade are **not in any WP's `owned_files`**. WP08 touches `src/charter/**` and WP09/10 touch `src/doctrine/drg/**` + `graph.yaml` — none overlap the runtime/guard surfaces. The package-root-only import gate for `mission_runtime` (decision 4) is not threatened.
- **MissionStep facade-contract retirement does not collide with WP06's ADR move.** `MissionStep` lives in `src/doctrine/missions/` (`models.py`, `step_contracts.py`, `mission_step_repository.py`) and the runtime schema — **not** in `architecture/3.x/adr/`. No WP renames or moves around `MissionStep`. The only obligation is **content**: the refreshed C4 (WP03) and the Ops ADR (WP06) must not depict `MissionStep` as a charter-facade contract row if it was retired from that table yesterday. **Operator/architect note:** WP03's component diagram of the doctrine/charter facade should reflect the *post-retirement* facade contract surface, not the pre-retirement one. (I could not enumerate the exact retired facade-contract table from the disabled-issues tracker; the C4 author must pull the live `src/doctrine/service.py` facade as the source of truth, per C-002.)

---

## 3. High-leverage considerations & failure modes

1. **The mission's biggest risk is re-forking a surface it means to consolidate** (C-005 self-violation). The glossary is already promoted (#1636) and the ADR home already moved to `3.x/adr/`; if WP01/WP02 run their literal "move to top-level" scripts they can create a *second* `glossary/` or leave three live ADR authority paths. **Mitigation:** re-scope WP01/WP02 to "reconcile + delete residual," and make "exactly one glossary home, exactly one ADR authority path" an explicit DoD assertion verified by `grep`.
2. **Stale source material.** WP04/WP05/WP11 author doctrine and reorganise #391 from `work/` traces captured *before* the 2026-06-09 tracker-hierarchy cleanup (operator memory). Authoring the styleguide and reparenting #391 against the pre-cleanup topology will encode drift. **Mitigation:** DoD line requiring the authored doctrine + #391 reorg to be validated against the *current* tracker tree.
3. **C4/Ops-ADR depicting superseded runtime shapes.** Decisions 1-4 all landed *after* the spec; the refreshed C4 (WP03) and Ops ADR (WP06) source-of-truth lists predate the 2026-06-10 addendum. **Mitigation:** add the addendum + `mission_runtime`/`commit_guard` modules to WP03/WP06 source lists.
4. **occurrence_map ↔ WP-body inconsistency.** `occurrence_map.yaml` (remediation O1) declares bulk_edit **reverted** to a non-gate checklist, but **WP01 and WP02 bodies still assert "This WP is bulk_edit … governed by `occurrence_map.yaml`."** An implementer following the WP body will look for a gate that the occurrence_map says isn't one. **Mitigation:** amend WP01/WP02 prose to match O1 (reference-rewrite checklist + post-move `grep`/`glossary validate`/`doctor doctrine` as the DoD-enforced integrity check), and confirm `meta.json` carries no `change_mode: bulk_edit` (verified: it does not).
5. **WP07 gap.** The fan-out has no WP07 (WP01-06, 08-11). Harmless if intentional, but confirm no IC was silently dropped — IC-01..09 map to WP01,02,03,04,05,06,08,09,10 + WP11(FR-012); that is 10 WPs for 9 ICs+FR-012, with the numbering skipping 07. Likely a renumber artifact; worth a one-line confirmation at finalize-tasks.

---

## 4. Verdict counts

- **HOLDS:** 6 (FR-001/002 WP04, FR-007 WP06, FR-008 WP08, FR-010-content/FR-011 WP01-content, FR-012 WP11, C-005-as-principle/NFR/SC)
- **NEEDS-AMENDMENT:** 5 (FR-003/004 WP05; FR-005 WP02; FR-006 WP03; FR-009 WP09/WP10; FR-010 "promote" framing WP01)
- **SUPERSEDED:** 0 (no FR is invalidated; several are *partially pre-delivered* — glossary promotion by #1636, DRG provenance by decision 3 — but the FRs' residual scope survives)
- **CONFLICTS:** 1 (potential, latent) — WP01/WP02 literal "move" framing vs C-005 / the already-promoted glossary + already-moved ADR home; resolution = re-scope to "reconcile," not "move." Plus the #1839-fold-in temptation, which would conflict with R-04 (resolve by keeping #1839 a deferred ticket).

---

## 5. Operator decisions needed (crisp)

1. **#1839 vs #1812:** Confirm #1839 (generated/deterministic diagrams) stays a **deferred** ticket (not folded into WP03), and adjudicate whether #1839 duplicates/supersedes #1812. (Architect recommendation: defer; dedup #1839↔#1812.)
2. **#1805 closure:** Confirm #1805 is closed as **delivered-by-this-mission** on merge (it is already the source FR of FR-005/006). (Recommendation: yes.)
3. **#1843 reservation:** Approve the cheap non-foreclosure DoD line (tier dimension = optional declared field, never structural) on WP04/05/10, without expanding scope to implement #1843 here. (Recommendation: yes.)
4. **Glossary re-scope:** Approve re-scoping WP01/WP02 from "promote/move glossary" to "**reconcile** the already-promoted `glossary/` and delete residual `architecture/glossary/`," to avoid a C-005 self-violation.

---

_Review complete. No files committed; this is the only new file written._
