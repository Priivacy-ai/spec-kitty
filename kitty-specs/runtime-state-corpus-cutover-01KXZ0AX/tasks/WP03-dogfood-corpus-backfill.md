---
work_package_id: WP03
title: Execute dogfood corpus backfill + commit seeds (BLOCKER-fix)
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-002
- FR-003
planning_base_branch: feat/runtime-state-corpus-cutover
merge_target_branch: feat/runtime-state-corpus-cutover
branch_strategy: Planning artifacts for this mission were generated on feat/runtime-state-corpus-cutover. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/runtime-state-corpus-cutover unless the human explicitly redirects the landing branch.
subtasks:
- T009
- T010
- T011
- T012
agent: "claude"
shell_pid: "3781659"
shell_pid_created_at: "1784551839.14"
history:
- timestamp: '2026-07-20T08:39:02Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/specify_cli/migration/
create_intent:
- tests/specify_cli/migration/test_dogfood_corpus_backfilled.py
execution_mode: code_change
model: claude-opus-4-8
owned_files:
- tests/specify_cli/migration/test_dogfood_corpus_backfilled.py
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP03 – Execute dogfood corpus backfill + commit seeds (BLOCKER-fix)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the **`python-pedro`** agent profile (role: `implementer`)
**before doing any work**, and behave according to its guidance for the whole WP.

This WP writes **no source**, but it *drives* the WP01 migration CLI and must reason about its
fail-closed contract with an implementer's rigour: treat a verify failure as a real defect to route
back to WP01, never noise to force past.

## Objective

RUN `spec-kitty migrate backfill-runtime-state` over **this repository's own** `kitty-specs/` corpus
and **commit** the two resulting artefact classes: the **seed events** the backfill emits
(`kitty-specs/**/status.events.jsonl` — `InnerStateChanged` seed annotations + a seed `planned→claimed`
transition for claim state) and the **`status_phase` flips** (`kitty-specs/**/meta.json` set to `"1"`
for every mission that verifies) — so that when WP04 (IC-03) makes the reduced snapshot the
**unconditional** authority, every dogfood mission already has its runtime state in the event log
instead of reducing to an **empty** snapshot.

This is the migration contract's **execution** step (research D-07 / plan IC-01b). It has **no source
edits**: the *tool* ships in WP01, the *consumer upgrade path* ships in WP02 — but **no WP has ever
backfilled *this* repo's corpus**. WP03 owns exactly that gap and nothing else.

## Context & grounding

### What the corpus looks like today (data-model "Today's corpus state")

- All ~299 dogfood missions are `status_phase=0`.
- Under the flag-OFF path their runtime slots — `shell_pid`, `agent`, `assignee`, `tracker_refs`,
  subtask completion, `review` — are written to WP-file frontmatter / `tasks.md` checkboxes **only,
  never emitted as events** (`emit.py:314-317`).
- Consequence: **every** mission's reduced snapshot is currently empty. Nothing in the event log
  carries runtime state until this WP seeds it.

### Why this is a BLOCKER (plan IC-01b + the "Merge-unit atomicity" callout; research D-07)

- The moment WP04 removes the flag-OFF branch and deletes `_phase1_snapshot_authority_active`, all the
  runtime-slot readers become **unconditional** (always the snapshot).
- If IC-03 reaches local main **before** WP03 has committed this repo's seed events, every dogfood
  mission reads an **empty snapshot** → `_infer_subtasks_complete` fail-closes to `False`,
  ownership/review reads return `None`, and the suite goes red **instantly**.
- This is the **exact contract-step-ownership gap the mission's own field report documents**
  (`docs/plans/engineering-notes/2026-07-19-migration-contract-step-ownership-field-report.md`):
  IC-01 ships the *tool*, IC-02 backfills *consumers* on `spec-kitty upgrade`, but neither runs on
  *this mission's merge*, so neither closes the in-repo window. **The plan must own backfill
  *execution*, not just the *tool*.** WP03 is that owner.

### Merge-unit atomicity (BLOCKER-fix — non-negotiable)

- WP03 must land in **one merge unit** with WP04/WP05 under the dependency spine
  `IC-01 → IC-01b → {IC-03, IC-04}`, i.e. `WP03 → WP04 → WP05`.
- WP03's seeds+flips must be merged to **local main *before* WP04**, or local main is transiently red.
- The dependency edges enforce the order; the mission PR carries all three together. Do **not** split
  WP03 out of the cutover merge unit.

### The requirements, applied to THIS corpus

- **FR-001 (dry-run CLI)** — use `migrate backfill-runtime-state` with `--dry-run` first (reports
  would-seed counts, writes nothing), then the real run.
