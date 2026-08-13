---
title: Mission transition gates — declarative, asset-backed, trust-gated
description: How transition gates work under the declarative model — a first-class gate artefact kind whose check ships as an asset, is invoked via an entrypoint at a topology-resolved surface, runs only from trusted publishers, and is fail-closed by default.
doc_status: active
updated: '2026-08-13'
type: explanation
related:
- docs/architecture/mission-type-resolution.md
- docs/architecture/artifact-placement-seam.md
- docs/architecture/doctrine-kinds.md
- docs/adr/3.x/2026-08-13-2-gates-are-declarative-asset-backed-doctrine-artefacts.md
- docs/adr/3.x/2026-08-13-3-gate-execution-targets-through-kernel-surface-selector.md
- docs/adr/3.x/2026-08-13-4-executable-doctrine-runs-only-from-trusted-publishers.md
- docs/adr/3.x/2026-08-13-5-local-daemon-amortizes-doctrine-parse-and-caches-gate-verdicts.md
---
# Mission transition gates — declarative, asset-backed, trust-gated

> **Status: design (Proposed).** This page describes the intended model captured across
> ADRs 2026-08-13-2 … -5. It is being hardened before implementation; treat it as the design
> of record, not a description of shipped behaviour.

A **transition gate** is a deterministic check that runs when a work package crosses a lane
edge (e.g. `in_progress → for_review`) and returns a pass/fail verdict that can block the
transition. This page explains the declarative model that replaces the legacy
named-Python-handler registry.

## The four moving parts

| Concern | Answer | ADR |
|---|---|---|
| **What a gate is** | A first-class doctrine `gate` artefact kind (declarative YAML), reusable by id, tiered like every other kind. | [-2](../adr/3.x/2026-08-13-2-gates-are-declarative-asset-backed-doctrine-artefacts.md) |
| **What the check is** | Code shipped as an `asset` (inert blob, resolved by id), invoked by the gate's `entrypoint` oneliner. | [-2](../adr/3.x/2026-08-13-2-gates-are-declarative-asset-backed-doctrine-artefacts.md) |
| **Where it runs** | An `executionTarget` surface selector (kernel vocabulary) resolved by the topology-aware placement seam's new `execute_dir` verb. | [-3](../adr/3.x/2026-08-13-3-gate-execution-targets-through-kernel-surface-selector.md) |
| **Whether it may run** | Trust: built-in is release-signed and trusted; org/project packs are trust-on-first-use; untrusted ⇒ skip + warn. | [-4](../adr/3.x/2026-08-13-4-executable-doctrine-runs-only-from-trusted-publishers.md) |
| **How fast (later)** | An optional local daemon holds parsed doctrine + a deterministic verdict cache keyed on the pack content-hash. | [-5](../adr/3.x/2026-08-13-5-local-daemon-amortizes-doctrine-parse-and-caches-gate-verdicts.md) |

## Definition vs binding

Two separated concerns:

- **Definition** — the `gate` artefact says *what the check is*: which asset holds the code,
  the `entrypoint`, the `executionTarget`, the timeout, and the fail disposition.
- **Binding** — the `MissionStep` says *when it fires*: an `on_transition` edge plus the gate
  id. Definition is reusable across steps and mission types; binding is per-step and ships in
  the per-type mission bundle.

```yaml
# gate definition — packs/built-in/gates/docs-structural-lint.gate.yaml
id: docs-structural-lint
schema_version: "1.0"
description: "DIRECTIVE_042 structural lint for documentation missions"
asset: common-docs-structural-lint       # code blob (asset kind, inert, resolved by id)
entrypoint: "python {asset} --strict"     # {asset} → resolved asset path
executionTarget: primary                  # kernel surface selector → placement seam execute_dir
timeout_seconds: 120
disposition: fail_closed                   # exit 0 = pass; non-zero = fail (stderr → reason)
```

```yaml
# binding — packs/built-in/missions/mission-steps/documentation/validate/step.yaml
id: validate
# … unified MissionStep fields …
gates:
  - on_transition: "in_progress->for_review"
    gate: docs-structural-lint
```

## Execution model

1. A lane transition fires; the single generic `declarative-gate` dispatcher (the shrunken
   `GATE_REGISTRY`) is invoked with a `TransitionGateContext`.
2. The dispatcher resolves the gate's `executionTarget` selector through the placement seam,
   given the mission's `MissionTopology`, to a physical workdir (`execute_dir`).
3. It checks the **trust** of the gate's owning pack. Untrusted ⇒ **skip + warn**, transition
   proceeds unguarded. Trusted ⇒ continue.
4. It resolves the referenced asset to a path, runs the `entrypoint` in the resolved workdir
   under a bounded, network-denied context, and maps the exit code to a `GateVerdict`
   (fail-closed by default).

## Invariants

- Gates are **deterministic and side-effect-free** — pure checks, never mutate mission state.
  (Determinism is what makes verdict caching sound; see ADR -5.)
- The `asset` kind stays inert — resolved to a path, never self-executing. The gate is the
  only thing that turns a path into an invocation.
- Trust is only ever consulted for **executing code**; inert doctrine needs no trust decision.
- "Fail-closed" blocks only when the gate actually **runs**; an untrusted (skipped) gate
  protects nothing — this is surfaced loudly, not silently.

## Relationship to the mission subtree

Gates that are mission-type dependent (documentation linting, per-type consistency checks)
ship inside the per-type bundle under `packs/built-in/missions/<type>/`; shared gates live at
the built-in tier and are referenced by id. This follows the nested, self-contained mission
subtree fixed by [ADR 2026-08-13-1](../adr/3.x/2026-08-13-1-built-in-mission-subtree-stays-nested-retire-legacy-step-contracts.md).
