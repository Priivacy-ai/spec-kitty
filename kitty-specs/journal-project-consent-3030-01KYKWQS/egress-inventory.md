# Egress inventory — spec-kitty CLI

Produced 2026-07-30 by a dedicated sink-first enumeration, after five egress paths had been
found one at a time by five separate reviews. This file is the artefact the spec lacked.

**Method**: enumerate every network/transmit primitive in `src/` (`httpx`, `requests`,
`urllib.request`, `http.client`, `websockets`, `socket`, transmitting `subprocess`), then trace
each **backwards** to its reachable callers. The five known paths were deliberately *not* used
as the starting point.

**The defining test**: an egress path is any code causing project data to leave the machine.
The bug class is *the path reaches a consent answer through something other than the data's own
`project_uuid`*. Note this is **not** "the code uses cwd" — `cli/commands/sync.py:1107,1204`
read cwd with no argument and are **correct**, being human-invoked commands whose subject
genuinely is the current checkout.

**Structural headline**: the consent chain has consumers in exactly three packages — `sync/`,
`delivery/`, and `invocation/` (the last only as of FR-025). Zero hits in `tracker/`,
`saas_client/`, `sync/history_import/`, `widen/`, `doctrine/`, `compat/`, `distribution/`,
`dashboard/`. Two of those carry mission slugs and verbatim dossier text.

## Inventory — ungated and proxy-gated first

