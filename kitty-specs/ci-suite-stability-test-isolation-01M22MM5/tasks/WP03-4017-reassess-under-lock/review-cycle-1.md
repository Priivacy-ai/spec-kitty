---
affected_files: []
cycle_number: 1
mission_slug: ci-suite-stability-test-isolation-01M22MM5
reproduction_command:
reviewed_at: '2026-09-09T13:58:43Z'
reviewer_agent: user
wp_id: WP03
---

# WP03 Review Feedback #1 — REJECT (one trivial gate failure; core fix is correct)

**Reviewer:** reviewer-renata (independent)
**Verdict:** REJECT — a single, one-command fix. The #4017 core fix itself is correct and fully
proven; the only blocker is a newly-introduced `ruff format` gate failure on WP03's own lines.

## The blocker (must fix before re-review)

`ruff format --check` fails on two changed source files, and the violating lines were introduced
by this WP (the mission base is format-clean — verified by running `ruff format --check` against
`kitty/mission-ci-suite-stability-test-isolation-01M22MM5:src/specify_cli/runtime/bootstrap.py`,
which reports "already formatted").

```
$ .venv/bin/python -m ruff format --check src/specify_cli/runtime/*.py
Would reformat: src/specify_cli/runtime/asset_preparation.py
Would reformat: src/specify_cli/runtime/bootstrap.py
```

The two hunks ruff wants collapsed to a single line (repo line-length permits it):

1. `asset_preparation.py` ~L612 — the `content_paths = tuple(...)` generator (your new line).
2. `bootstrap.py` ~L233 — the `logger.info("runtime assets already materialized ...")` call (your new line).

Why this gates (this tree's checked-out `CLAUDE.md`, post-#3995 CI):
- CI runs `ruff format --check .` over the whole repo (`ci-quality.yml` / `ci-router.yml`) — the
  file goes red regardless of whether it was run locally.
- `tests/architectural/test_ruff_format_enforcement.py` enforces the same command inside `make test-full`.
- It contradicts this WP's own Validation line ("ruff+mypy clean") and the DoD ("0 new regressions
  vs base" — the base format gate was green).
- This is the CI-suite-stability mission, and WP04 depends on WP03; a format-red WP03 hands the red
  downstream.

**Fix (one command, reviewer does not apply it per role separation):**
```
.venv/bin/python -m ruff format src/specify_cli/runtime/asset_preparation.py src/specify_cli/runtime/bootstrap.py
```
Then confirm `ruff format --check` is clean on both, re-commit, and request re-review. No other
change is needed.

## Everything else verified PASS (no other findings)

1. **Both e2e DRIVEN for real — headline gate:** `26 passed in 659.42s (0:10:59), 0 skipped, 0 xfailed`
   (`tests/e2e/test_worktree_owned_root_concurrency.py` — 20 parametrized iterations + siblings — and
   `tests/e2e/test_charter_epic_golden_path.py`, `-rsx`, `SPEC_KITTY_ENABLE_SAAS_SYNC=0 PWHEADLESS=1`).
   Both `@pytest.mark.skip("#4017…")` decorators are removed with NO xfail/skipif substitution.
2. **Retry bounded + non-swallowing (`retry_torn_read`):** `_TORN_READ_RETRY_ATTEMPTS = 3`; the loop
   retries at most 2 times on a `ValueError` whose message starts with `"Asset changed during
   preparation:"`, then the final `return build()` runs un-guarded so a still-unstable torn read (or
   any non-prefixed exception) propagates. Genuine mid-write corruption is never masked.
3. **Re-assess-under-lock correctness:** cold path applies the *re*assessment, never the stale plan;
   on `reassessment.effects == []` it logs the operator sentence and returns (loser no-op). Warm
   fast-path (`if not assessment.effects: return`) is upstream of `recheck_assets`, so it takes
   exactly one assess and NO lock — proven by the instrumented spies in `test_reassess_under_lock.py`
   (`assess == 1`, `lock == 0`). No double-apply. Both owners (`ensure_global_agent_skills`,
   `_apply_command_assessment` via `rebuild`) mirror the seam symmetrically.
4. **Role-tagging:** the agent_skills/agent_commands destination-root + target probes now pass
   `role="destination_probe"`; `observe()` only ever *upgrades* a path to `source_read` (monotonic,
   never downgrades), so genuine source drift is still refused — confirmed by
   `test_genuine_package_source_change_between_assess_and_apply_is_still_caught` and the combined
   source+destination drift test (both green).
5. **Out-of-map edits (`agent_commands.py`, `agent_skills.py`):** genuinely necessary (fixing only
   `bootstrap` leaves the two sibling owners exposed to the same torn-read/stale-plan race), minimal
   (role tags + mirrored re-assess + retry wrapper only), and recorded (comments cite the
   all-owners rescope; the interleave test header records the flip). Sanctioned by the operator's
   Generic-all-owners decision — not a scope violation.
6. **No regression + WP02 intact:** `tests/runtime/` → `921 passed, 1 skipped` (the 1 skip is the
   unrelated pre-existing live-preview skip; the WP03 files run full when `.venv/bin/spec-kitty`
   exists — all 8 WP03/interleave tests pass here). mypy clean on all 4 changed source files;
   `ruff check` clean. WP01 interleave asserts the operator signal and the absence of both race
   signals — green.

Re-review will be fast: the fix is cosmetic and the substance is already proven.
