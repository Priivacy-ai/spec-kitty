---
work_package_id: WP08
title: The upgrade note, its index link, and the anchor check
dependencies:
- WP05
requirement_refs:
- C-011
- C-016
- FR-013
planning_base_branch: bundle-c-tracker-refusal-3108
merge_target_branch: bundle-c-tracker-refusal-3108
branch_strategy: Planning artifacts for this mission were generated on bundle-c-tracker-refusal-3108. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into bundle-c-tracker-refusal-3108 unless the human explicitly redirects the landing branch.
created_at: '2026-08-01T00:20:00+00:00'
subtasks:
- T043
- T044
- T045
- T046
phase: Stage 7 - The upgrade note
history:
- at: '2026-08-01T00:20:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: docs/migrations/
create_intent:
- docs/migrations/tracker-egress-refusal.md
- tests/docs/test_tracker_egress_upgrade_note_3108.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- docs/migrations/tracker-egress-*.md
- docs/migrations/index.md
- tests/docs/test_tracker_egress_upgrade_note_3108.py
role: implementer
tags: []
task_type: implement
tracker_refs:
- '3108'
---

# Work Package Prompt: WP08 – The upgrade note, its index link, and the anchor check

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and
behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`

---

## Objective

This Mission ships a **breaking change**: deny-on-absence of both channels means **every existing
`beads`/`fp` binding stops working on upgrade** unless its project records a decision at one of the
two channels.

> "This is not a footnote to US3 — it is US3's cost, and **a refusal an operator cannot act on is an
> outage**. The squad measured a state in which today's message tells the operator to do exactly what
> they just did."

Write the operator-facing upgrade note that carries all remediation paths, link it from
`docs/migrations/index.md`, and pin it with a CI anchor check that fails if the section is removed or
renamed.

## Owned files — a hard boundary

You may write **exactly three files**:

- `docs/migrations/tracker-egress-refusal.md` (**new** — the `docs/migrations/tracker-egress-*.md`
  slot)
- `docs/migrations/index.md`
- `tests/docs/test_tracker_egress_upgrade_note_3108.py` (**new**)

You may **not** edit any source file, any other test, or `CHANGELOG.md`.

**`CHANGELOG.md` is explicitly not yours.** From `plan.md` Stage 7 and IC-09:

> "**IC-09(a), the CHANGELOG Breaking Changes entry, is not here** — it lands in the same change as
> Stage 4, so the break never lands undocumented."

WP04 owns `CHANGELOG.md` and authored that entry. Your note is IC-09(b): "the **upgrade note, its
`index.md` link and the CI anchor check** follow **WP05**, because only then is the remaining
`HOSTED_SERVICE`-side limitation's exact shape fixed."

**One live agent per file.** If the CHANGELOG entry is missing or does not link your note, **report
it** — do not add it yourself.

## What you may assume is already true (dependencies)

WP08 depends on **WP05**, and transitively on WP01–WP04. Therefore:

- Both gates ship. The local path (`beads`/`fp`) refuses when neither channel permits; the hosted
  path narrows on the tracker key but is never granted by it.
- `CHANGELOG.md` already carries a **Breaking Changes** entry stating that local tracker providers now
  require a recorded decision at one of the two channels, landed with WP04.
- The acceptance suite `tests/sync/tracker/test_tracker_egress_refusal_3108.py` (WP01) already proves
  each remedy **by execution** — applying it to the refusing fixture, re-running, and asserting the
  sentinel title reaches the recorder (FR-018 H5, SC-004, SC-007).
- `sync doctor` renders the verdict on two destination rows (WP06), so an operator has a diagnostic
  surface to point at.

## Requirements this WP satisfies

**FR-013 — The breaking change is a deliverable, not a note.** Quoted from `spec.md`:

> "I want the upgrade cost carried in three places: (1) the refusal message, per FR-012; (2) a
> **Breaking Changes** entry in `CHANGELOG.md` stating that `beads`/`fp` bindings now require a
> recorded decision at one of the two channels and that absence of both denies; (3) **an upgrade note
> under `docs/migrations/`, linked from `docs/migrations/index.md`, giving all remediation paths —
> including the Channel-2 grant, which is the only one that works without a project identity —
> stating the remaining one-direction limitation at `HOSTED_SERVICE` (C-016, not C-014 — the earlier
> revision cited the wrong constraint here), and carrying one sentence on the `map list` split**,
> which will otherwise read as a bug: on the same refusing project, `spec-kitty tracker map list`
> succeeds while `spec-kitty tracker map list --provider jira` refuses, because the second crosses the
> hosted transport and the first does not — **the gate follows the destination, not the subcommand
> name**. Pinned by an anchor check that fails in CI if the section is removed or renamed — the
> `#3030` FR-018 pattern."

