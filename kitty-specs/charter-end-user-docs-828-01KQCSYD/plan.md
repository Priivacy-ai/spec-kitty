# Implementation Plan: Charter End-User Docs Parity (#828)

**Branch**: `docs/charter-end-user-docs-828` | **Date**: 2026-04-29 | **Spec**: [spec.md](spec.md)
**Mission ID**: `01KQCSYDGQN09RV05M6V8Q5H1B` | **Slug**: `charter-end-user-docs-828-01KQCSYD`
**Mission**: `charter-end-user-docs-828-01KQCSYD`
**Input**: `/Users/robert/spec-kitty-dev/spec-kitty-20260429-161241-ycLfiR/spec-kitty/kitty-specs/charter-end-user-docs-828-01KQCSYD/spec.md`

## Summary

Bring Spec Kitty end-user documentation to parity with the shipped Charter-era product by producing a documentation PR on branch `docs/charter-end-user-docs-828` that targets `main`. The IA strategy is **Hybrid (C)**: a new `docs/3x/` directory acts as the Charter-era hub for the current mental model and deep product surfaces, while the main Divio sections (`tutorials/`, `how-to/`, `reference/`, `explanation/`) are updated so new users find Charter workflows where they naturally look. `docs/2x/` is relabeled as historical archive.

## Technical Context

**Language/Version**: Markdown (DocFX site — toc.yml hierarchy, no build-tool version pinned)
**Primary Dependencies**: DocFX-compatible Markdown; `tests/docs/` pytest suite; `uv run spec-kitty` for CLI reference verification
**Storage**: Flat file — `docs/` tree in the repository root
**Testing**: `tests/docs/` (test_architecture_docs_consistency.py, test_readme_canonical_path.py, test_versioned_docs_integrity.py); link-integrity checks; command-snippet smoke
**Target Platform**: GitHub-rendered docs + DocFX site build
**Project Type**: Documentation-only mission — no product source changes
**Performance Goals**: N/A (documentation)
**Constraints**: No source-repo pollution from smoke commands; `SPEC_KITTY_ENABLE_SAAS_SYNC=1` for any command touching hosted auth/tracker; all snippets must parse cleanly
**Scale/Scope**: ~18 new or updated pages across tutorials/, how-to/, reference/, explanation/, docs/3x/, and docs/migration/; plus gap-analysis.md and release handoff

## Charter Check

- **DIRECTIVE_003** (Decision Documentation Requirement): The IA strategy decision (hybrid, docs/3x/ hub) is recorded in `decisions/DM-01KQCV1G5DQQ3GV6ZP391DB8NR.md`. No further governance decisions are open.
- **DIRECTIVE_010** (Specification Fidelity): All generated pages must faithfully implement the corresponding FR row. CLI reference must be verified against `uv run spec-kitty --help` output, not assumed.
- **Code quality gates** (pytest, mypy, coverage): Not applicable — this mission produces no product source code. Docs-suite tests must pass.
- **No violations requiring justification.**

## Project Structure

### Documentation artifacts (this mission)

```
kitty-specs/charter-end-user-docs-828-01KQCSYD/
├── spec.md                  # Mission specification
├── plan.md                  # This file
├── research.md              # Phase 0: gap analysis and audit findings
├── data-model.md            # Phase 1: IA structure and page map
├── quickstart.md            # Phase 1: implementer orientation
├── decisions/               # Decision moment records
├── checklists/
│   └── requirements.md      # Spec quality checklist (passing)
└── tasks.md                 # Phase 2 output (created by /spec-kitty.tasks)
```

### Repository docs tree (existing + planned changes)

```
docs/
├── index.md                               # (existing — no change)
├── toc.yml                                # UPDATE: add 3x/ entry; relabel 2x/ as Archive; do NOT register retrospective-learning-loop at root level (it moves to explanation/)
├── retrospective-learning-loop.md         # EXISTING — currently not in toc.yml; integrate + split
├── 1x/                                    # archive (no change)
├── 2x/                                    # UPDATE: add archive label to index.md
│   └── index.md                           # UPDATE: "This section describes 2.x behavior. See 3.x Docs for current."
├── 3x/                                    # NEW: Charter-era hub
│   ├── index.md                           # Charter hub landing
│   ├── charter-overview.md                # Current-state Charter model: synthesis, DRG, bundle
│   ├── governance-files.md                # Authoritative vs generated files
│   └── toc.yml                            # 3x section nav
├── tutorials/
│   ├── toc.yml                            # UPDATE: add charter-governed-workflow entry
│   └── charter-governed-workflow.md       # NEW: end-to-end tutorial (setup → synthesis → mission → retro)
├── how-to/
│   ├── setup-governance.md               # UPDATE: add current Charter synthesis/bundle flow
│   ├── synthesize-doctrine.md            # NEW: dry-run, apply, status, lint, provenance, recovery
│   ├── run-governed-mission.md           # NEW: spec-kitty next, composed steps, blocked decisions
│   ├── use-retrospective-learning.md     # NEW: summary, synthesizer dry-run/apply, exit codes
│   └── troubleshoot-charter.md           # NEW: stale bundle, missing doctrine, compact context, synth rejection
├── explanation/
│   ├── charter-synthesis-drg.md         # NEW: Charter as synthesis/DRG model
│   ├── governed-profile-invocation.md   # NEW: (profile, action, gov-context) primitive; lifecycle trails
│   └── retrospective-learning-loop.md   # NEW: split from root-level file into Divio shape
├── reference/
│   ├── cli-commands.md                  # UPDATE: add Charter-era command surface
│   ├── charter-commands.md              # NEW: Charter subcommand reference (interview, generate, context, status, sync, lint, bundle)
│   ├── profile-invocation.md            # NEW: ask/advise/do, invocation trail, lifecycle
│   └── retrospective-schema.md          # NEW: retrospective.yaml schema, proposal kinds, event fields
└── migration/
    └── from-charter-2x.md               # NEW: upgrade path from 2.x/early-3.x Charter projects
```

