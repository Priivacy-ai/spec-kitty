# Closeout Deep-Dive — Consolidation / Dead-Code / Duplication / Export Hygiene (reducer-randy)

**Mission:** execution-context-unification-01KTPKST
**Reviewer:** reducer-randy (ad-hoc profile)
**Branch reviewed:** `fixups/code-engine-stabilization` (12 WPs squash-merged `6065d1368` + rebased onto upstream/main)
**Date:** 2026-06-10
**Scope:** Did the merged result deliver the net-subtraction + no-duplication it promised (NFR-005, FR-013/FR-015, SC-7)? Adjudicate F-009 dead-code per symbol; confirm duplicate-mechanism collapse survived the merge; audit export/`__all__` hygiene.

---

## VERDICT: PASS on de-duplication / export hygiene — **FAIL (overstated) on the literal NFR-005 "net subtraction" claim**

The **anti-duplication thesis is fully delivered**: every duplicate mechanism the mission targeted collapsed to one, and I found **no surviving parallel resolver, second status-write surface, duplicate worktree parser, or parallel daemon kill/reaper** (C-005 holds — concurs with alphonso + renata). Export hygiene is sound bar **one** real privatization (`legacy_record_path`).

**But the NFR-005 LOC claim is empirically false as written.** The mission's production diff is **net +1609 LOC** (`src/***.py`: +2151 / −542), not "trending down." The collapses landed (parser −120, status_service −23, orphan_sweep −16, dashboard/lifecycle −12, feature_dir_resolver −10 ≈ **−180**) but were dwarfed by the *new* doc-09 fragment infrastructure (context.py +200, resolution.py +293, _read_path_resolver.py +159 ≈ **+650** in three files). This is **not duplication that survived** — it is genuine new value-object machinery (6 fragments + CommitTarget + builder + canonicalizing resolver). The reduction is real but local; the unification is additive overall. NFR-005's framing ("collapses ~500–650 LOC; changed-path LOC trends down") was a mis-estimate that the executed mission did not — and arguably could not — honour while *also* building the fragment model. **Re-classify NFR-005 as "targeted duplication removed; net LOC up due to new fragment VOs," not "net subtraction achieved."**

---

## F-009 per-symbol disposition (definitive)

