# Tracer: post-specify adversarial squad — findings and resolutions

**Point-cut:** post-specify. **Subject:** `spec.md` @ `6e7835e` (parented on `bb2020fea`).
**Squad:** four independent lenses, dispatched in parallel, profile-loaded, read-only, all opus —
`architect-alphonso` (structure/seams), `reviewer-renata` (anti-laziness/fakeable assertions),
`debugger-debbie` (live evidence), `paula-patterns` (boundaries/ownership).

**Verdict: 4 × REJECT.** No lens saw another's output.

---

## 1. Convergence — findings reached independently by more than one lens

| Finding | Lenses | Severity |
|---|---|---|
| FR-010/SC-004 demand an absence-vs-refusal distinction the seam cannot make, and C-004 forbids acquiring it | **3/3** | BLOCKER |
| Gate placement wrong: `_load_runtime` raises before `_build_engine` is reached | **3/3** | BLOCKER/HIGH |
| `bind` erases a committed `egress_refused` (measured with controls, twice, independently) | **2** | BLOCKER |
| "Channel 2 can only narrow" has no surviving justification | **4/4** | HIGH |
| FR-006 ground (a) — uniformity — falsified by evidence the spec itself cites | **2** | MEDIUM/HIGH |
| FR-013's falsity guard is file-scoped; the invariant is repo-wide | **3** | MEDIUM |

Convergence at this rate on a spec one agent wrote is the squad earning its cost.

---

## 2. Findings that produce **a green suite with no gate**

The most dangerous class, all **measured** by the live-evidence lens.

### 2.1 The positive control cannot pass on a default binding — BLOCKER

`TrackerProjectConfig.doctrine_mode` defaults to `"external_authoritative"` (`tracker/config.py:38`)
→ `OwnershipPolicy.external_authoritative()` (`local_service.py:236`) → `owner_for("title") is
FieldOwner.EXTERNAL` → `local_can_write("title") is False` (`spec_kitty_tracker/policy.py:47-49`)
→ `SyncEngine.push` does `stats.skipped += 1; continue` (`spec_kitty_tracker/sync.py:112-115`) and
**never calls `create_issue`**.

Measured: a *consenting* `sync_push` on a default binding captures exactly one argv,
`['<cmd>', '--json', 'list']`, sentinel **absent**. Under `spec_kitty_authoritative` the same
fixture captures the full create with title, body, labels and assignee.

Neither `spec.md` nor `tracer-evidence-base.md` mentioned ownership mode — **zero grep hits** for
`doctrine_mode|OwnershipPolicy|spec_kitty_authoritative`.

**Resolution:** every acceptance fixture pins `doctrine: {mode: spec_kitty_authoritative}`, and the
spec states why: under `external_authoritative` no title crosses on push, so a sentinel control
there asserts the absence of something that never happens.

### 2.2 The chokepoint is the seam the only existing tests stub out — BLOCKER

Mutation-as-plugin (no source edit), injecting FR-001's gate onto `_build_engine` via `PYTHONPATH`:

```
FR-001 MUTATION BIND COUNT: _build_engine entered=0 refused=0 permitted=0
519 passed, 1 warning in 59.65s
```

**Bind count zero — the all-green is vacuous.** Cause:
`tests/sync/tracker/test_local_service.py:235,262,287` each do
`with patch.object(svc, "_build_engine", return_value=(mock_connector, mock_engine))`, docstring at
`:193-195`: *"We mock `_build_engine` to avoid needing the spec_kitty_tracker package."*

An implementer following the house pattern patches out the method holding the gate. Every refusing
scenario then captures zero argv **whether or not the gate exists**.

**Resolution:** the recorder's injection point becomes a *requirement*, not a fixture choice — it is
installed at or below the credential-named executable / `SubprocessCommandRunner.run`, and
`_build_engine`, `build_connector` and `SyncEngine` are **un-patched** in every acceptance test. The
gate carries a bind counter asserted non-zero. **A gate never entered is not a gate.**

### 2.3 The arming gate satisfies every refusing assertion with nothing built — BLOCKER

`cli/commands/tracker.py:354-366` aborts the whole tracker group when
`SPEC_KITTY_ENABLE_SAAS_SYNC` is unset. Measured at `bb2020fea`, fully consenting project, no gate:

```
SPEC_KITTY_ENABLE_SAAS_SYNC=None  -> exit 1, subprocess.run 0, http 0
   'Hosted SaaS sync is not enabled on this machine. Set `SPEC_KITTY_ENABLE_SAAS_SYNC=1` to opt in.'
SPEC_KITTY_ENABLE_SAAS_SYNC='1'   -> exit 1, subprocess.run 1
```

SC-001, SC-003, SC-004 and NFR-002 are **all green today**.

**Resolution:** every acceptance fixture sets `SPEC_KITTY_ENABLE_SAAS_SYNC=1` explicitly and asserts
the refusal **text**, not merely a non-zero exit; plus a negative pin proving the un-armed message is
not what the refusing scenarios matched.

---

## 3. Findings against the consent model itself

### 3.1 The key would be inert on SaaS bindings while `sync doctor` confirms it — BLOCKER

FR-003 placed the join in `_build_engine` (local providers only); FR-014 left
`saas_client.py:329-331` untouched. So on a `jira`/`linear` binding a committed
`tracker: {egress_refused: true}` refuses **nothing**, while `_render_consent_readability` — which is
checkout-scoped and provider-blind — reports it as in force. A confidentiality control the operator
was *shown confirmation of* and that was *not enforced*: the incident's false-green, sign flipped.
And #3108 is framed entirely around Jira, so it is the first thing an operator will try.

**Resolution — operator decision, see §5:** Channel 2 reaches **both** paths.

### 3.2 Neither remedy works for an identity-less checkout — BLOCKER

Measured:

```
B: NO project.uuid, sync.enabled: true   <-- remedy 1 already applied
  routing.project_uuid  : None
  ConsentDecision       : granted=False level=absent reason='project identity did not resolve; not consentable'
  `sync opt-in` core    : ConsentIdentityUnresolvedError: … no project_uuid resolved. Run `spec-kitty init`
```

`locate_project_root` (`core/paths.py:182`) needs only `.kittify/` or a git root, so
`tracker bind` succeeds on an identity-less checkout; `enable_checkout_sync`
(`routing.py:320-321`) then refuses to record consent for it. The binding becomes **permanently
dead with actively wrong advice**. `resolve_project_consent` computes the true reason and
`project_egress_refusal` **discards it**.

This falsifies **FR-006's second ground** ("the refusal carries its own remedy"), which was part of
the argument given to the operator for why deny-on-absence was safe.

**Resolution:** FR-010 grows a **third** Channel-1 state — recorded refusal / no record / **not
consentable (no project identity)** — the third carrying `spec-kitty init` as its remedy, with its
own acceptance scenario and success criterion. The bidirectional decision (§5) independently
dissolves this for local bindings, since Channel 2 needs no `project_uuid`.

### 3.3 FR-003 contradicts FR-012, and C-013 argues FR-003's side — BLOCKER

FR-003: *"no third function computes a combined verdict."* FR-012 requires `sync doctor` to state
*"whether tracker egress is currently refused … and which channel refuses it"* — definitionally a
second combined verdict. C-013 defers `tracker status` for exactly that reason.

**Resolution:** extract one named `tracker_egress_verdict(root)` that **both** the gate and
`sync doctor` call, with a guard pinning its caller count. FR-003 is amended to permit exactly one
such function rather than none.

### 3.4 `sync doctor` mis-renders all three cases — HIGH

Measured three ways through `_render_consent_fault` (`cli/commands/sync.py:1711-1733`):

- a plain string → `kind="unknown"`, `detail="no detail recorded"` — the refusal text is discarded;
- a fault-shaped carrier → announces a **correct, readable** file as `UNREADABLE` and tells the
  operator to `REPAIR` it;
- `_CONSENT_FAULT_NOT_ABSENCE` (`sync.py:1691-1696`) prints *"This is NOT a missing consent record"*
  unconditionally — **literally false** for the absence case, and hard-coded outside the registry, so
  registering a fifth kind does not fix it.

`CONFIG_FAULT_KINDS` is pinned by exact-equality at
`tests/sync/test_consent_fault_vocabulary_3030.py:261`. The section's contract is **readability**
(`sync.py:1737`), not verdict.

**Resolution:** a **new** renderer beside `_render_consent_fault`, not a third scope routed through
it. A verdict inside a readability section is the same category error the spec refuses elsewhere.

### 3.5 The mission would introduce a refusal-laundering regression — HIGH

