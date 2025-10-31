# Local Development Guide

This guide shows how to iterate on the `spec-kitty` CLI locally without publishing a release or committing to `main` first.

Remember that CLI commands will pause with `WAITING_FOR_*` tokens until you answer their discovery questions—handy when testing new prompt changes.

> Spec Kitty is a community-maintained fork of GitHub's [Spec Kit](https://github.com/github/spec-kit). The workflows below target the spec-kitty repository while keeping upstream attribution intact.

> Scripts now have both Bash (`.sh`) and PowerShell (`.ps1`) variants. The CLI auto-selects based on OS unless you pass `--script sh|ps`.

## 1. Clone and Switch Branches

```bash
git clone https://github.com/Priivacy-ai/spec-kitty.git
cd spec-kitty
# Work on a feature branch
git checkout -b your-feature-branch
```

## 2. Run the CLI Directly (Fastest Feedback)

You can execute the CLI via the module entrypoint without installing anything:

```bash
# From repo root
python -m src.specify_cli --help
python -m src.specify_cli init demo-project --ai claude --ignore-agent-tools --script sh
```

If you prefer invoking the script file style (uses shebang):

```bash
python src/specify_cli/__init__.py init demo-project --script ps
```

## 3. Use Editable Install (Isolated Environment)

Create an isolated environment using `uv` so dependencies resolve exactly like end users get them:

```bash
# Create & activate virtual env (uv auto-manages .venv)
uv venv
source .venv/bin/activate  # or on Windows PowerShell: .venv\Scripts\Activate.ps1

# Install project in editable mode
uv pip install -e .

# Now 'spec-kitty' entrypoint is available
spec-kitty --help
```

Re-running after code edits requires no reinstall because of editable mode.

## 4. Invoke with uvx Directly From Git (Current Branch)

`uvx` can run from a local path (or a Git ref) to simulate user flows:

```bash
uvx --from . spec-kitty init demo-uvx --ai copilot --ignore-agent-tools --script sh
```

You can also point uvx at a specific branch without merging (optional if you want to exercise the published GitHub flow):

```bash
# Push your working branch first
git push origin your-feature-branch
uvx --from git+https://github.com/Priivacy-ai/spec-kitty.git@your-feature-branch spec-kitty init demo-branch-test --script ps
```

### 4a. Absolute Path uvx (Run From Anywhere)

If you're in another directory, use an absolute path instead of `.`:

```bash
uvx --from /mnt/c/GitHub/spec-kitty spec-kitty --help
uvx --from /mnt/c/GitHub/spec-kitty spec-kitty init demo-anywhere --ai copilot --ignore-agent-tools --script sh
```

Set an environment variable for convenience:
```bash
export SPEC_KITTY_SRC=/mnt/c/GitHub/spec-kitty
uvx --from "$SPEC_KITTY_SRC" spec-kitty init demo-env --ai copilot --ignore-agent-tools --script ps
```

(Optional) Define a shell function:
```bash
spec-kitty-dev() { uvx --from "$SPEC_KITTY_SRC" spec-kitty "$@"; }
# Then
spec-kitty-dev --help
```

## 5. Testing Script Permission Logic

After running an `init`, check that shell scripts are executable on POSIX systems:

```bash
ls -l scripts | grep .sh
# Expect owner execute bit (e.g. -rwxr-xr-x)
```
On Windows you will instead use the `.ps1` scripts (no chmod needed).

## 6. Verify Bundled Workflow Helpers

After running `spec-kitty init`, confirm that the generated project contains the task workflow helpers introduced after the fork:

```bash
ls .kittify/scripts/tasks/
# expect tasks_cli.py plus helper modules
ls .kittify/scripts/bash/ | grep tasks-move-to-lane
```

Run one of the helpers (inside a generated feature worktree) to ensure Python fallbacks resolve correctly even without an installed package:

```bash
.kittify/scripts/bash/tasks-move-to-lane.sh FEATURE-SLUG WP01 planned --note "Smoke test"
```

Have an older project that still ships the legacy `tasks_cli.py` importing `specify_cli`? Refresh it in-place with the new standalone helpers:

```bash
/path/to/spec-kit/scripts/bash/refresh-kittify-tasks.sh /path/to/your/project
```

The script walks upward from the provided path (or the current directory if no argument is given), replaces `.kittify/scripts/tasks/` with the current repo copy, and leaves a `tasks_cli.py.legacy` backup alongside the updated files.

## 7. Run Lint / Basic Checks (Add Your Own)

Currently no enforced lint config is bundled, but you can quickly sanity check importability:
```bash
python -c "import specify_cli; print('Import OK')"
```

## 8. Build a Wheel Locally (Optional)

Validate packaging before publishing:

```bash
uv build
ls dist/
```
Install the built artifact into a fresh throwaway environment if needed.

## 9. Using a Temporary Workspace

When testing `init --here` in a dirty directory, create a temp workspace:

```bash
mkdir /tmp/spec-test && cd /tmp/spec-test
python -m src.specify_cli init --here --ai claude --ignore-agent-tools --script sh  # if repo copied here
```
Or copy only the modified CLI portion if you want a lighter sandbox.

## 10. Debug Network / TLS Skips

If you need to bypass TLS validation while experimenting:

```bash
spec-kitty check --skip-tls
spec-kitty init demo --skip-tls --ai gemini --ignore-agent-tools --script ps
```
(Use only for local experimentation.)

## 11. Rapid Edit Loop Summary

| Action | Command |
|--------|---------|
| Run CLI directly | `python -m src.specify_cli --help` |
| Editable install | `uv pip install -e .` then `spec-kitty ...` |
| Local uvx run (repo root) | `uvx --from . spec-kitty ...` |
| Local uvx run (abs path) | `uvx --from /mnt/c/GitHub/spec-kitty spec-kitty ...` |
| Git branch uvx | `uvx --from git+URL@branch spec-kitty ...` |
| Build wheel | `uv build` |
| Acceptance check | `spec-kitty accept --json` |
| Dashboard smoke test | `spec-kitty dashboard` |

## 12. Cleaning Up

Remove build artifacts / virtual env quickly:
```bash
rm -rf .venv dist build *.egg-info
```

## 13. Common Issues

| Symptom | Fix |
|---------|-----|
| `ModuleNotFoundError: typer` | Run `uv pip install -e .` |
| Scripts not executable (Linux) | Re-run init or `chmod +x scripts/*.sh` |
| Git step skipped | You passed `--no-git` or Git not installed |
| Wrong script type downloaded | Pass `--script sh` or `--script ps` explicitly |
| TLS errors on corporate network | Try `--skip-tls` (not for production) |

## 14. Next Steps

- Update docs and run through Quick Start using your modified CLI
- Open a PR when satisfied
- (Optional) Tag a release once changes land in `main`
