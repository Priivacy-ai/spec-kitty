---
work_package_id: WP10
title: Action-Surface Calibration Reports + DRG Edge Changes
dependencies:
- WP01
- WP05
requirement_refs:
- C-011
- FR-030
- FR-031
- FR-032
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T048
- T049
- T050
- T051
- T052
- T053
- T054
agent: "claude:opus:reviewer:reviewer"
shell_pid: "24305"
history:
- at: '2026-04-27T08:18:00Z'
  actor: claude
  action: created
authoritative_surface: architecture/calibration/
execution_mode: code_change
mission_slug: mission-retrospective-learning-loop-01KQ6YEG
owned_files:
- architecture/calibration/README.md
- architecture/calibration/software-dev.md
- architecture/calibration/research.md
- architecture/calibration/documentation.md
- architecture/calibration/erp-custom.md
- src/specify_cli/calibration/__init__.py
- src/specify_cli/calibration/inequality.py
- src/specify_cli/calibration/walker.py
- .kittify/doctrine/overlays/calibration-software-dev.yaml
- .kittify/doctrine/overlays/calibration-research.yaml
- .kittify/doctrine/overlays/calibration-documentation.yaml
- .kittify/doctrine/overlays/calibration-erp-custom.yaml
- tests/calibration/__init__.py
- tests/calibration/test_inequality.py
- tests/calibration/test_walker.py
- tests/architectural/test_no_prompt_filtering_added.py
priority: P2
status: planned
tags: []
---

# WP10 — Action-Surface Calibration Reports + DRG Edge Changes

## Objective

Calibrate action surfaces for the four in-scope missions (software-dev, research, documentation, ERP custom) so that the architecture §4.5.1 inequality holds for every step. Produce a calibration report per mission and apply recommended DRG edge changes via project-local overlays only — no shipped `src/doctrine/graph.yaml` mutations from this WP, and absolutely no prompt-builder filtering (C-011).

## Spec coverage

- **FR-030** per-mission calibration reports with the required column shape.
- **FR-031** DRG edges only; no prompt filtering.
- **FR-032** §4.5.1 inequality holds for every step.
- **C-011** prohibition against new prompt-builder filtering call sites.

## Context

The §4.5.1 inequality is pinned in [`../research.md`](../research.md) R-005:

1. `ResolvedScope(s) ⊇ RequiredScope(s)` — no missing-context regressions.
2. `ResolvedScope(s)` is **not** a strict superset of `RequiredScope(s) ∪ {known-irrelevant URNs}`.

`RequiredScope(s)` is determined per step by inspection during calibration. Calibration outcomes (recommended DRG edge changes) go to **project-local overlays** under `.kittify/doctrine/overlays/calibration-<mission>.yaml`. The shipped `src/doctrine/graph.yaml` is owned by WP01 and must not be edited from here.

## Subtasks

### T048 — §4.5.1 inequality predicate as a calibration helper

In `src/specify_cli/calibration/inequality.py`:

```python
@dataclass(frozen=True)
class InequalityResult:
    holds: bool
    missing_urns: frozenset[str]
    over_broad_urns: frozenset[str]

def assert_inequality_holds(
    *,
    resolved_scope: frozenset[str],
    required_scope: frozenset[str],
    known_irrelevant: frozenset[str] = frozenset(),
) -> InequalityResult: ...
```

The function returns the `InequalityResult` (does not raise). Callers decide whether a violation is fatal.

### T049 — Calibration walker

In `src/specify_cli/calibration/walker.py`:

```python
def walk_mission(
    *,
    mission_key: str,           # "software-dev", "research", "documentation", or a custom mission id
    repo_root: Path,
) -> list[CalibrationFinding]: ...
```

For each `(profile, action)` pair invoked by any step in the mission:

1. Resolve `ResolvedScope` via the existing DRG resolver.
2. Look up `RequiredScope` from a curated YAML map (created during calibration; lives under `.kittify/doctrine/overlays/calibration-<mission>-required.yaml` or inline in the calibration report — pick one and document).
3. Run `assert_inequality_holds`.
4. Emit a `CalibrationFinding` per violating step with: action_id, profile_id, missing_urns, over_broad_urns, recommended edge changes.

### T050 — Per-mission calibration report template + 4 reports

`architecture/calibration/README.md` describes the report template:

| Column | Notes |
|---|---|
| Step id | The mission step under calibration. |
| Action id | Resolved action. |
| Profile id | Resolved profile. |
| Resolved DRG artifact URNs | Output of the resolver. |
| Scope edges involved | DRG edges that produced the surfaced URNs. |
| Missing context | URNs the step needed but did not receive. |
| Irrelevant / too-broad context | URNs the step received but did not need. |
| Recommended DRG edge changes | Structured `add_edge` / `remove_edge` / `rewire_edge` proposals. |
| Before/after evidence | Before snippet (resolved scope before fix) + after snippet (resolved scope after fix). |

Then create one report file per mission: `architecture/calibration/{software-dev,research,documentation,erp-custom}.md`. Populate each report by running the walker against the mission and recording findings.

### T051 — DRG edge changes for software-dev and research

Per the calibration findings, write project-local overlays:

- `.kittify/doctrine/overlays/calibration-software-dev.yaml`
- `.kittify/doctrine/overlays/calibration-research.yaml`

Each overlay contains structured edge mutations. The runtime DRG resolver MUST be able to read overlays alongside the shipped `graph.yaml` (this may require a small enhancement to the resolver if it doesn't already; if so, surface that as a finding and decide whether to absorb it in this WP or split — prefer to absorb if the change is small and obviously correct).

### T052 — DRG edge changes for documentation and ERP custom

- `.kittify/doctrine/overlays/calibration-documentation.yaml`
- `.kittify/doctrine/overlays/calibration-erp-custom.yaml`

Same shape as T051. The ERP custom mission lives in the local custom-mission loader fixtures referenced in `start-here.md`.

### T053 — Architectural test: no new prompt-builder filtering call sites

In `tests/architectural/test_no_prompt_filtering_added.py`:

- Walk the source tree for any call site that filters prompt-builder context (e.g., functions named `filter_*`, `redact_*`, or argument names like `exclude_urns`, `hide_artifacts` introduced under `src/specify_cli/`).
- Maintain a known-good list of any pre-existing call sites; the test fails if any new site is introduced after this WP merges.

If there are zero existing prompt-filter sites, the test asserts zero. If existing sites exist, list them in the test as "grandfathered" and assert no new ones appear.

### T054 — Tests: §4.5.1 inequality holds for every in-scope step

In `tests/calibration/test_walker.py` and `tests/calibration/test_inequality.py`:

- For each in-scope mission, walk every step and assert `InequalityResult.holds` is True after the calibration overlays are applied.
- For the inequality predicate itself: a small unit test against known fixtures (over-broad case, missing case, exact-match case).

## Definition of Done

- [ ] All four calibration reports exist with the documented column shape.
- [ ] Project-local overlays apply the recommended edge changes.
- [ ] §4.5.1 inequality holds for every step in the four missions.
- [ ] Architectural test confirms no new prompt-filtering call sites.
- [ ] No edits to `src/doctrine/graph.yaml` (owned by WP01).
- [ ] `mypy --strict` passes.
- [ ] Coverage ≥ 90% on new modules.
- [ ] No changes outside `owned_files`.

## Risks

- **Resolver overlay support**: if the resolver doesn't already merge overlays with the shipped graph, this WP needs a small resolver change. Prefer to absorb if obviously correct; otherwise propose a minimal split.
- **Calibration report size**: keep it tight; don't write essays. Long-form analysis becomes follow-up issues.

## Reviewer guidance

- Confirm the four reports are present and follow the column template.
- Confirm overlays are project-local (under `.kittify/`) not shipped (under `src/doctrine/`).
- Run the architectural test against current `main` and after the changes — confirm no new prompt-filter sites.

## Implementation command

```bash
spec-kitty agent action implement WP10 --agent <name>
```

## Activity Log

- 2026-04-27T10:57:38Z – claude:sonnet:implementer:implementer – shell_pid=22798 – Started implementation via action command
- 2026-04-27T11:09:34Z – claude:sonnet:implementer:implementer – shell_pid=22798 – Ready for review: calibration reports + project-local overlays; 30 tests / mypy strict / 94% cov; all 4 missions pass §4.5.1 with no edge changes needed
- 2026-04-27T11:09:36Z – claude:opus:reviewer:reviewer – shell_pid=24305 – Started review via action command
- 2026-04-27T11:11:13Z – claude:opus:reviewer:reviewer – shell_pid=24305 – Review passed (opus): 30/30 tests, mypy strict, all 4 missions pass §4.5.1, no graph.yaml edits, no new prompt-filter sites, grandfathered list verified
