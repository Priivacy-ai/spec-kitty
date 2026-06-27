---
title: '09 — Context Decomposition: A Conceptual Model'
doc_status: draft
updated: '2026-06-03'
related:
- docs/plans/engineering-notes/runtime_and_state_overhaul/11-dialectic-and-revised-claims.md
---
# 09 — Context Decomposition: A Conceptual Model

**Phase:** 2 (conceptual modeling) · **Date:** 2026-06-03
**Hypothesis under test (Stijn):** "Context" is not one object. It is several **domain-owned chunks
of contextual information/config** — infrastructure, filesystem, version control, execution
preferences, execution state — each modeled individually in its proper domain, then **aggregated by
composition** into fit-for-purpose composites passed through the API.

> **⚠ Revised by [11](./11-dialectic-and-revised-claims.md).** A corroborate-vs-refute pass found that
> composed domain-owned context **already exists** as `ActionContext` (`core/execution_context.py:44`,
> ADR 2026-03-09-1 "commands resolve context, prompts consume it"). The fragments below are best read
> as the **internal structure of a hardened `ActionContext`**, not six new public objects — keep it a
> deep module. Read `11` before treating this as the target.

**Verdict up front: the hypothesis holds, and it is the right model.** It satisfies every doctrine
constraint in `04`, it dissolves the `OperationalContext` naming collision (`07` §2), and ~4 of the
~6 fragments **already exist** in the codebase in some form. This document formalizes the model.

---

## 1. Two axes for classifying contextual information

