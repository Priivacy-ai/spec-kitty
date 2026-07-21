# Contract: Resolved-binding record + WP-view reconstruction (FR-012..FR-015)

Behavioural contract for the resolved-binding half (operator decision 2026-07-20). Acceptance surface
for IC-07 (reconstruction reader), IC-08 (vocabulary + resolve seam), IC-09 (SaaS fan-out). Gated by the
C-009 field-authority ADR (IC-08a) landing first.

## Vocabulary (IC-08) — `WPInnerStateDelta` / claim `StatusEvent.actor`

Add resolved-binding fields (home decided by the C-009 ADR — delta slots vs structured actor):

```
resolved: { role, agent_profile, agent_profile_version, model, provider }
```

- **Source (dispatch→claim linkage, operator decision Q1)**: the genuine model+profile are resolved on the
  dispatch/Op path (`invocation/executor.py` `RoutingRecommendation`, `registry.resolve`; recorded in
  `invocation/record.py`, keyed by `invocation_id`) and **threaded into the implement/review commands**
  (new `--model`/`--profile`/`--invocation-id` on `cli/commands/agent/workflow.py`) — the claim seam alone
  has only the bare `--agent` string. **NEVER** a copy of the frontmatter `agent_profile` string (C-007 / INV-6).
- **Written**: at each pick-up/claim/reassign transition, as an **`InnerStateChanged` annotation** (so it
  folds latest-wins at BOTH implement-claim and review-claim — the `policy_metadata` claim fold fires only
  on `planned→claimed`), **plus** enriching the transition's structured `actor` for the IC-09 fan-out.
- **Reduced**: latest-wins into snapshot resolved slots (`_RUNTIME_SLOTS` + `_apply_annotation_delta`).
- **Historical non-seed (C-011)**: authored recommendations are never copied into resolved actuals;
  deterministic authored-derived seed rows are invalid and must be removed by exact seed identity.
- **Absence is valid**: a never-reclaimed WP has no resolved slot → reconstruction shows empty resolved.

## Reconstruction reader (IC-07) — `status/wp_view.py::reconstruct_wp_view(feature_dir, wp_id)`

Single reader replacing the three hand-rolled gates (dashboard scanner, `agent tasks status` board,
`WorkPackage`). Returns a view with **two distinct** identity groups:

| Group | Source | Fields |
|-------|--------|--------|
| `resolved` (actual) | snapshot (event-sourced) | lane, agent, assignee, subtasks, review, resolved role/profile(+version)/model/provider |
| `authored` (recommended) | frontmatter (static) | authored role/agent_profile/model, owned_files, dependencies, requirement_refs, … |

- **Contract**: all three consumers call this reader; none hand-rolls a snapshot gate afterward (SC-007).
- **Tolerate-absent**: absent resolved slots → `authored` populated, `resolved` empty; never the authored
  value returned in the `resolved` group (INV-7).
- **subtasks authority**: the snapshot `subtasks` slot, not `tasks.md` checkbox counting (resolves the
  dashboard split-brain).

**Acceptance (US6):**
1. implement-claim (P1/M1) → `resolved` = P1/M1 from the event log; `authored` shown separately.
2. later review-claim (P2/M2) → `resolved` updates to P2/M2 (latest-wins), 0 bytes to `tasks/WP##.md`.
3. dashboard, status board, `WorkPackage` all agree for the same WP (one reader).
4. never-reclaimed WP → `authored` populated, `resolved` empty (no crash, no masquerade).
5. recorded resolved profile came from `resolve_profile`/`resolved_agent()`, not the frontmatter string.

## SaaS fan-out (IC-09)

- **Preferred**: enrich the structured `actor` (`{role, profile, tool, model}`) on the claim/review
  `StatusEvent` + its existing `_saas_fan_out`. `spec_kitty_events` 6.1.0 `StatusTransitionPayload.actor`
  is already `Union[str, Dict]` → **zero shared-package change**. Feature-detect the dict actor defensively.
- **Fallback**: `WPResolvedBindingChanged` shared event + a fan-out added to `emit_inner_state_changed`
  (none today), version-gated (`hasattr(spec_kitty_events, "WPResolvedBindingChanged")`, mirroring the
  genesis-lane gate). Land the local event now; enable fan-out when the package ships (never block-on-shared).
- **Acceptance**: a claim transition's fan-out payload carries the resolved `{role, profile, tool, model}`;
  with an older `spec_kitty_events`, the new-event fan-out is skipped (logged) and local persistence is
  unaffected.

## Cross-cutting

- **C-009 ADR precedes vocabulary** — the per-field authority (resolved role/profile/model → dynamic;
  authored → static) is ratified before IC-08 lands.
- **Dogfood re-seed (IC-08)** — after extending the backfill vocabulary, re-run the corpus backfill in the
  same merge unit so IC-07 reads seeded resolved slots (else empty for the dogfood corpus).
- **No suppression / complexity ≤15 / no repo-root write** (NFR-004, C-003) apply as for the cutover half.
