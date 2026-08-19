---
work_package_id: WP04
title: --include selector widening (glossary_pack + anti_pattern)
dependencies:
- WP03
requirement_refs:
- FR-006
planning_base_branch: spec/charter-resolution-parity
merge_target_branch: spec/charter-resolution-parity
branch_strategy: Planning artifacts for this mission were generated on spec/charter-resolution-parity. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into spec/charter-resolution-parity unless the human explicitly redirects the landing branch.
subtasks:
- T020
- T021
- T022
- T023
- T024
history:
- Created by /spec-kitty.tasks (M1 charter-resolution program)
agent_profile: python-pedro
authoritative_surface: src/charter/context_renderers/
create_intent:
- tests/charter/context_renderers/test_include_selector_widening.py
execution_mode: code_change
owned_files:
- src/charter/context_renderers/template_include.py
- tests/charter/context_renderers/test_include_selector_widening.py
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

Make every charter-activatable kind a **recognized** `--include <kind>:<id>` selector kind, so a correctly-derived stanza **resolves** instead of erroring on an unknown selector (FR-006 / SC-003).

- **SC**: `charter context --include glossary_pack:<id>` renders the glossary pack (via `service.glossary_packs`).
- **SC**: `charter context --include anti_pattern:<id>` resolves to a standard "No anti_pattern found for selector …" not-found — **never** "Unsupported --include selector kind".
- **SC (S1)**: no `CHARTER_ACTIVATABLE_KINDS` member hits the "Unsupported selector kind" path.

## Context & Constraints

Read `contracts/kind-vocabulary.md` §"FR-006 selector recognition" and `research.md` §D-5. Verified:
- `charter/context.py` dispatch resolves the kind via `_resolve_include_kind` → `ArtifactKind.from_operator_token` (already accepts all 12 kinds), then calls `_render_catalog_kind_include_selector`; when that returns `None`, it raises `ValueError("Unsupported --include selector kind '<kind>'.")`.
- The real gap is in `charter/context_renderers/template_include.py::_render_doctrine_artifact_include`: a **hardcoded 6-kind `renderers` dict** (paradigm, styleguide, toolguide, procedure, agent_profile, mission_step_contract). `glossary_pack` and `anti_pattern` are absent → returns `None` → "Unsupported selector kind".
- `service.glossary_packs` exists (real repo). `anti_pattern` ships **no** artifact file (per `artifact_kinds.py`) and has no service repo.

**Constraints**: zero suppressions (C-005); charter → doctrine only (C-006). Keep the existing render shape for the 6 kinds unchanged.

## Branch Strategy
Planning base **`spec/charter-resolution-parity`**; merge target **`spec/charter-resolution-parity`**. Worktrees per computed lane from `lanes.json`. Depends on WP03 (derive the recognized-selector-kind set from the shared vocabulary authority).

## Subtasks & Detailed Guidance

### Subtask T020 – Red: `--include glossary_pack:<id>` unsupported
Write `tests/charter/context_renderers/test_include_selector_widening.py`. Drive the include path (via `charter.context._render_include_selector` or the narrower `_render_doctrine_artifact_include`) for `glossary_pack:<id>` against a service exposing a `glossary_packs` repo with a known pack. **Assert it renders** the pack label + body. This **fails** on `main` with "Unsupported --include selector kind 'glossary_pack'".

### Subtask T021 – Red: `--include anti_pattern:<id>` unsupported [P]
Same module: drive `anti_pattern:<id>`. **Assert** the error raised is the **not-found** form (`"No anti_pattern found for selector 'anti_pattern:<id>'."`) — i.e. the kind is *recognized* — **not** the "Unsupported --include selector kind" form. **Fails** pre-fix (currently unsupported-kind).

### Subtask T022 – Add `glossary_pack` renderer
In `_render_doctrine_artifact_include.renderers`, add:
```python
"glossary_pack": ("glossary_packs", "Glossary pack", "name", _format_inline_glossary_pack_body),
```
Choose the correct title attribute for the glossary-pack model (inspect `GlossaryPackRepository`'s model — likely `name` or `title`) and reuse an existing inline body formatter if one exists; otherwise add a minimal `_format_inline_glossary_pack_body` consistent with the sibling formatters (keep it small and typed). The existing `repo.get(identifier)` + not-found `ValueError` path then applies unchanged.

### Subtask T023 – Make `anti_pattern` recognized (not unsupported)
`anti_pattern` has no service repo and no artifact files, so it cannot render a file-based artifact — but it must not fall through to "Unsupported selector kind". Add a recognized branch that yields the standard not-found for the kind, e.g. an `anti_pattern` entry whose repo attr resolves to `None` and thus raises the existing `ValueError(f"No {kind} found for selector '{kind}:{identifier}'.")`. Ensure the code path is the not-found branch, never the caller's unsupported-kind branch. Prefer deriving the recognized-kind coverage from `CHARTER_ACTIVATABLE_KINDS` where clean, so a future kind cannot silently become "unsupported".

### Subtask T024 – Green + S1 coverage
- Make T020/T021 pass.
- Add a parametrized test asserting **every** `CHARTER_ACTIVATABLE_KINDS` operator token, when passed to the include path with a non-existent id, raises the *not-found* form (or renders) — **never** the "Unsupported --include selector kind" form (S1). This is the durable guard that the selector vocabulary tracks the activatable vocabulary.
- Record: `spec-kitty agent tasks mark-status T020 T021 T022 T023 T024 --status done --mission single-authority-resolution-parity-01M0CEBQ`.

## Test Strategy
Red-first (T020/T021). Reuse the existing `tests/charter/context_renderers/` service doubles/fixtures if present. Markers per that package's convention. Run: `PATH=.venv/bin:$PATH SPEC_KITTY_SYNC_DISABLE=1 pytest tests/charter/context_renderers/test_include_selector_widening.py -q`. Also run the existing include tests to prove the 6 unchanged kinds still render.

## Risks & Mitigations
- **Wrong glossary-pack title attr** → inspect the model; fall back to `identifier` like sibling renderers do (`getattr(artifact, title_attr, identifier)`).
- **anti_pattern accidentally full-rendering** → intended semantics is recognized-but-not-found; assert the exact not-found message (T021).
- **S1 test brittleness** → derive the expected kind set from `CHARTER_ACTIVATABLE_KINDS`, not a hand list.

## Review Guidance
Verify: `glossary_pack` renders; `anti_pattern` returns the not-found (recognized) form; the 6 original kinds unchanged; S1 parametrized guard present and derived from the authority; zero suppressions; `mypy --strict` clean on `template_include.py`.

## Activity Log
- (implementer appends entries here)