**C-016 — Separability, and the direction still not delivered.**

> "Delivered: **permit hosted sync, refuse tracker** (US1) and **refuse/never-record hosted sync,
> permit the local tracker** (US2). Not delivered: **a SaaS tracker binding without hosted-sync
> consent** — Channel 1 remains a hard prerequisite there by FR-004, because the destination is
> spec-kitty's hosted service. **Stated in the upgrade note (FR-013) as a decided limitation, not an
> oversight.**"

**Success criterion — SC-018:**

> "`CHANGELOG.md` carries a Breaking Changes entry and `docs/migrations/` carries the upgrade note,
> linked from `docs/migrations/index.md`; **the anchor check fails when the section is removed or
> renamed**."

---

## Measured hazards — carried verbatim, not summarised

### H-A. The breaking change needs an operator-facing remedy that *works*. One of them did not.

Measured, and it is why FR-012 grew a third Channel-1 state:

> "For a checkout with no `project.uuid`, `enable_checkout_sync` raises
> `ConsentIdentityUnresolvedError` (`routing.py:320-321`) and **hand-authoring `sync.enabled: true`
> still denies** — so the third Channel-1 state carries **`spec-kitty init`** as its remedy."

And from `spec.md` US6 sc3: *"Without this state the binding is permanently dead with actively wrong
advice: today's message tells the operator to do what they just did."*

**Remedies are proven by execution:** "apply each, re-run, assert the title now reaches the recorder."
Never by substring. That proof lives in WP01's acceptance suite (SC-004, SC-007). **Your note may
only claim a remedy the acceptance suite has proven by execution.** Cross-check each remedy sentence
against a passing executed-remedy test before you write it. If a remedy you were going to document has
no executed-remedy test behind it, **do not document it — report it.**

The three Channel-1 states and their remedies, from `data-model.md` §3:

| Channel-1 state | Meaning | Remedies |
|---|---|---|
| **no record** | Nothing was recorded for this project at any Channel-1 level. | Record `sync.enabled: true` in the project's own `.kittify/config.yaml`; **or** run `spec-kitty sync opt-in` for it; **or** record `tracker: {egress: permitted}` (needs no project identity). |
| **recorded refusal** | A Channel-1 refusal exists (e.g. committed `sync: {enabled: false}`). | Change the recorded decision; **or** record the Channel-2 grant. |
| **not consentable** | Project identity did not resolve (no `project.uuid`), so `enable_checkout_sync` raises `ConsentIdentityUnresolvedError` and hand-authoring `sync.enabled: true` **still denies**. | **`spec-kitty init`** (mints an identity, after which the "no record" remedies apply); **or** the Channel-2 grant, which needs no identity at all. |

**The Channel-2 grant is the only remedy that works without a project identity.** FR-013 requires the
note to say so.

### H-B. The `map list` split will read as inconsistent, and the note must pre-empt it.

From `spec.md` Edge Cases:

> "**`map list` is two commands wearing one name.** `map list` with no `--provider` goes to
> `_resolve_backend()` and, on a local binding, performs no egress — **ungated**. `map list
> --provider <saas>` goes to `_resolve_saas_backend_for_provider` (`service.py:210`) and crosses
> `_request`, so it **is** gated, at `HOSTED_SERVICE`, by the SaaS gate — with no change to
> `tracker.py:942-963` and no new gate site. The same holds for `issue-search --provider` and
> `list-tickets --provider`. This is a direct consequence of making the destination a parameter: **the
> gate placement follows the transport rather than the subcommand name.**"

