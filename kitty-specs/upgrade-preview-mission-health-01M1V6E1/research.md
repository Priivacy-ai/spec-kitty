# Research: Upgrade Preview Reliability and Mission Corpus Health

Audience: agentic-framework-core-team. Updated: 2026-09-06.
Baseline source: c0054153b9bce0778cf41a85d11ecd4e9650031d.
Creation commit df19b88f1c89ac0510ef9fb00c606e364db1c711 adds mission metadata;
reviewers observed that concurrent advance, not a source behavior change.

## Findings and Decisions

1. Root callback runs runtime, global skills and global commands ensure paths
   before upgrade handles preview (src/specify_cli/__init__.py:123-138).
   Read-only intent must be known before startup mutation. Ordinary bootstrap
   and non-mutating compatibility gates must continue working.
2. SurfacePlanBuilder is the existing generated-surface inventory authority
   (src/specify_cli/tool_surface/plan.py:22). Providers/installers own physical
   changes; existing dry-run ID lists omit manifests, pruning and bundle writes.
   Extend these owners rather than build a parallel CLI filename registry.
3. Upgrade finalization performs provisioning, surface repair and generated
   churn commits (src/specify_cli/upgrade/finalize.py:26). Compose a read-only
   assessment of these owner decisions; no migrations must not mean no writes.
4. Target validation already belongs to upgrade/runner.py:59. JSON branches
   before it at cli/commands/upgrade.py:1260. Share validation before rendering.
5. The legacy compat-planner contract has additionalProperties:false and fixed
   enums. Preserve that pinned consumer contract; provide an explicit opt-in
   full-plan representation, never encode surface repairs as fake migrations.
   Target rejection must also be fixed on the existing JSON dry-run surface.
6. Ownership preservation outranks matching unsafe existing writes. Inspect
   manifest_store.py:448,509: adopting arbitrary canonical-path content and
   prefix-based symlink deletion can destroy customizations. Narrowly fix these
   touched repair paths with non-vacuous custom-content/symlink sentinels.
7. Reproduced #3903 with public doctor audit: exit 1, 424 directories, four
   errors/TeamSpace blockers. Same four original failures; other warnings/info
   are not accepted for blanket repair.

## Corpus Provenance

- R2-T1-local-legacy-removal contains two program evidence documents, introduced
  at 0be7d692adcc71503ad1c3b0ad6b0d16accdef62 and
  557a55946d9a23f0c4f7bf4311eb02bb8d3d04cb. Relocate byte-for-byte outside
  immediate mission scanning; update references. Do not create identity.
- reject-cyclic-lane-graphs-01M0QCK4 is a real mission with immutable identity
  01M0QCK4D9D65AVNC15HKWAQZ7. Recover its full historical record from
  3442ca1afc20b1b83b27a7bc64fd7014050b12a1, matching the pre-convergence public
  parent. Convergence 2554bd13adc289d3457681308645fe52619bca0e removed 31
  historical files while retaining its consumed schema. Restoring metadata
  alone would hide lost history, not resolve the issue.
- doctrine-drg-silent-drop-boundary-01M0PE7E and
  symbolkey-source-module-01M0B0SF snapshots equal transition-only projections.
  Canonical replay restores annotation metadata while preserving eight done
  lanes and all eight review_result objects. Use mission-scoped
  agent status materialize; preserve raw event hashes, verdicts, IDs and
  provenance. Replay twice to verify idempotence.

## Evidence and Verification Plan

Three independent profile-loaded pre-spec reviewers inspected current source:
Architect Alphonso (authority/design), Reviewer Renata (test fakeability), and
Debugger Debbie (live corpus audit/provenance). Their external reports live in
the parent workspace under pre-spec-architect-alphonso, pre-spec-reviewer-renata,
and pre-spec-debugger-debbie. Core issue sources are linked in spec.md.

Public-entry-point subprocess acceptance must cover cold/stale/warm homes,
ignored paths, directories, symlinks, modes, per-file mtimes, complete JSON stdout,
target ordering and real preview/apply equivalence. Snapshot oracle gets its
own mutation controls. A separately installed wheel witness prevents source
overrides from concealing packaging behavior. Every subprocess rebinds HOME,
XDG/runtime/tool roots and SaaS sync=0 into its sandbox. No production network.

## Risks and Open Technical Work

- Full physical-effect reporting requires installer cooperation; serializing
  current provider dry-runs is insufficient. Plan interfaces before WP fan-out.
- Legacy invalid-target mapping must stay truthful and strict-schema-valid.
- Corrupt config/manifest or unavailable sources must report incomplete/blocked
  planning rather than successful empty work or silently broaden agent scope.
- Governance compact/runtime resolution is degraded, filed as #3908. Read
  binding charter/profile sources explicitly; no successful-resolution claim.
- E2E inventory moved to spec-kitty/EXPERIMENTAL-spec-kitty-end-to-end-testing.
  Inspect current floor scenarios rather than assuming retired SaaS test exists.
- No product decisions remain deferred; implementation details belong in plan.
