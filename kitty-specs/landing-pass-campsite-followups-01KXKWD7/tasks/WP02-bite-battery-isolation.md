---
work_package_id: WP02
title: 'Bite-battery mutation isolation (#2673 + #2638)'
dependencies: []
requirement_refs:
- C-003
- C-006
- FR-005
- FR-006
- NFR-002
tracker_refs: []
planning_base_branch: feat/landing-pass-campsite-followups
merge_target_branch: feat/landing-pass-campsite-followups
branch_strategy: Planning artifacts for this mission were generated on feat/landing-pass-campsite-followups. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/landing-pass-campsite-followups unless the human explicitly redirects the landing branch.
subtasks:
- T010
- T011
- T012
- T013
phase: Phase 1 - Test isolation
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3768044"
shell_pid_created_at: "1784159197.68"
history:
- at: '2026-07-15T22:32:40Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- tests/architectural/test_single_mission_surface_resolver.py
- tests/architectural/test_surface_resolution_audit.py
- tests/architectural/untrusted_path_audit/audit.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP02 – Bite-battery mutation isolation (#2673 + #2638)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent status` or the Activity Log below).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Review Feedback

*[If this WP was returned from review, the reviewer feedback reference appears in the Activity Log below or in the status event log.]*

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`,````bash`

---

## Objectives & Success Criteria

**Objective:** Remove the shared-mutable-real-file hazard in the untrusted-path bite-battery so a concurrent `pytest-xdist` worker's scanner can never observe `src/specify_cli/core/mission_creation.py` mid-mutation. One change fixes **#2673 AND its duplicate #2638** (a second scanner victim). The battery MUST still prove that the untrusted-path audit detects an unsanctioned raw path-join.

**Success criteria:**

- The real `src/specify_cli/core/mission_creation.py` is **byte-unchanged** across the full run of `test_raw_join_bite_battery_new_unsanctioned_join_reds` — asserted structurally, not by a flaky repeated run.
- Both sibling scanners are immune to the injector's mutation window:
  - `test_untrusted_path_containment.py::test_all_discovered_rows_appear_in_inventory` (#2673)
  - `test_surface_resolution_audit.py::test_audit_passes_on_current_tree` (#2638)
- The bite-battery STILL asserts the audit flags the injected `_wp04_bite_witness` raw join through the real detector code path.
- Production `src/specify_cli/core/mission_creation.py` is **NOT** modified by this WP.
- A parallel smoke run of the three test files (`-n auto --dist loadfile`) is green `>=5x`.

## Context & Constraints

**RED-FIRST (C-005).** Land the failing structural assertion before the isolation fix.

**Root cause.** `_SourceMutation` (class definition ~line 822 in `tests/architectural/test_single_mission_surface_resolver.py`; the #2673 mutation CALL is at ~line 745 inside `test_raw_join_bite_battery_new_unsanctioned_join_reds`) writes `original + snippet` into the REAL `mission_creation.py` on disk, then restores it. Under `-n auto --dist loadfile`, a sibling worker running a root-scanning test invokes the same `discover_rows()` (in `tests/architectural/untrusted_path_audit/audit.py`, driven by the module-global `SRC_ROOT`) and reads the injected `_wp04_bite_witness` sink **mid-mutation** — producing a false RED. Two distinct scanners hit this:

- `test_untrusted_path_containment.py::test_all_discovered_rows_appear_in_inventory` (**#2673**)
- `test_surface_resolution_audit.py::test_audit_passes_on_current_tree` (**#2638**)

**CI-safe today.** The injector runs in shard_1 and the scanners in shard_2 — separate CI jobs — so this never reds CI. The flake is **LOCAL** under `-n auto`.

**Fix direction (Option (i), operator-plan).** Mutate an ISOLATED tmp copy of the target file (outside the scanned tree) and, for the mutation window, monkeypatch `audit.SRC_ROOT` (the module global) to that tmp root. `pytest-xdist` workers are separate PROCESSES, so a sibling scanner in another process keeps reading the never-mutated real tree — the monkeypatch is process-local and cannot leak across workers.

**⚠️ SHARP cross-mission contention (C-006).** `tests/architectural/test_single_mission_surface_resolver.py` (~1372 LOC) is the primary test surface of the shipped / in-flight resolver-seam mission. Keep the diff **tight and mid-file-localized** — do not reflow the file, do not renumber, do not restructure unrelated helpers. Touch only `_SourceMutation` and the single bite-battery test.

**Constraints:**

- `xdist_group` / `--dist loadgroup` is **NOT** an option — the repo mandates `--dist loadfile` (see `docs/guides/testing-parallel.md`).
- Do not weaken what the battery proves. Detection of the raw join must remain a real assertion.
- New code passes `ruff` and `mypy` clean; no blanket suppressions.

**References:** `research-notes-csf-2670.md`, plan IC-02.

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: {{planning_base_branch}}
- **Merge target branch**: {{merge_target_branch}}

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

## Subtasks & Detailed Guidance

### Subtask T010 (RED) – Structural byte-unchanged assertion for the real target file

- **Purpose**: Lock in a deterministic RED that captures the hazard: today, under concurrency, a sibling scanner can observe the mutation because the real file is briefly rewritten.
- **Steps**:
  1. In `tests/architectural/test_single_mission_surface_resolver.py`, add a structural assertion that the real `src/specify_cli/core/mission_creation.py` is byte-UNCHANGED after `test_raw_join_bite_battery_new_unsanctioned_join_reds` completes.
  2. Capture a hash (e.g. `hashlib.sha256` of the file bytes) of the real target file BEFORE the mutation is invoked, and assert the same hash AFTER the test body finishes (including the mutation's restore path).
  3. Prefer a deterministic structural check (hash before/after) over a flaky repeated-run reproduction. The point is: even the transient in-place rewrite is disallowed, because it is the transient window a sibling reads.
  4. Confirm this assertion is RED against the current `_SourceMutation` behavior (the current implementation writes the real file, so an assertion that the real file is *never rewritten during the window* will not hold until T011). If a plain before/after hash is equal because restore is exact, sharpen the assertion to observe the file is untouched *during* the mutation window (e.g. record file mtime/hash at the moment the mutation context is active, via the isolated-copy contract you will introduce in T011) — the assertion must fail against today's real-file mutation and pass once the mutation targets the tmp copy.
- **Files**: `tests/architectural/test_single_mission_surface_resolver.py`.
- **Parallel?**: No — same file as T011/T013.
- **Notes**: This is the PRIMARY gate (NFR-002). Keep it mid-file-localized near the existing bite-battery test.

### Subtask T011 – Isolate the mutation onto a tmp copy + monkeypatch `audit.SRC_ROOT`

- **Purpose**: Eliminate the shared-mutable-real-file hazard so the mutation is never visible on the scanned tree.
- **Steps**:
  1. Refactor `_SourceMutation` (class def ~line 822) — or add an isolated variant — so that instead of writing `original + snippet` into the real `mission_creation.py`, it:
     - copies the target file into a `tmp_path`-style isolated root **outside** the scanned tree,
     - injects the `_wp04_bite_witness` witness snippet into the COPY there,
     - monkeypatches `audit.SRC_ROOT` (the module global in `tests/architectural/untrusted_path_audit/audit.py`) to point at that tmp root for the mutation window,
     - restores `audit.SRC_ROOT` and cleans up the tmp root on exit (context-manager `__exit__` / `finally`).
  2. The real production `src/specify_cli/core/mission_creation.py` MUST NOT be modified at any point.
  3. If cleaner, add an optional `root` parameter to `discover_rows` / `composite_key_from_file` in `audit.py` (test-support only) and thread it through — BUT the module-global monkeypatch is sufficient and keeps production code paths untouched. Prefer the monkeypatch unless threading a param is clearly simpler; if you add the optional param it must default to `SRC_ROOT` so production callers are unchanged.
  4. Ensure the tmp root mirrors enough of the tree structure that `discover_rows()` produces a composite key for the injected copy (i.e. the witness file must be discoverable under the patched root exactly as it would be under the real root).
- **Files**: `tests/architectural/test_single_mission_surface_resolver.py` (mutation helper), `tests/architectural/untrusted_path_audit/audit.py` (only if threading the optional `root` param).
- **Parallel?**: No.
- **Notes**: Workers are separate PROCESSES — the monkeypatch is process-local and cannot leak to a sibling scanner. This is exactly why Option (i) works under `--dist loadfile`.

### Subtask T012 – Confirm the second scanner (#2638) is immune

- **Purpose**: Prove the one change fixes both duplicate reports.
- **Steps**:
  1. Confirm `test_surface_resolution_audit.py::test_audit_passes_on_current_tree` (#2638) uses the same `discover_rows()` / `SRC_ROOT` scanning path and is therefore immune once the mutation targets the tmp copy.
  2. If `test_surface_resolution_audit.py` has any assumption that would still read the real tree during the window, adjust coverage within the owned file to assert immunity explicitly (e.g. a focused test that the audit-on-current-tree result is stable regardless of an active bite mutation).
  3. Add or adjust coverage as needed strictly within owned files.
- **Files**: `tests/architectural/test_surface_resolution_audit.py`.
- **Parallel?**: No — shares the `audit.SRC_ROOT` contract.
- **Notes**: Do not duplicate the injector logic here; rely on the isolated mutation contract from T011.

### Subtask T013 – Prove the battery STILL detects the unsanctioned join + parallel smoke

- **Purpose**: Guard against a fix that silently stops proving detection.
- **Steps**:
  1. Confirm the bite-battery STILL asserts that the audit flags the injected `_wp04_bite_witness` raw join. Detection runs through the real detector code path, which is root-agnostic (it scans whatever `SRC_ROOT` points at) — so pointing it at the tmp copy still exercises the genuine detector, not a stub.
  2. Assert the detector returns the witness row / composite key for the injected copy, and that the assertion would FAIL if the witness snippet were absent (i.e. the battery is a live detector test, not a tautology).
  3. Run the parallel smoke and record the result:
     ```bash
     uv run pytest tests/architectural/test_single_mission_surface_resolver.py \
       tests/architectural/test_surface_resolution_audit.py \
       tests/architectural/test_untrusted_path_containment.py \
       -n auto --dist loadfile -q
     ```
     Confirm green `>=5x` (repeat the command, or loop it) and note the count in the Activity Log.
- **Files**: `tests/architectural/test_single_mission_surface_resolver.py`, `tests/architectural/test_surface_resolution_audit.py`, `tests/architectural/test_untrusted_path_containment.py` (read-only for the smoke; no edits unless immunity coverage requires it).
- **Parallel?**: No.
- **Notes**: The parallel smoke is SECONDARY evidence; the structural byte-unchanged assertion (T010) is the primary gate.

## Test Strategy

- **Primary gate (NFR-002):** the structural byte-unchanged assertion from T010 — deterministic, not concurrency-dependent.
- **Secondary smoke:** the repeated `-n auto --dist loadfile` run over the three files, green `>=5x`.
- Run the focused files first, then the smoke:
  ```bash
  uv run pytest tests/architectural/test_single_mission_surface_resolver.py -q
  uv run pytest tests/architectural/test_single_mission_surface_resolver.py \
    tests/architectural/test_surface_resolution_audit.py \
    tests/architectural/test_untrusted_path_containment.py \
    -n auto --dist loadfile -q   # repeat >=5x
  ```
- `ruff check tests/architectural/` and `mypy` on touched files must be clean.

## Risks & Mitigations

- **Risk: weakening what the battery proves.** Mitigation — T013 explicitly re-asserts detection through the real detector against the injected witness, and asserts absence-of-witness would fail.
- **Risk: `xdist_group` / `--dist loadgroup` temptation.** Mitigation — prohibited; the repo mandates `--dist loadfile`. The process-local monkeypatch is the sanctioned fix.
- **Risk: cross-mission churn in the ~1372-LOC resolver-seam file (C-006).** Mitigation — keep the diff tight and mid-file-localized; touch only `_SourceMutation` and the single bite-battery test; no reflow/renumber.
- **Risk: production `mission_creation.py` accidentally modified.** Mitigation — the whole point of the tmp copy; T010's byte-unchanged assertion catches any regression.
- **Risk: tmp root missing tree structure so `discover_rows()` skips the witness.** Mitigation — mirror enough of the path layout that the composite key resolves identically under the patched root.

## Review Guidance

- Verify production `src/specify_cli/core/mission_creation.py` is untouched by the diff.
- Verify both scanners (#2673 and #2638) are immune — the mutation targets a tmp copy, and `audit.SRC_ROOT` is monkeypatched process-locally then restored.
- Verify the battery STILL asserts detection of the injected `_wp04_bite_witness` raw join through the real detector.
- Verify the structural byte-unchanged assertion (T010) is present and is the primary gate; confirm the parallel smoke was run `>=5x` green.
- Verify the diff is tight and mid-file-localized in the ~1372-LOC resolver-seam file (C-006); no reflow, no renumber, no unrelated helper churn.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

### How to Add Activity Log Entries

**When adding an entry**:

1. Scroll to the bottom of this Activity Log section
2. **APPEND the new entry at the END** (do NOT prepend or insert in middle)
3. Use exact format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`
4. Timestamp MUST be current time in UTC (check with `date -u "+%Y-%m-%dT%H:%M:%SZ"`)
5. Agent ID should identify who made the change (claude-sonnet-4-5, codex, etc.)

**Format**:

```
- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <brief action description>
```

**Example (correct chronological order)**:

```
- 2026-01-12T10:00:00Z – system – Prompt created
- 2026-01-12T10:30:00Z – claude – Started implementation
- 2026-01-12T11:00:00Z – codex – Implementation complete, ready for review
- 2026-01-12T11:30:00Z – claude – Review passed, all tests passing  ← LATEST (at bottom)
```

**Common mistakes (DO NOT DO THIS)**:

- Adding new entry at the top (breaks chronological order)
- Using future timestamps (causes acceptance validation to fail)
- Inserting in middle instead of appending to end

**Why this matters**: The acceptance system reads the LAST activity log entry as the current state. If entries are out of order, acceptance will fail even when the work is complete.

**Initial entry**:

- 2026-07-15T22:32:40Z – system – Prompt created.

---

### Updating Status

Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task <WPID> --to <status>` to change WP status.

### Optional Phase Subdirectories

For large features, organize prompts under `tasks/` to keep bundles grouped while maintaining lexical ordering.
- 2026-07-15T23:16:51Z – claude:sonnet:python-pedro:implementer – shell_pid=3622117 – Assigned agent via action command
- 2026-07-15T23:46:12Z – claude:sonnet:python-pedro:implementer – shell_pid=3622117 – bite-battery mutation isolated to tmp copy; both scanners immune; battery still proves detection
- 2026-07-15T23:46:41Z – claude:opus:reviewer-renata:reviewer – shell_pid=3768044 – Started review via action command
