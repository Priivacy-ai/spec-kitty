# 06 — Domains & Splits: Technical Concretization

> **Rewritten (2026-06-03)** as the **technical/codebase concretization of the consolidated model
> ([17](./17-consolidated-domain-model.md))**, grounded in the fan-out package findings
> ([16](./16-codebase-reassessment-fanout.md) H6). The earlier "for discussion" sketch (C1–C6 context
> catalogue, options A/B/C) is preserved in git history; its still-relevant parts (the owner-shape
> options, the e2e ratchet, the #992 alignment) are folded in below.

**Premise (Stijn):** *each domain is a **bounded module with external API entry points**; **communication
artefacts** cross between modules through those entry points.* This is the hinge from the conceptual
model (`17`) to code: map every model element to a **package home**, an **API entry point**, and a
**status** (exists / to-harden / net-new), then sequence the migration (Strangler).

---

## 1. Module map — model element → package home → API entry point → status

| Model element (`17`) | Kind | Package home (code, `16` H6) | API entry point(s) | Status |
|----------------------|------|------------------------------|--------------------|--------|
| **Governance** | domain (module) | `src/charter/` ⊕ `src/doctrine/` (two clean contexts) | `DoctrineService`, `build_charter_context(action=…)`, `AgentProfileRepository`, `ProfileRegistry` | **exists** |
| ↳ **GovernanceContext** | per-domain Context | `charter/context.py` (action-scoped bundle) | `build_charter_context` / `_load_action_doctrine_bundle` | exists |
| **Mission Management** | domain (module) | `kitty-specs/<slug>/` artefacts + planning cmds (`cli/commands/agent/tasks.py`, `agent/mission.py`) | `tasks-finalize`, `mission` CRUD, `bootstrap_canonical_state` | **exists** |
| ↳ **Mission / WorkPackage** | aggregates | `kitty-specs/` + `status/wp_metadata.py` | WP frontmatter + status events | exists |
| **Status / Kanban** | **shared context (seam)** | `src/specify_cli/status/` | `status/__init__.py` facade (`read_events`/`reduce`/`materialize`/`get_wp_lane`/`emit_*`) | **exists; boundary NOT enforced → [#1664](https://github.com/Priivacy-ai/spec-kitty/issues/1664)** |
| ↳ **`MissionStatus` aggregate** | aggregate root | (would wrap `status/`) | `MissionStatus.load/claim/transition/save` | **net-new** (today: free functions over `Lane`/`StatusEvent`) |
| **Execution / Runtime** | domain (module) | `src/runtime/next/_internal_runtime/` (canonical) + `runtime_bridge.py` | `decide_next`, `start_mission_run`, `get_or_start_run` | **exists** |
| ↳ **MissionRun** | aggregate | `runtime/next/_internal_runtime/{schema,engine}.py` | `MissionRunSnapshot` / `MissionRunRef` | exists; **can't name its Mission → [#1663](https://github.com/Priivacy-ai/spec-kitty/issues/1663)** |
| ↳ **ExecutionContext** (≈ ActionContext) | per-domain Context | `src/specify_cli/core/execution_context.py` | `resolve_action_context` (OHS) | **exists; to HARDEN (#1619)** |
| ↳ **Effector** | Actor realized in Execution | TBD (unify 3 vocabularies) | TBD | **net-new naming** |
| **Shared Kernel** | code module | `core/paths.py`, `workspace/root_resolver.py`, `mission_metadata`, `missions/_read_path_resolver.py` | `resolve_mission_identity`, `resolve_mission_read_path`, `get_status_read_root`/`get_main_repo_root`, `canonicalize_feature_dir` | **exists; the two OHS facades are the entry points** |
| **InfraContext** | ambient Context | `kernel/paths.py` (`get_kittify_home`), `charter/catalog.py` (`resolve_doctrine_root`), `state/contract.py` | `get_kittify_home`, `resolve_*_root`, `StateRoot` | exists |
| **Communication artefact** (Executor Prompt) | boundary artefact | `runtime/next/prompt_builder.py` (rendered text) | `build_prompt` → temp-file path | exists; **3 projections to consolidate** (below) |

**Reading:** the model is **mostly already in code**. Net-new is small and named: the `MissionStatus`
aggregate, the `Effector` type, and a unified communication-artefact contract. The #1619 core work is
**hardening one existing entry point** (`resolve_action_context` / ExecutionContext) and **enforcing one
existing boundary** (`status/`, #1664).

---

## 2. The communication-artefact contract (consolidate 3 projections)

Today the governed invocation produces **three** parallel projections (`16` H4) — we should converge them on one contract:

| Projection | Today | Consumer | Target |
|------------|-------|----------|--------|
| **Executor Prompt** | rendered text, `prompt_builder.py` → temp file (path returned) | LLM Effector | the canonical **communication artefact** |
| **`ActionContext.to_dict()` JSON** | `cli/commands/agent/context.py:111` | agent-context CLI / shim | a *serialization* of the same ExecutionContext (keep as a wire view) |
| **`OperationalContext`** (frozen VO) | `charter/invocation_context.py:155`, built at the decision boundary, **not passed to the prompt builder** | logs / composition | fold into the artefact assembly (or retire) |

**Target:** one **communication-artefact assembly** that takes (Mission/WP intent · GovernanceContext ·
ExecutionContext) and produces the artefact the Effector consumes — with the JSON `to_dict()` as a
*view* of the ExecutionContext, not a fourth independent thing. This is the technical form of "domains
exchange communication artefacts through API entry points."

---

## 3. The `Effector` type (net-new) — unify the fragmented Actor

The Actor metamodel is fragmented across **three vocabularies** (`16` H3): runtime `Literal["human","llm","service"]`
(`_internal_runtime/schema.py:62`), retrospective `Literal["human","agent","runtime"]`
(`retrospective/schema.py`), decisions `Literal["human","llm","service"]`, and free-form `str` in
`status/emit.py`. The **Effector** is the execution-domain realization (`Effector = Actor ∩ Execution`).

**Decision needed:** introduce a single `Effector`/`Actor` value type (kind + identity + sourced
beliefs) that the runtime, decisions, status, and retrospective surfaces all use — or leave the
vocabularies separate and only name "Effector" in docs. The fan-out makes this a *real* unification
target, not vocabulary-only (answers `12 §7`). Likely home: a small shared type in `kernel/` or
`status/` (consumed by both `runtime/` and `specify_cli/`), respecting the layer rules (§4).

---

## 4. Package placement under the layer meta-guard

Constraints from `16` H6 / `tests/architectural/test_layer_rules.py`:

- **Spine:** `kernel ← doctrine ← charter ← specify_cli`; **`runtime/` and `glossary/` are siblings at
  the charter level**. `runtime` may import `specify_cli.*` **except** `specify_cli.cli` / `specify_cli.next`.
- **A net-new top-level `mission_runtime/` would fail `test_no_unregistered_src_packages`** until
  registered in `_DEFINED_LAYERS` (both `conftest.py` and `test_layer_rules.py`).

**Placement decisions (revised from the old §4):**
- **Do NOT greenfield a `mission_runtime/` umbrella by default.** Execution already has a home
  (`src/runtime/next/`). Per the dialectic (`11`), **harden `ActionContext` in place**
  (`core/execution_context.py`) and consume it from `runtime/` (allowed). This avoids the layer-registration cost.
- **`MissionStatus` aggregate** wraps `status/` — lives in `src/specify_cli/status/` (the shared context).
- **`Effector`/`Actor` type** — a low-layer shared type (`kernel/` or a new `actor.py` consumed by
  both runtime and specify_cli), so the three vocabularies can converge without an illegal up-import.
- If a `mission_runtime/` umbrella is later justified, it must be a **registered** layer sibling, not a `specify_cli/*` package.

---

## 5. The ExecutionContext owner shape (options carried forward)

The old A/B/C options now scope specifically to **the ExecutionContext owner + the commit seam**
(not a whole new "MissionExecutionContext"):

- **A — value object + resolver:** harden `resolve_action_context` to return an immutable, complete
  `ExecutionContext` (read/write/dest/cwd/prompt). Simple; doesn't enforce atomicity.
- **B — operation service:** an `ExecutionOperation` that owns the commit seam (`worktree_root == destination_ref`),
  closing #1618/#1348. Bigger; enforces I-4.
- **C — Strangler façade:** route surfaces through a stable `resolve_action_context` interface first,
  delegate to today's resolvers, swap implementation later.

**Lean (unchanged, now code-grounded):** **C → B.** Strangler via the *existing* `resolve_action_context`
OHS entry point (it already fuses planning+execution actions — `16` H1), converging on a commit-owning
operation service. Option A is the fallback.

---

## 6. Strangler sequencing (the migration order)

Ordered by isolation / value, tied to the filed issues and the keepers:

1. **Build the e2e ratchet** — `next → implement → move-task → review → status` parity from **main and
   lane CWD** (#1619 AC-5). The gate that proves a surface was unified, not re-masked. *(do first)*
2. **Enforce the Status boundary** (#1664) — make the planning↔execution seam an actually-bounded
   shared context (import test mirroring `test_shared_package_boundary.py`).
3. **Harden ExecutionContext** — route the residue surfaces (`02` §4: `agent/status.py`, `runtime_bridge`
   query-mode, `workflow.py` fix-mode, …) through `resolve_action_context`; delete duplicated path-builders.
4. **MissionRun → Mission reference** (#1663) — contained; unblocks "runtime knows its mission".
5. **Consolidate the 3 context projections** → one communication-artefact contract (§2).
6. **Effector unification** (§3) — converge the 3 Actor vocabularies.
7. **Commit-seam atomicity** (Option B, I-4) — close #1618/#1348 (`worktree_root == destination_ref`).

---

## 7. Open questions (now technical) + keepers

**Keepers (code-validated, don't re-litigate):** Mission ≠ MissionRun; MissionType ∈ Governance(doctrine);
the execution spine; Context is per-domain; Shared Kernel is a code module; harden-don't-greenfield.

**Open:**
1. **Effector home + shape** — shared type in `kernel/`, or named-in-docs only? (§3)
2. **`mission_runtime/` — net-new umbrella or harden-in-place?** Lean: harden-in-place (§4).
3. **Atomicity (I-4)** — enforce `worktree_root == destination_ref` in the seam (Option B), or guideline? (§5/6)
4. **Communication-artefact contract** — one assembly with `to_dict()` as a view, or keep projections separate? (§2)
5. **`MissionStatus` aggregate now, or keep free functions** behind the hardened facade? (`07` §4)
6. **Naming ratification** (DIRECTIVE_032) — lock GovernanceContext / ExecutionContext / InfraContext / Effector / communication-artefact into the glossary + an ADR before code.

---

## 8. Path to a decided design
1. **Ratify vocabulary** (Q6) → glossary + ADR(s) under `architecture/3.x/adr/`: (a) the domain model
   (`17`); (b) ExecutionContext owner + one-atomicity-domain commit rule; (c) Effector/Actor unification.
2. **Build the e2e ratchet** (step 6.1).
3. **Strangler increments** in the order of §6, each gated by the ratchet.
4. **Close #1619** when no raw mission-state reads remain outside the resolver (except documented fallbacks) and the e2e parity test is green from both CWDs.

> **Alignment:** this is the execution/state slice of team epic **#992 "centralize domain invariants"**
> (`03` C); reconcile explicitly. Free-wins #1663/#1664 are independently shippable down-payments.
