# Contract: Fail-Closed Pre-Merge Guard

**Concern**: IC-03 / IC-04 · **Requirements**: FR-002, FR-003, FR-008, FR-009, NFR-002, NFR-003

## Trigger

Every pull request whose diff touches `kitty-specs/**` — **including a diff that
touches ONLY `kitty-specs/**`**. Hosted in a `pull_request`-scoped CI job that is
outside the `src/**` `changes` filter and registered as a **required,
non-skippable** status check.

## Inputs

The set of missions whose corpus (`meta.json` / `status.events.jsonl`) appears in
the PR diff (all of them, not just the "current" mission).

## Behavior

For each diff-touched mission, decide **cut over** using the data-model
definition — the acceptance test's event-log-evidence predicate
(`_mission_carries_event_log_runtime`) + non-empty-snapshot birth invariant
(`_assert_birth_invariant_holds`) + `verify_backfill` as a necessary-not-sufficient
check. **Do NOT key solely on `verify_backfill.ok`** (vacuous for native missions).

## Outcome (MUST)

- **Pass**: every diff-touched mission is cut over.
- **Fail (non-zero)**: any diff-touched mission is un-cut-over — message names the
  mission(s) and prints the exact remedy:
  `spec-kitty migrate backfill-runtime-state --mission <slug>`.
- **Fail closed**: on any verify error, missing artifact, ambiguous corpus, or
  absent `mission_id` — never pass on uncertainty.

## Performance

- Diff-scoped (touched missions only); completes < 30s in CI on the current
  corpus (measure on the real corpus — the full-corpus dogfood test is separate).

## Wiring guarantees (FR-008 / R1)

- The host workflow's `on.pull_request.paths` includes `kitty-specs/**` (or the
  host has no `paths` filter).
- The job runs on `pull_request` (not push-only) and is not behind the src
  `changes` gate.
- Registered as a **required** check in branch protection; the job must actually
  execute and exit non-zero on failure (a skipped required check passes silently).
- **Verified live**: a scratch PR touching only `kitty-specs/**` shows the job
  running and able to fail.

## Acceptance tests

- **US2**: a diff carrying an un-cut-over (incl. natively-born) mission → guard
  reds with name + remedy; all-cut-over diff → passes.
- **R1 live check**: corpus-only scratch PR triggers the guard.
- **R2 vacuity**: a natively-born un-cut-over mission (empty `verify_backfill`)
  is still flagged un-cut-over by the guard.
