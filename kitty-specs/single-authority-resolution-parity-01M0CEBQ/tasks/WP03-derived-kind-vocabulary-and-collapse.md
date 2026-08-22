---
work_package_id: WP03
title: Derived charter-activatable kind vocabulary + collapse hand copies
dependencies: []
requirement_refs:
- C-003
- FR-004
- FR-005
planning_base_branch: spec/charter-resolution-parity
merge_target_branch: spec/charter-resolution-parity
branch_strategy: Planning artifacts for this mission were generated on spec/charter-resolution-parity. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into spec/charter-resolution-parity unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-single-authority-resolution-parity-01M0CEBQ
base_commit: 2fa8069ef2157fe3939537b6befef661e02affcf
created_at: '2026-08-19T14:53:26.590449+00:00'
subtasks:
- T014
- T015
- T016
- T017
- T018
- T019
history:
- Created by /spec-kitty.tasks (M1 charter-resolution program)
agent_profile: python-pedro
authoritative_surface: src/charter/
create_intent:
- tests/doctrine/test_charter_activatable_vocabulary.py
- tests/charter/test_activation_kind_vocab_collapse.py
execution_mode: code_change
owned_files:
- src/doctrine/artifact_kinds.py
- src/charter/activations.py
- src/charter/_activation_render.py
- tests/doctrine/test_charter_activatable_vocabulary.py
- tests/charter/test_activation_kind_vocab_collapse.py
role: implementer
tags: []
tracker_refs:
- '2981'
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile so your boundaries, directives, and
tactics are active:

```
/ad-hoc-profile-load python-pedro
```

Then run `spec-kitty charter context --action implement --json` and apply the resolved
initialization. State which directives/tactics you applied before writing code.

## Objectives & Success Criteria

Introduce **one derived** charter-activatable plural↔singular kind authority (10 kinds = `ArtifactKind − {template, asset}`, **including `anti_pattern`** per C-003/FR-005) and collapse the spec-named hand copies onto it — fixing the two drifted `_activation_render` maps that fail open.

- **SC (FR-004)**: `charter.activations` and `charter._activation_render` declare **no** local plural↔singular kind dict; all read the derived authority.
- **SC (drift fix)**: `_singular_kind("glossary_packs") == "glossary_pack"` (was `"glossary_packs"`); `_infer_kind` finds a `glossary_packs` artifact (was blind).
- **SC (FR-005/C-003)**: exactly 10 activatable kinds including `anti_pattern`; round-trips plural↔singular.

## Context & Constraints

Read `contracts/kind-vocabulary.md` and `research.md` §D-4. Verified current state:
- `activations._SINGULAR_TO_PLURAL_KIND` = 10 kinds, **already equal** to `ArtifactKind − {template, asset}` → deriving it is **behavior-preserving**.
- `_activation_render._singular_kind` inline inverse = **8 kinds** (DRIFTED, missing `glossary_pack`, `anti_pattern`); `.get(plural, plural)` fails open.
- `_activation_render._KIND_TO_PROPERTY` = **8 kinds** (DRIFTED, missing `glossary_packs`, `anti_patterns`); read by `_infer_kind` via `getattr(service, prop, None)`.
- Derive-authority precedents: `doctrine.artifact_kinds.PROJECT_KIND_DIRS` (total literal, gate-visible) and `doctrine.drg.org_pack_loader._derive_plural_to_singular` / `AUGMENTATION_ELIGIBLE_KINDS`.

**Documented NON-GOAL** (do NOT touch): `activations._ALLOWED_KINDS` — an 11-kind *validation frozenset* (includes `templates`/`assets`, excludes `anti_patterns`), **not** a plural↔singular map, **not** named by the spec's duplicator list, and mirrored by `charter.pack_context`. Because `_SINGULAR_TO_PLURAL_KIND`'s membership is unchanged by the collapse, `normalize_artifact_kind`→`_ALLOWED_KINDS` validation stays byte-identical. Reconciling `_ALLOWED_KINDS` is a follow-up, not this mission (avoids C-004-style scope creep). Do not confuse this with the separate `ACTIVATION_YAML_KEYS` config-key vocabulary (already guarded by `test_activation_vocabulary_setequal.py`) — also out of scope.

**Constraints**: authority in the `doctrine` layer (C-006); charter imports down. Zero suppressions (C-005). No golden-count change (C-004 — verified in WP05).

## Branch Strategy
Planning base **`spec/charter-resolution-parity`**; merge target **`spec/charter-resolution-parity`**. Worktrees per computed lane from `lanes.json`. No dependency (parallel with WP01).

## Subtasks & Detailed Guidance

### Subtask T014 – Red: `_singular_kind` drift fails open
Write `tests/charter/test_activation_kind_vocab_collapse.py`. Assert `charter._activation_render._singular_kind("glossary_packs") == "glossary_pack"`. **Fails** on `main` (drifted map returns `"glossary_packs"` unchanged). Add `anti_patterns → anti_pattern` too.

### Subtask T015 – Red: `_infer_kind` blind to glossary_packs [P]
In the same module, build a fake/service double exposing a `glossary_packs` repo that contains a known id, and assert `_infer_kind(id, service) == "glossary_packs"`. **Fails** pre-fix (`_KIND_TO_PROPERTY` lacks `glossary_packs`). Prefer a lightweight stand-in over building the full `DoctrineService` if practical; otherwise use the real service against a `tmp_path` glossary pack.

