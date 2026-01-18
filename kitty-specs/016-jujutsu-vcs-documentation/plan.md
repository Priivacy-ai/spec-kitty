# Implementation Plan: Jujutsu VCS Documentation

**Branch**: `016-jujutsu-vcs-documentation` | **Date**: 2026-01-17 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/kitty-specs/016-jujutsu-vcs-documentation/spec.md`
**Mission**: documentation

## Summary

Document the jujutsu (jj) VCS integration from feature 015, following the established Divio 4-type structure. The documentation will both integrate jj mentions throughout existing docs AND create dedicated jj-specific content. Research completed using both live CLI help output and feature 015 design documents.

## Technical Context

**Framework**: DocFX 2.76.0 (existing from feature 014)
**Hosting**: GitHub Pages via `.github/workflows/docs-pages.yml`
**Format**: Markdown with YAML frontmatter
**Navigation**: `docs/toc.yml` (DocFX table of contents)
**Source of Truth**: CLI `--help` output + feature 015 design docs
**Target Audience**: End users of spec-kitty

## Constitution Check

*No constitution file exists at `.kittify/memory/constitution.md` - proceeding without constitution constraints.*

## Project Structure

### Documentation (this feature)

```
kitty-specs/016-jujutsu-vcs-documentation/
├── spec.md              # Feature specification (complete)
├── plan.md              # This file
├── research.md          # CLI + design doc research (complete)
├── meta.json            # Feature metadata
├── checklists/
│   └── requirements.md  # Spec quality checklist (complete)
└── tasks/               # Work package prompts (created by /spec-kitty.tasks)
```

### Target Documentation Changes

```
docs/
├── index.md                              # Minor update: mention jj support
├── toc.yml                               # Add new jj-related pages
│
├── tutorials/
│   ├── getting-started.md                # UPDATE: Add jj installation recommendation
│   ├── your-first-feature.md             # UPDATE: Mention VCS abstraction
│   ├── multi-agent-workflow.md           # UPDATE: Highlight jj auto-rebase benefits
│   └── jujutsu-workflow.md               # NEW: Complete jj workflow tutorial
│
├── how-to/
│   ├── install-spec-kitty.md             # UPDATE: Add jj installation section
│   ├── implement-work-package.md         # UPDATE: jj workspace vs git worktree
│   ├── parallel-development.md           # UPDATE: Emphasize jj benefits
│   ├── handle-dependencies.md            # UPDATE: Mention sync command
│   ├── sync-workspaces.md                # NEW: How to use spec-kitty sync
│   ├── handle-conflicts-jj.md            # NEW: Non-blocking conflict handling
│   └── use-operation-history.md          # NEW: How to use spec-kitty ops
│
├── reference/
│   ├── cli-commands.md                   # UPDATE: Add sync, ops commands
│   ├── file-structure.md                 # UPDATE: Document .jj/ alongside .git/
│   └── configuration.md                  # UPDATE: Document vcs config section
│
└── explanation/
    ├── workspace-per-wp.md               # UPDATE: Add jj workspace info
    ├── git-worktrees.md                  # UPDATE: Compare with jj workspaces
    ├── jujutsu-for-multi-agent.md        # NEW: Why jj is preferred
    └── auto-rebase-and-conflicts.md      # NEW: How jj auto-rebase works
