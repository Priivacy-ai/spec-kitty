# Contract: `scripts/docs/check_docs_freshness.py`

**Purpose**: Implement FR-020 / FR-021. Orchestrate every docs-freshness check into a single CI-friendly report.

## Inputs

- Environment: same as `check_cli_reference_freshness.py` (`SPEC_KITTY_ENABLE_SAAS_SYNC=1`, `SPEC_KITTY_NO_UPGRADE_CHECK=1`).
- `--inventory PATH`, `--docs-root PATH`, `--reference PATH`, `--agent-reference PATH` — pass-through to the underlying checks.
- `--link-check {none,spot,full}` (default `spot`) — `none` skips link health; `spot` checks 20 random `current`-tagged pages plus the CLI reference for `http(s)://` links and runs HEAD requests; `full` checks every external link.
- `--report PATH` (optional) — single JSON `FreshnessReport`.
- `--ci` flag — plain text output.
- `--strict-mode` flag — pass-through to underlying CLI freshness checker.

## Sub-checks

1. `version_leakage_check.py` — gathers `LEAK-*` findings.
2. `check_cli_reference_freshness.py` — gathers `REF-*` and `HELP-*` findings.
3. Link health (per `--link-check`).
4. Page-inventory completeness — every `.md` under `docs/` is present in the manifest or explicitly excluded by glob.

## Outputs

- Aggregated `FreshnessReport`. Errors from any sub-check propagate. Warnings are reported but do not fail.

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | No errors across any sub-check. |
| 1 | One or more sub-checks reported errors. |
| 2 | Input error (missing inventory or reference). |
| 3 | Environmental setup error. |

## Guarantees

- Single point of entry for the publication gate (FR-021).
- Each sub-check runs in isolation; one sub-check's input error does not skip the others.

## Non-guarantees

- Does not build the docs site; that remains a separate workflow step in CI.
- Does not write to disk except for the optional `--report` JSON.

## CI wiring (informational)

Tasks-phase WP F3 wires this into `.github/workflows/ci-quality.yml` (or the current equivalent) as:

```yaml
# round-trip: skip: GitHub Actions CI step (not a Pydantic model payload) — migrated from the legacy allowlist to an explicit non-executable marker (#2255)
- name: Docs freshness
  run: |
    SPEC_KITTY_ENABLE_SAAS_SYNC=1 SPEC_KITTY_NO_UPGRADE_CHECK=1 \
      uv run scripts/docs/check_docs_freshness.py --ci --report freshness.json
```

The CI step uploads `freshness.json` as an artifact for the publication checklist evidence.

## Test fixtures

- `tests/docs/test_check_docs_freshness.py` covers:
  - Happy path → exit 0.
  - One leak + one reference miss → aggregated exit 1.
  - Missing inventory → exit 2.
  - SaaS sync off → exit 3.
