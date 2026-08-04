# Tracer: evidence base — tracker-egress-refusal-3108

**Authored against:** `bb2020fea` (upstream/main, 2026-07-31 08:52), fresh clone at
`/home/jeroennouws/dev/sk-missions/3108`. Every claim below was read or executed at that
commit. Where this file and the `#3030` dossier disagree, **the code at `bb2020fea` wins**
and the disagreement is stated explicitly rather than reconciled silently.

---

## 0. The finding that reframes the mission

Issue `#3108` and `kitty-specs/journal-project-consent-3030-01KYKWQS/egress-inventory.md:243-272`
(entry **E20**) both assert:

> `tracker/local_service.py` sends project data (issue titles, items) to Jira/Linear.
> […] Most tellingly: **a project with a committed `sync.enabled: false` — an explicit
> refusal — can still push its issue titles to Jira.**

**Both sentences are false at `bb2020fea`.**

### Measured, not inferred

Isolated `HOME`, HTTP trip-wire installed on `httpx.Client.request`, positive control included:

| project-local `.kittify/config.yaml` | `SaaSTrackerClient.push(provider="jira", …)` |
|---|---|
| no record (absence) | **REFUSED**, `error_code=project_consent_denied`, no HTTP attempted |
| `sync: {enabled: false}` | **REFUSED**, `error_code=project_consent_denied`, no HTTP attempted |
| `sync: {enabled: true}` | gate passed → failed later at `No valid access token` |

The third row is the **positive control**: it distinguishes "the gate refused" from "the harness
never reached the code". Without it, rows 1–2 would be indistinguishable from a broken probe.

### Why the claim is false — the routing

- `src/specify_cli/tracker/factory.py:17` — `SUPPORTED_PROVIDERS: tuple[str, ...] = ("beads", "fp")`.
  `build_connector` raises `TrackerFactoryError` for anything else (`factory.py:38-39`).
  **`LocalTrackerService` cannot construct a Jira or Linear connector.**
- `src/specify_cli/tracker/config.py:19` — `SAAS_PROVIDERS = frozenset({"linear", "jira", "github", "gitlab"})`;
  `config.py:20` — `LOCAL_PROVIDERS = frozenset({"beads", "fp"})`.
- `src/specify_cli/tracker/service.py:77-80` — `_resolve_backend` sends `SAAS_PROVIDERS` to
  `SaaSTrackerService`, `LOCAL_PROVIDERS` to `LocalTrackerService`.
- `src/specify_cli/tracker/saas_service.py:109` — `self._client = client or SaaSTrackerClient(project_root=repo_root)`.
- `src/specify_cli/tracker/saas_client.py:329-331` — **the gate**, at `_request`, the single
  chokepoint all 13 endpoints and the operation poller pass through, placed **before**
  `_fetch_access_token_sync()`:

  ```python
  refusal = project_egress_refusal(self._project_root)
  if refusal is not None:
      raise TrackerEgressRefusedError(refusal)
  ```

