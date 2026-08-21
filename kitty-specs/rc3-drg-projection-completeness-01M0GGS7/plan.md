# Implementation Plan: M2 — DRG projection completeness

**Mission**: rc3-drg-projection-completeness-01M0GGS7
**Spec**: [spec.md](spec.md) · **Grounding**: [research.md](research.md)
**Target branch**: `rc3-drg-projection-completeness-01M0GGS7` (non-protected feature
branch; PR to `upstream/main` is the closeout — operator merges)

## Overview

Close the two **emit-seam** completeness gaps where authored doctrine validates,
loads, then is silently dropped before it reaches the committed DRG goldens
(`packs/built-in/*.graph.yaml`), **verify-and-close** the **delivery-seam**
residual (no code gap survives on `main` — the fix is surfacing + a structural
bind), and **bind the two seams** so they cannot silently re-diverge. Regenerate
the golden graph **exactly once**, as a dedicated final step, after both extractor
edits land and after M3 (`#3617`) merges.

## Architecture — the two seams

```
authored YAML ──emit──▶ packs/built-in/*.graph.yaml ──cascade──▶ resolved reach ──delivery──▶ agent-visible text
  (doctrine)   extractor.py        (DRG goldens)                 profile_sections.py renderers
```

- **Emit seam** — `src/doctrine/drg/migration/extractor.py` projects authored YAML
  into DRG edges. Two gaps: (a) the procedures loop drops authored `when`/`reason`;
  (b) no pass projects a mission type's type-wide `governance-profile.yaml`.
- **Delivery seam** — `src/charter/context_renderers/profile_sections.py` renders
  resolved reach into agent text. On current `main` this is **complete** (bodies
  render, step `description` renders, styleguide/toolguide pointer-only is a
  documented deliberate choice). The residual is discoverability + a structural
  test binding emit↔delivery.

## Design decisions (locked; from spec + grounding)

1. **#3605 — reuse the single authority.** Replace the inline `DRGEdge(...)` in the
   procedures loop (`extractor.py:878–906`) with `**_reference_edge_kwargs(ref)`
   (`:542`), matching directive/tactic/paradigm. **NFR-002/AC-009 invariant:** the
   edge **triple** set `(source, target, relation)` must stay byte-identical — only
   `when`/`reason` metadata is added. Optionally (FR-002) extract one shared emit
   helper and add a structural assertion that all five `{type,id,when?,reason?}`
   branches route through it (mechanism: `inspect.getsource` + regex over
   `extract_artifact_edges` — no existing pattern to mirror, so name it explicitly).
2. **#3604 — net-new, differently-shaped pass.** Add a function that walks
   `packs/built-in/missions/*/governance-profile.yaml` and emits
   `mission_type:<t> --scope--> <selected_* target>` for all four types. Relation
   `scope`, source node `mission_type` (**C-003, operator-decided** — both are
   existing `Relation`/`NodeKind` members; cascade already follows `scope`, so zero
   traversal churn). The `mission_type:<t>` node already exists
   (`_discover_mission_type_nodes:1177`); wire the pass next to `extract_action_edges`
   (`:1044`). Targets are **bare ids**, not `{type,id}` dicts — so it does **not**
   reuse `_reference_edge_kwargs`.
3. **`_DRG_NODE_KINDS` fold.** Add `"mission_type"` to the frozenset at
   `src/charter/synthesizer/topic_resolver.py:37` — load-bearing because #3604 emits
   `mission_type` as an edge source.
4. **#3488 — verify-and-close + bind (C-004).** No delivery-path code change (the
   rc1 gaps are shipped and correct). Close the **residual**: (a) surface the
   pointer-only styleguide/toolguide contract for pack authors (doc + an assertion
   that pins the documented reason), (b) surface the `operating_procedures_unresolved`
   fail-closed diagnostic in docs, (c) build the **FR-008** anti-divergence structural
   test binding projection to delivery (a channel projected into the DRG must be
   body-delivering **or** carry an attested pointer-only contract — a channel added on
   one seam but not the other fails).
5. **Single re-ledger, deferred.** One `spec-kitty doctrine regenerate-graph` after
   both extractor edits land (C-002); a dedicated final step, not "whoever lands
   edit #2". **Landing-sequence:** run it only after **M3 (#3617) merges** — rebase
   onto landed M3 first, regenerate once, then verify M3's cascade tests stay green
   against the re-ledgered goldens. `--check` clean immediately after (NFR-001). Never
   hand-edit goldens (C-001).

## Work package breakdown

