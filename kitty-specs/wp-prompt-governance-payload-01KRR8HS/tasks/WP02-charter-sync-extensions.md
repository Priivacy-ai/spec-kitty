---
work_package_id: WP02
title: charter sync — catalog-citation detection + authority_paths extraction
dependencies:
- WP01
requirement_refs:
- FR-006
- FR-007
- FR-008
- NFR-005
planning_base_branch: feat/org-doctrine-layer
merge_target_branch: feat/org-doctrine-layer
branch_strategy: Planning artifacts for this mission were generated on feat/org-doctrine-layer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/org-doctrine-layer unless the human explicitly redirects the landing branch.
subtasks:
- T004
- T005
- T006
- T007
- T008
agent: "claude:opus-4-7:python-pedro:implementer"
agent_profile: python-pedro
authoritative_surface: src/charter/extractor.py
execution_mode: code_change
owned_files:
- src/charter/extractor.py
- src/charter/sync.py
- tests/charter/test_sync_references.py
- tests/charter/test_sync_authority_paths.py
role: implementer
history: []
tags: []
shell_pid: "1095915"
---

## Objective

Teach `spec-kitty charter sync` to:

1. **Detect catalog citations** inside the body of each charter-extracted directive.
   When a `DIRECTIVE_\d{3}` ID or a known tactic-id slug appears in the description, lift
   it into `Directive.references` (FR-006).
2. **Read the resolver-input declaration block** from the charter's fenced YAML and
   persist `template_set:`, `available_tools:`, and `authority_paths:` into
   `DoctrineSelectionConfig` (FR-007, FR-008).

After this WP, the ATDD test
`TestCharterSyncEmitsCrossLinkWhenBodyCitesCatalogId::test_charter_sync_emits_cross_link_when_body_cites_catalog_id`
turns green, and the fenced-YAML extraction unblocks WP04 (which renders authority
paths) and WP07 (which writes the dogfood charter block).

---

## Context

`charter.extractor.Extractor._extract_directives` (around `src/charter/extractor.py:263`)
today parses charter Markdown's numbered-items into `Directive` records but does **not**
look inside the body for catalog references. The extracted `DIR-NNN` record loses the
`DIRECTIVE_032` mention that may sit in the description, breaking journey 4 of the spec.

`Extractor._merge_doctrine_selection` (`src/charter/extractor.py:198-261`) already reads
`template_set` and `available_tools` via `_apply_selection_row`, but does **not** scan
fenced YAML blocks for top-level keys, so a charter that declares them in a fenced YAML
block (as the FR-007 user-journey requires) is ignored.

This WP closes both gaps in one sync change so WP07 can dogfood the result.

---

## Branch Strategy

- **Planning/base branch**: `feat/org-doctrine-layer`
- **Merge target**: `feat/org-doctrine-layer`
- **Worktree**: allocated by `finalize-tasks`
- **Implement command**: `spec-kitty agent action implement WP02 --agent claude`

---

## Subtask T004 — Detection regex helper in `charter.extractor`

**File**: `src/charter/extractor.py`

Add a module-level helper:

```python
_DIRECTIVE_CITATION_RE = re.compile(r"\bDIRECTIVE_(\d{3})\b")
_TACTIC_SLUG_RE = re.compile(r"\b([a-z][a-z0-9]*(?:-[a-z0-9]+){1,4})\b")


def _detect_catalog_references(
    body: str,
    *,
    tactic_registry: Callable[[str], bool],
) -> list[str]:
    """Return catalog IDs cited in *body*.

    - Every ``DIRECTIVE_NNN`` match becomes ``"DIRECTIVE_NNN"``.
    - Every kebab-case slug that ``tactic_registry`` recognises becomes the slug.
    - Duplicates are removed; order is first-seen.
    """
```

`tactic_registry` is a callable so the extractor stays decoupled from `DoctrineService`
construction — the caller (sync orchestration) supplies the lookup.

---

## Subtask T005 — Wire `_detect_catalog_references` into `_extract_directives`

**File**: `src/charter/extractor.py`

In `_extract_directives`, after constructing each `Directive`, populate
`references=_detect_catalog_references(body, tactic_registry=...)`. The `tactic_registry`
is the bound predicate `lambda slug: doctrine_service.tactics.get(slug) is not None`
passed from `charter.sync.sync()`.

If no citations are found, the field defaults to `[]` (per the WP01 schema).

---

## Subtask T006 — Read `authority_paths:` from fenced YAML blocks

**File**: `src/charter/extractor.py`

Extend `Extractor._merge_doctrine_selection` (or add a sibling helper called from the
same site) to iterate every `yaml_blocks` payload extracted from the charter sections
and, when a top-level key `authority_paths:` is present with a list value, append its
entries into `DoctrineSelectionConfig.authority_paths`.

Deduplicate while preserving order. Reject non-string entries with a clear `SyncError`
(or sync warning, per project convention — match existing `_apply_selection_row`
behaviour).

---

## Subtask T007 — Persist `template_set:` / `available_tools:` from the YAML block

**File**: `src/charter/extractor.py`

The existing `_apply_selection_row` reads selection-table rows. Extend the same fenced-
YAML scan from T006 so that a fenced YAML block carrying:

```yaml
template_set: software-dev-default
available_tools:
  - git
  - spec-kitty
  - pytest
  - mypy
  - ruff
```

sets `DoctrineSelectionConfig.template_set` (if currently `None`) and
`DoctrineSelectionConfig.available_tools` (additive — merge, dedupe). When the YAML
block conflicts with a selection-table row, the YAML block wins (it is the more
explicit declaration); emit an `info`-level sync diagnostic noting the override.

