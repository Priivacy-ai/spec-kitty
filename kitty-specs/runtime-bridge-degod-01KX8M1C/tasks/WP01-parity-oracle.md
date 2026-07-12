---
work_package_id: WP01
title: Parity oracle (WP-0a, BLOCKING safety net)
dependencies: []
requirement_refs:
- FR-002
- NFR-001
- NFR-006
- C-004
tracker_refs:
- '2531'
planning_base_branch: design/runtime-bridge-degod
merge_target_branch: design/runtime-bridge-degod
branch_strategy: Planning artifacts for this mission were generated on design/runtime-bridge-degod. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/runtime-bridge-degod unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-runtime-bridge-degod-01KX8M1C
base_commit: 000a0825c2062e9d0db9cdb5df8b85fbd35eeee9
created_at: '2026-07-11T14:29:43.440476+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
phase: Extraction spine
shell_pid: '1263853'
history:
- at: '2026-07-11T00:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/runtime/
create_intent:
- tests/runtime/test_bridge_parity.py
- tests/runtime/_bridge_oracle.py
- tests/runtime/fixtures/bridge/README.md
execution_mode: code_change
owned_files:
- tests/runtime/test_bridge_parity.py
- tests/runtime/_bridge_oracle.py
- tests/runtime/fixtures/bridge/README.md
role: implementer
tags: []
task_type: implement
---

# WP01 — Parity oracle (WP-0a, BLOCKING safety net)

## Context

