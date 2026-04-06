---
work_package_id: WP05
title: Concurrent Review Isolation
dependencies: []
requirement_refs:
- C-004
- FR-013
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-066-review-loop-stabilization
base_commit: 4dbb05e1ae46b17dad6ae64402cfb2861107f268
created_at: '2026-04-06T16:42:34.948851+00:00'
subtasks:
- T024
- T025
- T026
- T027
- T028
- T029
shell_pid: "49299"
agent: "claude:opus-4-6:reviewer:reviewer"
history:
- timestamp: '2026-04-06T16:32:04Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/review/lock.py
execution_mode: code_change
owned_files:
- src/specify_cli/review/lock.py
- tests/review/test_lock.py
---

# WP05: Concurrent Review Isolation

## Objective

Prevent concurrent review agents from colliding on shared test infrastructure. Primary approach (80% effort): explicit serialization via a review lock. Secondary approach (20% effort): opt-in env-var isolation via config for projects that want concurrent reviews.

**Issues**: [#440](https://github.com/Priivacy-ai/spec-kitty/issues/440)
**Dependencies**: None

## Context

### Current Problem

Multiple review agents pointed at the same lane worktree attempted to run Django/PostgreSQL tests concurrently, causing test database collisions (DB lock errors, table-already-exists) and review churn unrelated to the code. Observed during Feature 064 with GPT-5.4 review agents.

### Design Decisions

- **Serialization-first**: 80% effort. Universal, reliable, works for every framework. When a second review agent tries to start in a worktree with an active review, block with an actionable message.
- **Opt-in env-var isolation**: 20% effort. Config-driven, not auto-detected. Projects that declare `review.concurrent_isolation` in `.kittify/config.yaml` get env-var scoping per review agent. No framework detection.
- **Lock location**: `.spec-kitty/review-lock.json` in the worktree (git-ignored, ephemeral runtime state).

## Branch Strategy

- Planning base branch: `main`
- Merge target: `main`
- Execution worktree: allocated per lane (independent lane)

## Subtask Details

### T024: Create lock.py with ReviewLock dataclass

**Purpose**: Define the review lock model and core operations.

**Steps**:
1. Create `src/specify_cli/review/lock.py`
2. Define the dataclass:
   ```python
   @dataclass
   class ReviewLock:
       worktree_path: str
       wp_id: str
       agent: str
       started_at: str  # ISO 8601 UTC
       pid: int

       def to_dict(self) -> dict[str, Any]:
           return {
               "worktree_path": self.worktree_path,
               "wp_id": self.wp_id,
               "agent": self.agent,
               "started_at": self.started_at,
               "pid": self.pid,
           }

       @classmethod
       def from_dict(cls, data: dict[str, Any]) -> ReviewLock:
           return cls(**data)
   ```

3. Note: This is NOT a frozen dataclass — the lock is mutable runtime state, not an immutable event.

4. Define constants:
   ```python
   LOCK_DIR = ".spec-kitty"
   LOCK_FILE = "review-lock.json"
   ```

### T025: Implement stale lock detection

**Purpose**: Cross-platform PID check to detect stale locks from dead processes.

**Steps**:
1. Add `is_stale()` method:
   ```python
   def is_stale(self) -> bool:
       """Check if the lock's process is still alive."""
       try:
           os.kill(self.pid, 0)  # Signal 0 = existence check, no actual signal
           return False  # Process is alive
       except ProcessLookupError:
           return True  # Process does not exist
       except PermissionError:
           return False  # Process exists but we can't signal it
       except OSError:
           # Fallback: check lock file age (>1 hour = stale)
           return True
   ```

2. Import `os` at module level
3. The `PermissionError` case (process exists but different user) should treat the lock as NOT stale — conservative approach

### T026: Hook lock acquire/release into agent action review

**Purpose**: Acquire lock when review starts, release when review completes.

**Steps**:
1. Add class methods for lock lifecycle:
   ```python
   @classmethod
   def acquire(cls, worktree: Path, wp_id: str, agent: str) -> ReviewLock:
       """Acquire a review lock. Raises if lock exists and PID is alive."""
       lock_path = worktree / LOCK_DIR / LOCK_FILE
       if lock_path.exists():
           existing = cls.load(worktree)
           if existing and not existing.is_stale():
               raise ReviewLockError(
                   f"Worktree {worktree} has an active review by agent "
                   f"'{existing.agent}' on {existing.wp_id} "
                   f"(PID {existing.pid}, started {existing.started_at}). "
                   f"Wait for that review to complete or use a different lane."
               )
           # Stale lock — log warning and overwrite
           logger.warning("Removing stale review lock (PID %d is dead)", existing.pid if existing else -1)

       lock = cls(
           worktree_path=str(worktree),
           wp_id=wp_id,
           agent=agent,
           started_at=datetime.now(timezone.utc).isoformat(),
           pid=os.getpid(),
       )
       lock.save(worktree)
       return lock

   @staticmethod
   def release(worktree: Path) -> None:
       """Release the review lock."""
       lock_path = worktree / LOCK_DIR / LOCK_FILE
       if lock_path.exists():
           lock_path.unlink()

   def save(self, worktree: Path) -> None:
       """Write lock to disk."""
       lock_dir = worktree / LOCK_DIR
       lock_dir.mkdir(parents=True, exist_ok=True)
       lock_path = lock_dir / LOCK_FILE
       lock_path.write_text(json.dumps(self.to_dict(), indent=2))

   @classmethod
   def load(cls, worktree: Path) -> ReviewLock | None:
       """Load lock from disk. Returns None if not found or malformed."""
       lock_path = worktree / LOCK_DIR / LOCK_FILE
       if not lock_path.exists():
           return None
       try:
           data = json.loads(lock_path.read_text())
           return cls.from_dict(data)
       except (json.JSONDecodeError, KeyError, TypeError):
           return None
   ```

2. Define custom exception:
   ```python
   class ReviewLockError(Exception):
       pass
   ```

3. In `workflow.py` review() function (around line 992), after resolving workspace:
   ```python
   from specify_cli.review.lock import ReviewLock, ReviewLockError

   try:
       lock = ReviewLock.acquire(workspace_path, normalized_wp_id, agent_name)
   except ReviewLockError as e:
       console.print(f"[red]{e}[/red]")
       raise typer.Exit(1)

   try:
       # ... existing review logic ...
       pass
   finally:
       ReviewLock.release(workspace_path)
   ```

4. Also release the lock in move-task when completing a review (for_review → approved or for_review → planned)

### T027: Add .spec-kitty/ to .gitignore

**Purpose**: Ensure lock files are never committed.

**Steps**:
1. Check if `.spec-kitty/` is already in `.gitignore` at project root
2. If not, append to `.gitignore`:
   ```
   # Review lock files (runtime state, not committed)
   .spec-kitty/
   ```
3. This should also be added to any worktree `.gitignore` if worktrees have separate gitignore files (they typically inherit from the main repo)

### T028: Implement opt-in env-var isolation

**Purpose**: Config-driven env-var scoping for projects that want concurrent reviews.

**Steps**:
1. In `lock.py`, add config reading:
   ```python
   def _get_isolation_config(repo_root: Path) -> dict[str, str] | None:
       """Read concurrent_isolation config from .kittify/config.yaml.

       Returns dict with 'strategy', 'env_var', 'template' keys, or None.
       """
       config_path = repo_root / ".kittify" / "config.yaml"
       if not config_path.exists():
           return None
       yaml = YAML()
       config = yaml.load(config_path)
       review = config.get("review", {})
       isolation = review.get("concurrent_isolation", {})
       if isolation.get("strategy") == "env_var":
           return {
               "strategy": "env_var",
               "env_var": isolation["env_var"],
               "template": isolation["template"],
           }
       return None
   ```

2. When `strategy == "env_var"`, instead of blocking, set the env var:
   ```python
   def _apply_env_var_isolation(config: dict, agent: str, wp_id: str) -> None:
       """Set env var for isolated test execution."""
       value = config["template"].format(agent=agent, wp_id=wp_id)
       os.environ[config["env_var"]] = value
       logger.info("Set %s=%s for review isolation", config["env_var"], value)
   ```

3. In the acquire flow: check config first. If env-var isolation is configured, apply it and skip lock serialization. If not configured (default), use lock serialization.

### T029: Write tests

**Test file**: `tests/review/test_lock.py`

**Required test cases**:
1. `test_acquire_creates_lock_file` — lock file exists after acquire
2. `test_release_removes_lock_file` — lock file gone after release
3. `test_acquire_blocks_on_active_lock` — raises ReviewLockError when PID alive
4. `test_acquire_overwrites_stale_lock` — dead PID → lock overwritten
5. `test_is_stale_with_dead_pid` — returns True (mock os.kill to raise ProcessLookupError)
6. `test_is_stale_with_alive_pid` — returns False
7. `test_load_missing_file` — returns None
8. `test_load_malformed_json` — returns None
9. `test_isolation_config_env_var` — config parsed correctly
10. `test_isolation_config_missing` — returns None
11. `test_apply_env_var_isolation` — env var is set with correct value
12. `test_default_serialization_no_config` — no config → lock serialization used

**Coverage target**: 90%+ for `src/specify_cli/review/lock.py`

## Definition of Done

- [ ] ReviewLock serialization works (acquire/release/stale detection)
- [ ] Concurrent review blocked with actionable message when lock is active
- [ ] Stale locks detected and overwritten with warning
- [ ] .spec-kitty/ is in .gitignore
- [ ] Opt-in env-var isolation works from config
- [ ] Default behavior (no config) is serialization
- [ ] 90%+ test coverage on lock.py
- [ ] All existing tests pass

## Reviewer Guidance

- Test stale lock detection on the target platform (PID check varies across OS)
- Verify lock file is always cleaned up, even on exceptions (try/finally)
- Check that the error message is actionable (includes agent name, WP ID, PID, start time)
- Verify env-var isolation only activates with explicit config (never auto-detected)

## Activity Log

- 2026-04-06T16:42:35Z – claude:sonnet-4-6:implementer:implementer – shell_pid=48083 – Started implementation via action command
- 2026-04-06T16:47:29Z – claude:sonnet-4-6:implementer:implementer – shell_pid=48083 – Ready for review: ReviewLock with acquire/release/stale-detection implemented, opt-in env-var isolation config, 19 tests passing at 95% coverage
- 2026-04-06T16:47:45Z – claude:opus-4-6:reviewer:reviewer – shell_pid=49299 – Started review via action command
