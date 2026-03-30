# Efficient Local Tooling

Use efficient, operation-appropriate local tools by default.

## Session record

- Record the locally available preferred tools, the tool choice for the current session, and any missing-tool remediation in `.kittify/memory/available_tooling.md`.
- When a preferred tool is missing, warn the user that a more efficient option exists and offer to guide them through installation or setup before falling back.
- Use `has` when it helps confirm whether a preferred tool is installed and to capture that result in the session tooling record.

Examples:

```bash
has rg fd jq yq
has lnav ncdu bat
```

## Repository search

- Prefer `rg` over `grep`, `git grep`, or `find | xargs grep` for repository text searches.
- Scope searches deliberately with options such as `-n`, `-l`, `--type`, and path filters.
- Prefer `fd` over slower recursive `find` usage for file and path discovery when you are locating files rather than searching file contents.
- Use `fzf` to narrow large result sets interactively when a non-interactive `rg` or `fd` result is too broad.

Examples:

```bash
rg -n "Directive" src/doctrine
rg --type py "validate_" src
rg -l "TODO" tests/doctrine
fd '\.directive\.yaml$' src/doctrine
fd prompt src .kittify | fzf
```

## Large-file inspection

- Prefer `less` or another pager for large files instead of dumping them directly with `cat`.
- Use targeted extraction commands when only a file section is needed.
- Use `bat` for syntax-highlighted previews or short, structured inspection, but keep `less` as the default for very large files.

Examples:

```bash
less CHANGELOG.md
sed -n '1,120p' README.md
bat --style=plain pyproject.toml
```

## Compressed content

- Prefer stream-oriented tools such as `zcat` when inspecting gzip-compressed content.
- Avoid unpacking archives to disk unless the workflow genuinely requires extracted files.

Examples:

```bash
zcat logs/app.log.gz | less
zcat snapshot.json.gz | jq '.items[0]'
```

## Structured data inspection

- Prefer `jq` for JSON inspection and transformation instead of ad hoc text matching.
- Prefer `yq` for YAML inspection and transformation when repository configuration or doctrine artifacts need structured queries.

Examples:

```bash
jq '.project.version' package.json
yq '.id' src/doctrine/directives/_proposed/028-search-tool-discipline.directive.yaml
```

## Logs and disk usage

- Prefer `lnav` for log-heavy workflows where indexed viewing, filtering, or multi-file navigation is materially better than a pager.
- Prefer `ncdu` for disk-usage investigation instead of manual recursive size checks.

Examples:

```bash
lnav logs/app.log
ncdu .
```

## Git ergonomics

- Prefer local git defaults that reduce noisy paging, expensive status scans, or accidental interactive flows in automation.
- Use repository-safe settings and explicit flags when they improve speed or reproducibility.

Examples:

```bash
git -c core.pager=cat status --short
git -c commit.gpgsign=false commit -m "..."
```

## Navigation

- Prefer `zoxide` for repeated navigation across large repositories or multi-worktree setups when jumping directly to known directories is faster than manual `cd` traversal.

Examples:

```bash
zoxide query src
z src
```

## Token-optimized proxies

- Prefer `rtk` (Rust Token Killer) as a CLI proxy for common dev operations when available. It reduces agent token consumption by 60-90% on operations like `git status`, `git diff`, `git log`, and file listing.
- `rtk` wraps standard commands and filters output to only the information agents need, eliminating noise that wastes context window budget.
- Use `rtk` meta commands directly (`rtk gain`, `rtk discover`) to inspect token savings and identify missed optimization opportunities.
- When `rtk` is installed, a hook-based rewrite layer can transparently redirect standard commands (e.g., `git status` → `rtk git status`) without requiring agents to change their behavior. This is the preferred enforcement path for agents that support pre-tool-use hooks.

Examples:

```bash
rtk gain                    # Show cumulative token savings
rtk gain --history          # Show per-command savings breakdown
rtk discover                # Analyze session history for missed rtk opportunities
rtk git status              # Token-optimized git status
rtk git diff                # Token-optimized git diff
rtk --version               # Verify installation
```

### Hook-based enforcement

Some agentic tooling providers (e.g., Claude Code) support pre-tool-use hooks that can intercept and rewrite shell commands before execution. When available, this provides a deterministic enforcement path: the hook rewrites eligible commands to their `rtk` equivalents transparently, without requiring the agent to be aware of `rtk` at all.

**Important**: Hook-based enforcement is NOT universally supported across all agent tool providers. It must not be relied on as the sole mechanism for tooling guidance. The directive and toolguide remain the primary guidance layer — hooks are an optional acceleration when the host environment supports them.

Example hook pattern (Claude Code `PreToolUse`):
```
git status  →  hook intercepts  →  rtk git status  →  agent receives filtered output
```

## Windows and WSL

- Prefer WSL for repository-scale Unix-oriented workflows on Windows when it materially improves tool availability or throughput.
- Use efficient native tools such as `robocopy` or `7z` when Windows-native workflows are required.
- Prefer faster copy or sync tools over slow exploratory copy loops.

Examples:

```powershell
robocopy src dst /E
7z x archive.tar.gz
wsl rg -n "TODO" /mnt/c/project
```

## Avoid

- `grep -R "..." .` for routine repository search
- `find . -type f ...` when `fd` covers the same path-discovery task more directly
- `cat` on large files when a pager or targeted slice is sufficient
- regex or text scraping when `jq` or `yq` can query the structure directly
- extracting gzip archives to disk just to inspect contents
- slow copy loops when `rsync`, `robocopy`, or an equivalent optimized tool is available
