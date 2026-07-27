# Closeout Scout — Paula Patterns: "Fixed N of M?" duplication-survival lens

**Mission:** gate-read-surface-completion-01KVW9B0 (draft PR #2113)
**Branch:** feat/gate-read-surface-completion @ HEAD (7271cd65c impl + 8cf711428 docs)
**Profile applied:** paula-patterns (architecture-scout / whack-a-field-recurrence lens).
Fallback alphonso not needed — recurrence + "did the consolidation eliminate the
duplication or do parallel resolutions survive?" is paula's exact remit.
**Mode:** read-only review. No files mutated except this report.

---

## VERDICT: N+1 SITE FOUND — consolidation is NOT complete; ratchet has a blind spot

The mission retired the bespoke planning-surface resolutions for the **enumerated**
gate commands (`setup_plan`, `record_analysis`, `map_requirements`, the accept
cluster, plus the 2 write-branch resolvers + `finalize_tasks` commit). Those are
genuinely folded onto the kind-aware seam and the FR-010 ratchet pins them well.

**But the pre-plan squad (map-requirements) and post-tasks squad (finalize-tasks)
each found one more site than the spec enumerated — and this closeout finds the
N+2: the `research` (Phase 0) command.** It is a planning-lifecycle command that
reads AND writes planning artifacts through a **topology-routed** dir, bypasses the
seam entirely, and is **NOT** in the ratchet's pinned surface set. Same defect
class as the #2107 driver bug.

---

## Surviving-duplication inventory

| # | Site (file:line) | Resolver binding | Reads/writes which planning artifact | In ratchet set? | Severity |
|---|---|---|---|---|---|
| **1** | `src/specify_cli/cli/commands/research.py:77` → `:94` | `resolve_feature_dir_for_slug` (topology-routed; delegates to `_resolve_mission_read_path`, honours coord topology — `_read_path_resolver.py:1359-1390`) | **READS** `feature_dir / "plan.md"` and gates progression via `validate_plan_filled(..., strict=True)` | **NO** | **HIGH — true N+1** |
| **1b** | `src/specify_cli/cli/commands/research.py:77` → `:134-135` | same topology-routed `feature_dir` | **WRITES** `research.md` + `data-model.md` (`_copy_asset`) and `feature_dir.mkdir` onto the coord surface | **NO** | **HIGH (write twin of 1)** |
| 2 | `src/specify_cli/cli/commands/agent/tasks.py:3249` (`list_tasks`) | `resolve_feature_dir_for_mission(...) / "tasks"` (topology-routed) | reads the WP `tasks/` dir (WORK_PACKAGE_TASK kind = primary) for listing | NO (bare `tasks/` dir, not a pinned `.md` literal) | LOW — read-only kanban listing, non-gating |

Sites checked and **cleared** (correctly on the seam / out of scope):
`setup_plan`, `record_analysis`, `map_requirements` (read 3787 + commit), the
accept cluster (`collect_feature_summary` / `acceptance/__init__.py:1246-1251`
via `planning_read_dir`), `finalize_tasks` (`planning_dir = primary` @ 3116),
`check_prerequisites` (primary-anchored first, coord fallback only for coord-only
legacy — spec-sanctioned), `_resolve_mission_dir_name_primary_anchored` /
`_primary_anchored_feature_dir` (now route through `_planning_read_dir`),
`get_feature_target_branch` / `resolve_target_branch` (primary anchor).
Pure status/display reads (`dashboard/scanner.py`, `retrospective/generator.py`,
`release/changelog.py`, `status/doctor.py`) are status-surface, out of mission scope.

---

## Why site 1 is a real defect, not a false positive

* `research` is a registered top-level planning-lifecycle CLI command
  (`__init__.py:225`, `/spec-kitty.research`), Phase 0 — runs **after** plan,
  **before** tasks. It is squarely inside the planning lifecycle the mission's
  FR-004 says "ALL planning-lifecycle GATE/verify commands ... MUST consult the
  single kind-aware surface seam — no command may reconstruct a planning path via
  topology routing."
* `resolve_feature_dir_for_slug` is **coord-aware** (confirmed at
  `_read_path_resolver.py:1384` — `_resolve_mission_read_path` with stored
  topology). Under coordination topology it returns the coord worktree dir.
* `plan.md` is a PRIMARY-partition kind since #2106 — it lives on primary, not
  coord. So on a coord-topology mission, `research` validates `coord/plan.md`
  (absent) and raises `PlanValidationError` / blocks. **This is byte-for-byte the
  #2107 driver shape** (`setup_plan` reading `coord/spec.md`).
* The write twin (1b) is arguably worse: research scaffolds `research.md` +
  `data-model.md` onto the coord surface, re-introducing the split the write-side
  mission #2106 just eliminated.

---

## Is the ratchet's pinned set COMPLETE? — NO

`_READ_ARM_SURFACES` pins exactly 4 functions: `setup_plan`, `record_analysis`,
`map_requirements`, `collect_feature_summary`
(`test_gate_read_literal_ban.py:126-150`). `research` is absent. The ratchet's
own docstring admits it does **not** auto-derive the scan set from
`@app.command` — so a planning-lifecycle command that reads a planning artifact
but is not hand-listed is silently un-scanned. That is precisely the vacuity the
pin test was meant to prevent, and `research` slipped through it. The ratchet is
**non-vacuous for what it scans but its scan set is incomplete** — the exact
"fixed N of M" pattern paula exists to catch.

The recurrence signature is unmistakable: pre-plan squad found map-requirements
(N+1), post-tasks squad found finalize-tasks-commit (N+1 again), closeout finds
research (N+1 a third time). Each enumeration undersized by one. This is a
whack-a-field boundary leak: the missing boundary is "every coord-aware
`feature_dir` binding followed by a planning-kind read/write," and the team keeps
patching named instances instead of fencing the shape at the resolver boundary.

---

## Recommendation (release-fix vs. long-term, paula synthesis)

**Smallest safe release fix (this mission, before merge):**
1. Re-point `research.py:77` (and the validate at :94) to the kind-aware seam:
   read `plan.md` via `resolve_planning_read_dir(..., kind=PLAN)`; scaffold
   `research.md`/`data-model.md` via the kind-aware write/placement seam
   (research/data-model are planning kinds → primary).
2. **Add `research` to `_READ_ARM_SURFACES`** (and its writes to the write-arm if
   applicable) so the ratchet actually fences it. Without this the ratchet's
   pinned set is the documented blind spot.
3. Red-first guard: a coord-topology mission with `plan.md` on primary → `research`
   must read/scaffold PRIMARY, not block on `coord/plan.md` (mirror the existing
   `test_setup_plan_read_surface.py` pattern; RED on current code).

**Long-term architecture issue (follow-up, do not expand this mission):** the pin
test should *enforce coverage*, not just *existence* — derive the candidate set
from the planning-lifecycle `@app.command` entry functions and FAIL if any of them
contains a topology-routed planning-kind join not on the allowlist. That converts
the recurring N+1 from a manual-enumeration gamble into a closed gate.
