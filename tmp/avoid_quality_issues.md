# Catching Quality Issues Ahead of Time

## Current State

SonarCloud flagged **129 issues** on the `develop` branch. Of these:

- **1 BLOCKER** (S2083 — false positive path traversal in `workflow.py`)
- **28 CRITICAL** (cognitive complexity + string duplication)
- **11 MAJOR** (unused params, async bugs, nested conditionals)
- **2 MINOR** (redundant exception, string literal)

Most of these could have been caught **before pushing** with local tooling.

## What We Fixed

| Category | Count | Fix |
|----------|-------|-----|
| CI missing lint deps | 1 | Added `[lint]` extras group to `pyproject.toml` |
| Test failures (datetime) | 2 | Replaced `datetime.utcnow()` with `datetime.now(timezone.utc)` |
| Test failures (paths) | 3 | Used `importlib.resources.files()` instead of relative paths |
| Unused parameters | 3 | Removed from function signatures + call sites |
| Async bugs (GC/cancel) | 4 | Store task refs, re-raise `CancelledError` |
| Code clarity | 4 | Merge conditionals, extract constants, simplify exceptions |
| Pydantic deprecations | 4 | Remove `class Config`/`json_encoders`, use `model_dump()` |

## What Remains

### Cognitive Complexity (S3776) — 15 functions

These need structural refactoring (extract methods, use early returns, reduce nesting):

| File | Function | Complexity | Limit |
|------|----------|-----------|-------|
| `agent/tasks.py:430` | (large function) | **131** | 15 |
| `dashboard/scanner.py:422` | (scanner logic) | **39** | 15 |
| `core/dependency_resolver.py:122` | | **25** | 15 |
| `cli/commands/implement.py:44` | | **24** | 15 |
| `constitution/resolver.py:43` | | **22** | 15 |
| `core/worktree.py:442` | | **21** | 15 |
| `cli/commands/auth.py:70` | | **20** | 15 |
| `core/vcs/git.py:62` | | **19** | 15 |
| `template/asset_generator.py:16` | | **19** | 15 |
| Several others | | 16-17 | 15 |

**Recommendation:** Tackle the worst offenders (131, 39, 25) as dedicated refactoring tasks. The 16-17 range can often be fixed with a single extract-method.

### String Duplication (S1192) — ~13 instances

Repeated string literals that should be constants. Quick wins.

### False Positive (S2083)

The path traversal flag on `workflow.py:999` is a false positive — `wp.path` is validated through `_normalize_wp_id()` regex + `locate_work_package()` filesystem search. If Sonar keeps flagging it, add an explicit assertion:

```python
assert str(wp.path.resolve()).startswith(str(tasks_root.resolve()))
```

## Prevention Strategy

### 1. Run linters locally before pushing

Add a pre-commit hook or just run:

```bash
# Quick check (~5s)
ruff check src tests

# Type check (~30s)
mypy --strict src/specify_cli

# Security scan
bandit -r src/ --severity-level medium
```

**Install the tools:**

```bash
pip install -e ".[lint]"
```

### 2. Add a `pre-push` git hook

Create `.githooks/pre-push`:

```bash
#!/bin/bash
set -e
echo "Running pre-push quality checks..."
ruff check src tests --quiet
echo "Ruff: OK"
```

Enable with: `git config core.hooksPath .githooks`

### 3. Configure ruff to catch Sonar-equivalent rules

Add to `pyproject.toml`:

```toml
[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "F",    # pyflakes
    "W",    # pycodestyle warnings
    "C90",  # mccabe complexity (equivalent to S3776)
    "ARG",  # unused arguments (equivalent to S1172)
    "B",    # bugbear (catches many Sonar-equivalent issues)
    "SIM",  # simplify (equivalent to S1066, S3358)
    "UP",   # pyupgrade (catches deprecated patterns)
    "ASYNC",# async issues (equivalent to S7497, S7502)
]

[tool.ruff.lint.mccabe]
max-complexity = 15  # Same threshold as SonarCloud
```

This single config would have caught **~80% of the Sonar issues locally**.

### 4. CI quality gate ordering

Current CI runs linting in parallel with tests. This is fine for speed, but consider:

- **Fast feedback:** Keep `ruff check` as the first step in the lint job (it takes <5s)
- **Fail fast:** Consider making lint a required check for PR merge

### 5. Track technical debt explicitly

For the 15 cognitive complexity violations, create a tracking issue:

```bash
gh issue create --title "refactor: reduce cognitive complexity in 15 functions" \
  --body "Functions exceeding SonarCloud complexity limit (15). Priority: tasks.py (131), scanner.py (39), dependency_resolver.py (25)."
```

## Summary

| Prevention Method | Issues Caught | Effort |
|-------------------|---------------|--------|
| `ruff check` with ARG, SIM, ASYNC | ~60% | 5s per run |
| `ruff check` with C90 (mccabe) | +15% (complexity) | Already included |
| `mypy --strict` | Type errors, unused imports | 30s per run |
| `bandit` | Security issues | 10s per run |
| Pre-push hook | All of the above | One-time setup |
| **Total** | **~80% of Sonar issues** | **<1 min local** |
