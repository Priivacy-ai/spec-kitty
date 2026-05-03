---
work_package_id: WP01
title: Boyscout cleanup — scanner audit + assume-unchanged removal + parity baseline
dependencies: []
requirement_refs:
- C-003
- C-004
- FR-013
- FR-014
- FR-015
planning_base_branch: feature/650-dashboard-ui-ux-overhaul
merge_target_branch: feature/650-dashboard-ui-ux-overhaul
branch_strategy: Planning artifacts for this feature were generated on feature/650-dashboard-ui-ux-overhaul. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/650-dashboard-ui-ux-overhaul unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-mission-registry-and-api-boundary-doctrine-01KQPDBB
base_commit: b7cced4da2d6b70635f8f14160d17a8bfa03ac04
created_at: '2026-05-03T13:58:21.850234+00:00'
subtasks:
- T001
- T002
- T003
agent: "claude:opus-4-7:reviewer-renata:reviewer"
shell_pid: "1364433"
history:
- date: '2026-05-03'
  event: created
  note: Auto-generated alongside tasks.md
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/dashboard/scanner.py
execution_mode: code_change
owned_files:
- src/specify_cli/dashboard/scanner.py
- tests/test_dashboard/test_scanner_entrypoint_parity.py
- .gitignore
role: implementer
tags:
- boyscout
- prerequisite
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load the `implementer-ivan` agent profile:

```
/ad-hoc-profile-load implementer-ivan
```

This profile governs your role in this work package. You are operating as Implementer Ivan: your responsibility is clean, test-backed implementation. Boyscout work in particular: leave the substrate cleaner than you found it without changing production behaviour.

## Objective

Boyscout cleanup. Three discrete deliverables that, together, leave the codebase in a state where the registry mission's subsequent WPs (WP02–WP07) can build on top without inheriting pre-existing debt. **Every other WP in this mission carries `dependencies: [WP01]`** — this WP is the ordering anchor.

**Critical**: WP01 makes ZERO production behaviour changes. Documentation, test addition, and git-config / .gitignore changes only.

## Context

The mission ships a `MissionRegistry` that wraps the existing scanner functions. Before that wrap can land cleanly, three pre-existing problems need to be resolved:

1. The scanner module has multiple overlapping entry points (`scan_all_features`, `scan_feature_kanban`, `build_mission_registry`, `resolve_active_feature`, `resolve_feature_dir`, `format_path_for_display`). Their I/O shapes are not documented in one place. The registry will subsume some but not all of them; before doing so, document each one.

