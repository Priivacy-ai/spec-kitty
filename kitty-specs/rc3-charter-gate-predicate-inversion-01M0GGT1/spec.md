# Mission Specification: M3 — Gate on the declared entity, not a coarse set

**Status**: Draft (LIGHT spec — specify-phase only; NOT finalized)
**Created**: 2026-08-20
**Author**: analyst-annie
**Milestone / rc target**: 3.2.x — one of eight specs feeding a single-branch PR before rc2; run later.
**Scope (operator-EXPANDED)**: #3596 + #3598 + `_KNOWN_ACTIONS` fold + #3599 + #3597 + #3407 — all one ADR shape.
**Separate mission (reference only, do NOT fold)**: M5 — meta.json reader convergence.

> **Source provenance note.** This spec is grounded in the investigation `docs/plans/investigations/friction-bugs-processing-charter-root-cause.md` (§2.2/§2.3/§10, shipped in this same PR) and re-verified line-level against `main` (#3596/#3598/#3599/#3597/#3407).

---

## Problem & impact (BLUF)

One theme, five surfaces: charter/runtime code decides delivery, tolerance, and gating by testing membership in a **coarse hardcoded set** instead of the **entity actually declared**. Each silently starves shipped configuration or fails open. Verified on `main`:

1. **#3596 — action gate.** `BOOTSTRAP_ACTIONS = frozenset({"specify","plan","implement","review"})` (`src/charter/context.py:115`) short-circuits any other action to `mode=compact` before a bundle is built (`context.py:255` plain-text, `:484` `--json`). `software-dev/actions/tasks/index.yaml` (13 lines) and `documentation/actions/retrospect/index.yaml` (16 lines) carry non-empty grain that delivers **nothing**. The DRG traversal that would honour a declared `action:<type>/<step>` node already works; only the gate is wrong.
2. **#3598 — governance-slot probe.** `_resolve_governance_slot` (`mission_type_profiles.py:766`) tolerates an unregistered type whenever `_project_has_doctrine_overrides(repo_root)` is `True` (`:1235`) — a **project-wide** probe that is `True` for nearly every charter-bearing project. A typo'd type (`softwaer-dev`) then resolves **silently**: `action_sequence=[]`, `template_set=None`, `provenance='project'` (fabricated), **no warning**.
3. **`_KNOWN_ACTIONS`** (`charter/interview.py:34`) — third copy of the same 4-token frozenset; warn-drops (`treating as global`) any `local_supporting_files` `action:` outside the four, even actions about to start delivering.
4. **#3599/#3597 — artifact seam.** Artifact filenames are hardcoded literals at the gates while four per-type manifests ship and gate nothing. `_HASH_INPUTS = ("spec.md","plan.md","tasks.md")` (`analysis_report.py:33`); `_PRESENCE_FILE_TAGS` is a closed tuple (`runtime_bridge_io.py:841`); the v1 guard registry (`mission_v1/guards.py` `GUARD_REGISTRY`/`compile_guards`) has **no production callers of those symbols** (verified — the live FSM `mission-runtime.yaml` has no guard fields), so no per-type artifact gate executes; a custom type's report phase advances with no artifact evidence. `worktree.py:596-609` creates a stray empty `spec.md` that satisfies every existence gate and nothing reads.
5. **#3407 — CLI guard.** `_check_cli_guards` (`runtime_bridge.py:785`) hardcodes `mission_family="software-dev"` (`:797`) for **every** mission type. Latent today (`plan`'s `review` step lexically collides with software-dev's `review` and reaches `_evaluate_wp_iteration_guard`, currently returning `[]` only because `wp_advance_ready` defaults `True` when no `tasks/` dir exists) but a real, reachable, mission-blind branch and a spurious-block risk.

**Impact**: non-canonical actions/types get no action-scoped doctrine; typo'd types fail open with fabricated provenance; custom mission types cannot declare or gate on their own artifact filenames; a `plan` mission's `review` step can silently alias into a WP-iteration guard it has no domain relation to.

**Fix shape (the single ADR)**: at each surface, replace the coarse-set membership test with a predicate on the actually-declared entity — DRG node-membership (#3596), per-type profile existence+id-match (#3598), per-type artifact-name source (#3599), per-type presence/guard tables keyed on mission type (#3597), the resolved mission family (#3407) — and unify the 4-token literal to one canonical source. Defaults preserve today's values for the four built-ins where a value exists; the two intended behaviour changes are recorded in one policy-reversal ADR.

---

## In scope

**A. Action gate (#3596 + `_KNOWN_ACTIONS`)**
- Replace both `BOOTSTRAP_ACTIONS` checks with: an action carries a doctrine grain **iff** the merged DRG (`bundle.merged`) declares its node. Resolve the bundle first, then gate. Keep the 4-token fast path. Resolve the type via `resolve_mission_type_key` (bypasses `resolve_mission_type_context`/its hard-fail). Typeless stays `compact`. Thread the already-loaded graph (no double load; ~100 ms budget). Document the pack-root `*.graph.yaml` carrier as sanctioned.
- Fold `_KNOWN_ACTIONS` (`interview.py:34`) into one canonical vocabulary; interview validation consults it and accepts declared action nodes.

**B. Governance-slot probe (#3598)**
- Replace the project-wide `_project_has_doctrine_overrides` tolerance gate with a **layered per-type** probe: tolerate an unregistered type **iff** a per-type `governance-profile.yaml` exists **and its `id` matches the type** at **any** layer — project (`.kittify/doctrine/mission_types/<type>/`), org, **or** built-in (`src/doctrine/missions/<type>/`). Reuse `MissionTypeProfileRepository` (already resolves + id-matches across layers via `_GOVERNANCE_PROFILE_GLOB`); do not add a second merge/probe site.

**C. Artifact-name + gate seam (#3599, #3597)**
- Build `artifact_kind → filename` as the twin of the live `resolve_configured_template` seam: relocate `ExpectedArtifactManifest` into `src/doctrine/missions/`; add `artifact_file` to `MissionStepTemplateRef`; add `project_artifact_name_set` beside `project_template_set`; two charter bundle slots on the existing thunk; `resolve_configured_artifact_name` + `required_artifacts_for(step)` in `specify_cli/runtime/resolver.py`. **Source the artifact NAME from `step.yaml`** (short-key vocab `spec`/`plan`, already org-layerable and charter-projected); use `expected-artifacts.yaml` only for gate **sets**.
- Make per-type artifact gating live: a per-type source for `_PRESENCE_FILE_TAGS` and the family guard tables keyed on mission type; defaults preserving today's values for the four built-ins.
- Convert only these call sites: `analysis_report._HASH_INPUTS`; the accept triple; the retrospective precondition; `validate_feature_structure` (`core/worktree.py:704`); the `_PRESENCE_FILE_TAGS` contents.
- **Delete** `worktree.py`'s stray-`spec.md` creation (`:596-609`).
- Surface the two second-order blockers hit by any real third artifact kind: `_substantive.py`'s `Kind = Literal["spec","plan"]` (raises on a third), and `_ARTIFACT_TYPE_TO_KIND` (`mission_feature_resolution.py:47`, raises "no silent default").

**D. CLI guard family (#3407)**
- Resolve the mission's actual type before dispatching guard evaluation in `_check_cli_guards` (`runtime_bridge.py:785`, drop the hardcoded `mission_family="software-dev"` at `:797`); add a dedicated `plan`-family guard branch (initially a no-op/empty table) so `plan`'s `review` cannot alias into software-dev's WP-iteration guard.

**E. Governance**
- One policy-reversal ADR for both intended behaviour changes (§B typo hard-fails; §A tasks/retrospect now deliver). Name every red-by-design test in the ACs.

## Out of scope

- **M5 (separate mission)** — `_read_meta_mission_type` vs `mission.py` legacy-`mission` fallback convergence. Reference only; do NOT fold.
- Adding `actions` to `_ORG_DRG_KIND_ALIASES` (diagnostics-only loader) — record as rejected.
- Opening `ALLOWED_MISSION_TYPES` / `REGISTERED_TRIGGERS` / the activation-registry fetch-command route — leave closed, record decision.
- **Full census conversion** of artifact-name literals (~100 sites / 800–1200 LOC across 20 packages) — rejected; convert only the named call sites.
- `_MISSION_FILE_KIND_BY_BASENAME` (`mission_runtime/artifacts.py:211`) — placement seam; a `None` classification correctly routes PRIMARY for custom-type artifacts, so no entry needed.
- The frozen migrations.

---

## Functional Requirements

| ID | Title | Requirement | Priority | Status |
|----|-------|-------------|----------|--------|
| FR-001 | Node-membership action gate | Both `context.py` gate sites: an action carries a grain **iff** `bundle.merged` declares its node; bundle resolved before the mode decision. | High | Open |
| FR-002 | 4-token fast path preserved | `specify`/`plan`/`implement`/`review` keep resolving `bootstrap` via a fast path without regressing the hot-path budget. | High | Open |
| FR-003 | Typeless stays compact | Typeless input returns `compact` unchanged. | High | Open |
| FR-004 | Single graph load | The already-loaded DRG graph is threaded into the predicate; no second load on the path. | High | Open |
| FR-005 | Layered per-type governance tolerance | `_resolve_governance_slot` tolerates an unregistered type **iff** a per-type `governance-profile.yaml` exists AND its `id` matches, at project, org, OR built-in layer; else `UnknownMissionTypeError`. | High | Open |
| FR-006 | Typo no longer resolves silently | Unregistered type with no matching per-type profile at any layer raises the named error — no empty sequence, no fabricated provenance. | High | Open |
| FR-007 | Canonical action vocabulary (fold) | The 4-token literal exists in exactly one location, consumed by `context.py` fast path and `interview.py`; `_KNOWN_ACTIONS` removed as a copy. | Medium | Open |
| FR-008 | Interview accepts declared actions | `local_supporting_files` with `action: <declared node>` is retained, not warn-dropped. | Medium | Open |
| FR-009 | Per-type artifact NAME resolution | `resolve_configured_artifact_name` + `required_artifacts_for(step)` project `artifact_kind → filename` from `step.yaml`; charter slot typed `Mapping[str, Any]` (charter ⊥ specify_cli). | High | Open |
| FR-010 | Named call sites converted | `_HASH_INPUTS`, accept triple, retrospective precondition, `validate_feature_structure`, `_PRESENCE_FILE_TAGS` contents read the resolved name set — not hardcoded literals. | High | Open |
| FR-011 | Live per-type artifact gate | `_PRESENCE_FILE_TAGS` + family guard tables become per-type/keyed on mission type; a custom type can gate on a filename outside the canonical nine. | High | Open |
| FR-012 | Stray spec.md deleted | `worktree.py:596-609` no longer creates an empty `spec.md`. | Medium | Open |
| FR-013 | Third-kind blockers surfaced | `_substantive.py`'s `Kind = Literal["spec","plan"]` and `_ARTIFACT_TYPE_TO_KIND` are extended (or explicitly deferred with a named guard) so a real third artifact kind does not raise. | Medium | Open |
| FR-014 | Resolve actual mission family | `_check_cli_guards` resolves the mission's real type instead of hardcoding `software-dev`; a `plan`-family guard branch exists so `plan`'s `review` cannot alias into the WP-iteration guard. | High | Open |
| FR-015 | Sanctioned carrier documented | Pack-root `*.graph.yaml` `action:<type>/<step>` + `scope` edge mechanism documented as sanctioned. | Low | Open |
| FR-016 | Policy-reversal ADR | One ADR records both behaviour changes and names each red-by-design test (see ACs). | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Import-time / hot-path budget | Action-gate path stays within `tests/charter/test_charter_import_time_io.py` and the ~100 ms FSM budget; no new import-time I/O, no double graph load. | Performance | High | Open |
| NFR-002 | No new hard-fail surface | `resolve_mission_type_key` (not `_context`) introduces no new mission-type-seam hard-fail on the delivery path. | Reliability | High | Open |
| NFR-003 | Installed-base compatibility | For the four built-in mission types, every converted artifact/guard site yields the same values as `main` except the two intended reversals. | Reliability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | charter ⊥ specify_cli | `charter` must not import `specify_cli`; the artifact-name charter slot stays a bare `Mapping[str, Any]`; `ExpectedArtifactManifest` relocates to `src/doctrine/missions/`. | Technical | High | Open |
| C-002 | Deliberate behaviour change | NOT a byte-identical refactor — tasks/retrospect begin delivering; typo'd types begin hard-failing. Ship only with the ADR (FR-016); operator has signed off. | Business | High | Open |
| C-003 | #3386/#3388 dispatch precondition | Per-type guard/manifest data-sourcing (#3597/#3599) assumes the family dispatch is already correct (#3386 closed) and `expected-artifacts.yaml` reconciled (#3388 closed); re-confirm at plan. | Technical | Medium | Open |

---

## Acceptance criteria

**#3596 — three pins (byte-identity reframing, corrected):**
1. **AC-1 — bootstrap actions unchanged.** `specify`/`plan`/`implement`/`review` on all four built-ins deliver the same grain as `main` (fast path, `mode=bootstrap`).
2. **AC-2 — undeclared action stays compact (self-limiting pin, stays GREEN).** An action with no declared node returns `mode=compact`, empty arrays. **`tests/charter/test_context.py::test_non_bootstrap_action_returns_compact` (`action="custom-action"`) MUST still pass unchanged.**
3. **AC-3 — declared non-bootstrap actions now deliver (RED BY DESIGN → reverse).** `build_charter_context_json(action="tasks", mission_type="software-dev")` delivers the non-empty `tasks` grain (`mode=bootstrap`, non-empty `directives`); same for `documentation`/`research` `retrospect`. **This flips `tests/charter/test_every_load_delivery.py::test_json_non_bootstrap_action_is_explicitly_ruled_out` RED — reverse the assertion, do NOT "fix it back."** Sweep sibling delivery tests for the same `non-bootstrap → compact`/`directives==[]` assertion and reverse each with an ADR reference.

**#3598 — layered per-type probe:**
4. **AC-4 — typo hard-fails.** Unregistered type with no matching per-type `governance-profile.yaml` at any layer raises `UnknownMissionTypeError`, even when the project has other `selected_*` doctrine.
5. **AC-5 — genuine custom type tolerated at each layer.** An unregistered type whose per-type `governance-profile.yaml` (with matching `id`) exists at project **or** org **or** built-in resolves without error.
6. **AC-6 — RED BY DESIGN → reverse.** `tests/charter/test_mission_type_profiles.py::test_project_with_overrides_does_not_hard_fail_for_unknown_type` (line ~260) documents the project-wide tolerance as intentional. Rewrite it around the layered per-type predicate; do NOT restore the old tolerance.

**Fold:**
7. **AC-7 — single vocabulary.** A search for `{"specify","plan","implement","review"}` finds exactly one canonical definition; none remains at `interview.py:34`.
8. **AC-8 — interview accepts declared actions.** A `local_supporting_files` entry with `action: tasks` is retained, not warn-dropped.

**#3599/#3597 — artifact seam:**
9. **AC-9 — built-in name sets byte-compatible.** All four built-ins resolve the canonical triple (`spec.md`/`plan.md`/`tasks.md`) through the new seam; `_HASH_INPUTS`, accept triple, retrospective precondition, `validate_feature_structure`, and `_PRESENCE_FILE_TAGS` produce today's values (NFR-003).
10. **AC-10 — custom type gates on its own filename.** A regression test proves a custom mission type gates on a filename **outside** the canonical nine, via the per-type presence source.
11. **AC-11 — stray spec.md gone.** `worktree.py` no longer writes an empty `spec.md`; existence gates depend on real artifacts. (Guard any test that asserted the stray file's presence — reverse it.)
12. **AC-12 — third kind does not raise.** A third artifact kind does not raise through `_substantive.py`/`_ARTIFACT_TYPE_TO_KIND` (extended, or a named test pins the deferred boundary).

**#3407 — CLI guard family:**
13. **AC-13 — plan review no longer aliases.** With a `plan`-type mission whose directory contains a `tasks/WP*.md` set, `plan`'s `review` step is NOT evaluated by software-dev's WP-iteration guard; it resolves against its own (empty) family table. Its real gate stays `gate_passed("plan_approved")`.
14. **AC-14 — built-in dispatch unchanged.** software-dev missions evaluate exactly as on `main` (NFR-003).

---

## Key design decisions

- **KDD-1 (predicate over set, five surfaces, one ADR).** Every diff replaces coarse-set membership with a predicate on the declared entity: DRG node (#3596), per-type profile existence+id-match across layers (#3598), per-type artifact-name from `step.yaml` (#3599), per-type presence/guard tables (#3597), resolved family (#3407).
- **KDD-2 (resolve then gate; single graph load).** #3596 resolves the bundle first and reads `bundle.merged`; the fast path avoids paying that for the common four.
- **KDD-3 (`resolve_mission_type_key`, not `_context`).** No new hard-fail on the delivery path (NFR-002).
- **KDD-4 (layered tolerance witness).** The per-type profile file (id-matched) is the honest witness of "a project/org/pack defining this type"; any-`selected_*` is not. Reuse `MissionTypeProfileRepository`; add no second probe site.
- **KDD-5 (twin an existing seam).** Artifact names follow `resolve_configured_template` exactly — no new pattern. NAME from `step.yaml`; gate SETS from `expected-artifacts.yaml`. Defaults keep the four built-ins byte-compatible.
- **KDD-6 (self-limiting, corrected).** The pin is **"an undeclared action node stays compact"** — NOT "all built-ins byte-identical." tasks/retrospect are non-empty and SHOULD change.
- **KDD-7 (charter ⊥ specify_cli).** The artifact-name charter slot stays `Mapping[str, Any]`; `ExpectedArtifactManifest` relocates into `src/doctrine/missions/` (C-001).

---

## OPEN QUESTIONS (operator decision)

Scope forks (a)-(c) are **RESOLVED** by the coordinator (fold the full seam; layered id-matched probe at any layer; one signed-off ADR). Two genuine, costed **design forks** remain for the WP01 ADR — flagged, not blocking:

- **(d) #3597 gate mechanism — revive vs data-source.** Options: **(i) revive the v1 guard path** (`compile_guards` over `mission.yaml` conditions) — retires ~1000 LOC of dead `mission_v1` rather than adding a consumer; **(ii) give the Python family tables + presence tuple a per-type data source** (with `expected-artifacts.yaml` reconciled, #3388, the obvious source). *Recommendation*: **(ii)** — the live FSM (`mission-runtime.yaml`) has no guard fields, so reviving v1 re-introduces a parallel engine; a per-type data source aligns with the #3599 `step.yaml`/`expected-artifacts.yaml` split already chosen. Note that `mission_v1` is still imported elsewhere (composition/decision/next_cmd), so "retire the package" (option i's upside) is not free. Decide in WP01 ADR.
- **(e) Artifact NAME source of truth.** Options: **(i)** `step.yaml` short-key vocab (`spec`/`plan`) as issue #3599 proposes; **(ii)** `expected-artifacts.yaml`'s `artifact_key` (`input.spec.main`…). *Recommendation*: **(i) `step.yaml` for names, `expected-artifacts.yaml` for gate sets** — the two vocabularies cannot join and `expected-artifacts.yaml`'s key is a provenance label, not a role key. Confirm in WP01 ADR.
- **(f) #3413/third-kind blockers — extend now or pin-and-defer.** Options: **(i)** extend `_substantive.py` `Kind` + `_ARTIFACT_TYPE_TO_KIND` to accept a third kind now; **(ii)** leave them closed for M3 (all built-ins are 2–3 canonical kinds) and pin the boundary with a test that asserts the named raise, deferring true N-kind support. *Recommendation*: **(ii) pin-and-defer** unless a WP in this mission actually introduces a third built-in kind — extending them without a consumer adds untested breadth. Operator to confirm at plan.

---

## Risks

- **Import-time / hot-path budget (NFR-001).** Resolving the bundle before the mode decision or a stray second graph load trips `test_charter_import_time_io` / the ~100 ms path. Mitigation: thread the loaded graph (FR-004), keep the fast path, measure.
- **"Byte-identity" mis-reframing.** Easily overstated as "all built-ins unchanged." Corrected (KDD-6): only undeclared nodes stay compact; tasks/retrospect change on purpose; artifact/guard sites are byte-compatible for built-ins (NFR-003) except the two reversals. An implementer who "restores" identity re-breaks the fix.
- **Red-by-design tests fixed backwards.** Named reversals: AC-3 (`test_json_non_bootstrap_action_is_explicitly_ruled_out`), AC-6 (`test_project_with_overrides_does_not_hard_fail_for_unknown_type`), plus AC-11 (any stray-`spec.md` presence assertion) and the AC-2 green guard. FR-016 ADR must point at each.
- **Seam breadth (L mission).** #3599 is L (~280–380 LOC, ~35 test files; 61 test files reference the literal triple, expect 30–40 real edits). Folding #3597/#3407 adds runtime-bridge surface. Mitigation: WP slicing at plan; convert only the named call sites; C-003 preconditions confirmed.
- **`mission_v1` liveness assumption.** #3597 rests on the guard-registry symbols being dead; the package is imported for other reasons. Re-verify the *specific* `GUARD_REGISTRY`/`compile_guards`/`artifact_exists` callers are absent before choosing fork (d).

---

## Issues / traceability

| Issue | Role in M3 |
|-------|-----------|
| #3596 (P2) | In scope — action gate predicate (`context.py:255`,`:484`). |
| #3598 (P1) | In scope — layered per-type governance probe (`mission_type_profiles.py:766`,`:1235`). |
| new (`_KNOWN_ACTIONS` fold) | In scope — file the ticket; third 4-token copy at `interview.py:34`. |
| #3599 (P2/L) | In scope — artifact_name_set seam; NAME from `step.yaml`, sets from `expected-artifacts.yaml`. Fork (e). |
| #3597 (P2) | In scope — live per-type artifact gate; presence tuple + family tables per-type. Fork (d). |
| #3407 (P3) | In scope — resolve actual family in `_check_cli_guards` (`runtime_bridge.py:785`/`:797`) + `plan` guard branch. |
| M5 (separate mission) | Reference only — meta.json reader convergence. Do NOT fold. |
| #3386, #3388 | Closed preconditions (family dispatch correct; expected-artifacts reconciled); re-confirm at plan (C-003). |

**Re-verify before finalize/implement**: all cited line numbers against `main` (issues note prior drift); locate/confirm the source investigation file; confirm the specific `GUARD_REGISTRY`/`compile_guards` symbols have no live callers; sweep for sibling `non-bootstrap → compact` delivery assertions and any stray-`spec.md` presence tests.
