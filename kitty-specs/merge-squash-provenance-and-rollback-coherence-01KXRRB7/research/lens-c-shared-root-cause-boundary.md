# Lens C — Shared Root-Cause & Scope-Boundary (architecture-scout)

Pair under review: **#2709** (squash overwrites target-newer meta.json acceptance
fields + append-only traces with older mission-branch copies) and **#2711**
(rollback + `--resume` leave committed `approved->done` events opposed to a
reverted `approved` working status; resume duplicates transitions). Both observed
in the SAME #2658 coordination merge (TF-046/049/066).

READ-ONLY investigation. No product code or tests changed.

---

## 1. Ownership map (who owns which mutation)

| Concern | Owner (module / fn) | Boundary health |
|---|---|---|
| Advance target branch (git commits) | `lanes/merge.py` (`integrate_mission_into_target`) via `merge/executor.py::_phase_mission_to_target` | OK — git is the mutator |
| Write status events (durable authority) | `status/emit.py` + `coordination/status_transition.py` (transactional emit), append-only `status.events.jsonl` | OK as an authority… |
| …BUT project status to target checkout | `merge/bookkeeping_projection.py::_project_status_bookkeeping_to_target` (executor.py:571) | **LEAK** — blind `write_bytes()` byte-copy of coord→target `status.events.jsonl` + `status.json`, bypassing the event-log authority (see §2) |
| Materialize working snapshot | `status/reducer.py::materialize` (event log → snapshot) | OK, but not consulted on merge/resume |
| Reconcile mission artifacts on merge | **NO OWNER** — meta.json rides the git squash wholesale; `merge/baseline.py` only stamps `baseline_merge_commit` (guarded `if existing: return`), never reconciles acceptance provenance | **MISSING SEAM** |
| Resume/rollback progress | `merge/state.py::MergeState.completed_wps` (second, ephemeral authority) + hand-rolled byte-snapshot rollback `_restore_final_bookkeeping_snapshots` | **LEAK** — parallel progress store; rollback restores working bytes only, not git commits or MergeState |

Top leak: the merge core mutates three stores (git commits, the append-only event
log, and `MergeState`/`meta.json` blobs) **non-transactionally and
non-reconcilingly**, reaching directly into artifact blobs with byte copies.

## 2. Shared-root verdict: ONE root cause, TWO fix surfaces — STRONG

The canonical event-log reconciler ALREADY EXISTS and is the single authority:
`status/event_log_merge.py::merge_event_payloads` (union → dedupe-by-`event_id` →
sort-by-`at`). It is wired as the git merge driver `merge=spec-kitty-event-log`
(`.gitattributes`, migration `m_3_1_1_event_log_merge_driver.py`) and is used at
the lane→coord hop (`lanes/auto_rebase.py::merge_event_log_texts`).

The **coord→target projection bypasses it**: `_project_status_bookkeeping_to_target`
does `trusted_target_events_path.write_bytes(source_events_bytes)` — a blind
overwrite that clobbers any target-newer events → **#2709**. The very same absent
invariant ("durable event log is the single authority; never shadow or clobber
it") is what breaks **#2711**: `MergeState.completed_wps` is a *second* progress
authority, and rollback restores working-tree bytes without unwinding the
already-committed `done` events, so resume re-derives from the shadow store and
re-emits transitions instead of reducing the durable log.

Evidence it is ONE root, not two coincidences: the reconciler exists but the last
merge hop refuses to use it (blind copy) AND resume refuses to derive from it
(reads `completed_wps` + working-tree bytes). Both are the missing rule *"all
merge reads/writes of canonical status route through the event-log authority."*
Honest nuance: meta.json acceptance provenance has **no** reconciler at all (no
merge driver, no field-union) — so #2709 has a second sub-surface that the status
authority does not yet cover.

## 3. Scope boundary (in / out)

IN: (a) route `_project_status_bookkeeping_to_target` through
`merge_event_payloads` (union vs target-committed, not overwrite); (b) extend the
same union/field-reconcile to `meta.json` acceptance provenance
(accepted/reviewed fields) — a driver or explicit field-merge, since the event-log
driver does not cover meta.json; (c) make `--resume` derive progress from the
reduced durable event log, retiring `completed_wps` to a cache/hint; (d) make
rollback coherent — either unwind committed events or forbid the reverted-working
vs committed-done split; (e) one class-closing regression gate.

OUT (tracked follow-up): the god-module decomposition is done (#2057) — do not
re-refactor executor phases; broad status-model changes; SaaS/dossier sync;
push/preflight remote-state work (017/018/049 own it).

## 4. Recurrence signature — this class has regressed repeatedly

`merge/` is a heavily re-patched "merge loses/overwrites canonical status" surface:
`a5f30616e` merge-done-surface-resolver (#1732 coord write/read divergence),
`#1772` FR-037/FR-038 (zero-diff squash / target-history validation), `#1827`
baseline ordering, `c16291214` MergeState canonical keying (#601), `dadb71148`
resume capability, plus `merge-review-status-hardening`,
`mission-coordination-branch-atomic-event-log-01KSPTVW`, `merge-base-diff-ssot-01KX44SD`.
Each patched one field/one hop; none installed the invariant. Class-closer:
a single **"canonical status authority"** seam every merge write funnels through
(union-merge, never byte-copy) + a resume that reduces the durable log, guarded by
a regression test that fails if any merge write to `status.events.jsonl` /
`meta.json` overwrites target-newer content or if resume re-emits an existing
transition.

## 5. WP slicing hint (minimal)

- **WP01 — red-first repros:** two failing tests — (a) merge with target-newer
  `status.events.jsonl`+`meta.json` acceptance fields, assert no data loss; (b)
  rollback→`--resume` after committed `done`, assert no duplicate transitions.
- **WP02 — #2709 reconciliation seam:** route projection through
  `merge_event_payloads`; add meta.json acceptance-field reconcile (driver or
  field-union). Depends on WP01.
- **WP03 — #2711 durable-resume + coherent rollback:** derive resume progress from
  reduced event log; demote `completed_wps` to hint; make rollback unwind or
  forbid committed-vs-working divergence. Depends on WP01.
- **WP04 — class-closing gate:** invariant test forbidding byte-overwrite of
  target-newer canonical status/meta and forbidding resume re-emission.

## Overlap risk (confirm before implementation)

TOP RISK: sibling P0 **#2770** was owned in a separate session and its git-history
touches the SAME `merge/state.py` + `merge/done_bookkeeping.py` rollback/resume
lines this mission must change — a lane-collision hazard. Confirm #2770's landed
diff and rebase onto it before WP03. Secondary: `049-fix-merge-target-resolution`
and `017/018` merge-preflight own push/remote-state — keep this mission off the
preflight surface. `#2057` god-module decompose relocated these helpers
byte-for-byte and does NOT own the reconcile logic, so no semantic conflict there.
