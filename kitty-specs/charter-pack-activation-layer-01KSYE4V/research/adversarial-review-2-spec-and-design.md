# Adversarial Review Round 2: Spec & Design
**Reviewer**: Claire (Spec & Design Reviewer)
**Date**: 2026-05-31
**Focus**: Internal consistency, completeness, implementability

---

## BLOCKING

### B-1. `CharterPackManager` method signature contradicts itself in two places in the same file

**File**: `data-model.md`, §CharterPackManager

The Key Methods block at line 108 declares:
```
activate(repo_root, kind, artifact_id, cascade) -> ActivationResult
```
The usage example at line 153 (under `ProjectContext`) declares:
```python
def activate(ctx: ProjectContext, kind: str, artifact_id: str, ...) -> ActivationResult:
    repo_root = ctx.require_repo_root()
```
The State Transitions flow diagram at line 252 calls:
```
→ CharterPackManager.activate(repo_root, "directive", "python-style-guide", CascadeScope.none)
```

Three representations of the same method exist in one document with incompatible first parameters: `repo_root: Path`, `ctx: ProjectContext`, and `repo_root` again. FR-040 says "all wiring sites introduced in this mission accept `ProjectContext` as their primary context parameter," which implies the `ctx: ProjectContext` form is canonical — but the Key Methods block and the state-transition pseudocode both pass `repo_root` directly.

An implementer cannot determine from this document whether `CharterPackManager.activate` takes `repo_root` or `ctx`. If it takes `ctx`, the state-transition flow pseudocode and Key Methods signatures must be updated. If it takes `repo_root`, FR-040 and the usage example are wrong. The contradiction is directly in the data model section an implementer will use as their reference for the service contract.

**Also**: `ActivationResult` and `MergeResult` appear as return types of `activate`, `deactivate`, and `merge_defaults` but are never defined anywhere in `data-model.md`, `spec.md`, or the CLI contracts. Neither their fields nor their module location is specified. An implementer must invent both types.

---

### B-2. `FR-040` says `OperationalContext` is "specced" in this mission but does not say it has zero required call sites — an implementer will try to wire it

**Files**: `spec.md` FR-040, `data-model.md` §OperationalContext

FR-040 text: "A new `src/charter/invocation_context.py` module is created defining `ProjectContext`, `OperationalContext`, and `ContextPreconditionError`; a `src/specify_cli/context/` package re-exports these types and provides population factories."

`data-model.md` §OperationalContext says: "`OperationalContext` is **specced but not wired** in this mission — it is reserved for future context-aware activation filtering."

The FR says "provides population factories" and the module table says `factory.py` provides `build_operational_context(...) -> OperationalContext`. These statements together imply `build_operational_context` is in scope for this mission. FR-040 does not contain any phrase like "zero required call sites" or "define only, do not wire." An implementer reading the FR as their implementation contract will create `build_operational_context`, attempt to wire it into at least one call site, and then encounter that no call site exists — or, worse, create a call site that is architecturally incorrect.

Additionally, `OperationalContext` introduces public symbols (`OperationalContext`, `build_operational_context`, `require_active_profile`, `require_active_role`) that will be flagged as dead by `test_no_dead_symbols.py`. FR-024 covers 12 already-identified dead symbols; it is silent on whether `OperationalContext`-family symbols are expected to be dead and should be pre-listed in the allowlist.

**Resolution required**: FR-040 must explicitly state: "OperationalContext is defined (class body and guard methods only) with zero required production call sites in this mission; `build_operational_context` is a stub returning an empty `OperationalContext()`; all four `OperationalContext`-family symbols are added to the dead-symbols allowlist with justification `'specced, wiring deferred'`."

---

### B-3. `ProjectContext.from_repo()` behaviour is entirely unspecified

**File**: `data-model.md` §ProjectContext

The factory is declared as:
```python
@classmethod
def from_repo(cls, repo_root: Path) -> "ProjectContext":
    """Construct a fully-populated ProjectContext from a repository root."""
```

