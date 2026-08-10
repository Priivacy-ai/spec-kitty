---
work_package_id: WP02
title: Channel-2 key shape and preservation at the erasure sites (Stage 2 root)
dependencies: []
requirement_refs:
- C-001
- C-011
- C-012
- C-019
- C-020
- FR-002
- FR-006
- FR-009
- FR-010
- FR-011
- NFR-005
planning_base_branch: bundle-c-tracker-refusal-3108
merge_target_branch: bundle-c-tracker-refusal-3108
branch_strategy: Planning artifacts for this mission were generated on bundle-c-tracker-refusal-3108. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into bundle-c-tracker-refusal-3108 unless the human explicitly redirects the landing branch.
created_at: '2026-08-01T00:20:00+00:00'
subtasks:
- T008
- T009
- T010
- T011
- T012
- T013
- T014
phase: Stage 2 - Channel 2's data layer and preservation, before the gate
history:
- at: '2026-08-01T00:20:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks-packages
agent_profile: python-pedro
authoritative_surface: src/specify_cli/tracker/config.py
create_intent:
- tests/sync/tracker/test_tracker_egress_config_3108.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/tracker/config.py
- src/specify_cli/tracker/service.py
- src/specify_cli/tracker/saas_service.py
- tests/sync/tracker/test_tracker_egress_config_3108.py
role: implementer
tags: []
task_type: implement
tracker_refs:
- '3108'
---

