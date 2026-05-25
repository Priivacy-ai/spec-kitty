# Phase 1 — Data Model

**Mission**: `charter-ux-and-org-pack-vocabulary-01KSAF14`

This document captures the new and changed data structures introduced by the mission. It is read-only design; no code is written here.

---

## 1. Doctrine artifact models (extended)

### 1.1 `Tactic` (`src/doctrine/tactics/models.py`)

```python
class Tactic(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    id: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    schema_version: str = Field(pattern=r"^1\.0$", alias="schema_version")
    name: str
    overrides: str | None = Field(default=None, description="ID of a built-in tactic this artifact replaces in full.")
    enhances: str | None = Field(default=None, description="ID of a built-in tactic this artifact augments via field-merge.")
    purpose: str | None = None
    steps: list[TacticStep] = Field(min_length=1)
    failure_modes: list[str] = Field(default_factory=list)
    applies_to_languages: list[str] = Field(default_factory=list)
    references: list[TacticReference] = Field(default_factory=list)
    opposed_by: list[Contradiction] = Field(default_factory=list)
    notes: str | None = None

    @model_validator(mode="after")
    def _augmentation_intent_is_exclusive(self) -> Self:
        if self.overrides is not None and self.enhances is not None:
            raise ValueError(
                f"overrides and enhances are mutually exclusive on tactic {self.id}"
            )
        return self
```

**Same pattern** applies to:
- `Styleguide` (`src/doctrine/styleguides/models.py`)
- `Paradigm` (`src/doctrine/paradigms/models.py`)
- `Procedure` (`src/doctrine/procedures/models.py`)
- `AgentProfile` (`src/doctrine/agent_profiles/profile.py`)

Each model gains:
- `overrides: str | None = None`
- `enhances: str | None = None`
- a cross-field validator named `_augmentation_intent_is_exclusive`.

Schema YAML files (`src/doctrine/schemas/*.schema.yaml`) gain matching optional `string` properties with the same regex pattern as `id`.

### 1.2 Field semantics

| Field | Set on artifact | Meaning |
|---|---|---|
| neither | typical | pack-only artifact; ID may or may not collide with built-in; collision triggers reworded advisory (R-9) |
| `overrides: <id>` | pack-side | declares full replacement of built-in `<id>`; advisory suppressed; DRG emits `OVERRIDES` edge |
| `enhances: <id>` | pack-side | declares augmentation of built-in `<id>` via field-merge; advisory suppressed; DRG emits `ENHANCES` edge |
| both set | invalid | model validator rejects |
| `enhances: <unknown-id>` | pack-side | `pack validate` raises hard error `unknown_target` |
| `overrides: <unknown-id>` | pack-side | same |

---

## 2. DRG `Relation` enum (extended)

`src/doctrine/drg/models.py`:

```python
class Relation(StrEnum):
    REQUIRES = "requires"
    SUGGESTS = "suggests"
    APPLIES = "applies"
    SCOPE = "scope"
    VOCABULARY = "vocabulary"
    INSTANTIATES = "instantiates"
    REPLACES = "replaces"          # retained (existing fragments may use this)
    DELEGATES_TO = "delegates_to"
    ENHANCES = "enhances"          # NEW — auto-emitted from `enhances:` field
    OVERRIDES = "overrides"        # NEW — auto-emitted from `overrides:` field
```

Edges with `relation=ENHANCES` and `relation=OVERRIDES` are emitted by `org_pack_loader.py` automatically; pack authors do **not** write them in `drg/fragment.yaml`.

---

## 3. `DecayReport` (extended)

`src/specify_cli/charter_lint/findings.py`:

```python
class DecayReport(BaseModel):
    findings: list[LintFinding]
    scanned_at: str
    feature_scope: str | None
    duration_seconds: float
    drg_node_count: int
    drg_edge_count: int
    graph_state: GraphState  # NEW

class GraphState(StrEnum):
    MERGED = "merged"              # built-in + (optional org) + project
    BUILT_IN_ONLY = "built_in_only"  # project DRG missing; lint ran against built-in
    MISSING = "missing"            # no DRG loadable; lint did not run
```

`LintEngine.run()` always populates `graph_state`. The JSON serialiser emits it as `"graph_state"` at the top level.

---

## 4. `CharterPreflightResult` (new)

`src/specify_cli/charter_preflight/result.py`:

