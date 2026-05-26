# Mission Brief — Charter UX & Org-Pack Vocabulary

**Researcher:** Researcher Robbie
**Date:** 2026-05-23
**Mission:** `charter-ux-and-org-pack-vocabulary-01KSAF14`
**Parent epic:** #1111 — 3.2.0 release work: Charter / Doctrine enhancement and remediation
**Sources cited in scope:** #1099, #1100, #1101, #1104 (Slice A), #1291 (Slice F), epic body for "shipped → built-in" naming consistency call.

This brief is the code-grounded pre-research that informs the spec and plan. It is read-only investigation: no production code changed.

---

## 1. Bundled threads & scope

The architect's prior assessment proposed two separate missions; the Human-in-Charge bundled them and added a vocabulary refactor:

| Thread | Issues | Origin |
|---|---|---|
| **A. Charter freshness UX** | #1099, #1100, #1101, #1104 | Slice A of epic #1111 (P1 launch-blockers, MVP) |
| **B. Pack-authoring vocabulary (`overrides` + `enhances` as first-class fields)** | #1291 (+ closed precedents #832, #522) | Slice F of epic #1111 |
| **C. Vocabulary refactor: `shipped` → `built-in`** | epic body | HiC directive at handoff |

All three land in one mission/spec/plan because they share two cross-cutting code surfaces:
- `src/specify_cli/cli/commands/charter.py` (status + lint + synthesize commands)
- `src/doctrine/` schemas + Pydantic models + validator (pack validator, DRG resolver)

Bundling avoids two parallel missions touching `charter.py` simultaneously.

---

## 2. Code-surface map (authoritative file references)

### Thread A — charter freshness UX

| Issue | File / symbol | Today's behaviour | Gap |
|---|---|---|---|
| #1099 (lint shipped + project overlay) | `src/specify_cli/charter_lint/_drg.py::load_merged_drg` | Returns `None` when no graph file exists. | No shipped fallback; no provenance flag returned. |
| #1099 cont. | `src/specify_cli/charter_lint/engine.py::LintEngine.run` lines 102-113 | Returns `DecayReport(findings=[], drg_node_count=0)` and the CLI prints `"No decay detected"` + `"Scanned 0 nodes"`. | Cannot distinguish "graph missing" from "no findings". `DecayReport` needs a `graph_state` field (`merged` / `built_in_only` / `missing`). |
| #1099 cont. | `src/specify_cli/cli/commands/charter.py::charter_lint` lines 3215-3221 | Unconditionally prints the "No decay detected" banner. | Banner must branch on graph state. JSON output must expose `graph_state`. |
| #1100 (session-start preflight) | none — module does not exist | Charter freshness never checked at session start. | New module needed: `src/specify_cli/charter_preflight/`. Pattern exists at `src/specify_cli/core/git_preflight.py` (`run_git_preflight`, `GitPreflightResult`). |
| #1101 (status freshness reporting) | `src/specify_cli/cli/commands/charter.py::status` lines 1708-1820 (+ `_collect_synthesis_status`, `_collect_charter_sync_status`) | Reports `Generation state: PROMOTED` but does not surface (a) charter-source-modified-since-last-sync hash comparison beyond a single "STALE" check, (b) `.kittify/doctrine/graph.yaml` missing-vs-stale-vs-fresh state, (c) machine-readable freshness fields per layer. | Add a `freshness` sub-payload per layer (charter source, synced bundle, synthesized DRG) and per-state remediation hints. Detection must be hash/timestamp based, not file existence. |
| #1104 (synthesize bootstrap contract) | `src/specify_cli/cli/commands/charter.py::charter_synthesize` lines 2475-2890; `src/charter/synthesizer/project_drg.py` | Has a fresh-project minimal artifact set (line 2411) but the post-condition is informal: there is no test that asserts "after a successful synthesize on a fresh checkout, `.kittify/doctrine/graph.yaml` is either present **or** downstream commands report `built_in_only`". | Codify the post-condition as an asserted contract: synthesize must either produce `graph.yaml` or set an explicit `built_in_only` marker that downstream commands consume. |

### Thread B — `overrides` and `enhances` as first-class declarative fields

