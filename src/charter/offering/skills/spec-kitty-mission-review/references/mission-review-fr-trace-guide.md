# FR Trace Reasoning Guide

Supporting reference for `spec-kitty-mission-review`. Explains the three major
failure modes that appear when tracing FRs from spec to code, and provides
structured reasoning patterns for FR coverage analysis.

---

## Failure Mode 1: The Synthetic Fixture Trap

A test that creates its own data using a model that does not match the production
model will always pass, regardless of whether the code is correct.

**Example**: An FR requires a changelog block to be non-empty when missions have
approved WPs. The test creates a synthetic WP file with `status: done` in
YAML frontmatter. The production system stores WP state in
`status.events.jsonl` using a JSONL event log. The function under test reads
frontmatter only. The test passes. The function always returns `""` in
production.

**Detection**: For each new function that reads mission artifacts, ask:
1. What data format does it actually read?
2. Does the test fixture match that format?
3. If not, the test is a false positive.

**Real-world example from spec-kitty**: WP07 review cycle 1 caught this when
`proposed_changelog_block()` was reading legacy frontmatter `status: done`
instead of the new event log. The function shipped with 100% test coverage
but produced empty output in production because the spec never stated the
version contract as a formal FR.

---

## Failure Mode 2: The Dead Code Module

A new module with 100% test coverage but zero callers from live entry points
is dead code. The tests verify the module's internal behavior; they do not
verify that the module is invoked by the system.

**Example**: A new mission `status_validator` module is introduced with full
project-test-runner coverage. All tests pass. The module is never imported from any live
command path. When a user runs `spec-kitty implement WP01`, the validator
is never called because no code path invokes it.

**Detection**: For each new module introduced by the mission:
1. Search for all imports of that module from `src/` (not just `tests/`)
2. Verify at least one live entry point (a command, a step procedure, etc.)
3. Zero grep hits = dead code

**Why this happens**: The WP is reviewed independently. A reviewer sees a new
module with 100% test coverage and approves it. No reviewer checks whether
the module is actually called.

---

## Failure Mode 3: The Compliant Stub

A function that satisfies the letter of an FR by returning the correct type but
not the correct content. Common in error recovery paths: `except Exception:
return []` satisfies "returns a list" but silently discards the data.

**Example**: An FR says "when a JSONL event log is corrupted, emit a recovery
status event and return a clean snapshot." The implementation does:

```python
try:
    events = read_events(path)
    return reduce(events)
except JSONDecodeError:
    return []  # "Returns a list" ✓, but silently loses data
```

The function type-checks (returns list), the test passes (mocked fixture never
fails), and the FR is marked "covered." In production, a user with a partially
corrupted event log gets an empty list silently instead of a recovery event.

**Detection**: For each new function with a broad exception handler:
1. Trace what is returned on failure
2. Is the return value indistinguishable from a legitimate empty result?
3. Would a user notice the failure, or would the system proceed silently?

---

## FR Coverage Quality Scale

| Grade | Description | Test adequacy |
|-------|-------------|----------------|
| **ADEQUATE** | Test exercises the live code path against realistic inputs. Test would fail if the implementation code were deleted. Data model in test matches production. | ✓ Fully constrains behavior |
| **PARTIAL** | Test exists but relies on synthetic fixtures, mocks, or old data models that do not match production. Function may pass test but fail in production. | ⚠️ Constrains type, not behavior |
| **FALSE_POSITIVE** | Test passes unconditionally (implementation not actually exercised). Example: test mocks the I/O layer entirely; the actual read/write code is untested. | ✗ Does not constrain behavior |
| **MISSING** | No test found for this FR. | ✗ No constraint |

**How to assess**:

1. **Read the test code** (not just the test name)
2. **Identify what data the test provides** (fixture, mock, synthetic)
3. **Identify what data the implementation consumes** (file format, API response, etc.)
4. **Do they match?** If not → PARTIAL or FALSE_POSITIVE

---

## Non-Goal Invasion Detection Checklist

For each Non-Goal in the spec:

1. **What is the protected territory?** (file system paths, code modules, data structures, external APIs)
2. **What patterns would indicate a violation?** (new imports, new file operations, new subprocess calls)
3. **Does the diff show any of those patterns?**

**Example**:

- Non-Goal: "No backfill of historical missions"
- Protected territory: the `kitty-specs/` directory of older missions
- Violation patterns: code that iterates existing `kitty-specs/*/`, code that reads `*.md` files from all missions, code that recomputes lanes for past features
- Grep test: `git diff baseline..HEAD -- src/ | grep -n "kitty-specs\|for.*mission\|walk\|glob.*mission"`

