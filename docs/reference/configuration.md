# Configuration Reference

This document describes all configuration files used by Spec Kitty.

---

## meta.json (Feature Metadata)

Each feature has a `meta.json` file in its directory that stores metadata about the feature.

**Location**: `kitty-specs/<feature-slug>/meta.json`

**Fields**:

```json
{
  "feature_number": "014",
  "slug": "014-comprehensive-end-user-documentation",
  "friendly_name": "Comprehensive End-User Documentation",
  "mission": "documentation",
  "source_description": "Original feature description provided during /spec-kitty.specify",
  "created_at": "2026-01-16T12:00:00Z"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `feature_number` | string | Three-digit feature number (e.g., "014") |
| `slug` | string | Full feature slug including number |
| `friendly_name` | string | Human-readable feature name |
| `mission` | string | Mission type: `software-dev`, `research`, or `documentation` |
| `source_description` | string | Original description from `/spec-kitty.specify` |
| `created_at` | string | ISO 8601 timestamp of creation |

---

## Work Package Frontmatter

Each work package file (`tasks/WP##-*.md`) contains YAML frontmatter that tracks its status.

**Location**: `kitty-specs/<feature-slug>/tasks/WP##-*.md`

**Fields**:

```yaml
---
work_package_id: "WP01"
title: "Setup and Configuration"
lane: "planned"
dependencies: ["WP00"]
subtasks:
  - "T001"
  - "T002"
  - "T003"
phase: "Phase 1 - Foundation"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-16T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---
```

| Field | Type | Description |
|-------|------|-------------|
| `work_package_id` | string | WP identifier (e.g., "WP01") |
| `title` | string | Work package title |
| `lane` | string | Current lane: `planned`, `doing`, `for_review`, `done` |
| `dependencies` | list | WP IDs this WP depends on |
| `subtasks` | list | Task IDs belonging to this WP |
| `phase` | string | Development phase |
| `assignee` | string | Human assignee name |
| `agent` | string | AI agent type (e.g., "claude") |
| `shell_pid` | string | Process ID of implementing agent |
| `review_status` | string | Empty, `has_feedback`, or `approved` |
| `reviewed_by` | string | Reviewer name |
| `history` | list | Activity log entries |

---

## docfx.json (Documentation Build)

DocFX configuration for building the documentation site.

**Location**: `docs/docfx.json`

**Key sections**:

```json
{
  "build": {
    "content": [
      {
        "files": [
          "*.md",
          "tutorials/*.md",
          "how-to/*.md",
          "reference/*.md",
          "explanation/*.md",
          "toc.yml"
        ]
      }
    ],
    "resource": [
      {
        "files": ["assets/**"]
      }
    ],
    "dest": "_site",
    "template": ["default", "modern"],
    "globalMetadata": {
      "_appTitle": "Spec Kitty Documentation",
      "_enableSearch": true
    }
  }
}
```

| Section | Description |
|---------|-------------|
| `content.files` | Markdown files to include |
| `resource.files` | Static assets (images, CSS) |
| `dest` | Output directory (don't commit this) |
| `template` | DocFX templates to use |
| `globalMetadata` | Site-wide settings |

---

## toc.yml (Table of Contents)

Defines the documentation navigation structure.

**Location**: `docs/toc.yml`

**Format**:

```yaml
- name: Home
  href: index.md

- name: Tutorials
  items:
    - name: Getting Started
      href: tutorials/getting-started.md
    - name: Your First Feature
      href: tutorials/your-first-feature.md

- name: How-To Guides
  items:
    - name: Install & Upgrade
      href: how-to/install-spec-kitty.md
```

Each entry has:
- `name`: Display text in navigation
- `href`: Path to markdown file
- `items`: Nested navigation items (optional)

---

## constitution.md (Project Principles)

Optional file defining project-wide coding principles and standards.

**Location**: `.kittify/memory/constitution.md`

**Purpose**: When present, all slash commands reference these principles. Claude and other agents will follow these guidelines during implementation.

**Example**:

```markdown
# Project Constitution

## Code Quality Principles

1. All APIs must have rate limiting
2. All database queries must use parameterized statements
3. All user input must be validated
4. Test coverage must be at least 80%

## Architecture Principles

1. Use dependency injection for testability
2. Separate business logic from infrastructure
3. Document all public APIs
```

**Creating**: Use `/spec-kitty.constitution` to interactively create this file.

---

## Mission Configuration (Advanced)

Mission-specific templates and configuration.

**Location**: `.kittify/missions/<mission-key>/`

**Structure**:

```
.kittify/missions/
├── software-dev/
│   └── mission.yaml
├── research/
│   └── mission.yaml
└── documentation/
    └── mission.yaml
```

**mission.yaml fields**:

```yaml
key: software-dev
name: Software Development
domain: Building software features
phases:
  - research
  - design
  - implement
  - test
  - review
artifacts:
  - spec.md
  - plan.md
  - tasks.md
  - data-model.md
```

---

## Legacy Configuration

### .kittify/active-mission (Deprecated)

**Status**: Deprecated in v0.8.0+

Previously stored the project-wide active mission. Now missions are per-feature and stored in `meta.json`.

If you see this file in older projects, it will be ignored. The mission in each feature's `meta.json` takes precedence.

---

## See Also

- [File Structure](file-structure.md) — Directory layout reference
- [Environment Variables](environment-variables.md) — Runtime configuration
- [Missions](missions.md) — Mission types and their artifacts