**Both are correct.** On the same refusing project, `spec-kitty tracker map list` succeeds while
`spec-kitty tracker map list --provider jira` refuses. FR-013 requires **one sentence** on this,
because without it the split reads as a bug and someone will "fix" it.

### H-C. A typo fails closed, and the note must say what to type instead.

C-020: the closed value set means an operator typo — `tracker: {egress: refuse}` (singular),
`Refused`, `deny`, or a stray `true` — is a **fault, and a fault refuses**.

> "**This is intended, not a side effect**: on a confidentiality control the only safe reading of a
> value nobody defined is refusal, because the alternative is a mis-spelling that silently permits.
> The cost is that a typo can take a working local binding offline, and **the mitigation is the
> message, not a looser decode**."

The note must state the closed set (**exactly `refused` and `permitted`**, no case-folding, no
synonyms) and say that anything else refuses.

### H-D. Absence at the two channels means opposite things, and the note must not blur them.

- **Channel 1 (`sync.enabled`)**: absence **denies**.
- **Channel 2 (`tracker.egress`)**: absence — the key being missing — **records nothing** and defers
  to Channel 1.

From `spec.md` Key Entities: *"Two keys spelled alike that answer absence oppositely is a sharper trap
than two keys spelled differently."* Your prose must not present them as parallel switches.

Also: **a non-mapping `tracker:` block** (`tracker: "yes"`, `tracker: [a, b]`, `tracker: 3`,
`tracker:` null) is **absence, not a fault** — the block is not the key, and the key is missing. Say so
if you enumerate shapes; do not invent the natural guess.

### H-E. Terminology canon.

Canonical product term is **Mission**, never "feature". `tests/architectural/test_no_legacy_terminology.py`
enforces it and runs in a CI job that the fast suites do not cover, so a regression passes locally and
fails at CI. **Run it before pushing prose.**

---

## Standing rules — binding on every measurement you take

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
  status and buffers until exit. **Quote the `N passed` line.** An **empty output file is no
  measurement**.
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
- **Control your diagnostic** — run any probe against a case whose answer you already know before
  trusting it.
- **Mutations as pytest plugins via `PYTHONPATH`, never source edits**, and never source edits during
  a verification run.
- **Five recorded ways a mutation silently lies** — check each: (1) the architecture moved and the
  patched gate became a redundant second → all-green reads as "your pin is fine"; (2) the reds are
  `TypeError`s from a changed signature, not assertion failures; (3) the mutant hard-codes a value the
  tests **vary** → no-ops for exactly the tests most likely to catch the defect; (4) the branch is
  unreachable on the local interpreter and **live on CI's** (3.11/3.12 vs 3.14) → zero binds means
  *your environment differs*, not *the code is dead*; (5) **`from X import f` rebinds by value** →
  patching the defining module leaves the *deciding* module inert; patch every name a symbol is
  reachable by and report the per-site split.
- **Explicit-path staging.** `git add <paths>`, never `git add -A` — 13 files were lost to a stray
  `add -A` in this lineage.
- **`ruff format` is NOT clean on this repo** (`line-length = 164`); only `ruff check` is meaningful.
  New code must pass `ruff` and `mypy --strict` with no blanket suppressions.
- **One live agent per file.**
- **Known pre-existing failures — do not chase, do not fix in-PR, do not retry to green:**
  `tests/architectural/test_tid251_enforcement.py` (4 tests);
  `test_charter_package_exports::test_charter_package_cold_import_keeps_status_orchestration_out`;
  two `test_safe_commit_cmd::…_3033`;
  `test_charter_io::test_get_mission_id_returns_none_when_meta_json_malformed`;
  `test_doctor_ops::test_sweep_nfr_002_10k_files_under_5s` (wall-clock, fails under load).
  `ModuleNotFoundError: No module named 'typer'` in subprocess daemon tests is environmental.

