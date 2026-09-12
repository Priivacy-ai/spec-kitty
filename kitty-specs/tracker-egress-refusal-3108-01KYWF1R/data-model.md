# Data Model: Tracker Egress Refusal (Mission `tracker-egress-refusal-3108-01KYWF1R`)

**Authored against:** `bb2020fea` (upstream/main, 2026-07-31 08:52). Entities below are what this
Mission **introduces or touches**; the "Existing types" section describes, but does not modify,
what they compose with. Two vocabularies recur throughout and must not be conflated — see the
callout at the end of §1.

---

## 1. `tracker.egress` — the new Channel-2 key

**Location:** the `tracker:` block of the project's own committed `.kittify/config.yaml` (not a
machine-global file — the same file `ConsentLevel.PROJECT_LOCAL` reads for Channel 1).

**Value set — closed, exactly two legal strings:**

| Value | Meaning |
|---|---|
| `refused` | Refuses tracker egress. Two-way at **both** destinations. |
| `permitted` | At **`LOCAL_SUBPROCESS`**: an affirmative grant, satisfying the path **independently of Channel 1**. At **`HOSTED_SERVICE`**: a **no-op** — grants nothing, must be *reported* as a no-op rather than silently dropped. |

**Absence semantics:** the key being **missing** records nothing and defers entirely to Channel
1. Absence does not share a spelling with either recorded value — no `null`, no empty string, no
falsy sentinel doing double duty. `dict.get` would otherwise collapse "key missing" with "key
holds `null`"; the two are told apart by a **module-local sentinel** defined in `tracker/`,
carrying the same semantics as `sync/consent.py:145`'s `_MISSING` with the *reasoning* cited
rather than the object imported — importing the private sentinel across the package boundary
would give `tracker/` an import-time dependency on `sync.consent` and risk an `ImportError` out of
a gate that must never raise (NFR-003).

**A non-mapping `tracker:` block is also absence, not a fault.** `tracker: "yes"`, `tracker: [a]`,
`tracker: 3` and a null `tracker:` all reach `TrackerProjectConfig.from_dict(None)`
(`config.py:151-152` — `tracker_data if isinstance(tracker_data, dict) else None`), which returns a
default `cls()`. Channel 2 is therefore **absent** and the verdict defers to Channel 1. Stated
because the natural guess is the opposite: the block is not the key, and the key is missing.

**Anything else present at the key is a fault, and a fault refuses at both destinations** —
`Refused`, `REFUSED`, `refuse`, `deny`, `true`, `false`, `0`, `null`, an empty string, a mapping, a
list. No case-folding, no synonym table: the decode is an exact match against exactly the two
legal strings.

### The decode must be `isinstance`-guarded — measured

```python
_LEGAL = frozenset({"refused", "permitted"})

value = raw if (isinstance(raw, str) and raw in _LEGAL) else FAULT   # correct
value = raw if raw in _LEGAL else FAULT                             # raises
```

The second form raises `TypeError: unhashable type` when `raw` is a mapping or a list — the two
shapes §1 itself enumerates as fault values, both trivially authorable in YAML
(`tracker: {egress: {a: b}}`, `tracker: {egress: [a, b]}`) — from inside a function NFR-003 says
**never raises**. The `isinstance` guard comes **first**; the membership test is only reached for
`str`. A mapping and a list **at the key** are therefore members of NFR-003's probed set, which
previously listed file-level shapes only.

### The fault-carrying field shape — critical

On `TrackerProjectConfig`, the field carries the **raw loaded value plus a derived fault** — it is
**not** narrowed to an enum-or-`None`, nor to `bool | None`, at the dataclass level. The squad
measured why a narrowed type is unsafe, on the `doctrine.mode` precedent (`tracker/config.py:39`,
default `"external_authoritative"`): a committed `doctrine.mode: 42` — a known field with a value
the parser cannot use — comes back on read as the field's **default**, `'external_authoritative'`,
not as an error and not as the recorded `42`. Applied to `egress`, a narrowed type would let
`spec-kitty tracker bind` silently replace a recorded `refused` with the type's default on the
next round trip — **converting a refusing project into a permitting one** (tracer-squad-findings.md
§3.5, §3.6). So the field must retain the raw value it read, plus a fault flag computed from it,
so that "unusable" and "absent" and "a legal value" remain three distinguishable states all the
way through a `bind`/`unbind` round trip, not two.

