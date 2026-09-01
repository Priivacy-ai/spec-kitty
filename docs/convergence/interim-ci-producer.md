---
doc_status: active
updated: '2026-08-30'
---

The existing factory `.github/workflows/ci.yml` remains untouched and is not an upstream restore.

| path | disposition | reason |
|---|---|---|
| `.github/workflows/ci-quality.yml` | restore | Restored as the reduced five-job interim producer on stock runners: `lint`, `build-wheel`, `clean-install-verification`, `uv-lock-check`, and `quality-gate`. |
| `.github/workflows/protect-main.yml` | restore | Restored on `ubuntu-latest` so the promoted tree has the Phase-1 exit check-run; rebase-merge association checking is retained. |
| `.github/workflows/ci-windows.yml` | restore | Restored on stock runners with the obsolete `tests/sync/*` path filters removed. |
| `.github/workflows/docs-pages.yml` | restore | Restored on `ubuntu-latest`; the existing docs build scripts and Pages deployment contract are live on this tree. |
| `.github/workflows/check-spec-kitty-events-alignment.yml` | restore | Restored on `ubuntu-latest`; its drift script and pinned metadata surfaces are live on this tree. |
| `.github/workflows/all-contributors-normalize.yml` | never-restore | Pre-fork contributor automation is not part of the MVP and has no current contributor-data contract. |
| `.github/workflows/all-contributors-sync.yml` | never-restore | Pre-fork contributor automation is not part of the MVP and has no current contributor-data contract. |
| `.github/workflows/canonical-producer-lint.yml` | defer | The producer lint is potentially useful, but restoring it requires a current docs-producer ownership audit after the interim topology lands. |
| `.github/workflows/docs-build-pr.yml` | defer | A PR-side docs build can be reduced later; `docs-pages.yml` provides the required deploy-side producer for this phase. |
| `.github/workflows/docs-freshness.yml` | defer | Current docs tests already cover freshness invariants; a separate workflow needs path-scope reconciliation first. |
| `.github/workflows/doctrine-charter-tests.yml` | defer | Its suites belong to the factory CI topology; restoring a second producer before topology reconciliation would duplicate authority. |
| `.github/workflows/module-doctrine-fast.yml` | defer | The reduced `ci-quality.yml` intentionally excludes the old modular suite topology; any restored parallel fast selector must also exclude `timing` (#94). |
| `.github/workflows/module-doctrine-integration.yml` | defer | The reduced `ci-quality.yml` intentionally excludes the old modular suite topology. |
| `.github/workflows/module-kernel.yml` | defer | The reduced `ci-quality.yml` intentionally excludes the old modular suite topology. |
| `.github/workflows/module-packs.yml` | defer | The reduced `ci-quality.yml` intentionally excludes the old modular suite topology. |
| `.github/workflows/orchestrator-boundary.yml` | never-restore | It guards the pre-fork orchestrator boundary rather than the current programme topology. |
| `.github/workflows/plantuml-egress-spike.yml` | never-restore | The spike is superseded by the pinned, no-egress PlantUML render path in `docs-pages.yml`. |
| `.github/workflows/plugin-validate.yml` | defer | Plugin validation is valuable but outside the interim CI producer and needs a current plugin-surface audit. |
| `.github/workflows/regen-assets.yml` | defer | Generated-asset regeneration needs a current ownership and artifact audit before another producer is added. |
| `.github/workflows/ui-e2e.yml` | defer | Cross-repo E2E belongs to the e2e repository and factory CI topology, not this interim CLI producer. |
| `.github/workflows/release.yml` | restore | Restored on `ubuntu-latest` with the wheel-content gate re-pointed to `src/charter/offering` and its bundled skills. |
| `.github/workflows/release-readiness.yml` | restore | Restored on `ubuntu-latest`; the cutover guard runs from source without resolving the CLI's git direct references. |
| `.github/workflows/scripts/check-release-exists.sh` | defer | Release script; owned by the P3.4b release topology sibling. |
| `.github/workflows/scripts/create-github-release.sh` | defer | Release script; owned by the P3.4b release topology sibling. |
| `.github/workflows/scripts/create-release-packages.sh` | defer | Release script; owned by the P3.4b release topology sibling. |
| `.github/workflows/scripts/generate-release-notes.sh` | defer | Release script; owned by the P3.4b release topology sibling. |
| `.github/workflows/scripts/get-next-version.sh` | defer | Release script; owned by the P3.4b release topology sibling. |
| `.github/workflows/scripts/update-version.sh` | defer | Release script; owned by the P3.4b release topology sibling. |
| `.github/workflows/drift-detector.yml` | never-restore | The CLI-to-SaaS sync transport is deleted; the workflow's subject no longer exists. |
| `.github/workflows/project-sync-consent-evidence.yml` | never-restore | The CLI-to-SaaS sync transport is deleted; the workflow's subject no longer exists. |
| `.github/workflows/review-verdict-durability.yml` | never-restore | Programme verdict durability is owned by GitHub comments and the planning provenance contract, not this pre-fork workflow. |
| `.github/workflows/teamspace-mission-state-readiness.yml` | never-restore | The pre-fork teamspace readiness surface is not part of the current MVP topology. |
| `.github/workflows/performance.yml` | never-restore | Performance pipelines are out of the MVP; timing coverage remains in the local full suite. |
| `.github/workflows/ci-flake-report.yml` | never-restore | Flake classification is the deterministic CI and merge agents' responsibility, not a separate GitHub Actions producer. |
| `.github/workflows/mutation-remediation.md` | never-restore | Documentation for an absent mutation workflow; it has no live subject on this tree. |
