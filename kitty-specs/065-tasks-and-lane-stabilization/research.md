# Research: Tasks And Lane Stabilization

## Root Cause Analysis

### #406 — Dependency Stripping

**Decision**: Consolidate to a single canonical dependency parser that supports both inline and bullet-list formats. Use `FrontmatterManager` API (not `set_scalar()`) for list-typed fields.

**Rationale**: Two independent parsers exist with different regex patterns:
- `mission.py:1802-1819` recognizes `Depends on WP##` and `**Dependencies**: WP##`
- `tasks.py:1673` recognizes `depends on:`, `dependency:`, `requires:` with mandatory colon

Neither recognizes the bullet-list format the `/spec-kitty.tasks` template instructs LLMs to generate:
```markdown
### Dependencies
- WP01 (reason)
- WP02 (reason)
```

Additionally, `tasks.py:1716` uses `set_scalar(frontmatter, "dependencies", deps)` which is a type mismatch: `set_scalar` expects `str`, receives `list[str]`. The proper API is `FrontmatterManager.update_field()` or direct dict assignment + `write_frontmatter()`.

**Alternatives considered**:
- Fix only the regex: Leaves the `set_scalar` type bug and the two-parser inconsistency
- Make `set_scalar` handle lists: Fragile string manipulation for YAML lists; `FrontmatterManager` already handles this correctly via ruamel.yaml
- Remove `tasks.py` finalize path entirely: Too disruptive; both entry points must work per C-004

### #417 — validate-only Mutation

**Decision**: Gate all file-write operations on `validate_only` before they execute, not after.

**Rationale**: In both implementations, the frontmatter write loop runs unconditionally:
- `mission.py:1419-1457`: `write_frontmatter()` executes before the `validate_only` check at line 1509
- `tasks.py:1700-1721`: `wp_file.write_text()` executes unconditionally; `validate_only` only gates `bootstrap_canonical_state()` at line 1732

The fix is structurally simple: wrap existing write calls in `if not validate_only:` guards. Accumulate the would-be mutations in a report structure for the validate-only output.

**Alternatives considered**:
- Snapshot files before, restore after: Complex, error-prone, and doesn't match the contract name
- Rename flag to `--no-commit`: Dishonest — operators expect read-only behavior from `--validate-only`

### #422 — Impossible WPs and Incomplete Lane Graphs

**Decision**: Add post-computation assertion that all executable WPs are lane-assigned. Add ownership validation warnings for zero-match globs. Make the `src/**` fallback emit a diagnostic warning.

**Rationale**: The structural gaps are:
1. `compute_lanes()` at `compute.py:170-171` only processes WPs in `dependency_graph.keys()`. WPs missing from the graph are silently dropped.
2. `infer_owned_files()` at `inference.py:135-136` falls back to `["src/**"]` without warning.
3. No validation checks that extracted path globs match real files.

The specific mission-064 artifacts cited in the issue have been fixed, but the structural gaps remain and can produce the same class of failure on any future mission.

**Alternatives considered**:
- Full filesystem validation of every glob: Expensive at scale and would require repo access during lane computation. Warning-only is sufficient for stabilization.
- Remove the `src/**` fallback entirely: Would break features with WPs that don't mention paths. Warning + fallback is safer.

### #423 — Silent Parallelism Collapse

**Decision**: Add a collapse report to `compute_lanes()` output. Refine Rule 3 (surface heuristics) so disjoint-ownership WPs are not collapsed by broad keyword matches alone.

**Rationale**: The union-find in `compute.py:186-216` has three rules that all collapse independently:
- Rule 1 (dependency): Correct by design — dependent WPs must share a lane
- Rule 2 (write-scope overlap): Correct when globs genuinely overlap
- Rule 3 (surface heuristics): Overly aggressive — `_SURFACE_KEYWORDS` at `compute.py:38-47` uses substring matching that triggers on common words ("api", "test", "layout")

Rule 3 should be gated: only union WPs by surface when their ownership globs are not provably disjoint. If WP A owns `src/a/**` and WP B owns `src/b/**` with no overlap, a shared surface keyword should not force them into the same lane.

The collapse report is a new `CollapseReport` data structure returned alongside `LanesManifest`, listing each merge event with the triggering rule and evidence.

**Alternatives considered**:
- Remove Rule 3 entirely: Too aggressive; surface heuristics catch real conflicts that glob analysis misses (e.g., two WPs modifying different files in the same logical module)
- Make Rule 3 opt-in: Adds configuration complexity; gating on disjoint ownership is simpler and automatic

### #438 — mark-status Format Mismatch

**Decision**: Add pipe-table row parsing to `mark-status`. Standardize future generation to checkbox format.

**Rationale**: `mark-status` at `tasks.py:1344` uses regex `rf'-\s*\[[ x]\]\s*{re.escape(task_id)}\b'` which only matches checkbox lines. Pipe-table format (`| T001 | desc | WP01 | [P] |`) used in existing artifacts like `kitty-specs/063-universal-charter-rename/tasks.md` is not recognized.

The pipe-table parser needs to:
1. Detect pipe-delimited rows containing the task ID
2. Find the status column (by position or marker pattern like `[P]`, `[D]`, `[x]`)
3. Replace the status marker in-place without disturbing other columns

Future generation standardizes to checkbox because it's simpler to parse, universally recognized as task-tracking syntax, and already supported by the mutation path.

**Alternatives considered**:
- Standardize generation only (no pipe-table support): Breaks existing active missions with pipe-table artifacts
- Auto-migrate pipe-table to checkbox on first mutation: Violates FR-010b (no auto-rewriting)

### #434 — Agent Command Guidance

**Decision**: Fix all generated command examples to include `--mission <slug>`. Fix error messages to use `--mission` consistently.

**Rationale**: Three sources of confusion:
1. `context/middleware.py:100` and `context/store.py:65` use `--feature` in error messages, but the CLI parameter is `--mission`
2. `shims/generator.py:53-76` generates bare `$ARGUMENTS` with no hint about required flags
3. The tasks command template at `tasks.md:52-58` shows `context resolve` without `--mission`

All three must be fixed. The shim template should include a comment line indicating that `--mission <slug>` is required for mission-scoped commands.

**Alternatives considered**:
- Re-add auto-detection: Explicitly rejected by ADR `2026-03-09-1-prompts-do-not-discover-context-commands-do`
- Only fix error messages: Doesn't prevent the first-try failure; agents need the guidance before they fail
