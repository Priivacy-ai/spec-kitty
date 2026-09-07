---
work_package_id: "WP02"
title: "Immutable owner operations and assessment dispatch"
dependencies: []
requirement_refs: ["FR-002", "FR-003", "FR-004", "C-001"]
subtasks: ["T006", "T007", "T008", "T009", "T010"]
owned_files:
  - src/specify_cli/tool_surface/operations.py
  - src/specify_cli/tool_surface/model.py
  - src/specify_cli/tool_surface/plan.py
  - src/specify_cli/tool_surface/repair.py
  - src/specify_cli/tool_surface/service.py
  - src/specify_cli/tool_surface/registry.py
  - src/specify_cli/tool_surface/providers/protocol.py
  - src/specify_cli/tool_surface/providers/_registry.py
  - src/specify_cli/tool_surface/providers/_discovery.py
  - tests/specify_cli/tool_surface/test_operations.py
  - tests/specify_cli/tool_surface/test_plan.py
  - tests/specify_cli/tool_surface/test_repair.py
  - tests/specify_cli/tool_surface/test_registry.py
create_intent:
  - src/specify_cli/tool_surface/operations.py
  - tests/specify_cli/tool_surface/test_operations.py
authoritative_surface: "src/specify_cli/tool_surface/"
execution_mode: "code_change"
agent_profile: "python-pedro"
role: "implementer"
agent: "codex"
---

# WP02: Immutable Owner Operations and Assessment Dispatch

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `codex`

The legacy skill maps to canonical `spk-doctrine-profile-load`.
Run the resolver-backed profile load and binding implement action context first.
Use direct warm binaries with `SPEC_KITTY_ENABLE_SAAS_SYNC=0`; never resync.

```sh
env SPEC_KITTY_ENABLE_SAAS_SYNC=0 .venv/bin/spec-kitty agent profile show python-pedro
env SPEC_KITTY_ENABLE_SAAS_SYNC=0 .venv/bin/spec-kitty charter context --action implement --json
```

Apply resolved initialization, boundaries, directives and tactics.
If #3908 still returns empty governance arrays/unavailable-directive diagnostics,
disclose degraded resolution and read binding charter/profile sources explicitly.
A success envelope is not evidence of complete doctrine activation.
Do not repair governance/configuration in this package.

---

## Objective

Deliver a small immutable owner-assessment contract and dispatch seam using
the existing tool-surface inventory, without inventing a second path catalog.
Preserve original provider context and separate pure assessment from explicitly
requested application so later owners can report exact physical effects.

## Context

Read `AGENTS.md` and `.kittify/charter/charter.md` before implementation.
Mission-local authority is `../spec.md`, `../plan.md`, `../data-model.md`,
`../research.md` and all files in `../contracts/`, relative to this prompt.
In particular, owner-operations.md fixes semantics, upgrade-plan.schema.json
fixes wire fields, and acceptance.md fixes independent observation requirements.
The parent external task-authoring-brief.md assigns exactly T006-T010 here.

This package has no WP dependency and can run beside WP01 and WP11.
Do not add a dependency on WP01 merely to import its unfinished harness.
WP01 owns independent oracle infrastructure and recorded public bug witnesses.
WP02 owns core protocol/value/dispatch correctness, not final product acceptance.
WP03-WP08 consume these APIs; WP10 composes upgrade assessment and CLI output.
WP09 keeps charter preparation below specify_cli without upward imports.
WP13 owns aggregate public subprocess/wheel/architecture acceptance.

Existing physical authorities:
- `src/specify_cli/tool_surface/plan.py:SurfacePlanBuilder` expands definitions.
- `registry.py:ToolSurfaceRegistry` stores tool/definition policy.
- `providers/_registry.py:SurfaceProviderRegistry` supplies registered providers.
- `providers/protocol.py:ReportingSurfaceProvider` is the existing interface.
- `repair.py:SurfaceRepairService` selects/group statuses and invokes owners.
- `service.py` composes existing registry/provider service entrypoints.

All abbreviated source paths below are relative to
`src/specify_cli/tool_surface/`; abbreviated test paths are relative to
`tests/specify_cli/tool_surface/`. Frontmatter paths are authoritative.
Do not modify concrete providers, installers, status.py, shared conftest or CLI.
Root startup stays unchanged in WP03; WP10 exclusively owns suppression and
validated-apply bootstrap wiring. No startup integration is required here.

