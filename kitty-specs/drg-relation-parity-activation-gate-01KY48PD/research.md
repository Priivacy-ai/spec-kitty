# Phase 0 Research — DRG completeness (#2843)

## D1 — Verify-first: the activation-gate bug is LIVE, not merely latent (FR-004)

**Decision**: Frame Item B as fixing a **live** correctness defect (silent under-resolution in charter-mediated paths), not a purely latent one.

**Evidence** (measured 2026-07-22 against the working tree):
- `.kittify/config.yaml:22` populates `activated_directives` with **26 directive stems** (`001-architectural-integrity-standard` … `046-common-docs`); `activated_tactics`, `activated_toolguides`, `activated_paradigms`, `activated_styleguides` are likewise populated; `.kittify/charter/charter.yaml:1405+` mirrors them.
- `PackContext.activated_directives` is read **un-normalized** from that list: `pack_context.py:212` → `_read_activated_directives` → `_read_list_key(data, "activated_directives")` (`:364`). It stores stems. `consistency_check.py:115` documents this verbatim ("holds config *stems*").
- `_node_is_activated` Step 3 (`drg.py:319`) compares the node's **canonical** `artifact_id` (`DIRECTIVE_001`) against that stem set → never matches → `return False` → node dropped.
- Three **live** callers run the filter: `mission_step_contracts/executor.py:182`, `reference_resolver.py:67`, `consistency_check.py:424`. The main `DoctrineService.get()` path is **exempt** (module docstring), so directives still load via the direct API — the bug manifests as **silent under-resolution in charter-mediated resolution**, not a crash.

**Consequence for the plan**: the red-first characterization test (NFR-001) can use this repo's real config + a charter-mediated path — no synthetic fixture needed. The fix is **behavior-changing** in those three paths (the 26 activated directives, currently dropped, will be retained). Any existing test asserting the current (buggy) filtered output is a stale assertion to update, not preserve (feeds NFR-002's "corrected observable", not "unchanged").

**Alternatives considered**: treat as latent (rejected — the config demonstrably populates the lists; "≈always None" in the pre-spec research was an over-generalization corrected here).

## D2 — Resolver siting: resolve-in-gate, roots from PackContext (FR-002, C-002, C-004)

**Decision**: `filter_graph_by_activation` resolves the activated **stems → canonical** **once per call** by **reusing** `charter.kind_vocabulary.resolve_artifact_urn`, building a `dict[kind, frozenset[canonical_urn] | None]` that `_node_is_activated` consumes as a pure membership check. **No public gate-signature change; `PackContext.activated_*` keeps holding stems.**

**Refined by the post-plan squad (paula + pedro, code-cited) — three binding corrections:**
- **Batch once, keep `drg.py` IO-lean.** Resolve at the filter entry (lift `_build_tension_active_urns`, `consistency_check.py:932-956`), NOT per-node — per-node is O(nodes×stems×fs-walk) and blows the ≤15 complexity ceiling. `_node_is_activated` takes the pre-resolved map. The deleted tension-scan trio is a ready-made template.
- **One doctrine-root source.** Use `resolve_doctrine_root()` (`charter.catalog`) — the same source the surviving compiler projection uses — NOT `pack_context.pack_roots[0]` (a naive `__file__` join with no fallback that can disagree in installed/wheel layouts and reintroduce the silent-drop class). `org_roots = pack_roots[1:]`. Pin gate-root == projection-root with a test; prefer a named `PackContext` accessor so the gate is not a third open-coded `pack_roots[1:]` copy (compiler `:144`, tension-scan `:940`).
- **Unknown stem → skip-with-report, never raise.** Catch `UnknownArtifactIdError` and `continue` (as `consistency_check.py:734-735`/`:902-903` do); `_check_unknown_references` reports it. Raising would throw through all five consumers, including the fail-closed-**report** `_check_graph_kind_parity` (`:811-812`).
- Compare on full URN (`"directive:DIRECTIVE_001"`) against `node.urn`, not bare `artifact_id`; `drg.py` needs its own small singular→`ArtifactKind` constant (the existing map lives in `consistency_check.py`, which imports `drg` → can't import back).

**Rationale**:
- `resolve_artifact_urn` (`kind_vocabulary.py:186`) already performs stem→canonical and is already reused by the compiler projection (`compiler.py:122`) and the tension-scan (`consistency_check.py:899`) — reusing it satisfies C-004/DIRECTIVE_044 (one normalizer) and shrinks the mission (no new resolver).
- The gate already receives `pack_context`; pulling roots from it avoids threading `doctrine_root`/`org_roots` through all five callers (no signature churn).
- The field stays stems, so the compiler projection, tension-scan, and their "holds stems" comments remain correct — minimal blast radius.
- Require-canonical (C-002): config authors stems; the gate resolves stems→canonical and matches on canonical. A raw canonical-id in config is **not** a supported input (no dual-branch tolerate-both). Unknown/unresolvable stems must be handled explicitly (resolver raises `UnknownArtifactIdError`) — decide skip-vs-error during implementation; a skip that silently drops is itself a bug, so prefer surfacing.

**Alternatives considered**:
- **Option B — normalize at PackContext construction** (store canonical in `activated_*`): rejected — changes what the shared field holds and ripples to every stem-expecting reader (compiler projection, tension-scan, their comments), a larger and riskier blast radius for no benefit.
- **Option A (new params)** — resolve-in-gate but thread `doctrine_root`/`org_roots` as new gate parameters: rejected in favor of sourcing from `pack_context` (same locality, no signature churn).

## D3 — Item A doc surface is a restructure, not a constant bump (FR-006)

**Decision**: Budget `doctrine-relationships.md` as a **restructure**: give each of the 15 relations its own `### …` section whose body equals its `RELATION_DESCRIPTIONS` entry (whitespace-normalized), then widen `_SCOPED_RELATIONS` 3→15.

**Evidence** (post-spec squad, daphne, code-cited): the parity comparator requires a dedicated per-relation heading and verbatim body equality. Today ~7 relations (`requires, suggests, applies, scope, vocabulary, instantiates, refines`) have **no heading** → `_find_heading_span` raises `LookupError`; `enhances`/`overrides`/`replaces` share one grouped heading (must split into three); Lineage/Delegation bodies are multi-paragraph prose + YAML that must reduce to the registry text. `docs/context/doctrine.md` is a glossary that deliberately **paraphrases** — it is NOT the parity surface; extend it as prose only (FR-008).

**Rationale**: prevents undersizing the doc lane and mis-scoping `context/doctrine.md` as a second enforced surface.

**Alternatives considered**: single grouped section covering multiple relations (rejected — the comparator extracts one shared body, so three distinct registry strings cannot all content-equal it).

## Cross-cutting

- **No DRG regen**: `RELATION_DESCRIPTIONS` is a Python dict, not serialized into any `*.graph.yaml`; Item A adds/renames no `Relation` member and no edge, so generated graphs are untouched (daphne, verified). `applies=1`/`scope=157` edge counts confirmed against tracked `src/doctrine/*.graph.yaml`.
- **Missed gate folded**: `tests/doctrine/drg/test_models.py` pins `RELATION_DESCRIPTIONS == {the 3}`; widening reds it → FR-007 converts to `== set(Relation)` (else NFR-002 violated).
- **Anti-sprawl ratchet retirement** (branch commit `ecb294f5e`) does not interact with Item A (content edits in existing files).