---

## Subtasks, in execution order

### T043 — Author the upgrade note

Create `docs/migrations/tracker-egress-refusal.md`.

**Before writing a word of remedy prose**, verify each remedy against a **passing executed-remedy
test** in `tests/sync/tracker/test_tracker_egress_refusal_3108.py` (WP01's file — read it, never edit
it). Run it and quote the `N passed` line. **A remedy with no executed-remedy test behind it does not
go in the note.**

**Frontmatter** — match the house shape used by every page in `docs/migrations/` (see
`docs/migrations/index.md` and its siblings): `title`, `description`, `doc_status: active`, `updated`,
`related` (listing `docs/migrations/index.md` at minimum).

**Required content**, each item a named section with a **stable heading** (the anchor check in T045
pins the substance, not only the heading — see the `#3030` pattern):

1. **What changed and why it breaks you.** `beads` and `fp` bindings previously reached the tracker
   binary with **no consent question asked** — `src/specify_cli/tracker/local_service.py` held zero
   consent references. They now require a **recorded decision at one of two channels**, and **absence
   of both denies**. State plainly that an existing working binding will stop working until a decision
   is recorded.

2. **The two channels, and what absence means at each** (H-D):
   - **Channel 1 — hosted-sync egress consent.** Keyed on the project's identity. **Absence denies.**
   - **Channel 2 — `tracker.egress`**, a new key in the `tracker:` block of the **project's own
     committed `.kittify/config.yaml`**, holding **exactly one of two strings, `refused` or
     `permitted`**. **Absence is the key being missing, and records nothing** — it defers to Channel 1.
   - Show the YAML:

     ```yaml
     tracker:
       egress: permitted   # or: refused
     ```

3. **How to tell which channel is refusing you.** `spec-kitty sync doctor` prints a tracker-egress
   block in **every** checkout, with **one row per destination** — `LOCAL_SUBPROCESS` and
   `HOSTED_SERVICE` — and names the refusing channel on each row. This is the surface to check first.
   (`sync doctor` is used rather than a `tracker`-side command because the `spec-kitty tracker` group
   is **conditionally registered** and does not exist unless hosted SaaS sync is armed on the machine —
   it would be unreachable in exactly the configuration where an operator most needs it.)

4. **The three Channel-1 states and their remedies** — reproduce the table in H-A, in operator prose.
   For each state, give the exact command or the exact YAML. **Say explicitly that the Channel-2 grant
   is the only remedy that works without a project identity.**

5. **The identity-less checkout, called out on its own.** If `spec-kitty sync opt-in` fails and
   hand-authoring `sync.enabled: true` **still** denies, the checkout has no project identity. The
   remedy is **`spec-kitty init`** — or record `tracker: {egress: permitted}`, which needs no identity
   at all. Say this in plain words: it is the state where the old advice was actively wrong.

6. **What `permitted` does and does not do (C-016) — the remaining one-direction limitation.**
   - At the **local subprocess** destination (`beads`/`fp`), `permitted` is an **affirmative grant**
     that works **independently of hosted-sync consent**. You can keep a local tracker without opting
     the repository into spec-kitty's hosted SaaS.
   - At the **hosted service** destination (`jira`, `linear`, and anything reached with
     `--provider <saas>`), `permitted` **grants nothing**. It can only narrow. Hosted-sync consent
     remains a hard prerequisite there, because that path sends to **spec-kitty's own hosted service**
     — `/api/v1/tracker/…`, bearer token, `X-Team-Slug` — which holds the connector and relays.
   - **State this as a decided limitation, not an oversight**, and cite it as such: a SaaS tracker
     binding without hosted-sync consent is **not delivered by design**.

7. **The `map list` split — one sentence, per FR-013** (H-B). On the same refusing project,
   `spec-kitty tracker map list` succeeds while `spec-kitty tracker map list --provider jira` refuses,
   because the second crosses the hosted transport and the first does not: **the gate follows the
   destination, not the subcommand name.** The same holds for `issue-search --provider` and
   `list-tickets --provider`.

