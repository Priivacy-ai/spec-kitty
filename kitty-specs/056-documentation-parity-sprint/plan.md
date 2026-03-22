# Implementation Plan: Documentation Parity Sprint

**Branch**: `fix/skill-audit-and-expansion` | **Date**: 2026-03-22 | **Spec**: [spec.md](spec.md)

---

## Technical Context

- **Output**: Markdown files (.md) and DocFX configuration (.json, .yml)
- **Build system**: DocFX, built by GitHub Actions, deployed to docs.spec-kitty.ai
- **No code changes**: Pure documentation — no Python, no tests, no migrations
- **Source material**: 8 distributed skills in `src/doctrine/skills/`
- **Target**: `docs/` directory following existing Divio structure

### Key Decision: DocFX Build Configuration

The critical fix is updating `docs/docfx.json` to include the unversioned Divio
directories. Currently only `1x/` and `2x/` are built. Adding `tutorials/`,
`how-to/`, `reference/`, `explanation/` to the build config makes 56 existing
docs visible on the site.

### Key Decision: Skill Distillation Strategy

Each skill is distilled by:
1. Reading the SKILL.md and its references
2. Extracting user-facing content (CLI commands, workflows, concepts)
3. Removing internal architecture details (middleware pipelines, source file
   references, dataclass schemas, subprocess patterns)
4. Writing in end-user voice with copy-pasteable command examples

---

## Constitution Check

- **TEST_FIRST directive**: Not applicable — this is a documentation mission
  with no code changes
- **Tools**: git (commits), spec-kitty (workflow) — no Python/pytest/mypy needed
- **No conflicts**: Documentation-only work does not trigger governance gates

---

## Work Package Strategy

### Phase 1: Build Infrastructure (1 WP)

Fix the DocFX build so all existing docs become visible on the site. This
unblocks everything else — there's no point writing new guides if they won't
be published.

**WP01**: Update `docfx.json` to include all 4 Divio categories in the build.
Update `docs/toc.yml` and `docs/index.md` to link to the categories. Fix the
missing `how-to/use-operation-history.md` file reference.

### Phase 2: Skill Distillation — How-To Guides (4 WPs)

Create new how-to guides from skills that teach users to accomplish specific
tasks. These are the highest-value additions because they fill real gaps.

**WP02**: Distill glossary-context skill → `how-to/manage-glossary.md`
- What the glossary is, the 4 scopes, CLI commands (list, conflicts, resolve)
- How to add terms, resolve conflicts, check strictness
- Omit: middleware pipeline, extraction methods, checkpoint/resume internals

**WP03**: Distill constitution-doctrine skill → `how-to/setup-governance.md`
- Interview workflow, generation, sync, context loading
- governance.yaml and directives.yaml explained at user level
- Omit: extraction regex patterns, parser internals, compiler details

**WP04**: Distill setup-doctor skill → `how-to/diagnose-installation.md`
- Running verify-setup, checking agent config, common failure patterns
- Recovery steps for each failure type
- Omit: agent-path-matrix internals, skill root resolution details

**WP05**: Distill runtime-review skill → update existing `how-to/review-work-package.md`
- Add discovery step (find reviewable WPs), --feature flag guidance
- Add governance context loading, empty-lane handling
- Preserve existing content, extend with skill insights

### Phase 3: Skill Distillation — Explanations (3 WPs)

Expand existing explanation docs with knowledge from skills that help users
understand concepts.

**WP06**: Distill mission-system skill → update existing `explanation/mission-system.md`
- 4 built-in missions with step sequences and guards
- Mission → Feature → WP → Workspace hierarchy
- Template resolution chain (user-facing: override > global > default)
- Omit: v0/v1 schema internals, MissionConfig dataclass

**WP07**: Distill git-workflow skill → new `explanation/git-workflow.md`
- What spec-kitty does automatically vs what agents/users do
- Worktree lifecycle, auto-commit behavior, merge execution
- Omit: safe_commit() stash pattern, subprocess call details

**WP08**: Distill runtime-next skill → update existing `explanation/runtime-loop.md` or new file
- What `spec-kitty next` does and when to use it
- Decision kinds (step, blocked, terminal, decision_required)
- The agent loop pattern at a conceptual level
- Known issues (#335, #336) as user-facing notes
- Omit: runtime_bridge.py internals, DAG planner code

### Phase 4: Reference Update (1 WP)

**WP09**: Distill orchestrator-api skill → update existing `reference/orchestrator-api.md`
- All 9 commands with flags and JSON output examples
- Policy metadata fields explained
- Error code catalog
- Omit: implementation details, envelope.py internals

### Phase 5: Content Expansion (1 WP)

**WP10**: Expand thin 2x/ versioned docs
- `2x/doctrine-and-constitution.md` (currently 60 lines) — expand with
  constitution workflow summary and link to new how-to
- `2x/glossary-system.md` (currently 37 lines) — expand with glossary
  concepts and link to new how-to
- `2x/runtime-and-missions.md` (currently 49 lines) — expand with mission
  overview and link to new explanation
- Update `2x/toc.yml` and cross-references

---

## Dependency Graph

```
WP01 (DocFX build fix)
  ├── WP02 (glossary how-to)
  ├── WP03 (governance how-to)
  ├── WP04 (diagnostics how-to)
  ├── WP05 (review how-to update)
  ├── WP06 (mission explanation update)
  ├── WP07 (git workflow explanation)
  ├── WP08 (runtime loop explanation)
  ├── WP09 (orchestrator-api reference update)
  └── WP10 (2x/ content expansion)
        └── depends on WP02, WP03, WP06 (links to new guides)
```

WP01 is the only prerequisite. WP02-WP09 are independent and parallelizable.
WP10 depends on WP02, WP03, and WP06 because it links to the guides they create.

---

## Artifacts Produced

| Artifact | Description |
|---|---|
| `docs/docfx.json` | Updated to include all Divio categories |
| `docs/index.md` | Updated homepage with category links |
| `docs/toc.yml` | Updated top-level navigation |
| `docs/how-to/manage-glossary.md` | New: glossary user guide |
| `docs/how-to/setup-governance.md` | New: constitution/governance guide |
| `docs/how-to/diagnose-installation.md` | New: setup-doctor user guide |
| `docs/how-to/use-operation-history.md` | New: missing file fix |
| `docs/how-to/review-work-package.md` | Updated: expanded with skill content |
| `docs/explanation/mission-system.md` | Updated: expanded with skill content |
| `docs/explanation/git-workflow.md` | New: git operation boundary guide |
| `docs/explanation/runtime-loop.md` | New: runtime-next user guide |
| `docs/reference/orchestrator-api.md` | Updated: expanded with skill content |
| `docs/2x/doctrine-and-constitution.md` | Updated: expanded |
| `docs/2x/glossary-system.md` | Updated: expanded |
| `docs/2x/runtime-and-missions.md` | Updated: expanded |
| Various `toc.yml` files | Updated navigation entries |

---

## Risks

1. **DocFX compatibility**: New files must follow DocFX markdown dialect.
   Mitigation: test build locally before merging.
2. **Stale content**: Existing docs may reference outdated commands.
   Mitigation: verify all CLI commands against `--help` during WP implementation.
3. **Scope creep**: Temptation to rewrite existing complete docs.
   Mitigation: only gap-fill and extend, don't rewrite what works.