`egress` is added to `TrackerProjectConfig._KNOWN_KEYS` (`tracker/config.py:69-72`) rather than
left reachable only through the untyped `_extra` catch-all (`config.py:107`, re-emitted at
`to_dict`, `config.py:53-67`) — a passthrough whose consumers have never been audited (see
`research.md` §5).

### Distinct from the Channel-1 vocabulary

**Channel-2 value** — the tri-state-plus-fault above: `{absent, refused, permitted, fault}` —
must never be conflated with the **Channel-1 reporting triple** (§3 below). Requirements,
messages, and `sync doctor` output name which of the two they mean, every time both appear.

---

## 2. `EgressDestination` — the closed set the verdict is asked *about*

A closed two-member set, **supplied by the caller**, never derived from a configuration read.

| Member | Where the data goes | Channel-2 polarity there |
|---|---|---|
| `LOCAL_SUBPROCESS` | An executable named by the operator's own **machine-global** tracker credential file (`factory.py:56`), invoked with issue fields as argv. spec-kitty's SaaS is not involved. | **Two-way** — `refused` refuses, `permitted` grants independently of Channel 1. |
| `HOSTED_SERVICE` | spec-kitty's own `/api/v1/tracker/…` endpoints — base URL from `resolve_runtime_target().resolved_server_url` (`saas_client.py:247`), bearer token, `X-Team-Slug`. | **Narrowing only** — `refused` refuses, `permitted` is a reported no-op; Channel 1 stays a hard prerequisite. |

### Why it is a parameter and not a derivation — measured

`TrackerService._resolve_saas_backend_for_provider` (`service.py:84-98`) substitutes
`TrackerProjectConfig(provider=provider)` **in memory** when `--provider <saas>` is passed and
**never rewrites the file**:

```
PRECONDITION on-disk provider : 'beads'
SUBJECT backend class         : SaaSTrackerService
SUBJECT in-memory cfg.provider: 'jira'
SUBJECT on-disk cfg.provider  : 'beads'   <-- what a config-reading verdict() would have seen
CONTROL (disk=jira) backend   : SaaSTrackerService
NEGATIVE CONTROL              : TrackerServiceError raised for 'beads' (the probe discriminates)
```

Three operator-reachable commands reach the hosted transport this way, all with
`allow_unbound=True`: `list-tickets --provider` (`cli/commands/tracker.py:998-1007` →
`service.py:220` → `saas_client.py:613` → `_request`), `issue-search --provider`
(`tracker.py:369-386` → `service.py:214`), `map list --provider` (`tracker.py:942-963` →
`service.py:210`). A config-derived destination reads `beads` on all three and applies the local
half — turning `tracker.egress: permitted` into an **affirmative grant to spec-kitty's hosted
service with Channel 1 absent**, which is `#3030`'s P0 boundary reopened by the key introduced to
protect it.

**Shape rules, each earning its keep:** *required* (a default would let a call site inherit a
polarity silently); *keyword-only* (positional would let the two members be transposed at a call
site with no type error); *a closed enum rather than a string* (so `mypy --strict` rejects an
invented third destination). Together with guard **G5** — every call expression passes an
`Attribute` node on `EgressDestination`, never a `Name` or a `Call` — this makes *"polarity follows
the destination"* a **checked property** rather than a remembered rule.

**Import form is load-bearing.** `EgressDestination` is imported under its own name
(`from … import EgressDestination`). An aliased import (`import … as ED`) makes every `destination`
argument an `Attribute` on `ED`, and G5 reports non-literal — a **false red**. It fails loudly rather
than silently, so it is not the dangerous class, but it is written down because it is a property of
a guard and appears nowhere in the source it guards except the docstring below.

**The enum carries a docstring, and it is a deliverable** (`spec.md` FR-017). **No guard decides
polarity for a new transport**, and the previous revision named the wrong instrument. G5 **passes**
when a new transport reuses `HOSTED_SERVICE`: the argument is still an `Attribute`, the literal set
is still exactly the two members, and the per-site clause names only the four existing sites. What
fires is **G4** — the membership/count assertion — and it fires only as a *prompt*, whose obvious
resolution is to edit the guard. So the requirement lives where a developer will read it: the enum's
docstring states that **adding a member, or pointing an existing member at a new transport, requires
an operator decision on that member's Channel-2 polarity**, and cites FR-004 as where the decision is
recorded. Neither G4 nor G5 substitutes for that decision; they only make its absence visible.

