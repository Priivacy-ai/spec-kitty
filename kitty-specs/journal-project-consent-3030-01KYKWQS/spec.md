# Mission Specification: Journal Project Consent

**Mission Branch**: `feat/journal-project-consent-3030`
**Created**: 2026-07-28
**Revised**: 2026-07-28 (post-spec adversarial squad — root cause re-anchored, see "Correction")
**Status**: Draft
**Input**: `Priivacy-ai/spec-kitty#3030` (P0) — CLI counterpart of `Priivacy-ai/spec-kitty-saas#585`

## Problem

The sync drain **authorizes and delivers at different scopes**. One opted-in checkout ships the
whole producer-scoped event store — every unrelated local project on the machine — to the hosted
server. Confirmed live on 2026-07-27: 1,322 events belonging to 5 projects the operator never opted
into were delivered alongside 7,811 from the one intended project. Per-repo routing in that checkout
was correct throughout. Confidentiality breach reachable with no misconfiguration; the only
"mistake" available is working on more than one project on one machine.

### Correction to the original diagnosis

Issue #3030 and `saas#585` both pin the defect at `sync/batch.py:1064-1080`. **That is the wrong
drain for `sync now`.** Verified:

- `cli/commands/sync.py:2360-2367` — "the journal-based dispatcher is now the **SOLE** event drain
  (FR-001): the retired legacy `service.sync_now()` offline-queue drain deleted journal-owned events
  AND double-POSTed every event the dispatcher also delivers (the dual-drain defect)".
  `cli/commands/sync.py:1004-1005` repeats it: "This is the SOLE event-delivery path for `sync now`".
- `sync/queue.py:1-12` — "Event-queueing authority has been **retired** from this module: the durable
  event store is now the WP03 append-only journal… The `queue` table here is kept only as the
  *legacy batch-transport bridge*".
- `sync/migrate_journal.py:769-772` — "delivery reads from the journal, not the queues".

The real selection is `delivery/dispatcher.py:192-223` `_select_undelivered`, whose universe is
`journal.read_all()` (`dispatcher.py:214`) — every row of every project, with no project predicate —
reached from `cli/commands/sync.py:1001-1049` `_run_event_sync_dispatch`. The `selected` figure the
incident reported is `DispatchSummary.selected` (`dispatcher.py:87`, printed at
`cli/commands/sync.py:1047-1048`), not a `batch.py` counter.

A fix implemented at `batch.py:1064` would pass its unit tests and leak in production.

### Root cause, restated against the real path

1. **The delivery context has no consent gate at all.** The complete gate vocabulary is
   `GateKind = {SAAS_ENABLED, PRIVATE_TEAMSPACE, AUTH, ENDPOINT_CONFIGURED}`
   (`delivery/receivers.py:143-146`), built at `cli/commands/sync.py:681-686` from
   `is_saas_sync_enabled()`, `bool(target.team_slug)`, `bool(auth_token)`, `receiver.endpoint_url`.
   No consent field exists. `is_sync_enabled_for_checkout` has **zero callers** under `delivery/`.
   Authorization on the leaking path is per-producer/team (`event_journal/journal.py:60-75`) — which
   is exactly the scope of the whole machine's journal. The defect is larger than "scope mismatch":
   it is the total absence of a consent gate where delivery is decided.
2. **The consent registry that does exist is default-ALLOW.** `sync/routing.py:82-87`
   (`_build_checkout_sync_routing`) falls through to `effective_sync_enabled = True` when neither a
   checkout override nor a repo default is recorded. In the incident the five client repos were
   **never opted in**, so they have no record — under a literal "reuse the existing records" reading
   each evaluates to *consented*. Inverting only the `routing is None` branch
   (`routing.py:114-116`) does not close this.
3. **Consent is keyed by absolute filesystem path; events are keyed by project.**
   `sync/config.py:216,233` writes `checkout_overrides[str(repo_root.resolve())]`. `project_uuid`
   appears nowhere in `sync/config.py`. A `project_uuid` is bound to a checkout only inside that
   checkout's own working tree (`routing.py:64` reads `repo_root/.kittify/config.yaml`).
   `sync/project_identity.py` is a 29-line re-export shim holding no mapping. **There is no durable,
   machine-global `project_uuid → consent` index.** The predicate FR-003 needs has no data source.
4. **Two live drains over two stores.** `sync now` uses the journal dispatcher, but the background
   daemon still drains the legacy queue: `sync/background.py:589-592` constructs
   `BackgroundSyncService(queue=OfflineQueue(), …)` and `background.py:455-461` reaches
   `batch_sync(queue=self.queue, …)`, plus `background.py:395` `_perform_full_sync` →
   `sync_all_queued_events`. Whichever store this mission does not cover keeps shipping.

## User Scenarios & Testing *(mandatory)*

### User Story 1a - Containment: the drain refuses rather than leaks (Priority: P1)

Before any schema work, the drain stops being silent. If a selected batch spans more than one
project, it refuses, names the projects, and exits non-zero without POSTing. If consent cannot be
determined, it denies.

**Why this priority**: This is hours of work with no migration, and it converts a silent
confidentiality breach into a loud refusal. It ships first and independently of everything below.

**Independent Test**: Seed a journal with events from six projects, run the drain against a
recording ingress, assert zero HTTP requests were made and the refusal names the projects.

**Acceptance Scenarios**:

1. **Given** a selected batch spanning more than one project, **When** pre-flight runs, **Then** the
   drain refuses before any POST, names the projects, and exits non-zero without mutating delivery
   state or bumping retry counts.
2. **Given** `resolve_checkout_sync_routing_readonly()` returns `None`, **When** the sync-enabled
   gate is consulted, **Then** it denies and no network request is made.
3. **Given** a project with **no** consent record at all, **When** consent is evaluated for
   delivery, **Then** the answer is deny — absence of a record is non-consent.
4. **Given** no consented events are selectable, **When** the drain runs, **Then** it short-circuits
   before building or POSTing a payload, reports "nothing to deliver", and exits zero with a message
   that names the real cause rather than the unrelated no-Private-Teamspace diagnostic.

---

### User Story 1b - Only consented projects are ever selected (Priority: P1)

Selection itself excludes non-consented projects, so the invariant holds without relying on a
refusal.

**Why this priority**: The durable fix. Depends on the enablers below, which is why US1a ships
first.

**Independent Test**: Seed a journal with events from six `project_uuid`s, consent exactly one,
drain against a recording ingress, and assert `delivered_project_uuids ⊆ consented_project_uuids`
and `None ∉ delivered_project_uuids`. Fixture must leave the five non-consenting projects with **no**
consent record, mirroring the incident.

