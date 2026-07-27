# Contract: Characterization envelope (FR-008 / FR-006 / NFR-001)

**Purpose**: pin the trio's observable behaviour BEFORE refactor; every decomposition WP depends on this suite being green on pre-refactor code.

**Three assertion layers**:
1. **Pure-core in→out** — deterministic fixtures for each helper about to move; exact-value assertions.
2. **CLI JSON envelope** — drive `agent action implement/review`, `spec-kitty implement`, `spec-kitty accept` in `--json` mode via CliRunner; assert the envelope (`_json_safe_output`) after **normalizing** non-deterministic fields: git SHAs, `at`/timestamp ISO fields, absolute paths, worktree ids. Guarded alongside `tests/integration/test_json_envelope_strict.py`.
3. **State-transition** — assert lane/state transitions via the deterministic status-event reducer given event inputs (NOT wall-clock fields), covering rejection/rewind/resume.

**Normalization rule**: a field that varies by environment (SHA, timestamp, path, pid) is normalized to a stable token before comparison — never asserted raw.

**Gate**: an `implement WP##` for any decomposition WP is blocked until the characterization suite is committed green against the pre-refactor tree (tasks encode this as a hard dependency on the IC-CHAR WP).
