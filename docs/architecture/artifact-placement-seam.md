---
title: The Artifact Placement Seam
description: How a mission artifact's kind and topology resolve to a physical tree, the two composition roots, and where callers still bypass the seam.
doc_status: active
updated: '2026-07-28'
related:
- docs/architecture/branch-target-routing.md
- docs/adr/3.x/2026-06-24-1-kind-and-topology-aware-artifact-placement.md
- docs/adr/3.x/2026-07-23-1-surface-vocabulary-two-domains-and-topology-surface-rename.md
- docs/context/orchestration.md
---
# The Artifact Placement Seam

This page explains the layering that decides **where a mission artifact physically lives**
— which directory a read resolves to, which branch a write commits against — and names the
places a caller can still bypass that decision. It exists because three missions in a row
spent their discovery budget re-deriving facts this page now states once: `#3014` was filed
on a false premise about the layering, and this mission (`read-side-seam-primary-primitive-
closure-01KYKMMT`) was re-scoped twice before the layering itself was pinned down correctly.

This page is **explanatory, not normative**. The binding placement rules live in
[ADR 2026-06-24-1](../adr/3.x/2026-06-24-1-kind-and-topology-aware-artifact-placement.md) and
[ADR 2026-07-23-1](../adr/3.x/2026-07-23-1-surface-vocabulary-two-domains-and-topology-surface-rename.md)
(see [Citations](#citations)); this page does not restate their rules, only shows how the code
that implements them is layered. Every code-shape claim below carries a `module:symbol`
citation so a future rename shows up as a broken reference rather than silent drift.

## What "routing" means here

"Routing" on this page means exactly one thing: **mapping a mission artifact's *kind* — a
`MissionArtifactKind` member such as `SPEC` or `STATUS_STATE`
(`src/mission_runtime/artifacts.py:62`) — together with the mission's *topology*, to a
`TopologySurface` (`src/mission_runtime/artifacts.py:22`): the physical tree the artifact
resolves to for reading or writing. This is the **placement sense** of "routing."

"Routing" is heavily overloaded elsewhere in this codebase — branch selection, git-commit
targets, dispatch/profile matching, sync fan-out, model/task assignment, and more all use the
same word for unrelated decisions. Do not infer any of those senses from this page. The full
disambiguation, with a "do NOT use when" guard for every governed sense, lives in the
`Routing` entry of [`docs/context/orchestration.md`](../context/orchestration.md#routing) —
consult it rather than guessing from context.

## The layer table

The question "where does this artifact live?" passes through five layers before it reaches a
filesystem path. Each layer has exactly one owner; a caller that reaches past its own layer
(picking a surface, or assembling a path, itself) is the semi-compliance shape [§4](#the-compliance-taxonomy)
names.

| Layer | Question answered | Owning module:symbol | Aware of |
|---|---|---|---|
| **L0 — entry** | *What* artifact am I reading or writing? | The caller names a `MissionArtifactKind` and asks a `PlacementSeam` (`src/mission_runtime/resolution.py:1373`) for `read_dir` or `write_target` | kind only — nothing about *where* |
| **L1 — partition classification** | Which partition does this kind belong to — PRIMARY or COORD? | The `_PRIMARY_ARTIFACT_KINDS` / `_PLACEMENT_ARTIFACT_KINDS` frozensets and `assert_partition_invariant` (`src/mission_runtime/artifacts.py:136`, `:172`, `:269`) | kind only — **topology-blind** |
| **L2a — declared decision** | Where does this fact *architecturally* live, independent of what is materialized on disk right now? | `declared_read_surface` (`src/mission_runtime/resolution.py:1545`) | kind + topology; **materialization-BLIND** |
| **L2b — affirmative decision** | Where does this read resolve *right now*, given what is actually materialized? | `_classify_artifact_surface` (`src/mission_runtime/resolution.py:1588`), consuming `probe_coord_state` (`src/specify_cli/missions/_read_path_resolver.py:284`) | kind + topology + **materialization** |
| **L3 — candidate discovery / assembly** | Which concrete directories exist for this handle, and how is the final path assembled? | `resolve_planning_read_dir` (`src/specify_cli/missions/_read_path_resolver.py:1367`) and the module-private leaf `_compose_primary_feature_dir` (`src/specify_cli/missions/_read_path_resolver.py:1263`) | filesystem + handle form — this is where paths are **built** |
| **L4 — translation** | Given a chosen surface, *which* already-discovered location is it? | `translate_surface` (`src/mission_runtime/resolution.py:1503`) over a `SurfaceLocations` record (`:1471`) | neither kind nor topology — it **selects** a field off an already-populated record, and **refuses** (`ValueError`) when that field is absent |

**L2 is two functions, not one, and the split is deliberate.** `declared_read_surface` is
materialization-*blind* precisely so it can disagree with an already-resolved surface stamp —
that disagreement is what lets `GateExecutionContext.surface_cannot_hold`
(`src/specify_cli/acceptance/execution_context.py:194`, `#2885`) refuse rather than silently
pass an empty surface. Describing L2 as "one decision module" erases the reason that guard can
fire at all. `_classify_artifact_surface`'s own docstring names this: it defers to
`declared_read_surface` first and only consults the materialization-aware `CoordState`
classifier when the declared answer is `COORD`.

**L4 selects; it does not assemble.** `translate_surface` reads a field off a `SurfaceLocations`
record that L3 already populated and raises when the field is `None` — it never touches the
filesystem or builds a path from parts. Treating L4 as the place to "fix" a placement bug
teaches the exact misappropriation this page exists to prevent: re-adding discovery logic at a
call site instead of routing through L0–L3.

**A third `read_dir` route, not shown as a table row.** `PlacementSeam.read_dir`
(`src/mission_runtime/resolution.py:1417`) short-circuits exactly one kind —
`MissionArtifactKind.RETROSPECTIVE` — to `resolve_retrospective_home`
(`src/specify_cli/retrospective/writer.py:36`) at `resolution.py:1454`, **before** any of L2's
classification runs. See [Honest bounds](#honest-bounds) for why this is load-bearing rather
than a footnote.

## Both composition roots

There are two composition roots, not one, and both are reached through the same seam object:

- **The read root** — `resolve_artifact_surface` (`src/mission_runtime/resolution.py:1718`),
  projected by `PlacementSeam.read_dir`.
- **The write root** — `resolve_placement_only` (`src/mission_runtime/resolution.py:1241`),
  projected by `PlacementSeam.write_target` (`:1408`).

Both are constructed via one entry point, `placement_seam(repo_root, mission_slug)`
(`src/mission_runtime/resolution.py:1850`), which also asserts the L1 partition invariant
before returning — "two roots, one seam."

**This is the intent, not a landed invariant with zero exceptions** — see
[Honest bounds](#honest-bounds) for the measured count of direct callers that reach either root
without going through `PlacementSeam`.

## The compliance taxonomy

A call site's relationship to the seam falls into one of four shapes:

| Shape | What the caller does | Verdict |
|---|---|---|
| **Compliant (tier-1)** | Names a `MissionArtifactKind`, asks `placement_seam(...).read_dir(kind)` / `.write_target(kind)`, and fails loud on an unresolved surface | Target state |
| **Delegating-but-lenient** | Names a kind, delegates the surface decision to the seam, but the surrounding code never supplies the fail-closed input the leaf needs (e.g. a missing `coordination_branch`) | Censused as a bypass on the *leniency* axis, not the *routing* axis |
| **Semi-compliant** | Passes an already-canonical mission handle, but picks its own surface/resolver directly instead of asking the seam for the kind's home | **This page's headline concept** — see below |
| **Non-compliant** | Uses a raw or unrecognized handle, or hand-assembles a path from parts | Should red the read-side bypass census; one currently-permanent exception is named in [Honest bounds](#honest-bounds) |

**Semi-compliance is the headline shape, and it is invisible to a handle-hygiene gate.** A call
site can canonicalize its mission handle perfectly — passing every check the canonicalizer
authority gate (`tests/architectural/test_resolution_authority_gates.py`,
`CANONICALIZER_PRIMITIVE_NAMES`) runs — and still choose its own surface by calling a
kind-blind resolver (`resolve_feature_dir_for_mission`,
`src/specify_cli/missions/_read_path_resolver.py:1603`) directly, instead of asking
`placement_seam(...).read_dir(<kind>)` to make the decision. The handle is canonical; the
*routing* is not. A gate that only checks handle canonicalization form (def-use canonicality)
cannot see this, because canonicality and routing-compliance are orthogonal axes.

**Which gate catches it, and which does not (US7.4):**

- **Does NOT catch it:** the canonicalizer authority gate
  (`tests/architectural/test_resolution_authority_gates.py`) — it verifies the *handle argument*
  passed to a small allow-listed set of primitives is already canonical; it has no opinion on
  which primitive or surface the caller chose.
- **Does catch it:** the read-side bypass census
  (`tests/architectural/test_no_read_side_bypass.py`,
  `test_no_read_side_bypass_outside_sanctioned_and_allow_listed`) — it scans for calls to the
  kind-blind primitives by name (`primary_feature_dir_for_mission` while it existed;
  `resolve_feature_dir_for_mission` today) anywhere outside a named sanction, independent of
  whether the handle passed to them is canonical.

## Honest bounds

**Surface members with no production producer.** `TopologySurface` (`src/mission_runtime/
artifacts.py:22`) has five members — `PRIMARY`, `COORD`, `LANE`, `CONSOLIDATED`, `TEMP` — all
declared together so `translate_surface`'s totality assertion (`assert_surface_totality`,
`src/mission_runtime/artifacts.py:300`) has no phantom member to skip. Only `PRIMARY` and
`COORD` are wired to a production caller today; `LANE`, `CONSOLIDATED`, and `TEMP` are declared
with the seam but have **no production producer yet** — the enum's own docstring
(`artifacts.py:41-48`) says so directly. Do not read their presence in the enum as evidence a
caller resolves them today.

**The residual `PLACEMENT` rename debt.** ADR `2026-07-23-1` renamed the `TopologySurface`
member `PLACEMENT` → `COORD`. The frozenset that decides *which artifact kinds* route to that
surface, however, is still named `_PLACEMENT_ARTIFACT_KINDS` (`src/mission_runtime/
artifacts.py:172`) — the rename reached the enum member but not this frozenset's name. This is
named here, not laundered: a future cleanup can rename the frozenset without changing any
behavior, since membership (not the Python identifier) is what every consumer reads.

**The `RETROSPECTIVE` short-circuit is a foundation site, not a footnote.** `PlacementSeam.
read_dir` routes `MissionArtifactKind.RETROSPECTIVE` to `resolve_retrospective_home`
(`src/specify_cli/retrospective/writer.py:36`) before `resolve_artifact_surface` ever runs —
because a second RETROSPECTIVE-home computation would duplicate the single authority that
function already is. `resolve_retrospective_home` itself calls the module-private leaf
`_compose_primary_feature_dir` (`src/specify_cli/missions/_read_path_resolver.py:1263`)
directly, never `read_dir` again. This mission proved the short-circuit is load-bearing, not
cosmetic: an intermediate draft that routed the wrapper *through* `read_dir(RETROSPECTIVE)`
produced a **real recursion cycle** (`resolve_retrospective_home → read_dir(RETROSPECTIVE) →
resolve_retrospective_home → …`), caught only by call-graph tracing, not by a `RecursionError`
at runtime (the cycle's other legs terminate, so nothing crashed). The standing rule this
leaves behind: **any site beneath this short-circuit is a foundation site** — it must call the
leaf directly and permanently, never route back through `read_dir`.

**Two composition roots, measured bypass count (not a zero-exception invariant).** Re-derived
directly from the tree by AST-matching `Call` nodes (`grep`/`ast.walk` over `src/**/*.py`, this
mission's own re-derive-don't-copy discipline):

| Root | Total call expressions | Reached via `placement_seam(...)` | Direct callers bypassing the seam object |
|---|---|---|---|
| `resolve_placement_only` (write) | 13 | 1 (`PlacementSeam.write_target`, `resolution.py:1415`) | **12**, across 8 modules (`coordination/commit_router.py` ×4, `merge/executor.py`, `merge/done_bookkeeping.py`, `coordination/status_transition.py`, `cli/commands/safe_commit_cmd.py`, `cli/commands/agent/tasks_shared.py`, `orchestrator_api/commands.py` ×2, `mission_runtime/write_target_degrade.py`) |
| `resolve_artifact_surface` (read) | 8 | 2 (`PlacementSeam.read_dir` at `:1467`, and the sibling thin projection `coord_read_dir_for` at `:1839`, both co-located in `resolution.py` itself) | **6**, across 5 modules (`merge/forecast.py`, `post_merge/review_artifact_consistency.py`, `cli/commands/accept.py` ×2, `migration/runtime_state_cutover.py`, `acceptance/execution_context.py`) |

None of these 18 direct callers is a defect by itself — several are the composition root's own
adjacent infrastructure (e.g. `GateExecutionContext` in `acceptance/execution_context.py`
legitimately consumes `resolve_artifact_surface` directly, since it *is* the gate-facing
consumer of that authority, not a bypass of it). The count exists so "one seam object" is never
read as a landed zero-exception invariant — it is the destination, measured against the
current tree, not a claim about it.

**`#3055` — one deliberately-deferred edge.** `decisions/emit.py:71`
(`src/specify_cli/decisions/emit.py`) still calls `resolve_feature_dir_for_mission` directly
rather than routing through the seam. It is allow-listed, not routed, because the
coord-authority gate (`tests/architectural/test_resolution_authority_gates.py`) independently
sanctions this exact call as a permanent legitimate coord-owned write bypass, keyed on the
literal primitive name — the gate must learn the seam idiom (recognize a kind-aware
`read_dir(<COORD kind>)` call as the same sanctioned bypass) before this site can route without
breaking that gate. `#3055` tracks the follow-up. This is the one edge *this mission audited*
as directory-identical-routable and deliberately deferred. It is not the only unrouted
sanctioned `resolve_feature_dir_for_mission` coord-write: `widen/state.py:63`,
`agent_tasks_ports.py:322`, and `lanes/recovery.py:765` carry the same coord-authority
sanction, and `widen/state.py:63`'s rationale is verbatim-identical to this one — they were
simply not re-audited for the directory-identical-routing property this mission established
for `emit.py:71`. So the honest statement is "the one edge adjudicated and deferred," not "the
one call site in tension."

## Citations

- [ADR 2026-06-24-1: Kind- and Topology-Aware Artifact Placement — One Partition, Read/Write
  Symmetry](../adr/3.x/2026-06-24-1-kind-and-topology-aware-artifact-placement.md) — the
  governing decision for the L1 partition (`_PRIMARY_ARTIFACT_KINDS` /
  `_PLACEMENT_ARTIFACT_KINDS`) and for read/write symmetry across the two composition roots.
- [ADR 2026-07-23-1: `surface` names two unrelated domains — split the vocabulary, rename to
  `ToolSurfaceKind` and `TopologySurface`](../adr/3.x/2026-07-23-1-surface-vocabulary-two-domains-and-topology-surface-rename.md)
  — the governing decision for the `TopologySurface` vocabulary (including the
  `PRIMARY`/`COORD`/`LANE`/`CONSOLIDATED`/`TEMP` members) and the forbidden-conditioning rule
  (naming a surface is not licence to branch behavior on it).

See also the `Routing` disambiguation in
[`docs/context/orchestration.md`](../context/orchestration.md#routing) for every other sense of
"routing" this page deliberately does not cover, and
[`branch-target-routing.md`](branch-target-routing.md) for the **branch** sense — which git
branch a commit lands on, a related but distinct question from the placement question this page
answers.