Nothing in `data-model.md`, `spec.md`, or `research.md` specifies:
- What happens when `repo_root` does not contain a `.kittify/` directory (no config.yaml, no charter). Does it return a `ProjectContext` with `pack_context=None`? Does it raise? Does it raise `ContextPreconditionError`?
- How `org_root` is resolved (from config.yaml? from environment? from `.kittify/config.yaml` org key?).
- How `specs_dir` is resolved (`repo_root / "kitty-specs"`? configurable?).
- How `architecture_dir` is resolved (`repo_root / "architecture"`? configurable?).

Two fields — `specs_dir` and `architecture_dir` — have no corresponding guard methods in the guard-methods list (only `require_repo_root`, `require_pack_context`, `require_org_root` are listed). If callers need these fields to be non-None, they cannot guard them — the guard contract is incomplete.

The module table says `factory.py` provides `build_project_context(repo_root: Path) -> ProjectContext`. It is unclear whether `ProjectContext.from_repo()` and `build_project_context()` are identical, one calls the other, or they have different semantics. Two construction paths for the same type with no specified relationship is an implementer trap.

---

### B-4. `CascadeScope` named values in both CLI contracts cover only 3 of 8 non-mission-type kinds; Journeys 3–5 use cascade tokens that are not in the CascadeScope table

**Files**: `spec.md` Journeys 3–5, `spec.md` FR-007, `data-model.md` §CascadeScope, `contracts/charter-activate-cli.md` Arguments, `contracts/charter-deactivate-cli.md` Arguments

**Round 1 finding (S6) remains open.** The prior review identified this. It is NOT resolved.

`data-model.md` CascadeScope table defines named cascade values: `none`, `all`, `profiles`, `directives`, `tactics` (5 entries). `styleguide`, `toolguide`, `paradigm`, `procedure` have no named cascade values.

Both CLI contracts (`charter-activate-cli.md:15` and `charter-deactivate-cli.md:15`) list the `--cascade` argument description as: "Cascade scope: `all`, `profiles`, `directives`, `tactics`, or comma-separated subset." That is still the old 4-value set, unchanged from Round 1.

`spec.md` Journey 3 (line 89) uses `--cascade agent_profile,tactic`. Journey 4 (line 94) uses `--cascade agent_profile,tactic`. Journey 5 (line 102) uses `--cascade agent_profile`. In all three, `agent_profile` (with underscore) is used as a cascade token — but the CascadeScope table only has `profiles` (plural, no underscore). There is no entry for `agent_profile` or `agent-profile`.

FR-007 says `--cascade all|<kind>[,<kind>...]` accepts "any combination of the nine activation kind names." The CascadeScope table does not map any of `styleguide`, `toolguide`, `paradigm`, `procedure`, `agent_profile`, `mission_step_contract` to a named value. An implementer cannot implement a parser for `--cascade` that satisfies both FR-007 and the Journeys without inventing the mapping themselves.

**Specific contradictions**:
1. Journey uses `agent_profile` (underscore); CascadeScope table has `profiles` (plural); CLI kind table has `agent-profile` (hyphen). Three different tokens for one concept.
2. `styleguide`, `toolguide`, `paradigm`, `procedure` are not cascade-addressable by name per the CascadeScope table, but FR-007 says they must be.
3. The CLI contracts' `--cascade` argument description does not match FR-007 or the Journeys.

---

### B-5. `doctor.py:2332` is a 4th `load_org_charter_policies()` caller; it is absent from `research.md` and from FR-037

**Files**: `research.md` §2 Pattern B, `spec.md` FR-037, prior `adversarial-review-architecture-and-wiring.md` blocking item 4

FR-037 says: "all call sites of `load_org_charter_policies()` that currently pass `pack_context=None` are updated."

`research.md` §2 Pattern B lists exactly 3 callers: `org_charter.py:660`, `org_charter.py:710`, and `org_layer.py:218,236`. The prior architecture review (blocking item 4) confirmed a 4th caller: `src/specify_cli/cli/commands/doctor.py:2332`, which calls `load_org_charter_policies(repo_root)` without `pack_context`.