8. **A typo refuses (C-020, H-C).** The value set is closed: exactly `refused` and `permitted`. No
   case-folding, no synonyms, no `yes`/`on`/`1`/`true`. **Anything else present at the key is a fault,
   and a fault refuses at both destinations** — including `Refused`, `REFUSED`, `refuse`, `deny`, a
   number, a `null`, an empty string, a mapping or a list. This is intended: on a confidentiality
   control the only safe reading of a value nobody defined is refusal. The refusal message names the
   offending value verbatim and both legal values, and `sync doctor` renders the same wording.

9. **Which commands are gated and which are not.** `sync pull`, `sync push` and `sync run` are gated
   on the local path. `status`, `bind`, `unbind` and `map add` construct no connector, run no
   subprocess and reach no transport, so they are **not** gated — a refusing project keeps its
   local-only commands.

10. **A recorded decision outlives its binding.** `bind`, `rebind` and `unbind` preserve a committed
    `tracker.egress`. A recorded `permitted` survives an unbind exactly as a recorded `refused` does.

**Prose rules:** canonical term is **Mission**, never "feature" (H-E). Follow the existing
`docs/migrations/` voice — these are runbooks, not release notes.

**Exit for T043:** the note exists with all ten sections; every remedy in it is backed by a passing
executed-remedy test whose `N passed` line you have quoted.

---

### T044 — Link it from `docs/migrations/index.md`

1. Add the note to the `related:` list in the index frontmatter, in the existing alphabetical position
   (`docs/migrations/tracker-egress-refusal.md`).
2. Add a body link in the **Current 3.2 migrations** section, matching the surrounding entry style —
   a link plus a one-line description of *when an operator needs this page* ("your `beads`/`fp`
   tracker binding stopped working after upgrading").
3. Do **not** restructure the index, and do **not** touch any other entry.

**Exit for T044:** the index links the note from both the frontmatter `related:` list and the body;
`git diff docs/migrations/index.md` shows only additive lines.

---

### T045 — The anchor check, red first

Create `tests/docs/test_tracker_egress_upgrade_note_3108.py`.

**Follow the `#3030` FR-018 pattern already in this tree** —
`tests/docs/test_env_var_scope_warning.py`. Read it first. Its own docstring states the rule that
makes it work:

> "This test asserts on the ***substance*** (both variable names plus the phrase that carries the
> meaning), **not on a heading, because a heading anchor passes happily against an emptied
> section**."

That is the design constraint. A test that only checks a heading exists is the vacuity this WP is
supposed to prevent.

**Required assertions:**

1. The note file exists at its path, and `docs/migrations/index.md` links it — asserted **both** in the
   frontmatter `related:` list and in the body.
2. **Substance assertions**, one per load-bearing claim, each with an explanatory failure message:
   - the key path `tracker` + `egress` and **both** legal values `refused` and `permitted`;
   - the sentence that **absence of both channels denies**;
   - **`spec-kitty init`** as the remedy for the identity-less checkout, plus the phrase that says
     hand-authoring `sync.enabled: true` still denies there;
   - the statement that the **Channel-2 grant is the only remedy that needs no project identity**;
   - the **C-016 limitation** — `permitted` grants nothing at the hosted destination and hosted-sync
     consent remains a prerequisite there;
   - the **`map list` split** sentence, including both command forms and the phrase carrying the
     reason (*the gate follows the destination, not the subcommand name*);
   - the **fault-refuses** statement naming at least one near-miss value.
3. **The heading anchor itself** — assert the stable heading is present, *in addition to* the substance
   assertions, so a rename is caught as well as an emptying. FR-013: the check "fails in CI if the
   section is removed **or renamed**."
4. **Print the input count**: the note's byte length and the number of substance assertions run,
   alongside any pass. A doc check that ran on an empty file passes vacuously.
5. Mark the module `pytestmark = pytest.mark.fast`, matching the sibling doc tests.

