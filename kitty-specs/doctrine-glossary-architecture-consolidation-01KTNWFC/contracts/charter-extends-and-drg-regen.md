# Contracts — charter `extends:` (IC-07) & DRG regeneration (IC-08)

No HTTP API in this mission; the "contracts" are the config-schema and CLI-surface behaviours.

## C1 — `org-charter.yaml` `extends:` (FR-008, IC-07)

**Schema addition (additive, optional):**
```yaml
# org-charter.yaml
extends:                      # optional list; absent = current behaviour
  - <base-org-charter-ref>    # resolvable reference to a base org charter
```

**Resolution contract:**
- **Additive merge**: extended config is layered onto the base; the extending org's values take **precedence** over the base on conflict.
- **Cycle detection**: an `extends:` cycle is rejected fail-closed with a structured error (no partial/ambiguous resolution).
- **Single mechanism**: resolution runs through `charter.activation_engine` (plan→commit) + `charter.cascade`; **no parallel resolver** (C-005, R-10).
- **Non-destructive**: existing charter content and user customizations are preserved (C-004).

**Acceptance:** a charter declaring `extends:` resolves additively and passes charter validation; a cycle is rejected; existing single-org charters behave unchanged.

## C2 — DRG regeneration command (FR-009, IC-08)

**CLI surface:** a single regeneration command produces `src/doctrine/graph.yaml` deterministically.
- **Determinism**: running it twice on unchanged inputs yields byte-identical `graph.yaml`.
- **Symmetric profile-edge detection**: a declared profile edge (e.g. `specializes_from` / `delegates_to`) is validated/detected in both directions (no asymmetric blind spot).
- **Freshness gate**: the existing freshness test passes after regeneration.

**Re-curation (data):** built-in DRG + agent profiles are sanitized — new doctrine artefacts (IC-04) added as nodes/edges; stale/duplicate edges and dead profiles pruned. No valid edge dropped silently.

**Acceptance:** `spec-kitty doctor doctrine --json` healthy (no skipped profiles); regenerate-twice identical; freshness gate green.
