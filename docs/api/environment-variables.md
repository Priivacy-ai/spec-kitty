---
title: Environment Variables Reference
description: Environment variable reference for Spec Kitty 3.2 runtime, CI, hosted sync, tracker, dashboard, and test configuration.
doc_status: active
updated: '2026-06-26'
related:
- docs/api/cli-commands.md
- docs/api/configuration.md
---
# Environment Variables Reference

This page lists the user-facing environment variables that are active in the current `3.2` CLI surface.

---

## Runtime and Installation

### SPEC_KITTY_HOME

Override the runtime home directory used for shared Spec Kitty state.

**Purpose**: Change where the CLI stores shared state such as runtime files and upgrade-managed assets.

**Example**:
```bash
export SPEC_KITTY_HOME="$HOME/.spec-kitty-dev"
spec-kitty verify-setup
```

### SPEC_KITTY_TEMPLATE_ROOT

Point Spec Kitty at a local checkout for bundled templates and mission assets.

**Purpose**: Useful when developing Spec Kitty itself, testing template changes from source, or running in an environment where packaged resources are unavailable.

**Example**:
```bash
export SPEC_KITTY_TEMPLATE_ROOT=/path/to/spec-kitty
spec-kitty init my-project --ai claude
```

### SPECIFY_TEMPLATE_REPO

Override the remote template repository slug (`owner/name`).

**Purpose**: Use a custom remote template source when you explicitly want to bootstrap or repair from a different repository.

**Example**:
```bash
export SPECIFY_TEMPLATE_REPO=my-org/custom-spec-kitty
spec-kitty upgrade
```

### SPEC_KITTY_NON_INTERACTIVE

Force non-interactive mode for commands that normally prompt.

**Purpose**: Equivalent to passing `--non-interactive` / `--yes` on commands such as `spec-kitty init`.

**Example**:
```bash
export SPEC_KITTY_NON_INTERACTIVE=1
spec-kitty init my-project --ai codex --non-interactive
```

### SPEC_KITTY_WORKTREE_REMOVAL_DELAY

Adjust the delay before completed worktrees are removed.

**Purpose**: Useful when debugging merge/worktree cleanup behavior.

**Example**:
```bash
export SPEC_KITTY_WORKTREE_REMOVAL_DELAY=10
spec-kitty merge
```

---

## Hosted Auth and Sync

### SPEC_KITTY_ENABLE_SAAS_SYNC

Opt in to hosted auth, tracker, and sync flows.

**Purpose**: Enables the SaaS-backed readiness path. Leave it unset for fully local CLI workflows.

**Example**:
```bash
export SPEC_KITTY_ENABLE_SAAS_SYNC=1
spec-kitty auth login
```

**See also**:
- [Internal Hosted-Readiness (Pre-Launch)](../guides/internal-hosted-readiness.md)
  for the full operator walkthrough of the hidden hosted-readiness
  mode this flag enables today.
- [Launch-Readiness Behavior (Coming Soon)](../architecture/launch-readiness-future.md)
  for how this variable's meaning changes at the public Teamspace
  launch.

### SPEC_KITTY_SAAS_URL

Override the Spec Kitty SaaS base URL.

**Purpose**: Point auth, tracker discovery, and sync clients at a specific hosted environment such as a dev deployment.

**Example**:
```bash
export SPEC_KITTY_SAAS_URL=https://spec-kitty-dev.fly.dev
spec-kitty auth login
```

**See also**:
- [Internal Hosted-Readiness (Pre-Launch)](../guides/internal-hosted-readiness.md)
  -- this URL override is a dev / staging tool used by internal
  operators, not user behavior.
- [Launch-Readiness Behavior (Coming Soon)](../architecture/launch-readiness-future.md)
  -- the override remains internal-only after launch; only the
  user-facing default URL changes.

---

## Output and UX

### SPEC_KITTY_NO_NAG

Disable CLI upgrade check notices.

**Purpose**: Suppress human upgrade notices for the current shell. This also
keeps JSON, quiet, help, version, CI, and non-TTY output clean.

**Example**:
```bash
export SPEC_KITTY_NO_NAG=1
spec-kitty next --agent claude --mission my-mission --json
```

### SPEC_KITTY_NAG_THROTTLE_SECONDS

Override the minimum interval between upgrade checks.

**Purpose**: Tune local upgrade-check cadence. Values outside the supported
range fall back to the default silently.

**Example**:
```bash
export SPEC_KITTY_NAG_THROTTLE_SECONDS=86400
spec-kitty status
```

### SPEC_KITTY_UPGRADE_DISABLED

Disable the launch-readiness upgrade UX.

**Purpose**: Hard kill switch for the interactive readiness prompt and
auto-upgrade path. It is evaluated per invocation and is not persisted.

**Example**:
```bash
export SPEC_KITTY_UPGRADE_DISABLED=1
spec-kitty status
```

### SPEC_KITTY_UPGRADE_AUTO

Attempt safe auto-upgrade without prompting when an upgrade is available.

**Purpose**: Per-invocation override equivalent to choosing "Always keep me up
to date". Auto-upgrade still only runs for known-safe install methods such as
`pipx`, `uv tool`, Homebrew, and pip installs. Unknown or source installs print
manual guidance instead of mutating anything.

