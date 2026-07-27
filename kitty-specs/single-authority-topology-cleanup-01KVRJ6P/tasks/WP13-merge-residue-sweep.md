---
work_package_id: WP13
title: 'Merge residue-gate sweep + auto-rebase 4th site (FR-012, #1887)'
dependencies:
- WP01
requirement_refs:
- FR-012
tracker_refs: []
planning_base_branch: feat/single-authority-topology-cleanup
merge_target_branch: feat/single-authority-topology-cleanup
branch_strategy: Planning artifacts for this mission were generated on feat/single-authority-topology-cleanup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/single-authority-topology-cleanup unless the human explicitly redirects the landing branch.
subtasks:
- T025
- T026
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1420779"
history:
- Created by /spec-kitty.tasks 2026-06-23
agent_profile: python-pedro
authoritative_surface: src/specify_cli/lanes/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/merge.py
- src/specify_cli/lanes/merge.py
- src/specify_cli/lanes/auto_rebase.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
Read `src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml` and adopt its
directives/tactics (or `/ad-hoc-profile-load python-pedro`). State which you applied.

## Objective
**FR-012 (#1887)** — converge ALL merge-path working-tree dirty/conflict gates
onto the single canonical coordination-residue authority, so a coordination-topology
merge does not leak residue into the target index and no gate carries its own
residue literal.

## Context (4 consumers; the constant + param already exist)
- `advance_branch_ref(...)` accepts `coord_owned_filenames` (`git/ref_advance.py:220`);
  `COORD_OWNED_STATUS_FILES` exists (`status/__init__.py:202`). The 3 callers
  `cli/commands/merge.py:1284`, `lanes/merge.py:458`, `lanes/merge.py:485` **omit** it.
- The post-merge invariant `cli/commands/merge.py:~2625` hardcodes a 3rd copy
  `{status.events.jsonl, status.json, meta.json}`.
- **4th site (brownfield)**: `lanes/auto_rebase.py:154` `_is_coordination_owned_artifact`
  (consumed `:351-352`, the "take theirs" arm) hardcodes a **drifting subset**
  `{tasks.md, lanes.json, acceptance-matrix.json}` — it OMITS
  `plan.md`/`issue-matrix.md`/`analysis-report.md`. Converge onto the canonical
  `is_coordination_artifact_residue_path` / `_COORD_RESIDUE_FILENAMES`
  (`mission_runtime/artifacts.py:71-80,113`).

## Subtasks
### T025 — Wire the 3 ref-advance callers + the post-merge invariant
Pass `coord_owned_filenames=COORD_OWNED_STATUS_FILES` at the 3 `advance_branch_ref`
callers. Replace the post-merge invariant's hardcoded literal with a call to
`is_coordination_artifact_residue_path`. Add a test: a post-write ff-advance with
coordination status residue on a checked-out worktree does NOT raise
`RefAdvanceDirtyWorktreeError`.

### T026 — Converge the auto_rebase 4th site
Replace `_is_coordination_owned_artifact`'s hardcoded `{tasks.md, lanes.json,
acceptance-matrix.json}` with the canonical `is_coordination_artifact_residue_path`
/ `_COORD_RESIDUE_FILENAMES` so the "take theirs" arm recognizes the FULL residue
set (incl. `plan.md`/`issue-matrix.md`/`analysis-report.md`). Add a test proving
a `plan.md` conflict on the coord side is now treated as coordination-owned. Add a
guard/assertion (or extend an existing test) that no merge-path gate carries its
own residue literal — the set is expressed once.

## Campsite (#1970)
Remove the now-dead local literal sets; hoist S1192; fix lint/type debt on touched
lines.

## Test approach (doctrine standard)

> **Test approach (doctrine standard — DIRECTIVE_034/036/041, #2071 CTn).** Assert the **observable contract** — returned value, resolved surface/ref, persisted JSONL/`meta.json`, CLI `--json` payload, or gate verdict — **never** the internal call graph or "collaborator X was invoked" (CT4/D036). Build mission fixtures by delegating to the **production creation seam** (`create_mission_core` / the existing `_stored_topology` helper), not a hand-rolled `meta.json` writer that rots (CT3); use **production-shaped data** — a real 26-char ULID + 8-char mid8, never a short placeholder (testing-principles). Any architectural guard/ratchet anchors keys on `_ratchet_keys.composite_key` (qualname + token-line) or an AST node — **never `file.py:NNN`** — and reuses `audit.py`/`_ratchet_keys.py` (CT1); resolve symbols by AST, never by grepping a string that collides with a surviving flag (NFR-003). Any xfail/skip is a **RED-by-design ATDD pin that names the WP that drains it** and is removed (not re-keyed) when the fix lands — never a defect mask (CT2). Prove behavior-neutrality via the **differential cell over the `(topology × transient)` matrix** PLUS at least one **absolute** assertion (see below) — never a brittle golden count of sites/LOC/refs (CT5); prefer a **tightening ratchet** (count only drops, keyed by symbol-set) over a fixed `== N`. **Pair every "allow / passes / absorbs / ignores-residue" assertion with its negative control** ("still-blocks / still-raises / wrong-topology-differs") — one-sided gate tests let the over-allow mutant survive. When a touched test goes red, classify it (stale→re-point preserving setup / fakeable→delete / valid→fix the product) and establish causation by **code-path coupling, not git-blame** (D041).

### WP13-specific test-DoD
- **(a) T025 negative-control paired cell.** Alongside the "coordination residue does NOT raise" assertion, add a paired cell: a **non-residue** dirty path (e.g. `.worktrees/`-rooted or an author-owned file) during ff-advance **still raises** `RefAdvanceDirtyWorktreeError`. Without the negative control, an over-allow mutant (ignore all dirt) survives.
- **(b) T026 parametrize over all three omitted members.** The take-theirs test is parametrized over **all three** previously-omitted residue members — `plan.md`, `issue-matrix.md`, `analysis-report.md` — not just `plan.md`; each must now be treated as coordination-owned on the coord side.
- **(c) AST/symbol-based "expressed-once" guard.** The literal-ban guard (no merge-path gate carries its own residue literal) must be **AST/symbol-based** — assert each consumer **imports `_COORD_RESIDUE_FILENAMES`** — with a **planted-offender self-test** (a synthetic source carrying its own residue literal trips the guard), reusing WP01's AST infra. A string-grep guard is theater.

## Definition of Done
- All 4 consumers draw the recognized-residue set from the single authority; the
  ff-advance + take-theirs tests pass; no second residue literal remains.
  `ruff`/`mypy` clean; full `tests/` green.
- T025 carries a paired negative control (non-residue dirty path **still raises**);
  T026 is parametrized over all three omitted members (`plan.md`/`issue-matrix.md`/
  `analysis-report.md`); the expressed-once guard is AST/symbol-based (import-of-
  `_COORD_RESIDUE_FILENAMES`) with a planted-offender self-test (no string-grep).

## Branch Strategy
`feat/single-authority-topology-cleanup`. Lane F. Worktree from `lanes.json`.

## Reviewer guidance
Confirm the auto_rebase 4th site now recognizes `plan.md`/`issue-matrix.md`/
`analysis-report.md` (the drift the brownfield squad found). Confirm no gate keeps
a private residue literal (I-4: expressed once).

## Activity Log

- 2026-06-23T07:38:00Z – claude:opus:python-pedro:implementer – shell_pid=1326489 – Assigned agent via action command
- 2026-06-23T08:02:58Z – claude:opus:python-pedro:implementer – shell_pid=1326489 – Ready: 4 consumers draw from single residue authority; ff-advance + take-theirs (parametrized plan/issue-matrix/analysis-report) + caller-wiring AST cell + expressed-once AST guard w/ planted offender; negative controls robust to extended residue set. --force: staleness is planning-artifact-only (spec.md/issue-matrix.md rebase conflict); owned code has no overlap with mission branch.
- 2026-06-23T08:03:55Z – claude:opus:reviewer-renata:reviewer – shell_pid=1420779 – Started review via action command
- 2026-06-23T08:09:49Z – user – shell_pid=1420779 – Review passed: T025/T026/expressed-once all met. 13/13 green, non-vacuous (8 cells go RED against pre-fix src incl. all 3 take-theirs members plan/issue-matrix/analysis-report + caller-wiring AST + import/literal guards). Residue literal genuinely gone not shadowed (merge.py status filename consts are unrelated path-builders). auto_rebase delegates wholesale; WP*.md preserved via authority tasks-dir rule. Negative controls real (author-owned obstruction still raises; non-residue conflict still halts Manual). Expressed-once guard AST/symbol-based w/ planted-offender self-test. ruff+mypy clean, no src suppressions. Stale spy = justified signature-forward kwargs passthrough. --force: 47-commit staleness is feat-side churn on OTHER files; all 3 owned src files have feat==pre-WP13-parent (zero conflict risk; verified bytes are exactly what lands).
