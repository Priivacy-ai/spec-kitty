---
affected_files: []
cycle_number: 1
mission_slug: per-project-sync-consent-ledgers-01KZKMQZ
reproduction_command:
reviewed_at: '2026-08-10T01:02:18Z'
reviewer_agent: codex
wp_id: WP03
---

# WP03 Review Cycle 1 — Approved

The implementation matches the locked WP03 contract and is approved without
implementation edits.

## Authority and consent decisions

- `ProjectSyncStore` is the sole persisted consent authority. The only direct
  grant writer is `record_project_opt_in`; opt-out and legacy import are
  refusal-only.
- Environment, login, target, checkout, repository default, legacy UUID index,
  discovery, and store presence cannot create a grant. Missing, unreadable, and
  incompatible authority fail closed.
- Retired implicit and bulk writers raise
  `LegacyConsentMigrationRequiredError` with explicit migration guidance and do
  not create a project-store decision.
- Same-action retry returns the identical stored action identity without a
  generation bump. An adversarial cross-actor retry also returned the original
  record. Opposite actions advance the generation; opt-out followed by opt-in
  reached generations 2 and 3.
- The public routing action persists consent locally while offline and while the
  machine rollout switch is disabled. Egress paths continue to require the
  independent `SPEC_KITTY_ENABLE_SAAS_SYNC` gate.

## Epoch, history, and hint boundaries

- Capture sequence allocation and epoch selection occur inside the caller's real
  SQLite unit of work. Both capture-before-opt-in and opt-in-before-capture
  orderings are covered. The opt-in tail is inclusive, subsequent capture is
  strictly after it, and opt-out/re-opt-in seals without deleting or relabelling
  historical rows.
- History preview binds exact row IDs, source epochs, row-content hashes, and an
  aggregate SHA-256 without persisting authority. Confirmation persists the
  exact cohort and actor/idempotency/consent/target/admission generations.
  Consumption revalidates both cohort and current authority. A separate
  adversarial probe confirmed that opt-out invalidates an already confirmed
  history capability.
- Daemon hints are atomic, checksummed, payload-free, expiring, and can encode
  only deny or revoke. Missing, malformed, forged-grant, stale, expired,
  generation-mismatched, or incompatible hints require the project authority;
  only a current integrity-checked denial may narrow discovery.

## Evidence

- RED at `8b463beea`: the committed acceptance contract failed collection because
  `ConsentAction`, `allocate_capture_sequence`, and the new authority types were
  absent before the implementation commit.
- GREEN at `7f9366cea`: 27/27 owned tests passed.
- The rewritten #3030 denial and whole-config write-refusal defenses passed
  57/57; legacy tests retain denial and preservation behavior without a hidden
  grant path.
- Architecture, aggregate, and incident coverage passed 114 tests with 2
  documented expected failures.
- Ruff format-check and lint passed on all 14 owned files; strict mypy passed on
  the 5 source modules; `git diff --check 8c99d8cfa^..HEAD` passed.
- The structural census proves exactly one direct may-grant persistence site and
  exactly one may-grant consent resolver. All 13 `TODO(#3280)` disclosures remain
  intact.
- Planning commits `a8b75a965` and `9d2b0703d` narrowly record ownership of the
  superseded #3030 tests and structural census files; the corrections do not
  broaden implementation scope.

## Anti-pattern checklist

1. **Dead code — N/A**: history capability and deny-hint seams are intentionally
   staged for dependent WPs, and the consent-to-hint path is already wired.
2. **Synthetic fixtures — PASS**: acceptance tests exercise the real
   `ProjectSyncStore`, SQLite transactions, epoch rows, history rows, and atomic
   hint files.
3. **Silent empty returns — PASS**: uncertainty is represented as typed denial or
   authority-required state; no silent grant or success was found.
4. **Functional-requirement coverage — PASS**: consent authority, both epoch
   orderings, immutable history, stale-authority refusal, deny hints, offline
   actions, and legacy-writer retirement are covered.
5. **Frozen surface — PASS**: no frozen external contract was changed.
6. **Locked decisions — PASS**: sole authority, fail-closed inputs, monotonic
   epochs, explicit history confirmation, and narrowing-only hints are enforced.
7. **Shared-file ownership — PASS**: both planning corrections are explicit and
   limited to the files required by the WP03 contract.
8. **Production fragility — PASS**: new failures are typed, fail-closed boundary
   failures; local opt-in/opt-out perform no network operation.

No material blocker or newly discovered non-critical hardening issue remains for
this review cycle.
