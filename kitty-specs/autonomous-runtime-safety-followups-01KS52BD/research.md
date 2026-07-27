# Research: Autonomous Runtime Safety Follow-ups

## Sources Consulted

- GitHub issues #1255, #1256, #1235, #1257, #1236, and #1258 via `gh issue view`.
- PR #1251 metadata via `gh pr view`.
- PR #1251 artifacts fetched as local ref `pr-1251`:
  - `kitty-specs/spec-kitty-3-2-docs-01KS4KSZ/tasks/WP01-version-taxonomy-and-occurrence-map.md`
  - `kitty-specs/spec-kitty-3-2-docs-01KS4KSZ/tasks.md`
  - `kitty-specs/spec-kitty-3-2-docs-01KS4KSZ/lanes.json`
- Local source search with `rg` across `src/specify_cli` and tests.

Retrieval note: `.kittify/missions/01KS4KSZ67PMNRJ057BGT0Z8AW/retrospective.yaml`
was not present in the fetched `pr-1251` ref.

## Findings

### #1255 Retrospective Schema

The issue reports that `retrospect create` writes top-level fields rejected by
`agent retrospect synthesize`, including mission identity, target branch,
provenance, evidence, and generator metadata. Existing synthesize tests are in
`tests/cli/test_agent_retrospect_synthesize.py`; broader retrospect command
tests are in `tests/cli/commands/test_retrospect.py`. Source search points to
`src/specify_cli/retrospective/` and `src/specify_cli/cli/commands/agent_retrospect.py`.

Decision: plan WP01 as a schema compatibility fix with tests for default dry-run
and `--apply`.

### #1256 Decision Closure

Source search found decision states and verifier logic in:

- `src/specify_cli/decisions/models.py`
- `src/specify_cli/decisions/service.py`
- `src/specify_cli/decisions/verify.py`
- `src/specify_cli/cli/commands/decision.py`
- `src/specify_cli/acceptance/__init__.py`

The verifier explicitly recognizes `DEFERRED_WITHOUT_MARKER`,
`MARKER_WITHOUT_DECISION`, and `STALE_MARKER`. The fix must make a closed
deferred decision no longer participate in the deferred-without-marker rule.

Decision: prefer `deferred -> resolved` rather than a new public flow unless
implementation reveals a stronger state-machine reason for `close-with-default`.

### #1235 Owned Files Contract Split

PR #1251 WP01 frontmatter declared
`kitty-specs/spec-kitty-3-2-docs-01KS4KSZ/occurrence_map.yaml` in `owned_files`.
The issue states `finalize-tasks` accepted it but lane handoff later rejected
`kitty-specs/` changes. Source search points to:

- `src/specify_cli/cli/commands/agent/mission.py`
- `src/specify_cli/lanes/compute.py`
- task/finalization tests under `tests/tasks/` and `tests/agent/`
- workspace context tests already covering some `kitty-specs/` ownership cases

Decision: catch the mismatch at finalization with a structured error and add an
architectural regression test.

### #1257 Bulk-edit Planning False-positive

Bulk-edit inference and gates live in:

- `src/specify_cli/bulk_edit/inference.py`
- `src/specify_cli/bulk_edit/gate.py`
- `src/specify_cli/bulk_edit/occurrence_map.py`
- `src/specify_cli/cli/commands/implement.py`
- `src/specify_cli/cli/commands/agent/workflow.py`

The implement command currently warns when spec text scores as bulk-edit-like
and `--acknowledge-not-bulk-edit` is absent. The planning-artifact case should
be identified from the claimed WP's `owned_files`.

Decision: add a WP-aware exception for occurrence-map/planning-artifact WPs while
preserving active rewrite gates.

### #1236 Lane Collapse

Lane computation lives in `src/specify_cli/lanes/compute.py`; manifest models
live in `src/specify_cli/lanes/models.py`. PR #1251 `tasks.md` planned six
lanes, while `lanes.json` collapsed all 14 WPs into `lane-a` with 13 dependency
merge events.

Decision: refine collapse to consider ownership overlap and dependency ordering.
The fan-in WP should depend on upstream lanes rather than forcing upstreams into
one lane.

### #1258 Focused PR Docs

Docs search found likely official doc targets under `docs/how-to/`, including
`accept-and-merge.md`, `merge-feature.md`, `parallel-development.md`, and
`keep-main-clean.md`. If no autonomous-run page exists, create
`docs/how-to/run-an-autonomous-mission.md` and wire it into the nearest TOC if
required by existing docs conventions.

Decision: docs WP must cite `TARGET_BRANCH_NOT_SYNCHRONIZED` and include both
the runtime-suggested focused branch path and the direct mission-branch PR path
used by PR #1251.
