# How to Install and Upgrade Spec Kitty

> **Formal requirements**: [`kitty-specs/cli-upgrade-nag-lazy-project-migrations-01KQ6YDN/spec.md`](../../kitty-specs/cli-upgrade-nag-lazy-project-migrations-01KQ6YDN/spec.md)

---

## Two upgrades, not one

Spec Kitty has two distinct upgrade concepts:

- **Upgrading the CLI** — installing a newer `spec-kitty` binary (pipx, pip, Homebrew, etc.).
- **Migrating a project** — updating `.kittify/` schema inside one specific project to match the installed CLI.

Spec Kitty never silently upgrades itself and never touches projects you are not currently inside.

---

## Upgrade the CLI

Run from anywhere:

```bash
spec-kitty upgrade --cli
```

Spec Kitty detects your install method and prints the right command:

| Install method | Upgrade command |
|---|---|
| pipx | `pipx upgrade spec-kitty-cli` |
| pip (user) | `pip install --upgrade --user spec-kitty-cli` |
| pip (venv/system) | `pip install --upgrade spec-kitty-cli` |
| Homebrew | `brew upgrade spec-kitty` |
| System package | use your package manager |

If the install method cannot be detected, Spec Kitty prints manual instructions instead
of a runnable command — rerun `spec-kitty upgrade --cli` after you upgrade to confirm
detection works.

---

## Migrate the current project

Run from inside the project root:

```bash
spec-kitty upgrade           # interactive
spec-kitty upgrade --project # same thing, explicit
```

**Preview first**:

```bash
spec-kitty upgrade --dry-run
# Project: schema 1, target schema 3
# Migrations:
#   m_2_0_0_lane_layout
#   m_2_5_0_lane_consolidation
#   m_3_0_0_canonical_context
```

**Apply non-interactively** (CI, scripts):

```bash
spec-kitty upgrade --yes    # or --force; both work
```

Migrations are idempotent and applied in version order.

---

## The throttled nag

When a newer CLI version is available, Spec Kitty prints one line before normal output:

```
Spec Kitty 2.0.14 is available; you have 2.0.11.
Upgrade with: pipx upgrade spec-kitty-cli
```

Throttled to **once per 24 hours** by default. Configure:

```bash
SPEC_KITTY_NAG_THROTTLE_SECONDS=3600 spec-kitty status   # 1-hour window
```

Or in `~/.config/spec-kitty/upgrade.yaml`:

```yaml
nag:
  throttle_seconds: 3600
```

Disable entirely:

```bash
spec-kitty status --no-nag              # this invocation only
SPEC_KITTY_NO_NAG=1 spec-kitty status   # this shell session
```

---

## The lazy gate

When a project's schema is incompatible with the installed CLI, unsafe commands are
blocked.

**Project needs migration — exit code 4**:

```bash
cd /path/to/oldproj
spec-kitty next --agent claude
# This project needs Spec Kitty project migrations before this command can run.
# Run: spec-kitty upgrade
# Preview first: spec-kitty upgrade --dry-run
echo $?   # 4
```

Remediate: run `spec-kitty upgrade`, then retry.

**Project too new for installed CLI — exit code 5**:

```bash
cd /path/to/futureproj
spec-kitty implement WP01
# This project uses Spec Kitty project schema 7, but this CLI supports up to schema 6.
# Upgrade the CLI: pipx upgrade spec-kitty-cli
echo $?   # 5
```

Remediate: upgrade the CLI. `--yes` and `--force` do **not** bypass this block.

**Commands that always work** regardless of schema:

```bash
spec-kitty --help
spec-kitty --version
spec-kitty status              # read-only
spec-kitty upgrade --dry-run   # always allowed
spec-kitty upgrade --cli       # always allowed
```

---

## Behavior in CI

When `CI=1` is set (or stdout is not a TTY):

- The nag is **suppressed** and no PyPI fetch is made.
- The **project compatibility gate still runs** — incompatible projects exit with
  code 4 or 5 as normal.

```bash
CI=1 spec-kitty next --agent claude
# no nag; still exits 4 if project needs migration
```

---

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Success / safe pass-through |
| `2` | Usage error (e.g. `--cli` and `--project` combined) |
| `4` | Project needs migration — run `spec-kitty upgrade` |
| `5` | Project too new for this CLI — upgrade the CLI |
| `6` | Project metadata corrupt or unreadable |

---

## JSON output for tooling

```bash
spec-kitty upgrade --dry-run --json | jq .case
# "project_migration_needed"

spec-kitty upgrade --dry-run --json | jq -r '.upgrade_hint.command'
# pipx upgrade spec-kitty-cli

spec-kitty upgrade --dry-run --json | jq '.pending_migrations | length'
# 3
```

Schema (stable across patch releases):
[`kitty-specs/cli-upgrade-nag-lazy-project-migrations-01KQ6YDN/contracts/compat-planner.json`](../../kitty-specs/cli-upgrade-nag-lazy-project-migrations-01KQ6YDN/contracts/compat-planner.json)

---

## Troubleshooting

**I get the nag every time.**
The cache lives at `~/.cache/spec-kitty/upgrade-nag.json`. If it is being cleared between
runs, set `SPEC_KITTY_NAG_THROTTLE_SECONDS=86400` explicitly or check for a process that
deletes the cache directory.

**The CLI won't upgrade with the printed command.**
Your install method may have changed. Rerun `spec-kitty upgrade --cli` to get a fresh
detection result.

**I'm told my project is corrupt (exit 6).**
Check that `.kittify/metadata.yaml` exists, is valid YAML, and has
`spec_kitty.schema_version` as an integer.

**I'm in CI with no nag but commands still block.**
Expected — the nag is suppressed in CI but the compatibility gate is not. Add
`spec-kitty upgrade --yes` to your CI setup step.

---

## See also

- [CLI Commands](../reference/cli-commands.md)
- [Environment Variables](../reference/environment-variables.md)
- [Getting Started Tutorial](../tutorials/getting-started.md)
- [Non-Interactive Init](non-interactive-init.md)