Parent explicitly selected `src/specify_cli/tool_surface/` as the authoritative
surface. Ownership validation requires a prefix of at least one owned entry,
not a common prefix across source and tests. This remains a narrow package;
no codebase-wide exemption or manifest change is authorized.

Implementation entry, after parent dispatches:

```sh
env SPEC_KITTY_ENABLE_SAAS_SYNC=0 .venv/bin/spec-kitty agent action implement WP02 --agent codex --mission upgrade-preview-mission-health-01M1V6E1
```

### Subtask T006: Inspect and Tidy Existing Inventory/Repair Seams

**Purpose:** Establish the real authority chain and preserve behavior before
introducing values or dispatch. Do not replace the existing inventory.

**Steps:**
1. Read model.py, plan.py, repair.py, service.py and registry.py completely.
2. Follow provider registration/discovery through providers/_registry.py and
   providers/_discovery.py; identify where missing providers currently disappear.
3. Inspect existing test_plan.py, test_repair.py and test_registry.py.
4. Record how definitions become SurfaceInstance and SurfaceStatus objects.
5. Inspect SurfaceRepairService._group_by_provider and _apply; retain the
   provider-owned instance/hash/source context rather than rebuilding from IDs.
6. Identify existing doctor/init callers of repair before changing signatures.
7. Perform only behavior-preserving tidy-first changes needed for this seam.
   Keep this distinct from the functional red/green change and record rationale.
8. Characterize the existing missing-provider and shared-owner behavior through
   the real builder/dispatcher API before introducing a replacement method.

**Files:** Existing owned core modules and their three existing test modules.
Expect localized changes, not a package-wide redesign or registry migration.

**Validation:**
- Existing selected builder/repair/registry tests remain green after tidy-first.
- An attributable characterization demonstrates actual routing/context behavior.
- Tests call real service/builder methods, not a replacement inventory.
- Record pre-existing failures with the parent under charter policy.
- A new-method import error alone is not evidence of an existing product defect.

**Evidence:** Source SHA, exact test command/result and a short authority map.
No changes to concrete provider implementations belong in this step.

### Subtask T007: Add Immutable Operation and Assessment Values

**Purpose:** Supply leaf values owners can consume without import cycles or
a generic filesystem transaction framework.

**Steps:**
1. Create operations.py using stdlib-only immutable representations.
2. Represent FileState, PhysicalEffect, Disposition, Diagnostic, OwnerAssessment
   and OwnerApplyResult with the semantics fixed in owner-operations.md.
3. Include owner key, phase, root identity/relative path, all logical owners
   and surface IDs, before/after state, reason and exact ownership proof.
4. Represent observations/input fingerprints separately from ownership proof.
   A current content hash never establishes ownership by itself.
5. Keep prepared owner data opaque and immutable in-process; never serialize
   callbacks, mutable live config dictionaries or executable replay tokens.
6. Use tuples/frozen nested values, not a frozen outer shell around mutable lists.
7. Preserve explicit completeness and diagnostics; an empty effect tuple does
   not imply a complete successful no-op assessment.
8. Define create/update/delete/replace/retarget/chmod distinctions precisely.
   Created final mode is part of create; file bytes plus mode is one update.
9. Keep sampled times and final rendered bytes in prepared owner values.
   Dispatcher must not resample clocks or normalize hashes before application.
10. Keep effect identity stable under owner ordering/root normalization;
    exclude new volatile timestamp values from identity construction.

**Files:** New operations.py, small model.py integration if needed, and new
test_operations.py. Aim for compact value definitions, not hundreds of
serializer branches; report any size growth before designing another framework.

**Validation:**
- Mutation attempts against outer and nested values fail or cannot affect originals.
- Invalid action/state pairs and escaping relative paths are rejected explicitly.
- Distinct before-kind/link target/mode observations remain distinguishable.
- Completeness false survives an otherwise empty assessment.
- No imports of providers, runtime, CLI, upgrade, or filesystem writers from
  operations.py; importing values cannot discover providers or initialize assets.

**Evidence:** Focused tests and changed import graph. Full wire rendering is
WP10-owned; do not add unrelated legacy JSON fields or decisions here.

### Subtask T008: Add Assessment Protocol and Preserve Owner Context

**Purpose:** Add an upgrade-capable seam without forcing unrelated reporting
consumers to acquire a new mutation interface.

