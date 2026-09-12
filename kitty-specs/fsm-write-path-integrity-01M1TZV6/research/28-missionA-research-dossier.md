<!-- Provenance: copied from work/post-convergence/28-missionA-research-dossier.md (spec-kitty repo) -->
<!-- Copied: 2026-09-06 for proto-mission fsm-write-path-integrity-01M1TZV6 (spec ground truth) -->
<!-- Verified against tree at commit e721763759 (HEAD, 2026-09-06); do not re-derive or contradict -->
# Mission A Research Dossier — `fsm-write-path-integrity` (2026-09-06)

**Repo:** `spec-kitty` · tree `3.2.7rc1` (HEAD `e721763759`) · **Consumer:** the spec author running
`/spec-kitty.specify` for Mission A (P0, parent epic #3893, milestone 3.2.7), then the post-spec
squads. **Provenance:** consolidation of reports 21 (Paula), 22 (Priti), 23 (Renata fact-check),
24 (Alphonso red-team — **binding on mechanisms where reports disagree**), and 27 §2/§4
(after-action register + the seven binding amendments). Every file:line below was re-verified
against the tree on 2026-09-06; two precision corrections vs the reports are noted inline.

**Mission in one sentence:** one locked, validated write door for `status.events.jsonl` (the FSM's
sole authority), with dependency gating inside it, raw appends gated, and a crash-safe,
identity-correct run-state store — hardening + deletion, **no redesign**.

---

## 0. Binding constraints (invariants the spec must not trade away)

| # | Constraint | Anchor |
|---|---|---|
| C1 | **Coord/primary partition (FR-004 rows 7/8).** Stored `COORD`/`LANES_WITH_COORD` topology ⇒ status writes land on the coord worktree + `safe_commit`, with truncate-rollback symmetry on commit failure, fail-loud via `FallbackCoordWorktreeUnresolved`; `SINGLE_BRANCH`/`LANES`/flat ⇒ the legitimate primary-uncommitted write. The transactional door and its fallback ENCODE this contract — a collapse must preserve it, not flatten it. | `coordination/status_transition.py:176` (error class), `:259` (`_emit_via_non_transactional_fallback`), `:382-435` (fallback arms) |
| C2 | **NFR-006: no inter-process lock held across a git subprocess.** Stated verbatim at `review/cycle.py:845-851`. Known standing violation: `BookkeepingTransaction` holds L1 across `git worktree add`/`safe_commit` (`transaction.py:290` acquire, released post-commit). NOT Mission A's to fix — but it goes on the risk register (R9 below) because WP01 grows the victim population of a hung-git-under-L1 stall. | `review/cycle.py:845-851`; `coordination/transaction.py:290` |
| C3 | **083 identity model: `mission_id` is the only runtime identity** — never slug for lookup, locking, or routing. Two live violations Mission A closes: `feature-runs.json` keyed by slug (`runtime_bridge_io.py:618`) and the status lock file keyed by slug (`locking.py:57-60`). | CLAUDE.md §Mission Identity Model |
| C4 | **Dependency guard is tri-state, fail-OPEN on `None`.** The guard fires only when the orchestrator supplies a readiness verdict. Rationale: two live probe sites call `validate_transition` with self-built contexts on exactly the guarded edges — `lanes/recovery.py:78` (crash-recovery progression probe) and `agent/tasks_transition_core.py:337` (FR-015 force-free backward-edge probe) — and fail-closed-on-`None` silently kills both. Sound because after WP03 no durable write bypasses the orchestrator. (Contrast: `subtasks_complete` is fail-closed, `wp_state.py:370` `is not True` — do NOT copy that polarity.) | report 24 §3 amendment 1 |
| C5 | **Replay never validates.** The reducer is a pure fold (zero `validate_transition`/`GuardContext` references in `reducer.py`); historical audit (`status/validate.py` `validate_transition_legality`) re-checks edge legality only, never guards. A new guard therefore cannot retro-flag history — preserve this split; do not add guard evaluation to any replay/audit path. | report 24 §3 |
| C6 | **Layering direction: status never imports coordination.** `status` is the MM-owned OHS facade; `coordination/status_transition.py` + `transaction.py` are exempted plumbing ABOVE it (`tests/architectural/test_status_module_boundary.py`). The lazy reach at `status/aggregate.py:623` is the existing precedent-violation that bred the triple-orchestration mess — do not add another. This constraint is what kills the "shim emit over coordination" mechanism (D5). | report 24 §1.2#1 |
| C7 | **Three distinct failure policies preserved.** Single transactional: fail-closed on unresolvable coord worktree (#1848/SC-001). Batch: `status_transition.py:1574`. Inner-state: deliberately **degrades** to the uncommitted write on `BookkeepingWorktreeMissing` (#3460, pinned by named tests). Plus the alias-collapse no-op arm. A unified pipeline must keep all three explicit. | `status_transition.py:1318/:1446/:1574` |
| C8 | **Plain-door callers keep their semantics.** `contracts/anchoring.py`, `dossier/rebaseline.py`, `migration/verdict_provenance_backfill.py`, `runtime/next/runtime_bridge_composition.py` call plain `emit_status_transition` today; routing them through identity resolution (git subprocesses) or into committing writes for stored-`LANES` missions is a semantic change, not a refactor. Pin with a no-new-commits test (LANES mission via plain door). | report 24 §1.2#4, R2 |
| C9 | **Red-first regression repros are transitional** — after the fix they are deleted/replaced by unit tests or relocated to functional homes (house rule). | memory: redfirst-transitional |
| C10 | **Test policy:** `make test-fast` baseline + blast radius (`tests/status/`, `tests/coordination/` if present, targeted `tests/runtime/`); never the full arch suite locally. Terminology guard before any doc push. | CLAUDE.md §Test policy |

---

## 1. Area 1 — writer census + lock design (→ WP01)

### Settled decisions

- **D1 — Final census: 3 locked / 4 unlocked writer families, plus the unlocked batch door.**
  Locked: ① emit single + inner-state (`status/emit.py:634`, `:1013` — note `:1013` belongs to
  `emit_inner_state_changed` at `:961`, **not** the batch); ② lifecycle appender
  (`status/lifecycle_events.py:538` → `_lifecycle_write_lock:234-254` → `feature_status_lock`);
  ③ `BookkeepingTransaction` (`transaction.py:290`, held for the txn lifetime, so its append AND
  rollback-truncate run under it). Unlocked: ④ `retrospective/events.py:213` raw `open("a")`
  (largely the superseded `run_terminus` path); ⑤ `retrospective/lifecycle_events.py:250-256`
  (`_append_retro_lifecycle_event` — raw `open("a")` + TOCTOU `_next_lamport` read at `:265`; its
  callers `post_merge/retrospective_terminus.py` and `runtime/next/runtime_bridge_retrospective.py`
  are the **live** post-merge path — highest-priority fix of the four); ⑥⑦ the two migration
  backfills (`migration/verdict_provenance_backfill.py:419`,
  `migration/backfill_runtime_state.py:1533` + `:1535` — atomic primitives but no lock). And:
  `emit_status_transition_batch` (`emit.py:808-960`) **takes no lock at all** (verified: zero
  `feature_status_lock` in the body; appends via `append_event_stream_atomic_verified` ~`:934`).
  **Dropped from census:** `core/mission_creation.py` — routes through the locked lifecycle
  appender; its direct touch is a benign `touch(exist_ok=True)` (Renata correction, confirmed).
  The in-code "only 2 of 6" comment (`orchestrator_api/commands.py:3568-3570`) is a stale
  historical admission — quote it as such, never as present-tense fact.
- **D2 — Fix pattern = the `lifecycle_events.py:234-254` migration, generalized.** Route each raw
  writer through an atomic-append store primitive UNDER `feature_status_lock`. The atomicity fix
  travels WITH the lock: `retrospective/events.py` needs raw `open("a")` →
  `append_raw_rows_atomic`-class primitive in addition to the lock (an `os.replace` writer racing a
  buffered append clobbers it). Named precondition gaps: none of the three retrospective/migration
  writers has `repo_root` in scope — derive via `resolve_status_lock_root`
  (`workspace/root_resolver.py:36` — note: NOT in `status/`, contra report 24's implication); the
  pattern's `nullcontext()` no-git degrade must be a conscious per-site choice.
- **D3 — Three lock rules, encoded in code + WP docs.** Observed hierarchy (no inverse edge):
  L5 merge-global sentinel → L1; L3 verdict-save queue → L1 (bounded); L1 re-entrant (3 deep in
  production: `workflow_executor` → `work_package_lifecycle` → `transaction`); L1 → L4 workspace
  `threading.Lock` → git (only via `BookkeepingTransaction`). Rules: (a) any L1 acquisition
  reachable from an L3 scope uses the bounded `_in_queue_status_lock_timeout` pattern
  (`cli/commands/agent/tasks_verdict_persistence.py` ~`:546-561` / `review/cycle.py:804,881` —
  L3→L1-unbounded against L1→git is the one constructible deadlock-shaped outage, the #3773
  class); (b) the merge path's new retrospective L1 take carries a **finite timeout** (L5→L1 with
  default timeout `-1` otherwise converts a slow status commit into a repo-wide merge refusal);
  (c) one lock-key convention (D4). Adding L1 to the four unlocked writers creates **no new
  deadlock** — none sits under an enclosing lock; re-entrancy absorbs accidental same-path nesting.
- **D4 — Lock key = `feature_dir.name` uniformly, via `resolve_status_lock_root`.**
  `feature_status_lock_path` keys on `mission_slug` (`locking.py:57-60`) while the transaction keys
  identity on `mission_id`: slug collision ⇒ shared lock file (over-serialization); a bare/legacy
  slug ⇒ a *different* lock file that serializes against nobody
  (`status/migrate_lifecycle_envelope.py:228-243` documents this exact trap). Cheap, in-scope fix.

### Red-first targets (WP01)

1. **The rollback-truncate race** — NOT concurrent appends. POSIX `O_APPEND` whole-line buffered
   writes land atomically, so "two writers, one raw `open('a')`" will not reliably go red
   (Renata's correction, adopted as binding). The reproducible lost-write: a raw (retrospective)
   append landing inside `BookkeepingTransaction._rollback`'s truncate-to-pre-emit-offset window —
   `fh.truncate(self._pre_emit_size)` at **`transaction.py:944`** (reports cite `:943`; verified
   `:944` at HEAD) — is destroyed. Repro shape: start a transaction, force its commit to fail,
   interleave a raw `_append_retro_lifecycle_event` between the pre-emit size capture and the
   truncate; assert the retro event survives (RED on main).
2. **The backfill two-append window** — `backfill_runtime_state.py:1533` (transitions) + `:1535`
   (annotations) are a non-atomic pair; its idempotency read at `:1497` (`read_event_stream`) is
   TOCTOU and must move inside the lock.
3. **Lock-held assertion per writer family** + a lock-key test (two missions, colliding slugs,
   distinct `feature_dir.name`s ⇒ distinct lock files; bare-slug legacy dir ⇒ same lock as its
   ordinary writers).

### Open questions for the spec interview

- **Q1:** Does the batch door get its lock in WP01 (at the emit/store layer, immediately) or as
  part of the WP02 shell composition (one change instead of two)? Report 24 says "free under the
  §1.4 layering" — but WP01 may land first.
- **Q2:** Is a finite default L1 timeout (+ structured timeout error naming the holder) in Mission
  A's scope, or a named cheap follow-up? (Report 24 §6-3 leans follow-up; the merge-path finite
  timeout of D3(b) is in scope either way.)
- **Q3:** `retrospective/events.py` is largely the superseded path ("do not add new callers",
  `post_merge/retrospective_terminus.py:79-81`) — harden it, or fold its hardening into a
  deprecation/removal note and prioritize `retrospective/lifecycle_events.py`? (Default: harden
  both; the live one first.)

---

## 2. Area 2 — emit collapse via layered extraction (→ WP02, the mission's core)

### Settled decisions

- **D5 — Layered extraction, NOT shim-over-coordination.** Promote `_prepare_event`
  (`coordination/status_transition.py:842-945` — already the de-facto shared core: alias-resolve →
  infer gates → alias-collapse → build evidence → `validate_transition` → `build_status_event`,
  currently implemented by reaching into five `_emit` privates) into `status/` as **one public,
  pure, I/O-parameterized pipeline function**, with **two thin composition shells**: the
  flat/primary shell (lock + atomic append + materialize + immediate fan-out) and the transactional
  shell (txn + post-commit-deferred fan-out). The originally-planned "make `emit_status_transition`
  a thin delegating shim over `coordination.status_transition`" is REJECTED: it inverts C6's
  layering and changes plain-door caller semantics (C8). The layered cut is also the better future
  seam for #2173's StatusWriter port (port wraps a status-owned pipeline, not plumbing).
- **D6 — Scope = THREE orchestrations + the aggregate's duplicate validation.** (1) `MissionStatus.transition`
  (`status/aggregate.py:605-698`) — the ADR-ratified authoritative write facade (#1667, C-004) —
  re-derives from_lane, re-infers gates, re-runs `validate_transition` (`:685`), then calls the
  transactional door which re-derives and re-validates again: route it through the shell, delete
  the pre-duplication. (2) The transactional door (`:1318`) + its batch (`:1574`) and inner-state
  (`:1446`) siblings. (3) The legacy plain door (`emit.py:508`), which survives as the fallback's
  target and the plain-door callers' entry. All three twin PAIRS converge on the one pipeline; the
  three failure policies (C7) stay explicit per-shell/per-arm.
- **D7 — The `effective_root`/owned-mission divergence is a live intra-file whack-a-field proof and
  gets fixed in the collapse.** Single variant: owned-mission check raising `ActionContextError`
  (`status_transition.py:1342-1345`) + acquire with `primary_root or repo_root` and `effective_root=`
  kwarg (`:1362-1369`). Batch variant: **none of it** (`:1605-1614` — plain `repo_root`, no check,
  no kwarg; verified at HEAD). A feature landed on one sibling and silently missed the other inside
  one file. The unified pipeline makes the divergence structurally impossible.
- **D8 — Fan-out ordering unifies on post-commit-deferred, and the phantom fan-out is a named
  defect.** In `_fallback_emit_single._coord` (`status_transition.py:401-432`), the arm calls plain
  `_emit.emit_status_transition`, whose step-7 SaaS fan-out (`emit.py:794` `_saas_fan_out`, after
  L1 release) fires **before** `_commit_status_artifacts_to_coord`; on commit failure the event is
  truncated back (`_restore_coord_status_artifacts`) but the outside world was already notified of
  an event that no longer exists. Fix: all fan-out defers behind commit success in the coord arm.
- **D9 — Docs follow, Mission C owns final text.** The stale "single entry point" sentence
  (CLAUDE.md status section; `docs/architecture/status-model.md:393`) is corrected in-WP, but
  Mission C WP01 has the final word on the contended paragraphs (three writers: A-WP02, PR #3885,
  C-WP01 — extend the existing soft-dep to the CLAUDE.md hunk).
- **Sizing (binding):** 4–5 days once batch/inner-state/aggregate are in scope — not the original
  "2–3 days". This WP is the mission's core.

### Red-first targets (WP02)

1. **Phantom fan-out rollback escape** — coord-topology mission, fallback path, commit forced to
   fail: assert zero SaaS/zeitgeist fan-out for the truncated event (RED on main via
   `emit.py:794` firing pre-commit).
2. **Twin-divergence pin** — owned-mission (`effective_root`) request through the batch door: today
   silently skips the owned-mission refusal the single door raises (`:1342-1345` vs `:1594+`); RED
   as an equivalence test. (The original "ordering parity" test also goes red — immediate
   `emit.py:794` vs deferred `queue_saas_emission:1403/:1688` — keep it as a second pin.)
3. **No-new-commits pin (C8)** — stored-`LANES` mission via the plain door: working tree gains no
   commits (guards against the rejected shim mechanism resurfacing during implementation).
4. Post-collapse (transitional swap per C9): delegation tests replace the divergence pins.

### Open questions for the spec interview

- **Q4 (operator decision B3 — MUST be resolved before WP02 starts):** which surface is *named*
  the one orchestrator — `MissionStatus` (the aggregate, per the Accepted ADR chain #1667/C-004)
  over the promoted status-owned pipeline, or the pipeline itself with the aggregate as one caller?
  The debrief recommends the aggregate per the existing decision records; record the answer in the
  WP02 design note. The wrong choice re-inverts C6 or silently changes commit semantics.
- **Q5:** Does the batch shell *gain* the single shell's owned-mission/`effective_root` handling
  (feature-parity, D7's default), or is any part of the divergence adjudicated as intentional?
  (No evidence of intent found; default is parity.)
- **Q6:** Where do the five `_emit` private symbols (`_derive_from_lane`, `_generate_ulid`,
  `_mirror_phase1_frontmatter_lane`, `build_status_event`, `_infer_subtasks_complete`) land —
  pipeline-internal privates, or narrow public helpers? (Constraint: the phase-gated frontmatter
  `lane` mirror must remain the tree's ONLY `write_frontmatter` of `lane` —
  `test_2093_authority_invariant.py`.)
- **Q7:** O(n) `_derive_from_lane` full-log reduction per emit (O(n²) per mission life) — the
  pipeline promotion is the natural place to thread a snapshot-anchored read, but compaction is a
  NON-GOAL (§5). Does WP02 merely preserve current cost, or is the cheap snapshot-read allowed
  in-scope? (Default: preserve; flag follow-up on #3893.)

---

## 3. Area 3 — dependency gating into the FSM guard (→ WP04)

### Settled decisions

- **D10 — Readiness becomes a `GuardContext` field, tri-state, fail-open on `None` (C4).**
  Guard the entry edges `planned→claimed` / `claimed→in_progress`; `force` bypasses with
  actor+reason (existing semantics). Today `validate_transition` has NO dependency logic
  (`transitions.py`, `wp_state.py` — zero "depend" hits beyond a docstring) and a direct emit
  claiming a dep-blocked WP **succeeds** — the WP04 red-first test, RED on main.
- **D11 — Resolution happens INSIDE the lock/transaction, against the transaction's event surface.**
  `dependency_readiness_for_wp` (`core/dependency_graph.py:34`) reads other WPs' lanes; resolving
  it before the lock reproduces at the chokepoint the exact pre-flight TOCTOU the WP closes, and
  resolving against the primary planning dir under coord topology reads stale state — use
  `txn.feature_dir` (the coord surface when coord topology). Both qualifiers are binding (report 24
  amendments; the plan's "resolve once inside the orchestrator" lacked them).
- **D12 — Reuse, don't reimplement.** `dependency_readiness_for_wp` already encodes
  approved-OR-done (gating on `done` only deadlocks same-mission chains — CLAUDE.md). The 6
  existing caller sites (`cli/commands/implement.py:1340`, `agent/workflow_executor.py:653`,
  `agent/tasks_status_view.py:228`, `orchestrator_api/commands.py:1115,1440`,
  `runtime/next/discovery.py:150`) are demoted to pre-flight UX — left in place, re-commented.
  Re-invoking `implement` on an `in_progress` WP stays a no-op resume (not re-gated).

### Red-first targets (WP04)

1. Direct `emit_status_transition` claiming a dep-blocked WP succeeds today — RED on main.
2. Probe-site regressions: `lanes/recovery.py:78` progression probe and
   `agent/tasks_transition_core.py:337` FR-015 force-free probe both still pass with a `None`
   readiness field (pins C4's polarity).
3. Force-override + same-mission chain ordering (WP02 depends on WP01 `approved` — claim allowed;
   `in_progress` dep — claim blocked).

### Open question

- **Q8:** Fail-open-on-`None` (C4, the default) vs updating both probe sites to supply verdicts and
  going fail-closed — the spec should confirm fail-open explicitly and record why (probe sites +
  no-bypass-after-WP03), so a future reader doesn't "fix" the polarity to match `subtasks_complete`.

---

## 4. Area 4 — run-state crash-safety + identity (→ WP05)

### Settled decisions

- **D13 — Atomic cursor writes.** `engine._write_snapshot`
  (`runtime/next/_internal_runtime/engine.py:128-130`) is a plain `open("w")+json.dump` overwrite
  of the run's authoritative cursor — copy `reducer.materialize`'s tmp-then-`os.replace` shape
  (~6 lines). The journal `_append_event` (`:110-119`, plain append) hardens with it.
- **D14 — `feature-runs.json` keyed by `mission_id`; slug demoted to display.** Lookup today is
  `if mission_slug in index` (`runtime_bridge_io.py:618`; `mission_id` stored in the entry but not
  the key, `:650-657`) — a direct 083 violation (C3) re-opening the collision class 083 closed. A
  missing `state.json` currently falls through silently to "start a new run" (`:617-627`,
  orphaning history) — becomes a loud, structured error.
- **D15 — Pure read path.** `runtime/next/decision.py:369-377` calls the *writing*
  `materialize(lane_read_dir)` (`:373`) inside `try/except: pass` on a progress-count path — the
  exact call three other sites explicitly refuse (`dashboard/scanner.py`, `audit/classifiers/`,
  `agent/mission_finalize.py`) because it clobbers tracked `status.json` during scans (the merge
  coord-flatten/reset-guard gotcha family). Swap to `materialize_snapshot` (pure).

### Red-first targets (WP05)

1. Identity: two missions sharing a slug resolve distinct runs — RED on main (`:618` slug key).
2. Crash window: kill between truncate-of-old and write-of-new `state.json` ⇒ recoverable (tmp file
   or old file intact), not a torn cursor.
3. Read-path purity: the progress query leaves tracked `status.json` byte-identical.
4. Missing `state.json` with a live index entry ⇒ structured error, not a silent fresh run.

### Open questions

- **Q9:** Index migration shape — in-place rekey on first touch vs a one-shot migrate step; and the
  key for legacy missions without `mission_id` (the transaction's `legacy-<slug>` fallback pattern
  at `status_transition.py:1606` is the precedent — adopt it?).
- **Q10 (lane assignment, see §6):** WP05 shares all four contended files with Mission B — does it
  stay in Mission A behind an "A goes first" ordering (the debrief's answer), move to Mission B, or
  become the declared single-owner shared lane? The spec must state the choice; the interference
  map below assumes **A first, B rebases**.

---

## 5. Explicit NON-GOALS (state verbatim in the spec)

1. **No port inversions** — StatusReader/StatusWriter (#2173) are NOT built here. A-WP02 only
   *shapes* the seam (the status-owned pipeline is the future StatusWriter cut). The StatusReader
   port is **de-serialized** from this mission (Renata correction C3 of report 23; recorded in
   #2173 tracker action) — do not reintroduce the false dependency.
2. **No runtime facade work** — Mission D (`runtime-public-surface-seam`, queued behind PR #3888)
   owns the `_internal_runtime` promotion/facade and the `runtime` naming collision.
3. **No event-log compaction / snapshot-anchored reads** — flag as follow-up on #3893 with the
   O(n²) evidence: `_derive_from_lane` reduces the FULL log on every emit (O(n) per transition over
   an append-only log with no compaction story). Currently unowned.
4. **No `transaction.py` rollback-atomicity redesign** — the truncate/restore pair is two
   independently-guarded non-atomic steps (`transaction.py:922-971`; live-reproduced per
   `orchestrator_api/commands.py:3600-3614` region). Document the crash window; defer (item 16 /
   R9). Same for the NFR-006 L1-across-git standing violation (C2) — risk register + follow-up
   note, not in-scope.
5. **No `status/adapters.py` fan-out registry redesign** — live and wired (the E3/zeitgeist seam);
   leave it. No zeitgeist/upstream work; no `RuntimeEventEmitter` disposition (Mission B WP01, with
   its own decision record per debrief B2).
6. **No `wp_state.py` edge/guard/force logic changes** — it is the healthy, ratified part; WP04
   only adds one guard field + clause through the established `GuardContext` shape.
7. **No event schema changes**; no snapshot-drift-on-read chokepoint (accepted risk; follow-up home
   is the read-chokepoint drift check named in report 24 §6-6).

---

## 6. Interference map

### 6.1 Mission B (`dead-port-disposition`) — NOT parallel-safe; **A goes first**

Four shared files (verified at HEAD; "A ∥ B disjoint" is FALSE — report 24 §5):

| File | Mission A touch | Mission B touch |
|---|---|---|
| `runtime/next/runtime_bridge_io.py` | WP05 rekeys the index (`:611-660`) | B-WP01 emitter consolidation: `NullEmitter` import (`:95`), constructions (`:592,:643`) |
| `runtime/next/_internal_runtime/engine.py` | WP05 `_write_snapshot` (`:128-130`) | B-WP01: four `emitter or NullEmitter()` entry defaults (`:191-795`) |
| `runtime/next/decision.py` | WP05 `materialize`→`materialize_snapshot` (`:373`) | B-WP03 owns its `mission_v1.events` import (`:200`) + dead DSL readers (`:194-235`) |
| `runtime/next/runtime_bridge_engine.py` | adjacent to all WP05 bridge-satellite work | 16 of 29 production `sync_emitter` sites |

Resolution (debrief §4): **Mission A first, Mission B after (or a declared single-owner shared
lane for exactly these four files)**. The spec records the choice (Q10).

### 6.2 PR #3888 (runtime governance ledger) — no source-file conflict, one binding mental model

- #3888 (tip `a86907a52d`) touches docs/ADRs, its kitty-specs, pyproject, `tests/architectural/*` —
  none of Mission A's status/coordination/retrospective/migration surfaces.
- The `_RUNTIME_ALLOWED_SPECIFY_CLI` ledger (`test_layer_rules.py`) is per first-level subpackage;
  A-WP05's runtime edits stay inside already-ledgered subpackages (`status`, `mission_metadata`,
  `mission_v1`, `retrospective`) — **no ledger change for A**.
- **Binding model: `test_runtime_ledger_has_no_stale_entries` REDS when a subpackage's last live
  edge is removed** — shrinking *forces* a same-PR ledger edit; it does not merely "tolerate"
  shrink. Any A/B refactor that removes a ledgered lazy reach budgets the ledger edit in the same
  PR. Likewise the widened doctrine scan pins `runtime_bridge_composition.py` /
  `runtime_bridge_io.py` in its baseline — removing those lazy reaches means updating that baseline
  in-PR. Whichever of B/#3888 lands second rebases.

### 6.3 Doc contention

CLAUDE.md status section + `status-model.md`: three writers (A-WP02, PR #3885 docs alignment,
Mission C WP01). **Mission C owns the final text** (D9); A-WP02's doc edit is the minimal
stale-sentence correction only.

---

## 7. Proposed WP slicing (5 WPs, no owned-file overlap)

Dependency shape: WP01 → WP03 (gate needs the fixed census to be green-able); WP02 → WP04 (guard
lands in the unified pipeline); WP05 independent (but see Q10 re Mission B). WP01 ∥ WP02 are
separable: WP01 owns the *out-of-pipeline* writers; WP02 owns the pipeline modules. The batch-door
lock (Q1) is assigned to WP02 below to keep files single-owner; if the spec answers Q1 "WP01", move
the batch-lock hunk and add `emit.py` to a declared shared file.

| WP | Slice | Red-first target (defect anchor) | owned_files sketch |
|---|---|---|---|
| **WP01** — serialize the out-of-pipeline writers | Lock+atomic-append the 4 unlocked families (D1/D2); encode the 3 lock rules (D3); lock key → `feature_dir.name` (D4) | Rollback-truncate race (`transaction.py:944` window; RED); backfill two-append + `:1497` TOCTOU; lock-key collision test | `retrospective/events.py`, `retrospective/lifecycle_events.py`, `migration/verdict_provenance_backfill.py`, `migration/backfill_runtime_state.py`, `status/locking.py`, (touch) `merge/executor.py` retro-path timeout, tests |
| **WP02** — layered pipeline extraction | Promote `_prepare_event` into `status/` pure pipeline + two shells (D5); converge 3 orchestrations + aggregate (D6); batch-door lock + `effective_root` parity (D7); fan-out unification + phantom-fan-out fix (D8); minimal doc correction (D9). **4–5 days.** | Phantom fan-out pre-commit (`status_transition.py:401-432` + `emit.py:794`; RED); batch owned-mission divergence (`:1342-1345` vs `:1605+`; RED); no-new-commits plain-door pin (C8) | `status/emit.py`, `status/aggregate.py`, new `status/<pipeline>.py`, `coordination/status_transition.py`, CLAUDE.md + `status-model.md` (stale-sentence hunks only), tests |
| **WP03** — facade strip + write gates | `append_event*` exports (`status/__init__.py:518-537`) → `status/_unsafe.py` with shrink-only caller allowlist; AST arch gate: no `open(..,"a")`/write on paths ending `status.events.jsonl` outside `status/store.py`; note on #3895 as the census-gate rule's first instance | The two gates themselves, seeded from WP01's fixed census, **with non-vacuity floors** (the vacuous-gate pattern of report 27 §3.3 — a gate matching zero writers must go RED) | `status/__init__.py`, `status/_unsafe.py` (new), `tests/architectural/` (2 new gates) |
| **WP04** — dependency guard | Readiness → `GuardContext`, tri-state fail-open (D10/C4); resolve in-txn on `txn.feature_dir` (D11); reuse `dependency_readiness_for_wp`, demote 6 caller copies (D12) | Direct emit claims dep-blocked WP — succeeds today (RED); probe-site `None` regressions (`lanes/recovery.py:78`, `tasks_transition_core.py:337`); force + chain-order tests | `status/models.py` (GuardContext), `status/wp_state.py` (guard clause only), pipeline touch-point from WP02, comment-edits at the 6 caller sites, tests |
| **WP05** — run-state hardening | Atomic `_write_snapshot` (D13); `feature-runs.json` mission_id key + loud missing-state (D14); `decision.py:373` pure read (D15) | Slug-collision distinct runs (RED, `runtime_bridge_io.py:618`); crash-window cursor; read-path purity; missing-state loud error | `runtime/next/_internal_runtime/engine.py`, `runtime/next/runtime_bridge_io.py`, `runtime/next/decision.py`, (maybe) `runtime_bridge.py` `_load_feature_runs`, tests |

Note on WP04's `wp_state.py` vs the "no edge logic changes" non-goal: WP04 adds the one guard
field/clause via the established `subtasks_complete` shape (`emit.py:650-662` precedent) — it does
not restructure edges, force, or terminal rules.

---

## 8. Risk register (carry into the spec's risk section)

Condensed from report 24 §7; all mitigations already folded into the decisions above.

| # | Risk | Mitigation home |
|---|---|---|
| R1 | WP02 shim direction inverts layering / misses batch+inner-state+aggregate | D5/D6 (layered extraction, full scope, resized) |
| R2 | Plain-door callers silently gain commit semantics | C8 pin test (WP02) |
| R3 | Phantom fan-out for rolled-back coord-fallback events | D8 red-first (WP02) |
| R4 | Fail-closed `None` guard breaks recovery + FR-015 probe | C4/D10 + probe tests (WP04) |
| R5 | Readiness resolved outside lock / wrong surface | D11 (WP04) |
| R6 | Census drift (mission_creation false positive; live retro writer missed) | D1 (WP01) |
| R7 | New L1 takers under L3/L5 convert stalls into outages | D3 rules a+b (WP01) |
| R8 | Lock-key divergence ⇒ silent non-serialization | D4 (WP01) |
| R9 | L1-across-git NFR-006 standing violation amplifies as acquirers grow | risk register + #3893 note; finite-timeout follow-up (NON-GOAL 4) |
| R10 | WP01 red-first won't go red as originally drafted | corrected repro shapes (§1) |
| R11 | A ∥ B collide on 4 runtime files | §6.1 (A first / shared lane; Q10) |
| R12 | Three-way doc contention | D9 (Mission C final word) |

---

## 9. Verification deltas vs the source reports (for the record)

- `transaction.py` truncate is at **`:944`** at HEAD (reports cite `:943`) — same statement, one
  line off.
- `resolve_status_lock_root` lives at **`workspace/root_resolver.py:36`**, not in `status/`.
- The L3 verdict-save queue module is **`cli/commands/agent/tasks_verdict_persistence.py`**
  (report 24 cited it without the `cli/commands/agent/` prefix).
- Renata's "`emit.py:1013` batch — feature_status_lock" is imprecise: `:1013`'s lock belongs to
  `emit_inner_state_changed` (`:961`); the batch door (`:808-960`) is confirmed lockless —
  report 24's correction is the binding one.
- All other load-bearing anchors (D1–D15, C1–C8, all red-first sites) re-verified verbatim at
  HEAD `e721763759` on 2026-09-06.

---

*Read-only consolidation; this file is the single permitted write. Sources: reports 21/22/23/24 +
27 §2/§4 in this directory; anchors re-verified by targeted grep/read against the tree.*