**Acceptance Scenarios**:

1. **Given** a journal holding events from 6 projects with consent recorded for 1, **When** the drain
   runs, **Then** every delivered event belongs to the consented project and the other 5 projects'
   rows remain in the journal, undeleted.
2. **Given** an event whose project identity cannot be resolved, **When** selection runs, **Then**
   it is treated as non-consented and never selected, and it is **counted and reported** so the
   denial is observable rather than silent.
3. **Given** 2,000 non-consented events older than 10 consented events, **When** one drain runs,
   **Then** all 10 consented events are delivered — the predicate is applied before the row limit,
   not after it.
4. **Given** a checkout that is opted out, **When** the drain runs, **Then** rows are left untouched
   and no request is made.
5. **Given** the background daemon rather than `sync now`, **When** it drains, **Then** the same
   consent invariant holds on that path and store.

---

### User Story 2 - Per-project store state is visible before draining (Priority: P1)

`sync doctor` and `sync status` report what is actually in the store, per project, with consent
state.

**Why this priority**: `doctor` reported healthy throughout the incident. A fix the operator cannot
verify is not a fix.

**Independent Test**: Seed a multi-project journal; assert both commands report one row per project
with event count, oldest-event age and consent state, and that totals reconcile against the
journal's retained-event count.

**Acceptance Scenarios**:

1. **Given** a journal spanning 6 projects, **When** `sync doctor` runs, **Then** it reports a
   per-project breakdown with consent state and flags non-consented projects.
2. **Given** the same, **When** totals are summed, **Then** they reconcile against the journal's
   retained-event count (`_count_retained_events`, `cli/commands/sync.py:714-717`) — **not** against
   `OfflineQueue().get_queue_stats()` (`cli/commands/sync.py:3619-3627`), which is empty after
   `sync migrate` and is the source of the incident's false-green.
3. **Given** a consented project whose checkout path no longer resolves, **When** the report runs,
   **Then** it appears as a distinct "consented but unresolvable" row rather than silently denied.
4. **Given** `sync migrate` consolidating rows, **When** it runs, **Then** it reports the per-project
   composition of what it moved.

---

### User Story 3 - The operator can purge non-consenting data locally (Priority: P2)

**Why this priority**: There is no remediation path today; `sync gc` only purges payloads delivered
to *all* targets, so it cannot clear retained rejected rows. Independent of the enablers, so it can
be pulled forward.

**Independent Test**: Seed delivered, rejected and undelivered rows across projects; dry-run and
assert nothing changed; execute and assert exact removal.

**Acceptance Scenarios**:

1. **Given** a multi-project store, **When** `sync purge --project <slug-or-uuid>` runs without
   confirmation, **Then** it reports per-state counts and changes nothing.
2. **Given** the same, **When** run with confirmation, **Then** only that project's rows are removed
   across **both** the journal and the delivery ledger, including rejected rows `sync gc` cannot
   reach.
3. **Given** a slug matching nothing, **When** purge runs, **Then** it reports zero matches and
   exits zero.
4. **Given** `sync purge --all` with confirmation, **When** it runs, **Then** the store is emptied
   and the total is reported.

---

### User Story 4 - Machine-global arming is documented (Priority: P3)

**Acceptance Scenarios**:

1. **Given** the sync docs, **When** an operator reads the env-var reference, **Then** the
   machine-global scope of `SPEC_KITTY_ENABLE_SAAS_SYNC` and `SPEC_KITTY_SAAS_URL` is stated
   explicitly, with a docs-anchor check that fails in CI if the section is removed.

---

### Edge Cases

- **Consented checkout moved, renamed or deleted.** Consent is path-keyed
  (`sync/config.py:216`), and resolving a `project_uuid` requires reading a file inside that path
  (`routing.py:64`). A `git mv`, reclone or laptop migration makes the lookup miss, FR-004 denies,
  and the operator's **own** history strands with no diagnostic. Covered by FR-013 (uuid-keyed
  consent) and US2 scenario 3.
- **Identity-less events.** `sync/emitter.py:2081-2085` deliberately enqueues events with no
  `project_uuid`. Identity resolves from three sites (`namespace.project_uuid`, top-level, payload —
  `sync/queue.py:1714-1720`). Any recorder or predicate must use the same three-site chain, and the
  nil sentinel `00000000-0000-0000-0000-000000000000` (`emitter.py:2150`) counts as unresolvable,
  not as a groupable value.
- **Two checkouts of one repository with opposite overrides.** `project_uuid` lives in
  `.kittify/config.yaml`, which can be committed, so two checkouts can share a uuid and hold
  contradictory `checkout_overrides`. Resolution rule is mandated by FR-013.
- **Same repository re-`git init`ed.** New `project_uuid`, genuinely a new project, starts
  non-consented.
- **Consent revoked between selection and POST.** Evaluated at selection; an in-flight batch is not
  retroactively filtered. Revocation takes effect from the next selection.
- **Journal per producer, not per team.** `resolve_journal_path` keys on `user_id`/`team_slug`;
  switching teams selects a different DB. The predicate must not assume one journal means one team.
- **Backfill interrupted.** Idempotent and resumable; a partial backfill must never leave a row
  *appearing* consented.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | ~~Consent gate in the delivery context~~ **RETIRED 2026-07-30** | US1a | Originally: a new `GateKind` plus a consent port injected into the dispatcher. Retired on three grounds, not dropped. (1) **The per-project half is superseded**: `GateContext` is run-scoped booleans with no project dimension and `evaluate_gates` yields one decision per receiver per run, so a gate structurally cannot carry it — and C-003 settled that project consent is represented once, in selection. A `GateKind` would be the second representation C-003 forbids. (2) **The machine-level half already ships, in a better form**: IC-01 allowed a gate to express "this batch spans projects", which `_cross_project_refusal` does at exactly the position a gate would occupy — and better, because a blocked `GateDecision` is binary with no per-event outcome vocabulary, so it could only abort. That is what H1 had to fix: routing a batch refusal to `TERMINAL_FAILED` destroyed the *consented* project's events too. The gate vocabulary is the wrong instrument for the one case that matters. (3) **The residual "consent unresolvable" case is real but not computable** — see FR-020. Shipping the member anyway would reproduce this mission's own worst pathology: a symbol that looks like FR-001 landed while the invariant is unenforced. Verified: a resolver that *raises* already propagates out of `dispatch`; only the swallowed-fault path is silent. | High | **Retired** |
