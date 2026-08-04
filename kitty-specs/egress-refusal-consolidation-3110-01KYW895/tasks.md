# Tasks — One Wrapper, One Shape: Project Egress Refusal Consolidation (`#3110` / `#3111` / `#3109`)

**Mission**: `egress-refusal-consolidation-3110-01KYW895`
**Planning/base branch**: `pr/egress-refusal-consolidation-3110` · **Merge target**: `pr/egress-refusal-consolidation-3110`
**Spec**: [spec.md](./spec.md) (**ACCEPTED**) · **Plan**: [plan.md](./plan.md) (**ACCEPTED**) · **Squad**: [tracer-squad-findings.md](./tracer-squad-findings.md)

---

## Read this before opening any WP file

1. **The spec has exactly three operative blocks** — *Edge Cases*, *Success Criteria*, and the
   *Requirement → Success Criterion coverage* table. Read them; the Requirements/NFR/Constraints
   tables and *Falsifiers and preconditions* are the **justification record**, not instructions.
   The spec says this itself in `## How to use this document`. **These work packages cite
   `SC-###` / `FR-###` and deliberately do not restate them.**
2. **`plan.md` §Verification Strategy is binding on every work package** — the 15 standing
   measurement rules, the five rot-modes, the mutation suite MUT-1…MUT-6, and the red-first proof
   for `#3111`. Each WP below quotes the rules that bite it; none of them repeals any.
3. **`[ratchet]` criteria do not discriminate.** SC-004 clauses 1–2, SC-010, SC-021 and NFR-004's
   five pins are all true at `bb2020fea`. Report them **per clause**; never as one verdict (R13).

## Standing rules, restated once (plan §Verification Strategy — the ones every WP trips)

- **Rule 1** — never pipe a suite whose exit status you intend to trust. Write full output to a
  file, read the file, **quote the `N passed` line**. An empty output file is no measurement.
- **Rule 5** — print the **input count** alongside any "all checks passed". A gate over zero files
  passes vacuously; that already happened once on this surface during `#3030`.
- **Rule 10** — control your diagnostic: run every probe against a known answer **first**, and make
  the control discriminate the error mode you actually have.
- **Rule 11** — **mutations are pytest plugins injected via `PYTHONPATH`, never source edits.** No
  source edits during a verification run, ever.
- **Rule 15** — **every mutation plugin must fail loudly when its target is absent.** A silently
  absent target gives "mutant survived", which is a false finding about the code.
- **Rule 12** — only 3.14 is installed locally; CI runs 3.11/3.12. `uv venv --python 3.11` is
  mandatory for SC-014.
- **Rule 13** — **never run `ruff format`** (not clean at line-length 164). `ruff check` only.
- **Rule 14** — **explicit-path staging only. Never `git add -A`.** Do not commit `kitty-specs/`
  from a lane branch.
- **Environment** — `pytest` from the clone root is safe (`pytest.ini` sets `pythonpath = src`).
  **Every other python invocation must set `PYTHONPATH=/home/jeroennouws/dev/sk-missions/3110/src`**,
  or imports silently resolve to a different, concurrently-edited checkout.
- **Fixed collection cost is ~69 s per pytest invocation.** Budget accordingly; do not "just run
  the suite".

## Pre-existing reds — never scope a WP to fix these

`tests/architectural/test_tid251_enforcement.py` (4 tests) ·
`test_charter_package_exports::test_charter_package_cold_import_keeps_status_orchestration_out` ·
two `test_safe_commit_cmd::…_3033` ·
`test_charter_io::test_get_mission_id_returns_none_when_meta_json_malformed` ·
`test_doctor_ops::test_sweep_nfr_002_10k_files_under_5s` (wall-clock) ·
`ModuleNotFoundError: No module named 'typer'` in subprocess daemon tests (environmental).
Also on **this** surface: running `tests/specify_cli/invocation/test_propagator_consent_gate_3030.py`
before `tests/specify_cli/saas_client/test_client_consent_gate_3030.py` in one process fails with
*"no hosted-sync consent resolver is registered"* — a fixture-teardown ordering artefact,
deterministic in alphabetical order. **On a consent mission that failure text reads exactly like the
defect under repair. Do not chase it.**

