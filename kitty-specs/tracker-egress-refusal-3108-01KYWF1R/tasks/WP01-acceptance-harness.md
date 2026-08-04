---
work_package_id: WP01
title: Acceptance harness proven on the un-gated tree (Stage 1 root)
dependencies: []
requirement_refs:
- C-007
- C-011
- C-012
- C-013
- C-014
- C-015
- C-016
- C-019
- FR-004
- FR-016
- FR-018
- NFR-001
- NFR-002
- NFR-004
planning_base_branch: bundle-c-tracker-refusal-3108
merge_target_branch: bundle-c-tracker-refusal-3108
branch_strategy: Planning artifacts for this mission were generated on bundle-c-tracker-refusal-3108. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into bundle-c-tracker-refusal-3108 unless the human explicitly redirects the landing branch.
created_at: '2026-08-01T00:20:00+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
phase: Stage 1 - The acceptance harness, before any product code
history:
- at: '2026-08-01T00:20:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks-packages
agent_profile: python-pedro
authoritative_surface: tests/sync/tracker/test_tracker_egress_refusal_3108.py
create_intent:
- tests/sync/tracker/test_tracker_egress_refusal_3108.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- tests/sync/tracker/test_tracker_egress_refusal_3108.py
role: implementer
tags: []
task_type: implement
tracker_refs:
- '3108'
---