```python
@dataclass(frozen=True)
class CharterPreflightCheck:
    name: str               # e.g. "charter_source", "synced_bundle", "synthesized_drg"
    state: str              # "fresh" | "stale" | "missing" | "invalid" | "skipped"
    detail: str             # human-readable
    remediation: str | None # one exact recovery command (or None)

@dataclass(frozen=True)
class CharterPreflightResult:
    passed: bool
    checks: list[CharterPreflightCheck]
    auto_refresh_applied: bool
    auto_refresh_actions: list[str]
    blocked_reason: str | None      # only set when passed is False and no auto-refresh occurred

    def to_json(self) -> str: ...
```

JSON shape returned by `spec-kitty charter preflight --json`:

```json
{
  "passed": false,
  "checks": [
    {"name": "charter_source", "state": "fresh", "detail": "...", "remediation": null},
    {"name": "synced_bundle", "state": "fresh", "detail": "...", "remediation": null},
    {"name": "synthesized_drg", "state": "missing", "detail": "...", "remediation": "spec-kitty charter synthesize"}
  ],
  "auto_refresh_applied": false,
  "auto_refresh_actions": [],
  "blocked_reason": "synthesized_drg missing; run `spec-kitty charter synthesize`"
}
```

---

## 5. Charter freshness sub-object on `charter status --json`

`src/specify_cli/cli/commands/charter.py::status` JSON gains a new top-level `freshness` key, computed by hash/timestamp comparison (FR-005):

```json
{
  "result": "success",
  "charter_sync": { ... existing ... },
  "synthesis":    { ... existing ... },
  "org_layer":    { ... existing ... },
  "freshness": {
    "charter_source": {"state": "fresh", "last_change": "2026-05-19T13:00:45.966069+00:00", "remediation": null},
    "synced_bundle":  {"state": "fresh", "last_change": "...", "remediation": null},
    "synthesized_drg": {"state": "missing", "last_change": null, "remediation": "spec-kitty charter synthesize"}
  }
}
```

State value vocabulary matches `CharterPreflightCheck.state` for cross-consistency.

---

## 6. Synthesis manifest marker

`src/charter/synthesizer/manifest.py` — `synthesis-manifest.yaml` gains an optional field:

```yaml
schema_version: "1.0"
run_id: 01KPE222CD1MMCYEGB3ZCY51VR
...
built_in_only: true   # NEW — set when synthesize legitimately produced no project DRG
```

When `built_in_only: true`, downstream commands report `graph_state="built_in_only"` instead of `"missing"`.

### Conflict resolution rule (architect remediation)

The two states (`built_in_only: true` AND `.kittify/doctrine/graph.yaml` exists) MUST be detected and resolved deterministically:

1. **Authoritative read order**: `synthesis-manifest.yaml.built_in_only` is read first. If `true`, the manifest is authoritative — `graph.yaml` (if present) is treated as **stale residue** from a previous run.
2. **Reporting**: `charter status` MUST surface this conflict explicitly: `synthesized_drg.state = "invalid"` with `detail = "synthesis manifest declares built_in_only=true but graph.yaml exists; this is a stale artifact"`.
3. **Remediation**: the remediation hint is `rm .kittify/doctrine/graph.yaml` OR `spec-kitty charter synthesize --force-overwrite` — both are acceptable but the synthesize command path is preferred.
4. **Synthesize itself**: when `spec-kitty charter synthesize` runs and decides the result is built-in-only, it MUST delete any pre-existing `graph.yaml` and write `built_in_only: true` in the manifest in a single atomic operation. This prevents the conflict state from being created by the synthesizer itself.

---

## 7. Pack-validator advisory categories

`src/specify_cli/doctrine/pack_validator.py::ValidationIssue.category`:

| Category (existing) | Triggered by |
|---|---|
| `schema_invalid` | YAML doesn't validate against schema (existing) |
| `drg_dangling_edge` | DRG edge references unknown URN (existing) |
| `same_id_collision` | Pack artifact ID matches built-in (existing, reworded text) |

| Category (NEW) | Triggered by |
|---|---|
| `unknown_target` | `enhances`/`overrides` references unknown built-in ID |
| `intent_conflict` | both `enhances` and `overrides` set |

Severity: `unknown_target` and `intent_conflict` are `severity="error"`; `same_id_collision` remains `severity="advisory"` (but suppressed when the intent is declared).

---

End of data model.