**Steps:**
1. Extend providers/protocol.py with a separate assessment/application protocol.
2. Keep ReportingSurfaceProvider behavior available to existing consumers.
3. Express assess(inputs, provider_owned_statuses) -> OwnerAssessment and
   apply(assessment, explicit_consent) -> OwnerApplyResult using the agreed
   opaque-prepared semantics, with idiomatic typing in this codebase.
4. Retain original provider-owned statuses and instances through service dispatch.
   Do not reconstruct file paths by splitting findings strings or surface IDs.
5. Carry projected config/manifest inputs without an overlay filesystem;
   concrete owners interpret and render their own formats.
6. Wire assessment selection through the existing registry/provider expansion.
7. If a selected required provider lacks assessment support, return explicit
   incomplete diagnostics; never silently shrink the selected provider set.
8. Preserve optional/not-applicable disposition policy rather than treating
   every unsupported advisory surface as a fatal global failure.
9. Keep existing repair consumers working while concrete owners migrate in
   later WPs; do not route ordinary repair to an unimplemented assessment method.
10. Document the staged boundary: missing support is honest incompleteness now;
    final complete same-version coverage is mandatory once owners integrate.

**Files:** providers/protocol.py, plan.py, service.py, registry.py and necessary
providers/_registry.py/_discovery.py glue; existing owned tests.
No concrete provider or status.py edits; retain context in dispatch values.

**Validation:**
- A selected required definition without an owner/assessment produces diagnostics.
- A supported test owner receives the original statuses and projected inputs.
- Legacy repair entrypoints still invoke their existing concrete owners.
- Optional disabled/advisory policy remains distinguishable from missing support.
- A test which removes a registered required owner must not turn green by
  reducing its expected set to whatever providers remain.

**Evidence:** Tests may use a minimal recording owner for protocol mechanics.
That double is not the public CLI acceptance oracle or proof that real owners
perform no writes; preserve that distinction in the review report.

### Subtask T009: Deterministic Deduplication and Recheck Dispatch

**Purpose:** Preserve one physical writer per path and ensure application does
not consume stale owner preparation or silently overwrite conflicting intent.

**Steps:**
1. In repair.py/core dispatch, group assessments by executable owner and root.
2. Deduplicate equivalent physical destinations while retaining every logical
   owner, surface ID and manifest-sharing context.
3. Use existing root identity/confinement observations; never follow a hostile
   symlink to decide that an escaping destination is safely shared.
4. Reject contradictory desired bytes/kind/mode for one destination explicitly.
   No last-writer-wins order and no synthetic merged write callback.
5. Emit deterministic ordering based on phase/owner/root/relative path.
6. Before invoking an owner's writer, require its whole-batch input/destination
   recheck under its existing lock where applicable.
7. Keep format-aware recheck and physical writing in the concrete owner.
   Core dispatch carries/enforces the boundary, not a second generic installer.
8. On precondition_changed, stop that batch before writes; require explicit fresh
   assessment rather than automatically retrying or bypassing via --yes.
9. Retain actual succeeded/failed/skipped IDs on partial I/O failure.
   Do not report all requested effects as applied or promise cross-owner rollback.
10. Preserve drift/custom-content dispositions and separate consent. Assessment
    cannot prompt or turn --yes into overwrite/mission-repair authorization.

**Files:** repair.py, model.py/operations.py only as needed for dispatch values,
test_repair.py and test_operations.py. Keep the change within owned modules.

**Validation:**
- Shared codex/vibe-style roots produce one physical operation with both owners.
- Input permutation preserves effect identity/order and all ownership references.
- Conflicting after states refuse application, not just print a warning.
- Changed observation before apply records conflict and zero batch writer calls.
- Apply failure after one recorded success yields a truthful partial result.
- Unchanged assessments do not invoke writers or refresh manifest dates.
- A deliberately bypassed recheck makes its negative control fail.

**Evidence:** Recording-owner mechanics are valid here; concrete on-disk race
and no-churn witnesses are required in downstream owner WPs and WP13.

### Subtask T010: Verify Values, Dispatch and Non-Vacuous Coverage

**Purpose:** Hand downstream owners a green, stable API with honest incomplete
states rather than claiming the unresolved public upgrade issues are fixed.

**Steps:**
1. Run the four owned test modules using the direct warm pytest binary.
2. Cover supported, missing-required, optional-disabled, conflict, unchanged,
   partial-failure and precondition-changed outcomes.
3. Exercise existing registered builder/repair entrypoints, not only new values.
4. Assert a nonempty concrete registry floor using known required kinds/owners;
   removal of an expected registration must fail a mutation control.