| FR-021 | An unreadable project-local file must not defer to a stale grant | US1b | **New 2026-07-30, found while fixing FR-020 — and it fails OPEN, unlike FR-020.** Level 1 (`.kittify/config.yaml`) carried the same swallowed read as level 2, so an unparseable or unreadable project file fell through to the machine-global index. Measured with the index carrying a grant: readable `sync.enabled: false` -> denied correctly; **unparseable YAML -> `granted=True, level=machine_index`**; **chmod 000 -> `granted=True, level=machine_index`**. FR-013's refusal-outranks-grant rule was therefore voidable by a syntax error, deferring to precisely the record that survives a clone or rename — so the surviving value is a stale grant. Live path: an operator commits `sync.enabled: false`, a later edit breaks the YAML, and egress resumes silently. Fixed with FR-020 in `c633c548b0`. **Measurement trap recorded**: the first probe showed this as *denied*, because `_answer_project_local` calls `_reconcile_index`, so a readable-refusal case rewrites the index before a later case runs — a shared-home fixture makes this leak look like a denial. | Security | High | **Fixed** |
| FR-022 | The same fall-through survives in `sync/routing.py` | US1b | **Reported 2026-07-30, FIXED same day (`5928ef189b`).** `routing.py` swallowed an unreadable project-local file, after which a checkout-level grant overrode it before default-deny — the FR-021 shape on a second path. Measured through `is_sync_enabled_for_checkout` with a checkout grant present and a per-case `SPEC_KITTY_HOME`: readable `sync.enabled: false` → denied ✓; **chmod 000 → granted** (`assert True is False`); **unparseable YAML → granted** (`effective_sync_enabled=True, local_sync_enabled=True`); absent → granted ✓ (correct, regression-guarded). **A third state was not the leak at all but a crash**: a top-level-list `config.yaml` raised `AttributeError: 'CommentedSeq' object has no attribute 'get'` out of `load_identity` (`identity/project.py:322`), so a policy read that should answer a boolean took out its caller — found only by reading failure text rather than the pass/fail tally. Fixed by `_routing_for_unreadable_project_config` placed **before the identity read** in both entry points, which closes leak and crash together: a broken project file can no longer take out any command that consults the gate. Consumes `project_local_consent_fault()` (its first production consumer) rather than re-deciding readability, per C-003. Absence stays absence — denying on a missing file would deny every delivery on the machine. Denial-on-this-ground is distinguishable from ordinary no-record via `CheckoutSyncRouting.project_local_fault`. Also pins that **opt-in on an unreadable config refuses and writes no grant**, without which the natural remedy for the new denial would manufacture exactly the stale grant the fix stops honouring. | Security | High | **Fixed** |
| FR-032 | `token_manager._ws_client` is a phantom attribute that silently disables three senders | US1a | **Found 2026-07-30 by composing two agents' findings; NOT FIXED — and it is a latent-severity multiplier rather than a leak.** `getattr(token_manager, "_ws_client", None)` is read at `sync/__init__.py:373`, `sync/local_commit.py:683`, and (transitively) by `invocation/propagator.py` via `adapters.get_saas_client` → the factory registered at `sync/__init__.py:411`. **Nothing in `src/` ever assigns it** — no `=`, no `setattr`, and `src/specify_cli/auth/` never declares it; only tests inject it. The genuinely live WebSocket client is a **different attribute on a different owner**: `SyncRuntime.ws_client`, constructed at `sync/runtime.py:242` and handed to the emitter at `:252`/`:379`, which is what `emitter.py:2497` publishes through. Consequences: (1) `invocation/propagator.py`'s send (FR-025) is **dead in production** — the factory returns `None` and the function early-returns at the client lookup, so FR-025's fix is defence-in-depth against a path that does not currently execute; (2) `emit_local_commit`'s **immediate** send is dead (E16), which is why WP12 gating the **connect-time flush** was the load-bearing half; (3) `_saas_client_factory` always returns `None`. **Why it is not merely dead code:** the moment anyone assigns `_ws_client` — a plausible one-line "fix" for "the propagator never sends" — all three paths go live simultaneously, and FR-025's and WP12's gates become the only thing standing between them and the incident. The gates are now in place, which is the right order; but the phantom must be resolved deliberately (wire it and accept that the gates are load-bearing, or delete the three readers and the factory) rather than left as an accident that happens to be safe. It is also invisible to `tests/architectural/test_no_dead_symbols.py`, which scans the AST for references — a string-literal `getattr` is a string, not a reference, so a never-assigned attribute read this way cannot be seen by that gate. | Security | **Medium** | **Open** |
| FR-028 | `import-history` is a **sixth egress path** and is ungated | US1a | **Found 2026-07-30 by the dedicated egress enumeration. NOT FIXED.** `sync/history_import/upload.py:290` `_deliver_chunks` → `receivers.deliver` → `requests.post`, reached from `sync import-history --apply` (`cli/commands/sync.py:2390`). A grep for consent or `sync_enabled` across `src/specify_cli/sync/history_import/` returns **zero hits**. Its only gate is `_resolve_gated_receiver` → the `GateKind` set `{SAAS_ENABLED, PRIVATE_TEAMSPACE, AUTH, ENDPOINT_CONFIGURED}` — **the exact set this spec's own root-cause §1 states has no consent field** — plus a `Mode.TEAMSPACE` check. It is single-project by construction (`build_import_plan(repo_root)` yields one `plan.identity.project_uuid`), so it **holds the uuid and never asks it**; the fix is therefore small. Ships a mission's full synthesized history: `mission_slug`, `project_slug`, envelope payloads. **This is where FR-001's retirement has a scope error** — FR-001 was retired because `_cross_project_refusal` sits "at exactly the position a gate would occupy", which is true for the dispatcher, but `import-history` shares the `GateContext` and **not** the dispatcher, so it inherited the retirement without inheriting the replacement. A correct decision recorded in this mission left this path with nothing. | Security | **High** | **Open** |
| FR-029 | The tracker SaaS client is a **seventh egress path**, ungated, and fires during mission creation | US1a | **Found 2026-07-30. NOT FIXED.** `tracker/saas_client.py:301` `_request` → `httpx` across 10 endpoints, of which `push`, `run` and `bind_mission_origin` are POSTs. Gated on auth and `X-Team-Slug` only (`:280-291`); `project_uuid` appears **nowhere in the module**. Reachable interactively via `sync push` / `run` / `pull` and `mission_type.py:309` — and **non-interactively during mission creation**, through `core/mission_creation.py:617` → `core/adapters.consume_pending_origin` → `tracker/origin_consumer.py:55` → `bind_mission_origin`, registered at `tracker/__init__.py:46`. Carries `mission_slug`, `project_slug`, `mission_id` and the external issue `title`. **The non-interactive reachability is what makes this the worst of the three**: no operator action is required to reach it. | Security | **High** | **Open** |
| FR-030 | The generic SaaS client is an **eighth egress path** and is ungated | US1a | **Found 2026-07-30. NOT FIXED.** `saas_client/client.py:146` `_post` / `:127` `_get` → `httpx`, reached from `cli/commands/decision.py:558`, `charter/interview.py:216`, `missions/plan/{plan,specify}_interview.py:150` and four `widen/*` modules. No consent consumer exists anywhere in the package. One POST carries only `invited_user_ids`; **four GETs carry `mission_id` in the URL path, documented as "ULID or slug"** — and a slug is a client engagement name. Lower severity than FR-028/FR-029 (metadata in a URL rather than payloads) but the same structural gap. | Security | **Medium** | **Open** |
| FR-031 | The body-upload enqueue gate is fail-open and consults the wrong chain | US1b | **Found 2026-07-30. NOT FIXED — the only fail-open gate found on a live-sender path.** `sync/body_upload.py:150` reads `if repo_root is not None and not is_sync_enabled_for_checkout(repo_root)`, carrying **two** defects in one line. (a) When `locate_project_root(feature_dir)` returns `None` the gate is **skipped entirely** — undetermined read as consent, FR-003's defect verbatim, and its fourth independent occurrence in this codebase. (b) It consults the **routing** chain rather than the consent chain, and `sync/__init__.py:348-352` already records exactly why that is wrong: `effective_sync_enabled` "also honours the repo-slug-keyed `[sync.repo_defaults]` record, which FR-019 condemns". So a single path now has two gates on two different chains — a C-003 divergence inside the mission's own fix. Reached from `dossier_pipeline.py:274` via six or more agent commands (`mission_finalize`, `tasks_mark_status`, `research`, `mission_record_analysis`, `mission_setup_plan`, `backfill_identity`) and carries **verbatim `spec.md` / `plan.md` / `tasks/WP*.md` text**. Not itself a leak — E10's per-task gate covers the actual send — but a broken secondary on a store that, unlike `queue_event`, **has a live sender**. | Security | **High** | **Open** |
| FR-025 | The invocation propagator is a **fourth egress path** and reads undetermined consent as consent | US1a | **Found 2026-07-30 by independent review. MEASURED LEAKING. NOT FIXED.** `invocation/propagator.py::_propagate_one` guards with `if sync_enabled is False: return` — `is False`, not `not`. `invocation/adapters.py::resolve_sync_routing` returns `None` **both** when no resolver is registered **and when the registered resolver raises** (`except Exception: return None`), and the registered resolver in `sync/__init__.py` also returns `None` whenever `resolve_checkout_sync_routing(path)` is `None`. So `None` means *"could not determine consent"* and the propagator reads it as **proceed** — FR-003's exact defect ("inability to determine consent is never read as consent") re-derived in a second place, because FR-003 was fixed *inside* `is_sync_enabled_for_checkout` and this path never calls it. Measured with **no consent record anywhere**: resolver `None` → **1 envelope sent**, `request_text` leaked verbatim (`"ACME Holdings carve-out: draft the disclosure schedule"`); resolver raises → **1 envelope sent**, same; resolver `False` → 0. It is also the bug class verbatim: **the path never consults `project_uuid` at all** — consent is reached entirely through `repo_root`. The envelope carries `request_text`, the verbatim agent prompt. **Reachability needs no fault at all** — just an Op record whose `repo_root` does not resolve as a project root; and the raises-branch is live too, since FR-023 records five shapes that crash `resolve_checkout_sync_routing` and FR-024 adds more. **The dossier mentions `propagator`, `invocation/` and `ProfileInvocation` nowhere: this surface was never enumerated, so the mission's egress inventory was incomplete.** | Security | **Critical** | **Open** |
| FR-026 | `runtime.publish_event` is a **fifth egress path** with no consent gate at all | US1a | **Found 2026-07-30 by independent review. NOT FIXED.** `sync/runtime.py::publish_event` sends **any** event dict over the live WebSocket with zero consent check; `grep -n "consent"` returns nothing in `sync/events.py` and nothing in `sync/daemon.py`. Two reachable entries: (1) `_lifecycle_saas_fanout_handler` (`sync/__init__.py:201`) → `_publish_event_via_sync_daemon(event, repo_root)` for `MissionCreated`, whose only gates are `is_saas_sync_enabled()` — **machine-global arming, which this spec states explicitly is never a grant, and which is the incident's own mechanism** — plus a Teamspace scope and resolvable identity, with **no per-project consent**; and (2) the daemon's `POST /api/sync/publish` (`daemon.py:490` → `handle_sync_publish` → `runtime.publish_event`). Failure scenario: the daemon auto-starts for consenting project A (`_auto_start_enabled` consults `is_sync_enabled_for_checkout(project_root)` for **cwd's** project) and is machine-global; a `MissionCreated` for never-opted-in project B then relays through it carrying `project_slug` and `mission_slug` — **in this repository mission slugs are client engagement names**. That is the M1-1 shape one level up: a cwd/daemon-scope grant authorising another project's publish. | Security | **Critical** | **Open** |
| FR-027 | A field-level shape fault in the consent key must not void a committed refusal | US1b | **Found 2026-07-30 by independent review. NOT FIXED — and it is FR-021's own defect, unclosed.** The three modules agree on *file-level* faults but not on field-level ones: `consent.py` treats only a **top-level** non-mapping as a fault, and `_read_project_local` requires `isinstance(raw_hosted, bool)` — anything else is discarded as **absence** and falls through to the stale machine-index grant. Measured post-merge with the index carrying a grant: `sync: {enabled: false}` → denied ✓; unparseable → denied ✓; top-level list → denied ✓; but **`enabled: "false"` → granted (machine_index)**, **`enabled: no` → granted**, **`sync: disabled` → granted**, **`enabled: 0` → granted**. Note `enabled: no`: ruamel's round-trip loader is YAML 1.2, so `no` is the **string** `"no"`, not `False`. So a committed project-local refusal is voidable by a mis-spelling, deferring to precisely the record that survives a clone or rename. **Nothing in production writes this key** (`identity/project.py:328` treats `sync.enabled` as a foreign section it must preserve), so it is hand-authored and committed — which makes mis-spelling the refusal the **expected** failure mode, not an exotic one. `routing.py` inherits it via the same `project_local_consent_fault`. | Security | **High** | **Open** |
| FR-024 | A valid mapping with an unusable `uuid` value must not crash the policy read | US1b | **Found 2026-07-30 by composing two agents' partial findings; NOT yet fixed.** FR-023 guards the *top-level shape*, so a perfectly valid mapping whose `project.uuid` cannot be parsed sails past it: `ProjectIdentity.from_dict` calls `UUID(uuid_str)` (`identity/project.py:121`) **outside** `load_identity`'s `try/except`, which wraps only the YAML parse. Measured through both routing entry points, with the FR-023 case as a passing control: `list-shaped → is_sync_enabled=False` (fence works ✓), but `uuid: "<<<<<<< HEAD"` → **`ValueError: badly formed hexadecimal UUID string`**, `uuid: "not-a-uuid"` → same, `uuid: 42` → **`AttributeError: 'int' object has no attribute 'replace'`** — from **both** `is_sync_enabled_for_checkout` *and* `resolve_checkout_sync_routing`. So the crash half of FR-022 is reopened for a shape its fence does not recognise, and `load_identity`'s seven production callers are all exposed. **A merge conflict marker in `.kittify/config.yaml` is a realistic route** — it is a tracked, hand-edited file. Direction: it crashes rather than grants, so it is not a leak, but it takes out any command that consults the gate, which is precisely the harm FR-022's fence was added to prevent. Fix belongs at the parse (`from_dict`), not at each caller, so all seven are covered at once; the answer must match FR-022/FR-023's existing "exists and cannot be understood" notion rather than adding a fourth. **FIXED** (`136019c3f8`, `11b58403bb`, `7ff1ca7dcf`) — and it was **11 of 13 uuid shapes, in three exception flavours**, not the three reported: `ValueError` for malformed hex / conflict marker / whitespace, `AttributeError` for `42`/`1.5`/`true`/mapping/list/32-hex, `TypeError` for a bare date — each raising on **all five** paths (load, resolve, ensure, and both routing entries). 70 raises across the matrix became 18, all of them the deliberate write refusal. **An entirely unreported second class was found: `repo_slug`.** `load_identity` accepted a non-`str` happily and both routing entry points then died *in someone else's code* — `GitMetadataResolver`'s `"/" not in repo_slug` and `SyncConfig`'s dict lookup, both entitled to assume a string — for 7 of 13 shapes, with `uuid` never involved. Fixed at the parse, so all seven `load_identity` callers are covered at once. Decisions recorded: a padded uuid is **accepted after stripping**, because `sync/consent.py:197` already reads the same key as `str(raw).strip() or None` and diverging would leave two modules disagreeing about which uuid a config declares (C-003); whitespace-only and `''` are **absence**, matching consent.py, which preserves FR-017's "unreachable from production writes" property since the parse still yields a `UUID` object rather than text. YAML's implicit typing is **undone rather than rejected** — about 1 in 281 generated `node_id`s is all-digits and a dash-less 32-hex uuid is legitimate, so scalars are coerced while containers are a genuine fault (`str(CommentedMap(...))` is a Python repr). The fault is a property of the **record**, not the field that carried it: any unusable value drops the whole identity, because per-field triage would be a fourth notion in miniature. **On the write path the harm was concrete, not aesthetic**: before, a direct `atomic_write_config` silently overwrote the corrupt record for every crashing shape — and the uuid is the key other stores reference, so minting a new one orphans every journal row, ledger row and consent-index entry still keyed on the old value, i.e. exactly the data FR-016/FR-017's purge must reach. Truncation was **measured**: `tempfile.mkstemp` counted at runtime, 0 calls on a refusal and 1 on the valid control (proving the counter binds), bytes unchanged, `.kittify/` clean in all 65 probed cases. All faults are reported, not just the first. FR-022's fence re-proved non-redundant by blinding it with the invocations counted (6). | Security | Medium | **Fixed** |
| FR-023 | A structurally invalid `config.yaml` must not crash `load_identity` | US1b | **Found 2026-07-30 while fixing FR-022; fenced there, not yet fixed at source.** A top-level-list `.kittify/config.yaml` makes `load_identity` raise `AttributeError: 'CommentedSeq' object has no attribute 'get'` at `identity/project.py:322`. FR-022's fence sits above the identity read so routing can no longer be taken out by it, but the defect is **latent for every other caller**, including the **writing** path via `resolve_identity` — where a crash mid-write is how a config file gets truncated. Three properties this must satisfy: the non-mapping shape set is probed as a set (list, bare scalar, empty file, top-level string), not just the one shape that happened to surface; "structurally invalid" resolves to the **same** answer routing already gives, or the mission has grown a third notion of "broken config" one function apart (C-003); and if the remedy is a raised typed error, every existing caller that assumes `load_identity` cannot raise is audited, because a new exception nobody catches is a crash moved rather than fixed. Absence must remain absence. | Security | Medium | **Fixed** (`a1ae36b13a`) — and it was **five** crashes, not one. Probing the shape *set* rather than the one shape that surfaced found that **any** non-mapping top level crashed both read and write (`- a\n- list` → `CommentedSeq`; `hello` and `"a string document"` → `str`; `42` → `int`), while empty, comments-only, unparseable and `project: scalar` were already handled on read. The fifth was on the **write** path and nothing had noticed it: `load_identity` swallows a parse error, so `ensure_identity` concludes identity is missing and proceeds to write, where `yaml.load` raises `ParserError` straight through its `except OSError`. **The mid-write truncation worry was disproved, not assumed** — the merge mutates before `mkstemp`, so every case failed *before* writing; no truncation and no stray temp file in any shape, before or after. Decision: a non-mapping top level means "exists and cannot be understood", the same notion `consent.py` already encodes as `ConfigReadFault(kind="unparseable")` — one notion, two directions, so no second definition of "broken config" one function apart. **Reading** yields no identity and never raises, chosen over raising because `load_identity` has **seven** production callers and a new exception nobody catches is a crash moved; two already wrapped it in `except Exception → absence`, so the fix aligns the function with what its careful callers assumed and repairs the five without a wrapper. **Writing** over it refuses via `ConfigNotUnderstoodError`, handled inside `ensure_identity`, which degrades down its existing in-memory path. Side finding: the operator was previously told *"Config not writable"* for a perfectly writable file, sending them to `chmod` when the real fix is a YAML error; the message now names the cause. **FR-022's fence is NOT redundant** — proven by blinding it at runtime (a patch, not a source edit): with the fence `False`, fence blinded `True`, so the leak returns. This fix removed the *crash*, not the *leak*. | Security | Medium | **Fixed** |
| FR-020 | Unreadable consent state must not read as absent | US2 | **New 2026-07-30, found while retiring FR-001.** `SyncConfig._load` returns `{}` for a corrupt-or-unreadable config, which is its documented "missing or invalid" behaviour — so a machine fault becomes **machine-wide silent denial**, misreported to the operator as "no consent record for this project". Measured: healthy → `granted=True, level=machine_index`; corrupt TOML → `granted=False, level=ABSENT`; unreadable (chmod 000) → `granted=False, level=ABSENT`. Every project on the machine reads as never-opted-in, the drain delivers nothing, looks idle, and tells the operator to record consent they already recorded. The distinction dies inside `_load`, below both `consent.py` and `receivers.py`, so **no layer above can report it truthfully** — which is why FR-001's gate could not have been implemented honestly. Also constrains SC-004: `sync doctor` currently cannot tell an operator their consent index is unreadable. | High | **Fixed** (`c633c548b0`) — `ConsentLevel.UNDETERMINED` plus a fault-preserving `read()` keep the distinction alive above `_load`, and `consent_index_health()` exposes it. Note the asymmetry that made this the *lesser* of the pair: FR-020 fails **closed** (silent machine-wide denial — an availability and honesty defect), FR-021 fails **open** (a leak). The doctor-surface wiring of `consent_index_health()` is still owed; `project_local_consent_fault()` is wired as of FR-022. |
| FR-002 | Absence of a consent record denies | US1a | As a consultant, I want an unrecorded project treated as non-consented **for capture and for delivery**, overriding the default-allow fall-through at `sync/routing.py:87`, so never-opted-in projects neither reach the journal nor ship. Pinned by `tests/sync/test_sync_consent_default_deny.py::test_unconfigured_checkout_does_not_consent_to_sync`. | High | Open |
| FR-003 | Routing gate fails closed | US1a | As a maintainer, I want `is_sync_enabled_for_checkout()` to deny when routing is unresolvable (`routing.py:114-116`) so inability to determine consent is never read as consent. Defence in depth for the daemon path, which is its only caller set. | High | Open |
| FR-004 | Cross-project drain refusal | US1a | As an operator, I want the drain to refuse, name the projects and exit non-zero if a selected batch spans more than one project, so a regression in FR-007 cannot silently leak. | High | Open |
| FR-005 | Empty-selection short-circuit | US1a | As an operator, I want the drain to **report the real cause** when nothing is selectable. **Description corrected 2026-07-30** — the original cited two premises that FR-012 and the dispatcher had already made obsolete, and would send the next reader to dead code: (a) the no-Private-Teamspace message at `sync/batch.py:1484-1488` lives in `sync_all_queued_events`, the legacy drain FR-012 **retired** and `sync/__init__.py` deliberately no longer re-exports, so `sync now` cannot print it (its modern counterpart is a structured *log* warning from `sync/_team.py`, never operator stdout); (b) `dispatcher._post` already returns early on an empty batch, so no `{"events": []}` is POSTed; (c) exit 0 was already the behaviour. What was genuinely missing — and is now delivered — is the **diagnosis**: the drain distinguishes *no consented project* / *all identities unresolved* / *everything terminally drain-blocked* / *genuinely empty journal*, sourced from `build_per_project_store_report` so it cannot disagree with `doctor`, `status` or `migrate` (C-003). The delivered/blocked pair is deliberately offered without asserting between them, because telling them apart needs ledger state the report does not carry — and guessing would rebuild the wrong-but-actionable diagnosis this requirement exists to remove. | High | Open |
| FR-006 | Project identity on stored events | US1b | As a maintainer, I want additive indexed `project_uuid`/`project_slug` columns on the journal event row (`event_journal/models.py:31-58` `ORDERED_COLUMNS`) as a derived projection of the envelope, so consent is evaluable without decoding every payload. | High | Open |
| FR-007 | Selection filters by consent | US1b | As a consultant, I want the project predicate applied inside the journal read, so non-consented events are never part of the selected universe. | High | Open |
| FR-008 | Project-filtered journal read seam | US1b | As a maintainer, I want a project-filtered journal read API (e.g. `read_all(project_uuids=…)`) consumed by `_select_undelivered` (`delivery/dispatcher.py:214`), because the current `read_all()` materializes every row of every project and an indexed predicate is otherwise impossible. | High | Open |
| FR-009 | Backfill existing rows | US1b | As an operator, I want existing rows' identity decoded into the new columns idempotently, using the three-site resolution chain, so the predicate covers the 42-day history. | High | Open |
| FR-010 | Mandatory identity at write time | US1b | As a maintainer, I want project identity required when an event is journaled going forward, closing the identity-less class by construction rather than denying it forever downstream. | High | Open |
| FR-011 | Unresolved-identity events are observable | US1b | As an operator, I want events denied for unresolvable identity counted and surfaced in the per-project report, so fail-closed denial is visible rather than silent data loss. | High | Open |
| FR-012 | Both drains enforce the invariant | US1b | As a maintainer, I want the consent invariant enforced on the background-daemon queue drain (`sync/background.py:455-461`) as well as the journal dispatcher, or the queue-backed drain removed, so the uncovered store cannot keep shipping. | High | Open |
| FR-013 | Durable per-project consent index | US1b | As a consultant, I want consent recorded against `project_uuid` (written by `enable_checkout_sync`/`disable_checkout_sync`, `routing.py:130-182`, which already hold both `repo_root` and the resolved uuid), backfilled from today's path-keyed records, with a stated conflict rule — **deny if any checkout of the project is opted out** — and a way to grant or revoke consent by slug/uuid without standing in the checkout. | High | Open |
| FR-014 | Terminal reject classification | US1b | As a maintainer, I want a stable server reject reason mapped to `failed_permanent` and counted in terminal-failure totals, because `failed_permanent` is produced at exactly one site today (`sync/batch.py:414-418`, oversized events) and every server rejection becomes `rejected` → `retry_count + 1` with no deletion and no retry ceiling. Folds #3005; required by `saas#585` FR-004. | High | Open |
| FR-015 | Per-project store reporting | US2 | As an operator, I want `sync doctor`, `sync status` and `sync migrate` to report per-project event count, oldest-event age and consent state, reconciled against the journal's retained count. Folds #3004, without which the report renders from the wrong store. | High | Open |
| FR-016 | Purge by project | US3 | As an operator, I want `sync purge --project <slug-or-uuid>`, dry-run by default, removing that project's rows from both the journal and the delivery ledger via `delivery/retention.py` (`_purge_journal_rows`, `retention.py:51,189`). | Medium | Open |
| FR-017 | Purge all | US3 | As an operator, I want `sync purge --all` behind explicit confirmation. | Medium | Open |
| FR-018 | Document machine-global env vars | US4 | As an operator, I want the machine-global scope of both env vars documented, with a CI-checkable anchor. | Low | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | No unconsented egress | For every drain in the suite, `delivered_project_uuids ⊆ consented_project_uuids` **and** `None ∉ delivered_project_uuids`. Stated as a subset invariant, not a cardinality check: identity-less events collapse to `{None}` and would satisfy `cardinality == 1` while leaking. The recorder must resolve identity via the same three-site chain as `queue.remove_project_events` (`queue.py:1714-1720`). | Security | High | Open |
| NFR-002 | Predicate precedes the row limit | A drain delivers consented events regardless of how many non-consented rows precede them in FIFO order. Filtering after `LIMIT` starves the drain permanently (`_should_stop_sync_loop` breaks on an empty selection); the predicate must be inside the filtered read. | Reliability | High | **Implemented, but its pins are currently UNPROVEN** — flagged 2026-07-30. The predicate is inside the filtered read (H5 moved consent resolution into SQL via `select_consented_event_ids`), and pins exist. But NFR-002's *only* mutation plugin, `mutB_limit_first`, is **obsolete**: its three reds are `TypeError`s from the pre-rebase `read_identity_projection` signature, not assertion failures, so it never demonstrated the starvation property at all. It has been quarantined. A replacement must be written against `select_consented_event_ids`, where the property now lives. Until then, treat NFR-002 as implemented-and-untested-for-falsifiability rather than verified: **absence of a working mutant is not evidence of a load-bearing test**, and this mission has already found a pin that passed with the invariant stripped entirely. Do not claim NFR-002 as verified in any PR body until a valid mutant reds it. |
| NFR-003 | Predicate cost does not scale with store size | With 100k rows across 20 projects, selecting one project's batch performs no full-table payload decode — indexed column lookup only, via FR-008's filtered read. | Performance | High | Open |
| NFR-004 | Backfill is idempotent and lossless | Two runs yield identical column values and identical row counts; no row deleted or mutated outside **the new identity columns**. | Reliability | High | Open |
| | | *Wording narrowed 2026-07-30: was "the two new columns". `repo_slug` was added later (WP06, operator decision) and is one of the columns this mission introduced, so the invariant always held — only the count was stale. Narrowing the **write** instead was rejected: it would blank the repo name for all pre-mission history, which is the incident's own population, with no safety gain since `repo_slug` cannot widen consent.* | | | |
| NFR-005 | Consent gates capture, not only delivery | **Amended 2026-07-29 (operator decision).** Previously: "capture continues unconditionally; no event dropped at write time." That yielded to `#3031` Defect 3 — a non-consenting project's events must **never reach the journal**. Capture-first durability now applies only to *consenting* projects. `event_journal/journal.py` documents the journal write as deliberately unconditional for Teamspace-bound families, so this is a **deliberate reversal of a documented invariant**, not an oversight; the journal's own contract must be updated with it. Beware the fake-green: a bare `if skip_journal: return event` guard leaves capture unconditional at the real caller. | Security | High | Open |
| NFR-006 | Purge is exact | After purging project X, a differential row count over all other projects, in journal and ledger, is zero. | Correctness | High | Open |
| NFR-007 | Fake ingress must exercise the real window | **Retargeted 2026-07-30.** `max_events_per_batch` / `_should_probe_advertised_limits` live only in `sync/batch.py`, whose queue drain WP02 retired — a fake advertising batch limits would exercise an unreachable path. The journal drain's real window is the local constant `_EVENT_SYNC_DISPATCH_BATCH_LIMIT` in `_run_dispatch_batches` (`cli/commands/sync.py:807-820`), halved on HTTP 413 and regrown. The recording ingress must exercise **that** window, since it is what decides whether non-consented rows can fill the selection window. Note WP02 un-exported `batch.py`'s drain entry points but did not delete the module, so it still exists and must not be used as the target. | Security | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Additive schema only | New columns nullable and additive; no rename, retype or drop. An older CLI reading the same DB keeps working. | Technical | High | Open |
| C-002 | Migration never deletes | The backfill must not delete or quarantine any row, including rows whose identity stays unresolvable. Deletion is the operator's explicit act via FR-016/FR-017. | Technical | High | Open |
| C-003 | Journal carries no target/receiver identity | Restated post-review: the journal is **target**-agnostic, not delivery-agnostic — it already stores a delivery-eligibility verdict via `classify_drain_blocked_reason` and the `drain_blocked_reason` column (`journal.py:338`, `models.py:26`). So "the journal must not know about consent" is not load-bearing; what must stay out is *target/receiver* identity (`models.py:2-9`: no target/server/queue-scope field). The new columns are a data projection; the consent *decision* stays in delivery. Decide explicitly whether project consent extends the existing eligibility vocabulary or is a third one — never ship two representations of one invariant. **Decided 2026-07-29: a SEPARATE representation, and the two never overlap.** `drain_blocked_reason` is a *machine-global gate snapshot* taken at capture time (saas/auth/team), re-evaluated at each drain tick and therefore transient; project consent is a *per-project* decision that is stable across ticks. Collapsing them would mean either stranding every pre-login capture or making consent transient. So: consent is represented by the stored `project_uuid` column plus the `consent.py` resolver, and `drain_blocked_reason` keeps its existing vocabulary untouched. Post-backfill the stored column is the **sole** authority for selection (T018); the in-memory identity chain is used only by FR-004's refusal check and the backfill. The one invariant is "delivered ⊆ consented", represented once, in selection. | Technical | High | Open |
| C-004 | Purge routes through retention, not the legacy queue | Use `delivery/retention.py`. `queue.remove_project_events()` (`queue.py:1702-1723`) targets the retired store and full-decodes every row; treat it as superseded and remove it. | Technical | High | Open |
| C-005 | Journal-per-repository-root is a non-goal | Re-scoping the journal per repo root would strand existing multi-week history and is not required for the *egress* property, which FR-006+FR-007 secure within the shared store. Recorded and declined. | Technical | Medium | Open |
| C-006 | Collection remains open for *consenting* projects only | **Restated 2026-07-29** — the original text said "NFR-005 forecloses" write-path gating and concluded the mission secures egress, not collection. NFR-005's amendment reversed that premise: write-path gating is now **required and shipped** (T006 — a non-consenting project's events never reach the journal). The either/or is therefore resolved in favour of gating the write path, and C-005 still declines per-root journal scoping. What remains open is narrower than before: a *consenting* project's payloads still accumulate in one machine-global store shared with other consenting projects, and rows captured **before** T006 landed are still on disk for every project (the incident's own 1,322 among them) until FR-016's purge removes them. So this mission now secures egress **and** future collection for non-consenting projects, while historical collection stays an operator purge action. Whether that is sufficient for a P0 is the operator's call. | Technical | High | Open |
| C-007 | Server-side half is out of scope | Rejecting events whose project is not bound to the authenticated teamspace is `spec-kitty-saas#585`. **Exception:** FR-014 is a genuine directed dependency from that mission into this one and is in scope here. | Technical | High | Open |