Neither `spec.md` nor `research.md` has been updated to include `doctor.py:2332`. The wiring table in `research.md` still lists 3 callers. FR-037 says "all call sites" — but the spec's own research document doesn't know about the 4th one.

An implementer implementing FR-037 by walking the research.md table will fix 3 sites and leave `spec-kitty doctor` resolving policies without activation filtering. The hard-restriction model will silently not apply to the `doctor` command.

---

## SIGNIFICANT

### S-1. C-006 "same process and transaction" language is unchanged and still unenforceable on a filesystem

**File**: `spec.md` C-006

**Round 1 finding (S9) remains open and verbatim.**

C-006 reads: "The WP start precondition check (assigned profile present in charter) must execute in the same process and transaction as the claim transition; it may not be deferred."

YAML files do not participate in atomic transactions. Two concurrent `agent action implement` invocations can both read the same `PackContext`, both see the profile as activated, and both proceed past the precondition check before either writes a claim transition event. The word "transaction" either means "database transaction" (impossible with YAML) or is being used loosely to mean "before any workspace is created." If the latter, the constraint should be rewritten as: "The precondition check must complete and pass before any git worktree is created or any status transition is emitted; it must not be performed asynchronously or lazily after workspace creation begins."

No change has been made since Round 1. An implementer who reads "transaction" literally will either try to implement file locking (not specified) or will be confused.

---

### S-2. FR-011 WP template reference scan is absent from the consistency-check contract behavior

**Files**: `spec.md` FR-011, `contracts/charter-pack-consistency-check-cli.md` Behavior

**Round 1 finding (S10) remains open.**

FR-011: "`charter pack consistency-check` validates that every artifact in the charter pack exists in the active doctrine pack, **and that every artifact referenced by WP templates or base prompt templates is activated**."

The contract's Behavior section has 4 steps. Step 1 loads `PackContext`. Steps 2–4 check charter-to-doctrine coherence. There is no step that scans WP task files, task frontmatter, or base prompt templates for artifact references, nor a step that cross-checks those references against the activated set.

`ConsistencyReport` has fields: `coherent`, `unknown_references`, `missing_from_doctrine`, `kind_violations`, `suggestions`. None of these fields captures "artifacts referenced in WP templates that are not activated." There is no field for `template_reference_violations` or equivalent.

The second half of FR-011 — the WP-template scan — has zero implementation surface in the contract and zero data-model representation. An implementer cannot implement this half of FR-011 from the spec alone.

---

### S-3. NFR-001 performance threshold is p99 in spec.md and p95 in plan.md

**Files**: `spec.md` NFR-001, `plan.md` Performance Goals

**Round 1 finding (S11) remains open and unchanged.**

`spec.md` NFR-001 threshold: "≤ 100ms p99."
`plan.md` Performance Goals: "Charter activation read path ≤ 100ms p95 under real filesystem I/O (NFR-001)."

A benchmark implementation that measures p95 at 80ms with p99 at 140ms satisfies `plan.md` but violates `spec.md`. No document states which is authoritative.

---

### S-4. Orphaned artifact detection is absent from `ConsistencyReport` and the consistency-check contract

**Files**: `spec.md` Domain Language, `contracts/charter-pack-consistency-check-cli.md`, `data-model.md` §ConsistencyReport

**Round 1 finding (S12) remains open.**

`spec.md` Domain Language defines "orphaned artifact" as "An artifact in the charter whose kind is no longer referenced by any other active artifact." This is a first-class concept in the domain vocabulary.

`contracts/charter-pack-consistency-check-cli.md` Behavior step 3 checks only whether cross-kind referenced artifacts are activated — not whether activated artifacts are referenced by nothing. `ConsistencyReport` fields (`coherent`, `unknown_references`, `missing_from_doctrine`, `kind_violations`, `suggestions`) contain no field for orphaned artifacts. The consistency check command as specced will never report an orphaned artifact, making the Domain Language definition a dead concept.