| # | Sink | Reachable via | Verdict | Carries |
|---|---|---|---|---|
| **E1** | `sync/history_import/upload.py:290` → `receivers.deliver` → `requests.post` | `sync import-history --apply` (`cli/commands/sync.py:2390`) | **UNGATED** — zero consent hits in the whole package. Its only gate is the `GateKind` set that this spec's own root-cause §1 states has **no consent field**. Single-project by construction, so it **holds the uuid and never asks it**. | full synthesized mission history: `mission_slug`, `project_slug`, envelope payloads |
| **E2** | `tracker/saas_client.py:301` → `httpx` (10 endpoints; `push`/`run`/`bind_mission_origin` are POSTs) | `sync push`/`run`/`pull`, `mission_type.py:309`, **and non-interactively during mission creation** via `core/mission_creation.py:617` → `origin_consumer.py:55` → `bind_mission_origin` | **CLOSED 2026-07-30 (`bc5332a979`, FR-029).** Gate at `_request` — the chokepoint all 12 endpoints and the operation poller share — placed **before the token fetch**. Refuses with `TrackerEgressRefusedError`, subclassed so mission creation reports it through an existing channel and the mission is still created locally. Reached through `invocation.adapters.resolve_egress_consent`, the same registry slot the drain, emitter, daemon and `local_commit` use; layering did **not** force that choice (both packages are on the INTEGRATION side and may import `sync` directly) — it was taken on C-003 grounds, to avoid writing the derivation a third time. **Open point:** resolves from `self._project_root`, a proxy, sound only under an unwritten locality argument — routed back for the precondition. | `mission_slug`, `project_slug`, `mission_id`, external issue `title`, `items[]` |
| **E3** | `saas_client/client.py:146` `_post` / `:127` `_get` → `httpx` | `decision.py:558`, `charter/interview.py:216`, `plan/{plan,specify}_interview.py:150`, `widen/*` | **CLOSED 2026-07-30 (`bc5332a979`, FR-030).** `_refuse_unless_project_consents()` in both `_get` and `_post`, **before the URL is built**, since four of five endpoints carry `mission_id` in the path. `health_probe` gated with **no carve-out** — an exemption parameter was rejected because "a bypass switch on a chokepoint is what the next endpoint author will find". Same open locality point as E2. | `mission_id`/slug, `decision_id` |
| **E4** | `sync/body_upload.py:150` — the **enqueue** gate | `dossier_pipeline.py:274` ← 6+ agent commands (`mission_finalize`, `tasks_mark_status`, `research`, `mission_record_analysis`, `mission_setup_plan`, `backfill_identity`) | **PROXY-GATED and FAIL-OPEN — two defects in one line.** (a) when `locate_project_root` returns `None` the gate is **skipped entirely** (undetermined → proceed, FR-003 verbatim); (b) it uses the **routing** chain, not the consent chain — and `sync/__init__.py:348-352` records exactly why that is wrong ("also honours the repo-slug-keyed `[sync.repo_defaults]` record, which FR-019 condemns"). Two sites on one path using two different chains = C-003 divergence. Not itself a leak (E10 gates the send) but **the only fail-open gate found on a live-sender path**. | verbatim `spec.md` / `plan.md` / `tasks/WP*.md` text |
| **E5** | `dossier_pipeline.py:232` (the gate above E4) | as E4; also `sync/__init__.py:320` via `register_dossier_sync_handler` | **PROXY-GATED** on `is_saas_sync_enabled()` — machine-global arming, which this spec states is never a grant and which is the incident's own mechanism. Identity resolves from `repo_root`, so no cross-project reach; the proxy is the arming flag. | as E4 |
| **E6** | `invocation/propagator.py:219` → `client.send_event` (**FR-025**) | `dispatch.py:46`, `doctor/ops.py:150` | **Fix correct in shape; severity overstated.** `resolve_egress_consent` is now a 4-member enum where `NO_RESOLVER`/`UNANSWERABLE`/non-bool all refuse. **But the sender is dead in production** — its only client source is `getattr(token_manager, "_ws_client", None)` and `src/` has **zero writers**. The "measured leaking" result must have injected a client. Land as defence-in-depth; do not call it Critical. `repo_root` is safe here only by a **locality argument nowhere written down** (both construction sites pass the invoking checkout) — same argument WP08 made for `pending_local_commits`. | `request_text` (verbatim agent prompt) |
| **E7** | `sync/runtime.py:465` `publish_event` (**FR-026**) | `daemon.py:490` `POST /api/sync/publish`; `events.py:171` relay | **Fix correct** — `event_project_consents_to_publish` resolves the **event's own** uuid, fails closed, gates before every side effect including `start()`. Own-uuid. | any envelope; `project_slug`, `mission_slug` |
| **E8** | `sync/events.py:188` → `urlopen` loopback into E7 | 11 `emit_*` wrappers + `sync/__init__.py:299` `MissionCreated` fan-out | **Fix correct** — same seam, before crossing the loopback socket | as E7 |
| **E9** | `delivery/dispatcher.py:283` → `receivers.py:298` `requests.post` | `sync now` | **Own uuid** — consent pushed into SQL by `select_consented_event_ids`; `_cross_project_refusal` is the second fence | journal events |
| **E10** | `sync/body_transport.py:60` `requests.post` | `background.py:738` `_drain_body_queue` | **Own uuid, per task** — exclusion pushed *into* the read so refused rows cannot starve the window | dossier bodies |
| **E11** | `sync/emitter.py:2503,2508` — **the live WS sender** (`runtime.py:329,339` assigns the real client) | `_route_event` ← `_emit` | **Own uuid** (M1-1) | any envelope |
| **E12** | `sync/local_commit.py:338` `flush_pending_local_commits` | `sync/client.py:187` **connect-time flush** — client passed as a parameter, which is why this one is live | **Own uuid, per frame** | commit frames, `changed_files` |
| **E13** | `sync/sharing_client.py` `httpx` (4 endpoints) | `cli/commands/sync.py:1743…1972` | **Own uuid** — every call passes `source_project_uuid` explicitly | `project_uuid`, `team_slug` |
| **E14** | `sync/client.py:414` pong | `_listen` heartbeat | **Own uuid by construction** — client built per project | `build_id` |
| **E15** | `sync/batch.py:1125` `requests.post` | `batch_sync` ← `sync_all_queued_events` ← **nothing** | **Not reachable**, re-verified in this tree. Both live `drain_queue` readers are read-only. `_is_checkout_sync_enabled_for_batch:338` inert with it. | — |
| **E16** | `sync/local_commit.py:703` immediate send | `_get_saas_client()` → phantom `_ws_client` | **Not reachable** | — |
| **E17** | `status/adapters.py:301` `fire_resolved_binding_fanout` | fired at `status/emit.py:1065`; **zero handlers registered in `src/`** | **Not reachable — a pre-declared empty seam.** Docstring: "The sync package registers the handler … once the events package ships it." A firing site exists; the sink does not yet. Also `reset_handlers()` does not clear `_resolved_binding_handlers`. | `wp_id`, `mission_slug` |
| **E18** | auth flows, `core/upgrade_probe`, `compat/provider`, `distribution/simple_index`, `doctrine/sources/*`, `saas/readiness:204`, loopback control endpoints in `dashboard/`, `daemon.py`, `orphan_sweep.py` | | **Not project egress** — verified individually, not assumed | — |
| **E19** | `git push origin <branch>` — `merge/executor.py:1233`, `orchestrator_api/commands.py:584` | `if run.push and has_remote(...)` | **Out of boundary by design**, recorded so the boundary is explicit: the project's own commits to the project's own `origin`, opt-in, not the spec-kitty SaaS. Meets the literal test; excluded on the same operator-intent ground as `sync.py:1107,1204`. | project source |

