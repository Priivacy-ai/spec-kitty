---
work_package_id: WP10
title: 'Polish: end-to-end smoke + field-merge edge case fixture'
dependencies:
- WP08
- WP09
requirement_refs:
- FR-009
- FR-014
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-charter-ux-and-org-pack-vocabulary-01KSAF14
base_commit: 9c35535fe77b439482410071f3dad0769f2d8d07
created_at: '2026-05-24T11:22:59.167026+00:00'
subtasks:
- T055
- T056
- T057
agent: "claude:opus-4-7:reviewer-renata:reviewer"
shell_pid: "1419859"
history:
- by: claude
  at: '2026-05-23T13:30:00+00:00'
  action: generated
agent_profile: reviewer-renata
authoritative_surface: tests/integration/
execution_mode: code_change
mission_id: 01KSAF14K8FZ56MHYT45EGWHHC
mission_slug: charter-ux-and-org-pack-vocabulary-01KSAF14
owned_files:
- tests/integration/test_pack_enhances_partial_fields.py
- tests/integration/test_quickstart_end_to_end.py
priority: P2
role: reviewer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Invoke `/ad-hoc-profile-load` with argument `reviewer-renata` before reading further. This is the polish-and-validate WP — Renata's reviewer lens (verify outcomes, not implementation details) is the right fit.

## Objective

Validate the mission end-to-end by running the quickstart smoke flow on a fresh fixture, lock the field-merge sharp edge from the architect remediation (data-model.md §6 + quickstart.md §4a) into a permanent integration test, and follow through on DIR-012 by close-commenting each linked GitHub issue with the merged PR link.

## Branch strategy

- Planning base branch: `main`
- Merge target branch: `main`
- Execution worktree: allocated by `finalize-tasks`.

## Context

- `kitty-specs/.../quickstart.md` — Steps 1-5 + Step 4a (field-merge edge case lock)
- `kitty-specs/.../data-model.md` — §6 (conflict resolution) + §1.2 field semantics
- All prior WPs (WP01..WP09) merged.

## Subtask details

### T055 — End-to-end quickstart smoke

**Files**: NEW `tests/integration/test_quickstart_end_to_end.py`

Implement a single end-to-end integration test that walks Steps 1-5 of `quickstart.md` on a `tmp_path`-materialised fixture repo. Assertions:

- Step 1: `spec-kitty charter status --json` payload matches the expected `freshness` shape.
- Step 1: `spec-kitty charter lint --json` returns `graph_state="built_in_only"` on a fresh checkout.
- Step 2: `spec-kitty charter preflight --json` returns `passed=false` with the expected `blocked_reason`.
- Step 2: `--auto-refresh` produces `auto_refresh_applied=true` with the expected actions array.
- Step 3: After auto-refresh, either `graph.yaml` exists OR the manifest reports `built_in_only: true`.
- Step 4: Pack validate flow (advisory suppression, auto-emit edge, unknown_target error).
- Step 5: Architectural assertion — no `"shipped"` in any surface's JSON.

This is a heavy integration test (10-30 s runtime). Mark with `@pytest.mark.integration` if the project uses tags.

### T056 — Close-comment on issues

For each linked issue, comment with the merged PR link:

```bash
unset GITHUB_TOKEN
PR_URL="<the PR URL once merged>"  # populated by the implementer at execution time
for issue in 1099 1100 1101 1104 1291; do
  gh issue comment $issue --repo Priivacy-ai/spec-kitty --body "Closed by mission 01KSAF14 — see $PR_URL"
  gh issue close $issue --repo Priivacy-ai/spec-kitty --comment "Resolved in $PR_URL"
done
```

Verify each issue ends up in CLOSED state.

### T057 — Field-merge edge case fixture

**Files**: NEW `tests/integration/test_pack_enhances_partial_fields.py`

Implement the architect-remediation lock from `quickstart.md` §4a. Test:

```python
def test_pack_enhances_with_partial_fields_field_merges_per_2026_05_16_adr(tmp_repo, fixture_pack):
    """
    Architect remediation lock for ADR 2026-05-16-1.

    When a pack tactic declares `enhances: <built-in-id>` and provides an empty
    `steps:` list (or omits an optional field), the field-merge MUST:
      - For fields the pack provides with non-empty value: pack value wins.
      - For fields the pack omits: built-in value survives.
      - For fields the pack provides as empty list/null: built-in value survives
        (empty is "not provided" for merge purposes per src/doctrine/base.py::_merge).
    """
    # Arrange: built-in tactic has steps=[step1, step2], failure_modes=[a,b],
    # applies_to_languages=[python]. Pack tactic declares enhances and provides
    # only name + purpose (omits steps, failure_modes, applies_to_languages).

    # Act: load merged tactic.

    # Assert: merged.steps == [step1, step2]
    #         merged.failure_modes == [a, b]
    #         merged.applies_to_languages == [python]
    #         merged.name == pack_value (overridden)
    #         merged.purpose == pack_value (overridden)
```

Use existing fixtures from `tests/doctrine/conftest.py` for the built-in tactic seed.

## Definition of Done

- [ ] End-to-end smoke test passes on `tmp_path` fixture and exercises Steps 1-5.
- [ ] All 5 linked issues are CLOSED with PR link comment.
- [ ] Field-merge edge case fixture passes and locks the ADR-ratified behaviour.
- [ ] Final CI is green.
- [ ] Mission `meta.json.status` advances to `done` after merge.

## Risks

- **Subprocess perf in CI**: end-to-end smoke spawns several `spec-kitty` invocations. Mark `@pytest.mark.slow` if CI grouping demands it.
- **GitHub rate limits**: closing 5 issues in sequence with `gh` is safe but verify after T056.
- **Field-merge sharp edge**: if `_merge()` semantics change in some future refactor, this fixture catches it — that's the point. Don't soften the assertions.

## Reviewer guidance

1. Verify the smoke test does not rely on side effects from other tests.
2. Confirm each issue has the close-comment with the actual PR URL.
3. Confirm the field-merge fixture asserts BOTH `pack-overrides-survive` AND `built-in-omitted-fields-survive` cases — both directions matter.

## Activity Log

- 2026-05-24T11:22:59Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=1389224 – Assigned agent via action command
- 2026-05-24T11:36:34Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=1389224 – Ready for review: 2 new integration tests + 5 GH issue close-comments
- 2026-05-24T11:37:12Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=1419859 – Started review via action command
- 2026-05-24T11:39:42Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=1419859 – Review passed: end-to-end smoke + field-merge fixture landed (14 new tests, 141 smoke green), 5 issue comments posted, ADR-merge-semantics calibration documented correctly
- 2026-05-24T11:46:56Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=1419859 – Done override: Feature merged to main as squash commit 37407a3b2; status carried through from mission branch