If orphaned artifact detection is out of scope for this mission, the Domain Language entry should be annotated as "future" or moved to Out of Scope. If it is in scope, a `ConsistencyReport` field and a contract Behavior step must be added.

---

### S-5. Success criterion 10 requires grepping for `activated_kinds` but with `ProjectContext` threading, `activated_kinds` is now accessed via `ctx.pack_context.activated_kinds` — the grep may miss all consumers

**File**: `spec.md` Success Criteria item 10, §Wiring Acceptance Criteria item 6

Success criterion 10: "a codebase grep for `activated_kinds` returns consumer call sites, not only the constructor."

With FR-040 introducing `ProjectContext` threading, call sites that previously would have called `pack_context.activated_kinds` directly now have `pack_context` accessed via `ctx.require_pack_context()`. A caller that does:
```python
ctx.require_pack_context().activated_kinds
```
would appear in a grep for `activated_kinds` — so the grep would still find it. However, Wiring Acceptance Criterion 6 says: "Grep `src/` for resolution paths that construct `PackContext` with `activated_kinds` set but never pass it downstream. Assert zero such paths exist." This grep requires static analysis of data flow, not a simple string search. With `ProjectContext` as the threading vehicle, a `PackContext` is never "passed downstream" directly — it is accessed through `ctx.pack_context`. The grep pattern in criterion 6 is unworkable as stated and will produce false negatives or false positives depending on the implementation.

Success criterion 10 and Wiring Acceptance Criterion 6 need to be rewritten to reflect the `ProjectContext`-threaded access pattern established by FR-040.

---

### S-6. `CharterPackManager.activate()` initialization from `None` state sources "all built-ins" from `default.yaml` but the consistency between `default.yaml` and `DoctrineService` catalog is unspecified

**Files**: `data-model.md` §CharterPackManager, §CharterPack State Transitions

The data-model specifies: "If `activated_<kind>` is `None`: materialize from `default.yaml` then add." This is the `activate()` from-None materialization path. The `list_available(repo_root, kind)` method would be needed to enumerate all current doctrine artifacts, but the data-model says the initialization source is `default.yaml` (a static snapshot), not the live doctrine catalog.

If a user adds a third-party directive to their local doctrine pack after the default pack was written, and then runs `charter activate directive new-third-party-directive` on a project whose `activated_directives` is `None`, the materialization from `default.yaml` would produce a set that does not include the new third-party directive. The user would lose access to artifacts that were previously available via the `None` fallback.

The data-model acknowledges this: "This is deterministic and independent of the live doctrine catalog." But it does not specify what the user-visible behavior is, nor does it specify a warning. An implementer reading this may or may not emit a warning. The spec should either: (a) require a warning that third-party artifacts absent from `default.yaml` will not be included in the materialized set, or (b) require using `DoctrineService.list(kind)` instead of `default.yaml` for materialization, or (c) explicitly document that third-party artifact loss is acceptable and no warning is needed.

---

## MINOR / POLISH

### M-1. `PackContext` described as "Pydantic dataclass" in `data-model.md`; actual implementation uses stdlib `@dataclass(frozen=True)`

**File**: `data-model.md` §PackContext (line 36)

**Round 1 finding (S14) remains open and unchanged.**

`data-model.md` line 36: "Existing Pydantic dataclass in `src/charter/pack_context.py`."

The implementation uses `@dataclass(frozen=True)` from stdlib, not Pydantic. The distinction matters for: field validators, `model_config`, `model_validate`, JSON serialization, error messages on invalid input. An implementer who adds new fields using Pydantic `Field()` decorators or `@validator` will introduce a dependency mismatch.

---

### M-2. `mission_step_contract` → `mission_steps` DRG naming gap is unreferenced in FR-028

**File**: `spec.md` FR-028, prior `adversarial-review-spec-and-design.md` (S15)

**Round 1 finding (S15) remains open.**

