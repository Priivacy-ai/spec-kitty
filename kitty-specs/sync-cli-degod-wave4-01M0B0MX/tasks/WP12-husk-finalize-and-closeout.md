---
work_package_id: WP12
title: Husk finalize + governance closeout
dependencies:
- WP11
requirement_refs:
- C-005
- FR-007
- FR-008
- NFR-004
planning_base_branch: refactor/wave4-sync-degod
merge_target_branch: refactor/wave4-sync-degod
branch_strategy: Planning artifacts for this mission were generated on refactor/wave4-sync-degod. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into refactor/wave4-sync-degod unless the human explicitly redirects the landing branch.
subtasks:
- T023
- T024
- T025
history:
- Created by /spec-kitty.tasks (Wave-4 sync degod)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/sync.py
create_intent:
- docs/plans/code-quality/sync-env-census.md
- tests/architectural/test_sync_env_census.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/sync.py
- docs/plans/code-quality/sync-env-census.md
- tests/architectural/test_sync_env_census.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Load your profile before anything else: `/ad-hoc-profile-load python-pedro`. Then run
`spec-kitty charter context --action implement --json` and apply the resolved
directives/tactics. State in your first status note which directives/tactics you applied
(expect `DIRECTIVE_001`/`043` architectural-gate discipline, `DIR-013` open-an-issue-for-inherited-red,
and the canonical-sources / no-improvise directive front-of-mind — this WP re-pins governance
baselines and must not green-wash inherited red).

## Objective

The tail of the mission: finalize the `cli/commands/sync.py` **husk** and close out governance.
After WP03-WP11 the file is the Typer `app` host + the guarded re-export/late-bind block + the 22
`@app.command` thin shells; the decision logic now lives under `specify_cli.sync.*`. This WP
(a) confirms the husk shape and re-pins every arch-gate baseline against the **true merge-base
(`upstream/main`)**, treating each relocated writer as a **1:1 census-key swap** (not a net add);
(b) produces the `SPEC_KITTY_*` env census with an **executable** anti-deletion guard (FR-007);
and (c) files the deferred follow-on issue(s) at merge (FR-008). **No env var is deleted** (WS6);
no daemon-lifecycle behavior changes (WS4).

## Read first (source of truth)

The mission `plan.md` — IC-06 ("Husk finalize + governance closeout"; re-pin against
`upstream/main` not stale fork origin; DIR-013 for inherited red; husk measured against a
**separate, larger LOC ceiling** than the extracted modules, A-6) and the Structure Decision
(the husk keeps the `app` host + guarded re-export; `@app.command` shells stay). The contract item
**5/6** (env set-unchanged, `research/env-census.md` — but see the path note below). `data-model.md`
INV-3 (boundary), INV-5 (≤800 LOC for the *focused* modules, husk on its own ceiling), INV-6
(frozen deferrals). `research/squad-findings-post-plan.md` A-5 (per-writer 1:1 census-key swap),
A-6 (husk ceiling), Pr-5 (FR-007 must be executable). **Zero behavior change** — this WP re-pins
baselines to reflect the relocation; it must never loosen a gate to hide a real regression.

## Environment (CRITICAL — worktree vs editable install)

Work in the lane worktree. The repo-root `.venv` editable-install points at the MAIN checkout,
so test YOUR changes with `PYTHONPATH=<worktree>/src`. Define `VENV=<repo>/.venv/bin; WT=<worktree>`.

Arch-gate + env-census tests:

```
SPEC_KITTY_ENABLE_SAAS_SYNC=1 PWHEADLESS=1 SPEC_KITTY_SYNC_DISABLE=1 PYTHONPATH=$WT/src \
  $VENV/python -m pytest \
  tests/architectural/test_sync_env_census.py \
  tests/architectural -k "sync or writer_census or dead_symbol or golden_count or ratchet or visible_count" \
  -q -p no:cacheprovider
```

Establish the merge-base baseline by running the same arch-gate on `upstream/main` via
`PYTHONPATH=<merge-base-checkout>/src` — a red there is **inherited**, not yours (open an issue
per DIR-013 before treating it as baseline). Lint/type:

```
$VENV/ruff check $WT/src/specify_cli/cli/commands/sync.py
$VENV/mypy --strict $WT/src/specify_cli/cli/commands/sync.py
```

NEVER run the full suite or `uv run`. Run daemon/real-port arch tests `-n0`.

## Subtasks

### T023 — Finalize the husk; re-pin arch-gate baselines vs `upstream/main`

**Purpose**: confirm the husk shape and update every arch-gate baseline so it reflects the
post-degod module topology — without loosening any gate.

**Steps**:

- **Husk shape**: verify `cli/commands/sync.py` is the `app` host + the guarded re-export/late-bind
  block + the 22 `@app.command` shells only. Measure it against the **separate, larger LOC ceiling**
  agreed for the app-host husk (A-6) — the SC-001 ≤800 applies to the focused `sync_*` modules, not
  the husk. Confirm each extracted module is ≤800 LOC.
- **Re-pin against the merge-base (`upstream/main`)**, not stale fork origin:
  - dead-symbol / dead-module baselines;
  - the DIR-041 ratchet `_baselines.yaml`;
  - the golden-count `_golden_count_baseline.json`;
  - the CLI-count `test_real_typer_app_visible_count` (still 22 commands — no command added/removed);
  - the sync-writer census (`test_sync_writer_census.py`).
- **Writer census = 1:1 key swaps (A-5)**: each relocated consent/grant writer drops its old
  `relpath::qualname::…` key and adds the equivalent post-relocation key — a **swap, never a net
  add**. Verify per-writer; a net addition means a writer was duplicated, not moved.
- **Inherited red (DIR-013)**: if the merge-base arch-gate is already red, open a tracking issue
  **first** and record it; do not fold a pre-existing red into your re-pin or green-wash it.

**NOTE — shared arch-gate surfaces (out-of-map edits)**: `_baselines.yaml`,
`_golden_count_baseline.json`, and the writer-census/CLI-count baseline artifacts are **shared**
arch-gate files. They are deliberately **NOT** in this WP's `owned_files` (to avoid cross-mission
lane overlap). Edit them as **small, individually-justified out-of-map edits**, each with a one-line
rationale in the commit/PR body naming the relocation that necessitated it.

**Files**: `src/specify_cli/cli/commands/sync.py` (husk confirm); the shared baseline artifacts
(out-of-map, justified).

**Validation**: the full arch-gate suite green on this branch; each baseline delta traceable to a
relocation; no gate loosened.

### T024 — `SPEC_KITTY_*` env census + executable anti-deletion guard (FR-007)

**Purpose**: prove the mission deleted **no** environment variable (WS6 defers env retirement).

**Steps**:

- Write the census to **`docs/plans/code-quality/sync-env-census.md`** — NOT `kitty-specs/…`
  (lanes cannot write into `kitty-specs/`; this is a deliberate path relocation from the plan's
  `research/env-census.md` phrasing). List **every** `SPEC_KITTY_*` reference on the sync surface,
  each with a **live** or **retire-candidate** verdict (inventory + verdict only — no deletion).
- Write `tests/architectural/test_sync_env_census.py` — an **executable** guard (Pr-5: prose is not
  enough) asserting the **SET** of `SPEC_KITTY_*` references on the sync surface is **unchanged**
  by the mission (the anti-deletion proof, FR-007). Compute the set by scanning the sync module(s)
  and compare to a frozen expected set; a removed var fails the test.
- **Delete NO var (WS6)**: retire-candidates are *documented*, not acted on — that is a WS6/follow-on
  concern (T025), not this mission.

**Files**: `docs/plans/code-quality/sync-env-census.md` (new); `tests/architectural/test_sync_env_census.py`
(new).

**Validation**: the env-set-unchanged guard green; the census lists every `SPEC_KITTY_*` ref with a
verdict; `git diff` shows no env-var removed from the sync surface.

### T025 — File the deferred follow-on issue(s) (FR-008, at merge)

**Purpose**: hand the explicitly-deferred work to tracked children so the deferral is auditable.

**Steps** (perform at merge, per FR-008):

