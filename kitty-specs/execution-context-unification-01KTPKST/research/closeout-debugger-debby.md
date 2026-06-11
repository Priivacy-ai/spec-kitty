# Closeout deep-dive — debugger-debbie (RUNTIME & BEHAVIORAL RISK lens)

**Mission:** execution-context-unification-01KTPKST
**Branch:** fixups/code-engine-stabilization (12 WPs merged + rebased onto upstream/main)
**Lens:** residual "will it actually break at runtime?" — not the structural correctness the other reviews already covered.
**Date:** 2026-06-10

---

## VERDICT: SHIP-WITH-FOLLOWUPS

The structural split-brain fix is **runtime-sound for BOTH topologies**, not flattened-only.
The coordination path is genuinely exercised (not mocked away), the git-op guard is correctly
conservative, and the daemon reaper's blast-radius guard holds. One real (already-known) tooling
follow-up (F-006) and two low-severity hardening notes remain. Nothing here blocks the release;
all items are follow-up tickets.

---

## Highest-value risk — COORD-TOPOLOGY COVERAGE (was the fix flattened-only?)

**Risk falsified. Confidence: HIGH.**

The mission was dogfooded on a flattened topology, but the coordination path is **not** untested:

- `tests/specify_cli/coordination/test_surface_resolver.py::test_materialized_coord_worktree_resolves_exactly_once`
  **materializes a real coord worktree on disk** (`.worktrees/<slug>-coord/kitty-specs/...`), plants the
  #1772 nested-`.worktrees` double-resolution trap, and asserts the resolver lands on the coord feature
  dir with `.worktrees` appearing exactly once. This is the coordination read path, exercised end-to-end.
  (Ran: 12 passed across the two coord facade/resolver suites.)
- The meta key is **consistently `coordination_branch`** across every resolver
  (`status/aggregate.py:341`, `coordination/surface_resolver.py:77`, `mission_runtime/resolution.py:280`,
  written at `core/mission_creation.py:402`). I specifically chased a suspected `coordination_branch`-vs-`n`
  key divergence — it does **not** exist (an `rg` highlight artifact). No silent topology mismatch.
- Single-resolution discipline (SC-4) holds at the write seam: `coordination/status_transition.py`
  (`_canonical_primary_feature_dir`, `_identity_for_request`) anchors the transaction identity on the
  canonical primary dir via `candidate_feature_dir_for_mission` — the single coord-aware primitive that
  `resolve_status_surface` and `MissionStatus` both build on. This is the F-007 root fix (lane-worktree
  `genesis` misread).

**Residual note (LOW severity, MEDIUM confidence):** `status/aggregate.py::MissionStatus.load`
composes the coord candidate path **itself** (`CoordinationWorkspace.worktree_path` + `_compose_mission_dir`)
rather than delegating to `candidate_feature_dir_for_mission` like the other two surfaces. The composition is
equivalent today, so they agree — but it is a *second hand-rolled composition* of the same path, i.e. a
latent SC-4 drift seam: if the worktree-naming convention ever changes, `aggregate.py` must be updated in
lockstep or it silently diverges from the canonical primitive. **Action:** follow-up ticket to have
`MissionStatus.load` consume `candidate_feature_dir_for_mission` (or a shared compose helper) so there is
truly one composition site.

---

## git-op guard (WP07) edge cases — `git_operation_in_progress`

**Sound. Confidence: HIGH.**

`status/views.py::git_operation_in_progress` is filesystem-only (no subprocess), probes
`{rebase-merge, rebase-apply, MERGE_HEAD, CHERRY_PICK_HEAD, REVERT_HEAD, index.lock}` against both the
per-worktree gitdir and the shared common gitdir (`_resolve_git_dirs` handles primary checkout, linked
worktree via the `gitdir:` pointer file, and missing/non-repo → empty tuple → returns False).

Edge cases checked:
- **Bare repo / detached gitdir / non-repo path** → `_resolve_git_dirs` returns `()` → guard returns
  `False` (conservative "no op detected"). This is the *safe* direction here because the consumers
  (`materialize_if_stale`, the dashboard read) are **already write-free** via `materialize_snapshot`; the
  guard is belt-and-suspenders + observability, not the sole write-prevention. Confirmed at
  `dashboard/scanner.py:579` — the read is `materialize_snapshot` regardless of the guard outcome.
- **Undetected git ops:** `git stash` (uses index.lock briefly), `git bisect`, `git filage`/`gc`
  packing are not in the marker set. For a *long* operation that clobbers tracked status the relevant
  hazards (rebase/merge/cherry-pick/revert/index.lock) are all covered (SC-5). A bisect or gc does not
  rewrite `kitty-specs/` tracked status the way a rebase replaying mission commits does, so the omission
  is immaterial to the #1789 hazard. **No action.**

**Minor note (INFO):** because the dashboard read is unconditionally write-free, the git-op guard in
`read_only_weighted_percentage` is currently *observational only* (it logs, then reads the same way).
That's fine, but means the guard's real load-bearing consumer is the runtime writer
(`materialize_if_stale`), not the dashboard. Worth knowing for anyone who later "optimizes" the dashboard
to write again — they'd lose the only enforced protection.

