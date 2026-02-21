---
work_package_id: WP16
title: Backport to 0.1x & Parity Matrix
lane: "done"
dependencies:
- WP01
base_branch: 2.x
base_commit: a15c80388fc7a190603b5805406698505b777167
created_at: '2026-02-08T15:35:06.391529+00:00'
subtasks:
- T081
- T082
- T083
- T084
- T085
- T086
phase: Phase 3 - Delivery
assignee: ''
agent: ''
shell_pid: "80759"
review_status: "approved"
reviewed_by: "Robert Douglass"
history:
- timestamp: '2026-02-08T14:07:18Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP16 -- Backport to 0.1x & Parity Matrix

## IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

```bash
spec-kitty implement WP16 --base WP15
```

This WP depends on all previous WPs (WP01-WP15). It is the final implementation step before documentation. The workspace branches from WP15 to ensure all 2.x implementation and tests are available.

**Important**: This WP involves work on the 0.1x branch (main or release branches). The implementation will:

1. Start in the WP16 worktree (2.x line) to prepare the backport
2. Create a backport branch from `main` (0.1x target)
3. Cherry-pick or adapt modules from 2.x to the backport branch
4. Run parity tests on both branches
5. Generate the parity matrix document

---

## Objectives & Success Criteria

Backport Phases 0-2 to the 0.1x line with maximum parity and generate a parity matrix documenting any deltas. This WP delivers:

1. Identification of 0.1x target branches (main, release/0.13.x)
2. Adapted `status/` package ported to the 0.1x codebase
3. SaaS fan-out configured as a no-op on 0.1x (sync/ infrastructure absent)
4. Phase cap enforcement verified on 0.1x (max Phase 2, reconcile dry-run only)
5. Cross-branch parity tests passing on 0.1x with identical output
6. Parity matrix document listing every module with its delta status

**Success**: The same `sample_events.jsonl` processed by both 2.x and 0.1x reducers produces byte-identical `status.json` (excluding `materialized_at`). The parity matrix clearly documents every module as identical, adapted, or missing with justification.

---

## Context & Constraints

- **Spec**: `kitty-specs/034-feature-status-state-model-remediation/spec.md` -- User Story 10 (Dual-Branch Delivery), SC-003 (Cross-branch compatibility tests)
- **Plan**: `kitty-specs/034-feature-status-state-model-remediation/plan.md` -- Backport Strategy section (7 steps), AD-5 (Phase Configuration, 0.1x cap)
- **Data Model**: `kitty-specs/034-feature-status-state-model-remediation/data-model.md` -- All entities must be identical on both branches
- **Contracts**: `kitty-specs/034-feature-status-state-model-remediation/contracts/` -- Schemas are branch-independent; both branches must validate against them
- **Cross-branch fixtures**: `tests/cross_branch/fixtures/` from WP15 -- these are the shared fixtures for parity testing

**Key constraints**:

- Python 3.11+ on both branches
- The 0.1x line does NOT have the `sync/` package (SaaS infrastructure). Any references to `sync/events.py` must be handled gracefully.
- On 0.1x, `status reconcile --apply` must be disabled (dry-run only)
- On 0.1x, phase is capped at Phase 2 (no Phase 3 behaviors)
- The 0.1x line is heading toward 1.x then bug-fix mode -- changes must be stable and low-risk
- Cherry-picking may not apply cleanly due to branch divergence -- manual adaptation per file is expected
- No fallback mechanisms on either branch -- both must fail identically on invalid input
- The ULID dependency (`ulid` package) may need to be added to `pyproject.toml` on 0.1x if not already present

---

## Subtasks & Detailed Guidance

### Subtask T081 -- Identify 0.1x Target Branches

**Purpose**: Determine which branches need the backport and document the branch strategy.

**Steps**:

1. Check git branches for 0.1x targets:

   ```bash
   git branch -a | grep -E "(main|release/)"
   ```