**Example**:
```bash
export SPEC_KITTY_UPGRADE_AUTO=1
spec-kitty status
```

### SPEC_KITTY_UPGRADE_NEVER_ASK

Suppress the launch-readiness upgrade prompt.

**Purpose**: Per-invocation override equivalent to choosing "Never ask again".
It does not rewrite the persisted cache unless the user chooses that option at
the interactive prompt.

**Example**:
```bash
export SPEC_KITTY_UPGRADE_NEVER_ASK=1
spec-kitty status
```

### SPEC_KITTY_SIMPLE_HELP

Request a simpler help presentation.

**Purpose**: Reduce the formatted help surface for terminals or wrappers that prefer plainer output.

**Example**:
```bash
export SPEC_KITTY_SIMPLE_HELP=1
spec-kitty --help
```

### SPEC_KITTY_NO_BANNER

Suppress the startup banner.

**Purpose**: Useful for scripts, screenshots, or wrappers that want less decorative output.

**Example**:
```bash
export SPEC_KITTY_NO_BANNER=1
spec-kitty init my-project --ai claude
```

---

## Selector / Compatibility Toggles

### SPECIFY_REPO_ROOT

Override repository-root discovery for certain internal path-resolution flows.

**Purpose**: Primarily useful for advanced development or unusual wrapper setups.

**Example**:
```bash
export SPECIFY_REPO_ROOT=/path/to/repo
spec-kitty verify-setup
```

### SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION

This variable is now inert. The `--feature` alias has been hard-removed from all
user-facing commands as of this release. No deprecation warnings are emitted;
this variable has no effect. Operators who have this set in their environment may
safely unset it.

**Previously**: Suppressed warnings for the deprecated `--feature` alias.

### SPEC_KITTY_SUPPRESS_MISSION_TYPE_DEPRECATION

Suppress warnings for the deprecated mission-type alias surfaces.

**Purpose**: Only for transitional automation or compatibility harnesses.

---

## External Tool Convention

### CODEX_HOME (legacy only)

Legacy Codex prompt-home override.

This is a **Codex CLI convention**, not a Spec Kitty variable. Current Spec
Kitty Codex support uses project-local Agent Skills under
`.agents/skills/spec-kitty.<command>/SKILL.md`; do not set `CODEX_HOME` for
current Spec Kitty command-skill installs.

**Legacy-only example**:
```bash
export CODEX_HOME="/path/to/legacy/codex-home"
```

---

## Test-Only Variables

The codebase also contains test and harness overrides such as `SPEC_KITTY_TEST_MODE`, `SPEC_KITTY_CLI_VERSION`, and `SPEC_KITTY_AUTORETRY`. Those are intentionally omitted from day-to-day operator guidance because they exist for tests, CI fixtures, or internal retry harnesses rather than normal end-user workflows.

---

## Summary Table

| Variable | Purpose | Example Value |
|----------|---------|---------------|
| `SPEC_KITTY_HOME` | Override shared runtime home | `$HOME/.spec-kitty-dev` |
| `SPEC_KITTY_TEMPLATE_ROOT` | Use a local template checkout | `/path/to/spec-kitty` |
| `SPECIFY_TEMPLATE_REPO` | Use a custom remote template repo | `org/templates` |
| `SPEC_KITTY_NON_INTERACTIVE` | Disable prompts | `1` |
| `SPEC_KITTY_WORKTREE_REMOVAL_DELAY` | Delay worktree cleanup | `10` |
| `SPEC_KITTY_ENABLE_SAAS_SYNC` | Opt in to hosted sync/auth flows | `1` |
| `SPEC_KITTY_SAAS_URL` | Override hosted base URL | `https://spec-kitty-dev.fly.dev` |
| `SPEC_KITTY_NO_NAG` | Disable upgrade notices | `1` |
| `SPEC_KITTY_NAG_THROTTLE_SECONDS` | Override upgrade-check cadence | `86400` |
| `SPEC_KITTY_UPGRADE_DISABLED` | Disable upgrade readiness UX | `1` |
| `SPEC_KITTY_UPGRADE_AUTO` | Enable safe auto-upgrade override | `1` |
| `SPEC_KITTY_UPGRADE_NEVER_ASK` | Suppress upgrade prompt override | `1` |
| `SPEC_KITTY_SIMPLE_HELP` | Use simpler help output | `1` |
| `SPEC_KITTY_NO_BANNER` | Suppress startup banner | `1` |
| `SPECIFY_REPO_ROOT` | Override repo-root discovery | `/path/to/repo` |
| `SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION` | **Inert** — `--feature` alias removed; no warnings emitted | N/A |
| `SPEC_KITTY_SUPPRESS_MISSION_TYPE_DEPRECATION` | Silence deprecated mission-type warnings | `1` |
| `CODEX_HOME` | Legacy Codex CLI prompt-home override | Legacy only; current Codex skills live under `.agents/skills/` |

---

## See Also

- [Configuration](configuration.md) — Configuration file reference
- [CLI Commands](cli-commands.md) — Command line reference
- [Non-Interactive Init](../guides/non-interactive-init.md) — Common automation patterns

## Getting Started

- [Claude Code Workflow](../guides/claude-code-workflow.md)

## Practical Usage

- [Non-Interactive Init](../guides/non-interactive-init.md)
- [Install Spec Kitty](../guides/install-spec-kitty.md)
