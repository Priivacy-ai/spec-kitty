---
title: Profile-Load Reliability (Squads & WP Prompts)
description: 'Why adversarial/research squads stopped loading charter agent profiles, and the near-term stabilization design: orchestrator-resolves-then-injects, fail-loud dispatch, and the /spk-load-profile primitive.'
doc_status: active
updated: '2026-08-30'
related:
- docs/architecture/governed-profile-invocation.md
- docs/architecture/multi-agent-orchestration.md
- docs/architecture/charter-backend-service-future.md
---
# Profile-Load Reliability (Squads & WP Prompts)

This document records a corroborated investigation into why **research / adversarial
squads recently stopped loading charter agent profiles**, and defines the **near-term
(3.2.6-scope) stabilization design**. The deployable charter-backend evolution that this
work makes possible is a **separate, backlog-scoped** design — see
[Charter Backend Service (Future)](charter-backend-service-future.md).

> **Provenance.** Root cause established 2026-08-30 by a five-agent corroboration squad
> (researcher, debugger, reviewer, architect lenses), each profile-loaded through the
> charter API. The squad overturned an initial mis-attribution (see §2.4) and converged
> on the activation-allowlist root cause with live-command and git evidence.

## 1. Symptoms

Squad delegates dispatched at a point-cut (per the `adversarial-squad` skill) were
expected to load a doctrine lens via the charter API and act under it. Recently, delegates
assigned certain lenses acted **unprofiled** — no initialization, boundaries, directives,
or tactics applied — while nothing errored visibly at the orchestrator.

## 2. Root cause — a charter activation-allowlist gap (Issue 1)

The loading **mechanism is healthy**. In live testing, 7/7 *activated* profiles resolved
`EXIT 0` through `spec-kitty agent profile show <id>`, and `spec-kitty charter context
--action <x> --json` never failed. The failure is a **data + fail-open** defect, not a
code or template regression.

### 2.1 The gate
`src/specify_cli/cli/commands/profiles_cmd.py:337` (FR-014, introduced in #1636
`488fe34e0c`) refuses any profile absent from the charter's `activated_agent_profiles`
allowlist:

```
Error: profile 'doctrine-daphne' is not activated.
```

The two source files exist (`packs/built-in/agent_profiles/doctrine-daphne.agent.yaml`,
`…/randy-reducer.agent.yaml`) and are declared DRG nodes — they are **de-activated, not
missing**. Count check: **25 source profiles, 23 activated → the 2 omitted are exactly the
2 the squad skill recommends.**