2. Identify the primary target: `main` branch (0.1x line).

3. Check for release branches: `release/0.13.x`, `release/0.14.x`, etc.

4. Document the branch strategy:
   - Primary target: `main` (current 0.1x development)
   - Release branches: port only if actively maintained
   - Create backport branch: `034-feature-status-state-model-remediation-backport` from `main`

5. Verify the 0.1x codebase structure:

   ```bash
   git checkout main
   ls src/specify_cli/  # Verify expected directories
   python -m pytest tests/ -x --co  # Dry run to check test collection
   ```

6. Document findings in a temporary `backport-notes.md`:
   - Target branches
   - Missing dependencies (e.g., `ulid` package)
   - Structural differences (e.g., missing `sync/` package)
   - Existing `status/` code on main (if any -- should be none)

**Files**: None created permanently; notes are working documents

**Validation**:

- Target branches identified and accessible
- Codebase structure differences documented
- Missing dependencies identified

**Edge Cases**:

- `main` branch has diverged significantly from `2.x`: may need more manual adaptation than cherry-picking
- Release branch already has conflicting changes: skip release branch, note in parity matrix
- The `sync/` package does not exist on 0.1x: confirmed expected behavior

---

### Subtask T082 -- Cherry-Pick/Adapt Status Engine

**Purpose**: Port the `status/` package and CLI commands from 2.x to a backport branch from main.

**Steps**:

1. Create the backport branch:

   ```bash
   git checkout main
   git checkout -b 034-feature-status-state-model-remediation-backport
   ```

2. Cherry-pick or copy the following modules from 2.x:
   - `src/specify_cli/status/__init__.py`
   - `src/specify_cli/status/models.py`
   - `src/specify_cli/status/transitions.py`
   - `src/specify_cli/status/reducer.py`
   - `src/specify_cli/status/store.py`
   - `src/specify_cli/status/phase.py`
   - `src/specify_cli/status/legacy_bridge.py`
   - `src/specify_cli/status/doctor.py`
   - `src/specify_cli/status/reconcile.py`
   - `src/specify_cli/status/migrate.py` (if separate from legacy_bridge)
   - `src/specify_cli/cli/commands/agent/status.py`

3. Adapt imports for 0.1x:
   - Remove or guard `sync/events.py` imports:

     ```python
     # In status/__init__.py or the emit orchestration:
     try:
         from specify_cli.sync.events import emit_wp_status_changed
     except ImportError:
         emit_wp_status_changed = None  # SaaS not available on 0.1x
     ```

   - Verify all other imports resolve against 0.1x's codebase

4. Adapt `tasks_support.py` and `frontmatter.py` for 7-lane expansion (cherry-pick from WP05 or apply manually).

5. Adapt `merge/status_resolver.py` for rollback-aware resolution (cherry-pick from WP10).

6. Adapt `cli/commands/agent/tasks.py` for move-task delegation (cherry-pick from WP09).

7. Update `pyproject.toml` on the backport branch:
   - Add `ulid` dependency if missing
   - Verify version constraints match 2.x

8. Run the test suite to verify nothing is broken:

   ```bash
   python -m pytest tests/ -x -q
   ```

**Files**: All `status/` files (new on 0.1x), modified files in `tasks_support.py`, `frontmatter.py`, `merge/status_resolver.py`, `cli/commands/agent/tasks.py`

**Validation**:

- All adapted modules import without errors on 0.1x
- Existing tests continue to pass
- New status tests pass (after copying test files)

**Edge Cases**:

- Cherry-pick conflicts: resolve manually, preferring the 2.x implementation
- Import paths differ between branches: grep for all `from specify_cli.` imports and verify
- Some test fixtures reference 2.x-only features: skip or adapt those tests
- The `agent_utils/status.py` module may have different function signatures on 0.1x: review and adapt

---

### Subtask T083 -- SaaS Fan-Out as No-Op

