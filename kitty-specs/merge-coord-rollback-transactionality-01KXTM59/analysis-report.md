---
schema_version: 1
artifact_type: spec-kitty.analysis-report
command: /spec-kitty.analyze
mission_slug: merge-coord-rollback-transactionality-01KXTM59
mission_id: 01KXTM59YZZ6AGKA7YVJA0HCRS
generated_at: '2026-07-18T17:12:10.836974+00:00'
analyzer_agent: unknown
input_artifacts:
  spec.md:
    path: /home/stijn/Documents/_code/SDD/fork/spec-kitty-gate-doctrine/kitty-specs/merge-coord-rollback-transactionality-01KXTM59/spec.md
    sha256: 545d76fd95673cccc5a3fd28f57e330711bc2c7443da801e7a57222897e752fd
  plan.md:
    path: /home/stijn/Documents/_code/SDD/fork/spec-kitty-gate-doctrine/kitty-specs/merge-coord-rollback-transactionality-01KXTM59/plan.md
    sha256: 537ba064a8a9264d3c3a03b4591ccc6877c75490b3b42619dd038089cfc70a21
  tasks.md:
    path: /home/stijn/Documents/_code/SDD/fork/spec-kitty-gate-doctrine/kitty-specs/merge-coord-rollback-transactionality-01KXTM59/tasks.md
    sha256: cba06535380676417fdc10fab7b8a09c8912c7f1a67f14d252b76c423afba49b
  charter:
    path: /home/stijn/Documents/_code/SDD/fork/spec-kitty-gate-doctrine/.kittify/charter/charter.md
    sha256: cb2dc6cd12aade3d5464997467b7ecdbd3849ea3581207b58c207c3d16fff9b8
verdict: ready
issue_counts:
  critical: 0
  low: 3
  medium: 0
  high: 0
  info: 0
findings:
- id: I1
  severity: low
  category: inconsistency
  summary: Two coord-DONE reducers coexist (coord_incoherent_done_wps + _durable_done_wps_on_coordination_ref); convergence is a documented follow-up, not in scope.
- id: I2
  severity: low
  category: coverage
  summary: NFR-001/002/003 are pinned in WP DoD checkboxes but not in requirement_refs (the mapper accepts FR refs only) — coverage is real, the ref index just doesn't show it.
- id: I3
  severity: low
  category: process
  summary: WP dependencies were set via the frontmatter preserve-path because the finalize CLI's tasks.md dependency parser did not match the section phrasing; deps are correct and validated.
---

## Specification Analysis Report

**Mission**: `merge-coord-rollback-transactionality-01KXTM59` (P0 #2786 + #2367-B). Artifacts analysed:
`spec.md`, `plan.md`, `tasks.md`, `data-model.md`, `research.md`, 5 WP prompts. This mission was hardened
by three adversarial squads (post-spec, post-plan, post-tasks) whose findings are folded and recorded in
the spec's audit-trail sections; this report is the non-remediating cross-artifact consistency pass.

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| I1 | Inconsistency | LOW | data-model.md (two-readers note) | `coord_incoherent_done_wps` (new strand authority) and `_durable_done_wps_on_coordination_ref` (resume-dedup) both reduce coord-`DONE` via the same contract | Already documented as a follow-up; keep `coord_incoherent_done_wps` as THE strand authority. No action this mission. |
| I2 | Coverage | LOW | tasks/WP03,WP04 DoD | NFR-001/002/003 are pinned as WP DoD checkboxes but not in `requirement_refs` (the mapper takes FR refs only) | None required — coverage is real; the ref index simply can't hold NFRs. |
| I3 | Process | LOW | tasks/WP0*.md frontmatter | WP `dependencies` were set via the preserve-existing frontmatter path because the finalize CLI's tasks.md parser didn't match the section phrasing | Deps are validated (`validation_passed`); consider filing a CLI parser-robustness note, out of mission scope. |

**Coverage Summary Table:**

| Requirement Key | Has Task? | Task IDs (WP) | Notes |
|-----------------|-----------|---------------|-------|
| FR-001 modify #2786 assertion | ✅ | WP01 | red-on-base SC-006 |
| FR-002 #2786 companion (≥2-WP) | ✅ | WP01 (split-brain), WP02/WP03 (marker-names) | priti sequencing folded |
| FR-003 #2367-B bake repro | ✅ | WP01 | bake path only |
| FR-004 MergeState marker | ✅ | WP02 | + enumerator |
| FR-005 mark both strands | ✅ | WP03 | candidate = write-set field |
| FR-006 resume heal | ✅ | WP03 | strand-gated |
| FR-007 doctor check/fix | ✅ | WP04 | canonical surface + enumerator |
| FR-008 class-closing guard | ✅ | WP03 (primitive), WP05 (guard) | seven sites, 701 routed |
| FR-009 single coherence owner | ✅ | WP02 | consumed by WP03/WP04 |
| FR-010 SaaS fence | ✅ | WP03 | explicitly out-of-scope, documented |
| NFR-001 no happy-path regression | ✅ | WP03 DoD | byte-identical |
| NFR-002 repair idempotency | ✅ | WP03/WP04 DoD | resume-twice byte-identical |
| NFR-003 scoped test surface | ✅ | all WPs | |

**Charter Alignment Issues:** None. ATDD red-first (WP01), no-direct-push (consolidate→PR), architectural
gates (INV-5 #1827, AC-B3/AC-F1) honored in plan Charter Check; tracker gate satisfied (#2367 reparented/
retyped, #2795 filed). No charter MUST is violated.

**Unmapped Tasks:** None — every WP maps to ≥1 FR; every FR maps to ≥1 WP.

**Metrics:**
- Total Requirements: 10 FR + 3 NFR = 13
- Total Work Packages: 5 (16 subtasks)
- Coverage %: 100% (13/13 requirements have ≥1 task)
- Ambiguity Count: 0 (no vague-adjective NFRs; all measurable/behavioral)
- Duplication Count: 0
- Critical Issues Count: 0

**Verdict: READY** — no high/critical findings. The three LOW items are documented follow-ups /
process notes, none blocking implementation.
