# Post-Tasks Adversarial Review

**Date**: 2026-08-09  
**Point cut**: after `/spec-kitty.tasks`, before finalization/analyze  
**Method**: three independent, profile-loaded, read-only reviewers covering
requirements/dependencies, ownership/architecture, and evidence/falsification;
root acted as arbiter.

## Findings and dispositions

| Severity | Finding | Disposition |
|---|---|---|
| High | WP01 would merge expected-red behavior tests. | WP01 remains green census/instrumentation/positive-control work; each behavior WP owns and greens its first red test. |
| High | `delivery/targets.py` and `sync/__init__.py` escaped the one-store ownership graph. | WP05 owns target registry/interfaces/exports; WP04 owns the live offline-queue constructor and every current payload writer. |
| High | Migration promised every writer used a layout barrier without owning those writers. | WP02 owns the sole layout-generation/write-permit API; WP04 wires all current writers; WP10 owns snapshot/cutover orchestration only. |
| High | Contract selection used an ambient sibling path and cross-repo acceptance ownership was circular. | Core WP05 requires explicit SaaS WP04 checkout/commit/contract digest. Core owns conforming bytes/parking; SaaS owns bypass/zero-effect/hosted evidence. Reviewed SaaS WP02/WP08 are pinned prerequisites for WP11. |
| High | Sender/crash work was too broad and opt-out did not settle orphaned attempts. | Split protocol, interactive transports, daemon/background, aggregate race proof, migration, and evidence into WP06-WP11. Opt-out reconciles or irrevocably parks every older prepared/in-flight/unknown attempt before acknowledgement, including kill-during-response → opt-out → late recovery. |
| High | Architecture-only profiles were assigned to code-changing packages. | Every code-changing package uses `python-pedro`; architecture profiles remain review-only. |
| Medium | Closure evidence had no immutable schema/retention and issue WPs were null. | Added schema-versioned SHA-256 manifest, producer ownership, exact commits/digest, 90-day CI retention, and explicit issue-to-WP mappings. |

## Final verdict

PASS. `finalize-tasks --validate-only` reports 11 WPs and zero ownership warnings.
All 54 task IDs, 100 exact owned paths, requirement mappings, YAML/JSON, create
intent, and `git diff --check` pass. Production and the historical 1,322-event
cohort remain untouched.
