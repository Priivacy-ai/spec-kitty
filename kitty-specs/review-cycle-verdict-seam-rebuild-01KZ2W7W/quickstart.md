# Quickstart: verifying the Review-Cycle Verdict Seam Rebuild

How to check this mission did what it says. Written so a reviewer can re-derive
every claim rather than trust a summary.

## Before anything: the baseline

```bash
PWHEADLESS=1 uv run pytest \
  tests/review/ tests/status/ \
  tests/regression/test_2646_stale_verdict_closes_via_fr001.py \
  tests/integration/test_review_cycle_rejection_only.py \
  tests/integration/test_ac5_hash_guard.py \
  tests/integration/test_wp_file_hash_stability.py \
  tests/post_merge/test_review_artifact_consistency.py \
  tests/specify_cli/cli/commands/agent/ -q
```

Compare the failing node ids against `research/baseline-8466727eb.md`. That set is
a **floor, not a target** — it may not grow, and a node id disappearing because the
test moved, was deleted, or lost parametrization is an NFR-001 violation, not a
pass.

## The invariant, both directions

The mission's core claim is that a recorded verdict and a completed transition are
the same fact. Test it from both ends — the second direction is the one an earlier
spec revision omitted, and omitting it made "swap two lines" a passing implementation.

```bash
# transition fails after the verdict would be written -> no readable approval
# durable write fails after the transition succeeded  -> the WP has not moved
PWHEADLESS=1 uv run pytest tests/specify_cli/cli/commands/agent/ -k "atomicity or execute_failure" -q
```

## The repeat-rejection case

The defect FR-004 closes, and the trap next to it.

**Do not select on prose adjectives.** Verified: `-k "repeat_feedback or provenance"`
selects 17 tests that are **all green today**, so it proves nothing either way. The
FR-004 direction does not exist yet. Select on the requirement reference instead,
and state the expected count:

```bash
# Must include BOTH directions. Assert the count, not just the exit code.
PWHEADLESS=1 uv run pytest tests/review/ -m "requirement_refs and FR_004" -q
```

Both must hold simultaneously. If only the refusal direction passes, FR-004 is
undelivered; if only the recording direction passes, the implementation has deleted
the #990 control — a C-002 violation, while the PR claims `Closes #990`.

## The census

```bash
PWHEADLESS=1 uv run pytest tests/architectural/ -k "verdict_seam_census" -q
```

Then read `contracts/verdict-seam-census.md`. Every row must be `retain` or
`retire`, and every `retire` must name its FR. Introduce a new writer, resolver or
reader anywhere in `src/` and re-run — the check must go red. If it does not, the
reduction is a one-time cleanup rather than a durable property.

## Reader polarity

**Verified non-discriminating**: `-k "damaged or unreadable"` selects exactly one
test and it is already green. Select on the requirement:

```bash
PWHEADLESS=1 uv run pytest -m "requirement_refs and FR_012" -q
```

Seed a non-UTF-8 verdict record. Every reader in the census must resolve to its
**declared** polarity — five fail-open or crashing readers were measured, including
`tasks_parsing_validation.py:296`, which carries an explicit `# fail-open` comment.

The merge gate is **already** fail-closed and needs no change — but record *why*: it
works only because `UnicodeDecodeError` subclasses `ValueError` and `from_file`
funnels `OSError` into `ValueError` too, while the gate catches bare `ValueError`. A
future reader-side exception outside that hierarchy silently re-opens it.

## Date rot

```bash
PWHEADLESS=1 uv run pytest tests/status/test_work_package_lifecycle.py -q
PWHEADLESS=1 uv run pytest tests/architectural/ -k "absolute_event_timestamp" -q
```

The lifecycle test must pass **with no product change** — if `work_package_lifecycle.py`
appears in the diff for this concern, the fix is wrong. The new check must flag a
fixture that mixes a hard-coded timestamp with a `now()`-generated one, and must
**not** flag a fixture whose events are all hard-coded.

## Coverage is measurable again

```bash
gh pr checks <pr> | grep -E "fast-tests-(status|review|dashboard)"
```

Before this mission, one red shard silently skipped five others plus their
integration counterparts, so `src/specify_cli/review` — this mission's own write
surface — produced no coverage XML. All should now run regardless of each other's
result.

## Gates

```bash
uv run ruff check src/ tests/
uv run mypy --strict <touched files>
uv run ruff check --select C901 src/specify_cli/review/ src/specify_cli/cli/commands/agent/
PWHEADLESS=1 uv run pytest tests/architectural/test_no_legacy_terminology.py -q
```

Zero issues, zero new suppressions, every touched function at complexity ≤15.

## What "done" does not mean

- The renames in #3158 items 1–2 are **not** in this mission (C-003).
- The repo-wide frontmatter consolidation is **not** in this mission — deferred on
  breadth, not on an architectural block.
- Epic #3044 does **not** close: its remaining child #3088 is out of scope.
- `test_issue_2804_*` and `test_issue_3086_*` stay **red** (C-005). Greening them
  is a violation, not an improvement.
