# Quickstart: Legacy→Journal Capture Cutover

How to reproduce the bugs and verify the mission is green. Commands assume the shadow
venv is on PATH (`export PATH="$PWD/.venv/bin:$PATH"`) and
`SPEC_KITTY_SYNC_DISABLE=1` for fast local runs.

## Reproduce (red, on `main` today)

The blocking-CI reproduction:

```bash
PWHEADLESS=1 .venv/bin/python -m pytest \
  tests/regression/test_issue_3425_setup_plan_legacy_layout_silent_capture.py -q
# Expect (pre-fix): 3 failed, 4 passed
#   - test_authenticated_setup_plan_lands_in_scoped  → LegacyQueueMigrationRequiredError
#   - test_setup_plan_refuses_on_daemon_owner_mismatch → wrong (auth) refusal
#   - test_setup_plan_authenticated_coherent_succeeds  → exit 2 (spurious auth refusal)
```

Live dogfood reproduction (this repo is an un-migrated legacy root): any
`spec-kitty agent mission create …` prints `Warning: Explicit-context event capture
failed: live payload writes require the project_only layout; legacy state is migration
input only` — silent zero-capture.

## Verify (green, post-fix)

Per-slice acceptance:

- **IC-01 credential parsing (FR-004 / SC-002)**: a coherent authenticated host passes
  setup-plan preflight (exit 0), scope derived from the supported credential format.
- **IC-02 layout + auto-cutover (FR-002/003 / SC-001/004/005)**: on a fresh temp root,
  emitted events land in the journal (was 0); on a legacy-with-data temp root, capture
  resumes and the pre-existing event count is preserved exactly once (snapshot diff);
  re-running an interrupted cutover adds nothing (idempotent).
- **IC-03 single record + honest sync (FR-005/006)**: each event appears once; `sync
  now` does not report success while events remain in the legacy queue.
- **IC-04 loud cutover/backfill (FR-007)**: a cutover write that cannot land surfaces a
  non-silent failure.
- **IC-05 observable emitter (FR-001/010, #3391)**: an unrecoverable capture failure is
  surfaced (not stderr-swallowed) and stays non-fatal (host command does not crash).
- **IC-06 reproductions (FR-008 / SC-003)**: the rewritten `test_issue_3425_*` suite is
  fully green.

Blocking gate (the release-authority check):

```bash
# The regression-blocking selection must be green on this branch (NFR-004):
PWHEADLESS=1 .venv/bin/python -m pytest tests/regression/ -q
```

Escape hatch check:

```bash
# With the escape hatch set, a legacy-with-data root is NOT auto-mutated; it surfaces a
# loud, actionable refusal pointing at `sync project-store-migrate` (never silent):
SPEC_KITTY_NO_AUTO_CUTOVER=1 <driver that emits an event on a legacy-with-data root>
```

## Rebase note

Before landing, rebase `fix/legacy-journal-capture-cutover` onto current
`upstream/main`. All target files were last touched by merged #3293 (`cd3d6a91d2`);
nothing has re-touched them since, so conflicts are unlikely (research finding 03).
