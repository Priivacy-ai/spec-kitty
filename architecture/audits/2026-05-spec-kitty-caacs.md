# spec-kitty CaaCS Audit — 2026-05

## Audit metadata

- **Repository**: `spec-kitty` (fork at `/home/stijn/Documents/_code/SDD/fork/spec-kitty`)
- **Branch**: `feat/caacs-doctrine`
- **Commit SHA at audit time**: `bc64dec6ee37dbbd6bc21a0a1aa3195f2bab1b57`
- **Audit date**: 2026-05-08
- **Window**: 1 year (`--since="1 year ago"`); velocity uses 2 years
- **Scope**: `src/` only (`src/specify_cli/`, `src/doctrine/`, `src/charter/`, `src/kernel/`,
  plus three empty leftover dirs `src/runtime/`, `src/dashboard/`, `src/constitution/` that
  contain only `__pycache__/` and are flagged as cleanup candidates).
- **Exclusion list applied** (vanity / generated / non-code):
  `**/__pycache__/**`, `**/.mypy_cache/**`, `**/CHANGELOG*.md`, `**/*.lock`,
  `uv.lock`, `poetry.lock`. Generated agent directories (`.claude/`, `.amazonq/`, etc.)
  live outside `src/` and are naturally excluded by the scope filter.
  No `**/*.json` exclusion was applied because there are very few JSON files in `src/`
  and they are intentional (schemas, manifests, `default-toolguides.json`); excluding
  them would have hidden two legitimately churning schema files.
- **Tooling**: `git` 2.x, Python 3.13.12, `radon` 6.0.1. `cloc` is not installed on
  this machine, so SLOC counts use `wc -l` instead (acceptable for the Python-only
  scope; documented under "Limitations").
- **Producer**: researcher subagent ("Reza"), instructed by the
  `forensic-repository-audit` tactic and `legacy-codebase-triage` procedure on
  this branch. Not architect-reviewed.

## Methodology

The five core CaaCS recipes from the
[`forensic-repository-audit`](../../src/doctrine/tactics/shipped/analysis/forensic-repository-audit.tactic.yaml)
tactic were executed verbatim against `src/`, with the exclusion list above
applied. The procedure
[`legacy-codebase-triage`](../../src/doctrine/procedures/shipped/legacy-codebase-triage.procedure.yaml)
specifies the additional steps (temporal coupling, complexity overlay, DDD-tentative
classification, Eisenhower triage). The exact commands run are:

```bash
# 1. Churn (top 50)
git log --format=format: --name-only --since="1 year ago" -- src/ \
   ':!**/CHANGELOG*.md' ':!**/__pycache__/**' ':!**/*.lock' ':!**/uv.lock' \
   ':!**/poetry.lock' ':!**/.mypy_cache/**' \
  | grep -v '^$' | sort | uniq -c | sort -nr | head -50

# 2. Bus factor (overall + per top-15 hotspot)
git log --no-merges --since="1 year ago" --format='%an' -- src/ \
  | sort | uniq -c | sort -nr
git log --since="1 year ago" --no-merges --format='%an' --follow -- <file> \
  | sort | uniq -c | sort -nr   # per file

# 3. Bug hotspots
git log -i -E --grep="fix|bug|broken|regress|hotfix" --since="1 year ago" \
   --name-only --format='' --no-merges -- src/ <exclusions> \
  | grep -v '^$' | sort | uniq -c | sort -nr

# 4. Velocity (2y, monthly)
git log --since="2 years ago" --format='%ad' --date=format:'%Y-%m' --no-merges -- src/ \
  | sort | uniq -c

# 5. Firefighting
git log --oneline --since="1 year ago" --no-merges -- src/ \
  | grep -iE 'revert|hotfix|emergency|rollback'

# 6. Temporal coupling: Python script (/tmp/caacs/coupling.py) walks
#    `git log --no-merges --since="1y" --name-only --format=__COMMIT__%H -- src/`,
#    emits all unordered file-pairs per multi-file commit, counts.

# 7. Complexity (Python only)
radon cc -a -s --total-average src/specify_cli src/doctrine src/charter src/kernel
radon mi -s src/specify_cli src/doctrine src/charter src/kernel | grep -E " - [BC] "
```

