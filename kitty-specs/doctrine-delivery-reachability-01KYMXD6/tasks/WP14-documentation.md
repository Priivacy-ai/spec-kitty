---
work_package_id: WP14
title: Documentation and CLI reference
dependencies:
- WP03
- WP05
- WP10
requirement_refs:
- FR-019
- NFR-002
planning_base_branch: feat/doctrine-delivery-reachability
merge_target_branch: feat/doctrine-delivery-reachability
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-delivery-reachability. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-delivery-reachability unless the human explicitly redirects the landing branch.
created_at: '2026-07-28T19:48:12Z'
subtasks:
- T076
- T077
- T078
- T079
- T080
phase: Phase 5 - Polish
history:
- at: '2026-07-28T19:48:12Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: curator-carla
authoritative_surface: docs/doctrine/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- docs/doctrine/doctrine-kinds.md
- docs/doctrine/create-a-doctrine-artifact.md
- CHANGELOG.md
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# WP14 — Documentation and CLI reference

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the profile named in the frontmatter, and behave
according to its guidance before parsing the rest of this prompt.

- **Profile**: `curator-carla`
- **Role**: `implementer`
- **Agent/tool**: `claude`

Resolve it with **`spec-kitty agent profile show curator-carla`**. **Do not read the raw
`*.agent.yaml`**. If `curator-carla` is not present, `spec-kitty agent profile list` and pick the
closest documentation/curation profile.

---

## Objective

Make the documented remedy **followable**. #3037's actual complaint is that "ship executable logic as
an asset" is not executable downstream — landing the mechanism without the docs leaves the complaint
standing.

## Context — the doc defects, verified

- `docs/doctrine/doctrine-kinds.md:~50` states asset is "a newer, loose-contract kind ... with **no
  built-in artifacts yet**" — **false**, one ships. (Cite the sentence, not the line — anchors drift.)
- `docs/doctrine/create-a-doctrine-artifact.md` contains the word "asset" **zero** times, while
  `docs/development/review-gates.md` cites it as the asset how-to.
- New visible Typer paths from WP05 trip `REF-MISSING` in `scripts/docs/check_cli_reference_freshness.py`
  against the 4,950-line `docs/api/cli-commands.md` — WP05 owns that file; coordinate.
- The delivery verdicts (which kinds the bundle delivers, and why assets are delivered-but-ungated)
  belong "where the table records verdicts" — the slot-table doc surface WP10 touches.

## Subtasks

### T076 — Correct the false "no built-in artifacts yet" claim
1. Update `doctrine-kinds.md` to describe the shipped asset and the resolution path.

### T077 — Write the asset how-to
1. Add the asset section to `create-a-doctrine-artifact.md` that `review-gates.md` already promises:
   author a manifest, place the blob, resolve it with `spec-kitty doctrine asset path`.
2. This must be executable end-to-end against a fresh project (SC-008). Prefer doc-as-test if the
   harness exists.

### T078 — Document the delivery verdicts
1. Where the slot table records verdicts (WP10's surface), document which kinds are delivered and why
   assets are delivered-but-not-activation-gated (the third category).

### T079 — Refresh the kind-vocabulary reference
1. Update the kind-vocabulary reference for WP03's hoisted authority — one canonical mapping, no
   scattered copies.

### T080 — CHANGELOG and terminology guard
1. Add a `CHANGELOG.md` entry for the mission's user-visible surface (asset commands, activation
   delivery).
2. Run the terminology guard before pushing — it lives in a CI job the fast suites do not cover:
   `pytest tests/architectural/test_no_legacy_terminology.py`.

## Branch Strategy

Planning base and merge target `feat/doctrine-delivery-reachability`. Depends on WP03 (kind reference),
WP05 (CLI paths), WP10 (verdict surface). `spec-kitty implement WP14` resolves the workspace.

**File-ownership note**: `docs/api/cli-commands.md` is WP05's (the CLI-path entries). You own the
doctrine prose and CHANGELOG.

## Test strategy

```bash
pytest tests/docs/test_check_cli_reference_freshness.py tests/architectural/test_no_legacy_terminology.py -q
# SC-008 doc-as-test if present:
pytest tests/docs/ -k asset_howto -q
```

## Definition of Done

- [ ] `doctrine-kinds.md` no longer claims "no built-in artifacts yet"
- [ ] `create-a-doctrine-artifact.md` has an executable asset how-to (SC-008)
- [ ] Delivery verdicts documented where the slot table records them
- [ ] Kind-vocabulary reference reflects the hoisted authority
- [ ] CHANGELOG entry added
- [ ] Terminology guard passes
- [ ] `ruff` clean; docs freshness gate green

## Risks

| Risk | Mitigation |
|---|---|
| How-to that does not actually run | doc-as-test / execute against a fresh project |
| REF-MISSING on the CLI reference | WP05 owns those entries; coordinate before merge |
| Terminology regression | Run the guard before push (CI-only otherwise) |

## Reviewer guidance

1. Follow the asset how-to end to end against a fresh project — it must work.
2. Confirm the false "no built-in artifacts" claim is gone.
3. Confirm the terminology guard passes.
