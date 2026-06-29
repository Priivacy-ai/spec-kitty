# Mission Review Report: event-sync-retention-delivery-01KVYWRG

**Reviewer**: Senior reviewer (Claude Opus, post-merge mission review)
**Date**: 2026-06-29
**Mission**: `event-sync-retention-delivery-01KVYWRG` — event sync retention delivery (#2124)
**Baseline commit**: `81dfa05158e3e7a41efe6134d002b62935ca7be4`
**HEAD at review**: `5898596de2b01e5640eb2294031e27d94b1b1475`
**WPs reviewed**: WP01..WP12 (all `done`/merged on `mission/event-sync-retention-delivery`)
**Mission diff**: 26 src files, +5988/-60; new domains `src/specify_cli/event_journal/` + `src/specify_cli/delivery/`, plus `sync/target_authority.py`, `sync/migrate_journal.py`, `sync/emitter.py`.

---

## Gate Results

### Gate 1 — Contract tests
- Command: `SPEC_KITTY_ENABLE_SAAS_SYNC=1 .venv/bin/pytest tests/contract/ -q`
- Exit code: **non-zero** (5 failed, 275 passed, 1 skipped — 96 s)
- Result: **FAIL** (hard gate; literal non-zero exit)
- **Attribution: NONE of the 5 failures is caused by this mission.** Verified by `git diff baseline..HEAD --name-only`: the mission touched zero of the failing files and made **no `pyproject.toml`/`uv.lock`/dependency change**.
  - 3× `tests/contract/test_events_envelope_matches_resolved_version.py` — missing snapshot `tests/contract/snapshots/spec-kitty-events-6.1.0.json`. The repo resolves `spec-kitty-events==6.1.0` (constraint `>=6.0.0,<7.0.0`) but only snapshots through `6.0.0` exist. The 6.1.0 bump landed in a foreign commit (`6c060f1d8`, mission 2119); the snapshot was never regenerated. Dependency-snapshot drift, repo-level, not this mission.
  - 2× `tests/contract/test_example_round_trip.py` — `MISSING_FRONTMATTER` in `kitty-specs/org-pack-subdir-and-doctrine-qol-01KVSRJ6/...` and `kitty-specs/specify-protected-primary-coherence-01KVMBD6/...`. Both belong to **other missions**; untouched here.
- The mission's own contract-surface changes (`contracts/batch-api-contract.md` additive; `kitty-specs/mvp-cli-sync-boundary-completion-01KRX11M/contracts/sync-status-output.md` additive) are intact and not among the failures.

### Gate 2 — Architectural tests
- Command: `.venv/bin/pytest tests/architectural/ -q`
- Exit code: **non-zero** (6 failed, 595 passed — 384 s)
- Result: **FAIL** (hard gate)
- **Attribution: ALL 6 failures are mission-attributable.** This is a real, fixable, mission-caused gate breach:
  1. `test_no_new_orphan_surfaces` — **9 new test files run in ZERO CI gates and will never run in CI**: all `tests/delivery/test_*.py` (6) + all `tests/event_journal/test_*.py` (3). **HIGH** — the mission's entire test evidence for both new domains is unenforced in CI.
  2. `test_every_test_file_declares_a_pytestmark_marker` — the same 9 files declare no `pytestmark` marker (root cause of #1).
  3. `test_no_dead_symbols::test_no_public_symbol_in_all_is_unimported` — ~26 public symbols in `delivery/config.py`, `delivery/ledger.py`, `delivery/receivers.py` `__all__` with no live `src/` importer. The set includes the **entire C-008 discard machinery** (`AuditSink`, `DiscardAuditRecord`, `DiscardDecision`, `DiscardDecisionKind`, `FamilyClassification`, `JsonlAuditSink`, `discard_decision`) — confirming C-008 is implemented but not wired (see DRIFT-1).
  4. `test_no_dead_modules::test_no_new_dead_modules_under_src` — `specify_cli.event_journal.coalesce` flagged as a new dead module. It is functionally live (the dispatcher activates it) but only via `importlib.import_module("specify_cli.event_journal.coalesce")` in `delivery/dispatcher.py:142,159`, which static analysis cannot see (see RISK-2).
  5. `test_no_new_tmp_literals_in_tests` — `tests/delivery/test_targets.py:63` introduces a `/tmp/` literal not in the frozen baseline (LOW; also a per-worker HOME-isolation concern).
  6. `test_docs_cli_reference_parity::test_visible_paths_match_reference` — `spec-kitty sync archive`, `sync gc`, `sync mode` are missing from the reference docs (MEDIUM; new operator surface undocumented).

### Gate 3 — Cross-repo E2E
- Command: `SPEC_KITTY_ENABLE_SAAS_SYNC=1 .venv/bin/pytest spec-kitty-end-to-end-testing/scenarios/ -v`
- Exit code: **NOT RUN** — the `spec-kitty-end-to-end-testing` repo is not present in this checkout.
- Result: **NOT RUN (ENVIRONMENTAL)** — recorded as an environmental non-run, not a code defect. No `mission-exception.md` is required: the mission claims **no new cross-repo behavior** (IC-09 SaaS `/health` metadata is explicitly out of scope per C-004, deferred to a follow-on). There is no mission-claimed cross-repo scenario left unproven.

### Gate 4 — Issue Matrix
- File: `kitty-specs/event-sync-retention-delivery-01KVYWRG/issue-matrix.md`
- Rows: 5
- Empty / `unknown` verdicts: 0
- Result: **FAIL**
- **3 rows carry an `in-mission` verdict that survives to mission `done`** — a hard fail by the Gate-4 rule (`in-mission` is accepted at per-WP `approved` but **rejected on the `done` transition**):
  - **#2130** (design synthesis) — implemented across the mission WPs → must be promoted to `fixed` / `verified-already-fixed`.
  - **#2146** (target-authority prerequisite) — delivered by WP01/WP02 → must be promoted to a terminal verdict.
  - **#2144** (capture-before-drain invariant) — delivered by WP03 → must be promoted to a terminal verdict.
  - The two `deferred-with-followup` rows (**#2165** docs-reorg, **#2131** multi-target fan-out) each name a follow-up handle → OK.

**Gate tally: Gate 1 FAIL (external/non-attributable), Gate 2 FAIL (mission-attributable), Gate 3 NOT RUN (environmental), Gate 4 FAIL (matrix not promoted). Any hard-gate FAIL forces the Final Verdict to FAIL.**

---

## FR Coverage Matrix

Tally: **17 ADEQUATE · 2 PARTIAL · 0 MISSING · 0 FALSE_POSITIVE.** Every verdict was reached by reading test bodies. The suite drives production code against real SQLite/journal DBs and re-reads persisted state; the FR-011 immutability test reads raw BLOB bytes via `sqlite3`, bypassing the in-memory model. No synthetic-fixture false positives found. (Caveat: per Gate-2 #1, these tests currently do **not run in CI** — coverage exists but is unenforced.)

| FR | Brief | WP | Test (file:func) | Adequacy | Finding |
|----|-------|----|------------------|----------|---------|
| FR-001 | Non-destructive success | WP03/07 | `test_journal.py::test_no_normal_path_delete_surface_exists`, `test_reappend_…idempotent` | ADEQUATE | append OR IGNORE; re-read keeps v1; no delete surface |
| FR-002 | Per-target ledger | WP04/05 | `test_ledger.py::test_delivered_to_a_still_selectable_for_b` | ADEQUATE | real PK `(event_id,target_id)`; A excludes, B selects |
| FR-003 | Target-independent journal | WP03 | `test_journal.py::test_event_model_carries_no_target_or_delivery_field` | ADEQUATE | introspects `dataclasses.fields(Event)` vs forbidden set |
| FR-004 | Select undelivered-for-target | WP05/07 | `test_dispatcher.py::test_select_undelivered_uses_universe_and_excludes_terminal` | ADEQUATE | real terminal rows; query returns only undelivered |
| FR-005 | Re-drain to new target | WP07/12 | `test_dispatcher.py::test_replay_to_new_target_redelivers_and_retains` | ADEQUATE | A→B replay; `journal.count()==3` after both |
| FR-006 | EventSyncConfig modes | WP09 | `test_config.py` (presets / refuse / fail-closed) | ADEQUATE¹ | 4 modes observable; OPT_OUT refuse+audit unit-tested (C-008 caveat) |
| FR-007 | External receiver | WP06/09 | `test_config.py::test_external_receiver_records_ledger_without_teamspace_credentials` | ADEQUATE | external branch + shared mapper + ledger write (no network e2e) |
| FR-008 | Stub receiver | WP06 | `test_receivers.py::test_stub_records_events_with_no_teamspace_credentials` | ADEQUATE | real production receiver, creds deleted, driven via `dispatch` |
| FR-009 | status retention/delivery split | WP11/12 | `test_status_report.py::test_distinct_counts_retained_previous_current` | ADEQUATE | 124/prev/current-0 distinct from real journal+ledger |
| FR-010 | Explicit gc/archive | WP11/12 | `test_status_report.py` + `test_sync_commands.py::…gc` | ADEQUATE | real gc/archive; ledger preserved; explicit-only |
| FR-011 | Coalescing honesty | WP08 | `test_coalesce.py::test_coalesce_against_delivered_event_leaves_bytes_unchanged` (T049/NFR-002) | ADEQUATE | raw BLOB byte-for-byte unchanged after real coalesce |
| FR-012 | Target-reset detection | WP04 | `test_targets.py::test_reset_flagged_on_stable_field_change` / `…deployment_id_only…not_a_reset` | **PARTIAL** | advisory-only by design (C-004); no `/health`, no auto-redrain; **no production caller** |
| FR-013 | Migration of scoped queues | WP10 | `test_migrate_journal.py::test_multiple_scoped_dbs_migrate_in_one_run`, `…unknown_digest…` | ADEQUATE | multi-DB + legacy + malformed-skip; unknown provenance |
| FR-014 | DeliveryReceiver contract | WP06 | `test_receivers.py::test_all_three_receivers_implement_the_one_protocol` | ADEQUATE | all 3 vs runtime Protocol; dispatch has no isinstance branch |
| FR-015 | Terminal-failed handling | WP05/07 | `test_dispatcher.py::test_terminal_failed_parks_event_and_drain_progresses` | ADEQUATE | parks payload; drain progresses; excluded from next select |
| FR-016 | Canonical sync target authority | WP01/02 | `test_target_authority_wiring.py::test_owner_identity_follows_resolved_target_under_split_brain` | **PARTIAL** | status/scope leg bound+tested; **WebSocket + tracker NOT threaded onto resolver** (DRIFT-2) |
| FR-017 | Capture-first durability | WP03 | `test_capture_first.py::test_emit_writes_journal_before_delivery_gates_when_disabled` | ADEQUATE | sync disabled → journal row exists with `drain_blocked_reason` |
| FR-018 | Migration collision quarantine | WP10 | `test_migrate_journal.py::test_divergent_duplicate_creates_conflict_and_preserves_source` | ADEQUATE | conflict row; sources untouched; cleanup blocked; non-zero exit |
| FR-019 | Machine-readable status contract | WP11/12 | `test_status_report.py::test_report_has_seven_sections_and_preserves_base` + `test_sync_commands.py` | ADEQUATE | all 7 additive sections + base preserved; JSON round-trips |

¹ FR-006 ADEQUATE for WP09's owned policy scope; the C-008 runtime-enforcement gap is DRIFT-1.

**Legend**: ADEQUATE = test constrains the required behavior against the real production path; PARTIAL = behavior is advisory-by-design or only partially wired; MISSING = no test; FALSE_POSITIVE = test passes with implementation deleted.

---

## Drift Findings

### DRIFT-1: C-008 "no silent Teamspace-bound discard" is implemented but not runtime-enforced
**Type**: LOCKED-CONSTRAINT NOT ENFORCED
**Severity**: HIGH
**Spec reference**: C-008; FR-006; spec US2 acceptance #5; contract §2 ("OPT_OUT/TRASH can discard only local-only or explicitly discardable families; Teamspace-bound discard must be refused or audit-recorded").
**Evidence**:
- `delivery/config.py` exports the discard-safety machinery (`discard_decision`, `DiscardDecision`, `DiscardDecisionKind`, `FamilyClassification`, `AuditSink`, `JsonlAuditSink`, `DiscardAuditRecord`) — all flagged by `test_no_dead_symbols` as having **no live `src/` importer**.
- `cli/commands/sync.py:1747-1752` (`sync mode OPT_OUT`) only sets `retention=OFF` and prints a note; no capture-time path routes a Teamspace-bound family through `discard_decision`. The emitter's `_emit`/`capture_teamspace_bound` path does not consult the discard guard.
- `cli/commands/sync.py:418-420` self-documents "capture→journal emit path … not yet live".

**Analysis**: The OPT_OUT mode, as actually wired, can silently stop journaling/delivery without invoking the audit/refuse guard the constraint requires. The unit tests for `discard_decision` pass because they call the function directly — but production never calls it. This is the classic "module has no live caller" anti-pattern, and here it lands on a **binding constraint** (C-008), so it is HIGH, not mere hygiene. Note this is corroborated independently by the Gate-2 dead-symbols failure.

### DRIFT-2: FR-016 single-target authority not threaded onto the WebSocket/tracker network leg
**Type**: PARTIAL-FR (network arm)
**Severity**: MEDIUM (documented follow-up exists)
**Spec reference**: FR-016; C-007; SC-008 ("never derive queue scope for one target and call another").
**Evidence**:
- `sync/client.py` (WebSocket) has **zero** resolver references; it provisions its own `ws_url` via `provision_ws_token(team_id)` on each `connect()` and never receives a `ResolvedSyncTarget`.
- `sync/tracker_client_glue.py:22-30` references `ResolvedSyncTarget` only in its docstring; no resolver call.
- `sync/runtime.py` resolves the target only to emit a debug log, then constructs `WebSocketClient(...)` **without** it; `_resolve_runtime_target` swallows all exceptions (including `SyncTargetSplitBrainError`) → `None`.
- No tests cover `client.py`/`tracker_client_glue.py`/`runtime.py` against the resolved target.

**Analysis**: The status/queue-scope leg of FR-016 is genuinely bound and adversarially tested (`test_target_authority_wiring.py`), satisfying SC-008 for readiness/owner/preflight. But the real-time transport (WebSocket) and tracker still derive their URL independently — exactly the split-brain class FR-016 set out to eliminate. **This is a known, documented follow-up**: the WP02 approval verdict (status event log) explicitly records it ("FR-016's one-target-across-tracker/WebSocket only PARTIALLY met within owned files … Recommend follow-up WP to bind those two sites to `ResolvedSyncTarget.resolved_server_url`") and notes the two sites lie outside any WP's `owned_files`. The implementer honestly documented the invariant rather than fabricating dead resolver calls. Non-blocking on its own, but the matrix/report must carry it forward.

### DRIFT-3 (informational): FR-012 reset-detection advisory-only and uncalled — by design
**Type**: PUNTED-FR (declared)
**Severity**: LOW (matches C-004)
**Evidence**: `delivery/targets.py:377` `detect_reset` is read-only (diffs `_STABLE_RESET_FIELDS`, which excludes `deployment_id`), returns an advisory signal, makes no `/api/v1/sync/health/` call, and has no production caller. `tasks.md` addendum A5 and C-004 declare full reset-detection deferred to the IC-09 follow-on. Documented and consistent — recorded for completeness, not a defect.

---

## Risk Findings

### RISK-1: Dual live drain in `sync now` double-POSTs each event to the server during the transition
**Type**: CROSS-WP-INTEGRATION
**Severity**: MEDIUM
**Location**: `cli/commands/sync.py:1618-1660`; emitter dual-write `sync/emitter.py:1930` (journal) + `:2053/2213/2262` (legacy `OfflineQueue`).
**Trigger condition**: Any `sync now` with SaaS enabled, auth present, and events present in the legacy queue.
**Analysis**: The capture-first emitter writes every event to **both** the legacy `OfflineQueue` (`queue` table) **and** the new `event_journal`. `sync now` then runs (a) the legacy destructive drain `service.sync_now()` — which still POSTs the `queue` rows and deletes them on success (`queue.py:1716` `process_batch_results`) — and (b) additively the new non-destructive WP07 `dispatch()` (`sync.py:1660`), which POSTs the same events from the journal to the same Teamspace endpoint and records to the ledger. Each event is therefore delivered to the server twice in this transitional release; the server dedupes by `event_id` (the second arrival maps to `duplicate`, recorded as such in the ledger), so there is **no data corruption and no event loss** (the journal retains everything — FR-001/FR-005 hold from the journal). This is documented bridge-staging (WP10 verdict: "legacy dispatcher stays sole active drain → no double-delivery" described the *pre-WP07* state; post-WP12 both drains run). Flagged so the follow-on that retires the legacy queue drain is tracked — until then, expect 2× event POSTs and `duplicate` ledger rows on the new path.

### RISK-2: `event_journal.coalesce` is reachable only via dynamic string import — trips the dead-module gate
**Type**: DEAD-CODE (gate-visible, functionally live)
**Severity**: MEDIUM
**Location**: `delivery/dispatcher.py:62,136-160` (`_COALESCE_MODULE`, `importlib.import_module`, `coalesce.install(ledger)`).
**Analysis**: The dispatcher activates WP08 coalescing on the live path via `importlib.import_module("specify_cli.event_journal.coalesce")`. Functionally this is wired (FR-011 works; `dispatch()` calls `_install_coalescing` first), but the static no-dead-modules gate cannot see a string import and flags the module as orphaned (Gate-2 #4). Either add a direct import seam or record the module in the gate's allowlist with rationale. Not a correctness defect, but it is a real red gate the mission must resolve.

### RISK-3: New-domain test suite (220+ tests) does not run in CI
**Type**: CROSS-WP-INTEGRATION / coverage-not-enforced
**Severity**: HIGH
**Location**: `tests/delivery/*` (6 files), `tests/event_journal/*` (3 files).
**Analysis**: Gate-2 #1/#2 show all 9 new test files lack a `pytestmark` marker and are selected by zero CI gates — they "will never run in CI." Every FR test I rated ADEQUATE in the matrix above is real and passing locally, but **none of it gates CI**. A future regression in `event_journal/`/`delivery/` would not be caught by the marker-based CI profiles. Add the appropriate `pytestmark` markers (and remove the `tests/delivery/test_targets.py:63` `/tmp/` literal) so the evidence is actually enforced.

---

## Silent Failure Candidates

| Location | Condition | Silent result | Spec impact |
|----------|-----------|---------------|-------------|
| `sync/runtime.py` `_resolve_runtime_target` (≈:245) | any exception incl. `SyncTargetSplitBrainError` | returns `None` (debug log only) | FR-016/SC-008: a config/env split-brain that the resolver is meant to surface is swallowed on the runtime/WebSocket path; transport falls back to its own URL derivation (ties to DRIFT-2). |
| `sync/target_authority.py:300-302` | session-scope read fails | returns `None` (debug log) | Benign — `active_queue_scope` is a diagnostic, never an authority input (matches contract §1). Acceptable. |
| `delivery/dispatcher.py:206-212` `_decode_payload` | payload not JSON-object | wraps in `{event_id,event_type}` envelope | Acceptable — keeps the batch well-formed; result keys on `OutboundEvent.event_id`, not payload. Documented. |
| `delivery/receivers.py:476-487` `_post_batch` | `requests.RequestException` | batch-wide `transient` (http_status `None`) | Correct by design — does not poison per-event retries (contract §3, edge case). Acceptable. |

Only the first row is a genuine concern, and it is subsumed by DRIFT-2.

---

## Security Notes

| Finding | Location | Risk class | Assessment |
|---------|----------|------------|------------|
| HTTP timeout present | `delivery/receivers.py:251,479` (`timeout=BATCH_TIMEOUT_SECONDS`) | UNBOUND-HTTP | PASS — every POST has an explicit timeout; no hang-the-CLI exposure. |
| Bearer token handling | `delivery/receivers.py:514-526` (`TeamspaceReceiver.auth_headers` → `Bearer {token}`) | CREDENTIAL-LEAK | PASS — token injected via header only; transport-error string interpolates the exception, not the token; not logged. |
| Parameterized SQL | `event_journal/models.py:77-83`, `delivery/ledger.py`, `delivery/status_report.py:97-99`, `delivery/retention.py:48`, `sync/migrate_journal.py:377` | SQL-INJECTION | PASS — all values bound via `?`; every `# noqa: S608` is identifier-only (table/column names from static module constants), and the migrate projection is built from a fixed allowlist. |
| Migration reads source DBs read-only | `sync/migrate_journal.py` (`mode=ro`) | DATA-DESTRUCTION | PASS — source `queue-<digest>.db` opened read-only; never rewrites event IDs; divergent dup leaves source untouched and blocks cleanup. |
| External/stub receiver URLs | `delivery/receivers.py:532-585` | SSRF | ACCEPTABLE — `ExternalReceiver` posts to an operator-supplied endpoint by design; `StubReceiver` is localhost. No untrusted-input-derived URL. |
| Raw SHA-256 digests | `delivery/targets.py:126`, `sync/migrate_journal.py:350` (`# noqa: TID251`) | HASH-MISUSE | PASS — used for target-identity / payload-equality digests, not security tokens; correctly distinguished from the charter freshness hash. |

No blocking security findings. The mission posts to `{resolved_server_url}/api/v1/events/batch/` with Bearer auth, explicit timeout, gzip body, and clean transient-error mapping.

---

## Final Verdict

**FAIL**

### Verdict rationale
Three of the four hard gates are red, and — unlike a purely environmental miss — **two of those failures are squarely this mission's responsibility**. Gate 2 (architectural) fails on six checks that are all mission-attributable: most seriously, the 9 new-domain test files run in **zero CI gates** (RISK-3, HIGH) so the otherwise-strong test evidence is unenforced; the dead-symbols gate exposes that the **C-008 discard-safety machinery is implemented but never wired into a live path** (DRIFT-1, HIGH); plus a dead-module gate trip (RISK-2), undocumented new CLI subcommands, and a `/tmp` literal. Gate 4 (issue matrix) fails because three rows (#2130, #2146, #2144) remain `in-mission` after the mission reached `done`, which the gate rejects. Gate 1 (contract) is also red, but every one of its five failures is **external and non-attributable** (a `spec-kitty-events 6.1.0` snapshot the mission never bumped, plus two foreign missions' contract frontmatter); it must still be green before tagging, but it is not this mission's code defect.

Set against that, the **core implementation is genuinely strong**: 17/19 FRs are ADEQUATE against real SQLite/journal-driven tests with no synthetic-fixture false positives; the central behavioral shift (non-destructive success → ledger update) is correct; the NFR-002 delivered-event immutability invariant is proven at the raw-byte level; migration is transactional/idempotent with safe unknown-provenance and divergent-dup quarantine; C-006 body-upload tables are intact; security is clean (timeouts, parameterized SQL, Bearer not logged, read-only migration). The two PARTIAL FRs (FR-012 advisory, FR-016 network leg) are both declared/known. In substance this mission is "PASS WITH NOTES" caliber — but the hard-gate contract forces FAIL while Gate 2 and Gate 4 are red, and those reds are real, mission-owned, and fixable in a short follow-up.

### Blocking items (must clear before the verdict can flip)
1. **Gate 2 #1/#2 (HIGH)** — add `pytestmark` markers to the 9 `tests/delivery/*` + `tests/event_journal/*` files so they run in CI; remove the `tests/delivery/test_targets.py:63` `/tmp/` literal (or baseline it with justification).
2. **Gate 2 #3 + DRIFT-1 (HIGH)** — either wire the C-008 discard machinery (`discard_decision`/`JsonlAuditSink`/`FamilyClassification`) into the capture-time OPT_OUT path so Teamspace-bound discard is actually refused/audited, or remove the dead public surface from `__all__` and downgrade the C-008 claim to "deferred" with a follow-up issue. As shipped, OPT_OUT can silently stop delivery without the required audit/refuse.
3. **Gate 2 #4 / RISK-2 (MEDIUM)** — resolve the `event_journal.coalesce` dead-module gate (direct import seam or allowlist entry with rationale).
4. **Gate 2 #6 (MEDIUM)** — document `spec-kitty sync gc | archive | mode` in the CLI reference.
5. **Gate 4 (process)** — promote issue-matrix rows #2130, #2146, #2144 from `in-mission` to terminal verdicts (`fixed`/`verified-already-fixed`).
6. **Gate 1 (repo-level, not mission code)** — regenerate `tests/contract/snapshots/spec-kitty-events-6.1.0.json` (`python scripts/snapshot_events_envelope.py --force`) and fix the two foreign-mission contract-frontmatter round-trip failures so `tests/contract/` is green before any release tag.

### Open items (non-blocking, follow-up mission)
- **DRIFT-2 / FR-016 network leg** — bind `sync/client.py` (WebSocket) and `sync/tracker_client_glue.py` to `ResolvedSyncTarget.resolved_server_url`; stop `runtime.py` from swallowing `SyncTargetSplitBrainError`. Already recorded in the WP02 verdict as a recommended follow-up WP.
- **RISK-1 / dual drain** — retire the legacy destructive `queue.py` event drain from `sync now` once the journal/ledger path is the sole drain, to stop the transitional 2× server POST.
- **FR-012 / IC-09** — wire `detect_reset` to SaaS `/api/v1/sync/health/` metadata when the cross-repo `spec-kitty-saas` change lands (C-004 follow-on); `#2131` (fan-out) and `#2165` (docs-reorg) remain correctly deferred-with-followup.

## Retrospective Reminder

The canonical post-merge sequence is: **mission review → author or verify the retrospective (`spec-kitty retrospect create --mission event-sync-retention-delivery-01KVYWRG`) → surface findings (`spec-kitty retrospect summary` aggregates; `spec-kitty agent retrospect synthesize --mission event-sync-retention-delivery-01KVYWRG` reviews proposals, dry-run by default)**. Under default 3.2.0 policy the `retrospective.yaml` is authored at the runtime terminus; verify it at `.kittify/missions/01KVYWRGF148VXAXDJ90MECYRR/retrospective.yaml`. If it is absent and `retrospect create` fails, escalate — check `status.events.jsonl` for `RetrospectiveCaptureFailed` events and their `remediation_hint`.
