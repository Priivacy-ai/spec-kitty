---
work_package_id: WP04
title: Render authority paths and critical-section bodies in compact and bootstrap text
dependencies:
- WP02
- WP03
requirement_refs:
- FR-001
- FR-003
- NFR-004
planning_base_branch: feat/org-doctrine-layer
merge_target_branch: feat/org-doctrine-layer
branch_strategy: Planning artifacts for this mission were generated on feat/org-doctrine-layer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/org-doctrine-layer unless the human explicitly redirects the landing branch.
subtasks:
- T014
- T015
- T016
- T017
- T018
agent: "claude:opus-4-7:python-pedro:implementer"
agent_profile: python-pedro
authoritative_surface: src/charter/context_renderers/
execution_mode: code_change
owned_files:
- src/charter/context_renderers/authority_paths.py
- src/charter/context_renderers/section_bodies.py
- tests/charter/test_context_authority_paths.py
- tests/charter/test_context_section_bodies.py
role: implementer
history: []
tags: []
shell_pid: "1138959"
---

## Objective

Extend `charter.context` so the bootstrap render emits two structural sections that the
ATDD suite requires:

1. `Project authority paths:` — bulleted list naming `glossary/contexts/` and
   `architecture/2.x/adr/` when those directories exist, plus every path declared in
   `DoctrineSelectionConfig.authority_paths` (populated by WP02). Each line carries a
   one-sentence "When you …, …" conditional. (FR-003)
2. `Action-Critical Charter Sections (<action>):` — the **verbatim body** of each
   action-critical charter section, with Terminology Canon / Code Review Checklist /
   Regression Vigilance as the `software-dev` defaults. When a body is missing from the
   charter, the resolver emits the fetch + when-doing stanza instead (the renderer never
   crashes on a missing section). (FR-001)

ATDD tests turned green by this WP:

- `TestImplementPromptRegressionVigilance::test_implement_prompt_regression_vigilance_body_or_fetch_with_when_doing_rule`
- `TestImplementPromptAuthorityPaths::test_implement_prompt_references_glossary_path`
- `TestImplementPromptAuthorityPaths::test_implement_prompt_references_adr_path`

---

## Module organisation note

To keep ownership boundaries clean between WP03, WP04, and WP05 (all of which extend
`src/charter/context.py`), the helpers introduced here MUST live in a new submodule
`src/charter/context_renderers/`:

- `src/charter/context_renderers/authority_paths.py` — `_render_authority_paths` (T014)
- `src/charter/context_renderers/section_bodies.py` — `_render_critical_section_bodies` (T015)

`src/charter/context.py` imports from this submodule. The wiring change to
`_render_bootstrap_text` in T016 is a small edit to `context.py` (a few lines: import +
call); this is intentionally narrow so it does not cross the WP03 / WP05 ownership
slices.

---

## Context

The bootstrap and compact renderers in `src/charter/context.py` already emit several
sections (`Charter Context (Bootstrap):`, `Policy Summary:`, `Action Doctrine:`,
`Reference Docs:`). The mission's contract (data-model.md §3) inserts two new sections
between `Policy Summary:` and `Action Doctrine:`:

| # | Section header | This WP adds? |
|---|---|---|
| 3 | `Project authority paths:` | Yes (FR-003) |
| 4 | `Action-Critical Charter Sections (<action>):` | Yes (FR-001) |
| 5 | `Profile-Cited Directives (...):` | Already added in WP03 |
| 6 | `Profile-Cited Tactics (...):` | Already added in WP03 |

The order matters because the ATDD self-sufficiency test (test 7) greps for these
headers as anchors.

---

## Branch Strategy

- **Planning/base branch**: `feat/org-doctrine-layer`
- **Merge target**: `feat/org-doctrine-layer`
- **Worktree**: allocated by `finalize-tasks`
- **Implement command**: `spec-kitty agent action implement WP04 --agent claude`

---

## Subtask T014 — Add `_render_authority_paths(repo_root, doctrine_selection)`

