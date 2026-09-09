# R2-T1 destructive manifest (frozen module scope)

**Bead:** `R2-T1` (parent feature `R2`, `docs/BEADS_PROGRAM_GRAPH.json`) · **Reviewer:** reviewer-renata
**Frozen:** 2026-08-21 · **Base:** `38090b6493dd9fdf77826200348a82a22c5f61c4` (`spec-kitty`)
**Source contract:** `m1-contract-drafts/R2.md` §3.4 ("Physical absence — public interface")

This is the frozen module-deletion scope R2-T1 works against, taken verbatim from the
reviewed R2 contract-freeze draft (`R2.md`, review disposition §9 clean — HIGH/MEDIUM/LOW
findings all fixed). It is not a summary to be re-derived by each reader; it is the contract
this WP's own diff is checked against.

**What this manifest is and is not.** This freezes *scope* (which modules are DELETE /
RETAIN / MIXED and why) ahead of the daemon-retirement and migration-tool work packages
(§5 (a)/(b)) that must land and converge first, per R2.md §3.2.3: "`daemon.py`,
`orphan_sweep.py`, `owner.py`, `daemon_protocol.py`, `restart.py` are deleted once the
retirement step above ships and is proven to converge." It is **not** yet the #3167-style
three-independent-controls symbol-level closure proof (`scripts/verify_batch_retirement_3167.py`
and `kitty-specs/chain-b-consent-bypass-3167-01KZ63HK/contracts/deletion-manifest.md` are the
methodology precedent this repo already established, per R2.md §2.5) — that AST-closure
verification is WP(c)'s work, run once physical deletion is safe to perform, and this
document is the frozen input to it, not a substitute for it.

## DELETE (full module/package, all tests whose only subject is the module, all doc/CLI-help references)

Grouped by the R2 criterion's own vocabulary (R2.md §3.4):

**daemons**
- `sync/daemon.py`, `sync/daemon_protocol.py`, `sync/orphan_sweep.py`, `sync/owner.py`, `sync/restart.py`

**sender/receiver**
- `delivery/receivers.py` (`TeamspaceReceiver`, `ExternalReceiver`, `StubReceiver`)
- `delivery/dispatcher.py`, `delivery/consent_gate.py`, `delivery/selection.py`, `delivery/ledger.py`,
  `delivery/config.py`, `delivery/status_report.py`
- `sync/client.py` (`WebSocketClient`), `sync/emitter.py`
- `sync/events.py` (SaaS-emission functions only — the local `status.emit`/`status.events.jsonl`
  writer in `specify_cli/status/emit.py` is a different module, F2-owned, not touched here)
- `sync/runtime.py`, `sync/runtime_event_emitter.py`, `sync/consent.py`, `sync/routing.py`,
  `sync/preflight.py`
- `sync/admission_operations.py`, `sync/target_authority.py` — **conditional**: retained if R1's
  landed retained-admission surface still needs them; R2-T1 must re-verify against R1's actual
  landed state before deleting, not assume (R2.md §2.3, §3.4)
- `sync/feature_flags.py` (`SAAS_SYNC_ENV_VAR` / `is_saas_sync_enabled`)
- `saas/readiness.py`, `auth/websocket/token_provisioning.py`, `auth/websocket/__init__.py`

**history**
- `sync/history_import/` (all 5 files: `upload.py`, `pipeline.py`, `scan.py`, `synthesize.py`,
  `identity.py`), `sync/history_disclosure.py`

**body**
- `sync/body_transport.py`, `sync/body_upload.py`, `sync/body_queue.py`,
  `sync/namespace.py` (body-upload namespace types), `sync/dossier_pipeline.py`

**external**
- `delivery/targets.py` (`ProjectDeliveryTargetRegistry`), the `EXTERNAL_RECEIVER` mode in
  `delivery/config.py` (subsumed above)

**legacy raw/invalid stores**
- `sync/project_store.py`'s doomed tables (file itself retained only if F2 needs the
  SQLite-aggregate/transaction pattern as a starting point — R2-T1's call, recorded in
  candidate notes, not this manifest's)
- `sync/project_store_migration.py`, `sync/migrate_journal.py`, `sync/queue.py`,
  `sync/layout_generation.py`
- `sync/queue.py`'s `OfflineQueue` / `ProjectOutboxTask`
- `sync/local_commit.py`'s SaaS-push half only (`reconcile_local_commit_result`); the
  local-state half (`SyncState`, `load_sync_state`/`save_sync_state`) is F2's to rehome first