**Purpose**: Verify that the emit orchestration pipeline handles the absence of `sync/events.py` gracefully.

**Steps**:

1. In the emit orchestration on 0.1x, the `try/except ImportError` pattern should already handle this:

   ```python
   try:
       from specify_cli.sync.events import emit_wp_status_changed
       _has_saas = True
   except ImportError:
       _has_saas = False
   ```

2. In the emit pipeline, gate the SaaS step:

   ```python
   if _has_saas:
       emit_wp_status_changed(...)
   # If not available, silently skip (not a fallback -- SaaS is optional functionality)
   ```

3. Verify this handling by running:

   ```python
   # On 0.1x, this import should fail gracefully:
   python -c "from specify_cli.status import emit_status_transition; print('OK')"
   ```

4. Write a specific test:

   ```python
   def test_saas_unavailable_no_error(tmp_path, monkeypatch):
       """When sync.events is unavailable, emit succeeds without SaaS fan-out."""
       monkeypatch.setattr("specify_cli.status._has_saas", False)
       # Emit a transition
       # Verify: no ImportError, event still appended to log
   ```

**Files**: Verify existing code in `status/__init__.py` or emit orchestration module

**Validation**:

- `emit_status_transition()` succeeds on 0.1x without SaaS
- No ImportError raised during normal operation
- Event is still appended to JSONL regardless of SaaS availability

**Edge Cases**:

- `sync/` package partially exists but `events.py` is missing: ImportError still caught
- SaaS configuration present in config but sync module absent: no error (config is ignored)
- Note: This is NOT a fallback mechanism. SaaS is optional infrastructure. On 0.1x, it simply does not exist. The canonical local model is the primary system.

---

### Subtask T084 -- Phase Cap Enforcement

**Purpose**: Verify that `resolve_phase()` caps at Phase 2 on 0.1x and that `reconcile --apply` is disabled.

**Steps**:

1. Verify `resolve_phase()` implementation on the backport branch:

   ```python
   def resolve_phase(repo_root: Path, feature_slug: str | None = None) -> tuple[int, str]:
       # ... existing resolution logic ...
       # Cap at Phase 2 on 0.1x
       MAX_PHASE = 2
       if resolved_phase > MAX_PHASE:
           resolved_phase = MAX_PHASE
       return resolved_phase, source
   ```

2. Add explicit branch check in `phase.py` (optional, for defense-in-depth):

   ```python
   import subprocess

   def _is_01x_branch() -> bool:
       """Check if current branch is on the 0.1x line."""
       try:
           result = subprocess.run(
               ["git", "rev-parse", "--abbrev-ref", "HEAD"],
               capture_output=True, text=True, timeout=5,
           )
           branch = result.stdout.strip()
           # 0.1x branches: main, release/0.1x.y, or backport branches
           return branch in ("main",) or branch.startswith("release/0.")
       except (subprocess.TimeoutExpired, FileNotFoundError):
           return False  # Can't determine -- don't cap
   ```

3. Verify `reconcile --apply` is disabled on 0.1x:
   - In `reconcile.py`, the apply-mode gate should check phase
   - On 0.1x with phase capped at 2, and reconcile apply requiring Phase 3, it is automatically disabled
   - Alternatively, add explicit check for 0.1x line in reconcile command

4. Write verification tests:

   ```python
   def test_phase_capped_at_2(tmp_path):
       """On 0.1x, phase never exceeds 2."""
       # Configure phase 3 in config
       config = tmp_path / ".kittify" / "config.yaml"
       config.parent.mkdir(parents=True)
       config.write_text("status:\n  phase: 3\n")
       phase, source = resolve_phase(tmp_path)
       assert phase <= 2

   def test_reconcile_apply_disabled_on_01x(tmp_path):
       """reconcile --apply raises error on 0.1x."""
       # Set up 0.1x environment
       # Attempt apply
       # Verify error message
   ```

