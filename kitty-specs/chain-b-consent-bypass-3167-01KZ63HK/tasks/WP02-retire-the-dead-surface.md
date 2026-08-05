---
work_package_id: WP02
title: Retire the dead surface and its coverage, atomically
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-003
- FR-004
- FR-007
- NFR-001
- NFR-002
planning_base_branch: feat/chain-b-consent-bypass-3167
merge_target_branch: feat/chain-b-consent-bypass-3167
branch_strategy: Planning artifacts for this mission were generated on feat/chain-b-consent-bypass-3167.
  During /spec-kitty.implement this WP may branch from a dependency-specific base,
  but completed changes must merge back into feat/chain-b-consent-bypass-3167 unless
  the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
- T008
- T009
- T010
- T011
phase: Phase 2 - The retirement
history:
- at: '2026-08-04T10:30:00Z'
  actor: system
  action: Prompt generated from wps.yaml
agent_profile: python-pedro
authoritative_surface: src/specify_cli/sync/batch.py
create_intent:
- tests/architectural/test_batch_drain_retired_3167.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/sync/batch.py
- tests/architectural/test_batch_drain_retired_3167.py
- tests/sync/test_batch_sync.py
- tests/sync/test_batch_error_surfacing.py
- tests/sync/test_integration.py
- tests/sync/test_offline_replay.py
- tests/architectural/test_batch_split_single_authority.py
- tests/architectural/test_egress_consent_boundary.py
- tests/architectural/_baselines.yaml
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP02 – Retire the dead surface and its coverage, atomically

## ⚡ Do This First: Load Agent Profile

Load `python-pedro`. Then read `contracts/deletion-manifest.md` from WP01 — it is your contract.

## Goal

Delete the 24 first-tier and 9 second-tier symbols from `src/specify_cli/sync/batch.py`, the orphaned
module-level imports, **and** the test nodes that only covered them — **plus the `E15` allowlist
entry** — in **one commit**.

## ⚠️ Why this is one commit and not four

There is **no green intermediate state**. The moment the senders go, the 7 code-coupled test files break
at import. If the tests go first, the source still references nothing removed. And the two
egress-allowlist assertions are **bidirectionally coupled**:

- `test_no_unlisted_file_holds_an_egress_sink` reds if `E15` is removed while any transmit primitive
  remains in `batch.py`;
- `test_every_listed_file_still_holds_a_sink` reds if `E15` survives after the primitives go.

All three primitives live inside first-tier symbols, so a **complete** first-tier deletion leaves zero —
but a partial one does not. **Partial deletion is not a valid intermediate state.**

## Subtasks

### T005 — RED FIRST: land the per-name absence assertion

Write the assertion that the manifest's dead symbols are absent from `sync/batch.py`. It **must fail
now** (they exist) and pass after T007. Make the red *the consequence* — a named symbol still present —
not a boolean.

**Do not lean on `tests/architectural/test_no_dead_symbols.py`.** It keys on modules declaring
`__all__`, and `sync/batch.py` declares none, so **nothing in CI reds on stranded privates**. This
assertion is the substitute. (The previous plan cited that gate as the forcing function and was wrong.)

### T006 — Disposition every coupled test node BEFORE deleting anything

At **node-id** granularity, recorded in `contracts/deletion-manifest.md`. **Five of the seven files are
SPLITS.** Whole-file deletion is the coverage-loss event:

| File | Shape | Must survive |
|---|---|---|
| `test_batch_sync.py` (1489 lines, 40 tests) | split, ~37 retire | `TestBatchSyncResult` (2) and `test_oversized_batch_error_classifies_without_unknown` — they cover the retained `BatchSyncResult` and `categorize_error` |
| `test_batch_error_surfacing.py` (54 nodes) | split, ~26 retire | ~28 nodes: `TestCategorizeError`, `TestFormatSyncSummary`, `TestFailureReport`, `TestProcessBatchResults`, `TestBatchSyncResultProperties`, `TestBatchEventResult` |
| `test_integration.py` | split, 7 retire | `TestLamportClockReconciliation` (2) — pure `sync.clock` |
| `test_offline_replay.py` | split, ~11 retire | `TestQueueEventsOffline` (2), `TestQueueSizeLimit` (2) — pure `OfflineQueue`, which stays live |
| `test_batch_split_single_authority.py` | split | **T018's AST single-authority sweep AND its non-vacuity control, verbatim.** It pins `Priivacy-ai/spec-kitty#2755` across all of `src/` independently of `batch.py`. Only T017 retires. |
| `test_batch_retry_hygiene.py` (6 nodes) | retire whole | name the survivor: `tests/delivery/test_ledger.py::test_batch_transient_does_not_flip_per_event_rejection` |
| `test_batch_400_no_details_poison_2736.py` (2) | retire whole | name the survivor: `tests/delivery/test_poison_batch_2736.py` — **and first confirm** `tests/delivery/test_receivers.py` actually pins the 400-*with*-details branch |