FR-028: "The stale `'mission_step_contracts'` kind string in `test_org_charter_pack_context.py` line 65 is corrected to the current canonical kind identifier."

The prior review (S15) identified that `drg.py:592 _SINGULAR_TO_PLURAL` maps `mission_step_contract` to `"mission_steps"` while `pack_context.py:58 _BUILTIN_ARTIFACT_KINDS` contains `"mission_step_contracts"`. These are different strings. FR-028 says to correct the test to "the current canonical kind identifier" — but which one? The two source files disagree about the canonical plural. FR-028 cannot be implemented without knowing which string is authoritative. The spec does not answer this.

---

### M-3. `ActivationKind` in Key Entities uses underscore form (`agent_profile`); CLI kind table uses underscore form; Activation Kinds Reference uses underscore form; CLI contracts use hyphen form (`agent-profile`); Journeys use underscore form in `--cascade` argument — the CLI-to-internal mapping is documented in `data-model.md` but not referenced from `spec.md`

**Files**: `spec.md` Domain Language line 40, Activation Kinds Reference table line 54, Key Entities line 242, Journeys 3–5, `data-model.md` §ActivationKind

The data-model §ActivationKind table provides the definitive CLI→PackContext mapping. However, `spec.md` itself is internally inconsistent:
- Domain Language: `agent_profile` (underscore)
- Activation Kinds Reference: `agent_profile` (underscore) in CLI kind column
- Key Entities `ActivationKind` definition: `agent_profile` (underscore)
- Journeys 3, 4, 5: `--cascade agent_profile` (underscore)
- FR-004 allowed kinds: `agent_profile` (underscore)
- CLI contracts (activate, deactivate) argument table: `agent-profile` (hyphen)

The `spec.md` itself uses underscore in the narrative and the contracts use hyphen. An implementer who writes the CLI parser from the contracts will accept `agent-profile`; an implementer who writes the parser from the FRs will accept `agent_profile`. Both will fail tests written from the other form.

`spec.md` must state explicitly: "CLI kind values use hyphen separators (matching other typer CLI conventions); internal Python identifiers use underscore. The canonical mapping is in `data-model.md` §ActivationKind."

---

### M-4. `mission-type` dispatch in `CharterPackManager` writes to a different YAML key than all other kinds — this special case is documented in the ActivationKind table but not in the CharterPackManager behavior description

**Files**: `data-model.md` §ActivationKind, §CharterPackManager, §State Transitions

**Round 1 finding (S18) remains open.**

The ActivationKind table shows `mission-type` maps to YAML key `mission_type_activations`, while every other kind maps to `activated_<kind>`. The CharterPackManager Key Methods block shows a single `activate(repo_root, kind, artifact_id, cascade)` signature. The Behavior section of the manager does not describe how the manager branches on `kind == "mission-type"` to write to `mission_type_activations` rather than `activated_mission_types`. The State Transitions flow shows `CharterPackManager.activate(repo_root, "directive", ...)` — there is no flow for `kind="mission-type"`.

An implementer who follows the table will implement the YAML key dispatch correctly. But an implementer who writes a generic `activated_{kind}s` key formatter (the pattern that works for 8 of 9 kinds) will write `activated_mission_types` instead of `mission_type_activations` and break the Phase 1 config format.

---

### M-5. `specs_dir` and `architecture_dir` fields in `ProjectContext` have no corresponding guard methods

**File**: `data-model.md` §ProjectContext

The Guard Methods section lists: `require_repo_root()`, `require_pack_context()`, `require_org_root()`. Fields `specs_dir` and `architecture_dir` are both `Path | None` but have no listed guard methods.

If any method in this mission uses `specs_dir` or `architecture_dir` (e.g., the consistency-check command scanning WP templates under `specs_dir`), there is no guard to call and the implementer must write ad-hoc None-checks — exactly the pattern FR-040 is designed to replace.

Either define the missing guard methods or annotate `specs_dir` and `architecture_dir` as "read without guard; callers should None-check directly."

---

### M-6. Wiring Acceptance Criterion 5 still underspecified; Criterion 6 cannot be expressed as a grep