### Subtask T016 – Add the derived authority in `artifact_kinds`
In `src/doctrine/artifact_kinds.py`, beside `PROJECT_KIND_DIRS`, add:
```python
#: Charter-activatable kinds = every ArtifactKind except the two that resolve
#: specially (template: mission-tier; asset: loose-contract). INCLUDES
#: anti_pattern (C-003/FR-005 — 10 kinds), deliberately distinct from
#: CHARTER_KIND_TOKENS (9) and _NON_AUGMENTATION_ELIGIBLE_KINDS (drops anti_pattern).
CHARTER_ACTIVATABLE_KINDS: frozenset[ArtifactKind] = frozenset(ArtifactKind) - {
    ArtifactKind.TEMPLATE,
    ArtifactKind.ASSET,
}
CHARTER_ACTIVATABLE_SINGULAR_TO_PLURAL: dict[str, str] = {
    k.value: k.plural for k in ArtifactKind if k in CHARTER_ACTIVATABLE_KINDS
}
CHARTER_ACTIVATABLE_PLURAL_TO_SINGULAR: dict[str, str] = {
    plural: singular for singular, plural in CHARTER_ACTIVATABLE_SINGULAR_TO_PLURAL.items()
}
```
Add all three to `__all__` (the `__all__` convention is binding). Write `tests/doctrine/test_charter_activatable_vocabulary.py`: exactly 10 kinds; `ANTI_PATTERN in`, `TEMPLATE/ASSET not in`; round-trip `plural_to_singular[singular_to_plural[s]] == s` for all; ordering derived from `ArtifactKind`.

### Subtask T017 – Collapse `activations` maps
In `charter/activations.py`, replace the `_SINGULAR_TO_PLURAL_KIND` literal with an import/alias of `CHARTER_ACTIVATABLE_SINGULAR_TO_PLURAL`, and `_PLURAL_TO_SINGULAR_KIND` with `CHARTER_ACTIVATABLE_PLURAL_TO_SINGULAR` (or keep the local inverse comprehension over the imported map). Do **not** touch `_ALLOWED_KINDS` (non-goal above). Confirm `normalize_artifact_kind` behavior is unchanged (membership identical). Keep the `__all__` re-export of `normalize_artifact_kind`.

### Subtask T018 – Collapse `_activation_render` maps
In `charter/_activation_render.py`:
- Replace `_singular_kind`'s inline `inverse` dict with `CHARTER_ACTIVATABLE_PLURAL_TO_SINGULAR` (keep the `.get(plural, plural)` fall-through for unknown plurals). This adds `glossary_packs → glossary_pack` and `anti_patterns → anti_pattern`.
- Replace `_KIND_TO_PROPERTY` with a derived `{plural: plural for plural in CHARTER_ACTIVATABLE_SINGULAR_TO_PLURAL.values()}` (property name == plural for every kind). This adds `glossary_packs` (real repo) and `anti_patterns` (inert — `getattr(service, "anti_patterns", None)` returns `None`). Confirm `_infer_kind`'s first-match order for the pre-existing 8 kinds is unchanged (enum order preserved).

### Subtask T019 – Green + assertions
- Make T014/T015 pass.
- Assert no local plural↔singular kind **dict** remains in `activations.py`/`_activation_render.py` (grep-style test or reference the imported authority).
- Assert `anti_patterns` in `_KIND_TO_PROPERTY` is inert (a service without `anti_patterns` yields no crash in `_infer_kind`).
- Record: `spec-kitty agent tasks mark-status T014 T015 T016 T017 T018 T019 --status done --mission single-authority-resolution-parity-01M0CEBQ`.

## Test Strategy
Red-first (T014/T015). Markers per each file's package convention (`doctrine`/`fast` for the doctrine test; `charter`/`unit` for the charter test). Run: `PATH=.venv/bin:$PATH SPEC_KITTY_SYNC_DISABLE=1 pytest tests/doctrine/test_charter_activatable_vocabulary.py tests/charter/test_activation_kind_vocab_collapse.py -q`. Also run the existing `tests/charter/test_activations.py` and `tests/charter/test_activation_vocabulary_setequal.py` to prove no regression in the neighboring vocabularies.

## Risks & Mitigations
- **Accidentally changing `_ALLOWED_KINDS` / `ACTIVATION_YAML_KEYS`** → explicitly out of scope; do not edit. Re-run their guards.
- **`_infer_kind` order change** → derive `_KIND_TO_PROPERTY` from `ArtifactKind` order so the 8 pre-existing kinds keep their positions.
- **Golden ripple from anti_pattern** → these are render/inference helpers, not DRG emission; WP05 asserts zero golden movement.

## Review Guidance
Verify: 10-kind authority with `anti_pattern`, not 9; both `_activation_render` copies now include `glossary_pack`/`anti_pattern`; `_ALLOWED_KINDS` untouched; no local plural↔singular dict left in the two charter modules; `__all__` updated; zero suppressions; `mypy --strict` clean.

## Activity Log
- (implementer appends entries here)
