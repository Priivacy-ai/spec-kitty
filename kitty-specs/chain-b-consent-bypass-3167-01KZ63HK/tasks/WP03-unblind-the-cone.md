---
work_package_id: WP03
title: Unblind the cone, then measure and attribute
dependencies:
- WP02
requirement_refs:
- FR-005
- FR-006
- NFR-003
- NFR-004
planning_base_branch: feat/chain-b-consent-bypass-3167
merge_target_branch: feat/chain-b-consent-bypass-3167
branch_strategy: Planning artifacts for this mission were generated on feat/chain-b-consent-bypass-3167.
  During /spec-kitty.implement this WP may branch from a dependency-specific base,
  but completed changes must merge back into feat/chain-b-consent-bypass-3167 unless
  the human explicitly redirects the landing branch.
subtasks:
- T012
- T013
- T014
- T015
- T016
phase: Phase 3 - Unblind and verify
history:
- at: '2026-08-04T10:30:00Z'
  actor: system
  action: Prompt generated from wps.yaml
agent_profile: python-pedro
authoritative_surface: tests/sync/conftest.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- tests/sync/conftest.py
- tests/sync/test_no_queue_drain_constructed_3030.py
- tests/sync/_leak_guard.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP03 – Unblind the cone, then measure and attribute

## ⚡ Do This First: Load Agent Profile

Load `python-pedro`.

## Goal

Stop the autouse fixture patching a name production no longer consults, make a mis-targeted patch fail
loudly instead of going inert, give the standing drain guard a positive control so its green keeps
meaning something, and attribute every change in the two swept cones.

## Why this WP is arguably the most valuable in the mission

`tests/sync/conftest.py`'s autouse fixture patched
`specify_cli.sync.batch.is_sync_enabled_for_checkout` to `True` for **every** `tests/sync` file
whose name lacked `"consent"` or `"capture_gate"`. That is **why the gate stayed broken and
uncovered** — a covering test written in its natural home was granted consent by the fixture and passed
regardless of the implementation. And it patches with `raising=False`, so after WP02 it goes **inert
with no error**.

## Subtasks

### T012 — Remove ONLY the `batch` seam

The fixture makes **three** patches. Be precise:

| Patch | Action |
|---|---|
| `specify_cli.sync.batch.is_sync_enabled_for_checkout` | **Remove.** The name no longer exists after WP02. |
| `specify_cli.sync.runtime.is_sync_enabled_for_checkout` | **Keep.** `C-001` keeps `runtime.py:106`, and `runtime.py:37` imports the name, so dropping its `raising=False` **resolves** rather than errors. |
| `EventEmitter._project_consents_to_capture` (`:284-287`, default `raising=True`) | **LEAVE COMPLETELY ALONE.** This is the grant the cone actually depends on. It is out of scope. `FR-006` is not licence over the whole block. |

The fixture is autouse over ~106 files, and removing the `batch` seam is a **behavioural no-op** for all
of them. If you observe otherwise, stop and report — that would mean something else depends on it.

### T013 — Negative control for the patch target

Add a control proving a **wrong** patch target now fails loudly rather than going inert.

`SC-005` as written only proves *resolvability*, not *consultation* — those differ, and a
resolvable-but-never-read name passes it. The control is what makes the criterion mean something.

### T014 — Give the drain guard a positive control

`tests/sync/test_no_queue_drain_constructed_3030.py` is an AST scan for imports/calls of
`batch_sync`/`sync_all_queued_events`. **Once those names do not exist, it passes for a reason that no
longer discriminates** — nothing can import a name that is gone. `NFR-004` promises the guarantee never
decreases; a vacuous green is a decrease.

- Add the positive control its sibling already has: a **synthetic source string** containing
  `from .batch import batch_sync` that the scanner must still flag.
- Remove the now-vacuous `_DEFINING_MODULE` self-exclusion — with the definitions gone, the carve-out
  leaves `batch.py` as the one file where re-adding a sender *plus* a caller is invisible to the gate.

**This, not the deletion, is the strengthening `NFR-004` promises.**

### T015 — Collection-level diff, pre/post

Capture `--collect-only -q` node-id lists for `tests/sync` and `tests/architectural`, before and
after, and diff them. ~126 nodes disappear, so the comparison must distinguish **ABSENT** from
**PRESENT-BUT-FLIPPED** — only the latter is interesting, and a bulk sentence hides it. Cheap (~2 min)
and it catches every collection-level change, which is where a deletion's differences actually land.

### T016 — Sweep once, attribute everything

```bash
pgrep -af 'run_sync[_]daemon'                    # BEFORE. Must be empty.
.venv/bin/python -m pytest tests/sync -n0 -ra -p no:cacheprovider --timeout=300 > /tmp/sync.txt 2>&1
tail -30 /tmp/sync.txt                           # quote the N passed line
```

**⚠️ The baseline is a DISTRIBUTION, not a number — corrected after WP02's review.** The committed
"5 errors" was `n=1` and **5 is the tail, not the mode**: a second measurer ran the base arm five times
and got errors `{5, 5, 6, 6, 6}`, the after arm three times and got `{6, 6, 7}`.

- **Baseline: 5–6 errors at `b0482a832^`, measured n=5.** A 6-error run is **not** a regression; a
  5-error run is **not** "the baseline". `passed` and `input` are the stable figures.
- **Compare by per-node-id set difference over ≥5 runs per arm.** Never by a scalar count. A scalar
  comparison here is attributing against noise, and this mission already made that mistake once.