**File**: `src/charter/context.py`

```python
_DEFAULT_AUTHORITY_PATHS: dict[str, str] = {
    "glossary/contexts/": "canonical terminology — when you encounter a domain term in the diff, grep this directory",
    "architecture/2.x/adr/": "architectural intent — when you change a structural boundary, read the relevant ADR",
}


def _render_authority_paths(
    repo_root: Path,
    doctrine_selection: DoctrineSelectionConfig,
) -> str:
    """Render the 'Project authority paths:' section.

    - Default entries (glossary/contexts/, architecture/2.x/adr/) appear when the
      directory exists in repo_root.
    - Each path in doctrine_selection.authority_paths is appended (dedup against defaults).
    - Each line has the form ``  - <path>    (<when-doing conditional>)``.
    - Returns the empty string when no paths qualify.
    """
```

The when-doing copy for non-default (charter-declared) paths defaults to:
`"consult when you change content under this directory"`. A future WP may parameterise this; for now it is acceptable to keep it generic.

---

## Subtask T015 — Add `_render_critical_section_bodies(charter_content, action)`

**File**: `src/charter/context.py`

```python
_ACTION_CRITICAL_SECTIONS: dict[str, list[str]] = {
    "implement": ["Terminology Canon", "Code Review Checklist", "Regression Vigilance"],
    "review":    ["Terminology Canon", "Code Review Checklist", "Regression Vigilance"],
    # Other actions (specify, plan, tasks) add their own entries in later missions.
}


def _render_critical_section_bodies(
    charter_content: str,
    action: str,
) -> str:
    """Render 'Action-Critical Charter Sections (<action>):' block.

    For each heading in _ACTION_CRITICAL_SECTIONS[action]:
      - slice the body from the markdown content (heading → next heading at same level).
      - emit ``### <heading>\\n<body verbatim>`` when found.
      - emit fetch + when-doing stanza (selector ``section:<slug>``) when the section
        is missing from the charter.
    """
```

The heading-slicer should reuse any existing helper in `charter.extractor` (e.g.
`_extract_section_body`) rather than reinventing markdown parsing.

`section:<slug>` selector uses kebab-cased heading slug:
- `Terminology Canon` → `section:terminology-canon`
- `Code Review Checklist` → `section:code-review-checklist`
- `Regression Vigilance` → `section:regression-vigilance`

When-doing copy per section (must match the contract in
`contracts/charter-context-resolver.md`):

| Section | When-doing clause |
|---|---|
| Terminology Canon | "rename or introduce a term in the diff" |
| Code Review Checklist | "prepare a WP for review" |
| Regression Vigilance | "perform a terminology cutover" |

---

## Subtask T016 — Wire both renderers into `_render_bootstrap_text` and the compact surface

**File**: `src/charter/context.py`

In `_render_bootstrap_text`, after the `Policy Summary:` block and before the existing
`Action Doctrine:` block, splice in the output of `_render_authority_paths` and then
`_render_critical_section_bodies`. The same goes for the compact renderer used on
non-bootstrap actions (if `_governance_context` invokes a compact path for any action,
both surfaces must carry the new sections — verify by reading `_governance_context`
in `src/specify_cli/next/prompt_builder.py`).

The Profile-Cited renderers from WP03 already sit between the new sections and
`Action Doctrine:` in the desired final order; reorder calls in `_render_bootstrap_text`
to match data-model.md §3 numbering exactly.

---

## Subtask T017 — Unit tests for authority paths

**File**: `tests/charter/test_context_authority_paths.py` (new)

