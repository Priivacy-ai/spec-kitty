# Mission Specification: retire the dead queue-backed event drain

**Mission Branch**: `feat/chain-b-consent-bypass-3167`
**Created**: 2026-08-04 · **Re-specified**: 2026-08-04 after the post-specify adversarial squad
**Status**: Draft
**Input**: #3167 asks for the two remaining Chain-B enforcement sites to be migrated onto the consent
seam. The squad established that one of the two sites is on a code path with **no production caller**,
so migrating it would harden dead code and report a confidentiality win the mission had not produced.
This spec instead **retires the dead senders**, which the repository's own standing guard nominates as
the successor work.

**Baseline**: `upstream/main` `abca7ec96`. The rejected premise, its evidence, and the findings that
survived it are in `analysis-report.md`. The original research is in `research.md` with its two wrong
findings marked inline rather than edited away.

## Why this shape, in one paragraph

`batch_sync` and `sync_all_queued_events` have zero production callers — the only matches outside
`sync/batch.py` are three comments. `sync/__init__.py:61-66` records the journal dispatcher
(`delivery/dispatcher.py`) as the **sole** event drain; `tests/architectural/test_egress_consent_boundary.py:577-586`
allowlists `sync/batch.py` as `UNREACHABLE` (inventory `E15`, "ungated, but unreachable… if it is ever
re-wired this allowance is void"); and `tests/sync/test_no_queue_drain_constructed_3030.py` is a
standing AST guard against re-wiring, whose own docstring says **"retiring the implementations outright
belongs to the work package that already opens `batch.py`."** This is that work package. Deleting the
senders removes the latent hole permanently, which is strictly better than gating code that should not
exist — and it discharges the recorded precondition at `sync/emitter.py:2441-2443` ("if a queue-backed
sender is ever restored, this write becomes egress and must be gated on consent *first*") by removing
the thing that could be restored by accident.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The ungated sender cannot be revived by a one-line edit (Priority: P1)

A future contributor wires a queue drain back in, because the functions were sitting there looking
usable. Today the standing guard catches the *import*, but the ungated sender still exists to be
imported. After this mission the sender is gone, so there is nothing to re-wire and the guard has
nothing left to defend.

**Why this priority**: it is the whole mission. The residual risk `E15` records is "one edit away from
egress", and deletion is the only change that removes it rather than documenting it.

**Independent Test**: assert the symbols are absent from `sync/batch.py` and from the package API, and
that the ungated POST path they reached no longer exists in the module.

**Acceptance Scenarios**:

1. **Given** the retirement has landed, **When** `sync/batch.py` is read, **Then** neither
   `batch_sync` nor `sync_all_queued_events` is defined.
2. **Given** the retirement has landed, **When** the batch POST path is searched for, **Then** no
   sender in `sync/batch.py` posts queued events without a per-project consent decision — established
   by enumerating the module's remaining outbound calls, with the count stated.
3. **Given** the retirement has landed, **When** `tests/sync/test_no_queue_drain_constructed_3030.py`
   runs, **Then** it still passes — its guarantee is strengthened, never weakened, and it is **not**
   deleted as redundant.

---

### User Story 2 - Everything that still uses `sync/batch.py` keeps working (Priority: P1)

`sync/batch.py` is not a dead module — only its two senders are dead. `categorize_error`,
`format_sync_summary`, `generate_failure_report`, `write_failure_report`, `run_final_sync_with_retries`,
`BatchEventResult` and `BatchSyncResult` are live and exported. Retirement must remove exactly the dead
senders and nothing else.

**Why this priority**: P1 alongside User Story 1, deliberately. A deletion that takes live helpers with
it is the failure mode here, and it is the mirror of the positive-control asymmetry the squad found in
the previous draft of this spec.

**Independent Test**: the retained public surface of `specify_cli.sync` is unchanged except for the two
intentionally-absent names, and every existing consumer of the retained helpers still passes.

**Acceptance Scenarios**:

1. **Given** the retirement has landed, **When** `specify_cli.sync`'s public API is enumerated,
   **Then** it differs from baseline by **zero** names — the two senders were already deliberately
   absent (`sync/__init__.py:61-66`), so this deletion must not change the API at all.
2. **Given** the retirement has landed, **When** the retained helpers' existing tests run, **Then**
   they pass, with the node count stated.
3. **Given** `run_final_sync_with_retries` (`sync/batch.py:628-645`) takes its operation as a
   parameter and is called from `sync/background.py:467` with `self._perform_sync`, **When** the
   senders are deleted, **Then** that call path is untouched and its tests still pass.

---

### User Story 3 - The test suite stops being blind to the seam it was mocking (Priority: P1)

`tests/sync/conftest.py:221` is an autouse fixture that patches
`specify_cli.sync.batch.is_sync_enabled_for_checkout` to `True` for every `tests/sync` file whose name
lacks `"consent"` or `"capture_gate"` — so the drain suite ran with the gate wired open and could not
observe its decision. Worse, it patches with `raising=False` (`:283`), so once the patched name is gone
the patch becomes **inert with no error**: green for the wrong reason, silently, across 20 files.

**Why this priority**: P1. This is the mechanism that let the gate stay broken and uncovered, and
deleting the sender is exactly the event that converts the fixture from wrong-but-loud to
wrong-and-silent. Retiring the sender without cleaning the fixture leaves the trap armed for the next
mission.

**Independent Test**: the fixture no longer patches a name that production does not consult, and a
deliberately-wrong patch target fails loudly rather than silently.

**Acceptance Scenarios**:

1. **Given** the senders are deleted, **When** `tests/sync/conftest.py` is read, **Then** it does not
   patch `specify_cli.sync.batch.is_sync_enabled_for_checkout`.
2. **Given** the fixture patches any remaining seam, **When** that seam's name is wrong, **Then** the
   patch fails loudly — `raising=False` is removed or individually justified in place with the reason
   it is safe.
3. **Given** the fixture change has landed, **When** the `tests/sync` cone runs, **Then** the result
   is compared per-node-id against the committed baseline and every difference is attributed.

---

### User Story 4 - The record stops pointing at things that are not there (Priority: P2)

Three text corrections, each a false or soon-to-be-false pointer:

- `tests/architectural/test_egress_consent_boundary.py:577-586` — the `E15` allowance describes a file
  that will no longer hold the sender. Its own suite reds on an inert allowlist entry, so the entry
  must be removed, not amended.
- `sync/runtime.py:106` — stays on the checkout chain per **C-001**, and gains a comment stating that
  auto-start is not an egress boundary, so its Chain-B call is not read as an unfixed bypass.
- **"The drain" has three referents and no glossary entry** — `delivery/selection.py` (dispatch
  selection), `sync/background.py:280` (body upload), and `sync/batch.py` (the retired event drain,
  after this mission: gone). This overload is what made the previous draft of this spec assert that a
  true docstring was false.

**Why this priority**: P2 — no behaviour change, but a false pointer is how an auditor concludes a gate
exists. The previous draft of this spec was itself produced by one.

**Independent Test**: read each of the three sites and confirm the statement matches the tree as
shipped; for `E15`, its own allowlist-consistency test is the check.

**Acceptance Scenarios**:

1. **Given** the senders are gone, **When** the egress-allowlist consistency test runs, **Then** it
   passes with the `E15` entry removed — not with the entry retained and re-worded.
2. **Given** `sync/runtime.py:106` is unchanged in behaviour, **When** it is read, **Then** a comment
   states auto-start is not an egress boundary, names the real gate, and does **not** claim that gate
   covers every path (the squad established that a started runtime emits a `build_id` in a `pong` that
   the publish gate never sees; it is classified not-project-data at
   `tests/architectural/test_egress_consent_boundary.py:567-575`, and the comment must point at that
   enumeration rather than overclaiming).
3. **Given** the terminology fix has landed, **When** "the drain" appears in `sync/` or `delivery/`,
   **Then** each occurrence either names its referent or the glossary disambiguates it, following the
   `primary`/`merge`/`routing` precedent in the Terminology Canon.

---

### Edge Cases

- **A test exists that only covers a deleted sender** → it is retired with the sender, and the reason
  is recorded in the commit. Silent deletion of a `#3030`-era regression test is a reviewer-reject.
- **`tests/sync/test_batch_sync.py:294`** patches `specify_cli.sync.batch.is_sync_enabled_for_checkout`
  with default `raising=True` and asserts the checkout-disabled behaviour. It breaks hard, and its
  *premise* is deleted. Disposition must be explicit: retire with the reason, not re-point at a
  survivor.
- **A retained helper turns out to be reachable only from a deleted sender** → it is dead too;
  enumerate and state it rather than leaving an orphan.
- **The deletion changes the `tests/sync` leak-guard observation set** → attribute per node-id against
  the committed baseline. If a pinned leak stops reproducing *as a consequence* of this mission, the
  guard requires the pin be removed (`tests/sync/_leak_guard.py:818-823`); do that and record the
  attribution. Do **not** opportunistically re-pin, and do **not** remove a pin for any other reason.
- **The senders are reachable dynamically** (entry point, plugin, `getattr`) → static absence of callers
  would not show it. Establish it before deleting, and say how.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Retire the dead senders | As a maintainer, I want `batch_sync` and `sync_all_queued_events` deleted, so an ungated queue drain cannot be revived by a one-line edit. | High | Open |
| FR-002 | Prove non-reachability before deleting | As a reviewer, I want reachability established — static enumeration **plus** a check for dynamic entry points — before the deletion lands, so "no callers" is a measurement. | High | Open |
| FR-003 | Retire only the dead surface | As a consumer, I want `sync/batch.py`'s live helpers and the `specify_cli.sync` public API unchanged, so retirement does not become a breaking change. | High | Open |
| FR-004 | Dispose of orphaned tests explicitly | As a reviewer, I want every test retired alongside a deleted sender named with its reason in the commit, so no `#3030`-era regression test disappears silently. | High | Open |
| FR-005 | Clean the blinding fixture | As a maintainer, I want `tests/sync/conftest.py` to stop patching a name production no longer consults, so the cone cannot pass for the wrong reason. | High | Open |
| FR-006 | Make mis-targeted patches loud | As a maintainer, I want `raising=False` removed from that fixture, or justified in place, so a wrong patch target fails instead of going inert. | High | Open |
| FR-007 | Remove the E15 allowance entry | As a maintainer, I want the `UNREACHABLE` allowlist entry for `sync/batch.py` removed once its sender is gone, so the egress inventory does not carry an inert row. | Medium | Open |
| FR-008 | Annotate the auto-start boundary | As a maintainer, I want `sync/runtime.py:106` commented as a non-egress auto-start decision pointing at the per-sender egress enumeration, without claiming one gate covers every path. | Medium | Open |
| FR-009 | Disambiguate "the drain" | As a reader, I want each use of "the drain" to name its referent or be covered by a glossary entry, so the overload stops producing false findings. | Medium | Open |
| FR-010 | Close the tracker honestly | As the operator, I want `#3167` dispositioned with the evidence — one site retired rather than migrated, one site deliberately unchanged — and the residuals filed as issues rather than absorbed. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | No new egress surface | The count of module-level senders in `sync/batch.py` that can POST without a per-project consent decision goes from its measured baseline to **zero**, with both numbers stated. | Security | High | Open |
| NFR-002 | Public API unchanged | `specify_cli.sync`'s exported name set differs from baseline by **zero** names, asserted by comparing enumerated sets, not by inspection. | Compatibility | High | Open |
| NFR-003 | Cone attributed per node-id | Every difference between the post-change `tests/sync` result and the committed baseline is attributed to a cause. Unattributed differences block the work package. | Reliability | High | Open |
| NFR-004 | Guard strength never decreases | `tests/sync/test_no_queue_drain_constructed_3030.py` still passes and is not deleted, weakened, or narrowed. | Reliability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Auto-start is not consent | `sync.auto_start` must not be unified with `sync.enabled`. Per operator decision D-M5a-1 = a, `sync/runtime.py:106` keeps its checkout-chain call and gains a comment only. | Technical | High | Open |
| C-002 | Deletion, not gating | The dead senders are removed rather than migrated onto the consent seam. Gating code slated for deletion cannot produce a non-manufactured red. | Technical | High | Open |
| C-003 | Sweep serialisation | `tests/sync` and `tests/cli` sessions must never run concurrently. This mission holds the `tests/sync` window; it must also not run `tests/cli` itself while holding it. | Process | High | Open |
| C-004 | Cross-mission file hazard | This mission opens `tests/sync/conftest.py` — the leak-guard host — and the cone hosts 3 of the 12 pinned leaks (`tests/sync/_leak_guard.py:420, :442, :452`). It lands before the sync-cone mission's enumeration opens. It must not opportunistically re-pin; if a pinned node stops reproducing **as a consequence** of this mission, un-pin it and record the attribution in the handoff note (C-005). | Process | High | Open |
| C-005 | Handoff artifact for the sync-cone mission | A per-node-id pre/post leak-observation delta for the 3 pinned nodes, plus a description of the `conftest.py` fixture change, committed to this dossier and cited as a required input to that mission's replan gate. Ordering alone gives a fresh enumeration but not **attribution**. | Process | High | Open |
| C-006 | Residual placed in the code | C-004's ordering and do-not-re-pin rule is recorded on the three `_PinnedLeak` entries themselves, not only in this dossier. A successor edits `_leak_guard.py`, not this spec. | Process | Medium | Open |
| C-007 | Red first, where a red is possible | Requirements whose red is achievable land red-first with the red as the consequence. Requirements that are **already** true at baseline (see the register below) are declared as regression guards, not padded with an inspection claim. | Process | High | Open |
| C-008 | File, do not absorb | The out-of-scope findings in the register below are filed as issues before merge. | Process | High | Open |

### Register — which requirements can be red-first, and which cannot

The previous draft of this spec was rejected partly for demanding a red-first proof of things already
true at baseline. Stated explicitly instead:

| Requirement | Red achievable? | How it lands |
|---|---|---|
| FR-001, FR-005, FR-006, FR-007 | **Yes** | The absence assertions are red before the deletion and green after. |
| FR-002 | Yes | The reachability enumeration is the deliverable; its red is a caller found. |
| FR-003, NFR-002, NFR-004 | **No — already true** | Regression guards. Their obligation is not to break, with node ids quoted in the baseline. |
| FR-004, FR-008, FR-009, FR-010 | **No — text/tracker** | Verified by reading and by the tracker state, declared as such rather than dressed as tests. |

### Key Entities

- **`batch_sync` / `sync_all_queued_events`**: the retired senders, ungated and unreachable. Subject of
  the deletion.
- **`sync/batch.py`'s retained helpers**: `categorize_error`, `format_sync_summary`,
  `generate_failure_report`, `write_failure_report`, `run_final_sync_with_retries`, `BatchEventResult`,
  `BatchSyncResult` — live, exported, out of scope for deletion.
- **`E15` allowance**: the `UNREACHABLE` entry in the egress inventory that this deletion makes inert.
- **`_consented_checkout_by_default`**: the autouse fixture at `tests/sync/conftest.py:221` that
  blinded the cone.
- **"The drain"**: an overloaded term with three referents. After this mission, two.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `sync/batch.py` defines **0** senders that POST queued events without a per-project
  consent decision, down from a stated baseline count, with both numbers printed.
- **SC-002**: `specify_cli.sync`'s exported name set is **identical** to baseline — set difference
  empty, both set sizes printed.
- **SC-003**: `tests/sync/test_no_queue_drain_constructed_3030.py` passes, quoted from a redirected
  run with its node count.
- **SC-004**: Of the tests retired alongside the senders, **K/K** have their reason recorded in the
  commit message, K stated.
- **SC-005**: `tests/sync/conftest.py` patches **0** names that production does not consult, verified
  by resolving each patch target against the post-change tree, with the number of targets checked
  stated.
- **SC-006**: The `tests/sync` cone is compared per-node-id against the committed baseline of
  the measured **distribution** — `{5,5,6,6,6}` errors at `b04da00e13^`, n=5, input 2395 (`analysis-report.md` §4). **Not a scalar:** 5 is the tail, not the mode, and comparison is by per-node-id set difference over ≥5 runs per arm. Every difference is
  attributed by node id; **0** unattributed differences.
- **SC-007**: The egress-allowlist consistency test passes with `E15` removed, quoted from a redirected
  run.
- **SC-008**: **K/K** residuals in the register are filed as issues with numbers recorded here, K
  stated.

## Out of scope — filed, not absorbed

Per the programme rule that produced this mission. Each gets an issue before merge (FR-010, SC-008).

| Finding | Evidence | Disposition |
|---|---|---|
| `consented_project_uuids` **writes machine-global config on read** (`sync/consent.py:483,:512` → `_reconcile_index` → `set_project_consent`). Measured: index goes `None` → `True` after one read, and the grant survives removal of the project-local grant. Makes a documented side-effect-free gate mutate machine state, and cross-contaminates refusal vs positive-control tests through a shared `SPEC_KITTY_HOME`. | `analysis-report.md` §3 | **File** → `Priivacy-ai/spec-kitty#3196` (WP04/T019). Not this mission's file, and a real defect. |
| **Three envelope→`project_uuid` resolvers disagree** — `sync/project_identity.py:70-125` (envelope then payload, nil-normalised), `delivery/consent_gate.py:183-206` (envelope-only), `sync/queue.py:110-127` (third walker, legacy overlay). The same row resolves differently by caller. | `analysis-report.md` §3 | **File** → `Priivacy-ai/spec-kitty#3197` (WP04/T019). |
| **A consenting project's events are withheld when cwd is inside no project** — the daemon's usual case, since `sync/daemon.py:1319` passes no `cwd=` and sets `start_new_session=True`. Demonstrated on the live path. `sync/emitter.py:1910-1914` records this over-refusal having happened once already. | `analysis-report.md` §3 | **File** → `Priivacy-ai/spec-kitty#3198` (WP04/T019). Silent hosted-sync outage, independent of this mission. |
| **`sync/runtime.py:106` defence-in-depth** — options (b)/(c) of D-M5a-1, declined once by the operator. | `research.md` §6 | **File** → `Priivacy-ai/spec-kitty#3199` (WP04/T019), so the residual has an owner. |
| **The leak guard's failure text points at `tests/sync/conftest.py`** for a registry that moved to `_leak_guard.py` in `#3144` (defined at `:376`/`:481`; the six stale message sites are `:521,:629,:642,:847,:878,:908` — WP01's `:572,:585,:822` citation drifted when WP03 edited the file). | `analysis-report.md` §3 | **File** → `Priivacy-ai/spec-kitty#3200` (WP04/T019) for the sync-cone mission (registry owner). Do not fold. |
| **`cli/commands/sync.py:2081`** branches control flow on `routing.effective_sync_enabled`; #3167 calls both CLI sites "display-only", which is wrong for this one. | squad finding | **File** → `Priivacy-ai/spec-kitty#3201` (WP04/T019), with the misclassification noted. |
| **Revocation between selection and POST** | `research.md` §6 | **Fold** as a declared boundary — genuinely out of scope and already named. **Deliberately NOT filed** — WP04/T019 checked this row against the six `File` rows before filing so the Fold disposition was not swept up by mistake. |
| **`core/batch_partition.py::split_in_half` now has zero production consumers** — its last one, `sync/batch.py::_shrink_events_for_retry`, went with the deletion. **Kept** as a canonical leaf by operator decision; the T018 AST sweep in `tests/architectural/test_batch_split_single_authority.py` still guards all of `src/` against hand-rolled `len(...) // 2` midpoint maths and is unchanged by the retirement. | `contracts/deletion-manifest.md` §1; `tests/architectural/test_batch_split_single_authority.py:8-27` | **File** → `Priivacy-ai/spec-kitty#3202` (WP04/T019). A disclosure so a later dead-code sweep cannot remove it without seeing why it survives — **not** a request to delete it. |
| **FR-009's out-of-scope drain prose** — **12** `src/` files still carry ambiguous "the drain" (control: `emitter.py` = 11 occurrences, case-insensitive). In-place naming was scoped by operator decision to the files this mission already opens; the rest are hot cross-mission surfaces and a sweep there collides with the sync-cone mission. | `contracts/deletion-manifest.md` §7 | **File** → `Priivacy-ai/spec-kitty#3203` (WP04/T019). |

### SC-008 closure — K = 8, and why 8 and not 9

**K = 8 residuals filed**, as `Priivacy-ai/spec-kitty#3196`–`#3203`, one per row above with a `File`
disposition (six) plus the two additional residuals WP04/T019 was handed (`#3202`, `#3203`).

The table holds **nine** rows and only eight issues exist. The ninth — *revocation between selection
and POST* — is dispositioned **Fold**, and folding means the boundary is declared in the spec rather
than deferred to a tracker row. Filing it would have manufactured a follow-up for something already
resolved, which is the mirror image of the defect this mission exists to remove.

**FR-009's count is 12, not the 13 asserted at `plan.md:270` and `WP04:86`.** Neither figure was
ever derived; WP01 measured every reading (`contracts/deletion-manifest.md` §7) and reproduced 12
out-of-scope files, with 13 reachable only by counting `sync/batch.py`, which is inside this
mission's own write scope. `#3203` is filed at the measured 12.

Every one of the eight was checked against the open tracker before filing, and against the five
follow-ups this mission had **already** filed and which are therefore *not* register rows:
`Priivacy-ai/spec-kitty#3188` (pre-existing marker reds), `#3190` (the closure script's C901s),
`#3191` (the per-event forbidden-key screen still owed), `#3192` (three live-path branches
unpinned), `#3193` (the leak-guard attribution race). No duplicates.
