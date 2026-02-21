# Backport Notes: Status Engine to 0.1x (main)

**Feature**: 034-feature-status-state-model-remediation
**Created**: 2026-02-08
**Target branch**: main (0.1x line)
**Source branch**: 2.x (after feature merge)

## Context

The canonical status engine (12 modules in `src/specify_cli/status/`) was
developed entirely on the 2.x branch across multiple work packages. The
0.1x line (main branch) needs this engine for backward-compatible status
tracking. This document describes the backport strategy.

## Structural Differences: 2.x vs 0.1x

### Present on 2.x, Absent on 0.1x

| Component | Path | Impact on Status Engine |
|-----------|------|----------------------|
| SaaS sync pipeline | `src/specify_cli/sync/` | `emit.py` has guarded import (`try/except ImportError`). No impact. |
| SaaS events | `src/specify_cli/sync/events.py` | Only used by `_saas_fan_out()` which becomes no-op. |

### Present on Both Branches

| Component | Path | Notes |
|-----------|------|-------|
| Frontmatter manager | `src/specify_cli/frontmatter.py` | Used by `legacy_bridge.py` and `migrate.py`. Verify API parity. |
| YAML config | `.kittify/config.yaml` | Used by `phase.py` for config-level phase setting. |
| Feature meta.json | `kitty-specs/<slug>/meta.json` | Used by `phase.py` for feature-level phase override. |
| Rich console | (dependency) | Used by `reconcile.py` for report formatting. Already in pyproject.toml. |
| ruamel.yaml | (dependency) | Used by `phase.py` for config reading. Already in pyproject.toml. |

### Missing on 0.1x (Must Add)

| Dependency | Used By | Action Required |
|-----------|---------|-----------------|
| `python-ulid` (or `ulid-py`) | `emit.py`, `reconcile.py`, `migrate.py` | Add to `[project.dependencies]` in pyproject.toml |

## Backport Strategy

### Approach: Cherry-Pick with Squash

Since the status engine was built across 15+ WP branches on 2.x, individual
cherry-picks would be fragile. Instead:

1. **After feature merge to 2.x**: All WP commits are on 2.x.
2. **Create backport branch from main**: `git checkout -b backport/034-status-engine main`
3. **Cherry-pick the relevant files** using `git checkout 2.x -- <paths>`:

   ```bash
   git checkout 2.x -- src/specify_cli/status/
   git checkout 2.x -- tests/specify_cli/status/
   ```

4. **Add missing dependency**: Update pyproject.toml to include `python-ulid`.
5. **Run tests on backport branch**: `pytest tests/specify_cli/status/ -x -q`
6. **Verify branch detection**: `is_01x_branch()` must return True on main.
7. **PR to main**: Create PR with parity test results.

### Files to Backport

**Source code** (all files in `src/specify_cli/status/`):

- `__init__.py` - Package init with public API
- `models.py` - Lane enum, StatusEvent, StatusSnapshot, evidence dataclasses
- `transitions.py` - State machine matrix, guards, validation
- `reducer.py` - Deterministic event replay with rollback-aware precedence
- `store.py` - JSONL append-only event log
- `phase.py` - Phase resolution with 0.1x cap
- `emit.py` - Orchestration pipeline with SaaS fan-out guard
- `legacy_bridge.py` - Frontmatter view updates
- `validate.py` - Schema, transition, evidence, and drift validation
- `doctor.py` - Health check framework
- `reconcile.py` - Cross-repo drift detection and reconciliation
- `migrate.py` - Legacy frontmatter-to-event-log migration

**Tests** (all files in `tests/specify_cli/status/`):

- `conftest.py` - Shared fixtures
- `test_models.py`
- `test_transitions.py`
- `test_reducer.py`
- `test_store.py`
- `test_phase.py`
- `test_emit.py`
- `test_legacy_bridge.py`
- `test_validate.py`
- `test_doctor.py`
- `test_reconcile.py`
- `test_migrate.py`
- `test_conflict_resolution.py`
- `test_lane_expansion.py`
- `test_parity.py` - Cross-branch parity verification tests

## Guard Mechanisms Already in Place

### 1. SaaS Fan-Out Guard (emit.py)

```python
def _saas_fan_out(event, feature_slug, repo_root):
    try:
        from specify_cli.sync.events import emit_wp_status_changed
        emit_wp_status_changed(...)
    except ImportError:
        pass  # SaaS sync not available (0.1x branch)
    except Exception:
        logger.warning("SaaS fan-out failed...")
```

**Result on 0.1x**: Silent no-op. No `sync/` package means `ImportError` is caught.

### 2. Legacy Bridge Guard (emit.py)

```python
try:
    from specify_cli.status.legacy_bridge import update_all_views
    update_all_views(feature_dir, snapshot)
except ImportError:
    pass  # WP06 not yet available
except Exception:
    logger.warning("Legacy bridge update failed...")
```

**Result on 0.1x**: Works normally since `legacy_bridge` is part of the status package.

### 3. Phase Cap Guard (phase.py)

```python
if is_01x_branch(repo_root) and phase > MAX_PHASE_01X:
    phase = MAX_PHASE_01X
    source = f"{source} (capped to {MAX_PHASE_01X} on 0.1x)"
```

**Result on 0.1x**: Any phase > 2 is capped at 2. Currently all valid phases (0, 1, 2) are within range, so this is a future-proofing mechanism.

## Verification After Backport

Run the parity test suite:

```bash
# On the backport branch (based on main):
pytest tests/specify_cli/status/test_parity.py -x -q -v

# Full status test suite:
pytest tests/specify_cli/status/ -x -q

# Verify branch detection:
python -c "
from specify_cli.status.phase import is_01x_branch
from pathlib import Path
print(f'is_01x_branch: {is_01x_branch(Path(\".\"))}')  # Should be True on main
"
```

## Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| `FrontmatterManager` API changed on main | Low | Tests will catch import/API errors |
| `ulid` dependency version conflict | Low | Use same version range as 2.x |
| Phase detection incorrect on main | Low | `is_01x_branch()` tested with mock; verify live |
| Merge conflicts in pyproject.toml | Medium | Manual resolution; only adding one dependency |
| Existing frontmatter status on main | Medium | `migrate.py` handles idempotent bootstrap |
