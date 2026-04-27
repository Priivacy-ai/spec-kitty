# Quickstart: CLI Upgrade Nag and Lazy Project Migration

**Mission**: `cli-upgrade-nag-lazy-project-migrations-01KQ6YDN`
**Audience**: planner, reviewer, implementer of work packages.

This is a hands-on tour of the user-facing surfaces this mission delivers. Every example matches one user scenario in [`spec.md`](spec.md) and one example in [`contracts/compat-planner.json`](contracts/compat-planner.json).

---

## 1. Install the CLI (no-op for this mission, just orient)

```bash
pipx install spec-kitty-cli
spec-kitty --version
# spec-kitty 2.0.11
```

The `--version` and `--help` paths are **always safe** — the planner short-circuits on them and never opens a socket.

---

## 2. Compatible CLI, newer release available (Scenario A)

Setup: a project on disk whose schema is fine, but PyPI has `2.0.14` published.

```bash
cd /path/to/myproj
spec-kitty status
# Spec Kitty 2.0.14 is available; you have 2.0.11.
# Upgrade with: pipx upgrade spec-kitty-cli
#
# (then the normal `status` output)
```

Re-run within 24 hours:

```bash
spec-kitty status
# (no nag this time — throttle window not yet elapsed)
```

Override the throttle window:

```bash
SPEC_KITTY_NAG_THROTTLE_SECONDS=3600 spec-kitty status   # 1-hour window
```

Disable the nag entirely:

```bash
spec-kitty status --no-nag                               # this run only
SPEC_KITTY_NO_NAG=1 spec-kitty status                    # this shell session
```

---

## 3. Stale-but-migratable project (Scenario B)

Setup: project schema is `1`, CLI's `MIN_SUPPORTED_SCHEMA` is `3`.

```bash
cd /path/to/oldproj
spec-kitty next --agent claude
# This project needs Spec Kitty project migrations before this command can run.
# Run: spec-kitty upgrade
# Preview first: spec-kitty upgrade --dry-run
echo $?
# 4
```

Preview the migration:

```bash
spec-kitty upgrade --dry-run
# CLI: current 2.0.14, latest 2.0.14
# Project: schema 1, target schema 3
# Migrations:
#   m_2_0_0_lane_layout
#   m_2_5_0_lane_consolidation
#   m_3_0_0_canonical_context
echo $?
# 0
```

Get the same plan as JSON for tooling:

```bash
spec-kitty upgrade --dry-run --json | jq .
# (matches contracts/compat-planner.json — see example #3)
```

Apply, non-interactively:

```bash
spec-kitty upgrade --yes
# (or, equivalently, --force)
spec-kitty next --agent claude
# (now succeeds)
```

---

## 4. Project too new for installed CLI (Scenario C)

Setup: project schema is `7`, CLI's `MAX_SUPPORTED_SCHEMA` is `6`.

```bash
cd /path/to/futureproj
spec-kitty implement WP01
# This project uses Spec Kitty project schema 7, but this CLI supports up to schema 6.
# Upgrade the CLI: pipx upgrade spec-kitty-cli
echo $?
# 5
```

The CLI does not touch project files in this case. Even `--yes` and `--force` do not bypass this block (CHK037 / A-006).

---

## 5. CLI guidance outside any project (Scenario F)

```bash
cd /tmp
spec-kitty upgrade --cli
# Spec Kitty 2.0.14 is available; you have 2.0.11.
# Upgrade with: pipx upgrade spec-kitty-cli
echo $?
# 0
```

If the install method cannot be detected:

```bash
spec-kitty upgrade --cli
# Spec Kitty 2.0.14 is available; you have 2.0.11.
# Your install method could not be detected automatically.
# Upgrade Spec Kitty using the same method you used to install it.
# See https://spec-kitty.dev/docs/how-to/install-and-upgrade for guidance.
echo $?
# 0
```

---

## 6. Safe commands under stale schema (Scenario G)

The following all run successfully even when the project's schema is incompatible with the installed CLI:

```bash
spec-kitty --help
spec-kitty --version
spec-kitty status                              # read-only
spec-kitty dashboard                           # read-only mode
spec-kitty doctor                              # diagnostic mode
spec-kitty upgrade --dry-run                   # always allowed
spec-kitty upgrade --cli                       # always allowed
```

The mode-aware split for `dashboard` and `doctor` is enforced by per-command predicates registered in `compat.safety`:

```bash
spec-kitty dashboard --repair                  # blocked under schema mismatch (write mode)
spec-kitty doctor --fix                        # blocked under schema mismatch (repair mode)
```

