# Test Suite

## Design Intent

The test suite is a **readable description of system capabilities**, not a mirror of
internal module boundaries or a filing cabinet sorted by test-runner mechanics.

Four principles govern every decision about test structure:

### 1. Form follows function — vertical slices

Top-level directories map to system capabilities, not to source packages or test types:

```
tests/
  missions/         — mission lifecycle, schema, loading, guards
  merge/            — merge workflow, preflight, multi-parent, conflict resolution
  agent/            — agent config, context, commands, workflow, review
  tasks/            — WP management, planning, pre-commit guard, move-task
  git_ops/          — branch ops, worktree, preflight, stale detection, safe commit
  status/           — status model, lane management, CLI, validation
  upgrade/          — migrations, upgrade path, version detection
  init/             — project initialisation, constitution setup
  sync/             — background sync, event emission, transport, offline queue
  runtime/          — bootstrap, doctor, resolver, global convergence
  research/         — research workflow, research plan deliverables
  next/             — next-command loop, prompt builder, runtime bridge
  cross_cutting/    — concerns that cut across multiple slices (encoding, packaging, versioning, dashboard)
  doctrine/         — schema and link-integrity validation of canonical YAML/Markdown artefacts
  adversarial/      — security and attack-surface tests
  e2e/              — full CLI workflow smoke tests (outermost boundary)
  docs/             — documentation consistency and integrity
  release/          — release artefact validation
  legacy/           — 1.x-era tests, branch-gated (see below)
```

A new contributor looking for "tests that cover merge" navigates to `tests/merge/`.
A new test for a merge capability belongs in `tests/merge/`.

### 2. Test type is expressed orthogonally — markers and filename suffixes

Test type (unit vs integration) is a runner-mechanics concern. It is expressed through:

| Signal | Meaning |
|--------|---------|
| `pytest.mark.fast` | Pure-logic test — no subprocess, no git, sub-second |
| `pytest.mark.git_repo` | Creates a real git repository |
| `pytest.mark.slow` | Slow subprocess/CLI invocation (>5s) |
| `*_unit.py` filename | Mock-boundary unit test; always carries `fast` marker |
| `*_integration.py` filename | Real git/subprocess integration; carries `git_repo` or `slow` |

This allows orthogonal selection:

```bash
pytest -m fast                    # dev loop — pure logic only
pytest -m git_repo                # mid-tier — real git, no dashboard/e2e
pytest -m "not slow and not e2e"  # pre-commit gate
pytest tests/merge/               # everything for one capability
pytest tests/merge/ -m fast       # unit tests for one capability
```

### 3. Testing pyramid — many unit, fewer integration, few e2e

Every slice should have more `*_unit.py` tests than `*_integration.py` tests.
Unit tests mock at the responsibility boundary: stub what is outside the unit under
test, exercise real logic inside. Integration tests use real git repos and real CLI
invocations to verify the seams between components.

End-to-end tests in `tests/e2e/` exercise full CLI workflows and are the smallest tier.

### 4. Readability — tests as documentation

Each test file should open with a docstring that states its **scope** in one sentence.
Test names use plain English describing observable behaviour, not internal function
names. The three-block structure (Arrange / Act / Assert) is standard.

---

## Running Tests

```bash
# Dev loop — fast feedback, pure logic only (~5s)
pytest -m fast

# Mid-tier — real git repos, no dashboard/e2e (~2 min)
pytest -m git_repo

# Slow suite — subprocess CLI invocations (~30s)
pytest -m slow

# Everything for one capability
pytest tests/merge/

# Full suite
pytest

# Single file
pytest tests/merge/test_multi_parent_merge.py -v
```

---

## Writing Tests

### Placing a new test

1. Identify the capability slice (see directory list above).
2. If the test needs no real git repo: add to or create a `*_unit.py` file with
   `pytestmark = pytest.mark.fast`.
3. If the test needs a real git repo: add to or create a `*_integration.py` file with
   `pytestmark = pytest.mark.git_repo`.
4. If the concern cuts across multiple slices: use `tests/cross_cutting/`.

### Test body structure — four blocks

Every test follows four blocks in order. All four blocks are present even when trivial;
this makes the test's intent unambiguous without reading the implementation.

```
Arrange          — construct the specific inputs, objects, or state this test needs
Assumption check — assert the preconditions the test relies on (system state sanity)
Act              — call the single unit of behaviour under test
Assert           — verify the observable outcome
```

