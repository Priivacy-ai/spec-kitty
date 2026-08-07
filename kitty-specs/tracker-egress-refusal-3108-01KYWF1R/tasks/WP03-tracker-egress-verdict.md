---
work_package_id: WP03
title: 'tracker_egress_verdict: one function, one message, never raising'
dependencies:
- WP02
requirement_refs:
- C-002
- C-003
- C-004
- C-005
- C-008
- C-011
- C-017
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
- FR-008
- FR-012
- FR-017
- NFR-003
- NFR-005
planning_base_branch: bundle-c-tracker-refusal-3108
merge_target_branch: bundle-c-tracker-refusal-3108
branch_strategy: Planning artifacts for this mission were generated on bundle-c-tracker-refusal-3108. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into bundle-c-tracker-refusal-3108 unless the human explicitly redirects the landing branch.
created_at: '2026-08-01T00:20:00+00:00'
subtasks:
- T015
- T016
- T017
- T018
- T019
- T020
phase: Stage 3 - The verdict function, before either gate
history:
- at: '2026-08-01T00:20:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks-packages
agent_profile: python-pedro
authoritative_surface: src/specify_cli/tracker/egress_verdict.py
create_intent:
- src/specify_cli/tracker/egress_verdict.py
- tests/sync/tracker/test_tracker_egress_verdict_3108.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/tracker/egress_verdict.py
- tests/sync/tracker/test_tracker_egress_verdict_3108.py
role: implementer
tags: []
task_type: implement
tracker_refs:
- '3108'
---

# Work Package Prompt: WP03 – `tracker_egress_verdict`

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter and behave per its
guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`

---

## Objective

Write the **one** function that composes the two consent channels and a caller-supplied destination
into a single value object — the object both gates raise from and `sync doctor` renders — so that the
enforced answer and the reported answer **cannot disagree**.

**Done** = `src/specify_cli/tracker/egress_verdict.py` exists with `EgressDestination`,
`tracker_egress_verdict(root: Path | None, *, destination: EgressDestination)`, the verdict value
object, Channel 2's `isinstance`-guarded resolver, the module-local absence sentinel and the
Channel-1 reporting classifier; `len(_JOIN) == 8` holds structurally; the never-raises contract holds
over **24** cases; and `ruff check` is clean with **no `# noqa: C901`** on the new module.

**There are still zero call sites.** This WP adds a pure function with a value object and **zero blast
radius**. Guards G4 and G5 do not land here — they assert five call sites and there are none.

---

## Boundaries — what this WP may touch

**Owned files — the only files you may create or edit:**

- `src/specify_cli/tracker/egress_verdict.py` (new)
- `tests/sync/tracker/test_tracker_egress_verdict_3108.py` (new)

**Hard boundary.** You may not edit files another WP owns:
`src/specify_cli/tracker/config.py`, `service.py`, `saas_service.py` (WP02);
`src/specify_cli/tracker/local_service.py`, `src/specify_cli/cli/commands/tracker.py`,
`tests/sync/tracker/test_local_service.py`, `CHANGELOG.md` (WP04);
`src/specify_cli/tracker/saas_client.py` (WP05); `src/specify_cli/cli/commands/sync.py` (WP06);
`tests/sync/tracker/test_tracker_egress_refusal_3108.py` (WP01);
`tests/architectural/test_tracker_egress_guards_3108.py` (WP07).

**Explicitly unchanged, and you must not change them:**
`src/specify_cli/tracker/egress_consent.py` (Channel 1 — `project_egress_refusal`),
`src/specify_cli/invocation/adapters.py` (`EgressConsent`, the `Callable[[Path], bool]` port),
`src/specify_cli/sync/consent.py` (`ConsentLevel`, `PROJECT_CONSENT_PRECEDENCE`),
`src/specify_cli/tracker/factory.py`.

**Dependency: WP02.** You may assume, and must not re-implement:

- `TrackerProjectConfig` has an `egress` field in `_KNOWN_KEYS` carrying **the raw loaded value plus a
  derived fault**, never a narrowed type.
- **The module-local absence sentinel is `EGRESS_ABSENT`, defined in
  `src/specify_cli/tracker/config.py`** — a **public** name (no leading underscore) precisely so you
  can import it across the module boundary without reaching for a private symbol in a file you do
  not own. It distinguishes *"key missing"* from *"key holds `null`"*. **Import it; do not define a
  second one, and do not compare against `None` as a substitute** — `None` is a *fault* value here,
  not absence, and collapsing the two is the specific defect the sentinel exists to prevent.
- A **non-mapping `tracker:` block is absence, not a fault**.
- `load_tracker_config` still **raises** `TrackerConfigError` on an unparseable file
  (`config.py:148-149`) — your function must catch it.

If WP02's field or `EGRESS_ABSENT` is not on the branch you are working from, **stop**. Do not add
the field yourself and do not define your own sentinel — you own only `egress_verdict.py`, so a
sentinel you define here is a second one, and the two will disagree.

---

## Requirements this WP satisfies

### FR-003 — One named `tracker_egress_verdict(root, *, destination)`

> *"I want exactly **one** function that composes the two channels for a **named destination**, so
> that the enforced answer and the reported answer cannot disagree. **Signature:**
> `tracker_egress_verdict(root: Path | None, *, destination: EgressDestination)` — `destination` is
> **required and keyword-only**, and `EgressDestination` is a closed two-member set, `LOCAL_SUBPROCESS`
> and `HOSTED_SERVICE`. It returns a value object carrying: `refused`, the set of `refusing_channels`
> (never just the first), the Channel-1 state (no record / recorded refusal / not consentable), the
> Channel-2 state (**`absent` / `refused` / `permitted` / `fault`**, with the raw value), **the
> destination it was asked about**, the operator message and its remedies. **There is no
> `binding_kind` field and no binding-kind derivation** — the caller states the destination; the
> function never reads the provider."*

