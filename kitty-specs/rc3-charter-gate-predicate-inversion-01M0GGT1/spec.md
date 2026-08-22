# Mission Specification: M3 — Gate on the declared entity, not a coarse set

**Status**: Finalized (specify-phase; forks locked; deep design deferred to WP01 ADR at plan)
**Created**: 2026-08-20 · **Re-verified & finalized**: 2026-08-21 (against current `main`, post-M0)
**Author**: analyst-annie · **Finalized by**: planner-priti (M3 re-grounding pass)
**Target branch**: `main` · **Milestone / rc target**: 3.2.x
**Scope (operator-EXPANDED)**: #3596 + #3598 + `_KNOWN_ACTIONS` fold + #3599 + #3597 + #3407 — one ADR shape.
**Separate missions (reference only, do NOT fold)**: M5 (`rc3-canonical-mission-type-reader`) reader convergence; M4 (`rc3-operator-signal-fail-loud`) manifest fail-loud.

> **Source provenance.** Grounded in `docs/plans/investigations/friction-bugs-processing-charter-root-cause.md` (§2.2/§2.3/§10) and sequenced by `docs/plans/initiatives/rc3-friction-burndown/rc3-friction-burndown-approach.md`. **Re-verified line-level against current `main` on 2026-08-21** (three independent code-truth passes). All drift from the pre-M0 baseline is recorded in the **Respec vs pre-M0 baseline** section below.

---

## Program status (re-verified 2026-08-21)