### 2.2 The regression commit
`9a99801f1b` (2026-08-08, *"feat(charter): activate writing-comms & diagramming doctrine
set"*) first **materialized** the allowlist (23 entries) in
`.kittify/charter/charter.yaml:1744`, silently omitting `doctrine-daphne` and
`randy-reducer`. The parent commit had **no allowlist key** → three-state `None` → *all*
built-in profiles resolved (NFR-001 back-compat), so squads worked before that date. This
matches "recently stopped."

### 2.3 It ships upstream
`src/charter/packs/default.yaml:187` — the built-in default charter pack — carries the
same allowlist and **also omits both profiles**. **Every new project inherits the gap**,
not just this dogfooding checkout.

### 2.4 The seam gap (why it's silent)
The `adversarial-squad` skill (`SKILL.md:43,47`) **hardcodes** the persona names
`doctrine-daphne` and `randy-reducer` with no reconciliation against the activated set.
Its fallback clause sanctions reading the raw YAML **only for "a read-only harness that
cannot invoke the CLI."** A *de-activation* `EXIT 1` is a **different failure mode the
clause does not cover** — so a compliant delegate has no sanctioned recovery and proceeds
**unprofiled**. There is no canonical "squad-eligible profiles" query; the skill roster
and the activation set drifted apart the moment the allowlist was compiled.

> **Adjudicated divergence.** An initial trace blamed #1840 `60f038cee2` (2026-07-28) for
> flipping the load instruction from a YAML read to a CLI call. The debugger and architect
> lenses refuted this: #1840 **strengthened** the instruction (it never removed loading);
> the CLI works for any *activated* profile. The true cause is the 2026-08-08 allowlist.
> A secondary, narrower contributor remains for genuinely CLI-less harnesses: #1840's
> fallback YAML path has since drifted across two relocations.

## 3. Secondary finding — WP-prompt naming hygiene (Issue 2, LOW)

- **`ad-hoc-load` does not exist anywhere** (0 hits). It is a conflation; the real token
  is `/ad-hoc-profile-load`.
- `/ad-hoc-profile-load` is a **deliberately maintained, test-locked** (`tests/doctrine/
  test_spk_skill_pack.py:127`) compatibility alias for canonical
  `spk-doctrine-profile-load`. It **resolves correctly** — nothing is broken. This is
  canonical-naming drift (LOW), not a defect.
- Software-dev WP source templates reference the legacy alias
  (`packs/built-in/missions/software-dev/templates/task-prompt-template.md:31`, the
  `implement`/`review`/`tasks(-packages)` prompts, `reviewer-implementer-role-separation.
  tactic.yaml:26`, and the rc35 handoff migration).
- **`research` and `documentation` task-prompt templates carry no profile-load section at
  all** — a real cross-mission-type inconsistency, but *additive*, not a rename target.

## 4. Near-term stabilization design (3.2.6 scope)

Three coordinated changes. The activation-data fix restores squads immediately; the
orchestrator-injects contract closes the failure **class**.

### 4.1 Fix the activation data (close by construction)
Activate the two doctrine lenses everywhere the allowlist is authored:
- This project: `spec-kitty charter activate agent-profile doctrine-daphne randy-reducer`
  (or edit `charter.yaml` + `charter sync`).
- Upstream default pack: add both to `src/charter/packs/default.yaml:187`.
- **Regression guard:** a test asserting *every lens the `adversarial-squad` skill names
  resolves `EXIT 0`* (or, equivalently, source-profile-count parity for squad-eligible
  lenses). This closes the defect class per directive 043 (close-by-construction).

### 4.2 Orchestrator-resolves-then-injects (the durable seam fix)
Make the **orchestrator** — the one context that reliably *can* resolve — load each lens
**once**, with overlays / `specializes_from` lineage / `enhances`/`overrides` applied, and
**inject the resolved profile + compact action context inline** into each delegate prompt.
Consequences:
- Removes the subagent's dependency on **any** runtime call (CLI *or* backend). Works for
  read-only, shell-less, headless, and stale-cached-copy harnesses alike.
- **Fail-loud by construction:** an unresolved / de-activated lens errors *at the
  orchestrator*, which substitutes, activates, or aborts — a delegate can **never** be
  dispatched unprofiled. This is what converts Issue 1's class from "silent unprofiled" to
  "loud at dispatch."
- Use `charter context`'s existing `mode: compact`; inject profile-init + boundaries +
  directive **IDs**, not full bodies. Keep a *hybrid*: a runtime pull for an on-demand
  tactic stays **allowed where available**, never **required**.

### 4.3 The `/spk-load-profile <id> <instructions>` primitive
Consolidate `spk-doctrine-profile-load` + the `ad-hoc-profile-load` alias into a single
dispatch primitive `/spk-load-profile <name|id> <instructions>` that both **resolves** the
profile and **carries the task** the profiled agent runs — the surface the orchestrator
emits under §4.2. Retain the two existing names as **redirecting aliases** (they are
test-locked — redirect, never delete). *(New surface: `/spk-load-profile` does not exist
today.)*

### 4.4 WP-prompt hygiene (LOW, optional)
If pursued, rename WP-template references `/ad-hoc-profile-load → /spk-load-profile`,
**keeping the leading slash**, and:
- **Exclude** the alias-*declaring* surfaces (`spk-doctrine-profile-load/SKILL.md:35`,
  `src/doctrine/skills/README.md:116`) — they are test-locked; editing them goes red.
- Do it via a **new forward migration**, not by editing the shipped rc35 migration in
  place (mutating emitted text diverges already-migrated installs).
- Gate on `pytest tests/doctrine/test_spk_skill_pack.py`.
- The research/documentation missing-section gap is a **separate additive** item.

## 5. Scope boundary

| In 3.2.6 | Backlog (NOT 3.2.6) |
|---|---|
| §4.1 activation-data fix + regression guard | Deployable charter backend service (API/MCP) |
| §4.2 orchestrator-injects contract + fail-loud dispatch | Remote compute / shared cache / out-of-cycle context precompute |
| §4.3 `/spk-load-profile` consolidation | — |
| §4.4 WP-prompt hygiene (optional, LOW) | — |

The backend evolution is deliberately **out of 3.2.6**. §4.2 is intentionally a transport
change the *orchestrator* owns, so a future backend slots in behind the **same resolution
contract** without touching delegates. See
[Charter Backend Service (Future)](charter-backend-service-future.md).

> **Freeze note.** The `adversarial-squad` skill and charter packs are doctrine surfaces;
> some changes may fall under the 3.2.x doctrine-surface freeze (`pr:deferred`). Sequence
> the data fix (§4.1) first — it restores squads with the least surface.