---

## 2a. The verdict type — `tracker_egress_verdict(root, *, destination)`

```python
def tracker_egress_verdict(
    root: Path | None,
    *,
    destination: EgressDestination,
) -> TrackerEgressVerdict: ...
```

The single function called by the three local gates, the hosted gate, and `sync doctor`. Its call
sites in `src/` are **exactly five enclosing functions and exactly six call expressions** — pinned
by exact membership and exact counts (spec.md FR-015 guard G4). The sixth expression is the
doctor's second destination row: the renderer prints **one row per destination**, so it asks twice.
FR-003 amends the earlier "no third function computes a combined verdict" rule to "exactly **one**
function computes it, and every caller asks it" (the earlier rule contradicted FR-012's requirement
that `sync doctor` name which channel refuses — definitionally a second combined verdict). **No
`_require_egress` helper wraps it:** a helper would satisfy G3's "first executable statement"
property with a call to the helper, which stops pinning `tracker_egress_verdict` at all.

Returned value object carries:

| Field | Shape | Notes |
|---|---|---|
| `refused` | `bool` | The enforced answer, **for the destination asked about**. |
| `refusing_channels` | set of channel identifiers | **Never just the first** — when both channels refuse, both are named, so an operator who clears one key is not surprised by a second refusal. |
| `destination` | `EgressDestination` | Echoed back, so a renderer cannot mislabel a row and a test can assert the enforced and reported rows were asked the same question. |
| Channel-1 state | one of the reporting triple (§3) | Reporting-only, non-authoritative, and **debt** — see §3. |
| Channel-2 state | `{absent, refuse, grant, fault}` + the raw value | The value vocabulary from §1. |
| operator message | `str` | Byte-identical between the local and hosted raise sites for the same Channel-1 state (spec.md FR-012, SC-016). |
| remedies | ordered list | Includes the Channel-2 grant remedy at `LOCAL_SUBPROCESS`; at `HOSTED_SERVICE` it instead states that a recorded grant does not apply there. |

**There is no `binding_kind` field, and the function never reads the provider.** The `none` binding
kind of the previous revision existed only to describe a root the function could not classify; with
the destination supplied, `root=None` — reachable only from `SaaSTrackerClient._request`, whose
`self._project_root` is `Path | None` — is simply `HOSTED_SERVICE` with Channel 2 absent, and must
answer with text byte-identical to `UNDETERMINED_PROJECT_REFUSAL`. Removing the binding-kind
derivation also removes a **second read of the project config inside the verdict**: it now reads
the file exactly once, for Channel 2's value.

**Never raises** (NFR-003): every input to Channel 2's resolver and to the classifier that
produces the Channel-1 state — unreadable file, unparseable YAML, non-mapping `tracker:` block, a
**mapping or a list at the `egress` key**, absent file, `root=None`, a `repo_root` that is not a
project root — returns a value object, for **both** destinations. Hosted-sync imports needed for
the Channel-1 state (`resolve_project_consent`, `resolve_checkout_sync_routing_readonly`) are
imported **at call time inside a guarded block**, degrading to generic Channel-1 wording on failure
rather than propagating `ImportError` out of a gate that must never raise.

**Internal decomposition — a requirement, not a style note.** A conservative, feature-complete
single function measures `C901 17 > 15`, over the charter's ceiling, and no blanket `# noqa` is
permitted (NFR-005). The shape that fits:

| Piece | Form | Measured complexity |
|---|---|---|
| the 8-cell join | module-level `_JOIN: dict[tuple[str, EgressDestination], str]`, **exactly 8 entries** | 0 — it is data |
| Channel-2 decode | helper (`isinstance` guard + membership) | ≤ 3 |
| Channel-1 resolution | helper (guarded call-time import + `project_egress_refusal`) | ≤ 3 |
| Channel-1 reporting classifier | helper | ≤ 3 |
| message + remedy composition | helper | ≤ 3 |
| `tracker_egress_verdict` | short composition over the above | small |

`_JOIN` also gives the *"exactly 8 cells"* criterion a **structural** pin — `len(_JOIN) == 8` —
rather than only a test-local counter. The structural half survives the test being deleted; the
parametrised half survives an entry being wrong. Both are required (SC-015).

