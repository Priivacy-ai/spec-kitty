# Contract: legacy `--feature` alias hidden from CLI help

**Traces to**: FR-006 (#790), NFR-007, C-004

## Stimulus

A user (or agent) runs `--help` against any `spec-kitty` command path that
historically accepted a `--feature` flag. The flag was deprecated in favor
of `--mission` but must remain accepted for backward compatibility.

## Required behavior

1. For **every** command listed in the FR-006 inventory (28 declarations
   across 17 files; see [research.md R5](../research.md#r5--feature-alias-hiding-fr-006--790)),
   the rendered `--help` output MUST contain zero literal occurrences of
   the token `--feature`.
2. For each such command, passing `--feature <value>` on the CLI MUST
   continue to behave exactly as it does today: route the value into
   `--mission` semantics with no behavioral difference, and (per the
   existing `SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION` env var) optionally
   emit a deprecation warning.

## Forbidden behavior

- Any newly-introduced visible mention of `--feature` in `--help`.
- Any change that breaks an existing call site that passes `--feature`.
- Removing the alias altogether (out of scope for this tranche; C-004).

## Implementation hint (informative, not normative)

Verified during planning that all 28 declarations already carry
`hidden=True`. FR-006 collapses to a regression test that prevents future
drift.

## Verifying tests

- New `tests/specify_cli/cli/test_no_visible_feature_alias.py`:
  - Walks the typer app via Click introspection.
  - For every leaf command, invokes `<command> --help` via `CliRunner`,
    captures the rendered string, asserts `"--feature"` is not a substring.
  - Asserts (via direct typer Parameter inspection) that every parameter
    with name "feature" carries `hidden=True`.
- An existing call-site smoke test (extend
  `tests/e2e/test_cli_smoke.py` if necessary) that passes `--feature` to
  one of the historically-accepting commands and asserts the command runs
  to completion identically to passing `--mission`.

## Out-of-scope

- Changing the value of the `SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION`
  env var or its default.
- Removing the alias.
