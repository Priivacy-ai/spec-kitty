# Adversarial Review Round 2: Architecture & Wiring
**Reviewer**: Architect Alphonso
**Date**: 2026-05-31
**Focus**: Layer rules, ProjectContext/OperationalContext module design, wiring completeness, dead-code risk, migration safety, contract consistency

---

## BLOCKING

### B-1. `src/specify_cli/context/` already exists as MissionContext identity resolution — FR-040 clobbers a live namespace

**Files**: `data-model.md` §Module Ownership, `src/specify_cli/context/__init__.py`

`data-model.md` specifies:
> `src/specify_cli/context/__init__.py` — Re-exports the charter-owned types; provides population factories

The existing `src/specify_cli/context/` package is a **fully operational, heavily tested** module for bound mission/WP identity resolution. Its public API exports: `MissionContext`, `ContextToken`, `resolve_context`, `resolve_or_load`, `load_context`, `save_context`, `context_callback`, `get_context`, `require_context`, and seven error types. It is imported from 12+ production files across `specify_cli.*` and multiple test files.

Adding `ProjectContext`, `OperationalContext`, and `ContextPreconditionError` to this package's `__init__.py.__all__` would:

1. **Merge two unrelated concepts** in one namespace: mission-lifecycle identity (WP code, mission slug) and charter/invocation runtime context (repo root, pack context, model, profile). These are entirely different domain objects.
2. **Import `charter.*` types into `specify_cli.context`**, changing the dependency profile of every module that currently imports from `specify_cli.context`. The existing package has no charter imports.
3. **Break the ratchet baseline** for `test_no_dead_symbols.py` categories — `OperationalContext` is "specced but not wired," meaning its appearance in `specify_cli.context.__all__` will immediately register as a dead symbol needing allowlisting.
4. **Confuse the naming**: `resolve_context` already exists in `specify_cli.context` as a MissionContext builder. A `build_project_context` factory in the same namespace would sit next to it with an entirely different return type and meaning.

**Resolution required**: FR-040 must designate a distinct package for the charter invocation context types. Options:
- `src/specify_cli/charter_context/` — new package with no existing claims
- `src/specify_cli/invocation/` — parallel to the charter module's name
- Instruct callers to import directly from `charter.invocation_context` (no re-export layer needed; `specify_cli.*` is allowed to import `charter.*`)

Do NOT extend `src/specify_cli/context/__init__.py` to include charter types. The existing package's semantics must remain coherent.

---

### B-2. `ProjectContextProtocol` fields mismatch: research.md specifies wrong fields for `MissionStepRepository`

**Files**: `research.md` §4 C-004 Fix, `src/doctrine/missions/mission_step_repository.py` lines 256, 289, 325, 347

`research.md` states:
> "Define a narrow `ProjectContextProtocol` in `src/doctrine/missions/` matching only the fields `MissionStepRepository` actually uses (likely `activated_mission_step_contracts` and `activated_mission_types`)"

This is **incorrect**. A code inspection of `mission_step_repository.py` confirms that the only `PackContext` fields accessed are:

- `pack_context.pack_roots` — lines 289, 312, 325 (org layer iteration)
- `pack_context.repo_root` — lines 256, 347 (project layer path construction)

Neither `activated_mission_step_contracts` nor `activated_mission_types` is accessed. These fields are activation-gate fields; the repository uses the context only for **path resolution** (which doctrine root dirs to scan).

`ProjectContext` (as defined in `data-model.md`) has `repo_root: Path | None` and `pack_context: PackContext | None`. It does **not** expose `pack_roots` directly. A structural Protocol that satisfies both mypy and the mission_step_repository call sites would need:

```python
class _PackContextLike(Protocol):
    pack_roots: tuple[Path, ...]
    repo_root: Path
```

This is a `PackContext`-shaped protocol, not a `ProjectContext`-shaped one. An implementer following `research.md`'s guidance and building a protocol with `activated_mission_step_contracts: frozenset[str] | None` would produce a protocol that `PackContext` does NOT structurally satisfy (those fields don't exist in the current `PackContext`), causing mypy errors.

**Resolution required**: Correct `research.md` §4 to specify a protocol with `pack_roots` and `repo_root` fields. Update FR-020 to reference the correct field names. Verify at implementation time which fields are used — the implementer must grep for all `pack_context.` accesses in the file, not rely on research guesses.

