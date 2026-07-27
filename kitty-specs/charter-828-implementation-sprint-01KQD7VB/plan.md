# Implementation Plan: Charter #828 Implementation Sprint

**Branch**: `docs/charter-end-user-docs-828` | **Date**: 2026-04-29 | **Spec**: [spec.md](spec.md)  
**Input**: `kitty-specs/charter-828-implementation-sprint-01KQD7VB/spec.md`  
**Source WPs**: `kitty-specs/charter-end-user-docs-828-01KQCSYD/tasks/`

## Summary

Execute the 10 pre-planned work packages from `charter-end-user-docs-828-01KQCSYD` against the `docs/charter-end-user-docs-828` branch to produce 14 new documentation pages, 5 updated pages, a validation report, and a release handoff artifact — all verified against live CLI output and committed to one PR targeting `main`. No product code changes; only `docs/` and `kitty-specs/charter-end-user-docs-828-01KQCSYD/` artifacts are written.

## Technical Context

**Language/Version**: Markdown (DocFX-flavoured); toolchain is Python 3.11+ via `uv run spec-kitty 3.2.0a5`  
**Primary Dependencies**: spec-kitty 3.2.0a5 (CLI truth source), DocFX (site generator), pytest (`tests/docs/`), uv (package runner)  
**Storage**: Markdown files committed to `docs/`; no database or external state  
**Testing**: `uv run pytest tests/docs/ -q` — zero failures gate for WP09/T036  
**Target Platform**: `docs/` directory, DocFX-generated site; PR target `Priivacy-ai/spec-kitty:main`  
**Project Type**: Documentation only — zero source code changes  
**Performance Goals**: N/A  
**Constraints**: Zero invented CLI flags (all content verified against `--help`); zero smoke-test pollution (isolated temp dirs, cleaned after); exact mission-phase-name match with `mission-runtime.yaml`

## Charter Check

Charter mode: **compact** (tools: git, spec-kitty; languages: python).

| Principle | Status | Notes |
|-----------|--------|-------|
| Use `uv run spec-kitty` not ambient binary | ✅ Compliant | C-001 in spec enforces this |
| SaaS-sync commands prefixed `SPEC_KITTY_ENABLE_SAAS_SYNC=1` | ✅ Compliant | C-002 in spec |
| No new planning mission for existing planning scope | ✅ Compliant | C-003: source WPs not re-planned here |
| CLI surface correctness (`charter synthesize`, `retrospect summary`, etc.) | ✅ Compliant | C-004; NFR-001 enforces zero invented flags |
| Documentation standards (Divio types, DocFX frontmatter) | ✅ Compliant | All pages follow DocFX + Divio conventions |
| Branch/release strategy (feature branch → PR → main) | ✅ Compliant | `docs/charter-end-user-docs-828` → PR #885 → main |

No charter conflicts. No violations to justify.

## Execution Strategy

### Phase Sequencing

```
PRE-FLIGHT
  git status --short --branch
  git pull --ff-only origin main
  uv run spec-kitty --version               # must be 3.2.0a5+
  uv run spec-kitty agent mission check-prerequisites \
    --mission charter-end-user-docs-828-01KQCSYD --json

PHASE 1: Foundation (sequential)
  WP01 — Gap analysis + navigation architecture
         Outputs: gap-analysis.md, docs/toc.yml updates,
                  docs/3x/toc.yml, section toc.yml files,
                  docs/2x/index.md archive notice,
                  docs/docfx.json updated (add docs/3x/ and docs/migration/)

PHASE 2: Content Generation (parallel after WP01)
  WP02  docs/3x/ Charter hub (3 pages)
  WP03  Tutorial: charter-governed-workflow.md
  WP04  How-To: governance, synthesis, missions, glossary (4 pages)
  WP05  How-To: retrospective + troubleshooting (2 pages)
  WP06  Explanation pages + redirect stub (4 pages)
  WP07  Reference: CLI + profile invocation (2 new + 1 updated)
  WP08  Reference: schema + migration + documentation-mission review (2 new + 1 reviewed)

PHASE 3: Validation (sequential, after all Phase 2 WPs)
  WP09  pytest + toc reachability + CLI flag check + phase accuracy + smoke tests
         Outputs: checklists/validation-report.md

PHASE 4: Ship (sequential, after WP09)
  WP10  Release handoff artifact + stale-text grep + branch cleanliness
         Outputs: release-handoff.md
```

### Content Inventory

