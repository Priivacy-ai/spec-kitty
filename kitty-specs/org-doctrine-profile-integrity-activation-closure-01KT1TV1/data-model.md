# Data Model: Org Doctrine Profile Integrity Activation Closure

Entities, value objects, invariants, and state transitions for the mission. Filesystem-only; no database. All shapes are Python (Pydantic models / dataclasses / StrEnum) plus on-disk YAML.

---

## 1. Canonical Kind & ID model (R-009, FR-027)

### `ArtifactKind` (extended)

Existing `doctrine.artifact_kinds.ArtifactKind` (StrEnum, canonical singular underscore values) becomes the single source of truth for the kind vocabulary. Extended with operator-token mapping.

| Concept | Representation | Notes |
|---------|----------------|-------|
| Canonical kind | `ArtifactKind` member (e.g. `agent_profile`) | underscore singular |
| Operator token | hyphen form (e.g. `agent-profile`, `mission-step-contract`, `mission-type`) | CLI surface |
| Plural | `ArtifactKind.plural` (e.g. `agent_profiles`) | dir / service attr / config key stem |
| Glob | `ArtifactKind.glob_pattern` | empty for `template` (no extension) |

**New accessor** `from_operator_token(token: str) -> ArtifactKind` — normalizes hyphen→underscore and validates. The charter surfaces (`context --include`, `activate`, `deactivate`, `list`) route every kind string through it.

**Charter kind universe** = `ArtifactKind` artifact kinds **+ `mission-type`** (which is *not* an `ArtifactKind` member). `template` is an `ArtifactKind` member but is resolved specially (mission-tier, no glob).

**Invariants**:
- I-K1: No charter command re-declares the kind set; `YAML_KEY_MAP`, `_KIND_TO_DOCTRINE_DIR`, `_KIND_ORDER`, the `--include` renderer table, and the augmentation tables all derive from the canonical model.
- I-K2: `from_operator_token` is total over the documented operator tokens and raises a structured error (not silent drop) on unknown tokens.

### Artifact ID resolver (FR-014/015/016, R-011-D)

Maps the config/file-stem ID (e.g. `001-architectural-integrity-standard`) ↔ DRG URN node ID (e.g. `directive:DIRECTIVE_001`) using the artifact's existing `id:` field (already read by `catalog._extract_artifact_id`). Replaces the kind-only workaround in `consistency_check`.

**Invariant** I-ID1: every activatable artifact has exactly one resolver entry; cascade resolves a config ID to a unique DRG node or raises.

---

## 2. DRG relationship model (C-009, FR-001..004)

### `Relation` (extended)

`doctrine.drg.models.Relation` StrEnum gains:

| Member | Value | Semantics |
|--------|-------|-----------|
| `SPECIALIZES_FROM` | `specializes_from` | structural profile/artifact lineage (inheritance) |

Distinct from `DELEGATES_TO` (runtime work handoff), `ENHANCES`/`OVERRIDES` (augmentation), `REPLACES` (full replacement).

**Invariants**:
- I-R1 (FR-002): no traversal that filters for `DELEGATES_TO` returns `SPECIALIZES_FROM` edges. Guarded by a regression test (today `DELEGATES_TO` has zero DRG consumers).
- I-R2 (FR-003): lineage edges from shipped/org/project fragments validate identically. Unknown relations are surfaced as errors, not silently dropped (org-fragment bridge fix).

### `DRGGraph` (extended)

Add `edges_to(urn, relation=None) -> list[DRGEdge]` (reverse adjacency) — required for shared-reference deactivation (FR-015).

### Canonical merge (relocated — OQ-2-ii)

`merge_three_layers(built_in, org_fragments, project_fragments) -> DRGGraph` **moves from `charter/drg.py` into `doctrine/drg/merge.py`**. Inputs are graph data (built-in graph + fragments supplied by callers); doctrine never imports charter/specify_cli. `charter` becomes a caller that applies activation-aware filtering/aggregation on the returned merged graph.