The **assumption check** block is the distinguishing addition over plain AAA. It makes
implicit preconditions explicit and turns obscure failures ("why did the assert fire?")
into clear failures ("the precondition was already wrong before act ran"). Skip it only
when there is genuinely nothing meaningful to check.

```python
def test_resolve_target_branch_uses_primary_when_no_override() -> None:
    """Falls back to primary branch when no override is configured."""
    # Arrange
    config: dict[str, str] = {}

    # Assumption check
    assert "target_branch" not in config, "config must be empty for this test to be meaningful"

    # Act
    with patch("specify_cli.core.git_ops.resolve_primary_branch", return_value="main"):
        result = resolve_target_branch(config)

    # Assert
    assert result == "main"
```

For integration tests where a fixture provides the pre-built state, the assumption
check verifies that the fixture produced the expected starting point:

```python
def test_merge_records_done_evidence(merge_repo: tuple[Path, Path, str]) -> None:
    """Merge command writes done evidence to WP frontmatter."""
    repo, worktree, slug = merge_repo

    # Arrange
    wp_file = worktree / "tasks" / "WP01.md"

    # Assumption check
    assert worktree.exists(), "fixture must have created the worktree directory"
    assert wp_file.exists(), "WP file must exist before merge runs"
    frontmatter = read_frontmatter(wp_file)
    assert "done_evidence" not in frontmatter, "done_evidence must not be pre-populated"

    # Act
    result = run_merge(repo, slug)

    # Assert
    assert result.returncode == 0
    updated = read_frontmatter(wp_file)
    assert "done_evidence" in updated
```

The comment labels (`# Arrange`, `# Assumption check`, `# Act`, `# Assert`) are
**always written**, including when a block is a single line. They are load-bearing
documentation, not clutter.

### Unit test conventions

```python
"""Scope: mock-boundary tests for resolve_target_branch — no real git."""
import pytest
from unittest.mock import patch

pytestmark = pytest.mark.fast


def test_resolve_target_branch_uses_primary_when_no_override() -> None:
    """Falls back to primary branch when no override is configured."""
    # Arrange
    config: dict[str, str] = {}

    # Assumption check
    assert "target_branch" not in config

    # Act
    with patch("specify_cli.core.git_ops.resolve_primary_branch", return_value="main"):
        result = resolve_target_branch(config)

    # Assert
    assert result == "main"
```

### Integration test conventions

```python
"""Scope: full merge workflow against a real git repo with worktrees."""
import pytest

pytestmark = pytest.mark.git_repo


def test_merge_records_done_evidence(merge_repo: tuple[Path, Path, str]) -> None:
    """Merge command writes done evidence to WP frontmatter."""
    repo, worktree, slug = merge_repo

    # Arrange
    wp_file = worktree / "tasks" / "WP01.md"

    # Assumption check
    assert worktree.exists()
    assert wp_file.exists()

    # Act
    result = run_merge(repo, slug)

    # Assert
    assert result.returncode == 0
    assert "done_evidence" in read_frontmatter(wp_file)
```

---

## Fixtures

Core fixtures are defined in `tests/conftest.py` and available everywhere:

| Fixture | Scope | Description |
|---------|-------|-------------|
| `isolated_env` | function | `os.environ` dict that blocks host `spec-kitty-cli`, sets `PYTHONPATH=src/` |
| `run_cli` | function | Callable that runs `spec-kitty` via venv subprocess inside a project dir |
| `temp_repo` | function | `tmp_path` with `git init`, user name/email configured |
| `feature_repo` | function | `temp_repo` with a full `kitty-specs/001-demo-feature/` tree |
| `merge_repo` | function | Two-branch repo with a WP worktree |
| `conflicting_wps_repo` | function | Repo with 3 WP branches all touching a shared file |
| `git_stale_workspace` | function | Repo where `main` has advanced past the WP branch |
| `dirty_worktree_repo` | function | WP worktree with uncommitted changes |

Integration-specific fixtures (requiring `test_project`, `dual_branch_repo`, etc.) live
in `tests/integration/conftest.py`.

---

## Legacy Tests

`tests/legacy/` contains 1.x-era tests that are skipped entirely on the 2.x branch
(enforced by `IS_2X_BRANCH` in `tests/branch_contract.py`). They are preserved as a
knowledge archive. The plan is to audit them for 2.x-relevant knowledge before
deleting the directory.

---

## Architecture Decision

The structural design is recorded in:
`architecture/2.x/adr/2026-03-15-1-vertical-slice-test-organisation.md`