- `local_service.py:8` (the file's own header) — *"No SaaS imports live here — only local
  connector infrastructure."*

`#3030`'s **FR-029** shipped this. So *"key tracker egress through the existing consent chain"*
is not a proposal — **it is the status quo.**

---

## 1. What the real gaps are

### Gap A — no separability (the genuine C-006 shape)

One key, `sync.enabled`, answers two different questions:

- *may my events go to spec-kitty's hosted SaaS?*
- *may my issue titles go to **the operator's own** Jira?*

A project cannot permit one and refuse the other. `#3030` never separated them because it was
closing a hosted-sync leak.

### Gap B — the `beads`/`fp` path is ungated entirely

`src/specify_cli/tracker/local_service.py` holds **zero** consent references. Verified by
per-file count across all 16 files in `src/specify_cli/tracker/` matching
`egress_consent|project_egress_refusal`:

| File | Matches |
|---|---|
| `egress_consent.py` | 6 (defines `project_egress_refusal` at `:147`) |
| `saas_client.py` | 3 (imports at `:34` — two matches on that one line — calls at `:329`) |
| **`local_service.py`** | **0** |
| the other 13 files | 0 |

The path, traced end to end:

```
cli/commands/tracker.py:1022,1074,1163   (@sync_app.command — operator entry)
 └─ _service()                            tracker.py:335
     └─ TrackerService.sync_*             service.py:193-200
         └─ _resolve_backend()            service.py:76   ← only production reach
             └─ LocalTrackerService.sync_pull/push/run    local_service.py:115,130,140
                 └─ _build_engine(...)                    local_service.py:217
                     └─ build_connector(...)              local_service.py:225 → factory.py:32
                         └─ BeadsConnector / FPConnector
                             └─ SubprocessCommandRunner.run
                                 └─ subprocess.run(list(command))
                                     spec_kitty_tracker/connectors/cli_runner.py:22
```

**What crosses:** issue `title`, `body`, `labels`, `assignees` and `workspace`, as **argv** of an
operator-named executable (`spec_kitty_tracker/connectors/beads.py:121-141`, `:163-214`).
The executable name comes from the **machine-global** credential file:
`factory.py:56` — `command=str(credentials.get("command") or "bd")`.

**Consent functions consulted on that path: zero.** A committed `sync.enabled: false` does not
stop it.

**Its only current gate is arming.** `cli/commands/tracker.py:354-366` gates the whole tracker
CLI group on `is_saas_sync_enabled()` — i.e. `SPEC_KITTY_ENABLE_SAAS_SYNC`
(`core/saas_sync_config.py:37-44`), which this spec lineage calls **arming and never a grant**,
and which was the 2026-07-27 incident's own mechanism. Worse,
`_check_sync_readiness` (`tracker.py:296-312`) **short-circuits entirely** for local bindings
via `_is_local_binding()` (`:280-293`), skipping readiness *and* daemon policy.

---

## 2. It is a `subprocess` surface, not an HTTP one — three consequences

AST-scanned with the egress guard's own scanner, with a positive control and a printed input
count (a gate that ran on zero files passes vacuously):

```
CONTROL saas_client.py sinks = 8   (expected >0 — it is allowlisted as SEAM)
SUBJECT local_service.py sinks = 0
INPUT COUNT: 1198 .py files scanned under src/; 72 sink sites in 28 files
```

1. **`local_service.py` is NOT in `_EGRESS_ALLOWLIST`, and cannot be added.**
   `tests/architectural/test_egress_consent_boundary.py::test_every_listed_file_still_holds_a_sink`
   (`:792-805`) deletes entries that guard nothing.
2. **Therefore the Bundle A allowlist collision this mission was warned about does not arise.**
   No entry to add; no `_baselines.yaml` bump (`egress_allowlist_files: 28`) needed; no
   `test_ratchet_baselines.py` red in a third file.
3. **`#3113`'s all-positional evasion is irrelevant to this gate** — there is no transport call
   here for the guard to match. The guard's own **Limit 4** scopes `subprocess` out by design.

Confirmed live nonetheless, with controls in both directions, because the mission brief asked:

| Probe | Sinks found | |
|---|---|---|
| `poster(url, data=body, headers=hdrs, timeout=5.0)` | 1 | control — matches the guard's own fixture |
| `poster(url, body, hdrs, 5.0)` | **0** | **evaded** (#3113) |
| `requests.post(u, b)` | 1 | control — the name rule still fires |

Gate status at this commit: `pytest tests/architectural/test_egress_consent_boundary.py -q`
→ **`27 passed in 77.30s`**, `EXIT=0`, unpiped.

---

## 3. The chokepoint for a gate

**`local_service.py::_build_engine`, `def` at `:217`, `build_connector(...)` at `:225`.**

- Called from exactly three sites: `:119` (`sync_pull`), `:134` (`sync_push`), `:144` (`sync_run`).
  Nothing else in the file constructs a connector.
- Already holds `self._repo_root` (`local_service.py:39`) — the exact argument
  `project_egress_refusal` takes.
- Covers **push, pull and sync** in one place.

**CORRECTION (measured during `specify`, 2026-07-31).** An earlier draft of this file asserted
that the *pull* direction ships a filter string outward (`beads.py:86-88`, `--title-contains`).
**That is false as reached from this code path.** `LocalTrackerService.sync_pull` calls
`engine.pull(limit=limit)` (`local_service.py:124`) with **no filters**, and
`SyncEngine.pull(filters=None)` (`spec_kitty_tracker/sync.py:53-68`) therefore builds argv
`[<cmd>, --json, list]` plus an optional `--updated-after <date>`. **No issue title crosses on
pull today.** `beads.py:86-88` is real but unreached — the `filters` parameter exists and no
caller populates it.

Pull is still gated, on three restated grounds: `sync run` shares the same chokepoint; pull still
executes an **operator-named binary from a machine-global credential file**; and the `filters`
parameter exists, so a future caller ships titles through an already-built path with no new gate.
Acceptance assertions for pull must therefore pin **argv shape and count**, not a title —
asserting a title's absence on pull would be asserting the absence of something that never
happens, which is the "assertion of absence that establishes nothing" this lineage forbids.

**Rejected alternatives, with reasons:**

- `_load_runtime` (`:192`) — **bypassed by `status()`** (which calls `load_tracker_config`
  directly at `:81`) and by `bind`/`unbind`. Wider than needed and still not universal.
- `TrackerService._resolve_backend` (`service.py:65`) — **bypassed by `bind()`**
  (`service.py:131-166`, which constructs both backends itself at `:142` and `:163`).
- `cli/commands/tracker.py::_service` (`:327`) — covers the CLI but not the automatic
  `origin_consumer` path.
- `factory.build_connector` (`factory.py:32`) — equally narrow, but does **not** have the repo
  root in scope.

---

## 4. The consent chain, as it actually is

### `EgressConsent` — 4 members (`invocation/adapters.py:41-74`)

`GRANTED` (resolver returned literal `True`) · `DENIED` (literal `False`) · `NO_RESOLVER`
(sync package never loaded) · `UNANSWERABLE` (resolver raised, or returned a non-bool).

`permits_egress` is `self is EgressConsent.GRANTED` — *"The single place this verdict is turned
into a branch. Callers must ask this rather than comparing against a member, so that adding a
future member cannot silently widen egress."*

**Load-bearing for this mission:** `DENIED` is returned for **both** absence and a recorded
`False`. The seam **cannot distinguish them.** Telling them apart requires
`ConsentDecision.level` (`ABSENT` vs `PROJECT_LOCAL`) from `sync/consent.py`.

### `ConsentLevel` — 5 members, 3 dispatchable (`sync/consent.py:66-108`)

**CORRECTED 2026-07-31.** An earlier draft of this file said *6 members*. Measured:
`len(list(ConsentLevel)) == 5` — `PROJECT_LOCAL`, `MACHINE_INDEX`, `ENV`, `ABSENT`,
`UNDETERMINED`; `len(PROJECT_CONSENT_PRECEDENCE) == 3`. The enum's own docstring explains the
shape: *"Two members are **outcomes** rather than levels — `ABSENT` and `UNDETERMINED`. Neither
appears in `PROJECT_CONSENT_PRECEDENCE` or `LEVEL_RESOLVERS`, so neither participates in
dispatch."* So it is 3 levels plus 2 terminal outcomes, not 6 of anything.

`PROJECT_CONSENT_PRECEDENCE = (PROJECT_LOCAL, MACHINE_INDEX, ENV)`. `ABSENT` and `UNDETERMINED`
are terminal, not dispatchable. `ENV` **never answers** — `_answer_env` returns `None`
unconditionally; *"that is the invariant rather than a stub"*.

`LEVEL_RESOLVERS` is held in **bijection** with the precedence tuple by
`_check_chain_is_dispatchable()`, which runs **at import** and raises `RuntimeError` on
disagreement — *"Cheaper to refuse to load than to under-enforce consent."*

### `CONFIG_FAULT_KINDS` — 4 kinds (`sync/config.py:78-83`)

`unreadable` · `unparseable` · `wrong_shape` · `unusable`. The set is cut by **the operator
action that resolves the fault**, not by the failure mode.

### `project_egress_refusal` (`tracker/egress_consent.py:147`)

`(project_root: Path | None) -> str | None`. **`None` — and only `None` — is permission.**
Every other outcome, including every future `EgressConsent` member, is a refusal string. The
fallback branch at `:205-211` already handles an unknown member honestly, naming the value
rather than reusing `DENIED`'s remedy.

Near-duplicated at `saas_client/egress_consent.py:92` **by declared necessity**
(`saas_client/egress_consent.py:33-36`): *"the two packages share no parent inside this change's
scope […] What is duplicated is the **call**, not the chain."*

---

## 5. Absence semantics, and why the asymmetry question was live

**Today, absence denies** (`sync/consent.py:642-659`, FR-002), and the recorded reasoning is
**mixed** — which is the seam this mission had to reason about:

- **Incident-anchored, for the *absence* branch.** `spec.md:53-56`: *"In the incident the five
  client repos were never opted in, so they have no record."* `consent.py:24-25`: *"Absence of a
  decision is not consent; **the five leaked projects had no record at all.**"*
- **Principled, for the *undetermined* branch.** `adapters.py:49-51`: *"neither is consent
  (FR-003's rule, re-derived here)."*

So **FR-003 governs *undetermined*, not *unrecorded*** — the two are separable, and the tree
already declines a fail-closed reading for absence three times where the cost was too high
(`consent.py:295-299`: *"Calling this a fault would deny every delivery on the machine"*;
`consent.py:218-221`; `tracer-design-decisions.md:424-425`).

**The operator was offered that asymmetry and declined it.** See §7.

---

## 6. `sync doctor` — where a refusal becomes visible

Two surfaces, wired at `cli/commands/sync.py:5928-5941`:

- **A — the per-project Consent column** (`_per_project_store_table`, `:1429-1473`).
  **Hard-coded binary**: `consented` / `denied (<level>)`, plus one special case rendering
  `unknown (identity unresolved)`. There is **no category dimension** — a refusal that is a
  second *decision* rather than a second *level* has nowhere to go in this table.
- **B — consent-record readability** (`_render_consent_readability`, `:1736-1817`).
  A **registry**, `_CONSENT_FAULT_ACTIONS` (`:1635-1664`), keyed on `ConfigReadFault.kind`, with
  an explicit unknown-kind fallback (`:1666-1675`) added because *"a kind-keyed table that
  renders nothing for an unrecognised key would turn the next addition into an invisible fault"*.
  Its **scopes are hard-coded** — exactly two, and there is no scope registry.

Section contract (`:1739-1743`): *"Both surfaces, always printed. 'Consent is fine', 'I could not
read it' and 'I never looked' must not render identically — that equivalence **is** the
incident's false-green."*

---

## 7. The decision, as taken

Escalated to the operator with evidence and a recommendation. Answers recorded 2026-07-31:

| Question | Answer | Was it the recommendation? |
|---|---|---|
| Scope | Separability **and** close the ungated local path | yes |
| Model | Adjacent resolver, own key, joined at the call site | yes |
| Absence on the local path | **Absence denies, uniform with SaaS tracker** | **no** — recommendation was *honour recorded refusals, absence permits* |

### The model

**REVISED 2026-07-31 after the post-specify squad (4 × REJECT). See `tracer-squad-findings.md` §5.**

Two further operator answers, both against the first draft:

| Question | Answer |
|---|---|
| How far does Channel 2 reach? | **Both local and SaaS bindings** |
| Does Channel 2 stay narrowing-only? | **Bidirectional — `false` is a tracker grant** |

**The destination finding that shapes the combination.** Verified at `bb2020fea`:
`saas_client.py:247` resolves `_base_url` from `resolve_runtime_target().resolved_server_url`, and
every endpoint is `/api/v1/tracker/…` carrying a bearer token and `X-Team-Slug`. **The SaaS tracker
path sends to spec-kitty's hosted service, not to Jira directly** — spec-kitty's server holds the
Jira/Linear connector and relays. Taken literally, an unrestricted bidirectional Channel 2 reaching
SaaS bindings would let a committed `egress_refused: false` ship engagement names **to spec-kitty's
hosted SaaS** while hosted-sync consent is absent or refused — reopening the boundary #3030's P0 fix
established, to the destination the incident leaked to.

**So polarity follows the destination:**

- **Channel 1 (existing, unchanged):** `resolve_egress_consent(repo_root)` — the hosted-sync consent
  chain. **Absence denies.** Already gates SaaS providers at `saas_client.py:329`; now also gates the
  local path.
- **Channel 2 (new):** a tracker-scoped key in the project's own committed config, resolved by its
  own function, applied to **both** paths.
  - On **local (`beads`/`fp`)** bindings it is **bidirectional**: `true` refuses, and `false` is an
    affirmative tracker grant that satisfies the path **independently of Channel 1**. The destination
    is a subprocess named by the operator's own credential file; spec-kitty's SaaS is not involved.
  - On **SaaS providers** it is **narrowing only**: it may refuse Jira/Linear, it may not grant them.
    Channel 1 stays a hard prerequisite, because the destination *is* spec-kitty's hosted service.

This delivers two-way separability from **spec-kitty's SaaS** — which is what C-006 names — without
punching a hole in #3030. Flagged to the operator as a modification of their answer, with the
evidence, and reversible on request.

**Two consequences of bidirectionality on the local path, both wanted:**

1. The *"consent to hosted sync or lose your local tracker"* coercion dissolves. An operator keeps a
   local `beads` binding by recording one tracker key in the file they already own, granting nothing
   to anyone.
2. The identity-less-checkout brick dissolves. Channel 2 reads the project's own config and needs no
   `project_uuid`, so a checkout that `enable_checkout_sync` refuses to record consent for is no
   longer permanently dead. Channel 1 still needs its third state — see `tracer-squad-findings.md`
   §3.2.

**Deny-on-absence stands, affirmed by all four lenses.** Absence of *both* channels still denies.

One representation each, of two invariants — the shape
`tracer-design-decisions.md:385-386` explicitly authorises: *"the C-003 rule is one
representation of one invariant, and these are two invariants."*

### Why not a new `ConsentLevel` or `EgressConsent` member

`PROJECT_CONSENT_PRECEDENCE` is an ordered **authority** chain answering **one** question at
descending authority. A tracker key is not lower authority — it is a **different question**.
Adding it makes the tuple an unordered dispatch table wearing a precedence type. The tree
already names this failure mode at `consent.py:52-56`, on why `sync.auto_start` was deliberately
*not* unified in: *"Conflating them would let a daemon-autostart preference grant hosted-sync
consent."*

A new `EgressConsent` member would require widening the resolver contract
(`Callable[[Path], bool]`, `adapters.py:81`) — which forces **Bundle B's Q3** open.

### Accepted cost of uniform deny-on-absence

**Every existing `beads`/`fp` binding stops working on upgrade** unless its project has a
committed consent record. Nothing in `src/` writes the project-local `sync.enabled` key —
`spec-kitty sync opt-in` writes only machine-global records (`routing.py:323-326`) — so affected
operators must hand-author `.kittify/config.yaml` or run the opt-in. This is a **breaking
change** and is a first-class deliverable (refusal message carrying the remedy, changelog,
upgrade note), not a footnote.

### Consequence for Bundle B — **B is unblocked**

Uniform deny-on-absence means this mission never needs to distinguish `ABSENT` from a recorded
`False`, so it never needs `ConsentDecision.level`. **B's Q3 stays closed.** No widening of
`EgressConsent` or the resolver contract. B may finish its consolidation on the four-member enum.

The one thing B must know: this mission's gate calls `project_egress_refusal`, so when B deletes
`tracker/egress_consent.py` and moves it to `specify_cli.egress`, **this mission's new call site
in `local_service.py` moves with it.**

### Stated limitation, decided rather than glossed

Separability is delivered in **one** direction — permit hosted sync, refuse tracker. The reverse
(tracker integration **without** hosted sync) remains **unsupported**, because Channel 1's
absence-denies still applies to local providers. Recorded as a named limitation, not an
oversight.

---

## 8. Falsifying preconditions

Written in the dossier's house style (`tracer-design-decisions.md:518-524`): state the condition
under which the decision holds, name the exact change that flips it, name the class of harm.

1. **`build_connector` stays restricted to `("beads", "fp")`.** If `factory.py:17` ever admits a
   `SAAS_PROVIDERS` member, `LocalTrackerService` becomes a second, differently-gated route to a
   third party and the two gates can disagree. **Harm:** the E20 shape returns, now with two
   contradictory answers instead of none. Make this an executable guard, not prose.
2. **`_build_engine` stays the sole connector-construction site in `local_service.py`.** A
   second construction site bypasses the gate silently. **Harm:** an ungated sibling path,
   invisible to the egress guard because the file holds no HTTP sink and can never be
   allowlisted. Guard it.
3. **The tracker path stays operator-invoked.** If any daemon, sweep, hook or `next`-loop
   reaches `LocalTrackerService`, the attribution precondition at
   `tracker/egress_consent.py:64-129` is violated — a **valid** root for the **wrong** project.
   **Harm:** exactly the cross-project substitution `#3030` exists to close.
4. **`bd`/`fp` remain local.** See §9.1. If either becomes a network client, this stops being a
   trust-boundary question and becomes a third-party leak under a machine-global credential —
   and the gate's *placement* is still right but its *justification* changes.
5. **Absence keeps denying at Channel 1.** If a future mission restores absence-permits for
   hosted sync, Channel 2 becomes the only tracker refusal and this mission's uniformity
   argument dissolves.

---

## 9. UNVERIFIED — stated as plainly as the findings

1. **Whether `bd` or `fp` themselves make network calls.** `spec_kitty_tracker` invokes them as
   opaque executables (`cli_runner.py:22`). Neither binary is installed here; neither is
   vendored; the executable name is **operator-overridable** (`factory.py:56`), so it is not even
   fixed. **This is the largest residual uncertainty and it is unresolvable from this repo.**
   If `bd` is a thin client for a remote beads server, Gap B is a genuine third-party leak; if it
   is a local store, Gap B is a trust-boundary question. The gate is defensible either way, but
   the *severity* is not established.
2. **Whether E20 was accurate against an earlier commit.** `local_service.py`'s last three
   touches are `3b313b6d1`, `2db24b362`, `02f78b034` (the PRI-16 "SaaS-mediated CLI tracker
   reflow"). Those revisions were **not** diffed to see whether `build_connector` once supported
   jira/linear. The dossier may be describing pre-reflow behaviour correctly.
3. ~~**Runtime confirmation of the Gap B claim.**~~ **RETIRED 2026-07-31 by the post-specify squad —
   Gap B is now observed, not inferred.** A real fake `bd` was installed on disk and named through
   the machine-global credential file; the real `LocalTrackerService` was driven with nothing in the
   production path patched:

   ```
   CASE committed sync.enabled=false / doctrine=spec_kitty_authoritative / op=sync_push
     argv captured : 2
        ['…/fake-bd', '--json', 'list']
        ['…/fake-bd', '--json', 'create', 'ACME Holdings carve-out', '--type', 'task',
         '--priority', '2', '--description', 'confidential body',
         '--assignee', 'alice@acme.example', '--label', 'secret-label']
     SENTINEL in argv: True     http attempts: 0
   ```

   A committed `sync.enabled: false` ships title, body, labels and assignee as argv. The residual
   uncertainty is now only §9.1 — what the real `bd` *does* with that argv.

   **Ownership mode is load-bearing and was missed here.** `doctrine_mode` defaults to
   `"external_authoritative"` (`tracker/config.py:38`), under which `local_can_write("title")` is
   `False` (`spec_kitty_tracker/policy.py:47-49`) and `SyncEngine.push` skips without calling
   `create_issue` (`spec_kitty_tracker/sync.py:112-115`) — so a *consenting* push on a default
   binding captures only `['<cmd>', '--json', 'list']` and no title crosses. Every acceptance fixture
   must pin `doctrine: {mode: spec_kitty_authoritative}` or its positive control is vacuous.
4. **`#3030`'s "seven independent places" of FR-003 violation.** The mission brief says seven;
   module docstrings say "four" (`tracker/egress_consent.py:60-61`) and "fourth independent
   occurrence" (`spec.md:225`). ~16 *current* fail-closed expressions were enumerated; the
   historical violation count was not reconstructed. **Unresolved.**
5. **`LocalTrackerService.sync_publish` does not exist.** `TrackerService.sync_publish`
   (`service.py:202-203`) delegates unconditionally, so `spec-kitty tracker sync publish` on a
   beads/fp binding raises `AttributeError`, which `_run_or_exit` (`tracker.py:346-351`) catches
   only for `RuntimeError`/`ValueError`. **A live bug, incidental to this mission** — file it,
   do not absorb it.
6. **The `_extra` round-trip as a smuggling surface.** `tracker/config.py:107` collects unknown
   `tracker:` keys and `to_dict` re-emits them (`:55`). Whether any consumer reads `_extra` was
   not checked. **Relevant** — Channel 2's key lands in this block.
7. **Test-suite health beyond the 154 consent tests executed.** `pytest
   tests/sync/test_consent_resolver_3030.py tests/sync/test_consent_fault_vocabulary_3030.py
   tests/sync/test_consent_read_fault_3030.py tests/sync/test_consent_field_fault_3030.py
   tests/invocation/test_adapters.py tests/architectural/test_egress_consent_boundary.py -q`
   → **`154 passed in 54.07s`**, `EXIT=0`, unpiped. The full suite was **not** run.

---

## 10. Import-rebinding split — measured, and binding on every test this mission writes

Standing rule: `from X import f` rebinds by value, so patching the defining module leaves the
deciding module inert. Measured at `bb2020fea`:

| Name | Binding | Observes a patch on `invocation.adapters`? |
|---|---|---|
| `specify_cli.invocation.adapters.resolve_egress_consent` | defining module | — |
| `specify_cli.invocation.resolve_egress_consent` (`invocation/__init__.py:23`) | module-level `from … import` | **No** (measured `False`) |
| `specify_cli.invocation.propagator.resolve_egress_consent` (`propagator.py:38`) | module-level `from … import` | **No** (measured `False`) |
| inside `tracker/egress_consent.py:178` | **call-time** import | **Yes** (measured: flipped refuse→permit) |

`project_egress_refusal` is bound **by value** into its consumers (`tracker/saas_client.py:34`,
`saas_client/client.py:23`). Measured: after patching
`specify_cli.tracker.egress_consent.project_egress_refusal`,
`TSC.project_egress_refusal is TE.project_egress_refusal` → **`False`**.

**Consequence, binding on this mission's tests:** a test asserting a tracker refusal must patch
**the deciding module's** name — `specify_cli.tracker.saas_client.project_egress_refusal`, and
for the new gate, whatever name `local_service.py` binds it under — **not**
`specify_cli.tracker.egress_consent.project_egress_refusal`. Report the per-site split.

---

## 11. Where this file and the `#3030` dossier disagree

| Claim | Dossier source | Code at `bb2020fea` |
|---|---|---|
| `local_service.py` sends to Jira/Linear | `egress-inventory.md:246` | **False** — `factory.py:17` supports only `("beads","fp")` |
| `sync.enabled: false` still pushes titles to Jira | `egress-inventory.md:262` | **False** — measured REFUSED, no HTTP |
| FR-013's rule "has no analogue" for tracker | `egress-inventory.md:261` | **Overstated** — the tracker binding lives in the same committed file; the analogue is direct |
| FR-002 / FR-003 status "Open" | `spec.md:232-233` | **Implemented** — `consent.py:650`, `routing.py:241,274`, measured denying |
| FR-013 writers at `routing.py:130-182` | `spec.md:243` | Stale line numbers; actual `routing.py:304,332` |
| C-003 titled "one representation of one invariant" | ~24 source comments | C-003 is titled *"Journal carries no target/receiver identity"*; the phrase is a **clause inside it**. Quote the clause, not the ID. |

`local_service.py` **is** correctly described by E20 in one respect and it is the respect that
matters: it has no consent gate.