5. Test value-module import isolation without bootstrapping runtime assets.
6. Keep the final source-entrypoint/owner AST gate in WP13's owned file;
   do not create another architectural test file or duplicate acceptance harness.
7. Run the full affected tool-surface subsystem and relevant existing layer/import
   gates under the parent-approved isolated fixture policy.
8. Run changed-module Ruff and mypy, plus the calibrated fast suite required by
   repository policy; no defensive uv resync and no per-WP make test-full.
9. Publish exact signatures and one small in-memory assessment/apply example
   in the handoff, linking contracts rather than editing shared planning docs.
10. Record the stage limitation: existing concrete providers are upgraded by
    WP03-WP08; aggregate public preview/apply and wheel evidence land in WP13.

**Focused command, after environment-policy prerequisites:**
```sh
env SPEC_KITTY_ENABLE_SAAS_SYNC=0 .venv/bin/pytest tests/specify_cli/tool_surface/test_operations.py tests/specify_cli/tool_surface/test_plan.py tests/specify_cli/tool_surface/test_repair.py tests/specify_cli/tool_surface/test_registry.py -q
```

**Files:** The four owned test modules and their corresponding owned source.
Use actual returned test counts; do not predict a passing count in advance.

**Validation prerequisites:**
- Shell sync=0 is not an effective fixture lock: current shared conftest can
  override it. Use the parent-approved isolated policy; never disable conftest
  wholesale or edit it here. Flag=1 alone is not proof of hosted traffic.
- No host credentials, real home mutation or production network.
- Parent-authorized isolated test installs do not authorize production dependencies.
- Relevant baseline failures require tracking and explicit disposition, not xfail.
- Full CORE contract/architecture/E2E/terminal issue gates remain parent-owned.

## Definition of Done

- T006-T010 have individual evidence and supported event-sourced completion records.
- Pure values and registry-driven dispatch meet FR-002/003/004 and C-001.
- Required unsupported providers report incomplete, never false complete no-op.
- Existing reporting/repair behavior remains compatible at this delivery stage.
- No production filesystem transaction framework, parallel inventory or CLI policy.
- Exact owner context, deterministic deduplication and batch recheck are tested.
- Targeted/subsystem/lint/type results are recorded with commit and environment.
- Downstream owners receive documented API examples and completeness semantics.
- Independent reviewer approves actual code/tests, not this authored prompt.
- No full mission or public bug acceptance is inferred from WP02's green tests.

Use supported subtask recording only after each subtask actually meets its DoD:
```sh
env SPEC_KITTY_ENABLE_SAAS_SYNC=0 .venv/bin/spec-kitty agent tasks mark-status T006 --status done --mission upgrade-preview-mission-health-01M1V6E1
```
Repeat for T007-T010 with real evidence; never hand-edit status or fake tasks.md.
Parent owns package registration/finalization and canonical runtime advancement.

## Risks

- Import cycles: keep operations a stdlib-only leaf and protocol imports narrow.
- Staged provider support: incomplete is explicit; never break existing repair
  merely because downstream assessment methods are not implemented yet.
- Dedup hides ownership: retain logical owners and reject disagreeing after states.
- False purity: mock-owner tests prove dispatch only, not physical CLI behavior.
- Stale preparation: batch recheck is obligatory; no automatic force or retry.
- Scope creep: all concrete renderers/writers and finalizer/CLI remain other owners.
- Ownership: preserve the explicit source surface and exact owned-file list;
  do not use a broad overlap-check exemption as a workaround.
- Interrupted workers: preserved local test logs are not a completed handoff.

## Reviewer Guidance

Review T006-T010 against the real existing builder/registry/repair seams.
Demand a behavior-preserving tidy-first boundary and attributable failing-first
functional evidence; unknown-method errors do not reproduce the old defect.
Check that missing required providers cannot disappear from coverage.
Check deep immutability, no import-time discovery, and no hidden clock sampling.
Inspect shared-root/conflicting-after-state and recheck-bypass mutation controls.
Require truthful partial application and original status context retention.
Confirm concrete providers and root startup were not changed by this package.
Confirm no serialized executable plan, new dependency or status fabrication.
Keep WP02 stage approval distinct from WP01 oracle approval and WP13 product proof.
If an unavoidable edit touches another WP's owned file, stop for parent routing;
never silently overlap or broaden owned_files to finish faster.
All listed tests/gates are implementation obligations, not author-executed results.