**Invariants**:
- I-M1: the merged DRG is the canonical relationship representation; a relationship exists iff a merged edge exists.
- I-M2: doctrine-layer consumers (profile hierarchy resolver) resolve against the doctrine-merged graph; no doctrine→charter import.

---

## 3. Authoring model — DRG-fragment only (hard cutover, OQ-2-i, FR-028..032)

### Removed fields

`enhances`, `overrides` removed from `Tactic`, `Styleguide`, `Paradigm`, `Procedure`, `AgentProfile`, and **not** added to `Directive`, `Toolguide`, mission step contract, mission type. `specializes_from` removed from `AgentProfile`. With `extra="forbid"`, presence of any of these keys is now a **validation error**.

### Authoring → edges

Relationships are authored as DRG-fragment edges. The org-pack auto-emitter no longer scans artifact fields; built-in/shipped relationships are migrated to fragment edges (governed by `occurrence_map.yaml`).

**State transition** (per relationship occurrence):
```
field-authored (pre)  ──migrate──▶  fragment edge (post)
   reader: field            reader: DRG traversal
```
**Invariants**:
- I-A1 (NFR-007): migration is relationship-preserving — every pre-existing field-authored relationship has a corresponding merged DRG edge after migration (verified by a count/identity diff).
- I-A2: post-cutover, no runtime reader consults the removed fields (dead-symbol/grep gate).
- I-A3 (NFR-005): all built-in artifacts load with zero diagnostics after migration.

### Augmentation single-source (FR-030)

`_AUGMENTATION_PLURAL_TO_KIND` (loader) and `_AUGMENTATION_PLURAL_KINDS` (validator) derive from one shared constant covering all augmentation-eligible kinds. Mission-type augmentation resolved per FR-032 (expand `_ORG_DRG_CANONICAL_KINDS` as a binding change with contract-test sweep, or a separate path; never silently dropped).

**Topology invariant** I-A4 (FR-029): for step contracts and mission types, an `enhances` field-merge preserves action-sequence ordering and step I/O contracts; `overrides` is full replacement.

---

## 4. Profile load diagnostics (FR-005..007, NFR-002)

### `SkippedProfile` (new record)

| Field | Type | Notes |
|-------|------|-------|
| `layer` | `str` (`built-in`/`org`/`project`) | source layer |
| `path` | `str` | filesystem path for operator action |
| `profile_id` | `str \| None` | discovered ID before validation failed, else `None` |
| `error_summary` | `str` | concise parse/validation error |

Held on `AgentProfileRepository._skipped`; exposed via `skipped_profiles() -> list[SkippedProfile]` (sorted, deterministic). `list_all()` stays valid-only (FR-006). Survives on the `DoctrineService`-cached repo (FR-007).

**Invariants**:
- I-P1 (NFR-002): `skipped_profiles()` returns the same sorted records for the same inputs (sort by `(layer_rank, path)`; scans sorted).
- I-P2: every drop site (5 `warnings.warn` + silent `continue`/`pass`) routes through one `_record_skip()`.

---

## 5. Doctrine health report (FR-008..010, NFR-001)

### `DoctrineHealthReport` (new) + `PackHealth`

One structure rendered by both human and `--json` doctor output (no independent assembly).

| `PackHealth` field | Type | Notes |
|--------------------|------|-------|
| `pack_id` / `layer` | `str` | |
| `discovered_count` / `valid_count` | `int` | per kind/pack |
| `invalid_profiles` | `list[SkippedProfile]` | from §4 |
| `healthy` | `bool` (derived) | `valid_count == discovered_count` AND no invalid profiles |

**Invariants**:
- I-H1 (FR-010): `healthy` is derived from validity, **not** snapshot presence or glob count.
- I-H2 (FR-009): JSON fields are a passthrough of `SkippedProfile` (stable: layer/path/profile_id/error_summary).
- I-H3 (NFR-001): report built once (single `DoctrineService`/DRG load) → ≤ 2s on built-in + one pack.

---

## 6. Charter activation (FR-011..016, NFR-003)

### `ActivationPlan` (new value object) + `CascadeScope`