# Work Package Prompt: WP01 – Acceptance harness proven on the un-gated tree

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter and behave per its
guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`

---

## Objective

Build the acceptance harness for the whole Mission and **prove it against the un-gated tree**, where
its positive controls must already pass and its refusing pins must already fail. Nothing in
`src/` is touched by this work package. What you deliver is one test file plus the measurements that
make every later "no bytes crossed" assertion in this Mission mean something.

**Done** = `tests/sync/tracker/test_tracker_egress_refusal_3108.py` exists; its consenting `push`
control captures **exactly 3** argv with the sentinel title verbatim in the `create`, on a tree with
**no gate in it**; its unseeded consenting variant captures exactly **1**; and its refusing pins are
committed **red**, with the red printing the confidential title inside a captured argv element.

> **Read this before a reviewer rejects you for it. This work package exits with committed red
> tests, by design.** The refusing acceptance pins in this file only flip green at WP04 (local
> destination) and WP05 (hosted destination). WP01's exit criterion covers the **positive controls
> and the harness non-vacuity checks only**. A reviewer applying a blanket "the suite must be green"
> rule to WP01 would reject it wrongly. The charter's ATDD rule is the opposite: the failing test is
> committed **before** the implementation commit. Say so in the PR body.

---

## Boundaries — what this WP may touch

**Owned file — the only file you may create or edit:**

- `tests/sync/tracker/test_tracker_egress_refusal_3108.py`

**Hard boundary.** Every other file in this Mission is owned by another work package and must not be
edited here, including: `src/specify_cli/tracker/config.py`, `service.py`, `saas_service.py`
(WP02); `src/specify_cli/tracker/egress_verdict.py` (WP03); `src/specify_cli/tracker/local_service.py`,
`src/specify_cli/cli/commands/tracker.py`, `tests/sync/tracker/test_local_service.py`, `CHANGELOG.md`
(WP04); `src/specify_cli/tracker/saas_client.py` (WP05); `src/specify_cli/cli/commands/sync.py`
(WP06); `tests/architectural/test_tracker_egress_guards_3108.py` (WP07); `docs/migrations/**`
(WP08). One live agent per file.

**Dependencies: none.** This is one of the Mission's two independent roots (`plan.md` Sequencing,
Stage 1). You may assume nothing about `tracker.egress` existing as a config key, about
`tracker_egress_verdict` existing, or about any gate existing. **You are writing against the
un-gated tree and that is the point.**

**Cross-package note you must not resolve by editing someone else's file.** `plan.md` Stage 5
requires SC-005 and SC-005a — the hosted-destination acceptance cells — to live in
**this** file, "because both run end to end through the CLI and the pairing is only meaningful in one
file against one trip-wire". `wps.yaml` gives WP05 only `src/specify_cli/tracker/saas_client.py` —
**WP05 owns no test file at all.** So every hosted acceptance cell is authored **here**, by you, in
T007: **US5 sc1, sc2, sc3, sc4 (SC-005a) and sc5 (the hosted near-miss, SC-010's end-to-end half)**,
plus the two positive controls. They stay red until WP05 lands, **except SC-005a and the controls,
which are green throughout** (T007 says why). Do not open `saas_client.py`.

**And the hosted bind counter is authored here too**, against the name WP05 will bind — see T006
step 2. WP05 has nowhere to put it.

---

## Requirements this WP satisfies

Quoted or tightly paraphrased from `spec.md` so you do not have to go hunting.

### FR-018 — The acceptance harness is a contract, not a fixture preference

> *"I want the harness pinned, because the measured alternative is a green suite with no gate.
> **Four** independent mechanisms have now been measured to produce that outcome; H1, H2, H3 and H8
> are each one of them."*

- **H1 — ownership mode.** Every acceptance fixture pins `doctrine: {mode: spec_kitty_authoritative}`.
  Under the default `external_authoritative` (`tracker/config.py:39`),
  `OwnershipPolicy.external_authoritative()` (`local_service.py:236`) gives
  `owner_for("title") is FieldOwner.EXTERNAL`, so `local_can_write("title")` is `False`
  (`spec_kitty_tracker/policy.py:47-49`) and `SyncEngine.push` does `stats.skipped += 1; continue`
  (`spec_kitty_tracker/sync.py:112-115`) and **never calls `create_issue`**. Measured: a *consenting*
  push on a default binding captures only `['<cmd>', '--json', 'list']`, sentinel absent.
- **H2 — injection point.** *"The recorder **is** the fake executable on disk"*: a script written per
  fixture and named through the machine-global tracker credential file (`factory.py:56` —
  `command=str(credentials.get("command") or "bd")`), which appends every argv it receives to a file.
  It is **not** an injected `SubprocessCommandRunner` — *"that class is not exported from
  `spec_kitty_tracker.__all__` and `build_connector` passes no runner, so **there is no injection
  seam**, and the charter's shared-package boundary forbids reaching into the private submodule to
  manufacture one."* `_build_engine`, `build_connector`, `SyncEngine`, `LocalTrackerService` and
  `TrackerService` are **un-patched in every acceptance test**.
- **H3 — arming.** Every fixture sets `SPEC_KITTY_ENABLE_SAAS_SYNC=1` **explicitly** and asserts
  refusal **text**, not merely a non-zero exit, plus the negative pin of US1 scenario 3.
- **H4 — bind counter.** The gate is instrumented by a **delegating wrapper (never a stub)** (C-007).
  There are **two** counters, one per destination, because one name cannot count both — see T006
  step 2 for the split, the exemption and the scope. *"A gate never entered is not a gate."*
- **H5 — executed remedies.** Every remedy claimed in a message is asserted by **applying it to the
  refusing fixture and re-running**, asserting the title now reaches the recorder — never by
  substring alone.
- **H6 — patch sites.** Reported per site per C-007.
- **H7 — isolation.** Isolated `HOME` / `SPEC_KITTY_HOME`, HTTP trip-wire on `httpx.Client.request`,
  `subprocess.run` counter, and the tracker-DB assertions of NFR-002.
- **H8 — the store is seeded.** Every push/run fixture seeds the tracker store with the sentinel issue
  **before** the command runs, via `store.upsert_issue(CanonicalIssue(...))`. *"`SyncEngine.push`
  iterates `store.list_issues(system=self.connector.name)` (`spec_kitty_tracker/sync.py:109`) and an
  **empty store never reaches `create_issue`**."*

### NFR-001 — No project bytes reach argv for a refusing project

> *"For every refusing fixture, across all three entry points, the recorder captures **zero argv**. On
> `push` and `run` the assertion is additionally that no captured element equals or contains the
> seeded sentinel title. On `pull` the title assertion is **not** made […] Every absence assertion is
> paired, in the same test file and against the same recorder, with a consenting control that
> captures argv — otherwise 'no bytes' is indistinguishable from 'the harness never ran the code'."*

### NFR-002 — A refused command performs no network I/O, no subprocess, and no local side effect

Stated **twice, over two fixture pairs**, because the two properties are not simultaneously
observable on one pair:

- **(a) Content-identity, on the seeded pair.** The tracker SQLite file necessarily exists beforehand;
  assert its **bytes are unchanged** (digest before == digest after), and that the consenting
  control's digest differs.
- **(b) Non-existence, on a dedicated unseeded pair (US3 sc4).** With no file at the resolved db path
  when the command starts, a refused command leaves none, and the consenting control creates one.
  *"clause (b) […] is the pin that reds if the gate is moved back to `_build_engine`, where
  `TrackerSqliteStore.__init__` `mkdir`s and creates a SQLite file with three tables
  (`store.py:278-281`). Clause (a) alone would not catch that move, because re-opening an existing
  store is idempotent."*

### NFR-004 — The gate is total across the three entry points

> *"`sync_pull`, `sync_push` and `sync_run` each have their own refusing case and their own consenting
> control, each exercised end to end through the CLI. **A parametrised pair that runs once and is
> asserted three times does not satisfy this.**"*

### Constraints

- **C-007** — `from X import f` rebinds by value; patch the **deciding** module's name, report per site.
- **C-011** — measurement discipline (reproduced in *Standing Rules* below).
- **C-012** — blast radius, named before the work starts.
- **C-013** — known pre-existing failures are not this Mission's to green.
- **C-014 / C-015** — Chain B and the explicit non-goals: **filed as issues, not absorbed**.
- **C-019** — stated limits carried forward unresolved.

### Success criteria owned or exercised here

SC-001, SC-002, SC-003, SC-004, SC-006, SC-007, SC-011, SC-012, SC-013, SC-020 — and, per the
cross-package note, SC-005, **SC-005a** (green throughout, not a red-then-green pin) and **SC-010's
end-to-end hosted half** (US5 sc5, one representative near-miss; the full 15-value coverage is
WP03's, at the unit level, for both destinations).

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
- **Include a positive control that must pass**, or "nothing broke" is indistinguishable from "the
  harness never ran the code".
- **Any assertion of absence must establish why the thing would otherwise have happened.**
- **Mutations as pytest plugins via `PYTHONPATH`, never source edits**, and never source edits during
  a verification run.
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

## Measured hazards that apply to this WP — facts, not advice

**Hazard 1 — the house test pattern patches out the gate.**
`tests/sync/tracker/test_local_service.py:235,262,287` do `patch.object(svc, "_build_engine", …)`
(docstring `:193-195`: *"We mock `_build_engine` to avoid needing the spec_kitty_tracker package"*).
A plugin-injected gate on that seam measured **bind count 0 with 519 tests green**. Your acceptance
tests must leave `_build_engine`, `build_connector` and `SyncEngine` **un-patched**; the recorder is
a **real fake executable on disk** named through `TrackerCredentialStore`. `SubprocessCommandRunner`
is **not publicly importable** from `spec_kitty_tracker`, so the fake executable is the only
charter-clean route.

**Hazard 2 — the positive control needs a seeded store AND the right ownership mode.**
`doctrine_mode` defaults to `external_authoritative`, under which `local_can_write("title")` is
`False` and `push` skips without calling `create_issue`. And an empty store never reaches
`create_issue` at all. Measured:

```
### EMPTY STORE ###   push stats: {'pushed_created': 0}   CAPTURED 1 argv   sentinel: False
### SEEDED STORE ###  push stats: {'pushed_created': 1}   CAPTURED 3 argv   sentinel: True
```

Seed with `store.upsert_issue(CanonicalIssue(...))` and pin `status=CanonicalStatus.TODO` — a status
outside `{TODO, IN_PROGRESS}` adds **two** further argv (`update` plus its own `show`), total 5.

**Hazard 3 — the arming gate satisfies every refusing assertion with nothing built.**
Un-armed, `cli/commands/tracker.py:354-366` aborts the whole group: exit 1, 0 subprocess, 0 HTTP.
Measured:

```
SPEC_KITTY_ENABLE_SAAS_SYNC=None  -> exit 1, subprocess.run 0, http 0
   'Hosted SaaS sync is not enabled on this machine. Set `SPEC_KITTY_ENABLE_SAAS_SYNC=1` to opt in.'
SPEC_KITTY_ENABLE_SAAS_SYNC='1'   -> exit 1, subprocess.run 1
```

Every fixture sets `SPEC_KITTY_ENABLE_SAAS_SYNC=1` **and asserts refusal text**, never merely a
non-zero exit. Include the negative pin (US1 sc3) proving the un-armed message is **not** what the
refusing scenarios matched.

**Hazard 4 — `from X import f` rebinds by value.** Measured at `bb2020fea`: after patching
`specify_cli.tracker.egress_consent.project_egress_refusal`,
`TSC.project_egress_refusal is TE.project_egress_refusal` → **`False`**. Tests patch the **deciding**
module's bound name and report the per-site split. The hosted path has **two targets that apply at
different times**, because WP05 deletes the first:

| Path | Target **before** the WP05 swap | Target **after** the WP05 swap |
|---|---|---|
| hosted (`saas_client._request`) | `specify_cli.tracker.saas_client.project_egress_refusal` | `specify_cli.tracker.saas_client.tracker_egress_verdict` |
| local (`local_service` gates) | — (no gate yet) | whatever name `local_service.py` binds `tracker_egress_verdict` under |

A recipe naming only the pre-swap target is **correct on the base and inert on the delivered tree**.

**Hazard 5 — pull ships no title today, so a title-absence pin there proves nothing.**
`LocalTrackerService.sync_pull` calls `engine.pull(limit=limit)` and `SyncEngine.pull(filters=None)`
builds `[<cmd>, "--json", "list"]` plus an optional `--updated-after`. Pull's refusing assertion is
**zero captured argv**; its consenting control asserts argv **shape and count**.

**Hazard 6 — the harness is POSIX-scoped and must say so.** The recorder is a `#!`-script made
executable and `subprocess.run` takes no shell; Windows needs a `.cmd`/`.bat` sibling. The Mission's
chosen default is **document the skip**: mark the suite `skipif(os.name == "nt")` with the reason
recorded **in the file**. A silently POSIX-only acceptance suite on a cross-platform target is a
coverage claim the Mission has not earned.

**Hazard 7 — an autouse fixture in your own directory falsifies the hosted base behaviour this
prompt describes.** `tests/sync/tracker/conftest.py:55` defines `_patch_saas_token_bridges`, an
**`autouse=True`** fixture that unconditionally replaces the module's `_fetch_access_token_sync`.
It first tries `request.getfixturevalue("mock_credential_store")` (`:66-71`) and, when the test file
does not define one, falls back to a `MagicMock` whose `get_access_token()` returns
**`"test-access-token"`** (`:72`). **Inside `tests/sync/tracker/` the hosted control therefore does
not reach `No valid access token` at all** — it proceeds past the token check into a real `httpx`
call and **trips your own trip-wire (Hazard 7 meets Hazard 7: your trip-wire fails loudly, and you
will misread that as a gate)**.

**The neutralisation, stated so you do not discover it by bisect:** define a **local
`mock_credential_store` fixture in your own file** whose `get_access_token()` returns **`None`**
(and whose `get_team_slug()` / `get_refresh_token()` return whatever your cells need). The autouse
fixture resolves it at `conftest.py:69` and the bridge then returns `None`, restoring the
`No valid access token` behaviour the US5 controls are written against.

**Consequently: every base behaviour this prompt attributes to the hosted path — US5 sc1's
`No valid access token`, US5 sc3's control, SC-005a's control — must be RE-DERIVED by you from
inside `tests/sync/tracker/`, with the neutralising fixture in place, and quoted.** A behaviour
measured outside that directory is a statement about a different fixture stack.

Two related facts from the same file, so you do not trip on them either:

- `conftest.py:129-153` builds a **consenting** checkout and `_compat_init` (`:155-165`) injects it
  as `project_root` **only when the caller omitted `project_root` entirely**. Passing
  `project_root=None` explicitly still refuses, and `SaaSTrackerService` passes `project_root=repo_root`
  explicitly (`saas_service.py:110`), so your cells are unaffected — but a throwaway probe that
  constructs `SaaSTrackerClient()` bare **is** affected and will report a consent state it did not set.
- That file deliberately does **not** stub `project_egress_refusal` (comments at `:120-128`). Neither
  may you.

**Hazard 8 — "Channel 1 granted" appears in eight scenarios and has one recipe. Use it.**
The minimal grant is the project's **own committed `.kittify/config.yaml`** carrying **both**:

```yaml
project:
  uuid: 6f1c2f2e-59a1-4a1f-9a2e-0f1c2f2e59a1   # any well-formed UUID; identity must RESOLVE
  slug: <anything>
sync:
  enabled: true        # a YAML boolean, unquoted
```

**Only a real YAML boolean records a decision.** `_consent_value_or_fault`
(`src/specify_cli/sync/consent.py:196-241`) returns the value only for `isinstance(raw, bool)`
(`:235-236`); `"true"`, `yes`, `on`, `1` and every other present non-boolean fall through to `:237-241`
as a **fault** — and **a field fault denies**. A quoted `"true"` in a fixture therefore produces a
*refusing* project that looks granted in the YAML, which is the worst possible fixture bug in this
Mission.

The variants you need:

| Fixture | Recipe |
|---|---|
| **Channel 1 granted** | `project.uuid` **and** `sync.enabled: true` (boolean), as above. |
| **Channel 1 — no record** | `project.uuid` present, **no `sync:` block and no `sync.enabled` key** (`consent.py:223-234` returns `(None, None)` for both). |
| **Channel 1 — recorded refusal** | `project.uuid` present, `sync.enabled: false` (boolean). |
| **Channel 1 — not consentable** | **omit `project.uuid`.** `enable_checkout_sync` then raises `ConsentIdentityUnresolvedError` (`routing.py:320-321`) and hand-authoring `sync.enabled: true` **still denies**. |

**Precedents in the tree — read them, do not re-invent them:** `tests/sync/tracker/conftest.py:131-153`
(the grant, written as a real config file rather than a stub) and
`tests/sync/test_consent_resolver_3030.py:48-63` (`_checkout(...)`, which renders exactly this shape
and whose docstring records that `sync.hosted` was a spelling nothing else in the tree used).
`tests/sync/test_consent_resolver_3030.py:66-71` shows the public writer for the machine-global
uuid-keyed index (`set_project_consent`) if a cell needs that level rather than the project-local one.

---

## Subtasks & Detailed Guidance

### T001 — File the follow-ups, pin the base, re-measure the baselines

- **Purpose**: IC-10 states it once and nowhere contradicts it: *"the issues are filed **before
  implementation starts**. Not 'at any point', not 'at the end'."* And C-011's citation revalidation
  must precede any work that trusts a line number.
- **Steps**:
  1. **File the follow-up issues** (C-014, C-015). **Four**, at minimum:
     - **Chain B.** Framed as ***"finish `#3030` FR-031's migration at the two remaining enforcement
       sites"*** — not "consolidate two consent chains", because *"the second framing is what got it
       deferred last time"*. It must carry: the two remaining enforcement sites (`sync/batch.py:338`
       via the drain gate, and `sync/runtime.py:106`), the two display-only reads
       (`cli/commands/sync.py:1964,2081`), the named canonical replacement
       (`sync/body_upload.py::project_consents_to_hosted_sync`, `body_upload.py:54`, rationale
       `:60-88`), and **the reachability sentence that makes it urgent rather than tidy**:
       *"`_build_checkout_sync_routing` falls through to
       `SyncConfig().get_repository_sync_enabled(repo_slug)` (`routing.py:194-200`) when both the
       project-local and the checkout-local records are `None`, and `enable_checkout_sync` writes that
       **repo-slug-keyed** record on **every** opt-in (`routing.py:325`) — so a fresh clone of an
       already-opted-in repository drains events that Chain A denies."*
     - **`LocalTrackerService.sync_publish` `AttributeError`** (C-015): `service.py:202-203` delegates
       unconditionally and `_run_or_exit` (`tracker.py:346-351`) catches only
       `RuntimeError`/`ValueError`. A live bug, incidental to this Mission.
     - **`_extra`'s consumers are unaudited** (C-019 (3)), sharpened: two are now known
       (`saas_service.py:219`, `:316`) and this Mission's field promotion breaks them; the unaudited
       remainder is what is left after those two.
     - **The upstream gap in `finalize-tasks`' requirement-ID scraping.** File it against the
       spec-kitty toolchain, not against this Mission. `spec-kitty agent mission finalize-tasks`
       scrapes requirement IDs out of the **whole spec** with a bare regex and cannot tell a
       Mission's **own** IDs from **citations of another Mission's**. **Describe both failure
       modes**, because only the first was hit and the second is worse:
       1. **Phantom unmapped IDs** — an ID that appears only as a citation is reported as an
          unmapped requirement of this Mission, so the board is told it has coverage holes it does
          not have. Noisy, visible, and what was actually observed here.
       2. **Silent mis-attribution** — a citation of **another** Mission's `FR-003` / `FR-018` /
          `C-003` is attributed to **this** Mission's same-numbered requirement, so a WP that maps
          the local `FR-003` appears to cover the cited one too. **Apparent coverage is inflated and
          nothing reports it.** This is the mode that matters: it is invisible in exactly the way a
          coverage tool is supposed not to be.
       **Four such citations remain in `spec.md` and were deliberately left**, because rewording them
       would lose the meaning of the cross-Mission reference while the collision stays invisible to
       the reader. Say so in the issue, and name them, so the toolchain fix has a test case.
  2. **Record the actual base SHA.** Every citation in this dossier was taken at `bb2020fea` and
     implementation is deferred, so the base will not be `bb2020fea`.
  3. **Revalidate the citations this WP depends on, by symbol name (`grep`), never by line number**:
     `cli/commands/tracker.py:354-366` (the arming abort), `tracker/factory.py:56` (the
     credential-named command), `tracker/config.py:39` (`doctrine_mode` default),
     `local_service.py:115/130/140` (the three sync entry points), `local_service.py:236`
     (`OwnershipPolicy.external_authoritative()`), `spec_kitty_tracker/sync.py:109,112-115`,
     `spec_kitty_tracker/connectors/beads.py:151-153`, `store.py:278-281`.
     **A line that moved is bookkeeping. A symbol that moved *semantically* — a changed signature, a
     relocated gate, a changed default, a new caller of `LocalTrackerService` — is a re-plan trigger**,
     and the correct response is to stop and re-plan, not to patch the citation and continue.
  4. **Re-measure the five Stage-0 baselines, each against its prediction**, unpiped, in a worktree
     pinned to the base with `PYTHONPATH=$WT/src`:

     | Suite | `bb2020fea` | Prediction — direction and cause |
     |---|---|---|
     | six consent/boundary suites | `154 passed in 51.31s` | **increases**, by the tests `#3113` adds to `tests/architectural/test_egress_consent_boundary.py`. A **decrease**, or **any** movement when `#3113` has *not* landed, is a stop-and-attribute event. |
     | `tests/architectural/test_egress_consent_boundary.py` alone | `27 passed in 77.30s` | **increases**, same cause, same stop conditions. |
     | `tests/sync/tracker/ tests/agent/cli/commands/test_tracker.py` | `519 passed, 1 warning in 64.73s` | **unchanged** |
     | `tests/cli/commands/test_sync_doctor_consent_health_3030.py` | `15 passed in 54.64s` | **unchanged** |
     | `tests/specify_cli/` | `35 passed in 54.65s`, exit 0 | **unchanged** |

     Additionally **measure and record `tests/sync/tracker/test_saas_client_consent_gate_3030.py`
     alone** — its count is otherwise folded invisibly into the 519, and Stage 5 needs a number to
     cite.
- **Files**: none in this repository. GitHub issues plus the recorded measurements in the PR body.
- **Validation**: **four** issue URLs; the base SHA; a symbol-by-symbol citation verdict; five (six)
  quoted `N passed` lines, each reconciled against its direction-and-cause prediction.
- **Edge cases**: an **unpredicted** movement in any row is a stop-and-attribute event. Do not
  continue and do not average it away.

### T002 — The isolation, arming and trip-wire substrate

- **Purpose**: H3 and H7. Without arming, every refusing assertion in this file is already green with
  nothing built.
- **Steps**: Build the module-level fixtures:
  - Isolated `HOME` **and** `SPEC_KITTY_HOME` per test (the machine-global consent index and the
    machine-global tracker credential file both live under them).
  - `SPEC_KITTY_ENABLE_SAAS_SYNC=1` set **explicitly** in every fixture — never inherited, never
    assumed.
  - An HTTP trip-wire on `httpx.Client.request` that counts attempts and fails loudly rather than
    performing them.
  - A `subprocess.run` counter (counting only; the real fake executable still runs).
  - A helper that writes a project's committed `.kittify/config.yaml`, taking the `sync:` block, the
    `tracker:` block and the `doctrine:` block as explicit arguments, so a "differs by exactly one
    committed line" claim is checkable by diffing two rendered fixtures.
  - The POSIX scope marker: `skipif(os.name == "nt")` with the reason recorded in a module-level
    comment — the recorder is a `#!`-script, `subprocess.run` takes no shell, and Windows needs a
    `.cmd`/`.bat` sibling that this Mission has no runner to prove.
- **Files**: `tests/sync/tracker/test_tracker_egress_refusal_3108.py`.
- **Validation**: a throwaway smoke test asserting `SPEC_KITTY_ENABLE_SAAS_SYNC == "1"` inside the
  fixture and that the trip-wire raises when deliberately tripped (control your diagnostic — run the
  probe against a case whose answer you already know).
- **Edge cases**: if any fixture inherits arming from the ambient environment rather than setting it,
  the suite will pass on your machine and mean nothing on CI.

### T003 — The recorder: a real fake executable, nothing patched

- **Purpose**: H2. **The recorder *is* the fake executable on disk.** There is no
  `SubprocessCommandRunner` injection seam: the class is absent from `spec_kitty_tracker.__all__`,
  `build_connector` passes no runner, and the charter's shared-package boundary forbids reaching into
  the private submodule to manufacture one.
- **Steps**:
  1. Write a `#!`-script per fixture that appends its full `argv` (one JSON line per invocation) to a
     capture file, and make it executable.
  2. Name it through the **machine-global tracker credential file** — the same path `factory.py:56`
     reads (`command=str(credentials.get("command") or "bd")`) — via `TrackerCredentialStore`, not by
     writing the file by hand if a public writer exists.
  3. The script must emit JSON on stdout shaped well enough for `BeadsConnector` to parse `list`,
     `create` and `show` responses; otherwise the consenting control dies before it can capture 3
     argv and you will misread that as a gate. **Specify all three responses — and `list` must
     return an empty list:**

     | Subcommand in argv | Response the script prints | Why this exact answer |
     |---|---|---|
     | `list` | **`[]`** (an empty JSON array in the connector's list shape) | `SyncEngine.push` calls `_collect_remote_index` → `connector.list_issues` **before** `store.list_issues`. A **non-empty** `list` matches the seeded issue against a remote one and sends the run down the **update** branch — so the sentinel never appears in a `create`, the count is not 3, and the whole pair is void. |
     | `create` | one issue object with a **stable id** the script reuses | It is the argv element that must carry `ACME Holdings carve-out` verbatim; `create_issue` then follows with `get_issue` on that id. |
     | `show` | **the same issue object** the `create` returned | `create_issue` ends with `get_issue` (`spec_kitty_tracker/connectors/beads.py:151-153`) — this is the third argv, and a mismatched id here fails the push after the sentinel has already crossed, which reads like a gate and is not one. |

     Branch on the subcommand token in argv, not on argv length. **Control your diagnostic:** run the
     script by hand once for each of the three subcommands and confirm the output parses, before you
     conclude anything from a test that uses it.
  4. Author the **SC-020 pin in this same file**: a grep-based check over this Mission's new test
     files asserting `_build_engine` is patched **nowhere**, **with its input count printed**. A
     grep that scanned zero files passes vacuously.
- **Files**: `tests/sync/tracker/test_tracker_egress_refusal_3108.py`.
- **Validation**: the capture file exists and holds at least one argv line after a consenting run;
  the SC-020 pin prints a non-zero file count.
- **Edge cases**: do **not** patch `_build_engine`, `build_connector`, `SyncEngine`,
  `LocalTrackerService` or `TrackerService` anywhere in this file. That prohibition is scoped to
  **this acceptance suite and those named seams** — it is not a blanket ban on patching in the
  Mission (see `plan.md` Open Items 8).

### T004 — Seed the store, pin the doctrine mode, prove the positive controls

- **Purpose**: H1 and H8 — the two false-greens that survive H2 and H3. **This subtask is Stage 1's
  exit criterion.**
- **Steps**:
  1. Every fixture writes `doctrine: {mode: spec_kitty_authoritative}` into the project's committed
     `.kittify/config.yaml`. Under the default `external_authoritative` a *consenting* push captures
     only `['<cmd>', '--json', 'list']` and the sentinel never appears.
  2. Every push/run fixture seeds the tracker store **before** the command runs.

     **`TrackerSqliteStore.upsert_issue` is `async def`** (`src/specify_cli/tracker/store.py:367`).
     Written synchronously it returns a coroutine, **never touches the database, and leaves the store
     empty** — producing exactly the 1-argv false-green the seeding requirement exists to prevent,
     with no error and no warning. Write it as:

     ```python
     asyncio.run(store.upsert_issue(CanonicalIssue(...)))
     ```

     and **assert the store is non-empty after seeding** rather than assuming the call landed.

     Note also that `TrackerSqliteStore` is **repo-local** — `src/specify_cli/tracker/store.py:275` —
     **not** part of the shared `spec_kitty_tracker` package, so constructing it directly is not a
     shared-package-boundary violation. Its `__init__` takes a `db_path` and `mkdir`s the parent.

     Seed with exactly this shape:
     `ref=ExternalRef(system="beads", workspace=<the bound workspace>, id=<a local id>)`,
     `title="ACME Holdings carve-out"`, `body="confidential body"`,
     `status=CanonicalStatus.TODO`, `issue_type=CanonicalIssueType.TASK`,
     `assignees=["alice@acme.example"]`, `labels=["secret-label"]`.
     **`status` must be `TODO` or `IN_PROGRESS`.** Measured across all six `CanonicalStatus` members:
     those two give **3** argv (`list`, `create`, `show`); every other member gives **5**
     (`list`, `create`, `update`, `show`, `show`), because `BeadsConnector.create_issue` follows with
     a `transition_issue` contributing an `update` **and** its own `show`. The band adds **two** argv,
     not one.
  3. Author the consenting controls and **run them on the un-gated base**:
     - `push`: exactly **3** argv — `list`, `create`, `show` — with `ACME Holdings carve-out` verbatim
       as an element of the `create`. The count is 3, not 2, because `create_issue` ends with
       `get_issue` (`spec_kitty_tracker/connectors/beads.py:151-153`).
     - the **unseeded** consenting variant: exactly **1** argv, `[<cmd>, "--json", "list"]`.
     - `pull`: argv **shape** `[<command>, "--json", "list", …]`.
  4. **Resolve the db path the same way production does — it is load-bearing three times.**
     NFR-002's clause (a) hashes it, clause (b) asserts nothing exists at it, and the consenting
     control asserts something does. Guess it wrong and the *"a refused command leaves no file"*
     clause passes **vacuously**, because you are looking at a path nothing was ever going to write.

     The resolution is `LocalTrackerService._resolve_db_path` (`local_service.py:205-215`), which
     calls `default_tracker_db_path(...)` (`store.py:105-120`), which builds a SHA-256-derived scope
     (`build_tracker_scope`, `store.py:90-102` — `sha256(f"{provider}|{workspace}|{server}|{user}|{team}")[:16]`)
     and returns `_trackers_dir() / f"{scope}.db"`. The five inputs come from the bound config and
     the **machine-global credential record**: `provider`, `workspace`, and
     `credentials["server_url"] or credentials["base_url"]`, `credentials["username"] or
     credentials["email"]`, `credentials["team_slug"]` — each defaulting to `local` / `anonymous` /
     `no-team` when empty.

     **Rules for the fixture:**
     - Call `default_tracker_db_path(...)` (or `_resolve_db_path`) yourself with **the same
       credential values the fixture wrote**. Do not reconstruct the filename, do not glob the
       trackers directory, and do not assume "one file therefore the right file".
     - **Add a positive control**: on the **consenting** member, assert a file appears **at that
       exact path** — not merely that some file appeared somewhere. That control is what turns the
       refusing member's "no file at this path" from an absence assertion into a measurement.
     - Isolated `SPEC_KITTY_HOME` is what makes `_trackers_dir()` per-test; without it the path is a
       machine-global one another test may already have created.

  5. Add the suite-level non-vacuity check: **every push/run acceptance test whose fixture SEEDS the
     store asserts its consenting control captured exactly 3 argv.** A control that captured 1 means
     the store was empty and every absence assertion in that test is void.

     **Scope this to the seeded tests, and name the exception in the same sentence:** the
     **US3 sc4 unseeded pair** is deliberately unseeded, and its consenting member captures
     **exactly 1** argv **by design**. Assert **1** there, and assert **3** everywhere else. An
     unqualified "every push/run test captures 3" reads as licence to seed the unseeded pair — which
     would destroy the only pin that reds when the gate drifts back to `_build_engine`.
- **Files**: `tests/sync/tracker/test_tracker_egress_refusal_3108.py`.
- **Validation**: run the file **alone** on the un-gated base, unpiped, and quote the `N passed` line
  together with the printed argv counts. *"If the consenting control captures 1 argv, the fixture is
  wrong and no later result from this suite means anything."*
- **Edge cases**: a seeded store with a status outside the band gives 5 and your exact-count
  assertions will read as a gate failure later. Assert 3 exactly, never `>= 3`.

### T005 — The refusing pins, committed red, with the red as the consequence

- **Purpose**: SC-001, SC-003, SC-006, SC-011 and NFR-002's two clauses. **These go in red.**
- **Steps**: Author, as pairs that differ by **exactly one committed config line**:
  - **US1 sc1** — `beads`, Channel 1 **granted**, `tracker: {egress: refused}`, seeded store,
    `sync push`. Assert **zero** captured argv, `ACME Holdings carve-out` in **no** captured element,
    the tracker SQLite file **byte-identical** (digest before == digest after), non-zero exit, and a
    refusal **text** naming **Channel 2 — the tracker key** and quoting the key's path.
    *Its red on the base is the recorder capturing **3** argv with the confidential title inside the
    `create` — the leak itself, not a return code standing in for one.*
  - **US1 sc2** — the same project with `tracker.egress` **absent**: the 3-argv control. Green on the
    base and after.
  - **US1 sc3 — the negative pin.** The refusal text is **not** `saas_sync_disabled_message()` — the
    string beginning *"Hosted SaaS sync is not enabled on this machine. Set"* and naming
    `SPEC_KITTY_ENABLE_SAAS_SYNC=1` — and the assertion that matched in sc1 does **not** match that
    string. Without this, the arming abort satisfies sc1 with no gate built (SC-013).
  - **US2 sc1** — **no** Channel-1 record at any level, committed `tracker: {egress: permitted}`:
    argv captured with the sentinel verbatim. Green on the base (nothing gates the local path today)
    and green after (Channel 2 grants).
  - **US2 sc2** — the same fixture with that one line removed: zero argv, refusal naming **Channel 1**.
  - **US2 sc3** — committed `sync: {enabled: false}` **and** `tracker: {egress: permitted}`: the
    connector is constructed. *A recorded hosted-sync refusal does not veto an explicit tracker grant
    on a local binding.*
  - **US3 sc1** — no record at either channel, seeded store: refuses, exits non-zero, db bytes
    unchanged, and the printed refusal carries the Channel-1 remedies for the **no record** state
    **and** the Channel-2 remedy.
  - **US3 sc2** — committed `sync: {enabled: false}`, no tracker key: the message says a hosted-sync
    **refusal is recorded** — wording **distinct** from sc1's *"no record was found"*.
  - **US3 sc3** — Channel 1 granted, no tracker key: 3 argv, sentinel verbatim. *Positive control.*
  - **US3 sc4 — the unseeded pair**, carrying NFR-002's **file-existence** clause: with **no** tracker
    SQLite file at the resolved db path when the command starts, the refusing member creates **no**
    file and captures **zero** argv; the consenting member creates the file and captures exactly
    **one** argv, `[<cmd>, "--json", "list"]`. **Make no sentinel assertion on this pair** — an
    unseeded store never reaches `create_issue`, so no title crosses in either member and asserting
    its absence would establish nothing. Record that reason in a comment in the file.
- **Files**: `tests/sync/tracker/test_tracker_egress_refusal_3108.py`.
- **Validation**: on the un-gated base, the refusing members are **red** and the failure text prints
  the captured title; the controls are green. Quote both.
- **Edge cases**: do not weaken a refusing assertion to make the file green. It is supposed to be red
  here.

### T006 — Totality across the three entry points, the bind counter, and executed remedies

- **Purpose**: NFR-004, H4, H5 — SC-004, SC-007, SC-012.
- **Steps**:
  1. **Totality (US4).** `sync_pull`, `sync_push` and `sync_run` each get **their own** refusing case
     and **their own** consenting control, each exercised end to end through the CLI. A parametrised
     pair that runs once and is asserted three times does not satisfy NFR-004.
     - pull refusing: **zero** captured argv, non-zero exit. Its red on the base is
       `len(captured) == 1` with the argv printed: `[<cmd>, '--json', 'list']`. **Never** a
       title-absence assertion — no title crosses on pull today.
     - run refusing: **zero** argv — neither the pull half nor the push half reaches the runner.
     - run consenting: argv for both halves, the push half carrying the sentinel.
  2. **The bind counter (H4) — TWO counters, split by destination, with one stated exemption.**
     Install a **delegating wrapper — never a stub** — and count entries. C-007: patch the
     **deciding** module's bound name, not the defining module's.

     **Why two.** A counter pinned to the name `local_service` binds is permanently **0** for the
     cells that never enter `local_service` at all — and this one file holds three such groups. A
     single counter asserted non-zero "in every acceptance test" is therefore not a strict rule; it
     is an **unsatisfiable** one, and the only way to satisfy it is to delete assertions until it
     passes.

     | Counter | Patch target | Asserted non-zero in |
     |---|---|---|
     | **local** | the name `local_service.py` binds `tracker_egress_verdict` under — WP04 binds it with `from specify_cli.tracker.egress_verdict import EgressDestination, tracker_egress_verdict`, so the target is **`specify_cli.tracker.local_service.tracker_egress_verdict`** | every **US1 sc1/sc2**, **US2**, **US3 sc1–sc3**, **US4** cell — i.e. every cell that drives `sync_pull` / `sync_push` / `sync_run` on a **local** binding |
     | **hosted** | **`specify_cli.tracker.saas_client.tracker_egress_verdict`** — the name WP05 binds after its swap | every **US5** cell (sc1–sc5): `jira` → `SaaSTrackerService` → `_request`. The local name is **never** called on this path and its counter is 0 there, permanently. |

     **The one exemption, stated in the file with its reason: US1 sc4, the `sync now` queue drain.**
     Neither name is called — it is the hosted **body/event** drain, a different transport with its
     own consent chain, and this Mission changes nothing about it. **The cell asserts no bind
     counter at all**, and a comment in the file says why. An exemption recorded is a decision; an
     exemption discovered later is a hole.

     **Also NOT applied: the consenting controls.** The bind counter is a pin on *refusing* cells —
     it answers *"was the gate entered before it refused?"*. Applying it to the consenting controls
     would make them red on the un-gated tree, which contradicts this WP's own exit criterion that
     the controls **pass** and are quoted. (After WP04 lands, a consenting local control *does*
     enter the gate — but that is WP04's evidence, not WP01's exit criterion.)

     **One test asserts the wrapper changes no outcome** — run one refusing cell and one consenting
     cell with the wrapper installed and with it absent, and assert the captured argv and the exit
     status are identical. A counting wrapper that changed an outcome would be a stub.

     **Record the interpreter version beside every bind count**: *"a zero bind count is a statement
     about the environment, not about the code"* — CI runs 3.11/3.12, the local interpreter here is
     3.14.

     Until WP04 and WP05 land there is no name to wrap at either target; write both wrappers against
     the names named above and let those assertions be part of the committed red. **Do not rename
     them later** — WP04 and WP05 are told the same two strings.
  3. **Executed remedies (US6, H5).** For each of the three Channel-1 states — **no record**,
     **recorded refusal**, **not consentable** — assert the printed state wording, then **apply the
     offered remedy to that fixture, re-run the same command, and assert the sentinel title now
     reaches the recorder**. Never a substring check.
     - *no record*: three remedies — `sync.enabled: true` in the project's own config,
       `spec-kitty sync opt-in`, or `tracker.egress: permitted`. All three must be executed.
     - *recorded refusal*: change the recorded decision, or the Channel-2 grant.
     - *not consentable*: a checkout with no `project.uuid`, where `enable_checkout_sync` raises
       `ConsentIdentityUnresolvedError` (`routing.py:320-321`) and hand-authoring `sync.enabled: true`
       still denies. Remedies: `spec-kitty init` (then sc1's remedies apply) or the Channel-2 grant,
       which needs no identity. *"Without this state the binding is permanently dead with actively
       wrong advice: today's message tells the operator to record a decision they have just
       recorded."*
- **Files**: `tests/sync/tracker/test_tracker_egress_refusal_3108.py`.
- **Validation**: three distinct refusing cases and three distinct controls per entry point, visible
  as separate test ids; the executed-remedy tests each re-run the command.
- **Edge cases**: an executed remedy that "passes" because the fixture was never refusing in the
  first place is worthless — assert the pre-remedy refusal first, in the same test.

### T007 — The hosted-destination cells, and the suite-level discipline

- **Purpose**: SC-005 and SC-005a live in **this** file by `plan.md` Stage 5's explicit instruction;
  and the suite has to be run the way the Verification Plan requires.
- **Steps**:
  1. **US5 sc1** — `jira` binding, Channel 1 **granted**, committed `tracker: {egress: refused}`,
     `sync push`: refuses with **0** HTTP attempts and a message naming **Channel 2**.
     **Important — the red here cannot be the HTTP count.** `_request` raises at the token check
     *before* any HTTP, so *"0 HTTP attempts" is **already green on the base***. The base behaviour is
     `No valid access token`; the required behaviour is `TrackerEgressRefusedError` naming Channel 2.
     **The red must pin the exception type and the message text**; the HTTP count is a supporting
     non-vacuity assertion proven to bind by sc3.
  2. **US5 sc2** — `jira`, Channel 1 **absent**, committed `tracker: {egress: permitted}`: still
     refuses with 0 HTTP, message names **Channel 1** *and additionally states that a tracker grant is
     recorded and does not apply to the hosted destination*.
  3. **US5 sc3** — `jira`, Channel 1 granted, no tracker key: the gate passes and the call fails later
     at `No valid access token`. *Positive control; the shipped `#3030` behaviour, unchanged.*
  4. **US5 sc4 / SC-005a** — **the pin that discriminates a destination-as-parameter implementation
     from a destination-as-derivation one.** On-disk `tracker.provider` is `beads`, the project commits
     `tracker: {egress: permitted}`, Channel 1 is **absent**, and
     `spec-kitty tracker list-tickets --provider jira` runs.
     `TrackerService._resolve_saas_backend_for_provider` (`service.py:84-98`) serves it by overriding
     the provider **in memory** and routing to `SaaSTrackerClient._request`. Assert it **refuses**
     with **0** HTTP attempts and a message naming **Channel 1**. **And** the paired positive control
     — on-disk `provider: jira`, Channel 1 granted, no tracker key, same command → reaches
     `No valid access token` — so the zero-HTTP count in the refusing member is not vacuous.

     > **SC-005a is GREEN BEFORE AND AFTER. It is not a red-then-green pin, and nothing in this WP
     > may describe it as one.** Measured at the base: `_request` calls
     > `project_egress_refusal(self._project_root)` at `saas_client.py:329-331` — **before**
     > `_fetch_access_token_sync()` at `:333` — and `SaaSTrackerService` passes a **non-`None`**
     > `project_root=repo_root` (`saas_service.py:110`). So with Channel 1 absent the base **already
     > refuses, already at zero HTTP, already with Channel-1 wording**. Writing "and that is the red"
     > here would send an implementer looking for a failure that does not exist, and the most likely
     > way to "find" it is to weaken the fixture until something fails.
     >
     > **What the cell is worth, stated exactly.** It reds **only on a destination-as-derivation
     > implementation** — one that reads `beads` off disk, applies the **local** half, and **grants**.
     > Its evidentiary value is therefore **contingent on the guards** (G5 pinning every call site's
     > `destination` to a literal member, G6 pinning the verdict's own body free of provider reads),
     > not on a transition. **Assert it here, quote it green on the base, quote it green after, and
     > say in the PR body that its green-before is expected and why.** A cell that is green
     > throughout is still a pin — it is the pin that fails the day someone "simplifies" the
     > destination into a config read.

     Measured, with a positive and a negative control:

     ```
     PRECONDITION on-disk provider : 'beads'
     SUBJECT backend class         : SaaSTrackerService
     SUBJECT in-memory cfg.provider: 'jira'
     SUBJECT on-disk cfg.provider  : 'beads'   <-- what a config-reading verdict() would have seen
     CONTROL (disk=jira) backend   : SaaSTrackerService
     NEGATIVE CONTROL              : TrackerServiceError raised for 'beads' (the probe discriminates)
     ```
  5. **US5 sc5 — the hosted near-miss, end to end.** `jira` binding, Channel 1 **granted**, committed
     `tracker: {egress: refuse}` (the singular near-miss). Assert it **refuses** at the hosted
     destination with **0** HTTP attempts, **without raising anything other than
     `TrackerEgressRefusedError`**, and that the printed fault **names the key**, **quotes `refuse`
     verbatim**, and names **both** legal values `refused` and `permitted` (C-020). **One
     representative near-miss is all this cell carries** — the full 15-value probed set is discharged
     at the unit level by WP03's fault-wording pins over both destinations. This cell exists so that
     "the fault refuses at the hosted destination" is proven **through the transport**, not only
     against the verdict function. It is authored here because WP05 owns **no test file**, and it
     goes in **red** with the rest of the US5 cells.
  6. **US1 sc4 — hosted sync is unaffected by the tracker key.** `spec-kitty sync now` drains a queue
     in a project recording `tracker: {egress: refused}`, and **exactly the same events** are
     delivered as in the paired fixture identical except that it records no tracker key.

     **This scenario is scoped here, because "compare event-for-event" is not a recipe and the
     obvious readings are all wrong.**

     - **How to enqueue.** Use the queue's own public writer through a `BackgroundSyncService`
       instance, following the precedent in `tests/sync/test_body_drain_consent_3030.py` — its
       `_service(tmp_path, monkeypatch)` helper (`:144`) and `_enqueue_body(...)` (`:117`). Enqueue
       **N = 2** events for a consenting project uuid so a partial drain is distinguishable from a
       full one; N = 1 cannot tell "drained" from "drained the only one it had".
     - **How delivery is observed under a trip-wire that fails loudly on any HTTP attempt.** It is
       **not** observed over HTTP. `test_body_drain_consent_3030.py` installs an egress **recorder**
       at the transport seam (its `_Egress` fixture) and asserts against
       `egress.project_uuids` / `egress.posts` / `egress.bodies` (`:247-249`). Port that seam. **Your
       `httpx.Client.request` trip-wire stays armed and must still record 0** — the drain path is
       instrumented *above* it, which is precisely why the two coexist.
     - **What "event-for-event" compares.** The **ordered list of delivered project uuids** and the
       **ordered list of delivered bodies**, plus `queue.size() == 0` at the end — the three
       assertions the precedent makes at `:247-250`. Equality is between the refusing fixture's
       lists and the control fixture's lists, element for element, not merely between their lengths.
     - **The non-vacuity clause.** Assert the queue was **non-empty before** the drain and **empty
       after**, in **both** members. *A drain that never ran satisfies a weaker wording* — and an
       empty queue drains "identically" in every fixture ever written.
     - **No bind counter is asserted in this cell.** Neither the local nor the hosted counter is
       entered: this is the body/event drain, a different transport with its own consent chain, and
       this Mission changes nothing about it. Record that reason **in a comment in the file**.

     **If porting that seam turns out to cost more than the cell is worth, the alternative is
     stated and permitted: move US1 sc4 out of the acceptance file** and record in the file, at the
     point where it would have been, that hosted-sync drain non-interference is covered by
     `tests/sync/test_body_drain_consent_3030.py` and is not re-asserted here. **Decide, write down
     which you did, and do not leave a half-specified scenario in the file.**
  7. **Run the suite twice: alone, and inside a full `tests/sync/tracker/` run.** A discrepancy
     between the two is cross-test pollution (the `#3115` class), not this Mission — and is a finding
     to **report**, not to chase to green.
- **Files**: `tests/sync/tracker/test_tracker_egress_refusal_3108.py`.
- **Validation**: with the neutralising `mock_credential_store` fixture in place (Hazard 7),
  **re-derive and quote from inside `tests/sync/tracker/`**: US5 sc3's control reaches
  `No valid access token`; SC-005a's control reaches `No valid access token`; **SC-005a's subject
  already refuses naming Channel 1 — green on the base, green after**; US5 sc1 and sc5 are **red**,
  and their red is an **exception type and message**, never an HTTP count.
- **Edge cases**: do not open `src/specify_cli/tracker/saas_client.py`. WP05 owns it. And do not
  report "0 HTTP attempts" as any hosted red — `_request` raises before any HTTP, so it is already
  true on the base for every one of these cells.

---

## Test Strategy

- **New**: `tests/sync/tracker/test_tracker_egress_refusal_3108.py` — the whole deliverable.
- **Run alone**: `pytest tests/sync/tracker/test_tracker_egress_refusal_3108.py` — unpiped, `N passed`
  quoted.
- **Run in context**: `pytest tests/sync/tracker/ tests/agent/cli/commands/test_tracker.py` — expect
  the Stage-0 number **plus** this file's passing controls, **minus** nothing; the refusing pins are
  the expected new reds and must be enumerated by name in the PR body so a reviewer can tell them
  from a regression.
- `ruff check` and `mypy --strict` clean on the new file, no blanket suppressions.

## Definition of Done

**The exit criterion, stated once so it cannot contradict itself:** on the un-gated tree, **the
consenting controls pass; the enumerated refusing pins fail, by name.** Nothing else in this list
may be read as requiring a green suite, and nothing in this list may be read as requiring a
consenting control to fail. In particular **the bind-counter assertion is not applied to the
consenting controls** (T006 step 2 says so, and says why).

- **Four** follow-up issues filed, with URLs, **before** any other subtask — Chain B,
  `sync_publish`'s `AttributeError`, `_extra`'s unaudited consumers, and the `finalize-tasks`
  requirement-ID scraping gap with **both** of its failure modes described.
- Base SHA recorded; citation sweep recorded with a symbol-by-symbol verdict; five (six) baselines
  re-measured and reconciled against their direction-and-cause predictions.
- The consenting `push` control captures **exactly 3** argv with the sentinel verbatim in the
  `create`, on the **un-gated** base; the unseeded variant captures **exactly 1**. Both quoted.
- The refusing pins are committed **red**, **enumerated by name in the PR body** so a reviewer can
  tell them from a regression, and the US1 sc1 red prints `ACME Holdings carve-out` inside a captured
  argv element.
- The hosted base behaviours are **re-derived from inside `tests/sync/tracker/`** with the
  neutralising `mock_credential_store` fixture in place, and quoted. **SC-005a is recorded green
  before and after, with its green-before explained.**
- Both bind counters are wired against the two named patch targets; US1 sc4's exemption is recorded
  **in the file** with its reason.
- `_build_engine`, `build_connector`, `SyncEngine`, `LocalTrackerService`, `TrackerService` patched
  **nowhere** in this file — asserted by the SC-020 grep pin with its input count printed.
- The POSIX skip is documented in the file with its reason.
- No file outside `tests/sync/tracker/test_tracker_egress_refusal_3108.py` is modified.

## Risks & Mitigations

- **The harness passes with no gate** → four measured mechanisms (H1, H2, H3, H8); each has its own
  control in this file.
- **The gate is installed and never entered** → the H4 bind counter, asserted non-zero in every test,
  with the interpreter version recorded beside it.
- **The refusing red is a proxy rather than the consequence** → assert the captured bytes; US5 sc1's
  red is the exception type and message, never the HTTP count.
- **A reviewer rejects the WP for committed reds** → the objective section says why, and the PR body
  must repeat it.

## Review Guidance

- Verify the recorder is a **real executable on disk named through the credential store**, not a
  patched runner.
- Verify every fixture sets `SPEC_KITTY_ENABLE_SAAS_SYNC=1` explicitly and asserts refusal **text**.
- Verify the seeded issue's `status` is `TODO` or `IN_PROGRESS` and the consenting count assertion is
  exactly 3.
- Verify the unseeded pair makes **no** sentinel assertion, and pull makes **no** title-absence
  assertion, and that both omissions are explained in the file.
- Verify the refusing pins are red for the **right reason** — read the failure text, not the tally.

## Activity Log

- 2026-08-01T00:20:00Z – system – Prompt created.
- 2026-08-03T00:00:00Z – python-pedro – **T001 inherited-and-verified from the orchestrator** (not
  redone): four follow-up issues already filed upstream (#3167 Chain B, #3168 `sync_publish`
  AttributeError, #3169 `_extra` audit, #3170 finalize-tasks ID scraper); base pinned at
  `abca7ec9615e6e74caf9d7e807351a3a9a4d88a1`; baselines re-measured at that base by the
  orchestrator, each reconciled against its `bb2020fea` prediction: six consent/boundary suites
  `156 passed, 2 xfailed` (was 154 — the exact `#3113` delta, `#3113` closed upstream and in our
  base); `test_egress_consent_boundary.py` alone `29 passed, 2 xfailed` (was 27 — same delta);
  `tests/sync/tracker/ tests/agent/cli/commands/test_tracker.py` `519 passed` (unchanged, as
  predicted); `test_sync_doctor_consent_health_3030.py` `15 passed` (unchanged). `#3115` noted
  still OPEN — local serial proofs unaffected per handoff §4.1; only
  `test_saas_client.py::TestRetryBehaviors::test_429_respects_retry_after` is at risk on CI's
  parallel shard.
- 2026-08-03T00:00:00Z – python-pedro – Revalidated citations this WP depends on by symbol name
  (grep, not line number) directly against the working tree at the implementation base: all held
  semantically (`cli/commands/tracker.py` arming gate and `_check_sync_readiness` /
  `_is_local_binding` short-circuit; `tracker/factory.py:56` credential-named command;
  `tracker/config.py` `doctrine_mode` default `external_authoritative` and the
  `spec_kitty_authoritative` → `OwnershipPolicy.local_authoritative()` mapping in
  `local_service.py::_build_engine`; the three sync entry points at `local_service.py:115/130/140`;
  `spec_kitty_tracker.sync.SyncEngine.push/pull/_collect_remote_index`; `connectors/beads.py`'s
  `list_issues`/`create_issue`/`get_issue` argv shapes and the trailing `get_issue` after
  `create_issue`; `store.py`'s `TrackerSqliteStore.__init__` (mkdir + table creation) and
  `default_tracker_db_path`/`build_tracker_scope`; `tracker/saas_client.py`'s `_request` ordering
  (`project_egress_refusal` before `_fetch_access_token_sync`, before any `httpx.Client`
  construction) and `TrackerEgressRefusedError`). One additional hazard found by spiking, not
  named in the dossier: the CLI's own readiness pre-flight (`saas.readiness._probe_auth`, via
  `TokenManager.is_authenticated`) is a *second*, unrelated auth gate that blocks a literal
  `CliRunner` invocation of hosted (`jira`) commands before ever reaching this Mission's code —
  documented in the test file's own module docstring, and resolved by constructing the real,
  un-patched `TrackerService`/`SaaSTrackerService` directly for the US5 cells instead of routing
  through `CliRunner` for those specific cells (local US1-US4 cells are unaffected and go through
  the real CLI).
- 2026-08-03T00:00:00Z – python-pedro – Implemented
  `tests/sync/tracker/test_tracker_egress_refusal_3108.py` (T002-T007). Measured on the
  un-gated base (`.venv/bin/python -m pytest tests/sync/tracker/test_tracker_egress_refusal_3108.py -q`):
  **`21 failed, 19 passed in 67.61s`**. All 19 passes are the required positive controls (T004's
  seeded-push/unseeded-push/pull controls; US1 sc2, US2 sc1/sc3, US3 sc3/sc4-consenting, US4
  pull/run consenting controls; US5 sc3 and all four SC-005a cells, green throughout as required;
  US1 sc4's hosted-drain positive control; the two SC-020/forbidden-seam harness pins; the arming
  smoke test and the recorder hand-validation test). All 21 failures are the enumerated refusing
  pins, red for the intended reason (confirmed by reading each failure's captured argv/exception
  text, not the tally) — see the PR-body-equivalent enumeration in the final report. Re-ran inside
  `tests/sync/tracker/` alone (`549 passed`) and inside
  `tests/sync/tracker/ tests/agent/cli/commands/test_tracker.py` (`600 passed`): the failing-test
  set was byte-identical across all three runs (alone / tracker-dir / full-context diffed) — no
  `#3115`-class cross-test pollution attributable to this file. `ruff check` and
  `mypy --strict` both clean on the new file. **Correction (round 2): "zero suppressions" was
  inaccurate** — two narrowly-scoped `# noqa: TID251` (test-only sha256 content-identity/checksum
  helpers) exist, each with an inline rationale; not zero, but both individually justified.
- 2026-08-03T00:00:00Z – python-pedro – **Round-1 review verdict: REJECT** (coordinator relay).
  Two HIGH findings (F1, F2) required a fix; F3/F4/F7/F8/F9/F10 folded into the same pass; F5
  (bind-counter scope) and F6 (US5 CLI-bypass framing, docstring only) were the coordinator's to
  carry/amend. Fixed:
  - **F1** — `test_us1_sc4_hosted_drain_unaffected_by_tracker_key` compared a fixture with itself
    (neither arm had a real project root). Chose **option (A)**: each arm now gets its own real
    `.kittify/config.yaml` (one committing `tracker: {egress: refused}`, one with no tracker key)
    and the test `chdir`s into it. Recorded honestly in the test's own docstring that
    `BackgroundSyncService.drain_body_uploads_only` reads no repo root today, so this is a
    forward-looking guard, not a live discriminator — verified still passing after the fix.
  - **F2** — the wrapper-no-outcome-change test compared full captured argv across arms whose
    recorder-script *paths* are deliberately made to differ (to avoid capture-file collisions),
    so `argv[0]` guaranteed a mismatch once WP04 lands and unmasks it from the `AttributeError`.
    Added `_argv_without_recorder_path` and compare `argv[1:]`. Verified directly by replaying the
    reviewer's own simulation (skip the counter-install line entirely, as if WP04 had landed):
    `EQUAL (argv[0] stripped): True` — confirmed genuinely fixed, not still masked.
  - **F3** — added the missing NFR-002(a) non-vacuity control (consenting digest must differ) to
    `test_seeded_push_control_captures_exactly_3_argv_with_sentinel`.
  - **F4** — added refusal-text assertions to the three named cells
    (`test_sc4_unseeded_pair_refusing_creates_no_file_committed_red`,
    `test_pull_refusing_zero_argv_committed_red`,
    `test_run_refusing_zero_argv_neither_half_reaches_runner_committed_red`) and printed-state
    wording to all seven `TestUS6ExecutedRemedies` cells, distinguishing "no record" / "recorded
    refusal" / "not consentable". **While doing so, found and fixed a related, unflagged fixture
    defect**: several cells labelled "no record" used Hazard 8's *"not consentable"* recipe
    (`project.uuid` omitted) instead of the *"no record"* recipe (`project.uuid` present, no
    `sync:` block) — `test_sc1_no_record_no_tracker_key_refuses_committed_red`,
    `test_sc4_unseeded_pair_refusing_creates_no_file_committed_red`, and two of the three
    `TestUS6ExecutedRemedies` "no-record" cells. Fixed all four to use the correct recipe so the
    new wording pins actually probe the state their names claim.
  - **F7** — replaced the line-scoped regex (`[^\n]*`, blind past a newline; required the literal
    substring `monkeypatch.` so `mp.setattr(...)` never matched) with an `ast`-based
    `_iter_patch_call_sites` helper that walks `Call` nodes structurally. Verified directly against
    both cases the reviewer demonstrated (a continuation-line target, and an `mp.setattr(...)`
    alias) — both now detected.
  - **F8** — reordered all seven `TestUS6ExecutedRemedies` pre-remedy blocks (and the
    not-consentable hand-authoring test) so the captured-argv/sentinel assertion runs before the
    exit-code assertion; each red now prints the leaked bytes, not a bare boolean.
  - **F9** — corrected the "zero suppressions" claim above; two exist, both justified.
  - **F10** — this round's numbers below are quoted from a `git archive HEAD` clean-tree export
    (no WP02 working-tree changes present), per the coordinator's instruction.
  - **F6** (coordinator's, addressed as instructed) — amended the module docstring's "why
    construct directly instead of CliRunner" section to frame it explicitly as a **recorded
    departure from `plan.md` Stage 5's "run end to end through the CLI" clause**, resolved-negative
    on the CLI-literal reading and resolved-positive one layer below it — not a resolution.
  - **F5** — left as directed (coordinator carrying the "extend to every cell" obligation into
    WP04/WP05 dispatch); the file's own "Scope decision" docstring note is unchanged.

  **Round-2 measurements, all on a clean `git archive HEAD` export
  (`abca7ec96`-based commit `82fe338f6`, no WP02 changes present) with
  `PYTHONPATH=$WT/src`, `.venv/bin/python -m pytest`, unpiped and redirected:**
  - Alone: `21 failed, 19 passed in 87.60s` — **identical failing-test set** to round 1.
  - `tests/sync/tracker/` (this file only present, WP02's file absent on this clean export):
    `21 failed, 487 passed in 80.73s`.
  - `tests/sync/tracker/ tests/agent/cli/commands/test_tracker.py`:
    `21 failed, 538 passed in 84.95s`.
  - Failing-test sets diffed pairwise across all three (alone vs tracker-dir vs full-context):
    **byte-identical**, and no `FAILED` line outside this file in the full-context run.
  - `ruff check` and `mypy --strict`: both clean.
  - F1's fixed cell (`test_us1_sc4_hosted_drain_unaffected_by_tracker_key`) re-verified passing
    standalone: `1 passed in 50.50s`.
- 2026-08-03T00:00:00Z – python-pedro – **Round-2 review verdict: ACCEPT-WITH-FINDINGS.** Both
  HIGH findings independently re-verified by the reviewer (their own WP04-landed replay for F2:
  `EQUAL: True`; a purpose-built drain-consent mutant for F1: `assert 2 == 0` under mutant,
  `1 passed` without). Nothing above MEDIUM stood; escalation clock not engaged. Three small
  fixes requested before approval:
  - **F13** (regression from round 2, fixed for certain) —
    `test_no_record_remedy_tracker_egress_permitted_committed_red`'s remedy write still passed
    `project_uuid=None` while the pre-state (already fixed in round 2) used
    `project_uuid=CONSENTING_PROJECT_UUID`, so the remedy silently changed two things (stripped
    identity **and** added the Channel-2 grant) instead of the required one committed line. Fixed
    by keeping `project_uuid=CONSENTING_PROJECT_UUID` in the remedy write; updated the adjacent
    comment to stop claiming this cell demonstrates "needs no identity" (that claim correctly
    belongs to `test_not_consentable_remedy_channel2_grant_committed_red`, whose pre-state already
    has no identity).
  - **F11** (MEDIUM, fixed) — the five "no record" cells' wording pin
    (`"no record" in output or "Channel 1" in output`) was satisfiable by one undifferentiated
    "Channel 1 denies" message for all three Channel-1 states. Dropped the `or "Channel 1"` escape
    from all five (US3 sc1, US3 sc4-refusing, and the three US6 no-record cells); each now asserts
    `"no record" in output` directly.
  - **F12** (fixed) — `test_pull_refusing_zero_argv_committed_red` and
    `test_run_refusing_zero_argv_neither_half_reaches_runner_committed_red` still used
    `project_uuid=None` ("not consentable") while asserting the dead `"no record"` disjunct.
    Switched both to the "no record" recipe (`project_uuid=CONSENTING_PROJECT_UUID,
    sync_block=None`) to mirror US3 sc1, and — for consistency with the five cells F11 fixed —
    also dropped the `or "Channel 1"` escape from both, since after the recipe fix they are
    genuine "no record" cells too.
  - **F15** (one sentence, done) — added the honest limit to US1 sc4's docstring: the guard
    covers only a **cwd-shaped** regression (this cell's `chdir`-per-arm), not a
    `_drain_checkout_roots()`-shaped one, per `background.py:284-286`'s own record that a
    cwd-derived consent answer is this Mission's own defect class.
  - **F7-residual, F5, F6, F14** — not mine; routed/carried per the coordinator's message. No
    further action taken on them here.

  **Round-3 measurements, all on a clean `git archive HEAD` export (commit `c4b5b76c4` — verified
  via `git diff --stat 82fe338f6 HEAD -- src/ tests/` producing no output, i.e. no committed
  `src/`/`tests/` drift since round 1's base; the runtime's own status-transition commits on top
  are bookkeeping only) with `PYTHONPATH=$WT/src`, `.venv/bin/python -m pytest`, unpiped and
  redirected:**
  - Alone: `21 failed, 19 passed in 86.79s`.
  - `tests/sync/tracker/`: `21 failed, 487 passed in 72.47s`.
  - `tests/sync/tracker/ tests/agent/cli/commands/test_tracker.py`: `21 failed, 538 passed in 72.60s`.
  - Failing-test sets diffed pairwise across all three round-3 runs: **byte-identical**; no
    `FAILED` line outside this file in the full-context run.
  - Failing-test set diffed against round 2's: **byte-identical by name** (same 21 reds, same 19
    greens; counts unchanged at 487/538, confirming no fixture/wording edit flipped a result).
  - `ruff check` and `mypy --strict`: both clean.
