# Harness-Owned Generated-Artifact Charter Handoff Contract

**Status:** Accepted

**Date:** 2026-04-19

**Deciders:** Spec Kitty Development Team

**Mission:** `phase-3-charter-synthesizer-pipeline-01KPE222`

**EPIC:** Charter EPIC #461 · ADR-6 replacement #692

---

## Context

Charter synthesis is no longer an internal model call. The host LLM or harness
does the reasoning work, reads project evidence, and writes doctrine YAML into
the generated-artifact staging area. `spec-kitty` then validates those files,
records provenance, emits the project DRG layer, and promotes the results into
the live project doctrine tree.

The important boundary is simple:

- The harness owns **reading evidence and generating doctrine**
- `spec-kitty` owns **validation, neutrality gating, provenance, staging, and promotion**

This ADR exists to keep that boundary explicit and prevent future drift back to
an in-process model adapter.

## Decision

### 1. Canonical generated-artifact layout

The harness writes generated doctrine YAML under:

```text
.kittify/charter/generated/
  directives/
    <NNN>-<slug>.directive.yaml
  tactics/
    <slug>.tactic.yaml
  styleguides/
    <slug>.styleguide.yaml
```

The live promoted tree remains:

```text
.kittify/doctrine/
  directives/
  tactics/
  styleguides/

.kittify/charter/
  provenance/
  synthesis-manifest.yaml
```

### 2. Canonical identity rules

The harness must match both the filename rule and the YAML identity rule.

- Directives use `artifact_id = PROJECT_<NNN>` and filename `<NNN>-<slug>.directive.yaml`
- Tactics use `artifact_id = <slug>` and filename `<slug>.tactic.yaml`
- Styleguides use `artifact_id = <slug>` and filename `<slug>.styleguide.yaml`
- The top-level YAML `id` field must exactly match the target `artifact_id`

Examples:

- `directive:PROJECT_001` → `.kittify/charter/generated/directives/001-mission-type-scope-directive.directive.yaml`
- `tactic:testing-philosophy-tactic` → `.kittify/charter/generated/tactics/testing-philosophy-tactic.tactic.yaml`
- `styleguide:python-style-guide` → `.kittify/charter/generated/styleguides/python-style-guide.styleguide.yaml`

If the file is missing or the YAML `id` does not match, synthesis fails closed.

### 3. Evidence ownership

Evidence is split on purpose:

- `spec-kitty` owns evidence declaration and identity:
  - code-reading signals
  - configured URL lists
  - bundled corpus snapshots
  - hashing and provenance fields derived from that evidence
- The harness owns evidence consumption:
  - reading the repo and the URLs
  - deciding how that evidence should shape generated doctrine text
  - writing the generated YAML files that `spec-kitty` will validate

No internal HTTP fetcher, browser reader, or model client belongs inside
`spec-kitty` for this contract.

### 4. Operator CLI sequence

The canonical operator flow is:

1. Collect interview answers and any configured synthesis inputs.
2. Have the harness write generated YAML into `.kittify/charter/generated/`.
3. Validate the handoff without promotion:

```bash
spec-kitty charter synthesize --dry-run
```

4. Promote the validated artifacts into the live tree:

```bash
spec-kitty charter synthesize
```

5. Regenerate one bounded topic after the harness updates the corresponding
generated artifact:

```bash
spec-kitty charter resynthesize --topic directive:PROJECT_001
```

6. Inspect operator state, evidence summary, manifest health, and provenance:

```bash
spec-kitty charter status --provenance
```

### 5. Fixture adapter policy

`--adapter fixture` remains supported only as the deterministic regression
harness. It is not the default runtime path and it is not a production
generation policy.

## Consequences

### Positive

- One inference engine, the host harness already talking to the user.
- No hidden SDK calls or second API-key story inside `spec-kitty`.
- Clear separation between generation and validation.
- Provenance stays trustworthy because the CLI records the exact validated
handoff, not a hidden model invocation.

### Negative

- The harness now has to respect the file layout and identity rules exactly.
- Operator tooling must make the handoff state visible enough that a bad file is
easy to diagnose. That is why `charter status` and generated-artifact error UX
matter.

## More information

- `src/charter/synthesizer/generated_artifact_adapter.py`
- `src/specify_cli/cli/commands/charter.py`
- `src/charter/synthesizer/write_pipeline.py`
- `tests/agent/cli/commands/test_charter_status_cli.py`