# Work Package Prompt: WP02 – Channel-2 key shape and preservation at the erasure sites

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter and behave per its
guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`

---

## Objective

Make `tracker.egress` a **first-class known field** of `TrackerProjectConfig` whose recorded value
cannot be silently replaced by a default, whose absence stays spelled as **the key being missing**,
and which **survives `bind`, rebind and `unbind`** at every construction site in this WP's files that
reaches disk.

**Done** = `egress` is in `_KNOWN_KEYS` carrying the **raw loaded value plus a derived fault**; a
`bind` into a project with no tracker key writes **no `egress` key at all**; every value in the
probed set of **exactly 15** round-trips **byte-identically**; and the preservation sites A3, B1, B2,
C and D each carry a recorded decision forward **on disk**, pinned in **both** directions with the
sibling `sync:` block asserted present as the control — while **A2 and A4 are class A′**:
defence-in-depth, asserted at the **unit level** against the constructed object, with **no red-first
pin and no exit criterion** for either.

---

## Boundaries — what this WP may touch

**Owned files — the only files you may create or edit:**

- `src/specify_cli/tracker/config.py`
- `src/specify_cli/tracker/service.py`
- `src/specify_cli/tracker/saas_service.py`
- `tests/sync/tracker/test_tracker_egress_config_3108.py` (new)

**Hard boundary.** You may not edit files another WP owns. In particular:

- **`src/specify_cli/tracker/local_service.py` is WP04's.** Preservation site **A1**
  (`LocalTrackerService.bind`, construction at `local_service.py:57`) is therefore **not yours** — it
  lands in WP04. Your class-A work is A2 (`service.py:163`), A3 (`saas_service.py:266`) and A4
  (`service.py:98`).
- `src/specify_cli/tracker/egress_verdict.py` is WP03's. You do **not** write the verdict function,
  the `EgressDestination` enum, or any message text. Your fault work stops at the **data layer**: the
  field carries a raw value and a derived fault flag; the *wording* of the fault message is WP03's.
- `src/specify_cli/tracker/saas_client.py` (WP05), `src/specify_cli/cli/commands/sync.py` (WP06),
  `tests/sync/tracker/test_tracker_egress_refusal_3108.py` (WP01),
  `tests/architectural/test_tracker_egress_guards_3108.py` (WP07) are all out of bounds.

**Detection signals — files you must NOT edit, whose greenness is your evidence:**

- `tests/specify_cli/tracker/test_binding_report_only.py:254-268` holds
  `test_apply_binding_upgrade_preserves_extra_fields`, asserting
  `svc._config._extra == {"future_flag": True}` — *the forward-compat `_extra` contract at
  `saas_service.py:219`, the exact line B1 modifies*. **It is a detection signal, not a planned
  edit**: `_extra` must keep carrying `future_flag` after `egress` stops riding in it. **If it reds,
  the B1 fix replaced the `_extra` carry instead of adding an `egress` carry beside it — do not
  "repair" it by weakening the assertion.**
- `tests/specify_cli/sync/test_worktree_clean_invariant.py:22` documents the
  `apply_binding_upgrade` / `bind` write boundary. Untouched.

**Dependencies: none.** This is the Mission's **second independent root** (`plan.md` Sequencing,
Stage 2). You may assume nothing about the verdict function, the gate, or the acceptance harness.

**Preconditions that are not dependencies but are still binding before your first landing subtask
(T009):**

- **The four follow-up issues must already exist, with URLs.** IC-10 states it without qualification:
  *"the issues are filed **before implementation starts**. Not 'at any point', not 'at the end'."*
  They are filed in **WP01 T001**, and WP01 is a **co-equal root** with no edge to you — so nothing
  in the dependency graph enforces this and you must check it yourself. **Before T009 lands, confirm
  the four issue URLs exist** (Chain B, `sync_publish`'s `AttributeError`, `_extra`'s unaudited
  consumers, the `finalize-tasks` scraping gap). If they do not, **stop and report** — do not file
  them yourself (WP01 owns their framing, and the Chain B framing is load-bearing) and do not proceed
  past T008.
- **You own your own Stage-0 numbers.** The suite baselines this WP's Definition of Done cites are
  measured in **WP01 T001**, which you have no edge to. T008 therefore re-measures the two you
  actually need, yourself. Do **not** resolve this by adding a WP01 dependency: that would collapse
  the Mission's two independent roots into a chain and destroy the parallelism the board is built on.

---

## Requirements this WP satisfies

### FR-002 — A tracker-scoped key, named and shaped as a tri-state, carrying its raw value

> *"I want to decide tracker egress for one project by recording **`egress` in the `tracker:` block of
> that project's own `.kittify/config.yaml`**, holding one of a **closed set of two strings, `refused`
> or `permitted`**, with **absence spelled as the key being missing**. […] On `TrackerProjectConfig`
> the field holds the **raw loaded value plus a derived fault**, never a narrowed type such as an
> enum-or-`None` or `bool | None`: measured on the `doctrine.mode` precedent, a known field with an
> unusable value is silently replaced by its default on round trip, which would convert a refusing
> project into a permitting one at the next `bind`. The field is added to `_KNOWN_KEYS`
> (`config.py:69-72`) so it is not reachable only through the untyped `_extra` passthrough whose
> consumers have never been audited (C-019). Absence is distinguished from a present `null` by a
> **module-local sentinel** (C-001)."*

### FR-006 — Absence and unusability, stated per channel

> *"**Channel 2: absence — the key missing — records nothing** and defers to Channel 1. A
> **non-mapping `tracker:` block is also absence**, not a fault (`config.py:151-152` passes `None`;
> `from_dict` returns `cls()`). **Channel 2 present and outside the closed set refuses at both
> destinations**: the decode is an exact match against exactly two strings, `refused` and `permitted`,
> and **every other present value is a fault, and a fault refuses and never grants**. No case-folding,
> no `yes`/`on`/`1`/`true`, no synonym or truthy table, no coercion of non-strings. **The decode is
> `isinstance`-guarded before the membership test — `isinstance(raw, str) and raw in _LEGAL`, never
> `raw in _LEGAL` alone.**"*

### FR-009 — A write must never plant a decision

> *"I want `save_tracker_config` to **omit** `egress` from the emitted `tracker:` block when no
> decision is recorded, rather than emitting a null the way `to_dict` emits every other unset known
> field (`config.py:53-67`). Without this, `spec-kitty tracker bind` — the command that creates a
> working binding — writes `egress:` with a null, which FR-006 reads as a fault, which refuses. **The
> binding command would disable the binding.**"*

### FR-010 — Every probed value round-trips byte-identically

> *"…for **every** value in the probed set — the two legal values `refused` and `permitted`; the
> quoted forms `"refused"` and `'permitted'`; the near-miss strings `Refused`, `REFUSED`, `refuse`,
> `deny`; the wrong types `true`, `false`, `0`, `null`, a mapping, a list; and the empty string — not
> merely for the one that surfaced first."*
>
> *"If achieving byte-identity requires `load_tracker_config` to set `preserve_quotes = True` —
> matching what `save_tracker_config` already does at `config.py:160` — that change is in scope. […]
> **Also in scope, and separately measured:** `clear_tracker_config` (`config.py:178-194`) constructs
> a **third** `YAML()` at `config.py:184` with **no** `preserve_quotes` and dumps straight to the file
> handle, so today `unbind` destroys quoting in **sibling blocks**."*
>
> *"**Scope decision: byte-identity is required of the `egress:` line only.**"* The pin asserts the
> `egress:` line byte-for-byte and asserts the rest of the file differs only in lines the operation is
> supposed to touch — *"because a whole-file assertion would make every unrelated ruamel formatting
> difference a failure of this Mission."*

### FR-011 — A recorded tracker-egress decision outlives its binding

The inventory is **re-derived from `grep -n "TrackerProjectConfig(" src/`**, not recalled. Nine
construction sites; seven reach disk. Your share:

| # | Site | Class | Today | Required |
|---|---|---|---|---|
| A2 | `TrackerService.bind`, local branch (`service.py:163`) | **A′ — defence-in-depth. NO end-to-end pin, NO red-first pin, and no exit criterion inside this WP.** | `LocalTrackerService(self._repo_root, TrackerProjectConfig())` — hands the constructor an **empty** config, unlike the SaaS branch above it (`:142-145`) which passes `load_tracker_config(self._repo_root)`. *"The argument is a lie about what is on disk."* | Hand `bind` the **loaded** config, matching the SaaS branch. **Assert at the unit level against the object handed to the constructor.** |
| A3 | `SaaSTrackerService.bind` (`saas_service.py:266`) | **erases today — measured** | Builds a bare `TrackerProjectConfig(provider=…, project_slug=…)` carrying **nothing** forward, then saves. **Missed by every previous revision**, and it is the site where Channel 2 is the *only* narrowing conjunct. | Carry `egress` (and `_extra`) forward from the loaded config. |
| A4 | `TrackerService._resolve_saas_backend_for_provider` (`service.py:98`) | **defence-in-depth — NO production write path, NO red-first pin** | Substitutes a fresh `TrackerProjectConfig(provider=provider)` which becomes `self._config` and *would* feed an empty `_extra` into `_persist_binding`. | Carry the loaded config's `egress` (and `_extra`) into the substituted object, or make a substituted config non-persistable. **Assert at the unit level against the substituted object. Do not write a red-first pin: there is no production path to red it.** |
| B1 | `saas_service.py:206-219` — construction at `:206`, `_extra=` carry at `:219` | **works today; your own promotion breaks it** | Preserves a committed `egress` **only because it currently rides in `_extra`**. | Gain an **explicit `egress=` carry beside** the `_extra` carry. |
| B2 | `saas_service.py:303-316` — construction at `:303`, carry at `:316` (`_persist_binding`) | same | same, via `_extra=dict(self._config._extra)`. | same. |
| C | `clear_tracker_config` (`config.py:178-194`) | **erases today** | Unconditional `del payload["tracker"]` at `:191`; also builds a third `YAML()` at `:184` with no `preserve_quotes`. | Retain a `tracker:` block holding **only** a recorded `egress` when one exists; delete the block entirely when none is recorded; set `preserve_quotes`. |
| D | `SaaSTrackerService.unbind` (`saas_service.py:281`) | **library-caller reachable only** | Resets `self._config = TrackerProjectConfig()` **in memory** after `clear_tracker_config`; a subsequent `_persist_binding` on the same instance would write a config with no `egress` — **erasing exactly what site C was just fixed to preserve**. | Reset to `load_tracker_config(self._repo_root)`. |

Not in scope, checked and stated so the next reader does not re-derive the negative: `origin.py:536`
and `config.py:142` construct configs that **never reach `save_tracker_config`**.

> **Why A2 is class A′ and not class A — measured, and it changes what you may promise.**
> `LocalTrackerService.bind` (`local_service.py:47-63`) **never reads `self._config`.** It builds a
> **fresh** `TrackerProjectConfig` from its keyword arguments at `:57` and hands that to
> `save_tracker_config` at `:63`. So handing `TrackerService.bind`'s local branch a **loaded** config
> at `service.py:163` **changes nothing on disk** — the loaded object is dropped on the floor one
> frame later. An end-to-end pin written against A2 in this WP would be **red before your fix and
> red after it**, and the only ways to make it green are to edit `local_service.py` (WP04's file) or
> to weaken the pin.
>
> The behaviour A2 is *supposed* to protect only becomes observable when site **A1**
> (`local_service.py:57`) lands, and **A1 is WP04's, in T024.** `plan.md`'s Red-First table already
> records the honest position: the FR-011 preservation reds were *"measured independently at three of
> them: **A1, A3, C**"* — **A2 is not among them.**
>
> Therefore: **A2 is fixed here as defence-in-depth, asserted at the unit level against the object
> handed to the `LocalTrackerService` constructor, with no red-first pin and no exit criterion.**
> The end-to-end `TrackerService.bind` preservation pin — commit a decision, run
> `TrackerService.bind` on a local provider, assert the decision survived on disk with the sibling
> `sync:` block as the control — **lives in WP04 T024**, where A1 makes it real. Do not write it
> here, and do not claim it.
>
> **The window this split creates, named rather than left implicit (C-006-style precondition).**
> The spec makes a cross-site guard the condition of splitting FR-011's construction sites across
> change sets: *"the split requires a guard asserting that every `TrackerProjectConfig(`
> construction whose value flows into `save_tracker_config` carries `egress`."* That guard is **not**
> written for the A1-vs-A2/A3 split, and the reason it is accepted anyway is that **WP02 and WP04
> land on one branch** (`bundle-c-tracker-refusal-3108`) and are never released separately.
> **The window is: from WP02 landing until WP04's T024 lands, `LocalTrackerService.bind` still
> erases a committed `egress`.** Nothing ships in that window; nothing else may be built on the
> assumption that it is closed. WP04 carries the same paragraph, so both ends of the window know
> about it.

**Recorded semantics: a recorded tracker-egress decision outlives its binding.** Symmetric across the
tri-state. *"Deleting a `refused` is a **silent fail-open**; deleting a `permitted` silently
withdraws a working local binding."* **Erasure must not be confusable with absence.**

### NFR-005, C-001, C-012, C-019, C-020

- **NFR-005** — `ruff check` and `mypy --strict` clean on new code, no blanket suppressions,
  ≥90 % coverage on new branches from focused tests executing the new helpers directly.
- **C-001** — the key lives in the `tracker:` block, carries its raw value, and uses a
  **module-local sentinel** *"with the same semantics as `sync/consent.py:145`'s `_MISSING` and the
  reasoning cited rather than the private object imported — importing it would give `tracker/` an
  import-time dependency on `sync.consent` and risk an `ImportError` out of a gate NFR-003 says never
  raises."*
- **C-020** — *"a typo fails closed"*: `tracker: {egress: refuse}` (singular), `Refused`, `deny`, a
  stray `true` are each a **fault, and a fault refuses**. Intended, not a side effect.
- **C-012 (4) and (5)** — `saas_service.py:219` and `:316` are blast radius that *"looks like a
  reference pattern"*; and `tests/specify_cli/` entered the blast radius with `saas_service.py`.
- **C-019 (3)** — whether any consumer reads `TrackerProjectConfig._extra` was not checked. *"C-001's
  known-field placement is the mitigation, not the answer."*

### Success criteria owned here

SC-008, SC-009, SC-010 (the data-layer half — the fault **classification** for all 15 probed values;
the fault **wording** is WP03's).

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

**Hazard A — a known field with an unusable value is silently replaced by its default on round trip.**
Measured on `doctrine.mode` (`tracker/config.py:39`, default `"external_authoritative"`): a committed
`doctrine.mode: 42` came back on read as `'external_authoritative'`, not as an error and not as the
recorded `42`. Applied to `egress`, **a narrowed type would let `spec-kitty tracker bind` silently
replace a recorded `refused` with the type's default on the next round trip — converting a refusing
project into a permitting one.** The field therefore carries the **raw value plus a fault**, not a
narrowed type.

**Hazard B — the decode must be `isinstance`-guarded.**

```python
_LEGAL = frozenset({"refused", "permitted"})

value = raw if (isinstance(raw, str) and raw in _LEGAL) else FAULT   # correct
value = raw if raw in _LEGAL else FAULT                             # raises
```

The second form raises `TypeError: unhashable type: 'CommentedMap'` for a mapping and
`TypeError: unhashable type: 'CommentedSeq'` for a list — **both of which the spec enumerates as
fault values**, and both trivially authorable in YAML (`tracker: {egress: {a: b}}`,
`tracker: {egress: [a, b]}`) — inside a function that must never raise. The `isinstance` guard comes
**first**.

**Hazard C — nine `TrackerProjectConfig(` construction sites, seven reaching disk.** Class A erases
today; **Class B works today only because the key rides in `_extra`, and the field-shape change breaks
it**; C is `clear_tracker_config`; D is library-caller reachable. `saas_service.py:266` was **measured
erasing**:

```
BEFORE: tracker: provider: linear / project_slug: p / egress: refused
AFTER  SaaSTrackerService.bind:            egress present? False    <-- erases TODAY
CONTROL (_extra-carrying pattern):         egress present? True
```

**A recorded tracker-egress decision outlives its binding.**

> **The trap this exists to disarm:** B1 and B2 were cited by a previous revision as *"the pattern to
> copy"*. They are the two lines this Mission's own field-shape change **breaks**. Copying them
> without fixing them yields a Mission that preserves the key at the site it added and loses it at
> the two sites it held up as correct.

**Hazard D — promoting the field manufactures the FR-009 defect.** On the base, `egress` is an unknown
key handled by `_extra`, so a "bind plants no null" pin is **vacuously green**. Promoting it to
`_KNOWN_KEYS` is what creates the defect, because `to_dict` (`config.py:53-67`) emits every known
field unconditionally, including `None`s. **That red must be deliberately produced and observed on the
FR-002-only tree** — skipping it means FR-009 ships untested.

**Hazard E — the FR-002-only tree is a required measurement point, not a commit boundary.** On that
same tree, **B1's and B2's preservation pins are also red**. *"Build it, observe and quote all three
reds, then close them."* The landing rule is unchanged: the field-shape change and the preservation
work **land as one commit**.

**Hazard F — `preserve_quotes` blast radius, measured rather than guessed.** `from_dict`
`str()`-coerces **every** known string field (`provider`, `binding_ref`, `project_slug`,
`display_label`, `workspace`, `provider_context` values, `doctrine.mode`, `field_owners`), so the
ruamel scalar-string subclass survives on **only** `_extra` values and the raw `egress` value — not on
"every string loaded from `tracker:`". Confirm this rather than assuming either bound.

---

## Subtasks & Detailed Guidance

### T008 — Revalidate the inventory before you trust a line number

- **Purpose**: C-011. Roughly forty citations in this dossier are pinned to `bb2020fea` and
  implementation is deferred to a later base. **Four drifts were already found at `bb2020fea` itself**
  (`config.py:160` not `:165`; `config.py:39` not `:38`; `sync.py:5737` not `:5736`;
  `saas_service.py:219,316` not `:220,317`) — which is the evidence that this step is necessary
  rather than ceremonial.
- **Steps**:
  1. Record the base SHA. Run `git diff --stat bb2020fea..<base>` over `src/specify_cli/tracker/`.
  2. **Re-derive the inventory yourself**: `grep -n "TrackerProjectConfig(" src/`. Confirm **nine**
     sites, and confirm the classification of each against the table above (A2, A3, A4, B1, B2, C, D
     reach disk in your files; A1 is WP04's; `origin.py:536` and `config.py:142` never reach
     `save_tracker_config`).
  3. Re-derive by symbol name, never line number: `_KNOWN_KEYS`, `from_dict`, `to_dict`,
     `load_tracker_config`, `save_tracker_config`, `clear_tracker_config`,
     `TrackerService.bind`, `TrackerService._resolve_saas_backend_for_provider`,
     `SaaSTrackerService.bind`, `SaaSTrackerService.unbind`, `apply_binding_upgrade`,
     `_persist_binding`.
  4. Confirm the `_extra` exclusion mechanism at `config.py:107` (`from_dict` excludes `_KNOWN_KEYS`
     from `_extra`) — it is the mechanism your promotion destroys.
  5. **Confirm the four follow-up issue URLs exist** (see *Preconditions* above). If they do not,
     stop here and report. Do not file them yourself.
  6. **Measure your own Stage-0 numbers, here, before you change anything.** This WP's Definition of
     Done cites two suite baselines, and they are measured in **WP01 T001**, which is a co-equal root
     with **no edge to you** — so you cannot inherit them and you must not quote a number from
     someone else's PR body. Run each **unpiped, exit status trusted**, in a worktree pinned to your
     base with `PYTHONPATH=$WT/src`, and **quote the `N passed` line**:

     | Suite | Value at `bb2020fea`, for orientation only | Prediction at your base |
     |---|---|---|
     | `pytest tests/sync/tracker/ tests/agent/cli/commands/test_tracker.py` | `519 passed, 1 warning in 64.73s` | **unchanged** by anything before you; any movement is a stop-and-attribute event, attributable to the base, not to you |
     | `pytest tests/specify_cli/` | `35 passed in 54.65s`, exit 0 | **unchanged** — this is the suite holding `test_apply_binding_upgrade_preserves_extra_fields`, your detection signal |

     **These two numbers, measured by you at your base, are the ones your Definition of Done means.**
     Recording them here is what makes "still at its Stage-0 number" a checkable claim rather than a
     reference to a measurement you never saw. **Do not add a dependency on WP01 to obtain them** —
     that would collapse the Mission's two independent roots into a chain.
- **Files**: none (read-only).
- **Validation**: a symbol-by-symbol verdict recorded in the PR body; the grep output quoted with its
  count; the four issue URLs; **two `N passed` lines measured at your own base and quoted**.
- **Edge cases**: **a symbol that moved *semantically* — a changed signature, a relocated write, a
  changed default — is a re-plan trigger**, not something to patch in passing. Stop and escalate.

### T009 — The field shape: raw value plus derived fault, in `_KNOWN_KEYS`

- **Purpose**: FR-002, C-001. This is the change that makes everything else in this WP necessary.
- **Steps**:
  1. Define the **module-local absence sentinel** in `tracker/` (do **not** import
     `sync/consent.py:145`'s `_MISSING`; cite its reasoning in a comment instead). It distinguishes
     *"key missing"* from *"key holds `null`"*, which `dict.get` otherwise collapses.

     **This sentinel is a cross-WP contract, so it is named here rather than left to taste.**
     WP03's Channel-2 resolver must tell absence from a present `null`, and WP03 owns **only**
     `egress_verdict.py` — so it cannot fix a name it cannot import.

     - **Name:** `EGRESS_ABSENT`.
     - **Home:** `src/specify_cli/tracker/config.py`, beside the field it describes.
     - **Public, no leading underscore** — WP03 imports it across module boundaries, and a
       leading-underscore name would make that import a lint finding WP03 has no way to resolve
       inside its own file.
     - `tracker/config.py` currently declares **no `__all__`**. If you add one to advertise
       `EGRESS_ABSENT`, it must also enumerate the module's **existing** public names
       (`TrackerProjectConfig`, `load_tracker_config`, `save_tracker_config`,
       `clear_tracker_config`, and anything else `src/` imports from here) — a partial `__all__`
       silently *narrows* the module's public surface and will break importers. Adding no `__all__`
       at all is acceptable; adding a partial one is not.
     - **Do not rename it later.** WP03's "you may assume" list names this exact symbol and this
       exact module.
  2. Add `egress` to `TrackerProjectConfig._KNOWN_KEYS` (`config.py:69-72`).
  3. Add the field to the `@dataclass(slots=True)` carrying **the raw loaded value plus a derived
     fault flag** — never `enum | None`, never `bool | None`. Three states must remain distinguishable
     all the way through a `bind`/`unbind` round trip: **absent**, **a legal value**, **unusable**.
  4. Implement the decode as `isinstance(raw, str) and raw in _LEGAL` where
     `_LEGAL = frozenset({"refused", "permitted"})`. **The `isinstance` guard comes first.** No
     case-folding, no synonym table, no truthy coercion.
  5. `from_dict`: a **non-mapping `tracker:` block** is **absence, not a fault** — `config.py:151-152`
     passes `None` and `from_dict` returns a default `cls()`. Stated because *"the natural guess is
     the opposite: the block is not the key, and the key is missing."*
  6. Hoist repeated non-trivial literals (the two legal values, the key path) to named module
     constants once they appear ≥ 3 times (Sonar `S1192`).
- **Files**: `src/specify_cli/tracker/config.py`;
  `tests/sync/tracker/test_tracker_egress_config_3108.py`.
- **Validation**: unit pins over all 15 probed values asserting the field's `(raw, fault)` pair; a
  pin that a mapping and a list at the key produce a fault **without raising**; a pin that a
  non-mapping `tracker:` block produces **absence**, distinct from a present `null` which produces a
  **fault**.
- **Edge cases**: `tracker: {egress: }` (a present null) is a **fault**; a missing `egress:` is
  **absence**. Those two must not share a representation.

### T010 — The write side must never plant a decision (observe the red first)

- **Purpose**: FR-009, SC-008 first clause. **The red for this does not exist on the base — you
  manufacture it in T009.**
- **Steps**:
  1. On the **FR-002-only tree** (T009 applied, T010's fix not yet applied), write and run the pin:
     `spec-kitty tracker bind` into a project with **no** tracker key renders a `tracker:` block
     containing **no `egress` key at all**. Observe it **red** and **quote the failure text.**

     **Do not pre-classify this red.** The shape it takes depends on a decision *you* make in T009,
     and both shapes are legitimate:

     - If the unset value is a plain `None`, `to_dict` emits it, ruamel renders `egress:` with a
       null, and the red is an **`AssertionError`** on the rendered block.
     - **If the unset value is the `EGRESS_ABSENT` module-local sentinel** — which is exactly what
       C-001 asks for — then `to_dict` hands ruamel an object it has **no representer for**, and the
       red is a **`RepresenterError` raised out of `save_tracker_config`**, with no rendered `null`
       to assert on at all.

     **Observe and quote whatever the red actually is, then classify it** against the exception type
     you saw. A red pre-classified as an `AssertionError` that arrives as a `RepresenterError` is
     exactly the mismatch an implementer explains away — *"close enough, it failed"* — and the
     explaining-away is what loses the measurement. What you must rule out is a red caused by a
     **changed signature** (a `TypeError` at the call), which would mean the pin never reached the
     behaviour it is about. Say in the PR body which of the three you got.
  2. Then fix `to_dict` to **omit** `egress` entirely when nothing is recorded, rather than emitting a
     written-out null the way it emits every other unset known field.
  3. Re-run; green.
- **Files**: `src/specify_cli/tracker/config.py`;
  `tests/sync/tracker/test_tracker_egress_config_3108.py`.
- **Validation**: the red quoted, then the green quoted. **Both.** An implementer who lands the field
  shape and this fix in one motion without observing the red ships FR-009 untested.
- **Edge cases**: absence must stay spelled as **the key being missing**. A written-out null would put
  absence back into the value slot the tri-state moved it out of.

### T011 — Byte-identical round trip over the probed set of exactly 15

- **Purpose**: FR-010, SC-008 second clause.
- **Steps**:
  1. Parametrise over the probed set — **exactly 15**, enumerated once in `spec.md` FR-010 and nowhere
     re-enumerated: `refused`, `permitted`, `"refused"`, `'permitted'`, `Refused`, `REFUSED`,
     `refuse`, `deny`, `true`, `false`, `0`, `null`, empty string, mapping, list. **The parametrised
     test prints and asserts its own case count is 15.**
  2. For each: write the value into a project's `.kittify/config.yaml`, run a `bind`, and assert the
     `egress:` line is **byte-identical** before and after, and that **the rest of the file differs
     only in lines a `bind` is supposed to touch**. Byte-identity is scoped to the `egress:` line —
     a whole-file assertion would make every unrelated ruamel formatting difference a failure of this
     Mission.
  3. **Observe the red on the base first** — the pin fails for at least the quoted-string and `null`
     cases. Quote it.
  4. If byte-identity requires it, set `preserve_quotes = True` on `load_tracker_config`, matching
     what `save_tracker_config` already does at `config.py:160`. **Confirm the measured blast radius**
     rather than assuming either bound: `from_dict` `str()`-coerces every known string field, so only
     `_extra` values and the raw `egress` retain the ruamel scalar-string subclass.
  5. Give `clear_tracker_config`'s third `YAML()` (`config.py:184`) `preserve_quotes` too — today
     `unbind` destroys quoting in **sibling blocks** even where `save_tracker_config` would have
     preserved it.
- **Files**: `src/specify_cli/tracker/config.py`;
  `tests/sync/tracker/test_tracker_egress_config_3108.py`.
- **Validation**: the parametrised test prints `15` and asserts it; `tests/sync/tracker/test_config.py`
  and `tests/sync/tracker/test_local_service.py` still at their Stage-0 numbers, or any red traceable
  to the `preserve_quotes` change and explained.
- **Edge cases**: the mapping and list cases round-trip as YAML structures, not strings — the
  byte-comparison is over the rendered `egress:` region, and you must decide (and record) how that
  region is delimited for a multi-line value.

### T012 — Class A preservation: A2, A3, and the pin-less A4

- **Purpose**: FR-011 class A and A′.
- **Steps**:
  1. **A2 — `TrackerService.bind`'s local branch (`service.py:163`). CLASS A′.** Hand
     `LocalTrackerService` the **loaded** config (`load_tracker_config(self._repo_root)`), matching
     the SaaS branch above it at `:142-145`.
     **Write NO red-first pin and NO end-to-end pin for A2.** Measured: `LocalTrackerService.bind`
     (`local_service.py:47-63`) never reads `self._config` — it constructs a fresh
     `TrackerProjectConfig` at `:57` and saves that — so your change alters **nothing on disk** until
     site **A1** lands in **WP04 T024**. An end-to-end pin here is red before your fix and red after
     it. **Assert A2 at the unit level: that the object handed to the `LocalTrackerService`
     constructor carries the loaded `egress` (and `_extra`)** — a constructor-argument assertion, not
     a file assertion. The end-to-end `TrackerService.bind` preservation pin is **WP04's**, in T024,
     and is not yours to write or to claim.
  2. **A3 — `SaaSTrackerService.bind` (`saas_service.py:266`).** Carry `egress` (and `_extra`) forward
     from the loaded config instead of building a bare
     `TrackerProjectConfig(provider=…, project_slug=…)`. Red-first pin exists on the base; its red is
     `AFTER bind: egress present? False` against `CONTROL (_extra-carrying pattern): True`.
  3. **A4 — `TrackerService._resolve_saas_backend_for_provider` (`service.py:98`).** Carry the loaded
     config's `egress` (and `_extra`) into the substituted object, or make a substituted config
     non-persistable — **so a future write-capable caller cannot reintroduce the erasure.**
     **Write NO red-first pin for A4.** Measured: it cannot be reached from any write today.
     `_persist_binding`'s three call sites (`saas_service.py:347`, `:412`, `:505`) all sit inside bind
     flows (`_confirm_and_persist`, `_bind_from_resolution`, `validate_and_bind`) entered from
     `TrackerService.bind` (`service.py:141-145`), which constructs its own service with
     `load_tracker_config`; `_resolve_saas_backend_for_provider` serves only the three **read** paths
     (`service.py:210,214,220`), whose methods (`saas_service.py:556,575,592`) persist nothing; and
     `apply_binding_upgrade` (`saas_service.py:191`) has **zero callers in `src/`** — tests only.
     *"An implementer told to 'red it first' would be writing a pin against code no production path
     executes."* Assert A4 at the **unit level, against the substituted config object directly.**
  4. Every **file-level** A-site pin — that is **A3 only**, in this WP — runs in **both directions**
     (a recorded `refused` and a recorded `permitted`) **with the sibling `sync:` block asserted
     still present as the control**. The control proves the file was written and the rest survived,
     so a missing key is **erasure** and not a write failure. A2's and A4's unit-level assertions run
     in both directions too, but against the constructed object, not against a file.
- **Files**: `src/specify_cli/tracker/service.py`, `src/specify_cli/tracker/saas_service.py`;
  `tests/sync/tracker/test_tracker_egress_config_3108.py`.
- **Validation**: **A3** observed **red on the base**, then green, with the `sync:` control asserted.
  **A2 and A4** asserted at the **unit level** with **no red-first claim made for either**.
- **Edge cases**: do **not** touch `local_service.py:57` (site A1). It is WP04's. And do not "fix"
  A2's inertness by reaching into `local_service.py` — the window is named above and closes in
  WP04 T024.

### T013 — Class B carries: the two sites your own promotion breaks

- **Purpose**: FR-011 class B. **These are green on the base and red only on the FR-002-only tree.**
- **Steps**:
  1. On the **FR-002-only tree** (T009 applied, no class-B carry yet), write and run B1's and B2's
     preservation pins. Observe them **red** and **quote both**, at the same measurement point where
     T010's null-planting red is observed. *"Without this, B1/B2 would be the only requirement in the
     Mission shipping without an observed red."*
  2. **B1 — `saas_service.py:206-219`** (the binding-ref upgrade inside `apply_binding_upgrade`;
     construction at `:206`, `_extra=` carry at `:219`): add an explicit `egress=self._config.egress`
     carry **beside** the `_extra` carry. **Do not replace the `_extra` carry.**
  3. **B2 — `saas_service.py:303-316`** (`_persist_binding`; construction at `:303`, carry at `:316`):
     same.
  4. Re-run; green.
  5. Run the detection signal: `tests/specify_cli/` must stay at its Stage-0 number
     (`35 passed in 54.65s` at `bb2020fea`). If
     `test_apply_binding_upgrade_preserves_extra_fields` reds, **the B1 fix replaced the `_extra`
     carry instead of adding an `egress` carry beside it. Do not weaken the assertion to "repair"
     it.**
- **Files**: `src/specify_cli/tracker/saas_service.py`;
  `tests/sync/tracker/test_tracker_egress_config_3108.py`.
- **Validation**: two reds quoted from the FR-002-only tree, then green; `tests/specify_cli/` at its
  Stage-0 number with the `N passed` line quoted.
- **Edge cases**: the FR-002-only tree is a **measurement point, not a commit boundary** — T009
  through T014 land as **one commit**. If you must split them, the split requires a guard asserting
  that every `TrackerProjectConfig(` construction whose value flows into `save_tracker_config` carries
  `egress`. *"Splitting them without that guard ships a window in which the two SaaS sites are
  silently broken."*

### T014 — Sites C and D: `unbind` keeps the decision

- **Purpose**: FR-011 (C), (D); SC-009.
- **Steps**:
  1. **Site C — `clear_tracker_config` (`config.py:178-194`).** Replace the unconditional
     `del payload["tracker"]` at `:191` with: **retain** a `tracker:` block holding **only** a
     recorded `egress` when one exists; **delete** the block entirely when none is recorded. Give the
     third `YAML()` at `:184` `preserve_quotes`.
  2. **Site D — `SaaSTrackerService.unbind` (`saas_service.py:281`).** Reset
     `self._config = load_tracker_config(self._repo_root)` instead of `TrackerProjectConfig()`, so the
     in-memory object matches what site C just left on disk. *"A subsequent `_persist_binding` on the
     same instance would then write a config with no `egress` — erasing exactly what site C was just
     fixed to preserve."* Library-caller reachable only (the CLI builds a fresh service per
     invocation), which is why it is class D and not class A — **assert it at the unit level.**
  3. **SC-009 pins**: `spec-kitty tracker unbind` on a project with a committed `egress` leaves the key
     **present with its value unchanged** and every other `tracker:` key gone — asserted for **both**
     `refused` and `permitted`; on a project **without** the key it removes the `tracker:` block
     entirely; and **the sibling `sync:` block survives all three, as the control**.
  4. Close the WP by running the quality gates: `ruff check` clean (complexity ceiling 15, no blanket
     `# noqa`), `mypy --strict` clean with no added `# type: ignore`, ≥90 % coverage on the new
     branches from focused tests executing the new helpers directly.
- **Files**: `src/specify_cli/tracker/config.py`, `src/specify_cli/tracker/saas_service.py`;
  `tests/sync/tracker/test_tracker_egress_config_3108.py`.
- **Validation**: site C observed **red on the base** (measured: `unbind` erases today, with the
  sibling `sync:` block present as the control), then green. Site D asserted at the unit level.
- **Edge cases**: an `unbind` that leaves a binding-named block holding only a consent decision is
  **the accepted cost**, recorded in `plan.md` Project Structure — not a bug to tidy away.

---

## Test Strategy

- **New**: `tests/sync/tracker/test_tracker_egress_config_3108.py` — the probed-set round trip through
  `bind`, the `unbind` preservation in both directions with the sibling `sync:` block as control, the
  no-null-planting pin, and the fault **classification** pin over all 15 values.
- **Run**:
  - `pytest tests/sync/tracker/test_tracker_egress_config_3108.py` — unpiped, `N passed` quoted.
  - `pytest tests/sync/tracker/ tests/agent/cli/commands/test_tracker.py` — must stay at its Stage-0
    number.
  - `pytest tests/specify_cli/` — must stay at its Stage-0 number. **Detection signal.**
- `ruff check` and `mypy --strict` clean on all four owned files.

## Definition of Done

- `egress` in `_KNOWN_KEYS`, carrying the raw value plus a derived fault; module-local sentinel;
  `isinstance`-guarded decode.
- `to_dict` omits `egress` when nothing is recorded — with the null-planting red **observed and
  quoted on the FR-002-only tree** before the fix.
- The round-trip pin **prints and asserts 15**, and is byte-identical on the `egress:` line for every
  case.
- The module-local sentinel is named **`EGRESS_ABSENT`**, homed in `tracker/config.py`, public, and
  importable by WP03 without reaching for a private name.
- Preservation green **on disk**, in **both directions**, at **A3, B1, B2, C and D**, each with the
  sibling `sync:` block asserted present. **A2 and A4 asserted at the unit level, with NO red-first
  pin and NO end-to-end pin for either** — and the reason A2 cannot be earned inside this WP stated
  in the PR body.
- B1's and B2's reds **observed and quoted** on the FR-002-only tree. T010's null-planting red
  **observed, quoted, and classified from what was actually seen** (an `AssertionError` on a rendered
  null, or a `RepresenterError` out of `save_tracker_config` — say which).
- `tests/specify_cli/` and `tests/sync/tracker/ tests/agent/cli/commands/test_tracker.py` at the
  Stage-0 numbers **you measured yourself in T008**, quoted before and after.
- `ruff check` and `mypy --strict` clean, no blanket suppressions.
- **T009–T014 land as one commit.** No file outside the four owned files is modified.

## Risks & Mitigations

- **A narrowed field type silently converts refused → permitted** → raw value plus derived fault; the
  15-value byte-identical pin.
- **The promotion silently breaks B1/B2** → they land in the same commit, with their reds observed and
  quoted on the FR-002-only tree first.
- **A "repair" of `test_apply_binding_upgrade_preserves_extra_fields`** → it is a detection signal;
  a red there means the `_extra` carry was replaced, not that the assertion is wrong.
- **`preserve_quotes` blast radius** → measured narrow (`_extra` values and the raw `egress` only);
  confirm rather than assume; made while no gate exists so any red is attributable.

## Review Guidance

- Verify the decode is `isinstance(raw, str) and raw in _LEGAL`, in that order, and that a mapping and
  a list at the key are covered by a test.
- Verify the null-planting red and B1/B2's reds were **observed and quoted**, not asserted.
- Verify **every file-level** preservation pin has the sibling `sync:` block as its control.
- Verify **no** red-first pin and **no** end-to-end pin was written for **A2** or **A4**, and that
  the A2 reasoning (`LocalTrackerService.bind` never reads `self._config`) is stated rather than
  assumed.
- Verify the sentinel is `EGRESS_ABSENT`, public, in `tracker/config.py`, and that any `__all__`
  added enumerates the module's existing public names too.
- Verify T010's red was **quoted and classified from observation**, not pre-declared.
- Verify `local_service.py` was not touched — site A1 is WP04's.

## Activity Log

- 2026-08-01T00:20:00Z – system – Prompt created.
