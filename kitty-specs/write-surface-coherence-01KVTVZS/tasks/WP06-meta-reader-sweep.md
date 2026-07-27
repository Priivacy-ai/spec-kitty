---
work_package_id: WP06
title: Meta-reader sweep (in-mission)
dependencies:
- WP05
requirement_refs:
- FR-009
tracker_refs: []
planning_base_branch: feat/write-surface-coherence
merge_target_branch: feat/write-surface-coherence
branch_strategy: Planning artifacts for this mission were generated on feat/write-surface-coherence. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/write-surface-coherence unless the human explicitly redirects the landing branch.
subtasks:
- T024
- T025
- T026
phase: Phase 4 - Canonical meta authority
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3013827"
history:
- at: '2026-06-23T19:28:09Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/task_utils/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/agent/mission.py
- src/specify_cli/task_utils/support.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP06 – Meta-reader sweep (in-mission)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter
**before parsing the rest of this prompt**, and behave according to its guidance.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If the profile cannot be loaded, run `spec-kitty agent profile list` and select the
best match for `task_type: implement` on `authoritative_surface: src/specify_cli/task_utils/`.

---

## Objective

Route the inline `json.loads(meta…read_text())` reads in the modules **this mission
touches** (`agent/mission.py`) through the canonical `load_meta` authority
(`mission_metadata.py`), and **name/reconcile** the duplicate `load_meta` at
`task_utils/support.py:363` (FR-009 / SC-004). Keep strictly to in-mission sites — the
remaining ~53-site #2100 backlog stays deferred (research D-6).

## Context & Constraints

Ground truth: [spec.md](../spec.md) FR-009, SC-004; [plan.md](../plan.md) IC-05;
[research.md](../research.md) D-6.

Verified inline meta reads in `mission.py` (the in-mission set, ≈3):
- `mission.py:442` — `data = json.loads(meta_file.read_text(encoding="utf-8"))`.
- `mission.py:1647` — `meta_data = json.loads(meta_file.read_text(encoding="utf-8"))`.
- `mission.py:3487` — `meta = json.loads(meta_path.read_text(encoding="utf-8"))`.

Canonical authority: `specify_cli.mission_metadata.load_meta` (the `load_meta` family:
`load_meta`/`load_meta_strict`/`load_meta_or_empty`; takes the feature **dir**, has
`allow_missing` / `on_malformed` knobs). Already consumed widely (e.g.
`resolution.py:372/381`, `commit_router.py:274`).

Duplicate: `task_utils/support.py:363` `load_meta(meta_path: Path)` — takes the meta
**file path** (not the dir) and delegates to `_load_meta_canonical` (the canonical reader)
already. It is a path-taking SHIM with a different signature, exported in `__all__`
(`support.py:439`).

## Branch Strategy

- **Strategy**: `shared-lane`
- **Planning base branch**: `feat/write-surface-coherence`
- **Merge target branch**: `feat/write-surface-coherence`

> Overlaps `mission.py` with WP02/WP03/WP05; serialized by WP05→WP06.

## Subtasks & Detailed Guidance

### Subtask T024 – Route the ~3 inline meta reads through canonical `load_meta`

- **Files**: `mission.py:442`, `:1647`, `:3487`.
- **Steps**:
  1. For each site, replace `json.loads(<path>.read_text(...))` with
     `load_meta(<feature_dir>, allow_missing=..., on_malformed=...)` from
     `specify_cli.mission_metadata`. Determine the feature **dir** from the existing
     `meta_file`/`meta_path` variable (`meta_path.parent` where the variable is the file).
  2. Preserve the local error/degrade behavior at each site: if the surrounding code
     tolerates a missing/malformed meta, pass `allow_missing=True` / `on_malformed="none"`;
     if it expects a present, well-formed meta, use `on_malformed="raise"` and keep the
     existing try/except shape. Read ±15 lines around each site to match the contract — do
     NOT change observable behavior (this is a canonicalization, not a behavior change).
  3. Remove now-unused `json` imports only if no other use remains in the module (it is a
     large module — verify before removing the import).
- **Notes**: These three are the ONLY in-mission inline reads (SC-004). Do not sweep other
  modules — #2100 backlog is deferred (Out of Scope).

### Subtask T025 – Name/reconcile the duplicate `load_meta`

- **Files**: `task_utils/support.py:363`.
- **Steps**:
  1. Declare `specify_cli.mission_metadata.load_meta` as the **canonical** authority
     (it is the dir-taking, knob-bearing reader). The `support.py` `load_meta` is a
     **path-taking shim** that already delegates to `_load_meta_canonical`
     (`support.py:380`). Do NOT silently fork: add a module-level docstring/comment on
     `support.py:363` stating it is a thin path-signature adapter over the canonical
     `mission_metadata.load_meta`, and is retained only for its `meta_path`-file calling
     convention + `TaskCliError` translation.
  2. If feasible without churning callers, prefer renaming the shim to make the canonical
     one unambiguous (e.g. keep the name but ensure the docstring + `__all__` comment make
     "canonical = mission_metadata.load_meta" explicit). Renaming the exported symbol risks
     breaking `task_utils` consumers — scope-check first; if the rename fan-out exceeds this
     mission's touched modules, name-via-docstring is sufficient for SC-004.
- **Notes**: SC-004 requires the canonical authority be **unambiguous**, not that the shim
  be deleted. The shim's distinct signature (file path vs dir) is a legitimate adapter.

### Subtask T026 – SC-004 contract-pinned test (DIRECTIVE_034 spirit)

