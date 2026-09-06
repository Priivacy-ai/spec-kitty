---
work_package_id: "WP09"
title: "Charter-owned provisioning preparation"
dependencies: ["WP01"]
owned_files:
  - "src/charter/activation/compiler.py"
  - "src/charter/activation/pack_manager.py"
  - "src/charter/activation/charter_yaml_io.py"
  - "tests/charter/test_pack_manager.py"
  - "tests/charter/test_charter_yaml_io.py"
  - "tests/charter/test_compiler_charter_yaml.py"
  - "tests/specify_cli/upgrade/test_upgrade_provisions_mission_type_activations.py"
requirement_refs: ["FR-001", "FR-002", "FR-003", "FR-004", "NFR-004", "C-001"]
subtasks: ["T043", "T044", "T045", "T046"]
authoritative_surface: "src/charter/activation/"
execution_mode: "code_change"
agent_profile: "python-pedro"
role: "implementer"
agent: "codex"
create_intent: []
---

# WP09: Charter-owned provisioning preparation

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `codex`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Extract read-only provisioning preparation into the three existing charter-owned
files. Existing writers apply the exact prepared bytes after rechecking inputs,
preserving comments, unowned sections, explicit-empty activation and pointer policy.

## Context

Audience: automation-agent implementing Python; independent maintainer reviewer.
This prompt describes future work. Prompt authoring runs no implementation,
runtime action, status change, commit, dispatch or product acceptance test.

Repository root checkout:
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty`.
Mission root:
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1`.
External task-authoring brief:
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/task-authoring-brief.md`.

Read the binding sources before implementation:

- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/AGENTS.md`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.kittify/charter/charter.md`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/wps.yaml`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/spec.md`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/plan.md`, D3, D5 and IC-07.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/data-model.md`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/research.md`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/contracts/owner-operations.md`, Provisioning Authority.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/contracts/acceptance.md`, P7 and focused boundary cells.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/contracts/upgrade-cli.md`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/contracts/upgrade-plan.schema.json`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/contracts/corpus-recovery.md` (excluded work).

Governance: author first loaded planner-priti and task charter context with
SPEC_KITTY_ENABLE_SAAS_SYNC=0. Planner Priti resolved as builtin; context had zero
references and empty directives/tactics with unresolved governance diagnostics.
Disclose #3908; this is an explicit charter fallback, not successful resolution.
The binding charter is the absolute charter.md above; resolved planner source:
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/packs/built-in/agent_profiles/planner-priti.agent.yaml`.
Apply its initialization: decompose, sequence, identify risks and acceptance;
do not implement, make architectural decisions or manage agents.
Directive 003 requires traceable decisions; scope rationale follows approved IC-07.
Planner resolution supplied no tactics; do not invent resolved tactic claims.

