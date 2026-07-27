---
work_package_id: WP15
title: ADR-note amendment (FR-013) + LEAK-FRONTMATTER-MISMATCH retirement (FR-014)
dependencies:
- WP14
requirement_refs:
- FR-013
- FR-014
tracker_refs: []
planning_base_branch: docs/2165-mission-b-structural-move
merge_target_branch: docs/2165-mission-b-structural-move
branch_strategy: Planning artifacts for this mission were generated on docs/2165-mission-b-structural-move. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/2165-mission-b-structural-move unless the human explicitly redirects the landing branch.
subtasks:
- T087
- T088
- T089
- T090
- T091
agent: "claude:opus:python-pedro:implementer"
history: []
agent_profile: python-pedro
authoritative_surface: scripts/docs/version_leakage_check.py
create_intent: []
execution_mode: code_change
owned_files:
- scripts/docs/version_leakage_check.py
shell_pid: '0'
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile: run `/ad-hoc-profile-load python-pedro` (or read `src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml` and adopt it). State which directives apply, then proceed.

## Objective

Two spine-tail cleanups: **(FR-013)** amend the reconciliation ADR's "install as peer skills" Neutral note to record that the skills shipped as **3 doctrine tactics** (`common-docs-scaffold` / `common-docs-write` / `common-docs-find`); **(FR-014)** retire `version_leakage_check.py`'s `LEAK-FRONTMATTER-MISMATCH` enforcement now that the lockfile gate (WP14) is **proven red live + blocking**. This is IC-07 — it runs last because the LEAK retirement is gated on the lockfile gate being proven blocking.

## Context

- **FR-013 (sanctioned self-amendment):** Mission A's Accepted reconciliation ADR records an "install as peer skills" Neutral consequence; amend that prose to record the skills shipped as **3 doctrine tactics**, superseding the wording. This is a **sanctioned amendment of the ADR's own prose** — C-002's no-content-mutation protects ADR *decision-records being moved*, **not** this self-amendment. The file moved under WP06 to **`docs/adr/3.x/2026-06-27-1-common-docs-reconciliation.md`** — amend it at the new path. It is **explicitly excluded from the content-invariance check** (WP05/WP06 scope the check to *moved* ADRs, not this one).
  - **Ownership note:** this reconciliation ADR is **created at its new path by WP06's move** (it is not net-new here — WP15 must NOT declare it in `create_intent`), and it lives under WP06's `docs/adr/**`. WP15 amends it as a small, well-justified **out-of-map leeway edit** (one prose note), sequenced strictly after WP06 via the WP14 dependency — so WP15 owns only `version_leakage_check.py` and does not lane-collide with WP06.
- **FR-014 (gated retirement):** retire `LEAK-FRONTMATTER-MISMATCH` **only after** the lockfile drift gate (WP14) is proven red-live + blocking — the lockfile gate **subsumes** it (A deferred this retirement to B). Retiring it before the gate is proven blocking would drop frontmatter-drift enforcement with no replacement.

## Requirement refs (hints for the orchestrator's map-requirements)

FR-013 (amend the reconciliation ADR Neutral note → 3 doctrine tactics), FR-014 (retire `LEAK-FRONTMATTER-MISMATCH` once the lockfile gate is proven blocking). Depends on WP14 (the gate must be proven blocking first).

## Subtasks

### T087 — Confirm the lockfile gate is proven blocking (FR-014 precondition)
Verify WP14's C-005 dry-run demonstrated the lockfile gate going RED on a re-introduced drift (the gate is proven red-live + blocking). This is the gate for the LEAK retirement — do NOT retire before this is confirmed.

### T088 — Amend the reconciliation ADR Neutral note (FR-013)
At `docs/adr/3.x/2026-06-27-1-common-docs-reconciliation.md`, amend the "install as peer skills" Neutral note to record the skills shipped as **3 doctrine tactics** (`common-docs-scaffold` / `common-docs-write` / `common-docs-find`), superseding the wording. Keep it a minimal, sanctioned prose edit — do not rewrite the decision content. Confirm this file is excluded from the content-invariance check (it is the one sanctioned exception).

