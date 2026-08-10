---
work_package_id: WP01
title: Tautological test assertions (S5863 x16)
dependencies: []
requirement_refs:
- FR-004
- NFR-001
- NFR-002
- NFR-003
planning_base_branch: fix/sonar-bug-blocker-remediation
merge_target_branch: fix/sonar-bug-blocker-remediation
branch_strategy: Planning artifacts for this mission were generated on fix/sonar-bug-blocker-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/sonar-bug-blocker-remediation unless the human explicitly redirects the landing branch.
created_at: '2026-08-10T15:05:00+00:00'
subtasks:
- T001
- T002
- T003
phase: Mechanical stream - test integrity
history:
- at: '2026-08-10T15:05:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- tests/_support/git_template/test_git_template.py
- tests/audit/test_audit_serializer.py
- tests/core/test_batch_partition.py
- tests/cross_cutting/encoding/test_contextive_traceability.py
- tests/doctrine/missions/test_step_projection.py
- tests/glossary/test_drg_builder.py
- tests/runtime/test_tmp_prompt_namespace.py
- tests/specify_cli/lanes/test_resolve_lanes_dir.py
- tests/specify_cli/skills/test_manifest_store.py
- tests/specify_cli/tool_surface/profiles/test_renderers.py
- tests/sync/test_clock.py
- tests/sync/test_leak_guard_fingerprint_3115.py
- tests/sync/test_namespace.py
- tests/sync/tracker/test_origin_models.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter and behave per its
guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`

---

## Objective

Fix all 16 SonarCloud **S5863** BUG issues ("Replace this assertion to not have the same actual and
expected expression"). Each is an assertion whose left and right sides are the **same expression**, so
it can never fail — the test proves nothing. Restore each to the comparison the test actually intended.

This is the **mechanical** stream, but "mechanical" ≠ "thoughtless": recovering the intended comparison
requires reading the surrounding test. Never leave a tautology; never invent a wrong comparison.

## Per-site rule (apply to every fix)

1. **Read the test** around the flagged line — the setup, the name, the other assertions — to recover
   what relationship was meant (e.g. `assert result.foo == expected.foo` where both currently read
   `result.foo == result.foo`, or a value that should be compared to a fixture/literal).
2. **Red-first (NFR-003)**: write the corrected assertion so it would **fail** against the current
   (pre-fix) production behavior or a deliberately-wrong value, confirm it fails, then make it pass. A
   corrected assertion that cannot be shown to bite is not done.
3. **If intent is genuinely unrecoverable**: remove the assertion (do not keep it tautological) and add
   a one-line comment stating why it was removed. Prefer recovery; removal is the fallback.
4. **No suppression** (NFR-001): never add `# noqa` / `NOSONAR`.

## Subtasks

### T001 — sync cluster (4 sites)

- `tests/sync/test_clock.py:209`
- `tests/sync/test_leak_guard_fingerprint_3115.py:70`
- `tests/sync/test_namespace.py:120`
- `tests/sync/tracker/test_origin_models.py:64`

Apply the per-site rule. The leak-guard one (`test_leak_guard_fingerprint_3115.py:70`) is a
fingerprint-equality test — verify the two sides are meant to be *different* captured fingerprints, not
the same expression twice.

### T002 — specify_cli cluster (5 sites)

- `tests/specify_cli/lanes/test_resolve_lanes_dir.py:53`
- `tests/specify_cli/skills/test_manifest_store.py:510`
- `tests/specify_cli/tool_surface/profiles/test_renderers.py:387`
- `tests/specify_cli/tool_surface/profiles/test_renderers.py:393`
- `tests/specify_cli/tool_surface/profiles/test_renderers.py:399`

The three `test_renderers.py` sites are adjacent — likely a rendered-output vs expected-fixture
comparison where the expected side was mistyped to echo the actual. Recover the intended expected value.

### T003 — remaining cluster (7 sites)

- `tests/_support/git_template/test_git_template.py:42`
- `tests/audit/test_audit_serializer.py:157`
- `tests/core/test_batch_partition.py:60`
- `tests/cross_cutting/encoding/test_contextive_traceability.py:157`
- `tests/doctrine/missions/test_step_projection.py:106`
- `tests/glossary/test_drg_builder.py:86`
- `tests/runtime/test_tmp_prompt_namespace.py:62`

## Branch Strategy

Planning base and final merge target are both `fix/sonar-bug-blocker-remediation`. The execution
worktree for this WP is allocated per the computed lane in `lanes.json` — do not reconstruct the path;
consume the workspace `spec-kitty implement` resolves.

## Definition of Done

- All 16 S5863 sites corrected (or removed with rationale); no tautological assertion remains in the
  owned files.
- Red-first evidence captured for each recovered assertion (a commit/run showing it fails pre-fix).
- Scoped `pytest` over the touched files is green; `ruff` clean on changed files.
- Zero suppression comments added.
- `move-task --to for_review` pre-review gate passes.

## Risks / reviewer guidance

- **Wrong-comparison risk**: the reviewer must confirm each corrected assertion checks the *intended*
  relationship, not just something that passes. Red-first evidence is the guard.
- Some sites may compare objects whose `__eq__` is identity — ensure the fix compares the meaningful
  fields, not two references to the same object.