| Symbol | File:line | Callers (verified) | In `__all__`? | Disposition |
|--------|-----------|--------------------|---------------|-------------|
| `legacy_record_path` | `retrospective/writer.py:52` | intra-module only: `writer.py:80` (`resolve_existing_record_path`), `writer.py:530` (`write_gen_record`) + **one control test** (`tests/retrospective/test_record_committable_1771.py:71`, `test_legacy_path_was_gitignored_control`) | **No `__all__` in writer.py** | **PRIVATIZE → `_legacy_record_path`.** Real (minor) finding. No external/`__all__` caller; the sole test is a deliberate back-compat *characterization* control (proves the legacy path is gitignored), so it is legitimate to keep — just update its import to the renamed symbol. **Concur with renata Finding 1 + alphonso.** |
| `ReapResult` | `sync/owner.py:497` | **LIVE**: return type of `reap_orphan_daemons` (`owner.py:610`, `:630`); the single canonical reaper wired to the spawn path. In `__all__` (`:707`). Consumed by `tests/sync/test_daemon_singleton_reaper_consolidation.py`. | **Yes (`:707`)** | **KEEP PUBLIC (false-positive — REFUTE the scan).** Live structural return type of the public reaper. The dead-code scanner's documented "public-API-consumed-structurally-only" class. No action. |
| `canonical_executable_scope` | `sync/owner.py:512` | **LIVE**: called internally `owner.py:629` (`scope = executable_scope or canonical_executable_scope()` inside `reap_orphan_daemons`). In `__all__` (`:709`). | **Yes (`:709`)** | **KEEP (false-positive — REFUTE).** Genuinely live identity-scoping helper for the reaper. If the operator wants tighter hygiene, it *could* be de-exported from `__all__` (no external caller found), but it is not dead. **De-export is optional, not required.** |
| `_auth_doctor.py:236` BLE001 | `cli/commands/_auth_doctor.py:236` | n/a | n/a | **OUT OF SCOPE.** Pre-existing (`38abeebf`, #1297); not a mission-touched file; whole-repo lint scan artifact. **Confirm: not this mission's debt.** |

**Net F-009 adjudication: 1 real privatization (`legacy_record_path`), 2 confirmed false-positives (KEEP), 1 out-of-scope pre-existing.** This matches both prior closeout reviews — no disagreement.

### Recommended fix (the only required one)
In `src/specify_cli/retrospective/writer.py`: rename `legacy_record_path` → `_legacy_record_path` (def + the two intra-module call sites `:80`, `:530`). Update the single test import in `tests/retrospective/test_record_committable_1771.py:22,71`. ~5 edits, behavior-preserving, no `__all__` to touch.

---

## Duplicate-mechanism survivors — NONE (all collapses verified in merged tree)

| Mechanism | Promised collapse | Merged-tree verification |
|-----------|-------------------|--------------------------|
| Read-path resolver | `candidate_feature_dir_for_mission` → `_read_path_resolver` | **ONE.** `def resolve_mission_read_path` + `def candidate_feature_dir_for_mission` defined once (`missions/_read_path_resolver.py:214,339`); `missions/feature_dir_resolver.py` is a 67-LOC re-export shim. |
| Worktree-pointer parser | delete `workspace/root_resolver` parser, keep `core/paths` | **ONE.** Parser gone from `root_resolver.py` (now 85-LOC re-export shim of `resolve_canonical_root` from `core/paths`); single parser in `core/paths.py`. The `−120` LOC delta on `root_resolver.py` is the largest single deletion in the merge. |
| Action-context resolver | one assembler | **ONE.** `def resolve_action_context` exactly once (`mission_runtime/resolution.py:494`). |
| `target_branch` derivation | single source | **ONE.** `def get_feature_target_branch` once (`core/paths.py:441`); resolved once in the builder. |
| `mid8` derivation (C-CTX-3) | single call site | **ONE.** `IdentityFragment.derive(...)` invoked at exactly one site (`resolution.py:414`). |
| Writing `materialize()` | dashboard stops clobbering tracked status | **ONE write path.** `def materialize` once (`status/reducer.py:318`). `dashboard/scanner.py:579` now uses read-only `materialize_snapshot`; `dashboard/handlers/features.py` has **no** `materialize` call at all. wp11's two flagged clobber sites are both clean. |
| Daemon kill path (3→1) | one reaper keyed on `DaemonOwnerRecord` | **ONE kill path.** `owner._sweep_daemon_process` (psutil terminate→kill escalation, `owner.py:543`) is the sole killer; `orphan_sweep._sweep_one` (`:331`) and `daemon.cleanup_orphan_sync_daemons` (`:1238`) both delegate to it. `reap_orphan_daemons` is the single spawn-wired reaper. The `daemon.py:657` SIGTERM/SIGINT is the daemon's **own self-shutdown handler**, NOT an orphan-reaper — no parallel kill mechanism. |
| Liveness probe | defined once across `sync/` + `dashboard/` | **ONE.** `sync/daemon.py:218` is canonical; `dashboard/lifecycle.py:125` is a 3-line delegate to `_canonical_is_process_alive`. |

**SC-7 nuance (concur with alphonso F2):** discovery/diagnostic wrappers (`scan_sync_daemons`, `enumerate_orphans`, `sweep_orphans`, `cleanup_orphan_sync_daemons`) still exist by name, so a literal name-count `rg` finds >1 "reaper-shaped" function. But none carry independent kill logic — they are thin port-scan/cmdline-scan/record-based *discovery* shims feeding the one kill path. The load-bearing invariant (one kill path, one spawn-reaper, one liveness probe) holds. SC-7's *wording* ("exactly one reaper") is not satisfiable by name-count; its *intent* (no parallel mechanism) is met.

---

## FR-013 reality (concur with alphonso F1 / renata FR-013)

**2 of 5 "dead" symbols deleted**, not 5. Verified in `coordination/status_service.py`:
- **DELETED:** `append_event_log_batch`, `read_wp_lane_actor` (grep: zero hits). ✓
- **RETAINED-BECAUSE-LIVE:** `EventLogWriteTarget` (`:42`), `StatusContractError` (`:50`), `StatusReadSource` (`:34`) — heavily live internals driving `EventLogReadContract`/`EventLogWriteContract`/`read_event_log`/`append_event_log` (8+ intra-module references each). The IC-01 facade-adoption work made the contract layer the *live* path; deleting these would break the build. **Correctly NOT deleted.**
- **Export hygiene check:** the 3 retained symbols were **de-exported from `__all__`** (status_service `__all__` `:277` lists only `EventLogReadContract`, `EventLogWriteContract`, `append_event_log`, `merge_append_preserving_coordination_event_log_bytes`, `read_event_log`, `wp_lane_actor_from_events` — the 3 retained internals are absent). **Good hygiene — they are live internals, not public API.** No `__all__` drift.

The "5 dead symbols" was a **stale research premise** (mine, in wp11/research — refuted post-#1614 rebase). FR-013/NFR-005's LOC-subtraction claim is overstated by 3 symbols. Re-classify; no code change.

---

## Export / `__all__` hygiene — clean bar one

- `status_service.__all__` — tight, 3 live internals correctly excluded. ✓
- `owner.__all__` — `ReapResult`/`canonical_executable_scope` legitimately exported (live public reaper API). `canonical_executable_scope` *could* be de-exported (optional). ✓
- `root_resolver.__all__` / `feature_dir_resolver` shims — re-export only the canonical symbols; no widening. ✓
- `retrospective/writer.py` — **no `__all__`**, so `legacy_record_path` leaks as importable public surface by default. The privatization (`_` prefix) is the fix; adding an `__all__` would be an alternative but the rename is the minimal behavior-preserving move.

No new public symbols from the merge that should be private, other than `legacy_record_path`.

---

## Net assessment

De-duplication and consolidation: **delivered and verified — every targeted duplicate mechanism collapsed to one, no parallel mechanism survived the merge.** Export hygiene: **clean except one privatization.** F-009: **1 real (privatize `legacy_record_path`), 2 false-positives (keep), 1 out-of-scope.**

The single material correction is to the **NFR-005 narrative**: the mission did *not* achieve net LOC subtraction (production diff +1609). It removed ~180 LOC of genuine duplication and added ~650+ LOC of new doc-09 fragment value objects + builder. That is a sound, behavior-preserving *structural* trade (duplication → one model), but it is **additive, not subtractive**. The closeout/retro should record NFR-005 as "targeted duplication removed; overall LOC up due to the new fragment model" rather than letting the "net subtraction" claim stand as met.

### Recommended actions (priority order)
1. **DO:** privatize `legacy_record_path` → `_legacy_record_path` (writer.py + 1 test import). Only required code change.
2. **DO:** correct NFR-005 status in retro/issue-matrix — "duplication collapsed; net LOC +1609 (new fragment VOs), not net subtraction." Don't leave the subtraction claim as satisfied.
3. **DO:** correct FR-013 status to "2/5 deleted; 3 retained-because-live + de-exported" (already noted by alphonso/renata — ensure it lands in the retro, not just review docs).
4. **OPTIONAL:** de-export `canonical_executable_scope` from `owner.__all__` (no external caller). Low value.
5. **NO ACTION:** `ReapResult` (keep), `_auth_doctor.py` BLE001 (pre-existing/out-of-scope).