**NOT on this list — and it is the one you will meet first.**
`tests/specify_cli/cli/commands/test_decision_widen_subcommand.py` is **green today** (measured
isolated: **`28 passed in 56.40s`**, 28 items, 1 file) and **WP04/T027 reds it, twice over**: its
`DECISION_ID = "01KWIDETEST00000000001"` fixture (`:45`) is **22 characters and contains an `I`**, so
it fails **all three** existing ULID regexes, and its nine `patch(… SaasClient.from_env …)`
live-path tests run against a bare `tmp_path` that owns **no ledger**, so they hit the new ownership
refusal before `from_env`. **Those reds are WP04's to fix, by correcting the fixtures — see
T027 (b).** The two cheapest exits — relaxing the ULID check, or making ownership permissive when the
acting root has no `kitty-specs/` — are **forbidden repairs** (the second is the fall-through this
mission exists to close, under another name). The file is now in **WP04's `owned_files`**, in
**lane-c's `write_scope`**, and in **WP07/T038's isolated-run list**.

## Bundle A (`#3115`, `#3113`) is OPEN — this mission halts at design for it

Neither issue is fixed here. Every WP carries a **Bundle A bite** section saying which of its greens
are conditional, so the successor who lands Bundle A can tell which evidence to re-take:

| Issue | State | What it costs this mission |
|---|---|---|
| `#3115` shard-parallel isolation | **OPEN** | Full-suite reds on this surface are **not attributable**. NFR-005/SC-009's isolated per-file runs (WP07) are the compensation, and they are the only trustworthy green. |
| `#3113` egress-guard positional blind spot | **OPEN** | Bounds the **boundary** guard (`test_egress_consent_boundary.py`) only. It does **not** bound the attribution guards (R-12/D-10) — do not credit their coverage to it. Any green from the boundary guard on a moved sink (WP03) is **conditional on `#3113`**. |
| Global `pytest` timeout (FU-6) | **OPEN** (`pytest.ini:11` has no `--timeout`) | A hang consumes a run rather than failing it. Narrow scope; never raise a timeout to explain a kill (rule 2). |

