---
title: 'ADR: Transition gates are declarative, asset-backed, first-class doctrine artefacts'
description: 'Replaces the named-Python-handler gate registry with a first-class declarative `gate` kind whose check ships as an asset invoked via an entrypoint, fail-closed by default.'
status: Proposed
date: '2026-08-13'
related:
- docs/architecture/mission-gates.md
- docs/architecture/doctrine-kinds.md
- docs/adr/3.x/2026-08-13-1-built-in-mission-subtree-stays-nested-retire-legacy-step-contracts.md
---
# Transition gates are declarative, asset-backed, first-class doctrine artefacts

**Filename:** `2026-08-13-2-gates-are-declarative-asset-backed-doctrine-artefacts.md`

**Status:** Proposed

**Date:** 2026-08-13

**Deciders:** Operator (ATDD)

**Technical Story:** Follows [ADR 2026-08-13-1](2026-08-13-1-built-in-mission-subtree-stays-nested-retire-legacy-step-contracts.md),
which retires the legacy `MissionStepContract` surface that currently carries gate bindings.
Gate semantics must be re-homed onto the unified `MissionStep` model as part of that removal.

---

## Post-dialectics revision (2026-08-13)

Hardened after the dialectics pass (`work/gate-design-dialectics/`, `99-COHERENCE.md`). Settled deltas:

- **KEEP — gate is a first-class `ArtifactKind`** (operator decision, over the dialectic's
  boilerplate objection). Accept the ~8 totality-map edits as the cost of a uniform kind model.
- **CHANGE — no shell `entrypoint`.** Invocation is a **structured `interpreter` + `args` list**
  with `{asset}` as one argv element, no shell string (removes injection + the
  `sys.executable`-lacks-deps trap).
- **CHANGE — outcome is a structured JSON verdict carrying a severity, not exit-code + a
  fail-closed boolean.** Block-vs-proceed is decided by the operator's error-handling strategy
  over the severity ladder — see [ADR 2026-08-13-6](2026-08-13-6-gate-outcomes-carry-severity-operator-strategy-decides-effect.md).
  The "fail-closed by default" language below is **superseded** by that model.
- **CLARIFY — `spec-kitty-pre-review` stays a grandfathered *code* gate** (its inputs are an
  injected `ScopeSource` + baseline + changed-files SSOT, not cwd+exit-code). The dispatcher is
  "one generic declarative dispatcher **plus a few code gates**," not a full collapse.
- **ADD — determinism must be *enforced* by a sandbox** (network-denied, bounded), not asserted.

## Context and Problem Statement

Today a transition gate is a **binding** in a step-contract YAML — `on_transition:
"in_progress->for_review"`, `handler: "spec-kitty-pre-review"`, `fail_open: true` — where
`handler` is a *name* into `GATE_REGISTRY` (`src/specify_cli/review/gate_registry.py`), a
Python dict whose `run: Callable[[TransitionGateContext], GateVerdict]` is compiled code.
The binding is data, but the **check logic is Python registered in-process**. There is
exactly one handler, and it is **fail-open**.

Two problems: (1) adding a gate requires a code deploy (a new registered handler), not a
doctrine edit, so gates cannot ship as part of a mission-type's doctrine pack; (2) retiring
`MissionStepContract` (ADR 2026-08-13-1) removes the surface the gate binding lives on, so
gate semantics must move to the unified `MissionStep` model regardless.

Gates are **deterministic** — a simple code check or a script (documentation linting,
consistency checks, structural validation). That determinism is the lever: the check can be
declared as data and shipped in the pack rather than compiled into the CLI.

## Decision Drivers

* Gates should ship *with* the mission-type doctrine that needs them, per-type where relevant.
* Single canonical authority — one step model (`MissionStep`), one gate mechanism.
* Reuse the existing `asset` kind (the sanctioned way to ship executable logic downstream)
  rather than invent a second code-shipping mechanism.
* Determinism must be preserved and enforced (gates are pure checks, never mutate state).

## Considered Options

* **A — Keep the Python handler registry**, add handlers as needed (status quo, code-deploy per gate).
* **B — Declarative `gate` artefact kind**, check logic referenced from an `asset`, invoked via an entrypoint.
* **C — Inline command strings** in the gate/step YAML (no asset), executed directly.

## Decision Outcome

**Chosen option: "B".** A gate is a **first-class doctrine `ArtifactKind`** (`gate`), tiered
and DRG-participating like every other kind, reusable by id.

* **Code ships as an `asset`** (unchanged loose-contract inert blob, `mime` + `path`,
  resolved to a path, never auto-executed). The gate *references* the asset by id.
* **The gate declares how to run it** via an `entrypoint` (a Docker-style oneliner, e.g.
  `python {asset} --strict`, where `{asset}` resolves to the asset path). Option C (inline
  command strings) is **rejected**: it creates an unsandboxed arbitrary-shell surface inside
  the pack for negligible convenience over an asset.
* **Fail-closed by default** (`disposition: fail_closed`) — a flip from today's lone
  fail-open gate. Exit `0` = pass; non-zero = fail; captured stderr becomes the
  `GateVerdict` reason.
* **Binding lives on the `MissionStep`** (`gates: [{on_transition, gate: <id>, ...}]`) —
  definition (what the check is) and binding (when it fires) are cleanly separated. This
  keeps the edge-scoped transition model and `TransitionGateContext`.
* **`GATE_REGISTRY` collapses to one generic dispatcher** (`declarative-gate`) that reads the
  gate, runs the entrypoint against the referenced asset, and returns a `GateVerdict`. Named
  per-gate Python handlers are retired; the existing `spec-kitty-pre-review` gate is
  re-expressed declaratively (or kept as a single grandfathered code gate — see open Q).

### Consequences

#### Positive
* Adding/changing a gate is a doctrine edit, shippable per mission-type in the pack.
* One code-shipping mechanism (assets); the asset kind keeps its inert loose contract.
* Determinism is enforceable (pure check, exit-code contract).

#### Negative
* "Execute an asset" is **net-new machinery** — assets are resolved to a path today and
  never executed (see [ADR 2026-08-13-3](2026-08-13-3-gate-execution-targets-through-kernel-surface-selector.md)
  for *where* it runs and [ADR 2026-08-13-4](2026-08-13-4-executable-doctrine-runs-only-from-trusted-publishers.md)
  for *whether* it may run).
* Fail-closed-by-default is a behaviour change; existing flows must be audited for gates that
  were relying on fail-open.

#### Neutral
* A new `gate` `ArtifactKind` is added shortly after `mission_step_contract` is removed — net
  kind count roughly unchanged, but the new kind is declarative-data, not a code registry.

### Open questions (for the dialectics squad)
1. Does `spec-kitty-pre-review` become a declarative gate, or stay a single grandfathered code gate?
2. One asset per gate, or may a gate carry its own blob (collapsing asset+gate for non-reused checks)?
3. Gate→asset DRG edge: reuse `requires`, or a dedicated relation?
4. Where do gate *inputs* come from (env vars vs args vs cwd contents)? (Depth handled in ADR -3.)