Implementer source, resolved as builtin in the preceding batch:
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/packs/built-in/agent_profiles/python-pedro.agent.yaml`.
Load it anew before implementation and apply its initialization/boundaries,
specification fidelity, locality/tidy-first, TDD, quality gates and canonical
authority. Apply bug-fixing-checklist, tdd-red-green-refactor and meaningful
test-scaffolding discipline. Real owner filesystem tests remain mandatory.
Keep Python >=3.11 compatibility; profile prose does not raise the repo floor.
No dependency changes, global installs, resync or governance activation repair.

WP01 alone is the dependency: consume its delivered independent snapshot and
transient-write observer after approval/done. Do not add WP02 as a dependency.
WP09 returns lower-layer values; WP10 wraps them into PhysicalEffect and handles
upgrade assessment, projected activation composition, diagnostics and finalizer.
This is IC-07's explicitly split charter sub-lane. No other WP owns these files.
A missing-key same-version fixture must be fully preparable, not called opaque
migration work. Whole public CLI purity/JSON integration belongs to WP10/WP13.

Authoritative surface is the explicit nonempty production prefix in frontmatter,
not an empty source/test common prefix (#2446). Ownership paths are exact
repository-relative manifest values; all root bindings in this prompt are absolute.
All seven literal owned files exist. Extend them; no new literal files planned,
so create_intent is empty. A later scope change requires parent reconciliation.

Production edits are restricted to compiler.py, pack_manager.py and
charter_yaml_io.py. Do not edit pack_context.py, default_pack.py, activation_engine,
charter package exports, CLI/upgrade/finalizer, tool_surface operations/providers,
shared conftest/preview_support, architecture gates, manifest/tasks.md/meta/state,
corpus or tracer files. Route necessary outside changes to their owner.
Parent owns external evidence placement, issue matrix, workflow and final gates.
Do not start WP10 or WP13, author another prompt, or dispatch another agent.

Future implementation entry command; prompt author must not execute:

```sh
SPEC_KITTY_ENABLE_SAAS_SYNC=0 /var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.venv/bin/spec-kitty agent action implement WP09 --agent codex --mission upgrade-preview-mission-health-01M1V6E1
```

Consume the resolver's absolute execution workspace. Never guess a lane/base.
Use its verified direct warm binaries; the commands below show this root binding
and must use the corresponding absolute execution paths when implementation starts.

### Subtask T043: Characterize legacy config/pointer-charter provisioning and missing-key red

**Purpose**: Witness current preservation/visibility gaps through existing seams.

**Files**:
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/tests/charter/test_compiler_charter_yaml.py`;
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/tests/charter/test_charter_yaml_io.py`;
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/tests/specify_cli/upgrade/test_upgrade_provisions_mission_type_activations.py`.
Add roughly 80-140 focused test lines; fixture helpers stay in these owned files.

**Steps**:

1. Trace compiler.provision_mission_type_activations to
   pack_manager.resolve_activation_write_target and its selected save function.
   Missing key seeds from load_default_mission_type_activations; key presence
   returns False, including explicit []. Do not use truthiness to classify absence.
2. Inspect _write_stranded_project and _write_pointer_charter_project in the
   upgrade tests. They establish supported schema and same-version/no-migration
   fixtures. Existing heal tests already pass their historical stranding checks;
   do not claim those green controls reproduce the current preview defect.
3. Build legacy and pointer fixtures missing only mission_type_activations.
   Include real comments, quoted values, indented block sequences, blank lines,
   block scalars and unrelated catalog/governance/metadata/override content.
   Preserve raw baseline bytes, mode and mtime for config and pointed target.
4. Add an existing-entrypoint missing-key regression using the real compiler
   provisioner. Require a nonempty seed at the resolved target AND byte-exact
   preservation of unrelated authored spans. Indented unowned sequences expose
   whole-document ruamel formatting changes that substring-only tests miss.
   Witness the actual failed preservation assertion on the unmodified base;
   do not label an unexecuted expectation or passing control RED.
5. Add a concrete existing-YAML-writer no-churn regression: call
   update_charter_yaml_section with the already-present activation values and
   require bytes, mode and mtime unchanged. Establish a distinct fixture mtime
   before measuring so an unconditional write cannot hide in timer granularity.
   Current code opens for write unconditionally; record the real failing assertion.
6. Retain original public same-version missing-key preview/apply omission evidence
   from WP01, or capture it through the real absolute console entry in isolated
   fixtures. Observe actual config/charter writes, not just a pending Boolean.
   The current replacement Typer _test_app and patched surface repair are narrow
   historical unit/integration controls, not public preview-purity evidence.
7. Commit witnessed owner regression tests separately before functional changes
   through the parent's authorized implementation workflow. Record baseline SHA,
   exact argv/cwd, failure reason, exit and bytes/snapshot provenance.
   Missing imports, unknown --plan-json or nonexistent new APIs are not defect RED.
8. Inspect the touched seams for complexity and test friction. Perform focused
   behavior-preserving tidy-first extraction as a distinct step before the fix.
   Keep existing pointer/empty/create-gate controls; no broad compiler cleanup.