**File**: `spec.md` §Wiring Acceptance Criteria items 5–6

**Round 1 finding (S17) remains open and compounded by FR-040.**

Criterion 5: "Grep `src/` for callers of `filter_graph_by_activation` after implementation. Assert at least one non-test caller exists." This is underspecified: `research.md` identifies 4 required production call sites. An implementation with 1 call site and 3 still-dead wiring points satisfies criterion 5 while leaving 3 resolution paths unfiltered.

Criterion 6: "Grep `src/` for resolution paths that construct `PackContext` with `activated_kinds` set but never pass it downstream." With `ProjectContext` threading (FR-040), `PackContext` is accessed via `ctx.pack_context` — it is never "passed downstream" as a standalone argument. This criterion was written before FR-040 existed. It now describes a code pattern that FR-040 explicitly eliminates. The criterion will either produce zero results (because no code passes `PackContext` directly) or false negatives (because callers that should thread `ctx` but don't are invisible to this grep).

---

## VERIFIED

The following items from the Round 1 adversarial review have been resolved in the current spec:

- **Round 1 Blocking #1** (storage location contradiction `charter.md` vs `config.yaml`): `spec.md` Domain Language, Journey 1, Journey 2, and Assumptions now consistently state activation state lives in `.kittify/config.yaml`. Charter.md is described as "human-readable governance document" only. RESOLVED.

- **Round 1 Blocking #2** (per-artifact-ID filter gap): FR-038 has been added, explicitly requiring `_node_is_activated` to check per-kind frozensets when non-None, with `activated_kinds` remaining as the outer check. The two-layer filter architecture is now specced. RESOLVED.

- **Round 1 Blocking #3** (three-state invariant broken by `and raw` guard): FR-039 explicitly requires the `and raw` guard be removed for new per-kind readers; the data-model Invariant and Reader Rule sections now describe the correct three-state semantics. RESOLVED.

- **Round 1 Blocking #4** (backup path in Journey 2 contradicts C-008): Journey 2 now says "creates a timestamped backup at `.kittify/charter/backups/charter-{timestamp}.md`", consistent with C-008 and `research.md`. RESOLVED.

- **Round 1 Blocking #5** (`ActivationKind` Key Entities truncated to 4 values): Key Entities table now lists all 9 kinds: `mission_type`, `directive`, `tactic`, `styleguide`, `toolguide`, `paradigm`, `procedure`, `agent_profile`, `mission_step_contract`. RESOLVED.

- **Round 1 Blocking #6** (`CascadeScope` covers only 3 of 8 non-mission-type kinds): `data-model.md` §CascadeScope table still only has `profiles`, `directives`, `tactics` as named values. **NOT RESOLVED** — see B-4 above.

- **Round 1 Significant #7** (upgrade migration algorithm does not populate per-kind artifact ID lists): `research.md` §5 Upgrade Algorithm now explicitly lists all 10 per-kind writes (including `activated_directives` through `activated_mission_step_contracts`). The algorithm reads `default.yaml` for all kinds. RESOLVED.

- **Round 1 Significant #8** (deactivate from None state — no materialization step): `data-model.md` §CharterPackManager now has an explicit "Deactivation from `None` state" block: exit 1 with message. The CLI contract Behavior step 3 matches this. RESOLVED.

- **Round 1 Minor #13** (duplicate success criteria numbering): Success criteria now run 1–14 with no duplicates. RESOLVED.

- **Round 1 Minor #16** (`CharterPackManager.activate` materialization source unspecified): `data-model.md` now explicitly states "The source is `src/charter/packs/default.yaml`." PARTIALLY RESOLVED — but see S-6 above for the residual gap (third-party artifact loss not addressed).

- **C-004 fix / mypy Protocol requirement** (from architecture review): FR-020 now explicitly states "a narrow `ProjectContextProtocol` defined in `doctrine.*` replaces the direct `PackContext` annotation, satisfying both pytestarch and mypy strict." RESOLVED at spec level.

---

## SUMMARY TABLE

| # | Severity | Item | File(s) | Round 1 ref |
|---|----------|------|---------|-------------|
| B-1 | BLOCKING | `CharterPackManager` method signature contradicts itself three ways in one document; `ActivationResult`/`MergeResult` are undefined types | `data-model.md` | — (new) |
| B-2 | BLOCKING | FR-040 does not say `OperationalContext` has zero required call sites; `build_operational_context` will be treated as in-scope; dead-symbol fallout unaddressed | `spec.md` FR-040, `data-model.md` | — (new) |
| B-3 | BLOCKING | `ProjectContext.from_repo()` behavior is entirely unspecified (missing-`.kittify` case, field resolution rules, guard method coverage, factory vs from_repo relationship) | `data-model.md` §ProjectContext | — (new) |
| B-4 | BLOCKING | `CascadeScope` named values still cover only 3 of 8 non-mission-type kinds; Journeys use `agent_profile` cascade token not in CascadeScope table; both CLI contracts still list old 4-value set | `data-model.md`, `spec.md`, contracts | Round 1 S6 (not resolved) |
| B-5 | BLOCKING | `doctor.py:2332` is a 4th `load_org_charter_policies()` caller; absent from `research.md` and FR-037 | `research.md`, `spec.md` FR-037 | Arch-review B-4 (not resolved in spec) |
| S-1 | SIGNIFICANT | C-006 "transaction" language still unenforceable on YAML filesystem; unchanged | `spec.md` C-006 | Round 1 S9 (not resolved) |
| S-2 | SIGNIFICANT | FR-011 WP template scan has no Behavior step in consistency-check contract and no `ConsistencyReport` field | `spec.md` FR-011, contract | Round 1 S10 (not resolved) |
| S-3 | SIGNIFICANT | NFR-001 p99 in spec vs p95 in plan; unchanged | `spec.md`, `plan.md` | Round 1 S11 (not resolved) |
| S-4 | SIGNIFICANT | Orphaned artifact detection absent from `ConsistencyReport` and contract; Domain Language term is dead | `spec.md`, `data-model.md`, contract | Round 1 S12 (not resolved) |
| S-5 | SIGNIFICANT | Success criterion 10 and Wiring Criterion 6 use grep patterns that are broken by the `ProjectContext`-threading model FR-040 introduces | `spec.md` SC-10, WAC-6 | — (new, introduced by FR-040) |
| S-6 | SIGNIFICANT | Activate from `None` materializes from `default.yaml`; third-party artifact loss on materialization is undocumented; no warning specified | `data-model.md` §CharterPackManager | Round 1 M16 (partially resolved) |
| M-1 | MINOR | `PackContext` described as "Pydantic dataclass"; actual impl is stdlib `@dataclass(frozen=True)` | `data-model.md` §PackContext | Round 1 S14 (not resolved) |
| M-2 | MINOR | FR-028 says fix to "canonical kind identifier" but two source files disagree on what the canonical plural is | `spec.md` FR-028 | Round 1 S15 (not resolved) |
| M-3 | MINOR | `spec.md` narrative and FRs use underscore form (`agent_profile`); CLI contracts use hyphen form (`agent-profile`); Journeys use underscore in `--cascade` argument; no cross-reference to data-model mapping | `spec.md`, contracts | — (new, introduced by contract updates) |
| M-4 | MINOR | `mission-type` YAML key dispatch special case (`mission_type_activations` vs `activated_*`) undescribed in `CharterPackManager` Behavior | `data-model.md` §CharterPackManager | Round 1 S18 (not resolved) |
| M-5 | MINOR | `specs_dir` and `architecture_dir` fields in `ProjectContext` have no guard methods defined | `data-model.md` §ProjectContext | — (new) |
| M-6 | MINOR | Wiring Acceptance Criterion 5 still requires only 1 of 4 required callers; Criterion 6 grep is invalidated by FR-040 | `spec.md` §WAC | Round 1 S17 (partially, compounded) |