---

### B-3. Plan.md project structure omits `src/charter/invocation_context.py` and `src/specify_cli/context/factory.py`

**Files**: `plan.md` §Project Structure Source Code tree, `spec.md` FR-040

`spec.md` FR-040 is a **Must** requirement that creates `src/charter/invocation_context.py` and a factory module under `src/specify_cli/context/`. The `plan.md` project structure section lists every new source file explicitly but **neither file appears**. The plan tree under `src/charter/` shows:

```
├── packs/
│   └── default.yaml
├── pack_manager.py
└── consistency_check.py
```

No `invocation_context.py`. The `src/specify_cli/` tree shows no `context/factory.py` or any new `invocation/` package.

An implementer following the plan would miss both files entirely. The wiring tables in `research.md` (§2) reference `ProjectContext` threading but give no entry point telling the implementer where to create these modules. FR-040 is isolated from the plan's build output.

**Resolution required**: Add `src/charter/invocation_context.py` and the factory module (wherever it is decided to live after resolving B-1) to the plan's project structure tree. Add corresponding test files (`tests/charter/test_invocation_context.py`, `tests/specify_cli/test_project_context_factory.py`).

---

### B-4. `doctor.py:2332` is a confirmed fourth caller of `load_org_charter_policies` — absent from FR-037 and all wiring tables

**Files**: `src/specify_cli/cli/commands/doctor.py:2330–2332`, `spec.md` FR-037, `research.md` §2 Pattern B

