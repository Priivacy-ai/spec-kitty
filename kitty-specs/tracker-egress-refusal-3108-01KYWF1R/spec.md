# Mission Specification: Tracker Egress Refusal

**Mission Branch**: `bundle-c-tracker-refusal-3108`
**Created**: 2026-07-31
**Status**: Draft
**Input**: `Priivacy-ai/spec-kitty#3108` — "tracker connectors have no expressible per-project
refusal (E20 / C-006)". Authored against `bb2020fea` (upstream/main, 2026-07-31 08:52). Evidence
base: `tracer-evidence-base.md` in this dossier — **authoritative**; where this spec extends or
departs from it, the departure is marked. Squad findings and their decided resolutions:
`tracer-squad-findings.md` — this revision implements every resolution in its §2, §3 and §4, and
carries its §6 and §7 forward as constraints so they are not re-litigated.

## Problem

### The issue's premise is false at `bb2020fea`, and a reader who believes it will think this Mission built the wrong thing

Issue `#3108` and `kitty-specs/journal-project-consent-3030-01KYKWQS/egress-inventory.md:243-272`
(entry **E20**) both assert that `tracker/local_service.py` sends project data to Jira/Linear, and
that "a project with a committed `sync.enabled: false` — an explicit refusal — can still push its
issue titles to Jira."

**Both sentences are false.** Measured at `bb2020fea` with an isolated `HOME`, an HTTP trip-wire on
`httpx.Client.request`, and a positive control:

| project-local `.kittify/config.yaml` | `SaaSTrackerClient.push(provider="jira", …)` |
|---|---|
| no record (absence) | **REFUSED**, `error_code=project_consent_denied`, no HTTP attempted |
| `sync: {enabled: false}` | **REFUSED**, `error_code=project_consent_denied`, no HTTP attempted |
| `sync: {enabled: true}` | gate passed → failed later at `No valid access token` |

The third row is the positive control: without it, rows 1–2 are indistinguishable from a probe that
never reached the code.

The routing explains why. `tracker/factory.py:17` — `SUPPORTED_PROVIDERS = ("beads", "fp")`;
`build_connector` raises for anything else (`factory.py:38-39`). `tracker/service.py:77-80` routes
`SAAS_PROVIDERS` to `SaaSTrackerService` and `LOCAL_PROVIDERS` to `LocalTrackerService`.
**`LocalTrackerService` cannot construct a Jira or Linear connector.** Jira/Linear tracker egress
passes through `tracker/saas_client.py:329-331`, the gate `#3030` shipped for the tracker SaaS client (its tracker-client-is-a-seventh-egress-path
requirement, in `kitty-specs/journal-project-consent-3030-01KYKWQS/spec.md`), placed at
`_request` — the single chokepoint all thirteen endpoints and the operation poller cross, and placed
*before* `_fetch_access_token_sync()`:

```python
refusal = project_egress_refusal(self._project_root)
if refusal is not None:
    raise TrackerEgressRefusedError(refusal)
```

So "key tracker egress through the existing consent chain" is **not a proposal — it is the status
quo.** This Mission does not build it. This Mission closes the two gaps that are actually open, and
corrects the polarity error the first draft of this spec made about the second one.

### Where the SaaS tracker path actually sends — the finding that shapes the whole design

Verified at `bb2020fea`: `saas_client.py:247` resolves `_base_url` from
`resolve_runtime_target().resolved_server_url`, and every endpoint on the class is
`/api/v1/tracker/…` (`_STATUS_PATH`, `_MAPPINGS_PATH`, `_PULL_PATH`, `_PUSH_PATH`, `_RUN_PATH`,
`_OPERATIONS_PATH`), carrying a bearer token and `X-Team-Slug`.

**The SaaS tracker path does not talk to Jira. It talks to spec-kitty's hosted service**, which holds
the Jira/Linear connector and relays. That single fact is why this Mission's new key cannot have one
polarity: a grant recorded against a `jira` binding would ship engagement names **to spec-kitty's
SaaS** while hosted-sync consent is absent — reopening the exact boundary `#3030`'s P0 fix
established, to the exact destination the 2026-07-27 incident leaked to. The local path's destination
is a subprocess named by the operator's own credential file. Two destinations, two polarities. See
FR-004.

### The destination is a **parameter**, not something derivable from the config on disk

The polarity split above is only sound if "which destination is this?" is answered correctly.
Answering it by reading `load_tracker_config(root)` is **unsound at `bb2020fea`**.
`TrackerService._resolve_saas_backend_for_provider` (`service.py:84-98`) overrides the on-disk
config **in memory** when `--provider <saas>` is passed, and never rewrites the file. Measured, with
a positive and a negative control:

```
PRECONDITION on-disk provider : 'beads'
SUBJECT backend class         : SaaSTrackerService
SUBJECT in-memory cfg.provider: 'jira'
SUBJECT on-disk cfg.provider  : 'beads'   <-- what a config-reading verdict() would have seen
CONTROL (disk=jira) backend   : SaaSTrackerService
NEGATIVE CONTROL              : TrackerServiceError raised for 'beads' (the probe discriminates)
```

Three operator-reachable commands drive the **hosted** transport from a repository whose on-disk
provider is local, all of them with `allow_unbound=True`:

| Command | CLI site | Service site | Client site |
|---|---|---|---|
| `tracker list-tickets --provider jira` | `cli/commands/tracker.py:998-1007` | `service.py:220` | `saas_client.py:613` → `_request` |
| `tracker issue-search --provider jira` | `cli/commands/tracker.py:369-386` | `service.py:214` | → `_request` |
| `tracker map list --provider jira` | `cli/commands/tracker.py:942-963` | `service.py:210` | → `_request` |

So a verdict that derived its polarity from the on-disk provider would read `beads`, apply the
**local** half of the rule, and turn `tracker.egress: permitted` into an **affirmative grant to
spec-kitty's hosted service with Channel 1 absent** — reopening `#3030`'s P0 boundary through the
very key introduced to protect it, for exactly the operator US2 exists to serve.

**Therefore the destination is an explicit, required, keyword-only parameter of the join function**,
drawn from a closed two-member set (`LOCAL_SUBPROCESS`, `HOSTED_SERVICE`), and every call site passes
a **literal** member. This is the load-bearing structural change in this revision, and it is worth
stating plainly: *polarity follows the destination* stops being a rule a reader has to remember and
becomes a property **`mypy` checks and a guard pins**. `saas_client._request` is structurally
incapable of asking about anything but the hosted destination; `local_service`'s three methods are
structurally incapable of asking about anything but the local one; and no call site is permitted to
compute the answer from a config read at all. See FR-004 and FR-015 G5.

### Gap A — no separability

One key, `sync.enabled`, answers two different questions:

- *may my events go to spec-kitty's hosted SaaS?*
- *may my issue titles go to **the operator's own** tracker binary?*

A project cannot permit one and refuse the other. `#3030` never separated them because it was
closing a hosted-sync leak. This is the genuine C-006 shape.

### Gap B — the `beads`/`fp` path is ungated entirely

`src/specify_cli/tracker/local_service.py` holds **zero** consent references. Verified by per-file
count across all sixteen files in `src/specify_cli/tracker/` matching
`egress_consent|project_egress_refusal`: `egress_consent.py` 6, `saas_client.py` 3 (two matches on
the import line `:34`, one call at `:329`), **`local_service.py` 0**, the other thirteen 0.

The path, traced end to end:

```
cli/commands/tracker.py:1022,1074,1163   (@sync_app.command — operator entry)
 └─ _service()                            tracker.py:335
     └─ TrackerService.sync_*             service.py:193-200
         └─ _resolve_backend()            service.py:76   ← only production reach
             └─ LocalTrackerService.sync_pull/push/run    local_service.py:115,130,140
                 └─ _load_runtime()                       local_service.py:116,131,141
                 └─ _build_engine(...)                    local_service.py:217 (inside the coroutine)
                     └─ build_connector(...)              local_service.py:225 → factory.py:32
                         └─ BeadsConnector / FPConnector
                             └─ SubprocessCommandRunner.run
                                 └─ subprocess.run(list(command))
                                     spec_kitty_tracker/connectors/cli_runner.py:22
```

What crosses is issue `title`, `body`, `labels`, `assignees` and `workspace`, as **argv** of an
operator-named executable whose name comes from the **machine-global** credential file
(`factory.py:56` — `command=str(credentials.get("command") or "bd")`). Consent functions consulted
on that path: **zero**. A committed `sync.enabled: false` does not stop it.

This is no longer inferred. The post-specify squad installed a real fake `bd` on disk, named it
through the machine-global credential file, and drove the real `LocalTrackerService` with nothing in
the production path patched:

```
CASE committed sync.enabled=false / doctrine=spec_kitty_authoritative / op=sync_push
  argv captured : 2
     ['…/fake-bd', '--json', 'list']
     ['…/fake-bd', '--json', 'create', 'ACME Holdings carve-out', '--type', 'task',
      '--priority', '2', '--description', 'confidential body',
      '--assignee', 'alice@acme.example', '--label', 'secret-label']
  SENTINEL in argv: True     http attempts: 0
```

Its only current gate is *arming*: `cli/commands/tracker.py:354-366` gates the whole tracker CLI
group on `is_saas_sync_enabled()` — `SPEC_KITTY_ENABLE_SAAS_SYNC`, which this spec lineage calls
arming and never a grant, and which was the 2026-07-27 incident's own mechanism. Worse,
`_check_sync_readiness` (`tracker.py:296-312`) **short-circuits entirely** for local bindings via
`_is_local_binding()` (`:280-293`), skipping readiness *and* daemon policy.

Measured consequence, and it is why FR-018 exists: with the group un-armed the command aborts before
anything is built, so a refusal assertion that only checks a non-zero exit code is **already green at
`bb2020fea` with no gate present**.

```
SPEC_KITTY_ENABLE_SAAS_SYNC=None  -> exit 1, subprocess.run 0, http 0
   'Hosted SaaS sync is not enabled on this machine. Set `SPEC_KITTY_ENABLE_SAAS_SYNC=1` to opt in.'
SPEC_KITTY_ENABLE_SAAS_SYNC='1'   -> exit 1, subprocess.run 1
```

### It is a `subprocess` surface, not an HTTP one

AST-scanned with the egress guard's own scanner, with a positive control and a printed input count
(a gate that ran on zero files passes vacuously):

```
CONTROL saas_client.py sinks = 8   (expected >0 — it is allowlisted as SEAM)
SUBJECT local_service.py sinks = 0
INPUT COUNT: 1198 .py files scanned under src/; 72 sink sites in 28 files
```

Three consequences, all load-bearing on scope: `local_service.py` is not in `_EGRESS_ALLOWLIST` and
**cannot be added** (`tests/architectural/test_egress_consent_boundary.py::test_every_listed_file_still_holds_a_sink`,
`:792-805`, deletes entries that guard nothing); therefore the allowlist collision this Mission was
warned about does not arise, and no `_baselines.yaml` bump (`egress_allowlist_files: 28`) is needed;
and `#3113`'s all-positional evasion is irrelevant here, because there is no transport call for the
guard to match — the guard's own Limit 4 scopes `subprocess` out by design.

### The model this Mission specifies

Tracker egress is decided by **two channels and one destination, joined in exactly one named
function**, whose verdict is both enforced by the gates and reported by `sync doctor`.

- **Channel 1 (existing, unchanged):** `resolve_egress_consent(repo_root)` reached through
  `project_egress_refusal` — the hosted-sync consent chain, keyed on `project_uuid`. **Absence
  denies.**
- **Channel 2 (new):** `tracker.egress`, a tracker-scoped key in the project's own committed
  `.kittify/config.yaml`, holding one of a **closed set of two strings — `refused` or `permitted`** —
  resolved by its own function and applied to **both** transports. **Absence is the key being
  missing**, and has its own spelling rather than sharing one with a recorded value.
