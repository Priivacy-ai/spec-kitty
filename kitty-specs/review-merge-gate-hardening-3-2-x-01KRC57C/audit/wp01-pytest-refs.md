# WP01 Audit: `uv run pytest` Reference Classification

**Mission**: review-merge-gate-hardening-3-2-x-01KRC57C  
**WP**: WP01 — Hermetic mission-review gate invocation  
**FR**: FR-001, FR-002  
**Audit date**: 2026-05-12  

## Methodology

Searched the worktree for every `uv run pytest` reference:

```bash
rg -n 'uv run pytest' --type md --type py --type yaml --type toml
```

Each reference was classified as:

- **release-gate**: documentation that instructs an operator or CI system to run a gate command as part of a release or migration ceremony. Replacing these with `uv run python -m pytest` eliminates PATH fallthrough.
- **developer-convenience**: instructions for contributors iterating locally; these references live in planning artifacts, spec files, or contributor guides where a mis-configured developer environment fails fast and is fixed locally — not at release time.

## Audit Table

| File:line | Verbatim | Classification | Rationale |
|-----------|----------|----------------|-----------|
| `docs/migration/teamspace-mission-state-repair.md:89` | `uv run pytest tests/migration/test_teamspace_migration_rehearsal.py -q` | **release-gate** | "Cross-Repo Rehearsal" section; documents CLI-side rehearsal run as part of the 920 mission-state repair migration ceremony |
| `docs/migration/teamspace-mission-state-920-closeout.md:61` | `SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run pytest tests/contract/... -q` | **release-gate** | "Verification run" / "Commands run in the clean checkout" section; formal release closeout verification |
| `docs/migration/teamspace-mission-state-920-closeout.md:62` | `uv run pytest tests/audit -q` | **release-gate** | Same "Verification run" section; formal release closeout verification |
| `kitty-specs/077-mission-terminology-cleanup/tasks/WP05-inverse-drift-refactor.md:365` | `PWHEADLESS=1 uv run pytest tests/specify_cli/...` | developer-convenience | Spec/task artifact; implementation guidance for a contributor |
| `kitty-specs/077-mission-terminology-cleanup/tasks/WP13-scope-b-acceptance-gate.md:78` | `PWHEADLESS=1 uv run pytest tests/contract/...` | developer-convenience | Spec/task artifact; contributor verification step |
| `kitty-specs/077-mission-terminology-cleanup/tasks/WP04-next-cmd-and-agent-tasks-refactor.md:253` | `PWHEADLESS=1 uv run pytest tests/specify_cli/...` | developer-convenience | Spec/task artifact |
| `kitty-specs/077-mission-terminology-cleanup/tasks/WP02-selector-resolution-helper.md:409` | `uv run pytest tests/specify_cli/...` | developer-convenience | Spec/task artifact |
| `kitty-specs/077-mission-terminology-cleanup/tasks/WP02-selector-resolution-helper.md:416` | `PWHEADLESS=1 uv run pytest tests/specify_cli/...` | developer-convenience | Spec/task artifact |
| `kitty-specs/077-mission-terminology-cleanup/tasks/WP10-scope-a-acceptance-gate.md:145` | `uv run pytest --cov=... tests/specify_cli/...` | developer-convenience | Spec/task artifact |
| `kitty-specs/077-mission-terminology-cleanup/tasks/WP10-scope-a-acceptance-gate.md:185` | `PWHEADLESS=1 uv run pytest tests/contract/...` | developer-convenience | Spec/task artifact |
| `kitty-specs/077-mission-terminology-cleanup/tasks/WP10-scope-a-acceptance-gate.md:190` | `PWHEADLESS=1 uv run pytest tests/contract/...` | developer-convenience | Spec/task artifact |
| `kitty-specs/077-mission-terminology-cleanup/tasks/WP10-scope-a-acceptance-gate.md:208` | `PWHEADLESS=1 uv run pytest tests/contract/...` | developer-convenience | Spec/task artifact |
| `kitty-specs/077-mission-terminology-cleanup/tasks/WP09-grep-guards.md:160` | `PWHEADLESS=1 uv run pytest tests/contract/...` | developer-convenience | Spec/task artifact |
| `kitty-specs/077-mission-terminology-cleanup/tasks/WP09-grep-guards.md:191` | `PWHEADLESS=1 uv run pytest tests/contract/...` | developer-convenience | Spec/task artifact |
| `kitty-specs/077-mission-terminology-cleanup/tasks/WP09-grep-guards.md:211` | `PWHEADLESS=1 uv run pytest tests/contract/...` | developer-convenience | Spec/task artifact |
| `kitty-specs/077-mission-terminology-cleanup/tasks/WP09-grep-guards.md:281` | `PWHEADLESS=1 uv run pytest tests/contract/...` | developer-convenience | Spec/task artifact |
| `kitty-specs/077-mission-terminology-cleanup/tasks/WP09-grep-guards.md:291` | `PWHEADLESS=1 uv run pytest tests/contract/...` | developer-convenience | Spec/task artifact |
| `kitty-specs/077-mission-terminology-cleanup/tasks/WP12-canonical-field-rollout.md:183` | `PWHEADLESS=1 uv run pytest tests/contract/...` | developer-convenience | Spec/task artifact |
| `kitty-specs/077-mission-terminology-cleanup/quickstart.md:50` | `uv run pytest tests/specify_cli/...` | developer-convenience | Spec quickstart; contributor guidance |
| `kitty-specs/077-mission-terminology-cleanup/quickstart.md:69` | `uv run pytest tests/specify_cli/...` | developer-convenience | Spec quickstart |
| `kitty-specs/077-mission-terminology-cleanup/quickstart.md:129` | `uv run pytest tests/specify_cli/...` | developer-convenience | Spec quickstart |
| `kitty-specs/077-mission-terminology-cleanup/quickstart.md:156` | `uv run pytest tests/specify_cli/...` | developer-convenience | Spec quickstart |
| `kitty-specs/077-mission-terminology-cleanup/quickstart.md:240` | `uv run pytest tests/contract/...` | developer-convenience | Spec quickstart |
| `kitty-specs/077-mission-terminology-cleanup/quickstart.md:268` | `PWHEADLESS=1 uv run pytest tests/` | developer-convenience | Spec quickstart |
| `kitty-specs/077-mission-terminology-cleanup/quickstart.md:269` | `uv run pytest --cov=...` | developer-convenience | Spec quickstart |
| `kitty-specs/local-custom-mission-loader-01KQ2VNJ/tasks/WP07-nfr-enforcement.md:134` | `uv run pytest \` | developer-convenience | Spec/task artifact |
| `kitty-specs/charter-e2e-827-followups-01KQAJA0/spec.md:117` | `uv run pytest tests/architectural -q` (and others, NFR-003 list) | developer-convenience | NFR definition in spec artifact |
| `kitty-specs/charter-e2e-827-followups-01KQAJA0/plan.md:176-187` | multiple `uv run pytest ...` | developer-convenience | Implementation plan artifact |
| `kitty-specs/charter-e2e-827-followups-01KQAJA0/tasks.md:47,82,115,147` | multiple `uv run pytest ...` | developer-convenience | Task outline artifact |
| `kitty-specs/charter-e2e-827-followups-01KQAJA0/quickstart.md:27-33,46,54,64,72,89,151-152` | multiple `uv run pytest ...` | developer-convenience | Spec quickstart |
| `kitty-specs/charter-e2e-827-followups-01KQAJA0/tasks/WP01-uv-lock-pin-drift-detector.md:168,175,181,202` | multiple `uv run pytest ...` | developer-convenience | Spec/task artifact |
| `kitty-specs/charter-e2e-827-followups-01KQAJA0/tasks/WP02-charter-e2e-prompt-file-contract.md:130,137,138,161,207,228-231` | multiple `uv run pytest ...` | developer-convenience | Spec/task artifact |
| `kitty-specs/charter-e2e-827-followups-01KQAJA0/tasks/WP03-dossier-snapshot-no-self-block.md:184,203` | multiple `uv run pytest ...` | developer-convenience | Spec/task artifact |
| `kitty-specs/charter-e2e-827-followups-01KQAJA0/tasks/WP04-specify-plan-commit-boundary.md:304,308,328,329` | multiple `uv run pytest ...` | developer-convenience | Spec/task artifact |
| `kitty-specs/research-mission-composition-rewrite-v2-01KQ4QVV/mission-review.md:206,212` | `uv run pytest tests/specify_cli/...` | developer-convenience | Post-mission review artifact |
| `kitty-specs/research-mission-composition-rewrite-v2-01KQ4QVV/tasks/WP03-drg-nodes-and-edges.md:177,178` | `uv run pytest tests/specify_cli/...` | developer-convenience | Spec/task artifact |
| `kitty-specs/research-mission-composition-rewrite-v2-01KQ4QVV/tasks/WP04-profile-defaults-and-composition-test.md:107,114,115` | `uv run pytest tests/specify_cli/...` | developer-convenience | Spec/task artifact |
| `kitty-specs/research-mission-composition-rewrite-v2-01KQ4QVV/tasks/WP06-real-runtime-walk-and-smoke.md:110,135` | `uv run pytest tests/...` | developer-convenience | Spec/task artifact |

## Release-Gate Files Targeted by T002

Only these 3 files (2 files, 3 lines) receive replacements:

1. `docs/migration/teamspace-mission-state-repair.md` line 89
2. `docs/migration/teamspace-mission-state-920-closeout.md` lines 61 and 62

## Classification Rationale

The `docs/migration/` tree is the operator-facing migration runbook. The "Cross-Repo Rehearsal" and "Verification run" sections explicitly describe commands the release operator runs in a clean checkout to validate the migration before shipping. These are part of the formal release gate ceremony and must use hermetic invocation (`python -m pytest`) to prevent PATH fallthrough to a system-installed pytest.

The `kitty-specs/` tree holds planning artifacts (specs, plans, tasks, quickstarts) that agents and contributors read during implementation. Instructions there are advisory; a misfire fails fast locally with no release-gate consequence.

The `src/specify_cli/missions/software-dev/command-templates/review.md` was checked and contains no `uv run pytest` references.

The `.github/workflows/` directory was checked and contains no `uv run pytest` references.