| Type | Count | Key files |
|------|-------|-----------|
| New pages | 14 | docs/3x/(3), docs/tutorials/(1), docs/how-to/(4 new), docs/explanation/(3 new), docs/reference/(2 new), docs/migration/(1) |
| Updated pages | 5 | docs/how-to/setup-governance.md, docs/how-to/manage-glossary.md, docs/reference/cli-commands.md, docs/explanation/documentation-mission.md, docs/retrospective-learning-loop.md (→ redirect stub) |
| Nav files | 6 | docs/toc.yml, docs/3x/toc.yml, docs/how-to/toc.yml, docs/explanation/toc.yml, docs/reference/toc.yml, docs/migration/toc.yml |
| Config file | 1 | docs/docfx.json (add docs/3x/ and docs/migration/ entries) |
| Validation artifacts | 2 | checklists/validation-report.md, release-handoff.md |

### CLI Verification Rule (NFR-001)

Before writing any CLI reference content, capture live `--help` output:

```bash
uv run spec-kitty charter --help
uv run spec-kitty charter interview --help
uv run spec-kitty charter generate --help
uv run spec-kitty charter synthesize --help
uv run spec-kitty charter resynthesize --help
uv run spec-kitty charter status --help
uv run spec-kitty charter sync --help
uv run spec-kitty charter lint --help
uv run spec-kitty charter bundle --help
uv run spec-kitty next --help
uv run spec-kitty retrospect --help
uv run spec-kitty retrospect summary --help
uv run spec-kitty agent retrospect synthesize --help
```

Document only what `--help` confirms. If a subcommand returns "No such command", omit its section.

### Smoke Test Isolation (NFR-002)

All smoke tests run in `$(mktemp -d)` directories created outside the source repo. The smoke-test procedure:

```bash
TMPDIR=$(mktemp -d)
# run commands in $TMPDIR ...
rm -rf "$TMPDIR"
# verify: git status --short (source repo must be clean)
```

Zero uncommitted changes in the source repo after any smoke test.

### Phase Accuracy Rule (NFR-003)

Before writing any reference to documentation mission phases, read:

```bash
cat src/specify_cli/missions/documentation/mission-runtime.yaml
```

Use exact phase names from that file. Zero discrepancies allowed.

## Project Structure

### Planning artifacts (this sprint)

```
kitty-specs/charter-828-implementation-sprint-01KQD7VB/
├── spec.md              # Mission spec
├── plan.md              # This file
└── checklists/
    └── requirements.md
```

### Source WP prompts (read-only — do not modify)

```
kitty-specs/charter-end-user-docs-828-01KQCSYD/
├── tasks.md             # WP01–WP10 definitions
├── tasks/               # WP prompt files
│   ├── WP01-gap-analysis-and-navigation-architecture.md
│   ├── WP02-3x-charter-hub.md
│   ├── WP03-charter-tutorial.md
│   ├── WP04-howto-governance-synthesis-missions.md
│   ├── WP05-howto-retrospective-troubleshooting.md
│   ├── WP06-explanation-pages.md
│   ├── WP07-reference-cli-profile.md
│   ├── WP08-reference-schema-migration.md
│   ├── WP09-validation.md
│   └── WP10-release-handoff.md
└── checklists/          # WP09 + WP10 artifacts land here
    └── validation-report.md  (produced by WP09)
```

### Documentation output (written by WP02–WP08)

```
docs/
├── docfx.json           # Updated by WP01: add docs/3x/, docs/migration/
├── toc.yml              # Updated by WP01: add 3x/, relabel 2x/ as Archive
├── 3x/
│   ├── toc.yml
│   ├── index.md
│   ├── charter-overview.md
│   └── governance-files.md
├── tutorials/
│   └── charter-governed-workflow.md
├── how-to/
│   ├── setup-governance.md          (updated)
│   ├── synthesize-doctrine.md       (new)
│   ├── run-governed-mission.md      (new)
│   ├── manage-glossary.md           (updated)
│   ├── use-retrospective-learning.md (new)
│   └── troubleshoot-charter.md      (new)
├── explanation/
│   ├── documentation-mission.md     (reviewed/updated)
│   ├── charter-synthesis-drg.md     (new)
│   ├── governed-profile-invocation.md (new)
│   └── retrospective-learning-loop.md (new)
├── reference/
│   ├── cli-commands.md              (updated)
│   ├── charter-commands.md          (new)
│   └── profile-invocation.md        (new)
├── migration/
│   └── from-charter-2x.md          (new)
└── retrospective-learning-loop.md   (→ redirect stub, WP06/T024)
```

## Complexity Tracking

No charter violations. No complexity justifications required.