| File | Symbol | Today | Change needed |
|---|---|---|---|
| `src/doctrine/tactics/models.py` line 44 | `Tactic.model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)` | `extra="forbid"` rejects any `overrides:` or `enhances:` field. | Add `overrides: str \| None = None` and `enhances: str \| None = None` fields. Add cross-field validator: mutually exclusive. |
| `src/doctrine/schemas/tactic.schema.yaml` | top-level `properties` | No `overrides` / `enhances`. | Add both as optional `string` properties matching ID pattern. |
| `src/doctrine/schemas/styleguide.schema.yaml` | top-level | Same gap. | Same addition. |
| `src/doctrine/schemas/paradigm.schema.yaml` | top-level | Same gap. | Same addition. |
| `src/doctrine/schemas/procedure.schema.yaml` | top-level | Same gap. | Same addition. |
| `src/doctrine/schemas/agent-profile.schema.yaml` | top-level | Same gap (issue claimed it existed; it does not). | Same addition. |
| `src/doctrine/styleguides/models.py`, `paradigms/models.py`, `procedures/models.py`, `agent_profiles/profile.py` | Pydantic models | `extra="forbid"` (verify per file). | Add the two fields + cross-field validator. |
| `src/specify_cli/doctrine/pack_validator.py::_shipped_id_collision_advisories` lines 413-456 | Emits "artifact id X overrides a shipped Y" advisory whenever pack and shipped share an ID. | No way to distinguish replace from augment. | Branch on declared field: <br>• `overrides: <same-id>` declared → suppress advisory (intent is explicit replace). <br>• `enhances: <same-id>` declared → suppress advisory + reword to "augments built-in via field-merge". <br>• Neither declared but same ID → keep advisory; reword per ratified ADR `2026-05-16-1-doctrine-layer-merge-semantics.md` (field-merge is the actual behaviour, so the wording must say so, e.g. "same-ID pack artifact will field-merge into built-in (declare `enhances:` to suppress this advisory, or `overrides:` to declare full replacement)"). |
| `src/specify_cli/doctrine/pack_validator.py::validate_pack` | Validates referenced URNs against `shipped ∪ pack-artifacts`. | No validation of the new fields. | New error category: when `enhances`/`overrides` reference an ID not present in built-in of the same kind, emit a hard validation error (per #1291 acceptance criterion 3). |
| `src/doctrine/drg/org_pack_loader.py` | Bridges pack artifacts → DRG fragments. | DRG edges manually authored under `drg/fragment.yaml`. | Auto-emit `Relation.ENHANCES` and `Relation.OVERRIDES` edges from the declared fields. |
| `src/doctrine/drg/models.py::Relation` lines 46-56 | Has `REPLACES`, no `ENHANCES`, no `OVERRIDES`. | `REPLACES` is structurally close to "overrides" but vocabulary is inconsistent. | Add `ENHANCES = "enhances"` and `OVERRIDES = "overrides"` (decide: alias `OVERRIDES` to `REPLACES` for backward compatibility, or rename `REPLACES` → `OVERRIDES`). |
| `src/charter/drg.py::_warn_project_override` lines 322-336 | Warns when project layer overrides a built-in/org node. | Already converts internal provenance `"built-in"` → human-facing label `"shipped"` (a vocabulary fossil). | Drop the conversion; emit `built-in` directly. Aligns with Thread C. |
| `src/doctrine/base.py::_apply_org_overrides`, `_apply_project_overrides` | Field-level merge (ADR-ratified). | Behaviour is correct; vocabulary in comments and parameter names is `shipped`. | Vocabulary work only (Thread C). |

### Thread C — vocabulary rename `shipped` → `built-in`

| Surface | Count | Notes |
|---|---|---|
| Python files mentioning `shipped` | **63 files / ~459 lines** | Mostly comments and identifiers. Two string-literal occurrences (`src/specify_cli/cli/commands/profiles_cmd.py:56` returns `"shipped"` as a user-facing provenance value; `src/charter/drg.py:328` maps internal `"built-in"` → label `"shipped"`). |
| Test files mentioning `shipped` | **90 files** | Many are doc-comments; some assert literal `"shipped"` strings. Must be migrated together. |
| Doc / YAML files | **48 files** | docs, ADRs, schema descriptions, fixture YAML. |
| Disk directory names | 0 — **already** `built-in` | `src/doctrine/*/built-in/` directories already use the target term. The shipped name lives in code/messages/tests/docs. |

Public API impact summary:
- `charter status --json` may currently emit `"shipped"` in some sub-fields; switching to `"built-in"` is a breaking change for any external consumer that pattern-matches the string.
- `charter lint` human banner already uses `[built-in]` (`src/specify_cli/cli/commands/charter.py:3210`). The vocabulary refactor reinforces this — no banner regression.
- The `profiles_cmd.py` line is the most user-visible footgun: a profile listed via the agent-profile CLI may currently print `Source: shipped` instead of `Source: built-in`.

**Migration strategy required:** dual-write a deprecation period (emit both keys / accept both labels) **or** straight cutover with a CHANGELOG breaking-change entry. Decision belongs to the planner per the merge-semantics ADR's "operator-visible" principle; my recommendation is straight cutover with deprecation note, since the codebase is pre-3.2.0 stable and the term has not appeared in public release notes long.

---

## 3. Cross-cutting risks & dependencies

1. **Two missions already merged** in this space (`layered-doctrine-org-layer-01KRNPEE` closed #832; the ADR `2026-05-16-1-doctrine-layer-merge-semantics.md` ratified field-merge). New work must respect those constraints:
   - **Do not** change the merge semantics; only add declarative vocabulary on top.
   - Re-read the ADR before writing any merge-related code.

2. **Slice A and Slice F share `charter.py`.** Implementing them in two parallel WPs touching the same file will produce merge conflicts. The plan should sequence them on the same lane or factor `charter.py` shared work into a single early WP.

3. **`extra="forbid"` blast radius.** Adding fields to `Tactic`, `Styleguide`, `Paradigm`, `Procedure`, `AgentProfile` is non-breaking for *consumers* but every test fixture YAML that constructs these models must continue to load. Spot-check needed during planning of how many fixture YAMLs exist.

4. **Schema `additionalProperties: false`.** Both the Pydantic model and the JSON Schema enforce strictness. Both must change in lockstep.

5. **Relation enum extension is graph-public.** Any consumer (dashboard, glossary, lint) that switches on `Relation` must handle the new values. Verify dashboard `entity_pages.py` and glossary surfaces.

6. **Vocabulary rename intersects with #1102 (Slice C)** — git policy issue references doctrine artifact naming. Worth confirming with the planner whether to bundle #1102 here or defer; my recommendation is to **defer #1102** (it is doc-policy work, different reviewer expertise, and Slice C is one open issue without code dependency on this mission).

7. **Bulk-edit gate.** The `shipped → built-in` rename will trip Spec Kitty's own bulk-edit-classification gate (the skill is explicitly listed for this). The plan must produce an `occurrence_map.yaml` and classify each occurrence (rename-in-place vs. preserve-historical vs. delete) before implementation begins, otherwise the gate blocks the WP.

---

## 4. Acceptance signal — concrete tests that must exist post-mission

These are not implementation tasks; they are the tests Robbie believes will land in the WP suite.

1. **#1099 regression.** `LintEngine.run()` on a repo with no `.kittify/doctrine/graph.yaml` returns `DecayReport(graph_state="built_in_only")` and the human banner says so. JSON output includes `graph_state` field.
2. **#1100 regression.** New `charter preflight` command (or auto-runner) on a fresh checkout with a charter but no synthesized doctrine produces a deterministic JSON payload with `result="degraded"` and a non-empty `remediation` array.
3. **#1101 regression.** `charter status --json` payload contains separate freshness booleans for `charter_source`, `synced_bundle`, and `synthesized_drg`, each with a `state` field and a `remediation` field.
4. **#1104 regression.** Synthesize on a fresh checkout either produces `.kittify/doctrine/graph.yaml` **or** writes an explicit marker (e.g. `built_in_only: true` in `synthesis-manifest.yaml`) that downstream commands honour.
5. **#1291 regression — schema.** Loading a pack tactic with `enhances: <built-in-id>` succeeds. Loading with `enhances: <unknown-id>` fails with a named error. Loading with both `enhances:` and `overrides:` fails with a mutually-exclusive error.
6. **#1291 regression — validator.** `pack validate` on a same-ID pack tactic without `enhances`/`overrides` still emits an advisory. With `enhances` declared → advisory suppressed. With `overrides` declared → advisory suppressed.
7. **#1291 regression — DRG.** Pack validation produces a DRG fragment with `Relation.ENHANCES` (or `OVERRIDES`) edges automatically without `drg/fragment.yaml` hand-authoring.
8. **Thread C regression.** Architectural test that asserts the public CLI surfaces (`charter status --json`, `charter lint --json`, `agent profile list`) emit `"built-in"` and never `"shipped"`. Existing tests asserting `"shipped"` are migrated.

---

## 5. Hand-off recommendations to the planner

1. **Sequence in three waves.** Wave 1: shared `charter.py` instrumentation (status freshness payload + `graph_state` plumbing). Wave 2: Thread A user-facing commands (preflight + synthesize contract). Wave 3: Thread B schema + validator + DRG. Wave 4: Thread C vocabulary cutover (last, because it touches the broadest surface; do it after the code is otherwise stable).
2. **Bundle the occurrence-map work into a first-up WP.** Thread C cannot start without the classification document.
3. **One ADR per thread, not one umbrella.** `2026-MM-DD-X-charter-freshness-ux-contract.md`, `2026-MM-DD-Y-pack-augmentation-vocabulary.md`, and a short follow-up to `2026-05-16-1-doctrine-layer-merge-semantics.md` documenting the vocabulary cutover.
4. **Defer #1102 (git policy) and #682 (composable workflows)** out of this mission — they are independent enough to merit separate spec slices.
5. **Tracker housekeeping (DIR-012):** assign issues #1099, #1100, #1101, #1104, #1291 to the HiC at the moment implementation begins, per the charter directive.

---

## 6. Open questions for the architect's review

These are decisions Robbie does not own. Flagged so Alphonso can resolve during plan review.

1. **`overrides` vs. `REPLACES` enum naming.** Add new `Relation.OVERRIDES` (and alias `REPLACES`) or rename `REPLACES → OVERRIDES` outright? Either way, glossary entry needed.
2. **Field name: `enhances` or `augments`?** The issue text in #1291 uses `enhances`. The HiC said `augments`. The pack-author audience may have a preference. Recommend Alphonso decide via DIR-032 (conceptual alignment).
3. **Deprecation of `shipped` string in public JSON.** Straight cutover or dual-emit during a deprecation period?
4. **Scope of session-start preflight.** Run on every governed command, or only on a subset (e.g. `next`, `implement`, dashboard launch)?

---

End of brief. This document is read-only research — no production code was modified in producing it.
