---
work_package_id: WP05
title: Chain-delivery verification, both classes (#3530 close)
dependencies:
- WP04
requirement_refs:
- FR-011
- FR-012
planning_base_branch: fix/doctrine-drg-silent-drop-boundary
merge_target_branch: fix/doctrine-drg-silent-drop-boundary
branch_strategy: Planning artifacts for this mission were generated on fix/doctrine-drg-silent-drop-boundary. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/doctrine-drg-silent-drop-boundary unless the human explicitly redirects the landing branch.
subtasks:
- T021
- T022
- T023
- T024
history:
- at: '2026-08-23T00:00:00Z'
  actor: tasks
  note: WP created
agent_profile: python-pedro
authoritative_surface: tests/integration/
create_intent:
- tests/integration/test_org_pack_chain_delivery.py
- tests/doctrine/fixtures/minimal_org_pack_2/drg/fragment.yaml
execution_mode: code_change
owned_files:
- tests/integration/test_org_pack_chain_delivery.py
- tests/doctrine/fixtures/minimal_org_pack_2/**
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

`/ad-hoc-profile-load python-pedro` (+ `spec-kitty charter context --action
implement --json`). Apply + state what you applied. Shadow venv:
`export PATH="$PWD/.venv/bin:$PATH"`.

## Objective

Evidence #3530's closing condition on the real `packs/internal/` pack (class-b,
fragment-drop) AND a 2nd minimal org fixture (class-a, multi-org-pack fold), with
enumerated misconfig fail-loud. Depends on WP04 (the caller fix must land first).

## Context (squad finding F10)

- `merge_three_layers` already iterates **all** fragments (`merge.py:1251`); the
  historical "only-first-pack" bug was the caller seam, already fixed by #3525. So
  a single org pack (built-in + internal) exercises only **class-b** (this
  mission's fragment-drop). To pin the **class-a** multi-org-pack fold you need
  **≥2 org packs** and must assert **pack #2's** fragment reaches the merged graph.
- `packs/internal/` declares: `glossary_packs:spk-internal-glossary`,
  `procedures:landing-contributor-prs`, `directives:OPERATOR_SIGNAL_CONTRACT`, and
  `refines` edges to built-in `procedure:red-main-release-discipline` /
  `tactic:pr-agent-worktree-isolation`.
- Reusable references: `tests/integration/test_three_layer_drg_end_to_end.py`,
  `test_org_pack_artifact_lifecycle.py`, `tests/doctrine/test_overlay_precedence.py`,
  fixture shapes under `tests/doctrine/fixtures/org_pack_template_asset/valid_pack/`.

## Subtasks

### T021 — 2nd minimal org fixture pack
- New `tests/doctrine/fixtures/minimal_org_pack_2/drg/fragment.yaml` (canonical org
  shape: plural node kinds, `body_path` where needed, singular `<kind>:<id>` edge
  URNs). Declare ≥1 distinctive node (e.g. `directives:MINIMAL_ORG_2_MARKER`) and
  optionally a `refines` edge to a real built-in target so it merges clean.
- **G10 guard**: neither this fixture nor `packs/internal` may carry a
  governance-profile `selected_*` selection — WP03's org-tier guard would raise on
  an unresolved one. Keep the fixtures fragment/refines-only so class-b/class-a
  assert delivery, not governance fail-loud (that is WP03's territory). This is why
  WP05 depends only on WP04, not WP03.

### T022 — Class-b delivery test (built-in + internal)
- In `tests/integration/test_org_pack_chain_delivery.py`: register `packs/internal`
  as an org tier over built-in; drive the executor / action-doctrine-bundle path
  (the seam WP04 fixed); assert every kind internal declares (glossary pack,
  procedure, directive) and its `refines` edges reach the consumer.

### T023 — Class-a multi-org-pack fold test
- Register built-in + internal + `minimal_org_pack_2` as a 2-org-pack chain; assert
  **pack #2's** distinctive fragment node/edge (`MINIMAL_ORG_2_MARKER`) appears in
  the merged graph (proves fragments past the first are folded — the class-a path
  a single-pack fixture cannot prove).

### T024 — Enumerated misconfig fail-loud tests
- Parametrized cases, each asserting a **raise** (not warn) with a target-naming
  message: (i) a `refines` edge → nonexistent built-in target; (ii) a fragment
  missing a required key; (iii) a declared kind with no node. Contrast with the
  honest "no graph" **warning** for a genuinely graphless root (that is WP04's
  behaviour, asserted here as a warn, not a raise).

## Branch Strategy

Planning base + merge target: `fix/doctrine-drg-silent-drop-boundary`. Worktrees
per computed lane from `lanes.json` at implement time. This WP depends on WP04.

## Definition of Done

- Class-b: built-in + internal delivers 100% of internal's declared kinds via the
  WP04-fixed seam.
- Class-a: the 2nd fixture's fragment node/edge reaches the merged graph in a
  2-org-pack chain.
- 3 enumerated misconfigs each raise with a naming message; graphless root warns
  (not raises).
- `ruff` clean on new tests/fixtures; no new suppressions.
- Targeted green: `pytest tests/integration/test_org_pack_chain_delivery.py -q`
  (and the daemon/real-port caveat does not apply — these are in-process DRG loads).
- #3530 closing condition met (leaving the explicitly-non-child #3412 open).

## Risks / reviewer guidance

- Depends on WP04 — if the seam fix is not merged first, class-b will red for the
  wrong reason. Reviewer: confirm class-a asserts **pack #2** specifically (not just
  "some org node"), else it does not prove the multi-org-pack fold (F10). Confirm
  misconfig cases assert raise vs the graphless warn.