- File the **adapter-consolidation** follow-on — the `emitter` / `transport_attempts` / `queue` /
  daemon internals that this mission deliberately kept out of scope (WS4 / WS6 / the #2173-Phase-2
  boundary).
- File the **env retirement-candidates** follow-on — the vars T024 flagged as retire-candidates,
  to be actioned under WS6 (never in this mission).
- Parent both as **tracked children under the degod-delivery epic #1797** (advancing #1619).
- **Reference the filed issue link(s) in the PR body** so a later agent does not re-discover the
  deferral.

**Files**: none in-repo (tracker action) — the link is recorded in the PR body.

**Validation**: the follow-on issue(s) exist under #1797, referenced from the PR body.

## Branch Strategy

Planning/base + merge target: `refactor/wave4-sync-degod`. The execution worktree is allocated per
the computed lane from `lanes.json` (`spec-kitty implement WP12` prepares it) — do not reconstruct
the path. This is **lane-c**, the final position in the serial chain; it edits the single `sync.py`
and depends on WP11 (rebase on its shrunk file). Not a parallel lane.

## Definition of Done

- [ ] `cli/commands/sync.py` is the husk (app host + guarded re-export/late-bind + 22
      `@app.command` shells) under its separate larger LOC ceiling; every extracted `sync_*` module
      ≤ 800 LOC.
- [ ] All arch-gate baselines (dead-symbol/module, ratchet `_baselines.yaml`, golden-count,
      CLI-count 22, writer-census) re-pinned vs **`upstream/main`**; writer-census deltas are
      **1:1 key swaps**; no gate loosened; any inherited red has a DIR-013 tracking issue.
- [ ] Shared baseline artifacts edited as justified out-of-map edits (one-line rationale each).
- [ ] `docs/plans/code-quality/sync-env-census.md` lists every `SPEC_KITTY_*` ref with a
      live/retire-candidate verdict; **no var deleted** (WS6).
- [ ] `tests/architectural/test_sync_env_census.py` executable env-set-unchanged guard green (FR-007).
- [ ] Deferred follow-on issue(s) (adapter-consolidation WS4/WS6 + env retirement-candidates) filed
      under epic #1797 / advancing #1619 and linked in the PR body (FR-008).
- [ ] Full arch-gate suite + env-census guard green; `ruff`/`mypy --strict` clean.

## Reviewer Guidance

- **DIR-013 (inherited red)**: confirm the re-pin used `upstream/main` as the merge-base and that
  any pre-existing red got a tracking issue **before** being treated as baseline — reject any
  baseline change that hides a real regression.
- **A-5 (census swaps)**: verify each writer-census delta is a drop-old-add-equivalent **swap**, not
  a net addition — a net add means a writer was duplicated, not relocated.
- **A-6 (husk ceiling)**: confirm the husk is judged against its separate larger ceiling and the
  focused modules are each ≤ 800.
- **Pr-5 (executable guard)**: `test_sync_env_census.py` must actually scan and compare the env set,
  not merely assert on the markdown; a removed var must make it fail.
- **WS6 / INV-6**: confirm **zero** `SPEC_KITTY_*` var was deleted and no daemon-lifecycle behavior
  changed — retire-candidates are documented + deferred, not actioned.
- **FR-008**: confirm the follow-on issue link(s) are in the PR body and parented under #1797.


## Post-tasks squad corrections (BINDING)
- **Rn-5:** add an assertion (a check or a test) that **no non-monster command body exceeds complexity 15** after all helpers extract — run `ruff --select C901` over the whole final `sync.py` and confirm ZERO `C901` findings remain (the 3 monster suppressions gone AND no other command tripped the ceiling). This verifies "absorbed, not evaporated".
- **Rn-3/Pr-2:** the arch-gate baseline data files (`tests/architectural/_baselines.yaml`, `_golden_count_baseline.json`, `_inert_slots_baseline.yaml`, `test_sync_writer_census.py`) you re-pin are authorized **small, individually-justified out-of-map edits** (record a one-line rationale each); they are intentionally not in `owned_files` (shared arch-gate surfaces, cross-mission).
