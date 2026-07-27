# Agent Harness Install Audit Follow-Through

**Mission ID**: 01KT5YTQ9HXWAFSEHSFZ61K3HX
**Mission type**: software-dev
**Source**: GitHub #1649 (epic) + child issues #1644, #1645, #1646, #1647

## Purpose

Close the four agent harness-install gaps discovered during the 2026-06-03
audit: stale Codex install path documentation, pre-existing snapshot drift in
the command renderer test suite, and unverified install-surface claims for
Antigravity and Kiro. Completing this work puts the 3.3.x plugin-install
work (tracked in #1635) on a verified foundation.

## Bulk-Edit Scope

This mission includes a bulk-edit sub-task: stale Codex install paths
(`.codex/prompts/`, `.codex/skills/`, `CODEX_HOME=$(pwd)/.codex`) are removed
and replaced with the canonical path `.agents/skills/spec-kitty.<command>/SKILL.md`
across active documentation files. Per-category classification rules are
captured in `occurrence_map.yaml` (produced during plan).

---

## Functional Requirements

| ID | Description | Status |
|----|-------------|--------|
| FR-001 | Active how-to and reference documentation must not reference `.codex/prompts/` as a current Codex install target | Proposed |
| FR-002 | Active how-to and reference documentation must not reference `.codex/skills/` as a current Codex install target | Proposed |
| FR-003 | Active how-to and reference documentation must not reference `CODEX_HOME=$(pwd)/.codex` as current guidance | Proposed |
| FR-004 | Active documentation referencing Codex command skill paths must point to `.agents/skills/spec-kitty.<command>/SKILL.md` | Proposed |
| FR-005 | Codex invocation examples in active documentation must use `$spec-kitty.<command>` syntax | Proposed |
| FR-006 | Stale Codex paths may remain in documentation that explicitly labels the content as historical or legacy migration guidance | Proposed |
| FR-007 | `tests/specify_cli/skills/test_command_renderer.py` must pass with zero failures for `test_snapshot[codex-implement]` and `test_snapshot[vibe-implement]` | Proposed |
| FR-008 | Codex and Vibe command skill snapshots must use canonical WP lifecycle dependency-gate wording (`approved or done`) | Proposed |
| FR-009 | The Antigravity CLI must be accessed and its actual plugin, skills, MCP, and hook install targets verified against current upstream tooling | Proposed |
| FR-010 | `docs/reference/supported-harnesses.md` and `docs/how-to/harnesses/` must reflect verified Antigravity install-surface findings, or contain an explicit note that the surface is unverified | Proposed |
| FR-011 | Kiro documentation must be reviewed to determine whether a plugin or Powers bundle primitive exists | Proposed |
| FR-012 | `docs/reference/supported-harnesses.md` must contain an explicit Kiro classification: either a verified plugin-candidate record or a documented record stating Kiro is prompt/hook/MCP-only and out of #1635 scope for 3.3 | Proposed |

---

## Non-Functional Requirements

| ID | Description | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | The full command renderer snapshot suite must pass after snapshot refresh | Zero new test failures introduced | Proposed |
| NFR-002 | Documentation changes must preserve accurate historical migration context | No accurate historical content removed without an explicit "legacy" label | Proposed |
| NFR-003 | Research findings for Antigravity and Kiro must be based on verified upstream tooling or documentation, not assumptions | Every install-surface claim in docs cites a verified source (CLI output, upstream docs, or explicit "unverified" label) | Proposed |

---

## Constraints

| ID | Description | Status |
|----|-------------|--------|
| C-001 | No changes to `src/specify_cli/core/config.py` or any harness registry — plugin-install implementation is deferred to 3.3.x (#1635) | Proposed |
| C-002 | Antigravity and Kiro may not be added to the plugin-install scope in this mission, even if research confirms a viable package surface | Proposed |
| C-003 | This mission does not duplicate #1635 (Claude/Codex plugin installation implementation) | Proposed |
| C-004 | Stale path removal in documentation follows the `occurrence_map.yaml` classification produced during plan | Proposed |

---

## User Scenarios & Testing

### Scenario 1: Developer reads Codex how-to guide
**Given** a developer is following `docs/how-to/upgrade-project.md` or `docs/reference/upgrade-lifecycle.md`
**When** they look for Codex command skill install paths
**Then** they see `.agents/skills/spec-kitty.<command>/SKILL.md` as the current path and no reference to `.codex/prompts/` or `.codex/skills/` as active targets

### Scenario 2: Developer reads environment variables reference
**Given** a developer reads `docs/reference/environment-variables.md`
**When** they look for Codex-related environment variable guidance
**Then** `CODEX_HOME=$(pwd)/.codex` does not appear as an active instruction

### Scenario 3: Maintainer runs command renderer test suite
**Given** the test suite is run with `pytest tests/specify_cli/skills/test_command_renderer.py`
**When** the command completes
**Then** all tests pass including `test_snapshot[codex-implement]` and `test_snapshot[vibe-implement]`, with snapshots using `approved or done` wording

### Scenario 4: Developer evaluates Antigravity integration
**Given** a developer reads `docs/reference/supported-harnesses.md`
**When** they look up Antigravity's install-surface details
**Then** they find either verified install targets with source citations, or an explicit "not yet verified" record — no unverified claims presented as fact

### Scenario 5: Developer evaluates Kiro for plugin-install scope
**Given** a developer reads `docs/reference/supported-harnesses.md` for Kiro
**When** they check whether Kiro qualifies for 3.3 plugin-install work
**Then** they find an explicit classification: either a verified plugin-candidate record or a documented record stating Kiro is prompt/hook/MCP-only and excluded from #1635

---

## Success Criteria

- All `test_command_renderer.py` tests pass (zero failures)
- No active documentation file references `.codex/prompts/`, `.codex/skills/`, or `CODEX_HOME=$(pwd)/.codex` as current guidance
- `docs/reference/supported-harnesses.md` contains a verified install-surface entry or explicit unverified note for Antigravity
- `docs/reference/supported-harnesses.md` contains an explicit Kiro classification (plugin-candidate or prompt-only) for 3.3 scoping
- All four child issues (#1644, #1645, #1646, #1647) are closeable upon completion

---

## Assumptions

- The Antigravity CLI is accessible for spike verification (FR-009); if access is blocked, FR-010 will document the surface as unverified
- `approved or done` is the canonical WP dependency-gate wording, confirmed by the status model (`src/specify_cli/status/transitions.py`) and documented in `CLAUDE.md`
- Legacy/historical docs may retain stale paths as long as they carry an explicit "legacy" or "historical" label

---

## Out of Scope

- Plugin-install implementation for any agent (deferred to #1635 / 3.3.x)
- Changes to `src/specify_cli/core/config.py` or harness registry
- Antigravity or Kiro being added to the plugin-install agent list
- Any work tracked by #1635
