---
work_package_id: WP09
title: Operator UX (doctrine new + validate + doctor doctrine Selections) + Glossary Promotion
dependencies:
- WP04
- WP06
requirement_refs:
- FR-016
- FR-017
- FR-018
- NFR-006
- C-006
- C-007
planning_base_branch: feat/org-doctrine-layer
merge_target_branch: feat/org-doctrine-layer
branch_strategy: Planning artifacts for this mission were generated on feat/org-doctrine-layer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/org-doctrine-layer unless the human explicitly redirects the landing branch.
subtasks:
- T048
- T049
- T050
- T051
agent: "claude:opus-4-7:reviewer-renata:reviewer"
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/doctrine.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/doctrine.py
- src/specify_cli/cli/commands/doctor.py
- glossary/contexts/doctrine.md
- docs/explanation/org-doctrine-layer.md
- tests/specify_cli/cli/commands/test_doctrine_new.py
- tests/specify_cli/cli/commands/test_doctrine_validate.py
- tests/specify_cli/cli/commands/test_doctor_doctrine_selections.py
- tests/cli/test_doctor_doctrine_selections_snapshot.py
- tests/cli/__snapshots__/doctor_doctrine_selections.txt
role: implementer
history: []
tags: []
shell_pid: "1816945"
---

## Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Add three operator-facing CLI surfaces:

1. **`spec-kitty doctrine new <kind> <name>`** — scaffolds a stub artifact YAML in `.kittify/doctrine/<kind>/` (or `<pack_path>/<kind>s/` with `--pack`).
2. **`spec-kitty doctrine validate <path>`** — validates a single artifact YAML or a doctrine tree against the schemas (project-layer analogue of `pack validate`).
3. **Extended `spec-kitty doctor doctrine`** — new "Selections" section listing, per kind, the active globally-selected artifacts with resolved pack source.

Plus the C-006 user-doc update for the missing-pack policy change (landed in WP06; this WP makes sure the docs are explicit). Plus the C-007 glossary promotion of 10 candidate entries to canonical.

---

## Context

This is operator-experience polish that turns the new mechanism into a discoverable tool. Without these, users can extend the charter but have no scaffolding gesture and no audit surface for what's active.

The 10 candidate glossary entries are already drafted in `glossary/contexts/doctrine.md`; they just need their `Status: candidate` flipped to `Status: canonical`.

See:
- [plan.md §2.12](../plan.md)
- [spec.md "Acceptance Criteria"](../spec.md)

---

## Branch Strategy

- **Planning/base**: `feat/org-doctrine-layer`
- **Merge target**: `feat/org-doctrine-layer`
- **Implement command**: `spec-kitty agent action implement WP09 --agent claude`

---

## Subtasks

### T048 — `spec-kitty doctrine new <kind> <name>` command

**File**: `src/specify_cli/cli/commands/doctrine.py`

Add a typer subcommand:

```python
@app.command()
def new(
    kind: Annotated[str, typer.Argument(help="Artifact kind: styleguide, toolguide, directive, ...")],
    name: Annotated[str, typer.Argument(help="Artifact ID (kebab-case)")],
    pack: Annotated[Path | None, typer.Option("--pack", help="Target a pack instead of project")] = None,
) -> None:
    """Scaffold a stub doctrine artifact YAML."""
    ...
```

The scaffolder:

- Validates `kind` is one of the 8 canonical kinds.
- Resolves the target directory: `.kittify/doctrine/<kind>/` (project) or `<pack>/<kind>s/` (`--pack`).
- Writes a stub `<name>.<kind>.yaml` populated with the required schema fields (`schema_version`, `id`, plus kind-specific placeholders).
- Refuses to overwrite an existing file (use `--force` to override — out of scope here).

Stub example for a styleguide:

```yaml
schema_version: "1.0"
id: <name>
title: TODO — short title
scope: code   # or docs / generic
applies_to_languages: []
principles: []
patterns: []
```

### T049 — `spec-kitty doctrine validate <path>` command

```python
@app.command()
def validate(
    path: Annotated[Path, typer.Argument(help="Artifact YAML or doctrine tree")],
) -> None:
    """Validate a project-layer artifact or doctrine tree against schemas."""
    ...
```

Behaviour:

- If `path` is a file: validate single artifact against the schema for its detected kind.
- If `path` is a directory: walk for `*.yaml` files, validate each.
- Exit 0 on all-valid; non-zero on any failure with per-file error report.

Reuse validation from `pack_validator.py` where possible (the schemas are the same).

### T050 — Extend `spec-kitty doctor doctrine` with Selections section

**File**: `src/specify_cli/cli/commands/doctor.py`

After the existing Collisions / Packs sections, add:

```
Selections (active globally-selected artifacts):
  directives:
    - DIRECTIVE_032         (source: built-in)
  styleguides:
    - caveman-comments      (source: project)
    - python-conventions    (source: org:very-serious-developers)
  toolguides: (none)
  ...
  agent_profiles:
    - python-pedro          (source: built-in)
```

The data source is the resolved `DoctrineSelectionConfig` (after project + org pre-fill + mission-type profile union). Provenance from the same `org_source_map` mechanism WP04 introduced.