Today `egress_refused: "true"` is an unknown key → `_extra` (`config.py:107`) → re-emitted (`:55`),
so the fault **round-trips correctly**. After C-001 promotes it to `_KNOWN_KEYS`, `from_dict`
coerces a non-`bool` to the field default (measured on the `doctrine.mode` precedent: a recorded
`42` came back as `'external_authoritative'`), `_extra` no longer catches it, and FR-008's
"omit when `None`" then erases it. **`tracker bind` converts a refusing project into a permitting
one.** The current code handles this case better than the fix did.

**Resolution:** the field carries the raw value and a fault, not `bool | None`; FR-009/SC-006 require
**every** value in FR-005's probed set to round-trip byte-identically through `bind`/`unbind`.

### 3.6 `bind` and `unbind` erase the key — BLOCKER (measured twice, independently)

```
--- CONTROL: from_dict puts unknown key into _extra ---   _extra = {'egress_refused': True}   ok
--- CONTROL: save of a LOADED config preserves it ---     egress_refused present: True        ok
--- SUBJECT: bind (service.py:163 path) ---               egress_refused present: False       XX
--- SUBJECT: unbind (clear_tracker_config) ---            egress_refused present: False       XX
              sibling `sync:` block still present         True  (control)                     ok
```

The read-modify-write is **payload**-level, not tracker-block-level: `save_tracker_config` does
`payload["tracker"] = config.to_dict()` (`config.py:171`), and `LocalTrackerService.bind` builds a
**fresh** `TrackerProjectConfig` from a caller that already handed it an empty one
(`service.py:163`). `clear_tracker_config` does an unconditional `del payload["tracker"]`
(`config.py:178-194`) — never mentioned in the spec. Contrast `saas_service.py:220,317`, which
*deliberately* carry `_extra=dict(self._config._extra)` forward.

Because the key is refusal-polarity, deleting it is a **silent fail-open**.

**Resolution:** name all three sites; decide and record the semantics the spec ducked —
**a refusal outlives its binding.** A rebind must not silently re-permit.

---

## 4. Findings on evidence and argument quality

- **[HIGH] NFR-001 mandated the vacuous pull pin** that SC-003 had already corrected. Rewritten to
  the zero-argv formulation; the title-absence assertion is meaningful only on `push` and `run`.
- **[HIGH] US1 scenario 3 had no positive control** — "hosted-sync delivery is unaffected" is
  satisfied by a drain that never ran. Now requires the fixture to be hosted-sync-consent-**granted**
  and asserts *the same N events are delivered with and without the tracker key, N ≥ 1*.
- **[HIGH] SC-004 asserted the remedy as a string, never as a remedy.** Replaced with an
  **executed-remedy** criterion: apply each remedy to the refusing fixture, re-run, assert the title
  now reaches the recorder. That test, and only that test, would have caught §3.2.
- **[HIGH] FR-001's rejection of `_service` cited a false premise** — `origin_consumer` never reaches
  `LocalTrackerService` (`origin.py` imports no `TrackerService`). The conclusion survives on the
  other grounds; the false clause is replaced, per the rule that a decision record citing a false
  premise cannot prevent re-litigation.
- **[MEDIUM] FR-006 ground (a)** (uniformity) is falsified by `spec.md:90-91`'s own citation of
  `_check_sync_readiness`'s local short-circuit. Deleted; FR-006 now rests on (b) — repaired per
  §3.2 — and (c), the unverified-`bd`-is-local ground, which is decisive on its own.
- **[MEDIUM] `_MISSING` reuse across a package boundary** would give `tracker/` an import-time
  dependency on `sync.consent`, risking an `ImportError` raise out of a gate NFR-003 says never
  raises. Now a module-local sentinel with the same *semantics*, citing the reasoning rather than
  importing the object.
- **[MEDIUM] The falsity guards were vacuous in the "empty" direction** — `assert count <= 1` passes
  on a zero-call scan, which is what happens after Bundle B moves the file. Now exact-membership and
  exact-count, scoped to `src/` (measured: `build_connector` has exactly one call site tree-wide),
  each asserting and printing its own non-zero input count.
- **[MEDIUM] `sync doctor`'s third scope reds an existing count-based pin** —
  `tests/cli/commands/test_sync_doctor_consent_health_3030.py:366` asserts
  `flat.count("REPAIR THE FILE'S SYNTAX") == 4` over the whole rendered output. Named in the blast
  radius.