---

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Hoist the **SaaS** attribution predicate to a module-level function; the live `rglob` scan calls it (PR-2) | WP01 | |
| T002 | Hoist the **tracker** attribution predicate to a module-level function; the live scan calls it (PR-2) | WP01 | |
| T003 | Behaviour-preservation evidence for T001/T002: identical live counts **plus the four synthetic witness shapes'** `(matched, attributed)` tuples before and after | WP01 | |
| T004 | Per-class non-vacuity floors as **named integers** — tracker 3, SaaS client 4 (SC-005 standing, SC-007) | WP01 | |
| T005 | SC-012 — per class, a form the guard **rejects**, asserted against a synthetic sample **through the extracted predicate** | WP01 | |
| T006 | SC-013 — per class, a **MATCH** on a shape no `src/` site uses; **no non-match anywhere** | WP01 | |
| T007 | MUT-4 / MUT-5 / MUT-6 plugin evidence, with the counter-intuitive controls | WP01 | |
| T008 | SC-005 `[one-off]` — remove one site of each class in a **throwaway worktree**, quote the two reds | WP01 | |
| T009 | Observe SC-006's static assertion **RED at baseline** before touching the workflow (red-first) | WP02 | |
| T010 | FR-017 shape (i): add `needs.changes.outputs.cli == 'true'` to `fast-tests-core-misc`'s if-gate | WP02 | |
| T011 | Add `'src/specify_cli/egress.py'` to the **`sync`** dorny filter group — **pairs with T012** | WP02 | |
| T012 | Add `'src/specify_cli/egress.py'` to the **`core_misc`** dorny filter group — **pairs with T011** | WP02 | |
| T013 | Add `'src/specify_cli/tracker/**'` to the **`sync`** filter group (PR-B; routes SC-021's ratchets to the file they protect) | WP02 | |
| T014 | SC-006 `[standing]` assertion through `_gate_coverage`'s `filter_groups` / `job_gating_groups` / `active_job_keys` | WP02 | |
| T015 | Write the SC-006 `[one-off]` **confound** into the PR body; register the post-merge observation | WP02 | |
| T016 | Create `src/specify_cli/egress.py` — template, four verdict branches, `UNDETERMINED_PROJECT_REFUSAL`, per-caller fragment **as an argument** | WP03 | |
| T017 | Delete both `*/egress_consent.py`; rebind `client.py:23` and `tracker/saas_client.py:34` | WP03 | |
| T018 | PB-5 carry-through — **five** pointers: two in-test imports, four test-side prose pointers, the **src-side** `saas_client/__init__.py:17` | WP03 | |
| T019 | Relocate FR-026's enumeration into `egress.py`, **rewriting** its cross-references (SC-022's anchor moves); **T019 (b)** — relocate the **tracker** file's precondition statement and **three-site enumeration** (219 lines with no destination, and FR-012's only written rationale) | WP03 | |
| T020 | SC-004 clause 3 — two `is` comparisons between **independently imported** names; **the baseline red is a `ModuleNotFoundError` and is NOT the discriminating red** — take that from MUT-2 | WP03 | |
| T021 | SC-015 — **both halves**: the standing definition-site scan (**not** a file-absence check) **and** the `[one-off]` second-definition demonstration | WP03 | |
| T022 | SC-016 `DENIED` content pins in **both** test trees + NFR-004's five per-branch pins, **added alongside** the four existing assertions | WP03 | |
| T023 | `"specify_cli.egress"` into `INTEGRATION_PREFIXES` + the **SC-025** assertion that reds if the line is removed | WP03 | |
| T024 | MUT-1 / MUT-2 plugin evidence, **patching all three names**, per-site split reported | WP03 | |
| T025 | Red-first: observe the pre-fix request carrying **B's `decision_id`** to A's team; quote the captured line | WP04 | |
| T026 | `src/specify_cli/decisions/ownership.py` — `resolve_decision_ownership`, explicit `except OSError`, never a bare bool | WP04 | |
| T027 | Wire `cmd_widen` to refuse before `SaasClient.from_env` (`decision.py:558`); FR-005 ULID check reusing an existing regex; `--dry-run` **warns**. **T027 (b)** — repair the pre-existing green `tests/specify_cli/cli/commands/test_decision_widen_subcommand.py`, which **both** changes red; the two cheapest exits are **forbidden repairs** | WP04 | |
| T028 | The acceptance module at the fixed home — `SPECIFY_REPO_ROOT`, **imported** `transmitted_text`, in-file positive control, `client._project_root == A_ROOT` | WP04 | |
| T029 | SC-002 **must-not-veto** case: unreadable ledger under X + positive hit under Y ⇒ the normal single request | WP04 | |
| T030 | SC-014 `[standing]` unreadable-ledger test — chmod the **`decisions/` directory** to `0o000`; asserts `resolve_decision_ownership`'s **outcome**; also SC-002 clause (c)'s **refuse** half | WP04 | |
| T031 | SC-018 — FR-021 discharge **(ii)**: enumeration equality, `.resolve()` before membership, one-level glob depth pinned | WP04 | |
| T032 | MUT-3 plugin evidence, with **both** SC-002 controls green | WP04 | |
| T033 | FR-018 — hand-edit `register_saas_client_factory`'s docstring; **do not touch `adapters.py:113`** | WP05 | Y |
| T034 | FR-019 — pin the **export half only**; quote the red from actually removing `__init__.py:21` / `:111` | WP05 | Y |
| T035 | FR-022 — the one-page ADR naming the boundary, the **provenance invariant**, and that the guard is **syntactic**; name the `freshen_adr_inventory.py` step (`docs/adr/3.x/README.md:9-10`) and **hand the ADR's filename to WP07** — WP06 lands **deliberately lockfile-dirty** | WP06 | |
| T036 | FR-023 — define "engagement" in `docs/context/`; run the terminology guard before pushing prose | WP06 | |
| T037 | NFR-006 / SC-014 `[one-off]` — the `uv venv --python 3.11` run, **including** T030's test; quote `N passed` verbatim | WP07 | |
| T038 | NFR-005 / SC-009 — isolated single-file runs, **with the count and the file list stated**; the list **includes the changed pre-existing `tests/specify_cli/cli/commands/test_decision_widen_subcommand.py`** | WP07 | |
| T039 | Seed and fill **`docs/plans/engineering-notes/01KYW895-verification-evidence.md`** with **`doc_status` + `updated`** frontmatter (WP07's owned deliverable — not a `kitty-specs/` dossier edit); consolidate every WP's friction entries; record the Bundle A conditionality of each green; **reconcile the docs lockfile and the ADR index for both new pages** | WP07 | |

---

## Work Packages

### WP01 — Attribution guard hardening + predicate extraction · [WP01-attribution-guard-hardening.md](./tasks/WP01-attribution-guard-hardening.md)
- **Goal**: make both guards non-vacuous **per transport class**, and make their predicates
  *callable objects* so a synthetic assertion and the live scan exercise the same code (PR-2).
- **Discharges**: **SC-005**, **SC-007**, **SC-012**, **SC-013**. Requirements: FR-014, FR-015,
  FR-016, NFR-003, C-002.
- **Deps**: none. **Blocks WP03.** · Subtasks T001–T008 · P2, must land first.

### WP02 — CI routing: FR-017 + the three glob lines · [WP02-ci-routing.md](./tasks/WP02-ci-routing.md)
- **Goal**: make the guard covering this mission's own construction-site edit run on a `cli`-only
  diff, and make an `egress.py`-confined diff route to **both** `fast-tests-sync` and
  `fast-tests-core-misc`.
- **Discharges**: **SC-006** (`[standing]` half in mission; the `[one-off]` half is **necessarily
  post-merge** — PA-2/PR-A). Requirements: FR-017.
- **Deps**: none. **Blocks WP04.** · Subtasks T009–T015 · P1 enabler.
- **Reallocation from the plan, deliberate**: the plan lists the two `egress.py` glob lines as
  IC-03 tasks 2 and 3. They are moved here so **one WP owns `ci-quality.yml`** (lane write-scope) and
  so the "are there **two**?" review question is asked in one place. The globs are inert until WP03
  creates the file; that is harmless and is stated in the WP.

### WP03 — Wrapper consolidation into `src/specify_cli/egress.py` · [WP03-wrapper-consolidation.md](./tasks/WP03-wrapper-consolidation.md)
- **Goal**: one editable presentation of the refusal policy in a **plain module** owned by neither
  transport; both `*/egress_consent.py` **deleted**.
- **Discharges**: **SC-004** (report per clause; only clause 3 reds), **SC-010**, **SC-015**,
  **SC-016**, **SC-021**, **SC-022**, **SC-025**. Requirements: FR-008…FR-013, FR-024, FR-026,
  FR-027, NFR-004; C-001, C-003, C-004, C-005.
- **Deps**: **WP01** (guards hardened first — US3). · Subtasks T016–T024 · P2.

### WP04 — Ownership before egress (`#3111`) · [WP04-ownership-before-egress.md](./tasks/WP04-ownership-before-egress.md)
- **Goal**: establish from local files under the acting root only that the checkout owns the
  decision, **before any URL is built**; refuse otherwise. The only live defect in the bundle.
- **Discharges**: **SC-001**, **SC-002**, **SC-003**, **SC-011**, **SC-014** (`[standing]` half — the
  unreadable-ledger test), **SC-018**, **SC-024**. Requirements: FR-001…FR-007, FR-020, FR-021,
  NFR-002; C-007, C-008, C-009, C-010.
- **Deps**: **WP02**. · Subtasks T025–T032 · **P1 — highest rigour**.
- **Indivisible**: FR-003 must never land without FR-001+FR-002 (D-9), **and `cli/commands/decision.py`
  must not be split away from `decisions/ownership.py`** — the non-`cli` path in the diff is what
  routes the SaaS guard onto it (ordering 2, as restated by PA-3).

### WP05 — The `#3109` seam: keep and pin · [WP05-3109-seam.md](./tasks/WP05-3109-seam.md)
- **Goal**: make the empty `register_saas_client_factory` seam read as a decision, not an oversight.
- **Discharges**: **SC-008**, **SC-023**. Requirements: FR-018, FR-019.
- **Deps**: none — fully independent, may run any time. · Subtasks T033–T034 · P3.

### WP06 — Durable record: ADR + glossary · [WP06-adr-and-glossary.md](./tasks/WP06-adr-and-glossary.md)
- **Goal**: put the egress-consent boundary in the charter authority path. The only item in the
  bundle acting on **recurrence** rather than on an instance.
- **Discharges**: **SC-019**, **SC-020** — *both are grep-gates; presence is mechanical, content is a
  PR-review item.* Requirements: FR-022, FR-023.
- **Deps**: **WP03**, **WP04** (the ADR names the wrapper's home and states the provenance invariant
  WP04 implements). · Subtasks T035–T036 · P2.
- **Lands deliberately lockfile-dirty.** `docs/development/3-2-page-inventory.yaml` is a 1:1 lockfile
  over every `docs/**/*.md` and every drift row is a blocking `error`. WP06 adds a page and edits two;
  **WP07 owns the lockfile and `docs/adr/3.x/README.md` and reconciles both new pages.** Two lanes
  cannot own one lockfile. WP06 must hand **the ADR's exact filename** to WP07 in its PR body.

### WP07 — Cross-cutting verification evidence · [WP07-verification-evidence.md](./tasks/WP07-verification-evidence.md)
- **Goal**: produce the evidence NFR-005/NFR-006 require, **in the stated form**, and record which
  greens are conditional on Bundle A.
- **Discharges**: **SC-009**, **SC-014** (`[one-off]` half — the 3.11 run). Requirements: NFR-004
  (per-clause reporting discipline), NFR-005, NFR-006.
- **Deps**: **all**. · Subtasks T037–T039 · P2. `execution_mode: planning_artifact`.
- **Deliverable path** — `docs/plans/engineering-notes/01KYW895-verification-evidence.md`, **with
  `doc_status` and `updated` frontmatter**. Not `docs/01KYW895-closeout/`: a new top-level docs
  directory fails `point_in_time_placement` and the frontmatter contract in
  `common-docs.styleguide.yaml` (`:114-119`, `:137-141`, `:144-146`, `:150-159`), and the repo's own
  precedent is `docs/plans/engineering-notes/883-*.md`.
- **Also owns the shared docs surfaces it reconciles**: `docs/development/3-2-page-inventory.yaml`
  and `docs/adr/3.x/README.md`. It is last and depends on WP06, which is why it is the reconciler.

---

## Dependency graph

```
WP01 (guards, must land first) ───────────┐
                                          ├──▶ WP03 (consolidation) ──┐
WP02 (CI routing) ──▶ WP04 (#3111, P1) ───────────────────────────────┴──▶ WP06 (ADR + glossary)

WP05 (#3109 seam) — no deps, any time

                                   WP01…WP06 ──▶ WP07 (evidence)
```

**The four load-bearing orderings, and what each is actually protecting** (plan §Sequencing):

1. **WP01 before WP03.** The guards are what make the consolidation safe to attempt (US3). Move the
   wrapper first and the only protection against F-A3's halving mechanisms is a global
   `assert scanned` that stays positive from the surviving class.
2. **The PR carrying the `decision.py:558` edit must either include a non-`cli` path or postdate
   WP02.** *(PA-3's restatement — read it, because the naive form is wrong for this mission's own
   diff.)* A `cli/**`-only PR selects `fast-tests-cli`, which runs only `tests/cli/` and
   `tests/specify_cli/cli/`, and `fast-tests-core-misc`'s if-gate does **not** list `cli` — so the
   SaaS attribution guard does not run, and `decision.py:558` is one of its four sites. **But WP04
   also creates `src/specify_cli/decisions/ownership.py`, and `src/specify_cli/decisions/**` is in
   the `closeout` group, which *is* in `fast-tests-core-misc`'s gate list** — so the guard runs on
   WP04's diff regardless of WP02. Keep WP02 first (it is free and closes the general hole FR-017
   names), but **do not report "WP02 landed first" as the reason the guard ran on WP04.** It is not.
   A WP that split `decision.py` away from `ownership.py` would satisfy the stated ordering while
   breaking the real invariant — which is why WP04 is indivisible.
