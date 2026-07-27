# Spec: Intake Auto-Detect from Harness Plan Artifacts

**Mission**: intake-auto-detect-01KPNGCX  
**Issue**: [Priivacy-ai/spec-kitty#703](https://github.com/Priivacy-ai/spec-kitty/issues/703)  
**Parent**: [#700](https://github.com/Priivacy-ai/spec-kitty/issues/700) — `spec-kitty intake` brief-intake mode  
**Status**: Draft

---

## Overview

Users arrive at `spec-kitty intake` with plan documents already written by coding harnesses (Claude Code, Cursor, Codex, etc.). Today they must know the path and pass it explicitly. This mission adds `--auto`: a zero-friction variant that scans known harness plan-artifact locations, finds the document, and ingests it without the user needing to know where the harness saved it.

The mission is two parts, sequentially dependent:

1. **Research deliverable** — a canonical reference document (`docs/reference/agent-plan-artifacts.md`) mapping all 13 supported harnesses to their plan-mode artifact locations, confidence levels, and sources. This becomes the authoritative input for Part 2.
2. **Implementation** — `--auto` flag on `spec-kitty intake`, backed by a new `intake_sources.py` module populated only from verified research entries.

---

## Actors

| Actor | Role |
|-------|------|
| Developer | Runs `spec-kitty intake --auto` to ingest a harness-generated plan without specifying a path |
| Coding harness | Produces a plan-mode artifact (e.g., PLAN.md, .cursor/plan.md) at a known location |
| Spec Kitty CLI | Scans locations, ingests the brief, records provenance |

---

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | Produce `docs/reference/agent-plan-artifacts.md` documenting plan-mode artifact information for all 13 spec-kitty–supported harnesses | Required |
| FR-002 | Each harness entry must document: plan mode (Yes/No/Unclear), canonical artifact path(s), filename pattern, user-configurable (Yes/No), confidence level (Verified-docs / Verified-empirical / Inferred / Unknown), and source (URL or empirical test description) | Required |
| FR-003 | Include a `source_agent` value mapping table in `agent-plan-artifacts.md` covering all 13 harnesses, showing the string to record in `brief-source.yaml` | Required |
| FR-004 | Create `src/specify_cli/intake_sources.py` with `HARNESS_PLAN_SOURCES`: a priority-ordered list of `(harness_key, source_agent_value, [candidate_paths])` tuples | Required |
| FR-005 | Only harnesses with Verified-docs or Verified-empirical confidence appear as active entries in `HARNESS_PLAN_SOURCES`; Inferred/Unknown entries appear as commented-out TODO blocks | Required |
| FR-006 | Add `--auto` flag to `spec-kitty intake` command in `src/specify_cli/cli/commands/intake.py` | Required |
| FR-007 | `--auto` scans `HARNESS_PLAN_SOURCES` in declaration order (most harness-specific paths before generic fallbacks); skips paths that do not exist on disk without error | Required |
| FR-008 | When exactly one plan file is found: print `BRIEF DETECTED: <path> (source: <harness-name>)`, write `.kittify/mission-brief.md` and `.kittify/brief-source.yaml` with `source_agent` set, exit 0 | Required |
| FR-009 | When multiple plan files are found: print a numbered candidate list with path and detected harness for each; if stdin is a TTY, prompt user to select by number; if stdin is not a TTY (piped/non-interactive), exit 1 with the candidate list on stderr | Required |
| FR-010 | When no plan files are found: print `No plan document detected in known harness locations. Pass a path explicitly: spec-kitty intake <path>` and exit 1 | Required |
| FR-011 | `--auto` is mutually exclusive with a positional path argument; invoking both exits 1 with a usage error before any filesystem scan | Required |
| FR-012 | `brief-source.yaml` gains an optional `source_agent` field set to the harness key (e.g., `claude-code`) when `--auto` is used | Required |
| FR-013 | `write_mission_brief()` in `src/specify_cli/mission_brief.py` accepts an optional `source_agent: str | None = None` parameter; the field is omitted from the YAML output entirely when `None` (not written as `null`) | Required |
| FR-014 | `--force` flag works with `--auto`: overwrites an existing brief if a plan is found, same as it does for explicit-path intake | Required |
| FR-015 | `--show` flag behavior is unchanged by this feature | Required |
| FR-016 | Add `tests/specify_cli/test_intake_sources.py` with unit tests for the scan logic | Required |
| FR-017 | Extend `tests/specify_cli/cli/commands/test_intake.py` with tests for `--auto` (single match, multiple matches, no match, mutually-exclusive-with-path, non-TTY multi-match, --force+--auto) | Required |

---

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | `--auto` scan completes without subprocess invocations; uses filesystem `stat` calls only | Scan of all entries completes in under 200 ms on a cold filesystem | Required |
| NFR-002 | No exception is raised when a harness is not installed or its candidate paths do not exist | Zero unhandled exceptions across all scan paths | Required |
| NFR-003 | Precision over recall: silently missing a plan file is acceptable; ingesting the wrong file without user confirmation is not | Zero silent wrong-file ingestions | Required |

---

## Constraints

| ID | Constraint | Status |
|----|-----------|--------|
| C-001 | No user-configurable scan paths in this release; `HARNESS_PLAN_SOURCES` is hardcoded in `intake_sources.py` (configurability deferred as future follow-on) | Required |
| C-002 | The research deliverable (`agent-plan-artifacts.md`) must be committed before or alongside the `--auto` implementation | Required |
| C-003 | `HARNESS_PLAN_SOURCES` active entries are derived only from Verified-docs or Verified-empirical confidence entries; lower-confidence entries go in commented TODO blocks | Required |
| C-004 | `source_agent` must be omitted from `brief-source.yaml` (not written as `null`) when intake is invoked with an explicit path rather than `--auto` | Required |
| C-005 | `--show` flag behavior is unchanged | Required |
| C-006 | No changes to existing `spec-kitty intake <path>` or `spec-kitty intake -` behavior | Required |

---

## User Scenarios & Testing

### Scenario 1 — Happy path: Claude Code user, single plan file

1. User runs Claude Code plan mode; it writes `PLAN.md` at the project root.
2. User runs `spec-kitty intake --auto`.
3. CLI prints: `BRIEF DETECTED: PLAN.md (source: claude-code)`
4. `.kittify/mission-brief.md` and `.kittify/brief-source.yaml` are written.
5. `brief-source.yaml` contains `source_agent: claude-code`.
6. Exit 0.

### Scenario 2 — Multiple harnesses, user selects one (TTY)

1. User has both `PLAN.md` (Claude Code) and `.cursor/PLAN.md` (Cursor) present.
2. User runs `spec-kitty intake --auto`.
3. CLI prints:
   ```
   Found multiple plan documents. Which should I use?
   1. PLAN.md  (claude-code)
   2. .cursor/PLAN.md  (cursor)
   Enter number:
   ```
4. User enters `2`.
5. `.cursor/PLAN.md` is ingested. Exit 0.

### Scenario 3 — Multiple harnesses, non-TTY (piped)

1. Same two files present.
2. `echo "" | spec-kitty intake --auto` (stdin is a pipe, not a TTY).
3. CLI exits 1 and prints candidates on stderr.

### Scenario 4 — No plan file found

1. No known harness plan files are present.
2. User runs `spec-kitty intake --auto`.
3. CLI prints: `No plan document detected in known harness locations. Pass a path explicitly: spec-kitty intake <path>`
4. Exit 1.

### Scenario 5 — --auto with positional path (usage error)

1. User runs `spec-kitty intake PLAN.md --auto`.
2. CLI exits 1 immediately with a usage error before any scan.

### Scenario 6 — --auto with --force overwrites existing brief

1. `.kittify/mission-brief.md` already exists.
2. `PLAN.md` is present.
3. User runs `spec-kitty intake --auto --force`.
4. Brief is overwritten. Exit 0.

### Edge Cases

- Scan path is a directory, not a file → skip silently (treat as not found).
- Scan path exists but is unreadable → skip silently (treat as not found).
- All harnesses have no verified plan-mode artifact paths → `HARNESS_PLAN_SOURCES` active list is empty; `--auto` returns "no plan document detected."

---

## Success Criteria

1. A developer running `spec-kitty intake --auto` in a project where a supported harness has written a plan document completes ingestion with a single command and no path argument.
2. The research reference document answers all five specified questions for every supported harness at a documented confidence level, providing a permanent record that future maintainers can update.
3. `--auto` never ingests a file without printing which file was selected and which harness it came from.
4. The scan list remains maintainable: adding a new verified harness entry requires editing only `intake_sources.py` and `agent-plan-artifacts.md`, with no changes to CLI logic.

---

## Key Entities

| Entity | Description |
|--------|-------------|
| `HARNESS_PLAN_SOURCES` | Priority-ordered list in `intake_sources.py`; each entry is `(harness_key, source_agent_value, [candidate_paths])` |
| `agent-plan-artifacts.md` | Research reference document at `docs/reference/`; authoritative source for what goes in `HARNESS_PLAN_SOURCES` |
| `brief-source.yaml` | Provenance sidecar for the ingested brief; gains optional `source_agent` field |
| `mission-brief.md` | The ingested brief content (unchanged format) |
| `source_agent` | Harness key string (e.g., `claude-code`) set by `--auto`; absent when intake uses an explicit path |

---

## Dependencies

| Dependency | Notes |
|------------|-------|
| Mission 089 (#700) | Core `spec-kitty intake <path>` command — already shipped; this mission extends it |
| `write_mission_brief()` | Function signature extended; existing callers pass no `source_agent` and are unaffected |
| Research deliverable | `agent-plan-artifacts.md` must exist before `intake_sources.py` is populated |

---

## Assumptions

1. Research will find at least a few harnesses with Verified-docs or Verified-empirical confidence for their plan-mode artifact paths. If all 13 remain Inferred/Unknown after research, `HARNESS_PLAN_SOURCES` will have zero active entries and `--auto` will always return "no plan document detected" — which is still a valid, shippable state (the doc and the infrastructure exist; entries get added as confidence improves).
2. Harness plan-mode artifacts are plain files at predictable paths relative to the project root. There is no harness that saves plan artifacts to a location only discoverable via a running harness process or daemon.
3. Python's `Path.exists()` is sufficient to detect candidate files — no content validation is needed to determine if a file is a plan artifact.

---

## Out of Scope

- User-configurable scan paths (deferred; no `.kittify/config.yaml` changes in this release)
- Automatic download or invocation of harness plan modes
- Content validation of detected plan files (any readable file at a candidate path is accepted)
- `spec-kitty intake --ticket` or other intake variants
