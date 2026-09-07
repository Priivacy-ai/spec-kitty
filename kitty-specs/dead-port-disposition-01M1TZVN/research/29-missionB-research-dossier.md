<!-- Provenance: copied from work/post-convergence/29-missionB-research-dossier.md (spec-kitty repo) -->
<!-- Copied: 2026-09-06 for mission dead-port-disposition-01M1TZVN; content unmodified below this header. -->
<!-- Verified-at: repo HEAD e721763759 (tree 3.2.7rc1), per the dossier's own verification log. -->
# 29 — Mission B Research Dossier: `dead-port-disposition` (Researcher Robbie, 2026-09-06)

**Repo:** `spec-kitty` · tree `3.2.7rc1` (HEAD `e721763759`) · **Mode:** READ-ONLY consolidation;
this file is the single permitted write. **Sources:** reports 20, 21, 24 (§4 dispositions —
authoritative where reports conflict), 25, 27 in this directory; every carried-forward `file:line`
below **re-verified against the tree at HEAD** (deltas from the reports are marked ⚠ VERIFIED-DELTA).

**Mission framing:** adjudicate and clean the core loop's dead/dormant hook seams. Sequenced
**AFTER Mission A** `fsm-write-path-integrity` (shared files: `runtime_bridge_io.py`,
`_internal_runtime/engine.py`, `decision.py`, `runtime_bridge_engine.py` — NOT parallel-safe,
report 24 §5). The **RuntimeEventEmitter disposition ADR is being drafted in a parallel session
and is an INPUT DEPENDENCY of this mission** — nothing here decides it; §3 splits work into
ADR-safe vs ADR-BLOCKED.

---

## 1. The `transitions`-library slice (mission-DSL v1)

### 1.1 The binding constraint — the eager import chain (verified, empirically)

`specify_cli/mission_v1/__init__.py` **eagerly imports every submodule**:

```
__init__.py:21  from specify_cli.mission_v1.compat  import PhaseMission        → compat.py:23  from transitions import Machine
__init__.py:22  from specify_cli.mission_v1.events  import emit_event, read_events   (no transitions import)
__init__.py:23  from specify_cli.mission_v1.guards  import compile_guards            (no transitions import — docstring refs only)
__init__.py:24  from specify_cli.mission_v1.runner  import MissionModel, StateMachineMission
                                                     → runner.py:15-16  from transitions import MachineError / MarkupMachine
__init__.py:25-29  from specify_cli.mission_v1.schema import …                       (no transitions import)
```

⚠ VERIFIED-DELTA: reports 24/25 cite the eager block as `:20-23` (runner + compat); at HEAD it is
**lines 21-29 and covers all five submodules** (compat, events, guards, runner, schema). The WP
must break the whole eager block, not two lines.

**Hot-path proof (re-run in the repo venv this session):**
`import specify_cli.mission_v1.events` ⇒ `transitions` AND `six` land in `sys.modules`, plus all
five `mission_v1.*` submodules. The two live production imports —
`runtime/next/next_invocation_lifecycle.py:332` (`emit_event`, the `MissionNextInvoked`
observability write on every `spec-kitty next`) and `runtime/next/decision.py:200` (`read_events`,
inside the `.. deprecated:: 2.0.0` `derive_mission_state`) — therefore load the `transitions`
library on every invocation. **Deleting files without trimming `__init__` frees nothing; trimming
`__init__` without deleting the files leaves ~1,190 LOC of test-only code. Both, together, or
neither.**

### 1.2 What production actually uses — reconciliation of 20 vs 21/25

Report 20 §1.2 listed `events` + `guards` as live; report 25 said `events` only. **Resolution
(verified): production *imports* = `events.py` only** (the two lazy sites above). `guards.py` has
zero production imports; its "liveness" in report 20 is prose:

- `review/gate_registry.py:7,132` reference `mission_v1.guards.GUARD_REGISTRY` /
  `compile_guards` **inside docstrings only** — a shape-precedent citation, not a dependency.