**Files**: `src/specify_cli/status/phase.py` (verify/adapt), `src/specify_cli/status/reconcile.py` (verify apply gate)

**Validation**:

- `resolve_phase()` never returns >2 on 0.1x, regardless of config
- `reconcile --apply` fails with clear error message on 0.1x
- `reconcile --dry-run` works normally on 0.1x

**Edge Cases**:

- Config explicitly sets phase 3 on 0.1x: capped to 2, with warning about cap
- No config file: default phase (1) is within cap
- Running on a detached HEAD (no branch name): don't cap (can't determine branch line)

---

### Subtask T085 -- Run Parity Tests

**Purpose**: Copy cross-branch fixtures to 0.1x and verify byte-identical reducer output.

**Steps**:

1. Copy test fixtures from 2.x to the backport branch:

   ```bash
   # From the WP16 worktree:
   cp -r tests/cross_branch/ /path/to/backport/tests/cross_branch/
   ```

2. Copy the parity test:

   ```bash
   cp tests/cross_branch/test_parity.py /path/to/backport/tests/cross_branch/
   ```

3. Run the parity tests on the backport branch:

   ```bash
   cd /path/to/backport
   python -m pytest tests/cross_branch/test_parity.py -v
   ```

4. Verify byte-identical output:
   - Run reducer on `sample_events.jsonl` on 2.x -> capture output
   - Run reducer on `sample_events.jsonl` on 0.1x -> capture output
   - Compare byte-for-byte (excluding `materialized_at` timestamp)

5. Run the full status test suite on 0.1x:

   ```bash
   python -m pytest tests/specify_cli/status/ -v
   python -m pytest tests/integration/test_dual_write.py tests/integration/test_read_cutover.py -v
   ```

6. Document any test failures and their resolutions.

**Files**: `tests/cross_branch/` (copied to 0.1x)

**Validation**:

- All parity tests pass on both branches
- Reducer output is byte-identical (excluding timestamp)
- No test failures unique to 0.1x

**Edge Cases**:

- Test imports that reference 2.x-only modules: update import paths for 0.1x
- Test fixtures that assume SaaS availability: mock or skip on 0.1x
- Different Python minor versions between branches: verify both use 3.11+

---

### Subtask T086 -- Generate Parity Matrix

**Purpose**: Create a comprehensive document listing every module with its parity status between 2.x and 0.1x.

**Steps**:

1. Create `kitty-specs/034-feature-status-state-model-remediation/parity-matrix.md`:

2. Structure the parity matrix as a table:

   ```markdown
   # Parity Matrix: 2.x vs 0.1x

   **Generated**: 2026-02-08
   **Feature**: 034-feature-status-state-model-remediation

   ## Module Parity

   | Module | 2.x | 0.1x | Status | Notes |
   |--------|-----|------|--------|-------|
   | `status/models.py` | Full | Full | Identical | All data types present |
   | `status/transitions.py` | Full | Full | Identical | Same transition matrix |
   | `status/reducer.py` | Full | Full | Identical | Byte-identical output |
   | `status/store.py` | Full | Full | Identical | Same JSONL I/O |
   | `status/phase.py` | Full | Capped | Adapted | Phase capped at 2 on 0.1x |
   | `status/legacy_bridge.py` | Full | Full | Identical | Same view generation |
   | `status/reconcile.py` | Full | Dry-run only | Adapted | --apply disabled on 0.1x |
   | `status/doctor.py` | Full | Full | Identical | Same health checks |
   | `status/migrate.py` | Full | Full | Identical | Same migration logic |
   | `cli/commands/agent/status.py` | Full | Full | Identical | All subcommands available |
   | `tasks_support.py` | 7 lanes | 7 lanes | Identical | Same lane expansion |
   | `frontmatter.py` | 7 lanes | 7 lanes | Identical | Same validation |
   | `merge/status_resolver.py` | Rollback-aware | Rollback-aware | Identical | Same resolution |
   | `cli/commands/agent/tasks.py` | Delegates | Delegates | Identical | Same delegation |
   | `sync/events.py` | SaaS emit | N/A | Missing | SaaS not on 0.1x (expected) |
   | `agent_utils/status.py` | Phase 2 reads | Phase 2 reads | Identical | Same read logic |
   ```