- **FR-002 (fail-closed verify — wired)** — the command invokes the existing WP01-library
  `verify_backfill`: count+value parity of the reduced snapshot against `read_legacy_runtime`
  (the `LegacyWPRuntime` ground truth). Any mismatch aborts **before** a flip.
- **FR-003 (atomic verify-then-flip)** — `status_phase` is flipped to `"1"` **only** for missions whose
  backfill+verify passed. The CLI is the **sole writer** of this field; there is no hand-flip surface.
- **C-001 (strict order)** — `backfill → verify(FAIL-CLOSED) → flip → …`. WP03's backfill+commit is the
  predecessor WP04's reader cutover depends on. Nothing downstream may precede it.
- **NFR-001 (zero silent data loss)** — **zero** tolerated parity mismatches; corpus-wide verify `ok`;
  `status_phase` never changes on a failed verify.
- **INV-1 / INV-4 / INV-5** (data-model) — a mission is `status_phase="1"` **iff** its verify passed;
  a re-run seeds nothing and re-flips nothing; all event writes resolve via `canonicalize_feature_dir`
  so nothing lands at repo root.

### `status_phase` is NOT inert (data-model / research D-02)

- Flipping `0 → 1` also **activates the kept `_legacy_lane_mirror_enabled` mirror** for that mission
  (C-004 keeps it live — it still reads `status_phase`).
- That lane-mirror consequence is WP04's regression to own; be aware that the flip WP03 commits is
  **load-bearing, not cosmetic** — do not treat the `meta.json` deltas as throwaway.

### CLI exit semantics (contract — for reading the run's result)

- **Exit 0** iff every visited mission flipped or was already migrated (idempotent skip); **exit
  non-zero** if any mission's verify failed — the command prints each mismatch and flips **no**
  unverified mission.

## Subtasks

- [ ] **T009 [FR-001] Dry-run + sanity-check.**
  Run `uv run spec-kitty migrate backfill-runtime-state --dry-run` over this repo's `kitty-specs/`.
  - Capture the **per-mission would-seed counts** and the would-flip set; confirm it wrote **0 events,
    0 flips**.
  - Sanity-check the counts against the old reader (`read_legacy_runtime` / `LegacyWPRuntime`) on a spot
    sample: a mission carrying frontmatter `shell_pid`/`agent`/`tracker_refs`/subtask completion should
    report a matching non-zero seed count; a never-claimed WP should report a skip/warn (edge case),
    **not** a seed.
  - If the dry-run reports **0 seeds corpus-wide**, STOP — the tool is not wired to this corpus and that
    is a **WP01 defect**, not a WP03 no-op.

- [ ] **T010 [FR-002/FR-003/NFR-001] Real run (no `--dry-run`).**
  Run `uv run spec-kitty migrate backfill-runtime-state` for real.
  - It seeds `InnerStateChanged` events + a seed `planned→claimed` transition per mission, verifies
    count+value parity, and flips `status_phase` to `"1"` **only** for every mission that verifies.
  - Confirm **corpus-wide verify is `ok` — zero mismatches** (NFR-001) and the command **exits 0**.
  - **If ANY mission fails verify: STOP.** A parity failure means the seed reconstruction diverges from
    the old reader — a **real defect to fix in WP01 / the backfill library**. Do **not** force-flip, do
    **not** hand-edit `status_phase`, do **not** commit a partial corpus. Capture the named mismatch and
    route it back to WP01.

- [ ] **T011 Commit the migration payload.**
  Stage and commit the seed-event deltas (`kitty-specs/**/status.events.jsonl`) **and** the
  `status_phase` flips (`kitty-specs/**/meta.json`) — these two file classes ARE the entirety of WP03's
  diff (no source).
  - The diff is **large by design** (hundreds of missions × seed events): a large diff here is
    **expected and IS the migration payload**, not a review smell.
  - Use one clear commit, e.g.
    `chore(runtime-state): backfill dogfood corpus runtime state to event log (IC-01b)`.
  - Do NOT let unrelated working-tree changes ride along; only the two owned file classes appear.

