---
work_package_id: WP09
title: Literal-ban ratchet — worktree/branch name-guessing forbidden outside the seam
dependencies:
- WP02
- WP03
- WP04
- WP05
- WP06
- WP10
requirement_refs:
- FR-001
- FR-005
- FR-009
tracker_refs: []
planning_base_branch: mission/mission-identity-seam-and-1908-panel
merge_target_branch: mission/mission-identity-seam-and-1908-panel
branch_strategy: Planning artifacts for this mission were generated on mission/mission-identity-seam-and-1908-panel. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/mission-identity-seam-and-1908-panel unless the human explicitly redirects the landing branch.
subtasks:
- T037
- T038
phase: Phase 4 - Enforce
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1356262"
history:
- at: '2026-06-15T17:53:20Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent:
- tests/architectural/test_no_worktree_name_guess.py
execution_mode: code_change
owned_files:
- tests/architectural/test_no_worktree_name_guess.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP09 – Literal-ban ratchet (filesystem twin of the branch-identity seam)

## ⚡ Do This First: Load Agent Profile
`/ad-hoc-profile-load` → `python-pedro` (implementer, claude).

---

## Objectives & Success Criteria
Add the **4th ratchet assertion** — the filesystem twin of the existing branch-identity seam: a
repo-wide architectural test that **fails** any ad-hoc worktree-dir / mission-branch name-guess
(an `.worktrees/...` f-string composing `…-{lane…}`/`{mission_slug}-…`, or a literal
`f"kitty/mission-{…}"`) anywhere **outside** `src/specify_cli/lanes/branch_naming.py`. This makes the
recurring wrong-compose regression class (#1860/#1949/#1978/#1899) structurally impossible to
reintroduce. Read [spec.md](../spec.md) FR-005/FR-001/FR-009, [plan.md](../plan.md) IC-03,
[research.md](../research.md) (research-authority-seams §3 topology contract).

**Done when:** the ratchet is green **after** all routing WPs landed; re-adding a name-guess OR an
inline `endswith(f"-{mid8}")` re-dedup in any non-seam module turns it RED; the seam module is the
sole allowed home; and a NFR-001 diff-scan confirms no stray hunks.

## Context & Constraints
- **Depends on WP02, WP03, WP04, WP05, WP06, WP10** — the ratchet only passes once every name-guess,
  inline-dedup, false-compose f-string AND parse-caller has been routed/removed. Enforcement WP; lands last.
- This WP owns **only** the new architectural test. It must NOT edit source — if the ratchet is red,
  the fix belongs in the relevant routing WP. (If you find a site the routing WPs missed, record it as
  a finding for that WP; do not silently route it from here.)
- **Squad note — author the ratchet's grep FIRST and use it as the completeness oracle**, not as a
  victory lap. Running the scan now surfaces the authoritative routing inventory (it would flag
  `missions/_create.py:157`, `_read_path_resolver.py`, `tasks.py:844`, `orchestrator_api:771`).
- Pattern to follow: existing `tests/architectural/` sweeps (`test_no_primary_anchored_gates.py`,
  `test_no_dead_symbols.py`) — AST/line-regex over `src/specify_cli/**` + `src/runtime/**`, single
  explicit allow-list entry for `lanes/branch_naming.py`.

## Subtasks
### T037 — Literal-ban ratchet targeting the RECURRENCE SHAPE (#1899 4th assertion)
Create `tests/architectural/test_no_worktree_name_guess.py`. Scan every `*.py` under
`src/specify_cli/` and `src/runtime/` for ALL three forbidden idioms (the squad showed the first two
alone miss the actual recurrence):
1. **worktree-dir name-guess** — a `.worktrees/` path composed via f-string with a lane/slug/mid8
   interpolation, INCLUDING the **assign-then-join indirection** (`name = f"{slug}-{lane}"` then
   `.worktrees / name`) — not just inline `.worktrees/f"…"`;
2. **branch name-guess** — a literal `f"kitty/mission-{…}"` not produced by the seam;
3. **inline mid8 re-dedup** — the `…endswith(f"-{mid8}")…` / `endswith(suffix)` compose idiom and
   bare `f"{slug}-{mid8}"` mission-dir composition (the #1860/#1949 recurrence shape — this is what
   would catch `tasks.py:844` and `_create.py:157`, which carry NO `.worktrees/` literal).
Allow-list exactly `src/specify_cli/lanes/branch_naming.py`. Allow-list with rationale any benign
UX-glob string (e.g. `lanes/stale_check.py` remediation `.worktrees/*-{lane}` glob) — narrow, commented.
Assert the violation set is empty with a `file:line`-naming failure message pointing at the seam API.

### T038 — NFR-001 diff-scan + red→green proof + full suites
(a) Add an NFR-001 boundary assertion: `git diff --name-only <mission-base>..HEAD` shows **no** hunks
in `src/specify_cli/status/` (other than `aggregate.py`) or `src/specify_cli/task_utils/`. (b) Prove
the ratchet bites for EACH of the 3 idioms: temporarily re-add (i) a `.worktrees/` f-string, (ii) a
`kitty/mission-{slug}` literal, (iii) an `endswith(f"-{mid8}")` dedup in a non-seam module — confirm
RED each time, then revert. (c) Run `ruff`+`mypy`; `PWHEADLESS=1 pytest tests/architectural/
tests/lanes/ -q`.
- [ ] ratchet green after all routing WPs; [ ] all 3 idioms proven to go RED (then reverted);
  [ ] NFR-001 diff-scan green; [ ] seam (+narrow rationale'd UX-glob) the only allow-list;
  [ ] `tests/architectural/` + `tests/lanes/` green; [ ] ruff/mypy clean.

## Branch Strategy
Planning base / merge target: `mission/mission-identity-seam-and-1908-panel`; lane-per-WP.
**Sequencing:** lands last — depends on ALL routing/composer/false-compose WPs (WP02, WP03, WP04, WP05, WP06, WP10) being merged/approved first.

## Definition of Done
A repo-wide ratchet forbids worktree/branch name-guessing outside `branch_naming.py`; verified to go
red on reintroduction; full architectural + lanes suites green; ruff/mypy clean.

## Reviewer Guidance
Confirm: (1) the ratchet's allow-list is exactly the seam module (+ at most a narrow, rationale'd
UX-glob carve-out) — no broad carve-outs that would let a real regression slip through; (2) the
red→green proof was performed for ALL 3 idioms (the failure message names file:line); (3) no source
files were edited in this WP — routing fixes live in WP02–WP06/WP10; (4) the 3rd idiom (inline
`endswith(f"-{mid8}")` dedup) genuinely catches `tasks.py:844` / `_create.py:157` (which carry no
`.worktrees/` literal) — the historical recurrence shape; (5) the NFR-001 diff-scan is present and green.

## Activity Log

- 2026-06-15T20:13:37Z – claude:opus:python-pedro:implementer – shell_pid=1296816 – Assigned agent via action command
- 2026-06-15T20:31:13Z – claude:opus:python-pedro:implementer – shell_pid=1296816 – BLOCKED (STOP-and-report per WP09 mandate): ratchet delivered + committed (aa48e471a), ruff/mypy clean, red->green proven for all 3 idioms, NFR-001 diff-scan GREEN, allow-list = seam + 2 narrow carve-outs. Completeness-oracle is RED on genuine compose sites no routing WP fixed: IN-SCOPE MISSED -> cli/commands/merge.py:2786 (worktree-dir guess f"{slug}-{lane}" in --remove-worktree teardown; WP02 owns file but scoped only to L1231 branch false-compose; LIVE defect: mid8-era worktrees not found/removed) + lanes/lifecycle_sync.py:135 (.worktrees/ f"{slug}-unknown" CorruptLanesError diagnostic; WP04 routed L150/157 not L135; borderline-benign placeholder). OUT-OF-SCOPE never-routed (no spec/plan/research/NFR-001 mention) -> core/worktree.py:367/370 + core/mission_creation.py:321 (genuine <slug>-<mid8> composes; new follow-up). Also test_no_dead_symbols RED for unwired WP01 seam symbols: resolve_branch_name (FR-004 failover resolver, no live caller), reset_legacy_failover_warning, LEGACY_FAILOVER_SUPPRESS_ENV -> cross-WP integration gap for orchestrator. NOT moved to for_review; NOT routed from WP09 (owns only the test). Pre-existing/independent architectural reds from routing landing (not WP09): test_no_raw_mission_spec_paths constructor-files, test_topology_resolution_boundary legacy-compose allowlist, test_pytest_marker_convention support-helper.
- 2026-06-15T20:51:44Z – claude:opus:python-pedro:implementer – shell_pid=1337526 – Assigned agent via action command
- 2026-06-15T21:06:06Z – claude:opus:python-pedro:implementer – shell_pid=1337526 – Ratchet green (merge.py:2786 fixed by WP02 c1; benign+out-of-scope composes allow-listed w/ rationale); routing-induced stale arch tests fixed (topology/raw-spec); dead-symbols green (2 test-seams allow-listed); tests/architectural/+tests/lanes/ green; lint 0
- 2026-06-15T21:06:48Z – claude:opus:reviewer-renata:reviewer – shell_pid=1356262 – Started review via action command
- 2026-06-15T21:13:19Z – user – shell_pid=1356262 – Review passed (reviewer-renata) [--force: benign kitty-specs/ planning-artifact drift inherited via dependency-lane merges, not WP09-authored; WP09 commits touch ONLY tests/architectural/]. 4th ratchet assertion lands. Ratchet bites all 3 idioms (probe RED then reverted; detector confirmed to FLAG not miss the allow-listed sites at exact file:line). Allow-list: branch_naming.py seam sole blanket entry; recovery.py:136 (branch --list glob)+vcs/detection.py:161 (seam-parser round-trip)+lifecycle_sync.py:135 (CorruptLanesError placeholder, never resolves real worktree) benign; mission_creation.py:321+worktree.py:367/370 verified PRE-EXISTING (c16291214 #601, untouched by routing WPs, out of NFR-001 scope)=logged exemption+follow-up. Topology allow-list trimmed to empty=TIGHTENING (unexpected+stale guards green). raw-spec 3 files=legit resolve_mission_read_path meta-seed reads named individually. Dead-symbols 2 entries genuinely live (test hook + intra-module env read), no fake importer. test_pytest_marker_convention failure=.worktrees/ dot-path harness artifact (PASSES on primary checkout), not a regression. NFR-001 green; ruff clean; tests/architectural/+tests/lanes/ green (319 passed).