## Why five paths needed five discoveries

**A category error in the artefact, not a vigilance failure.** The dossier's unit of reasoning is
**the store** — "the journal", "the queue", "the body queue" — so the search space was "places
that read a store". But egress is a property of **senders**, and the two sets do not coincide:
E2 and E3 touch no spec-kitty store at all, E1 builds its own universe by scanning the
filesystem, and E6/E16 read a store but have no live sender. Every path reachable by
store-reasoning was found; every path outside it was missed. Confirmed by dossier grep —
`import-history`/`history_import`, `saas_client`/`SaaSTrackerClient` and `dossier_pipeline` each
appear in **zero** dossier files.

**Three things make it structural:**

1. **There is no chokepoint.** Two independent universes feed the *same* HTTP sink:
   `dispatcher.py:283` (gated in SQL) and `history_import/upload.py:290` (ungated).
   `DeliveryReceiver` is the shared object and is exactly where a consent answer could have been
   made unbypassable — instead consent lives one layer *above* it, in a selection function only
   one of the two callers uses.

2. **FR-001's retirement has a scope error, and this is the most decision-relevant finding.**
   FR-001 was retired on the ground that "the machine-level half already ships, in a better form
   — `_cross_project_refusal` does at exactly the position a gate would occupy". True **for the
   dispatcher**. `import-history` shares the `GateContext` but **not** the dispatcher, so it
   inherited the retirement without inheriting the replacement. A correct decision, recorded in
   this mission, left a path with nothing.

3. **The existing guard is name-shaped**, re-confirmed: `RETIRED_DRAIN_NAMES` is two literal
   strings matched via `ast.ImportFrom`/`ast.Call`. It cannot see E1, E2, E3 or any future sender.

## Recommendation — reuse an idiom this repo already has

`tests/architectural/test_auth_transport_singleton.py` already does the right thing for a
different concern: AST-scans `src/` for `httpx.Client(...)`, permits only an explicit
`_TRANSPORT_ALLOWLIST`, asserts the allowlist has **no stale entries**, and carries a
**negative control**. Clone it as `tests/architectural/test_egress_consent_boundary.py`:

- **Scan for sinks, not names**: `requests.{post,put,patch}`, `httpx` `.post/.put/.request`,
  `urllib.request.urlopen` with a non-loopback URL, `.send_event(`, `ws.send(`.
- **Allowlist by file, each entry annotated with the consent seam that covers it** — E9 →
  `select_consented_event_ids`, E10 → `_consenting_body_project_uuids`, E11/E12 →
  `_project_consents_to_capture`/`_frame_project_consents`, E6 → `resolve_egress_consent`,
  E7/E8 → `event_project_consents_to_publish`, E13 → explicit `source_project_uuid`, E18 → not
  project data.