**Composition rule (FR-005):** both channels are **always evaluated** — never a Channel-1-first
short-circuit, because the granting half (Channel 2 `permitted` at `LOCAL_SUBPROCESS`) must be able
to satisfy the path even when Channel 1 alone would deny. The combination is a total, enumerated
**8-cell** table, and it *is* `_JOIN`:

| Channel-2 value | `LOCAL_SUBPROCESS` | `HOSTED_SERVICE` |
|---|---|---|
| `fault` (any present value outside the closed pair) | **refuses** | **refuses** |
| `refused` | **refuses** | **refuses** |
| `permitted` | **permits, independently of Channel 1** | no-op, **reported as a no-op**; Channel 1 decides |
| `absent` (key missing, or a non-mapping `tracker:` block) | defers to Channel 1 | defers to Channel 1 |

---

## 3. The Channel-1 reporting triple — reporting-only, non-authoritative

Three states, obtained by a classifier that runs only **after** Channel 1's refusal is already
decided by the one true derivation (`project_egress_refusal` → `resolve_egress_consent` →
`permits_egress`), never a second computation of the verdict itself:

| State | Meaning | Remedy named |
|---|---|---|
| **no record** | Nothing was recorded for this project at any Channel-1 level. | Record `sync.enabled: true`, or run `spec-kitty sync opt-in`, or record the Channel-2 grant (needs no project identity). |
| **recorded refusal** | A Channel-1 refusal exists (e.g. committed `sync: {enabled: false}`). | Change the recorded decision, or record the Channel-2 grant. |
| **not consentable** | Project identity did not resolve (no `project.uuid`), so `enable_checkout_sync` raises `ConsentIdentityUnresolvedError` (`routing.py:320-321`) and hand-authoring `sync.enabled: true` still denies. | `spec-kitty init` (mints an identity, after which the "no record" remedies apply), or the Channel-2 grant (needs no identity at all). |

**This triple is deliberately not a fourth `EgressConsent` member and not a `ConsentLevel`
change** — see `research.md` §2, options 2–3. It is pinned non-authoritative by a test that forces
every one of the three labels while Channel 1 actually permits, and asserts the command still
permits; and by a test that makes the classifier raise, asserting the refusal still prints with
generic wording. Its inputs are `resolve_checkout_sync_routing_readonly(root).project_uuid`
(present or not) and, when identity resolves, `resolve_project_consent(uuid, checkout_roots=[routing.repo_root]).level`.

### The classifier is recorded debt, with a cause and a retirement condition

**Cause.** It exists only to recover information the resolver port **discards**. The registry
contract is `Callable[[Path], bool]` (`invocation/adapters.py:81`) and manufactures an
`EgressConsent` member from that bool, so *why* a project is refused is thrown away at the boundary
and has to be re-derived alongside it. The classifier is that re-derivation. It is not a design
element; it is the shape of a missing return type.

**Retirement condition.** When the resolver contract returns a **decision value** rather than a
bool — sibling Bundle B's open **Q3** — the classifier **and both of its non-authoritativeness
pins are deleted**, not migrated.

**And it is recorded in source, not only here** (`spec.md` FR-017, deliverables 4 and 5). Everything
above lives in `kitty-specs/…/`; **Bundle B's implementer opens `src/specify_cli/tracker/` and
`src/specify_cli/egress/` and will never read it.** So the **module docstring of
`egress_verdict.py`** and the **classifier function's own docstring** are named deliverables, each
carrying (a) the cause, citing **`invocation/adapters.py:81`** by file and line; (b) the retirement
condition — Q3 opening means **delete, not migrate**, with both non-authoritativeness pins named;
and (c) the unregistered-consumer note. They are pinned by the **same docstring test** already
specified for `local_service.py:8`, and the test asserts the literal strings `invocation/adapters.py:81`,
`Q3`, `delete` and `not migrate` are present — so the condition cannot be softened into a "consider
revisiting" by a later edit that still passes.

**Two properties it must satisfy while it exists.**

1. **Same root as the enforcer.** It offers `checkout_roots=[routing.repo_root]` — the *same* root
   the registered resolver offers. Otherwise the reported Channel-1 state can contradict the
   enforced one, which reproduces the *"tells the operator to do what they just did"* pathology
   this Mission exists partly to fix. Pinned by a test that invokes a checkout **from a
   subdirectory** and asserts the classifier's root and the resolver's root are equal.