The prior adversarial review (blocking issue #4) identified `doctor.py:2332` as a production caller of `load_org_charter_policies(repo_root)` without `pack_context`. This call has been **confirmed still present**:

```python
from specify_cli.doctrine.org_charter import load_org_charter_policies
policy = load_org_charter_policies(repo_root)  # line 2332 — no pack_context
```

`research.md` §2 Pattern B wiring table lists only three callers: `org_charter.py:660`, `org_charter.py:710`, `org_layer.py:161`. `FR-037` says "call sites that currently pass `pack_context=None`" — the doctor.py caller does not even pass it; it relies on the default. FR-037 does not enumerate call sites by file or line number, so an implementer has no guarantee they will find this caller.

**Severity**: `spec-kitty doctor` is a health diagnostic command that explicitly summarizes org charter policies. Running it after this mission's activation wiring without supplying `PackContext` silently shows the wrong policy picture (unfiltered, ignoring charter activation state).

**Resolution required**: Add `doctor.py:2332` explicitly to the FR-037 wiring table. Consider adding a acceptance criterion: grep for `load_org_charter_policies` in `src/` and assert every call supplies `pack_context`.

---

### B-5. `OperationalContext` will appear in `__all__` with zero production callers — guaranteed dead-symbol failure

**Files**: `data-model.md` §OperationalContext, `spec.md` Key Entities table, `spec.md` FR-040

`data-model.md` §OperationalContext explicitly states:
> "`OperationalContext` is **specced but not wired** in this mission — it is reserved for future context-aware activation filtering."

If `OperationalContext` is defined in `src/charter/invocation_context.py` and exported in `__all__`, the dead-symbols test (`test_no_dead_symbols.py`) will immediately flag it as a dead symbol — because the test scans all `__all__` entries and checks for non-test `src/` callers. There are none.

FR-024 says "12 newly-introduced symbols… are either wired to production call sites or **explicitly added to the allowlist with justification**." The spec does not enumerate what these 12 symbols are and does not name `OperationalContext` specifically, but `OperationalContext` plus its guard methods (`require_active_profile`, `require_active_role`) would be at least 3 of them.

Additionally, the ratchet baseline in `tests/architectural/_baselines.yaml` caps `category_a_slice_f_deferred` at 13. Adding `OperationalContext` and its methods requires either:
- Growing the baseline (requires YAML edit + justification comment per the baseline policy)
- Placing them in a separate category (requires new `_CATEGORY_C_WP_IN_FLIGHT_*` entry in the test file)

Neither is specified in FR-024, FR-040, or the plan.

**Resolution required**: FR-040 must specify the dead-symbol disposal strategy for `OperationalContext`. Options: (a) omit it from `__all__` with a comment "export when wired"; (b) add it to a new `_CATEGORY_C_WP_IN_FLIGHT_INVOCATION_CONTEXT` category with a justification and baseline bump. The implementation PR that adds it must also update `_baselines.yaml`.

---

### B-6. `activate` contract is silent on None-state materialization; `deactivate` contract has step 3 but `activate` has no equivalent

**Files**: `contracts/charter-activate-cli.md`, `contracts/charter-deactivate-cli.md`, `data-model.md` §CharterPackManager §charter activate flow

`contracts/charter-deactivate-cli.md` Behavior step 3:
> "If the activation field for `kind` is absent (no explicit activation set): exit 1 with message…"

`contracts/charter-activate-cli.md` has no corresponding step. Steps 3–8 read:
> 3. Read current activation state
> 4. Add `id` to the activation set for `kind` in config.yaml

Step 4 implies there is already an activation set to add to. `data-model.md` §CharterPackManager specifies:
> "If None: initialize to all built-ins [from `default.yaml`], then add"

But this materialization logic appears **only** in the data model's service description, not in the contract that implementers consult for the command behavior. An implementer writing `CharterPackManager.activate()` against only the contract would produce a `KeyError` or write a single-element list when the key is absent — not a properly initialized default set.

**Resolution required**: Add a step between current steps 3 and 4 in `charter-activate-cli.md`:
> "3.5. If `activated_<kind>` key is absent in config.yaml: materialize the initial activation set from `src/charter/packs/default.yaml` for that kind before adding `id`."

---

## SIGNIFICANT

### S-1. `specify_cli.context.__init__.py` re-export strategy has no concrete plan for `__all__` maintenance

**Files**: `data-model.md` §Module Ownership, `spec.md` FR-040

Even if B-1 is resolved by using a distinct package (e.g., `specify_cli.charter_context`), the data-model's description of the re-export pattern — "`specify_cli.*` functions import from `specify_cli.context` for construction and from `charter.invocation_context` for type annotations" — describes **two separate import paths for the same type**. This is unnecessary complexity.

If `specify_cli.*` modules need `ProjectContext`, they should import it from one place. Since `specify_cli` is allowed to import `charter.*` directly, callers can simply write:

```python
from charter.invocation_context import ProjectContext
```

There is no need for a `specify_cli`-layer re-export unless the factory functions (`build_project_context`) need to be co-located. The re-export layer adds an indirection with no architectural value unless `charter.*` is being replaced or mocked at the `specify_cli` boundary.

**Resolution required**: Clarify whether `specify_cli.context.factory` (or the equivalent) re-exports the types or only the factory functions. Remove the dual-import pattern description from the data-model.

---

### S-2. Migration `detect()` predicate based on a single key is fragile for partially-migrated projects

**Files**: `research.md` §5 Upgrade Algorithm, `spec.md` FR-002, FR-003

The proposed `detect()` logic:
> "project has `.kittify/` AND no `activated_directives` in config.yaml"

This predicate has two failure modes:

1. **Manual edit before migration**: A project where a developer manually added `activated_directives: [python-style-guide]` to config.yaml (testing the spec, or following documentation) before running `spec-kitty upgrade` would have `activated_directives` present but all other per-kind keys absent. `detect()` returns `False`; migration never runs; `activated_tactics`, `activated_styleguides`, `activated_paradigms`, etc. are never written. The project has a partially-populated activation state with inconsistent semantics.

2. **Multiple independent per-kind keys**: Using `activated_directives` as the sentinel is arbitrary. If the migration only needs to run when ALL per-kind keys are absent, the predicate should check for absence of all 8 new per-kind keys (or a canonical marker key). If it needs to run when ANY per-kind key is absent, the predicate becomes per-key and the migration becomes incremental.

The `m_3_2_7` precedent uses a single sentinel key (`mission_type_activations`) that is the ONLY key that migration writes — correct sentinel for that migration. But `m_3_2_8` writes 9 keys; a single-key sentinel creates the partial-migration trap.

**Resolution required**: Either:
- (a) Define `detect()` as: "at least one of the 8 per-kind keys is absent" (incremental per-key migration)
- (b) Define `detect()` with a canonical boolean flag key `"charter_pack_initialized": true` written by the migration as an idempotency marker
- Document that manual pre-migration edits of individual per-kind keys are "user owns the invariants" — but this must be an explicit decision, not a silent trap

---

### S-3. Behavioral asymmetry between `activated_kinds`/`activated_mission_types` and new per-kind fields on empty-list handling

**Files**: `spec.md` FR-039, `src/charter/pack_context.py:196–212`, `data-model.md` §CharterPack Invariant

FR-039 correctly removes the `and raw` guard for **new** per-kind readers. But the **existing** readers retain it:

- `_read_activated_kinds()` — `if isinstance(raw, list) and raw:` → `[]` → all 8 built-in kinds (fallback)
- `_read_activated_mission_types()` — same guard → `[]` → all 4 built-in mission types (fallback)

After this mission ships:

| config.yaml key | YAML value `[]` | Semantic |
|----------------|-----------------|---------|
| `activated_kinds` | `[]` | All 8 built-in kinds available (old reader kept) |
| `mission_type_activations` | `[]` | All 4 built-in mission types available (old reader kept) |
| `activated_directives` | `[]` | Zero directives available (FR-039 new reader) |
| `activated_tactics` | `[]` | Zero tactics available (FR-039 new reader) |

A user who sets `activated_kinds: []` to "restrict to no kinds" gets all built-ins. A user who sets `activated_directives: []` gets full restriction. Same YAML structure, opposite semantics — in the same config.yaml file.

Additionally: since `PackContext.activated_mission_types` is typed as `frozenset[str]` (never `None`), mission-type has no None state — it always returns a populated frozenset (defaults to all 4 if absent/empty). But the new per-kind fields would be `frozenset[str] | None`. This asymmetry is not flagged anywhere.

**Resolution required**: Document explicitly in the spec and data-model that `activated_kinds` and `mission_type_activations` retain the `and raw` guard (old behavior, for backward compatibility with existing config.yaml files) while new per-kind fields do not. Add this as a migration note for users who might assume symmetry. At minimum, add a comment to `pack_context.py` to prevent future contributors from "fixing" the apparent inconsistency.

---

### S-4. FR-023 description is imprecise: `m_3_2_7` requires a baseline bump, not just an allowlist entry

**Files**: `spec.md` FR-023, `tests/architectural/test_no_dead_modules.py`, `tests/architectural/_baselines.yaml`

FR-023:
> "The `m_3_2_7_activate_builtin_mission_types` migration (WP12) is added to the dead-modules architectural test allowlist"

`m_3_2_7` is auto-discovered (no static import), so it belongs in `_CATEGORY_1_AUTO_DISCOVERED_MIGRATIONS`. The test's dead-modules ratchet baseline (`_baselines.yaml`) currently shows:

```yaml
category_1_auto_discovered_migrations: 71
```

Adding `m_3_2_7` grows this to 72. Adding `m_3_2_8` (also auto-discovered) grows it to 73. Both growth events require a YAML diff to `_baselines.yaml` with a `# justification:` comment per the baseline policy (documented in the file's header). FR-023 says only "add to allowlist" — the implementer who follows this literally will see the ratchet test fail because the baseline was not bumped.

**Resolution required**: Update FR-023 to specify:
1. Add `specify_cli.upgrade.migrations.m_3_2_7_activate_builtin_mission_types` to `_CATEGORY_1_AUTO_DISCOVERED_MIGRATIONS`
2. Bump `category_1_auto_discovered_migrations` baseline from 71 to 73 (covers m_3_2_7 + m_3_2_8)
3. Add justification comment

---

### S-5. FR-024 does not enumerate the 12 dead symbols — implementers must discover them through test failure

**Files**: `spec.md` FR-024, `tests/architectural/test_no_dead_symbols.py`, `_CATEGORY_C_WP_IN_FLIGHT_CHARTER_SCOPE`

`_CATEGORY_C_WP_IN_FLIGHT_CHARTER_SCOPE` is currently `frozenset()` — the 12 symbols from Phase 1 are not in any allowlist category, meaning the dead-symbols test is actively failing on the branch. FR-024 says they must be "wired to production call sites or explicitly added to the allowlist." Neither their names nor their modules are listed.

An implementer cannot fulfill FR-024 without first running the test, reading the failure output, and triaging each symbol. This is the correct process, but the spec should state it explicitly rather than implying the symbols are known. The risk is that an implementer adds the 12 symbols to the allowlist category without wiring them — "technically" satisfying FR-024 while perpetuating the dead-code pattern.

**Resolution required**: FR-024 should state that the 12 symbols must be identified by running `pytest tests/architectural/test_no_dead_symbols.py`, then each must be individually triaged: wired if a natural caller exists in this mission's scope, or added to `_CATEGORY_C_WP_IN_FLIGHT_CHARTER_SCOPE` with per-symbol justification. The PR must show that wired symbols are removed from any temporary allowlist.

---

### S-6. FR-011 WP template reference scan has no implementation specification in the consistency-check contract

**Files**: `spec.md` FR-011, `contracts/charter-pack-consistency-check-cli.md` §Behavior, `data-model.md` §ConsistencyReport

FR-011:
> "`charter pack consistency-check` validates that every artifact in the charter pack exists in the active doctrine pack, and that **every artifact referenced by WP templates or base prompt templates is activated**"

The consistency-check contract's 4-step Behavior section covers only the first half (charter-pack-to-doctrine-catalog validation). There is no step that scans WP task files or prompt templates. The `ConsistencyReport` data model has fields for `unknown_references`, `missing_from_doctrine`, `kind_violations`, and `suggestions` — but no field for "artifact referenced in WP template but not activated."

Implementing FR-011's second half requires:
- Discovering all WP task file locations (`.md` files in `kitty-specs/*/tasks/`)
- Parsing frontmatter (agent_profile, etc.) and body references to artifact IDs
- Cross-referencing against the activated set

None of this is specified. An implementer who reads only the contract implements a passing test against the first half and never notices the second half is missing.

**Resolution required**: Either:
- (a) Add an explicit step 5 to the consistency-check contract that describes the WP template scan algorithm, and add a `template_reference_violations` field to `ConsistencyReport`
- (b) Descope the WP template scan from this mission and remove the second clause from FR-011

---

### S-7. `ContextPreconditionError` propagation to user-facing output is unspecified — RuntimeError will surface raw to CLI users

**Files**: `data-model.md` §ContextPreconditionError, `spec.md` FR-040

`ContextPreconditionError` inherits from `RuntimeError`. When `ctx.require_repo_root()` fires in a production path (e.g., a CLI command that received an improperly initialized `ProjectContext`), the exception propagates up the call stack. Unless the CLI command handler catches it, the user sees:

```
RuntimeError: Context precondition failed: 'repo_root' is required but absent in ProjectContext
```

The existing `require_repo_root()` function in `specify_cli.tracker.config` raises `TrackerConfigError` which is caught by CLI commands and converted to a user-facing Rich error panel (confirmed in `tracker.py` handlers). The new `ContextPreconditionError` has no equivalent catch-and-format path specified.

**Resolution required**: Specify that any CLI command entrypoint that calls guard methods must either:
- Catch `ContextPreconditionError` and convert to `typer.Exit(1)` with a Rich error panel, or
- Only call guard methods on a `ProjectContext` constructed via `from_repo()` which always populates all fields (making the guard a last-resort assertion, not a user-facing error path)

The latter is simpler but must be stated explicitly.

---

## MINOR

### M-1. `activated_mission_types` is `frozenset[str]` (not `frozenset[str] | None`) — the None-state invariant does not apply to mission-type

**Files**: `src/charter/pack_context.py:87`, `data-model.md` §PackContext

`PackContext.activated_mission_types` is typed `frozenset[str]` — it can never be `None`. The new per-kind fields (`activated_directives` etc.) will be `frozenset[str] | None`. The deactivate contract (step 3) says "if the activation field for `kind` is absent: exit 1." For `mission-type` specifically, this guard can never trigger because `from_config()` always returns a populated frozenset (defaulting to `_BUILTIN_MISSION_TYPE_IDS` when the key is absent).

The `CharterPackManager.deactivate(kind="mission-type", ...)` branch would need special handling or the PackContext design for mission-type needs to be homogenized with the other 8 kinds. Currently unaddressed.

---

### M-2. CascadeScope named values cover only 3 of 8 non-mission-type kinds; contract inconsistency with FR-007

**Files**: `data-model.md` §CascadeScope, `contracts/charter-activate-cli.md`, `contracts/charter-deactivate-cli.md`, `spec.md` FR-007

`data-model.md` CascadeScope table lists named values: `none`, `all`, `profiles`, `directives`, `tactics`. CLI contracts say `--cascade: all, profiles, directives, tactics, or comma-separated subset.` Named values for `styleguides`, `toolguides`, `paradigms`, `procedures` are absent.

FR-007 uses `--cascade all|<kind>[,<kind>...]` where `<kind>` is an activation kind name. Journey 4 uses `--cascade agent_profile,tactic` — `agent_profile` is not in the CascadeScope named values (only `profiles` is). The inconsistency between the FR's `<kind>` syntax and the CascadeScope table's named shortcuts is unresolved. An implementer cannot determine whether `--cascade styleguides` is a valid input or an error.

---

### M-3. `charter.drg::PackContext` re-export in `__all__` disposition undecided

**Files**: `src/charter/drg.py:81`, `spec.md` FR-024

`src/charter/drg.py:81` exports `"PackContext"` in `__all__`. No `src/` file imports `PackContext` from `charter.drg`; the natural import is from `charter.pack_context`. This is a dead re-export that the dead-symbols test likely flags. FR-024 says wire or allowlist 12 symbols; this symbol is a candidate for clean removal (remove from `__all__`) rather than allowlisting. The specification does not decide its fate.

---

### M-4. `config.yaml` has three inconsistent naming patterns for activation state — naming outlier undocumented

**Files**: `research.md` §10, `data-model.md` §config.yaml Schema Extension

- `activated_kinds` — kind-level gate, plural snake_case
- `mission_type_activations` — legacy mission-type key from Phase 1, inverted name order
- `activated_directives` / `activated_tactics` / etc. — new per-kind keys, plural snake_case

The naming outlier (`mission_type_activations` vs the expected `activated_mission_types`) exists because Phase 1 used a different naming convention. The spec notes this in `data-model.md` but does not specify whether it will be normalized in a future migration or permanently retained as a legacy name. This will be a persistent source of confusion for contributors reading config.yaml files. At minimum, a comment in `pack_context.py` should explain the discrepancy.

---

### M-5. FR-023 says "WP12 migration" but the migration is `m_3_2_7`, not a WP12 artifact

**Files**: `spec.md` FR-023

FR-023 reads: "The `m_3_2_7_activate_builtin_mission_types` migration (WP12) is added to the dead-modules architectural test allowlist." The parenthetical "(WP12)" implies this migration was introduced by WP12 of this mission. Looking at the code, `m_3_2_7` already exists on the branch (it is the predecessor migration in the existing `migrations/` directory, introduced by the Phase 1 mission). The reference to "WP12" in parentheses appears to be carry-over from the prior mission's WP numbering. This could mislead implementers into thinking WP12 of THIS mission creates the migration, when in fact it already exists and just needs to be added to the allowlist. Clarify or remove the "(WP12)" annotation.

---

### M-6. NFR-001 threshold mismatch: spec says p99, plan says p95

**Files**: `spec.md` NFR-001, `plan.md` §Performance Goals

`spec.md` NFR-001: "≤ 100ms p99". `plan.md` §Performance Goals: "≤ 100ms p95". A benchmark passing p95 with p99 at 150ms satisfies `plan.md` but fails `spec.md`. The spec is authoritative, but the plan is what implementers reference when writing benchmark test thresholds. The implementer writing `tests/specify_cli/next/test_runtime_bridge_dispatch.py` would set a p95 threshold from the plan. Correct `plan.md` to read "p99" to match the spec.

---

## VERIFIED

1. **`filter_graph_by_activation` has zero production callers**: Confirmed by grep of `src/`. Only appears in `charter/drg.py` itself (`__all__` declaration, definition, one internal call from `filter_graph_by_activation` body). Dead code diagnosis in prior review is accurate.

2. **`_node_is_activated` only checks `activated_kinds` and `activated_mission_types`**: Confirmed at `drg.py:654–663`. It has no code path that checks `activated_directives` or any per-artifact-ID field. FR-038 extension is correctly specified as required.

3. **FR-038 is now in the spec as a Must requirement**: `spec.md` FR-038 explicitly requires `_node_is_activated` extension to check per-artifact-ID frozensets. The prior blocking issue (no implementation path for per-artifact-ID filtering) is resolved by FR-038. RESOLVED from prior review.

4. **`data-model.md` now specifies `ProjectContextProtocol` for the C-004 fix**: The Protocol approach is architecturally sound for resolving the `doctrine.*` charter import. The prior blocking issue #2 is addressed, with the caveat in B-2 above (wrong field names in research.md).

5. **`from_repo()` factory safety in `charter.*`**: `ProjectContext.from_repo(repo_root)` calling `PackContext.from_config(repo_root)` is a same-package call (both in `charter.*`). No layer violation. `from_repo()` can resolve `org_root` by calling `doctrine.drg.org_pack_config.resolve_org_roots()` (charter→doctrine direction, allowed). `specs_dir` and `architecture_dir` are pure `Path` operations. VERIFIED safe.

6. **No circular import risk in the proposed layout**: `charter.invocation_context` imports `charter.pack_context` (same package). `specify_cli.charter_context` (or whatever the factory package becomes) imports `charter.invocation_context` (specify_cli→charter, allowed). `charter.*` does not import `specify_cli.*` (confirmed by grep). No cycle.

7. **Layer rule: `specify_cli.*` importing `charter.*` is the correct direction**: `test_layer_rules.py` enforces `kernel ← doctrine ← charter ← specify_cli`. `specify_cli.context.factory` importing `charter.invocation_context` is architecturally correct. VERIFIED.

8. **`m_3_2_8` migration version is valid**: `m_3_2_7` is the last migration; `m_3_2_8` is a valid patch-bump (micro increment by 1). Migration chain integrity test will pass for this version. VERIFIED.

9. **`PackContext.from_config()` does not import from `specify_cli.*`**: Confirmed. Uses only `ruamel.yaml`, `dataclasses`, `pathlib`, and `doctrine.drg.org_pack_config`. Layer-safe confirmed.

10. **`doctor.py:2332` confirmed still present**: Live code inspection confirms `load_org_charter_policies(repo_root)` is called at line 2332 without `pack_context`. This is a production caller not in any wiring table.

11. **`mission_step_repository.py` accesses `pack_context.pack_roots` and `pack_context.repo_root` — not activation fields**: Confirmed by code inspection. The research.md Protocol field list is wrong (see B-2).

12. **`m_3_2_7` is not in `_CATEGORY_1_AUTO_DISCOVERED_MIGRATIONS`**: Confirmed by reading `test_no_dead_modules.py`. The allowlist stops at `m_3_2_6`. FR-023's need is real.

13. **Ratchet baseline `category_1_auto_discovered_migrations` is 71**: Confirmed from `_baselines.yaml`. Adding m_3_2_7 + m_3_2_8 requires bumping to 73.

14. **`specify_cli.context` already exports `resolve_context`**: The existing `specify_cli.context.__init__.py` exports `resolve_context` as a MissionContext builder. Adding a charter context package with `build_project_context` to the SAME namespace is both a naming clash risk and a semantic pollution issue (see B-1).

15. **`_CATEGORY_C_WP_IN_FLIGHT_CHARTER_SCOPE` is `frozenset()`**: The dead-symbols test is failing on the branch for Phase 1 symbols. FR-024 addresses this correctly but without enumerating the symbols.

16. **FR-039 correctly targets only per-kind readers**: FR-039 removes `and raw` only for new per-kind fields, not for existing `activated_kinds` / `activated_mission_types`. The reader asymmetry (see S-3) is by design, but must be documented.

17. **Deactivate contract step 3 None-state guard is correctly specified**: `contracts/charter-deactivate-cli.md` Behavior step 3 correctly specifies exit-1 behavior when `kind` has no explicit activation set. The prior SIGNIFICANT issue #8 is resolved in the contract. The activate contract is the missing counterpart (see B-6).

18. **`test_no_tracked_test_feature_missions` is a pure git subprocess test**: It calls `git ls-files kitty-specs/test-feature-*` and asserts the result is empty. This test has no relation to charter activation logic; it's an orthogonal guard against accidentally committed test fixtures (FR-025). Correctly identified and scoped.

---

## SUMMARY TABLE

| Severity | Count | Top Item |
|----------|-------|----------|
| BLOCKING | 6 | B-1: `src/specify_cli/context/` already exists with different semantics — FR-040 must not extend it |
| SIGNIFICANT | 7 | S-1: re-export strategy pollutes existing namespace; S-2: migration detect() fails for partial manual edits |
| MINOR | 6 | M-1: `activated_mission_types` asymmetry; M-2: CascadeScope names incomplete; M-3: stale re-export |
| VERIFIED | 18 | from_repo() safety; layer rules; m_3_2_8 version validity; doctor.py:2332 confirmed |