A single flat `MissionExecutionContext` (the #1619 field list) conflates information that differs on
**two independent axes**. Separating them is what makes decomposition natural.

### Axis A — Scope / lifetime (how long it's stable, how widely it applies)
| Scope | Stable for… | Examples |
|-------|-------------|----------|
| **Install** | the machine/install | shipped doctrine root, `~/.kittify`, `~/.spec-kitty` |
| **Repo** | a checkout | repo root, org packs, default target branch, `config.yaml` |
| **Mission** | one mission's life | `mission_id`, coord branch, `lanes.json`, coord worktree |
| **Operation** | one command invocation | cwd, op_kind, `destination_ref` for *this* op, flags |

### Axis B — Domain (which bounded context owns the *rules*)
Infrastructure · Filesystem · Version Control · Execution Preferences · Execution State
(+ **Identity** as the foundational zeroth domain everything keys on).

A field has **one position on each axis**: e.g. `coordination_branch` is *Version-Control domain ×
Mission scope*; `destination_ref` is *Version-Control domain × Operation scope*; `shipped doctrine
root` is *Infrastructure domain × Install scope*. The flat object hid both distinctions.

### A third distinction — primitive vs derived
- **Primitive** = read from a source (`meta.json`, `config.yaml`, `lanes.json`, cwd, env, git).
- **Derived** = computed by a **domain rule** combining primitives
  (`coord_worktree = f(repo_root, slug, mid8)`; `destination_ref = coordination_branch or current_branch`).

> **The key move:** a fragment is *not a data bag*. It encapsulates its domain's **derivation rules**
> (e.g. the Filesystem fragment owns the `.worktrees/<slug>-<mid8>-{coord,lane}` convention; the
> Version-Control fragment owns the `kitty/mission-<slug>-<mid8>` naming). That is the deep-module
> (`04`) discipline applied per domain — the four duplicated path-builders (`02`) collapse into the
> Filesystem fragment's rules.

---

## 2. The fragment catalogue

Six fragments. Five are immutable **value objects**; one (Execution State) is the mutable
**aggregate**. Each is owned by exactly one domain and references the others **by identity only**
(Aggregate Design Rules, `04`).

| # | Fragment (proposed name) | Domain | Scope | Primitive / derived | Exists today? |
|---|--------------------------|--------|-------|---------------------|---------------|
| **F0** | `MissionIdentity` | Identity | Mission | primitive (`meta.json`) | scattered → consolidate |
| **F1** | `InfrastructureEnv` | Infrastructure | Install/Repo | primitive (env, importlib, packs) | **exists** (DoctrineService roots, state-roots, `get_kittify_home`) |
| **F2** | `FilesystemLayout` | Filesystem | Repo+Mission+Op | derived (from F0 + roots + conventions) | partial (`resolve_mission_read_path`, `CoordinationWorkspace`) → **consolidate (NEW)** |
| **F3** | `VersionControlScape` | Version Control | Mission+Op | derived (from F0 + git + naming) | partial (`branch_naming`, `CoordinationWorkspace.branch_name`) → **consolidate (NEW)** |
| **F4** | `OperationalContext` | Execution Preferences | Session+Op | primitive (session, CLI, profile) | **exists, wired** (`charter/invocation_context.py:155`) |
| **F5** | `StatusSnapshot` (VO) + `MissionStatus` (aggregate) | Execution State | Mission | derived (hydrate via `reduce`) | **exists** (`status/`) → formalize aggregate (`07` §4) |

### Fragment detail

**F0 — `MissionIdentity`** *(value object; the key every other fragment carries)*
- Fields: `mission_id` (ULID), `mid8`, `mission_slug`, `mission_run_id`, `friendly_name`, `mission_type`.
- Rule: `mission_id` is canonical identity; `mission_run_id` is the distinct runtime/session id (ADR A4/A6, `03`). Other fragments reference F0 **by value**, never hold object refs to each other.
- Today: `_identity_for_request` (`status_transition.py:105`), `resolve_mission_identity`, `mid8_from_slug` (`branch_naming.py`) — consolidate into one VO + resolver.

**F1 — `InfrastructureEnv`** *(value object; mostly ambient)*
- Fields: built-in/shipped doctrine root, `kittify_home` (`~/.kittify`), `global_sync` (`~/.spec-kitty`), package asset roots, org-pack roots, state-root classification.
- Today: **already modeled** — `resolve_doctrine_root` (`charter/catalog.py:153`), `get_kittify_home` (`kernel/paths.py:24`), `StateRoot` (`state/contract.py`), `DoctrineService` roots. 
- **Open question:** F1 is largely *install/repo* scoped and *cross-mission* — it may **not** belong inside the mission composite at all; it's ambient and already injected via `DoctrineService`. Likely referenced, not embedded.

**F2 — `FilesystemLayout`** *(value object; the #1619 path fields)*
- Primitive: `primary_root` (repo root), `current_cwd`.
- Derived (owns the conventions): `feature_dir` (primary), `coord_worktree`, lane worktrees, integration root, `status_read_dir`, `status_write_dir`, `execution_workspace`, `prompt_source_dir`, `allowed_command_cwd`.
- Rule: owns the `.worktrees/<slug>-<mid8>-{coord,lane-<id>}` convention + sparse-exclusion facts (currently in `CoordinationWorkspace`). **This is where the four duplicated path-builders (`02`) go.**

**F3 — `VersionControlScape`** *(value object; the #1619 branch/ref fields)*
- Primitive: `current_branch`, worktree `HEAD`, default `target_branch` (from `meta.json`).
- Derived (owns the naming): `coordination_branch` (`kitty/mission-<slug>-<mid8>`), lane branches, integration branch, `destination_ref` (per op).
- Rule: owns `kitty/mission-…` naming (ADR A1). The **`worktree_root == destination_ref` invariant** lives at the **F2×F3 seam** (a tiny explicit shared kernel) — today it is `safe_commit`'s head-mismatch guard (`commit_helpers.py:858`).

**F4 — `OperationalContext`** *(value object; ALREADY EXISTS — resolves the naming collision)*
- Fields: `active_model`, `active_profile`, `active_role`, `current_activity`, `tech_stack`.
- **This existing object *is* the Execution-Preferences fragment.** We do **not** repurpose it for
  filesystem aspects (that was the `07` §2 collision). It slots into the model as F4 unchanged.
- **Open question:** operation **flags** (`force`, `--no-auto-commit`, `execution_mode`) — fold into
  F4, or split a tiny `OperationPolicy` fragment? (They're operation-scoped policy, not session preference.)

**F5 — `StatusSnapshot` (read VO) + `MissionStatus` (write aggregate)** *(Execution State)*
- The **one mutable** domain. CQRS-shaped already: `reduce(events) -> StatusSnapshot` is the read
  model (frozen, composable into read/prompt contexts); `MissionStatus` is the write aggregate
  (load → claim/transition → save) per `07` §4.
- **Modeling clarification:** Execution State appears in **two forms** — a frozen `StatusSnapshot`
  *fragment* you compose into read/render composites, and the `MissionStatus` *aggregate* you
  **load using** a composite to mutate. The aggregate is a *consumer* of the context, not a member of it.

---

## 3. The derivation graph

Fragments are not peers in a flat bag; they form a small DAG rooted at Identity.

```
  sources:  meta.json   config.yaml   lanes.json   git   cwd/env   session/CLI
                │            │             │         │       │          │
                ▼            ▼             ▼         ▼       ▼          ▼
   F0 MissionIdentity ◄──────┘             │         │       │          │
        │   │                              │         │       │          │
        │   └──────────────┐               │         │       │          │
        ▼                  ▼               ▼         ▼       │          ▼
   F3 VersionControl   F2 FilesystemLayout ◄─────────┘       │     F4 OperationalContext
   (branch naming)     (worktree/path conv.)                 │     (model/profile/role)
        │                  │   │                              │
        │  worktree_root   │   │ read_dir / write_dir         │
        └──── == ──────────┘   └──────────────┐               │
          destination_ref                     ▼               │
          (F2×F3 shared kernel =        F5 StatusSnapshot ◄────┘ (cwd/op selects which dir)
           safe_commit invariant)        (reduce(events @ read_dir))
```

- **F0 is the root**; F2 and F3 derive from it + conventions; F5 hydrates from F0+F2.
- **F1** sits to the side (install/repo-ambient).
- **F4** is independent of F0 (it's about the operator/session, not the mission) — which is *why* it
  composes cleanly and why it shouldn't have been conflated with mission topology.
- The only inter-fragment coupling is the **F2×F3 shared kernel**: the `(worktree_root,
  destination_ref)` pairing — small, explicit, already embodied by `safe_commit`. Everything else
  references F0 by value. This satisfies DIRECTIVE_031 (no shared mutable state; explicit kernel).

---

## 4. Composition into fit-for-purpose composites

The object **passed through the API** is an operation-specific composite that selects only the
fragments that operation needs. The composite is a **deep module** (small interface); the fragments
are its hidden structure.

| Operation | F0 Id | F2 FS | F3 VC | F4 Pref | F5 State | Composite (working name) |
|-----------|:----:|:-----:|:-----:|:-------:|:--------:|--------------------------|
| status read / kanban | ✓ | read_dir | | | snapshot | `ReadContext` |
| render agent prompt | ✓ | prompt_source | branch (display) | session | snapshot | `PromptContext` |
| claim / implement-start | ✓ | write_dir, workspace | dest_ref, lane | actor, flags | aggregate | `WriteContext` |
| move-task / transition | ✓ | write_dir | dest_ref | actor, force | aggregate | `WriteContext` |
| review | ✓ | read+write, artifact dir | dest_ref | reviewer | aggregate | `ReviewContext` |
| merge → done | ✓ | integration root | integration branch, dest_ref | | aggregate (all WPs) | `IntegrationContext` |
| doctrine/guidance load | ✓ | (project root) | | active action | | (uses F1 + action scope) |

Three observations:

1. **`ReadContext` and `WriteContext` are different composites** — exactly the read/write split the
   two existing half-resolvers (`02`) already imply, now made explicit. This directly satisfies I-2
   ("distinct read/write/destination outputs, never one fused `feature_dir`").
2. **`WriteContext` is the home of the atomicity invariant (I-4):** it bundles `F2.write_dir` +
   `F3.destination_ref` + the F2×F3 kernel, so a caller *cannot* commit to a mismatched pair. This is
   how #1618/#1348 get *closed* rather than avoided.
3. **`PromptContext` renders from F2+F4+F5** — so prompts are *derived from* the same fragments the
   CLI writes through. That is I-6 (#1616) by construction: the agent contract can't contradict the topology.

### Composition, not inheritance
Composites are **assembled by composition** (hold fragment instances), never by subclassing. This is
the `ProjectContext`-holds-`PackContext` precedent (`07` §1b) generalized. Fragments stay independently
testable; composites are thin selectors.

---

## 5. The central builder

One factory in `mission_runtime/` assembles fragments → composite, mirroring
`_build_doctrine_service_with_org_layer` (`07` §3):

```
build_mission_context(selector, *, op_kind, cwd) -> <Read|Write|Prompt|...>Context:
    identity   = resolve_identity(selector)              # F0  (meta.json)
    fs         = FilesystemLayout.for_mission(identity, repo_root, lanes)   # F2
    vc         = VersionControlScape.for_mission(identity, repo_root)       # F3
    prefs      = build_operational_context(...)          # F4  (existing builder)
    return compose(op_kind, identity, fs, vc, prefs)     # selects fragments for op_kind
# MissionStatus.load(ctx) only when mutation is needed (F5 aggregate)
```

- **Dataclasses (F0–F4) live in `charter`** (import-clean of `specify_cli`); **builders live in
  `specify_cli`/`runtime`** — the layer law (`07` §1e). `MissionStatus`/`StatusSnapshot` (F5) stay in `status/`.
- `op_kind` lives in the **builder**, not on the fragments (fragments are op-agnostic; the composite is op-specific).

---

## 6. How this resolves the open decisions

| Decision (`08`) | Resolution from this model |
|-----------------|----------------------------|
| **D1** OperationalContext naming collision | **Resolved.** Existing `OperationalContext` = the F4 Execution-Preferences fragment, unchanged. The filesystem concept is **F2 `FilesystemLayout`**, a *different* fragment. No rename. |
| **D5** durable topology vs per-invocation context | **Resolved into a cleaner cut:** durable = mission-scoped fragments (F2/F3 derivations); per-invocation = the *composite* + op-scoped fields (cwd, dest_ref, flags). Not two objects — one fragment set, op-specific composites. |
| **D2** does MissionStatus own the commit seam | **Sharpened:** the *commit target* is owned by `WriteContext` (F2×F3 kernel); `MissionStatus.save()` *uses* that target. Atomicity is enforced by the composite, the aggregate rides it. |
| **D4** object vs service vs façade | **Reframed:** fragments are value objects (A); the *write* composite + aggregate form the operation service (B) that enforces I-4. We get A and B at different layers, not either/or. |
| **D6** central builder signature | **Drafted** (§5): `build_mission_context(selector, *, op_kind, cwd)`. |

---

## 7. Constraint check (against `04`)

- ✅ **Boundaries by ubiquitous language** — each fragment is a domain (Filesystem, VC, Preferences, State), not a runtime stage. (DIRECTIVE_031)
- ✅ **No shared mutable state across boundaries** — only F5 mutates, as a single-writer aggregate; F0–F4 frozen; the one cross-fragment coupling (F2×F3) is an explicit small kernel. (DIRECTIVE_001/031)
- ✅ **Reference by identity** — fragments carry `mission_id`, not object refs to each other. (Aggregate Design Rules)
- ✅ **Deep modules** — composites expose small interfaces; derivation rules hidden in fragments. (Deep Module Design)
- ✅ **Layer law** — VO dataclasses in `charter`, builders in `specify_cli`/`runtime`. (test_layer_rules)
- ✅ **≤ a few contexts** — 6 fragments, 4 op-composites; not per-field or per-entity. (over-split failure mode avoided)
- ⚠️ **DIRECTIVE_032** — fragment names (`FilesystemLayout`, `VersionControlScape`, `InfrastructureEnv`) are provisional; ratify in glossary + ADR before coding.

---

## 8. Open modeling questions (for the next session)

1. **Is F1 (Infrastructure) in or out of the mission composite?** Leaning *out* — it's install/repo
   ambient, already injected via `DoctrineService`. Mission composites would *reference* it, not embed it.
2. **Do operation flags (`force`, `--no-auto-commit`, `execution_mode`) live in F4, or a 6th tiny
   `OperationPolicy` fragment?** They're op-scoped policy, not session preference.
3. **Is `current_cwd` a Filesystem (F2) field or its own `InvocationFacts` fragment** (cwd + op_kind
   + actor + timestamp)? Argues for a 7th micro-fragment — weigh against over-split.
4. **Composite granularity:** are `Read/Write/Prompt/Review/Integration` the right composites, or do
   we want fewer (one `OperationContext` with optional fragments) — at the cost of a larger interface?
5. **Where does the F2×F3 kernel object live?** A dedicated `CommitTarget` value object (worktree +
   ref, self-validating), or keep it implicit in `safe_commit`? A `CommitTarget` VO would make I-4 a *type*, not a runtime check.
6. **Does `StatusSnapshot` (F5 read VO) get embedded in composites, or fetched lazily** via the
   aggregate to avoid staleness? (Embedding = a point-in-time view; lazy = always-fresh but couples render to load.)
7. **Fragment naming ratification** (DIRECTIVE_032) — lock the vocabulary before the first ADR.

---

## 9. Why this model is the answer (summary)

The #1619 flat field list was a symptom: it bundled install-scope, mission-scope, and operation-scope
facts from five different domains into one object that every caller had to rebuild. Decomposing by
**domain × scope**, encapsulating **derivation rules** per fragment, and **composing per operation**
gives us: distinct read/write/destination outputs (I-2), atomicity-by-construction (I-4),
prompts-from-context (I-6), single-writer state (I-9), and a clean home for each rule — while
**reusing** F1 and F4 (which already exist) and **formalizing** F2/F3/F5 from logic that is already
written but scattered. It is the same compositional pattern the codebase already trusts
(`ProjectContext`⊃`PackContext`), applied to mission execution.