**Every retired node names either a surviving node id that pins the same requirement, or the argument
that the requirement died with the drain.** A retired node with neither is a rejected review.

**Operator decision, already taken:** `core/batch_partition.py::split_in_half` is **kept** as a
zero-consumer canonical leaf; a follow-up is filed in WP04. Do **not** fold it into this deletion.

### T007 — Delete, atomically

The 24 first-tier symbols, the 9 second-tier symbols, the orphaned imports, the retired test nodes, and
the `E15` entry from `tests/architectural/test_egress_consent_boundary.py` — **one commit**.

### T008 — Correct the ratchet baseline

`tests/architectural/_baselines.yaml` `egress_allowlist_files: 28` → **27**, and update its
justification prose (12 + 1 + 14 = 27).

**This reds nothing if you skip it.** The ratchet is shrink-only — growth fails, shrinkage merely warns —
so a stale count silently leaves the ceiling one free unconsented-egress file too high. That is exactly
the class of quiet drift this mission exists to close.

### T009 — Settle the two dispositions that must not be bulk-retired

**(a) `TestHistoricalMissionStateGuard` (`test_batch_sync.py:173`).** The per-event forbidden-key
check exists nowhere else. The live analogue `enforce_teamspace_mission_state_ready` is **entry-time**,
which a daemon-driven dispatch does not traverse. State whether the per-event check is still owed — and
**file the gap if it is**.

**(b) The 4 ingress tests at `test_batch_sync.py:1305-1413`.** They pin per-batch `/me` rehydrate and
negative-cache behaviour reachable only through `batch_sync`. If the claim is "covered at
`body_transport.py`", **check that claim**. Do not assert it.

### T010 — Verify the public API is untouched

Enumerate `specify_cli.sync`'s exported name set before and after; assert a **zero-name** delta
(`NFR-002`). The senders were already absent from the lazy map, so a correct deletion changes nothing.
**Print both set sizes** — a zero delta between two empty sets is not a result.

### T011 — Prove zero transmit primitives remain

Print the T002 baseline count and the post-change count. This is `SC-001`.

## Done when

- [ ] T005's absence assertion was red before T007 and is green after — both states quoted.
- [ ] **K is computed, not asserted.** At WP02's base commit and again after T007:
      `.venv/bin/python -m pytest tests/sync tests/architectural --collect-only -q -p no:cacheprovider > /tmp/nodes-{pre,post}.txt`,
      then `comm -23 <(sort -u /tmp/nodes-pre.txt) <(sort -u /tmp/nodes-post.txt) > /tmp/retired.txt; wc -l < /tmp/retired.txt`. **Quote K.**
- [ ] `contracts/deletion-manifest.md` has **one row per line of `/tmp/retired.txt`**, shaped
      `<retired node id> | SURVIVOR <node id> | DEATH <one sentence>`, and `grep -c '^| tests/'` on it **equals K** — both
      numbers quoted. A SURVIVOR value absent from `/tmp/nodes-post.txt`, or a DEATH sentence reused across rows, is a
      rejected review. **A bulk sentence covering many deletions is a rejected review.**
- [ ] The commit message body carries the same rows and states K (this is FR-004 / SC-004; the criterion is the
      commit message, so a manifest alone does not satisfy it).
- [ ] **Survivors checked mechanically, not by eye.** For each named survivor node id, `grep -qF "<id>" /tmp/nodes-post.txt`.
      Zero misses, and the per-file survivor counts printed next to T006's table numbers (2 / ~28 / 2 / 4).
- [ ] `tests/architectural/test_batch_split_single_authority.py`: `git diff` shows **only** T017's retirement, and T018's
      sweep plus its non-vacuity control are byte-identical — compare a sha of those two functions pre and post.
- [ ] `E15` removed and `_baselines.yaml` at 27, in the same commit as the deletion.
- [ ] `ruff check` clean on `sync/batch.py` (`ruff format` is NOT clean on this repo — do not run it).
- [ ] The public API delta is zero, with both set sizes printed.
- [ ] Zero transmit primitives remain, with baseline and final counts printed.
- [ ] T009's two questions answered in writing, with any gap **filed** rather than absorbed.