---

## Daemon reaper blast radius (WP12 / SC-6b / SC-7) — `reap_orphan_daemons`

**Sound. Confidence: HIGH on over-reap, MEDIUM on under-reap.**

The executable-scope guard (`sync/owner.py:606-657`) is correctly conservative against the #1071
reaper-over-kill risk:

- **Over-reap (killing a legitimately-separate daemon):** prevented. `_process_executable_scope` returns
  `None` when neither `proc.exe()` nor `cmdline[0]` is resolvable, and the reaper treats `None` *or* any
  scope mismatch as out-of-scope → **skip, never kill** ("treat as out-of-scope rather than risk killing a
  stranger"). A daemon from a different `$HOME`/venv/container resolves to a different canonical interpreter
  → skipped. The recorded singleton PID is already excluded upstream by `scan_sync_daemons` (state-file PID
  filtered at `daemon.py:1187`). Kill escalation (`_sweep_daemon_process`) handles NoSuchProcess/AccessDenied/
  vanish-race cleanly.
- **Under-reap (failing to reap a genuine stale orphan):** the documented leak case — two interpreters
  (editable vs pipx) on the *same* host. Each interpreter's spawn reaps orphans whose `cmdline[0]` resolves
  to its *own* canonical interpreter, so each cleans up its own same-exe leak. This matches the validation
  doc's root-cause (wp11-daemon-validation.md). **Edge gap (LOW severity):** a stale orphan whose venv was
  *deleted* — `proc.exe()` raises, and `cmdline[0]` points at a now-missing path; `_canonical_executable_path`
  falls back to the raw string on resolve failure, so the comparison still works only if the foreground's
  interpreter string matches that same dead path (it won't, if the foreground is a *different* live
  interpreter). Such an orphan would be skipped as out-of-scope and **leak until the OS reaps it**. This is
  a deliberate trade (never kill a stranger > always reap), and `is_orphan` (the record predicate) still
  flags it for the reconciliation path — but the *process* survives. **Action:** acceptable as-is; note in a
  follow-up that deleted-venv orphans rely on PID death, not scope-reaping.

---

## F-006 — record-analysis verdict substring-counting

**STILL LIVE. Confidence: HIGH. Severity: MEDIUM (operator-facing false-blocked).**

Per `findings.md`, F-006 was worked around (author prose to dodge keyword counts), **not fixed** — it is
explicitly a non-mission-FR upstream tooling gap. `record-analysis` derives `verdict`/`issue_counts` by
counting `CRITICAL`/`HIGH`/`MEDIUM`/`LOW` *substrings* in the report body, so a report stating "no CRITICAL,
no HIGH" scores as having critical/high issues → spurious `blocked` → spurious implement-gating. This is a
real, recurring foot-gun for every future mission's analyze step. **Action: file the upstream follow-up
ticket** (record-analysis should parse the structured findings-table severity column, or accept a structured
`--findings` input). Worth doing — it silently mis-gates missions.

---

## Integration / rebase regression scan

**No regression found. Confidence: MEDIUM-HIGH (targeted, not exhaustive — per pragmatism mandate).**

- Coord facade + surface-resolver suites: 12 passed.
- The post-merge `spec-kitty review` "fail (4 findings)" (mission-review-report.md / F-009) is **dead-code/
  BLE001 hygiene, not a runtime regression**: `retrospective/writer.py:legacy_record_path` (real: should be
  privatized), `sync/owner.py:ReapResult`+`canonical_executable_scope` (public API consumed by tests —
  classic dead-code-scan false positive; both are live, exported in `__all__`, and consumed by the reaper),
  and a pre-existing BLE001 in `_auth_doctor.py:236` (not mission-touched). None affect runtime behavior.

---

## Prioritized actions

| # | Action | Severity | Confidence |
|---|--------|----------|------------|
| 1 | File upstream follow-up: `record-analysis` must parse structured findings (F-006) — recurring false-`blocked` gate | MEDIUM | HIGH |
| 2 | Follow-up: make `MissionStatus.load` consume `candidate_feature_dir_for_mission` (kill the second hand-rolled coord-path composition; close the SC-4 drift seam) | LOW | MEDIUM |
| 3 | Privatize `retrospective/writer.py:legacy_record_path` → `_legacy_record_path` (real dead-export finding) | LOW | HIGH |
| 4 | Note (no code change): deleted-venv daemon orphans rely on PID-death, not scope-reaping — acceptable trade, document it | LOW | MEDIUM |
| 5 | De-export or annotate `ReapResult`/`canonical_executable_scope` to silence the dead-code-scan false positive (reducer-randy's call) | INFO | HIGH |

**Net:** the structural fix holds at runtime for coordination AND flattened topologies. No release blocker.
The one item with real operator impact is F-006 (false-blocked analyze gate) — file it. Everything else is
low-severity hardening / hygiene.
