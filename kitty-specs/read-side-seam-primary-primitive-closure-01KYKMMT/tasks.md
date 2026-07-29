# Tasks: Read-Side Seam: Placement-Authority Closure

**Mission**: `read-side-seam-primary-primitive-closure-01KYKMMT`
**Branch contract**: planning/base branch **`fix/read-side-seam-primary-primitive-closure`**;
final merge target **`fix/read-side-seam-primary-primitive-closure`**;
`branch_matches_target = true`.
Execution worktrees are allocated **per computed lane** from `lanes.json` after
`finalize-tasks` — never hand-constructed.

**Input**: [spec.md](./spec.md) (24 FR / 11 NFR / 11 C / 21 SC / 8 user stories) ·
[plan.md](./plan.md) (10 ICs + the Expected-Red Ledger + the Doctrine grounding table) ·
[research.md](./research.md) · [data-model.md](./data-model.md) ·
[contracts/](./contracts/) · [quickstart.md](./quickstart.md)

---

## ⚠ Read this before claiming any WP

### 1. The suite is deliberately red between WP01 and WP08

WP01 rewrites the architectural gates to describe the **target** design. From that moment
the suite states the destination, and each later WP's job is to turn specific nodes green.
**A red is not automatically a regression.** Classify every red into exactly one of three
buckets before touching anything:

| Bucket | How to recognise it | What to do |
|---|---|---|
| **Expected-by-design** | the node is on WP01's recorded expected-red list (`research/expected-reds.md`, see WP01 T007), or on your own WP's list | leave it, or green it if your WP owns it |
| **Foreign honest-red P0** | red on the mission base too, on a surface this mission does not own — e.g. `tests/sync/test_sync_consent_default_deny.py` (#3031, red **by design** per ADR `2026-07-17-1`, marked `fast` so it *will* appear in your lane, on `sync/routing.py` = the **sync fan-out** sense of "routing") | **do not touch.** Do not green-wash, do not widen scope (C-010) |
| **Load-bearing regression** | neither of the above; a resolved directory changed, a PRIMARY kind started raising, `RecursionError`, or a previously-green node went red | **fix the product** |

Classification is **by surface, not by timing** (C-010). Reproduce a suspected pre-existing
red on the true mission base (`git merge-base HEAD upstream/main`) in a scratch worktree
before attributing it to yourself — a lane tip is never a valid baseline.

    Run: spec-kitty charter context --include directive:DIRECTIVE_041

### 2. Never "fix" the product to keep a defunct gate green

This is the single most dangerous failure mode of this mission. Four gates *prescribe* the
shape being retired. Judge every red with `DIRECTIVE_041`'s taxonomy — **STALE → remediate ·
PATCHWORK/stub → delete · VALID and current → fix the product** — and record which applied
(SC-019). **Never retry-to-green.**

### 3. Two reds that fail by going *green*

`test_trio_seam_only.py`'s blessed-name staleness check and
`test_gate_read_literal_ban.py::test_write_arm_resolvers_anchor_meta_on_primary` both
currently pass while covering nothing (Ledger M6/M8). They need **positive assertions**, not
a fix-until-green loop. A gate that would stay green if the code regressed provides no
coverage.

### 4. Three hard sequencing gates (non-negotiable)

1. **WP01 before WP03** — retiring the use-count floors must precede the extraction. The
   extraction re-points 4 `resolution.py` callers off the primitive, which alone drops the
   scanned count below the 44 floor. (C-005; NFR-007)
2. **WP02 before any ledger row** — the grammar/index prerequisite. A row written under the
   old grammar parses **silently empty** while the reconciliation stays green. (C-009)
3. **WP03's extraction before its delegation** — the seam reaches the primitive *through*
   its PRIMARY leg; delegating without the extraction is an **infinite recursion**, not a
   refactor. Both halves are inside WP03 so the gate cannot be crossed by accident. (C-005
   Step 0)

### 5. Per-WP acceptance = the full C-008 local gate list

Not just your own suites. Run all six named gates every time — that is how a trio or
closeout red is caught in the WP that caused it instead of escaping to the aggregate:

```bash
PWHEADLESS=1 SPEC_KITTY_SYNC_MINIMAL_IMPORT=1 uv run pytest \
  tests/architectural/test_no_read_side_bypass.py \
  tests/architectural/test_resolution_authority_gates.py \
  tests/architectural/test_gate_read_literal_ban.py \
  tests/architectural/test_coord_read_residuals_closeout.py \
  tests/architectural/test_trio_seam_only.py \
  tests/architectural/test_no_write_side_rederivation.py \
  -q
```

**What "zero new findings" means.** Every WP's DoD says `ruff` and project-mode `mypy` report
**zero new** findings. The baseline is the **merge-base of your lane with
`fix/read-side-seam-primary-primitive-closure`**, measured on the files your diff touches — not
the whole tree, and not a lane tip. Capture the baseline before your first edit; if you cannot,
say so and report absolute counts instead of claiming a delta.

**Never run the full `tests/architectural/` suite locally** — it destabilises the session
(C-008). CI owns the exhaustive sweep. Never pipe `pytest`/`mypy` through `| tail` — it
masks the exit code. Inside a lane worktree always prefix `uv run` (a bare `python` imports
the *primary* checkout's `src`).

### 6. Ownership leeway

`owned_files` is non-overlapping by construction — that is the real guard against parallel
collisions. A small, well-justified edit outside your map is acceptable **with a one-line
rationale in the commit body**.

Pre-authorised out-of-map edits, stated in the direction they are actually needed:

| WP | May edit outside its map | Why |
|---|---|---|
| **WP08** | `src/specify_cli/missions/_read_path_resolver.py` (WP03's) | it deletes the wrapper and edits `__all__` — the deliberate serial-by-phase handoff |
| **WP08** | `docs/development/read-side-seam-classification.md` (WP02's) — **count rows and stale stay-lenient index rows only** | WP02 writes post-migration end-state counts and names WP08 the greening owner |
| **WP08** | comments/docstrings in the 7 modules that still name the deleted symbol | grep-and-correct after the delete |
| **WP08** | `src/specify_cli/core/paths.py` ×2, `src/specify_cli/core/git_ops.py`, `src/specify_cli/coordination/surface_resolver.py` (WP07's) | the **four FR-005 foundation sites** call the public wrapper; WP07 left them with rationale comments and deferred the re-point here. WP08 re-points all four at the module-private leaf `_compose_primary_feature_dir` **in the same change** as the wrapper deletion, or they ImportError (the M1 build-break) |
| **WP08** | `tests/architectural/test_no_read_side_bypass.py` (WP02's) — three specific edits | (a) update `_FOUNDATION_SANCTION_SEED` to match the four re-pointed foundation sites' new token text; (b) drop `src/mission_runtime/resolution.py` from the sanctioned set for `primary_feature_dir_for_mission` (WP03 drained its calls — the per-primitive non-vacuity assertion correctly reds until then); (c) reconcile `test_index_discriminator_represents_a_four_site_qualname`, which hardcodes the `_find_meta_path` sites as unrouted-forever though WP07 routed two of three |
| **WP08** | `tests/specify_cli/cli/commands/test_coordination_doctor.py` | re-point the `_raw` helper (~:1084) at `_compose_primary_feature_dir` — WP03's delegation turned this stale "raw resolver" test into a RecursionError; deleting the wrapper breaks it regardless |
| **WP04–WP07** | *nothing* in WP02's ledger or `test_no_read_side_bypass.py` — they **verify**, never author | WP02 lands the terminal shape including every per-site descriptor, so a routing WP that finds a gap **reports it as a WP02 gap** |
| **WP06** | `docs/development/read-side-seam-classification.md` — **the `retrospective/writer.py` row only** | WP03's cycle fix re-pointed that site at the leaf, so WP02's row (written before the fix) now mis-classifies it as an unrouted wrapper site. Correct it to `sanction-infra` (verify-only) with a one-line rationale citing WP03. Do **not** touch any other ledger row. |
| **WP07** (and any WP re-pointing a sanctioned site) | `tests/architectural/resolution_gate_allowlist.yaml` — **the affected entry's `token:` line only** | The YAML pins the literal token text of sanctioned call sites. Re-pointing such a site changes the token, so the entry must move with it or the gate reds on a correct fix. Keep the semantic sanction; record a one-line rationale. Precedent: WP03 `77226250f`. |

That last row is the load-bearing one: WP02 declares itself sole owner of the ledger and the
read-side gate *for the whole mission*, so "ensure the allow-list carries a descriptor" in the
shared procedure below means **confirm it exists**, not write it.

---

## The shared migration procedure (WP04–WP07 all follow this)

Each routing WP applies the same procedure per site. It is **semantic, not mechanical**
(C-007) — each site needs an individual kind decision.

1. **Read the ledger verdict** for the site (`docs/development/read-side-seam-classification.md`,
   authored to its terminal shape by WP02). The ledger is the authority; do not invent a
   classification.
2. **`migrate-fail-loud`** → replace the caller-chosen composition with
   `placement_seam(repo_root, handle).read_dir(<kind>)`. The caller declares only *what* it
   reads. Reuse the existing seam import in the module; do **not** introduce a second read
   authority.
3. **`stay-lenient`** → leave the site, and **confirm** (do not author) that WP02's allow-list
   carries a per-site descriptor with the production comment as its rationale of record (C-003 —
   no path-scoped blankets). A missing descriptor is a **WP02 gap to report**, not yours to
   write — see §6.
4. **`sanction-infra`** → record by name with the recursion rationale; **do not route**
   (FR-005, NFR-009).
5. **Pick the kind from what the site actually reads.** ~24 sites are unambiguous
   (`PRIMARY_METADATA`; `WORK_PACKAGE_TASK` and `ANALYSIS_REPORT` where named). If a site is
   genuinely ambiguous, say so in the WP notes rather than guessing.
6. **Behaviour-preservation evidence per site cluster** (NFR-001): for a materialized,
   non-backfilled mission the resolved directory is **identical**. The only permitted delta
   is the seam's bare-`<slug>` **backfill recovery** — pinned by test where it applies, never
   absorbed silently.
7. **No new raises** where leniency is the contract (NFR-002): a PRIMARY kind must not start
   raising on a husk, an empty coord worktree, or a deleted coord branch.
8. **Correct the comment you are standing next to.** Several of these files carry comments
   asserting that "the coord-aware resolver lands on the husk" as a reason not to route.
   That is true of the *kind-blind* resolver and false of the kind-aware seam (FR-015).
   Preserve the true warning, remove the false implication.

The decisive equivalence fixtures are in [quickstart.md](./quickstart.md) §4.

---

## Subtask Index

*Reference table only — not a tracking surface. The `Parallel` column marks parallelism, not
status. Record completion with `spec-kitty agent tasks mark-status T0xx --status done`, which
writes to the event log; there is no checkbox to tick.*

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Kind-discriminate the fold-prescription allow-sets (M7) | WP01 | |
| T002 | Give the write-arm node a positive assertion (M8) | WP01 | |
| T003 | Retire both use-count floors + the allow-list YAML block, with recorded before/after | WP01 | |
| T004 | Retire the closeout module's floor import and equality pins (M3) | WP01 | |
| T005 | Retire the `#2214` pin **with** its pin-existence test; fix the off-by-one census | WP01 | |
| T006 | Trio gate: shrink the blessed set and replace the self-nullifying exemption (M5/M6) | WP01 | |
| T007 | Refreeze gate-coverage baselines; record the expected-red set | WP01 | |
| T008 | Constrain the ledger's machine-parse grammar (one table per heading, trailing discriminator) | WP02 | [P] |
| T009 | Give the stay-lenient index a per-site discriminator + update its uniqueness assertion | WP02 | [P] |
| T010 | Add the two reconciliation/mutation gate assertions (per primitive) | WP02 | [P] |
| T011 | Grow the censused callees 2 → 4 with per-primitive non-vacuity and end-state sanctions | WP02 | [P] |
| T012 | AST-census and classify `resolve_feature_dir_for_mission` (both axes, per-disposition counts) | WP02 | [P] |
| T013 | Write the classification rows + honest bounds + Known-gap correction | WP02 | [P] |
| T014 | Correct every stale count in the ledger and the gate docstring | WP02 | [P] |
| T015 | Extract the terminal `KITTY_SPECS_DIR` assembler into a module-private leaf | WP03 | |
| T016 | Re-point the seam's PRIMARY leg and the resolver-internal callers at the leaf | WP03 | |
| T017 | Re-author the import-time content descriptor onto the leaf (same commit — else ~30 collection errors) | WP03 | |
| T018 | Prove the extraction behaviour-neutral: zero call-site changes, counts re-derived, no recursion | WP03 | |
| T019 | Delegate the public wrapper to `read_dir(<PRIMARY kind>)` | WP03 | |
| T020 | Attribute every divergence; pin backfill recovery red-first | WP03 | |
| T021 | Hand-verify the Class-C patch fixture did not go vacuously green | WP03 | |
| T022 | Route the 8 `resolve_feature_dir_for_mission` sites per ledger verdict | WP04 | |
| T023 | Route the 2 `primary_feature_dir_for_mission` sites in the same two files | WP04 | |
| T024 | Route **both** `_run_documentation_wiring` reads + the audit-metadata write | WP04 | |
| T025 | Pin the husk guarantee (or discharge the zero-case honestly) | WP04 | |
| T026 | Route the 4 trio rewrite targets (10 sites) | WP05 | |
| T027 | Correct the two `acceptance/__init__.py` comments and the three executor husk comments | WP05 | |
| T028 | Green the trio gate: blessed set empty of both drained names, positive assertion holds | WP05 | |
| T029 | Route the agent-CLI + lifecycle-shell cluster (10 sites) | WP06 | [P] |
| T030 | Correct the `next_cmd.py` husk comment | WP06 | [P] |
| T031 | Behaviour-preservation evidence for the cluster | WP06 | [P] |
| T032 | Route the runtime-bridge cluster (3 sites) + its two husk comments | WP07 | [P] |
| T033 | Route `status/aggregate.py` (4 sites) incl. the non-compliant `:522` and the `.name` `:543` shape | WP07 | [P] |
| T034 | Route `commit_router.py`; record the four foundation sites by name, unrouted | WP07 | [P] |
| T035 | Delete the public wrapper and drop it from `__all__` | WP08 | |
| T036 | Drain and privatise `_canonicalize_primary_read_handle` | WP08 | |
| T037 | Delete the `agent/tasks.py` re-export and rewrite its two tests against the real seam | WP08 | |
| T038 | Hand-edit the second census inventory (**do not** run the rekey script — #3011) | WP08 | |
| T039 | Green the read-side census for both new callees; record the floor→census transfer | WP08 | |
| T040 | Write `docs/architecture/artifact-placement-seam.md` against the **verified** layering | WP09 | |
| T041 | Narrow `branch-target-routing.md` to the branch sense | WP09 | |
| T042 | Add the `Routing` disambiguation + the Terminology Canon line | WP09 | |
| T043 | Register the page; regenerate both gated registries; docs hygiene green | WP09 | |
| T044 | Add the docs test asserting the page's required sections and citations | WP09 | |

---

## Phase 1 — State the destination *(no dependencies; WP01 and WP02 run in parallel)*

### WP01 — The suite states the target design

**Prompt**: [tasks/WP01-suite-states-target-design.md](./tasks/WP01-suite-states-target-design.md)
**Goal**: Rewrite the affected architectural gates so they describe the **destination**
rather than the structure being removed, making the suite this mission's specification.
**Priority**: P1 — this is the acceptance signal, and it dissolves two hazards structurally
(the floors are gone before the fifth routed site can trip their strict bound; the two
green-by-omission gates get positive assertions before anything can slip past them).
**ICs**: IC-0T, IC-01, IC-06 · **Dependencies**: none
**Independent test**: after this WP alone, **every** red is either an assertion about the
target design traceable to a named FR, or a listed foreign honest-red P0 — and **zero** reds
are collection errors introduced here.

Included subtasks: T001 T002 T003 T004 T005 T006 T007

Implementation sketch: fix the two gate *defects* first (kind-discriminated fold sets;
positive write-arm assertion) so the later widenings are not loosenings → retire the two
use-count floors and, in the same change, the closeout module's floor import and equality
pins that would otherwise `ImportError` at collection → retire the `#2214` pin together with
the test asserting it exists → shrink the trio blessed set and replace the exemption that
would leave the gate vacuously green → refreeze baselines and record the expected-red set.

Parallel opportunities: fully parallel with WP02 (disjoint files).
Risks: this is the one WP whose "green" is *not* the acceptance criterion — review it
against its recorded expected-red list. A carelessly red-stated suite **hides** regressions
instead of revealing them; the zero-collection-errors bar is what prevents that.
Estimated prompt size: ~330 lines.

### WP02 — Ledger grammar, per-site index, and the read-side gate's terminal shape

**Prompt**: [tasks/WP02-ledger-grammar-and-census.md](./tasks/WP02-ledger-grammar-and-census.md)
**Goal**: Make the ledger able to carry four primitives without parsing silently-empty, give
the index per-site addressing, land the read-side gate's **terminal** shape, and census +
classify the one resolver no gate covers.
**Priority**: P1 — C-009's hard gate. Every ledger row in the mission depends on it.
**ICs**: IC-02, IC-03 (+ IC-08's ledger/docstring line items) · **Dependencies**: none
**Independent test**: mutating a row belonging to **each** primitive independently reds the
gate; parsed row count equals the summed per-primitive census; the known four-site qualname
is representable and the uniqueness assertion holds.

Included subtasks: T008 T009 T010 T011 T012 T013 T014

Implementation sketch: constrain the grammar (one table per parsed heading, verbatim
headings, verdict/`rel_path`/`qualname` at their current leading positions, the `primitive`
discriminator **appended** as a trailing column) → discriminate the index per site → add the
two assertions that make the grammar enforceable → grow the censused callees 2 → 4 with
end-state sanctions and per-primitive non-vacuity → census and classify the 8 sites on both
axes with per-disposition counts → write the rows, the honest bounds and the corrected
Known-gap text → correct every stale count.

Parallel opportunities: fully parallel with WP01. **Sole owner** of the ledger and the
read-side gate module for the whole mission — it lands their terminal shape so later WPs only
*satisfy* those gates and never edit them.
Risks: the parse is positional and heading-exact — a sub-table under a parsed heading is
silently dropped, a mid-inserted column silently skips rows, a duplicated verdict key
silently overwrites. Landing the 2 → 4 census leaves the ~34 in-flight sites **expected
red** until WP08; that is the signal, not a defect.
Estimated prompt size: ~360 lines.

---

## Phase 2 — Make delegation possible, then prove equivalence

### WP03 — Extract the terminal assembler, then delegate the wrapper

**Prompt**: [tasks/WP03-extract-and-delegate.md](./tasks/WP03-extract-and-delegate.md)
**Goal**: Split the pure `KITTY_SPECS_DIR` assembly into a module-private leaf so the public
wrapper can delegate to the seam without recursing — then delegate it, surfacing every
hidden behavioural delta at **one file's** cost with the existing suite as the harness.
**Priority**: P1 — the safety property of the whole sequence.
**ICs**: IC-00, IC-04 · **Dependencies**: WP01
**Independent test**: the extraction lands with **zero** call-site changes and both
canonicalizer counts re-derived unchanged; then the delegation lands alone and every
divergence is attributed to anchoring / backfill-recovery / husk / raising, with backfill
recovery the only accepted behavioural delta.

Included subtasks: T015 T016 T017 T018 T019 T020 T021

Implementation sketch: extract the leaf → re-point the seam's PRIMARY leg and the
resolver-internal callers → re-author the import-time content descriptor in the **same
commit** → prove neutrality → *only then* delegate the wrapper body → attribute divergences
and pin backfill recovery red-first → hand-verify the Class-C fixture.

Dependencies rationale: WP01 must land first. Re-pointing the 4 `resolution.py` callers off
the primitive drops the scanned count from 46 to 42, below the retired 44 floor — the
extraction alone would red a gate WP01 removes.
Risks: **`RecursionError` after delegation is the highest-priority stop** — it means the
extraction did not fully cover the PRIMARY leg. The Class-C module-wide fixture stubs four
resolver names *because* the PRIMARY leg calls them internally; re-pointing that leg makes
the stubs unreached, so the convergence harness may go **vacuously green** — hand-verify it
here rather than discovering it three WPs later.
Estimated prompt size: ~340 lines.

---

## Phase 3 — Route the call sites *(WP04 parallel with WP05–WP07)*

### WP04 — Route the topology-routed reads and close the two residuals

**Prompt**: [tasks/WP04-route-unpoliced-and-residuals.md](./tasks/WP04-route-unpoliced-and-residuals.md)
**Goal**: Route the 8 `resolve_feature_dir_for_mission` sites per their ledger verdicts, the
2 primary-primitive sites that live in the same two files, and **both**
`_run_documentation_wiring` reads.
**Priority**: P1 for the resolver (the one genuinely unguarded silent-wrong-read path); P2
for the residuals.
**ICs**: IC-03 (routing half), IC-07 · **Dependencies**: WP01, WP02
**Independent test**: a `migrate-fail-loud` site on a **husk** mission resolves the primary
anchor, not the husk; the closeout gate's clean scan is green with non-vacuity from its site
floor.

Included subtasks: T022 T023 T024 T025

Files: `agent_tasks_ports.py`, `cli/commands/decision.py`, `cli/commands/mission_type.py`,
`context/resolver.py`, `decisions/emit.py`, `lanes/recovery.py`, `widen/state.py`,
`cli/commands/agent/mission_setup_plan.py`.
Dependencies rationale: WP02 owns the classification this WP applies; WP01 taught the
fold-prescription gate the seam idiom (routing before that flags the newly-routed site) and
removed the `#2214` pin (so this WP's routing is what turns that gate green).
Risks: routing only **one** of the two documentation-wiring reads clears the pin while
leaving the defect — a green-gate honesty hole. `gap-analysis.md` has **no** artifact kind:
it anchors on the resolved directory and is recorded as an honest bound; do not invent a kind
for it (out of scope).
Estimated prompt size: ~250 lines.

### WP05 — Route the trio and green its gate

**Prompt**: [tasks/WP05-route-trio.md](./tasks/WP05-route-trio.md)
**Goal**: Route the 10 sites in the 4 trio rewrite targets, correct the 5 comments in those
files, and turn the trio gate green on WP01's positive assertion.
**Priority**: P1 — the trio-membership slice is the **non-negotiable** first slicing axis.
**ICs**: IC-05 (trio slice), IC-08 (acceptance + executor comments) · **Dependencies**: WP03
**Independent test**: no trio file imports either drained name; the trio gate's positive
assertion holds (it is no longer satisfiable by an empty set); every routed site resolves an
identical directory for a materialized mission.

Included subtasks: T026 T027 T028

Slicing rationale (**non-negotiable**): the trio gate asserts its blessed names are
*currently used* by 8 specific files, 4 of which are rewrite targets. A directory-based split
would scatter them across three WPs and the blessed-name shrink would only be safe after the
third landed. **One WP owns all 8 trio files.**
Files: `cli/commands/agent/workflow.py` (2), `workflow_cores.py`,
`cli/commands/agent/workflow_executor.py` (3 + 3 husk comments), `cli/commands/implement.py`
(4), `implement_cores.py`, `acceptance/__init__.py` (1 + 2 misleading comments),
`acceptance/summary_core.py`, `acceptance/gates_core.py`.
Risks: `acceptance/__init__.py`'s comment is *about* the call site being rewritten — correct
them together or the corrected comment describes code that has since moved.
Estimated prompt size: ~230 lines.

### WP06 — Route the agent-CLI and lifecycle shells

**Prompt**: [tasks/WP06-route-agent-cli-and-lifecycle.md](./tasks/WP06-route-agent-cli-and-lifecycle.md)
**Goal**: Route the 10 sites in the agent-CLI and lifecycle-shell cluster.
**Priority**: P1 · **ICs**: IC-05, IC-08 (`next_cmd.py` comment) · **Dependencies**: WP03
**Independent test**: each routed site resolves an identical directory for a materialized
mission; no PRIMARY-kind read begins raising on husk / empty / deleted-coord.

Included subtasks: T029 T030 T031

Files: `cli/commands/agent/mission_feature_resolution.py` (1),
`cli/commands/agent/mission_finalize.py` (1), `cli/commands/agent/tasks_move_task.py` (2),
`cli/commands/accept.py` (1), `cli/commands/next_cmd.py` (3 + 1 husk comment),
`merge/executor.py` (1), `retrospective/writer.py` (1).
Parallel opportunities: fully parallel with WP05 and WP07 (disjoint files).
Risks: **`retrospective/writer.py:85` is a FOUNDATION site — do not route it.** `read_dir`
short-circuits `RETROSPECTIVE` to `resolve_retrospective_home`, so that site sits *beneath* the
seam and routing it is genuine infinite recursion. WP03 re-points it at the leaf; WP06 verifies
only. (An earlier version of this line told WP06 to "route through `resolve_retrospective_home`" —
self-recursive nonsense, since the site is *inside* that function. Corrected after WP03's review.)
Estimated prompt size: ~215 lines.

### WP07 — Route the runtime bridge and `status/aggregate.py`; record the foundation sites

**Prompt**: [tasks/WP07-route-runtime-and-status.md](./tasks/WP07-route-runtime-and-status.md)
**Goal**: Route the runtime-bridge cluster, the hardest module in the mission
(`status/aggregate.py` — the one non-compliant site, the `.name` divergence shape, and the
four-site qualname), and `commit_router.py`; then record the four foundation sites by name,
**unrouted**.
**Priority**: P1 · **ICs**: IC-05, IC-01 (the `:522` half), IC-08 (2 husk comments)
**Dependencies**: WP03
**Independent test**: `status/aggregate.py:522` no longer passes by omission; `:543`'s
`.name`-derived handle cannot silently return a non-existent path on a backfilled mission;
the four foundation sites are recorded with their recursion rationale and a census confirms
they remain unrouted, with no cycle in the `read_dir` call graph.

Included subtasks: T032 T033 T034

Files: `runtime/next/runtime_bridge.py` (2 + 1 comment),
`runtime/next/runtime_bridge_identity.py` (1 + 1 comment), `status/aggregate.py` (4),
`coordination/commit_router.py` (1); **recorded, not routed**: `core/paths.py` (2),
`core/git_ops.py` (1), `coordination/surface_resolver.py` (1).
Risks: **routing a foundation site risks a resolution cycle** — `core/paths.py:727` feeds the
write-side composition root (NFR-009). `status/aggregate.py::_find_meta_path` carries **four**
censused sites in one qualname: it is the acceptance fixture for WP02's index discriminator,
so coordinate the spelling rather than inventing one.
Estimated prompt size: ~250 lines.

---

## Phase 4 — Make the invariant structural

### WP08 — Delete the public wrapper; drain and privatise the canonicalizer

**Prompt**: [tasks/WP08-delete-wrapper-and-drain.md](./tasks/WP08-delete-wrapper-and-drain.md)
**Goal**: Delete the public `primary_feature_dir_for_mission` wrapper, drain and privatise
`_canonicalize_primary_read_handle`, and turn the read-side census green for both newly
censused callees — making the invariant **structural** rather than counted.
**Priority**: P1 — the mission's structural finish.
**ICs**: IC-05 (finish) · **Dependencies**: WP04, WP05, WP06, WP07
**Independent test**: the public name **no longer exists** and cannot be re-imported; the
private assembler has only in-module and named-sanctioned callers; the read-side census is
green for both new callees with per-primitive non-vacuity intact.

Included subtasks: T035 T036 T037 T038 T039

Pre-authorised out-of-map edit: `src/specify_cli/missions/_read_path_resolver.py` is WP03's
owned file. WP08 deletes the wrapper and edits `__all__` there — record the one-line
rationale in the commit body (the no-overlap rule is the real guard; see tasks.md §6).
Risks: `_canonicalize_primary_read_handle` has **38 call sites / 22 files** — every routed
site drains it too because the seam canonicalizes internally, but confirm the count by census
rather than trusting this number. The `agent/tasks.py` re-export exists **only** to serve a
test patch seam: **delete it and rewrite the two tests against the real seam** — preserving
it to keep tests green is exactly the scaffold-not-friction failure `DIRECTIVE_041` names.
**Do not run the rekey script** on the second census inventory — it is not round-trip-safe
(#3011); hand-edit `inventory.md`.
Estimated prompt size: ~290 lines.

---

## Phase 5 — Write the layering down once

### WP09 — Document the placement seam and disambiguate "routing"

**Prompt**: [tasks/WP09-document-the-seam.md](./tasks/WP09-document-the-seam.md)
**Goal**: Write one explanation page that states what "routing" means in the placement
sense and formalises the layering **as landed**, narrow the competing page in the same
slice, and add the `Routing` disambiguation — so the next mission cites a design document
instead of re-running a multi-round audit.
**Priority**: P1 — the durable deliverable. This discovery cost has now been paid three
times.
**ICs**: IC-09 · **Dependencies**: WP02, WP08
**Independent test**: a reader who has not followed this programme can state (a) what
routing means here and how it differs from branch-target routing, (b) which layer decides
placement, (c) why a canonical handle is not compliance.

Included subtasks: T040 T041 T042 T043 T044

Dependencies rationale: the page must document the layering **as landed**, not as intended —
so it is authored after the classification (WP02) and the structural finish (WP08).
Risks: this WP's failure mode is **becoming the fifth authority it exists to replace**. The
mitigations are requirements, not advice: explanatory only (link to the two ADRs for
normative rules), a `module:symbol` citation on every code-shape claim, the competing page
narrowed in the same slice, and the byte-frozen glossary pack + seed **untouched**. The layer
model must be the **verified** one — an earlier draft misdescribed it in two load-bearing
ways, and publishing that would have taught the very misappropriation the page prevents.
Estimated prompt size: ~300 lines.

---

## Dependency graph and parallelisation

```text
WP01 (suite → destination) ─┐
                            ├─> WP03 (extract → delegate) ─┬─> WP04 (unpoliced + residuals) ─┐
WP02 (grammar + census) ────┘                              ├─> WP05 (trio) ──────────────────┤
                                                           ├─> WP06 (agent-CLI) ─────────────┤
                                                           └─> WP07 (runtime + status) ──────┤
                                                                                             │
                                          WP08 (delete wrapper + drain canonicalizer) <──────┘
                                                              │
                                                              └─> WP09 (docs)
```

- **Phase 1 is fully parallel**: WP01 ‖ WP02 (disjoint files, no edges).
- **Widest parallel front**: WP04 ‖ WP05 ‖ WP06 ‖ WP07 — four routing clusters, disjoint files.
- **Critical path**: {WP01|WP02} → WP03 → {WP04|WP05|WP06|WP07} → WP08 → WP09 (5 deep).

**Why every routing WP depends on both WP02 and WP03.** WP02 is not optional context: each
routing WP is told to *apply* the ledger's per-site verdicts and never to re-derive them, and
those rows do not exist until WP02 lands. WP03 is the C-005 Step-1 gate: routing any call site
before the delegation is verified destroys the equivalence evidence the delegation exists to
produce. Accepted cost: this serialises the routing front behind Phase 1, and WP04's residuals
half waits on WP03 it does not strictly need — a scheduling cost, not a correctness one, and the
alternative (splitting WP04) buys earlier #2886 closure at the price of another WP boundary.

## MVP scope

**WP01 + WP02** are the minimum viable slice, and they are worth landing even if the mission
were cut short: WP01 leaves the suite stating the correct design (a durable specification
of the target), and WP02 closes the one genuinely unpoliced silent-wrong-read path and makes
the ledger multi-primitive-safe. Neither depends on the migration completing.

## Tracker rows for the issue matrix

| Issue | Action | Owning WP |
|---|---|---|
| #2886 | **Closes** | WP04 |
| #3014 | **Close with the corrected finding** (the issue that manufactured this mission) | WP02 |
| #2465 | **Partial** — no closing keyword; comment progress, or scope-check whether WP05 can consolidate all four resolvers in that file | WP05 |
| #2707 | **Verify first** — may already be fixed and stale; if live it is one more read in WP04's own file | WP04 |
| #3011 | Reference as a hazard — **do not run the rekey script** | WP08 |
| #2653 | Cross-reference only — shares the Terminology Canon surface | WP09 |

## Requirement coverage

| WP | Requirements |
|---|---|
| WP01 | FR-023, FR-001, FR-007, FR-014, FR-016, FR-024, NFR-004, NFR-005, NFR-007 |
| WP02 | FR-008, FR-009, FR-010, FR-012, FR-016, FR-017, FR-024, NFR-004, NFR-006, NFR-008 |
| WP03 | FR-002, FR-003, FR-021, FR-024, NFR-001, NFR-002, NFR-003, NFR-009 |
| WP04 | FR-004, FR-011, FR-013, FR-015, FR-024, NFR-001, NFR-002 |
| WP05 | FR-004, FR-015, FR-024, NFR-001, NFR-002 |
| WP06 | FR-004, FR-015, FR-024, NFR-001, NFR-002 |
| WP07 | FR-001, FR-004, FR-005, FR-015, FR-024, NFR-001, NFR-009 |
| WP08 | FR-006, FR-022, FR-024, NFR-004, NFR-007 |
| WP09 | FR-018, FR-019, FR-020, FR-024, NFR-010, NFR-011 |

All 24 functional requirements are mapped. FR-024 is on every WP because SC-021 requires
each WP body to carry its governing doctrine as resolvable citations.
