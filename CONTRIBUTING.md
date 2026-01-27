## Contributing to Spec Kitty

Hi there! We're thrilled that you'd like to contribute to Spec Kitty. Contributions to this project are [released](https://help.github.com/articles/github-terms-of-service/#6-contributions-under-repository-license) to the public under the [project's open source license](LICENSE).

Spec Kitty is inspired by GitHub's [Spec Kit](https://github.com/github/spec-kit). Please preserve upstream attribution when referencing historical work or documentation.

Please note that this project is released with a [Contributor Code of Conduct](CODE_OF_CONDUCT.md). By participating in this project you agree to abide by its terms.

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

### Test Isolation

Tests use several mechanisms to ensure they run against source code:

- **PYTHONPATH**: Points to `src/` directory
- **SPEC_KITTY_CLI_VERSION**: Overrides version detection
- **SPEC_KITTY_TEST_MODE**: Prevents fallback to installed package
- **isolated_env fixture**: Provides consistent environment for all tests

All integration tests use the `run_cli` fixture which handles this automatically.

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
4. Ensure memory files (`memory/constitution.md`) are updated if major process changes are made

## Release Process

Spec Kitty follows a structured release process using GitHub Actions for automated PyPI publishing.

### Release Workflow

1. **Create a release branch**
   ```bash
   git checkout -b release/X.Y.Z
   ```

2. **Update version number**
   - Edit `pyproject.toml` and update the `version` field
   - Use [Semantic Versioning](https://semver.org/):
     - **Patch** (X.Y.Z): Bug fixes, small improvements
     - **Minor** (X.Y.0): New features, backward compatible
     - **Major** (X.0.0): Breaking changes

3. **Update CHANGELOG.md**
   - Add a new version section under `## [Unreleased]`:
     ```markdown
     ## [X.Y.Z] - YYYY-MM-DD

     ### Added
     - New features go here

     ### Fixed
     - Bug fixes go here

     ### Changed
     - Breaking changes or major updates
     ```
   - Follow the [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format
   - Be specific about what changed and why it matters

4. **Commit the version bump**
   ```bash
   git add pyproject.toml CHANGELOG.md
   git commit -m "chore: Bump version to X.Y.Z"
   ```

5. **Push and create a pull request**
   ```bash
   git push origin release/X.Y.Z
   gh pr create --title "Release X.Y.Z: Brief description" \
                --body "Release notes..." \
                --base main
   ```

6. **Wait for PR approval and merge**
   - The Release Readiness Check workflow will validate:
     - Version is properly bumped
     - CHANGELOG.md has an entry for the new version
     - Tests pass
     - Package builds successfully
   - Get approval from a maintainer
   - Merge the PR (use "Merge commit" strategy, not squash)

7. **Create and push the release tag**
   ```bash
   git checkout main
   git pull origin main
   git tag -a vX.Y.Z -m "Release vX.Y.Z

   Brief description of what's in this release.
   "
   git push origin vX.Y.Z
   ```

8. **Automated publishing**
   - Pushing the tag triggers `.github/workflows/release.yml`
   - The workflow will:
     - Run all tests
     - Validate release metadata
     - Build wheel and source distributions
     - Publish to PyPI (requires `PYPI_API_TOKEN` secret)
     - Create a GitHub Release with artifacts
   - Monitor the workflow: `gh run watch`

9. **Verify the release**
   ```bash
   # Check the GitHub release
   gh release view vX.Y.Z

   # Verify PyPI upload
   pip install --upgrade spec-kitty-cli
   spec-kitty --version  # Should show X.Y.Z
   ```

10. **Clean up**
    ```bash
    git branch -d release/X.Y.Z
    git push origin --delete release/X.Y.Z
    ```

### Release Checklist

Before creating a release PR, ensure:

- [ ] All intended changes are merged to main
- [ ] Version number follows semantic versioning
- [ ] CHANGELOG.md is updated with clear, user-focused descriptions
- [ ] All tests pass locally: `pytest tests/`
- [ ] Package builds without errors: `python -m build`
- [ ] No direct commits to main (always use PRs)

### Important Notes

- **Never push directly to main** - Always create a PR for version bumps
- **Don't skip the PR review** - The Release Readiness Check validates release metadata
- **Tag after merge, not before** - Create the tag only after the version bump PR is merged
- **Use annotated tags** - Always use `git tag -a`, not `git tag`
- **Monitor the release workflow** - Watch for failures and be ready to fix issues
- **PyPI is immutable** - Once published, a version cannot be changed (only yanked)

### Troubleshooting Releases

#### Release workflow fails with "Version already exists on PyPI"
- You attempted to release a version that's already published
- Bump to the next version number and retry

#### Release workflow fails with "PYPI_API_TOKEN not configured"
- The GitHub Actions secret is missing or invalid
- Contact a repository maintainer to configure the secret

#### Tests fail in release workflow
- Fix the failing tests and push to the release branch
- The workflow will re-run on the updated branch

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