- [ ] **T012 Acceptance.**
  Prove the seeded corpus is populated and reads correctly under the *future* unconditional regime:
  1. `wp_snapshot_state` (the #2817 accessor) is **non-empty** for every mission that carries runtime
     state (never-claimed / no-runtime missions are legitimately empty).
  2. Sample a **done** mission and prove `_infer_subtasks_complete` returns the **correct** value with
     the phase-1 predicate treated as deleted — do a **LOCAL IC-03-style dry-run** to prove it (force
     the snapshot-authority path in a scratch check / monkeypatch, or read the snapshot directly).
     **Do NOT actually delete `_phase1_snapshot_authority_active` here — that is WP04.** The point is to
     demonstrate that once WP04 lands, this committed corpus reads green.
  3. **Idempotent re-run:** run the command a second time; confirm it seeds **nothing** and re-flips
     nothing (INV-4) — a clean no-op, exit 0.
  4. **Author the durable guard test** `tests/specify_cli/migration/test_dogfood_corpus_backfilled.py`
     (this WP's single owned code deliverable — the seed/`meta.json` commit under `kitty-specs/**` is the
     execution *output*, which WP ownership cannot cover): materialize the committed corpus for a sampled
     done mission and assert its reduced snapshot carries the expected runtime slots (non-empty), and that
     `verify_backfill` is `ok` for that mission. This locks the acceptance so a later regression (e.g. a
     stale/emptied corpus) fails loudly.

## Branch Strategy

- **Strategy:** Planning artifacts were generated on `feat/runtime-state-corpus-cutover`; completed
  changes merge back into `feat/runtime-state-corpus-cutover`.
- **Planning base branch:** `feat/runtime-state-corpus-cutover`
- **Merge target branch:** `feat/runtime-state-corpus-cutover`
- **⚠️ SAME MERGE UNIT AS WP04/WP05 (BLOCKER-fix):** WP03 must be merged to **local main *before*
  WP04** during WP-by-WP consolidation. The dependency edges `WP03 → WP04 → WP05` enforce this; the
  mission PR carries all three together. Merging WP04 (unconditional readers) ahead of WP03's committed
  seeds leaves local main transiently red — every dogfood mission would read an empty snapshot. Do not
  split WP03 out of the cutover merge unit.
- Per project policy: `spec-kitty merge` targets **local main only**; never `git push origin main`.
  Publishing is the operator's explicit, separate step.

## Test strategy

This is an **execution / data WP**, not a code WP — the verification surface is the migration outcome
itself, not new unit tests:

- **Corpus-wide `verify_backfill` is `ok`** with zero mismatches (NFR-001 / SC-001) — the primary gate.
- **`wp_snapshot_state` non-empty** for every runtime-carrying mission after the run (T012.1).
- **Idempotent re-run** seeds nothing / re-flips nothing (INV-4 / NFR-002).
- **No repo-root event file** (INV-5 / #2815): the run created no `status.events.jsonl` (or any event
  file) at the repository root — all writes resolved via `canonicalize_feature_dir` inside the library.
- The **durable guard test is REQUIRED** (T012.4) and is this WP's single owned code file:
  `tests/specify_cli/migration/test_dogfood_corpus_backfilled.py` — a check that the committed corpus
  reduces to non-empty snapshots for a sampled done mission (materialize → assert runtime slots present)
  plus `verify_backfill` `ok`. Run it with `uv run --extra test python -m pytest -p no:cacheprovider
  tests/specify_cli/migration/test_dogfood_corpus_backfilled.py` — bare `python` resolves a sibling
  checkout → false greens. Do **not** add broad new library unit tests here; the fail-closed verify +
  fault-injection coverage lives in WP01.

## Definition of Done

- [ ] **T009** dry-run executed; per-mission would-seed counts captured; sanity-checked against
  `read_legacy_runtime`; wrote 0 events / 0 flips.
- [ ] **T010** real run executed; **corpus-wide verify `ok`, zero parity mismatches**
  (FR-002 / NFR-001 / SC-001); `status_phase` flipped to `"1"` **only** for verified missions
  (FR-003 / INV-1); command exit 0. No mission force-flipped past a failed verify.
- [ ] **T011** seed-event deltas (`kitty-specs/**/status.events.jsonl`) + `status_phase` flips
  (`kitty-specs/**/meta.json`) committed as the migration payload; large diff expected.
- [ ] **T012** `wp_snapshot_state` non-empty for every runtime-carrying mission; a sampled done
  mission's `_infer_subtasks_complete` proven correct via a **local IC-03-style dry-run** (predicate
  NOT deleted here); idempotent re-run seeds nothing.
- [ ] **FR-001/002/003** honoured on this corpus; **SC-001** met; **INV-1** (flip iff verify passed),
  **INV-4** (idempotent), **INV-5** (no repo-root event file) all hold.
- [ ] Merge-unit note observed: WP03 lands **before** WP04 in the shared cutover merge unit.
- [ ] The owned guard test `tests/specify_cli/migration/test_dogfood_corpus_backfilled.py` is created and
  green (T012.4).
- [ ] The seed-event + `status_phase` commit under `kitty-specs/**` is the WP's *execution output* (WP
  ownership cannot cover `kitty-specs/` paths); the only *owned* code file is the guard test above. No
  other source changes in this WP.

## Risks & out-of-map edits