---

## Locked Decision Verification Pattern

For each Decision (D-N):

1. **What is the positive requirement?** (what MUST now happen)
2. **What is the negative requirement?** (what MUST NOT happen)
3. **Are BOTH sides verified by tests?**
4. **Are there exception handlers that re-enable the forbidden behavior?**

**Example**:

- Decision: "Init MUST NOT initialize git, under any flag combination"
- Positive requirement: `init` completes successfully without `.git/`
- Negative requirement: No `git init` call paths exist anywhere in the code
- Test for positive: ✓ (test verifies no `.git/` after `init`)
- Test for negative: ✗ (no test that explicitly verifies no `subprocess.run(["git", "init"])` call path exists)
- Finding: Negative side untested; a future contributor could add a `git init` call in an error handler and no test would catch it

**Why negatives matter**: Locked decisions often forbid something the *old* code did. Reviewers focus on "the new behavior works" and forget "the old forbidden behavior is gone."

---

## Invisible Hole Detection Heuristics

"Invisible holes" are assumptions the spec relies on but never states as FRs.

**Pattern 1: Version contracts**
- Spec says "the system reads from source A and writes to source B"
- Implicit assumption: source A and source B use the same version
- Invisible hole: what if they diverge?
- Example: `proposed_changelog_block()` reads `status.events.jsonl` (v3 model) but test uses frontmatter (v1 model)

**Pattern 2: Atomic transitions**
- Spec says "when X happens, do Y and Z"
- Implicit assumption: Y and Z happen together or not at all
- Invisible hole: what if Y succeeds and Z fails?
- Example: "emit a status event AND update the snapshot"—if snapshot update fails, event log is authoritative but snapshot stale. Is that handled?

**Pattern 3: Dependency ordering**
- Spec says "feature A requires feature B"
- Implicit assumption: B is already available/correct when A runs
- Invisible hole: what if B was partially implemented in a prior WP?
- Example: if WP02 adds a new status event type but WP03 adds the reducer, does WP02's code fail if WP03 hasn't landed yet?

**Pattern 4: Boundary conditions**
- Spec says "forbidden under any flag combination"
- Implicit assumption: the check catches all combinations
- Invisible hole: is there a code path that bypasses the check?
- Example: a guard that prevents `init --git-init`, but an exception handler that calls `git init` anyway on failure

**How to find them**: Read the spec's Acceptance Criteria and Goals. For each statement, ask "what would have to be true for this to fail?" Then search the code for whether that condition is handled.

---

## Test Inadequacy Patterns

These patterns indicate a test that looks good on paper but does not actually constrain the implementation.

| Pattern | Red flag | Investigation |
|---------|----------|----------------|
| Synthetic fixture data model | Test creates WP with `status: done` in frontmatter | Does real code read frontmatter or event log? |
| Mocked I/O layer | Test mocks `open()` or `Path()` | Does real code ever execute? Does test exercise actual file I/O? |
| Implicit pass condition | Test runs with no assertion | Is there an actual `assert`? Or does the test "pass" by not raising? |
| Exception swallowed | Test `try/except Exception: pass` | Does the test verify recovery behavior, or just that no exception escapes? |
| Dead import path | Test imports module directly | Does any live code path import this module? |
| Fixture independence | Test uses global fixtures | Does each test set up its own state, or rely on shared/previous tests? |

---

## FR-to-Code Traceability Template

Use this template to document each FR's journey from spec to shipped code:

```
## FR-NNN: <description>

**Spec reference**: Section <section>, paragraph <N>
**Acceptance criteria**: <copy from spec>
**Owned by WP**: <WP slug>
**Test(s)**: 
- `<test_file>::<test_name>` — <brief description of what it tests>

**Code path**:
- Main implementation: `src/<module>/<file>.py:<line_range>`
- Relevant functions: `<func1>`, `<func2>`

**Test adequacy**: [ADEQUATE | PARTIAL | MISSING | FALSE_POSITIVE]

**Reasoning**:
<Why this assessment. If PARTIAL or FALSE_POSITIVE, explain the fixture mismatch or missing constraint.>

**Finding** (if any):
[None | DRIFT-N | RISK-N]
```

---

## References

- Main skill: `spec-kitty-mission-review/SKILL.md`
- Related: `spec-kitty-runtime-review/SKILL.md` (per-WP review during implementation)
- Mission artifact locations: `kitty-specs/<slug>/spec.md`, `plan.md`, `tasks.md`, `contracts/`