- **The destination (new, and required):** a keyword-only argument of the join function, drawn from a
  closed two-member set — `LOCAL_SUBPROCESS` (an operator-named executable) and `HOSTED_SERVICE`
  (spec-kitty's own `/api/v1/tracker/…` endpoints). It is **never derived from a config read**; each
  call site passes a literal.
  - `refused` refuses at **both** destinations.
  - `permitted` at `LOCAL_SUBPROCESS` is an affirmative tracker grant that satisfies the path
    **independently of Channel 1**. At `HOSTED_SERVICE` it is a **no-op**: it grants nothing, must be
    *reported* as a no-op, and Channel 1 remains a hard prerequisite.
  - Anything else present at the key — an unknown string, a wrong type, an empty string, a `null`, a
    mapping, a list — is a **fault, and a fault refuses** at both destinations (FR-006, C-020).
- **Absence of both channels still denies** (FR-007).

## User Scenarios & Testing *(mandatory)*

Every acceptance scenario below is subject to the harness contract in **FR-018**, which is a
requirement and not a fixture preference: `SPEC_KITTY_ENABLE_SAAS_SYNC=1` set explicitly,
`doctrine: {mode: spec_kitty_authoritative}` pinned, **the tracker store seeded with the sentinel
issue before the command runs**, the recorder installed as a real executable on disk named through
the credential file, `_build_engine` / `build_connector` / `SyncEngine` **un-patched**, and the
gate's bind counter asserted non-zero. A scenario that satisfies its assertion without those is not
evidence of anything: all four have been *measured* to produce a passing refusal test on a tree with
no gate in it.

### User Story 1 - A project refuses tracker egress without refusing hosted sync (Priority: P1)

An operator who has opted a project into hosted sync — because the Mission dashboard, status
propagation and journal delivery all depend on it — records one key in that project's own
`.kittify/config.yaml` and its issue titles stop reaching the tracker binary, while hosted sync keeps
delivering.

**Why this priority**: This is the C-006 shape the issue is actually about. It is the only half a
consenting project can observe, and it is independently shippable: it needs no change to Channel 1.

**Independent Test**: One project, Channel 1 granted throughout, bound to `beads`, **with the tracker
store seeded** with one issue whose title is a distinctive sentinel (FR-018 H8 — an empty store never
reaches `create_issue`, measured). A fake executable on disk, named through the credential file,
appends every argv it receives to a file. With the tracker refusal recorded: zero argv captured and
the sentinel appears in no captured element. Without it: **three** argv captured — `list`, `create`,
`show` — and the sentinel appears verbatim as an argv element of the `create`. Both runs use the same
recorder in the same test file and differ by exactly one committed config line.

**Acceptance Scenarios**:

1. **Given** a project whose `.kittify/config.yaml` records `tracker: {egress: refused}`, whose
   hosted-sync consent is **granted**, and whose tracker store has been seeded with an issue titled
   `ACME Holdings carve-out`, **When** `spec-kitty tracker sync push` runs against its `beads`
   binding, **Then** the recorder captures **zero** argv, the string `ACME Holdings carve-out` appears
   in no captured element, **the tracker SQLite file at the resolved db path is byte-identical before
   and after** (NFR-002), and the command exits non-zero printing a refusal that names **Channel 2 —
   the tracker key** as the cause and quotes the key's path.
2. **Given** the same project with `tracker.egress` **absent** and hosted-sync consent
   granted, **When** the same command runs, **Then** the recorder captures **three** argv —
   `[<cmd>, "--json", "list"]`, `[<cmd>, "--json", "create", "ACME Holdings carve-out", …]`,
   `[<cmd>, "--json", "show", <id>]` — and `ACME Holdings carve-out` appears verbatim as an element of
   the second. *This scenario must pass. It is what makes scenario 1's absence assertion mean
   anything, and its argv count is asserted exactly, because a count of 1 would mean the store was
   never seeded and a count of 2 would mean `create_issue`'s trailing `get_issue`
   (`spec_kitty_tracker/connectors/beads.py:151-153`) did not run.*
3. **Given** the refusing project of scenario 1, **When** the refusal is printed, **Then** its text
   is **not** `saas_sync_disabled_message()` — the string beginning "Hosted SaaS sync is not enabled
   on this machine. Set" and naming `SPEC_KITTY_ENABLE_SAAS_SYNC=1` — and the assertion that matched
   in scenario 1 does not match that string. *Negative pin: without it, the arming abort satisfies
   scenario 1 with no gate built.*
4. **Given** a project that records `tracker: {egress: refused}` and whose hosted-sync consent is
   **granted**, **When** `spec-kitty sync now` drains a queue holding **N ≥ 1** events, **Then**
   exactly the same **N** events are delivered as in the paired fixture that is identical except that
   it records no tracker key, and the two deliveries are compared event-for-event. *Positive control
   on "hosted sync is unaffected": a drain that never ran satisfies the old wording.*

---

### User Story 2 - A project keeps its local tracker without granting hosted sync (Priority: P1)

An operator who will not opt a client repository into spec-kitty's hosted SaaS records
`tracker: {egress: permitted}` in that repository's own committed config and keeps a working
`beads` binding.

**Why this priority**: Without this half, closing Gap B converts every existing local binding into a
demand for hosted-sync consent — *"consent to spec-kitty's SaaS or lose your local tracker"*. The
operator decided against that coercion. It also dissolves the identity-less-checkout brick (US6
scenario 3) for local bindings, because Channel 2 reads the project's own file and needs no
`project_uuid`.

**Independent Test**: One project, **no** hosted-sync consent record at any level, `beads` binding,
**seeded** store holding the sentinel-titled issue, same recorder. With `egress: permitted`
committed: three argv captured and the sentinel appears verbatim. With the key removed: zero argv
captured. The two fixtures differ by exactly one committed line.

**Acceptance Scenarios**:

1. **Given** a project with **no** hosted-sync consent record at any level and a committed
   `tracker: {egress: permitted}`, **When** `spec-kitty tracker sync push` runs against a `beads`
   binding, **Then** the connector is constructed and the recorder captures argv containing the
   sentinel title verbatim. *This is Channel 2 granting independently of Channel 1.*
2. **Given** the same project with the tracker key removed, **When** the same command runs, **Then**
   zero argv is captured and the command refuses naming **Channel 1**. *The paired negative; the two
   differ by exactly one committed line.*
3. **Given** a project that commits `sync: {enabled: false}` — a recorded hosted-sync refusal — and also commits
   `tracker: {egress: permitted}`, **When** the same command runs, **Then** the connector is
   constructed. *A recorded hosted-sync refusal does not veto an explicit tracker grant on a local
   binding: the two questions are separable in both directions, which is what `#3108`'s C-006 shape names.*

---

### User Story 3 - The ungated local path refuses when neither channel permits (Priority: P1)

`beads` and `fp` bindings stop being the one tracker path that ships project data with no consent
question asked.

**Why this priority**: Gap B is the total absence of a gate on a live egress path — observed, not
inferred (see Problem). It is the half the issue got right, and it is the breaking half, so it ships
with its remediation (US6) rather than before it.

**Independent Test**: Two fixture projects sharing one recorder: one with no record at either
channel, one with a recorded hosted-sync grant. Same binding, same seeded issue, same command.
Assert the first captures zero argv and the second captures the title verbatim.

**Acceptance Scenarios**:

1. **Given** a project with **no** hosted-sync consent record at any level, **no** tracker key, and a
   **seeded** store, **When** `spec-kitty tracker sync push` runs against a `beads` binding, **Then**
   it refuses before `_load_runtime` is entered, exits non-zero, leaves the tracker SQLite file
   **byte-identical**, and the printed refusal carries the Channel-1 remedies for the "no record"
   state (FR-012) **and** the Channel-2 remedy (record `tracker.egress: permitted` in this project's
   own config).
2. **Given** a project with a committed `sync: {enabled: false}` and no tracker key, **When** the
   same command runs, **Then** it refuses, and the message says a hosted-sync **refusal is recorded**
   — distinct in wording from scenario 1's "no record was found" — and offers the remedy for that
   state.
3. **Given** a project whose hosted-sync consent is granted and which records no tracker key,
   **When** the same command runs, **Then** three argv reach the recorder and the sentinel appears
   verbatim. *Positive control; must pass.*
4. **Given** a second fixture pair that is identical to scenarios 1 and 3 except that the tracker
   store has **not** been seeded and **no tracker SQLite file exists at the resolved db path when the
   command starts**, **When** the same command runs, **Then** the refusing member creates **no** file
   at that path and captures **zero** argv, while the consenting member creates the file and captures
   exactly one argv, `[<cmd>, "--json", "list"]`. *This is where NFR-002's file-**existence** clause
   lives, and it is the pin that reds if the gate is later moved back to `_build_engine`
   (`TrackerSqliteStore.__init__` `mkdir`s and creates the file, `store.py:278-281`). The sentinel
   assertion is deliberately **not** made on this pair — an unseeded store never reaches
   `create_issue`, so no title crosses in either member, and asserting its absence here would
   establish nothing. The two members still differ by exactly one committed line.*

---

### User Story 4 - All three sync entry points are covered, not just push (Priority: P1)

`sync pull` and `sync run` are gated on the same verdict as `sync push`, at the same place.

**Why this priority**: A gate on push alone leaves `sync run` — pull-then-push in one command
(`spec_kitty_tracker/sync.py:158-160`) — half open, and leaves `pull` executing an operator-named
binary from a machine-global credential file inside the project's context with no consent question
asked. Covering three costs nothing extra once the gate is a named call; leaving two uncovered is
what costs.

> **Departure from the evidence base, §1 and §3.** An earlier draft of the evidence base stated that
> pull "ships a filter string outward (`beads.py:86-88`, `--title-contains`)". Measured at
> `bb2020fea`, that is a **capability, not a current behaviour**: `SyncEngine.pull` takes
> `filters: Mapping | None = None` (`spec_kitty_tracker/sync.py:53-68`) and
> `LocalTrackerService.sync_pull` calls `engine.pull(limit=limit)` (`local_service.py:124`) — no
> filters, so today's pull argv is `[<command>, "--json", "list"]` plus an optional
> `--updated-after <date>`. **No issue title crosses on pull today.** Pull is still gated, on three
> grounds: `sync run` shares the verdict, so gating push alone leaves run's pull half open; pull
> still executes an operator-named binary from a machine-global credential file inside the project's
> context; and the `filters` parameter exists, so a future caller passing it would ship titles
> outward with no new gate needed. Gating pull closes the class rather than an instance.
> Consequently **pull's refusal assertion is zero captured argv, never a title's absence** — asserting
> the absence of something that never happens establishes nothing (NFR-001).

**Independent Test**: Parametrise the refusal/control pair over `sync_pull`, `sync_push`, `sync_run`
and assert per entry point, each exercised end to end through the CLI.

**Acceptance Scenarios**:

1. **Given** a refusing project, **When** `spec-kitty tracker sync pull` runs, **Then** zero argv is
   captured and the command exits non-zero. **And** the consenting control for `pull` captures argv
   beginning `[<command>, "--json", "list"]`.
2. **Given** a refusing project, **When** `spec-kitty tracker sync run` runs, **Then** zero argv is
   captured — neither the pull half nor the push half reaches the runner.
3. **Given** a consenting project, **When** `sync run` runs, **Then** argv is captured for both
   halves and the push half carries the sentinel title. *Positive control; must pass.*

---

### User Story 5 - The tracker key narrows the hosted destination but never grants it (Priority: P1)

Whenever the transport is spec-kitty's hosted service, a committed `tracker: {egress: refused}`
refuses and a committed `tracker: {egress: permitted}` grants nothing — **including when the
project's on-disk provider is local and the hosted transport was selected by `--provider` at the
command line**.

**Why this priority**: The rejected first draft left the key inert on SaaS bindings while
`sync doctor` reported it as in force — a confidentiality control the operator was *shown
confirmation of* and that was *not enforced*: the incident's false-green with the sign flipped. And
`#3108` is framed entirely around Jira, so a SaaS binding is the first thing an operator will try. The
narrowing-only half is equally load-bearing: the destination is spec-kitty's hosted service (see
Problem), so a grant there would reopen `#3030`.

**Independent Test**: One project bound to `jira`, HTTP trip-wire on `httpx.Client.request`, four
cells: {Channel 1 granted, absent} × {`egress: refused`, `egress: permitted`}. Assert HTTP attempts
per cell. Plus the provider-override pair of scenario 4, which is the cell no config-derived
implementation can get right.

**Acceptance Scenarios**:

1. **Given** a `jira` binding, hosted-sync consent **granted**, and a committed
   `tracker: {egress: refused}`, **When** `spec-kitty tracker sync push` runs, **Then** it
   refuses with **0** HTTP attempts and the message names Channel 2.
2. **Given** a `jira` binding, hosted-sync consent **absent**, and a committed
   `tracker: {egress: permitted}`, **When** the same command runs, **Then** it still refuses with
   **0** HTTP attempts and the message names Channel 1 — *and additionally states that a tracker
   grant is recorded and does not apply to the hosted destination*, so the operator is not left
   believing the key did nothing.
3. **Given** a `jira` binding, hosted-sync consent **granted**, and no tracker key, **When** the same
   command runs, **Then** the gate passes and the call fails later at `No valid access token`.
   *Positive control; the shipped `#3030` behaviour, unchanged.*
4. **Given** a project whose **on-disk** `tracker.provider` is `beads`, which commits
   `tracker: {egress: permitted}`, and whose hosted-sync consent is **absent**, **When**
   `spec-kitty tracker list-tickets --provider jira` runs — which
   `_resolve_saas_backend_for_provider` (`service.py:84-98`) serves by overriding the provider **in
   memory** and routing to `SaaSTrackerClient._request` — **Then** it **refuses** with **0** HTTP
   attempts and the message names **Channel 1**, because `_request` passes `HOSTED_SERVICE` and at
   that destination `permitted` is a no-op. **And** the paired positive control — on-disk
   `provider: jira`, Channel 1 **granted**, **no** tracker key, same command — reaches
   `No valid access token`, so the zero-HTTP count in the refusing member is not vacuous. *This is
   the scenario that fails on any implementation deriving the destination from
   `load_tracker_config(root)`: that implementation reads `beads`, applies the local half, and
   **grants**.*

---

### User Story 6 - An upgrading operator is told why their working binding stopped, and how to restore it (Priority: P1)

**Why this priority**: Deny-on-absence of both channels means **every existing `beads`/`fp` binding
stops working on upgrade** unless its project records a decision at one of the two channels. This is
not a footnote to US3 — it is US3's cost, and a refusal an operator cannot act on is an outage. The
squad measured a state in which today's message tells the operator to do exactly what they just did.

**Independent Test**: Three refusing fixtures, one per Channel-1 state. For each: assert the printed
state wording, then **apply the offered remedy to that fixture, re-run the same command, and assert
the sentinel title now reaches the recorder**. Assert a CHANGELOG breaking-change entry and an
upgrade note at a pinned anchor.

**Acceptance Scenarios**:

1. **Given** a project with a resolvable project identity and **no** hosted-sync record, **When** any
   local tracker sync command runs, **Then** the refusal states that **no consent record was found**,
   names the project, and offers three remedies: record `sync.enabled: true` in the project's own
   `.kittify/config.yaml`, run `spec-kitty sync opt-in` for it, or record
   `tracker.egress: permitted` to grant the tracker path alone. **And** applying any one of the
   three to that fixture and re-running makes the sentinel title reach the recorder.
2. **Given** a project with a resolvable identity and a **recorded** hosted-sync refusal, **When** the
   same command runs, **Then** the refusal states that **a refusal is recorded** — wording distinct
   from scenario 1 — and its remedies are "change the recorded decision" or the Channel-2 grant.
   **And** applying either and re-running makes the title reach the recorder.
