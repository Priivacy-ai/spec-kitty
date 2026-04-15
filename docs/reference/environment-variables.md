# Environment Variables Reference

This page lists the user-facing environment variables that are active in the current `4.1.x` CLI surface.

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

### SPEC_KITTY_SAAS_URL

Override the Spec Kitty SaaS base URL.

**Purpose**: Point auth, tracker discovery, and sync clients at a specific hosted environment such as a dev deployment.

**Example**:
```bash
export SPEC_KITTY_SAAS_URL=https://spec-kitty-dev.fly.dev
spec-kitty auth login
```

---

## Output and UX

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

Suppress warnings for the deprecated `--feature` alias.

**Purpose**: Only for transitional automation that still emits the old selector.

### SPEC_KITTY_SUPPRESS_MISSION_TYPE_DEPRECATION

Suppress warnings for the deprecated mission-type alias surfaces.

**Purpose**: Only for transitional automation or compatibility harnesses.

---

## External Tool Convention

### CODEX_HOME

Point the Codex CLI at your project's `.codex/` directory.

This is a **Codex CLI convention**, not a Spec Kitty variable, but it remains relevant when using Codex with project-local prompts.

**Example**:
```bash
export CODEX_HOME="$(pwd)/.codex"
codex
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
| `SPEC_KITTY_SIMPLE_HELP` | Use simpler help output | `1` |
| `SPEC_KITTY_NO_BANNER` | Suppress startup banner | `1` |
| `SPECIFY_REPO_ROOT` | Override repo-root discovery | `/path/to/repo` |
| `SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION` | Silence deprecated `--feature` warnings | `1` |
| `SPEC_KITTY_SUPPRESS_MISSION_TYPE_DEPRECATION` | Silence deprecated mission-type warnings | `1` |
| `CODEX_HOME` | Codex CLI prompt path | `$(pwd)/.codex` |

---

## See Also

- [Configuration](configuration.md) — Configuration file reference
- [CLI Commands](cli-commands.md) — Command line reference
- [Non-Interactive Init](../how-to/non-interactive-init.md) — Common automation patterns

## Getting Started

- [Claude Code Workflow](../tutorials/claude-code-workflow.md)

## Practical Usage

- [Non-Interactive Init](../how-to/non-interactive-init.md)
- [Install Spec Kitty](../how-to/install-spec-kitty.md)
