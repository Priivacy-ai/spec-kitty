---
work_package_id: WP05
title: 'Wave A LD-1: consolidate _apply_org_overrides + _apply_project_overrides (FR-006)'
dependencies: []
requirement_refs:
- FR-006
planning_base_branch: kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ
merge_target_branch: kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ
branch_strategy: Planning artifacts for this mission were generated on kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ
base_commit: 1f260a75ce8fb5281036f736853cd64a488729b2
created_at: '2026-05-25T14:33:32.897415+00:00'
subtasks:
- T014
- T015
- T016
- T017
- T018
agent: "claude:opus-4-7:reviewer-renata:reviewer"
shell_pid: "1882060"
history:
- by: claude
  at: '2026-05-25T14:00:00+00:00'
  action: generated
agent_profile: python-pedro
authoritative_surface: src/doctrine/
execution_mode: code_change
mission_id: 01KSF9HJBFKRBC617JVHKZXNE2
mission_slug: test-stabilization-and-debt-pass-01KSF9HJ
owned_files:
- src/doctrine/base.py
- tests/doctrine/test_doctrine_layered_resolution.py
- tests/doctrine/test_doctrine_layer_collision_warnings.py
priority: P1
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Invoke `/ad-hoc-profile-load` with argument `python-pedro` before reading further. Pure Python refactor; behaviour-preservation is the success criterion.

## Objective

Replace the two near-identical methods `_apply_org_overrides` and `_apply_project_overrides` in `src/doctrine/base.py` with a single parameterised `_apply_overlay_layer(dirs, layer_name, *, built_in)` method.

This is the LD-1 finding from the architect's deep-dive review (§2). The current code reads the same skeleton twice (lines 210-308) and the merge-semantics ADR `2026-05-16-1` ratifies that org and project overlays use identical field-merge logic. Making them one method makes the identical-by-design intent visible.

**Behaviour-preserving** (spec C-002): existing tests must remain green WITHOUT modification.

## Branch strategy

- Planning base branch: mission lane branch
- Merge target branch: `main`
- Execution: lane workspace allocated by `finalize-tasks`.

## Context

- [`spec.md`](../spec.md) FR-006 + C-002.
- [`plan.md`](../plan.md) Wave A § WP05 (behaviour-preservation test anchors).
- [`docs/engineering_notes/architectural-review/2026-05-25-deep-dive-architectural-review.md`](../../../docs/engineering_notes/architectural-review/2026-05-25-deep-dive-architectural-review.md) §2 LD-1 (quoted code spans).
- [`architecture/3.x/adr/2026-05-16-1-doctrine-layer-merge-semantics.md`](../../../architecture/3.x/adr/2026-05-16-1-doctrine-layer-merge-semantics.md) — the ratified semantics.
- Existing source: `src/doctrine/base.py` lines 210-308.

## Subtask details

### T014 — Author `_apply_overlay_layer`

In `src/doctrine/base.py`, add the new method:

```python
def _apply_overlay_layer(
    self,
    dirs: Sequence[Path],
    layer_name: str,
    *,
    yaml_parser: YAML,
    built_in: dict[str, T],
) -> None:
    """Apply a stack of overlay directories to ``self._items`` with the given provenance.

    Used for both the org and project layers. Mirrors the field-merge semantics
    ratified by ADR 2026-05-16-1: for each YAML file in each dir, parse + validate
    + merge-or-insert against ``built_in``. Tag every resulting item with the given
    layer_name as provenance.

    Args:
        dirs: ordered list of overlay directories. Later dirs override earlier
              ones for the same artifact ID (FR-006, C-004 of the org-layer
              mission).
        layer_name: provenance string ("org" or "project").
        yaml_parser: pre-configured YAML loader.
        built_in: the resolved built-in items map (target of merge-on-collision).
    """
    for overlay_dir in dirs:
        if not overlay_dir.exists():
            continue
        for yaml_file in self._project_scan(overlay_dir):
            try:
                data = yaml_parser.load(yaml_file)
                if data is None:
                    continue
                self._pre_validate(data, yaml_file)
                item_id = data.get("id")
                if not item_id:
                    warnings.warn(
                        f"Skipping {layer_name} {self._kind} {yaml_file.name}: no id",
                        UserWarning,
                        stacklevel=3,
                    )
                    continue
                if item_id in built_in:
                    merged = self._merge(built_in[item_id], data)
                    if self._include_item(merged):
                        self._record_collision_if_present(
                            item_id=item_id,
                            higher_layer=layer_name,
                            higher_data=data,
                        )
                        self._items[item_id] = merged
                        self._provenance[item_id] = layer_name
                else:
                    obj = self._schema.model_validate(data)
                    if self._include_item(obj):
                        key = self._key(obj)
                        self._record_collision_if_present(
                            item_id=key,
                            higher_layer=layer_name,
                            higher_data=data,
                        )
                        self._items[key] = obj
                        self._provenance[key] = layer_name
            except (YAMLError, ValidationError, OSError) as exc:
                warnings.warn(
                    f"Skipping invalid {layer_name} {self._kind} {yaml_file.name}: {exc}",
                    UserWarning,
                    stacklevel=3,
                )
```

### T015 — Migrate the org caller

Find every caller of `_apply_org_overrides(yaml_parser, built_in)`. Replace with:

```python
self._apply_overlay_layer(self._org_dirs, "org", yaml_parser=yaml_parser, built_in=built_in)
```

### T016 — Migrate the project caller

Find every caller of `_apply_project_overrides(yaml_parser, built_in)`. Replace with:

```python
self._apply_overlay_layer(
    [self._project_dir] if self._project_dir else [],
    "project",
    yaml_parser=yaml_parser,
    built_in=built_in,
)
```

### T017 — Delete the two old methods

Remove `_apply_org_overrides` and `_apply_project_overrides` entirely.

### T018 — Verify behaviour-preservation tests

```bash
PWHEADLESS=1 .venv/bin/pytest tests/doctrine/test_doctrine_layered_resolution.py tests/doctrine/test_doctrine_layer_collision_warnings.py tests/doctrine/ -q
```

Expected: 0 net new failures vs the WP01 baseline.

## Definition of Done

- [ ] `_apply_overlay_layer` exists and is used in both org and project paths.
- [ ] `_apply_org_overrides` and `_apply_project_overrides` no longer exist in `src/doctrine/base.py`.
- [ ] `git grep "def _apply_.*_overrides" src/doctrine/base.py` returns nothing (Success criterion 2).
- [ ] Behaviour-preservation tests green.
- [ ] `mypy --strict src/doctrine/base.py` clean.
- [ ] `ruff check src/doctrine/base.py` clean.

## Risks

- **Provenance tag drift**: `"org"` and `"project"` strings are baked in elsewhere (e.g., `_warn_project_override` in `src/charter/drg.py`). Verify those consumers still receive the same strings via the new method.
- **`stacklevel=3` correctness**: the warning `stacklevel` was 3 in both old methods; verify it's still appropriate from the new call depth (may need adjustment if the new method adds a stack frame).

## Reviewer guidance

1. Verify the two old methods are GONE, not just deprecated.
2. Verify the org path's `for org_dir in self._org_dirs` semantics are preserved (multiple dirs iterated in declaration order).
3. Verify the project path's `if not (self._project_dir and self._project_dir.exists())` short-circuit is preserved by the empty-list pattern.

## Activity Log

- 2026-05-25T14:33:33Z – claude:opus-4-7:python-pedro:implementer – shell_pid=1856918 – Assigned agent via action command
- 2026-05-25T14:39:41Z – claude:opus-4-7:python-pedro:implementer – shell_pid=1856918 – LD-1 consolidation done; behaviour-preservation tests green
- 2026-05-25T14:40:11Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=1882060 – Started review via action command
- 2026-05-25T14:42:58Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=1882060 – Review passed: LD-1 consolidation, 25/25 behaviour-preservation tests green, 4 pre-existing failures verified out of scope