2. A background daemon (probably `spec-kitty next`'s state-event materialisation) auto-rewrites `kitty-specs/<slug>/status.json` files mid-session. We previously suppressed this with `git update-index --assume-unchanged`. That workaround interferes with this mission's WPs touching files in those directories. We need to fix it properly.

3. There are at least three independent readers of the same `kitty-specs/*/` data today (FastAPI routers, CLI `dashboard --json`, glossary handler internals). No test asserts they agree on the mission identity set. The registry refactor would otherwise be at risk of silently changing output shape; we add a baseline parity test as the safety net.

## Subtasks

### T001 — Scanner entry-point audit + documentation

**File**: `src/specify_cli/dashboard/scanner.py`

**Action**: append a documentation block to the module docstring (no code changes). Document each public entry point with:

- Function signature
- I/O contract (what it returns; what it raises; cache behaviour)
- Which downstream consumers call it today (grep `from specify_cli.dashboard.scanner import` in `src/`)
- Whether the registry will subsume it (yes/no/partial)

Format suggestion:

```python
"""Dashboard scanner — directory walks of kitty-specs/.

...existing docstring...

Entry-point audit (added 2026-05-03 by mission
mission-registry-and-api-boundary-doctrine-01KQPDBB; see initiative
architecture/2.x/initiatives/2026-05-stable-application-api-surface/README.md
for context):

| Function | Returns | Cached? | Subsumed by registry? |
|----------|---------|---------|------------------------|
| scan_all_features | list[FeatureItem] | No (per-call walk) | YES — MissionRegistry.list_missions() |
| scan_feature_kanban | KanbanResponse | No | YES — WorkPackageRegistry.list_work_packages() |
| build_mission_registry | dict[mission_id, MissionRecord] | No | YES — MissionRegistry.list_missions() (different return shape; consumers map) |
| resolve_active_feature | FeatureItem \| None | No | NO — stays in MissionScanService for active-detection logic |
| resolve_feature_dir | Path \| None | No | NO — used by file-serving routes; registry exposes feature_dir on MissionRecord |
| format_path_for_display | str | No (pure function) | NO — pure formatting helper |
"""
```

**Add `# TODO(remove with mission-registry-and-api-boundary-doctrine-01KQPDBB)` markers** above each function the registry will subsume (`scan_all_features`, `scan_feature_kanban`, `build_mission_registry`).

**No production code changes.** Lines of code change in functions = 0. Lines of docstring change = ~30.

**Validation**: open the file, read the docstring cold, ask: "could a contributor who has never seen the registry decide whether to call `scan_all_features` directly or wait for the registry?" If the answer is yes, the audit is complete.

### T002 — Replace the `assume-unchanged` workaround

**Files**: `.gitignore` (potentially), git config (via `git update-index --no-assume-unchanged`).

**Action**: investigate and choose one of two reversible directions:

**(a) Stop the daemon mutation**:
- Run `spec-kitty dashboard --kill` and `pgrep -f spec-kitty` to ensure no stray daemon is mutating files.
- If a stale `mission_number` backfill is the culprit, confirm by checking the git diff on a freshly-mutated file — if `mission_number` flips from `""` to a real number, it's the materialiser running on stale state.
- The fix is to ensure the materialiser only runs when invoked, not on every dashboard poll.

**(b) Gitignore the materialised snapshots**:
- Add `kitty-specs/*/status.json` to `.gitignore` (with a comment explaining: the canonical event log is `status.events.jsonl`; `status.json` is a derived snapshot for fast reads, regenerated on demand).
- Confirm `kitty-specs/*/status.events.jsonl` stays tracked (the canonical authority).
- Run `git rm --cached kitty-specs/*/status.json` to untrack the existing files; commit.

**Recommendation**: try (a) first. If the daemon mutation cannot be stopped within ~30 minutes of investigation, pivot to (b). Either is acceptable — the WP01 reviewer judges based on findings.

**Independent of choice**, run:

```bash
git update-index --no-assume-unchanged \
  kitty-specs/cli-upgrade-nag-lazy-project-migrations-01KQ6YDN/status.json \
  kitty-specs/documentation-mission-composition-fixup-01KQ6N5X/status.json \
  kitty-specs/documentation-mission-composition-rewrite-01KQ5M1Y/status.json \
  kitty-specs/mission-retrospective-learning-loop-01KQ6YEG/status.json \
  kitty-specs/research-mission-composition-rewrite-v2-01KQ4QVV/status.json
```

After this, `git ls-files -v | grep ^h | grep kitty-specs` MUST return empty.

**Document the chosen direction** in this WP's review record (the chat conversation, or a `kitty-specs/<this-mission>/wp01-review-notes.md` file if needed).

### T003 — Scanner parity baseline test

**File**: `tests/test_dashboard/test_scanner_entrypoint_parity.py` (new).

**Action**: write a baseline test that, for the same fixture project, asserts `scan_all_features(...)` and `build_mission_registry(...)` produce **structurally compatible** mission identity:

```python
"""Baseline parity test for the scanner's two mission-listing entry points.

Establishes the safety net for the registry refactor in WP02-WP07. If
this test starts failing after a registry change, the registry refactor
diverged scan_all_features and build_mission_registry; revert the change
and investigate.

Owned by WP01 of mission mission-registry-and-api-boundary-doctrine-01KQPDBB.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.fast


@pytest.fixture
def fixture_project(tmp_path: Path) -> Path:
    """Build a minimal fixture project with 2 missions."""
    kittify_dir = tmp_path / ".kittify"
    kittify_dir.mkdir()

    for mid8, slug, ulid in [
        ("01ABCDEF", "mission-alpha-01ABCDEF", "01ABCDEFGHJKMNPQRSTVWXYZ00"),
        ("01GHIJKL", "mission-beta-01GHIJKL", "01GHIJKLMNPQRSTVWXYZ00ABCD"),
    ]:
        feature_dir = tmp_path / "kitty-specs" / slug
        (feature_dir / "tasks").mkdir(parents=True)
        (feature_dir / "spec.md").write_text(f"# {slug}\n", encoding="utf-8")
        (feature_dir / "meta.json").write_text(json.dumps({
            "mission_id": ulid,
            "mission_slug": slug,
            "friendly_name": slug.replace("-", " ").title(),
            "mission_number": None,
            "mission_type": "software-dev",
        }, indent=2), encoding="utf-8")
    return tmp_path


def test_scan_and_registry_agree_on_mission_id_set(fixture_project: Path) -> None:
    """Both readers must surface the same set of mission_ids for the same fixture."""
    from specify_cli.dashboard.scanner import scan_all_features, build_mission_registry

    features = scan_all_features(fixture_project)
    registry = build_mission_registry(fixture_project)

    feature_ids = {f["meta"].get("mission_id") for f in features if f.get("meta", {}).get("mission_id")}
    registry_ids = set(registry.keys())

    assert feature_ids == registry_ids, (
        f"scan_all_features and build_mission_registry disagree on mission_id set:\n"
        f"  scan_all_features only: {feature_ids - registry_ids}\n"
        f"  build_mission_registry only: {registry_ids - feature_ids}\n"
        "If this fails on a fresh project: scanner divergence is a pre-existing bug."
    )


def test_scan_and_registry_agree_on_mission_slug_set(fixture_project: Path) -> None:
    """Same assertion at the slug level."""
    from specify_cli.dashboard.scanner import scan_all_features, build_mission_registry

    features = scan_all_features(fixture_project)
    registry = build_mission_registry(fixture_project)

    feature_slugs = {f["id"] for f in features}
    registry_slugs = {entry["mission_slug"] for entry in registry.values() if entry.get("mission_slug")}

    assert feature_slugs == registry_slugs, (
        f"slug-set divergence: scan-only={feature_slugs - registry_slugs}, "
        f"registry-only={registry_slugs - feature_slugs}"
    )
```

**If this test fails on first run** (e.g., the two readers genuinely diverge today): document the failing test as the **baseline state**. The test is the safety net for the registry refactor; the registry MUST NOT make divergence worse. WP03's reviewer checks this.

If both readers genuinely agree today, all the better — the test passes immediately.

## Branch Strategy

Planning base branch: `feature/650-dashboard-ui-ux-overhaul`
Merge target branch: `feature/650-dashboard-ui-ux-overhaul`
Execution: lane-less per spec C-001 (mission runs directly on the parent branch). No worktree allocation; commits land on the planning branch directly. State-machine `done` transition uses `--done-override-reason` per the established pattern.

## Definition of Done

- [ ] Scanner module docstring contains the entry-point audit table.
- [ ] Three functions (`scan_all_features`, `scan_feature_kanban`, `build_mission_registry`) carry `# TODO(remove with mission-registry-and-api-boundary-doctrine-01KQPDBB)` markers above their definitions.
- [ ] `git ls-files -v | grep ^h | grep kitty-specs/` returns empty.
- [ ] The chosen direction for T002 (stop daemon vs gitignore snapshot) is documented in the WP review record with rationale.
- [ ] `tests/test_dashboard/test_scanner_entrypoint_parity.py` exists and runs (passing or failing-as-documented).
- [ ] No production code behaviour changed by this WP — `git diff WP01-base..WP01-end --stat` shows changes ONLY in the docstring of `scanner.py`, the new test file, and `.gitignore` (if the gitignore route was chosen).

## Reviewer guidance

- **Test sanity check** (mission-wide rule C-003): the parity test uses a real fixture project tree (mkdir + meta.json), not a synthetic dict that mocks `scan_all_features`'s return value. If the test would still pass with the implementation deleted, reject the WP.
- **Boyscout boundary**: if the reviewer sees ANY production code change beyond the docstring, the test, and the gitignore: reject. Boyscout means "leave it cleaner without changing what it does."
- **T002 direction**: confirm the chosen direction is documented and reversible. Either route is acceptable; the rationale must be written down.

## Risks

- **The daemon mutation has more than one source**: T002 might find that multiple background processes (spec-kitty next, the dashboard's status materialiser, etc.) all mutate `status.json`. Stopping just one may not be sufficient. Mitigation: document the finding; if the source is genuinely diffuse, fall back to gitignore.
- **The parity test fails on a fresh fixture project**: this would mean the two readers have always diverged. The WP01 reviewer must record this as the baseline; WP03 must not make it worse. The test is informational here, not enforcing.
- **Scanner audit reveals more entry points than listed**: the table can grow. Add rows; do not skip any public function.

## Activity Log

- 2026-05-03T13:58:23Z – claude:opus-4-7:implementer-ivan:implementer – shell_pid=1357077 – Assigned agent via action command
- 2026-05-03T14:04:22Z – claude:opus-4-7:implementer-ivan:implementer – shell_pid=1357077 – Boyscout complete: scanner audit (docstring + 3 TODO markers, zero behaviour change), parity baseline test added (2/2 passing). Direction for T002: route (b) gitignore. Lane portion is .gitignore + scanner + test. assume-unchanged flag cleared in main repo; the 138 status.json untracking will be applied on the planning branch (lane branches cannot touch kitty-specs/).
- 2026-05-03T14:05:46Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=1364433 – Started review via action command
- 2026-05-03T14:07:59Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=1364433 – Review passed: boyscout invariant held (scanner.py diff is docstring + 3 TODO comments only, zero function-body changes), parity test passes 2/2 with real fixture (mkdir+meta.json — satisfies C-003), 246/246 dashboard tests pass, gitignore route chosen with rationale, deferred bulk untrack of 139 tracked status.json files is acceptable as a separate planning-branch operation (lane-branch protection legitimately blocks kitty-specs/ changes; the daemon-mutation noise is already suppressed for the lane WPs because their owned_files are under src/specify_cli/, not kitty-specs/)