This is the **load-bearing safety net for the entire mission** (#2531). Every
extraction WP (WP03–WP10) edits `src/runtime/next/runtime_bridge.py` by moving
symbols out of it; the only thing that proves those moves are
**behavior-preserving** (C-001) is this parity oracle re-run green as each
extraction's acceptance gate. Build it **now, against unmodified source**, and
prove it green at the full coverage floor before anyone touches the god-module.

Read `contracts/parity-oracle.md` — it is the authority for this WP and MUST be
implemented **verbatim** (masking contract, 3-entry harness, capture-and-assert
side effects, per-entry sub-ledgers, coverage floor, reason-normalizer meta-test,
NFR-006 timing seed). `research.md §Parity` is the derivation; `data-model.md`
describes `Decision.to_dict()` shape.

**Why the oracle must drive all three public entries.** The 29 `Decision(...)`
sites are **partitioned across three public entry points**, not concentrated in
`decide_next`:

| Public entry | Site | Owns (Decision sites) | Own side effects |
|--------------|------|-----------------------|------------------|
| `decide_next_via_runtime` | `runtime_bridge.py:2524` | ~15 sites (11 constructed directly `:2545–3015` + the WP-iteration path) | sync emit `:2556`, coord commit `:2563` |
| `query_current_state` | `runtime_bridge.py:3199` | the **4** `_build_*_query_decision` sites (`:3059`/`:3111`/`:3136`/`:3166`), reached **exclusively** here | none (read-only) |
| `answer_decision_via_runtime` | `runtime_bridge.py:3355` | remaining sites incl. the **10** `_map_runtime_decision` sites (`:3582–3798`, CC33) + `_build_wp_iteration_decision` (`:3468–3536`) | own sync emit `:3410`, snapshot seed via `_read_snapshot` `:3418`, coord commit `:3427` |

An oracle that drives `decide_next_via_runtime` alone leaves ~14 sites (including
the CC33 `_map_runtime_decision` cluster) unexercised → **WP-0 falsely green** →
silent drift in WP07. This is a hard failure mode; the coverage floor below
guards against it.

**Reuse the canonical surfaces.** Drive the real public functions from
`runtime.next.runtime_bridge`; never re-implement decision logic. The runtime
planner (`next_step` / `get_or_start_run`) is **never stubbed** — it is the logic
under test. Do not copy fixture shapes from older missions; build frozen repo
snapshots from realistic mission trees (production-shaped ULIDs, slugs, and file
lengths).

**Red-first note.** This oracle is built on **unmodified source**, so its final
state is GREEN, not red. But the coverage-floor assertion (T004/T006) is the
part that must be authored **red-first against a hollow harness**: write the
count assertion first, watch it FAIL against a stub that drives zero sites, then
fill the sub-ledgers until the tallies meet the floor. A hollow oracle is also
green on unmodified source — proving the floor tripped and then cleared is what
makes green meaningful.

## Ordered steps

### T001 — `canonical(decision, repo_root)` masking (`_bridge_oracle.py`)
Implement the equality contract over `Decision.to_dict()` (`decision.py:82–166`)
exactly as `contracts/parity-oracle.md §Equality contract` specifies:
- **MASK** (drop before compare, but keep None-vs-present so a kind-shape change
  is not blinded): `timestamp` (`bridge:2542`), `run_id`, `decision_id` (ULIDs).
- **PATH-NORMALIZE** (relativize to **each run's own `repo_root`** — the copytree
  temp dirs differ per fixture, so the normalizer takes the run's root, never a
  shared constant): `workspace_path`, `prompt_file`, **`reason`** (the non-obvious
  carrier — it embeds `feature_dir`/`exc` paths), `origin.mission_path`
  (`bridge:2575`). NB `origin.mission_tier` stays **STABLE**.
- **STABLE** (compare as-is): everything else — `kind`, `agent`, mission identity,
  `state`, `action`, `wp_id`, `step_id`, `guard_failures` (content **and order**),
  `progress`, `question`/`options`, `is_query`, …
Expose `assert_parity(before, after, repo_root)` ==
`canonical(before, root) == canonical(after, root)`.

### T002 — 3-entry harness (`_bridge_oracle.py`)
Build a harness that, per fixture, does a fresh `copytree` of a frozen repo
snapshot into a temp dir with a **fixed per-run `repo_root`**, then drives the
requested public entry among `decide_next_via_runtime` (`:2524`),
`query_current_state` (`:3199`), `answer_decision_via_runtime` (`:3355`). Run
create/advance (`get_or_start_run`) runs **REAL** on the throwaway copy — its
ULID is masked by T001, not stubbed. Return the raw `Decision` plus the captured
side-effect payloads (T003) so the test module can assert parity. **Never stub
`next_step`.**

### T003 — CAPTURE-and-assert side effects (`_bridge_oracle.py`)
Side effects are captured with **binding equality on the recorded payloads**, not
merely stubbed — a refactor that changes *what* is emitted/committed can still
return an identical `Decision` and pass otherwise. Capture and expose for
assertion (per `contracts/parity-oracle.md §Side-effect isolation`):
- the `decide_next` sync emitter (`bridge:2556`) and its coord-branch
  `DecisionGitLog` commit (`bridge:2563`);
- the retrospective `Confirm.ask` gate;
- the **answer-path** emitter (`bridge:3410`) and coord-branch commit
  (`bridge:3427`);
- the engine mutations relocated in IC-02 — `_append_event` / `_write_snapshot`
  (and the `_read_snapshot` snapshot seed at `:3418`).
A change to captured emitted/committed content = a parity break = reject.

### T004 — Per-entry fixture sub-ledgers + coverage floor as a checkable count (`test_bridge_parity.py`)
Author the fixture matrix as **three sub-ledgers keyed by owning entry**. The
matrix (`contracts/parity-oracle.md §Fixture matrix`):
- **29 `Decision(...)` sites**: 19 blocked / 4 step / 4 query / 1 terminal / 1
  decision_required, across 7 orchestrator phases, partitioned by owning entry.
- Both guards fully branched: `_check_cli_guards` (`:1057`, ~10 branches incl. the
  requirement-ref cross-check) and `_check_composed_action_guard` (`:1515`) across
  **3 mission families** (software-dev / research / documentation), including
  **both fail-closed defaults** and the 4-way `tasks` `legacy_step_id` union.
- Ledger ≈ **22–26 fixtures** across the three sub-ledgers.
**Coverage floor (binding, red-first):** every Decision site reached ≥1× AND
every guard branch reached ≥1× — **each reached from its owning entry**. Assert
the floor as a **checkable count**: tally sites/branches actually reached and
`assert reached >= floor`. Write this assertion first and watch it FAIL against a
still-empty ledger; only then fill fixtures until it passes. **Named
highest-risk fixtures**: the two fail-closed defaults + the `tasks` legacy-union —
each asserts identical `guard_failures` **content and order** before/after.

### T005 — `reason`-normalizer meta-test (`test_bridge_parity.py`)
Path-relativizing free text can swallow a genuine `reason`/field change, blinding
the oracle. Ship a **normalizer meta-test** proving `canonical()`:
- **COLLAPSES** pure path noise — two runs under different copytree roots with the
  same logical decision compare **equal**; AND
- does **NOT** collapse a **semantic** delta — a changed `reason` phrase, or any
  STABLE-field flip, compares **unequal**.
This is red-first by construction: the "must be unequal" half fails if the
normalizer over-collapses, which is exactly the self-blinding bug to prevent.

### T006 — NFR-006 timing seed + prove GREEN at full floor (`test_bridge_parity.py`)
Seed the NFR-006 before/after timing harness on the matrix (a `decide_next()`
before/after timing capture that stays within noise; WP10 asserts the after side).
Then run the full oracle on **unmodified source** and confirm it is GREEN at the
full coverage floor across all 3 entries. Document the fixture-snapshot layout and
regeneration procedure in `tests/runtime/fixtures/bridge/README.md` (what each
frozen snapshot represents, per-entry sub-ledger membership, how to rebuild).

## Acceptance
- Oracle **green on unmodified source** across all 3 public entries.
- Coverage floor asserted as a **checkable count** (sites + guard branches reached
  ≥ floor, each from its owning entry) — proven to have tripped red against a
  hollow harness before clearing.
- `reason`-normalizer meta-test green (collapses path noise, rejects a semantic
  delta).
- Captured side effects (sync emit, coord commit, retrospective, answer-path
  emit/commit, engine `_append_event`/`_write_snapshot`) assert binding equality.
- NFR-006 timing harness seeded on the matrix.
- `ruff` + `mypy` clean on new files; no `# noqa` / `# type: ignore` added.

## Safeguards
- **A hollow oracle is also green on unmodified source** — green-on-unmodified is
  necessary but NOT sufficient. The coverage floor MUST be asserted as a count.
- **Drive ALL 3 entries.** Driving `decide_next` alone can never reach the
  query/answer-only sites (the `_build_*_query_decision` family and the
  `_map_runtime_decision` cluster) → false-green WP-0.
- **Never stub `next_step`** — it is the logic under test.
- Per-run `repo_root` normalization only — never a shared path constant, or
  cross-fixture comparisons will spuriously differ.
- Use realistic, production-shaped fixture data (ULIDs, slugs, tasks.md lengths);
  placeholder data masks real behavior.

## References
- `contracts/parity-oracle.md` — authoritative contract (implement verbatim)
- `research.md:41-57` §Parity (derivation, fixture matrix, coverage floor)
- `data-model.md:15-18` (Decision-builder shape, non-deterministic fields)
- `src/runtime/next/runtime_bridge.py:2524` `decide_next_via_runtime` (entry 1; sync emit `:2556`, coord commit `:2563`, timestamp `:2542`, origin.mission_path `:2575`)
- `src/runtime/next/runtime_bridge.py:3199` `query_current_state` (entry 2; owns the 4 query builders `:3059`/`:3111`/`:3136`/`:3166`)
- `src/runtime/next/runtime_bridge.py:3355` `answer_decision_via_runtime` (entry 3; emit `:3410`, snapshot seed `:3418`, coord commit `:3427`)
- `src/runtime/next/runtime_bridge.py:3555` `_map_runtime_decision` (10 sites `:3582–3798`, CC33)
- `src/runtime/next/runtime_bridge.py:1057` `_check_cli_guards`, `:1515` `_check_composed_action_guard` (both guards, all branches)
- `src/runtime/next/decision.py:82-166` `Decision.to_dict()` (masking surface); `:129` `__post_init__` (`Path(prompt).is_file()`)

## Activity Log

- 2026-07-11T16:42:20Z – user – shell_pid=1263853 – Moved to for_review
- 2026-07-11T17:10:22Z – user – shell_pid=1263853 – Moved to approved
