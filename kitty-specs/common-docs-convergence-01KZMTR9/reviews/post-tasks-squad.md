---
title: Post-Tasks Adversarial Squad — Common Docs Convergence
doc_status: active
updated: '2026-08-10'
---
# Post-Tasks Adversarial Squad Review (anti-laziness)

Mission: `common-docs-convergence-01KZMTR9`. Point-cut: post-tasks, pre-analyze/implement.
Squad: 2 lenses (completeness/anti-laziness; ownership/lane-soundness). Dispositions per
`contracts/adversarial-evidence-contract.md`.

## Fixed in the WP set (re-finalized: a80425bac)
- **Ownership #1 (HIGH)** — WP10 didn't own the flat `docs/development/*.md` sources it must move.
  **Fixed:** WP10 owned_files += `docs/development/*.md`, `docs/development/toc.yml` (`.md`/named-file
  scoping avoids the WP13 `3-2-*.yaml` rollups).
- **Ownership #2 / completeness M4 (HIGH)** — WP07 wrote distilled content into `docs/adr/<era>/`
  (WP08's tree). **Fixed:** T020 now hands distilled content to WP08 (which owns `docs/adr/**` + depends
  on WP07 + authors it in T024); WP07 keeps only the `architecture/` source deletion.
- **Ownership #4 (HIGH)** — shipped `src/doctrine/templates/diagrams/README.md` anchor repoint unowned.
  **Fixed:** added to WP07 owned_files.
- **Ownership #5 (MED)** — WP11 context destinations + 12 existing context files unowned. **Fixed:**
  WP11 owns `docs/context/*.md` (non-recursive; disjoint from WP02's `docs/context/audience/**`).
- **Ownership #3 (HIGH)** — per-section `toc.yml` two-writer. **Fixed (adjudicated):** each mover owns
  its section `toc.yml`; WP13 is single writer of GLOBAL manifests only (root toc/docfx/llms/redirect_map
  + CLAUDE/AGENTS + plans link-targets). C-011 relaxed for section-local toc; documented in tasks.md.
- **Completeness M1 (MED)** — `gap_analysis.py` subdir-name pin unowned. **Fixed:** added
  `src/specify_cli/doc_analysis/gap_analysis.py` to WP10 (corrected path).
- **Completeness H1 (HIGH)** — root-allowlist check (NFR-006/SC-002) had no subtask. **Fixed:** new
  T041 in WP04 (advisory) + flipped blocking in WP13 T040.
- **Completeness H2 (HIGH)** — `plans/notes/` terminology-exemption reconcile (NFR-004) dropped.
  **Fixed:** new T042 in WP11 (+ owns the two terminology-guard test files).
- **Completeness M2 (MED)** — `check_cli_reference_freshness` not in PR gate. **Fixed:** added to WP04 T014.
- **Completeness C1 (CRITICAL)** — rewrite dimension open-ended. **Fixed (bounding):** tasks.md now sets
  a per-WP ceiling (≤10 rewritten pages), an enumerated-from-touched-set rule, and a per-page fidelity
  ledger; enumeration is produced by the mover at implement (pages don't exist at final paths until moved).
- **Completeness L1 (LOW)** — FR-022 stub-prefix verification. **Fixed:** added to WP13 T040.
- **Completeness L2 (LOW)** — WP08 title truncated (a `#2887` started a YAML comment). **Fixed:** quoted title.

## Deferred / accepted (recorded, resolve at implement or WP-claim)
- **Ownership #6 (MED)** — `docs/doctrine/create-a-doctrine-artifact.md` (WP07 source) →
  `docs/development/how-to/` (WP10 dest) is a cross-lane move with no WP07↔WP10 edge.
  **deferred_with_rationale:** each WP owns its own endpoint (WP07 deletes source, WP10 authors dest);
  the occurrence-map records the move; the redirect spine + WP13 reconcile cover link integrity. If
  ordering bites at implement, add a WP10←WP07 edge. Low blast radius (single file).
- **Completeness M3 (MED)** — the 13 free-text `audience:` pages aren't pre-enumerated.
  **deferred_with_rationale:** distributed to movers by section; WP02/WP04 whole-tree `audience_resolver
  --strict` (WP13 final green) is the backstop that catches any page missed. A mover claiming a WP should
  grep its section for free-text `audience:` first.
- **Completeness M5 (MED)** — new-persona authoring path (mover needs a persona not in the catalog;
  can't write WP02's authority-path surface). **deferred_with_rationale:** WP02 T005 pre-authors known
  needs; a mid-flight gap escalates to a WP02-scoped follow-up (movers must not write
  `docs/context/audience/**`).
- **Completeness L3 (LOW)** — `docs/doctrine/*.md → architecture/` vs the config's `doctrine_artifact →
  src/doctrine/` routing. **accepted:** these are docs ABOUT doctrine (explanation), not doctrine
  artifacts; occurrence-map records the rationale; the extended-lint sanctioned-section check treats
  `architecture/` as valid.
- **Ownership #7/#8/#9 (LOW)** — occurrence_map dual-writer (WP03 authors, WP13 merges — planning
  partition, exempt from lane ownership); DAG WP05→movers edge dropped (deliberate parallelization,
  file-partitioned so collision-safe); WP11 tasks.md/frontmatter prose drift. **accepted** (cosmetic /
  by-design; frontmatter is authoritative).

## Coverage
All FR-001..024, NFR-001..010, SC-001..010 have a WP home; the previously-unbuilt verifications
(NFR-006 root-allowlist, NFR-004 exemption, NFR-009 PR freshness wiring, FR-018 gap_analysis) now have
owners. Sizing OK (every WP ≤ ~6 subtasks; no lane too thin). No post-plan fold silently dropped.
Re-finalized clean: 13 WPs / 42 subtasks / 13 lanes.
