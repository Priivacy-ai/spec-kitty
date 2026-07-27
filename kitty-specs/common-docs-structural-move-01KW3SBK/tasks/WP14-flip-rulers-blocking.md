---
work_package_id: WP14
title: Flip the 3 rulers to blocking (--strict + lockfile code change) + CI wiring + full-gate dry-run (C-005)
dependencies:
- WP13
- WP06
- WP10
- WP16
- WP18
requirement_refs:
- FR-011
- C-005
- NFR-006
tracker_refs: []
planning_base_branch: docs/2165-mission-b-structural-move
merge_target_branch: docs/2165-mission-b-structural-move
branch_strategy: Planning artifacts for this mission were generated on docs/2165-mission-b-structural-move. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/2165-mission-b-structural-move unless the human explicitly redirects the landing branch.
subtasks:
- T080
- T081
- T082
- T083
- T084
- T085
- T086
agent: 'claude:opus:python-pedro:implementer'
history: []
agent_profile: python-pedro
authoritative_surface: scripts/docs/check_docs_freshness.py
create_intent:
- tests/docs/test_rulers_blocking.py
execution_mode: code_change
owned_files:
- scripts/docs/check_docs_freshness.py
- .github/workflows/docs-freshness.yml
- tests/docs/test_rulers_blocking.py
shell_pid: '0'
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile: run `/ad-hoc-profile-load python-pedro` (or read `src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml` and adopt it). State which directives apply, then proceed.

## Objective

Flip Mission A's three **report-only** rulers to **blocking** (FR-011) — the flip is **non-uniform**: the ratchet + `related:` validator flip via their wired `--strict` flag; the **lockfile drift gate flips via THREE code changes**. Wire all three into `.github/workflows/docs-freshness.yml`, and pair the flip with a **full-gate dry-run over the whole tree before merge** (C-005 — gate-unmask cannot self-validate). This is IC-06, the spine's penultimate node — it runs only after the tree is clean (WP06 ADRs frontmattered, WP10 shadow trees gone) and drift = 0 (WP13).

## Context

`contracts/rulers-blocking.md` is the authority. Pre-state verified live on this branch:

- **R1 (`anti_sprawl_ratchet.py`):** `--strict` wired but off; blocking branch exists. Flip = **invoke with `--strict`** in CI.
- **R2 (`related_validator.py`):** `--strict` wired but off. Flip = **invoke with `--strict`** in CI.
- **R3 (`check_docs_freshness.py`) — CODE CHANGE (three parts):**
  1. Thread **`strict=True`** through `_check_inventory_lockfile_drift` (a **harmless no-op** in this codepath — annotate it; the value that flips the gate is (2)).
  2. **Escalate `INVENTORY-LOCKFILE-DRIFT` from `severity="warning"` to `severity="error"`** in `_lockfile_finding` — **this is the real gate change** (the aggregate exit keys off `any(f.severity == "error")`).
  3. **Remove the `if inventory_lockfile_check:` opt-in guard** in `run_orchestrator` (~line 433) — make the check **default-on**. Without (3) the escalation is **DEAD CODE in CI** (`docs-freshness.yml:24` invokes the script WITHOUT `--inventory-lockfile`).

- **CI wiring (no CI job invokes the ratchet or `related:` validator today):** add steps to `.github/workflows/docs-freshness.yml` running `anti_sprawl_ratchet.py --strict` and `related_validator.py --strict` alongside the `check_docs_freshness.py` step (now default-on / lockfile-checked).

- **C-005 full-gate dry-run:** quickstart S3 run against the **entire tree** (not the mission diff). A ruler that only bites on the mission diff is invisible until post-merge — **gate-unmask cannot self-validate**. The dry-run must go **RED on a re-introduced violation** and green on the clean tree.

## Requirement refs (hints for the orchestrator's map-requirements)

FR-011 (flip the rulers — non-uniform: 2 via `--strict`, 1 via the 3-part code change + CI wiring), C-005 (full-gate dry-run before merge), NFR-006 (lockfile gate blocking), SC-005 (a re-introduced second root / missing index.md / un-frontmattered ADR / lockfile drift is rejected by CI as `error`).

## Subtasks

### T080 — R3 code change 1: thread `strict=True`
Thread `strict=True` through `_check_inventory_lockfile_drift` so `run_generate_and_compare(..., strict=True)`. **Annotate** that this is a harmless no-op in this codepath (the drift report is identical) — it is threaded for intent/consistency; (2) is what flips the gate.

### T081 — R3 code change 2: escalate severity to `error`
In `_lockfile_finding`, change `severity="warning"` → `severity="error"` for `INVENTORY-LOCKFILE-DRIFT`. This is the **real gate change** — the aggregate exit keys off `any(f.severity == "error")`.

### T082 — R3 code change 3: remove the opt-in guard (default-on)
Remove the `if inventory_lockfile_check:` opt-in guard in `run_orchestrator` (~line 433) so the lockfile check is **default-on**. Without this, the escalation is dead code in CI (the workflow invokes the script without `--inventory-lockfile`). (Equivalent alternative: pass `--inventory-lockfile` in CI — but default-on is the robust choice; do that.)

### T083 — CI wiring in `docs-freshness.yml`
Add to `.github/workflows/docs-freshness.yml` step(s) invoking `anti_sprawl_ratchet.py --strict`, `related_validator.py --strict`, and `check_docs_freshness.py` (lockfile default-on). Add the `description_length_check.py` (WP11) to the suite too (NFR-003 now blocking). Name the exact steps.

