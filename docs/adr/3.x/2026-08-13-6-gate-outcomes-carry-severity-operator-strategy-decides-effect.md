---
title: 'ADR: Gate outcomes carry a typed severity; an operator-configured error-handling strategy decides the CLI effect'
description: 'Gate outcomes emit a typed severity (BLOCKING / RECOVERABLE / WARN / INFO); an operator-configured error-handling strategy in .kittify maps severities to the CLI effect.'
status: Proposed
date: '2026-08-13'
related:
- docs/architecture/mission-gates.md
- docs/adr/3.x/2026-08-13-2-gates-are-declarative-asset-backed-doctrine-artefacts.md
- docs/adr/3.x/2026-08-13-4-executable-doctrine-runs-only-from-trusted-publishers.md
---
# Gate outcomes carry a typed severity; an operator-configured strategy decides the CLI effect

**Filename:** `2026-08-13-6-gate-outcomes-carry-severity-operator-strategy-decides-effect.md`

**Status:** Proposed

**Date:** 2026-08-13

**Deciders:** Operator (ATDD)

**Technical Story:** Resolves the fail-closed ([ADR 2026-08-13-2](2026-08-13-2-gates-are-declarative-asset-backed-doctrine-artefacts.md))
vs skip-and-proceed ([ADR 2026-08-13-4](2026-08-13-4-executable-doctrine-runs-only-from-trusted-publishers.md))
contradiction the dialectics pass surfaced. Instead of a per-gate boolean disposition, gate
outcomes are typed by severity and the CLI effect is an operator policy.

---

## Context and Problem Statement

The gate design produced two conflicting per-gate booleans: gates flip **fail-closed** (block on
failure), but untrusted packs were to be **skipped** (proceed). Same un-run gate, opposite
outcomes, decided by *why* it didn't run — and the "skip" branch silently no-ops security gates
in CI. A single boolean cannot express "proceed, but degraded, and record it," which is the real
operator need for many checks (a docs lint failing should not necessarily block a transition; a
missing security gate should).

The codebase already has the ingredients, **fragmented across five sites**:
`kernel.glossary_types.Severity` (`src/kernel/glossary_types.py:70`), `audit.models.Severity` +
its threshold `fail_on: Severity | None` with `severity <= fail_on_threshold`
(`src/specify_cli/audit/models.py:47,53,203`), `status.doctor.Severity`
(`src/specify_cli/status/doctor.py:26`), the charter-lint `SEVERITY_ORDER` blocking ladder
(`src/specify_cli/charter_runtime/lint/findings.py`, consumed by `analysis_report.py:338`), and
the `strictness` literals (`kernel.glossary_types.Strictness`, `runtime … schema.py:465`). The
`audit` module is already *exactly* the "block above a threshold" pattern requested.

## Decision Drivers

* One coherent model for "what happens when a check does not pass," across failed / degraded /
  informational / could-not-run outcomes.
* Operator owns strictness, not each gate author — mirrors linter/typechecker strictness config.
* Do not add a **sixth** Severity enum; converge on one canonical ladder.

## Decision Outcome

**A gate produces a typed outcome; the operator's error-handling strategy maps it to a CLI
effect.**

* **Severity ladder** (`ERROR_SEVERITY`): `BLOCKING` > `RECOVERABLE` > `WARN` > `INFO`.
  `RECOVERABLE` means "the system may proceed in a **degraded** fashion" (the outcome is
  recorded/surfaced, the transition is not necessarily stopped).
* **Every gate outcome carries a severity** — a check failure, and every *could-not-run*
  condition (untrusted publisher, crash, timeout, missing interpreter), maps to a severity.
  "Untrusted" is therefore not a special skip; it is one severity-bearing outcome among many.
* **The operator selects an error-handling strategy** in `.kittify` config, e.g.
  `block_above(RECOVERABLE)` — outcomes at or above the threshold block the transition; below it,
  the CLI proceeds (degraded) and records the finding. This is the existing `audit` `fail_on`
  threshold pattern, generalised.
* **Canonical severity, not a new enum.** `ERROR_SEVERITY` is defined once (extend/rename the
  kernel `Severity` — the layering-correct home, importable by doctrine) and the fragmented
  per-module Severity enums are migrated onto it. A gate schema references the canonical ladder.
* **A default strategy ships** (recommended `block_above(RECOVERABLE)` so `BLOCKING` and
  `RECOVERABLE` stop a transition by default, `WARN`/`INFO` do not) — chosen so security gates
  fail **closed** out of the box, and CI without operator config still blocks loudly rather than
  silently no-ops.

### Consequences

#### Positive

* One knob for strictness; the fail-closed/skip contradiction dissolves — the *operator's*
  threshold decides, uniformly, regardless of why a gate didn't pass.
* Consolidates five drifting Severity definitions onto one ladder (a debt-reduction win).
* `RECOVERABLE` expresses "proceed degraded," which no boolean could.

#### Negative

* Consolidating the existing Severity enums is a cross-cutting refactor with its own blast radius
  (audit, status/doctor, charter-lint, glossary) — must be sequenced carefully or scoped as a
  precursor.
* A permissive operator strategy can weaken security gates — the default must fail closed, and
  the effective strategy should be surfaced (so "why did this pass?" is answerable).

#### Neutral

* The strategy grammar (`block_above(threshold)` vs a per-severity action map) is a config-schema
  detail (open Q).

### Open questions (for scoping / a later pass)

1. Extend/rename `kernel.glossary_types.Severity`, or mint a new canonical `ERROR_SEVERITY` and
   migrate the others onto it?
2. Strategy grammar: single `block_above(threshold)`, or a per-severity action map
   (`{BLOCKING: block, RECOVERABLE: block, WARN: warn, INFO: log}`)?
3. Is severity gate-declared, outcome-declared (the check emits it), or both (gate caps it)?
4. Does the Severity consolidation ship as a precursor mission, or inside the gate mission?