---

## 7. CI / non-interactive mode (Scenario H)

```bash
CI=1 spec-kitty status
# (no nag, no network call — even if a newer release is available)

# Same effect when piping:
spec-kitty status | head -1
# (no nag — stdout is not a TTY)

# Same effect inside a CI job, with all checks still running:
CI=1 spec-kitty next --agent claude
# (still blocks on schema mismatch — only the *nag* path is suppressed,
#  not the project compatibility gate)
```

Test assertion (for the implementer):

```python
def test_ci_makes_zero_outbound_calls(cli_runner, network_blocker):
    result = cli_runner.invoke(["status"], env={"CI": "1"})
    assert network_blocker.call_count == 0
    assert "is available" not in result.stdout
```

---

## 8. JSON contract surface (FR-022, SC-004)

Every `spec-kitty upgrade` invocation supports `--json`. The shape is locked in [`contracts/compat-planner.json`](contracts/compat-planner.json) and is stable across patch releases (R-09).

```bash
spec-kitty upgrade --json
# { "schema_version": 1, "case": "...", "decision": "...", ... }
```

Useful queries:

```bash
spec-kitty upgrade --dry-run --json | jq -r .case
# project_migration_needed

spec-kitty upgrade --dry-run --json | jq -r '.upgrade_hint.command'
# pipx upgrade spec-kitty-cli

spec-kitty upgrade --dry-run --json | jq '.pending_migrations | length'
# 3

spec-kitty upgrade --dry-run --json | jq '[.pending_migrations[].migration_id]'
# ["m_2_0_0_lane_layout","m_2_5_0_lane_consolidation","m_3_0_0_canonical_context"]
```

---

## 9. Programmatic use of the planner (internal API)

For other CLI surfaces or tests:

```python
from specify_cli.compat import plan, NoNetworkProvider, PyPIProvider
from specify_cli.compat.cache import NagCache

p = plan(
    invocation=Invocation.from_argv(),
    latest_version_provider=PyPIProvider(timeout_s=2.0),
    nag_cache=NagCache.default(),
)

if p.decision in {"BLOCK_PROJECT_MIGRATION", "BLOCK_CLI_UPGRADE", "BLOCK_PROJECT_CORRUPT"}:
    print(p.rendered_human)
    raise SystemExit(p.exit_code)

if p.decision == "ALLOW_WITH_NAG":
    print(p.rendered_human)

# proceed with the requested command...
```

For CI tests, swap the provider:

```python
from specify_cli.compat import plan, NoNetworkProvider

p = plan(invocation=..., latest_version_provider=NoNetworkProvider(), nag_cache=...)
assert p.cli_status.latest_source == "none"
assert p.cli_status.latest_version is None
```

---

## 10. Verification matrix (what each Success Criterion looks like in practice)

| SC | Quickstart section | Test name (proposed) |
|---|---|---|
| SC-001 | §2 | `tests/cli_gate/test_nag_throttle.py::test_nag_prints_once_per_window_and_command_succeeds` |
| SC-002 | §3 | `tests/cli_gate/test_unsafe_commands.py::test_stale_migratable_project_blocks_with_remediation` |
| SC-003 | §4 | `tests/cli_gate/test_unsafe_commands.py::test_too_new_project_blocks_with_cli_upgrade_hint` |
| SC-004 | §8 | `tests/specify_cli/cli/commands/test_upgrade_command.py::test_dry_run_json_matches_contract_schema` |
| SC-005 | §7 | `tests/cli_gate/test_ci_determinism.py::test_zero_outbound_calls_under_ci_predicate` |
| SC-006 | §6 | `tests/cli_gate/test_safe_commands.py::test_safe_matrix_runs_under_schema_mismatch` |
| SC-007 | §3 | `tests/cli_gate/test_multi_project_isolation.py::test_upgrade_only_affects_current_project` |
| SC-008 | docs/how-to/install-and-upgrade.md | manual review during mission acceptance |

---

## 11. What this quickstart deliberately does NOT show

- A "compatibility planner" REPL — there is no interactive sub-tool. The planner is consumed via the typer callback and via `spec-kitty upgrade --json`.
- A global "upgrade everything" command — out of scope (FR-020, C-003).
- A project picker / recent-projects list — out of scope (FR-021, C-002).
- Self-upgrade execution from `--cli` — `--cli` only *prints* upgrade guidance in this mission; if a future ADR adds executable self-upgrade, that is a separate spec.
