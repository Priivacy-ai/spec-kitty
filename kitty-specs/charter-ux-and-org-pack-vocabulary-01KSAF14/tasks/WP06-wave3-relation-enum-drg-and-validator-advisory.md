---
work_package_id: WP06
title: 'Wave 3: Relation enum + DRG auto-emit + validator advisory (FR-012, FR-013, FR-014)'
dependencies:
- WP05
requirement_refs:
- FR-012
- FR-013
- FR-014
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-charter-ux-and-org-pack-vocabulary-01KSAF14
base_commit: dec5911802326a7fc78a7da4ee2d6bbc0b379ada
created_at: '2026-05-24T08:47:14.092517+00:00'
subtasks:
- T035
- T036
- T037
- T038
- T039
agent: "claude:opus-4-7:reviewer-renata:reviewer"
shell_pid: "1048306"
history:
- by: claude
  at: '2026-05-23T13:30:00+00:00'
  action: generated
agent_profile: python-pedro
authoritative_surface: src/specify_cli/doctrine/
execution_mode: code_change
mission_id: 01KSAF14K8FZ56MHYT45EGWHHC
mission_slug: charter-ux-and-org-pack-vocabulary-01KSAF14
owned_files:
- src/doctrine/drg/models.py
- src/doctrine/drg/org_pack_loader.py
- src/specify_cli/doctrine/pack_validator.py
- tests/specify_cli/doctrine/test_pack_validator.py
- tests/doctrine/drg/test_org_pack_auto_emit.py
priority: P0
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Invoke `/ad-hoc-profile-load` with argument `python-pedro` before reading further. StrEnum extension + Pydantic validator branching + pytest fixtures all sit in Pedro's primary focus.

## Objective

Extend the DRG `Relation` enum with `ENHANCES` and `OVERRIDES`; make `org_pack_loader` auto-emit those DRG edges from the WP05 declarative fields; rewrite the pack-validator advisory logic per the precedence rules in `contracts/pack-validator-advisory.md`. Two new error categories — `unknown_target` and `intent_conflict` — replace and augment the existing same-ID advisory wording.

## Branch strategy

- Planning base branch: `main`
- Merge target branch: `main`
- Execution worktree: allocated by `finalize-tasks`.

## Context

- `kitty-specs/.../spec.md` — FR-012, FR-013, FR-014
- `kitty-specs/.../contracts/pack-validator-advisory.md` — authoritative precedence + wording
- `kitty-specs/.../research.md` — R-2 (Relation enum policy: ADD, do not rename `REPLACES`), R-7 (unknown-target hard error), R-9 (advisory wording)
- WP05 owns the model-side fields — this WP is the consumer side.
- Existing code: `src/doctrine/drg/models.py` (Relation enum lines 46-56), `src/doctrine/drg/org_pack_loader.py` (DRG fragment builder), `src/specify_cli/doctrine/pack_validator.py` (advisory emission at line 413+)

## Subtask details

### T035 — Extend `Relation` enum

**Files**: `src/doctrine/drg/models.py`

```python
class Relation(StrEnum):
    REQUIRES = "requires"
    SUGGESTS = "suggests"
    APPLIES = "applies"
    SCOPE = "scope"
    VOCABULARY = "vocabulary"
    INSTANTIATES = "instantiates"
    REPLACES = "replaces"          # retained — existing fragments may use it
    DELEGATES_TO = "delegates_to"
    ENHANCES = "enhances"          # NEW
    OVERRIDES = "overrides"        # NEW
```

Export the new values via `doctrine.drg.__init__` `__all__`. Add a one-line docstring at the enum class explaining the augmentation pair vs the replacement edge.

### T036 — `org_pack_loader` auto-emit

**Files**: `src/doctrine/drg/org_pack_loader.py`

When loading an org pack, for each pack artifact discovered:
- If `enhances: Y` is set → append a DRG edge `(source=urn:<kind>:<id>, target=urn:<kind>:Y, relation=Relation.ENHANCES, reason="declared via <kind>.enhances field")`.
- If `overrides: Y` is set → same but with `relation=Relation.OVERRIDES`.

The edge MUST land in the pack's DRG fragment automatically — pack authors should NOT need to hand-author it in `drg/fragment.yaml`. If the author also hand-authored the same edge, the auto-emit takes precedence (deduplicate by `(source, target, relation)`).

Locate the existing pack-artifact loading point (around `org_pack_loader.load_pack`, `OrgPackFragment` construction). Hook into the per-artifact iteration.

### T037 — `pack_validator` advisory branching

**Files**: `src/specify_cli/doctrine/pack_validator.py`

Rewrite `_shipped_id_collision_advisories` (line 413+) into a more capable function — rename it to `_intent_aware_collision_messages`. Per the precedence rules in `contracts/pack-validator-advisory.md`:

```python
def _intent_aware_collision_messages(
    pack_artifacts: dict[str, dict[str, Any]],  # plural -> {id: raw_yaml_data}
    built_in_ids_per_kind: dict[str, set[str]],
) -> list[ValidationIssue]:
    issues = []
    for plural, artifacts in pack_artifacts.items():
        for art_id, data in artifacts.items():
            overrides_field = data.get("overrides")
            enhances_field = data.get("enhances")
            # 1. Both declared → intent_conflict ERROR
            if overrides_field and enhances_field:
                issues.append(ValidationIssue(
                    severity="error",
                    category="intent_conflict",
                    artifact_type=plural, artifact_id=art_id,
                    file=...,
                    message=f"overrides and enhances are mutually exclusive on {kind_singular(plural)} {art_id}",
                ))
                continue
            # 2. overrides unknown target → unknown_target ERROR
            if overrides_field and overrides_field not in built_in_ids_per_kind.get(plural, set()):
                issues.append(... unknown_target ERROR ...)
                continue
            # 3. enhances unknown target → unknown_target ERROR
            if enhances_field and enhances_field not in built_in_ids_per_kind.get(plural, set()):
                issues.append(... unknown_target ERROR ...)
                continue
            # 4. Either declared and target valid → no advisory (suppress)
            if overrides_field or enhances_field:
                continue
            # 5. Same-ID collision, no declaration → reworded advisory
            if art_id in built_in_ids_per_kind.get(plural, set()):
                issues.append(ValidationIssue(
                    severity="advisory",
                    category="same_id_collision",
                    ...,
                    message=(
                        f"artifact id {art_id!r} will field-merge into the "
                        f"built-in {kind_singular(plural)} — declare "
                        f"'enhances: {art_id}' to suppress this advisory, "
                        f"or 'overrides: {art_id}' to declare a full replacement"
                    ),
                ))
    return issues
```

Update the call site (around line 247-249) to pass the new arguments.

### T038 — Add validator categories

**Files**: `src/specify_cli/doctrine/pack_validator.py`

Update the `category` enum/literal and the docstring at the top of the file to list `unknown_target` and `intent_conflict` as valid categories alongside the existing `schema_invalid`, `drg_dangling_edge`, `same_id_collision`. Verify `render_validation_result` formats the new categories correctly.

### T039 — Tests

**Files**: `tests/specify_cli/doctrine/test_pack_validator.py` (extend), NEW `tests/doctrine/drg/test_org_pack_auto_emit.py`

Cases:
1. **FR-013 / advisory suppression**: pack tactic with `enhances: <built-in-id>` → no advisory.
2. **FR-013 / advisory suppression**: pack tactic with `overrides: <built-in-id>` → no advisory.
3. **FR-013 / reworded wording**: pack tactic with same-ID collision, no declaration → advisory message contains "field-merge" and both `'enhances: ...'` and `'overrides: ...'` recommendations.
4. **FR-011 / intent_conflict**: pack tactic with both fields → ERROR with category `intent_conflict`.
5. **FR-012 / unknown_target**: pack tactic with `enhances: bogus-id` → ERROR with category `unknown_target` mentioning the missing target.
6. **FR-012 / unknown_target**: pack tactic with `overrides: bogus-id` → same.
7. **FR-014 / auto-emit**: load a pack fragment after declaring `enhances: foo` → DRG fragment contains an edge with `relation=Relation.ENHANCES`, `source=tactic:<pack-id>`, `target=tactic:foo`.
8. **FR-014 / auto-emit dedupe**: if author also hand-authored the same edge, only one survives.

## Definition of Done

- [ ] `Relation.ENHANCES` and `Relation.OVERRIDES` exist; `REPLACES` unchanged.
- [ ] `org_pack_loader` auto-emits both edges with reason text.
- [ ] `_intent_aware_collision_messages` implements the full precedence table.
- [ ] `unknown_target` and `intent_conflict` categories surface in JSON output and human banner.
- [ ] All 8 test cases pass.
- [ ] `mypy --strict` and `ruff check` pass.

## Risks

- **Existing pack fragments**: any in-repo pack that already uses `relation: replaces` continues to work (R-2). Document this in commit message.
- **Existing test fixtures asserting old advisory wording**: WP08 will own the test migration. This WP only needs to update tests that live under `tests/specify_cli/doctrine/`. Cross-cutting tests in `tests/integration/` may break — flag for WP08.

## Reviewer guidance

1. Verify the advisory text exactly matches `contracts/pack-validator-advisory.md` — copy-paste comparison.
2. Verify the precedence ordering: intent_conflict trumps unknown_target trumps suppression trumps same_id_collision.
3. Verify deduplication of auto-emitted edges (test 8).

## Activity Log

- 2026-05-24T08:47:14Z – claude:opus-4-7:python-pedro:implementer – shell_pid=986427 – Assigned agent via action command
- 2026-05-24T09:01:12Z – claude:opus-4-7:python-pedro:implementer – shell_pid=986427 – Ready for review: Relation enum + auto-emit + intent-aware advisory
- 2026-05-24T09:02:10Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=1048306 – Started review via action command
- 2026-05-24T09:05:20Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=1048306 – Review passed: Relation enum extended (ENHANCES/OVERRIDES added, REPLACES retained, exported via __init__), auto-emit + dedupe working for all 5 augmentation kinds, intent-aware advisory implements full precedence table (intent_conflict > unknown_target > suppression > same_id_collision), reworded same_id_collision text contains 'field-merge' + both enhances/overrides recommendations matching contract rule 5, 24 tests pass (8/8 required cases + extras), ruff clean on WP-owned files (pre-existing unused-import in src/specify_cli/doctrine/config.py is out of WP scope)
- 2026-05-24T11:46:53Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=1048306 – Done override: Feature merged to main as squash commit 37407a3b2; status carried through from mission branch
