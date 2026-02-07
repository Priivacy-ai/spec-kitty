# Research: GitHub Observability Event Metadata

**Feature**: 033-github-observability-event-metadata
**Date**: 2026-02-07

## R1: Git Remote URL Parsing for `owner/repo` Extraction

**Decision**: Parse both SSH and HTTPS remote URL formats to extract `owner/repo`.

**Rationale**: The existing `derive_project_slug()` in `project_identity.py` already parses remote URLs but only extracts the repo name (last segment). The new `repo_slug` needs `owner/repo` (two segments). The parsing logic is similar but extracts one more path segment.

**URL Formats Analyzed**:

| Format | Example | Extracted `owner/repo` |
|--------|---------|----------------------|
| SSH standard | `git@github.com:acme/spec-kitty.git` | `acme/spec-kitty` |
| HTTPS | `https://github.com/acme/spec-kitty.git` | `acme/spec-kitty` |
| HTTPS (no .git) | `https://github.com/acme/spec-kitty` | `acme/spec-kitty` |
| SSH (no .git) | `git@github.com:acme/spec-kitty` | `acme/spec-kitty` |
| GitLab subgroup | `git@gitlab.com:org/team/repo.git` | `org/team/repo` |
| Bitbucket SSH | `git@bitbucket.org:acme/spec-kitty.git` | `acme/spec-kitty` |
| Self-hosted HTTPS | `https://git.internal.co/acme/repo.git` | `acme/repo` |

**Parsing Algorithm**:
1. Strip trailing `.git` if present
2. If URL contains `@` and `:` (SSH format): extract path after `:`
3. Otherwise (HTTPS): extract path after host (strip leading `/`)
4. Return the path as-is (preserves subgroups like `org/team/repo`)

**Note on subgroups**: GitLab allows nested groups (e.g., `org/team/repo`). The `owner/repo` format validation (exactly one `/`) would reject these. Decision: relax validation to "at least one `/`" rather than "exactly one `/`". This handles GitHub, GitLab, Bitbucket, and self-hosted scenarios.

**Alternatives considered**:
- Use `git remote -v` instead of `get-url origin`: More complex parsing, shows fetch/push separately. Rejected — `get-url` is cleaner.
- Use `urllib.parse` for HTTPS URLs: Would handle HTTPS but not SSH. Rejected — custom parsing handles both uniformly.

## R2: TTL Cache Design for Per-Event Git State

**Decision**: Use `time.monotonic()` with 2-second TTL for branch/SHA caching.

**Rationale**: `time.monotonic()` cannot go backward (immune to NTP adjustments, DST, manual clock changes). `time.time()` can jump backward, causing cache to serve stale data indefinitely.

**Cache invalidation scenarios**:
- Normal development: commits every few minutes → cache misses correctly after 2s
- Burst events (finalize-tasks emits 7+ WPCreated events in <1s): all hit cache → single subprocess call
- Branch switch: takes >2s to switch + start new command → cache naturally expires

**Performance measurement** (from subprocess benchmarks):
- `git rev-parse HEAD`: ~5-15ms typical (local repo)
- `git rev-parse --abbrev-ref HEAD`: ~5-15ms typical
- Combined (two subprocess calls): ~10-30ms per cache miss
- With 2s TTL: effectively 0ms for burst emissions

**Implementation detail**: Use a single `subprocess.run()` call with `git rev-parse --abbrev-ref HEAD` and a second for `git rev-parse HEAD`. These could be combined into one call using `git rev-parse --abbrev-ref HEAD HEAD` which outputs both values (branch name, then full SHA) on separate lines — reducing to a single subprocess.

**Alternatives considered**:
- No cache (subprocess per event): Rejected — finalize-tasks emits 7+ events in rapid succession
- Session-level cache (once per process): Rejected — stale metadata after branch switch
- File-watch cache (inotify on `.git/HEAD`): Over-engineered for 2-field resolution

## R3: Graceful Degradation Behavior

**Decision**: All git metadata failures produce `None` values, never exceptions. Warning logged once per failure type per session.

**Failure modes and behavior**:

| Failure | `git_branch` | `head_commit_sha` | `repo_slug` | Warning |
|---------|-------------|-------------------|-------------|---------|
| No git installed | `None` | `None` | `None` | "git not found; git metadata unavailable" |
| Not in git repo | `None` | `None` | `None` | "Not in a git repository; git metadata unavailable" |
| Detached HEAD | `"HEAD"` | SHA value | Derived normally | None (valid state) |
| No remote configured | Branch value | SHA value | `None` | None (optional field) |
| Subprocess timeout | `None` | `None` | Previous value | "git command timed out" |

**Implementation**: Wrap subprocess calls in try/except. Use `subprocess.run(..., timeout=5)` to prevent hangs. Store warning-seen flags to avoid log spam.

**Alternatives considered**:
- Raise exceptions on failure: Rejected — violates non-blocking emission principle (FR-010)
- Return empty strings instead of None: Rejected — None is semantically correct (field not available) and distinguishes from empty string (which would be invalid)

## R4: Event Envelope Field Placement

**Decision**: Place new fields at the top level of the event dict, alongside `project_uuid` and `project_slug`.

**Current envelope** (from `emitter.py::_emit()` line 468-481):
```python
event = {
    "event_id": ...,
    "event_type": ...,
    "aggregate_id": ...,
    "aggregate_type": ...,
    "payload": {...},
    "node_id": ...,
    "lamport_clock": ...,
    "causation_id": ...,
    "timestamp": ...,
    "team_slug": ...,
    "project_uuid": ...,
    "project_slug": ...,
    # NEW (this feature):
    "git_branch": ...,
    "head_commit_sha": ...,
    "repo_slug": ...,
}
```

**Rationale**: Consistent with `project_uuid`/`project_slug` placement (top-level envelope metadata). Not inside `payload` because these are correlation fields, not event-type-specific data.

**Alternatives considered**:
- Nest under `"git": {"branch": ..., "sha": ..., "repo_slug": ...}`: Rejected — adds nesting complexity for 3 fields; inconsistent with flat `project_uuid`/`project_slug` pattern
- Put in `payload`: Rejected — payload is event-type-specific; these are universal envelope fields