- **Count `^ERROR tests/`, not `^ERROR `.** The plain form **over**-counts: a captured-log record at
  level ERROR (`ERROR specify_cli.sync.background:background.py:369 Refusing to start background
  sync…`) begins with `ERROR ` and made one 6-error run read as 7. And never `grep -c` on the
  `[FR-007 leak guard]` tag — the banner carries the same tag as the errors.
- **The volatile band is exactly one shape:** `live thread name='Thread-N' target=None`, produced by
  `_ChainedTimer` (`sync/daemon.py:687,:715,:745`) and `threading.Timer` (`sync/background.py:528`),
  attributed by `_leak_guard.py:737`'s `after − before` difference to whichever test spans the thread's
  lifetime. **The observer moves; the leak does not.** None of those producers is a file this mission
  owns, and this is filed as `Priivacy-ai/spec-kitty#3193`.
- **Already proven to fire in the volatile band at BOTH commits — do not re-investigate** without new
  evidence: `test_background.py::TestSingletonAccessor::{test_get_sync_service_returns_same_instance,
  test_reset_clears_singleton}`,
  `test_daemon_self_retirement.py::TestStartSelfCheckTick::test_returned_timer_thread_is_daemon`,
  `test_legacy_queue_guard_3030.py::TestARefusedStartLeavesNoDeadSingleton::test_get_sync_service_does_not_cache_a_service_that_failed_to_start`.
- **The stable floor at both commits is 5 nodes:** `test_daemon_self_retirement::TestRunSyncDaemonWiring`
  ×2, `test_dual_write_integration` ×2, and the `:371` pin's partial match.
- **Environment, paid for:** `/tmp` is a 7.8 G tmpfs and one sweep costs ~1.5–2 G of `pytest-of-*`;
  three retained generations truncate a run mid-write with a bogus `EXIT=1`. Wipe basetemp between runs
  and keep it on `/tmp` — `/home` reds 3 consent/routing nodes via the `.kittify` root-walk, `/var/tmp`
  reds ~1530. And `pkill -f` needs the bracket class **in argument position too**:
  `pkill -f 'pytest tests/sync'` matched the caller's own shell and killed it.

- The leak guard's banner carries the same `[FR-007 leak guard]` tag as its errors, so `grep -c` on
  the tag **conflates them** and makes a green run look red. Count `^ERROR ` lines instead — and use
  `-ra`, because `-rf` suppresses them.
- Expect the leak-guard observation set to move. Attribute **per node id**. If a pinned leak stops
  reproducing **as a consequence** of this change, un-pin it and record the attribution — the guard
  hard-fails on a pin whose leak stopped, so leaving it is not an option. **Do not opportunistically
  re-pin**, and do not remove a pin for any other reason.
- The three pins in files this mission's cone touches are `tests/sync/_leak_guard.py:420`, `:389`,
  `:395`. `:371` fires as an error **only in the full serial sweep** — in isolation it passes — and its
  observability is supplied by an unpinned leak in `tests/sync/test_dual_write_integration.py`, a file
  this mission does not own. Do not treat that as a regression.
- Write `contracts/cone-attribution.md`: the per-node-id delta with a cause for **every** difference.
  Unattributed differences block this WP.
- **Do not run `tests/cli`.** The file once thought affected there is prose-only.

## Done when

- [ ] Only the `batch` seam was removed; `_project_consents_to_capture` is byte-identical.
- [ ] **Negative control demonstrated by a recorded mutation.** Run it once against the deleted name and once against
      the live one; quote both `pytest <nodeid> -ra` tails — one `1 failed` whose text names the unresolvable attribute,
      one `1 passed` — then quote `git diff -- tests/sync/conftest.py` clean of the mutation.
- [ ] **Positive control demonstrated the same way.** Mutate the drain guard's flagging branch to `return []`; quote the
      `1 failed` naming the synthetic `from .batch import batch_sync` source that went unflagged; revert; quote
      `N passed` **and the scanned-file input count** from both runs; quote `git diff` empty.
      (Note: `scripts/check_patch_targets.py` resolves `patch("...")` strings in CI but its regex never matches
      `monkeypatch.setattr("...")`, so it does **not** cover this fixture — the control is not duplicating a gate.)
- [ ] `_DEFINING_MODULE` self-exclusion removed.
- [ ] `contracts/cone-attribution.md` carries **one row per node id** in the pre/post delta, shaped
      `<node id> | ABSENT|FLIPPED | <cause> | <subtask>`, with cause drawn from the **closed set**
      {`RETIRED-BY-T007`, `FIXTURE-UNBLIND-T012`, `GUARD-STRENGTHEN-T014`, `LEAK-PIN-T016`, `NOT-CAUSED-BY-THIS-MISSION`}.
      Row count **equals** the delta line count; both printed. A `NOT-CAUSED-BY-THIS-MISSION` row must quote the command
      reproducing the same result on WP02's base commit. **"All differences are due to the deletion" is a rejected review** —
      a cause covering a set must enumerate its node ids.
- [ ] Post totals stated against the baseline triple: `post = A passed / B skipped / C errors, input D` vs
      `baseline 2376 / 19 / 5, input 2395`, with `grep -c '^ERROR ' /tmp/sync.txt` quoted — never `grep -c` on the
      `[FR-007 leak guard]` tag, which conflates the banner with the errors and makes a green run look red.
- [ ] **C-006's residual is recorded in the code**, on the three `_PinnedLeak` entries at `tests/sync/_leak_guard.py:420`,
      `:442`, `:452`: the ordering constraint, `#3167`, and the do-not-re-pin rule. A residual recorded only in the
      dossier is not recorded — a successor opens `_leak_guard.py`, not this prompt.
- [ ] The `N passed` line is quoted from a redirected run, with the input count.
- [ ] `pgrep` clean before and after; no daemon left on 9400-9449.

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