3. **Given** a checkout whose project identity does **not** resolve — no `project.uuid`, so
   `enable_checkout_sync` raises `ConsentIdentityUnresolvedError` (`routing.py:320-321`) and
   hand-authoring `sync.enabled: true` still denies — **When** the same command runs, **Then** the
   refusal states the project is **not consentable because no project identity resolved**, and its
   remedies are `spec-kitty init` (to mint an identity, after which scenario 1's remedies apply) or
   the Channel-2 grant, which needs no identity. **And** applying either and re-running makes the
   title reach the recorder. *Without this state the binding is permanently dead with actively wrong
   advice: today's message tells the operator to record a decision they have just recorded.*
4. **Given** the release notes, **When** an operator reads them, **Then** a Breaking Changes entry
   states that local tracker providers now require a recorded decision at one of the two channels,
   and links the upgrade note.
5. **Given** the upgrade note, **When** CI runs, **Then** an anchor check fails if the section is
   removed or renamed.

---

### User Story 7 - `sync doctor` says whether tracker egress is refused, and by which channel (Priority: P2)

**Why this priority**: `doctor` reported healthy throughout the 2026-07-27 incident. A refusal the
operator can only discover by running the command that fails is a diagnostic gap. `sync doctor` is
the right surface for a structural reason, not a preference: the `spec-kitty tracker` group is
**conditionally registered** (`cli/commands/__init__.py:238-243,300`) and does not exist unless
armed, while `sync` is registered unconditionally (`:298`) — a tracker-side surface would be
unreachable in exactly the configuration where an operator most needs it.

**Independent Test**: Run `sync doctor` in seven checkouts — tracker-key `refused`, a tracker-key
fault (a near-miss value, C-020), Channel-1 refusal, Channel-1 absent, not-consentable, tracker-key
`permitted`, fully permitted. Each checkout renders **one row per destination** — `LOCAL_SUBPROCESS`
and `HOSTED_SERVICE` — so assert **14** rows, the block printed in all seven checkouts, and each
row equal to the verdict the gate enforces **at that destination** for that checkout.

**One row per destination, not one row per binding.** The block does **not** consult the on-disk
provider to decide what to show. That is not a rendering preference: the provider on disk does not
determine the destination (see Problem — `--provider` overrides it in memory), so a
provider-conditional rendering would tell an operator with a `beads` binding that `permitted` is in
force while `list-tickets --provider jira` is refused, and tell an operator with a `jira` binding
nothing at all about the local half. Two rows are what the checkout actually has to say.

**Acceptance Scenarios**:

1. **Given** a checkout that records `tracker.egress: refused`, **When** `sync doctor` runs,
   **Then** a **new tracker-egress block** — not the consent-readability renderer — reports tracker
   egress refused **on both destination rows** and names Channel 2 as the refusing channel on each.
2. **Given** a checkout with hosted-sync consent absent and no tracker key, **When** `sync doctor`
   runs, **Then** both rows report tracker egress refused and name Channel 1, with the Channel-1
   state (no record / recorded refusal / not consentable) spelled out.
3. **Given** a checkout with hosted-sync consent absent and `tracker.egress: permitted`, **When**
   `sync doctor` runs, **Then** the `LOCAL_SUBPROCESS` row reports **permitted, by Channel 2**, and
   the `HOSTED_SERVICE` row reports **refused, by Channel 1**, and additionally states that the
   recorded tracker grant is a no-op at that destination. *"Tracker egress is fine" and "I never
   looked" must not render identically — that equivalence is the incident's false-green; neither may
   one destination's answer be printed as if it were both.*
4. **Given** any of the above checkouts and either destination, **When** `sync doctor` runs and the
   corresponding tracker command runs, **Then** the reported verdict and the enforced verdict are
   produced by the same function `tracker_egress_verdict(root, destination=…)` (FR-003) **with the
   same destination literal**, and are asserted equal field-for-field.
5. **Given** any of the above checkouts, **When** `sync doctor` runs, **Then** the string
   `This is NOT a missing consent record` does not appear in the new block, and
   `flat.count("REPAIR THE FILE'S SYNTAX")` in
   `tests/cli/commands/test_sync_doctor_consent_health_3030.py:366`'s scenario is still exactly `4`.

---

### Edge Cases

- **`tracker.egress` present and outside the closed set.** `Refused`, `REFUSED`, `refuse`, `deny`,
  `no`, `true`, `false`, `0`, `null`, an empty string, a mapping, a list. Every one is a **fault and
  refuses**, at both destinations (FR-006, C-020). There is no case-folding and no synonym table.
  **The decode must be `isinstance`-guarded before the membership test.** Measured: with `_LEGAL =
  frozenset({"refused", "permitted"})`, the expression `raw in _LEGAL` raises
  `TypeError: unhashable type: 'CommentedMap'` for a mapping and `TypeError: unhashable type:
  'CommentedSeq'` for a list — the two shapes this very list enumerates as fault values — from
  inside a function NFR-003 says must never raise. The decode is therefore
  `isinstance(raw, str) and raw in _LEGAL`, and a mapping and a list **at the key** are members of
  NFR-003's probed set, not only of this list.
- **A non-mapping `tracker:` block.** `tracker: "yes"`, `tracker: [a, b]`, `tracker: 3`, `tracker:`
  (null). `load_tracker_config` passes `None` to `from_dict` in every one of these cases
  (`config.py:151-152` — `tracker_data if isinstance(tracker_data, dict) else None`), and `from_dict`
  returns a default `cls()` (`config.py:105-106` region). So Channel 2 is **absent**, not a fault, and
  the verdict **defers to Channel 1**. Recorded rather than left to be invented: the natural guess is
  "a malformed block is a fault", and it is not — the block is not the key, and the key is missing.
- **A fault never grants.** A fault refuses at the local destination too, so it can never satisfy the
  grant. Otherwise a typo (`tracker: {egress: refuse}`, singular) would read as an unusable value
  today and as *something* the day someone widened the parser — and on a confidentiality control the
  only safe reading of a value nobody defined is refusal (C-020).
- **The key present with `null`, versus the key missing.** `dict.get` collapses "key missing" with
  "key holds null", and that collapse is the hazard the tri-state exists to remove at the level of
  the *value* — but it still has to be removed at the level of the *lookup*, because
  `tracker: {egress: }` is a record that records nothing while a missing `egress:` is no record.
  `null` is therefore a **fault** (it refuses) and absence is **absence** (it defers to Channel 1),
  and the two are told apart by a **module-local sentinel** in `tracker/`, with the same semantics as
  `sync/consent.py:145`'s `_MISSING` and the reasoning cited rather than the object imported (C-001).
- **`tracker.egress: null` planted by a writer.** `TrackerProjectConfig.to_dict`
  (`config.py:53-67`) emits every known field unconditionally, including `None`s. Under the rule
  above that null is a fault, a key that decides egress must not be planted by the command that
  creates a binding. FR-009 forbids it.
- **A committed decision survives `bind` and `unbind`.** **Six** construction sites of
  `TrackerProjectConfig` feed a `save_tracker_config`, and they split into two classes — *erases
  today* and *will be broken by FR-002* — enumerated in FR-011. Erasing a `refused` is a **silent
  fail-open**; erasing a `permitted` silently withdraws a working local binding. FR-011 records the
  semantics: **a recorded tracker-egress decision outlives its binding.**
- **`.kittify/config.yaml` unparseable.** `load_tracker_config` **raises** `TrackerConfigError`
  (`config.py:148-149`), and `_load_runtime` calls it *synchronously* at
  `local_service.py:116/131/141` — before the coroutine that reaches `_build_engine`. The gate is
  therefore placed ahead of `_load_runtime` (FR-001), and the verdict function catches the raise and
  answers with a fault refusal (NFR-003). **This behaviour is pinned at the unit level only**; the
  CLI-level acceptance scenario that used to assert it has been **cut**, for the reason recorded in
  C-021.
- **`status`, `bind`, `unbind`, `map add`.** None construct a connector, none run a subprocess and
  none reach a transport, so none are gated. Gating `_load_runtime` — which `map_add` and `map_list`
  also call — would take local-only commands away from a refusing project for no confidentiality
  gain. `status()` reaches `load_tracker_config` directly (`local_service.py:81`), bypassing
  `_load_runtime`, which is one of the reasons `_load_runtime` is not the gate site either.
- **`map list` is two commands wearing one name.** `map list` with no `--provider` goes to
  `_resolve_backend()` and, on a local binding, performs no egress — ungated, as above. `map list
  --provider <saas>` goes to `_resolve_saas_backend_for_provider` (`service.py:210`) and crosses
  `_request`, so it **is** gated, at `HOSTED_SERVICE`, by the SaaS gate — with no change to
  `tracker.py:942-963` and no new gate site. The same holds for `issue-search --provider` and
  `list-tickets --provider`. This is a direct consequence of making the destination a parameter: the
  gate placement follows the transport rather than the subcommand name.
- **An incomplete binding in a refusing project.** `_load_runtime` raises "Tracker provider/workspace
  configuration is incomplete." Because the gate now runs first, such an operator sees the refusal
  rather than the incompleteness. Deliberate: **the egress verdict outranks configuration
  completeness**, because telling an operator to finish a binding they are not permitted to use is
  worse advice than telling them why they are refused.
- **Two checkouts of one project with opposite tracker keys.** The tracker key is answered by the file
  in the checkout the command is standing in; there is no cross-checkout reconciliation and none is
  wanted, because the tracker path is always operator-invoked from inside the checkout (C-006
  precondition 3). If that precondition breaks, this becomes a real conflict rule that must be
  written.
- **`sync run` where the pull half would succeed and the push half refuse.** Cannot arise: the verdict
  is computed once, at the head of `sync_run`, and both halves are downstream of it.
- **The config file changes between the gate's read and `_load_runtime`'s read.** Two reads of one
  file inside one command. The verdict stands as computed; the gate is not re-run. The same window
  exists today between `_is_local_binding()` and `_load_runtime`. Recorded rather than closed, because
  closing it means threading a loaded config through a signature this Mission does not own. **Note
  what the destination parameter removed:** an earlier revision needed a *second* read inside the
  verdict itself, to derive the binding kind. With the destination supplied by the caller, the verdict
  reads the project config exactly **once**, so the command performs two reads rather than three and
  the verdict is internally self-consistent by construction. The remaining window is the pre-existing
  one and is unchanged by this Mission.
- **`spec-kitty tracker sync publish` on a `beads`/`fp` binding.** Raises `AttributeError`
  (`LocalTrackerService.sync_publish` does not exist; `service.py:202-203` delegates unconditionally),
  which `_run_or_exit` (`tracker.py:346-351`) catches only for `RuntimeError`/`ValueError`. A live
  bug, **incidental to this Mission** — filed, not absorbed (C-013).

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | The gate runs at the head of the three sync entry points, before `_load_runtime` | (US3, US4) As an operator, I want the tracker-egress verdict consulted as the **first statement** of `LocalTrackerService.sync_pull`, `sync_push` and `sync_run` — ahead of `self._load_runtime()` at `local_service.py:116/131/141` — so that a refusing project is told it refused rather than handed a `TrackerConfigError` traceback, and so that nothing is read or created on its behalf first. **Why not `_build_engine` (`def` at `:217`), the site the rejected draft chose:** `_load_runtime` is called *synchronously* before the coroutine that reaches `_build_engine`, and it calls `load_tracker_config`, which **raises** `TrackerConfigError` on an unparseable file (`config.py:148-149`) — so a refusing project with a broken config would get a traceback rather than its refusal (pinned at the unit level; C-021 records why the CLI-level scenario was cut). It also reads the machine-global credential store and constructs `TrackerSqliteStore`, which `mkdir`s and creates a SQLite file with three tables (`store.py:278-281`), on behalf of a project that is about to be refused. Moving the gate ahead of it makes the refusing path zero-effect as well as zero-argv (NFR-002). **Rejected alternatives:** `_load_runtime` itself — also called by `map_add`/`map_list`, which perform no egress, so gating there withdraws local-only commands from a refusing project; `TrackerService._resolve_backend` (`service.py:65`) — bypassed by `bind()` (`service.py:131-166`, which constructs both backends itself at `:142` and `:163`); `cli/commands/tracker.py::_service` (`:327`) — covers the CLI only, and a gate in a CLI helper is invisible to any future library caller (**note:** the rejected draft justified this by saying `_service` misses the automatic `origin_consumer` path; that premise is **false** — `origin.py` imports no `TrackerService` and `origin_consumer` never reaches `LocalTrackerService`. The rejection stands on the library-caller ground alone); `factory.build_connector` (`factory.py:32`) — does not have the repo root in scope. Because the local gate sits at three call sites rather than one, FR-015 guard G3 pins that set exactly — and pins the call as the first **executable** statement, so no `_require_egress` helper may stand in for it. | High | Open |
| FR-002 | A tracker-scoped key, named and shaped as a tri-state, carrying its raw value | (US1, US2) As an operator, I want to decide tracker egress for one project by recording **`egress` in the `tracker:` block of that project's own `.kittify/config.yaml`**, holding one of a **closed set of two strings, `refused` or `permitted`**, with **absence spelled as the key being missing**. Three visibly distinct states, no boolean negation, and absence does not share a spelling with a recorded value — which is the same absence-versus-recorded-value conflation this Mission exists to close at Channel 1. The name and shape are chosen, not inherited — see Key Entities. On `TrackerProjectConfig` the field holds the **raw loaded value plus a derived fault**, never a narrowed type such as an enum-or-`None` or `bool \| None`: measured on the `doctrine.mode` precedent, a known field with an unusable value is silently replaced by its default on round trip, which would convert a refusing project into a permitting one at the next `bind`. The field is added to `_KNOWN_KEYS` (`config.py:69-72`) so it is not reachable only through the untyped `_extra` passthrough whose consumers have never been audited (C-019). Absence is distinguished from a present `null` by a **module-local sentinel** (C-001). | High | Open |
| FR-003 | One named `tracker_egress_verdict(root, *, destination)`, called by the gates and by `sync doctor` | (US1, US5, US7) As a maintainer, I want exactly **one** function that composes the two channels for a **named destination**, so that the enforced answer and the reported answer cannot disagree. **Signature:** `tracker_egress_verdict(root: Path \| None, *, destination: EgressDestination)` — `destination` is **required and keyword-only**, and `EgressDestination` is a closed two-member set, `LOCAL_SUBPROCESS` and `HOSTED_SERVICE`. It returns a value object carrying: `refused`, the set of `refusing_channels` (never just the first), the Channel-1 state (no record / recorded refusal / not consentable), the Channel-2 state (absent / refused / permitted / fault, with the raw value), **the destination it was asked about**, the operator message and its remedies. **There is no `binding_kind` field and no binding-kind derivation** — the caller states the destination; the function never reads the provider (FR-004). **Call sites in `src/`, pinned by exact membership and exact count (FR-015 G4): exactly five enclosing functions** — `LocalTrackerService.sync_pull`, `.sync_push`, `.sync_run` (FR-001, each passing `LOCAL_SUBPROCESS`), `SaaSTrackerClient._request` (FR-016, passing `HOSTED_SERVICE`), and `sync doctor`'s new renderer (FR-014) — and **exactly six call expressions**, because the doctor renderer calls it once per destination (US7). Both numbers are asserted exactly, never `<=`. **No `_require_egress` helper is introduced**: a helper would let G3's "first statement" property be satisfied by a call to the helper, which stops pinning `tracker_egress_verdict` at all — the gate line is written out at each of the three local sites. **Amended 2026-08-30 (#539, following #458/PR #504):** the no-helper rule remains binding for G3's three `LOCAL_SUBPROCESS` sites; on the hosted side it is superseded by `SaaSTrackerClient._enforce_tracker_egress_consent()`, called first by both `_request` and `_request_with_retry`. The guard now pins that helper's own first runtime statement to `_current_tracker_egress_verdict()`, so `tracker_egress_verdict` remains transitively pinned; do not restore the duplicated hosted gate lines. **Its internal decomposition is specified, because a conservative feature-complete single function measures `C901 17 > 15`:** the 8-cell join is the module-level `_JOIN` mapping (FR-005), and the Channel-2 decode, the Channel-1 resolution, the reporting classifier and the message/remedy composition are each their own helper (each measured ≤ 3). `tracker_egress_verdict` itself becomes a short composition. This is a requirement, not a suggestion — the charter's ceiling is 15 and no blanket `# noqa` is permitted (NFR-005). **This amends the rejected draft's "no third function computes a combined verdict" to "exactly one function computes it, and everyone asks it"**: the draft's rule contradicted its own FR-012, which required `sync doctor` to state which channel refuses — definitionally a second combined verdict. One function with a pinned caller set is the shape that actually delivers the property the draft's rule was reaching for. | High | Open |
| FR-004 | Polarity follows the destination — and the destination is a parameter, not a derivation | (US1, US2, US5) As the operator of this decision, I want Channel 2's polarity fixed by **where the data goes**, and I want that to be a property the type checker and a guard enforce rather than a rule a reader remembers. At **`LOCAL_SUBPROCESS`** Channel 2 is **two-way**: `refused` refuses, `permitted` is an affirmative tracker grant that satisfies the path independently of Channel 1. The destination is a subprocess named by the operator's own credential file (`factory.py:56`); spec-kitty's SaaS is not involved; this is where the *"consent to hosted sync or lose your local tracker"* coercion lived, so this is where it dissolves. At **`HOSTED_SERVICE`** Channel 2 is **narrowing only**: it may refuse, it may not grant, and Channel 1 remains a hard prerequisite — because, verified at `bb2020fea`, `saas_client.py:247` resolves `_base_url` from `resolve_runtime_target().resolved_server_url` and every endpoint is `/api/v1/tracker/…` with a bearer token and `X-Team-Slug`, so **that path sends to spec-kitty's hosted service**, which holds the connector and relays. **Why the destination cannot be derived from the config, measured:** `TrackerService._resolve_saas_backend_for_provider` (`service.py:84-98`) substitutes `TrackerProjectConfig(provider=provider)` **in memory** when `--provider <saas>` is passed and never rewrites the file, so with on-disk `provider: beads` the subject reaches `SaaSTrackerService` while `load_tracker_config(root)` still answers `'beads'` (positive control: disk `jira` → same backend class; negative control: `TrackerServiceError` for `'beads'`, so the probe discriminates). Three operator-reachable commands do this with `allow_unbound=True` — `list-tickets --provider` (`cli/commands/tracker.py:998-1007` → `service.py:220` → `saas_client.py:613` → `_request`), `issue-search --provider` (`tracker.py:369-386` → `service.py:214`), `map list --provider` (`tracker.py:942-963` → `service.py:210`). A config-derived polarity would therefore read `beads`, apply the local half, and make `tracker.egress: permitted` an **affirmative grant to spec-kitty's hosted service with Channel 1 absent** — reopening `#3030`'s P0 boundary through the key introduced to protect it. **Therefore:** `saas_client._request` passes `HOSTED_SERVICE` **unconditionally**, `local_service.sync_pull/push/run` pass `LOCAL_SUBPROCESS`, every call site passes a **literal** member, and **no call site derives the destination from a config read** (FR-015 G5). Pinned end to end by US5 scenario 4 and its positive control. | High | Open |
| FR-005 | The combination is a total, enumerated 8-cell table | (US1, US2, US5) As a maintainer, I want the join written as one enumerated table rather than a chain of short-circuits, because the granting half means **both channels are always evaluated** — a Channel-1-first short-circuit would refuse a project that Channel 2 permits. The table is **8 cells**: **Channel-2 value** ∈ {absent, `refused`, `permitted`, fault} × **destination** ∈ {`LOCAL_SUBPROCESS`, `HOSTED_SERVICE`}. **fault** refuses at both. **`refused`** refuses at both. **`permitted`** permits at `LOCAL_SUBPROCESS`; at `HOSTED_SERVICE` it is a no-op that must be *reported* as a no-op, never silently dropped. **absent** defers to Channel 1 at both. **The `none` binding kind is gone**: it existed only because the old signature had to describe a root it could not classify, and `root=None` — reachable only from `SaaSTrackerClient._request`, whose `self._project_root` is `Path \| None` — is now simply `HOSTED_SERVICE` with Channel 2 absent, answering with text byte-identical to `UNDETERMINED_PROJECT_REFUSAL`. When more than one channel refuses, the message names **all** of them, so an operator who clears the tracker key is not surprised by a second refusal. **The table is a data structure, not a branch chain**: a module-level `_JOIN: dict[tuple[str, EgressDestination], str]` holding **exactly 8** entries, so `len(_JOIN) == 8` is a **structural** pin that a test-local counter is not — and so the join contributes no cyclomatic complexity. All 8 cells are additionally exercised by one parametrised test that prints and asserts the cell count it ran is exactly 8. **Vocabulary note:** "Channel-2 value" is the tri-state-plus-fault above; "Channel-1 state" is the separate reporting-only triple in FR-012 (no record / recorded refusal / not consentable). Requirements, messages and `sync doctor` output must always name which of the two they mean. | High | Open |
| FR-006 | Absence and unusability, stated per channel and defended | (US1, US2, US3) As a maintainer, I want the absence rule written down once, per channel, because the two differ and the difference is the design. **Channel 1: absence denies**, uniform with the SaaS tracker path at `saas_client.py:329`. **Channel 2: absence — the key missing — records nothing** and defers to Channel 1. A **non-mapping `tracker:` block is also absence**, not a fault (`config.py:151-152` passes `None`; `from_dict` returns `cls()`). **Channel 2 present and outside the closed set refuses at both destinations**: the decode is an exact match against exactly two strings, `refused` and `permitted`, and **every other present value is a fault, and a fault refuses and never grants**. No case-folding, no `yes`/`on`/`1`/`true`, no synonym or truthy table, no coercion of non-strings. **The decode is `isinstance`-guarded before the membership test — `isinstance(raw, str) and raw in _LEGAL`, never `raw in _LEGAL` alone.** Measured: the bare membership test raises `TypeError: unhashable type` for a mapping and for a list at the key — the two shapes this requirement itself enumerates as faults — from inside a function NFR-003 says must never raise. This is not a style note; it is the difference between a fault refusal and a traceback out of the gate. **This is the same rule the bool-only argument at `sync/consent.py:196-241` was written to enforce, not a retreat from it** — read that argument as being about *closed decoding* rather than about the `bool` type, and it transfers intact: the hazard it names is a lookup table that keeps having to rule on one more spelling, where each new accepted spelling on this key would manufacture a **grant**, a leak surface with no upside; and `no`/`off`/`yes`/`on` are strings under ruamel's YAML 1.2 round-trip loader anyway, so a permissive decode means re-implementing YAML 1.1 implicit typing in a module that does not own it. A closed string set is the same shape as `CONFIG_FAULT_KINDS` (`sync/config.py:78-83`), whose set is likewise cut by the operator action that resolves it and likewise admits nothing outside itself; **that is why moving from a boolean to a string enum does not reintroduce the leak surface the bool rule was written against.** A fault is *reportable* (C-020); a silently-honoured near-miss would not be. | High | Open |
| FR-007 | Absence of both channels denies — the decision, and the alternative it beat | (US3, US6) As the operator of this decision, I want the rejected alternative recorded at its real strength. **The alternative was: honour recorded refusals, absence permits** — the tracer's own recommendation. Its case is genuine: it breaks no existing binding, needs no upgrade action, and the tree has already declined a fail-closed reading of absence three times where the cost was too high (`consent.py:295-299` — *"Calling this a fault would deny every delivery on the machine"*; `consent.py:218-221`; `tracer-design-decisions.md:424-425`). It was **rejected anyway**, affirmed independently by all four squad lenses, on two grounds. (a) **The refusal carries its own remedy**, so the cost of denying is a one-time recorded decision, not a permanent block — repaired, because that ground was **falsified as written**: for an identity-less checkout neither Channel-1 remedy worked, which is why FR-012 grows the third state and its `spec-kitty init` remedy, and why the Channel-2 grant (FR-004) is the remedy that needs no identity at all. (b) **Absence-permits rests on an unverified premise.** Its case is "the local path is a trust-boundary question, not a third-party leak" — and whether `bd`/`fp` make network calls is **UNVERIFIED and unresolvable from this repository** (C-012.1). The executable name is operator-overridable from a machine-global credential file (`factory.py:56`), so permitting on absence would bet the confidentiality property on a claim nobody has established. **Deleted:** the rejected draft's third ground, uniformity ("one command surface, two meanings"), is **falsified by this spec's own citation** of `_check_sync_readiness`'s local short-circuit — `spec-kitty tracker sync push` already means different things on local and SaaS bindings, and has since before this Mission. | High | Open |
| FR-008 | `#3030` FR-003 governs *undetermined*, not *unrecorded* | (US3) As a maintainer, I want it stated that **the deny-on-absence decision above is NOT derivable from `#3030` FR-003**, because that derivation is the hinge of the argument and getting it wrong makes an operator choice look like a forced consequence. `#3030`'s recorded reasoning is mixed by branch: the *undetermined* branch is principled (`invocation/adapters.py:49-51` — *"neither is consent (FR-003's rule, re-derived here)"*), while the *absence* branch is incident-anchored (`spec.md:53-56` — *"In the incident the five client repos were never opted in, so they have no record"*; `consent.py:24-25` — *"the five leaked projects had no record at all"*). The two are separable, and the tree separates them. So: undetermined denies **because FR-003 says so**; absence denies **because the operator chose it**, at the cost stated in FR-007 and FR-013. | High | Open |
| FR-009 | A write must never plant a decision | (US1) As an operator, I want `save_tracker_config` to **omit** `egress` from the emitted `tracker:` block when no decision is recorded, rather than emitting a null the way `to_dict` emits every other unset known field (`config.py:53-67`). Without this, `spec-kitty tracker bind` — the command that creates a working binding — writes `egress:` with a null, which FR-006 reads as a fault, which refuses. The binding command would disable the binding. **Absence must stay spelled as the key being missing**, which is the whole point of the tri-state: a written-out null would put absence back into the value slot it was moved out of. Pinned by a test that binds into a project with no tracker key and asserts the rendered `tracker:` block contains no `egress` key at all. | High | Open |
| FR-010 | Every probed value round-trips byte-identically | (US1) As an operator, I want a committed `egress` value to survive `spec-kitty tracker bind` and any other whole-block rewrite **byte-identically**, for **every** value in the probed set — the two legal values `refused` and `permitted`; the quoted forms `"refused"` and `'permitted'`; the near-miss strings `Refused`, `REFUSED`, `refuse`, `deny`; the wrong types `true`, `false`, `0`, `null`, a mapping, a list; and the empty string — not merely for the one that surfaced first. The measured finding this defends against stands unchanged by the re-spelling: a known field whose value is unusable is silently replaced by its default on round trip, so a narrowed field type would let `bind` erase a recorded `refused`. `save_tracker_config` is a payload-level read-modify-write over `to_dict` (`config.py:171`). The pin compares the `egress` line's bytes before and after, and asserts the rest of the file differs only in lines a `bind` is supposed to touch. If achieving byte-identity requires `load_tracker_config` to set `preserve_quotes = True` — matching what `save_tracker_config` already does at **`config.py:160`** — that change is in scope. **Its blast radius, restated from measurement rather than from the earlier guess:** `from_dict` `str()`-coerces **every** known string field (`provider`, `binding_ref`, `project_slug`, `display_label`, `workspace`, `provider_context` values, `doctrine.mode`, `field_owners`), so the ruamel scalar-string subclass survives on **only** `_extra` values and the raw `egress` value — not on "every string loaded from `tracker:`". The blast radius is that narrow, and the implementer confirms it rather than assuming either bound. **Also in scope, and separately measured:** `clear_tracker_config` (`config.py:178-194`) constructs a **third** `YAML()` at `config.py:184` with **no** `preserve_quotes` and dumps straight to the file handle, so today `unbind` destroys quoting in **sibling blocks** even where `save_tracker_config` would have preserved it. **Scope decision, stated rather than left to be discovered: byte-identity is required of the `egress:` line only.** Whole-file byte-identity is not achievable through `clear_tracker_config` without giving it `preserve_quotes` too, which this Mission does do — but the pin asserts the `egress:` line byte-for-byte and asserts the rest of the file differs only in lines the operation is supposed to touch, because a whole-file assertion would make every unrelated ruamel formatting difference a failure of this Mission. Red first: the pin fails on `bb2020fea` for at least the quoted-string and `null` cases. | High | Open |
| FR-011 | A recorded tracker-egress decision outlives its binding — at **every** construction site that reaches disk | (US1, US2) As an operator, I want `bind`, `rebind` and `unbind` to preserve a committed `egress`. The inventory is **re-derived from `grep -n "TrackerProjectConfig(" src/`** rather than recalled, and it splits into two classes, because the second class does not exist until FR-002 lands. **Class A — erases today.** (A1) `LocalTrackerService.bind` (`local_service.py:57`) builds a **fresh** config from its arguments and discards everything committed. (A2) `TrackerService.bind`'s local branch (`service.py:163`) hands that constructor an **empty** `TrackerProjectConfig()`, so the argument is a lie about what is on disk — it must hand the loaded one. (A3) `SaaSTrackerService.bind` (`saas_service.py:266`) builds a bare `TrackerProjectConfig(provider=…, project_slug=…)` carrying **nothing** forward and saves — **measured**: `BEFORE tracker: provider: linear / project_slug: p / egress: refused` → `AFTER bind: egress present? False`, against the control `(_extra-carrying pattern): egress present? True`. This is an erasure **today**, on the destination where Channel 2 is the only narrowing conjunct, and it was missed by every previous revision. **Class A′ — defence-in-depth, no production write path, and therefore NO red-first pin on the base.** (A4) `TrackerService._resolve_saas_backend_for_provider` (`service.py:98`) substitutes a fresh `TrackerProjectConfig(provider=provider)` which becomes `self._config`, and *would* feed an empty `_extra` into `_persist_binding` — **but it is not reachable from any write today**, measured: `_persist_binding`'s three call sites (`saas_service.py:347`, `:412`, `:505`) all sit inside bind flows (`_confirm_and_persist`, `_bind_from_resolution`, `validate_and_bind`) entered from `TrackerService.bind` (`service.py:141-145`), which constructs its own service with `load_tracker_config`; `_resolve_saas_backend_for_provider` serves only the three **read** paths (`service.py:210,214,220`), whose methods (`saas_service.py:556,575,592`) persist nothing. The only other write path, `apply_binding_upgrade` (`saas_service.py:191`), has **zero callers in `src/`** — tests only. So A4 is fixed **so that a future write-capable caller cannot reintroduce the erasure**, and an implementer must **not** write a red-first pin for it — there is no production path to red. Its correctness is asserted at the unit level against the substituted config object directly. **Class B — works today, and FR-002 breaks it.** (B1) `saas_service.py:206-219` (the binding-ref upgrade inside `apply_binding_upgrade`; construction at `:206`, `_extra=` carry at `:219`) and (B2) `saas_service.py:303-316` (`_persist_binding`; construction at `:303`, carry at `:316`) preserve a committed `egress` **only because it currently rides in `_extra`**; `from_dict` excludes known keys from `_extra` (`config.py:107`), so promoting `egress` to `_KNOWN_KEYS` **destroys the mechanism that makes these two correct** — and the rejected draft cited exactly these two lines as *the pattern to copy*. They must gain an explicit `egress=self._config.egress` carry. **(C) `clear_tracker_config` (`config.py:178-194`)** does an unconditional `del payload["tracker"]` — it must retain a `tracker:` block containing only a recorded `egress`, and delete the block entirely when none is recorded. **(D) `SaaSTrackerService.unbind` (`saas_service.py:281`)** resets `self._config = TrackerProjectConfig()` **in memory** after `clear_tracker_config`. On the same instance a subsequent `_persist_binding` would then write a config with no `egress` — **erasing what (C) was just fixed to preserve**. Library-caller reachable only (the CLI builds a fresh service per invocation), which is why it is class D and not class A. Resolution: reset to `load_tracker_config(self._repo_root)` so the in-memory object matches what (C) just left on disk. **Not in the inventory, checked and stated:** `origin.py:536` and `config.py:142` construct configs that never reach `save_tracker_config`. **Landing rule:** the field-shape change (FR-002) and the preservation work at all of A1–A3, A4, B1–B2, C and D **land as one change** — or, if they are split, a guard is added asserting that every `TrackerProjectConfig(` construction whose value flows to `save_tracker_config` carries `egress`. Splitting them without that guard ships a window in which the two SaaS sites are silently broken. **If they are split, the FR-002-only tree is a required measurement point** (see the plan's *Red-First Proof Strategy*): B1's and B2's reds exist on exactly the tree the FR-009 null-planting red is already required to be observed on, so observing and quoting them costs nothing and is the difference between shipping them tested and shipping them asserted. **The recorded semantics: a recorded tracker-egress decision outlives its binding.** Symmetric across the tri-state — a recorded `permitted` survives an unbind exactly as a recorded `refused` does — and **erasure must not be confusable with absence**, which is precisely what a missing key now means. Deleting a `refused` is a **silent fail-open**; deleting a `permitted` silently withdraws a working local binding. Pinned in both directions at every site, with the sibling `sync:` block asserted still present as the control. | High | Open |
| FR-012 | The refusal is operator-visible, actionable, non-zero, and names the Channel-1 state | (US3, US6) As an operator, I want the refusal raised as a `RuntimeError` subclass so `_run_or_exit` (`tracker.py:346-351`) prints it in red and exits 1 — never a silent no-op, never a zero exit with an empty result, because these are interactive commands and someone running `sync push` would otherwise believe their data shipped. On the local path the exception is a new `LocalTrackerServiceError` subclass; on the SaaS path the existing `TrackerEgressRefusedError` (`saas_client.py:67`, a `SaaSTrackerClientError`, itself a `RuntimeError`) is kept unchanged. **The two hierarchies are not unified — the verdict is.** Both messages are the `message` field of the same `tracker_egress_verdict` value, pinned byte-identical across the two paths for the same verdict. Channel 1 resolves to **three** states, each with its own wording and remedies: **no record found** (remedies: `sync.enabled: true` in the project's own config, or `spec-kitty sync opt-in`, verified real — `enable_checkout_sync` (`routing.py:304`) → `set_project_consent(uuid, True)` (`routing.py:325`) writes the uuid-keyed index `resolve_project_consent` reads); **a refusal is recorded** (remedy: change the recorded decision); **not consentable, no project identity resolved** (remedy: `spec-kitty init`) — measured: `enable_checkout_sync` raises `ConsentIdentityUnresolvedError` (`routing.py:320-321`) when `routing.project_uuid` is falsy, and hand-authoring `sync.enabled: true` still denies, so today's message tells the operator to do what they just did. Every state also carries the Channel-2 grant as a remedy **when the destination is `LOCAL_SUBPROCESS`**, and at `HOSTED_SERVICE` explicitly says the grant does not apply there. **The three-way distinction is reporting-only** — see C-004 for how it is obtained without a second derivation of the verdict, for the debt it represents, and for the condition on which it is deleted. | High | Open |
| FR-013 | The breaking change is a deliverable, not a note | (US6) As an operator, I want the upgrade cost carried in three places: (1) the refusal message, per FR-012; (2) a **Breaking Changes** entry in `CHANGELOG.md` stating that `beads`/`fp` bindings now require a recorded decision at one of the two channels and that absence of both denies; (3) an upgrade note under `docs/migrations/`, linked from `docs/migrations/index.md`, giving all remediation paths — including the Channel-2 grant, which is the only one that works without a project identity — stating the remaining one-direction limitation at `HOSTED_SERVICE` (**C-016**, not C-014 — the earlier revision cited the wrong constraint here), and carrying **one sentence on the `map list` split**, which will otherwise read as a bug: on the same refusing project, `spec-kitty tracker map list` succeeds while `spec-kitty tracker map list --provider jira` refuses, because the second crosses the hosted transport and the first does not — the gate follows the destination, not the subcommand name. Pinned by an anchor check that fails in CI if the section is removed or renamed — the `#3030` FR-018 pattern. | High | Open |
| FR-014 | `sync doctor` gets a **new** renderer, printing **one row per destination**, not a third scope through `_render_consent_fault` | (US7) As an operator, I want tracker egress reported by a block written for a **verdict**, printed unconditionally including the permitted case, placed beside the consent-readability section (`cli/commands/sync.py:1736-1817`) and rendered by its own function. **The block prints one row per `EgressDestination` member — two rows, always, in every checkout — and never consults the on-disk provider to decide what to show.** That is a correctness requirement, not a layout choice: the on-disk provider does not determine the destination (FR-004's measurement), so a provider-conditional rendering would confirm `permitted` as in force to an operator whose `list-tickets --provider jira` is refused. Two rows also make the renderer honest about the case FR-005 covers and a one-row block cannot express: Channel 2 `permitted` with Channel 1 absent is *permitted locally and refused hosted* in the same checkout at the same moment. **Not** routed through `_render_consent_fault` (`:1711-1733`), measured to be wrong three ways for this content: a plain string arrives as `kind="unknown"`, `detail="no detail recorded"` and the refusal text is discarded; a fault-shaped carrier announces a **correct, readable** file as `UNREADABLE` and tells the operator to `REPAIR` it; and `_CONSENT_FAULT_NOT_ABSENCE` (`sync.py:1691-1696`) prints *"This is NOT a missing consent record"* **unconditionally** — literally false for the absence case, and hard-coded outside the registry, so registering a fifth kind does not fix it. **Not** in the per-project Consent column (`_per_project_store_table`, `:1429-1473`) either: it is hard-coded binary (`consented` / `denied (<level>)` plus one `unknown (identity unresolved)` case), so a second *decision* has nowhere to go in it. The readability section's contract is **readability**, not verdict (`:1737-1743`) — a verdict inside it is the category error this spec refuses elsewhere. `CONFIG_FAULT_KINDS` is **not** extended (pinned by exact equality at `tests/sync/test_consent_fault_vocabulary_3030.py:261`). Blast radius named: `tests/cli/commands/test_sync_doctor_consent_health_3030.py:366` asserts `flat.count("REPAIR THE FILE'S SYNTAX") == 4` over the **whole rendered output**, so the new block must contribute nothing to that count. | Medium | Open |
| FR-015 | **Six** falsity guards, repo-wide, exact-membership, non-vacuous, and **not blind to their own subject** | (US3, US4, US5) As a maintainer, I want the properties a future change can silently break enforced by AST guards over **`src/`**, each asserting **exact membership and an exact count** — never `<=`, which passes on a zero-call scan, which is exactly what happens after Bundle B moves a file — and each **printing and asserting its own non-zero input count**. **The matcher's call form is specified, because the obvious implementation is blind.** Measured: a sixth, ungated call site written module-qualified — `from specify_cli.tracker import egress_verdict as ev` … `ev.tracker_egress_verdict(root, destination=ev.EgressDestination.LOCAL_SUBPROCESS)` — **passes both G4 and G5**, with G4's input count merely *rising*, because a matcher that inspects only `ast.Name` func nodes never sees it. Every call-site guard therefore resolves **both `ast.Name` and `ast.Attribute` func nodes** (`f(...)` and `mod.f(...)`), and G4/G5 each carry a **third mutant that adds a call site in module-qualified form**. Both previously specified G5 mutants keep the `ast.Name` form, so a guard with this hole kills 2/2 and reports itself healthy — **a guard that survives its own mutants while blind to its subject is worse than no guard**, because it converts an unexamined property into an examined one that is false. **G1:** `set(factory.SUPPORTED_PROVIDERS) == {"beads", "fp"}`, so `LocalTrackerService` cannot become a second, differently-gated route to a third party. **G2:** the set of `build_connector` call sites in `src/` is exactly `{local_service.LocalTrackerService._build_engine}`, count exactly 1 (measured: exactly one call site tree-wide). **G3:** the set of `_build_engine` callers in `local_service.py` is exactly `{sync_pull, sync_push, sync_run}`, and in each **the gate call is the first executable statement** of the method body — a docstring is tolerated as the first AST node; nothing else is. **G4:** the set of **enclosing functions** containing a `tracker_egress_verdict` call in `src/` is exactly the **five** named in FR-003 — `sync_pull`, `sync_push`, `sync_run`, `SaaSTrackerClient._request`, and `sync doctor`'s renderer — count exactly **5**; and the number of **call expressions** is exactly **6**, the extra one being the doctor's second destination row. Both are exact. *The rejected draft said "exactly three" while its own FR-001 demanded three local sites, FR-016 a fourth and FR-014 a fifth; the number was arithmetically impossible and was repeated five times in the plan.* **G5 (new):** every `tracker_egress_verdict` call expression in `src/` passes `destination=` as an **`Attribute` node on `EgressDestination`** — a literal member — and **no call site derives it from a config read**: the guard asserts that no call expression's `destination` argument is a `Name` or `Call` node, and that the set of literal members passed is exactly `{LOCAL_SUBPROCESS, HOSTED_SERVICE}` with `_request`'s always `HOSTED_SERVICE` and the three local sites' always `LOCAL_SUBPROCESS`. **This is what converts "polarity follows the destination" from a remembered rule into a `mypy`-checkable, guardable property**, and it is the reason the destination is a required keyword-only parameter rather than a defaulted one. **G6 (new): the verdict function must not re-derive the destination in its own body.** G5 guards the call sites; the original defect lived in the *body*, and a future change reading *"if the on-disk provider is local, treat this as local regardless of the argument"* passes G5 at all six expressions. G6 asserts that `src/specify_cli/tracker/egress_verdict.py` contains **no** reference to `provider`, `LOCAL_PROVIDERS` or `SAAS_PROVIDERS`, and **no `.provider` attribute access on a `load_tracker_config` result** — exact membership, and the expected set is **empty**, with the **printed non-zero input count being the number of AST nodes scanned** (an empty-set assertion over zero nodes is the vacuity this rule exists to prevent). One mutant reintroduces a provider read. **How each guard is mutated, stated once and applying to all six:** every guard is written as an **analyzer callable taking source text or a root path** and returning its findings, and the test invokes it **twice** — once against `src/`, once against **synthetic mutated source held in the test** — reporting the real input count and the killed-pin count separately. That is how "mutations are pytest plugins injected via `PYTHONPATH`, never source edits" is satisfied for an AST guard: nothing on disk is edited, and the guard is exercised against a string. **On what G5's clauses are worth:** its set-equality clause (*"the literal members passed are exactly the two"*) carries almost nothing on its own, because the doctor renderer supplies both members by itself; **the per-site mapping — `_request` always `HOSTED_SERVICE`, the three local sites always `LOCAL_SUBPROCESS` — is the load-bearing half**, and it is the half whose mutant must kill. **Import form is load-bearing on G5 and is written down here because it is nowhere else:** `EgressDestination` is imported under its own name (`from … import EgressDestination`). An aliased import (`import … as ED`) makes each `destination` argument an `Attribute` on `ED` and G5 reports non-literal — a **false red**, loud rather than silent, but a lost afternoon for anyone who has not been told. | High | Open |
| FR-016 | The hosted path keeps Channel 1 exactly and gains Channel 2 as a narrowing conjunct | (US5) As a maintainer, I want `tracker/saas_client.py`'s chokepoint at `_request` (`:329-331`) to consult `tracker_egress_verdict(self._project_root, destination=EgressDestination.HOSTED_SERVICE)` instead of `project_egress_refusal` directly. **The destination literal is unconditional** — there is no branch, no provider read and no configuration under which `_request` can ask about anything else, which is what makes the hosted half of FR-004 structural rather than conventional. The Channel-1 half of the verdict must produce **byte-identical** refusal text to today's for the three measured outcomes (absence → refused; recorded `false` → refused; recorded `true` → gate passes to the token check), including the `root=None` case, which must reproduce `UNDETERMINED_PROJECT_REFUSAL` exactly. `SaaSTrackerService` and every other line of `saas_client.py` are untouched, the gate stays **before** `_fetch_access_token_sync()`, and `TrackerEgressRefusedError` keeps its identity and base class. A Mission that closes the local gap while perturbing the shipped hosted gate has traded one leak for another. | High | Open |
| FR-017 | Docstrings that this Mission makes false are amended, and the debt that a successor must act on is carried **in source** | (US3) As a maintainer, I want three docstrings corrected rather than silently falsified: `local_service.py:8` — *"No SaaS imports live here — only local connector infrastructure"* — must record the consent import; `_check_sync_readiness` (`tracker.py:296-312`) — *"Local providers reach the sync command without going through the SaaS surface at all: no auth token, no `SPEC_KITTY_SAAS_URL`, no reachability probe, no background daemon"* — becomes false the moment the local path consults the hosted-sync consent chain; and `_check_binding_readiness` (`tracker.py:315-324`), whose text is defined by mirroring the former and must not inherit a claim that is no longer true. **And two docstrings this Mission must *author*, not amend, because their audience never opens this dossier:** (4) the **module docstring of `src/specify_cli/tracker/egress_verdict.py`** and (5) **the Channel-1 reporting classifier's own docstring**, each carrying (a) the **cause** — the resolver port is `Callable[[Path], bool]` at **`invocation/adapters.py:81`**, cited by file and line, and it discards *why* a project is refused, so the classifier is the shape of a missing return type; (b) the **retirement condition** — when Bundle B's **Q3** gives that contract a decision return value, the classifier **and both of its non-authoritativeness pins are deleted, not migrated**, both pins named; and (c) the **unregistered-consumer note** — the module reaches around the registry indirection to `specify_cli.sync.consent` by call-time guarded import, a recorded exception that retires on the same condition. **Why in source:** Bundle B's implementer opens `src/specify_cli/tracker/` and `src/specify_cli/egress/`; every prior recording of this debt lives inside `kitty-specs/…/` and will not be read. The module docstring also states the `EgressDestination` import-form rule (FR-015 G5) so a reader hits it before writing a call site. All five are pinned by **the same docstring test**, so a later revert of any of them reds. | Medium | Open |
| FR-018 | The acceptance harness is a contract, not a fixture preference | (all) As a maintainer, I want the harness pinned, because the measured alternative is a green suite with no gate. **Four** independent mechanisms have now been measured to produce that outcome; H1, H2, H3 and H8 are each one of them. **H1 — ownership mode.** Every acceptance fixture pins `doctrine: {mode: spec_kitty_authoritative}`. Under the default `external_authoritative` (`tracker/config.py:39`), `OwnershipPolicy.external_authoritative()` (`local_service.py:236`) gives `owner_for("title") is FieldOwner.EXTERNAL`, so `local_can_write("title")` is `False` (`spec_kitty_tracker/policy.py:47-49`) and `SyncEngine.push` does `stats.skipped += 1; continue` (`spec_kitty_tracker/sync.py:112-115`) and **never calls `create_issue`** — measured: a *consenting* push on a default binding captures only `['<cmd>', '--json', 'list']`, sentinel absent. **H2 — injection point.** **The recorder *is* the fake executable on disk**: a script written per fixture and named through the machine-global tracker credential file (`factory.py:56` — `command=str(credentials.get("command") or "bd")`), which appends every argv it receives to a file. It is **not** an injected `SubprocessCommandRunner` — that class is not exported from `spec_kitty_tracker.__all__` and `build_connector` passes no runner, so **there is no injection seam**, and the charter's shared-package boundary forbids reaching into the private submodule to manufacture one. `_build_engine`, `build_connector`, `SyncEngine`, `LocalTrackerService` and `TrackerService` are **un-patched in every acceptance test**. The house pattern at `tests/sync/tracker/test_local_service.py:235,262,287` patches out exactly the method that would hold the gate (docstring `:193-195`: *"We mock `_build_engine` to avoid needing the spec_kitty_tracker package"*), and a plugin-injected gate on that seam measured **bind count 0 with 519 tests green**. **The harness is POSIX-scoped**: the fake executable is a `#!`-script made executable, `subprocess.run` takes no shell, and Windows needs a `.cmd`/`.bat` sibling. Either ship the sibling or mark the suite `skipif(os.name == "nt")` with the reason recorded in the file — silently POSIX-only on a cross-platform target is not acceptable. **H3 — arming.** Every acceptance fixture sets `SPEC_KITTY_ENABLE_SAAS_SYNC=1` **explicitly** and asserts refusal **text**, not merely a non-zero exit, plus the negative pin of US1 scenario 3. **H4 — bind counter.** The gate is instrumented by a **delegating wrapper** (never a stub) installed on the name `local_service` binds `tracker_egress_verdict` under (C-007); every acceptance test asserts the counter is **non-zero**, and one test asserts the wrapper does not change any outcome. **A gate never entered is not a gate.** **H5 — executed remedies.** Every remedy claimed in a message is asserted by **applying it to the refusing fixture and re-running**, asserting the title now reaches the recorder — never by substring alone. **H6 — patch sites.** Reported per site per C-007. **H7 — isolation.** Isolated `HOME` / `SPEC_KITTY_HOME`, HTTP trip-wire on `httpx.Client.request`, `subprocess.run` counter, and the tracker-DB assertions of NFR-002. **H8 — the store is seeded (new, and measured).** Every push/run fixture seeds the tracker store with the sentinel issue **before** the command runs, via `store.upsert_issue(CanonicalIssue(...))`. `SyncEngine.push` iterates `store.list_issues(system=self.connector.name)` (`spec_kitty_tracker/sync.py:109`) and an **empty store never reaches `create_issue`**. Measured, with the harness built exactly as H1–H3 specify and nothing in the production path patched: `### EMPTY STORE ### push stats: {'pushed_created': 0} CAPTURED 1 argv sentinel: False` versus `### SEEDED STORE ### push stats: {'pushed_created': 1} CAPTURED 3 argv sentinel: True`. **A fixture satisfying H1, H2 and H3 still captures zero sentinel argv on the un-gated tree — the exact shape of a passing refusal test.** The sentinel issue's shape: `ref=ExternalRef(system="beads", workspace=<the bound workspace>, id=<a local id>)`, `title="ACME Holdings carve-out"`, `body="confidential body"`, `status=CanonicalStatus.TODO`, `issue_type=CanonicalIssueType.TASK`, `assignees=["alice@acme.example"]`, `labels=["secret-label"]`. `status` must be `TODO` or `IN_PROGRESS`. Measured across all six `CanonicalStatus` members: those two give **3** argv (`list`, `create`, `show`); every other member gives **5** (`list`, `create`, `update`, `show`, `show`), because `BeadsConnector.create_issue` follows with a `transition_issue` that contributes an `update` **and** its own `show`. The status band is what keeps the exact count at 3 — it adds **two** argv, not one. **The expected consenting argv count is 3, not 2** — `list`, `create`, `show` — because `create_issue` ends with `get_issue` (`spec_kitty_tracker/connectors/beads.py:151-153`), which runs `[<cmd>, "--json", "show", <id>]`. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | No project bytes reach argv for a refusing project | For every refusing fixture, across all three entry points, the recorder captures **zero argv**. On `push` and `run` the assertion is additionally that no captured element equals or contains the seeded sentinel title. On `pull` the title assertion is **not** made: no title crosses on pull at `bb2020fea` (US4's marked departure), so asserting its absence would establish nothing; `pull`'s assertion is the zero-argv one, and its consenting control asserts the argv **shape** `[<command>, "--json", "list", …]`. Stated over captured argv rather than a boolean return, because a boolean can be satisfied by a gate that returns early *after* the connector already ran. **Every absence assertion is paired, in the same test file and against the same recorder, with a consenting control that captures argv** — otherwise "no bytes" is indistinguishable from "the harness never ran the code". | Security | High | Open |
| NFR-002 | A refused command performs no network I/O, no subprocess, and no local side effect | With an HTTP trip-wire on `httpx.Client.request` and a counter on `subprocess.run`, a refused tracker command records **0** HTTP attempts and **0** subprocess invocations. The local-side-effect clause is stated **twice, over two fixture pairs**, because the two properties are not simultaneously observable on one pair. **(a) Content-identity, on the seeded pair.** FR-018 H8 requires the store to be seeded before the command, so the tracker SQLite file necessarily exists beforehand; the assertion is therefore that **its bytes are unchanged** — a digest taken before and after is equal, and the consenting control's differs. **(b) Non-existence, on a dedicated unseeded pair** (US3 scenario 4): with no file at the resolved db path when the command starts, a refused command leaves none, and the consenting control creates one. **Why both, and why this is the resolution chosen over the alternative:** the alternative was to let the refusing and consenting fixtures differ by more than one committed line, which would forfeit SC-006 and C-012's central claim that *the repair is one committed config line*. Splitting the clause across two pairs keeps **both** pairs one line apart, keeps the sentinel assertion only where a sentinel can actually cross, and keeps clause (b) — which is the pin that reds if the gate is moved back to `_build_engine`, where `TrackerSqliteStore.__init__` `mkdir`s and creates a SQLite file with three tables (`store.py:278-281`). Clause (a) alone would not catch that move, because re-opening an existing store is idempotent. Recorded so that a later reader does not mistake "zero argv" for "zero effects" and quietly move the gate back (C-018). | Security | High | Open |
| NFR-003 | `tracker_egress_verdict` and Channel 2's resolver never raise | For every input — unreadable, unparseable, wrong-shape, `tracker:` non-mapping, **a mapping at the `egress` key**, **a list at the `egress` key**, empty file, comments-only, chmod 000, absent file, `root=None`, and a `repo_root` that is not a project root — **twelve shapes, enumerated here and nowhere re-enumerated** — the verdict function returns a value object, **for each of the two destinations**: **24 cases**, and the parametrised test prints and asserts that it ran 24. The probed set is deliberately stated at two levels: file-level shapes *and* value-level shapes **at the key**, because the measured `TypeError: unhashable type` came from the latter and the earlier probed set listed only the former. It never propagates `TrackerConfigError` or any other exception, and it holds **no import-time dependency on `specify_cli.sync`**: the hosted-sync imports it needs for the Channel-1 state (`resolve_project_consent`, `resolve_checkout_sync_routing_readonly`) are made **at call time inside a guarded block**, degrading to the generic Channel-1 refusal wording if they fail. An `ImportError` raised out of a gate that must never raise is the failure mode this closes, and it is why the absence sentinel is module-local rather than imported from `sync/consent.py:145`. Measured over the probed shape **set**, not over the one shape that surfaced first. | Reliability | High | Open |
| NFR-004 | The gate is total across the three entry points | `sync_pull`, `sync_push` and `sync_run` each have their own refusing case and their own consenting control, each exercised end to end through the CLI. A parametrised pair that runs once and is asserted three times does not satisfy this. FR-015 guard G3 makes the totality structural rather than test-dependent. | Security | High | Open |
| NFR-005 | Coverage and quality gates on new code | New code passes `ruff check` and `mypy --strict` with zero issues and zero warnings, no blanket suppressions, and ≥90% coverage on the new branches. **`ruff format` is not clean on this repository** (`line-length = 164`) — only `ruff check` is meaningful, and a formatting diff is not evidence of anything. **Owning concern: IC-11** (`plan.md`) — this requirement is deliberately given an owner rather than left as everyone's, because a quality gate no concern names is a quality gate nobody runs. `mypy --strict` carries extra weight in this revision: the `EgressDestination` parameter is the mechanism by which FR-004's polarity becomes type-checked, so a `mypy` failure on the destination argument is a **contract** failure, not a lint failure. | Maintainability | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | The key lives in the `tracker:` block, carries its raw value, and uses a module-local sentinel | `egress` is a field of `TrackerProjectConfig` (`tracker/config.py:29-41`), a `@dataclass(slots=True)` with a closed known-key set at `:69-72`. It is added to `_KNOWN_KEYS`, not left to the `_extra` catch-all. It holds the **raw value**, not a narrowed type such as an enum-or-`None` or `bool \| None`, so a known field with an unusable value cannot be silently replaced by its default on round trip (FR-002, FR-010). Absence versus a present `null` is carried by a **sentinel defined in `tracker/`**, with the same semantics as `sync/consent.py:145`'s `_MISSING` and the reasoning cited rather than the private object imported — importing it would give `tracker/` an import-time dependency on `sync.consent` and risk an `ImportError` out of a gate NFR-003 says never raises. Only the exact strings `refused` and `permitted` record a decision; every other present value is a fault (FR-006, C-020). | Technical | High | Open |
| C-002 | Channel 2's polarity is fixed by destination; the destination is supplied, never inferred | At `LOCAL_SUBPROCESS` the key is two-way (`refused` refuses, `permitted` grants); at `HOSTED_SERVICE` it is narrowing only (`refused` refuses, `permitted` is a no-op) (FR-004). Any implementation in which a tracker key can widen egress **to spec-kitty's hosted service** is out of contract, and US5 scenarios 2 and 4 assert the widening case is impossible. Any implementation in which a tracker grant fails to satisfy the **local** destination independently of Channel 1 is equally out of contract, and US2 scenario 1 asserts it. **A third clause, added because the second revision would have violated it: any implementation that computes the destination from a configuration read is out of contract**, regardless of the answers it happens to give — the on-disk provider is overridden in memory by `--provider` (`service.py:84-98`), so a config-derived destination is wrong on live, operator-reachable commands. G5 pins this structurally; US5 scenario 4 pins it behaviourally. Reversing any of the three is an operator decision, not an implementer one. | Technical | High | Open |
| C-003 | No new `ConsentLevel` member | `PROJECT_CONSENT_PRECEDENCE` (`sync/consent.py:104-108`) is an ordered **authority** chain answering **one** question at descending authority, held in bijection with `LEVEL_RESOLVERS` by `_check_chain_is_dispatchable()`, which runs at import and raises rather than under-enforce. It is walked first-level-that-answers-wins, so a tracker key inserted there would *answer the hosted-sync question* — verbatim the `sync.auto_start` failure mode named at `consent.py:52-56`: *"Conflating them would let a daemon-autostart preference grant hosted-sync consent."* This Mission needs an AND-conjunct; the tuple expresses precedence. Different algebra. | Technical | High | Open |
| C-004 | No new `EgressConsent` member; the resolver contract is unchanged; the Channel-1 state is reporting-only | A new member would require widening `Callable[[Path], bool]` (`invocation/adapters.py:81`) — the registry manufactures the member from a bool, so a tracker-sourced member cannot exist without widening the callable, which forces sibling Mission Bundle B's open **Q3**. `permits_egress` remains the single place the verdict becomes a branch, and **Bundle B's Q3 stays closed**. **Resolving the contradiction the squad flagged 3/3** between this constraint and FR-012's three-state requirement: the enforced verdict has exactly **one** derivation — `project_egress_refusal` → `resolve_egress_consent` → `permits_egress` — and the three-way Channel-1 state is **reporting-only**. It is obtained by a separate classifier that (1) runs **only** on a path whose refusal has already been decided, (2) returns a label from a closed set of three and can return nothing else, and (3) is pinned non-authoritative by a test that forces every one of its three labels while Channel 1 permits and asserts the command still permits, plus one that makes it raise and asserts the refusal still prints with generic wording. Its inputs are `resolve_checkout_sync_routing_readonly(root).project_uuid` (present or not — the identity question, which `resolve_project_consent(None)` cannot answer because it reports `ABSENT` for both an absent record and an absent identity) and, when identity resolves, `resolve_project_consent(uuid, checkout_roots=[routing.repo_root]).level`. Using `ConsentDecision.level` **for a message** does not widen `EgressConsent` and does not touch the resolver contract; the rejected draft's claim that this Mission "never needs `ConsentDecision.level`" is amended to "never needs it **for the verdict**". **The classifier is recorded as debt, with a stated cause and a stated retirement condition.** *Cause:* it exists only to recover information the `Callable[[Path], bool]` port (`invocation/adapters.py:81`) discards — the registry manufactures an `EgressConsent` member from a bool, so *why* a project is refused is thrown away at the boundary and has to be re-derived on the side. *Retirement condition:* when that contract returns a decision **value** rather than a bool — Bundle B's open **Q3** — the classifier and both of its non-authoritativeness pins are **deleted**, not migrated. **This is carried in source, not only here**: FR-017 makes the module docstring of `egress_verdict.py` and the classifier function's own docstring named deliverables holding the cause, the retirement condition and the unregistered-consumer note — because Bundle B's implementer opens `src/specify_cli/tracker/` and `src/specify_cli/egress/`, and will never read `kitty-specs/`. **Two further properties it must satisfy.** (i) The `checkout_roots=[routing.repo_root]` form above is **the same root the registered resolver offers**, and is the only form specified anywhere in this dossier — an earlier `repo_root=root` spelling is superseded and must not be reintroduced. It is pinned by a test that invokes a checkout from a **subdirectory** and asserts the classifier's root and the resolver's root are equal; without it the classifier can report "no record" for a root the enforcer resolved differently, reproducing the *"tells the operator to do what they just did"* pathology this Mission exists partly to fix. (ii) The new module is an **unregistered runtime consumer of `specify_cli.sync.consent`**: it reaches around the registry indirection that keeps the package boundary clean, by call-time guarded import (NFR-003). That is a deliberate, recorded cost of keeping Q3 closed, not an oversight, and it retires on the same condition. | Technical | High | Open |
| C-005 | Two keyings, because two invariants — one representation each | Channel 1 keys on `project_uuid`, resolved from the checkout root via `resolve_checkout_sync_routing_readonly(root).project_uuid` and then membership in `consented_project_uuids` (`sync/__init__.py:362-372`); the root is an **input to** the resolution, not a substitute for it. Channel 2 keys on the project whose `.kittify/config.yaml` it is — a file read, no uuid join. One representation each of two invariants, not two of one. The authorising clause is `tracer-design-decisions.md:385-386`: *"the C-003 rule is one representation of one invariant, and these are two invariants."* (Quote the clause, not the ID: `#3030`'s C-003 is titled *"Journal carries no target/receiver identity"*.) The keyings differ because the **reach** of the questions differs: hosted-sync consent must be answerable for a project whose checkout has moved, been renamed or deleted — hence a uuid and a machine-global index — while the tracker question is only ever asked with the checkout in hand. Channel 2's keying is **not** the checkout-keying `#3030` condemned: `ConsentLevel.PROJECT_LOCAL` reads the project's own committed `.kittify/config.yaml` too, so Channel 2's keying matches level 1's exactly, and `#3030`'s consent-lives-in-the-project requirement condemned repo-**slug** keying, which Channel 2 does not use. | Technical | High | Open |
| C-006 | Falsifying preconditions | The design holds only while: (1) `build_connector` stays restricted to `("beads", "fp")` — otherwise `LocalTrackerService` becomes a second, differently-gated route to a third party and the two gates can disagree [**guarded**, FR-015 G1]. *Note what this precondition no longer carries:* the earlier revision called it "the sharpest failure this Mission can have" because a widened `SUPPORTED_PROVIDERS` would have made a config-derived polarity mis-classify a hosted destination as local. With the destination supplied as a literal by each call site (FR-004), that failure mode is **structurally impossible** and G1 now guards only the gate-divergence half. The sharpest failure moved to a different place, and it is guarded by **G5**; (2) `_build_engine` stays the sole connector-construction site and its callers stay exactly the three gated methods [**guarded**, FR-015 G2, G3]; (3) the tracker path stays **operator-invoked** — if any daemon, sweep, hook or `next`-loop reaches `LocalTrackerService`, the attribution precondition at `tracker/egress_consent.py:64-129` is violated (a **valid** root for the **wrong** project), which is exactly the cross-project substitution `#3030` exists to close [**prose**; re-check required of any Mission adding an automatic caller]; (4) `bd`/`fp` remain local — if either becomes a network client, FR-004's local half loses its justification and the polarity must be revisited (C-012.1); (5) the SaaS tracker path keeps sending to spec-kitty's hosted service rather than direct to Jira — if that ever inverts, FR-004's SaaS half loses *its* justification in the opposite direction; (6) absence keeps denying at Channel 1 — if a future Mission restores absence-permits for hosted sync, Channel 2 becomes the only tracker refusal on SaaS bindings. | Technical | High | Open |
| C-007 | Test patch sites: `from X import f` rebinds by value | Measured at `bb2020fea`. `project_egress_refusal` is bound **by value** into its consumers (`tracker/saas_client.py:34`, `saas_client/client.py:23`): after patching `specify_cli.tracker.egress_consent.project_egress_refusal`, `TSC.project_egress_refusal is TE.project_egress_refusal` → **`False`**. So a test asserting a tracker refusal must patch **the deciding module's** name, never the defining module's. **The hosted path has two targets and they apply at different times, because FR-016 deletes the first:** before the swap, `specify_cli.tracker.saas_client.project_egress_refusal`; **after** the swap, `specify_cli.tracker.saas_client.tracker_egress_verdict`. A recipe naming only the first is correct on the base and inert on the delivered tree — which is the shape of a mutation that silently lies. The local path's target is whatever name `local_service.py` binds `tracker_egress_verdict` under, throughout. The split is not uniform and must be reported **per site**: `specify_cli.invocation.resolve_egress_consent` (`invocation/__init__.py:23`) and `specify_cli.invocation.propagator.resolve_egress_consent` (`propagator.py:38`) are module-level `from … import` and do **not** observe a patch on `invocation.adapters` (measured `False`), while the call-time import inside `tracker/egress_consent.py:178` **does** (measured: flipped refuse→permit). | Technical | High | Open |
| C-008 | `saas_client/egress_consent.py:92` is a **second definition**, not a re-export | Measured: different `id`, different `__module__` from `tracker/egress_consent.py:147`. Near-duplicated **by declared necessity** (`saas_client/egress_consent.py:33-36`): *"the two packages share no parent inside this change's scope […] What is duplicated is the **call**, not the chain."* This Mission adds no third definition; `tracker_egress_verdict` is defined once, in `tracker/`, and the `saas_client/` package is not touched. Recorded separately from C-007 because conflating a second definition with a re-export produces a patch-site table that is wrong for one of the two. | Technical | Medium | Open |
| C-009 | Bundle B moves this Mission's call sites | When Bundle B deletes `tracker/egress_consent.py` and moves it to `specify_cli.egress`, **`tracker_egress_verdict`, `EgressDestination`, Channel 2's resolver, the module-local sentinel and all five call sites move with it.** Recorded so the move is a rename rather than a rediscovery — and so FR-015 G4's exact-membership assertion (5 enclosing functions, 6 call expressions) and G5's literal-member assertion are understood as things Bundle B must update, not things Bundle B may let fall to zero. | Technical | Medium | Open |
| C-010 | `local_service.py` cannot be egress-allowlisted, and must not be added | It holds zero HTTP sinks (measured: 0, against a control of 8 in `saas_client.py`, over 1198 scanned files). `tests/architectural/test_egress_consent_boundary.py::test_every_listed_file_still_holds_a_sink` (`:792-805`) deletes entries that guard nothing, so an allowlist entry would be removed by the guard itself. No `_baselines.yaml` bump (`egress_allowlist_files: 28`) is needed or permitted. | Technical | High | Open |
| C-011 | Measurement discipline, binding on every claim this Mission makes | Never pipe a suite whose exit status is to be trusted — `pytest … \| tail` reports `tail`'s status and buffers until exit; quote the `N passed` line, and **an empty output file is no measurement**. A killed run is neither a pass nor a fail: re-run narrowed, do not explain it. Measure in a `git worktree` pinned to a commit **and set `PYTHONPATH=$WT/src`** — this repository's editable install hard-codes the main checkout's `src` path, so a worktree run otherwise imports the live tree and any "identical results" conclusion is a tautology. Read the failure text, not the tally. Print the input count alongside any "all checks passed" — a gate that ran on zero files passes vacuously. Red first, and make the red the **consequence**: assert the bytes, not a boolean. Include a positive control that must pass. Any assertion of absence must establish why the thing would otherwise have happened. Mutations are pytest plugins injected via `PYTHONPATH`, never source edits. Stage with explicit paths (`git add <paths>`), never `git add -A`. **Citations are revalidated before they are trusted.** Roughly forty exact line citations in this dossier are pinned to `bb2020fea`, while implementation is deferred to a later base. Before any implementation work: record the **actual base SHA**; run `git diff --stat bb2020fea..<base>` over `src/specify_cli/tracker/`, `src/specify_cli/sync/`, `src/specify_cli/cli/commands/` and `src/specify_cli/invocation/`; and **re-derive every cited line by symbol name (`grep`), never by line number**. A citation whose line moved is a bookkeeping fix; a **symbol that moved semantically** — a changed signature, a relocated gate, a changed default — is a **re-plan trigger**, not something to patch in passing. | Process | High | Open |
| C-012 | Blast radius, named before the work starts | (1) `tests/sync/tracker/test_local_service.py:235,262,287` — `TestSyncOperations` binds a `beads` provider into a fixture repo with **no consent record at either channel** and then calls `svc.sync_pull/push/run`, so FR-001's gate makes all three **red**. They are repaired by committing `tracker: {egress: permitted}` into the fixture repo — one line, no machine-global state, and the Channel-2 local grant is what makes that possible — **not** by patching out the gate (FR-018 H2). (2) `tests/cli/commands/test_sync_doctor_consent_health_3030.py:366` — an exact count over the whole rendered output (FR-014). (3) `tests/sync/test_consent_fault_vocabulary_3030.py:261` — `CONFIG_FAULT_KINDS` pinned by exact equality; not extended. (4) `saas_service.py:219` and `:316` are blast radius that **looks like a reference pattern**: they preserve `egress` today only because it rides in `_extra`, and FR-002's promotion to `_KNOWN_KEYS` breaks them (FR-011 class B). Any revision that cites them as "the pattern to copy" without also fixing them is citing a mechanism it is simultaneously destroying. (5) **`tests/specify_cli/` entered the blast radius with `saas_service.py` and was previously absent from every artifact.** `tests/specify_cli/tracker/test_binding_report_only.py:254-268` holds `test_apply_binding_upgrade_preserves_extra_fields`, which asserts `svc._config._extra == {"future_flag": True}` — the forward-compat `_extra` contract at **`saas_service.py:219`, the exact line B1 modifies**; `tests/specify_cli/sync/test_worktree_clean_invariant.py:22` documents the `apply_binding_upgrade` / `bind` write boundary this Mission now touches. Measured together: **`35 passed in 54.65s`, exit 0**. That test is a **detection signal, not a planned edit**: `_extra` must keep carrying `future_flag` after `egress` stops riding in it. If it reds, the B1 fix dropped the `_extra` carry instead of adding an `egress` carry beside it — do not "repair" it by weakening the assertion. (6) Baselines measured green at `bb2020fea`, unpiped, exit status trusted — **each carrying a predicted delta, because a re-measurement without a prediction has no control**: the six consent/boundary suites `154 passed in 51.31s` — **movement expected**, because the set includes `tests/architectural/test_egress_consent_boundary.py`, the file `#3113` modifies; `tests/architectural/test_egress_consent_boundary.py` alone `27 passed in 77.30s` — **movement expected**, same reason; `tests/sync/tracker/ tests/agent/cli/commands/test_tracker.py` `519 passed, 1 warning in 64.73s` — **unchanged expected**; `tests/cli/commands/test_sync_doctor_consent_health_3030.py` `15 passed in 54.64s` — **unchanged expected**; and **`tests/specify_cli/` `35 passed in 54.65s` — unchanged expected**. **The two "movement expected" predictions are stated with direction and cause, because "movement" alone is satisfied by any number:** the count **increases**, by the tests `#3113` adds to `test_egress_consent_boundary.py`. A **decrease**, or **any** movement when `#3113` has *not* landed, is a stop-and-attribute event — as is an unpredicted movement in any of the other three. Any red beyond C-013's roster and item (1) above is a regression this Mission owns. | Technical | High | Open |
| C-013 | Known pre-existing failures are not this Mission's to green | Red at `bb2020fea` and must not be required green: `tests/architectural/test_tid251_enforcement.py` (4 tests); `test_charter_package_exports::test_charter_package_cold_import_keeps_status_orchestration_out`; two `test_safe_commit_cmd::…_3033`; `test_charter_io::test_get_mission_id_returns_none_when_meta_json_malformed`; `test_doctor_ops::test_sweep_nfr_002_10k_files_under_5s` (wall-clock). `ModuleNotFoundError: No module named 'typer'` in subprocess daemon tests is environmental. Per the charter's Pre-existing Failure Reporting Rule, any *newly* encountered pre-existing failure is filed as an issue before being treated as baseline. | Process | High | Open |
| C-014 | Chain B is named, not touched, and filed | `sync/routing.py:178-252` `_build_checkout_sync_routing` → `is_sync_enabled_for_checkout` (`routing.py:255`) answers a version of *"may this data leave"*, honours the **repo-slug-keyed** `[sync.repo_defaults]` record that `consent.py:99-103` explicitly refuses (*"One was added on 2026-07-30 and removed the same day"*), and is live on a real egress gate at `sync/batch.py:1070` (via `_is_checkout_sync_enabled_for_batch`, `:334-339`), plus `sync/runtime.py:106` and the `routing.effective_sync_enabled` reads at `cli/commands/sync.py:1964,2081`. Three source comments explain why the good path avoids it; nobody has removed it. **This Mission does not add a third answerer** — Channel 1 reuses `project_egress_refusal` → Chain A — and it does not touch Chain B, because Chain B answers hosted-sync fan-out rather than tracker egress, its blast radius is the drain and the daemon, and folding it in would be a second Mission wearing this one's branch. But a Mission premised on *"one key answering two questions"* must name the place where **one question is answered by two chains**. Recorded as a constraint; **a follow-up issue is to be filed**, not absorbed — and **filed before implementation starts**. **Framing matters here, and the earlier framing was wrong.** The issue is *not* "consolidate two consent chains" — that is large, unbounded, and gets deferred forever. It is ***"finish `#3030`'s Chain-B migration at the two remaining enforcement sites"***: small, bounded, and gets done. `#3030` already migrated three modules off Chain B and left in-source rationale at each — `sync/body_upload.py:66-88`, `sync/emitter.py:65`, `invocation/adapters.py:51`, plus the argument at `sync/__init__.py:346`. **Two enforcement sites remain**: `sync/batch.py:338` (`_is_checkout_sync_enabled_for_batch`, reached from the drain gate) and `sync/runtime.py:106`; plus **two display-only reads** of `routing.effective_sync_enabled` at `cli/commands/sync.py:1964,2081`. The **named canonical replacement** is `sync/body_upload.py::project_consents_to_hosted_sync` (`body_upload.py:54`, rationale `:60-88`) — the uuid-keyed question the migrated sites already ask. **The reachability sentence the issue must carry, because it is what makes this urgent rather than tidy:** `_build_checkout_sync_routing` falls through to `SyncConfig().get_repository_sync_enabled(repo_slug)` (`routing.py:194-200`) when both the project-local and the checkout-local records are `None`, and `enable_checkout_sync` writes that **repo-slug-keyed** record on **every** opt-in (`routing.py:325`) — **so a fresh clone of an already-opted-in repository drains events that Chain A denies.** | Technical | Medium | Open |
| C-015 | Explicit non-goals | Out of scope, recorded rather than forgotten: the `LocalTrackerService.sync_publish` `AttributeError` (`TrackerService.sync_publish` at `service.py:202-203` delegates unconditionally; `_run_or_exit` catches only `RuntimeError`/`ValueError`, and `isinstance(e, (RuntimeError, ValueError))` is `False` for it) — **file it, do not absorb it**; an audit of `_extra`'s consumers; establishing whether `bd`/`fp` are network clients; Chain B (C-014); unifying the two refusal exception hierarchies (FR-012); adding tracker-egress state to `tracker status` — no longer deferred *because a second verdict would drift*, since FR-003 makes one verdict available to any caller, but deferred because the `tracker` group is conditionally registered and therefore the wrong surface for the diagnostic (US7); and the server-side half of anything. `SPEC_KITTY_ENABLE_SAAS_SYNC` remains **arming and never a grant**, and this Mission neither strengthens nor weakens it. | Technical | Medium | Open |
| C-016 | Separability, and the direction still not delivered | Delivered: **permit hosted sync, refuse tracker** (US1) and **refuse/never-record hosted sync, permit the local tracker** (US2). Not delivered: **a SaaS tracker binding without hosted-sync consent** — Channel 1 remains a hard prerequisite there by FR-004, because the destination is spec-kitty's hosted service. Stated in the upgrade note (FR-013) as a decided limitation, not an oversight. | Technical | High | Open |
| C-017 | Raised and judged wrong — recorded so it is not re-raised | (1) *"Channel 2 reintroduces the checkout-keying `#3030` condemned."* Withdrawn by the lens that raised it; see C-005's closing clause. (2) *"`write_local_sync_enabled` is a project-local writer, so the breaking-change framing is wrong."* Checked and retracted: `routing.py:283-285` delegates to `SyncConfig().set_checkout_sync_enabled` — **machine-global**. The name is the trap, not the spec. (3) *"Both the `ConsentLevel` and `EgressConsent` rejections are convenient rather than sound."* Steelmanned by two lenses; **both rejections survived**, on the grounds now recorded in C-003 (algebra) and C-004 (registry contract). C-004's conclusion survives; only its originally stated justification did not. | Technical | Medium | Open |
| C-018 | Where the gate sits, and what a later reader must not do with it | The gate is ahead of `_load_runtime` (FR-001), which is why NFR-002 can assert zero local side effects. **Moving it back to `_build_engine` reintroduces, on a refused command: a machine-global credential-store read, and a `TrackerSqliteStore` construction that `mkdir`s and creates a SQLite file with three tables (`store.py:278-281`)** — no egress, so every NFR about bytes still holds, which is exactly why the move would look harmless. It also re-breaks the unparseable-config behaviour, because `load_tracker_config` raises first (`config.py:148-149`) — now pinned at the unit level rather than through the CLI (C-021). Recorded so that *"zero argv"* is not mistaken for *"zero effects"*, and so that a later move is a decision someone has to argue for. | Technical | High | Open |
| C-019 | Stated limits, carried forward unresolved | (1) **Whether `bd` or `fp` themselves make network calls is UNVERIFIED and unresolvable from this repository.** `spec_kitty_tracker` invokes them as opaque executables (`cli_runner.py:22`); neither binary is installed here, neither is vendored, and the executable name is operator-overridable (`factory.py:56`). The squad's fake-`bd` harness proves what argv *would* be handed to the real one, not what the real one does with it. The gate is defensible either way, but the **severity is not established**. (2) **Whether E20 was accurate against an earlier commit is not established** — `local_service.py`'s last three touches (`3b313b6d1`, `2db24b362`, `02f78b034`, the PRI-16 SaaS-mediated CLI tracker reflow) were not diffed to see whether `build_connector` once supported jira/linear. (3) **Whether any consumer reads `TrackerProjectConfig._extra`** was not checked — relevant, because a raw `egress` value would otherwise land in that block; C-001's known-field placement is the mitigation, not the answer. (4) **`#3030`'s "seven independent places" of FR-003 violation** is unreconstructed — the brief says seven, module docstrings say "four" (`tracker/egress_consent.py:60-61`) and "fourth independent occurrence". (5) Test-suite health beyond the suites in C-012 item (4) is unknown; the full suite was not run. | Technical | High | Open |
| C-020 | A typo fails closed, and says what to type instead | The closed value set means an operator typo — `tracker: {egress: refuse}` (singular), `Refused`, `deny`, or a stray `true` — is a **fault, and a fault refuses**. **This is intended, not a side effect**: on a confidentiality control the only safe reading of a value nobody defined is refusal, because the alternative is a mis-spelling that silently permits. The cost is that a typo can take a working local binding offline, and the mitigation is the message, not a looser decode: the fault text must **name the offending value verbatim and name both legal values**, so the operator fixes it without guessing and without reading source. Pinned by a test asserting the offending token and both of `refused` and `permitted` appear in the printed fault for every near-miss in FR-010's probed set, and by SC-010's requirement that each fault names the key and quotes the raw value. The same wording is what `sync doctor` renders for that checkout (FR-014), on **both** destination rows, so the diagnostic surface and the failing command tell the operator the same thing. | Technical | High | Open |
| C-021 | The unparseable-config acceptance scenario is **cut**, and here is why it is not being fixed a fourth time | An acceptance scenario asserting that `spec-kitty tracker sync push` prints a fault refusal for a project whose `.kittify/config.yaml` cannot be parsed **cannot be written end to end through the CLI at `bb2020fea`, and has now been wrong in three successive forms.** The reason is `_is_local_binding()` (`cli/commands/tracker.py:280-293`): it wraps its `load_tracker_config(require_repo_root())` in `with suppress(Exception)` and returns `False` on any failure. So for an unparseable file `_check_sync_readiness` (`:296-312`) takes the **SaaS** branch, `LocalTrackerService` is never constructed, and the new gate is never reached through the CLI at all — while this spec's own harness contract requires acceptance to run end to end through the CLI (FR-018). The behaviour itself is **not** dropped: the *fault-refuses* property is pinned at the **unit** level against `tracker_egress_verdict` directly, for both destinations, as part of NFR-003's probed set. **Cut rather than re-fixed**, because a scenario that has been re-authored three times and is unreachable for a structural reason in a file this Mission does not touch is a defect in the scenario, not in the gate. Changing `_is_local_binding`'s exception handling to make the scenario reachable is explicitly out of scope (C-015) — it would alter readiness behaviour for every local command to buy one acceptance test. | Process | Medium | Open |

### Key Entities

- **`tracker.egress`** — the new key. Located in the `tracker:` block of the project's own
  `.kittify/config.yaml`; a **closed set of two strings, `refused` and `permitted`**, with **absence
  spelled as the key being missing**. On `TrackerProjectConfig` it holds the **raw loaded value** plus
  a derived fault, with a module-local sentinel for "not present". **Why this name and this shape**,
  since the brief requires the choice to be justified rather than assumed:
  - *Why a tri-state rather than a boolean.* Channel 2 has **three** things to say — refuse, permit,
    say nothing — and a boolean has two slots for them. Under a boolean, `false` has to carry
    *"permitted"*, so **absence and a recorded value share the meaning "not refused"**: the operator
    reading the file cannot see the difference between a project that decided and a project that
    never did, and neither can a reviewer. That conflation is the defect this whole Mission exists to
    close at Channel 1, where absence-is-not-consent is the incident's own lesson; reproducing it in
    the new key would have been the Mission arguing against itself. Three states, three spellings.
  - *Why not a boolean with a negative name.* `egress_refused: false` is a **double negative on a
    confidentiality control** — the reader has to compose "not refused" with "the destination decides
    whether that also grants" to arrive at the meaning, and the shortest wrong reading ("this project
    permits tracker egress everywhere") is exactly the belief FR-004 exists to prevent. `permitted`
    says what it does on the path where it does it, and the SaaS no-op is then a statement the message
    and `sync doctor` make (FR-005, US5 sc2) rather than an inference the operator has to draw from a
    negation.
  - *Why `refused`/`permitted` rather than `deny`/`allow` or `off`/`on`.* `refused` and `permitted`
    are the words the refusal messages, `project_egress_refusal`'s contract (*"`None`, and only
    `None`, is permission"*) and `sync doctor` already use for this verdict, so the file, the error and
    the diagnostic read as one vocabulary. `off`/`on` would be a state, not a decision, and would
    invite the YAML 1.1 truthiness the closed set exists to keep out.
  - *Why not spelled `enabled`, for uniformity with `sync.enabled`.* `#3030` canonicalised on
    `enabled` because three spellings of **one** invariant had accumulated. Here there are **two**
    invariants (C-005), and they disagree on absence: `sync.enabled`'s absence **denies**,
    `tracker.egress`'s absence **records nothing**. Two keys spelled alike that answer absence
    oppositely is a sharper trap than two keys spelled differently — and `enabled` is a boolean name,
    which would reintroduce exactly the two-slot problem above.
  - *Why `egress` rather than `sync` or `push`.* The key governs everything that leaves the machine on
    this path — `push` writes titles, `pull` executes an operator-named binary, `run` does both.
    Naming it after one direction would invite a reader to conclude the other is ungoverned.
  - *Why the value set is closed, and why that is the bool rule kept rather than abandoned.* The
    bool-only argument at `sync/consent.py:196-241` is, in substance, a rule about **closed
    decoding**: every spelling you accept is one more thing the table has to rule on, and on this key
    each accepted spelling would manufacture a **grant**. A two-member string set is as closed as
    `bool` and closed in the same way `CONFIG_FAULT_KINDS` is; unknown values are a **fault that
    refuses** (C-020), with no case-folding and no synonym table, so a string enum reintroduces
    nothing the bool rule was written against. A fault is *reportable*, and C-020 requires the report
    to name the offending value and both legal ones.
- **Channel 1 — hosted-sync egress consent** — `project_egress_refusal(project_root)`
  (`tracker/egress_consent.py:147`). `None`, and only `None`, is permission. Keyed on `project_uuid`.
  Absence denies. Unchanged by this Mission except for gaining a caller and a reporting-only
  classifier beside it.
- **Channel 2 — tracker egress decision** — a new resolver reading `egress` from the project's own
  config. Returns one **Channel-2 value** from {absent, `refused`, `permitted`, fault}, carrying the
  raw value. Never raises. Not to be confused with the **Channel-1 state** triple (FR-005's
  vocabulary note).
- **`EgressDestination`** — the new closed two-member set naming *where the data would go*, and the
  reason FR-004's polarity is checkable rather than remembered.
  - `LOCAL_SUBPROCESS` — an executable named by the operator's own machine-global credential file
    (`factory.py:56`), invoked as a subprocess with issue fields as argv. spec-kitty's SaaS is not
    involved.
  - `HOSTED_SERVICE` — spec-kitty's own `/api/v1/tracker/…` endpoints, bearer token plus
    `X-Team-Slug`, base URL from `resolve_runtime_target().resolved_server_url` (`saas_client.py:247`).
  - **Why a parameter rather than a derivation.** It is not derivable from the project's committed
    config: `--provider <saas>` makes `_resolve_saas_backend_for_provider` (`service.py:84-98`)
    override the provider **in memory** and route to the hosted client while the file still says
    `beads`. Deriving it would make `permitted` a hosted grant for the exact operator US2 serves.
  - **Why required and keyword-only.** A default would let a call site omit it and inherit a polarity
    silently; positional would let two members be transposed at a call site without a type error.
    Required-and-keyword-only makes both `mypy` errors, and G5 makes a computed value a guard failure.
  - **It carries a docstring, and the docstring is a deliverable** (FR-017). No guard *decides*
    polarity for a **new** transport: adding a third member makes G4's membership assertion fire —
    whose obvious resolution is to edit the guard — and **pointing an existing member at a new
    transport fires nothing at all**, because the argument is still an `Attribute`, the literal set is
    still the same two, and G5's per-site clause still names only the four existing sites. So the
    requirement is placed where the developer will actually read it: the enum's docstring states that
    **adding a member, or repointing an existing member at a new transport, requires an operator
    decision on that member's Channel-2 polarity**, and names FR-004 as where that decision is
    recorded.
  - **Import form.** Imported under its own name (`from … import EgressDestination`). An aliased
    import makes each `destination` argument an `Attribute` on the alias and G5 reports non-literal —
    a false red. Loud, not silent, but written down here because it is load-bearing on a guard.
- **`tracker_egress_verdict(root: Path | None, *, destination: EgressDestination)`** — the single
  join (FR-003). Consumes both channels **and the destination its caller names**, applies FR-005's
  8-cell table, and returns the value object that the two gates raise from and `sync doctor` renders.
  It **never reads the provider** and carries **no binding-kind field**. Five enclosing call sites in
  `src/`, six call expressions.
- **The local gate** — the first executable statement of `LocalTrackerService.sync_pull`, `sync_push`
  and `sync_run`, ahead of `_load_runtime`, each passing `LOCAL_SUBPROCESS` as a literal. Written out
  at each site: **no `_require_egress` helper**, because a helper would satisfy G3's "first statement"
  property with a call to the helper and stop pinning `tracker_egress_verdict` at all.
- **The hosted chokepoint** — `SaaSTrackerClient._request` (`saas_client.py:329-331`), before
  `_fetch_access_token_sync()`, unchanged in position and in Channel-1 behaviour, passing
  `HOSTED_SERVICE` **unconditionally**.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With `tracker.egress: refused` recorded, hosted-sync consent granted, and **the store
  seeded** with an issue titled `ACME Holdings carve-out`, a `beads` push produces **0** captured argv
  and **0** occurrences of the title across all captured argv elements. Fails on `bb2020fea` at
  Mission start, with the red being the captured title itself rather than a boolean.
- **SC-002**: The paired consenting control produces exactly **3** captured argv — `list`, `create`,
  `show` — the second containing the title verbatim as an element. Passes on `bb2020fea` and after.
  Without SC-002, SC-001 is unfalsifiable; and without the **seeded store**, SC-002 itself captures
  only `1` argv and no sentinel, which is the fourth measured false-green (FR-018 H8).
- **SC-003**: SC-001/SC-002 hold for **each** of `sync pull`, `sync push`, `sync run` — three refusing
  cases and three controls, each exercised end to end. For `push` and `run` the control asserts the
  title verbatim; for `pull` the control asserts argv shape `[<command>, "--json", "list", …]`. Every
  refusing case asserts **zero captured argv**.
- **SC-004**: With no record at either channel, the command refuses, exits non-zero, and the printed
  text names the Channel-1 state as **no record found** and carries all three remedies. Applying each
  remedy in turn to that fixture and re-running makes the title reach the recorder — asserted by
  **execution**, not by substring.
- **SC-005**: On a `jira` binding, `tracker.egress: permitted` with hosted-sync consent absent
  still refuses with **0** HTTP attempts, and the message states that the recorded tracker grant does
  not apply at `HOSTED_SERVICE`. **Paired with a mutation pin:** with Channel 2 removed entirely by a
  `PYTHONPATH`-injected plugin, US1 scenario 1 goes **red** while SC-005 stays **green** — which is
  the proof that SC-005 alone cannot carry the Mission and SC-001 is the criterion that does.
- **SC-005a**: With **on-disk `provider: beads`**, a committed `tracker: {egress: permitted}` and
  hosted-sync consent **absent**, `spec-kitty tracker list-tickets --provider jira` **refuses** with
  **0** HTTP attempts and a message naming **Channel 1** — paired with the positive control (on-disk
  `provider: jira`, Channel 1 granted, no tracker key, same command → reaches `No valid access
  token`), so the zero-count is not vacuous. **This is the criterion that discriminates a
  destination-as-parameter implementation from a destination-as-derivation one**: the latter reads
  `beads` from disk, applies the local half, and grants.
- **SC-006**: On a `beads` binding with **no** hosted-sync record and `tracker.egress: permitted`
  committed, the title reaches the recorder; removing that one line makes the same command capture
  zero argv. The two fixtures differ by exactly one committed line.
- **SC-007**: A checkout whose project identity does not resolve refuses with the **not consentable**
  wording and `spec-kitty init` as its Channel-1 remedy; applying `spec-kitty init` and then either
  Channel-1 remedy, or applying the Channel-2 grant alone, makes the title reach the recorder on
  re-run.
- **SC-008**: `spec-kitty tracker bind` on a project with no tracker key writes a `tracker:` block
  containing **no** `egress` key at all — absence stays spelled as the key being missing, never as a
  written-out null; and for **every** value in the probed set — **exactly 15**, enumerated once in FR-010 and nowhere
  re-enumerated: `refused`, `permitted`, `"refused"`, `'permitted'`, `Refused`, `REFUSED`, `refuse`,
  `deny`, `true`, `false`, `0`, `null`, empty string, mapping, list — a `bind` round-trips the
  `egress` line **byte-identically**. The parametrised test **prints and asserts its own case count
  is 15**.
- **SC-009**: `spec-kitty tracker unbind` on a project with a committed `egress` leaves the key
  present with its value unchanged and every other `tracker:` key gone — asserted for **both**
  `refused` and `permitted`; on a project without the key it removes the `tracker:` block entirely;
  and the sibling `sync:` block survives all three, as the control.
- **SC-010**: Every value in the probed set outside the closed pair — including the near-misses
  `Refused`, `REFUSED`, `refuse`, `deny`, the wrong types, and **a mapping and a list at the key** —
  refuses at **both** destinations without raising, and each is reported as a fault that names the
  key, quotes the offending raw value verbatim, and names **both** legal values `refused` and
  `permitted` (C-020). The probed set is a set, not the first shape that surfaced.
- **SC-011**: A refused tracker command records **0** HTTP attempts on the `httpx.Client.request`
  trip-wire and **0** `subprocess.run` invocations. On the **seeded** pair it leaves the tracker db
  file **byte-identical** (digest before == digest after) while the consenting control's digest
  changes; on the **unseeded** pair (US3 sc4) it leaves **no** file at the resolved db path while the
  consenting control creates one. All four assertions are proven to bind by their controls.
- **SC-012**: The gate's bind counter is **non-zero**, asserted per test, **per destination** — a
  wrapper on the name `local_service` binds asserted in the local-destination cells, and a second on
  `specify_cli.tracker.saas_client.tracker_egress_verdict` asserted in the hosted cells. One test
  proves the counting wrapper does not change any outcome. **The drain scenario is exempt, and the
  exemption is written in the file with its reason:** it reaches neither gate, so a counter assertion
  there could only ever be 0. *(Corrected 2026-08-01 — the earlier wording said "in every acceptance
  test". The hosted cells never call the name `local_service` binds and the drain scenario calls
  neither, so that reading was unsatisfiable by any work package: the acceptance file's owner cannot
  make it true, and the packages judged against it own no test file. An unsatisfiable criterion is
  discharged either by permanently red cells or by an implementer silently narrowing "every" — which
  is the requirement evaporating without a trace.)*
- **SC-013**: In every refusing acceptance test the matched refusal text is **not**
  `saas_sync_disabled_message()`, and `SPEC_KITTY_ENABLE_SAAS_SYNC=1` is set explicitly in the
  fixture.
- **SC-014**: `sync doctor` renders seven distinguishable tracker-egress blocks — refused by
  `tracker.egress: refused`, refused by a tracker-key fault (naming the offending value and both legal
  values, C-020), refused by Channel 1 in each of its three states, `tracker.egress: permitted`, fully
  permitted — each block carrying **one row per destination**, for **14** rows in total; prints the
  block in all seven checkouts; and each row's rendered verdict equals the verdict enforced at that
  destination, field-for-field. At least one checkout renders **two different answers on its two
  rows** (Channel 2 `permitted` + Channel 1 absent → local permitted, hosted refused), which is the
  assertion a one-row block cannot satisfy. The new block contributes **0** to
  `flat.count("REPAIR THE FILE'S SYNTAX")` and never prints `This is NOT a missing consent record`.
- **SC-015**: `len(_JOIN) == 8` as a structural assertion **and** all 8 cells exercised by one
  parametrised test that prints and asserts the number of cells it ran is exactly 8. The structural
  half survives a test being deleted; the behavioural half survives an entry being wrong.
- **SC-016**: The hosted path reproduces its three measured Channel-1 outcomes with
  **byte-identical** refusal text (absence → refused; recorded `false` → refused; recorded `true` →
  gate passes to the token check), plus `root=None` → `UNDETERMINED_PROJECT_REFUSAL` byte-identical;
  and the local and hosted raise sites produce byte-identical text for the same Channel-1 state.
- **SC-017**: All **six** falsity guards (FR-015 G1–G6) assert exact membership and an exact count,
  print a non-zero input count, and each fails against **synthetic mutated source** passed to the
  guard's analyzer callable — never a source edit — with the killed-pin count reported. **G4 and G5
  each kill three mutants**: (i) a call site whose `destination` is a name bound from a config read;
  (ii) for **G5**, a call site with the two literals swapped **in place**, and for **G4**, a **sixth**
  call site carrying a swapped literal — *(corrected 2026-08-01: an in-place swap leaves both of G4's
  counts unchanged, so it cannot kill G4; the per-site mapping is G5's clause. Where this shared
  sentence and a guard's own mutant table disagree, the table governs, and a killed-pin count is
  never lowered to clear the gate.)* and (iii) **a sixth call site written
  module-qualified** (`ev.tracker_egress_verdict(…, destination=ev.EgressDestination.…)`), which is
  the form measured to pass a `ast.Name`-only matcher. **G6 kills one**: a provider read reintroduced
  into `egress_verdict.py`. A guard that kills only mutants (i) and (ii) has not been proven — it has
  been proven against the two mutants that share its blind spot.
- **SC-018**: `CHANGELOG.md` carries a Breaking Changes entry and `docs/migrations/` carries the
  upgrade note, linked from `docs/migrations/index.md`; the anchor check fails when the section is
  removed or renamed.
- **SC-019**: The **five** docstrings named in FR-017 — three amended (`local_service.py:8`,
  `_check_sync_readiness`, `_check_binding_readiness`) and two authored (`egress_verdict.py`'s module
  docstring, the Channel-1 classifier's docstring) — carry their required sentences, pinned by one
  test so a revert of any of them reds. The two authored ones are asserted to contain the literal
  string `invocation/adapters.py:81`, the word `Q3`, and the words `delete` and `not migrate`, so the
  retirement condition cannot be softened into a "consider revisiting".
- **SC-020**: `tests/sync/tracker/test_local_service.py::TestSyncOperations` is green with its fixture
  repaired by a committed `tracker: {egress: permitted}` and with `_build_engine` still patched
  only for its own delegation assertions — and the acceptance suite for this Mission patches
  `_build_engine` **nowhere**, asserted by a grep-based pin over the new test files with its input
  count printed.

### Reconciliation note — 2026-08-31 (#782)

The executable G4 guard is the current authority: the census is **five enclosing functions and five call expressions** — the three local sync gates, `SaaSTrackerClient._current_tracker_egress_verdict`, and `_check_sync_readiness`. Earlier references to `_request`, the deleted sync-doctor renderer, or a sixth expression are retired historical prose. FR-004's unconditional hosted literal belongs to `_current_tracker_egress_verdict`, not `_request`.
