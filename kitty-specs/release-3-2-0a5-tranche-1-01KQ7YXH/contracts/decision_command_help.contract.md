# Contract: `spec-kitty agent decision` command shape consistency

**Traces to**: FR-007 (#774), NFR-008

## Stimulus

A user (or implementing agent) reads any of:

- `--help` output for `spec-kitty agent decision …` and sub-paths
- Any documentation page under `docs/reference/`, `docs/explanation/`,
  `docs/migration/`
- Any agent skill template snapshot under `.agents/skills/` or
  `tests/specify_cli/skills/__snapshots__/`
- Any source command template under
  `src/specify_cli/missions/*/command-templates/`

## Required behavior

Every reference to the decision command in the surfaces above MUST use
exactly one canonical shape:

```
spec-kitty agent decision { open | resolve | defer | cancel | verify } …
```

Specifically:

- The subgroup name is `decision` (singular). No `decisions`.
- The subgroup is reachable via `spec-kitty agent`. No top-level
  `spec-kitty decision …` alias is introduced or referenced.
- The five subcommands are exactly: `open`, `resolve`, `defer`,
  `cancel`, `verify`. No additional names referenced.
- All flags follow the existing typer schema (`--mission`, `--flow`,
  `--slot-key`, `--input-key`, `--question`, `--options`,
  `--final-answer`, `--rationale`).

## Forbidden behavior

- Any documented or rendered surface that names `spec-kitty decision …`,
  `spec-kitty agent decisions …`, or `spec-kitty agent decision-…`.
- Any divergence between `--help` output and a doc page on subcommand
  list, flag names, or flag arity.

## Implementation hint (informative, not normative)

Verified during planning that the actual subgroup
(`src/specify_cli/cli/commands/decision.py:1`) and the only doc reference
found (`docs/reference/missions.md:268`) already match the canonical
shape. FR-007 collapses to a regression test that prevents future drift.
See [research.md R6](../research.md#r6--spec-kitty-agent-decision-command-shape-fr-007--774).

## Verifying tests

- New `tests/specify_cli/cli/test_decision_command_shape_consistency.py`:
  - Walks the typer app, asserts the `agent decision` subgroup exists with
    exactly the five subcommands above.
  - Recursively greps `docs/`, `.agents/skills/`,
    `tests/specify_cli/skills/__snapshots__/`,
    `src/specify_cli/missions/*/command-templates/` for the regex
    `spec-kitty\s+(?:agent\s+)?decision[s\-]\w*` and asserts every match
    falls inside the canonical shape.
  - Asserts `--help` output for `spec-kitty agent decision` lists exactly
    these five subcommands (in any order).

## Out-of-scope

- Changing the subgroup name or adding new subcommands. (#774 asks to
  *clarify*, not to redesign.)
