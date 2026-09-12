# Research: Tracker Egress Refusal (Mission `tracker-egress-refusal-3108-01KYWF1R`)

**Input:** `Priivacy-ai/spec-kitty#3108`. **Authored against:** `bb2020fea` (upstream/main,
2026-07-31 08:52). **Authoritative sources, in descending order of trust:** the code at
`bb2020fea` itself; `tracer-evidence-base.md` (measured evidence); `tracer-squad-findings.md`
(four-lens adversarial squad + the operator decisions); `spec.md` (the specification this
research supports). Where the `#3030` dossier and the code disagree, **the code wins** and the
disagreement is stated, not reconciled silently (see tracer-evidence-base.md §11).

This document does not re-derive anything the tracer files already measured. It structures those
measurements as decisions with rationale, cites evidence-log/source-register rows (`E##` / `S##`)
for traceability, and records what remains open. Canon: **Mission**, never "feature".

---

## 1. The premise correction

Issue `#3108` and `#3030`'s `egress-inventory.md:243-272` (entry **E20**) both assert that
`tracker/local_service.py` sends issue titles to Jira/Linear, and that a project with a committed
`sync.enabled: false` can still push its issue titles to Jira. **Both sentences are false at
`bb2020fea`.**

Measured with an isolated `HOME`, an HTTP trip-wire on `httpx.Client.request`, and a positive
control (E01, S12–S15):

| project-local `.kittify/config.yaml` | `SaaSTrackerClient.push(provider="jira", …)` |
|---|---|
| no record (absence) | **REFUSED**, `error_code=project_consent_denied`, no HTTP attempted |
| `sync: {enabled: false}` | **REFUSED**, `error_code=project_consent_denied`, no HTTP attempted |
| `sync: {enabled: true}` | gate passed → failed later at `No valid access token` |

**The third row is the positive control.** Without it, rows 1–2 are indistinguishable from a
harness that never reached the code at all — a gate that always prints "refused" regardless of
input would pass rows 1–2 and this table would still look correct. Row 3 proves the harness *can*
reach a passing outcome, so rows 1–2's REFUSED is the gate acting, not the probe failing to fire.

**Why the claim is false — the routing.** `tracker/factory.py:17` restricts
`SUPPORTED_PROVIDERS` to `("beads", "fp")`; `build_connector` raises `TrackerFactoryError` for
anything else (`factory.py:38-39`). `LocalTrackerService` therefore cannot construct a Jira or
Linear connector at all. `tracker/service.py:77-80` routes `SAAS_PROVIDERS` to
`SaaSTrackerService` and `LOCAL_PROVIDERS` to `LocalTrackerService`. Jira/Linear egress passes
through `tracker/saas_client.py:329-331` — the gate `#3030` FR-029 shipped, at `_request`, the
single chokepoint every endpoint and the operation poller cross, placed *before*
`_fetch_access_token_sync()`:

```python
refusal = project_egress_refusal(self._project_root)
if refusal is not None:
    raise TrackerEgressRefusedError(refusal)
```

So "key tracker egress through the existing consent chain" is **not a proposal this Mission
builds — it is the status quo `#3030` already shipped.** This Mission closes the two gaps that
are actually open (below), and corrects the polarity error the spec's first draft made about the
second one.

---

## 2. Design options considered and why each was rejected

