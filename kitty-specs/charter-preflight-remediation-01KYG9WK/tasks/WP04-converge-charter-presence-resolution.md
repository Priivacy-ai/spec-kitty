---
work_package_id: WP04
title: Converge charter-presence resolution onto the canonical seam
dependencies:
- WP03
requirement_refs:
- FR-004
- C-002
- C-003
- NFR-004
planning_base_branch: fix/charter-preflight-remediation
merge_target_branch: fix/charter-preflight-remediation
branch_strategy: Planning artifacts for this mission were generated on fix/charter-preflight-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/charter-preflight-remediation unless the human explicitly redirects the landing branch.
subtasks:
- T017
- T018
- T019
- T020
- T021
- T031
- T022
- T023
phase: Phase 4 - Diagnosability
history:
- at: '2026-07-26T23:24:39Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/charter/
create_intent:
- tests/charter/test_charter_presence_seam.py
execution_mode: code_change
owned_files:
- src/charter/bundle.py
- src/charter/context.py
- src/specify_cli/cli/commands/charter/_common.py
- src/specify_cli/cli/commands/charter/_status_collectors.py
- src/specify_cli/cli/commands/charter/status.py
- src/specify_cli/cli/commands/charter/resynthesize.py
- src/specify_cli/cli/commands/charter/context.py
- src/specify_cli/cli/commands/charter_bundle.py
- tests/charter/test_charter_presence_seam.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP04 – Converge charter-presence resolution

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent tasks status`).
- **You must address all feedback** before your work is complete.

---

## ⛔ Direction of fix — read this before touching anything

The operator's experience is: the gate blocks, but every diagnostic reports healthy. The *tempting*
reading is that the gate is wrong. **It is not.**

`src/specify_cli/charter_runtime/freshness/computer.py:295`:

> *"Landmine 2 (data-model.md): `charter.yaml` — not `charter.md` — is the authoritative, resolving
> charter source post-inversion. The historical `charter.md`-SHA-vs-`metadata.yaml::charter_hash`
> comparison is retired outright."*

The gate resolves the **authoritative** artifact. The diagnostics resolve the **retired** one.

**Therefore**: converge the diagnostics onto `charter.yaml`. Never the reverse. Converging onto
`charter.md` would re-open a decision the post-inversion work deliberately closed, and would stop the
gate resolving the authoritative source. If your change makes the gate read `charter.md`, you have
inverted the fix.

The mission spec's User Story 2 narrative reads as though the gate is the outlier. That narrative is
corrected in `research.md` R-001. Trust R-001.

## Objectives & Success Criteria

Complete when:

1. All **nine** operator-reachable charter-presence resolvers route through one canonical seam.
2. The seam is **non-mutating** — it answers without changing the project.
3. The resolver census is pinned so growth is visible.
4. Every operator-reachable surface returns the same answer for any project state.

## Context & Constraints

**C-002 (`DIRECTIVE_044`)**: converge onto a single canonical resolver. Teaching each non-canonical
surface to mimic the canonical one is an architectural violation, not a fix.

**C-003**: do not move, rename, or change the home of any charter artifact. This WP changes how
presence is *resolved and reported*, nothing else.

**The canonical seam already exists**: `charter.bundle.first_missing_bundle_file` (`bundle.py:199`)
is a pure existence check over the manifest's content-hash files — no content read, no hash, no
mutation. It has exactly one live caller today (`cli/commands/charter/_synthesis.py:530`). It is
correct, tested (`tests/charter/test_references_missing_failclosed.py`), and under-adopted. **Adopt
it. Do not author a new resolver.**

**Two of the nine sites mutate while answering.** Both call `ensure_charter_bundle_fresh` before
returning a presence answer. Neither is eligible to *be* the seam, and the consolidation must not
spread that side effect into the others.

### The nine operator-reachable resolvers (R-003)

| # | Site | Keys off | Mutates? |
|---|---|---|---|
| 1 | `charter_runtime/freshness/computer.py:303` — **the gate** | `charter.yaml` | no |
| 2 | `charter/context.py:200` (`build_charter_context`) | `charter.md` | **yes** |
| 3 | `cli/commands/charter/_common.py:33` | `charter.md` | no |
| 4 | `cli/commands/charter/status.py:56` | `charter.yaml` | no |
| 5 | `cli/commands/charter/_status_collectors.py:62,65` | both | no |
| 6 | `charter/sync.py:98,224` | both | n/a — the reporter itself |
| 7 | `cli/commands/charter_bundle.py:363` | `charter.yaml` | no |
| 8 | `cli/commands/charter/resynthesize.py:102` | `charter.yaml` | no |
| 9 | `charter/context.py:2975-2988` (`_project_charter_json_block`) | `charter.md` | **yes** |
| 10 | `charter/context.py:339-343` (`build_charter_context_include`, `--include section:<id>`) | `charter.md` | **yes** |

**Site 1 is the convergence target, not a site to change.** Site 6 is `sync.py`, which is the
staleness reporter itself — treat with care and change only if it genuinely resolves presence for an
operator-facing answer.

### Explicitly NOT a resolver — do not "fix" it

`_compact_section_block` (`context.py:2702-2717`) also reads `charter.md` and is **correctly**
excluded. Its docstring states why:

> *"The companion file is an optional display surface (a project's governance authority lives in
> `charter.yaml`), so a missing or unreadable `charter.md` degrades to the empty string rather than
> raising (NFR-005)."*

It reads the file as optional display content and degrades. It answers no presence question. Routing
it through the seam would be wrong. This is the criterion (R-007) that separates a resolver from a
content read — apply it if you find any further candidate site:

| It **is** a resolver when… | It is **not** when… |
|---|---|
| its existence check determines an operator-visible answer about whether the charter exists | it reads the file as optional display content |
| a missing file makes it fail, block, or report absent | a missing file degrades to empty/default, changing no presence answer |

**Migration-local resolvers are OUT OF SCOPE** (`m_3_2_0rc35_unified_bundle.py`,
`m_unify_charter_activation_finalize.py`, `m_3_1_1_charter_rename.py`). They have idempotency-shaped
definitions built for one-time migration, not health reporting. Pin the count; do not converge them.

## Branch Strategy

- **Planning base**: `fix/charter-preflight-remediation`
- **Merge target**: `fix/charter-preflight-remediation`

---

## Subtasks

### T017 — Establish the canonical presence API

**Purpose**: give every consumer one thing to call.

**Steps**:
1. Read `charter/bundle.py:199` (`first_missing_bundle_file`) and its tests fully before deciding
   anything.
2. Decide whether consumers call it directly or whether a thin, clearly-named presence accessor over
   it reads better at the call sites. Prefer the smallest change that gives one answer — do not build
   an abstraction layer for its own sake.
3. Whatever you choose must be **non-mutating**. No `ensure_charter_bundle_fresh` in the read path.
4. Export it properly — follow the repo's `__all__` declaration convention.

**Files**: `src/charter/bundle.py`

**Validation**:
- The seam performs no writes and triggers no sync
- Existing `first_missing_bundle_file` behaviour and its tests are unchanged

### T018 — Route the non-mutating CLI resolvers (sites 3, 4, 5)

**Purpose**: the bulk of the operator-facing surfaces, and the lowest-risk ones.

**Steps**:
1. `cli/commands/charter/_common.py:33` — currently `charter.md`. Route to the seam.
2. `cli/commands/charter/status.py:56` — currently `charter.yaml`. Route to the seam.
3. `cli/commands/charter/_status_collectors.py:62,65` — currently checks both. Route to the seam.
4. For each, verify the surrounding logic still makes sense: a site that branched on `charter.md`
   existence may have downstream code assuming that file specifically.

**Files**: `_common.py`, `status.py`, `_status_collectors.py`

**Validation**:
- Each site's answer now matches the gate's for all four fixture shapes
- No behaviour change for the healthy case (F3)

### T019 — Route the remaining non-mutating resolvers (sites 7, 8)

**Steps**:
1. `cli/commands/charter_bundle.py:363` — route to the seam.
2. `cli/commands/charter/resynthesize.py:102` — route to the seam.
3. Check site 6 (`charter/sync.py:98,224`). Determine whether these are operator-facing presence
   answers or internal to the reporter's own logic. Route only what genuinely answers the operator's
   question; record your reasoning either way.

**Files**: `charter_bundle.py`, `resynthesize.py`, possibly `src/charter/sync.py`

**Validation**:
- Answers match the gate across all four shapes
- `sync.py`'s reporter contract (always `synced=False`, `files_written=[]`) is unchanged

### T020 — Route `build_charter_context` (site 2, mutating)

**Purpose**: the highest-profile diagnostic — the one the issue cites as "returns the project's full
governance content" while the gate blocks.

**Steps**:
1. Read `charter/context.py:196-233`. Note it calls `ensure_charter_bundle_fresh(repo_root)` and
   then checks `canonical_root / CHARTER_MD`.
2. Route the **presence question** through the seam.
3. Decide deliberately what happens to the `ensure_charter_bundle_fresh` call. It may still be
   legitimate for the *content-loading* path — but it must not be what answers "does the charter
   exist". Separate the two concerns; record your reasoning.
4. **NFR-004**: this must continue to degrade to a reported state rather than raising to the
   operator. Do not introduce a new exception path.

**Files**: `src/charter/context.py`

**Validation**:
- The presence answer matches the gate for all four shapes
- No new uncaught exception path
- `charter context --action <x>` still returns governance content for a healthy project

### T021 — Route `_project_charter_json_block` (site 9, mutating)

**Purpose**: the resolver the post-plan gate caught after the first enumeration called the set
"closed" at eight. Do not skip it.

**Steps**:
1. Read `charter/context.py:2975-2988`. It sets `"present": charter_path.exists()` where
   `charter_path = bundle_root / CHARTER_MD`, and reaches `bundle_root` via `_bundle_root_for_json`,
   which calls `ensure_charter_bundle_fresh` first.
2. **Note the trap**: `_bundle_root_for_json` short-circuits to `None` (falling back to raw
   `repo_root`) precisely when `charter.yaml` is missing — the mission's trigger state. So this
   field's answer is structurally decoupled from the gate exactly where they must agree.
3. Route `project_charter.present` through the seam.
4. This is a distinct code path from site 2: `build_charter_context_json` (`:3077`) is a separate
   top-level function from `build_charter_context` (`:133`). Fixing site 2 does **not** fix this.
5. Verify the CLI surface: `cli/commands/charter/context.py:115,142` emits this via the documented
   `--json` flag.

**Files**: `src/charter/context.py`, `src/specify_cli/cli/commands/charter/context.py`

**Validation**:
- `spec-kitty charter context --action implement --json` reports `project_charter.present` in
  agreement with the gate, **specifically on the F2 legacy-bundle fixture**
- The rest of the JSON block's fields are unchanged for healthy projects

### T031 — Route `build_charter_context_include` (site 10, mutating, raises)

**Purpose**: the resolver the post-tasks gate caught — the third consecutive enumeration miss.

**Steps**:
1. Read `charter/context.py:306-345`. For `kind == "section"` it resolves `_bundle_root_for_json`
   (the same mutating helper as site 9), checks `canonical_root / CHARTER_MD`, and **raises**
   `ValueError("No charter.md found for section selector.")`.
2. Route the presence question through the seam.
3. **Fix the raise (NFR-004).** This is the mission's clearest instance of a diagnostic that raises
   at the operator instead of degrading to a reported state. Convert it to a caught, reported error
   at the CLI boundary, consistent with how the other surfaces behave.
4. This is a third distinct top-level function (`:306`), separate from `:133` and `:3077`. Fixing
   sites 2 and 9 does **not** fix this one.
5. This path is actively advertised: the compact-mode renderer tells operators to run
   `spec-kitty charter context --include …` (`tests/charter/test_context_section_bodies.py:183`).
   Existing coverage lives in `tests/cli/commands/test_charter_rendering.py` — update expectations
   there if behaviour changes.

**Files**: `src/charter/context.py`, `src/specify_cli/cli/commands/charter/context.py`

**Validation**:
- `spec-kitty charter context --include section:<id>` agrees with the gate on the F2 fixture
- A missing charter reports rather than raising a traceback at the operator
- `tests/cli/commands/test_charter_rendering.py` passes with updated expectations

### T022 — Pin the resolver census by criterion, not by list

**Purpose**: SC-003. **The count has now been wrong three times running** — the spec said two, plan
said eight, the corrected nine was still wrong. A hand-written list is the wrong instrument.

**This is `DIRECTIVE_043` applied to our own planning artifact**: close the class rather than fixing
the instance. A census test asserting against a list it also defines proves nothing — it is the
planning-artifact equivalent of the vacuous gate NFR-001 forbids.

**Steps**:
1. Implement the census as a **scan for the pattern**, using the R-007 criterion above: an existence
   check on a charter artifact that gates an operator-visible presence answer.
2. Assert every site the scan finds routes through the canonical seam.
3. Assert the current count is **10** operator-reachable and **3** migration-local — as the scan's
   *output*, not as its input.
4. Explicitly exclude `_compact_section_block` and any other optional-display-content read, with the
   criterion as the stated reason.
5. Comment why the numbers exist and that changing one is a deliberate reviewed act.

**The bar**: if someone adds a new hand-rolled `charter.md` existence check that gates an answer,
this test must go red **without anyone remembering to update a list**. If your implementation would
not catch that, it has not met the requirement — say so rather than shipping a list-shaped check.

**Files**: `tests/charter/test_charter_presence_seam.py` (new)

**Validation**:
- Adding a hand-rolled `charter.md`-existence check somewhere turns this red
- The comment explains the census rather than just asserting it

### T023 — Verify one answer, and a non-mutating seam

**Steps**:
1. For each of the four fixture shapes, ask every operator-reachable surface and assert they all
   agree.
2. Assert the seam is non-mutating: snapshot the fixture directory before and after a presence query
   and assert nothing changed.
3. Pay particular attention to F2 — the state where the surfaces previously disagreed. That is the
   regression test for the entire User Story 2.

**Files**: `tests/charter/test_charter_presence_seam.py`

**Validation**:
- All surfaces agree on all four shapes
- A presence query leaves the fixture byte-identical

---

## Definition of Done

- [ ] Every site confirmed operator-reachable routes through the canonical seam.
      **Site 6 (`sync.py`) is conditional on T019's finding**: either it is confirmed
      operator-facing and routed (count stays 10), or it is confirmed internal-only, is *not* routed,
      and the pinned count is deliberately revised to 9 with the reasoning recorded in the handoff.
      Do **not** force-route an internal-only check to satisfy a checkbox — the deliberate,
      reviewed count change is the correct outcome in that case.
- [ ] Site 9 (`_project_charter_json_block`) specifically verified on the F2 fixture
- [ ] Site 10 (`build_charter_context_include`) routed **and** its `ValueError` converted to a
      reported state (NFR-004)
- [ ] `_compact_section_block` left alone, with the R-007 criterion as the recorded reason
- [ ] The seam is non-mutating; proven by a before/after directory snapshot
- [ ] Census is criterion-derived and would catch a new hand-rolled resolver without a list update
- [ ] All surfaces agree across all four fixture shapes
- [ ] No charter artifact moved or renamed (C-003)
- [ ] No new uncaught exception path on any diagnostic surface (NFR-004)
- [ ] `uv run ruff check <changed files>` exits 0
- [ ] `uv run mypy --strict` shows no new errors versus the merge base
- [ ] Existing charter tests still pass

## Reviewer Guidance

1. **Check the direction of fix first.** If the gate (`computer.py`) now reads `charter.md`, or if
   any change makes `charter.md` authoritative, reject immediately — that inverts R-001 and re-opens
   a closed decision. `computer.py` should have **zero diff** in this WP.
2. **Verify site 9 was actually done**, on the F2 fixture specifically. It is the one an enumeration
   already missed once. Run `spec-kitty charter context --action implement --json` against a
   legacy-bundle fixture and compare `project_charter.present` to the gate's answer.
3. **Verify the seam is non-mutating.** Snapshot a fixture, query presence, diff. Any write is a
   failure — it would spread a side effect into every consumer.
4. **Verify consolidation, not parity-patching** (C-002). If each site got its own copy of the same
   `charter.yaml` check rather than calling one seam, that is the architectural violation the
   directive names, and must be rejected.
5. **Check the census test is not self-satisfying — this is the highest-value review action here.**
   The count has been wrong three times running. Test it: add a throwaway function elsewhere that
   does its own `charter.md` existence check gating an answer, and confirm T022 goes red *without
   you updating any list*. If it stays green, the census is list-shaped and must be rejected.
6. **Verify `_compact_section_block` was left alone.** If the implementer routed it through the seam,
   they misapplied the criterion — it is optional display content that degrades, not a resolver.
7. **Verify site 10's raise is gone.** `charter context --include section:<id>` against a project
   with no charter must report, not raise. This is the NFR-004 instance.
8. **On site 6**: if T019 concluded it is internal-only, confirm the pinned count was deliberately
   revised to 9 with reasoning recorded — and that it was *not* force-routed to tick a checkbox.
6. **C-003**: grep the diff for file moves or renames under `.kittify/charter/`. There must be none.
