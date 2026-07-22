---
work_package_id: WP12
title: Enforcement gates + test posture (the join)
dependencies:
- WP03
- WP04
- WP06
- WP07
- WP08
- WP11
requirement_refs:
- C-002
- NFR-002
- NFR-003
- NFR-005
- NFR-006
- NFR-007
tracker_refs:
- '883'
planning_base_branch: mission/883-mission-type-governance-profiles
merge_target_branch: mission/883-mission-type-governance-profiles
branch_strategy: Planning artifacts for this mission were generated on mission/883-mission-type-governance-profiles. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/883-mission-type-governance-profiles unless the human explicitly redirects the landing branch.
subtasks:
- T064
- T065
- T066
- T067
- T068
- T069
- T070
shell_pid_created_at: "1784093792.51"
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1995887"
history:
- at: '2026-07-14T21:00:00Z'
  actor: claude
  action: Generated via /spec-kitty.tasks (IC-09, the join — enduring guards + terminal DRG regenerate)
agent_profile: python-pedro
authoritative_surface: tests/
create_intent:
- tests/doctrine/test_mission_type_governance_isolation.py
- tests/integration/test_mission_type_resolution_integration.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- tests/doctrine/test_mission_type_governance_isolation.py
- tests/integration/test_mission_type_resolution_integration.py
- src/doctrine/graph.yaml
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

`/ad-hoc-profile-load python-pedro` (role: implementer). Then read: [plan.md](../plan.md) §IC-09 (esp. the
"EXCLUDES IC-07" note), [spec.md](../spec.md) NFR-005/006/007 + SC-001/002/003/006,
[contracts/resolution-and-enforcement.md](../contracts/resolution-and-enforcement.md) C5, and the ADR
"Confirmation" section (enduring vs transitional). This WP authors the **enduring** behavioural guards and
performs the terminal DRG regenerate.

## Objective

Author the enduring, behavioural enforcement guards — **non-leakage** (URN-normalized denylist) with its
**non-vacuity twin** (shared action name), and **determinism** — at both the doctrine-module and
integration tiers, prove the unknown-typed hard-fail / typeless-degrade posture, **delete every remaining
transitional parity scaffold** (NFR-005 / C-002), and run the **single terminal**
`regenerate-graph --check`. This is the join that closes the mission.

**Dependency posture (binding):** WP12 depends on WP03, WP04, WP06, WP07, WP08, WP11 — and **explicitly
NOT WP09/WP10** (the detachable dossier lane). The enduring governance guards need the seam + leak-closure
+ content + steps, **not** the dossier flip; gating the join on the non-blocking lane would violate
FR-007/NFR-004.

## Context

- Enduring tests are **behavioural**, at doctrine-module (no `specify_cli` import) + integration level —
  not byte-pins on the removed path.
- The non-leakage test must compare **canonical URNs** on both sides (denylist + resolved set).
- The non-vacuity twin must fire through an action name **shared** across mission types so it cannot pass
  vacuously (it proves software-dev **does** resolve the denylisted set).
- The exact denylist membership is settled **here** (spec assumption), not at spec level.
- The terminal `regenerate-graph --check` is owned **only** by this WP (WP01 dangler-removal + WP06/07/08
  authoring both feed `graph.yaml`; running it once here avoids clobbering freshness).

## Subtask guidance

- **T064 — non-leakage (doctrine-module).** In `tests/doctrine/test_mission_type_governance_isolation.py`,
  assert each of documentation/research/plan's resolved (type ⊕ action) URN set is **disjoint** from a
  curated, URN-normalized software-dev-only denylist. Author the denylist membership here (settle it).
- **T065 — non-vacuity twin.** Add the twin proving software-dev **does** resolve that denylist, exercised
  through an action name **shared** across types (so the disjointness in T064 cannot pass vacuously).
- **T066 — determinism (NFR-007).** Assert two resolutions of identical inputs are **byte-identical**
  (doctrine-module).
- **T067 — integration (SC-001/004).** In `tests/integration/test_mission_type_resolution_integration.py`,
  exercise a **real** documentation/research/plan mission and assert domain-appropriate governance + gates
  resolve with **zero** software-dev-only doctrine. **Add a positive membership assertion (SC-004
  test-checkable, not prose-reviewed):** the resolved governance URN set for each type is a **superset (⊇)**
  of the expected authored+referenced artifact ids for that type (e.g. documentation ⊇ the 5 net-new
  styleguide URNs + audience/review-flow action-grain ids; research ⊇ spike-timebox-policy +
  citation-discipline + the referenced ids; plan ⊇ its referenced planning ids). Assert on **resolved
  URNs** — keep it behavioural, not a code-shape ratchet; source the expected-id lists from the authored
  profiles, not a frozen literal snapshot.
- **T068 — hard-fail / degrade (SC-002).** Assert an **unknown typed** mission hard-fails on every
  resolution path (prompt build + step bootstrap) and a **typeless** caller degrades neutrally — never a
  silent software-dev load — while a known-empty-grain (plan) resolves empty without error (FR-004).
