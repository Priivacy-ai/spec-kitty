---
description: "Work package task list for Doctrine Governance Fidelity"
---

# Work Packages: Doctrine Governance Fidelity

**Inputs**: Design documents from `kitty-specs/doctrine-governance-fidelity-01KW42KY/`
**Prerequisites**: plan.md (9 ICs), spec.md (12 FRs / 4 NFRs / 8 constraints), research.md, issue-matrix.md
**Topology**: lanes (no coord). Three dependency chains → Lane A (#2153), Lane B (#2156/#2166/FR-013), Lane C (#2082).

**Tests**: Red-first per WP through the pre-existing public surface (C-005). Every new branch/helper carries a focused test (NFR-003).

**Organization**: Subtasks (`Txxx`) roll up into work packages (`WPxx`). Each WP is independently deliverable, reviewable, and owns a disjoint file set (DIRECTIVE_024 locality-of-change).

---

## Work Package WP01: Charter documentation-policy interpolation (Priority: P2) 🎯 Lane A

**Goal**: Render the operator's `documentation_policy` interview answer in the generated charter, mirroring `risk_boundaries`; preserve the empty-answer branch.
**Independent Test**: Seed `documentation_policy: "SENTINEL_DOCS: …"` in interview answers; `spec-kitty charter generate --from-interview`; grep `charter.md` Project Directives for the sentinel (RED today). Empty-answer case emits no line.
**Prompt**: `/tasks/WP01-charter-doc-policy-interpolation.md`
**Requirement Refs**: FR-001, FR-002, C-005, C-007, NFR-003

### Included Subtasks

- [x] T001 Add a RED test driving `charter generate --from-interview` asserting a seeded `documentation_policy` sentinel appears in `charter.md` (and the risk sentinel still appears).
- [x] T002 Interpolate `documentation_policy` at `src/charter/compiler.py:944` using the `risk_boundaries` shape (`{index}. Keep documentation synchronized with workflow and behavior changes: {docs}`).
- [x] T003 Add a focused test for the empty-`documentation_policy` branch (no directive line emitted).

### Dependencies

- None (Lane A root).

### Risks & Mitigations

- Empty-answer regression → explicit test (T003). Single sink (charter.md) confirmed in research; no `directives.yaml` ripple.

---

## Work Package WP02: Charter-activation-aware org-profile resolver (Priority: P1) 🎯 Lane B foundation

**Goal**: One helper, `resolve_activated_org_profiles(repo_root) -> list[AgentProfile]`, returning the charter-activated org-provenance subset (reusing `build_activation_aware_doctrine_service`), provenance-tagged — NOT a raw `org_dirs` list.
**Independent Test**: Unit test over the three activation regimes (key absent → all org profiles; explicit list includes → that profile present; explicit list excludes → absent), provenance preserved.
**Prompt**: `/tasks/WP02-activation-aware-org-resolver.md`
**Requirement Refs**: FR-003, FR-007, C-002, C-006, C-008, NFR-004

### Included Subtasks

- [x] T004 RED unit test for the three-regime activation filter (absent/includes/excludes) over a real-format org pack fixture.
- [x] T005 Implement `resolve_activated_org_profiles` composing `resolve_org_roots` + `PackContext` via `build_activation_aware_doctrine_service`; return org-provenance subset with provenance.
- [x] T006 Fail-closed test: malformed allowlist/DRG does not flip a de-activated profile to admitted (NFR-004).

### Dependencies

- None (Lane B foundation).

### Risks & Mitigations

- Re-implementing the gate → reuse the existing wrapper only. Import cycle → place helper to avoid `charter`↔`specify_cli` cycles (decide exact module in T005).

---

## Work Package WP03: Dispatch routing + governance-context org visibility (Priority: P1)

**Goal**: `ProfileRegistry` (routing catalog) and the governance-context repo include the activation-admitted org subset, merged onto their existing `.kittify/profiles` project layer — no raw `org_dirs` splice.
**Independent Test**: Live two-regime proof — an admitted org profile is present in `ProfileRegistry.list_all()` and carries non-empty governance context via `dispatch --profile`; a de-activated one is absent.
**Prompt**: `/tasks/WP03-dispatch-routing-org-visibility.md`
**Requirement Refs**: FR-004, FR-005, C-008, NFR-001, NFR-002

### Included Subtasks

- [x] T007 RED test: activated org profile present in dispatch routing catalog (`ProfileRegistry`), de-activated absent; built-in-only project unchanged.
- [x] T008 Wire `registry.py` to merge `resolve_activated_org_profiles(repo_root)` onto the existing `.kittify/profiles` repo.
- [x] T009 Wire `charter/context.py` governance-context path so a `--profile`-hinted activated org agent loads non-empty context.
- [x] T010 Regression test: no org packs → byte-identical to today (NFR-001).

### Dependencies

- Depends on WP02.

### Risks & Mitigations

- Routed-but-context-empty half-fix → T009 covers the context leg. Raw splice → forbidden (covered by WP05 gate).

---

## Work Package WP04: Agent-profile projection org visibility — #2166 (Priority: P1)

**Goal**: Projection emits the activation-admitted org agents to the host surface + manifest with a non-builtin `source_layer`, merged onto the existing project layer.
**Independent Test**: With an admitted org profile, it appears in the projection manifest (`source_layer != builtin`) and `.claude/agents/`; de-activated absent; built-in-only project unchanged.
**Prompt**: `/tasks/WP04-projection-org-visibility.md`
**Requirement Refs**: FR-006, C-008, NFR-001, NFR-002

### Included Subtasks

- [x] T011 RED test: admitted org profile projected with non-builtin `source_layer`; de-activated absent.
- [x] T012 Wire `tool_surface/profiles/projection.py::default_profile_repository` to merge the activation-admitted org subset onto the project layer.
- [x] T013 Regression test: no org packs → projection byte-identical to today.

### Dependencies

- Depends on WP02.

### Risks & Mitigations

- Manifest provenance correctness → assert `source_layer` in T011.

---

## Work Package WP05: Activation-bypass architectural gate (Priority: P2)

**Goal**: CI gate that fails if a routing/projection surface splices raw `org_dirs`/`resolve_org_roots` bypassing the activation filter (asserts the activation seam is used — not a fakeable `org_dirs`-presence proxy).
**Independent Test**: Self-mutation — inject a raw `AgentProfileRepository(org_dirs=resolve_org_roots(...))` into a routing surface → gate fails; revert → passes. Non-vacuous floor.
**Prompt**: `/tasks/WP05-activation-bypass-gate.md`
**Requirement Refs**: FR-008, C-003, C-008

### Included Subtasks

- [x] T014 Implement `tests/architectural/test_org_activation_seam.py`: enumerate routing/projection construction sites; assert each routes through the activation-aware seam; scoped allowlist of confirmed built-in-only sites with rationale.
- [x] T015 Self-mutation teeth test (inject violation → fail; revert → pass); concrete integer floor.

### Dependencies

- Depends on WP03, WP04.

### Risks & Mitigations

- Vacuous/inverted gate → assert the contract (activation seam), self-mutation test required. Over-scope → exclude `agent/tasks.py` + `charter/context` language cache with rationale.

---

## Work Package WP06: Unify activation-CLI pack layout with runtime (FR-013) (Priority: P2)

**Goal**: Make `charter activate/deactivate/list agent-profile` resolve org packs from the canonical flat `<pack>/agent_profiles/` layout (runtime layout), so activation no longer fails "Unknown agent-profile ID" against a runtime-resolvable pack.
**Independent Test**: Org pack laid out `<pack>/agent_profiles/<id>.agent.yaml`; `spec-kitty charter activate agent-profile <id>` succeeds (RED today). At least one other kind still resolves.
**Prompt**: `/tasks/WP06-activation-layout-unify.md`
**Requirement Refs**: FR-013, C-006

### Included Subtasks

- [x] T016 RED test: `charter activate agent-profile <id>` against a flat-layout org pack succeeds (currently "Unknown agent-profile ID").
- [x] T017 Move the activation org-layer resolution to the flat `<pack>/<plural>/` layout: drop the `(<root>/doctrine).is_dir()` gate in `charter/_layer_roots.py:24-26`; update `charter/pack_manager.py::_scan_layer_dirs` org-layer branch. Decide hard-cutover vs layout-tolerant (accept both, prefer flat).
- [x] T018 Regression test across ≥2 kinds (agent-profile + one other) for `charter list/activate/deactivate`.

### Dependencies

- None (Lane B; independent of WP02–05). Verify before the Lane B two-regime live proof.

### Risks & Mitigations

- Shared across all org-pack kinds → per-kind regression (T018). Backward-compat → consider layout-tolerant resolver.

---

## Work Package WP07: Promote override-adjudication to production (Priority: P2) 🎯 Lane C foundation

**Goal**: Move `find_overridden_builtin_urns` / `find_unsanctioned_overrides` / `UnsanctionedOverride` from `tests/architectural/test_builtin_override_policy.py` into `src/doctrine/drg/override_policy.py` (pure, fail-closed); re-point the test to import from production.
**Independent Test**: The promoted predicates are importable from `doctrine.drg.override_policy` and the existing override + DRG-merge tests pass unchanged.
**Prompt**: `/tasks/WP07-promote-override-adjudication.md`
**Requirement Refs**: FR-009, NFR-004

### Included Subtasks

- [x] T019 Promote the three symbols into `override_policy.py` with `__all__` updates; keep pure + fail-closed.
- [x] T020 Re-point `test_builtin_override_policy.py` (and any `test_drg_merge.py` use) to import from production; confirm green.
- [x] T021 Focused unit tests for the promoted predicates (sanctioned vs unsanctioned, malformed allowlist fail-closed).

### Dependencies

- None (Lane C foundation).

### Risks & Mitigations

- Breaking the existing governance test → T020 keeps it green by re-pointing imports, not deleting.

---

## Work Package WP08: Wire doctor doctrine override diagnostics (Priority: P2)

**Goal**: `spec-kitty doctor doctrine` reports unsanctioned built-in overrides in a deployed repo (org-packs-present branch), reusing the merged 3-layer DRG already built in `_doctrine_collect`; project-tier overrides stay ungoverned (documented).
**Independent Test**: Scratch repo with an org pack overriding a built-in node without a sanctioning allowlist entry → `doctor doctrine --json` flags it and `healthy=false`; with a sanctioning entry → not flagged.
**Prompt**: `/tasks/WP08-doctor-override-diagnostics.md`
**Requirement Refs**: FR-010, FR-012, NFR-001

### Included Subtasks

- [x] T022 RED test: `doctor doctrine --json` flags an unsanctioned override (healthy=false); sanctioned → silent; no org packs → unchanged.
- [x] T023 Wire the promoted predicates into the doctor doctrine org-packs-present branch (`doctor.py`/`_doctrine_collect.py`); thread findings into JSON + human emitters + `healthy`/exit code.
- [x] T024 Document the project-tier ungoverned boundary (FR-012) in the doctor output/help and a short doc note.

### Dependencies

- Depends on WP07.

### Risks & Mitigations

- New DRG plumbing → reuse `_doctrine_collect` load (C-006). Healthy repos flipping RC → guard with the no-packs short-circuit.

---

## Work Package WP09: Retire override-policy allowlists + lower baseline (Priority: P2)

**Goal**: Remove the 4 override-policy symbols from `_CATEGORY_C_BUILTIN_OVERRIDE_POLICY` and the module from `_CATEGORY_7_GRANDFATHERED_ORPHANS`; lower `category_7_grandfathered_orphans` 7 → 6; full `tests/architectural/` dry-run pre-PR.
**Independent Test**: With the runtime caller live (WP08), the dead-symbol/-module gates pass with the symbols/module removed and baseline at 6; full architectural suite green.
**Prompt**: `/tasks/WP09-retire-override-allowlists.md`
**Requirement Refs**: FR-011, C-004; references #2049 (one burn-down item, no sweep)

### Included Subtasks

- [x] T025 Remove the 4 symbols from `_CATEGORY_C_BUILTIN_OVERRIDE_POLICY` (`test_no_dead_symbols.py`) and `doctrine.drg.override_policy` from `_CATEGORY_7_GRANDFATHERED_ORPHANS` (`test_no_dead_modules.py`).
- [x] T026 Lower `tests/architectural/_baselines.yaml` `category_7_grandfathered_orphans` 7 → 6.
- [x] T027 Full `tests/architectural/` dry-run (incl. CI-only shards) — gate-unmask cannot self-validate (C-004); record result.

### Dependencies

- Depends on WP07, WP08.

### Risks & Mitigations

- Gate-unmask self-validation trap → full-suite dry-run (T027) before PR.

---

## Dependency & Execution Summary

- **Lane A**: WP01 (independent).
- **Lane B**: WP02 → {WP03, WP04} → WP05; WP06 independent (verify before B's live proof).
- **Lane C**: WP07 → WP08 → WP09.
- **Parallelization**: Lanes A/B/C run in parallel. Within B, WP03 ∥ WP04 after WP02; WP06 ∥ everything. Within C, strictly sequential.
- **MVP**: WP01 (P2 quick win) + Lane B WP02–04 (the P1 dispatch/projection fix) constitute the highest-value release; WP05/WP06/Lane C harden + close debt.

---

## Requirements Coverage Summary

| Requirement | Covered By |
|-------------|------------|
| FR-001, FR-002 | WP01 |
| FR-003, FR-007 | WP02 |
| FR-004, FR-005 | WP03 |
| FR-006 | WP04 |
| FR-008 | WP05 |
| FR-013 | WP06 |
| FR-009 | WP07 |
| FR-010, FR-012 | WP08 |
| FR-011 | WP09 |
| NFR-001 | WP03, WP04, WP08 |
| NFR-002 | WP03, WP04 |
| NFR-003 | all WPs |
| NFR-004 | WP02, WP07 |
| C-002, C-006, C-008 | WP02, WP03, WP04, WP05 |
| C-003 | WP05 |
| C-004 | WP09 |
| C-005 | all WPs (red-first) |
| C-007 | WP01, WP02 (real-format fixtures) |

---

## Subtask Index (Reference)

| Subtask | Summary | WP | Parallel? |
|---------|---------|----|-----------|
| T001–T003 | Charter doc-policy interpolation + tests | WP01 | within-WP |
| T004–T006 | Activation-aware org resolver + 3-regime tests | WP02 | within-WP |
| T007–T010 | Dispatch routing + context org visibility | WP03 | after WP02 |
| T011–T013 | Projection org visibility (#2166) | WP04 | ∥ WP03 |
| T014–T015 | Activation-bypass gate + teeth | WP05 | after WP03/04 |
| T016–T018 | Activation-CLI layout unify (FR-013) | WP06 | independent |
| T019–T021 | Promote override adjudicator | WP07 | Lane C root |
| T022–T024 | doctor doctrine override diagnostics | WP08 | after WP07 |
| T025–T027 | Retire allowlists + baseline 7→6 | WP09 | after WP08 |