### Inherited biases (per the tactic's failure_modes)

| Bias | Effect on this audit |
|------|----------------------|
| Squash-merge distortion | Repo uses both squash and non-squash merges (mixed history). Velocity counts upstream activity reasonably faithfully; PR-level metadata not consulted. |
| Weak commit messages | Conventional Commits dominate (`fix:`, `feat:`, `refactor:`, `docs:`). The fix-grep matches body too — a few false positives (e.g. spec commits that contain "fix" in prose). Spot-checked, false-positive rate is low. |
| Vanity-file dominance | Lockfiles, `__pycache__`, CHANGELOG excluded. Spot-checked top 4 hotspots for insertion/deletion ratio — all show substantive code change, not formatting noise. |
| No rename-following by default | The bulk recipes do **not** follow renames. Per-file authorship for top-15 hotspots used `--follow`. Three known renames in this window (`acceptance.py` → `acceptance/__init__.py`, `dashboard.py` → `cli/commands/dashboard.py`, `cli/commands/agent/feature.py` deleted in `7428880c4`) split history; documented in the hotspot table. |
| No complexity capture in raw git data | Mitigated via `radon` overlay (Python-only). |
| Bus factor is a question, not a verdict | This audit treats single-author concentration as an open question. |

## Top findings (executive summary)

1. **Project is very alive but contributor-monopolised.** 1001 commits to `src/` in
   the last year, accelerating in 2026 (288 commits in Feb alone). One author
   (Robert Douglass) authored **89.5%** of all `src/` commits in the window
   (896 / 1001). Of the top 15 hotspots, 14 are >90% single-author. Bus factor is
   effectively 1 across the whole codebase. This is the dominant risk surfaced by
   the audit.
2. **`src/specify_cli/cli/commands/agent/` is a refactor target.** Three files
   (`tasks.py` — 3746 SLOC; `workflow.py` — 1895 SLOC; `mission.py` — 2314 SLOC)
   together hold five of the seven worst-complexity functions in the repo
   (`finalize_tasks` CC=160, `move_task` CC=139, `status` CC=87, `review` CC=84,
   `map_requirements` CC=74). They are also the top-three temporal-coupling
   pair (45 co-changes between `tasks.py` and `workflow.py` alone) and dominate
   the bug-hotspot table. **Both unstable and known-defective** = strongest refactor
   candidate the recipes can produce.
3. **Firefighting frequency is low (~0.8% of commits).** Eight matches across a
   year (2 reverts, 1 explicit hotfix, 5 "rollback" mentions that are
   feature-implementation references rather than emergency fixes). The team
   appears to trust the pipeline — this is a **healthy** signal that contradicts
   the "monopolised" risk above. The risk lives in knowledge transfer, not in
   merge discipline.
4. **Mission-template files churn alongside the CLI commands that consume them.**
   `software-dev/command-templates/{specify,plan,tasks,implement,review,tasks-packages}.md`
   appear in the top-30 hotspots and co-change with the agent commands (e.g.
   `tasks.md` ↔ `tasks.py`: 18 co-changes, `specify.md` ↔ `agent/tasks.py`: 12).
   This is **expected coupling** by design (templates are the contract between
   runtime and mission), not a defect — but it is also evidence that the
   "template + dispatcher" boundary is the load-bearing seam in the system.
5. **Three empty top-level src/ directories are leftovers from the
   shared-package-boundary cutover** (`src/runtime/`, `src/dashboard/`,
   `src/constitution/` contain only stale `__pycache__/`). Per `CLAUDE.md` these
   were either moved into `src/specify_cli/` or extracted to PyPI dependencies.
   Recommend deletion.

## Hotspot table (top 30, vanity-filtered)

`Churn` = commits touching the file in the 1y window. `Bug commits` = subset whose
commit message matches `fix|bug|broken|regress|hotfix` (case-insensitive). `Bus
factor` is the percentage of those churn commits authored by the dominant author
(in every case below: Robert Douglass). `CC max` is the highest-rated cyclomatic
function in the file at HEAD (radon rank in parens). DDD column is researcher-
**tentative**.

