---
work_package_id: WP09
title: DRG Provenanced[T] wrapper + consumer migration
dependencies: []
requirement_refs:
- FR-007
tracker_refs: []
planning_base_branch: fixups/code-engine-stabilization
merge_target_branch: fixups/code-engine-stabilization
branch_strategy: Planning artifacts for this mission were generated on fixups/code-engine-stabilization. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fixups/code-engine-stabilization unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-tooling-stability-guard-coherence-01KTRC04
base_commit: add42e46c5442ecd2d1c8c00015fab3fa5c727f1
created_at: '2026-06-10T14:50:33.662830+00:00'
subtasks:
- T034
- T035
- T036
- T037
phase: Phase 1 - Independent lanes
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "125328"
history:
- at: '2026-06-10T11:47:55Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: ''
authoritative_surface: src/doctrine/drg/
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/drg/merge.py
- src/glossary/entity_pages.py
role: ''
tags: []
task_type: implement
---

# Work Package Prompt: WP09 – DRG Provenanced[T] wrapper

## ⚡ Do This First: Load Agent Profile
Use `/ad-hoc-profile-load`; pick the best implementer match if none assigned.

---

## Objectives & Success Criteria
#1624 (DIRECTIVE_013): `doctrine/drg/merge.py::_tag_source` attaches provenance to frozen Pydantic models via
`object.__setattr__` — an untyped sidecar. Operator decision D2: replace with a typed **`Provenanced[T]`**
generic carrier (model + provenance; the model stays unpolluted).
- **Inventory FIRST** (split-review right-sizing: the ripple is ~2 real consumers — `drg/merge.py:480` and `src/glossary/entity_pages.py:164` — NOT 3 layers; verify, and if you find materially more, STOP and report before migrating).
- Introduce `Provenanced[T]` (frozen dataclass, Generic, `__all__`); `_tag_source` returns the carrier; the merge pipeline's internal handling adapts.
- Migrate the consumers: `getattr(node, "provenance", None)` → typed attribute access on the carrier.
- **Done when:** grep-zero `getattr(.*"provenance"` and `object.__setattr__.*provenance` in src/; `mypy --strict` clean on the DRG path; typed round-trip test.

## Context & Constraints
- Design (absolute): `kitty-specs/tooling-stability-guard-coherence-01KTRC04/{spec.md (FR-007), plan.md (IC-08), data-model.md §3, contracts/ (C-DRG-1), research/plan-review-reducer-randy.md + plan-review-python-pedro.md (consumer right-sizing)}` + ticket #1624 (notes the generic `TypeVar` half already landed — DON'T redo it).
- This is a **public-shape change in the Governance bounded context**: anything holding a DRG node and expecting a `.provenance` monkey-patched attribute changes shape. The inventory (T034) gates everything; STOP-and-escalate if larger than the 2 confirmed sites.
- DRG `graph.yaml` is generated + freshness-tested — if the merge pipeline output shape changes serialization, regenerate per the documented procedure (see memory/DRG docs); ideally the carrier is unwrapped before serialization so graph.yaml is unchanged.

## Branch Strategy
- Planning base / merge target: `fixups/code-engine-stabilization`. Populated by finalize-tasks.

## Subtasks & Detailed Guidance

### T034 — Consumer inventory (gate)
- `rg -n 'getattr\(.*"provenance"|\.provenance\b|object\.__setattr__.*provenance' src tests` — confirm the full set (expected: merge.py internal writes + :480 read; entity_pages.py:164). Record the inventory in the commit message. If >4 sites or a serialization dependency appears → STOP, report.

### T035 — `Provenanced[T]` carrier
- Frozen `@dataclass Provenanced(Generic[ModelT]): value: ModelT; provenance: str`. `_tag_source` constructs it instead of `object.__setattr__`. Keep the existing `TypeVar` generic typing (already landed). Ensure graph serialization unwraps `.value` (graph.yaml byte-stable — verify with the freshness test).

### T036 — Migrate consumers + mypy
- `drg/merge.py:480` + `src/glossary/entity_pages.py:164` consume the typed carrier. `python -m mypy src/doctrine/drg/merge.py --strict` clean; no new `type: ignore`.

### T037 — Tests + grep gate
- Typed round-trip test (tag → read provenance → unwrap model identity); the grep gate as an assertion-style test or DoD check; DRG freshness test green (graph.yaml unchanged).