**CLI surface** (`src/specify_cli/cli/commands/sync.py`, per R2.md §2.2's 21-command table)
- DELETE: `routes`, `opt-out`, `opt-in`, `import-history`, the workspace-sync-trigger command,
  `sync_server`, `now`, `gc`, `archive`, `project-store-preview/-migrate/-status/-quarantine/-history`,
  `migrate` (dead refusal stub), `mode`, `diagnose` — 16 commands total (exact registered names to be
  re-confirmed by `grep '@app.command' -A1` at implementation time, not by line number alone)
- SPLIT (same file, disjoint sections): `doctor` — retain only the tracker-egress rendering
  (`_render_tracker_egress*`)
- PARTIAL: `status` — delete the sync-target/delivery sections; any surviving "is my local
  journal healthy" reporting is an open item for R2-T1 to resolve with F2 (R2.md §6 D5), not to
  delete or keep unilaterally
- `purge` (line ~4359 at base) becomes R2-T1's own migration/retirement tool, or is deleted in
  favour of a new one-shot tool — R2-T1's design choice, not this manifest's
- Supporting doomed-surface plumbing: `sync/diagnose.py`, `sync/diagnostics.py`, `sync/deny_hints.py`,
  `sync/git_metadata.py` (if solely a sync-context helper), `sync/lint_report_staging.py`
  (if sync-delivery-scoped) — verify no F2/local use before deleting

**config**
- The `[sync]` table's server-URL/mode/target keys in `sync/config.py`; `SPEC_KITTY_ENABLE_SAAS_SYNC`
  env var references repo-wide

## RETAIN (unchanged — R2-T1 must not touch)

`sync/sharing_client.py`, `tracker/saas_client.py`,
`saas_client/client.py` + `saas_client/endpoints.py` + `saas_client/errors.py` + `saas_client/auth.py`
("Widen Mode" — flagged out of scope, not authorized by any R1–R4/F1–F3/Z1–Z8/TRACKER-M1 node),
`auth/*` (all OAuth), `dashboard/*`, `doctrine/sources/api_source.py`,
the `share`/`unshare` CLI commands, the tracker-egress slice of `doctor`.

## MIXED / must-split-not-delete-wholesale

`sync/local_commit.py`, `sync/config.py`, `sync/preflight.py`'s admission-adjacent helpers
(if any survive), `invocation/propagator.py` (open item — its consent-resolver seam may be
reused by a retained surface; do not delete as a corollary of the doomed pipeline without
reading every caller of `resolve_egress_consent` first), `cli/commands/sync.py`.

## Egress-allowlist arithmetic (`tests/architectural/test_egress_consent_boundary.py`)

At base, `_EGRESS_ALLOWLIST_FILES` / `tests/architectural/_baselines.yaml:264`
(`egress_allowlist_files`) = **28**. Of the DELETE-disposition files above that also hold an
`_EGRESS_ALLOWLIST` entry (R2.md §2.3's table): 12 are clean DELETE, 1 (`cli/commands/sync.py`)
is PARTIAL (file survives, allowance shrinks to the retained `share`/`unshare`/`doctor` slice).
WP(c) must lower the ratchet to match the post-deletion count **exactly** (a hard equality
check, not a ceiling — R2.md §4 row N13, §7 risk).

## Sequencing (R2.md §5 — internal WP order, one Beads task, no graph fork)

1. **(a) daemon retirement** — an explicit retirement step (no final sync) reachable from a
   normal post-R2 CLI invocation; converges against any pre-R2 daemon before anything in this
   manifest is deleted.
2. **(b) migration tool** — valid canonical facts (`journal_entries` rows) migrated into F2's
   journal with exact counts/hashes, forward-only, quarantine-on-conflict; blocked on F2-T1's
   published write surface (`F2 → R2-T1` typed edge, not yet landed as of this freeze).
3. **(c) physical deletion** — this manifest executed, egress-ratchet lowered, dead-code gates
   (`test_no_dead_modules.py`, `test_no_dead_symbols.py`) clean, #3167-style closure proof run.
4. **(d) CLI-surface split** — `doctor`/`status` split finalized once (a)–(c) land.

(c) cannot safely run until (a) and (b) are individually proven — this manifest freezes what
(c) deletes, it does not authorize deleting it yet.