| # | File | Churn | Bug commits | SLOC | CC max | Top-author share | DDD-tentative |
|---|------|------:|------------:|-----:|--------|------------------|----------------|
| 1 | `src/specify_cli/__init__.py` | 119 | 25 | 224 | A | 49% (Robert; co-owned w/ Den, honjo, Bruno) | glue (CLI bootstrap) |
| 2 | `src/specify_cli/cli/commands/agent/tasks.py` | 87 | 74 | 3746 | F (160 `finalize_tasks`) | 98% | **core** (mission orchestration) |
| 3 | `src/specify_cli/cli/commands/agent/workflow.py` | 77 | 67 | 1895 | F (84 `review`) | 96% | **core** (lane/workflow dispatch) |
| 4 | `src/specify_cli/cli/commands/implement.py` | 67 | 55 | 718 | F (44) | 97% | **core** (workspace resolution) |
| 5 | `src/specify_cli/cli/commands/merge.py` | 56 | 42 | 1599 | F (63 `_run_lane_based_merge_locked`) | 96% | **core** (merge state machine) |
| 6 | `src/specify_cli/cli/commands/agent/feature.py` | 56 | 43 | DELETED | n/a | 100% | glue (deleted in `7428880c4`, mission-id cutover) |
| 7 | `src/specify_cli/cli/commands/init.py` | 50 | 28 | 1018 | F (94 `init`) | 96% | supporting (project bootstrap) |
| 8 | `src/specify_cli/cli/commands/__init__.py` | 48 | 23 | 115 | A | 96% | glue (wiring) |
| 9 | `src/specify_cli/sync/emitter.py` | 42 | 30 | 1682 | C (avg) MI=C | 93% | supporting (SaaS sync) |
| 10 | `src/specify_cli/missions/software-dev/command-templates/specify.md` | 38 | 28 | n/a (markdown) | n/a | n/a | supporting (mission template) |
| 11 | `src/specify_cli/cli/commands/sync.py` | 36 | 23 | 1462 | MI=C | 97% | supporting (sync CLI) |
| 12 | `src/specify_cli/missions/software-dev/command-templates/tasks.md` | 33 | 27 | n/a | n/a | n/a | supporting (mission template) |
| 13 | `src/specify_cli/cli/commands/dashboard.py` | 33 | 24 | 142 (renamed from `dashboard.py`) | n/a | 100% | glue (CLI shim) |
| 14 | `src/specify_cli/glossary/middleware.py` | 36 | 19 | 689 | n/a | 100% | supporting (glossary) |
| 15 | `src/specify_cli/dashboard/static/dashboard/dashboard.js` | 29 | 21 | n/a | n/a | n/a | supporting (UI) |
| 16 | `src/specify_cli/dashboard/scanner.py` | 28 | 24 | 785 | n/a | 93% | supporting (dashboard scanner) |
| 17 | `src/specify_cli/missions/software-dev/command-templates/plan.md` | 27 | 19 | n/a | n/a | n/a | supporting |
| 18 | `src/specify_cli/missions/software-dev/command-templates/implement.md` | 27 | 21 | n/a | n/a | n/a | supporting |
| 19 | `src/specify_cli/upgrade/migrations/__init__.py` | 26 | 20 | 89 | n/a | 100% | glue (migration registry) |
| 20 | `src/specify_cli/sync/events.py` | 26 | 19 | 499 | n/a | 96% | supporting (sync envelopes) |
| 21 | `src/specify_cli/next/runtime_bridge.py` | 26 | 25 | 2552 | F (46) MI=C | 96% | **core** (mission-next runtime bridge) |
| 22 | `src/specify_cli/tasks_support.py` | 25 | 17 | 31 | A | 100% | glue (re-export shim) |
| 23 | `src/specify_cli/status/emit.py` | 25 | 22 | 656 | E (40 batch) | 100% | **core** (status state machine) |
| 24 | `src/specify_cli/core/worktree.py` | 25 | 20 | 681 | n/a | 96% | **core** (git worktree mgmt) |
| 25 | `src/specify_cli/glossary/__init__.py` | 24 | 13 | n/a | n/a | 100% | supporting (glossary entrypoint) |
| 26 | `src/specify_cli/cli/commands/charter.py` | 23 | 18 | 2934 | E (38 `interview`) MI=C | 100% | supporting (charter CLI) |
| 27 | `src/specify_cli/acceptance.py` (now `acceptance/__init__.py`) | 22 | 17 | 793 | MI=B | 100% | **core** (acceptance workflow) |
| 28 | `src/specify_cli/orchestrator_api/commands.py` | 21 | 17 | 1097 | n/a | 100% | **core** (external orchestration API) |
| 29 | `src/specify_cli/agent_utils/status.py` | 21 | 15 | 570 | F (53 `_display_status_board`) | 100% | supporting (kanban renderer) |
| 30 | `src/specify_cli/cli/commands/agent/status.py` | 20 | 14 | 886 | n/a | 100% | supporting (status CLI) |