```

## Documentation Deliverables

### Files to Update (Integration)

| File | Changes |
|------|---------|
| `tutorials/getting-started.md` | Add jj installation recommendation, mention VCS detection |
| `tutorials/your-first-feature.md` | Mention that workspace may be jj or git |
| `tutorials/multi-agent-workflow.md` | Highlight jj auto-rebase for parallel work |
| `how-to/install-spec-kitty.md` | Add jj installation section with brew/cargo commands |
| `how-to/implement-work-package.md` | Explain jj workspace vs git worktree |
| `how-to/parallel-development.md` | Emphasize jj benefits, link to new jj explanation |
| `how-to/handle-dependencies.md` | Mention sync command for keeping dependent WPs updated |
| `reference/cli-commands.md` | Add sync, ops log, ops undo, ops restore commands |
| `reference/file-structure.md` | Document .jj/ directory alongside .git/ |
| `reference/configuration.md` | Document vcs section in config.yaml |
| `explanation/workspace-per-wp.md` | Add jj workspace information |
| `explanation/git-worktrees.md` | Compare with jj workspaces |

### New Files to Create (Dedicated Content)

| File | Divio Type | Description |
|------|------------|-------------|
| `tutorials/jujutsu-workflow.md` | Tutorial | Complete jj workflow from init to merge |
| `how-to/sync-workspaces.md` | How-To | Using spec-kitty sync command |
| `how-to/handle-conflicts-jj.md` | How-To | Non-blocking conflict handling with jj |
| `how-to/use-operation-history.md` | How-To | Using spec-kitty ops log/undo/restore |
| `explanation/jujutsu-for-multi-agent.md` | Explanation | Why jj is preferred for multi-agent development |
| `explanation/auto-rebase-and-conflicts.md` | Explanation | How jj auto-rebase and non-blocking conflicts work |

## Command Documentation Reference

### spec-kitty sync

```
Usage: spec-kitty sync [OPTIONS]

Options:
  --repair, -r    Attempt workspace recovery (may lose uncommitted work)
  --verbose, -v   Show detailed sync output

Backend Differences:
  git: Sync may FAIL on conflicts (must resolve before continuing)
  jj:  Sync always SUCCEEDS (conflicts stored, resolve later)
```

### spec-kitty ops

```
Usage: spec-kitty ops COMMAND [ARGS]

Commands:
  log      Show operation history
  undo     Undo last operation (jj only)
  restore  Restore to a specific operation (jj only)
```

### spec-kitty ops log

```
Usage: spec-kitty ops log [OPTIONS]

Options:
  --limit, -n INTEGER   Number of operations to show [default: 20]
  --verbose, -v         Show full operation IDs and details

Backend: jj shows operation log, git shows reflog
```

### spec-kitty ops undo

```
Usage: spec-kitty ops undo [OPERATION_ID]

Arguments:
  operation_id    Operation ID to undo (defaults to last operation)

Backend: jj only - git does not support reversible operation history
```

### spec-kitty ops restore

```
Usage: spec-kitty ops restore OPERATION_ID

Arguments:
  operation_id    Operation ID to restore to (required)

Backend: jj only
```

### spec-kitty init --vcs

```
New Option:
  --vcs TEXT    VCS to use: 'git' or 'jj'. Defaults to jj if available.
```

## Key Documentation Patterns

### Backend Comparison Tables

Use tables to clearly show differences:

| Feature | jj | git |
|---------|-----|-----|
| Auto-rebase | Yes | No |
| Non-blocking conflicts | Yes | No |
| Operation undo | Full | Limited (reflog) |
| Stable change identity | Yes (Change ID) | No |

### Callout Boxes for Critical Differences

```markdown
> **jj vs git**: With jj, `spec-kitty sync` always succeeds - conflicts are stored
> in the files and you can resolve them later. With git, sync may fail if there
> are conflicts, requiring immediate resolution.
```

### Search Term Strategy

Use both "jj" and "jujutsu" throughout documentation to ensure searchability:
- Title: "Jujutsu (jj) Workflow"
- Body: Reference as "jj" after first mention
- Keywords: Include both terms in frontmatter

## Verification Checklist

### Before Each WP Completion

- [ ] Commands match `spec-kitty <cmd> --help` output
- [ ] Backend differences clearly documented
- [ ] Cross-references to related docs added
- [ ] Both "jj" and "jujutsu" terms used for searchability

### Final Validation

- [ ] DocFX builds without errors
- [ ] All internal links resolve
- [ ] toc.yml includes all new pages
- [ ] GitHub Pages deployment succeeds

## Dependencies

- Feature 014 documentation structure (complete)
- Feature 015 jujutsu integration (complete and merged)
- DocFX 2.76.0 build system
- GitHub Pages deployment workflow

## Risks

| Risk | Mitigation |
|------|------------|
| DocFX build fails with new structure | Test build locally before committing |
| Links to new pages break | Verify all toc.yml entries match file paths |
| CLI output changes | Document against spec-kitty 0.12.0+ |
| Users confused by jj vs git | Use comparison tables and clear callouts |