### Key Entities

- **Journal event row**: the durable record in `event_journal`. Gains additive, indexed
  `project_uuid`/`project_slug` as a derived projection; identity remains authoritative in the
  envelope.
- **Project consent record**: uuid-keyed consent (FR-013), backfilled from today's path-keyed
  `checkout_overrides`. Absence means deny.
- **Consent port**: the delivery-context abstraction the dispatcher consults. Pure data, no globals,
  mirroring `ReceiverGate`.
- **Selected universe**: the output of the project-filtered journal read. Post-mission invariant:
  every member belongs to a consented project.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Incident reproduction — 6 projects, 1 consented, the other 5 carrying **no consent
  record at all** — delivers events from exactly the consented project. Fails on `origin/main` at
  mission start.
- **SC-002**: Liveness — 2,000 non-consented events older than 10 consented events; one drain
  delivers all 10.
- **SC-003**: Each fail-closed path denies with no network request, each with its own test:
  unresolvable routing (FR-003), absent consent record (FR-002), unresolvable event identity
  (FR-011), multi-project batch (FR-004), empty selection (FR-005).
- **SC-004**: `sync doctor` on a contaminated store names every project present with count, oldest
  age and consent state, reconciled against the journal's retained count. Zero hand-written SQLite
  queries needed to answer "whose data is in here?".