> *"Call sites in `src/`, pinned by exact membership and exact count (FR-015 G4): exactly five
> enclosing functions […] and **exactly six call expressions**, because the doctor renderer calls it
> once per destination."* **You create none of them.**
>
> *"**No `_require_egress` helper is introduced**: a helper would let G3's 'first statement' property
> be satisfied by a call to the helper, which stops pinning `tracker_egress_verdict` at all."*

**One spelling of the Channel-2 vocabulary, and this is it: `absent` / `refused` / `permitted` /
`fault`.** An earlier revision spelled two of the four `refuse` / `grant`. **They are not
interchangeable.** These four strings are simultaneously (a) the Channel-2 **state field** on the
verdict value object and (b) the **first element of every `_JOIN` key**, so the field's value is
looked up in the table directly. If the field says `refuse` and the table is keyed on `refused`, the
lookup is a **`KeyError` inside a function NFR-003 says never raises** — a defect no test in this WP
would catch except by accident, because both spellings look right in isolation. Use **`refused`** and
**`permitted`**, matching the two on-disk values **exactly**, which is also what lets the fault
message quote the legal values without translating them. This spelling is binding everywhere it
appears, including WP06's renderer.

**Where the drift actually is, so you do not have to hunt for it.** `data-model.md:278` already
spells them correctly — *"absent / refused / permitted / fault"*. **`spec.md` FR-003 (line 616) still
spells them `absent / refuse / grant / fault`**, and the blockquote above is this prompt's corrected
rendering of that same sentence. **The on-disk values win**: `refused` and `permitted` are the two
strings an operator writes into `.kittify/config.yaml` and the two the fault message must name
verbatim, so any vocabulary that does not match them costs a translation layer that exists only to
be wrong once. **Report the `spec.md` drift; do not follow it, and do not edit `spec.md` to chase
it** — it is not yours.

### FR-004 — Polarity follows the destination, and the destination is a parameter

At **`LOCAL_SUBPROCESS`** Channel 2 is **two-way**: `refused` refuses, `permitted` is an affirmative
grant that satisfies the path **independently of Channel 1**. At **`HOSTED_SERVICE`** Channel 2 is
**narrowing only**: it may refuse, it may not grant, and Channel 1 remains a hard prerequisite —
because that path sends to **spec-kitty's hosted service** (`saas_client.py:247` resolves `_base_url`
from `resolve_runtime_target().resolved_server_url`; every endpoint is `/api/v1/tracker/…` with a
bearer token and `X-Team-Slug`), which holds the Jira/Linear connector and relays.

### FR-005 — The combination is a total, enumerated 8-cell table

> *"the granting half means **both channels are always evaluated** — a Channel-1-first short-circuit
> would refuse a project that Channel 2 permits."*

| Channel-2 value | `LOCAL_SUBPROCESS` | `HOSTED_SERVICE` |
|---|---|---|
| `fault` (any present value outside the closed pair) | **refuses** | **refuses** |
| `refused` | **refuses** | **refuses** |
| `permitted` | **permits, independently of Channel 1** | no-op, **reported as a no-op**; Channel 1 decides |
| `absent` (key missing, or a non-mapping `tracker:` block) | defers to Channel 1 | defers to Channel 1 |

> *"**The table is a data structure, not a branch chain**: a module-level
> `_JOIN: dict[tuple[str, EgressDestination], str]` holding **exactly 8** entries, so `len(_JOIN) == 8`
> is a **structural** pin that a test-local counter is not — and so the join contributes no cyclomatic
> complexity."*
>
> *"When more than one channel refuses, the message names **all** of them, so an operator who clears
> the tracker key is not surprised by a second refusal."*

**The join's VALUE vocabulary — four outcomes, not two — enumerated here because whatever labels you
invent become the contract `sync doctor` branches on.** `_JOIN`'s value type is `str`, and nothing
above says which strings. It is **not** a two-valued refuse/permit: `permitted` at `HOSTED_SERVICE`
behaves like *defer* but must be **reported differently**, and a renderer that cannot tell those two
apart cannot satisfy SC-014's checkout 6. Use exactly these four, and put them in named module
constants:

| Outcome | Meaning | Which cells |
|---|---|---|
| **`refuse`** | Channel 2 decides the answer, and the answer is no. | `fault` and `refused`, at **both** destinations — 4 cells. |
| **`permit`** | Channel 2 is an **affirmative grant** that satisfies the path **independently of Channel 1**. Channel 1 is still evaluated (FR-005 forbids a short-circuit) but does not decide. | `permitted` at **`LOCAL_SUBPROCESS`** — 1 cell. |
| **`defer`** | Channel 2 records nothing. Channel 1 decides, and the message says nothing about a tracker key because there is nothing to say. | `absent` at **both** destinations — 2 cells. |
| **`defer_reported_noop`** | Channel 1 decides, **and** the verdict carries the fact that a Channel-2 grant **is recorded and does not apply here**, so the message and the doctor row can say so. Distinct from `defer` in exactly one respect — what gets reported — and that respect is a requirement, not a nicety. | `permitted` at **`HOSTED_SERVICE`** — 1 cell. |

4 + 1 + 2 + 1 = **8**. If your four labels differ from these, that is tolerable only if you write them
in the module docstring and they are the ones WP06's renderer is handed — but there is no reason to
differ, and a rename after WP06 lands is a cross-WP break.

**Note the asymmetry deliberately:** `defer` and `defer_reported_noop` produce the **same enforced
answer** for every Channel-1 state. They differ only in what the verdict object reports. Collapsing
them into one value is the change that makes SC-014's *"two different answers on its two rows"*
checkout unrenderable and leaves the operator believing their key did nothing.

### FR-006, FR-007, FR-008

- **FR-006** — Channel 1 absence **denies**; Channel 2 absence **records nothing** and defers. The
  decode is `isinstance(raw, str) and raw in _LEGAL`, never `raw in _LEGAL` alone.
