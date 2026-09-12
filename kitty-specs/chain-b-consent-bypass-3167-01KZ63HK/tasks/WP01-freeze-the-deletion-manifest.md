---
work_package_id: WP01
title: Freeze the deletion manifest
dependencies: []
requirement_refs:
- FR-002
- NFR-001
- NFR-002
planning_base_branch: feat/chain-b-consent-bypass-3167
merge_target_branch: feat/chain-b-consent-bypass-3167
branch_strategy: Planning artifacts for this mission were generated on feat/chain-b-consent-bypass-3167. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/chain-b-consent-bypass-3167 unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
phase: Phase 1 - Establish the contract
history:
- at: '2026-08-04T10:30:00Z'
  actor: system
  action: Prompt generated from wps.yaml
agent_profile: python-pedro
authoritative_surface: scripts/verify_batch_retirement_3167.py
create_intent:
- scripts/verify_batch_retirement_3167.py
execution_mode: code_change
model: ''
owned_files:
- scripts/verify_batch_retirement_3167.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP01 – Freeze the deletion manifest

## ⚡ Do This First: Load Agent Profile

Load `python-pedro` and behave per its guidance before parsing the rest of this prompt.

## Goal

Turn "the senders have no callers" from a claim into a **committed, re-runnable artifact**, so the
deletion in WP02 is reviewed against a frozen list rather than re-derived by every reader.

You are writing an artifact. **You change no source and no test in this WP.**

## Why this WP exists

The first attempt at this manifest used `git grep -w <bare name>` and got two buckets wrong in
opposite directions:

- `_sleep_before_final_sync_retry` was filed as a deletion candidate although `batch.py:684` and
  `:700` call it on the live `run_final_sync_with_retries` chain that `sync/background.py:467`
  drives. Deleting it breaks a production daemon path.
- `_current_team_slug` and `_body_mentions_missing_private_team` were filed as production-alive on
  the strength of hits that are **different symbols entirely** — `EventEmitter._current_team_slug` at
  `sync/emitter.py:870`, and `body_transport.py`'s own definition.

A bare grep cannot tell a call from a comment, nor this module's symbol from another module's
same-named one. `scripts/verify_batch_retirement_3167.py` (**staged, not yet in HEAD — commit it as step zero of T001**) resolves references module-qualified and
classifies each as `CODE` / `STR-TARGET` / `PROSE`.

## Subtasks

### T001 — Run the closure, and control its diagnostic FIRST

```bash
.venv/bin/python scripts/verify_batch_retirement_3167.py
```

**Before trusting any tier**, confirm the known production consumers resolve:
`run_final_sync_with_retries`, `BatchEventResult`, `BatchSyncResult` → `src/specify_cli/sync/background.py`;
`categorize_error` → `src/specify_cli/sync/diagnose.py`. If any comes back with **no** production
reference, **the resolver is broken, not the code dead** — fix the resolver and re-run. This control
already caught one real bug: the first version missed the relative `from .batch import` form and
reported every sibling-module consumer as unreferenced.

Expected: `dead=33 (first=24 second=9)  alive=21`, 7 code-coupled and 19 prose-only test files.

### T002 — Define "sender" and compute the NFR-001 baseline

`NFR-001` and `SC-001` require a count going to zero *from a stated baseline*. Define a sender as
**a top-level symbol in `sync/batch.py` from which a `requests.*` or
`request_with_stdlib_fallback_sync` call is transitively reachable**, compute that count now, and
record it. Without the starting number, "goes to zero" is unverifiable.

Known transmit primitives: `requests.get` at `:223`, `requests.post` at `:1125`,
`request_with_stdlib_fallback_sync` at `:1212` and `:1282`.

### T003 — Establish non-reachability beyond static callers

Static absence of callers does not cover dynamic reach. Check and record: `[project.scripts]` in
`pyproject.toml` (sole entry point is `spec-kitty = "specify_cli:main"`), `getattr` /
`importlib` / `__getattr__` on either sender name, and `specify_cli.sync`'s lazy-import map.

**State why a caller would otherwise have appeared.** An assertion of absence needs that, or it is an
impression with a command attached.

### T004 — Write `contracts/deletion-manifest.md`

The frozen artifact review checks WP02 against. It must contain:

1. The tier table — 24 first, 9 second, 21 alive — with **per-symbol referrer sets**, so a
   name-collision error is visible rather than buried.
2. The orphaned module-level imports (`ruff check` F401 will name them: `gzip`, `requests`,
   `urlparse`, `OfflineQueue`, `batch_partition`, `validate_outbound_payload`, and others).
3. The 7 code-coupled test files, and the 19 prose-only ones listed separately.
4. The T002 baseline sender count.
5. The T003 reachability argument.
6. **The NFR-002 exported-name baseline, frozen here** so WP02's T010 diffs against a fixed list rather than one it
   re-derives itself:
   `.venv/bin/python -c "import specify_cli.sync as s; ns=sorted(set(dir(s))|set(getattr(s,'__all__',[]))); print(len(ns)); print(chr(10).join(ns))"`
7. **The 13 files still carrying ambiguous "the drain" prose**, enumerated — WP04's FR-009 residual issue cannot be
   written without that list, and "emitter.py alone has 11" is not a list.

## Done when

- [ ] **The control is self-verifying, not self-reported.** This WP *owns* the script and `main()` only prints, so
      editing `SEEDS` or `_classify_external` reproduces the expected totals exactly. Therefore:
      (a) `sha256sum scripts/verify_batch_retirement_3167.py` quoted in the manifest; any change during this WP quoted as
          a full `git diff` with the resolver bug named.
      (b) **Injection control** — append `from .batch import batch_sync` + a use to `src/specify_cli/sync/diagnose.py`,
          re-run, and quote `batch_sync` leaving FIRST TIER. Restore, re-run, quote the expected totals. A resolver blind
          to an injected caller cannot certify absence.
      (c) **Deletion control** — temporarily drop `sync/background.py`'s `from .batch import` line, re-run, quote
          `run_final_sync_with_retries` flipping ALIVE → dead, restore. If it does not flip, the ALIVE tier is vacuous.
- [ ] `contracts/deletion-manifest.md` exists with all five sections, committed.
- [ ] The NFR-001 baseline sender count is stated as a number.
- [ ] The reachability argument establishes why a caller would otherwise have appeared.
- [ ] No source or test file was modified by this WP — `git status` confirms it.

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
