# Contract: `/spec-kitty.checklist` surface removed; `requirements.md` preserved

**Traces to**: FR-003 (#815), FR-004 (#635), NFR-003, NFR-009, C-003, C-008

## Stimulus

A maintainer runs `spec-kitty init <tmp>` then `/spec-kitty.specify` (and
later `/spec-kitty.plan`, `/spec-kitty.tasks`) against a fresh project, OR
greps the repository for the deprecated command surface.

## Required behavior

1. **Surface removal**: Across the repository AND across every per-agent
   rendered surface for every supported agent (per `CLAUDE.md`
   "Supported AI Agents" table — currently 13 slash-command agents +
   2 skills agents):
   - Zero files named `checklist.md`, `checklist.prompt.md`,
     `checklist.SKILL.md`, or `spec-kitty.checklist.md`.
   - Zero remaining textual references to the literal token
     `/spec-kitty.checklist` (with or without leading slash) inside
     source templates, generated agent copies, registry/manifest entries,
     test fixtures, regression baselines, snapshots, README, or `docs/`
     reference pages.
2. **Artifact preservation**: After running `/spec-kitty.specify` against
   a fresh project, the file
   `kitty-specs/<mission_slug>/checklists/requirements.md` MUST still be
   created with the same content shape as today (Specification Quality
   Checklist).
3. **Bulk-edit gate**: The diff produced by FR-003 work MUST exactly
   match the REMOVE/KEEP classification in
   [`occurrence_map.yaml`](../occurrence_map.yaml). Anything extra
   triggers a DIRECTIVE_035 violation.

## Forbidden behavior

- A no-op shim command that prints "deprecated, use X" — explicitly
  rejected by this tranche (see research.md R3 alternative 1).
- Removing `kitty-specs/<mission>/checklists/requirements.md` (per
  C-003).
- Removing the standalone `RELEASE_CHECKLIST.md` file (unrelated process
  artifact).
- Adding `/spec-kitty.checklist` back into `CANONICAL_COMMANDS` or any
  registry.

## Implementation hint (informative, not normative)

The bulk edit is mechanical given the occurrence map. After removing
sources/templates/manifest entries, regenerate the per-agent baselines
under `tests/specify_cli/regression/_twelve_agent_baseline/<agent>/` so
the snapshot comparison at test time reflects the new reduced surface
for every agent. See
[research.md R3](../research.md#r3--spec-kittychecklist-removal-fr-003--fr-004--815--635).

## Verifying tests

- Update existing tests:
  - `tests/specify_cli/skills/test_registry.py` — drop checklist
    expectations.
  - `tests/specify_cli/skills/test_command_renderer.py` — assert checklist
    is NOT among rendered outputs.
  - `tests/specify_cli/skills/test_installer.py` — assert checklist is
    NOT installed.
  - `tests/missions/test_command_templates_canonical_path.py` — drop
    checklist from the canonical path enumeration.
- Update snapshots:
  - Delete `tests/specify_cli/skills/__snapshots__/codex/checklist.SKILL.md`
    and the vibe equivalent.
  - Delete every `checklist.md` / `checklist.prompt.md` under
    `tests/specify_cli/regression/_twelve_agent_baseline/<agent>/`.
- Add new aggregate regression test:
  - `tests/specify_cli/test_no_checklist_surface.py` — recursively walks
    `src/specify_cli/missions/`, every supported agent's command
    directory under the project root (sourced from the same constant the
    migrations use, e.g. `AGENT_DIRS`), `tests/specify_cli/regression/`,
    and `docs/`. Asserts zero filenames matching `checklist*` AND zero
    occurrences of the regex `/?spec-kitty\.checklist\b` in any text
    file.
- Add new artifact-preservation test:
  - `tests/missions/test_specify_creates_requirements_checklist.py` —
    drives `mission create` + reads the post-`/spec-kitty.specify`
    artifact set, asserts
    `kitty-specs/<slug>/checklists/requirements.md` exists and contains
    the canonical Specification Quality Checklist headers.

## Out-of-scope

- Renaming `requirements.md` or moving the `checklists/` directory.
- Introducing a new slash command in `/spec-kitty.checklist`'s place.
