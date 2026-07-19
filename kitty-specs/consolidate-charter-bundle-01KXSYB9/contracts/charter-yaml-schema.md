# Contract: `charter.yaml` structured schema (v2.0.0)

`charter.yaml` is the git-tracked, authorable project charter. Full field table in `data-model.md`. This contract fixes the observable guarantees consumers may rely on.

## Shape (top-level keys)
A concrete, round-trippable instance (executed against `charter.schemas.CharterYaml` by the FR-140 round-trip gate). `governance`/`directives`/`overrides` are shown at their empty defaults; the FLAT root activation lists carry sample values.
```yaml
# pydantic_model: charter.schemas.CharterYaml
# expect: valid
schema_version: "2.0.0"
governance: {}                       # GovernanceConfig — AUTHORED
directives:                          # DirectivesConfig — AUTHORED
  directives: []
catalog:                             # DERIVED-but-committed projection
  mission: consolidate-charter-bundle
  template_set: default
  languages:
    - python
  references:
    - id: DIRECTIVE_001
      kind: directive
      title: Single canonical authority
      summary: Illustrative catalog reference item.
      source_path: .kittify/charter/charter.md
      local_path: .kittify/doctrine/directives/DIRECTIVE_001.md
# --- activation: FLAT root keys (NOT nested), identical shape to packs/default.yaml ---
activated_kinds:
  - directive
  - tactic
mission_type_activations:
  - software-dev
activated_directives:
  - DIRECTIVE_001
activated_tactics: []
# ... one flat root list per kind (styleguides/toolguides/paradigms/procedures/agent_profiles/mission_step_contracts)
activated_styleguides: []
activated_toolguides: []
activated_paradigms: []
activated_procedures: []
activated_agent_profiles: []
activated_mission_step_contracts: []
overrides: {}                        # AUTHORED — project doctrine overrides (forward-compat)
metadata:
  generated_at: "2026-01-01T00:00:00+00:00"
  bundle_schema_version: 2
```

> ⚠ **Activation keys are FLAT at the charter.yaml root** (matching `src/charter/packs/default.yaml:5-38`), NOT nested under an `activation:` mapping — so `pack_context._read_activated_*` / `_read_list_key` and `activation_engine.commit_plan` read/write them unchanged, and pack overlay works (paula BLOCKER-1).

## Guarantees
- **G1**: `governance` and `directives` deserialize into the existing `GovernanceConfig` / `DirectivesConfig` models unchanged (nested in `CharterYaml`).
- **G2**: `catalog` is byte-equivalent in content to the retired `references.yaml` body (same keys), so parity/resolving consumers see identical data.
- **G3**: activation is a single flat set resolved by `PackContext.from_config`; an explicit empty list stays fail-closed (`frozenset()`); an absent key resolves the default pack fallback (`load_default_pack_activation_ids`, never a re-expanded `_BUILTIN_*`). `default.yaml` is the absent-key **fallback/seed**, not a live per-artifact tiered activation merge (see the note on tier accumulation in `active-doctrine-resolution.md`).
- **G7 (two-file read)**: `PackContext.from_config` reads `config.yaml` for the `charter:` pointer + `org_packs`, and `charter.yaml` for the flat activation. `org_packs` (pack roots) intentionally stay in `config.yaml`.
- **G4**: `metadata` carries `bundle_schema_version: 2` (read by `versioning.py`); it MUST NOT carry a self-referential `charter_hash`.
- **G5**: the file is git-tracked; a compile updates `catalog`/`metadata.generated_at` deterministically (stable ordering) — an unchanged charter produces a byte-identical file (content-identity, #2732).

## Resolution via config pointer
- **G6**: the active `charter.yaml` is located through the single `charter:` pointer in `.kittify/config.yaml` (default `.kittify/charter/charter.yaml`). The pointer may redirect to a sibling / shared / cross-project charter; a swap is a one-line config change. The resolver reads the pointer, then loads that file.

## Fail-closed
- Corrupt/unreadable `charter.yaml` → raise the re-homed `ReferenceCatalogError`/`ReferencesCorruptError` (#2530), never fall back to a legacy file.
- A `charter:` pointer to a missing/unreadable file → fail loud (C-003); never fall back.
