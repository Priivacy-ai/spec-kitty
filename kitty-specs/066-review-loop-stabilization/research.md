# Research: 066 Review Loop Stabilization

**Mission**: 066-review-loop-stabilization
**Date**: 2026-04-06

## Decision Log

### D1: Review-cycle artifact storage location

**Decision**: Committed artifacts at `kitty-specs/<mission>/tasks/<WP-slug>/review-cycle-{N}.md`
**Rationale**: The mission thesis is to stop losing state to ephemeral locations. The current `.git/spec-kitty/feedback/` path is git-internal, not committed, not versioned, not visible across clones. Moving to committed artifacts is the core value proposition.
**Alternatives considered**:
- `.git/spec-kitty/feedback/` (current) — rejected: ephemeral, invisible
- Worktree-local (`.spec-kitty/baseline/`) — rejected for same reason
- External storage (SQLite, SaaS API) — rejected: adds dependency, mission scope is filesystem artifacts

### D2: Backward compatibility for legacy feedback:// pointers

**Decision**: Read-side compatibility — `_resolve_review_feedback_pointer()` resolves both legacy `feedback://` (`.git/` path) and new `kitty-specs/` paths. No migration needed.
**Rationale**: The event log is append-only. Pre-066 StatusEvent records with `review_ref: "feedback://mission/WP/filename"` are historical and informational. A few lines of resolver code prevents a class of runtime errors. New writes go to `kitty-specs/`; old reads still work.
**Alternatives considered**:
- Full migration (rewrite event log entries) — rejected: event log is append-only by design, rewriting violates immutability
- Declare legacy pointers historical (non-resolving) — rejected: still causes runtime errors when code tries to read old feedback

### D3: WP dependency ordering

**Decision**: WP01 (artifact model) strictly precedes WP02 (rejection recovery). WP03 absorbed into WP02.
**Rationale (from operator)**:
1. The structured frontmatter in review-cycle-{N}.md is load-bearing for fix-prompt quality. WP02's fix-prompt generator needs affected_files with paths/line ranges, cycle_number, reviewer_agent, verdict — all from WP01's schema.
2. Building WP02 against a provisional location means WP03 becomes a rewrite, not a thin integration layer.
3. Issues #432 and #433 explicitly prescribe this order: "#432 first (persistence), #430 second (generation)."
4. WP03 was vacuous as a standalone WP — if WP02 consumes WP01's read API, the "wiring" is the implementation itself, not a separate unit.

### D4: Dirty-state classification approach

**Decision**: Classification layer that partitions `git status --porcelain` output by path pattern and WP ownership. Not a flag that disables checks.
**Rationale (from operator)**: Tranche 1 (#449) did not address this. The current code in `_validate_ready_for_review()` treats any dirty file as blocking, with `--force` as the only escape (which skips all validation). The fix is a filter, not a flag.
**Classification rules**:
- **Blocking**: uncommitted changes to files owned by the current WP (source files in the worktree, the WP's own task file)
- **Benign**: status artifacts (status.events.jsonl, status.json), other WPs' task files modified by concurrent agents, generated metadata

### D5: Baseline test cache — format and location

**Decision**: Committed artifact at `kitty-specs/<mission>/tasks/<WP-slug>/baseline-tests.json`. Structured results only — test name, status, one-line error for failures. No raw stdout/stderr, no passing test details.
**Rationale (from operator)**: Consistent with the "everything is a committed artifact" principle. Size constraint prevents bloat: a few KB of structured failure data, not megabytes of pytest output. The reviewer needs to know *which* tests fail and *why*, not the full console dump.
**Schema**:
```yaml
wp_id: WP01
captured_at: "2026-04-06T10:00:00Z"
base_branch: main
base_commit: abc123
test_runner: pytest
total: 487
passed: 484
failed: 3
failures:
  - test: test_legacy_import_path
    error: "ImportError: no module named 'old_name'"
    file: tests/test_compat.py:45
  - test: test_timeout_handling
    error: "TimeoutError: exceeded 5s"
    file: tests/test_network.py:112
```

### D6: Concurrent review strategy

**Decision**: Serialization-first with opt-in env-var isolation. 80% effort on serialization, 20% on env-var isolation.
**Rationale (from operator)**:
1. **Primary path (serialization)**: When a second review agent attempts to claim a WP in a worktree that already has an active review, block it with a clear message. This is reliable, universal, works for every framework.
2. **Optional path (env-var isolation)**: If `.kittify/config.yaml` declares a `test_db_isolation` strategy, the orchestrator sets env vars per review agent. This is config-driven, not auto-detected.
3. **Why not auto-detection**: Detecting whether a project uses Django (respects DATABASE_URL), Rails, Go, Rust, or a custom harness is brittle, framework-specific, and scope creep. Projects that want concurrent review configure it explicitly.
**Alternatives considered**:
- Auto-detect framework and set env vars — rejected: detection logic is brittle, produces false positives
- Ephemeral review worktrees — rejected: heavy, doesn't solve DB collisions at fixed addresses
- Pure serialization with no env-var option — rejected: leaves no path to concurrent review for projects that need it

### D7: Cycle number derivation

**Decision**: Count of existing `review-cycle-*.md` files in the WP's sub-artifact directory, plus one.
**Rationale**: Simple, deterministic, filesystem-based. No event log query needed. Consistent with append-only artifact model.

### D8: Baseline capture timing

**Decision**: Capture at **implement time** (inside `agent action implement`, when the worktree exists and dependencies are installed), not at claim time. Cache as committed artifact. Lookup at review time reads the cached artifact.
**Rationale (from operator review)**: The claim transition (`planned` → `claimed`) runs in the planning context, which may lack test dependencies and the implementation worktree may not even exist yet. The implement action (`agent action implement`) is when the workspace is ready. Capturing at implement time means the cost is paid once (before the agent starts coding), and the cached result is available instantly at review time.
**Corrects**: Earlier version incorrectly said "claim time" — operator flagged this as a lifecycle error.

### D9: Test runner output parsing

**Decision**: Use JUnit XML format (`pytest --junitxml=<tmpfile>`), parsed via `xml.etree.ElementTree` (stdlib). For non-pytest projects, require explicit configuration in `.kittify/config.yaml` — no auto-detection of test runners.
**Rationale (from operator review)**: Raw pytest stdout is not reliably parseable. JUnit XML is a structured, standardized format that works with pytest, unittest, and most CI systems. The stdlib XML parser is zero-dependency. Auto-detecting whether a project uses pytest, unittest, jest, cargo test, etc. is brittle and scope creep — projects that don't use pytest configure `review.test_command` explicitly.
**Alternatives considered**:
- `pytest-json-report` plugin — rejected: requires installing an extra plugin; JUnit XML is built into pytest
- Raw stdout parsing — rejected: unreliable, format varies across pytest versions and plugins
- Auto-detect test runner — rejected: brittle framework detection, false positives

### D10: Pointer scheme consolidation

**Decision**: Two pointer schemes only: `feedback://` (legacy) and `review-cycle://` (new). No `arbiter-override://` scheme.
**Rationale (from operator review)**: The arbiter decision is metadata on an existing review-cycle artifact, not a separate addressable resource. The `review_ref` for an arbiter override points to the same `review-cycle://` artifact that the rejection created. The `ArbiterDecision` is stored as a frontmatter extension on that artifact. Three URI schemes is unnecessary proliferation.