### T089 — Retire `LEAK-FRONTMATTER-MISMATCH` (FR-014)
Retire the `LEAK-FRONTMATTER-MISMATCH` enforcement in `scripts/docs/version_leakage_check.py` (the lockfile gate subsumes it). Remove the rule cleanly (no dead/effect-free handler left behind — Sonar). If `version_leakage_check.py` has other live rules, keep them; retire only `LEAK-FRONTMATTER-MISMATCH`.

### T090 — Confirm no enforcement gap
Confirm that with `LEAK-FRONTMATTER-MISMATCH` retired, frontmatter-drift is still enforced by the now-blocking lockfile gate (WP14) — there is no enforcement hole. If `version_leakage_check.py` is invoked by CI for this rule, update/remove that wiring coherently.

### T091 — Verify + suite green
Run the terminology guard (doctrine/prose touched — `test_no_legacy_terminology.py`), `ruff`/`mypy` on `version_leakage_check.py`, and the full rulers-blocking suite (WP14) still green. Confirm the ADR amendment did not trip the content-invariance check (it is scoped out).

## Surfaces & Loci

| Surface | Edit | Notes |
|---------|------|-------|
| `docs/adr/3.x/2026-06-27-1-common-docs-reconciliation.md` | amend "install as peer skills" Neutral note → 3 doctrine tactics | moved here by WP06; **excluded from content-invariance check** |
| `scripts/docs/version_leakage_check.py` | retire `LEAK-FRONTMATTER-MISMATCH` | only after WP14 proved the lockfile gate red-live + blocking |

The 3 doctrine tactics: `common-docs-scaffold` / `common-docs-write` / `common-docs-find`.

## Requirement → Subtask Traceability

| Requirement | Subtasks |
|-------------|----------|
| FR-013 (amend reconciliation ADR Neutral note — sanctioned self-amendment) | T088, T091 |
| FR-014 (retire `LEAK-FRONTMATTER-MISMATCH` once gate proven blocking) | T087, T089, T090 |

## Branch Strategy

Planning + final merge target: `docs/2165-mission-b-structural-move`. Depends on WP14 (the lockfile gate proven blocking). Spine tail — the mission's last WP. (The reconciliation ADR was moved by WP06; this WP amends it at `docs/adr/3.x/` — sequenced after WP06 via the WP14 dependency.)

## Definition of Done

- [ ] The reconciliation ADR Neutral note amended → records the **3 doctrine tactics**; a minimal sanctioned prose edit (not a decision-content rewrite); **excluded from the content-invariance check**.
- [ ] `LEAK-FRONTMATTER-MISMATCH` retired in `version_leakage_check.py` — **only after** WP14's lockfile gate is proven red-live + blocking (FR-014 precondition confirmed).
- [ ] **No enforcement gap**: frontmatter-drift still enforced by the now-blocking lockfile gate; no dead/effect-free handler left behind.
- [ ] **No reference/runtime break introduced**: the ADR is amended at its moved path `docs/adr/3.x/...`; the LEAK retirement leaves `version_leakage_check.py`'s other rules intact.
- [ ] Terminology guard + `ruff` + `mypy` clean; rulers-blocking suite still green.

## Risks & Reviewer Guidance

- **Reviewer (FR-014 ordering):** confirm the LEAK retirement happened **after** WP14 proved the lockfile gate blocking — retiring early drops frontmatter enforcement with no replacement.
- **The ADR self-amendment must not trip the content-invariance check** — confirm it is scoped out (WP05/WP06 check *moved* ADRs, not this sanctioned self-amendment).
- Removing a rule must not leave an empty/effect-free handler (Sonar) — retire cleanly.

## Activity Log

- (populated at implement time)
- 2026-06-27T19:28:48Z – user – done+validated on assembled integration tree (571 docs tests green, 5 gates green); lane alloc impossible (diamond merge)
- 2026-06-27T19:28:50Z – user – approved: assembled-tree validation is the objective review (571 docs tests + 5 blocking gates green; WP14 C-005 RED-per-class proven)