3. Add summary section:
   - Total modules: N
   - Identical: N (percentage)
   - Adapted: N (with justifications)
   - Missing: N (with justifications)

4. Add explanation for each "Adapted" and "Missing" entry:
   - **phase.py adapted**: Phase capped at 2 to prevent Phase 3 behaviors on a branch heading to bug-fix mode
   - **reconcile.py adapted**: `--apply` disabled because reconciliation event persistence on 0.1x would create operational complexity without SaaS downstream
   - **sync/events.py missing**: The `sync/` package is 2.x SaaS infrastructure; 0.1x is offline-only. This is expected and documented.

**Files**: `kitty-specs/034-feature-status-state-model-remediation/parity-matrix.md` (new)

**Validation**:

- Every module in the `status/` package and every modified existing module is listed
- Status values are: "Identical", "Adapted", or "Missing"
- Every non-Identical status has a clear justification
- The parity matrix is accurate (cross-referenced with actual file comparisons)

**Edge Cases**:

- New modules added after initial backport: update the matrix
- Modules that required minor import changes but are functionally identical: mark as "Identical" with note about import adaptation
- Test modules: optionally include test parity in a separate table

---

## Test Strategy

**This WP is primarily a backport operation, not a feature implementation.** Testing consists of:

1. **Parity tests**: `tests/cross_branch/test_parity.py` on both branches
2. **Full status suite on 0.1x**: All unit and integration tests from WP01-WP15
3. **Existing test regression**: `python -m pytest tests/ -x -q` on the backport branch (no regressions)
4. **Phase cap verification**: Specific tests for Phase 2 cap and reconcile apply gate
5. **SaaS no-op verification**: Test that emit succeeds without sync module

**Coverage target**: Same as 2.x (90%+ for status/ package)

**Test runner**: Same commands on both branches

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Cherry-pick conflicts due to branch divergence | Significant manual work | Budget extra time; document all manual adaptations in commit messages |
| 0.1x missing `ulid` dependency | Import errors | Add to `pyproject.toml` on backport branch; verify version compatibility |
| Test failures unique to 0.1x | Unclear parity status | Investigate each failure; fix or document as known delta |
| Branch merge back to main creates conflicts | Integration pain | Keep backport branch focused; squash to minimize commit surface |
| Parity matrix becomes stale | Misleading documentation | Generate matrix as final step after all adaptations |
| 0.1x codebase has changes that conflict with status/ | Module placement issues | Review 0.1x structure before starting; adapt placement as needed |

---

## Review Guidance

- **Check backport completeness**: All `status/` modules present on 0.1x
- **Check import adaptations**: No references to 2.x-only modules that would cause ImportError
- **Check SaaS handling**: `try/except ImportError` pattern, not a fallback mechanism
- **Check phase cap**: `resolve_phase()` never returns >2 on 0.1x
- **Check reconcile gate**: `--apply` fails with clear error on 0.1x
- **Check parity test results**: Byte-identical reducer output from shared fixtures
- **Check parity matrix accuracy**: Cross-reference with actual file diffs
- **Check existing test regression**: No pre-existing tests broken by backport
- **Check dependency changes**: `pyproject.toml` updated if needed, no unnecessary additions
- **No fallback mechanisms**: Both branches fail identically on invalid input

---

## Activity Log

- 2026-02-08T14:07:18Z -- system -- lane=planned -- Prompt created.
- 2026-02-08T15:44:16Z – unknown – shell_pid=80759 – lane=done – Parity matrix, backport notes, 42 parity tests
