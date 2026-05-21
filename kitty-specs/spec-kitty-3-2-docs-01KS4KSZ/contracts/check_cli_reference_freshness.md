# Contract: `scripts/docs/check_cli_reference_freshness.py`

**Purpose**: Implement FR-020 / NFR-001. Detect drift between the live Typer tree and the committed CLI reference.

## Inputs

- Environment: `SPEC_KITTY_ENABLE_SAAS_SYNC=1` and `SPEC_KITTY_NO_UPGRADE_CHECK=1` set before import.
- `--reference PATH` (default `docs/reference/cli-commands.md`).
- `--agent-reference PATH` (default `docs/reference/agent-subcommands.md`).
- `--report PATH` (optional) — JSON report slice.
- `--ci` flag — plain-text output for CI annotations.
- `--strict-mode` flag — also fail when an entry exists in the reference but the matching visible path's `help_summary` has drifted from what the reference recorded (`HELP-DRIFT`); off by default to allow hand-authored prose.

## Outputs

- stdout: findings table; counts by rule.
- optional JSON report.

## Rules

| `rule_id` | Severity | Condition |
|-----------|----------|-----------|
| `REF-MISSING` | error | A visible command path is missing from the reference. |
| `REF-EXTRA` | error | A reference entry names a command path not in the live tree. |
| `REF-DEPRECATED-UNCLASSIFIED` | error | A deprecated/removed visible command path is not classified as such in the reference. |
| `REF-INTERNAL-LEAK` | error | A path whose live `help_summary` starts with `Internal -` appears in the user-facing reference without an "internal" classification banner. |
| `REF-SAAS-SYNC-OFF` | error | `SPEC_KITTY_ENABLE_SAAS_SYNC` was not set, so `tracker`/`issue-search` paths could not be evaluated; refuse to declare clean. |
| `HELP-DRIFT` | warning (error in `--strict-mode`) | The reference's recorded summary differs from the live `help_summary`. |
| `REF-HIDDEN-LEAK` | error | A hidden path appears in the user-facing reference (allowed only in the `--include-hidden` appendix). |

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | No errors. |
| 1 | One or more errors. |
| 2 | Input error (missing reference file). |
| 3 | Environmental setup error (SaaS sync off, CLI fails to import). |

## Guarantees

- Read-only.
- Deterministic.
- Discovers visible paths the same way `build_cli_reference.py` does (`_typer_walker.py` is shared).

## Non-guarantees

- Does not enforce documentation prose quality. Reviewer judgement remains the gate for tone, examples, and clarity.
- Does not validate that linked tests exist or pass; that is the architectural test's job.

## Test fixtures

- `tests/docs/fixtures/sample_cli_reference.md` (clean) — exit code 0.
- `tests/docs/fixtures/sample_cli_reference_missing.md` — `REF-MISSING` count == 1; exit 1.
- `tests/docs/fixtures/sample_cli_reference_extra.md` — `REF-EXTRA` count == 1; exit 1.
- `tests/docs/fixtures/sample_cli_reference_no_saas.md` — env flag off in subtest; `REF-SAAS-SYNC-OFF`; exit 3.
