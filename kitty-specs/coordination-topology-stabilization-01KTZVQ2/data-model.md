# Data Model: Coordination Topology Stabilization

## Affected State Machines and Invariants

### 1. is_committed() — Read Primitive Contract

**Current state** (broken): `is_committed(file, repo_root)` checks `git cat-file -e HEAD:<relative>` against the primary checkout HEAD only.

**Target state**: `is_committed(file, repo_root, placement=None)` — when `placement` is provided and a coordination branch exists, checks `git cat-file -e <coord_ref>:<relative>` first; falls back to primary HEAD for flat topology (placement=None or no coordination branch).

**Invariant**: A file committed to the mission's coordination branch MUST be treated as committed by all gate checks. A file committed only to `origin/main` but not to the coordination branch MUST also be treated as committed (backward-compatible).

**Key interface change**:
```
# Before
is_committed(file: Path, repo_root: Path) -> bool

# After
is_committed(file: Path, repo_root: Path, placement: PlacementResult | None = None) -> bool
```

**Callers to migrate**:
- `_substantive.py:214` (setup-plan entry gate)
- `_planning_commit_worktree` silent fallbacks at `mission.py:603-621`
- Any other caller that checks spec/plan/tasks file commitment status

---

### 2. accept gate — git_dirty Baseline Model

**Current state** (broken): `collect_feature_summary` takes a whole-tree `git status --porcelain` snapshot at `acceptance/__init__.py:934`, which includes untracked files and tool-written artifacts that appear during the same run.

**Target state**: The dirty-tree gate uses a baseline snapshot taken before any accept-owned write, and excludes a fixed set of accept-owned derived paths:
- `acceptance-matrix.json`
- `status.json` (daemon-materialized)
- `kitty-specs/<slug>/` residue committed on success path

**Invariant**: `spec-kitty accept` run twice in the same mission state MUST produce the same pass/fail result. `spec-kitty accept --no-commit` MUST leave `git status --porcelain` output byte-for-byte identical before and after.

**Key field changes**:
- `accept.py:284`: `mutate_matrix=not diagnose` → `mutate_matrix=(not diagnose and commit_required)` (or equivalent gate)
- `AcceptanceSummary.git_dirty`: must exclude accept-owned paths from the dirty calculation
- `_commit_residual_acceptance_artifacts` (accept.py:74-108): called on ALL writing exit paths, not only success

---

### 3. safe_commit path guard

**Current state** (broken): `safe_commit` stages all requested paths with `git add --force` with no policy check against `.worktrees/` prefix.

**Target state**: `safe_commit` MUST reject any requested path where `path_is_under_worktrees(path, repo_root)` is True, raising a structured `SafeCommitPathPolicyError` before staging.

**Invariant**: No path under `.worktrees/` may appear in the repository's git index. This is enforced at the commit choke point, not only at the caller.

---

### 4. MISSION_NOT_FOUND error shape

**New error code**: `MISSION_NOT_FOUND`

```python
# Human-readable output (stderr):
Error: Mission not found: '<handle>'
No mission matching '<handle>' exists in this repository.
Run 'spec-kitty mission list' to see available missions.

# JSON output (stdout, --json mode):
{
  "result": "error",
  "error_code": "MISSION_NOT_FOUND",
  "handle": "<handle>",
  "remediation": "Run 'spec-kitty mission list' to see available missions.",
  "spec_kitty_version": "3.2.0rc43"
}
```

**Exit code**: 1 in all cases (both human and JSON modes).

**Replaces**: The silent "unknown" Decision object returned with exit 0 from `runtime_bridge.query_current_state` when the mission handle cannot be resolved.

---

### 5. ownership_warnings routing

**Current state** (broken): `validate_glob_matches` returns `ownership_warnings` as a list in the JSON response body, which no prompt or CLI surface reads.

**Target state**:
- JSON mode: warnings emitted to stderr in addition to `ownership_warnings` field in body
- Human-readable mode: warnings printed to console with a `WARNING:` prefix
- Literal-path zero-match: hard error (stderr + non-zero exit) with nearest-match suggestion
- Glob-pattern zero-match: warning (existing soft behavior, now routed correctly)
- `create_intent: true` annotation in WP frontmatter: suppresses zero-match error for that path

**Invariant**: No phantom literal path may enter `lanes.json`. Re-validation at lane-compute time enforces this at the downstream boundary.

---

### 6. RetrospectiveSkipped event shape

**New event** (added to status.events.jsonl schema):

```json
{
  "event_id": "<ULID>",
  "at": "<ISO-8601>",
  "actor": "system",
  "feature_slug": "<slug>",
  "wp_id": null,
  "from_lane": null,
  "to_lane": null,
  "event": "retrospective.skipped",
  "reason": "<human-readable reason>",
  "evidence": null
}
```

**Invariant**: After `spec-kitty merge` completes, EXACTLY ONE of the following must be true:
1. `kitty-specs/<slug>/retrospective.yaml` exists with non-empty `findings` or `ran_no_findings=true`
2. `status.events.jsonl` contains a `retrospective.skipped` or `retrospective.capture_failed` event

Both being absent is a hard invariant violation.

---

## Architectural Tests (ratchet)

| Test file | What it asserts | Introduced by |
|-----------|-----------------|---------------|
| `tests/architectural/test_worktrees_index_clean.py` | `git ls-files .worktrees/` returns empty | IC-02 |
| `tests/architectural/test_no_primary_anchored_gates.py` | No new callers of the old `is_committed(file, repo_root)` 2-arg form outside of the coord-aware wrapper | IC-01 |

## Regression Test Matrix

| Test file | Bug it covers | FR |
|-----------|---------------|----|
| `test_is_committed_coord_aware.py` | #1884 | FR-003 |
| `test_accept_gate_convergence.py` | #1883 cross-run non-convergence | FR-001 |
| `test_accept_no_commit_readonly.py` | #1883 --no-commit dirty tree | FR-002 |
| `test_next_fail_closed.py` | #1885 exit-0 unknown stub | FR-004 |
| `test_worktrees_index.py` | #1887 leaked paths | FR-005 |
| `test_finalize_ownership_routing.py` | #1888 warning routing | FR-006 |
| `test_retrospective_triggering.py` | #1164 merge-path trigger | FR-007 |
| `test_retrospective_content.py` | #1164 generator ingestors | FR-008 |
| `test_stale_assertions_message.py` | #1886 FP on message assertions | FR-009 |
| `test_no_manual_ffmerge.py` | #1878 ff-merge treadmill | FR-010 |