**Validation**: At least one missing-key preservation regression fails through
the existing provisioner for the intended reason; the no-churn writer regression
also has a real witness. Reviewer can replay red tests on the planning base.
No xfail, skip, fixture that stubs the writer, or invented public success.

### Subtask T044: Extract preparation in charter-owned compiler/pack-manager/YAML seams

**Purpose**: Prepare exact target bytes and projected activation without writing.

**Files**:
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/src/charter/activation/compiler.py`;
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/src/charter/activation/pack_manager.py`;
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/src/charter/activation/charter_yaml_io.py`;
owned tests above plus `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/tests/charter/test_pack_manager.py`.
Aim for roughly 120-220 source lines split by existing ownership; no new module.

**Steps**:

1. Keep compiler as the missing-key/seed authority. Extract preparation from
   provision_mission_type_activations; read the real shipped default through the
   existing loader only when the key is absent. Never seed all four by hand.
   Missing/broken default must fail closed, never silently produce an empty seed.
2. Preserve resolve_activation_write_target as the one write-target authority.
   Factor its read/resolve data seam for preparation without invoking its saver;
   preserve its existing triple-return API for unrelated callers as needed.
   Reuse resolve_charter_yaml_pointer; no second pointer parser.
3. Preserve the actual pointer policy: absent/non-string charter values are
   legacy inline config; only strings denote relative or absolute pointers.
   Pointer projects target their configured charter, not a guessed default path.
   Dangling/unreadable string pointers fail; never seed config as fallback.
4. Do not construct PackContext to discover the missing-key decision: its
   activation read is the fail-closed state provisioning is intended to repair.
   Supply explicit immutable projected activation values for subsequent consumers.
   Keep absent, explicit-empty and present custom lists distinguishable.
5. YAML I/O retains OWNED_SECTIONS and derives activation keys from the canonical
   ACTIVATION_YAML_KEYS vocabulary. Validate section/key membership before any
   mutation; activation is flat keys, never a new nested activation mapping.
6. Extract pure in-memory section preparation and byte rendering from
   update_charter_yaml_section/save_charter_yaml. Preserve round-trip metadata,
   comments, quote style, key order and unowned content; do not convert the
   only authoritative round-trip document to a plain dict before rendering.
7. Fix observed whole-document formatting drift locally in this YAML owner.
   Keep exact unowned spans intact when rendering the selected activation change;
   a surviving comment substring or equivalent decoded YAML is insufficient.
   Do not add a parallel YAML serializer or regex-based key policy in upgrade.
8. Return a bounded immutable lower-layer prepared value: resolved target,
   exact before/desired bytes and intended mode/kind, immutable projected
   activation data, change/no-op reason and source/input observations.
   Include config/pointer, target and shipped seed identity needed for recheck.
   Mutable ruamel maps, callbacks and generic virtual filesystems are not the payload.
9. Expose any required absent parent paths and ownership/section basis as
   charter data so WP10 can wrap all persistent operations. No PhysicalEffect,
   OwnerAssessment, tool_surface, specify_cli or CLI imports in charter,
   including annotation/TYPE_CHECKING dependencies.
10. Preparation performs only reads and in-memory work: no mkdir/open-for-write,
    temp file, save, backup, lock creation, compile-and-write, network or prompts.
    Do not call merge_defaults: it seeds all kinds and backs up charter.md.
    Do not call write_compiled_charter: it refreshes catalog/metadata and may
    bootstrap the bundle/pointer, exceeding this missing-key repair.

**Validation**: Missing-key preparation is nonempty and complete for both layouts.
Independent observer finds zero writes, including transient attempts.
Existing key (especially []) produces unchanged preparation without seed reads
or timestamp changes. Invalid inputs fail with preserved files and typed reasons.

### Subtask T045: Existing writers consume prepared bytes; no upward tool_surface import

**Purpose**: Apply the owner's prepared bytes with unchanged policy and safe rechecks.

**Files**: The exact three production files named in T044; existing owned
pack-manager, compiler and YAML I/O tests. Roughly 80-150 implementation/test lines.

**Steps**:

1. Route provision_mission_type_activations through prepare then apply, preserving
   its public Boolean: True only when a missing key was actually written,
   False for an authored existing key. Propagate owner errors, not empty success.
   Preserve the compiler/pack-manager lazy-import cycle-breaking seams.
2. Legacy config writes use pack_manager's existing ruamel serialization authority;
   pointed charter writes use charter_yaml_io's validated activation preparation.
   Existing save/update entry points consume the shared prepared byte path.
   Do not re-load and re-render different bytes after assessment.
3. Recheck the entire provisioning input set before the first write: config bytes
   and pointer form/target, target bytes/kind/mode/mtime, source/default identity,
   absence observations and parent path/link state. Detect same-byte rewrites too.
   Changed inputs refuse the batch; require explicit reassessment, no force retry.
4. Preserve configured relative/absolute target semantics while observing their
   identity. Reject escaping/replaced parent links before following a write;
   use existing kernel path authorities rather than inventing a second resolver.
   Do not silently retarget an unsafe pointer to the repository default.
5. Apply exactly retained bytes with the existing writer boundary, preserving
   file mode. No writes on validation/recheck failure or unchanged preparation.
   Retain atomic/locking behavior where already present; report actual I/O errors.
   No cross-file/cross-owner rollback guarantee or generic transaction engine.
6. Expose bounded execution-artifact details to WP10 if existing writes create
   transient temp/lock nodes; include persistent directories/locks in prepared
   data. The missing-key path must not create charter.md, backups, references,
   config pointers, catalog refreshes or metadata generation timestamps.
7. WP10 alone imports these lower-layer APIs, converts intended changes to
   PhysicalEffect and rechecks config/pointer plus target before delegation.
   Hand off exact value fields, changed/no-op/error semantics and caller examples
   in parent review context; do not edit WP10 source or add dependency on WP02.
8. Existing non-upgrade writers may prepare immediately before saving through
   the same seam. Keep activate/deactivate/merge_defaults and charter generation
   behavior outside the changed missing-key path intact; no opportunistic policy
   rewrite of their backups, catalog refresh or activation semantics.
9. Maintain __all__ in each changed charter module. Export only actual APIs
   consumed by production; private helpers remain private. Run the existing
   dead-symbol/layer checks without exemption growth or an upward import.
   If a production consumer is staged in WP10, report the exact pending symbol
   handoff honestly; coordinate final gate evidence rather than fake a caller.

**Validation**: Prepare at one instant and apply later; byte hashes agree exactly,
without timestamp normalization. Mutating pointer, target, seed or parent separately
causes zero writes and a clear precondition failure. Inject a specific write error
only for the failure test; normal plan/apply witnesses use real writers.

### Subtask T046: Comments/unowned sections, explicit-empty, dangling-pointer and byte-exact tests

**Purpose**: Prove owner-level purity, completeness, preservation and idempotence.

**Files**: All four owned test files; extend roughly 120-180 lines with reusable
local fixture helpers. Consume WP01 preview_support without edits.

**Steps**:

1. Exercise legacy config and pointer charter independently with a missing key,
   explicit [], custom nonempty list and malformed required document. Include a
   non-string inline charter namespace and a non-default pointer destination.
   Keep the real seed loader and writer in positive witnesses.
2. For missing-key cells require exact nonempty projected defaults and one target
   content change; pointer config bytes/mode/mtime stay untouched. Validate the
   persisted activation with the existing read authority after application.
   Never derive the expected target from the prepared value under test.
3. Verify the complete intended-versus-actual physical delta with WP01's independent
   lstat/hash/readlink/mode/mtime oracle, including any absent parent creation.
   Build expected paths from fixture policy. Omit no ignored file, config,
   authored companion, directory, backup or cache from the snapshot.
4. For pointed charters compare complete unowned spans, comments and metadata
   bytes, not only parsed values. For legacy config retain unrelated keys and
   inline namespaces exactly. No time fields need normalization in this repair.
   Applied bytes must equal prepared bytes and their SHA-256 exactly.
5. For both layouts, explicit [] and custom lists remain unchanged and do not
   load defaults or prompt. Null/scalar invalid activation values must not be
   silently coerced to defaults; preserve them and surface validation where
   required by the existing authority. Do not widen this into schema migration.
6. After one successful provision, prepare/apply twice more. Both are no-ops
   with unchanged bytes, link types, mode and mtime across all roots.
   Replay existing update/save no-churn regression on the final shared writer.
7. Test dangling, unreadable and malformed pointed targets; malformed config
   and missing/invalid seed. Require diagnosed failure, zero writes and no
   legacy fallback. Existing historical pending=True CLI predicate is a limited
   compatibility signal, not a complete successful upgrade plan.
8. Test target/config/source races and parent-link replacement after preparation.
   All sentinel link targets remain inside disposable sandbox roots.
   Refusal must precede even mkdir or opening the destination for write.
9. Negative controls must fail the relevant assertions: omit target change,
   swap pointer destination, change unowned comment/sequence bytes, treat [] as
   missing, resave unchanged content, or alter prepared bytes before apply.
   Mutate only disposable copies/expected-input controls, not shared source.
10. Keep real existing-entrypoint RED and GREEN command evidence. Preserve
    historical create-gate/upgrade controls, but do not use their patched
    _test_app path to claim public subprocess purity. Supply WP10/WP13 the
    owned P7 legacy/pointer fixtures and exact assertions for integrated checks.

**Validation**: Run all changed tests, full owning charter and upgrade-test
subsystem selections, make test-fast, changed-source/test Ruff and strict mypy,
and the existing charter-no-specify_cli/layer/dead-symbol gates.
No gate or product test has been run by this prompt author.

Before tests, use WP01/parent-approved isolation: disposable HOME/USERPROFILE,
all XDG/APPDATA/LOCALAPPDATA/SPEC_KITTY_HOME/temp roots; no global test assets.
Resolve binaries absolutely before rebinding child home; set child sync=0 last.
Use PYTHONDONTWRITEBYTECODE=1 and GIT_OPTIONAL_LOCKS=0 for source observations.
The acceptance contract records an autouse sync=1 override: verify effective
sync-off after fixtures, using the parent's approved harness policy.
Do not edit shared conftest, disable it wholesale, skip tests or treat that
override as a waiver. No network/host credentials or dependency resync.

Reference commands, after isolation is established in the resolved workspace:

```sh
SPEC_KITTY_ENABLE_SAAS_SYNC=0 /var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.venv/bin/pytest /var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/tests/charter/test_pack_manager.py /var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/tests/charter/test_charter_yaml_io.py /var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/tests/charter/test_compiler_charter_yaml.py /var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/tests/specify_cli/upgrade/test_upgrade_provisions_mission_type_activations.py -v -ra -p no:cacheprovider
SPEC_KITTY_ENABLE_SAAS_SYNC=0 /var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.venv/bin/pytest /var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/tests/charter/ /var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/tests/specify_cli/upgrade/ -v -ra -p no:cacheprovider
SPEC_KITTY_ENABLE_SAAS_SYNC=0 make -C /var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty test-fast
SPEC_KITTY_ENABLE_SAAS_SYNC=0 /var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.venv/bin/ruff check /var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/src/charter/activation/compiler.py /var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/src/charter/activation/pack_manager.py /var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/src/charter/activation/charter_yaml_io.py
SPEC_KITTY_ENABLE_SAAS_SYNC=0 /var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.venv/bin/mypy --strict /var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/src/charter/activation/compiler.py /var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/src/charter/activation/pack_manager.py /var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/src/charter/activation/charter_yaml_io.py
SPEC_KITTY_ENABLE_SAAS_SYNC=0 /var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.venv/bin/pytest /var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/tests/architectural/test_charter_no_specify_cli_import.py /var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/tests/architectural/test_layer_rules.py /var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/tests/architectural/test_no_dead_symbols.py -v -ra -p no:cacheprovider
```

Include changed test files in static checks per repository config; use direct
warm binaries only. No make test-full or whole-repo pytest for this scoped WP.
Shared/architectural changes would require parent scope revision and full
architecture checks; do not edit gates to avoid that requirement.
Record exact commands, baseline/final SHA, counts, failures and evidence paths.
Pre-existing failures require tracked parent disposition under charter policy;
no retry-to-green, xfailed product bugs, skip waivers or fabricated pass.
Report unsupported platform/mode/link coverage; obtain capable-platform evidence.

## Definition of Done

- T043: real missing-key preservation and existing-writer no-churn RED retained.
- T044: pure preparation in the exact three owners, complete lower-layer values.
- T045: existing writers apply prepared bytes with input recheck and no upward import.
- T046: nonempty exact delta equality, policy/preservation controls and no-churn GREEN.
- FR-001: preparation has zero persistent/transient mutations.
- FR-002/003: intended target/bytes/supporting paths agree with observed application.
- FR-004: repeat provisioning and unchanged section update do not rewrite.
- NFR-004/C-001: authored content survives and canonical authorities remain single.
- Focused/subsystem/static checks and independent review evidence are reported.
- Public upgrade integration remains WP10/WP13 work; do not claim mission completion.

Per-subtask completion evidence is the canonical event-sourced
`spec-kitty agent tasks mark-status <Txxx> --status done` record, not a checkbox.
Only after verified implementation evidence, record each completed subtask.
These exact future commands are instructions, not actions for prompt authoring:

```sh
SPEC_KITTY_ENABLE_SAAS_SYNC=0 /var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.venv/bin/spec-kitty agent tasks mark-status T043 --status done --mission upgrade-preview-mission-health-01M1V6E1
SPEC_KITTY_ENABLE_SAAS_SYNC=0 /var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.venv/bin/spec-kitty agent tasks mark-status T044 --status done --mission upgrade-preview-mission-health-01M1V6E1
SPEC_KITTY_ENABLE_SAAS_SYNC=0 /var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.venv/bin/spec-kitty agent tasks mark-status T045 --status done --mission upgrade-preview-mission-health-01M1V6E1
SPEC_KITTY_ENABLE_SAAS_SYNC=0 /var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.venv/bin/spec-kitty agent tasks mark-status T046 --status done --mission upgrade-preview-mission-health-01M1V6E1
```

These commands resolve the canonical status surface and may auto-commit events.
Do not replace them with manual tasks.md/frontmatter/state/event edits,
--no-auto-commit bypasses, invented lane state or self-issued review verdicts.

## Risks

- Whole-document YAML dump may reformat unowned spans; test exact bytes.
- Explicit-empty is a deliberate opt-out; missing-key tests must use membership.
- Mutable round-trip objects must not leak into supposedly immutable preparation.
- Resolving only the target misses pointer/config races; observe and recheck both.
- General bundle generation/merge_defaults adds unrelated writes; never use it here.
- Upward DTO imports violate layering; WP10 performs the adapter work.
- New APIs without real production consumers fail dead-symbol checks; coordinate honestly.

## Reviewer Guidance

Replay real pre-fix failure and final green assertion with their exact provenance.
Trace compiler policy to pack-manager target selection and YAML-owned rendering.
Require missing-key nonempty witnesses in both layouts and exact unowned bytes.
Check custom/empty lists, inline namespace, absolute/relative pointer and refusal cases.
Verify observer coverage includes transient writes and no-op mtimes.
Reject fake public purity from a replacement Typer app or patched production owner.
Confirm WP10 can consume immutable bytes/projected values without duplicating policy.
Reject upward imports, guessed paths, extra source files or manual runtime state.
Independent reviewer reports findings to parent; no self-approval or WP13 start.