**Cross-reference (procedure exit condition):** files appearing in both top-10
churn and top-10 bug-hotspot lists are the strongest refactor candidates per the
tactic. That set is:
`agent/tasks.py`, `agent/workflow.py`, `implement.py`, `merge.py`, `agent/feature.py`
(deleted), `init.py`, `commands/__init__.py`, `sync/emitter.py`, `cli/commands/sync.py`.

> **DDD classifications above are researcher-tentative — architect sign-off
> required before treating as authoritative.**

## Temporal coupling (top 30 pairs, both files non-vanity)

Source: 586 multi-file `src/`-only commits in the 1y window. 239,639 unique pairs
emitted (Cartesian product is large; we sliced top 30).

| # | Co-changes | File A | File B | Note |
|---|-----------:|--------|--------|------|
| 1 | 45 | `cli/commands/agent/tasks.py` | `cli/commands/agent/workflow.py` | Internal `agent/` cluster |
| 2 | 34 | `cli/commands/agent/tasks.py` | `cli/commands/implement.py` | Mission orchestration ↔ implementation dispatch |
| 3 | 29 | `cli/commands/agent/workflow.py` | `cli/commands/implement.py` | Same cluster |
| 4 | 26 | `cli/commands/implement.py` | `cli/commands/merge.py` | Workspace-lifecycle pair |
| 5 | 22 | `cli/commands/agent/tasks.py` | `cli/commands/merge.py` | Same cluster |
| 6 | 22 | `missions/software-dev/command-templates/plan.md` | `…/specify.md` | Mission templates co-evolve |
| 7 | 21 | `…/specify.md` | `…/tasks.md` | Mission templates co-evolve |
| 8 | 21 | `cli/commands/agent/feature.py` | `cli/commands/agent/tasks.py` | Pre-cutover coupling (`feature.py` deleted) |
| 9 | 20 | `sync/emitter.py` | `sync/events.py` | Sync envelope ↔ emitter (expected) |
| 10 | 19 | `cli/commands/agent/feature.py` | `cli/commands/agent/workflow.py` | Pre-cutover |
| 11 | 18 | `cli/commands/agent/tasks.py` | `missions/software-dev/command-templates/tasks.md` | **Template ↔ dispatcher seam** |
| 12 | 18 | `cli/commands/agent/feature.py` | `cli/commands/implement.py` | Pre-cutover |
| 13 | 17 | `cli/commands/agent/workflow.py` | `cli/commands/merge.py` | Same cluster |
| 14 | 17 | `cli/commands/agent/workflow.py` | `…/tasks.md` | **Template ↔ dispatcher seam** |
| 15 | 16 | `…/plan.md` | `…/tasks.md` | Mission templates co-evolve |
| 16 | 15 | `…/implement.md` | `…/review.md` | Mission templates co-evolve |
| 17 | 15 | `cli/commands/accept.py` | `cli/commands/implement.py` | Lifecycle pair |
| 18 | 15 | `cli/commands/agent/workflow.py` | `…/specify.md` | **Template ↔ dispatcher seam** |
| 19 | 15 | `cli/commands/implement.py` | `…/tasks.md` | **Template ↔ dispatcher seam** |
| 20 | 15 | `missions/software-dev/templates/task-prompt-template.md` | `templates/task-prompt-template.md` | **Duplicated template** (two locations co-edited) |
| 21 | 15 | `cli/commands/agent/feature.py` | `…/tasks.md` | Pre-cutover |
| 22 | 14 | `agent_utils/status.py` | `cli/commands/agent/tasks.py` | Status renderer ↔ status owner |
| 23 | 14 | `cli/commands/accept.py` | `cli/commands/merge.py` | Lifecycle pair |
| 24 | 14 | `cli/commands/agent/tasks.py` | `core/worktree.py` | Mission orchestration ↔ git worktree |
| 25 | 14 | `cli/commands/agent/workflow.py` | `core/worktree.py` | Same |
| 26 | 14 | `cli/commands/agent/feature.py` | `cli/commands/merge.py` | Pre-cutover |
| 27 | 13 | `dashboard/scanner.py` | `dashboard/static/dashboard/dashboard.js` | UI ↔ scanner (expected) |
| 28 | 13 | `…/tasks-packages.md` | `…/tasks.md` | Templates |
| 29 | 13 | `…/tasks-outline.md` | `…/tasks-packages.md` | Templates |
| 30 | 13 | `cli/commands/merge.py` | `core/worktree.py` | Merge ↔ worktree (expected) |