**Definition of Done (resolves analysis-report finding U1):** the Selections section format MUST be pinned by a snapshot test in `tests/cli/test_doctor_doctrine_selections_snapshot.py` that fixtures a known charter + activation registry state and asserts the rendered Selections section verbatim. The snapshot file lives at `tests/cli/__snapshots__/doctor_doctrine_selections.txt`. The snapshot covers (a) at least one kind with multiple sources (`built-in`, `project`, `org:<pack>`), (b) at least one empty kind rendered as `(none)`, and (c) the exact provenance suffix format. The snapshot file is regenerated only by deliberate operator intent; CI compares byte-for-byte.

### T051 — Glossary promotion + missing-pack doc note

**File**: `glossary/contexts/doctrine.md`

For each of the 10 entries (`Charter-Mediated Selection`, `Global Selection`, `Context-Scoped Selection`, `Activation Registry`, `Activation Context`, `Doctrine Pack ID`, `Trigger Registry`, `Charter Facade`, `Mission-Type Profile`, `selected_<kind>` / `required_<kind>`), flip:

```
| **Status** | candidate |
```

To:

```
| **Status** | canonical |
```

**File**: `docs/explanation/org-doctrine-layer.md` (or equivalent user-facing doc covering pack configuration)

Add a section calling out the FR-015 policy change:

> ### Breaking change (mission B): missing packs hard-fail
>
> Prior to mission `charter-mediated-doctrine-selection-01KRTZCA`, a doctrine pack configured in `.kittify/config.yaml` whose `local_path` did not exist on disk was silently skipped. As of this mission, missing packs cause `spec-kitty charter context` and downstream commands to fail loudly with a message naming the pack and the missing path.
>
> Migration: run `spec-kitty doctrine fetch --pack <name>` for each configured pack before upgrading, or remove stale entries from `.kittify/config.yaml`.

---

## Definition of Done

- ✅ `spec-kitty doctrine new styleguide my-test` writes a valid YAML to `.kittify/doctrine/styleguide/my-test.styleguide.yaml`
- ✅ `spec-kitty doctrine validate .kittify/doctrine/styleguide/my-test.styleguide.yaml` exits 0
- ✅ `spec-kitty doctor doctrine` output includes a "Selections" section
- ✅ `tests/cli/test_doctor_doctrine_selections_snapshot.py` GREEN; snapshot at `tests/cli/__snapshots__/doctor_doctrine_selections.txt` matches the rendered output byte-for-byte (resolves analysis-report finding U1)
- ✅ All 10 glossary entries in `glossary/contexts/doctrine.md` carry `Status: canonical`
- ✅ User docs include the FR-015 policy-change note
- ✅ New CLI integration tests cover happy paths for `doctrine new`, `doctrine validate`, and the extended `doctor doctrine` output
- ✅ `tests/specify_cli/next/test_wp_prompt_governance_contract.py` — 23/23 stays green
- ✅ Acceptance criterion 7 (glossary promotion) satisfied

---

## Risks

| Risk | Mitigation |
|------|------------|
| Glossary promotion happens before implementation lands → drift between definitions and behaviour | Promotion is the LAST step of this WP, after WP04–WP08 land. Definitions already match the spec's domain language table. |
| `doctrine new` scaffolds an invalid YAML (incomplete required fields) | Pair with `doctrine validate` in the same flow — the scaffolded stub MUST pass `validate` on first emit. Test fixture verifies. |
| `doctor doctrine` Selections section breaks on missing org pack | Defer to FR-015 hard-fail; the doctor command should report the error instead of crashing. |
| User docs land in the wrong file | Coordinate with WP06 (which also touches user docs for the same policy change). Single owner ensures one final paragraph. |

---

## Reviewer Guidance

- Run `spec-kitty doctrine new styleguide foo` then `spec-kitty doctrine validate .kittify/doctrine/styleguide/foo.styleguide.yaml` end-to-end; exit codes 0 / 0.
- Verify all 10 glossary entries flipped to `Status: canonical` — grep for `Status \| candidate` returns zero hits in the Mission B-affected sections.
- Verify the user-doc note names the FR-015 policy change with concrete remediation steps.
- Spot-check the doctor output formatting — provenance suffix readable, no empty sections shown.

## Activity Log

- 2026-05-17T18:38:00Z – claude:opus-4-7:python-pedro:implementer – shell_pid=1790218 – Started implementation via action command
- 2026-05-17T18:58:21Z – claude:opus-4-7:python-pedro:implementer – shell_pid=1790218 – Operator UX (doctrine new/validate + doctor doctrine Selections snapshot-tested) + 10 glossary entries promoted to canonical. Mission B closing WP.
- 2026-05-17T18:59:07Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=1816945 – Started review via action command
- 2026-05-17T19:04:14Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=1816945 – Review passed (closing WP): doctrine new + validate CLI + doctor doctrine Selections (snapshot-pinned); 10 glossary entries promoted to canonical (C-007); FR-015 breaking-change documented. All prior-WP ATDDs/architectural ratchets green. Mission B is complete and ready for merge.