- **FR-007** — **absence of both channels denies**. The rejected alternative (*honour recorded
  refusals, absence permits* — the tracer's own recommendation) was rejected on two grounds: the
  refusal carries its own remedy, and absence-permits rests on the **unverified** premise that
  `bd`/`fp` make no network calls (C-019 (1)).
- **FR-008** — *"the deny-on-absence decision above is NOT derivable from `#3030` FR-003"*. Undetermined
  denies **because FR-003 says so**; absence denies **because the operator chose it**.

### FR-012 — The refusal names the Channel-1 state

Channel 1 resolves to **three** states, each with its own wording and remedies:

| State | Meaning | Remedies |
|---|---|---|
| **no record** | Nothing recorded at any Channel-1 level. | `sync.enabled: true` in the project's own config; `spec-kitty sync opt-in`; **or** the Channel-2 grant. |
| **recorded refusal** | A Channel-1 refusal exists (e.g. committed `sync: {enabled: false}`). | Change the recorded decision, **or** the Channel-2 grant. |
| **not consentable** | Project identity did not resolve (no `project.uuid`), so `enable_checkout_sync` raises `ConsentIdentityUnresolvedError` (`routing.py:320-321`) and hand-authoring `sync.enabled: true` still denies. | `spec-kitty init` (mints an identity, after which the "no record" remedies apply), **or** the Channel-2 grant, which needs no identity. |

Every state also carries the Channel-2 grant as a remedy **when the destination is
`LOCAL_SUBPROCESS`**, and at `HOSTED_SERVICE` explicitly says the grant **does not apply there**.
*"The three-way distinction is reporting-only."*

**One message-composition function; no path-local message strings anywhere** (`plan.md` Open Items 1).
A tasks-phase test asserts the message text is produced by the verdict object and never re-composed at
a raise site.

### FR-017 — Two docstrings this Mission must **author**, and they are deliverables

> *"(4) the **module docstring of `src/specify_cli/tracker/egress_verdict.py`** and (5) **the Channel-1
> reporting classifier's own docstring**, each carrying (a) the **cause** — the resolver port is
> `Callable[[Path], bool]` at **`invocation/adapters.py:81`**, cited by file and line, and it discards
> *why* a project is refused, so the classifier is the shape of a missing return type; (b) the
> **retirement condition** — when Bundle B's **Q3** gives that contract a decision return value, the
> classifier **and both of its non-authoritativeness pins are deleted, not migrated**, both pins
> named; and (c) the **unregistered-consumer note** — the module reaches around the registry
> indirection to `specify_cli.sync.consent` by call-time guarded import, a recorded exception that
> retires on the same condition."*
>
> *"**Why in source:** Bundle B's implementer opens `src/specify_cli/tracker/` and
> `src/specify_cli/egress/`; every prior recording of this debt lives inside `kitty-specs/…/` and will
> not be read."*

The module docstring **also** states the `EgressDestination` import-form rule (FR-015 G5) so a reader
hits it before writing a call site. Per SC-019, the docstrings are asserted to contain the literal
strings `invocation/adapters.py:81`, `Q3`, `delete` and `not migrate`, *"so the retirement condition
cannot be softened into a 'consider revisiting'."*

### NFR-003 — Never raises

> *"For every input — unreadable, unparseable, wrong-shape, `tracker:` non-mapping, **a mapping at the
> `egress` key**, **a list at the `egress` key**, empty file, comments-only, chmod 000, absent file,
> `root=None`, and a `repo_root` that is not a project root — **twelve shapes, enumerated here and
> nowhere re-enumerated** — the verdict function returns a value object, **for each of the two
> destinations**: **24 cases**, and the parametrised test prints and asserts that it ran 24."*
>
> *"It never propagates `TrackerConfigError` or any other exception, and it holds **no import-time
> dependency on `specify_cli.sync`**: the hosted-sync imports it needs for the Channel-1 state
> (`resolve_project_consent`, `resolve_checkout_sync_routing_readonly`) are made **at call time inside
> a guarded block**, degrading to the generic Channel-1 refusal wording if they fail."*

### Constraints

- **C-002** — polarity fixed by destination; the destination is supplied, never inferred. *"Any
  implementation that computes the destination from a configuration read is out of contract,
  regardless of the answers it happens to give."* **And so is a provider read inside the function's
  own body** (G6).
- **C-003** — **no new `ConsentLevel` member.** `PROJECT_CONSENT_PRECEDENCE` is walked
  first-level-that-answers-wins, so a tracker key inserted there would *answer the hosted-sync
  question* — verbatim the `sync.auto_start` failure mode at `consent.py:52-56`. *"This Mission needs
  an AND-conjunct; the tuple expresses precedence. Different algebra."*
- **C-004** — **no new `EgressConsent` member; the resolver contract is unchanged; the Channel-1 state
  is reporting-only.** The enforced verdict has exactly one derivation:
  `project_egress_refusal` → `resolve_egress_consent` → `permits_egress`.
- **C-005** — two keyings because two invariants. Channel 1 keys on `project_uuid`; Channel 2 keys on
  the project whose `.kittify/config.yaml` it is.
- **C-008** — `saas_client/egress_consent.py:92` is a **second definition**, not a re-export
  (different `id`, different `__module__` from `tracker/egress_consent.py:147`). **This Mission adds
  no third definition**; `tracker_egress_verdict` is defined **once**, in `tracker/`, and the
  `saas_client/` package is not touched.
- **C-017** — raised and judged wrong; both the `ConsentLevel` and `EgressConsent` rejections survived
  steelmanning by two squad lenses. Do not re-litigate them.

### Success criteria owned here

SC-010 (the fault **wording** half), SC-015, SC-016 (the `root=None` clause), SC-019 (deliverables 4
and 5).

---

## Standing rules — binding on every measurement you make

- **Revalidate every line citation before you trust it (C-011).** Every `file.py:NNN` in this
  prompt was taken at the measurement base **`bb2020fea`** — recorded as `measurement_base_sha` in
  `wps.yaml`, so the drift diff is derivable rather than transcribed:
  `git diff --stat bb2020fea..<your base> -- <the paths you cite>`. Implementation runs on a **later**
  base. Re-derive every citation **by symbol name (`grep`), never by line number**, *before* any step
  that depends on it. **A line that moved is bookkeeping. A symbol that moved *semantically* — a
  changed signature, a relocated gate, a changed default, a new caller — is a re-plan trigger**, and
  the correct response is to stop and re-plan, not to patch the citation and continue. Four drifts
  were already found at `bb2020fea` itself, which is the evidence that this is necessary rather than
  ceremonial.
- **Never pipe a suite whose exit status you intend to trust.** `pytest … | tail` reports `tail`'s
  status and buffers until exit. **Quote the `N passed` line**; **an empty output file is no
  measurement.**
- **A killed run is neither a pass nor a fail.** Re-run it narrowed; do not explain it.
- **Measure in a `git worktree` pinned to a commit — and set `PYTHONPATH=$WT/src`.** The editable
  install hard-codes the **main checkout's** src path, so a worktree run otherwise imports the live
  tree and any "identical results" conclusion is a tautology.
- **Read the failure text, not the tally.**
- **Print the input count alongside any "all checks passed"** — a gate that ran on zero files passes
  vacuously.
- **Red first, and make the red the consequence.** Assert the bytes, not a boolean.
- **Include a positive control that must pass.**
- **Any assertion of absence must establish why the thing would otherwise have happened.**
- **Mutations as pytest plugins via `PYTHONPATH`, never source edits**, and never source edits during
  a verification run.
- **Explicit-path staging.** `git add <paths>`, never `git add -A` — 13 files were lost to a stray
  `add -A` in this lineage.
- **`ruff format` is NOT clean on this repo** (`line-length = 164`); only `ruff check` is meaningful.
- **One live agent per file.**
- **Known pre-existing failures — do not chase, do not fix in-PR, do not retry to green:**
  `tests/architectural/test_tid251_enforcement.py` (4 tests);
  `test_charter_package_exports::test_charter_package_cold_import_keeps_status_orchestration_out`;
  two `test_safe_commit_cmd::…_3033`;
  `test_charter_io::test_get_mission_id_returns_none_when_meta_json_malformed`;
  `test_doctor_ops::test_sweep_nfr_002_10k_files_under_5s` (wall-clock, fails under load).
  `ModuleNotFoundError: No module named 'typer'` in subprocess daemon tests is environmental.

---

## Measured hazards that apply to this WP — facts, not advice

**Hazard A — the decode must be `isinstance`-guarded.**

```python
_LEGAL = frozenset({"refused", "permitted"})

value = raw if (isinstance(raw, str) and raw in _LEGAL) else FAULT   # correct
value = raw if raw in _LEGAL else FAULT                             # raises
```

`raw in frozenset({...})` raises `TypeError: unhashable type: 'CommentedMap'` for a mapping and
`TypeError: unhashable type: 'CommentedSeq'` for a list — **both of which the spec enumerates as fault
values** — inside a function that **must never raise**. **The specific pin to observe red-then-green
is the mapping-at-the-key case, whose red on a bare `raw in _LEGAL` implementation is a `TypeError`,
not an `AssertionError`** — classify it as such and require the fixed implementation to return a fault
verdict.

**Hazard B — `destination` is a required keyword-only parameter, never derived.**
`TrackerService._resolve_saas_backend_for_provider` (`service.py:84-98`) overrides the on-disk
provider **in memory**, so three commands drive the hosted transport from a repository whose committed
config says `beads`:

```
PRECONDITION on-disk provider : 'beads'
SUBJECT backend class         : SaaSTrackerService
SUBJECT in-memory cfg.provider: 'jira'
SUBJECT on-disk cfg.provider  : 'beads'   <-- what a config-reading verdict() would have seen
CONTROL (disk=jira) backend   : SaaSTrackerService
NEGATIVE CONTROL              : TrackerServiceError raised for 'beads' (the probe discriminates)
```

The three commands, all with `allow_unbound=True`: `tracker list-tickets --provider jira`
(`cli/commands/tracker.py:998-1007` → `service.py:220` → `saas_client.py:613` → `_request`),
`tracker issue-search --provider jira` (`tracker.py:369-386` → `service.py:214`),
`tracker map list --provider jira` (`tracker.py:942-963` → `service.py:210`).
**Deriving polarity from the file would make `tracker.egress: permitted` a grant to spec-kitty's
hosted service with Channel 1 absent** — reopening `#3030`'s P0 boundary through the very key
introduced to protect it. *Required* (a default would let a call site inherit a polarity silently);
*keyword-only* (positional would let the two members be transposed with no type error); *a closed enum
rather than a string* (so `mypy --strict` rejects an invented third destination).

**Hazard C — the verdict must not exceed the complexity ceiling.** A conservative,
feature-complete monolithic implementation measured **`C901 17 > 15`**. The charter's ceiling is 15
and **no blanket `# noqa` is permitted**. The shape that fits:

| Piece | Form | Measured complexity |
|---|---|---|
| the 8-cell join | module-level `_JOIN: dict[tuple[str, EgressDestination], str]`, **exactly 8 entries** | 0 — it is data |
| Channel-2 decode | helper (`isinstance` guard + membership) | ≤ 3 |
| Channel-1 resolution | helper (guarded call-time import + `project_egress_refusal`) | ≤ 3 |
| Channel-1 reporting classifier | helper | ≤ 3 |
| message + remedy composition | helper | ≤ 3 |
| `tracker_egress_verdict` | short composition over the above | small |

`len(_JOIN) == 8` is a **structural** pin. *"The structural half survives the test being deleted; the
parametrised half survives an entry being wrong. Both are required."*

**Hazard D — the classifier's retirement condition goes in the source, not the dossier.**
**Bundle B's implementer opens `src/`, never this Mission's spec.** The module docstring and the
classifier's own docstring are **deliverables**, and SC-019 asserts their literal strings.

**Hazard E — an aliased import of `EgressDestination` produces a false red at guard G5.**
`EgressDestination` is imported under its own name (`from … import EgressDestination`). An aliased
import (`import … as ED`) makes each `destination` argument an `Attribute` on `ED` and G5 reports
non-literal — **loud rather than silent, but a lost afternoon for anyone who has not been told.**
Record this in the module docstring.

---

## Subtasks & Detailed Guidance

### T015 — Revalidate the 22 line citations, then the module, the enum, and the two authored docstrings

- **Purpose**: C-011 first, then FR-003's signature, FR-004's mechanism, FR-017's deliverables 4
  and 5.

  > **Step 1 is a gate on the rest of this subtask and on the whole WP.** This prompt carries
  > **more line citations into files it does not own than any other prompt on the board** — roughly
  > two dozen, into `egress_consent.py`, `invocation/adapters.py`, `sync/consent.py`, `routing.py`,
  > `service.py`, `saas_client.py`, `config.py`, `factory.py` and `cli/commands/tracker.py`. You own
  > **none** of those files, so every one of them can have moved under you without a merge conflict
  > to warn you, and several of this WP's deliverables — the docstrings' literal
  > `invocation/adapters.py:81`, the `checkout_roots=[routing.repo_root]` form, the
  > `UNDETERMINED_PROJECT_REFUSAL` bytes — are **assertions about those files' contents**. A
  > docstring asserting a line number that has moved is a deliverable that ships false on day one.

- **Steps**:
  1. **Revalidate every citation in this prompt, by symbol name (`grep`), never by line number.**
     Record the base SHA and run
     `git diff --stat bb2020fea..<base> -- src/specify_cli/tracker/ src/specify_cli/sync/ src/specify_cli/invocation/ src/specify_cli/cli/commands/tracker.py`.
     Re-derive **at minimum**, each by symbol: `project_egress_refusal` and
     `UNDETERMINED_PROJECT_REFUSAL` (`tracker/egress_consent.py`) **and their second definitions**
     (`saas_client/egress_consent.py` — C-008: a second definition, not a re-export);
     `EgressConsent` and its `Callable[[Path], bool]` port (`invocation/adapters.py:81` — **this one
     is a literal string in a deliverable docstring, so a move is a content change, not
     bookkeeping**); `resolve_egress_consent`, `permits_egress`; `resolve_project_consent`,
     `resolve_checkout_sync_routing_readonly`, `ConsentIdentityUnresolvedError`,
     `enable_checkout_sync`; `ConsentLevel`, `PROJECT_CONSENT_PRECEDENCE`, `_MISSING`
     (`sync/consent.py`); `TrackerProjectConfig`, `_KNOWN_KEYS`, `from_dict`, `to_dict`,
     `load_tracker_config`, `TrackerConfigError`, **`EGRESS_ABSENT`** (`tracker/config.py`);
     `TrackerService._resolve_saas_backend_for_provider`; `SaaSTrackerClient._request` and
     `_base_url` / `resolve_runtime_target` (`tracker/saas_client.py`); `SUPPORTED_PROVIDERS` and the
     credential-named command (`tracker/factory.py`).
     **A line that moved is bookkeeping — fix the citation. A symbol that moved *semantically* is a
     re-plan trigger — stop and escalate.** And **if `invocation/adapters.py:81` has moved, the
     docstring literal SC-019 asserts must be updated to the new line and the change called out**,
     because SC-019 pins the string, not the concept.
  2. Create `src/specify_cli/tracker/egress_verdict.py`. **This module holds the Mission's only
     module-level import of `project_egress_refusal`.**
  3. Define `EgressDestination` as a closed **two-member** enum: `LOCAL_SUBPROCESS`, `HOSTED_SERVICE`.
     Its docstring is a deliverable and must state:
     - what each member names — `LOCAL_SUBPROCESS`: an executable named by the operator's own
       **machine-global** tracker credential file (`factory.py:56`), invoked with issue fields as
       argv, spec-kitty's SaaS not involved; `HOSTED_SERVICE`: spec-kitty's own `/api/v1/tracker/…`
       endpoints, bearer token plus `X-Team-Slug`, base URL from
       `resolve_runtime_target().resolved_server_url` (`saas_client.py:247`);
     - that **adding a member, or repointing an existing member at a new transport, requires an
       operator decision on that member's Channel-2 polarity**, naming FR-004 as where that decision
       is recorded. *No guard decides polarity for a new transport*: G5 **passes** when a new transport
       reuses `HOSTED_SERVICE`, and G4 fires only as a prompt whose obvious resolution is to edit the
       guard.
  4. Write the **module docstring** carrying, verbatim enough to satisfy SC-019:
     - **(a) the cause** — the resolver port is `Callable[[Path], bool]` at **`invocation/adapters.py:81`**
       (cite the literal string), and it discards *why* a project is refused, so the Channel-1
       classifier is the shape of a missing return type;
     - **(b) the retirement condition** — when Bundle B's **`Q3`** gives that contract a decision
       return value, the classifier **and both of its non-authoritativeness pins are `delete`d,
       `not migrate`d**, with both pins named by test name;
     - **(c) the unregistered-consumer note** — this module reaches around the registry indirection to
       `specify_cli.sync.consent` by **call-time guarded import**; a recorded exception that retires on
       the same condition;
     - **(d) the `EgressDestination` import-form rule** — imported under its own name, never aliased,
       because G5 resolves `Attribute` nodes on the name `EgressDestination`.
  5. Define the verdict value object with the fields FR-003 names: `refused`,
     `refusing_channels` (a **set**, never just the first), the Channel-1 state, the Channel-2 state
     plus its raw value, `destination` echoed back, the operator message, the ordered remedies.
     **No `binding_kind` field.**
  6. `__all__` advertises only names with a real `src/` consumer — the symbol-level dead-code gate is
     shrink-only.
- **Files**: `src/specify_cli/tracker/egress_verdict.py`.
- **Validation**: **the citation sweep recorded symbol by symbol, with a verdict per symbol
  (unchanged / line moved / moved semantically), before anything else in this subtask** — and an
  explicit statement of whether `invocation/adapters.py:81` still resolves, since a deliverable
  docstring asserts that literal string; then the module imports cleanly with **no import of
  `specify_cli.sync` at module level**; a test asserts that (import the module in a subprocess with
  `specify_cli.sync` made unimportable and assert the import still succeeds).
- **Edge cases**: `destination` is **required and keyword-only**. A default is a contract failure, not
  a convenience.

### T016 — Channel 2's resolver: the `isinstance`-guarded decode, observed red first

- **Purpose**: FR-006, NFR-003, C-001, C-020. **This is the pin `plan.md` Stage 3 names explicitly.**
- **Steps**:
  1. **Write the failing test first**: a project committing `tracker: {egress: {a: b}}` and one
     committing `tracker: {egress: [a, b]}`, for **both** destinations, asserting the function returns
     a **fault verdict**.
  2. Implement the resolver deliberately with the **bare membership test** first, run the tests, and
     **quote the red** — it will be a `TypeError: unhashable type`, **not** an `AssertionError`.
     Classify it by exception type in your notes (mutation-lie check 2: *"classify every red by
     exception type"*).
  3. Fix it to `isinstance(raw, str) and raw in _LEGAL`, re-run, quote the green.
  4. Complete the resolver's contract:
     - **absent** — the `egress` key missing, **or** a non-mapping `tracker:` block. Both defer to
       Channel 1.
     - **present `null`** — a **fault**, told apart from absence by WP02's module-local sentinel.
     - **`refused`** / **`permitted`** — the only two recorded decisions. No case-folding, no synonym
       table, no truthy coercion.
     - **anything else present** — a fault, carrying **the raw value verbatim**.
  5. Catch `TrackerConfigError` from `load_tracker_config` (`config.py:148-149`) and answer with a
     fault refusal. The function reads the project config **exactly once**.
- **Files**: `src/specify_cli/tracker/egress_verdict.py`;
  `tests/sync/tracker/test_tracker_egress_verdict_3108.py`.
- **Validation**: the mapping-at-the-key red quoted as a `TypeError`, then the green quoted.
- **Edge cases**: `tracker: "yes"`, `tracker: [a, b]`, `tracker: 3` and a null `tracker:` are **absence**,
  not faults — `load_tracker_config` passes `None` to `from_dict` in every one of these cases
  (`config.py:151-152`) and `from_dict` returns a default `cls()`. *"The natural guess is 'a malformed
  block is a fault', and it is not — the block is not the key, and the key is missing."*

### T017 — `_JOIN`: the 8-cell table as data, not branches

- **Purpose**: FR-005, SC-015, and Hazard C's complexity ceiling.
- **Steps**:
  1. Define `_JOIN: dict[tuple[str, EgressDestination], str]` at **module level** with **exactly 8**
     entries, one per (Channel-2 state × destination) cell, per the table in *Requirements* above.
     **Keys**: the Channel-2 state strings `absent` / `refused` / `permitted` / `fault` — the same
     strings the verdict's state field carries, so the field indexes the table directly.
     **Values**: the **four** named outcomes enumerated in *Requirements* — `refuse`, `permit`,
     `defer`, `defer_reported_noop` — held in **named module constants**, never as bare literals
     repeated eight times. Four values, not two: `permitted` at `HOSTED_SERVICE` enforces like
     `defer` but must be **reported** differently, and that is a requirement (FR-005, SC-014's
     checkout 6), not a nicety.
  2. Assert `len(_JOIN) == 8` **structurally** in the test file — a pin that survives a test being
     deleted.
  3. Write **one parametrised test exercising all 8 cells** that **prints and asserts the number of
     cells it ran is exactly 8** — a pin that survives an entry being wrong. **Both halves are
     required.**
  4. **Both channels are always evaluated.** Do not write a Channel-1-first short-circuit: it would
     refuse a project that Channel 2 permits at `LOCAL_SUBPROCESS`.
  5. `permitted` at `HOSTED_SERVICE` is a **no-op that must be reported as a no-op**, never silently
     dropped — the verdict carries that fact so the message and `sync doctor` can state it.
  6. When more than one channel refuses, **`refusing_channels` names all of them.**
- **Files**: `src/specify_cli/tracker/egress_verdict.py`;
  `tests/sync/tracker/test_tracker_egress_verdict_3108.py`.
- **Validation**: `len(_JOIN) == 8`; the parametrised test prints `8`.
- **Edge cases**: the join must contribute **no** cyclomatic complexity. If you find yourself writing
  `if`/`elif` over the four Channel-2 values, you are building the shape that measured `C901 17`.

### T018 — Channel 1: the resolution, and the reporting classifier that is debt

- **Purpose**: FR-012, C-004, NFR-003's no-import-time-dependency clause.
- **Steps**:
  1. **The enforced Channel-1 answer has exactly one derivation**:
     `project_egress_refusal` → `resolve_egress_consent` → `permits_egress`. Call it, and nothing else,
     for the enforced half. **`None`, and only `None`, is permission.**
  2. **The reporting classifier** is a separate helper that (1) runs **only** on a path whose refusal
     has already been decided, (2) returns a label from a **closed set of three** and can return
     nothing else, and (3) is pinned non-authoritative. Its inputs:
     `resolve_checkout_sync_routing_readonly(root).project_uuid` (present or not — the identity
     question, which `resolve_project_consent(None)` cannot answer because it reports `ABSENT` for
     both an absent record and an absent identity) and, when identity resolves,
     `resolve_project_consent(uuid, checkout_roots=[routing.repo_root]).level`.
  3. **Both imports are made at call time inside a guarded block**, degrading to the generic Channel-1
     refusal wording if they fail. There must be **no import-time dependency on `specify_cli.sync`**
     anywhere in this module. *"An `ImportError` raised out of a gate that must never raise is the
     failure mode this closes."*
  4. **The `checkout_roots=[routing.repo_root]` form is the only form specified anywhere in this
     dossier** — an earlier `repo_root=root` spelling is superseded and **must not be reintroduced**.
     Pin it with a test that invokes a checkout **from a subdirectory** and asserts the classifier's
     root and the registered resolver's root are **equal**. *"Without it the classifier can report
     'no record' for a root the enforcer resolved differently, reproducing the 'tells the operator to
     do what they just did' pathology this Mission exists partly to fix."*
  5. **The two non-authoritativeness pins** (name them, because the docstring must name them):
     - a test that **forces every one of the three labels while Channel 1 actually permits** and
       asserts the verdict still permits;
     - a test that makes the classifier **raise** and asserts the refusal still prints with **generic**
       wording.
     Patching the classifier **by name** in these pins is legitimate — FR-018 H2's prohibition is
     scoped to the acceptance tests and their named seams (`plan.md` Open Items 8).
  6. Write the **classifier's own docstring** carrying (a), (b) and (c) from T015 — cause, retirement
     condition (`Q3` → `delete`, `not migrate`, both pins named), unregistered-consumer note.
- **Files**: `src/specify_cli/tracker/egress_verdict.py`;
  `tests/sync/tracker/test_tracker_egress_verdict_3108.py`.
- **Validation**: the root-equality pin passes from a subdirectory; both non-authoritativeness pins
  pass; the module has no import-time `specify_cli.sync` dependency.
- **Edge cases**: **no new `ConsentLevel` member, no new `EgressConsent` member.** Using
  `ConsentDecision.level` **for a message** widens neither the enum nor the
  `Callable[[Path], bool]` resolver contract — *"the rejected draft's claim that this Mission 'never
  needs `ConsentDecision.level`' is amended to 'never needs it **for the verdict**'."*

### T019 — Message and remedy composition, byte-exact where it must be

- **Purpose**: FR-012, C-020, SC-010's wording half, SC-016's `root=None` clause.
- **Steps**:
  1. **One message-composition helper.** No path-local message strings anywhere; the raise sites in
     WP04 and WP05 use `verdict.message` and never re-compose. Write the pin that asserts this at the
     unit level (the message equals the composition helper's output for the same verdict).
  2. Compose per Channel-1 state (the three above) and per destination:
     - at `LOCAL_SUBPROCESS`, every state also offers the **Channel-2 grant** as a remedy;
     - at `HOSTED_SERVICE`, the message explicitly says the grant **does not apply there**, so *"the
       operator is not left believing the key did nothing"*.
  3. **The fault message** (C-020) must **name the offending value verbatim** and **name both legal
     values `refused` and `permitted`**, so the operator fixes a typo without guessing and without
     reading source. Pin it for **every** near-miss in the probed set of 15.
  4. **`root=None` — specified in full here, because it is a named exception to two of this WP's own
     rules and it is reachable at BOTH destinations.**

     **First, correct the reachability claim.** Earlier drafts say `root=None` is *"reachable only
     from `SaaSTrackerClient._request`"*. **Do not write that sentence and do not rely on it.** It is
     true today and **false the moment WP06 lands**: the doctor renderer resolves its root with
     `locate_project_root(Path.cwd())` — the same call its sibling `_render_consent_readability`
     makes at `sync.py:1786` — and that returns **`None` outside a checkout**, after which the
     renderer passes `root=None` to **both** of its calls, including the `LOCAL_SUBPROCESS` one.

     **So specify both cells:**

     | Destination | `root=None` answer |
     |---|---|
     | `HOSTED_SERVICE` | **refuses**, with text **byte-identical to `UNDETERMINED_PROJECT_REFUSAL`**. This is the shipped `#3030` behaviour and WP05's byte-comparison depends on it. |
     | `LOCAL_SUBPROCESS` | **refuses**, with the **same** text. The project that owns the data could not be determined; an undetermined project is never a consenting one, and the polarity of Channel 2 is irrelevant because there is no file to read a key out of. Pin these bytes too, so WP06's `LOCAL_SUBPROCESS` row outside a checkout has a defined thing to render. |

     **Second — `root=None`'s message is a NAMED EXCEPTION to the composition rule in step 2.**
     Every other message this module produces names the Channel-1 state and carries **ordered
     remedies**. `UNDETERMINED_PROJECT_REFUSAL` is three lines and carries **no remedies at all**:

     ```
     the project that owns this data could not be determined, so its consent to
     hosted sync could not be resolved; refusing to transmit (an undetermined
     project is never a consenting one)
     ```

     **Byte-identity with that string and the compose-a-remedy-list rule are mutually exclusive, and
     byte-identity wins** — SC-016 requires it and WP05's four-row comparison measures it. Write the
     exception into the message helper explicitly (a guarded early return, named, with a comment
     saying *why* it does not compose) rather than letting it fall out of the general path by
     accident. An exception that is visible is a decision; an exception that emerges is a bug
     someone will "fix".

     **Third — its Channel-1 label.** It is **not** one of the classifier's three. The classifier
     answers *no record / recorded refusal / not consentable* for a root that **exists**; `root=None`
     is the case where there is no root to classify, and `not consentable`'s remedy — `spec-kitty
     init` — is actively wrong advice for it. Give the verdict's Channel-1 state field an explicit
     fourth value, spelled **`undetermined`**, set on this path **without calling the classifier at
     all**. Then keep C-004's *"closed set of three"* pin honest by scoping it to what it actually
     covers: **the classifier returns one of exactly three labels; the verdict's Channel-1 state
     field carries those three plus `undetermined`, and `undetermined` is reachable only when
     `root is None`.** Pin both halves.
  5. Hoist repeated non-trivial literals (the two legal values, the key path, the message fragments)
     to named module constants once they appear ≥ 3 times (Sonar `S1192`).
- **Files**: `src/specify_cli/tracker/egress_verdict.py`;
  `tests/sync/tracker/test_tracker_egress_verdict_3108.py`.
- **Validation**: the `root=None` text compared **byte-for-byte** against the current
  `UNDETERMINED_PROJECT_REFUSAL`; the fault message pinned for all near-misses.
- **Edge cases**: the Channel-1 **reporting triple** (*no record / recorded refusal / not consentable*)
  and the Channel-2 **value** vocabulary (*absent / refused / permitted / fault*) are two different
  vocabularies. **Name which one you mean, every time both appear.** Neither substitutes for the other.

### T020 — The never-raises contract, and the quality gates

- **Purpose**: NFR-003, NFR-005 — and Stage 3's exit criterion.
- **Steps**:
  1. Write the parametrised never-raises test over NFR-003's **twelve** enumerated shapes × **two**
     destinations = **24 cases**, and have it **print and assert that it ran 24**. The twelve shapes,
     enumerated in `spec.md` NFR-003 and nowhere re-enumerated: unreadable; unparseable; wrong-shape;
     `tracker:` non-mapping; **a mapping at the `egress` key**; **a list at the `egress` key**; empty
     file; comments-only; `chmod 000`; absent file; `root=None`; a `repo_root` that is not a project
     root.
     *"The probed set is deliberately stated at two levels: file-level shapes **and** value-level
     shapes at the key, because the measured `TypeError: unhashable type` came from the latter and the
     earlier probed set listed only the former."*
  2. Assert the function **never propagates** `TrackerConfigError` or any other exception, for all 24.
  3. Run the quality gates and quote them:
     - `ruff check` clean with **no `# noqa: C901`** on the new module. If C901 fires, the
       decomposition is wrong — extract, do not suppress.
     - `mypy --strict` clean, no `# type: ignore` added. **A `mypy` error on a `destination` argument
       is a contract failure, not a lint failure** — it is the mechanism by which FR-004's polarity
       becomes type-checked.
     - ≥90 % coverage on the new branches, from **focused tests executing the new helpers directly**
       rather than from any acceptance suite.
  4. Confirm this WP's **zero blast radius**: `tests/sync/tracker/ tests/agent/cli/commands/test_tracker.py`
     unchanged at its Stage-0 number.
- **Files**: `tests/sync/tracker/test_tracker_egress_verdict_3108.py`.
- **Validation**: the never-raises test prints `24`; `len(_JOIN) == 8`; the 8-cell test prints `8`;
  `ruff check` and `mypy --strict` quoted clean; the tracker baseline quoted unchanged.
- **Edge cases**: *"Once the function is behind a gate, an exception in it surfaces as a CLI traceback
  in an acceptance test, and distinguishing 'the verdict raised' from 'the gate is misplaced' costs a
  bisect."* Prove NFR-003 **here**, where the function has no callers.

---

## Test Strategy

- **New**: `tests/sync/tracker/test_tracker_egress_verdict_3108.py` — the 8-cell table, the 24-case
  never-raises contract, the classifier's root-equality and non-authoritativeness pins, the
  fault-message pins, the `root=None` byte-identity pin, the message-not-re-composed pin.
- **Run**:
  - `pytest tests/sync/tracker/test_tracker_egress_verdict_3108.py` — unpiped, `N passed` quoted.
  - `pytest tests/sync/tracker/ tests/agent/cli/commands/test_tracker.py` — unchanged from Stage 0.
- `ruff check` and `mypy --strict` clean on both owned files.

## Definition of Done

- `tracker_egress_verdict(root: Path | None, *, destination: EgressDestination)` exists, with
  `destination` **required and keyword-only** and **no `binding_kind` field**.
- `len(_JOIN) == 8` structurally, **and** the parametrised table test prints and asserts `8`.
- The never-raises test prints and asserts `24`; nothing propagates out of the function.
- The mapping-at-the-key case **observed red as a `TypeError`, then green as a fault verdict** — both
  quoted.
- The module docstring and the classifier's docstring contain the literal strings
  `invocation/adapters.py:81`, `Q3`, `delete` and `not migrate`, plus the import-form rule.
- The classifier is pinned **non-authoritative** by both named tests, and its root is pinned equal to
  the registered resolver's root **from a subdirectory**.
- `root=None` produces text **byte-identical** to `UNDETERMINED_PROJECT_REFUSAL` **at BOTH
  destinations** — the `LOCAL_SUBPROCESS` cell is reachable and is pinned, because WP06's renderer
  passes `root=None` at both when run outside a checkout. Its message is a **named, commented
  exception** to the compose-remedies rule, and its Channel-1 state field is the explicit fourth
  value `undetermined`, set **without calling the classifier**.
- `_JOIN`'s **value** vocabulary is the four named outcomes — `refuse`, `permit`, `defer`,
  `defer_reported_noop` — held in named module constants, with `defer` and `defer_reported_noop`
  distinct even though their enforced answers are identical.
- The Channel-2 **state** vocabulary is spelled `absent` / `refused` / `permitted` / `fault`
  everywhere, and the state field's value is what indexes `_JOIN`'s first key element.
- The citation sweep is recorded **symbol by symbol** before anything else in T015, with an explicit
  verdict on `invocation/adapters.py:81`.
- `ruff check` clean with **no `# noqa: C901`**; `mypy --strict` clean; ≥90 % coverage on new branches.
- **Zero call sites created.** G4 and G5 do not land here.
- No file outside the two owned files is modified.

## Risks & Mitigations

- **The function raises out of a gate** → NFR-003's 24 cases, proven here where there is no gate.
- **`C901 17 > 15`** → the decomposition in *Hazard C* is a requirement, not a suggestion. Extract; do
  not suppress.
- **The classifier becomes authoritative by accident** → the two pins force its labels while Channel 1
  permits, and force it to raise.
- **The debt is lost when Bundle B lands** → it is carried **in source**, in two docstrings, pinned by
  the literal-string assertions of SC-019.
- **A future body reads the provider** → guard G6 (WP07) forbids it; do not give it anything to find.

## Review Guidance

- Verify the decode is `isinstance(raw, str) and raw in _LEGAL`, in that order.
- Verify `_JOIN` is module-level **data** with exactly 8 entries, and that the join is not a branch
  chain.
- Verify there is **no module-level import of `specify_cli.sync`** anywhere in the module.
- Verify the module docstring and the classifier docstring carry all four required elements and the
  exact literal strings.
- Verify **no** `_require_egress`-style helper was introduced, and **no** call sites were created.
- Verify no provider read, no `LOCAL_PROVIDERS`/`SAAS_PROVIDERS` reference, and no `.provider`
  attribute access on a `load_tracker_config` result exists in the module.

## Activity Log

- 2026-08-01T00:20:00Z – system – Prompt created.