| WP | Scope | FRs / ACs | Touches | Depends |
|----|-------|-----------|---------|---------|
| **WP01** | #3605 procedure rationale via `_reference_edge_kwargs` + red-first `test_procedure_reference_reason_roundtrips` + NFR-002 triple-identity assertion; optional FR-002 single-helper structural test | FR-001, FR-002, NFR-002 / AC-001, AC-002, AC-009 | `extractor.py`; `tests/doctrine/drg/migration/test_extractor.py` | — |
| **WP02** | #3604 governance-profile.yaml → `mission_type --scope--> gov` pass (4 types) + `_DRG_NODE_KINDS` fold + red-first rewrite of `test_cascade.py:449` + new count assertions (31/23/160/plan-populated) | FR-003, FR-004, FR-005, FR-006 / AC-003, AC-004, AC-005 | `extractor.py`, `topic_resolver.py`; `tests/charter/test_cascade.py` | WP01 (same file `extractor.py` — sequence, don't parallel-lane) |
| **WP03** | #3488 verify-close: doc-surface pointer-only + unresolved diagnostic; net-new FR-008 anti-divergence structural test | FR-007, FR-008 / AC-006, AC-007 | `docs/…`, new test under `tests/charter/` | — (independent of WP01/02) |
| **WP04** | Single golden re-ledger: `regenerate-graph` once, commit `packs/built-in/*.graph.yaml`, `--check` clean | FR-009, NFR-001, C-001, C-002 / AC-008 | `packs/built-in/*.graph.yaml` | **WP01 + WP02**; **external: M3 (#3617) merged** |

**Ownership/lanes:** WP01 and WP02 both edit `extractor.py`, so they must run
**sequentially in one lane** (no-overlap is the real guard — DIRECTIVE-025 /
ownership-map). WP03 is doc/test-only and independent. WP04 is the terminal
re-ledger gate. A single lane running WP01→WP02→WP03→WP04 is the clean topology for
a mission this size; WP04 additionally blocks on the external M3 merge.

## Testing strategy (red-first / ATDD)

- **AC-001 (WP01):** `test_procedure_reference_reason_roundtrips` mirrors the
  directive/tactic roundtrip tests (`test_extractor.py:266,313`) — RED before the
  `_reference_edge_kwargs` wiring, GREEN after.
- **AC-009 (WP01):** triple-diff assertion — pre/post procedure edge `(source,
  target, relation)` sets identical; only metadata added.
- **AC-003 (WP02):** **rewrite** `test_cascade.py:449`
  `test_plan_cascade_is_empty_because_its_actions_scope_no_governance` (revise its
  rationale comment `:452–459`); move `mission_type:plan` into
  `_GOVERNANCE_BEARING_MISSION_TYPE_URNS` (`:406`). RED (plan empty) before #3604,
  GREEN (plan cascades to its 1 directive / 9 tactics / 3 paradigms / 1 styleguide)
  after.
- **AC-004 (WP02):** per-type `scope`-edge coverage for all four types; **new**
  count-pinned assertions (documentation 31 / research 23 / software-dev 160 / plan
  populated) — none exist today, so these are net-new, moved in the same PR as the
  code (not retro-fitted).
- **AC-007 (WP03):** the FR-008 structural test fails if a channel is projected into
  the DRG but neither delivered nor attested pointer-only.
- **Baseline-red discipline:** attribute any red against a green merge-base baseline
  before folding (behavior-preservation on the shipped delivery path).
- **Static gates:** ruff + mypy clean, no new suppressions. `regenerate-graph
  --check` clean after WP04.

## Risks & mitigations

- **Golden double-churn** → single dedicated re-ledger WP (WP04); neither extractor
  edit is "done" until it runs.
- **#3605 byte-identity** → triple-diff assertion (AC-009); a changed triple is
  silent graph corruption.
- **Stale #3488 re-fix** → C-004 verify-first (grounded: no code gap); the durable
  deliverable is the FR-008 bind, not re-fixing shipped code.
- **Cascade-count churn** → count-pinned assertions land red-first in the same PR;
  documented cascade counts move by design.
- **`scope`/`mission_type` baked into goldens** → decided (C-003) before the re-ledger.

## Landing sequence (per program notes)

M2's file surface (`src/doctrine/drg/`, `src/charter/`, `packs/built-in/*.graph.yaml`)
is **disjoint** from M7 (in progress; `ownership/`+`mission_runtime/`+`lanes/`) and
from M3 (`#3617`; charter gate). The only coordination is the golden re-ledger: **M3
lands first**, then M2 rebases and runs its single `regenerate-graph`, then confirms
M3's cascade tests stay green against the re-ledgered goldens. Implement WP01–WP03
now; gate WP04 on M3.

## Post-plan adversarial squad (advisory)

Warranted (canonical-source / doctrine-projection surface). Lenses: (1) NFR-002
triple-identity rigor on #3605; (2) C-003 `scope`/`mission_type` grain correctness
for cascade traversal; (3) C-004 anti-over-reach on the shipped #3488 delivery path.
Fold MAJORs; file MINOR/NOTE as one follow-up.
