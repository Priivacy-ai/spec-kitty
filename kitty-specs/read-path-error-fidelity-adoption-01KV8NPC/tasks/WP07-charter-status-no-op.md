---
work_package_id: WP07
title: charter status side-effect-free + JSON-safe
dependencies: []
requirement_refs:
- FR-010
tracker_refs: []
planning_base_branch: feat/read-path-error-fidelity
merge_target_branch: feat/read-path-error-fidelity
branch_strategy: Planning artifacts for this mission were generated on feat/read-path-error-fidelity. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/read-path-error-fidelity unless the human explicitly redirects the landing branch.
subtasks:
- T032
- T033
- T034
agent: "claude:sonnet:reviewer-renata:reviewer"
shell_pid: "2305513"
history:
- 2026-06-16 created (/spec-kitty.tasks)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/charter/_status_collectors.py
create_intent:
- tests/specify_cli/cli/commands/charter/test_status_no_op.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/charter/_status_collectors.py
- tests/specify_cli/cli/commands/charter/test_status_no_op.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before doing anything else, load the implementer profile so identity, governance scope, and
boundaries are in force for this session:

```
/ad-hoc-profile-load python-pedro
```

Then read, in this order, so the fix is grounded in the canonical mission record (do NOT improvise
from memory):

- `kitty-specs/read-path-error-fidelity-adoption-01KV8NPC/spec.md` — FR-010, and the issue-matrix row
  for #1914 (read-path/status-read no-op slice ONLY — broader umbrella stays on its own track).
- `kitty-specs/read-path-error-fidelity-adoption-01KV8NPC/plan.md` — IC-07 (charter status
  side-effect-free + JSON-safe). IC-07 has **no dependency**, start anytime.
- `kitty-specs/read-path-error-fidelity-adoption-01KV8NPC/contracts/behavioral-contracts.md` — C-IC07.

## Objective

Make the `charter status` collectors **side-effect-free** (a read-only status command MUST NOT write
to the working tree) and emit **one normalized, JSON-serializable hash** (FR-010, C-IC07). This is
the #2-partial / #1914 no-op slice: today the status collectors call generation/freshness routines
that WRITE to disk while merely reporting status. Scope to the **read-path / status-read no-op slice
only** — the broader #1914 governed-op no-op umbrella stays on its own track (plan.md IC-07 Risks).

**C-001 — adopt, don't build.** Do NOT introduce a parallel status surface or a new hashing scheme.
Make the EXISTING collectors read-only and normalize the hash they already compute.

## Context

**The disease.** `_collect_charter_sync_status` (`src/specify_cli/cli/commands/charter/_status_collectors.py:28-104`)
is invoked by the read-only `charter status` path but performs **writes**:
- It calls `ensure_charter_bundle_fresh(repo_root)` (resolved via the package shim,
  `_status_collectors.py:32-36`) — a freshness routine that can regenerate/rewrite bundle files.
- It calls `GlossaryEntityPageRenderer(repo_root).generate_all()` (`:38-42`) which WRITES glossary
  entity pages to disk (wrapped in a swallow-and-log `except`).