- **[MEDIUM] SC-005 was vacuous** — `egress_refused: false` + hosted-sync absent refuses identically
  whether or not Channel 2 exists. Paired with a mutation pin: remove Channel 2, US1-sc1 must red
  while SC-005 stays green.
- **[MEDIUM] C-007 conflated two distinct symbols.** Measured: `saas_client/egress_consent.py:92` is
  a **second definition**, not a re-export — different `id`, different `__module__`. Row split.
- **[NOTE] `sync doctor` is the right surface for a stronger reason than the spec gave:** the
  `spec-kitty tracker` group is **conditionally registered** (`cli/commands/__init__.py:238-243,300`)
  and does not exist unless armed, while `sync` is registered unconditionally (`:298`). A
  tracker-side surface would be unreachable in exactly the configuration where an operator most needs
  it. This converts a preference into a structural necessity.

---

## 5. Escalated to the operator, and decided

Two questions, both about Channel 2's reach. Both answered against the spec as written.

| Question | Answer |
|---|---|
| How far does Channel 2 reach? | **Both local and SaaS bindings** |
| Does Channel 2 stay narrowing-only? | **Bidirectional — `false` is a tracker grant** |

### The refinement the orchestrator applied, and why

Taken literally, those two answers combine into a hole. Verified at `bb2020fea`:
`saas_client.py:247` resolves `_base_url` from `resolve_runtime_target().resolved_server_url`, and
every endpoint is `/api/v1/tracker/…` carrying a bearer token and `X-Team-Slug`. **The SaaS tracker
path sends to spec-kitty's hosted service, not to Jira directly** — spec-kitty's server holds the
connector and relays. So an unrestricted bidirectional Channel 2 reaching SaaS bindings would let a
committed `egress_refused: false` ship engagement names **to spec-kitty's hosted SaaS** while
hosted-sync consent is absent or refused — reopening the exact boundary #3030's P0 fix established,
to the exact destination the incident leaked to.

**Polarity therefore follows the destination:**

- **Local (`beads`/`fp`) — bidirectional.** `egress_refused: false` grants the local path
  independently of Channel 1. The destination is a subprocess named by the operator's own credential
  file; spec-kitty's SaaS is not involved. This is where the coercion lived, so the coercion
  dissolves — and §3.2's brick dissolves with it, because Channel 2 reads the project's own file and
  needs no `project_uuid`.
- **SaaS providers — narrowing only.** Channel 2 may refuse Jira/Linear; it may not grant them.
  Channel 1 remains a hard prerequisite, because the destination *is* spec-kitty's hosted service.

This delivers two-way separability from **spec-kitty's SaaS**, which is what C-006 names, without
punching a hole in #3030. Flagged to the operator as a modification of their answer, with the
evidence, and reversible on request.

### What the squad said about deny-on-absence — the decision stands

All four lenses independently affirmed it. The decisive ground is (c): absence-permits would bet
confidentiality on the **unverified** premise that `bd`/`fp` are local, and `factory.py:56` makes the
executable name operator-overridable from a machine-global credential file. What needed repair was
the *argument*, not the decision — ground (a) is deleted and ground (b) is repaired per §3.2.

---

## 6. Raised and judged **wrong** — recorded so it is not re-raised

- **"Channel 2 reintroduces the checkout-keying #3030 condemned."** Withdrawn by the lens that raised
  it. `ConsentLevel.PROJECT_LOCAL` reads the project's own committed `.kittify/config.yaml` too, so
  Channel 2's keying matches level 1's exactly. FR-019 condemned repo-**slug** keying, which Channel
  2 does not use.
- **"`write_local_sync_enabled` is a project-local writer, so the breaking-change framing is wrong."**
  Checked and retracted by the lens that raised it: `routing.py:283-285` delegates to
  `SyncConfig().set_checkout_sync_enabled` — machine-global. **The name is the trap, not the spec.**
- **"Both `ConsentLevel` and `EgressConsent` rejections are convenient rather than sound."**
  Steelmanned by two lenses and **both rejections survived**. `ConsentLevel` fails on *algebra*:
  `PROJECT_CONSENT_PRECEDENCE` is walked first-level-that-answers-wins, so a tracker key inserted
  there would *answer the hosted-sync question* — verbatim the `sync.auto_start` failure mode at
  `consent.py:52-56`. The mission needs an AND-conjunct; the tuple expresses precedence. Different
  algebra. `EgressConsent` fails on the *registry contract*: `Callable[[Path], bool]`
  (`adapters.py:81`) manufactures the member from a bool, so a tracker-sourced member cannot exist
  without widening the callable — Bundle B's Q3. **C-004's conclusion survives; only its stated
  justification did not.**