- **SC-005**: The background-daemon drain satisfies NFR-001 on its own store, or the queue-backed
  drain is gone and a test asserts no code path constructs it.
- **SC-006**: `sync purge --project X` removes 100% of X's rows across journal and ledger and 0% of
  any other project's.
- **SC-007**: Backfill run twice over a 10k-row multi-project journal yields byte-identical column
  values and an unchanged row count.
- **SC-008**: A live two-project drain against **`spec-kitty-dev`** (never production, per
  `docs/production-safety-guardrails.md`) delivers only the consented project, verified server-side
  by grouping delivered events by `project_slug`. Evidence artefact: the captured query output. If
  `saas#585` FR-009's report command has shipped, use it; otherwise a read-only Django-shell
  aggregation is the sanctioned fallback.
- **SC-009**: A server rejection carrying the stable refusal reason is classified `failed_permanent`,
  counted in terminal-failure totals, and the drain makes forward progress past it (closes #3005 and
  unblocks `saas#585` FR-004).

## Absorbed: spec-kitty#3031's red pins (operator decision, 2026-07-29)

`origin/main` carries two deliberately-red P0 reproductions under the honest-red-P0 policy
(ADR 2026-07-17-1). **This mission absorbs them and they are its acceptance gate.** They are marked
`regression`, so the blocking `regression tests` CI job selects them; the marker comes off as each
goes green.