| `ActivationPlan` field | Type | Notes |
|------------------------|------|-------|
| `yaml_key` | `str` | resolved config key |
| `new_list` | `list[str]` | post-state (in-memory) |
| `warnings` | `list[str]` | incl. no-cascade skipped-reference warning (FR-013) and mission-type step-removal |
| `cascade_targets` | `dict[str, list[str]]` | kind → IDs |

`CascadeScope`: `all` (explicit shorthand) or an explicit set of `ArtifactKind`. `None` = no cascade (never means all).

**Pure seam**: `plan_activation(...) -> ActivationPlan` (raises on FR-011/012 before any mutation) + `commit_plan(...)` (single `_save_config` write).

**State transitions** (activation):
```
validate kind/ID ─▶ plan (pure) ─▶ commit (single write)
        │ unknown ID / malformed config
        ▼
   fail-closed (CharterPackConfigError or structured error), NO write
```
**Invariants**:
- I-AC1 (NFR-003): config bytes unchanged after any `plan_activation` failure.
- I-AC2 (C-005, FR-015): cascade deactivation removes only artifacts unreachable from all other still-activated sources (`edges_to` reverse reachability); shared artifacts are skipped with the referencing active artifact named.
- I-AC3 (FR-016): cascade uses the merged DRG reference model, no per-kind special cases.

---

## 7. OperationalContext (FR-017..020, C-006)

`charter.invocation_context.OperationalContext` — populated at runtime entry points. Built by `build_operational_context(*, active_model, active_profile, active_role, current_activity, tech_stack)` — a **pure explicit-parameter assembler** in `charter` (never reaches into runtime state; never imported by `doctrine`).

| Field | Source at call site |
|-------|---------------------|
| `active_model` | `--agent` value |
| `active_profile` | `_resolve_step_agent_profile(run_dir, step_id)` |
| `active_role` | claim actor / profile role |
| `current_activity` | `step_id` / `mission_state` |
| `tech_stack` | charter/meta |

Call sites: `implement.py` claim, `agent/workflow.py` claim, `runtime_bridge.decide_next_via_runtime`.

**Invariants**:
- I-OC1 (FR-018): `require_active_profile()` / `require_active_role()` raise `ContextPreconditionError` with actionable messages when absent.
- I-OC2 (NFR-004): precondition failure creates no worktree and emits no status event.
- I-OC3 (FR-019): wiring precedes allowlist removal; the dead-symbol gate's stale-detector enforces ordering.

---

## 8. Template identity (#1333, FR-033/034)

Templates become DRG-addressable with **mission-qualified-name** IDs.

| Concept | Representation |
|---------|----------------|
| Template ID | `<mission>/<name>` (e.g. `software-dev/spec`) |
| DRG node | `template:<mission>/<name>` minted from tier+mission+filename layout (no file frontmatter) |
| Discovery | enumerate across tiers/missions, annotated by source tier (override→…→package) |
| Resolution | `charter context --include template:<id>`; `charter list --all` includes `template` kind |

**Invariants**:
- I-T1: template discovery accounts for empty glob + mission-scoped dirs (not the flat `built-in/*.<suffix>` layout).
- I-T2: same-named templates across missions are distinct IDs (mission qualifier disambiguates).

---

## 9. Dead-symbol hygiene (FR-035/036, NFR-006)

| Symbol | Action |
|--------|--------|
| `charter.pack_context::CharterPackConfigError` | external caller added (activation/context fail-closed) → live |
| `charter.activate::charter_activate_app`, `charter.deactivate::charter_deactivate_app` | export normalized (one registration pattern) |
| 7 stale `_SYMBOL_ALLOWLIST` entries (`next._internal_runtime.events::*`, `lanes.auto_rebase::AutoRebaseReport`) | removed |
| `git.sparse_checkout::SparseCheckoutKind`, `lanes.lifecycle_sync::LANE_AUTO_REBASE_FAILED` | **out of scope**; allowlist-with-tracker if gate cannot pass |

**Invariant** I-D1: the dead-symbol gate passes for all in-scope symbols; out-of-scope offenders are explicitly tracked, not silently fixed.