- **A new sender in an unlisted file fails the build**, with a message naming the seam it must
  call. This catches the `drain_queue` → `urlopen` shape that `RETIRED_DRAIN_NAMES` was probed to
  **miss**, because it keys on the *sink*, which that shape cannot avoid having.
- **Copy both meta-tests verbatim.** The stale-entry test stops the allowlist rotting into the
  `RETIRED_DRAIN_NAMES` failure mode; the negative control stops the guard becoming decoration —
  this mission's own documented worst failure shape.

**The stronger form**: make the sink unconstructable without an answer. `DeliveryReceiver.deliver()`
takes `Sequence[Envelope]`; have it take a `ConsentedBatch`, a frozen type whose only constructor
requires a `ConsentDecision` per `project_uuid`. Then E1 **cannot compile** without checking. Cheap,
because `select_consented_event_ids` already computes exactly that value. The guard makes a new
sender a **red build**; the type makes it a **type error at the point of writing**.

## Completeness limits — stated, because a claim that names its gaps is the only defensible kind

What is claimed: **every statically reachable network sink in `src/` is in the table above**, each
with a traced caller chain rather than a grep hit. What is **not** claimed: closure under dynamic
dispatch, future registry registration, or at-rest pooling.

1. **`getattr`-by-string reaching a sender.** 433 string-literal `getattr` calls in `src/`;
   filtered to sender-ish names gives 3 hits (2 phantom, 1 counter). A sender reached via a
   differently named attribute, or via `__getattr__` (`compat/provider.py:275` has one), is
   invisible to this method. Same blind spot the tracer records for the AST dead-symbol gate —
   and it cuts both ways: it made two paths look live that are dead.
2. **Empty callback registries — and one was found.** E17 has a firing site and zero handlers.
   **A sink that does not exist yet cannot be found by scanning for sinks.** This is the hard
   limit of sink-first and the strongest argument for the guard over any audit.
3. **Reachability asserted from grep and reading, not execution.** E15's "no production caller"
   and E6/E16's "no writer" are static results over one tree state. Grep proves presence, not
   reachability — and equally does not prove *absence* under `importlib`, entry-point plugins or
   `exec`, which were not audited.
4. **The tree was mid-edit**: three agents were editing 9 files during the read. **E6's severity
   claim rests on `_ws_client` having no writer right now — if in-flight work wires it, Critical
   is the correct label after all. Re-check before any PR body claims anything.**
5. **`subprocess` that transmits**: scanned for `push|gh|curl|scp|rsync|clone|fetch`. A helper
   invoked through a variable command name would be missed.
6. **Non-HTTP egress**: no `smtplib`, `ftplib`, `paramiko` or DNS primitive is imported in `src/`
   (verified). Raw `socket` appears 10 times, all port-probing/hostname; import sites read but
   data flow not exhaustively traced.
7. **At-rest pooling, scoped out deliberately** as C-006's recorded collection surface. No
   complete inventory of `~/.spec-kitty/` write sites was produced. If wanted, that is a separate
   pass — `_lifecycle_saas_fanout_handler` (`sync/__init__.py:277`) is the thread to pull, since
   it writes full envelopes to `OfflineQueue()` gated only by `is_saas_sync_enabled()` + scope.

**Closing judgement from the enumerator**: spend remaining budget on the guard and the
`ConsentedBatch` type rather than on more enumeration. Enumeration is what has been tried five
times.


## Status update — 2026-07-30, after the fold-in decision

The operator folded **FR-028 … FR-032** into this mission and chose "guard and type first, then the
paths". Current state of everything this file listed as ungated or proxy-gated:

| Path | Then | Now |
|---|---|---|
| **E1** / FR-028 `import-history` | UNGATED | Closing via the **`ConsentedBatch`** type — `deliver()` will accept only a batch that cannot be constructed without a consent decision, so the sink is unforgeable rather than merely reviewed. In flight. |
| **E2** / FR-029 tracker client | UNGATED | **Closed** (`bc5332a979`) |
| **E3** / FR-030 widen client | UNGATED | **Closed** (`bc5332a979`) |
| **E4** / FR-031 body-upload enqueue | PROXY-GATED, fail-open | In flight. Note the guard **correctly declined to list this file**: it holds no transmit primitive, and an entry a guard can never clear by its own evidence is a standing false accusation rather than a work-list. |
| **E6/E16** / FR-032 phantom `_ws_client` | UNREACHABLE | Dead readers being removed, so the one-line "fix" that would activate three paths at once cannot be made by accident. In flight. |

**The boundary guard is built and green** (`72fbc1fb94`,
`tests/architectural/test_egress_consent_boundary.py`): 58 sink sites across 27 files, a closed
reason vocabulary so "no seam needed" cannot become an escape hatch, `_KNOWN_UNGATED` asserted
**empty** and ratcheted at 0, and the allowlist itself ratcheted at 27 — because the allowlist,
not the work-list, is the surface someone would edit to silence the gate. Blinding evidence:
emptying the allowlist reds all 58 sites; removing any one of the 12 `SEAM` allowances reds its own
file, **0 of 12 inert**.

Two properties of the guard worth knowing when reading a future red:

- **Its green depends on the seams staying alive.** `test_seam_allowances_name_a_live_seam` already
  caught `select_consented_event_ids` being renamed mid-session, which is why E9 is now anchored on
  `consented_batch` — the construction the receiver will not accept a batch without.
- **E17 stays invisible to it until someone registers a handler**, at which point it reds. That is
  intended, and it is documented as a stated limit rather than implied away — a sink that does not
  exist yet cannot be found by scanning for sinks.


## E1 closed — and the enumeration had missed a sink on that very path

**FR-028 is closed by the `ConsentedBatch` type** (`2bdc793277`), not by a local gate — and the
type immediately earned its keep.

**This inventory named one sink on the import path (`upload.py:290`). There are two.**
`run_server_preflight` POSTs the **full envelope stream** before the delivery call ever runs. In
the implementer's words: *"A gate at the delivery call alone would have leaked every envelope
while looking closed."*

That is the sharpest available argument for the structural approach over another local fix, and it
arrived from the method rather than from more looking: `_consented_batches()` runs **before** the
preflight, and the batches it returns are the only thing `deliver()` will accept, so a caller who
skips it has nothing to hand the receiver. A gate placed where this document pointed would have
been a correct-looking fix over a live leak — the sixth time on this mission that a reported
instance turned out to be a sample.

It also records a limit of **this file's own method**: sink-first enumeration finds sinks, and it
found `receivers.post`; it did not notice that a *second* caller reached the same package by a
different route. Tracing a sink backwards to its callers is not the same as tracing a *path*
forwards through every request it makes.

**How the type is unforgeable**, four mechanisms, each pinned: a module-private mint witness
compared by identity; **the witness burned in `__post_init__`** — the hole a plain sentinel leaves,
since `dataclasses.replace` copies field values and a live witness would let a cleared batch's
events be swapped for another project's; `__init_subclass__` refusing subclassing, or one
overridden `__post_init__` defeats the receivers' `isinstance`; and **runtime enforcement rather
than only mypy**, because an annotation is advice and this incident already defeated review.

Explicitly **not** claimed, and stated in the module docstring: immunity to `object.__new__` +
`object.__setattr__`, or to a caller passing a fabricated `consent_predicate`.

Consent is keyed on **each envelope's own `project_uuid`** — not on `plan.identity.project_uuid`,
not on a root. `checkout_root` is offered only as a level-1 lookup aid, and
`consent._project_local_votes` discards any root whose declared uuid differs, so a wrong root can
only be ignored (→ machine index → deny) or contribute a fault (→ deny). The precondition and its
two falsifiers are written into `_consent_answer`'s docstring.