## Complexity Tracking

No Charter Check violations. No unjustified complexity.

## Phase 0: Gap Analysis and Research

**Output**: `research.md` (see [research.md](research.md))

### Key findings (summary)

| Area | Current state | Gap |
|---|---|---|
| `how-to/setup-governance.md` | present-stale (2.x prerequisites, interview/generate/sync only) | Add Charter synthesis, bundle validation, DRG context |
| `docs/2x/` section | present-stale (not labeled as archive) | Add archive label to index.md |
| Charter tutorial | missing | New `tutorials/charter-governed-workflow.md` |
| Synthesis/resynthesis how-to | missing | New `how-to/synthesize-doctrine.md` |
| Governed mission how-to | missing | New `how-to/run-governed-mission.md` |
| Retrospective how-to | missing | New `how-to/use-retrospective-learning.md` |
| Troubleshooting | missing | New `how-to/troubleshoot-charter.md` |
| Charter/DRG explanation | missing | New `explanation/charter-synthesis-drg.md` |
| Profile invocation explanation | missing | New `explanation/governed-profile-invocation.md` |
| Retrospective explanation | present-stale (root level, not in nav, has TODO marker) | Move to `explanation/retrospective-learning-loop.md`, register in toc.yml |
| CLI reference (Charter era) | present-stale (cli-commands.md predates Charter subcommands) | New `reference/charter-commands.md`; update `reference/cli-commands.md` |
| Profile invocation reference | missing | New `reference/profile-invocation.md` |
| Retrospective schema reference | missing | New `reference/retrospective-schema.md` |
| Migration docs | missing | New `migration/from-charter-2x.md` |
| docs/3x/ hub | missing | New `docs/3x/` directory with index, charter-overview, governance-files |

## Phase 1: Design and Contracts

**Output**: `data-model.md` (see [data-model.md](data-model.md)) and `quickstart.md` (see [quickstart.md](quickstart.md))

### IA decision (resolved)

Decision `DM-01KQCV1G5DQQ3GV6ZP391DB8NR`: Hybrid (C) — `docs/3x/` as Charter hub + updates to main Divio sections. See `decisions/` for full rationale.

### Linking strategy

- Every new Divio page links to the `docs/3x/` hub for the canonical Charter mental model.
- The `docs/3x/` hub links outward to each Divio page for the corresponding workflow.
- `docs/retrospective-learning-loop.md` (root level) becomes a redirect stub pointing to `explanation/retrospective-learning-loop.md` to preserve any existing external links.
- `docs/2x/index.md` gains a clear archive notice pointing to `docs/3x/index.md` for the current equivalent.

### Page count

| Action | Count |
|---|---|
| New pages | 14 |
| Updated pages | 5 |
| Total | 19 |

## Work Package Sequencing (for /spec-kitty.tasks)

Recommended sequencing (not task files — those are produced by /spec-kitty.tasks):

1. **Gap analysis** — produce `gap-analysis.md` in the mission directory (full Divio coverage matrix)
2. **IA design** — finalize `docs/3x/toc.yml`, update root `docs/toc.yml`, update `how-to/toc.yml`, `tutorials/toc.yml`, `explanation/toc.yml`, `reference/toc.yml`
3. **Core tutorial** — `tutorials/charter-governed-workflow.md`
4. **How-to cluster** — `setup-governance.md` update + four new how-to pages
5. **Explanation cluster** — three explanation pages
6. **Reference cluster** — `charter-commands.md`, `profile-invocation.md`, `retrospective-schema.md`, `cli-commands.md` update
7. **docs/3x/ hub** — `index.md`, `charter-overview.md`, `governance-files.md`
8. **Migration + archive** — `migration/from-charter-2x.md`, `docs/2x/index.md` archive label
9. **Validation** — run `tests/docs/`, link checks, snippet smoke, CLI flag verification
10. **Release handoff** — produce handoff artifact, update docs release notes if maintained

## Validation Checklist (for Validate phase)

All of the following must pass before the PR is opened:

- [ ] `uv run pytest tests/docs/ -q` — zero failures
- [ ] DocFX link integrity or equivalent link checker — zero broken links in changed pages
- [ ] All changed pages reachable from toc.yml entries — manual spot-check
- [ ] No `TODO: register in docs nav` text remains in any changed file
- [ ] Command snippets in all new pages parse and run cleanly against a temp project
- [ ] `uv run spec-kitty charter --help` (and each subcommand `--help`) matches reference content in `charter-commands.md`
- [ ] Documentation mission phases in all pages match `mission-runtime.yaml`
- [ ] `tutorials/charter-governed-workflow.md` can be followed from a fresh temp repo to synthesis completion without error (or all external-service steps are explicitly labeled)
- [ ] No source-repo pollution from any smoke command

## Release Handoff Template (for Publish phase)

The implementer must produce a file at `kitty-specs/charter-end-user-docs-828-01KQCSYD/release-handoff.md` listing:
- Pages added (with paths)
- Pages updated (with paths and nature of change)
- Command snippets validated (command + outcome)
- Docs tests run (test file + pass/fail)
- Known limitations accepted (with issue links)
- Follow-up docs issues (if any)
