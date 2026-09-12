---
work_package_id: WP13
title: Terminal reconcile (shared manifests) + flip gates blocking + pre-merge build
dependencies:
- WP05
- WP06
- WP07
- WP08
- WP09
- WP10
- WP11
- WP12
requirement_refs:
- FR-016
- FR-020
- FR-022
- NFR-001
- NFR-003
- NFR-010
planning_base_branch: docs/common-docs-cleanup
merge_target_branch: docs/common-docs-cleanup
branch_strategy: Planning artifacts for this mission were generated on docs/common-docs-cleanup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/common-docs-cleanup unless the human explicitly redirects the landing branch.
subtasks:
- T037
- T038
- T039
- T040
history:
- at: '2026-08-10T03:30:00Z'
  actor: claude
  event: created
agent_profile: python-pedro
authoritative_surface: scripts/docs/redirect_map.yaml
create_intent:
- .github/workflows/docs-build-pr.yml
execution_mode: code_change
owned_files:
- scripts/docs/redirect_map.yaml
- docs/toc.yml
- docs/docfx.json
- docs/llms.txt
- docs/development/3-2-page-inventory.yaml
- docs/development/3-2-docs-retrieval-index.yaml
- CLAUDE.md
- AGENTS.md
- .github/workflows/docs-build-pr.yml
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile
```
/ad-hoc-profile-load python-pedro
```
Confirm: this is the SINGLE writer of all shared manifests (C-011). Run pytest+ruff+mypy + the docs gates
before handoff.

## Objective
Terminal integration: merge every mover's occurrence-map fragment, regenerate all derived shared
manifests + lockfiles, fix the cross-cutting refs, register the required pre-merge DocFX build, and flip
the structural gates to blocking. Runs LAST (after all movers). See [plan.md](../plan.md) IC-11/IC-03b, OB-2.

## Subtasks
- **T037** — Merge all per-WP occurrence-map fragments into the collapsed cumulative spine; regenerate
  the DERIVED `scripts/docs/redirect_map.yaml` via `redirect_stub_generator.py regenerate-map
  --occurrence-map <this mission>`; run `coverage` + `check-map` and verify **zero** dead targets and
  that all prior baseline URLs + this mission's moves are covered (NFR-010/SC-010). Include the 14
  archive/ prior-redirect targets and all ADR dated-prefix renames.
- **T038** — Regenerate the nav manifests (`docs/toc.yml`, `docs/docfx.json` — drop the dead `apidoc/**`
  glob, `docs/llms.txt`, per-section `toc.yml`) and the inventory lockfiles (`3-2-page-inventory.yaml`,
  `3-2-docs-retrieval-index.yaml`) IN PLACE via `inventory_lockfile.py` (these are owned across ~10 live
  missions — regenerate, never relocate/reassign; sequence if any owning mission is mid-flight).
- **T039** — Apply link-target-only fixes to inbound `related:`/body links under `docs/plans/**` that
  point at moved pages (no plans restructure — C-001); update the ~4 `CLAUDE.md` + `AGENTS.md` doc-path
  references and the `CONTRIBUTING.md` symlink target per WP10/WP11's moved-page lists.
- **T040** — Add the required pre-merge DocFX build workflow `.github/workflows/docs-build-pr.yml`
  (`pull_request`: `docfx docs/docfx.json` zero-error blocks; `redirect_stub_generator coverage`;
  `seo_verify --strict` on built `_site`) per [contracts/pre-merge-build-contract.md](../contracts/pre-merge-build-contract.md), and flip the
  WP04 structural invariants (incl. the T041 root-allowlist check) from advisory to blocking — verify
  every generated redirect stub carries the `description: "Redirect stub: …"` prefix (FR-022) so
  `shadow_tree_basename` skips it — **respecting OB-2**: enforce single-root /
  sanctioned-section as terminal verification, and only register a standing blocking single-root lint if
  #2851 is re-sanctioned (else keep it as the terminal green-check + curation). Run the full local gate
  set from [quickstart.md](../quickstart.md) and confirm green.

## Branch Strategy
Base/merge: `docs/common-docs-cleanup`. Worktree per `lanes.json` lane. This WP is the single
integration point — no mover runs concurrently with it on the shared manifests.

## Definition of Done
- redirect_map regenerated (derived) with zero dead targets + full prior+new coverage; nav manifests +
  lockfiles regenerated in place; plans/CLAUDE/AGENTS/CONTRIBUTING refs fixed; required pre-merge docfx
  build workflow added; structural gates blocking (OB-2 respected); full local gate set green.

## Risks
- Sole writer of shared manifests — if a mover edited one, reconcile/reject per C-011.
- The rollups are owned by other live missions (C-005) — coordinate timing; do not reassign ownership.
- Registering a required check touches branch protection (operator action) — note in the PR body if the
  check must be enabled in GitHub settings.