2. **It is an unregistered runtime consumer of `specify_cli.sync.consent`.** It reaches around the
   registry indirection that keeps the package boundary clean, by call-time guarded import
   (NFR-003). That is a recorded, accepted cost of keeping Q3 closed — named here so it appears in
   a boundary audit as a known exception rather than as a surprise. It retires on the same
   condition.

**Do not confuse this with the Channel-2 value set.** "No record / recorded refusal / not
consentable" is Channel 1's *reporting* vocabulary; "absent / refused / permitted / fault" is
Channel 2's *value* vocabulary. They describe two different channels and neither substitutes for
the other in a message or in `sync doctor`'s output.

---

## 4. Existing types composed with — described, not modified

| Type | Location | Shape | Role in this Mission |
|---|---|---|---|
| `EgressConsent` | `invocation/adapters.py:41-74` | 4 members: `GRANTED`, `DENIED`, `NO_RESOLVER`, `UNANSWERABLE`. `permits_egress` (`:74`) is `self is GRANTED` — the single place the verdict becomes a branch. | Unchanged. Channel 1 still resolves through this type exactly as before; no fifth member. |
| `ConsentLevel` | `sync/consent.py:66-86` | **5 members** — `PROJECT_LOCAL`, `MACHINE_INDEX`, `ENV`, `ABSENT`, `UNDETERMINED` — of which 3 are dispatchable via `PROJECT_CONSENT_PRECEDENCE` (`consent.py:104-108`). `ABSENT` and `UNDETERMINED` are terminal outcomes, not dispatch levels. **Correction:** `tracer-evidence-base.md` §4 states "6 members, 3 dispatchable"; the code at `bb2020fea` has 5 total (dispatchable count of 3 is correct). See `research.md` §5. | Unchanged. No tracker-scoped member is added (algebra mismatch, `research.md` §2 option 2). |
| `ConsentDecision` | `sync/consent.py:112-118` | `@dataclass(frozen=True)`: `granted: bool`, `level: ConsentLevel`, `project_uuid: str \| None`, `reason: str`. | Its `.level` feeds the Channel-1 reporting classifier (§3) for messages only — never for the enforced verdict. |
| `CONFIG_FAULT_KINDS` | `sync/config.py:78-83` | 4 kinds: `unreadable`, `unparseable`, `wrong_shape`, `unusable`. Pinned by exact equality at `tests/sync/test_consent_fault_vocabulary_3030.py:261`. | **Not extended.** A tracker-key fault is reported by a **new** renderer beside the consent-readability one, not by adding a fifth kind to this set. |
| `TrackerProjectConfig` | `tracker/config.py:29-72` | `@dataclass(slots=True)`. Fields: `provider`, `binding_ref`, `project_slug`, `display_label`, `provider_context`, `workspace`, `doctrine_mode` (default `"external_authoritative"`, `:39`), `doctrine_field_owners`, `_extra`. `_KNOWN_KEYS` (`:69-72`) currently: `provider`, `binding_ref`, `project_slug`, `display_label`, `provider_context`, `workspace`, `doctrine`. | Gains `egress` as an eighth known field (§1), carrying the raw value plus a fault rather than a narrowed type. **Consequence, not a side note:** `from_dict`'s `_extra` comprehension (`config.py:107`) excludes `_KNOWN_KEYS`, so this promotion is what breaks lifecycle sites B1/B2 (§5). |
| `preserve_quotes` reach | `tracker/config.py:160` (`save_tracker_config`), **absent** at `:138` (`load_tracker_config`) and at `:184` (`clear_tracker_config`) | `save_tracker_config` sets `yaml.preserve_quotes = True`; the other two build plain `YAML()` objects. | `load_tracker_config` may gain it for FR-010 byte-identity, and `clear_tracker_config` must gain it so `unbind` stops destroying sibling-block quoting. **Blast radius, measured rather than guessed:** `from_dict` `str()`-coerces every known string field, so the ruamel scalar-string subclass survives on **only** `_extra` values and the raw `egress` — not on "every string loaded from `tracker:`". |

---

## 5. Lifecycle — a recorded tracker-egress decision outlives its binding

A committed `egress` value must survive `bind`, `rebind` and `unbind`. The inventory below is
**re-derived from `grep -n "TrackerProjectConfig(" src/`**, not recalled — the previous revision
listed three sites and missed three more, one of which erases **today** on the destination where
Channel 2 is the only narrowing conjunct.