3. **FR-003 never lands without FR-001 + FR-002.** In isolation FR-003 *widens* the disclosure
   surface: it makes an operator-typed slug affect the live path for the first time (today it is
   inert — `decision.py:550`, dry-run only). One work package, never separable (D-9).
4. **Q2 resolved before `egress.py` is created — DISCHARGED, not pending.** The operator resolved Q2
   (per-caller fragment passed as an **argument**), so falsifier **F2 does not fire** and the module
   may be created. It stays a **standing** property of the module: if a future edit makes the shared
   module import a transport-specific list **from `saas_client/` or `tracker/`** at module scope, F2
   fires retroactively and the answer becomes Q1 option (e). An edge to a **non-transport** package
   such as `specify_cli.decisions` is **not** F2's antecedent (measured, PA-5).

**Lane note.** WP03 overlaps WP01 on the two guard test files, and WP07 overlaps WP01–WP06 by
construction. Both overlaps lie along directed dependency edges, so
`validate_no_overlap` exempts them (same-lane sequential) — see
`src/specify_cli/ownership/validation.py:198-207`. **WP02/WP04 and WP01/WP03 own disjoint literal
paths**; do not widen any `owned_files` entry to a directory glob, or the exemption stops applying.

**Three write-scope additions were made after the post-tasks review; they are deliberate:**