## Definition of Done
- Inventory recorded; grep-zero sidecar patterns; mypy strict clean; graph.yaml freshness green; `ruff` clean.

## Risks & Mitigations
- *Ripple larger than inventoried* → T034 is a hard gate; STOP-and-escalate, never half-migrate.
- *graph.yaml churn* → unwrap before serialization; freshness test is the canary.

## Review Guidance
- Recommended: **architect-alphonso sign-off** (Governance public-shape change) + **reviewer-renata**. Verify the inventory completeness and that serialization is shape-stable.

## Activity Log
- 2026-06-10T11:47:55Z – system – Prompt created.
- 2026-06-10T14:58:15Z – unknown – shell_pid=38158 – T034 HARD GATE TRIPPED — STOP-and-escalate (no half-migration). Inventory: object.__setattr__ provenance WRITE = 1 (merge.py:219, _tag_source, called at 6 sites: 273/322/461/464/484/486). getattr(...,'provenance') READS in src = 2 (merge.py:480 internal warn-path; glossary/entity_pages.py:164 external) — matches the prompt's '~2 consumers'. graph.yaml has NO serialization dependency on the attribute (generated by migration/extractor.generate_graph, NOT by merge_three_layers), so byte-stability is naturally safe. BUT the carrier design (D2 / Provenanced[T]) cannot be confined to those 2 sites: _tag_source's return flows into DRGGraph(nodes=list[DRGNode], edges=list[DRGEdge]) — a public Pydantic container. A Provenanced[DRGNode] cannot populate DRGGraph.nodes without changing the container's public shape, which additionally breaks DRGGraph convenience methods (node_urns/get_node/edges_from/edges_to read .urn/.source/.target on the same objects) and 15 test read-sites across 5 files (test_drg_merge=3, test_org_drg_loader=5, test_three_layer_drg_end_to_end=3, test_org_drg_edge_source_urn_preserved=2, test_project_layer_override_emits_warning=2) that read both n.urn AND getattr(n,'provenance'). The research right-sizing (python-pedro/reducer-randy) counted only the getattr CALL sites and missed that those objects flow through a typed DRGGraph container + 15 test assertions. mypy --strict on merge.py is ALREADY clean (the generic TypeVar half of #1624 landed). FR-007 itself offered 'Provenanced[T] wrapper OR a declared optional field on the models — decide in plan'; the plan chose D2 (wrapper). Recommendation to escalate: either (a) re-scope WP09 to add provenance as a declared Optional[str] field on DRGNode/DRGEdge (the field alternative FR-007 sanctioned — naturally typed, no container change, graph.yaml stays stable IF excluded from serialization), accepting the ~17-site touch, or (b) explicitly accept the Provenanced[T] container reshape as in-scope (large ripple, public-shape change in Governance bounded context, needs architect-alphonso sign-off). NOT half-migrating per WP risk-gate + spec FR-007 risk + CLAUDE.md canonical-sources discipline. No code changed; lane clean.
- 2026-06-10T15:28:30Z – user – shell_pid=38158 – Declared-field design (D2-revised): added provenance: str|None=None to DRGNode/DRGEdge; _tag_source now uses model_copy(update=...); deleted object.__setattr__ sidecar; consumer at merge.py:480 reads .provenance directly (entity_pages.py:164 kept getattr — node is Any-typed). graph.yaml byte-stable (extractor writes fields explicitly, never via _tag_source). Gates: mypy --strict clean, ruff clean, grep gate zero sidecar, 137 DRG/charter/integration tests + new typed round-trip class green.
- 2026-06-10T15:29:39Z – claude:opus:reviewer-renata:reviewer – shell_pid=125328 – Started review via action command
- 2026-06-10T15:32:55Z – user – shell_pid=125328 – Review passed: declared provenance:str|None field on DRGNode/DRGEdge replaces object.__setattr__ sidecar (zero remaining); _tag_source returns model_copy(update=) and both bridge sites + seed-maps now consume the returned copy (no silent discard); extractor _node_to_dict/_edge_to_dict are explicit field-by-field writers that never reference provenance, so graph.yaml is byte-stable (unchanged in diff); entity_pages:164 getattr retention accepted (node is duck-typed/Any there, sibling 'definition' is non-field metadata read the same way); mypy --strict clean (no new ignores), 123 DRG tests pass, ruff clean.