`tests/sync/test_sync_consent_default_deny.py` — five pins:

1. `test_unconfigured_checkout_does_not_consent_to_sync` — **contradicted this spec's earlier
   position.** An unconfigured checkout must resolve `effective_sync_enabled is False`. An earlier
   implementation attempt flipped this, measured 39 regressions across `tests/sync`, and reverted on
   capture-first grounds. The operator has now ruled: those 39 tests encode the defect, not a
   requirement — they are updated as part of the fix.
2. `test_unresolvable_routing_does_not_consent_to_sync` — satisfied by FR-003 (shipped, `de274f3f`).
3. `test_project_config_refusal_is_honoured` — **new to this mission.**
4. `test_project_config_refusal_outranks_env_override` — **new.** Project-local refusal beats the
   machine-global env var.
5. `test_machine_global_opt_in_does_not_leak_to_sibling_projects` — **new.** The sibling-leak case.

`tests/sync/test_sync_consent_capture_gap_3031.py` — Defect 3, ungated capture. See NFR-005 as amended.

### New requirement inherited from #3031

**FR-019 — consent lives in the project, not the machine.** Today the consent record sits in
machine-global `~/.spec-kitty/config.toml` keyed by `repo_slug`: invisible in the repo it governs,
unreviewable, not version-controlled, and keyed on a **mutable git remote**. Consent must be
expressible in the project's own `.kittify/config.yaml` and must outrank the machine-global record and
the env var (pins 3 and 4). This partially supersedes FR-013's uuid-keyed index — reconcile the two
before implementing either.