| Path | Lane / WP | Why |
|---|---|---|
| `tests/specify_cli/cli/commands/test_decision_widen_subcommand.py` | **lane-c / WP04** | A pre-existing green module **both** of T027's changes red. It was in no lane's write scope, so a cold implementer would have met ~24 reds in a file they were forbidden to touch — and the two cheapest exits were both forbidden repairs. |
| `docs/development/3-2-page-inventory.yaml` | **lane-planning / WP07** | A 1:1 docs lockfile whose every drift row is a blocking `error`. WP06 and WP07 each add a page; **two lanes cannot own one lockfile**, so it goes to the one that is last. |
| `docs/adr/3.x/README.md` | **lane-planning / WP07** | Same regeneration step (`freshen_adr_inventory.py` writes the lockfile row **and** this file's index row). Splitting them across lanes would guarantee a conflict. |

**One cross-lane dependency is deliberately NOT expressed as a graph edge.** WP04/T028 **imports**
`transmitted_text` from `tests/specify_cli/saas_client/test_client_consent_gate_3030.py:73`, a
**lane-a** file that WP01 and WP03 both edit, while **lane-c depends only on lane-b**. The symbol
**already exists at the base commit**, so an edge would serialise the **P1** package behind the
consolidation for nothing. The protection is instead a **review-guidance line in WP01 and WP03**:
*"`transmitted_text` must remain an importable module-level symbol."* **Do not add the edge.**

---

## Success Criterion → Work Package coverage

Every criterion in the spec resolves to exactly one WP, except the two that carry a
`[standing]`/`[one-off]` split across an **authoring WP and the evidence WP**. **Both halves are
named; neither may be reported as discharging the other.**

> **Correction — the sentence above was false for SC-015, and the omission was the point.** An
> earlier draft claimed both halves were named "for every split criterion". **SC-015 is
> `[standing: the mechanism] + [one-off: the divergence demonstration]`, and only the standing half
> was mandated.** Both halves now live in **WP03/T021** — this is a split **inside one WP**, not
> across an authoring WP and the evidence WP, which is why the framing above missed it. It matters
> more than the others: **FR-008 — *exactly one editable presentation*, the mission's headline —
> maps to SC-015 alone, and no mutation in the suite targets it.** The other splits (SC-005, SC-006,
> SC-008, SC-014) are unaffected.

| SC | WP | Note |
|---|---|---|
| SC-001 | WP04 | Two divergence routes (`--mission-slug`, `SPECIFY_REPO_ROOT`), **not four**. Assert the **bytes** first; the count is corroboration. |
| SC-002 | WP04 | Same module, same fixture as SC-001. Carries the compatibility clause, the **must-not-veto** half (T029) and the **forbidden repair**. Its refuse half lives in T030. |
| SC-003 | WP04 | Asserted against the constructed request, never the response. |
| SC-004 | WP03 | **Per clause.** Clauses 1–2 `[ratchet]`; **clause 3** is the only clause that reds. |
| SC-005 | WP01 | `[standing]` named integers (T004) + `[one-off]` removal demonstration (T008). |
| SC-006 | WP02 | `[standing]` `_gate_coverage` assertion (T014). The `[one-off]` CI observation is **structurally unobtainable in-mission** and is declared post-merge (T015). |
| SC-007 | WP01 | Per-class scanned counts ≥ baseline and name-matched sites not increased. |
| SC-008 | WP05 | `[standing]` export pin + `[one-off]` removal demonstration. **Export half only.** |
| SC-009 | WP07 | Evidence must state the **count and the file list**. |
| SC-010 | WP03 | `[ratchet]` — the four `could not be determined` assertions pass **unmodified**. |
| SC-011 | WP04 | B's `decision_id` in **no** constructed request line, via the imported `transmitted_text`. |
| SC-012 | WP01 | Synthetic sample, **through the extracted predicate**. |
| SC-013 | WP01 | **Two per-class MATCH assertions. No non-match anywhere** (it would collide with FU-8). |
| SC-014 | **WP04** (`[standing]` test) + **WP07** (`[one-off]` 3.11 run) | The test asserts `resolve_decision_ownership`'s **outcome**, not `Path.exists()`'s return value. |
| SC-015 | WP03 | **Both halves, both in T021**: `[standing]` an AST/text scan asserting **exactly one definition site** — **never a file-absence check**, which passes forever and can never red on a second definition in a **new** file — plus `[one-off]` a synthetic second definition in a throwaway worktree with the red's assertion text quoted. **SC-015's own text (`spec.md:1450`) still names the package form `src/specify_cli/egress/`; superseded — read it as `egress.py`.** |
| SC-016 | WP03 | Content pins in **both** packages' trees, **added alongside** the existing four. |
| SC-018 | WP04 | Under FR-021 discharge **(ii)**: enumeration equality. |
| SC-019 | WP06 | Grep-gate. Content is a PR-review item — the reviewer must read the ADR. |
| SC-020 | WP06 | Grep-gate. Same honesty note. |
| SC-021 | WP03 | `[ratchet]` — **no new test.** The two existing tracker tests must keep passing. |
| SC-022 | WP03 | The anchor **moves** into `egress.py`; say so in the PR body. **Ungated prose — see the table below; nothing reds if the rewrite is skipped.** |
| SC-023 | WP05 | Asserts `adapters.py:113` is **unchanged**. |
| SC-024 | WP04 | In-file positive control + the compensating `client._project_root == A_ROOT` assertion. **SC-024's clause *"passes both roots explicitly rather than relying on a kwarg default"* (`spec.md:1553`) is SUPERSEDED** — it is not executable under C-008's real invocation (`cmd_widen` builds the client; there is no kwarg for the test to pass) and "restoring" it means constructing a client inline, dropping the real entry point and the FR-003 slug route. Read it as **`SPECIFY_REPO_ROOT`**; the spec carries a POST-ACCEPTANCE CORRECTION under SC-024 and WP04/T028 item 2 quotes the superseded clause. **WP04 is not non-compliant for omitting it.** |
| SC-025 | WP03 | Must compare the module name against the gate's **own** prefix list. |
| ~~SC-017~~ | — | **Retired.** Folded into SC-004 clause 3. Do not cite it. |

**No criterion is unclaimed, and no work package is without a criterion.** The obligations in this
mission that have **no gate at all** are called out below rather than hidden.

> **Correction — this paragraph used to say "the **one** obligation … with no criterion at all" and
> then list four rows.** It was wrong twice: the count did not match its own table, and the table was
> short. The list below is now **eight rows**, and it deliberately mixes two kinds of ungated thing —
> *"no success criterion exists"* and *"a criterion exists but nothing mechanical checks it"*. **Both
> are places where skipping the work produces no red**, which is the only property this table is
> about. If you add an obligation to this mission, add a row here or state why it is gated.

## Obligations with no gate — named, because nothing will notice

| Obligation | WP | Why it is ungated |
|---|---|---|
| `'src/specify_cli/egress.py'` in the **`sync`** filter group | WP02 (T011) | Nothing gates a dorny glob line. **`core_misc` without `sync` is the dangerous direction**: one group true ⇒ `unmatched=false` ⇒ `run_all` does not fire ⇒ `fast-tests-sync` does not run ⇒ `tests/sync/tracker/` runs **nowhere** (`core-misc` shard carries `--ignore=tests/sync`), silently dropping SC-021's two ratchets, SC-016's tracker-side pin and the tracker attribution guard. **In review the question is "are there two?", not "is there one?"** |
| `'src/specify_cli/egress.py'` in the **`core_misc`** filter group | WP02 (T012) | Same. `sync` alone loses the SaaS-side guard and the architectural shard. |
| `'src/specify_cli/tracker/**'` in the **`sync`** filter group | WP02 (T013) | **Has no success criterion at all.** SC-006 is scoped by D-4 to the `cli`-only diff shape. This line closes PR-B's pre-existing hole (`agent_surface` routes `tracker/**` to `core_misc` but not to `sync`), so SC-021's ratchets are routed to the file they protect (`tracker/saas_client.py:329`) rather than only to this mission's own diff shape. Also carried under FU-1. **If the operator wants it out of scope, strike T013 — do not leave it half-done.** |
| The SC-006 `[one-off]` CI observation | WP02 (T015) | **Structurally unobtainable from any PR carrying the fix**: `ci-quality.yml` is itself a `core_misc` glob member (`:263`), so `core_misc` goes true regardless of the diff. A `core_misc`-green run on the mission PR **is not evidence and looks exactly like proof.** Declared post-merge, routed through `post-merge-arch-gate-adjudication`. **T015 must file a tracker issue as its carrier** — a paragraph in a PR body that merges is not an owner, and the mission's evidence file closes before the observation can exist. |
| **SC-022** — the FR-026 enumeration rewrite | WP03 (T019) | **Ungated prose with no verification step.** SC-022 has no test, no grep and no mutation. Nothing reds if the enumeration is copied **verbatim** with the F-B2-falsified item 4 intact ("`decision_id` is a ULID rather than a slug"), and nothing reds if it is skipped. **Same honesty note SC-019/SC-020 carry: presence is not a reading — the reviewer must open the relocated text.** T019 (b) — the tracker file's precondition statement and three-site enumeration — is ungated on the same terms. |
| **SC-015's mechanism** — that it is *exercised*, not merely present | WP03 (T021) | SC-015 is the **only** criterion FR-008 maps to, and **no mutation targets it**. The `[standing]` half can be satisfied by a `.exists()` file-absence check that **passes forever** and can never red on a second definition in a **new** file. The `[one-off]` demonstration is what makes the mechanism non-vacuous, and **nothing but a reviewer will notice if it is skipped.** |
| **The four PB-5 prose pointers** | WP03 (T018) | `test_client_consent_gate_3030.py:313` and `:360`; `test_saas_client_consent_gate_3030.py:361` and `:402`. **Hand-corrected failure-message and docstring text — no gate reads prose.** A dangling pointer on a consent guard survives every green in this mission. `:402` is the sharp one: it points at `tracker/egress_consent.py` for *"the precondition and what falsifies it"*, and repointing it at `egress.py` **without T019 (b)** creates a dangling pointer rather than repairing one. |
| **FR-012** — the consent chain remains single | WP03 (T016 + T019 (b)) | **High-impact, `[ratchet]`, and `spec.md:1631` says "no SC needed, deliberately".** Nothing asserts that the shared wrapper keeps resolving through **`resolve_egress_consent`** and **never re-derives checkout→project→consent locally**. Worse, its **only written rationale in the repository** is `tracker/egress_consent.py:18-45` — **a file T017 deletes.** WP03 is the carrier: name `resolve_egress_consent` and *"never re-derive the chain locally"* in `egress.py`'s content, cite FR-012 by name, and relocate the C-003 argument. Skipping it leaves an ungated High-impact requirement with **nothing written down at all**. |

## Requirement → Work Package coverage

| Requirement | WP | Requirement | WP |
|---|---|---|---|
| FR-001 | WP04 | FR-015 | WP01 |
| FR-002 | WP04 | FR-016 | WP01 |
| FR-003 | WP04 | FR-017 | WP02 |
| FR-004 *(folded → FR-002)* | WP04 | FR-018 | WP05 |
| FR-005 | WP04 | FR-019 | WP05 |
| FR-006 | WP04 | FR-020 | WP04 |
| FR-007 *(folded → FR-002)* | WP04 | FR-021 | WP04 |
| FR-008 | WP03 | FR-022 | WP06 |
| FR-009 `[ratchet]` | WP03 | FR-023 | WP06 |
| FR-010 `[ratchet]` | WP03 | FR-024 | WP03 |
| FR-011 `[ratchet]` | WP03 | ~~FR-025~~ *(retired)* | WP03 — **frontmatter only** |
| FR-012 `[ratchet]` | WP03 | FR-026 | WP03 |
| FR-013 `[ratchet]` | WP03 | FR-027 `[ratchet]` | WP03 |
| FR-014 | WP01 | NFR-002 | WP04 |
| NFR-003 | WP01 | NFR-004 `[ratchet]` | WP03 (pins) + WP07 (per-clause reporting) |
| NFR-005 | WP07 | NFR-006 | WP07 |

**On `acceptance-matrix.json` — it is a STUB. Do not accept this mission against it.** The file in
this dossier is generator boilerplate: **27 rows, all `"pass_fail": "pending"`, all
`"notes": "TODO: replace with a real acceptance criterion"`, all
`"proof_type": "automated_test"`, keyed on `FR-###` only**. Three concrete defects follow from that:

1. It carries **retired `FR-025`** and the **folded `FR-004`/`FR-007`** as live rows, which the table
   above and the spec both dispose of. Verifying them as written would re-introduce exactly the
   vacuously-satisfiable conditional FR-025 was retired for.
2. It asserts `proof_type: "automated_test"` for **every** row — including **FR-022 and FR-023, which
   are grep-gates whose content is a PR-review item** (SC-019/SC-020's own honesty notes), and
   including the `[ratchet]` rows whose criteria **do not discriminate**.
3. It has **no `SC-###` rows at all**, so nothing in it carries the per-clause discipline NFR-004/R13
   require, and nothing in it distinguishes a `[standing]` half from its `[one-off]` half.

**⇒ The substitute is the `SC → WP` table above** (plus the ungated-obligations table and the
per-clause reporting rules in WP07). **`acceptance-matrix.json` is to be rewritten per clause at
accept time**, from those tables — not filled in row-by-row from its current keys.

**On FR-025.** The plan says *"do not cite FR-025 or SC-017 in a work package"* — because FR-025 was
a vacuously-satisfiable conditional over tests and handing it to an implementer as an instruction is
the defect it was retired for. It appears in **WP03's `requirement_refs` frontmatter only**, so the
finalize coverage gate (which harvests every `FR-###` literal in `spec.md`, retired ones included)
does not report it unmapped. **WP03's body cites SC-004 clause 3, never FR-025.** If the operator
would rather the gate flag it, delete the frontmatter entry — nothing in the body depends on it.

---

## Lanes and status

**Every work package is in lane `planned`.** No status events were emitted while authoring these
files; `status.events.jsonl` is the sole authority and it carries no transitions for WP01–WP07.
Advance with `spec-kitty agent tasks move-task <WPID> --to <lane>`, never by editing frontmatter.

## Reviewer ≠ implementer

Charter standing order 8. Every WP names its own review guidance; the review must be taken by a
different agent than the one that implemented it. **WP04 is P1 confidentiality work — highest
rigour, strongest model.**
