# Research: Runtime-State Birth-Cutover (All Landing Paths)

Synthesis of the pre-planning grounding squad (reuse/related-issues lens +
adversarial lens; brownfield lens partial — its ground was covered by the reuse
lens). Decisions here are inputs the plan/tasks must honor.

## Settled context (do not re-litigate)

- **#2160** — single artifact authority thesis. There is one canonical
  authority path; a second stamp that resolves paths differently is a regression.
- **#2816** — established the `backfill → verify(fail-closed) → reader cutover →
  writer cutover → delete fallbacks` contract and made the snapshot reader
  unconditional. `status_phase`'s only remaining live effect is gating the legacy
  `lane` mirror (`emit.py:401`), a no-op for new missions — the drift is real but
  runtime-inert; it is a latent invariant violation, not a runtime break.
- **#2917 (reopened)** — root cause: no birth-time cutover seam; Option-C chosen
  (retire frontmatter authoring — already done by #2684/#2816 — then stamp at
  birth and re-key the guard to an event-log birth invariant). Newest diagnosis:
  the #2920 seam fires only in `merge/executor.py` (the `spec-kitty merge` path);
  GitHub squash/rebase landings never trigger it → recurrence.
- **#2920** — birth-cutover-at-merge. Two load-bearing engineering calls:
  (1) the flip was moved **post-target** with idempotent resume-heal because
  `canonicalize_feature_dir → resolve_canonical_root` redirects a worktree's
  `.git` to the main repo root and a pre-merge flip writes a stale `meta.json`;
  (2) the seed-event commit must target the **coord** ref (committing a COORD
  artifact through the PRIMARY bookkeeping seam raised `SafeCommitHeadMismatch`).
  Deferred follow-up **#2923**: route `_flip_phase` through the placement port.
- **#2968** — mechanical whole-corpus re-green (data-only), `Refs #2917`. This is
  the WP1 front-load; the backlog is cleared, so this mission focuses on the
  structural fix + guard.

## Reuse map (extend, do not duplicate)

- **Single stamp authority**: `runtime_state_cutover.cutover_mission` (:234) — the
  orchestrated `seed → fail-closed verify → atomic flip`, topology-aware via the
  `status_feature_dir` (COORD) kwarg; `_flip_phase` (:186) is the sole
  `status_phase` writer; `cutover_repo(dry_run=True)` (:315) backs the audit.
- **Reference wiring**: `merge/executor.py::_run_birth_cutover` (:939) — the
  accept-time stamp mirrors this shape so the two callers share one function.
- **Guard predicate**: reuse `test_dogfood_corpus_backfilled.py`'s
  `_mission_carries_event_log_runtime` (:142) + `_assert_birth_invariant_holds`
  (:242), NOT bare `verify_backfill`.
- **Audit host**: `spec-kitty doctor cutover` subcommand shell → `_cutover_doctor.py`
  (per-subcommand-module doctor convention).
- **Guard CI host**: a `pull_request`-scoped, fail-closed job (candidate
  `release-readiness.yml`), with `kitty-specs/**` added to its trigger paths.

## Decisions & rejected alternatives

| Decision | Rationale |
|----------|-----------|
| Stamp at terminal `accept`, not `create`/`finalize` | Runtime state must be final (dual-write trap); `accept` runs on-branch, pre-PR, already commits residual artifacts. |
| Guard keys on event-log evidence, not `verify_backfill.ok` | `verify_backfill` is vacuously green for natively-born missions (no frontmatter to seed → `wp_count=0, ok=True`). |
| Guard is the binding backstop; stamp is best-effort | Seam-bypass paths (direct-authored, cancelled, mid-flight, later-mission edits) never hit the terminal stamp. |
| Pin claim-anchor to one canonical leg | Prevents flipped-but-unverifiable corpus from divergent seed payloads (R5). |
| Fail closed on absent `mission_id` | Slug-namespaced seeds change identity when `mission_id` is later minted → duplicate/divergent events (R6). |
| No further one-time backfill | #2968 already re-greened whole-corpus; stamp + diff-guard hold the line. |
| **Rejected**: relax the acceptance predicate | Green-washing a valid lock; rejected twice on #2917. |
| **Rejected**: post-merge reconcile pushing to `main` | Violates no-direct-push (C-001). |

## Open verification items for implementation

- **Live path-filter check (R1)**: open a scratch PR touching only
  `kitty-specs/**` and confirm the guard job appears, executes, and can fail. A
  required check that is `if:`-skipped passes silently.
- **30s bound (NFR-002)**: measure the diff-scoped guard on the real corpus.
- **Payload determinism (R5)**: run the stamp twice from different leg contexts;
  assert byte-identical `status.events.jsonl`.
