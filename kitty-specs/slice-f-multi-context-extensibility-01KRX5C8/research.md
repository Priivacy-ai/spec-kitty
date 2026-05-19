# Research — Slice F: Multi-Context Extensibility + Strategic Remediations

> Mission: `slice-f-multi-context-extensibility-01KRX5C8`
> Companion: [plan.md](plan.md) | [spec.md](spec.md)

This document records the Phase-0 research input for Slice F. Most of the research was already executed by `architect-alphonso` post-merge of Mission B and lives in the gitignored `work/` directory. This file references those artifacts and captures the binding plan-time decisions distilled from them.

---

## 1. Source research artifacts (gitignored)

| Artifact | Contents | Used for |
|---|---|---|
| `work/mission-b-post-merge-review.md` | Mission B closure audit | Identifying the absorbed-remediation candidates |
| `work/remediation-mission-debrief.md` | Per-finding rationale (HIGH-1 .. LOW-3, INFO-1) | Spec §"Verbatim References"; plan §1 component changes |
| `work/ratchet-coherence-audit.md` | 5-axis architectural model (axes A/B/C/D/E + cross-cut process); 26-gate inventory; Gap-A1 .. Gap-A8 | Plan §1.5 + §1.6 (burn-down model + symbol-level gate); WP12 FR-300 (5-axis README); contract-round-trip-frontmatter.md mechanism |
| `work/mission-c-slice-f-scope-proposal.md` | 12-WP decomposition, 4 lanes, dependency graph, risk register | plan §3 ATDD landing plan, plan §4 sequencing & risks, plan §1 WP table |
| `work/process-gap-1-contract-round-trip.md` | Why the human-only Step 3.5 isn't enough | contracts/contract-round-trip-frontmatter.md FR-140 design |
| `work/process-gap-2-no-dead-modules.md` | Module-level vs symbol-level dead-code | FR-120 / FR-121 design |

The spec embeds verbatim extracts from these documents in its §"Verbatim References" section so the spec is self-contained and committable. This research file points the planner / reviewer at the originals for fuller context.

---

## 2. Predecessor mission (Mission B)

Mission B (`charter-mediated-doctrine-selection-01KRTZCA`) shipped the **selection** layer of three-layer governance: `selected_<kind>` / `required_<kind>` parity across 8 kinds, the activation registry, mission-type profiles. Slice F builds on top — adding the DRG layer, the scoping layer, and the workflow layer.

Key Mission B artefacts Slice F reuses (per C-009):

- 8-kind plural-naming union semantics
- `DoctrineSelectionConfig.selected_<kind>` / `OrgCharterPolicy.required_<kind>`
- `ActivationEntry`, `MissionTypeProfile`
- The runtime → charter → doctrine boundary (`test_runtime_charter_doctrine_boundary.py`)
- The byte-stability allow-list mechanism (`_OPTIONAL_EMPTY_OMIT_KEYS`)

Mission B's planning artifacts ([../charter-mediated-doctrine-selection-01KRTZCA/](../charter-mediated-doctrine-selection-01KRTZCA/)) are the structural precedent for this mission.

---

## 3. HiC adjudication record (2026-05-18)

The spec records three binding HiC decisions at §5a (constraints C-003, C-004, C-005):

| HiC § | Decision | Where it binds |
|---|---|---|
| 5a.1 | DRIFT-1 alias deleted in 3.2.x (no `DeprecationWarning`, no sunset) | C-003 → FR-100..FR-103 → WP04 |
| 5a.2 | Burn-down policy is charter-pinned (binding) | C-004 → FR-303(a) → WP01 + WP12 |
| 5a.3 | HIGH-3 auth.transport descoped — ADR + ticket only | C-005 → FR-200..FR-202 → WP12 |

These need no re-debate. Plan-time decisions in [plan.md §6](plan.md#6-plan-time-decisions) extend the record with 6 question resolutions + 2 architect-side calls.

---

## 4. Plan-time decisions distilled into binding state

- **Q4** — Skill deployment: surface, don't overwrite. NOT this mission.
- **Q5** — `glossary.prompts` + `glossary.rendering`: **DELETE both** ([DM-01KRX6N0YAFBY7MTJC0CN3D3E4](decisions/DM-01KRX6N0YAFBY7MTJC0CN3D3E4.md)). Combined with `doctrine.templates.repository`, this is the FR-113 same-PR shrinkage 10 → 7.
- **Q6** — Forward-only scope (C-002 binds).
- **Q7** — Forward-staging convention destination: `src/specify_cli/upgrade/migrations/README.md`.
- **NEW-1** — Org-DRG source mechanism: local-path only in this mission.
- **NEW-2** — Workflow back-compat default: permanent (opt-in, not migration-required).
- **ARCH-1** — Workflow registry location: `src/specify_cli/next/_internal_runtime/workflow_registry.py`.
- **ARCH-2** — `__all__` scope: `src/charter/` + `src/kernel/` only.

---

## 5. Architectural model (5 axes from ratchet-coherence-audit §3)

The post-Mission-B audit identified that the 26 active architectural gates collectively encode a single 5-axis model:

| Axis | Invariant | Slice F adds |
|---|---|---|
| **A — Layer direction** | `kernel ← doctrine ← charter ← specify_cli`; mediated boundaries | Org-DRG loader (charter); CharterScope (charter); workflow registry (specify_cli/next) — all preserve the layering |
| **B — Surface completeness** | Declared surfaces match implemented reality (facades, schemas, contracts) | FR-140 contract round-trip backstop; FR-120 symbol-level dead-code gate (the `__all__` walk) |
| **C — Closed-vocabulary integrity** | Operator-authored tokens belong to closed sets; SSOT byte-identity | FR-302 glossary canonical promotion (Slice F terms); reuse of Mission B 8-kind set (C-009) |
| **D — Lifecycle presence** | Every shipped module has a runtime caller; every released version has a migration; bounded latency | FR-110/FR-111 burn-down meta-test; FR-113 Cat-7 shrinkage; NFR-002 latency budget preserved |
| **E — Dependency hygiene** | Dependency manifests exact; retired packages stay retired | NO CHANGE this mission — boundary preserved |

WP12 lands `tests/architectural/README.md` documenting this model (FR-300, AC-14).

---

## 6. Open follow-ups (NOT this mission)

- URL / package source for org packs (NEW-1 deferral)
- Skill deployment migration + drift gate (MED-1; the "operator-surface hygiene" mission)
- HIGH-4 policy.audit wiring (separate mission per spec §"Overview")
- Most of MED-4 orphans (per spec §"Overview"; remaining orphans go to a triage mission)
- Auth-transport deletion (Robert's call per C-005)
- Multi-branch workflow action graphs (RR-9 forward-compat hook only this mission)

---

## 7. References

- Spec: [spec.md](spec.md)
- Plan: [plan.md](plan.md)
- Data model: [data-model.md](data-model.md)
- Contracts: [contracts/](contracts/)
- ATDD coverage: [atdd-coverage.md](atdd-coverage.md)
- Quickstart: [quickstart.md](quickstart.md)
- Decision artifacts: [decisions/DM-01KRX6N0YAFBY7MTJC0CN3D3E4.md](decisions/DM-01KRX6N0YAFBY7MTJC0CN3D3E4.md)
- Mission B planning artifacts: [../charter-mediated-doctrine-selection-01KRTZCA/](../charter-mediated-doctrine-selection-01KRTZCA/)
- Gitignored research: `work/remediation-mission-debrief.md`, `work/ratchet-coherence-audit.md`, `work/mission-c-slice-f-scope-proposal.md`
