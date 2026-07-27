# Contract: `scripts/docs/build_cli_reference.py`

**Purpose**: Implement FR-007 / FR-008. Build the 3.2 CLI reference markdown from the live Typer app, capturing every visible command path's `--help` output.

## Inputs

- Environment: `SPEC_KITTY_ENABLE_SAAS_SYNC=1` and `SPEC_KITTY_NO_UPGRADE_CHECK=1` MUST be set in the process environment before `specify_cli.app` is imported. The script enforces this by setting them in `os.environ` at module top before any other import.
- `--output PATH` (default `docs/reference/cli-commands.md`) — destination markdown file.
- `--agent-output PATH` (default `docs/reference/agent-subcommands.md`) — destination for `agent`-rooted subtree (kept as a separate page per repo convention).
- `--include-hidden` flag — append an internal appendix listing the 5 hidden paths.
- `--mode {generated, hybrid, hand}` (default `hybrid`) — controls the generated-block delimiter behavior:
  - `generated`: the entire body is auto-generated; no hand-authored prose allowed between `<!-- BEGIN GENERATED -->` and `<!-- END GENERATED -->`.
  - `hybrid` (plan default): the generated block is embedded; hand-authored prose lives outside the block and is preserved across runs.
  - `hand`: the script only writes the deprecation/internal classification table; everything else is hand-authored.
- `--dry-run` flag — print the diff without writing.

## Outputs

- `docs/reference/cli-commands.md` rewritten in place (or printed to stdout under `--dry-run`).
- `docs/reference/agent-subcommands.md` rewritten in place (same gating).
- stderr: a short summary table — visible/hidden/deprecated counts, generated lines, hand-authored lines preserved.

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Wrote (or would have written) successfully; output matched the expected freshness rules. |
| 1 | The live tree contains visible paths the generator could not classify; output not written. |
| 2 | Input error (missing dependencies, malformed CLI app, `pyproject.toml` not found). |
| 3 | Environmental setup error (`SPEC_KITTY_ENABLE_SAAS_SYNC` not set, `git status` shows uncommitted writes in target files). |

## Guarantees

- Read-only on the Typer app. The script imports `specify_cli.app` but never patches or rebinds command objects.
- Subprocess-isolated per-path help capture. Each `--help` is collected via `subprocess.run(["uv", "run", "spec-kitty", *path, "--help"], …)` with stdout captured. The walker prefers `group.name` then `group.typer_instance.info.name` per `cli-audit-3-2.md`.
- Idempotent. Re-running on a tree with no changes leaves the output byte-identical.
- Refuses to write if the target file has uncommitted edits already in the working tree (avoids stomping a reviewer's in-progress prose). Override with `--force` for ad-hoc local runs.

## Non-guarantees

- The script does NOT decide the hand-vs-generator policy. That is decision `01KS4KTM69EG2KVX5MQ54FQ939`. The script honours whichever `--mode` is passed.
- The script does NOT modify Typer command code, command files, or `docs/toc.yml`. Any help-text discrepancy is logged as a `MetaIssue` row prompt on stderr, not silently fixed.

## Test fixtures

- `tests/docs/fixtures/sample_cli_reference.md` — the expected output for a synthetic Typer app fixture (a tiny app used in unit tests so the test does not depend on the real CLI).
- Integration test (smoke) imports the real `specify_cli.app` with the env flags set and asserts: visible count ≥ 192, deprecated count == 2, hidden count == 5 (current snapshot from `cli-audit-3-2.md`; test tolerates ±10% with explicit log so an intentional command addition is visible).

## Error taxonomy (exemplar messages)

```
BUILD-ENV-MISSING-SAAS-SYNC
  SPEC_KITTY_ENABLE_SAAS_SYNC=1 must be set before import. tracker/issue-search will be missing without it.

BUILD-UNCLASSIFIED-VISIBLE-PATH spec-kitty foo bar
  Visible command with no help summary and no test reference; classify in cli-audit meta-issues and re-run.

BUILD-TARGET-DIRTY  docs/reference/cli-commands.md
  Target has uncommitted edits in the working tree. Stash, commit, or pass --force.
```