### T084 — Ruler-blocking regression tests
Author `tests/docs/test_rulers_blocking.py`: a re-introduced **second doc root** → ratchet RED; a **missing section `index.md`** → ratchet RED; an **un-frontmattered ADR** → ratchet RED; a **dangling `related:` edge** → R2 RED; a **lockfile-drift tamper** (hand-edit frontmatter so generated ≠ committed) → R3 exits non-zero with `severity="error"`. Each was RED-first (proven against the pre-flip code).

### T085 — C-005 full-gate dry-run (RED on re-introduced violation)
Run the full gate (quickstart S3) over the **whole tree**: confirm green on the clean tree, then **re-introduce a violation** (e.g. a second root or an un-frontmattered ADR) and confirm the full-gate dry-run goes **RED**. This is the C-005 proof the gate actually bites — a mission-diff-scoped assertion is invisible until post-merge. **This is the mission's DoD-critical proof.**

### T086 — Verify + suite green on the clean tree
Confirm all three rulers are blocking and green on the clean post-move tree (drift = 0 from WP13, ADRs frontmattered from WP06, shadow trees gone from WP10). `ruff`/`mypy` clean on `check_docs_freshness.py`. Terminology guard clean.

## Surfaces & Loci (from `contracts/rulers-blocking.md`)

| Ruler | Surface | Flip mechanism |
|-------|---------|----------------|
| R1 anti-sprawl ratchet | `scripts/docs/anti_sprawl_ratchet.py` | invoke `--strict` in CI (wired, off) |
| R2 `related:` validator | `scripts/docs/related_validator.py` | invoke `--strict` in CI (wired, off) |
| R3 lockfile drift gate | `scripts/docs/check_docs_freshness.py` | **3 code changes** (below) |
| CI wiring | `.github/workflows/docs-freshness.yml` (`:24` invokes freshness w/o `--inventory-lockfile`) | add `--strict` steps + lockfile default-on |

**R3 three changes:** (1) `_check_inventory_lockfile_drift` → `strict=True` (annotated no-op); (2) `_lockfile_finding` `severity="warning"` → `"error"` (the real flip; aggregate keys off `any(f.severity=="error")`); (3) remove `if inventory_lockfile_check:` guard in `run_orchestrator` (~L433) so the check is default-on (else (2) is dead code in CI).

## Requirement → Subtask Traceability

| Requirement | Subtasks |
|-------------|----------|
| FR-011 (non-uniform flip + CI wiring) | T080, T081, T082, T083 |
| C-005 (full-gate dry-run before merge — RED on re-introduced violation) | T085 |
| NFR-006 (lockfile gate blocking) | T081, T082 |
| SC-005 (re-introduced violation rejected as `error`) | T084, T085 |

## Branch Strategy

Planning + final merge target: `docs/2165-mission-b-structural-move`. Depends on WP13 (drift = 0), WP06 (ADRs frontmattered), WP10 (single-root). The tree must be clean before the gates flip — else the flip red-fails the mission's own merge.

## Definition of Done

- [ ] R1 + R2 flipped via `--strict` **wired into `docs-freshness.yml`** (no CI job invoked them before).
- [ ] R3 lockfile gate flipped via the **three code changes** (thread `strict=True` [annotated no-op] + escalate severity to `error` + remove the opt-in guard / default-on).
- [ ] `tests/docs/test_rulers_blocking.py` — each violation class (R1 anti-sprawl, R2 related-dangling, R3 lockfile-drift) goes RED **independently**, RED-first against pre-flip code (one class per assertion, so a single always-RED gate can't mask the other two).
- [ ] **The RED proof runs through the WIRED CI invocation path**, not just the script called directly — re-introduce one violation of each class and confirm the `docs-freshness.yml` gate (as CI invokes it) exits non-zero; a script-level RED that the CI wiring doesn't actually call is the gate-silent-death failure mode.
- [ ] **C-005 full-gate dry-run: green on the clean tree AND RED on a re-introduced violation over the WHOLE tree** — the DoD-critical gate-unmask-cannot-self-validate proof.
- [ ] **No reference/runtime break introduced**: the rulers are green on the clean tree (drift = 0, ADRs frontmattered, single-root) — flipping does not red-fail the mission's own merge.
- [ ] `ruff` + `mypy` clean; terminology guard clean.

## Risks & Reviewer Guidance

- **Reviewer (C-005 merge-blocker focus):** the DoD is the full-gate dry-run **going RED on a re-introduced violation over the whole tree** — a green-on-clean-tree-only proof is insufficient (gate-unmask cannot self-validate). Confirm the RED demonstration.
- **R3 dead-code trap:** without change (3) the severity escalation never fires in CI — confirm the guard is removed (or the flag passed) AND the workflow actually exercises the lockfile check.
- **Flipping before drift = 0 / clean tree** self-blocks the merge — confirm WP13/WP06/WP10 landed first.
- The `strict=True` thread (1) is a no-op — do not expect it alone to change CI behavior; (2) is the real flip.

## Activity Log

- (populated at implement time)
- 2026-06-27T19:28:44Z – user – done+validated on assembled integration tree (571 docs tests green, 5 gates green); lane alloc impossible (diamond merge)
- 2026-06-27T19:28:46Z – user – approved: assembled-tree validation is the objective review (571 docs tests + 5 blocking gates green; WP14 C-005 RED-per-class proven)