---

## Standing rules — these were each paid for. Do not paraphrase them.

**Measurement**
- *Never pipe a suite whose exit status you intend to trust.* Redirect, and quote the `N passed` line. An empty output file is no measurement.
- *A killed run is neither a pass nor a fail.* Re-run narrowed. Say you did. Do not explain it away.
- *Pin the interpreter:* `.venv/bin/python -m pytest`. Quote `sys.executable` **and** the `plugins:` header for anything load-bearing. `pytest-timeout` and `xdist` exist **only** in that venv.
- *Read the failure text, not the tally.*
- *Print the input count alongside any "all checks passed."* A gate that ran on zero files passes vacuously.
- *Red first* — and make the red **the consequence**, not a boolean.
- *Include a positive control that must pass.*
- *Any assertion of absence must establish why the thing would otherwise have happened.*
- *Control your diagnostic:* run any probe first against a case whose answer you already know.
- Use `-ra`, **not** `-rf`. `-rf` suppresses the error short-summary, which makes the standing `grep -c '^ERROR '` return 0 on a run that had errors. This actually happened on this mission.

**Concurrency**
- **Do not run `tests/sync` and `tests/cli` sessions concurrently.** They spawn real daemons and `pgrep`/port-scan; sibling sessions reap each other. 16 recorded false reds. This mission sweeps `tests/sync` and `tests/architectural` only — do not add `tests/cli`.
- `pgrep -af 'run_sync[_]daemon'` before every measurement. Leaked daemons on ports 9400-9402 contaminate the next one.
- **Put reaps in a script file**, where the command line is just `bash script.sh`. `pkill -f <pattern>` matches your own shell's command line and kills it — and so does `pgrep -f` in a script that greps for itself. The `[b]racket` trick is required in **both** forms. This bit a prior agent on this very mission.
- One live agent per file. The files this WP owns are listed in its frontmatter; do not touch another WP's.

**Git**
- **Explicit-path staging. `git add <paths>`, never `git add -A`.** Thirteen files were lost to one stray `add -A`.
- Commit via `spec-kitty safe-commit <paths> --to-branch feat/chain-b-consent-bypass-3167 -m "..."`.
- **`ruff format` is NOT clean on this repo** (`line-length = 164`). Only `ruff check` is meaningful.
- `git add` on an ignored file **silently does nothing** without `-f`. Confirm with `git status` that what you meant to stage is staged.

**Scope**
- **File follow-up issues for anything found out of scope rather than absorbing it.** That rule is what produced this mission; honour it again.
- Cite issues as `owner/repo#NNNN` for foreign issues and bare `#3167` for this mission's own. A bare `#NNNN` for a *foreign* issue in `spec.md`, `plan.md`, `research.md`, `analysis-report.md`, `tasks/*.md` or `contracts/*.md` mints a mandatory issue-matrix row this mission cannot resolve. Verify with `discover_issue_references(mission_dir)` — the multi-file API the merge gate actually calls — against a positive control.
- **A `len(x) == N` assertion in `tests/architectural/` trips the golden-count ratchet** (`test_golden_count_ban.py`). If the count genuinely *is* the contract, annotate `# golden-count: cardinality-is-contract` on the assertion's own physical line. **Do not re-freeze the baseline.**

**The disposition that matters more than any rule**

This mission exists because a gate carried a consent decision on a code path nobody calls, and because a
test fixture granted that gate `True` for every file whose name lacked one word. **A disclosed red beats
a manufactured green.** If the honest answer is "this is a real defect and the suite stays red until
someone fixes it", that is an acceptable deliverable. What is not acceptable is narrowing a watch set,
loosening a check, re-freezing a baseline, or pinning something unverified to get a green badge.

If you catch yourself about to report a number without having checked what it counts — stop. That is the
failure this whole programme is about.

---

## Where `contracts/` artifacts go

`contracts/*.md` and the other dossier files live under `kitty-specs/` and therefore **cannot appear in a
work package's `owned_files`** — the framework rejects it, and the commit router sends planning artifacts
to the mission's target branch on its own. Write them normally and commit them with `safe-commit`; they
are deliverables even though they are not owned files.

One consequence worth naming: the accept gate's `contracts/` check is satisfied by
`p.exists()`, so **`mkdir contracts` alone would pass it**. Put a real contract there. An empty directory
that satisfies a gate is the exact failure this mission exists to remove.