| # | Option | Why rejected |
|---|---|---|
| 1 | **Reuse `sync.enabled` alone** (no new key) | One key answers two unrelated questions — *may events reach spec-kitty's hosted SaaS* and *may issue titles reach the operator's own tracker binary*. A project cannot permit one and refuse the other under a single key. This is the genuine C-006 shape (Gap A) and reusing the key does not close it. |
| 2 | **A new `ConsentLevel` member** | `PROJECT_CONSENT_PRECEDENCE` (`sync/consent.py:104-108`) is an ordered **authority** chain answering **one** question at descending authority, held in bijection with `LEVEL_RESOLVERS` by `_check_chain_is_dispatchable()` (raises at import on disagreement). It is walked first-level-that-answers-wins, so inserting a tracker key there would make it **answer the hosted-sync question** — verbatim the `sync.auto_start` failure mode named at `consent.py:52-56` ("Conflating them would let a daemon-autostart preference grant hosted-sync consent"). This Mission needs an **AND-conjunct**; the tuple expresses **precedence**. Different algebra. **Fails on algebra.** This reasoning survived adversarial steelmanning by two squad lenses (tracer-squad-findings.md §6) — the conclusion held even after the squad tried to show the rejection was merely convenient. |
| 3 | **A new `EgressConsent` member** | `permits_egress` (`invocation/adapters.py:74`) is the single place the verdict becomes a branch, fed by a registry contract `Callable[[Path], bool]` (`adapters.py:81`) that manufactures the member from a bool. A tracker-sourced member cannot exist without widening that callable — which forces sibling Bundle B's open Q3 (whether the resolver contract itself changes shape). **Fails on the registry contract.** Also steelmanned by two lenses and survived (tracer-squad-findings.md §6). |
| 4 | **Narrowing-only Channel 2** (the spec's first draft) | Rejected by the post-specify squad, 4/4 lenses, HIGH severity: "'Channel 2 can only narrow' has no surviving justification" (tracer-squad-findings.md §1). A narrowing-only key applied to local bindings converts every existing `beads`/`fp` binding that never recorded hosted-sync consent into a permanently dead binding unless the operator also grants hosted sync — the *"consent to hosted sync or lose your local tracker"* coercion the operator explicitly rejected in the second escalation (tracer-squad-findings.md §5). |
| 5 | **A `bool` spelling of the key** (e.g. `egress_refused: false` / `enabled: true`) | Two independent reasons. (a) A boolean has two slots for three things Channel 2 needs to say — refuse, permit, say nothing — so `false` would have to mean "not refused", collapsing **absence** and **a recorded value** into the same reading. That collapse is the exact defect this Mission exists to close at Channel 1; reproducing it in the new key would be the Mission arguing against itself (spec.md Key Entities). (b) `egress_refused: false` is a double negative on a confidentiality control, and the shortest wrong reading — "this project permits tracker egress everywhere" — is exactly the belief FR-004's destination-dependent polarity exists to prevent. |
| 6 | **Relocating the key out of the `tracker:` block** — either to a new top-level `egress:` block, or into the existing `sync:` block | **Decided by the operator: the key stays in the `tracker:` block.** Recorded here because the previous revision's rejected-options list had five entries and *none of them was about where the key lives* — the placement read as inherited rather than chosen, and its costs (below) then read as accidents rather than as an accepted price. **Alternative (a) — a new top-level `egress:` block.** Genuinely attractive: it is owned by no command, so **none of the six `TrackerProjectConfig(` lifecycle sites could erase it** and the whole preservation machinery of `data-model.md` §5 would simply not exist. Rejected on two grounds: it adds a **third** reader of `.kittify/config.yaml` to a tree whose stated problem is *too many answerers of one question*, and it moves the key **away from the binding it qualifies** — an operator reading `tracker:` would see a provider and a workspace and no indication that egress is governed elsewhere, which is the discoverability failure `sync doctor` exists to compensate for. **Alternative (b) — the `sync:` block.** Rejected on measured grounds, not aesthetic ones: a key in `sync:` is dragged into `CONFIG_FAULT_KINDS` (`sync/config.py:78-83`), which is **pinned by exact equality** at `tests/sync/test_consent_fault_vocabulary_3030.py:261`, and into `_render_consent_fault` (`cli/commands/sync.py:1711-1733`) — which this Mission measured to be **wrong three ways** for this content (a plain string arrives as `kind="unknown"` with the text discarded; a fault-shaped carrier announces a correct, readable file as `UNREADABLE`; and `_CONSENT_FAULT_NOT_ABSENCE` prints *"This is NOT a missing consent record"* unconditionally, which is literally false for the absence case). It would also spell the tracker decision like `sync.enabled` while the two answer **absence oppositely**. **The accepted cost of keeping it in `tracker:`, stated honestly rather than glossed:** preservation work at **six** construction sites (§5 of `data-model.md`); a **manufactured red** (promoting `egress` to `_KNOWN_KEYS` creates the null-planting defect FR-009 then closes); a `preserve_quotes` change in two more places; and an `unbind` that leaves a **binding-named block holding only a consent decision** — a shape that reads oddly in a diff and needs the FR-011 rule to explain it. |

---

## 3. The operator decisions, and what each changed

The scope/model/absence questions were escalated with evidence and a recommendation on
2026-07-31 (tracer-evidence-base.md §7); two further questions were escalated after the
post-specify squad's 4×REJECT (tracer-squad-findings.md §5).

| # | Question | Answer | Was it the recommendation? | What it changed |
|---|---|---|---|---|
| 1 | Scope | Separability **and** close the ungated local path | Yes | Both Gap A (separability) and Gap B (the ungated `beads`/`fp` path) are in scope, not just one. |
| 2 | Model | Adjacent resolver, own key, joined at one call site | Yes | Established the two-channel shape: Channel 1 unchanged, Channel 2 new, joined by a single named function rather than folded into an existing type. |
| 3 | Absence on the local path | **Absence denies, uniform with SaaS tracker** | **No** — recommendation was *honour recorded refusals, absence permits* | Every existing `beads`/`fp` binding with no committed decision at either channel now refuses on upgrade. This is a breaking change (FR-013) and is why US6 (upgrade messaging) exists as a first-class user story rather than a footnote. |

**Revised after the squad (2026-07-31), against the spec's first draft:**

| # | Question | Answer | What it changed |
|---|---|---|---|
| 4 | How far does Channel 2 reach? | **Both local and SaaS bindings** | The first draft placed the join only in `_build_engine` (local providers), leaving a committed `tracker: {egress_refused: true}` inert on a `jira`/`linear` binding while `sync doctor` reported it as in force (tracer-squad-findings.md §3.1, BLOCKER). Channel 2 now reaches the SaaS gate too (FR-016), via the single `tracker_egress_verdict` function (FR-003). |
| 5 | Does Channel 2 stay narrowing-only? | **Bidirectional — a recorded grant is real, but only on local bindings** | Taken literally, answers 4+5 combine into a hole: `saas_client.py:247` resolves `_base_url` from `resolve_runtime_target().resolved_server_url`, and every endpoint is `/api/v1/tracker/…` with a bearer token and `X-Team-Slug` — **the SaaS tracker path sends to spec-kitty's hosted service, not to Jira directly** (E16). An unrestricted bidirectional Channel 2 on SaaS bindings would let a committed grant ship engagement names to spec-kitty's hosted SaaS while hosted-sync consent is absent or refused — reopening `#3030`'s P0 boundary, to the destination the 2026-07-27 incident leaked to. The orchestrator therefore split polarity by destination rather than applying the operator's literal answer uniformly, flagged this as a modification of the operator's answer with the evidence, and left it reversible on request. |

**Revised again after the post-plan squad (3 × REJECT), and this is the load-bearing correction:**

| # | Question | Answer | What it changed |
|---|---|---|---|
| 6 | How does the join know **which destination** it is being asked about? | **It is told.** `destination` is a **required, keyword-only** parameter of `tracker_egress_verdict`, drawn from a closed two-member set (`LOCAL_SUBPROCESS`, `HOSTED_SERVICE`); every call site passes a **literal**; no call site derives it from a config read. | The revision under review derived the polarity from `load_tracker_config(root).provider`. That is **unsound**: `TrackerService._resolve_saas_backend_for_provider` (`service.py:84-98`) overrides the provider **in memory** for `--provider <saas>` and never rewrites the file, so with on-disk `provider: beads` the subject reaches `SaaSTrackerService` while the file still reads `beads` (positive control: disk `jira` → same backend; negative control: `TrackerServiceError` for `beads`). Three operator-reachable commands do this — `list-tickets`, `issue-search`, `map list`, each `--provider`, each `allow_unbound=True`. A config-derived polarity therefore makes `tracker.egress: permitted` an **affirmative grant to spec-kitty's hosted service with Channel 1 absent**: `#3030`'s P0 boundary reopened by the key introduced to protect it, for exactly the operator US2 serves. Consequences: the `none` binding kind dissolves; the table shrinks from 12 cells to **8**; `sync doctor` prints **one row per destination**; a fifth guard (G5) pins the literal; and the verdict reads the project config **once** instead of twice. |

**The decided model, net of all six answers:** Channel 1 (`resolve_egress_consent` via
`project_egress_refusal`) is unchanged and absence-denies. Channel 2 (`tracker.egress`, a closed
`refused | permitted` string set in the project's own `.kittify/config.yaml`) is new. The
**destination** is supplied by the caller. At `LOCAL_SUBPROCESS` Channel 2 is bidirectional:
`refused` denies, `permitted` grants independently of Channel 1. At `HOSTED_SERVICE` it is
narrowing-only: `refused` denies, `permitted` is a reported no-op. Absence of both channels still
denies. Unknown values at the key are a fault, and a fault refuses — no case-folding, no synonyms,
with the decode `isinstance`-guarded so a mapping or a list at the key cannot raise out of a
function that must never raise.

---

## 4. Falsifying preconditions

Written in the dossier's house style: state the condition under which the decision holds, name
the exact change that flips it, name the class of harm. Items 1–4 and 6 are carried from
`tracer-evidence-base.md` §8; item 5 was added once the destination finding (§3, answer 5 above)
became load-bearing, and is recorded as `spec.md` C-006.

1. **`build_connector` stays restricted to `("beads", "fp")`** (`factory.py:17`). If it ever
   admits a `SAAS_PROVIDERS` member, `LocalTrackerService` becomes a second, differently-gated
   route to a third party and the two gates can disagree. **Harm:** the E20 shape returns, now with
   two contradictory answers instead of none. Guarded structurally (spec.md FR-015 guard G1), not
   left to prose. **What this precondition no longer carries:** the previous revision also claimed
   that widening `SUPPORTED_PROVIDERS` would make the polarity split "silently mis-classify a SaaS
   destination as local — the sharpest failure this Mission can have". With the destination supplied
   as a literal by each call site (answer 6 above), **that failure mode is structurally impossible**;
   G1 now guards only the gate-divergence half. The sharpest failure moved, and its guard is **G5**.
2. **`_build_engine` (`local_service.py:217`) stays the sole connector-construction site**, and
   its callers stay exactly `sync_pull`/`sync_push`/`sync_run`. **Harm:** a second construction
   site bypasses the gate silently — an ungated sibling path, invisible to the egress guard
   because the file holds no HTTP sink and can never be allowlisted. Guarded (FR-015 G2, G3).
3. **The tracker path stays operator-invoked.** If any daemon, sweep, hook or `next`-loop reaches
   `LocalTrackerService`, the attribution precondition at `tracker/egress_consent.py:64-129` is
   violated — a **valid** root for the **wrong** project. **Harm:** exactly the cross-project
   substitution `#3030` exists to close. Prose only; re-check required of any future Mission
   adding an automatic caller.
4. **`bd`/`fp` remain local.** If either becomes a network client, this stops being a
   trust-boundary question and becomes a third-party leak under a machine-global credential, and
   the gate's *placement* is still right but its *justification* changes. This precondition is
   itself **unverified** — see §5 below.
5. **The SaaS tracker path keeps sending to spec-kitty's hosted service rather than directly to
   Jira/Linear** (E16: `saas_client.py:247`, `/api/v1/tracker/…` endpoints, bearer token +
   `X-Team-Slug`). If that inverts, FR-004's SaaS-side no-op justification loses its ground in the
   opposite direction — a narrowing-only Channel 2 on SaaS bindings would then be under-protective
   rather than the safe default it is today, because the destination would no longer be
   spec-kitty's own trust boundary.
6. **Absence keeps denying at Channel 1** (`sync/consent.py:642-659`). If a future Mission
   restores absence-permits for hosted sync, Channel 2 becomes the only tracker refusal at
   `HOSTED_SERVICE` and this Mission's deny-on-absence uniformity argument dissolves.
7. **The set of tracker transports stays two.** `EgressDestination` is closed at
   `LOCAL_SUBPROCESS` and `HOSTED_SERVICE` because those are the only two transports the tracker
   package has: a subprocess (`spec_kitty_tracker/connectors/cli_runner.py:22`) and
   `SaaSTrackerClient._request`. A third transport — a direct third-party HTTP client in
   `tracker/`, say — would need a third member **and a decided polarity for it**, and until that
   decision is made the verdict function would be answering a question it was not designed for.
   **Harm:** a new transport silently inheriting one of the two existing polarities.
   **Detection — and the earlier draft of this item named the wrong instrument.** It is **not** G5.
   G5 **passes** when a new transport reuses `HOSTED_SERVICE`: the argument is still an `Attribute`,
   the literal set is still exactly two, and the per-site clause names only the four existing sites.
   What fires is **G4**, whose membership/count assertion breaks when a new call site appears — and
   it fires only as a **prompt**, whose obvious resolution is to edit the guard. **Stated honestly:
   neither guard decides polarity for a new transport; they only make its absence visible, and only
   in the add-a-call-site case.** The requirement is therefore placed where a developer will read it
   — a docstring on `EgressDestination` (`spec.md` FR-017) stating that **adding a member, or
   pointing an existing member at a new transport, requires an operator decision on that member's
   Channel-2 polarity**, citing FR-004 as where the decision is recorded.

---

## 5. Open questions and risks — feeding `/spec-kitty.tasks`

- **Whether `bd`/`fp` themselves make network calls is unresolved and unresolvable from this
  repository.** `spec_kitty_tracker` invokes them as opaque executables
  (`cli_runner.py:22`); neither binary is installed here, neither is vendored, and the executable
  name is operator-overridable from a machine-global credential file (`factory.py:56`). The
  squad's harness (E04) installed a **fake** `bd` binary and captured argv — it proves what argv
  *would be handed to* the real binary, not what the real binary *does with it*. **This is why the
  severity of Gap B is unestablished even though its existence is now measured, not inferred**: if
  `bd` is a thin client for a remote server, Gap B is a genuine third-party leak; if it is a purely
  local store, Gap B is a trust-boundary question. The gate design is defensible either way, but a
  task that tries to "prove" Gap B's severity from this repo alone cannot succeed.
- **Whether E20 was accurate against an earlier commit** is not established. `local_service.py`'s
  last three touches (`3b313b6d1`, `2db24b362`, `02f78b034`, the PRI-16 "SaaS-mediated CLI tracker
  reflow") were not diffed to check whether `build_connector` once supported jira/linear.
- **`#3030`'s "seven independent places" of FR-003 violation is unreconstructed.** The mission
  brief says seven; module docstrings at `tracker/egress_consent.py:60-61` say "four" places (and
  spec.md:225 says "fourth independent occurrence"). The historical violation count was never
  rebuilt from source history.
- **`TrackerProjectConfig._extra`'s consumers: three are now known, the rest are still unaudited.**
  Two are production sites this Mission's own field promotion **breaks** — `saas_service.py:219` and
  `:316`, which preserve a committed `egress` only because it rides in `_extra`. The third is a test
  that pins the contract: `tests/specify_cli/tracker/test_binding_report_only.py:254-268`'s
  `test_apply_binding_upgrade_preserves_extra_fields`, asserting
  `svc._config._extra == {"future_flag": True}` against the exact line B1 modifies. That file plus
  `tests/specify_cli/sync/test_worktree_clean_invariant.py` measure **`35 passed in 54.65s`, exit 0**,
  and are now a Stage-0 baseline. What remains unaudited is whatever else reads `_extra`; promoting
  `egress` to a known field is the mitigation, not the answer.
- **`LocalTrackerService.sync_publish` does not exist.** `TrackerService.sync_publish`
  (`service.py:202-203`) delegates unconditionally, so `spec-kitty tracker sync publish` on a
  `beads`/`fp` binding raises `AttributeError`, which `_run_or_exit` (`tracker.py:346-351`) only
  catches for `RuntimeError`/`ValueError`. A live, pre-existing bug, **incidental to this
  Mission** — file it, do not absorb it into this Mission's scope.
- **Chain B is named but not touched, and the follow-up issue must be framed so it gets done.**
  The earlier framing — *"consolidate the two consent chains"* — is large, unbounded and will be
  deferred indefinitely. The correct framing is small and bounded: ***finish `#3030` FR-031's
  migration at the two remaining enforcement sites.*** Three modules were already migrated and each
  carries its in-source rationale: `sync/body_upload.py:66-88`, `sync/emitter.py:65`,
  `invocation/adapters.py:51`, with the supporting argument at `sync/__init__.py:346`. **Two
  enforcement sites remain** — `sync/batch.py:338` (`_is_checkout_sync_enabled_for_batch`, reached
  from the drain gate) and `sync/runtime.py:106` — plus **two display-only reads** of
  `routing.effective_sync_enabled` at `cli/commands/sync.py:1964,2081`. The **named canonical
  replacement** is `sync/body_upload.py::project_consents_to_hosted_sync` (`body_upload.py:54`,
  rationale `:60-88`). **The reachability sentence that makes it urgent rather than tidy:**
  `_build_checkout_sync_routing` falls through to
  `SyncConfig().get_repository_sync_enabled(repo_slug)` (`routing.py:194-200`) when both the
  project-local and checkout-local records are `None`, and `enable_checkout_sync` writes that
  repo-slug-keyed record on **every** opt-in (`routing.py:325`) — **so a fresh clone of an
  already-opted-in repository drains events that Chain A denies.** File it **before implementation
  starts**; do not absorb it here.
- **The Channel-1 reporting classifier is debt, and its retirement is scheduled, not hoped for.**
  It exists only because the resolver port is `Callable[[Path], bool]`
  (`invocation/adapters.py:81`) and discards *why* a project is refused. When Bundle B's **Q3**
  gives that contract a decision return value, the classifier and both of its
  non-authoritativeness pins are **deleted**. Until then it must offer
  `checkout_roots=[routing.repo_root]` — the same root the registered resolver offers — or the
  reported Channel-1 state can contradict the enforced one; and it is an **unregistered runtime
  consumer** of `specify_cli.sync.consent`, reaching around the registry indirection that keeps the
  package boundary clean. Both are recorded costs of keeping Q3 closed, not oversights.
- **Citations must be revalidated before they are trusted.** Roughly **forty** exact line citations
  across this dossier are pinned to `bb2020fea`, while implementation is deferred to a later base.
  Before implementation: record the **actual base SHA**; run `git diff --stat bb2020fea..<base>`
  over `src/specify_cli/tracker/`, `sync/`, `cli/commands/` and `invocation/`; and **re-derive every
  cited line by symbol name (`grep`), never by line number**. A moved line is bookkeeping; a symbol
  that moved **semantically** — changed signature, relocated gate, changed default — is a
  **re-plan trigger**. Four drifts were already found and corrected in this revision at
  `bb2020fea` itself: `preserve_quotes` is `config.py:160` not `:165`; the ownership-mode default is
  `config.py:39` not `:38`; `def doctor` is `sync.py:5737` not `:5736`; the `_extra` carry-forward
  pattern is `saas_service.py:219,316` not `:220,317`.
- **Test-suite health beyond the executed suites is unknown, and each baseline now carries a
  predicted delta.** A re-measurement without a prediction has no control. Measured green at
  `bb2020fea`, unpiped, exit status trusted: `154 passed` (six consent/boundary suites) —
  **movement expected**, the set contains `tests/architectural/test_egress_consent_boundary.py`,
  which `#3113` modifies; `27 passed` (that guard suite alone) — **movement expected**, same reason;
  `519 passed, 1 warning` (`tests/sync/tracker/` + `tests/agent/cli/commands/test_tracker.py`) —
  **unchanged expected**; `15 passed` (`tests/cli/commands/test_sync_doctor_consent_health_3030.py`)
  — **unchanged expected**; and, added in this revision because `saas_service.py` entered scope,
  `35 passed in 54.65s` (**`tests/specify_cli/`**) — **unchanged expected**. **"Movement expected" on
  its own is unfalsifiable**, so the two moving predictions name a direction and a cause: the count
  **increases**, by the tests `#3113` adds; a **decrease**, or **any** movement when `#3113` has not
  landed, is a stop-and-attribute event. The full suite was **not** run; no red beyond the pre-existing/known roster (spec.md C-013) was encountered
  in what *was* run, but nothing broader was checked.
- **The Bundle A dependency was overstated, and the correction does not lift the halt.** `#3115`'s
  only affected test under `tests/sync/tracker/` is
  `test_saas_client.py::TestRetryBehaviors::test_429_respects_retry_after`, which this Mission does
  not touch; the pollution is **CI-shard-only** and explicitly **not locally reproducible**; and the
  `519 passed` baseline was measured **serially with A unlanded**. So waiting on Bundle A is **not a
  technical prerequisite** for this Mission's local red-first proofs, and any artefact claiming
  otherwise is wrong. **Implementation is nonetheless deferred by operator instruction**, and this
  correction is not permission to begin. The two statements are recorded together deliberately, so a
  successor cannot read one without the other.
- **`ConsentLevel` member count — a discrepancy this research surfaced, not previously recorded.**
  `tracer-evidence-base.md` §4 states `ConsentLevel` has "6 members, 3 dispatchable". Reading
  `sync/consent.py:66-86` directly at `bb2020fea` shows **5** members total —
  `PROJECT_LOCAL`, `MACHINE_INDEX`, `ENV`, `ABSENT`, `UNDETERMINED` — of which 3
  (`PROJECT_LOCAL`, `MACHINE_INDEX`, `ENV`) are dispatchable via `PROJECT_CONSENT_PRECEDENCE`
  (`consent.py:104-108`). The dispatchable count (3) matches; the total (6 vs. 5) does not. Per
  the rule that code at `bb2020fea` wins, `data-model.md` records **5**, and this is flagged here
  as an inconsistency in the evidence base rather than silently corrected without comment.
- **Two green-suite timings disagree between the two tracer files for the same six-suite run** —
  `tracer-evidence-base.md` §9.7 reports `154 passed in 54.07s`; `tracer-squad-findings.md` §8
  reports `154 passed in 51.31s`. The pass count (`154`) and exit status agree; only the wall-clock
  duration differs, consistent with two separate executions of the same suite. Recorded in
  `research/evidence-log.csv` as two rows rather than reconciled to one number.