- **T069 — scaffold sweep (NFR-005 / C-002).** Grep the tree and **delete every remaining transitional
  parity/snapshot scaffold** referencing the removed path (per the tasks.md ledger: WP03/WP10/WP11 should
  each have deleted their own; this is the belt-and-suspenders assertion that **0** survive at merge). Add
  an assertion/guard that fails if a parity-scaffold marker reappears.
- **T070 — terminal DRG regenerate.** Run the single `regenerate-graph --check` (after WP01 + WP06/07/08
  have landed), confirming `graph.yaml` freshness with all authored artifacts + removed danglers. Run the
  terminology guard (`pytest tests/architectural/test_no_legacy_terminology.py`). `ruff` + `mypy` clean.

## Branch Strategy

Planning artifacts were generated on `mission/883-mission-type-governance-profiles`. This WP branches from
the mission base during `/spec-kitty.implement` and merges back into
`mission/883-mission-type-governance-profiles`. It is the terminal join — deps WP03, WP04, WP06, WP07,
WP08, WP11 (NOT WP09/WP10). It owns the single `regenerate-graph --check`.

## Definition of Done

- [ ] Non-leakage test (URN-normalized denylist) green as an **enduring** doctrine-module check (NFR-006).
- [ ] Non-vacuity twin fires through a **shared action name** and proves software-dev resolves the denylist.
- [ ] Determinism test (byte-identical) green (NFR-007).
- [ ] Integration test: real doc/research/plan mission resolves domain governance + gates, **zero** sw-dev
      doctrine (SC-001), **and** the resolved URN set ⊇ the expected authored+referenced ids per type
      (positive membership check — SC-004 test-checkable, behavioural on resolved URNs).
- [ ] Unknown-typed hard-fails on every path; typeless degrades; known-empty-grain resolves empty (SC-002/FR-004).
- [ ] **0** transitional parity/snapshot scaffolds survive at merge (NFR-005 / C-002); a guard prevents
      their reappearance.
- [ ] Single terminal `regenerate-graph --check` green; terminology guard green; `ruff` + `mypy` clean.

## Risks

- **Vacuous non-leakage** — without the shared-action-name twin, disjointness can pass trivially. The twin
  is mandatory.
- **Gating the join on Lane D** — do NOT add WP09/WP10 as deps (FR-007/NFR-004); the dossier lane is
  deliberately non-blocking.
- **Clobbered DRG freshness** — this WP is the single regenerate owner; confirm WP01 + WP06/07/08 have
  landed before running it.
- **Code-shape ratchets** — keep enduring tests behavioural, not pins on the removed path (D7).

## Reviewer guidance (reviewer-renata, opus)

- Confirm the non-vacuity twin uses a genuinely **shared** action name and would fail if governance were
  empty (not a tautology).
- Confirm both sides of non-leakage are canonical-URN-normalized.
- Grep the whole tree for surviving parity/snapshot scaffolds (expect 0) and confirm the reappearance guard.
- Confirm WP12 has **no** dependency on WP09/WP10 and that the terminal DRG regenerate ran once, green.

## Activity Log

- 2026-07-15T05:01:54Z – user – Moved to planned
- 2026-07-15T05:02:01Z – claude:sonnet:python-pedro:implementer – shell_pid=1940466 – Started implementation via action command
- 2026-07-15T05:35:21Z – claude:sonnet:python-pedro:implementer – shell_pid=1940466 – WP12 join complete: terminal DRG regenerate clean (--check green, freshness reds resolved); non-leakage + MANDATORY non-vacuity twin (sw-dev resolves the 8-entry denylist via shared 'implement' probe; proven to fail loud on broken resolution) + determinism (NFR-007) doctrine test; integration SC-001/002/004; 0 surviving transitional scaffolds; marker-convention gate fixed (WP02 pytestmark). Suites: doctrine+integration+charter 4726 passed/1 skipped; architectural 1004 passed post-fix. --force: lane carried only stale planning artifacts (canonical on planning branch); deliverables committed.
- 2026-07-15T05:36:39Z – claude:opus:reviewer-renata:reviewer – shell_pid=1995887 – Started review via action command
- 2026-07-15T05:57:53Z – user – shell_pid=1995887 – APPROVED (capstone join). --force: stale-lane guard (lane carries stale kitty-specs; canonical on planning branch) - orchestrator-sanctioned, same as implementer's in_review move. Cycle-1 artifact was a workspace auto-merge re-dispatch (#771 lane-f), NOT a code rejection. C5 proven: non-leakage disjoint on canonical URN; non-vacuity twin EMPIRICALLY FIRES (healthy sw-dev resolves 8/8 via shared 'implement' probe; drop implement->missing=8->fails loud, not tautological); determinism NFR-007; hard-fail/degrade FR-003/003a/004; integration SC-001/002/004. regenerate-graph --check CLEAN. 0 scaffolds survive. Gates: doctrine+integration+charter 4726 passed/1 skip; architectural 0 failed serially (1 -n auto parallel flake, passes serially, untouched by mission); ruff+mypy+terminology clean. NON-BLOCKING: T069 self-imposed reappearance guard absent (spec NFR-005/C-002/SC-006 0-survive MET); stale docstring test_resolved_mission_type_context.py:11-12; report arch parallel flake.