| Test | Scenario | Expectation |
|---|---|---|
| `test_default_glossary_path_surfaces_when_directory_present` | repo has `glossary/contexts/` | output contains `glossary/contexts/` and the when-doing copy |
| `test_default_adr_path_surfaces_when_directory_present` | repo has `architecture/2.x/adr/` | output contains `architecture/2.x/adr/` and the when-doing copy |
| `test_default_path_skipped_when_directory_missing` | repo lacks `glossary/contexts/` | the path is NOT in the output (no broken pointer) |
| `test_charter_declared_path_additive` | `authority_paths: [docs/runbooks/]` and the dir exists | output contains the declared path |
| `test_charter_declared_duplicate_of_default_deduped` | `authority_paths: [glossary/contexts/]` (matches default) | output lists `glossary/contexts/` once |
| `test_no_paths_no_section` | repo lacks both defaults; charter declares none | output does NOT contain the `Project authority paths:` header |

---

## Subtask T018 — Unit tests for section bodies

**File**: `tests/charter/test_context_section_bodies.py` (new)

| Test | Scenario | Expectation |
|---|---|---|
| `test_terminology_canon_body_surfaces_verbatim_when_present` | Charter has `## Terminology Canon` with a body | output contains the `### Terminology Canon` header and the body text verbatim |
| `test_missing_section_emits_fetch_stanza` | Charter lacks `## Regression Vigilance` | output contains `section:regression-vigilance` selector + `When you perform a terminology cutover, …` line |
| `test_action_implement_uses_implement_section_set` | action=`implement` | the three default headings are included |
| `test_action_review_uses_review_section_set` | action=`review` | same three headings (per `_ACTION_CRITICAL_SECTIONS` default) |
| `test_unknown_action_emits_no_section` | action=`unknown-action` (no entry in the map) | the `Action-Critical Charter Sections` block is omitted |

---

## Definition of Done

- [ ] `_render_authority_paths` and `_render_critical_section_bodies` exist and are unit-tested.
- [ ] `_render_bootstrap_text` (and the compact renderer if used by `_governance_context`) call both helpers in the order required by data-model.md §3.
- [ ] `tests/charter/test_context_authority_paths.py` passes (6 tests).
- [ ] `tests/charter/test_context_section_bodies.py` passes (5 tests).
- [ ] ATDD `test_implement_prompt_regression_vigilance_body_or_fetch_with_when_doing_rule` passes.
- [ ] ATDD `test_implement_prompt_references_glossary_path` passes.
- [ ] ATDD `test_implement_prompt_references_adr_path` passes.
- [ ] `tests/architectural/test_layer_rules.py` (8 tests) still passes.
- [ ] All 14 currently-passing ATDD tests remain green.

---

## Risks

- **R-1**: The heading-slicer mis-slices when a section's body contains nested headings
  at lower levels. **Mitigation**: reuse an existing `extractor` helper; add a fixture
  with a nested-heading body and assert the full slice survives.
- **R-2**: Listing `architecture/2.x/adr/` as a default may surface a path that exists
  but contains zero ADRs (just a `README.md`). **Mitigation**: existence check only —
  the path is a pointer, not a guarantee of content. The Mission Review skill is the
  appropriate place to enforce content quality, not this resolver.
- **R-3**: The compact renderer (if used for non-bootstrap actions) lags behind the
  bootstrap renderer's structure. **Mitigation**: T016 explicitly wires both surfaces;
  reviewer verifies both code paths.

---

## Reviewer Guidance

Check that:

1. The section headers in the rendered output match the exact strings the ATDD assertions
   grep for: `Project authority paths:` and `Action-Critical Charter Sections (<action>):`.
2. The default authority-paths dict uses **trailing slashes** (`glossary/contexts/`, not
   `glossary/contexts`) so the ATDD assertions that match `glossary/contexts/` pass.
3. The when-doing copy for each section matches the contract in
   `contracts/charter-context-resolver.md` verbatim — drift here is a contract violation.
4. When a section heading is missing from the charter, the renderer emits the fetch
   stanza (not an empty body or a crash).
5. The dedup logic in `_render_authority_paths` is order-preserving (defaults first,
   charter-declared paths appended in declaration order).
6. The compact-context surface (if invoked) is wired identically to the bootstrap surface.

## Activity Log

- 2026-05-16T12:39:05Z – claude:opus-4-7:python-pedro:implementer – shell_pid=1138959 – Started implementation via action command
