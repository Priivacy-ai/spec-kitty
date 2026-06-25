## Contributing to Spec Kitty

Hi there! We're thrilled that you'd like to contribute to Spec Kitty. Contributions to this project are [released](https://help.github.com/articles/github-terms-of-service/#6-contributions-under-repository-license) to the public under the [project's open source license](LICENSE).

Spec Kitty is inspired by GitHub's [Spec Kit](https://github.com/github/spec-kit). Please preserve upstream attribution when referencing historical work or documentation.

Please note that this project is released with a [Contributor Code of Conduct](CODE_OF_CONDUCT.md). By participating in this project you agree to abide by its terms.

## Developer Setup

After cloning, bootstrap your environment:

```bash
uv sync --frozen --all-extras
make dev-setup
```

`make dev-setup` syncs dependencies and installs all spec-kitty slash commands
for your configured AI agents (including `/spec-kitty.specify` and related
commands in Claude Code). Re-run after pulling changes or after any
spec-kitty template change.

Without running `make dev-setup`, planning commands like `/spec-kitty.specify`
may be absent from your AI coding agent. `make dev-setup` always repairs this —
it is idempotent, so running it multiple times is safe.

> **Windows users**: `make` requires WSL or a GNU Make equivalent.
> Alternatively, run the setup steps manually:
> ```bash
> uv sync --frozen --all-extras
> uv run spec-kitty doctor skills --fix
> ```

## Contributor Recognition

This repository uses [All Contributors](https://allcontributors.org/) to recognize project contributions beyond code.

Code contributions are synced automatically by the scheduled GitHub workflow in
`.github/workflows/all-contributors-sync.yml`, which updates `.all-contributorsrc`
and `README.md` from repository activity without requiring PR comments.

Non-code recognition remains maintainer-driven. That includes both new
contributions and retroactive backfill for earlier docs, design, bug reports,
feature requests, mentoring, or other project help that deserves recognition.

For non-code contributions or manual corrections, maintainers can still add recognition from an issue or PR comment:

```text
@all-contributors please add @github-username for doc,design,ideas,bug
```

Supported contribution types are listed in the [emoji key](https://allcontributors.org/en/emoji-key/).

## Supported AI Agents

Spec Kitty supports **12 AI coding agents**. When contributing features that affect slash commands, migrations, or templates, ensure changes apply to ALL agents:

- **Claude Code** (`.claude/commands/`)
- **GitHub Copilot** (`.github/prompts/`)
- **GitHub Codex** (`.codex/prompts/`)
- **OpenCode** (`.opencode/command/`)
- **Google Gemini** (`.gemini/commands/`)
- **Cursor** (`.cursor/commands/`)
- **Windsurf** (`.windsurf/workflows/`)
- **Qwen Code** (`.qwen/commands/`)
- **Kilocode** (`.kilocode/workflows/`)
- **Augment Code** (`.augment/commands/`)
- **Roo Cline** (`.roo/commands/`)
- **Amazon Q** (`.amazonq/prompts/`)

**For contributors**: Use the `AGENT_DIRS` constant from `src/specify_cli/upgrade/migrations/m_0_9_1_complete_lane_migration.py` when writing migrations or features that affect slash commands.

## Prerequisites for running and testing code

These are one time installations required to be able to test your changes locally as part of the pull request (PR) submission process.

1. Install [Python 3.11+](https://www.python.org/downloads/)
1. Install [uv](https://docs.astral.sh/uv/) for package management
1. Install [Git](https://git-scm.com/downloads)
1. Have an [AI coding agent available](README.md#-supported-ai-agents)

### Shared Dependencies

Spec-kitty's shared libraries are published to PyPI and resolved automatically by
`uv sync` — **no SSH access or special repository permissions are required for
local development**:

- **[spec-kitty-events](https://pypi.org/project/spec-kitty-events/)** — event system and mission-next integration.
- **[spec-kitty-tracker](https://pypi.org/project/spec-kitty-tracker/)** — tracker consumer surface.

Compatibility ranges are declared in `pyproject.toml`; exact pinned versions live
in `uv.lock`.

`spec-kitty-runtime` is no longer a dependency: the CLI's runtime surface is
internalized under `src/runtime/next/`, and its absence is enforced by
`tests/architectural/test_pyproject_shape.py`.

## Running Tests

Spec Kitty's test suite is designed to run against source code, not installed packages. This ensures tests verify the current code, not a previously installed version.

### Quick Start

```bash
# Install dependencies (one time)
uv sync

# Run all tests
pytest

# Run specific test categories
pytest tests/integration/        # Integration tests
pytest tests/unit/               # Unit tests
pytest tests/integration/test_version_isolation.py  # Isolation tests
```

To run the suite in parallel (typically ≥2× faster on a ≥4-core machine), plus
the serial daemon pass and the coverage-neutrality gates, see
[Running the test suite in parallel](development/testing-parallel.md).

### Testing Unreleased Main or a Pull Request

When you need to test the current `main` branch or a specific pull request
before it is published to PyPI, avoid replacing your normal global
`spec-kitty` install unless that is the thing you are testing.

For normal contributor work, run from a source checkout:

```bash
git clone https://github.com/Priivacy-ai/spec-kitty.git
cd spec-kitty

# Latest main:
git switch main
git pull --ff-only

# Or a specific pull request:
gh pr checkout <PR_NUMBER>

uv sync --frozen --all-extras

SPEC_KITTY_NO_UPGRADE_CHECK=1 SPEC_KITTY_NO_NAG=1 \
  .venv/bin/spec-kitty --version
```

For a one-shot smoke test without cloning or installing a persistent tool, use
`uvx --isolated`:

```bash
# Latest main:
SPEC_KITTY_NO_UPGRADE_CHECK=1 SPEC_KITTY_NO_NAG=1 \
  uvx --isolated --from "git+https://github.com/Priivacy-ai/spec-kitty.git@main" \
  spec-kitty --version

# Specific pull request:
SPEC_KITTY_NO_UPGRADE_CHECK=1 SPEC_KITTY_NO_NAG=1 \
  uvx --isolated --from "git+https://github.com/Priivacy-ai/spec-kitty.git@refs/pull/<PR_NUMBER>/head" \
  spec-kitty --version
```

For a temporary installed binary, isolate both the tool environment and the
generated executable:

```bash
tmp="$(mktemp -d)"

UV_TOOL_DIR="$tmp/tools" UV_TOOL_BIN_DIR="$tmp/bin" \
  uv tool install --force \
  "spec-kitty-cli @ git+https://github.com/Priivacy-ai/spec-kitty.git@refs/pull/<PR_NUMBER>/head"

SPEC_KITTY_NO_UPGRADE_CHECK=1 SPEC_KITTY_NO_NAG=1 \
  "$tmp/bin/spec-kitty" --version

rm -rf "$tmp"
```

If you are testing a fork branch or an exact commit, replace the URL/ref with
`git+https://github.com/<OWNER>/spec-kitty.git@<BRANCH_OR_SHA>`. Hosted
tracker and sync flows are opt-in; set `SPEC_KITTY_ENABLE_SAAS_SYNC=1` only
when the scenario explicitly exercises those flows.

### Test Isolation

Tests use several mechanisms to ensure they run against source code:

- **PYTHONPATH**: Points to `src/` directory
- **SPEC_KITTY_CLI_VERSION**: Overrides version detection
- **SPEC_KITTY_TEST_MODE**: Prevents fallback to installed package
- **isolated_env fixture**: Provides consistent environment for all tests

All integration tests use the `run_cli` fixture which handles this automatically.

### Pytest collection fails with "cannot import name 'normalize_event_id' from 'spec_kitty_events'"

**Symptom**: Pytest collection fails before any tests run with:

```
ImportError: cannot import name 'normalize_event_id' from 'spec_kitty_events' (unknown location)
```

**Cause**: Local PEP 420 namespace-package corruption from a partial `pip uninstall`. The wheel
is fine; CI is unaffected. This is **NOT** a Spec Kitty bug — it is a Python install integrity
issue.

**Diagnostic**:

```bash
python -c "import spec_kitty_events; print(repr(spec_kitty_events.__file__), spec_kitty_events.__path__)"
# Healthy:   prints a path ending in __init__.py
# Corrupt:   prints None followed by _NamespacePath([...])  ← this is the bad state
```

**Fix**:

```bash
uv sync --reinstall-package spec-kitty-events
```

Per the closing comment on [#1137](https://github.com/Priivacy-ai/spec-kitty/issues/1137), the
Spec Kitty code path deliberately does NOT fall back to importing from
`spec_kitty_events.models.*` — that would violate the FR-024 frozen public-surface architectural
contract (enforced by `tests/architectural/test_events_tracker_public_imports.py`) and mask local
environment corruption that future contributors should still encounter visibly.

---

### Troubleshooting Version Issues

If you see errors like "Version Mismatch Detected", it means you have a pip-installed version of spec-kitty-cli that doesn't match your source code version.

**Solution:**

```bash
# Uninstall any installed version
pip uninstall spec-kitty-cli -y

# Run tests again
pytest
```

This is the most common test issue and is easy to fix. The test isolation system will detect mismatches automatically.

### Troubleshooting Shared Package Import Issues

If pytest fails during collection with an error like:

```text
ImportError: cannot import name 'normalize_event_id' from 'spec_kitty_events' (unknown location)
```

check whether Python is resolving `spec_kitty_events` as a namespace package:

```bash
python - <<'PY'
import spec_kitty_events

print(repr(getattr(spec_kitty_events, "__file__", None)))
print(spec_kitty_events.__path__)
PY
```

Healthy output points at `spec_kitty_events/__init__.py`. Broken output shows
`None _NamespacePath(...)`, which means the local install is corrupted. Rebuild
the project environment with:

```bash
uv sync --reinstall-package spec-kitty-events
```

If the broken package lives in a global or Homebrew Python environment, remove
the stale `spec_kitty_events/` directory and matching `.dist-info/` metadata
from that interpreter's `site-packages`, then reinstall
`spec-kitty-events`. See
[Diagnose Installation Problems](docs/how-to/diagnose-installation.md#9-shared-package-imports-resolve-as-a-namespace-package)
for the full recovery procedure.

### How Test Isolation Works

The test infrastructure guarantees that tests always use source code:

1. **Environment Variables**: Set by `isolated_env` fixture in `tests/integration/conftest.py`
2. **Test Mode Enforcement**: `SPEC_KITTY_TEST_MODE=1` forces CLI to use source version
3. **Fail-Fast**: If fixtures are misconfigured, tests fail immediately with clear error
4. **CI Verification**: GitHub Actions verify version consistency before running tests

For more details, see `tests/README.md`.

## Submitting a pull request

>[!NOTE]
>If your pull request introduces a large change that materially impacts the work of the CLI or the rest of the repository (e.g., you're introducing new templates, arguments, or otherwise major changes), make sure that it was **discussed and agreed upon** by the project maintainers. Pull requests with large changes that did not have a prior conversation and agreement will be closed.

1. Fork and clone the repository
1. Configure and install the dependencies: `uv sync`
1. Make sure the CLI works on your machine: `uv run spec-kitty --help`
1. Create a new branch: `git checkout -b my-branch-name`
1. Make your change, add tests, and make sure everything still works
1. Test the CLI functionality with a sample project if relevant
1. Push to your fork and submit a pull request
1. Wait for your pull request to be reviewed and merged.

Here are a few things you can do that will increase the likelihood of your pull request being accepted:

- Follow the project's coding conventions.
- Write tests for new functionality.
- Update documentation (`README.md`, `spec-driven.md`) if your changes affect user-facing features.
- Keep your change as focused as possible. If there are multiple changes you would like to make that are not dependent upon each other, consider submitting them as separate pull requests.
- Write a [good commit message](http://tbaggery.com/2008/04/19/a-note-about-git-commit-messages.html).
- Test your changes with the Spec-Driven Development workflow to ensure compatibility.

## Development workflow

When working on spec-kitty:

1. Test changes with the `spec-kitty` CLI commands (`/spec-kitty.specify`, `/spec-kitty.plan`, `/spec-kitty.tasks`) in your coding agent of choice
2. Verify templates are working correctly in `templates/` directory
3. Test script functionality in the `scripts/` directory
4. Ensure memory files (`memory/charter.md`) are updated if major process changes are made

## Release Process

Spec Kitty follows a structured release process using GitHub Actions for automated PyPI publishing.

> **For AI agents**: Use the `/release` skill (`.claude/skills/release/SKILL.md`) for a step-by-step guide.

### Branch Strategy

Spec Kitty maintains two long-lived branches:

- **`main`** — The release branch. All tags MUST be created from `main`.
- **`2.x`** — Development branch for the next major version.

If changes are made on `2.x`, cherry-pick them to `main` before releasing. The `2.x` branch may have test failures that do not affect `main`.

### Quick Release (Patch)

For simple bug fixes or improvements already committed to `main`:

```bash
# 1. Bump version and update changelog
#    Edit pyproject.toml: version = "X.Y.Z"
#    Edit CHANGELOG.md: add section after [Unreleased]

# 2. Commit
git add pyproject.toml CHANGELOG.md
git commit -m "chore: Bump version to X.Y.Z"
git push origin main

# 3. Tag and push
git tag -a vX.Y.Z -m "Release vX.Y.Z - Brief description"
git push origin vX.Y.Z

# 4. Monitor
unset GITHUB_TOKEN && gh run list --workflow=release.yml --limit=1
unset GITHUB_TOKEN && gh run watch <run-id>

# 5. Verify
unset GITHUB_TOKEN && gh release view vX.Y.Z
pipx install --force spec-kitty-cli==X.Y.Z
```

### Full Release (Minor/Major)

For larger releases with multiple changes:

1. **Create a release branch**
   ```bash
   git checkout -b release/X.Y.Z main
   ```

2. **Update version number** in `pyproject.toml`
   - Use [Semantic Versioning](https://semver.org/):
     - **Patch** (X.Y.Z): Bug fixes, small improvements
     - **Minor** (X.Y.0): New features, backward compatible
     - **Major** (X.0.0): Breaking changes

3. **Update CHANGELOG.md**
   - Add a new version section immediately after `## [Unreleased]`:
     ```markdown
     ## [X.Y.Z] - YYYY-MM-DD

     ### <emoji> <Category>

     **Short bold summary**:
     - Bullet point details
     ```
   - Categories used in this project (with emoji headings):
     - `### ✨ Added` — New features
     - `### 🔧 Improved` — Enhancements to existing features
     - `### 🐛 Fixed` — Bug fixes
     - `### 💥 Breaking` — Breaking changes
     - `### 📝 Architecture` — ADRs, design decisions
     - `### 🧹 Maintenance` — Refactoring, dependency updates
   - Use ISO date format: `YYYY-MM-DD`

4. **Create a pull request**
   ```bash
   git push origin release/X.Y.Z
   gh pr create --title "Release X.Y.Z: Brief description" --base main
   ```

5. **Wait for PR checks and merge**
   - The Release Readiness Check workflow validates version, changelog, and tests
   - Get approval from a maintainer
   - Merge the PR (use "Merge commit" strategy, not squash)

6. **Create and push the release tag**
   ```bash
   git checkout main && git pull origin main
   git tag -a vX.Y.Z -m "Release vX.Y.Z - Brief description"
   git push origin vX.Y.Z
   ```

7. **Monitor the workflow**
   ```bash
   unset GITHUB_TOKEN && gh run list --workflow=release.yml --limit=1
   unset GITHUB_TOKEN && gh run watch <run-id>
   ```
   Note: `unset GITHUB_TOKEN` is needed because the env var token may have limited scopes (e.g., only `copilot`). The keyring token has full `repo` scope.

8. **Verify the release**
   ```bash
   unset GITHUB_TOKEN && gh release view vX.Y.Z
   pipx install --force spec-kitty-cli==X.Y.Z
   ```

9. **Clean up**
   ```bash
   git branch -d release/X.Y.Z
   git push origin --delete release/X.Y.Z
   ```

### What the Release Workflow Does

Pushing a `v*.*.*` tag triggers `.github/workflows/release.yml`, which:

1. Checks out the tagged commit
2. Installs dependencies (including private `spec-kitty-events` via SSH deploy key)
3. Verifies no version mismatch between source and installed package
4. **Runs the full test suite** (2000+ tests)
5. Validates release metadata (`scripts/release/validate_release.py --mode tag`)
6. Validates repository URLs match `pyproject.toml`
7. Builds wheel and source distributions
8. Verifies wheel contains all migration files
9. Extracts changelog for release notes
10. Publishes to PyPI
11. Creates a GitHub Release with artifacts

### Release Checklist

Before tagging a release, ensure:

- [ ] You are on the `main` branch (not `2.x`)
- [ ] Version number follows semantic versioning
- [ ] CHANGELOG.md is updated with emoji category headings
- [ ] Tests pass locally: `pytest tests/`
- [ ] If changes were on `2.x`, they have been cherry-picked to `main`

### Important Notes

- **Tags MUST be created from `main`** — the `2.x` branch has pre-existing test failures that cause the release workflow to fail
- **Use annotated tags** — always use `git tag -a`, not `git tag`
- **Monitor the release workflow** — watch for failures and be ready to fix issues
- **PyPI is immutable** — once published, a version cannot be changed (only yanked)
- **PyPI CDN caching** — `pipx upgrade` may not find the new version immediately; use `pipx install --force spec-kitty-cli==X.Y.Z` instead

### Troubleshooting Releases

#### Release workflow fails — check the actual error first

The workflow prints a generic error listing three possible causes ("PYPI_API_TOKEN", "version/changelog mismatch", "Tests failed") whenever ANY step fails. Check the actual failing step:

```bash
unset GITHUB_TOKEN && gh run view <run-id> --log-failed | head -80
```

#### Tests fail in the release workflow

The most common cause. To fix:

```bash
# 1. Fix the failing test
# 2. Commit and push to main
# 3. Delete the broken tag
git tag -d vX.Y.Z
git push origin :refs/tags/vX.Y.Z
# 4. Re-tag from the fixed commit
git tag -a vX.Y.Z -m "Release vX.Y.Z - Brief description"
git push origin vX.Y.Z
```

#### Tag was created from wrong branch

If you accidentally tagged from `2.x` instead of `main`:

```bash
git tag -d vX.Y.Z
git push origin :refs/tags/vX.Y.Z
git checkout main
git tag -a vX.Y.Z -m "Release vX.Y.Z - Brief description"
git push origin vX.Y.Z
```

#### Version already exists on PyPI

- You attempted to release a version that's already published
- Bump to the next version number and retry

#### Changelog validation fails

- Ensure CHANGELOG.md has a section matching the version in pyproject.toml
- Check the date format is `YYYY-MM-DD`
- Verify the version number is monotonically increasing

## AI contributions in Spec Kitty

> [!IMPORTANT]
>
> If you are using **any kind of AI assistance** to contribute to Spec Kitty,
> it must be disclosed in the pull request or issue.

We welcome and encourage the use of AI tools to help improve Spec Kitty! Many valuable contributions have been enhanced with AI assistance for code generation, issue detection, and feature definition.

That being said, if you are using any kind of AI assistance (e.g., agents, ChatGPT) while contributing to Spec Kitty,
**this must be disclosed in the pull request or issue**, along with the extent to which AI assistance was used (e.g., documentation comments vs. code generation).

If your PR responses or comments are being generated by an AI, disclose that as well.

As an exception, trivial spacing or typo fixes don't need to be disclosed, so long as the changes are limited to small parts of the code or short phrases.

An example disclosure:

> This PR was written primarily by GitHub Copilot.

Or a more detailed disclosure:

> I consulted ChatGPT to understand the codebase but the solution
> was fully authored manually by myself.

Failure to disclose this is first and foremost rude to the human operators on the other end of the pull request, but it also makes it difficult to
determine how much scrutiny to apply to the contribution.

In a perfect world, AI assistance would produce equal or higher quality work than any human. That isn't the world we live in today, and in most cases
where human supervision or expertise is not in the loop, it's generating code that cannot be reasonably maintained or evolved.

### What we're looking for

When submitting AI-assisted contributions, please ensure they include:

- **Clear disclosure of AI use** - You are transparent about AI use and degree to which you're using it for the contribution
- **Human understanding and testing** - You've personally tested the changes and understand what they do
- **Clear rationale** - You can explain why the change is needed and how it fits within Spec Kitty's goals  
- **Concrete evidence** - Include test cases, scenarios, or examples that demonstrate the improvement
- **Your own analysis** - Share your thoughts on the end-to-end developer experience

### What we'll close

We reserve the right to close contributions that appear to be:

- Untested changes submitted without verification
- Generic suggestions that don't address specific Spec Kitty needs
- Bulk submissions that show no human review or understanding

### Guidelines for success

The key is demonstrating that you understand and have validated your proposed changes. If a maintainer can easily tell that a contribution was generated entirely by AI without human input or testing, it likely needs more work before submission.

Contributors who consistently submit low-effort AI-generated changes may be restricted from further contributions at the maintainers' discretion.

Please be respectful to maintainers and disclose AI assistance.

## Resources

- [Spec-Driven Development Methodology](./spec-driven.md)
- [How to Contribute to Open Source](https://opensource.guide/how-to-contribute/)
- [Using Pull Requests](https://help.github.com/articles/about-pull-requests/)
- [GitHub Help](https://help.github.com)
