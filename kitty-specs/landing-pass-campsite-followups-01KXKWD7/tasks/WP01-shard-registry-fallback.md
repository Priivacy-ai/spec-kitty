---
work_package_id: WP01
title: Shard-registry default fallback + doctrine header (#2671)
dependencies: []
requirement_refs:
- C-002
- C-008
- FR-001
- FR-002
- FR-003
- FR-004
- FR-011
- NFR-001
- NFR-006
tracker_refs: []
planning_base_branch: feat/landing-pass-campsite-followups
merge_target_branch: feat/landing-pass-campsite-followups
branch_strategy: Planning artifacts for this mission were generated on feat/landing-pass-campsite-followups. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/landing-pass-campsite-followups unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 1 - Test-infra enabler
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3810609"
shell_pid_created_at: "1784160240.79"
history:
- at: '2026-07-15T22:32:40Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/_shard_registry.py
create_intent:
- tests/test_shard_registry_fallback.py
execution_mode: code_change
model: ''
owned_files:
- tests/_shard_registry.py
- tests/_arch_shard_map.py
- tests/test_shard_registry_fallback.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Shard-registry default fallback + doctrine header (#2671)

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

Stop `main` from going red whenever a contributor adds a new `tests/architectural/*.py`
file without hand-editing the shard-assignment table in `tests/_arch_shard_map.py`.
This is issue **#2671** (Direction A, operator-chosen). It is a **SOFT ENABLER** — it
lands first in this mission so the follow-up campsite work builds on the fixed seam.

Concretely, this WP:

- Adds a **per-group opt-in** default-shard fallback so that an *unregistered*
  under-root arch file is automatically assigned a deterministic shard (auto-cover),
  instead of resolving to `None` and slipping through the collection hook unmarked.
- Keeps **explicit assignments winning** — `dir_assignment` / `file_assignment`
  entries are checked first and are unchanged.
- **Preserves the GC-1 union invariant** as the correctness net (the completeness
  guard still proves the partition is total).

**Success criteria (all must hold):**

1. A throwaway new `tests/architectural/*.py` file receives **exactly one**
   `arch_shard_N` marker via the collection hook (GC-1 completeness passes) and is
   **not** a zero-gate orphan (`tests/architectural/test_gate_coverage.py::test_no_new_orphan_surfaces`
   passes).
2. The fallback fires **only** when a group opts in (`default_fallback=True`) **and**
   the path is under one of that group's `roots`. Out-of-root paths still resolve to
   `None`. The `next` group (not opted in) still returns `None` for unregistered paths.
3. Fallback assignment is **deterministic** (same path → same shard) and spreads by
   hash-bucket (NOT "pile everything on the lightest shard").
4. Explicit `file_assignment` / `dir_assignment` entries resolve exactly as before.
5. New tests in `tests/test_shard_registry_fallback.py` cover every branch above and
   are RED-first (see Test Strategy).

## Context & Constraints

- **Issue**: #2671. Operator chose **Direction A** (additive default-fallback), not
  a scripted "regenerate the table" approach.
- **The seam** is `tests/_shard_registry.py` → `ShardRegistry.shard_for()`. Today it
  returns `None` for any under-root file that is not in `file_assignment`
  (or matched by a `dir_assignment` prefix). Downstream:
  - `tests/conftest.py`'s `pytest_collection_modifyitems` hook then applies **no**
    `arch_shard_N` marker to that file, and
  - the GC-1 completeness gate `tests/architectural/test_arch_shard_marker_completeness.py`
    **and** `tests/architectural/test_gate_coverage.py::test_no_new_orphan_surfaces`
    both go red.
- **This gap has recurred 3+ times.** The most recent instance shipped in commit
  `27eed6c9f` and had to be hand-patched by appending the new file to
  `_ARCH_SHARD_N_FILES`. The header comments in `tests/_arch_shard_map.py` are full
  of "Added post-data-model.md ... landing gap ... main went red" annotations that
  document exactly this failure mode.
- **Charter constraints:**
  - **RED-FIRST (charter C-005):** the failing test lands and is observed red before
    the fix.
  - **Fix, don't suppress:** do NOT weaken or skip either gate to make main green.
  - **Additive:** do **NOT** replace the manual bin-packing table. The explicit
    216/215/215 split stays authoritative; the fallback is a safety net that only
    catches files nobody registered yet.
- **Supporting docs**: `.kittify/charter/charter.md`;
  `kitty-specs/landing-pass-campsite-followups-01KXKWD7/plan.md` (IC-01);
  `kitty-specs/landing-pass-campsite-followups-01KXKWD7/tasks.md`;
  `research-notes-csf-2670.md`. FR reference: **FR-011** (the doctrine header rewrite).

**Current seam shape (for orientation, do not paste blindly):**

```python
# tests/_shard_registry.py — ShardGroup is a frozen dataclass with:
#   group, roots, shard_count, marker_prefix, dir_assignment, file_assignment
# shard_for(group, relpath) ends with:
#     for dirpath, shard in spec.dir_assignment.items():
#         if normalized == dirpath or normalized.startswith(f"{dirpath}/"):
#             return shard
#     return spec.file_assignment.get(normalized)   # <-- the miss returns None today
```

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: {{planning_base_branch}}
- **Merge target branch**: {{merge_target_branch}}

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

## Subtasks & Detailed Guidance

### Subtask T001 – RED: failing test documenting the gap, then the fix

- **Purpose**: Satisfy charter C-005 — land a test that is red against today's seam
  and turns green only once the fallback exists.
- **Steps**:
  1. Create the NEW file `tests/test_shard_registry_fallback.py`.
  2. Construct a `ShardRegistry()` in-test and `register()` an **arch-like** group
     (e.g. `group="arch_like"`, `roots=("tests/architectural",)`, `shard_count=3`,
     `marker_prefix="arch_shard"`, a small explicit `file_assignment`, and
     `default_fallback=True`).
  3. Assert that an **unregistered under-root** file (e.g.
     `"tests/architectural/test_brand_new_guard.py"`) — which resolves to `None`
     against the *current* code — resolves to a **valid shard in `1..shard_count`**
     after the fix. (Write the assertion for the post-fix behavior; observe it RED
     first, then green after T002/T003.)
  4. Assert an **out-of-root** path (e.g. `"src/specify_cli/foo.py"`) stays `None`
     even with `default_fallback=True`.
  5. Assert an **explicit** `file_assignment` entry still wins (returns its declared
     shard, not a hash bucket).
- **Files**: `tests/test_shard_registry_fallback.py` (create).
- **Parallel?**: No — this is the gating RED test; T002/T003 turn it green.
- **Notes**: Run and *observe the red* before writing the fix. Capture the failure
  in the Activity Log (charter red-first discipline).

### Subtask T002 – Add `default_fallback` field to `ShardGroup`

- **Purpose**: Let a group opt in to auto-cover without changing any existing
  construction site.
- **Steps**:
  1. In `tests/_shard_registry.py`, add an optional field to the `@dataclass(frozen=True)`
     `ShardGroup`: `default_fallback: bool = False`.
  2. Place it after the existing fields so every current positional/keyword
     construction remains valid; the default `False` keeps `next` and every other
     caller behaviorally identical.
  3. Update the class docstring to name the new field and its meaning (opt-in
     auto-cover for under-root files with no explicit assignment).
- **Files**: `tests/_shard_registry.py`.
- **Parallel?**: Can be done alongside T003 (same file, one edit pass).
- **Notes**: Frozen dataclass — the field must have a default so existing
  `ShardGroup(...)` calls that omit it still construct. Do NOT reorder existing fields.

### Subtask T003 – Add the opt-in, root-gated, hash-bucket fallback branch to `shard_for()`

- **Purpose**: The behavioral heart of the fix.
- **Steps**:
  1. In `ShardRegistry.shard_for()`, keep the existing lookup order intact:
     `dir_assignment` prefix scan first, then `file_assignment.get(normalized)`.
  2. Capture the `file_assignment` result; on a **miss** (`None`), add a branch:
     - **Only** if `spec.default_fallback` is `True`, **and**
     - the path is **under one of the group's `roots`** (gate on root membership —
       reuse the same `normalized == root or normalized.startswith(f"{root}/")`
       shape used for `dir_assignment`), then
     - return a **deterministic hash-bucket** shard:
       ```python
       return int(hashlib.sha1(normalized.encode()).hexdigest(), 16) % spec.shard_count + 1
       ```
  3. Otherwise return `None` (unchanged behavior: not opted in, or out of root).
  4. Add `import hashlib` at the top of the module.
- **Files**: `tests/_shard_registry.py`.
- **Parallel?**: Pairs with T002 in one edit.
- **Notes**:
  - **Do NOT use "lightest shard"** — that piles every unregistered file onto one
    shard and re-creates imbalance. Hash-modulo spreads them.
  - **Root membership is a hard gate** — never assign a shard to a file that is not
    under the group's roots. This is what keeps the collection hook scoped and keeps
    the `next` group (and any non-arch surface) untouched.
  - Explicit `file_assignment` / `dir_assignment` entries are checked **before** the
    fallback and therefore still win.
  - Keep `sha1` usage as a non-cryptographic bucket hash; if a lint hotspot flags it,
    add a narrow inline rationale (deterministic sharding, not security) rather than
    suppressing broadly — but prefer leaving it clean.

### Subtask T004 – Opt the `arch` group in + rewrite the load-bearing doctrine header

- **Purpose**: Turn on auto-cover for the real `arch` group and update the
  now-stale instructions (FR-011).
- **Steps**:
  1. In `tests/_arch_shard_map.py`, set `default_fallback=True` on the `arch`
     `ShardGroup(...)` passed to `register(...)` at the bottom of the module.
  2. **Do NOT** opt the `next` group in — leave `tests/_next_shard_map.py`
     unaffected (it keeps `default_fallback=False` by omission).
  3. Rewrite the module docstring / load-bearing header comments that currently
     instruct maintainers to "manually append to `_ARCH_SHARD_N_FILES`". Replace
     that guidance with the new model:
     - New `tests/architectural/*.py` files are **auto-covered** by the default
       fallback (deterministic hash bucket) — no manual edit is required just to keep
       main green.
     - The explicit `_ARCH_SHARD_N_FILES` table remains the **authoritative balance
       control**: add a file there only when you want to pin it to a specific shard
       for balance; explicit entries still override the fallback.
     - Reference **FR-011** and issue **#2671** so the provenance is traceable.
  4. Leave the existing explicit table entries **exactly as-is** — this is additive.
- **Files**: `tests/_arch_shard_map.py`.
- **Parallel?**: No — depends on T002/T003 (the field and branch must exist first).
- **Notes**: The header is genuinely load-bearing (it is the instruction future
  contributors read after a red main). Make it unambiguous that manual appends are now
  a *balance* decision, not a *keep-green* obligation.

### Subtask T005 – Verify end-to-end (both gates green, invariants held)

- **Purpose**: Prove the enabler works against the real gates, not just the unit test.
- **Steps**:
  1. Create a throwaway `tests/architectural/test_zz_fallback_probe.py` with a single
     trivial `def test_probe(): assert True`. Collect and confirm it receives
     **exactly one** `arch_shard_N` marker.
  2. Run the GC-1 completeness gate and the gate-coverage orphan gate — both must be
     green with the probe present:
     ```bash
     uv run pytest tests/architectural/test_arch_shard_marker_completeness.py \
       tests/architectural/test_gate_coverage.py -q
     ```
  3. Confirm explicit entries are unchanged (a known `file_assignment` file still maps
     to its declared shard) and the **GC-1 union invariant** still holds as the
     correctness net.
  4. **Delete the throwaway probe file** before finishing — it is verification
     scaffolding, not a deliverable.
- **Files**: none permanent (temporary probe only).
- **Parallel?**: No — final gate.
- **Notes**: If the probe lands on a shard the gate does not expect, re-check the
  root-membership gate and the `shard_count` modulo (`% shard_count + 1` yields
  `1..shard_count`).

## Test Strategy (include only when tests are required)

`tests/test_shard_registry_fallback.py` (new, owned) MUST cover:

- **Opt-in gating**: fallback fires only when `default_fallback=True`.
- **Root gating**: fallback fires only for under-root paths; out-of-root → `None`.
- **Determinism**: same relpath → same shard across repeated calls.
- **Range**: returned shard is within `1..shard_count`.
- **Explicit-wins**: a `file_assignment` entry returns its declared shard, not a
  hash bucket.
- **`next`-group parity**: a group with `default_fallback=False` (as `next` is)
  returns `None` for an unregistered under-root path.

Commands:

```bash
# Focused unit + both real gates:
uv run pytest tests/test_shard_registry_fallback.py \
  tests/architectural/test_arch_shard_marker_completeness.py \
  tests/architectural/test_gate_coverage.py -q
```

RED-first: run `tests/test_shard_registry_fallback.py` **before** T002/T003 and record
the failure, then implement and re-run to green.

## Risks & Mitigations

- **Shared seam consumed by both `arch` and `next`.** A change to `shard_for()`
  affects both. *Mitigation*: the fallback is **per-group opt-in** — only `arch` sets
  `default_fallback=True`; `next` is untouched, and a regression test pins that.
- **Over-broad assignment.** A fallback that ignored roots could mark files outside the
  pole roots and break the collection hook's scoping. *Mitigation*: **hard root-membership
  gate** before returning any fallback shard.
- **Imbalance.** A "lightest shard" fallback would pile all unregistered files on one
  leg. *Mitigation*: **hash-modulo bucket**, deterministic and spread.
- **Silently weakening a gate.** *Mitigation*: neither gate is modified; the GC-1 union
  invariant is retained as the correctness net and re-run in T005.

## Review Guidance

- Confirm the **GC-1 union invariant is retained** — the completeness guard still proves
  the partition is total; no gate was weakened or skipped.
- Confirm the fallback is **opt-in** (`default_fallback` defaults `False`) and
  **root-gated**, and that `next` still returns `None` for unregistered paths.
- Confirm the fallback is **hash-bucket** (deterministic, spread), not lightest-shard.
- Confirm **explicit entries still win** and the existing `_ARCH_SHARD_N_FILES` table is
  unchanged (additive, not a replacement).
- Confirm the **doctrine header** was rewritten to the automatic-default + explicit-override
  model (FR-011) and no longer instructs "manually append to keep green".
- Confirm the new tests exercise every branch and were RED-first.

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
- 2026-07-15T23:16:34Z – claude:sonnet:python-pedro:implementer – shell_pid=3619985 – Assigned agent via action command
- 2026-07-16T00:03:16Z – claude:sonnet:python-pedro:implementer – shell_pid=3619985 – shard fallback + doctrine header; gates green (45 passed)
- 2026-07-16T00:04:03Z – claude:opus:reviewer-renata:reviewer – shell_pid=3810609 – Started review via action command
