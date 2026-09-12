---
affected_files: []
cycle_number: 3
mission_slug: per-project-sync-consent-ledgers-01KZKMQZ
reproduction_command:
reviewed_at: '2026-08-10T04:02:42Z'
reviewer_agent: codex
wp_id: WP04
---

# WP04 Review Cycle 3 — Changes Requested

Cycle 3 repairs the incident control and rejects both the ordinary same-UUID
home-a/home-b pair and a structurally equal fake identity. One material
authority-binding gap remains: the identity object is transplantable because
it is not bound to the context's full authority snapshot.

## 1. A cloned A context accepts B's genuine store identity

`build_project_store_status()` now requires every repository identity to be
the same object as `context.store_identity`
(`src/specify_cli/delivery/status_report.py:544-555`). That proves all
repositories share one UoW open, but it does not prove the consent/admission
fields in the supplied context were derived from that UoW.

An exact real-store probe created UUID P under two physical homes. Home A was
explicitly opted in. Home B contained one body task. It then cloned the valid
home-A `ProjectSyncContext` with `object.__new__(ProjectSyncContext)`, copied
all A authority fields, and replaced only `store_identity` with the genuine
identity object exposed by home B's active UoW. Home B's journal, ledger, and
body queue all exposed that same genuine object. Status accepted the bundle
and returned:

```text
genuine_identity_transplant_ACCEPTED
{'decision': {'state': 'granted', 'generation': 1},
 'body_task_count': 1,
 'same_path': False}
```

The submitted negative tests do not exercise this case. They pass the original
home-A context to B, or replace its identity with a new structurally equal
`object.__new__(VerifiedProjectStoreIdentity)`. Both necessarily fail the `is`
comparison. Transplanting B's genuine identity onto the cloned A snapshot
satisfies that comparison while preserving A's authority fields, reproducing
the cycle-2 cross-pair with a coherent-looking report.

Bind the full authority snapshot to the verified active UoW rather than
validating a transplantable context attribute. Acceptable shapes include a
UoW-minted context capability whose validation covers the complete immutable
authority snapshot, or deriving the decision/context inside the same active
UoW used to construct the repository bundle. A path comparison, UUID check,
or `context.store_identity is repository.store_identity` alone is not enough.
Add the exact `object.__new__(ProjectSyncContext)` plus genuine-home-B-identity
transplant as a negative test, with journal/ledger/body read counters proving
rejection occurs before every read and a genuine same-UoW positive control.

## Verified cycle-3 evidence

- The re-pinned incident control uses real `ProjectSyncStore` UoWs for both
  journal and ledger. It executes the production write spies/counter and proves
  A `+1`, B `+0`, A-only opens, and byte-exact B storage.
- Direct `ProjectUnitOfWork(...)` construction raises `TypeError`. A real UoW's
  journal, ledger, body queue, and unit expose the exact same identity object.
  The submitted original cross-home and structurally equal fabricated-identity
  tests reject before reads. The stronger genuine-identity transplant above
  is the remaining failure.
- Exact owned/authorized matrix: `256 passed, 2 xfailed`.
- Extended history/purge/incident controls: `24 passed`.
- Normal repository collection gate: `67 passed`.
- Architecture gate: `48 passed, 2 xfailed`.
- An additional normal-collection superset passed `274 passed, 2 xfailed`.
- Strict mypy passed on all 26 designated files. Ruff check passed and all 11
  cycle-3 files are formatted. Compileall and
  `git diff --check f26780557^..33c3763ed` passed.
- The bounded `project_store.py` change adds the UoW/identity seam and path type
  casts only; it does not modify schema statements, layout authority, or
  admission behavior. Planning authority records sequential WP02 → WP04 → WP05
  ownership and WP05's dependency/consumption note. WP05 must consume the
  corrected cycle-4 seam, not the transplantable one.
- Cycle-1 and cycle-2 review artifacts remain byte-exact at SHA-256
  `33f755bfc5e1ade42a989a52d09d898c40aea720edbdb4a5be53b0024b93984e`
  and `da4bc756cbac53b1b5f49988be135280e3806eff6495bf3213c51efee202b706`.
- Cycle-3 RED `f26780557` precedes fix `33c3763ed`; planning authority
  `93f86096d` is in the candidate ancestry. No WP07/WP10 reserved source/test
  was changed, and the architectural files retain exactly 12 `TODO(#3280)`
  markers.
- The cycle-2 genuine persisted history capability/revalidation, physical body
  purge, foreign-owner rejection, deterministic backoff, and
  `preserve_delivery_history` separation remain green. No component-level live
  `connect()`/`commit()`, default path, or global resolver was added.
- The in-scope project-store layout contract remains unchanged and its explicit
  one-store/UoW rule is precisely the blocker above. The sender/migration matrix
  contains no cycle-3 example changed by this seam. All 11 issue-matrix rows
  retain allowed verdicts.

## Anti-pattern checklist

1. **Dead code — PASS**: every new identity/UoW surface has a production caller.
2. **Synthetic fixtures — PASS**: the incident and identity tests use real
   stores, UoWs, SQLite rows, and production status code.
3. **Silent empty return — PASS**: no new silent-empty failure path was found.
4. **Functional-requirement coverage — FAIL**: the locked cross-store authority
   boundary is neither enforced nor covered against genuine-identity transplant.
5. **Frozen surface — PASS**: cycle-1/2 artifacts and WP07/WP10 surfaces remain
   untouched.
6. **Locked decisions — FAIL**: independently supplied authority and repository
   state can still be combined despite the project-store contract.
7. **Shared-file ownership — PASS**: the bounded `project_store.py` and incident
   test transfers are explicitly sequenced in planning, including WP05 handoff.
8. **Production fragility — FAIL**: status can emit a trusted-looking grant from
   home A alongside payload diagnostics read from home B.

WP05, WP06, and WP10 depend on WP04 and must consume/rebase onto the corrected
cycle-4 boundary.