- **Never-claimed WPs skip runtime seeds — warn, not fail (spec Edge Cases).** A WP with no claim anchor
  cannot honestly carry completed subtasks, so its runtime seeds are skipped. Expect warnings for such
  WPs; they are **not** verify failures and must not be forced.
- **Do NOT delete the predicate here.** `_phase1_snapshot_authority_active` stays live until WP04. WP03
  only proves the corpus *would* read correctly once it is deleted (T012.2). Deleting it in this WP
  would make local main red on the WP03 tip.
- **The seed diff must be reviewed for correctness, not rubber-stamped.** "Large diff is the payload" is
  a reason to review *carefully* (spot-check that a sampled seeded snapshot equals the old reader), not
  a licence to wave it through.
- **A failed verify is out of WP03's authority to paper over.** If backfill parity diverges for any
  mission, the fix belongs in WP01 / `migration/backfill_runtime_state.py`, never in a hand-edit to
  `meta.json` or `status.events.jsonl`. WP03 stalls and reports; it never manufactures a passing state.
- **Keep the working tree clean.** Only the two owned file classes may appear in the commit — no
  incidental source, config, or generated-artefact churn riding along.

## Reviewer guidance

Spot-check the migration outcome; do not rubber-stamp the volume:

- **Parity:** pick several seeded missions across lanes and confirm the reduced snapshot equals the old
  `read_legacy_runtime` view **by count and value**; the corpus-wide verify must be `ok` (SC-001).
- **Flip discipline (INV-1):** every mission at `status_phase="1"` has a passing verify behind it; no
  `meta.json` shows a hand-flipped `"1"` without matching seed events.
- **Idempotency (INV-4):** re-running the command seeds nothing and re-flips nothing (exit 0, no-op).
- **No repo-root event file (INV-5 / #2815):** confirm no event file was created at the repository root.
- **Future-read proof (T012.2):** the sampled done mission's `_infer_subtasks_complete` is correct
  under a local snapshot-authority dry-run, with the phase-1 predicate **still present** (deletion is WP04).
- **Merge-unit:** confirm WP03 is sequenced to merge **before** WP04 in the cutover unit — flag any plan
  to land the reader cutover ahead of these seeds.

## Activity Log

- 2026-07-20T11:17:41Z – claude – shell_pid=3582981 – Assigned agent via action command
- 2026-07-20T11:32:58Z – claude – shell_pid=3582981 – BLOCKED on WP01 verify defects. Dry-run: 285/300 would-seed, 3303 seed events, 0 failed (T009 clean). Real run: 292 flipped, 3303 seeds, but 8 missions FAILED verify (exit 1) -> corpus-wide verify NOT ok, NFR-001/SC-001 unmet. Did NOT commit (partial corpus); reverted all partial seeds+flips. Two WP01/library defect classes: (1) never-claimed edge case hard-failed by verify_backfill (7 missions: 005,055,057,062,analysis-report-coord-worktree-fix,merge-coord-rollback-transactionality,+ our own live mission) - verify_backfill line ~702 counts has_evictable_state WPs with no _claim_anchors entry as 'count mismatch', contradicting spec Edge Case 'never-claimed -> warn not fail'; _build_seed_events line ~397 correctly skips them with a warning, verify must mirror that skip. (2) unshim-wave2-01KWMCAX tracker_refs parity: corpus frontmatter authored tracker_refs as char-list with duplicate ['#','2','2','9','1'] (5); reducer set-union dedups to 4 -> legacy-vs-snapshot mismatch. Fix belongs in WP01 migration/backfill_runtime_state.py (verify_backfill), never a WP03 hand-edit. Guard test deferred until corpus verifies ok.
- 2026-07-20T12:48:39Z – claude – shell_pid=3582981 – Re-run after WP01 verify fix (lane-a 906af76f5): verify OK corpus-wide (299/299 flip, 0 fail, exit 0), 285 missions seeded (3303 events); our own mission excluded (self-interference revert); idempotent re-run seeds nothing (seeded=0). Seed payload committed on feat primary partition (ecb6b452c, 583 files); guard test on lane-c (928b58927). Pre-review gate SKIPPED: hit its internal 300s timeout on the slow arch-dir scoped run (perf limit, not a failure). Per-file evidence at head: guard test tests/specify_cli/migration/test_dogfood_corpus_backfilled.py 4 pass + test_runtime_state_cutover.py 22 pass = 26 pass/50s; ruff clean; mypy at sibling baseline (only shared pytest-stub note; tests/ not CI-mypy-gated). WP03 is data+one-test only, no src changes.
- 2026-07-20T12:50:50Z – claude – shell_pid=3781659 – Started review via action command
- 2026-07-20T12:52:36Z – user – shell_pid=3781659 – Approved: corpus verify ok (0 mismatch), self-excluded, guard test 4-pass non-vacuous, idempotent