`_cross_project_refusal` is kept and is now **provably non-redundant**: a `ConsentedBatch` proves
every event's project consents, which does not mean they are the *same* project.

## E2/E3's locality question, answered — and it was not a locality argument

All **7** construction sites enumerated by a live scan (3/3 tracker, 4/4 widen):

| Site | Root from | Owner = root? |
|---|---|---|
| `origin.py:265` `bind_mission_origin` | `_resolve_repo_root(feature_dir)` | **Derived from the data** |
| `saas_service.py:109` | `require_repo_root()` → cwd | Benign locality |
| `origin.py:165` `search_origin_candidates` | caller | No production caller |
| 3 × interview sites | interview's `repo_root` | Derived — data read back from the same root |
| `decision.py:558` `decision widen` | cwd | **Can diverge; bounded** |

**The non-interactive creation path — the one that made FR-029 the worst open path — turns out
not to rest on locality at all.** `_resolve_repo_root` walks *up* from the directory whose
`meta.json` supplies the `mission_id`/`mission_slug` being sent, so the loop closes:
`mission_creation.py:374` builds `feature_dir = resolved_root/kitty-specs/<slug>`, `:588` passes
both, `origin_consumer` reads the issue `title` from `resolved_root/.kittify/pending-origin.yaml`,
and walking back up returns `resolved_root`. Every payload field originates under the root the
client is attributed to — **including** when `create_mission_core` is handed an explicit
`repo_root` differing from cwd, because dossier, meta and pending-origin all live under *that*
root. A cwd/owner divergence cannot arise there.

**The weakest site is `decision widen`**: cwd-derived root, operator-supplied `decision_id`.
Bounded rather than removed — the body carries only `invited_user_ids` and the id is a **ULID, not
a slug**, so no engagement name crosses even when root and owner diverge. **Precondition: if that
endpoint ever accepts a slug, the entry stops being benign.**

**The precondition was made executable rather than left as prose.** Each package carries a guard
that scans `src/` and reds on an unattributed construction site, naming file and line — proven to
bite in both directions (removing the attribution at `saas_service.py` and `decision.py` reds with
the intended message; restoring returns green), each with its own non-vacuity assertion so a
zero-site scan fails rather than passes.

## E20 — operator-configured tracker connectors (open collection surface, C-006)

`tracker/local_service.py` sends project data (issue titles, items) to Jira/Linear. Initially
called settled by the E19 `git push` analogy; that judgement was **revised on inspection**, and the
split is the answer:

- **The credential is the machine's** — `~/.spec-kitty/credentials`, keyed *by provider*, shared by
  every project on the machine. Structurally the same shape as `SPEC_KITTY_ENABLE_SAAS_SYNC`:
  arming, authorizing nothing about a specific project.
- **The binding is the project's own recorded decision** — `.kittify/config.yaml`'s `tracker:`
  block, verified git-tracked and not ignored, so it is committed, version-controlled, reviewable
  in a diff and travels with the repo. Those are exactly the properties **FR-019 demands**, and
  materially unlike the incident's mechanism.

So it is **not merely the machine's** — but it is **not this mission's consent either**:

- The binding is keyed on nothing. No `project_uuid`, no machine index, no
  `consented_project_uuids`, and **no way for a project to record a refusal** of tracker egress.
- FR-013's "deny if any checkout of the project is opted out" has no analogue.
- Most tellingly: **a project with a committed `sync.enabled: false` — an explicit refusal — can
  still push its issue titles to Jira.** The two answers are reconciled nowhere.

The half of the E19 analogy that survives: operator-invoked only, from `cli/commands/tracker.py`,
no daemon path. The half that does not: `git push origin` is opt-in per invocation to the
project's **own** remote, whereas this routes project data to a **third party** under a
machine-wide credential with **no per-project refusal available**.

**Recorded as an open collection surface under C-006**, not as a leak and not as settled:
*operator-configured tracker connectors — project-scoped destination binding, machine-scoped
credential, no expressible refusal.*