---

## 7. Carried as residuals — MEDIUM and below, recorded where a successor will find them

- **Chain B is not named anywhere.** `sync/routing.py:178-252` `_build_checkout_sync_routing` →
  `is_sync_enabled_for_checkout` answers a version of "may this data leave", honours the
  **repo-slug-keyed** `[sync.repo_defaults]` record that `consent.py:99-103` explicitly refuses
  (*"One was added on 2026-07-30 and removed the same day"*), and is live on a real egress gate at
  `sync/batch.py:1070`, plus `sync/runtime.py:106` and `cli/commands/sync.py:1964,2081`. Three source
  comments explain why the good path avoids it; nobody has removed it. **#3108 does not add a third
  answerer** — Channel 1 correctly reuses `project_egress_refusal` → Chain A — but a mission premised
  on "one key answering two questions" should name the place where one question is answered by two
  chains. Recorded as a constraint; **follow-up issue to be filed**, not absorbed.
- **`LocalTrackerService.sync_publish` does not exist** — `TrackerService.sync_publish`
  (`service.py:202-203`) delegates unconditionally, so `tracker sync publish` on a beads/fp binding
  raises `AttributeError`, which `_run_or_exit` catches only for `RuntimeError`/`ValueError`
  (confirmed: `isinstance(e, (RuntimeError, ValueError))` → `False`). **A live bug, incidental.
  File it; do not absorb it.**
- **`TrackerProjectConfig._extra` consumers unaudited.** Mitigated by promoting the key to a known
  field, not answered.
- **`_check_sync_readiness`'s docstring goes stale the moment this lands** — it says local providers
  *"reach the sync command without going through the SaaS surface at all"*, which FR-006 makes false.
  Extend the docstring-amendment requirement to `tracker.py:296-312` and `:315-324`.
- **Pre-gate local side effects.** A refusing project still reads the machine-global credential store
  and constructs `TrackerSqliteStore`, which `mkdir`s and creates a SQLite file with three tables
  (`store.py:278-281`). No egress, so every NFR still holds — recorded so a later reader does not
  mistake "zero argv" for "zero effects" and quietly move the gate.
- **Evidence-base nit:** the per-file table says `saas_client.py` **2**; measured **3** (line 34
  carries two regex matches on one line — a line count, not a match count). The load-bearing cell
  (`local_service.py` = 0) is exact.

---

## 8. What the squad retired from UNVERIFIED

**Gap B is now observed, not inferred.** With a real fake `bd` installed on disk, named through the
machine-global credential file, and the real `LocalTrackerService` driven with nothing patched:

```
CASE committed sync.enabled=false / doctrine=spec_kitty_authoritative / op=sync_push
  argv captured : 2
     ['…/fake-bd', '--json', 'list']
     ['…/fake-bd', '--json', 'create', 'ACME Holdings carve-out', '--type', 'task',
      '--priority', '2', '--description', 'confidential body',
      '--assignee', 'alice@acme.example', '--label', 'secret-label']
  SENTINEL in argv: True     http attempts: 0
```

A committed `sync.enabled: false` ships title, body, labels and assignee as argv.
**`tracer-evidence-base.md` §9.3 may be retired.**

**Still unverified, and still the largest residual:** whether `bd`/`fp` themselves make network
calls. The harness used a fake binary, so it proves what argv *would* be handed to the real one, not
what the real one does with it. Unresolvable from this repository.

**Baselines measured, unpiped, exit status trusted:**

| Command | Result | EXIT |
|---|---|---|
| the six consent/boundary suites | `154 passed in 51.31s` | 0 |
| `tests/sync/tracker/ tests/agent/cli/commands/test_tracker.py` | `519 passed, 1 warning in 64.73s` | 0 |
| `tests/cli/commands/test_sync_doctor_consent_health_3030.py` | `15 passed in 54.64s` | 0 |

No pre-existing failure from the known-red roster was encountered; none chased.

**Citation audit:** 23 `src/` and `spec_kitty_tracker` citations were spot-checked against the code.
**Every one resolves to the claimed construct.**