**Cluster signal:** the `agent/{tasks,workflow,feature}.py` ↔ `implement.py` ↔
`merge.py` ↔ `core/worktree.py` graph contains the densest coupling. Of the top-30
pairs, **22 involve at least one of those six files**. This is the system's
load-bearing transaction (mission state ↔ git worktree).

**Anomaly worth a question:** pair #20 — `missions/software-dev/templates/task-prompt-template.md`
co-edited 15 times with `templates/task-prompt-template.md`. **Why does the same
template exist in two locations and require synchronised edits?** This is a
candidate for connascence-of-meaning analysis (likely a stale duplicate after a
template-resolver chain change).

## Bus factor / knowledge map

**Overall (1y, src/-only commits):**

| Author | Commits | Share |
|--------|--------:|------:|
| Robert Douglass | 896 | 89.5% |
| Stijn Dejongh | 33 | 3.3% |
| Den Delimarsky 🌺 | 32 | 3.2% |
| honjo-hiroaki-gtt | 5 | 0.5% |
| den (work) | 5 | 0.5% |
| Jerome LACUBE | 3 | 0.3% |
| Jerome Lacube | 3 | 0.3% |
| Bruno Borges | 3 | 0.3% |
| Zhiqiang ZHOU | 2 | 0.2% |
| Tanner | 2 | 0.2% |
| Ram | 2 | 0.2% |
| Brian Anderson | 2 | 0.2% |
| 13 others | 1 each | <0.2% each |

**Per-hotspot single-author share** (top 15, with `--follow`):

| File | Top author share |
|------|-----------------:|
| `__init__.py` | 49% (Robert) — only file with significant co-authorship; reflects 1.x-era contributors (Den, Bruno, honjo) |
| `cli/commands/agent/tasks.py` | 97.7% (Robert; 2 commits Stijn) |
| `cli/commands/agent/workflow.py` | 96.1% (Robert; 2 Stijn, 1 Jerome) |
| `cli/commands/implement.py` | 97.0% (Robert) |
| `cli/commands/merge.py` | 96.4% (Robert) |
| `cli/commands/agent/feature.py` (deleted) | 100% (Robert) |
| `cli/commands/init.py` | 96.0% (Robert) |
| `cli/commands/__init__.py` | 95.8% (Robert) |
| `sync/emitter.py` | 92.9% (Robert; 3 Stijn) |
| `cli/commands/sync.py` | 97.2% (Robert) |
| `cli/commands/dashboard.py` (renamed) | 100% (Robert) |
| `glossary/middleware.py` | 100% (Robert) |
| `dashboard/scanner.py` | 92.9% (Robert) |
| `upgrade/migrations/__init__.py` | 100% (Robert) |
| `sync/events.py` | 96.4% (Robert) |