**Red first, and demonstrate it — do not assume it.** From `plan.md` Stage 7's exit criterion: *"the
anchor check fails when the section is renamed (**demonstrated, not assumed**)"*. Demonstrate it
**without editing the shipped note during a verification run**: write the assertions as a helper
taking the note's **text** so the test can be pointed at (a) the real file — must pass — and (b) a
**synthetic copy held in the test** with the section renamed and with the section emptied — both must
fail. This is the same analyzer-callable-invoked-twice discipline the guards use, and it is what
satisfies "never source edits during a verification run".

**Exit for T045:** the check passes against the real note; it **fails** against both synthetic
mutants (renamed heading, emptied section); the input count is printed and non-zero.

---

### T046 — Exit: terminology, quality gates, and staging

1. **The terminology guard, before pushing prose** (H-E) — this gate runs only in CI's
   `integration-tests-core-misc` job, not in the fast suites, so a regression passes local doctrine
   runs and fails at CI:

   ```
   pytest tests/architectural/test_no_legacy_terminology.py -q
   ```

   Unpiped. **Quote the `N passed` line.**

2. **The new anchor check, alone:**

   ```
   pytest tests/docs/test_tracker_egress_upgrade_note_3108.py -q
   ```

   Quote the `N passed` line and the printed input count.

3. **The docs suite, for collateral:**

   ```
   pytest tests/docs/ -q
   ```

   Quote the summary line. Prediction: **unchanged** apart from your added tests. An **unpredicted**
   movement is a **stop-and-attribute event**.

4. **Cross-check the CHANGELOG entry exists and links your note.** WP04 owns `CHANGELOG.md`; you only
   **read** it. Confirm it carries a Breaking Changes entry stating that `beads`/`fp` bindings now
   require a recorded decision at one of the two channels, that absence of both denies, and that it
   links the upgrade note. **If it is missing or the link is wrong, report it — do not edit
   `CHANGELOG.md`.**

5. **Quality gates:** `ruff check tests/docs/test_tracker_egress_upgrade_note_3108.py` clean, no
   blanket `# noqa`; `mypy --strict` clean on it, no `# type: ignore` added. Do not run `ruff format`
   and do not treat a formatting diff as evidence.

6. **Explicit-path staging:**

   ```
   git add docs/migrations/tracker-egress-refusal.md docs/migrations/index.md \
           tests/docs/test_tracker_egress_upgrade_note_3108.py
   ```

   **Never `git add -A`.** `git diff --stat` must show exactly these three files.

7. **Do not chase the known pre-existing failures.** A *newly* encountered pre-existing failure is
   **filed as an issue before being treated as baseline**, confirmed against the merge-base with
   `PYTHONPATH=<worktree>/src`.

---

## Exit criterion for WP08

From `plan.md` Stage 7:

> "**Exit criterion for Stage 7:** the anchor check **fails when the section is renamed
> (demonstrated, not assumed)** and passes otherwise; `pytest tests/architectural/test_no_legacy_terminology.py`
> green."

Plus SC-018: the upgrade note exists under `docs/migrations/`, is linked from
`docs/migrations/index.md`, and the CHANGELOG Breaking Changes entry (WP04's) is present and links it.
Plus: every remedy documented is backed by a **passing executed-remedy test**, not by a substring
assertion.

## What to report back

1. The `N passed` line from the executed-remedy tests you used to validate each remedy, and an
   explicit statement that **no remedy was documented without one**.
2. The anchor check observed **red against both synthetic mutants** (renamed heading, emptied section)
   and **green against the real note** — quoted, with the printed input count.
3. The `N passed` line for `tests/architectural/test_no_legacy_terminology.py`.
4. The `tests/docs/` summary line against its "unchanged" prediction.
5. Confirmation that the CHANGELOG Breaking Changes entry exists and links your note — or a report
   that it does not, **without having edited `CHANGELOG.md`**.
6. Confirmation that `git diff --stat` shows exactly your three files.
7. Any hazard you judged not to apply, and why.