This is what makes FR-007 (and the FR-009 dogfood) work: after this WP, a charter
declaring the resolver-input block produces no `Template set not selected in charter;
fallback ... applied` diagnostic.

---

## Subtask T008 — Unit tests

**File**: `tests/charter/test_sync_references.py` (new), `tests/charter/test_sync_authority_paths.py` (new)

`test_sync_references.py`:

| Test | Scenario | Expectation |
|---|---|---|
| `test_body_with_DIRECTIVE_032_yields_reference` | Body: `"... (DIRECTIVE_032 — Conceptual Alignment)"` | `Directive.references == ["DIRECTIVE_032"]` |
| `test_body_with_known_tactic_slug_yields_reference` | Body: `"... apply language-driven-design ..."`; registry knows `language-driven-design` | `references == ["language-driven-design"]` |
| `test_body_with_unknown_kebab_slug_yields_no_reference` | Body: `"my-random-words"`; registry rejects | `references == []` |
| `test_body_with_multiple_citations_dedupes` | Body cites `DIRECTIVE_010` twice + `DIRECTIVE_032` once | `references == ["DIRECTIVE_010", "DIRECTIVE_032"]` (order-preserved) |
| `test_body_without_citations_emits_empty_list` | Plain text body | `references == []`; sync does not error |

`test_sync_authority_paths.py`:

| Test | Scenario | Expectation |
|---|---|---|
| `test_fenced_yaml_authority_paths_extracted` | Charter section with fenced YAML block `authority_paths: [glossary/contexts/, architecture/2.x/adr/]` | `config.doctrine.authority_paths` contains both |
| `test_fenced_yaml_template_set_extracted` | Block `template_set: software-dev-default` | `config.doctrine.template_set == "software-dev-default"` |
| `test_fenced_yaml_available_tools_merges_with_existing` | Block `available_tools: [pytest, mypy]`; selection table already had `[git]` | Result deduplicated `[git, pytest, mypy]` |
| `test_charter_without_yaml_block_unchanged` | Charter with no fenced YAML block | Sync still succeeds; fallback diagnostic emitted (today's behaviour) |
| `test_non_string_authority_path_rejected` | Block `authority_paths: [123]` | `SyncError` (or sync warning per convention) |

---

## Definition of Done

- [ ] `Extractor._extract_directives` populates `Directive.references` from cited catalog IDs.
- [ ] `Extractor._merge_doctrine_selection` (or sibling) reads `template_set`, `available_tools`, and `authority_paths` from fenced YAML blocks.
- [ ] `tests/charter/test_sync_references.py` passes (5 tests).
- [ ] `tests/charter/test_sync_authority_paths.py` passes (5 tests).
- [ ] ATDD test `test_charter_sync_emits_cross_link_when_body_cites_catalog_id` passes.
- [ ] All existing `tests/charter/test_sync*.py` tests still pass (no regression).
- [ ] `tests/architectural/test_layer_rules.py` (8 tests) still passes.
- [ ] NFR-005 verified: a charter without any of the new YAML blocks syncs successfully and emits the same fallback diagnostics it does today.

---

## Risks

- **R-1**: Citation regex emits false positives on incidental `DIRECTIVE_001`-style text
  inside example blocks. **Mitigation**: per the plan's R-2 entry, this is acceptable
  noise; the token-budget mechanism (WP05) trims any bloat.
- **R-2**: Tactic-slug detection collides with arbitrary kebab-case words (`my-random-thing`).
  **Mitigation**: registry filter (`tactic_registry(slug)` predicate). Only registered
  slugs count as references.
- **R-3**: A charter that already uses a selection-table row plus a fenced YAML block
  declaring the same `template_set` ends up with conflicting sources. **Mitigation**:
  YAML block wins; an `info`-level diagnostic surfaces the override. Documented in T007.

---

## Reviewer Guidance

Check that:

1. The detection regex helpers in `extractor.py` are tested for the false-positive cases
   listed in the risks (especially the unknown-slug case).
2. `Directive.references` is **never** populated with `DIR-NNN` IDs (those are the
   charter-extracted namespace; only catalog IDs `DIRECTIVE_NNN` and tactic-slug strings
   belong there).
3. The fenced-YAML scan is order-independent (a YAML block can appear in any section,
   not just `## Charter Resolution Hints`).
4. The dedup logic preserves order (first-seen wins on identity).
5. `tests/architectural/test_layer_rules.py` still passes — `charter.extractor` must not
   import from `specify_cli`.
6. Backward-compat path: load an existing `.kittify/charter/charter.md` (e.g. spec-kitty's
   own pre-mission charter copy) and confirm sync still succeeds end-to-end.

## Activity Log

- 2026-05-16T12:00:39Z – claude:opus-4-7:python-pedro:implementer – shell_pid=1095915 – Started implementation via action command
- 2026-05-16T12:17:50Z – claude:opus-4-7:python-pedro:implementer – shell_pid=1095915 – WP02 complete — _detect_catalog_references helper + Directive.references population (FR-006), fenced-YAML resolver-input block extraction for template_set/available_tools/authority_paths (FR-007/FR-008), Code Review Checklist now classified as a directive section to surface DIRECTIVE_032 citations, NFR-005 byte-on-disk preserved via emit_yaml prune of empty optional fields. New tests: tests/charter/test_sync_references.py (10), tests/charter/test_sync_authority_paths.py (7). ATDD TestCharterDirectiveNamespaceCrossLink::test_charter_sync_emits_cross_link_when_body_cites_catalog_id is GREEN. Layer rules 8/8 PASS. Pre-existing tests/charter/ 789/790 (1 unrelated neutrality-lint failure on pytest term in secure-regex tactic).