### FR-013 × FR-019 reconciliation (operator decision, 2026-07-29)

**Both, with project-local winning.** FR-019 supersedes FR-013 on *authority*, not on *existence*:

1. **`.kittify/config.yaml` in the project** — authoritative whenever the checkout is readable. A
   project-local **refusal outranks a project-local grant** (the many-to-one case: two checkouts of one
   `project_uuid` with opposite settings resolve to deny, per FR-013's stated conflict rule).
2. **Machine-global uuid-keyed index** — the drain's lookup, and it must exist. The dispatcher resolves
   consent for events carrying only a `project_uuid`, and it must still answer when the checkout has
   moved, been renamed or deleted. A project-local-only design cannot: reading
   `.kittify/config.yaml` requires the path (`routing.py:64`), so a relocated checkout would strand the
   operator's own history — the "consented checkout moved" edge case and US2 scenario 3's
   "consented but unresolvable" row.
3. **Env var** — never a grant on its own. `SPEC_KITTY_ENABLE_SAAS_SYNC` is machine-global arming, not
   per-project consent; pin 5 (`test_machine_global_opt_in_does_not_leak_to_sibling_projects`) is
   exactly this.
4. **Absence at every level → deny** (FR-002).

Consequences for WP05: two writers, **one** resolver. The precedence chain is encoded once in
`sync/consent.py` and never re-derived per call site — the same single-definition rule T011 applies to
identity resolution, for the same reason (a second copy is how the reporting surface and the drain come
to disagree). The machine-global index is a **cache with a stated staleness rule**, not a second source
of truth: when a checkout is readable and its file disagrees with the index, the file wins and the index
is corrected. FR-015's report must render which level answered, or an operator cannot tell a
project-local grant from a stale cached one.

## Folded dependencies

Both were characterised as "incidental" on #3030 and `saas#585`. Neither is:

- **#3004** — `sync doctor`/`sync status` derive queue truth independently of `target_authority`,
  giving false-green `Queue size 0` after `sync migrate`. FR-015 bolts a per-project breakdown onto
  exactly those commands; rendering it from the wrong store would reproduce the incident's
  fake-green. Prerequisite for US2.
- **#3005** — permanently-rejected events reported as `Terminal failures 0`. FR-014 closes it, and
  `saas#585` FR-004 cannot work without it.

`#2995` / PR `#2998` are closed and merged as of 2026-07-27; no longer dependencies.
