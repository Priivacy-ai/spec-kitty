---
work_package_id: WP01
title: Research closeout and acceptance proof
dependencies: []
requirement_refs: []
tracker_refs: []
planning_base_branch: research/docling-graph-kitty-specs
merge_target_branch: research/docling-graph-kitty-specs
branch_strategy: The compatibility closeout is recorded on the research mission branch and must return to that branch.
base_branch: research/docling-graph-kitty-specs
base_commit: 21bcce5a70b72e385fad77954a9f45d7806b7835
created_at: '2026-08-18T11:35:41Z'
subtasks:
- T001
- T002
- T003
- T004
phase: Phase 6 - Closeout
assignee: ''
agent: codex
shell_pid: ''
history:
- at: '2026-08-18T11:35:41Z'
  actor: codex
  action: Compatibility closeout prompt created after v2 research runtime reached done.
agent_profile: researcher-robbie
authoritative_surface: docs/research/docling-graph-kitty-specs/publication-manifest.json
execution_mode: documentation
model: gpt-5
owned_files:
- kitty-specs/docling-graph-kitty-specs-01M0A0FG/tasks.md
- kitty-specs/docling-graph-kitty-specs-01M0A0FG/tasks/WP01-research-closeout-acceptance.md
- docs/research/docling-graph-kitty-specs-01M0A0FG/research/README.md
- docs/research/docling-graph-kitty-specs-01M0A0FG/data/README.md
- docs/research/docling-graph-kitty-specs-01M0A0FG/findings/README.md
- docs/research/docling-graph-kitty-specs-01M0A0FG/reports/README.md
role: researcher
tags:
- acceptance-compatibility
task_type: research
---

# Work Package Prompt: WP01 — Research closeout and acceptance proof

## Objective

Make the completed v2 research mission legible to the legacy acceptance reader
without changing the research report, evidence, option dispositions, or
canonical publication authority.

## Definition of done

- The v2 research runtime reports `done`.
- The original 40-artifact research seal remains historically verifiable at
  `48fd33167585c2757d7642297b663e074ed7c07e`; a compatibility-aware successor
  seal is issued after this projection and its verifier are reviewed.
- Legacy Deep Research directories contain pointers only.
- Spec Kitty acceptance succeeds without `--lenient` or `--allow-fail`.

## Review guidance

Reject any repair that duplicates the long-form report, reclassifies unknown
evidence, bypasses a guard, or makes a compatibility path canonical.

## Approved mission-type compatibility exception

`spec-kitty agent mission finalize-tasks --validate-only` rejected this
research WP because its parser recognizes only `FR|NFR|C` references, while the
built-in research spec defines `DR|AR|QR`. Adding a fake software-development
requirement would alter sealed research. This is the same mission-type root
cause tracked in [#3546](https://github.com/Priivacy-ai/spec-kitty/issues/3546).

The recovery therefore used the supported
`migrate backfill-runtime-state --mission ...` path, which verified and flipped
the state successfully. Subsequent transitions are canonical, `force:false`,
and adversarially reviewed. `requirement_refs` is deliberately empty rather
than falsely claiming runtime mapping; DR-004, AR-002, QR-001, and QR-002 remain
human research traceability only.

## Activity log

- 2026-08-18T11:35:41Z — codex — closeout WP created for acceptance-contract recovery after the v2 runtime reached `done`.
- 2026-08-18T11:39:00Z — codex — v0 path pointers created, publication gate reverified, and canonical WP state seeded through sanctioned runtime backfill.
