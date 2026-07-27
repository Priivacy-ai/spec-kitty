# Quickstart: Reproduce the 3.2 Docs Freshness Gate

**Mission**: `spec-kitty-3-2-docs-01KS4KSZ` | **Phase**: 1 (Design) | **Audience**: reviewers, release engineers

This quickstart shows how to reproduce the publication gate on a fresh checkout. Run it after `/spec-kitty.tasks` has materialised work packages and the implement-review loop has landed the tooling.

## Prerequisites

- Python 3.11+
- `uv` (the project's preferred runner) — `pipx install uv` or `pip install uv` if not already installed
- macOS, Linux, or Windows + Git Bash / PowerShell

## Setup

```bash
cd /path/to/spec-kitty
uv sync
```

The repo's `pyproject.toml` already declares typer, rich, ruamel.yaml, pytest, and mypy — no extra installs are needed.

## Step 1: Build the CLI reference

```bash
export SPEC_KITTY_ENABLE_SAAS_SYNC=1
export SPEC_KITTY_NO_UPGRADE_CHECK=1

uv run python scripts/docs/build_cli_reference.py \
  --output docs/reference/cli-commands.md \
  --agent-output docs/reference/agent-subcommands.md \
  --mode hybrid
```

Expected stderr summary (snapshot at planning time, will drift forward with the CLI):

```
visible: 192   hidden: 5   deprecated: 2
generated_lines: ...   hand_authored_lines_preserved: ...
saas_sync: on
```

To preview without writing:

```bash
uv run python scripts/docs/build_cli_reference.py --dry-run | head -80
```

## Step 2: Run the unit + integration tests

```bash
uv run pytest tests/docs/ -v
```

All tests must pass. Coverage report is emitted via the existing pytest-cov configuration.

## Step 3: Run the architectural parity test

```bash
uv run pytest tests/architectural/test_docs_cli_reference_parity.py -v
```

The test imports `specify_cli.app` with the SaaS sync flag set and asserts that every non-hidden command path appears in `docs/reference/cli-commands.md`.

## Step 4: Run the orchestrated freshness check

```bash
uv run python scripts/docs/check_docs_freshness.py \
  --report freshness.json \
  --ci
```

Expected exit code: `0`. Any non-zero exit means review the JSON report:

```bash
jq '.findings[] | select(.severity == "error")' freshness.json
```

Common error shapes:

- `LEAK-CURRENT-LINKS-ARCHIVAL` — a current-tagged page links to an archival page without a migration banner. Fix the page or move the target.
- `REF-MISSING <path>` — the live CLI added a visible command path that isn't in the reference. Re-run `build_cli_reference.py` and commit the result.
- `REF-EXTRA <path>` — the reference names a command no longer in the live tree. Remove the entry or move it to a "Deprecated/Removed" section with classification.

## Step 5: Smoke-build the docs site

If DocFX is the active site generator (confirmed in research R-002), run:

```bash
cd docs
docfx docfx.json
```

The local build must finish without broken cross-references. Navigation must show separate groups for "3.2 (current)", "Migration", "Archive (2.x)", "Archive (1.x)", and optionally "3.1 (supported)" depending on how decision `01KS4KTGTN4DBE60JFWKEA2FJB` resolves.

## Step 6: Run the publication checklist

Open `docs/development/3-2-publication-checklist.md` and walk each item. The checklist references the artifacts above; every item that requires evidence cites either a freshness JSON, a test ID, or a manual review note.

## Quick-fail signals

| Symptom | Probable cause | Resolution |
|---------|-----------------|------------|
| `BUILD-ENV-MISSING-SAAS-SYNC` | `SPEC_KITTY_ENABLE_SAAS_SYNC=1` was not exported. | Re-export and re-run; CI step already sets it. |
| `BUILD-TARGET-DIRTY` | The reference file has uncommitted edits. | Stash or commit first; do not `--force` in CI. |
| `REF-SAAS-SYNC-OFF` from freshness check | Same as above. | Re-export the env flag. |
| `LEAK-MISSING-INVENTORY` | A new markdown page was added without inventory rows. | Add a `PageInventoryEntry` row in `docs/development/3-2-page-inventory.yaml`. |
| `HELP-DRIFT` warnings | The CLI command's `--help` text changed but the reference was not rebuilt. | Re-run Step 1 and commit the diff. |

## Time budget

Step 1: ~60s on a developer laptop (192 subprocess `--help` invocations).
Step 2: ~5–15s.
Step 3: ~3s.
Step 4: ~30–90s depending on `--link-check`.
Step 5: ~10–30s.
Total: under 5 minutes for a clean reviewer pass.