- **M0 (`mission_type` backfill) — LANDED on `main`** (`migrate backfill-mission-type` + `doctor mission-type --fail-on <states>` fail-closed census gate; commits `c316bd5ae`, `a2b1a9879`, #3614). The #3598 typo/typeless hard-fail (FR-005/006) is therefore **safe to ship** — the census gate already surfaces `unknown`/`typeless` mission types across real projects. *(Was: "M0 must land first." Now: M0 landed.)*
- **C-003 preconditions satisfied**: #3386 (family dispatch correctness) CLOSED; #3388 (`expected-artifacts.yaml` reconciled) CLOSED.
- **M5 interlock already satisfied on `main`** (see Respec §I). **M4 same-file coordination** on `src/doctrine/missions/repository.py` still pending (M4 not landed) — per-symbol ownership at plan.

---

## Problem & impact (BLUF)

One theme, five surfaces: charter/runtime code decides delivery, tolerance, and gating by testing membership in a **coarse hardcoded set** instead of the **entity actually declared**. Each silently starves shipped configuration or fails open. Verified on current `main`:

1. **#3596 — action gate.** `BOOTSTRAP_ACTIONS = frozenset({"specify","plan","implement","review"})` (`src/charter/context.py:115`) short-circuits any other action to `mode=compact` before a bundle is built (plain-text gate `context.py:255`; `--json` gate `context.py:484` — both gate on membership before `_resolve_action_bundle` at `:272`/`:503`). `packs/built-in/missions/software-dev/actions/tasks/index.yaml` (13 lines) and `packs/built-in/missions/documentation/actions/retrospect/index.yaml` (16 lines) carry non-empty grain that delivers **nothing**. The DRG traversal that would honour a declared `action:<type>/<step>` node already works; only the gate is wrong.
2. **#3598 — governance-slot probe.** `_resolve_governance_slot` (`mission_type_profiles.py:766`) tolerates an unregistered type whenever `_project_has_doctrine_overrides(repo_root)` is `True` (`:1235`, evaluated once in `resolve_mission_type_context:635`) — a **project-wide** probe that is `True` for nearly every charter-bearing project. A typo'd type (`softwaer-dev`) then resolves **silently** with a fabricated `provenance` (`repo.get_provenance(mission_type) or "project"`), **no warning**. *(Return-shape note: `_resolve_governance_slot` returns `(provenance, governance_text, governance_thunk)`; the empty `action_sequence`/`None` `template_set` are assembled one level up in `resolve_mission_type_context` at `:659`/`:676`.)*
3. **`_KNOWN_ACTIONS`** (`charter/interview.py:34`) — third copy of the same 4-token frozenset; warn-drops (`unknown action '…' … treating as global`, `:104-113`, sets `action=None` but keeps the declaration) any `local_supporting_files` `action:` outside the four, even actions about to start delivering.
4. **#3599/#3597 — artifact seam.** Artifact filenames are hardcoded literals at the gates while four per-type manifests ship and gate nothing. `_HASH_INPUTS = ("spec.md","plan.md","tasks.md")` (`src/specify_cli/analysis_report.py:33`); `_PRESENCE_FILE_TAGS` is a **closed 10-member tuple** (`src/runtime/next/runtime_bridge_io.py:841` — `spec.md, plan.md, tasks.md, source-register.csv, findings.md, report.md, gap-analysis.md, audit-report.md, release.md, research.md`); the v1 guard registry (`mission_v1/guards.py` `GUARD_REGISTRY:270`/`compile_guards:329`) is **dead in production** (verified — zero `src/` callers outside tests; the live FSM `mission-runtime.yaml` has no guard fields; the live runtime carries its own `artifact_exists` at `engine.py:1445`), so no per-type artifact gate executes; a custom type's report phase advances with no artifact evidence. `core/worktree.py:595-610` `spec_file.touch()`es a stray empty `spec.md` that satisfies every existence gate and nothing reads.
5. **#3407 — CLI guard.** `_check_cli_guards` (`runtime_bridge.py:785`) hardcodes `mission_family="software-dev"` (`:796-798`) for **every** mission type when it calls `gather_artifact_presence`, routing the CLI-guard path **around** the per-type `_GUARD_TABLES`. Latent today (`plan`'s `review` step lexically collides with software-dev's `review` and reaches `_evaluate_wp_iteration_guard`, currently returning `[]` only because `_should_advance_wp_step` defaults `True` when no `tasks/` dir exists) but a real, reachable, mission-blind branch and a spurious-block risk. **Note (respec):** the per-type `plan` guard table already exists (`_evaluate_plan_guards` in `_GUARD_TABLES["plan"]`, `runtime_bridge_cores.py:680`); the defect is purely that the hardcode at `:797` bypasses it.

**Impact**: non-canonical actions/types get no action-scoped doctrine; typo'd types fail open with fabricated provenance; custom mission types cannot declare or gate on their own artifact filenames; a `plan` mission's `review` step can silently alias into a WP-iteration guard it has no domain relation to.

**Fix shape (the single ADR)**: at each surface, replace the coarse-set membership test with a predicate on the actually-declared entity — DRG node-membership (#3596), per-type profile existence+id-match (#3598), per-type artifact-name source (#3599), per-type presence/guard routing keyed on mission type (#3597/#3407), the resolved mission family (#3407) — and unify the 4-token literal to one canonical source. Defaults preserve today's values for the four built-ins where a value exists; the two intended behaviour changes are recorded in one policy-reversal ADR.

---

## In scope

**A. Action gate (#3596 + `_KNOWN_ACTIONS`)**
- Replace both `context.py` gate sites so an action carries a doctrine grain **iff** the merged DRG (`bundle.merged`) declares its node. Resolve the bundle first, then gate. Keep the 4-token fast path (NFR-001). Resolve the type via the already-landed `resolve_mission_type_key` (routes through `canonical_mission_type_key`; **no new hard-fail** — see Respec §I). Typeless stays `compact`. Thread the already-loaded graph (no double load; ~100 ms budget). Document the pack-root `action.graph.yaml`/`mission_type.graph.yaml` `action:<type>/<step>` carrier as sanctioned.
- Fold `_KNOWN_ACTIONS` (`interview.py:34`) into one canonical vocabulary; interview validation consults it and accepts declared action nodes.

**B. Governance-slot probe (#3598)**
- Replace the project-wide `_project_has_doctrine_overrides` tolerance gate with a **layered per-type** probe: tolerate an unregistered type **iff** a per-type `governance-profile.yaml` exists **and its `id` matches the type** at **any** layer — project (`.kittify/doctrine/mission_types/<type>/`), org, **or** built-in. Reuse `MissionTypeProfileRepository` (already resolves + id-matches across layers via `_GOVERNANCE_PROFILE_GLOB`); do not add a second merge/probe site.

**C. Artifact-name + gate seam (#3599, #3597)**
- Build `artifact_kind → filename` from the single per-type authority **`expected-artifacts.yaml` `path_pattern`** (loaded via `src/doctrine/missions/repository.py`): relocate `ExpectedArtifactManifest` from `src/specify_cli/dossier/manifest.py:168` into `src/doctrine/missions/` (C-001); add `project_artifact_name_set` beside `project_template_set` (`src/doctrine/missions/step_projection.py:100`); two charter bundle slots on the existing thunk; `resolve_configured_artifact_name` + `required_artifacts_for(step)` in `src/specify_cli/runtime/resolver.py`. Do **NOT** add `artifact_file` to `MissionStepTemplateRef` (`models.py:90`) — `path_pattern` is the sole filename authority (10/10 tags, all 4 types); `MissionStepTemplateRef`/`resolve_configured_template` (`resolver.py:414`) stay TEMPLATE-only (see Respec §III + squad §S2).
- Make per-type artifact gating live: a per-type source for `_PRESENCE_FILE_TAGS` (all **10** current filenames preserved for built-ins) and the family guard routing keyed on mission type; defaults preserving today's values for the four built-ins.
- Convert only these call sites: `analysis_report._HASH_INPUTS`; the accept triple; the retrospective precondition; `validate_feature_structure` (`core/worktree.py:704`); the `_PRESENCE_FILE_TAGS` contents.
- **Delete** `worktree.py`'s stray-`spec.md` creation (`:595-610`).
- Surface the two second-order blockers hit by any real third artifact kind: `_substantive.py`'s `Kind = Literal["spec","plan"]` (`src/specify_cli/missions/_substantive.py:25`, raises at `:281`), and `_ARTIFACT_TYPE_TO_KIND` (`mission_feature_resolution.py:47`, `KeyError` "no silent default" at `:62-66`).

**D. CLI guard family (#3407)**
- Resolve the mission's actual type before dispatching guard evaluation in `_check_cli_guards` (`runtime_bridge.py:785`; replace the hardcoded `mission_family="software-dev"` at `:796-798`) so the CLI-guard path reaches `_GUARD_TABLES[<actual family>]` — **including the already-existing `plan` branch** (`_evaluate_plan_guards`, `runtime_bridge_cores.py:680`). Do **not** duplicate the plan table; route to it.

**E. Governance**
- One policy-reversal ADR for both intended behaviour changes (§B typo hard-fails; §A tasks/retrospect now deliver). Name every red-by-design test in the ACs.

## Out of scope

- **M5 (`rc3-canonical-mission-type-reader`)** — full reader convergence + legacy-`mission` retirement + silent-`software-dev` removal + the `read_mission_type(meta)` dict helper. Reference only; do NOT fold. M3 consumes the already-landed `canonical_mission_type_key` primitive (Respec §I).
- **M4 (`rc3-operator-signal-fail-loud`)** — the malformed-manifest fail-loud at `src/doctrine/missions/repository.py:316-317` (#3412). M3 owns the relocation + name seam in the same file; M4 owns the except-clause. Per-symbol ownership at plan.
- Adding `actions` to `_ORG_DRG_KIND_ALIASES` (diagnostics-only loader) — record as rejected.
- Opening `ALLOWED_MISSION_TYPES` / `REGISTERED_TRIGGERS` / the activation-registry fetch-command route — leave closed, record decision.
- **Full census conversion** of artifact-name literals (~100 sites across 20 packages) — rejected; convert only the named call sites.
- `_MISSION_FILE_KIND_BY_BASENAME` (`mission_runtime/artifacts.py`) — placement seam; a `None` classification correctly routes PRIMARY for custom-type artifacts, so no entry needed.
- The frozen migrations.

---

## Respec vs pre-M0 baseline (evidence-backed change log)

Every change from the pre-M0 LIGHT spec, with the code-truth that motivates it. Verdicts are from three independent re-verification passes on `main` (2026-08-21).

**§I — M5 interlock: already satisfied on `main` (was "reconcile at plan; route through M5's `read_mission_type()`").**
- The named symbol **`read_mission_type()` does not exist** anywhere in the tree. M5's *dict* reader and full convergence are NOT landed; only the pure string canonicalizer `canonical_mission_type_key(raw: str|None) -> str|None` (`src/charter/mission_type_key.py:24`) shipped.
- `resolve_mission_type_key` (`mission_type_profiles.py:688`) → `_resolve_type_key` (`:733`) → `canonical_mission_type_key`. **No parallel legacy path, no legacy `mission` field, no `software-dev` default; typeless → `None`.**
- The delivery path never resolves the type itself: `context.py` threads the `mission_type` param → `action_doctrine_bundle.py:172` calls `resolve_mission_type_key` → `None` → empty bundle, **never raises `UnknownMissionTypeError`** (that hard-fail lives only on the governance surface).
- **Change:** NFR-002 reframed from "introduces no new hard-fail" to "**preserves** the already-safe `None`-degrading delivery path; does not re-introduce a parallel legacy-honoring reader." The M3↔M5 coordination note becomes: M3 consumes the landed `canonical_mission_type_key`; when M5 lands `read_mission_type(meta)`, `resolve_mission_type_key` can delegate to it (forward-compatible, canonical-field-only). No blocking dependency.

**§II — FR-014 (#3407): the `plan` guard branch already exists (was "add a dedicated `plan`-family guard branch").**
- `_evaluate_plan_guards` (review → `return []`) is already registered in `_GUARD_TABLES["plan"]` (`runtime_bridge_cores.py:680`), reachable only via `evaluate_guards_strict(mission_family=<mission>)`.
- The CLI path hardcodes `mission_family="software-dev"` at `runtime_bridge.py:797`, routing **around** that table, so the alias persists.
- **Change:** FR-014's remaining work is *only* resolving the actual family at `:797` so the CLI path reaches the existing plan table. Do not create a plan branch. AC-13 unchanged in intent; its mechanism is "route to the existing table."

**§III — Artifact-FILENAME source: `expected-artifacts.yaml` `path_pattern` (CORRECTED TWICE — see POST-SPEC squad §S2).**
- My first respec claimed "`step.yaml` does not exist" (from a src/-scoped verification miss). **The POST-SPEC squad source-adjudicated this false:** 30 `step.yaml` files exist at `packs/built-in/missions/mission-steps/<type>/<step>/step.yaml`, each carrying the `template:` block (`artifact_key: spec`, `template_file: spec-template.md`) — the `MissionStepTemplateRef` TEMPLATE name, **distinct from the artifact filename**.
- The artifact FILENAME for all 10 `_PRESENCE_FILE_TAGS` (incl. the 8 non-template outputs) is authored in `expected-artifacts.yaml` `path_pattern` (verified: `research/expected-artifacts.yaml` → `path_pattern: "source-register.csv"`, `"findings.md"`, `"report.md"`, `"spec.md"`, …). **`path_pattern` IS the filename** — a single per-type authority covering 10/10 tags across all 4 types.
- **Change (fork e RE-LOCKED):** filename authority = `expected-artifacts.yaml` `path_pattern` (per-type), loaded via `src/doctrine/missions/repository.py`. Do **NOT** add `artifact_file` to `MissionStepTemplateRef` (dual-authority whack-a-field, the KDD-1 anti-pattern). `MissionStepTemplateRef`/`resolve_configured_template` stays TEMPLATE-only. Code-layer (`src/doctrine/missions/`, `src/specify_cli/runtime/resolver.py`) vs pack-layer (`packs/built-in/missions/`) named distinctly.

**§IV — `ExpectedArtifactManifest` relocation still required.** Still at `src/specify_cli/dossier/manifest.py:168`; the C-001 relocation into `src/doctrine/missions/` is real work, not already done.

**§V — `_PRESENCE_FILE_TAGS` is a 10-member tuple, not 3.** FR-011 scope: the per-type conversion must preserve all 10 built-in filenames (NFR-003) while letting a custom type gate on a name outside them. AC-9 lists the 10, not the triple.

**§VI — Path drift (pack vs code layer).** Per-type manifests (`actions/<step>/index.yaml`, `expected-artifacts.yaml`, `*.step-contract.yaml`) live under `packs/built-in/missions/`, not `src/doctrine/missions/` (which holds Python modules). Line counts (tasks 13, retrospect 16) confirmed. FR-015 carrier = `packs/built-in/action.graph.yaml` (nodes) + `mission_type.graph.yaml` (edges).

**§VII — Minor line drift.** `worktree.py` stray-`spec.md` block is `595-610` (touch at `:610`), not `596-609`. `_HASH_INPUTS` full path `src/specify_cli/analysis_report.py:33`. `_PRESENCE_FILE_TAGS` full path `src/runtime/next/runtime_bridge_io.py:841`. All other cited lines (context.py 115/255/484, interview.py 34, mission_type_profiles.py 766/1235/688, worktree.py 704, runtime_bridge.py 785, _substantive.py 25, mission_feature_resolution.py 47) **match exactly**.

**§VIII — Forks locked** (see Key design decisions): (d) per-type DATA source, not revive-v1 (mission_v1 confirmed dead); (e) FILENAME source = `expected-artifacts.yaml` `path_pattern` (single per-type authority, 10/10 tags — RE-LOCKED by POST-SPEC squad §S2; NOT `MissionStepTemplateRef`); (f) pin-and-defer third-kind.

**No FR is fully mooted by M0/M5.** §I/§II reduce FR-002/FR-014/NFR-002 to *preserve-and-route* rather than *build-new*, but each still requires a diff and a red-first test. Recorded, not dropped.

---

## POST-SPEC squad revisions (2026-08-21) — convergent findings folded

A bounded 4-lens profile-loaded read-only squad (paula-patterns/seams, debugger-debbie/live-evidence, reviewer-renata/anti-laziness, doctrine-daphne/DRG) reviewed the finalized spec. Convergent findings that survived independent scrutiny (full detail: `tracer-squad-findings.md`):

- **§S1 (BLOCKER, daphne+debugger converge) — FR-001 predicate + NFR-001 test.** `resolve_context` already degrades an undeclared node to empty grain, and node URNs are activation-filter-exempt while their `scope`-edge targets are not — so the predicate MUST be `f"action:{type}/{action}" in bundle.merged.node_urns()` (node-URN membership), NOT empty-grain. A declared-but-activation-starved node → `bootstrap` + empty is legitimate; document it. The cited `test_charter_import_time_io.py` canNOT observe a runtime double-load — NFR-001 needs a NEW load-count test. → FR-001, NFR-001 rewritten.
- **§S2 (BLOCKER, paula, source-adjudicated) — fork (e) reversed.** Filename authority = `expected-artifacts.yaml` `path_pattern` (single per-type, 10/10 tags), NOT `MissionStepTemplateRef.artifact_file` (dual-authority). `step.yaml` exists but carries the template ref only. → §III, FR-009, KDD-5, fork (e) rewritten.
- **§S3 (MAJOR, renata+debugger) — fakeable ACs hardened.** AC-9 gets a load-bearing "patching path_pattern changes output" assertion; AC-10 asserts fail-closed **both** directions via the named `gather_artifact_presence` entry point; AC-2 gets a node-membership companion. → ACs rewritten.
- **§S4 (MAJOR, renata+debugger) — red-by-design enumeration + labels.** Added `test_context_schema_version_ledger.py:104` (AC-3) and `test_worktree.py:263` (AC-11) to FR-016; labeled AC-9/12/14/2 as GREEN characterization pins and AC-13 as a latent-defect pin with an explicit hand-built harness; noted the AC-6 patch-target vanishes. → ACs, FR-016 updated.
- **§S5 (MAJOR, daphne) — FR-015 carrier.** Grain is delivered by direct `action:<type>/<step>` URN construction + the node's `scope` edges; the `mission_type→action` edge is not load-bearing (the 3 retrospect nodes are sequence-orphans yet deliver). → FR-015 rewritten.
- **§S6 (MINOR, daphne) — FR-007/FR-008.** Keep the fold but name the constant for its fast-path role; the interview consults it **plus** a declared-node source (two inputs), so the fast-path set never becomes the closed acceptance allowlist. → FR-007 updated.
- **§S7 (MINOR, renata) — FR-012 scope** narrowed to the `else: spec_file.touch()` branch (~609-610), not the whole 595-610 block. → FR-012 updated.
- **§S8 (MINOR, paula) — C-001 relocation verified clean** (`src/doctrine/missions/` imports neither charter nor specify_cli; layer tests stay green; accepted mypy-strict typing cost on the `Mapping[str, Any]` charter slot). "Same-file M4 coordination" corrected: the relocation is `models.py`; M4 owns `repository.py:316 get_action_index`; M3's `repository.py` touch (if any) is near `get_expected_artifacts:362` — different symbol. Pin M3's exact `repository.py` touch at plan.

**Items pushed to the WP01 ADR (plan phase):** the interview validation mechanism (static label-union vs loaded action nodes, §S6); custom-family gate decision (`_GUARD_TABLES` registration vs strict-raise, AC-10); `load_validated_graph` memoization confirmation (§S1); exhaustive per-type `path_pattern` coverage audit for all 10 tags (§S2); the retrospect-node sequence-orphan decision (§S5).

---

## Functional Requirements

| ID | Title | Requirement | Priority | Status |
|----|-------|-------------|----------|--------|
| FR-001 | Node-membership action gate | Both `context.py` gate sites (`:255`, `:484`): an action delivers `mode=bootstrap` **iff** `f"action:{type}/{action}" in bundle.merged.node_urns()` (node-URN membership — NOT empty-grain, since `resolve_context` already degrades an undeclared node to empty). Bundle resolved before the mode decision. A declared-but-activation-starved node legitimately yields `bootstrap` + empty arrays (documented, per squad §S1). | High | Open |
| FR-002 | 4-token fast path preserved | `specify`/`plan`/`implement`/`review` keep resolving `bootstrap` via a fast path without regressing the hot-path budget. | High | Open |
| FR-003 | Typeless stays compact | Typeless input (`resolve_mission_type_key` → `None`) returns `compact` unchanged. | High | Open |
| FR-004 | Single graph load | The already-loaded DRG graph is threaded into the predicate; no second load on the path. | High | Open |
| FR-005 | Layered per-type governance tolerance | `_resolve_governance_slot` tolerates an unregistered type **iff** a per-type `governance-profile.yaml` with matching `id` exists at the **project or org** layer; else `UnknownMissionTypeError`. Does NOT tolerate a non-activated canonical type via its built-in profile (activation gating preserved — operator ruling, see ADR). | High | Open |
| FR-006 | Typo no longer resolves silently | Unregistered type with no matching per-type profile at any layer raises the named error — no empty sequence, no fabricated provenance. | High | Open |
| FR-007 | Canonical action vocabulary (fold) | The 4-token literal exists in exactly one location named for its **fast-path** role (e.g. `BOOTSTRAP_ACTIONS`), consumed by `context.py`; `_KNOWN_ACTIONS` removed as a copy. The interview (FR-008) consults it **plus** a declared-node source as two explicit inputs — the fast-path set must NOT become the closed acceptance allowlist (squad §S6). | Medium | Open |
| FR-008 | Interview accepts declared actions | `local_supporting_files` with `action: <declared node>` is retained, not warn-dropped. | Medium | Open |
| FR-009 | Per-type artifact FILENAME resolution | `resolve_configured_artifact_name` + `required_artifacts_for(step)` project `artifact_kind → filename` from **`expected-artifacts.yaml` `path_pattern`** (single per-type authority, 10/10 tags, via `src/doctrine/missions/repository.py`) — NOT from `MissionStepTemplateRef.artifact_file` (squad §S2). Charter slot typed `Mapping[str, Any]` (charter ⊥ specify_cli). `MissionStepTemplateRef` stays template-only. | High | Open |
| FR-010 | Named call sites converted | `_HASH_INPUTS`, accept triple, retrospective precondition, `validate_feature_structure`, `_PRESENCE_FILE_TAGS` contents read the resolved name set — not hardcoded literals. | High | Open |
| FR-011 | Live per-type artifact gate | `_PRESENCE_FILE_TAGS` (all 10 built-in filenames preserved) + family guard routing become per-type/keyed on mission type; a custom type can gate on a filename outside the built-in set. | High | Open |
| FR-012 | Stray spec.md deleted | The `else: spec_file.touch()` branch (~`worktree.py:609-610`) no longer creates an empty `spec.md`. Scope the deletion to that branch ONLY — the template-copy path in the same 595-610 block stays (keeps `test_copies_spec_template_when_exists` green — squad §S7). | Medium | Open |
| FR-013 | Third-kind blockers surfaced | `_substantive.py` `Kind = Literal["spec","plan"]` and `_ARTIFACT_TYPE_TO_KIND` are pinned by a test asserting the named raise (pin-and-defer, fork f) so a real third artifact kind's boundary is explicit. | Medium | Open |
| FR-014 | Resolve actual mission family | `_check_cli_guards` resolves the mission's real type at `runtime_bridge.py:797` instead of hardcoding `software-dev`, so the CLI-guard path reaches `_GUARD_TABLES[<actual family>]` (incl. the existing `plan` branch). No new plan table. | High | Open |
| FR-015 | Sanctioned carrier documented | Action grain is delivered by **direct `action:<type>/<step>` URN construction** (`action_doctrine_bundle.py:196`) + the action node's own `scope` edges in `action.graph.yaml` — the `mission_type→action requires` edge is an `action_sequence` artifact and is **NOT load-bearing for delivery** (squad §S5; the 3 `*/retrospect` nodes are sequence-orphans yet still deliver). Document this; either wire the retrospect nodes into their mission_type or record them as on-demand sequence-orphans. | Low | Open |
| FR-016 | Policy-reversal ADR | One ADR records both behaviour changes and **names each red-by-design test**: (1) `tests/charter/test_every_load_delivery.py:197`, (2) `tests/charter/test_context_schema_version_ledger.py:104`, (3) `tests/charter/test_mission_type_profiles.py:260`, (4) `tests/git_ops/test_worktree.py:263`, plus any sibling delivery/`spec.md`-presence assertions the red-first suite run surfaces. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Hot-path / single-graph-load budget | A **NEW** red-first test MUST patch `charter._drg_helpers.load_validated_graph` with a counter and assert `build_charter_context_json(action="tasks", mission_type="software-dev")` triggers **exactly one** load (the existing `test_charter_import_time_io.py` only spies import-time `MissionTypeRepository.default` and canNOT observe a runtime double-load — squad BLOCKER §S1). Confirm `load_validated_graph` is process-memoized so the FSM does not pay per step. Accept + record in the ADR the new (single) graph-load cost the non-bootstrap path now pays even for undeclared actions. | Performance | High | Open |
| NFR-002 | Delivery path stays hard-fail-free | The delivery path continues to route through `resolve_mission_type_key` (→ `canonical_mission_type_key`), preserving `None`-degradation; it introduces no new mission-type-seam hard-fail and no parallel legacy-honoring reader. | Reliability | High | Open |
| NFR-003 | Installed-base compatibility | For the four built-in mission types, every converted artifact/guard site yields the same values as `main` except the two intended reversals. | Reliability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | charter ⊥ specify_cli | `charter` must not import `specify_cli`; the artifact-name charter slot stays a bare `Mapping[str, Any]`; `ExpectedArtifactManifest` relocates from `src/specify_cli/dossier/manifest.py` to `src/doctrine/missions/`. | Technical | High | Open |
| C-002 | Deliberate behaviour change | NOT a byte-identical refactor — tasks/retrospect begin delivering; typo'd types begin hard-failing. Ship only with the ADR (FR-016); operator has signed off. | Business | High | Open |
| C-003 | Dispatch precondition (satisfied) | Per-type guard/manifest data-sourcing assumes family dispatch is correct (#3386 CLOSED) and `expected-artifacts.yaml` reconciled (#3388 CLOSED). Both confirmed on `main` 2026-08-21. | Technical | Medium | Closed-verified |

---

## Acceptance criteria

**#3596 — three pins (byte-identity reframing, corrected):**
1. **AC-1 — bootstrap actions unchanged.** `specify`/`plan`/`implement`/`review` on all four built-ins deliver the same grain as `main` (fast path, `mode=bootstrap`).
2. **AC-2 — undeclared action stays compact (self-limiting pin; GREEN characterization).** An action with no declared node returns `mode=compact`, empty arrays. **`tests/charter/test_context.py:228::test_non_bootstrap_action_returns_compact` (`action="custom-action"`, typeless) MUST still pass unchanged.** **Companion (NEW, isolates node-membership per squad §S3):** with `mission_type="software-dev"` **and** a genuinely *undeclared* action (a resolved type + a non-node action), the result is still `mode=compact` — proving the predicate is node-URN membership, not type-resolution.
3. **AC-3 — declared non-bootstrap actions now deliver (RED BY DESIGN → reverse).** `build_charter_context_json(action="tasks", mission_type="software-dev")` delivers the non-empty `tasks` grain (`mode=bootstrap`, non-empty `directives`); same for `documentation`/`research` `retrospect`. **This flips `tests/charter/test_every_load_delivery.py:197::test_json_non_bootstrap_action_is_explicitly_ruled_out` RED** (currently asserts `mode=="compact"`, `directives==[]`, `styleguides==[]`) — **reverse the assertion, do NOT "fix it back."** **Also flips (squad §S4, MUST reverse + name in FR-016): `tests/charter/test_context_schema_version_ledger.py:104::test_non_bootstrap_action_carries_stamped_version`** (same `action="tasks"` call asserting `mode=="compact"`). Sweep sibling delivery tests (`test_context.py`, `test_context_org_governance.py`, `test_action_bundle_delivery.py`, `test_action_grain.py`) for the same assertion and reverse each with an ADR reference; run the full `tests/charter/` suite red-first to surface any others.

**#3598 — layered per-type probe:**
4. **AC-4 — typo hard-fails.** Unregistered type with no matching per-type `governance-profile.yaml` at any layer raises `UnknownMissionTypeError`, even when the project has other `selected_*` doctrine.
5. **AC-5 — genuine custom type tolerated (project/org).** An unregistered type whose per-type `governance-profile.yaml` (with matching `id`) exists at the **project or org** layer resolves without error. **Operator ruling 2026-08-21 (activation gating preserved — see ADR):** the tolerance does NOT extend to the built-in layer for canonical types — a canonical built-in type a project has deliberately *not activated* still hard-fails (`test_mission_type_activation_gating.py::test_resolve_context_raises_for_type_outside_activated_subset` stays GREEN). Tolerating on built-in-profile-existence would silently defeat the activation-subset restriction; the `#3598` tolerance answers "genuine custom type vs typo," orthogonal to activation.
6. **AC-6 — RED BY DESIGN → reverse.** `tests/charter/test_mission_type_profiles.py:260::test_project_with_overrides_does_not_hard_fail_for_unknown_type` documents the project-wide tolerance as intentional. Rewrite it around the layered per-type predicate; do NOT restore the old tolerance. **Note (squad §S4):** the test currently patches `_project_has_doctrine_overrides`→True — a symbol FR-005 **deletes** — so the rewrite must instead seed a real per-type `governance-profile.yaml` with a matching `id`. AC-5's org/built-in tolerance is **net-new** behavior (today only the project layer is inspected) and needs layered fixtures. AC-4's red is clean (`resolve_mission_type_context(repo,"softwaer-dev")` silently resolves today, raises `UnknownMissionTypeError` at `mission_type_profiles.py:805` after).

**Fold:**
7. **AC-7 — single vocabulary.** A search for `{"specify","plan","implement","review"}` finds exactly one canonical definition; none remains at `interview.py:34`.
8. **AC-8 — interview accepts declared actions.** A `local_supporting_files` entry with `action: tasks` is retained, not warn-dropped.

**#3599/#3597 — artifact seam:**
9. **AC-9 — built-in name sets byte-compatible (GREEN characterization pin).** All four built-ins resolve their canonical artifact names through the new seam; `_HASH_INPUTS`, accept triple, retrospective precondition, `validate_feature_structure`, and `_PRESENCE_FILE_TAGS` (all 10: `spec.md, plan.md, tasks.md, source-register.csv, findings.md, report.md, gap-analysis.md, audit-report.md, release.md, research.md`) produce today's values (NFR-003). **Load-bearing assertion (squad §S3, so the seam is not decorative):** patching the per-type `path_pattern` source changes the call site's output — proving the literal was actually removed, not shadowed by an unused seam.
10. **AC-10 — custom type gates on its own filename (fail-closed, named entry point).** Via `gather_artifact_presence(feature_dir, mission_family="<custom>", step_id=...)` (squad §S3): with the custom filename PRESENT the gate **passes**, and with it ABSENT the gate **blocks** — both directions asserted (a present-only test permits a fail-open gate, the sin this mission kills). The WP01 ADR decides whether a custom family gets a `_GUARD_TABLES` registration or the `UnregisteredMissionFamilyError` strict-raise is the intended gate.
11. **AC-11 — stray spec.md gone (RED BY DESIGN → reverse; enumerated).** The `else: spec_file.touch()` branch no longer runs. **Named reversal (squad §S4): `tests/git_ops/test_worktree.py:263::test_creates_empty_spec_when_no_template`** (asserts `spec_file.exists()` + `read_text()==""`) flips RED — reverse it. **Classify as stay-GREEN: `tests/integration/test_specify_plan_commit_boundary.py:247`** (template-scaffold presence) and **`tests/agent/test_agent_feature.py:346`** — confirm they assert the template-copy path, not the stray touch, before touching them.
12. **AC-12 — third kind boundary pinned (GREEN characterization pin).** A test asserts the **specific** exception type + message fragment from `_substantive.py:281` (`ValueError("Unknown kind: …")`) and `_ARTIFACT_TYPE_TO_KIND` (`mission_feature_resolution.py:62-66`, `KeyError` "no silent default") for an unmapped third kind (pin-and-defer, fork f) — not a broad `pytest.raises(Exception)`, so a future silent-default reintroduction reds it.

**#3407 — CLI guard family:**
13. **AC-13 — plan review no longer aliases (latent-defect pin; squad §S4).** The red is a hand-built seam scenario, not a runtime-natural path (the runtime callers gate on `_is_wp_iteration_step`, and `_check_cli_guards` never reads the mission type today). Red-first harness: seed `meta.json mission_type: plan` + an unapproved `tasks/WP01.md` lane, call `_check_cli_guards("review", <plan dir>)` → today aliases into `_evaluate_wp_iteration_guard` (returns the WP-block string); after the fix it routes to `_GUARD_TABLES["plan"]` (`_evaluate_plan_guards` → `[]`, real gate `gate_passed("plan_approved")`). Label it a latent route-around pin (low live-regression value, genuine foot-gun).
14. **AC-14 — built-in dispatch unchanged.** software-dev missions evaluate exactly as on `main` (NFR-003).

---

## Key design decisions

- **KDD-1 (predicate over set, five surfaces, one ADR).** Every diff replaces coarse-set membership with a predicate on the declared entity: DRG node-URN membership (#3596), per-type profile existence+id-match across layers (#3598), per-type artifact filename from `expected-artifacts.yaml` `path_pattern` (#3599), per-type presence/guard routing (#3597/#3407), resolved family (#3407).
- **KDD-2 (resolve then gate; single graph load).** #3596 resolves the bundle first and reads `bundle.merged`; the fast path avoids paying that for the common four.
- **KDD-3 (consume the landed `canonical_mission_type_key`; no new hard-fail).** The delivery path already routes through `resolve_mission_type_key` → `canonical_mission_type_key`, which degrades typeless to `None`. M3 preserves this (NFR-002); it does not re-implement a reader or add a hard-fail. Forward-compatible with M5's eventual `read_mission_type(meta)` delegate.
- **KDD-4 (layered tolerance witness).** The per-type profile file (id-matched) is the honest witness of "a project/org/pack defining this type"; any-`selected_*` is not. Reuse `MissionTypeProfileRepository`; add no second probe site.
- **KDD-5 (single filename authority; twin the manifest-load seam).** Artifact filenames come from ONE authority: `expected-artifacts.yaml` `path_pattern` (per-type, 10/10 tags), loaded via `src/doctrine/missions/repository.py` — the artifact-name resolver twins the manifest-load path, not `resolve_configured_template` (which resolves the distinct TEMPLATE name from `step.yaml` and stays untouched). No `artifact_file` on `MissionStepTemplateRef` (that would be a second authority for the same value — the KDD-1 anti-pattern). Defaults keep the four built-ins byte-compatible (squad §S2).
- **KDD-6 (self-limiting, corrected).** The pin is **"an undeclared action node stays compact"** — NOT "all built-ins byte-identical." tasks/retrospect are non-empty and SHOULD change.
- **KDD-7 (charter ⊥ specify_cli).** The artifact-name charter slot stays `Mapping[str, Any]`; `ExpectedArtifactManifest` relocates into `src/doctrine/missions/` (C-001).
- **KDD-8 (#3407: route, don't rebuild).** The `plan` guard table exists; the fix is resolving the actual family at `runtime_bridge.py:797` so the CLI path reaches it. No duplicate table.

---

## Design forks — LOCKED (decided for the WP01 ADR)

Scope forks (a)-(c) were resolved by the coordinator (fold the full seam; layered id-matched probe at any layer; one signed-off ADR). The three costed design forks are now **locked** by the re-verification:

- **(d) #3597 gate mechanism → per-type DATA source (option ii). LOCKED.** The `mission_v1` guard cluster (`GUARD_REGISTRY`/`compile_guards`/`_make_artifact_exists_guard`) is confirmed **dead in production** (zero `src/` callers outside tests; live FSM has no guard fields; the live runtime has its own `artifact_exists` at `engine.py:1445`). Reviving v1 re-introduces a parallel dead engine and does not even retire the package (it is still imported for `events` by `decision.py`/`next_cmd.py`). Give the Python family routing + presence tuple a per-type data source aligned with the #3599 step-contract/`expected-artifacts.yaml` split.
- **(e) Artifact FILENAME source → `expected-artifacts.yaml` `path_pattern` (RE-LOCKED after POST-SPEC squad source-adjudication).** ~~step-contract short-key via `MissionStepTemplateRef`~~ was wrong on two counts (squad §S2): (1) `step.yaml` DOES exist (30 files, `packs/built-in/missions/mission-steps/`) and carries the TEMPLATE ref, not the filename; (2) `MissionStepTemplateRef` covers only 2/10 tags. The single per-type filename authority is `expected-artifacts.yaml` `path_pattern` (10/10 tags, all 4 types). Do NOT add `artifact_file` to `MissionStepTemplateRef` (dual-authority anti-pattern). `MissionStepTemplateRef`/`resolve_configured_template` stays template-only.
- **(f) third-kind → pin-and-defer (option ii). LOCKED.** No WP in M3 introduces a third built-in kind; pin the `_substantive.py` `Kind` + `_ARTIFACT_TYPE_TO_KIND` boundary with a test asserting the named raise (AC-12), deferring true N-kind support.

---

## Risks

- **Import-time / hot-path budget (NFR-001).** Resolving the bundle before the mode decision or a stray second graph load trips `test_charter_import_time_io` / the ~100 ms path. Mitigation: thread the loaded graph (FR-004), keep the fast path, measure.
- **"Byte-identity" mis-reframing.** Corrected (KDD-6): only undeclared nodes stay compact; tasks/retrospect change on purpose; artifact/guard sites are byte-compatible for built-ins (NFR-003) except the two reversals. An implementer who "restores" identity re-breaks the fix.
- **Red-by-design tests fixed backwards.** Named reversals: AC-3 (`test_json_non_bootstrap_action_is_explicitly_ruled_out`), AC-6 (`test_project_with_overrides_does_not_hard_fail_for_unknown_type`), plus AC-11 (any stray-`spec.md` presence assertion) and the AC-2 green guard. FR-016 ADR must point at each.
- **Seam breadth (L mission).** #3599 is L; `_PRESENCE_FILE_TAGS` is 10 filenames; ~35 test files reference the literal triple. Mitigation: WP slicing at plan; convert only the named call sites; C-003 preconditions confirmed.
- **Same-file coordination with M4 (`repository.py`).** M4 (not landed) owns the `:316-317` fail-loud; M3 owns the relocation + name seam. Mitigation: per-symbol ownership at plan; M3 targets `main` and opens a draft PR — if M4 lands first, rebase and reconcile the file.

---

## Issues / traceability

| Issue | Role in M3 |
|-------|-----------|
| #3596 (P2) | In scope — action gate predicate (`context.py:255`,`:484`). |
| #3598 (P1) | In scope — layered per-type governance probe (`mission_type_profiles.py:766`,`:1235`). |
| new (`_KNOWN_ACTIONS` fold) | In scope — file the ticket; third 4-token copy at `interview.py:34`. |
| #3599 (P2/L) | In scope — artifact filename seam; FILENAME from `expected-artifacts.yaml` `path_pattern` (single authority, 10/10 tags). Fork (e) RE-LOCKED (squad §S2). |
| #3597 (P2) | In scope — live per-type artifact gate; presence tuple + family routing per-type. Fork (d) LOCKED. |
| #3407 (P3) | In scope — resolve actual family at `runtime_bridge.py:797`; route to existing `plan` table (do not rebuild). |
| #3386, #3388 | Closed preconditions (family dispatch correct; expected-artifacts reconciled) — verified CLOSED 2026-08-21 (C-003). |
| M5 (`rc3-canonical-mission-type-reader`) | Reference only — interlock already satisfied on `main` via `canonical_mission_type_key`. Do NOT fold. |
| M4 (`rc3-operator-signal-fail-loud`) | Reference only — same-file (`repository.py`) coordination; per-symbol ownership at plan. Do NOT fold. |

## Cross-mission coordination (rc3 integration check)

- **M3↔M5 reader path — SATISFIED on `main`.** M3's delivery path already routes through `resolve_mission_type_key` → `canonical_mission_type_key` (canonical-field-only, `None`-degrading). No parallel legacy path exists to re-diverge. When M5 lands `read_mission_type(meta)`, `resolve_mission_type_key` becomes a delegate (forward-compatible). No blocking dependency.
- **M3↔M4 same-file (`src/doctrine/missions/repository.py`).** M4 owns the malformed-load fail-loud (`:316-317`); M3 owns `ExpectedArtifactManifest` relocation + artifact-name reads. Different symbols/lines. Assign per-symbol ownership at plan; rebase-reconcile if M4 lands first.
- **Program gate — SATISFIED.** M3's typeless/typo `mission_type` hard-fail (#3598) required **M0** to have run first; M0 is **landed** on `main` with a fail-closed `doctor mission-type` census gate.