**Open question (per the tactic):** is this single-author concentration a
**"stable mature ownership"** signal or a **"knowledge bus factor"** signal?
The recipes cannot answer that — only conversation with the team can. But the
combination of (a) 89.5% concentration, (b) high churn (still active), and
(c) high bug-fix density on those same files leans toward bus factor over
maturity.

## Firefighting signal

8 commits in the 1y window match `revert|hotfix|emergency|rollback` (out of 1001
on `src/`, ~0.8%). Spot-read of all 8:

```
cf997620c fix(review): enforce rollback feedback capture across 2.x flows
cd128b881 Revert "fix: Restore ClarificationMiddleware (WP06) after parallel branch merge"
2e52be19b fix: backport v0.15.2 hotfix to 2.x — branch detection, subprocess encoding, hook safety
4a9509ed6 feat(WP06): define software-dev v1 mission YAML with guards and rollback
bce568943 feat(WP10): add rollback-aware merge resolution and JSONL merge
87f3efb1f feat(WP03): add deterministic reducer with rollback-aware conflict resolution
192ca305d refactor: Remove rollback-task command
d864c9829 Revert "feat(merge): run from primary repo when invoked in worktree"
```

Of these 8, only 3 are genuine emergency events:

- `cd128b881` — explicit revert of a parallel-branch-merge fix
- `d864c9829` — explicit revert of a merge-from-primary-repo feature
- `2e52be19b` — explicit hotfix backport from `v0.15.2` to `2.x`

The other 5 are features/refactors that contain rollback in their **scope**
(rollback-aware merge, rollback feedback capture, etc.), not rollback events.

**Verdict:** firefighting frequency is genuinely low (~0.3% of commits if we
strip the false positives). The team appears to trust the merge pipeline. This
is a **healthy signal** that contradicts the high single-author concentration
risk — the lone author has, so far, kept the pipeline reliable. The risk is
**bus factor**, not **pipeline trust**.

## Velocity trend (24 months, monthly commit count on src/)

```
2025-08:   2  ▏
2025-09:  54  ████▎
2025-10:  47  ███▊
2025-11:  70  █████▌
2025-12:  45  ███▌
2026-01: 185  ██████████████▌
2026-02: 288  ██████████████████████▊
2026-03:  71  █████▌
2026-04: 210  ████████████████▌
2026-05:  29  ██▎ (partial month, audit on day 8)
```

(prior 12 months in the 2y window had no commits to `src/` — repository began
significant activity in late 2025 / early 2026)

Project is **decisively alive and accelerating**: the 2026-Q1 commit count
exceeds the previous five months combined. The 2026-03 dip is plausibly the
gap between the 2.x cutover (2026-02 surge) and the post-cutover reliability
work (2026-04 surge). Last 30 days: 193 src/ commits. Last 90 days: 550.

## Triage matrix (Eisenhower, per procedure exit condition)

The procedure asks for a four-bucket assignment of audit findings.

### Important + urgent (this week)

- **Schedule a knowledge-transfer pairing on `cli/commands/agent/tasks.py` and
  `agent/workflow.py`.** These are the two highest-churn-and-bug files, both
  >96% single-author, both contain F-rated cyclomatic functions. If the lone
  author is unavailable for two weeks, work on these files stops.
- **Question the duplicated template** at
  `missions/software-dev/templates/task-prompt-template.md` vs.
  `templates/task-prompt-template.md`. 15 co-edits in 1y suggests neither has
  become canonical; one of them is dead-code-by-edit-count and the audit cannot
  tell which from history alone.

### Important + not urgent (this quarter)

- **Refactor `cli/commands/agent/tasks.py` (3746 SLOC, F-160 `finalize_tasks`,
  F-139 `move_task`).** This is the single strongest "both unstable and
  known-defective" candidate the audit produces. A connascence-of-meaning pass
  on the function boundaries is the natural follow-up.
- **Refactor `cli/commands/agent/mission.py` (2314 SLOC, F-160 `finalize_tasks`)**
  — note `finalize_tasks` is in `mission.py`, not `tasks.py` despite the name;
  this name-vs-location mismatch is itself a coupling smell.
- **Decompose `cli/commands/init.py` (F-94 `init`, 1018 SLOC).** Worst MI in
  the CLI command layer (after charter).