- ⚠ VERIFIED-DELTA (coupling no report named): `tests/specify_cli/test_wp_frontmatter_fold.py:60`
  **enumerates `("specify_cli.mission_v1.guards", "read_wp_frontmatter")` in the
  tolerant-frontmatter-reader fold gate's list** — deleting `guards.py` requires editing that
  architectural gate in the same PR.
- `schema.py` is imported by `tests/research/test_research_plan_missions_integration.py:21` and
  `tests/missions/test_mission_software_dev_integration.py:21`, which run `validate_mission_v1`
  over the **built-in packs'** `mission.yaml` files — the only "interpreter" the orphan pack DSL
  blocks have (see §1.4). `skills/manifest_store.py:27` mentions `mission_v1.schema` in a
  docstring only.

Dead-symbol gate already grandfathers the public trio (`MissionProtocol`, `load_mission`,
`load_mission_by_name`) at `tests/architectural/test_no_dead_symbols.py:718-727` (verified —
report's `:720-727` is one comment-line off; the pins are real).

### 1.3 Retirement extent — the two scoping options on the table

| | Option MIN (report 24 §4) | Option FULL (report 25 §1c) |
|---|---|---|
| Delete | `runner.py` (252), `compat.py` (158), eager `__init__` block + `load_mission`/`load_mission_by_name` dispatch (~120 of 154) | MIN + `guards.py` (382) + `schema.py` (299) |
| Keep | `events.py` (93, live), `guards.py` (shape-precedent), `schema.py` | `events.py` only |
| Test blast | `test_mission_v1_runner_unit`, `test_mission_v1_compat_unit`, `test_e2e_mission_v1_integration`, `test_mission_loading_integration`, `test_mission_v1_events_unit` (imports `runner` at :228-304 — trim, don't delete: the events half stays live) | MIN + `test_mission_v1_guards_unit`, `test_mission_guards_integration`, `tests/specify_cli/mission_v1/test_guards_bulk_edit.py`, `test_mission_v1_schema_unit`, `test_research_plan_missions_integration` + `test_mission_software_dev_integration` (schema-validation halves), `test_wp_frontmatter_fold.py:60` gate entry, `_gate_coverage.py:1456` shard row |
| Frees `transitions` pin | **YES** — the only `import transitions` lines are runner:15-16 and compat:23 | YES |

Either option drops the pin; FULL additionally forces the pack-DSL and gate-list decisions.
`decision.py`'s two `.. deprecated:: 2.0.0` functions (`derive_mission_state:~187`,
`evaluate_guards:~218`) are the dead DSL readers — zero callers verified (`runtime_bridge_cores`'
`evaluate_guards*` family is an unrelated same-name function) — but `decision.py` is a
**Mission-A shared file**: their deletion rides whichever lane owns it (§6).

### 1.4 Pack-DSL honesty note (verified mechanics)

`packs/built-in/missions/{software-dev,plan,research}/mission.yaml` each ship orphan
`states:`/`transitions:` blocks. ⚠ VERIFIED-DELTA: the v0 loader does **not** choke on them —
`specify_cli/mission.py:59-67` (`MISSION_COMPAT_IGNORED_FIELDS`) strips exactly these keys before
Pydantic `extra="forbid"` validation (`mission.py:260-261`). So the blocks are inert *and
tolerated*; after retirement their only reader anywhere is gone. Disposition choices: delete the
blocks (and keep `MISSION_COMPAT_IGNORED_FIELDS` for third-party hybrid YAMLs), or keep them with
an in-file comment naming them uninterpreted. Interview question (§7).

### 1.5 Dependency-removal mechanics

- `pyproject.toml:82` — `"transitions>=0.9.2"` with justification comment; delete the line.
- `uv.lock` — `transitions 0.9.3` (lock ~:2687) plus its dep edge on `six`. ⚠ `six` **stays** in
  the lock: `python-dateutil` also depends on it (lock ~:1894). Regenerate with `uv lock`; do not
  hand-edit.
- Dependency change ⇒ version bump in `pyproject.toml` + `CHANGELOG.md` entry (house rule).
- **Clean-install CI**: the `clean-install-verification` job and
  `tests/architectural/test_pyproject_shape.py` are the surfaces that notice; run them in the WP's
  blast radius. `truststore` removal (report 25 H6) is the **quick-wins PR's** item, not this
  mission's — do not bundle (one dependency change per PR keeps the lock diff reviewable).
- Gate edits in the same PR: drop the 3 `test_no_dead_symbols.py` pins (§1.2), the
  `_gate_coverage.py:1456` `mission_v1` shard row if `tests/specify_cli/mission_v1/` empties,
  and (Option FULL) the `test_wp_frontmatter_fold.py:60` entry.
- Red-first target: **an import-hygiene test that is red today** —
  `import specify_cli.mission_v1.events` must NOT put `transitions` in `sys.modules`
  (subprocess-isolated). Goes green when the eager block breaks; survives as a permanent ratchet
  against re-eager-ing (unlike a parity test, this one is an enduring negative invariant).

---

## 2. `kernel/glossary_runner.py` — FALSE-POSITIVE dead; deliverable is DESIGN-STORY REPAIR

**Adjudication (reports 24/25/27, re-verified): the registry is LIVE — no retirement.** The only
`register()`/`get_runner()` caller in production is
`charter/offering/missions/glossary_hook.py:46` (import) + `:127-137` (the lazy self-bootstrap:
`get_runner()` → on `None`, `import_module("glossary.attachment")` →
`register(GlossaryAwarePrimitiveRunner)` → retry). Verified: **zero other `register()` calls in
`src/`**; `src/glossary/` is self-standing.

**The fiction to repair (four sites, all verified at HEAD):**

1. `kernel/glossary_runner.py:14-16` — "`specify_cli` calls `register()` at import time to install
   the concrete `GlossaryAwarePrimitiveRunner`" + the provider usage block `:33-38`. No such call
   exists. The docstring's dependency diagram (`doctrine → kernel ← specify_cli`) also predates
   the `charter.offering` relocation.
2. `charter/offering/missions/glossary_hook.py:16-17` — "registered into the kernel registry by
   `specify_cli` at startup" — contradicted eleven lines above its own bootstrap.
3. `kernel/README.md:18` — "`glossary` registers the concrete `GlossaryAwarePrimitiveRunner` at
   import time" (a *third* variant of the fiction: names `glossary`, not `specify_cli`).
4. `kernel/__init__.py:38-42` — same claim as README.

**The design decision inside the repair:** either (a) **canonicalize the self-bootstrap** — the
hook is both consumer and (lazy) provider; rewrite all four sites to document that, and the
"graceful degradation when no runner is registered" story becomes "degradation only when
`glossary.attachment` itself is unimportable"; or (b) **add a real registration** at a defined
`specify_cli` seam and keep the bootstrap as fallback. (a) is a docs-only WP; (b) is a design
change that needs an owner and has no current driver. Recommendation carried from report 27
(B-WP02): **(a)** — document reality.

**FR-020 enforcement-honesty note (verified):** the hook's contract says `glossary_check` defaults
to enabled per FR-020 (`glossary_hook.py:9,58-64`), but `execute_with_glossary` has **zero
production call sites** — consumers are `tests/doctrine/missions/test_glossary_hook.py` and the
agent-glossary integration tests; the live step executor never enters the hook. And **zero
`glossary_check` references exist in `packs/`** (verified grep) — no built-in step contract sets
the field the hook reads. So "enabled by default" is enforced nowhere in the live mission loop.
The repair must say so somewhere honest (tracker note on the glossary workstream / #1868, or a
`.. note::` in the hook) — silently keeping the green tests over a dead production path is the
exact rot shape report 21 §2.3 flagged. Whether to *wire* the hook into the executor is a separate
feature decision — out of Mission B scope (interview question).

**Optional adjacent tidy (report 24):** the three-link re-export chain
`charter/offering/missions/__init__.py:10` → `charter/primitives.py:14` →
`specify_cli/missions/__init__.py:28` (lazy map) all exist and forward `execute_with_glossary`;
the last two symbols are pinned as escalated live-collisions in `test_no_dead_symbols.py`
(`PrimitiveExecutionContext`, `execute_with_glossary` under `specify_cli.missions`). Pruning is
allowed but touches gate pins; keep it optional, not load-bearing.

---

## 3. RuntimeEventEmitter threading — ADR-safe vs ADR-BLOCKED

**The disposition itself (retire / rewire / merge-and-keep-seam) is owned by the parallel ADR
session. Everything below is either verified context safe under ANY disposition, or explicitly
ADR-BLOCKED.**

### 3.1 Safe-regardless facts (this dossier's contribution)

- **Name collision (verified):** two classes named `RuntimeEventEmitter` —
  `runtime/next/event_emitter.py:23` (concrete no-op, 88 LOC, `for_feature:43`,
  `seed_from_snapshot:60`) vs `runtime/next/_internal_runtime/events.py:67` (the live Protocol,
  with `NullEmitter`). Every disposition resolves the collision (retire deletes one; rewire/merge
  renames one) — so *documenting* it and pinning the map below is safe; *executing* a rename is
  the ADR's call.
- **The ~29-occurrence `sync_emitter` map (verified at HEAD):** 29 occurrences in `src/`, exactly
  two files — `runtime_bridge_engine.py` × 16 (`:139,166,183,188,198,226,237,270,292,301-307,
  323,344,346,366`) and `runtime_bridge.py` × 13 (`:1215,1231,1472,1552,1614,1647,1976,2187` +
  wrapper plumbing). Plus **10 test files** reference `sync_emitter`. ⚠ VERIFIED-DELTA worth
  recording: `runtime_bridge_engine.py:80` imports the concrete class **under
  `TYPE_CHECKING` only** — all 16 engine occurrences are annotations/parameter names; the sole
  *runtime* coupling to the concrete class is `runtime_bridge.py:195` (import) + `:1552`/`:2739`
  (`for_feature` construction) + `:1614`/`:2745` (`seed_from_snapshot`). Retyping the engine
  against the Protocol is a type-only edit; the bridge is where behavior lives.
- **Both files are Mission-A-adjacent:** `runtime_bridge_engine.py` is one of the four shared
  files; any emitter execution sequences after Mission A regardless of the ADR (§6).
- **`sync_emitter` is retired-transport vocabulary in a live API** (report 20 §3.4#4). A
  parameter rename is *probably* safe under every disposition but touches the same 29 sites the
  ADR's execution will touch — do it as part of the ADR's execution WP, not before (one pass over
  those signatures, not two).

### 3.2 ADR-BLOCKED (do not scope into Mission B until the ADR lands)

- Retire vs rewire vs merge; whether `for_feature` / `seed_from_snapshot` (absent from both the
  Protocol and `NullEmitter` — verified) migrate onto the seam.
- **The buffer flush-target defect (verified live at HEAD):** under the strict retrospective gate
  the buffer replaces the engine emitter (`runtime_bridge.py:2149-2150`) and later flushes into
  `ctx.sync_emitter` (`:2187`) — the **inner no-op**, not `emitter_for_engine` (the
  `DecisionGitLog`-wrapped emitter built at `:1560-1565`), so buffered decision events never reach
  the git log on the gated path. Any deletion silently freezes or silently fixes this; the ADR
  must adjudicate it explicitly (report 24 §4c). Record; don't touch.
- The upstream contract fact anchoring the ADR (verified this session): installed
  `spec_kitty_events` **9.1.6** carries the runtime moments in `VOLATILE_EVENT_TYPES`
  (`MissionRunStarted/Completed`, `NextStepIssued`, `NextStepAutoCompleted`,
  `DecisionInputRequested/Answered`, plus `DecisionPointOpened/Resolved`) with codecs and
  redaction rules — the hosted vocabulary is provisioned and waiting for a producer.
- The parity oracle constraint: `tests/runtime/test_bridge_parity.py:1131-1152`
  (`test_side_effect_sinks_are_actually_reached`) asserts the `sync_emitter` sink is populated by
  ≥1 fixture — a disposition that removes the capture must update this oracle in the same PR.
- `_BufferingRuntimeEmitter` (`runtime_bridge_retrospective.py:69`) is **rollback machinery**, not
  dead code — it structurally implements the Protocol and is the only thing preventing an
  unretractable `MissionRunCompleted` on a rolled-back terminal advance. Not deletable under any
  disposition.

---

## 4. Small confirmed-dead residue — here vs the quick-wins PR

| Item | Verified state at HEAD | Belongs | Sequencing note |
|---|---|---|---|
| `specify_cli/team_projection/` tombstone | Package contains **only** the 8-line `__init__.py` docstring stub. `test_no_retired_subsystems.py:39-40,99-100` and `pyproject.toml:3040-3041` (TID251) pin the *submodules* as **bans** — they assert absence, so deleting the package leaves them green; they stay. Check wheel-includes on delete. | **Quick-wins PR** (zero coupling to Mission B surfaces) | none |
| `ActionContext` alias | ⚠ VERIFIED-DELTA: deletion touches **two files**, not one — `mission_runtime/context.py:~338` (alias + `__all__` entry) AND `mission_runtime/__init__.py:127,139-142` (lazy `__getattr__` re-export + listing). Zero consumers in src or tests confirmed. | Quick-wins PR | none |
| 13 un-demoted test-only `__all__` exports | `mission_runtime/__init__.py` re-export set + `lifecycle_phase.py::content_present_at_primary_tip` + `kernel/paths.py::get_packs_root_default`. ⚠ Both of the latter have **in-package** src callers (`mission_runtime/resolution.py:52`, `kernel/env_expand.py:63`) — so the action is **demotion from package `__all__`**, never deletion; in-package/module-path imports keep working. Requires matching `test_no_dead_symbols.py` re-pin. | Quick-wins PR, or fold into Mission B's gate-touching WP (both edit the same gate file — avoid two PRs racing on its hash pins) | coordinate with whichever Mission-B WP edits `test_no_dead_symbols.py` (§1.5) |
| Stale `constitution` exclusion, `test_layer_rules.py:65-73` | Verified present; excludes a package that does not exist (mission 063 done). | Either | **⚠ Sequence after PR #3888 lands** — #3888 (OPEN, verified via `gh`) modifies `test_layer_rules.py` (`_RUNTIME_ALLOWED_SPECIFY_CLI` ledger) and `test_runtime_charter_doctrine_boundary.py`; land second, rebase trivially |

Rule of thumb adopted: residue with **zero coupling to Mission B's owned files or gates** goes to
the quick-wins PR (`truststore` removal already lives there); residue whose deletion edits a gate
file Mission B also edits rides Mission B to avoid pin-hash races.

---

## 5. NON-GOALS

1. **No emitter rewiring, deletion, renaming, or `sync_emitter` signature changes before the
   disposition ADR lands.** Mission B may carry the ADR's *execution* as a late WP only if the ADR
   has landed by tasks-time; otherwise that WP is minted separately.
2. **No touches to Mission A's surfaces**: `status/emit.py`, `coordination/status_transition.py`
   / `transaction.py`, `status/aggregate.py`, the writer census, dependency gating, lock work —
   and no parallel edits to the four shared files (`runtime_bridge_io.py`,
   `_internal_runtime/engine.py`, `decision.py`, `runtime_bridge_engine.py`) until Mission A's
   WPs on them are merged.
3. **No wiring of `execute_with_glossary` into the live step executor** (feature work, unowned).
4. **No adjudication of `_internal_runtime/{emitter,lifecycle,models}.py` frozen re-exports**
   (Category-6 contract renegotiation, shared-package-boundary owner).
5. **No `doctrine.py` shim deletion** (on schedule for 3.3.0 per shim-registry).
6. **No `truststore` removal here** (quick-wins PR owns it).

---

## 6. Proposed WP slicing (3 WPs)

**WP01 — mission-DSL v1 retirement + `transitions` drop** (the mission's bulk; ~2 days)
- Scope: §1.3 extent (interview settles MIN vs FULL); trim `__init__.py` to `events` re-exports
  (or make `events` importable without the package eager block); delete `load_mission*` dispatch;
  drop 3 dead-symbol pins; re-pin/trim the test files; `pyproject.toml:82` + `uv lock`; version
  bump + CHANGELOG; pack-DSL honesty per interview outcome.
- Red-first: the sys.modules import-hygiene test (§1.5) — red today, green on landing, permanent.
- Ratchet: pins removed, `_gate_coverage.py` row updated; clean-install CI green.
- `owned_files` sketch: `src/specify_cli/mission_v1/**`, `pyproject.toml`, `uv.lock`,
  `CHANGELOG.md`, `tests/missions/**`, `tests/specify_cli/mission_v1/**`,
  `tests/architectural/test_no_dead_symbols.py`, `tests/architectural/_gate_coverage.py`
  (+ Option FULL: `tests/specify_cli/test_wp_frontmatter_fold.py`,
  `packs/built-in/missions/{software-dev,plan,research}/mission.yaml`,
  `tests/research/test_research_plan_missions_integration.py`,
  `tests/missions/test_mission_software_dev_integration.py`).
  Authoritative surface: `src/specify_cli/mission_v1/__init__.py`.
- **Note:** `runtime/next/decision.py:187-235` (dead DSL readers) and the
  `next_invocation_lifecycle.py:332` import are *consumers*, not owned here — they keep working
  (`events.py` survives). The dead-reader deletion in `decision.py` belongs to whichever lane owns
  the shared file post-Mission-A; if Mission A's WP05 lane is still open at tasks-time, hand the
  two-function deletion to it, else a small Mission B follow-up owns `decision.py` alone.

**WP02 — glossary design-story repair** (docs-shaped; ~0.5 day)
- Scope: §2 four-site fiction repair; canonicalize the self-bootstrap as the documented contract
  (or interview outcome (b)); FR-020 honesty note (in-code note + tracker comment on #1868's
  glossary workstream); optional re-export-chain tidy only if pins allow cheaply.
- Test target: one behavior test pinning the bootstrap contract (after `execute_with_glossary`
  runs with no prior registration, `get_runner()` returns the concrete runner) — turns today's
  incidental mechanism into a pinned invariant; existing `test_glossary_hook.py` largely covers
  it, extend there.
- `owned_files`: `src/kernel/glossary_runner.py`, `src/kernel/__init__.py`,
  `src/kernel/README.md`, `src/charter/offering/missions/glossary_hook.py`,
  `tests/doctrine/missions/test_glossary_hook.py`.
  Authoritative surface: `src/kernel/glossary_runner.py`.

**WP03 — emitter disposition execution (ADR-GATED) + gate-adjacent residue** (~1-1.5 days once
unblocked)
- Scope: execute whatever the landed ADR decides (rename/merge/retire mechanics of
  `event_emitter.py`, the collision, `sync_emitter` vocabulary, the flush-target adjudication,
  parity-oracle update); plus the `constitution` exclusion deletion (after #3888 lands) and — if
  not already in the quick-wins PR — the 13 `__all__` demotions riding the same gate files.
- Gate: **blocked on** (a) the RuntimeEventEmitter ADR, (b) Mission A's WPs on
  `runtime_bridge_engine.py`/`engine.py`/`runtime_bridge_io.py`, (c) PR #3888 for the
  `test_layer_rules.py` hunk. If the ADR outcome is "explicit deferral", WP03 shrinks to the
  residue + a docstring correction pointing `event_emitter.py:1-10` at the real E3 seam
  (`status/adapters.py:364-366`) instead of the false promise.
- `owned_files` (max variant): `src/runtime/next/event_emitter.py`,
  `src/runtime/next/runtime_bridge.py`, `src/runtime/next/runtime_bridge_engine.py`,
  `src/runtime/next/runtime_bridge_io.py`, `src/runtime/next/runtime_bridge_retrospective.py`,
  `src/runtime/next/_internal_runtime/events.py`, `tests/runtime/**`,
  `tests/architectural/test_layer_rules.py`, `tests/architectural/test_no_dead_symbols.py`.
  Authoritative surface: `src/runtime/next/event_emitter.py`.
- ⚠ Runtime-ledger rule (report 24 §5): any removal that erases a subpackage's last live
  `specify_cli` edge REDS `test_runtime_ledger_has_no_stale_entries` — budget the same-PR ledger
  edit; likewise the widened doctrine-scan baseline pins `runtime_bridge_io.py` /
  `runtime_bridge_composition.py` lazy reaches.

Dependency order: WP01 ∥ WP02 (disjoint files); WP03 after both external gates. Whole mission
after Mission A's shared-file lanes merge.

---

## 7. Open questions for the spec interview

1. **DSL extent (MIN vs FULL, §1.3):** delete `guards.py`/`schema.py` too? Randy says FULL;
   Alphonso 24 keeps `guards.py` as shape-precedent — but the precedent is docstring prose that
   could cite git history instead. FULL forces the fold-gate edit
   (`test_wp_frontmatter_fold.py:60`) and kills the pack-DSL validator tests. Recommendation on
   the table: FULL, with `gate_registry.py` docstrings re-pointed at history.
2. **Is mission-DSL v1 on any roadmap?** (Randy's operator question — a "yes" converts WP01 from
   retirement to re-justification and keeps the pin.)
3. **Pack DSL blocks (§1.4):** delete from the three `mission.yaml`s or keep-with-comment? Does
   `MISSION_COMPAT_IGNORED_FIELDS` stay as third-party tolerance either way (recommended: yes)?
4. **`events.py` future home:** stays as `specify_cli.mission_v1.events` (a one-module package
   whose name outlives its DSL), or relocate (e.g. under `status`/`mission_metadata`) — relocation
   touches the two runtime lazy imports and the seam test
   (`tests/specify_cli/next/test_next_invocation_lifecycle_seam.py:49`); cheap now, costlier
   later. If kept, does the package docstring get rewritten to stop advertising the deleted DSL?
5. **Glossary contract choice (§2):** canonicalize the self-bootstrap (docs-only) or mint a real
   registration seam? And who owns the FR-020 honesty follow-through — a tracker note only, or
   does Mission C's design-codification arc absorb it?
6. **Wire-or-retire for `execute_with_glossary` itself** — explicitly out of Mission B (non-goal
   3), but the interview should confirm the operator accepts "documented-but-unwired" as the
   steady state, else mint the feature issue now.
7. **ADR timing:** will the RuntimeEventEmitter ADR land before Mission B's tasks phase? If not,
   does WP03 ship as the shrunk residue-only variant with the emitter execution minted as a
   follow-up mission/WP?
8. **Residue placement:** confirm the quick-wins PR takes `team_projection`, `ActionContext`,
   and (default) the 13 demotions — or pull the demotions into WP01/WP03's gate-editing PRs to
   avoid `test_no_dead_symbols.py` hash-pin races.
9. **`decision.py` dead-reader ownership (§6 WP01 note):** Mission A WP05 lane, or a Mission B
   follow-up that owns the file alone after A merges?

---

*Verification log: eager chain + hot-path load re-proven empirically in `.venv`
(`transitions`+`six` in `sys.modules` from `mission_v1.events` alone); `pyproject.toml:82`,
`uv.lock` (`transitions 0.9.3` → `six`; `six` retained via `python-dateutil`); gate pins
`test_no_dead_symbols.py:718-727`; fold-gate entry `test_wp_frontmatter_fold.py:60`;
`MISSION_COMPAT_IGNORED_FIELDS` `mission.py:59-67,260-261`; glossary sites
`glossary_runner.py:14-16,33-38`, `glossary_hook.py:16-17,46,127-137`, `kernel/README.md:18`,
`kernel/__init__.py:38-42`; zero `glossary_check` in `packs/`; emitter map (29 src occurrences:
engine×16 incl. TYPE_CHECKING-only import at `:80`, bridge×13; constructions `:1552,:2739`; seeds
`:1614,:2745`; buffer swap `:2149-2150`; flush `:2187`; DecisionGitLog wrap `:1560-1565`); parity
oracle `test_bridge_parity.py:1131-1152`; `spec_kitty_events` 9.1.6 runtime moments;
`team_projection/` = `__init__.py` only, bans at `test_no_retired_subsystems.py:39-40,99-100` +
`pyproject.toml:3040-3041`; `ActionContext` at `context.py:~338` + `__init__.py:127,139-142`;
`constitution` exclusion `test_layer_rules.py:65-73`; PR #3888 OPEN touching `test_layer_rules.py`
(gh, read-only). Sources: reports 20/21/24/25/27.*