Measured, with controls (tracer-squad-findings.md §3.6, plus this revision's probe):

```
CONTROL: from_dict puts unknown key into _extra          _extra = {'egress_refused': True}   ok
CONTROL: save of a LOADED config preserves it            egress_refused present: True         ok
SUBJECT: bind (service.py:163 path)                      egress_refused present: False        erased
SUBJECT: unbind (clear_tracker_config)                   egress_refused present: False        erased
         sibling `sync:` block still present (control)   True                                  ok

BEFORE: tracker: provider: linear / project_slug: p / egress: refused
AFTER  SaaSTrackerService.bind:            egress present? False    <-- erases TODAY
CONTROL (_extra-carrying pattern):         egress present? True
```

**All nine `TrackerProjectConfig(` construction sites in `src/`, classified.** Seven can reach
`save_tracker_config` — one of them only through a future caller, one only through a library caller;
two cannot.

| # | Site | Class | What it does today | What it must do |
|---|---|---|---|---|
| A1 | `LocalTrackerService.bind` (`local_service.py:57`) | **erases today** | Builds a **fresh** config from its arguments and calls `save_tracker_config` — everything committed and not passed as a constructor argument is discarded, including any recorded `egress`. | Load the committed config first and carry `egress` (and `_extra`) forward. |
| A2 | `TrackerService.bind`, local branch (`service.py:163`) | **erases today** | `LocalTrackerService(self._repo_root, TrackerProjectConfig())` — hands the constructor an **empty** config, in contrast to the SaaS branch above it (`service.py:142-145`), which passes `load_tracker_config(self._repo_root)`. The argument is a lie about what is on disk. | Hand `bind` the **loaded** config, matching the SaaS branch. |
| A3 | `SaaSTrackerService.bind` (`saas_service.py:266`) | **erases today** | Builds a bare `TrackerProjectConfig(provider=…, project_slug=…)` carrying **nothing** forward, then saves. Measured above. **Missed by every previous revision**, and it is the site where Channel 2 is the *only* narrowing conjunct. | Carry `egress` (and `_extra`) forward from the loaded config. |
| A4 | `TrackerService._resolve_saas_backend_for_provider` (`service.py:98`) | **defence-in-depth — NO production write path, NO red-first pin** | Substitutes a fresh `TrackerProjectConfig(provider=provider)` when the requested provider differs from disk; that object becomes the `SaaSTrackerService`'s `self._config`, so a `_persist_binding` on it *would* write an **empty** `_extra` and no `egress`. **Measured: it cannot be reached from any write today.** `_persist_binding`'s three call sites (`saas_service.py:347`, `:412`, `:505`) all sit inside bind flows (`_confirm_and_persist`, `_bind_from_resolution`, `validate_and_bind`) entered from `TrackerService.bind` (`service.py:141-145`), which builds its own service with `load_tracker_config`. `_resolve_saas_backend_for_provider` serves only the three **read** paths (`service.py:210,214,220`), whose methods (`saas_service.py:556,575,592`) persist nothing. The only other write path, `apply_binding_upgrade` (`saas_service.py:191`), has **zero callers in `src/`** — tests only. | Carry the loaded config's `egress` (and `_extra`) into the substituted object, or make a substituted config non-persistable — **so a future write-capable caller cannot reintroduce the erasure.** Assert at the unit level against the substituted object. **Do not write a red-first pin for this site: there is no production path to red it.** |
| B1 | `saas_service.py:206-219` — construction at **`:206`**, `_extra=` carry at **`:219`** (the binding-ref upgrade inside `apply_binding_upgrade`) | **works today; §1's promotion breaks it** | Preserves a committed `egress` **only because it currently rides in `_extra`** (`_extra=self._config._extra`). | Gain an explicit `egress=` carry. `from_dict` excludes known keys from `_extra` (`config.py:107`), so promoting `egress` to `_KNOWN_KEYS` **destroys** the mechanism that makes this line correct. **Both line numbers are cited so the `grep` this inventory instructs — which finds `:206` — and the citation agree.** |
| B2 | `saas_service.py:303-316` — construction at **`:303`**, carry at **`:316`** (`_persist_binding`) | **works today; §1's promotion breaks it** | Same, via `_extra=dict(self._config._extra)`. | Same. |
| C | `clear_tracker_config` (`config.py:178-194`) | **erases today** | Unconditional `del payload["tracker"]` at `:191` — deletes the whole block, including a committed `egress`. It also builds a **third** `YAML()` at `config.py:184` with **no** `preserve_quotes` and dumps straight to the handle, so `unbind` destroys quoting in sibling blocks. | Retain a `tracker:` block holding only a recorded `egress` when one exists; delete the block entirely when none is recorded; set `preserve_quotes`. |
| D | `SaaSTrackerService.unbind` (`saas_service.py:281`) | **library-caller reachable only** | Resets `self._config = TrackerProjectConfig()` **in memory** after `clear_tracker_config`. A subsequent `_persist_binding` **on the same instance** would then write a config with no `egress` — **erasing exactly what site C was just fixed to preserve**. The CLI builds a fresh service per invocation, so no command reaches it today. | Reset to `load_tracker_config(self._repo_root)`, so the in-memory object matches what C just left on disk. Listed rather than silently excluded, because "in-memory only" is precisely the reasoning that would otherwise have skipped it. |
| — | `origin.py:536`, `config.py:142` | **not in scope** | Construct configs returned to callers that **never reach `save_tracker_config`**. Checked and stated, so the next reader does not have to re-derive the negative. | Unchanged. |

**The trap this table exists to disarm:** B1 and B2 were cited by the previous revision as *"the
pattern to copy"*. They are the two lines this Mission's own field-shape change **breaks**. Copying
them without fixing them yields a Mission that preserves the key at the site it added and loses it
at the two sites it held up as correct.

**Landing rule.** The field-shape change (§1) and the preservation work at A1–A3, A4, B1–B2, C and D
**land as one change** — or, if split, a guard is added asserting that every `TrackerProjectConfig(`
construction whose value flows into `save_tracker_config` carries `egress`. **There is no
"no blast radius" data-layer stage:** promoting the field is exactly what breaks B1 and B2.

**Existing test coverage of these sites, which entered the blast radius together with
`saas_service.py` and appeared in no earlier revision.**
`tests/specify_cli/tracker/test_binding_report_only.py:254-268` holds
`test_apply_binding_upgrade_preserves_extra_fields`, asserting
`svc._config._extra == {"future_flag": True}` — the forward-compat `_extra` contract at **`:219`,
the exact line B1 modifies**. `tests/specify_cli/sync/test_worktree_clean_invariant.py:22` documents
the `apply_binding_upgrade` / `bind` write boundary. Measured together:
**`35 passed in 54.65s`, exit 0.** That test is a **detection signal, not a planned edit**: `_extra`
must keep carrying `future_flag` after `egress` stops riding in it. If it reds, the B1 fix
**replaced** the `_extra` carry instead of adding an `egress` carry beside it — do not "repair" it
by weakening the assertion.

**Where the reds are, and where they are not.** A1, A3 and C red **on the base** (measured). B1 and
B2 red only on the **§1-only tree** — the same tree on which the FR-009 null-planting red must
already be observed, so all three reds are observed and quoted at that single measurement point.
**A4 reds nowhere**: it has no production write path, and an implementer who writes a red-first pin
for it is writing a pin against code no production path executes.

**Recorded semantics:** deleting a `refused` is a **silent fail-open**; deleting a `permitted`
silently withdraws a working local binding that needed no Channel 1 grant. Neither is safe to
guess at on rebind, so the rule is symmetric across the tri-state: **a recorded tracker-egress
decision outlives its binding**, in both directions, and erasure must never be confusable with
absence — which is precisely what a missing key means after `egress` is promoted to a known
field (§1).

A companion write-side rule closes the loop: `save_tracker_config`'s `to_dict` must **omit**
`egress` from the emitted `tracker:` block when no decision is recorded, rather than emitting a
written-out `null` the way `to_dict` currently emits every other unset known field
(`config.py:53-67`). Without this, `spec-kitty tracker bind` — the very command that creates a
working binding — would write `egress: null`, which §1's fault rule reads as a fault, which
refuses: the binding command would disable the binding it just created.

### Reconciliation note — 2026-08-31 (#782)

G4's authoritative census is **5 enclosing functions / 5 call expressions**: the three local gates, `SaaSTrackerClient._current_tracker_egress_verdict`, and `_check_sync_readiness`. The no-helper rule is scoped to G3's three local sites; the hosted `_enforce_tracker_egress_consent` helper remains structurally guarded.