- **Files**: `tests/specify_cli/` (mission meta / support test module).
- **Steps**:
  1. **BEHAVIORAL form is MANDATORY (DECISION 7) — DROP the source-grep count option**:
     do NOT assert "zero inline `json.loads(...read_text())`" by parsing module source.
     Instead, feed a **malformed** `meta.json` through **each of the 3 converted sites**
     via their **pre-existing entry points**, and assert the read degrades via
     `load_meta`'s contract (the canonical reader's `on_malformed`/`allow_missing`
     behavior) rather than raising a raw `JSONDecodeError` (which the old inline
     `json.loads` produced). This proves the canonical reader is actually in play at each
     site — a source grep proves only that the text changed, not that the contract holds.
  2. For each of the 3 sites, choose the entry point that reaches it (the CLI/agent
     command or helper that invokes the path) and drive a malformed-meta case; assert the
     `load_meta`-contract degradation (e.g. the documented error/empty behavior), NOT a
     raw `JSONDecodeError`.
  3. Realistic fixtures: real-shaped `meta.json` (real ULID `mission_id`, real `mid8`),
     malformed by a realistic corruption (truncated/invalid JSON), not a 1-char fake.
- **Notes**: SC-004 is "zero inline reads in touched modules + canonical authority
  unambiguous" — pin it BEHAVIORALLY at all 3 sites, never via a repo-wide or
  module-source count.

## Test Strategy

- `pytest tests/specify_cli/ -k "meta or load_meta or support" -q`.
- `ruff check` + `mypy` on owned files — zero issues, no suppressions.

## Risks & Mitigations

- **Behavior drift at the 3 sites**: `json.loads` raises `JSONDecodeError`; `load_meta`
  has its own contract. Mitigation: T024 reads ±15 lines and matches `allow_missing`/
  `on_malformed` to the existing local behavior.
- **Scope creep into #2100**: Mitigation: only the 3 in-mission sites; backlog deferred.
- **Symbol-rename fan-out**: Mitigation: name-via-docstring is acceptable for SC-004 if a
  rename exceeds the touched-module set.

## Review Guidance

- Verify exactly the 3 in-mission inline reads are converted, no more, no fewer.
- Verify the canonical `load_meta` authority is unambiguous (docstring/comment names it).
- Verify behavior at each site is preserved (malformed/missing handling unchanged).
- Verify T026 is the **behavioral** form (malformed meta through each of the 3 sites'
  pre-existing entry points; `load_meta`-contract degradation asserted) — reject a
  source-grep / module-count test (DECISION 7).

## Activity Log

- 2026-06-23T19:28:09Z – system – Prompt created.
- 2026-06-23T23:46:27Z – claude:opus:python-pedro:implementer – shell_pid=2994340 – Started implementation via action command
- 2026-06-23T23:59:03Z – claude:opus:python-pedro:implementer – shell_pid=2994340 – Routed 3 in-mission inline json.loads(meta) reads through canonical load_meta (FR-009/SC-004): _read_feature_meta->load_meta_or_empty, extracted _read_meta_for_pr_bound->load_meta_or_empty, extracted _read_meta_for_emission->load_meta(on_malformed=none); behavior-neutral. support.py:load_meta documented as path-signature adapter over canonical mission_metadata.load_meta. Behavioral SC-004 test (9 cells), red-first proven. Diff-scoped ruff exit 0; mypy 0 new errors; WP06 9/9 green; 0 new failures vs base. --force used only to clear the inherited-kitty-specs guard (residue-ripple fallout from WP01-03 partition, not WP06's owned files).
- 2026-06-23T23:59:42Z – claude:opus:python-pedro:implementer – shell_pid=2994340 – WP06 meta-reader sweep complete (FR-009/SC-004); behavioral SC-004 test 9/9; --force clears inherited-kitty-specs guard (WP01-03 partition residue).
- 2026-06-24T00:00:50Z – claude:opus:python-pedro:implementer – shell_pid=2994340 – WP06 meta-reader sweep complete (FR-009/SC-004); routed 3 in-mission inline json.loads(meta) reads through canonical load_meta; behavioral SC-004 test 9/9 green; diff-scoped ruff exit 0; 0 new failures vs base. --force clears inherited-kitty-specs guard (WP01-03 partition residue).
- 2026-06-24T00:01:44Z – claude:opus:reviewer-renata:reviewer – shell_pid=3013827 – Started review via action command
- 2026-06-24T00:07:52Z – user – shell_pid=3013827 – Review passed: WP06 9/9 green (test_wp06_meta_reader_sweep.py); 3 in-mission inline json.loads(meta) reads routed through canonical mission_metadata.load_meta (load_meta_or_empty x2 silent-empty, load_meta on_malformed=none silent-none); ZERO surviving inline reads in owned files; behavior-preserved at each site; support.py:load_meta documented as non-canonical path-signature adapter delegating to _load_meta_canonical. Behavioral SC-004 confirmed: red-first verified by reverting _read_feature_meta to inline json.loads -> malformed cell fails with raw JSONDecodeError; canonical conversion makes it green = genuine mutation-killer. ruff clean, mypy 0 new errors (cast guards new helpers). 0 new failures: the 1 failure (test_prepare_merge_metadata_tolerates_malformed_json in _read_path_resolver.py) is WP05 residue-filter ripple, pre-existing on base d73b2660e, NOT WP06-owned -- flag for pre-merge sweep. --force only clears inherited kitty-specs-on-lane guard (WP01-03 partition residue), not a review concern.
- 2026-06-24T00:09:25Z – user – shell_pid=3013827 – Review passed (reviewer-renata): behavioral SC-004 mutation-killer confirmed, 3 sites converted zero survivors, duplicate delegates, 0 introduced failures. Canonical-surface sync.