- **Decompose `cli/commands/charter.py` (2934 SLOC, MI=C, three E-rated
  functions).** Charter interview, generate, status, and synthesize are
  effectively four CLI verbs jammed into one file.
- **Re-examine `next/runtime_bridge.py` (2552 SLOC).** Nominally a "bridge"
  but is itself a hotspot (rank #21 by churn, rank #7 by SLOC). Bridge that
  needs 26 commits/year and contains an F-46 function isn't a bridge, it's a
  hub.

### Not important + not urgent (don't worry)

- **Firefighting frequency.** Genuinely low; do not invest in pipeline-trust
  remediation absent other signal.
- **Velocity.** Healthy and growing; no investment needed.
- **`src/kernel/` and `src/charter/`.** Small (694 + 11,384 SLOC), low churn
  (8 + 38 commits/y), no F-rated complexity outside `charter/compiler.py`
  (MI=B). Stable subsystems.
- **`__init__.py` at 119 commits.** Shape of the data: it's the package
  bootstrap and absorbs every new export. Replace question with a check: is
  it >300 SLOC of logic? (Answer: 224 SLOC — fine.)

### Parallelisable (delegate / batch)

- **Delete the three empty leftover dirs**: `src/runtime/`, `src/dashboard/`
  (top-level — note the *real* dashboard is `src/specify_cli/dashboard/`),
  `src/constitution/`. They contain only stale `__pycache__/`. Trivial, batchable.
- **Recipe-level cleanup of D-rated migrations**
  (`m_0_10_8_fix_memory_structure.py` — F-47, `m_3_1_1_charter_rename.py` — D-27,
  `m_3_2_0_codex_to_skills.py` — D-24, `m_3_2_3_unified_bundle.py` — D-22).
  Migrations are write-once-and-never-touch; refactoring them is parallelisable
  and low-risk.

## Cross-cutting observations

1. **The `agent/` directory is doing too much.** `cli/commands/agent/tasks.py`,
   `workflow.py`, `mission.py`, `status.py`, and the deleted `feature.py`
   together hold ~10,000 SLOC of CLI dispatch and contain six of the eight
   worst-complexity functions in the project. This is "everything-the-mission-
   touches-funnels-here" architecture. The CaaCS recipes cannot prescribe a
   refactor; they can only flag that the seam is overloaded.
2. **Template ↔ dispatcher coupling is a designed feature, but its volume is
   load-bearing.** Pairs #11, #14, #18, #19 in the temporal-coupling table all
   show command-template `.md` files co-changing with their CLI dispatchers
   ~12-18 times per year. The mission system's design contract (templates are
   the source-of-truth for agent prompts) is correct, but every change to a
   template requires a corresponding dispatcher change. Worth examining whether
   a template-loader abstraction could reduce that.
3. **The `sync/` package is a coherent cluster.** `emitter.py`, `events.py`,
   `background.py`, `batch.py`, `queue.py`, `client.py` all appear in the
   churn list and co-change with each other (not with the rest of the
   codebase). This is a healthy modular cluster — high internal coupling, low
   external coupling — and **does not** need a refactor; it needs a second
   maintainer.
4. **`__init__.py` co-authorship history is a leading indicator.** It is the
   only top-15 hotspot with non-trivial co-authorship (Den, Bruno, honjo all
   contributed). This reflects the 1.x-era contributor base, before the 2.x
   cutover concentrated authorship. The drop from "many contributors on
   `__init__.py`" to "one contributor on everything else" is the bus-factor
   transition the project lived through.
5. **No `tests/` were in scope.** This is a deliberate scope decision but it
   blinds the audit to the most important counterweight: test coverage on the
   F-rated functions. A file with CC=160 and a 95% test-line-coverage harness
   is a different beast than one with CC=160 and no tests. The CaaCS recipes
   cannot tell them apart.

## Limitations of this run