Both are write side-effects executed inside a status read. A `charter status` run therefore mutates
the working tree (`git status` differs before/after), violating no-op-stability (FR-010, #1914) and
C-IC07. The collector also surfaces `current_hash` / `stored_hash` (`:94-95`) that must be one
**normalized, JSON-serializable** value (no raw bytes / non-serializable objects leaking into the
`--json` envelope).

**The fix shape.**
- For the **status read path**, do NOT call the writing routines. Read freshness/staleness without
  generating: compute or read the existing hash via the non-mutating primitive (`charter.hasher`'s
  `is_stale` is already non-mutating, `:52`); drop the `generate_all()` entity-page write and the
  `ensure_charter_bundle_fresh` WRITE from the status collector. If `charter status` genuinely needs
  a canonical root that `ensure_charter_bundle_fresh` currently provided as a by-product, derive it
  read-only (fall back to `repo_root` as the code already does at `:43-47`) — do not regenerate to
  obtain it.
- Emit **one normalized hash** that is JSON-serializable: a single canonical string field the
  `--json` body can serialize without custom encoders. Normalize `None`/empty consistently.
- Preserve the legacy patch-shim contract noted at `_status_collectors.py:22-25` only insofar as it
  does not reintroduce a write; if the shim's sole purpose was to reach the writing routine, the
  status path simply stops calling it.

**Scope discipline.** Touch ONLY the named `owned_files`. Do not expand into the broader #1914
governed-op no-op work, the charter generate/sync WRITE commands (those legitimately write), or other
collectors beyond what FR-010's status-read no-op requires.

**Engineering discipline (binding for every subtask):**
- **Function-over-form + verification-by-deletion.** The proof is observable: deleting the write
  calls from the status collector keeps `charter status` working and leaves `git status` unchanged.
- **TDD-first.** Write the failing no-op test (T032) before removing the writes (T033).
- **Topology-true fixtures — NO fabricated short ids.** Use a real initialized repo with a real
  charter bundle and a mission whose `meta.json` carries a **full 26-char ULID `mission_id`**. Do not
  hand-craft short slugs. Drive the actual `charter status` surface (real collector invocation), not
  a mock that hides the writes.
- **Quality gates.** New/changed code passes `ruff` + `mypy` with zero issues, complexity ≤ 15, NO
  suppressions (`# noqa`, `# type: ignore`, per-file ignores). Fix the code, not the gate (NFR-004).
  Note: the existing `# noqa: BLE001` at `:41` rides on a block being DELETED — do not preserve it.

## Subtasks

### T032 — TDD: charter status is side-effect-free + emits a JSON-safe hash [P]
1. Create `tests/specify_cli/cli/commands/charter/test_status_no_op.py`.
2. Build a real initialized repo with a charter bundle and a mission (full 26-char ULID
   `mission_id`). Snapshot the working tree (`git status --porcelain` + a recursive content/mtime
   hash of the charter/glossary output dirs) BEFORE running status.
3. Invoke the `charter status` collector path (the real `_collect_charter_sync_status` and the status
   command body, not a mock). Snapshot AFTER.
4. Assert: `git status --porcelain` is byte-identical before/after AND no new/modified files appear
   in the charter/glossary generated dirs (no `generate_all` write).
5. Assert: the emitted status dict's hash field is a single string and the full status payload
   round-trips through `json.dumps(...)` without error (JSON-serializable).
6. **Validation:** run against unmodified `_status_collectors.py` and confirm it FAILS (the working
   tree changes and/or the entity pages are written) — capture the failure so the green after T033 is
   trustworthy (live-evidence discipline).

### T033 — Make the status collectors side-effect-free [P]
1. In `_collect_charter_sync_status` (`_status_collectors.py:28-104`), remove the
   `GlossaryEntityPageRenderer(...).generate_all()` write (`:37-42`) and the
   `ensure_charter_bundle_fresh` WRITE invocation (`:32-36`) from the **status read path**.
2. Compute staleness/hash read-only via the existing non-mutating `is_stale(charter_path,
   metadata_path)` (`:52`); derive `canonical_root` read-only (the `repo_root` fallback at `:43-47`
   already exists) without regenerating.
3. Remove the now-dead `# noqa: BLE001` and any imports that become unused; keep
   `_collect_charter_sync_status` ≤ 15 complexity (extract a small read-only helper if needed).
4. **Validation:** T032 PASSES; `ruff check` + `mypy` clean on the file.

### T034 — Emit one normalized JSON-serializable hash [P]
1. Normalize the hash the status dict returns (`current_hash`/`stored_hash`, `:94-95`) to a single
   canonical string (consistent `None`/empty handling), JSON-serializable in the `--json` envelope.
2. Add a focused assertion in `test_status_no_op.py` that the normalized hash is a `str` (or `None`)
   and that the full payload `json.dumps` round-trips.
3. **Validation:** the JSON-safety assertions pass; full
   `pytest tests/specify_cli/cli/commands/charter/ -q` is green (no regression in existing charter
   status tests).

## Branch Strategy

Planning artifacts were generated on `feat/read-path-error-fidelity`. During `/spec-kitty.implement`
this WP may branch from a dependency-specific base, but completed changes merge back into
`feat/read-path-error-fidelity` unless the human explicitly redirects the landing branch. WP07 has
**no dependencies** and is immediately startable in parallel with WP06/WP08.

## Definition of Done

- [ ] `tests/specify_cli/cli/commands/charter/test_status_no_op.py` exists, authored TDD-first
      against a real repo+charter bundle fixture (full 26-char ULID); the TDD test **FAILED FIRST on
      HEAD** (the working tree changed / entity pages were written) and the **captured red is pasted
      into the Activity Log** (not a prose claim), flipping to green after the fix. The fixture MUST
      guarantee the writes would fire on HEAD (a glossary entity to render and/or a stale bundle) so
      the no-op green is falsifiable — an empty/fresh fixture greens vacuously.
- [ ] `charter status` is side-effect-free: `git status` is unchanged before/after a status run, and
      no charter/glossary generated files are written by the status path (FR-010, C-IC07).
- [ ] The status collector emits one normalized hash that is JSON-serializable (the `--json` payload
      `json.dumps` round-trips).
- [ ] No parallel status surface or new hashing scheme introduced (C-001); scope stays within the
      read-path/status-read no-op slice (broader #1914 untouched).
- [ ] Only `_status_collectors.py` and the new test changed; charter generate/sync WRITE commands are
      untouched (NFR-005).
- [ ] `ruff` + `mypy` clean on changed files; collector complexity ≤ 15; the dead `# noqa: BLE001`
      removed; no suppressions added (NFR-004).
- [ ] `pytest tests/specify_cli/cli/commands/charter/ -q` green.

## Risks / reviewer guidance

- **Do not break the writing commands.** Only the STATUS read path loses its writes. `charter
  generate`/`charter sync` legitimately call `ensure_charter_bundle_fresh` /
  `generate_all` — confirm those surfaces are unchanged.
- **Hidden write coupling.** `ensure_charter_bundle_fresh` was also the source of `canonical_root`
  here; the reviewer should confirm the read-only derivation produces the same root (the `repo_root`
  fallback) without regenerating — otherwise status could report against the wrong path.
- **Patch-shim fixtures.** Legacy tests patch
  `…charter.ensure_charter_bundle_fresh` (the shim at `:22-25`). Removing the status-path call must
  not break those fixtures for the generate/sync commands they actually target — run the full charter
  test module.
- **No-op proof must be real.** A mock-based test that stubs the renderer hides the write. Reviewer:
  confirm the test exercises the real collector and checks the actual working tree (`git status`),
  per NFR-002/C-IC07.

## Activity Log

- 2026-06-16 — WP prompt authored from plan.md IC-07, contracts C-IC07, and spec FR-010 (#2 partial /
  #1914 no-op slice). Awaiting implementation.
- 2026-06-16T20:11:08Z – claude:sonnet:python-pedro:implementer – shell_pid=2262648 – Assigned agent via action command
- 2026-06-16T20:20:48Z – user – shell_pid=2262648 – Moved to claimed
- 2026-06-16T20:20:53Z – user – shell_pid=2262648 – Moved to in_progress
- 2026-06-16T20:21:33Z – user – shell_pid=2262648 – Moved to claimed
- 2026-06-16T20:21:35Z – user – shell_pid=2262648 – Moved to in_progress
- 2026-06-16T20:22:01Z – claude:sonnet:python-pedro:implementer – shell_pid=2262648 – Ready: charter status no-op; removed ensure_charter_bundle_fresh + generate_all write calls from read path; is_stale used read-only; hashes are str (JSON-safe); captured-red confirmed 2 test failures on HEAD before fix, flipped to green after; ruff+mypy clean; 38/38 charter tests pass
- 2026-06-16T20:22:49Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=2305513 – Started review via action command
- 2026-06-16T20:27:41Z – user – shell_pid=2305513 – Review passed: side-effect-free confirmed (ensure_charter_bundle_fresh + generate_all removed from status read path); is_stale used read-only; hashes are str (JSON-safe); fixture is non-vacuous (stale hash + DRG glossary node); captured-red plausible and consistent with code evidence; 38/38 charter tests green; ruff+mypy clean on changed files; no suppressions added; scope bounded to owned files only