1. **Scope = `src/` only.** Per user instruction. This excludes
   `kitty-specs/` (the project's own dogfood missions), `tests/`,
   `architecture/`, `docs/`, and `.github/`. The biggest blind spot is
   **temporal coupling between `kitty-specs/<feature>/` and `src/`** — the
   project's design says feature plans live in `kitty-specs/` and drive `src/`
   changes, so the strongest causal coupling in the codebase is the one this
   audit cannot see.
2. **No `tests/` overlay.** As noted in cross-cutting observation #5.
3. **`cloc` not installed.** SLOC is `wc -l` (Python files only); language
   breakdown is implicit (everything in scope is Python except a few markdown
   templates and one JS dashboard file). For a pure-Python scope this is
   acceptable.
4. **Rename-following is partial.** Per-file authorship for the top-15 used
   `--follow`; the bulk recipes (churn, bug-hotspots, temporal coupling) did
   not. Three concrete renames in the window are documented inline:
   `acceptance.py` → `acceptance/__init__.py`, `dashboard.py` →
   `cli/commands/dashboard.py`, `cli/commands/agent/feature.py` deleted in
   `7428880c4`. Other renames likely exist and would push some files
   currently outside the top-30 closer to the top.
5. **Bug-grep heuristic.** `fix|bug|broken|regress|hotfix` is the recipe-
   spec'd grep. It matches commit body too, producing a low rate of
   false positives (spec/feat commits whose body mentions "fix" in prose).
   Spot-checked on 5 random matches: 4/5 are genuine fix commits, 1/5 is a
   spec commit that mentions opportunistic fixes in passing. Acceptable
   noise floor.
6. **Squash-merge mix.** History contains both squashed PRs (one commit each)
   and non-squashed PRs (multiple commits). Velocity counts are biased
   slightly downward against squashed PRs but the bias is uniform across the
   window so the **shape** of the velocity curve is reliable.
7. **The "vanity-file dominance" check is informal.** Top-4 hotspots were
   spot-checked for insertion-vs-deletion ratio (all show substantive
   churn). The full top-30 was not checked individually.
8. **DDD classifications are researcher-tentative** — architect sign-off
   required before treating any cell of the DDD column in the hotspot table
   as authoritative. The justifications are one-line and the researcher has
   no charter context to lean on.
9. **Per the tactic's own out-of-scope clause:** this audit is not a
   substitute for the brownfield-investigation skill (issues #665/#666);
   it is the evidence-gathering input to triage and connascence/premortem
   tactics, not a verdict.

## Open follow-ups for cross-check (Phase 3)

The following items should be cross-referenced against open `#822` sub-issues
by the planner:

1. Refactor `cli/commands/agent/tasks.py` (3746 SLOC, F-160 + F-139 + F-87 + F-74).
2. Refactor `cli/commands/agent/mission.py` (2314 SLOC, contains F-160
   `finalize_tasks` despite the name, suggesting a misplaced responsibility).
3. Decompose `cli/commands/charter.py` (2934 SLOC, three E-rated functions,
   MI=C).
4. Decompose `cli/commands/init.py` (F-94 `init`).
5. Examine `next/runtime_bridge.py` (2552 SLOC, F-46) — bridge or hub?
6. Resolve the duplicated `task-prompt-template.md` pair (15 co-edits/y at two
   paths).
7. Knowledge-transfer plan for `agent/`, `merge.py`, `implement.py`,
   `sync/emitter.py`, `glossary/middleware.py`, and `core/worktree.py` (all
   ≥96% single-author).
8. Delete empty leftover dirs `src/runtime/`, `src/dashboard/`,
   `src/constitution/`.
9. Re-run this audit with `tests/` in scope to overlay test coverage on the
   F-rated functions before scheduling refactors.
10. Re-run this audit with `kitty-specs/` in scope to surface
    feature-spec ↔ source-code temporal coupling, which is invisible to the
    current run.

---

*Generated 2026-05-08 by researcher subagent following the
[forensic-repository-audit](../../src/doctrine/tactics/shipped/analysis/forensic-repository-audit.tactic.yaml)
tactic and
[legacy-codebase-triage](../../src/doctrine/procedures/shipped/legacy-codebase-triage.procedure.yaml)
procedure on branch `feat/caacs-doctrine` at commit
`bc64dec6ee37dbbd6bc21a0a1aa3195f2bab1b57`. Not committed; review-only artifact.*
