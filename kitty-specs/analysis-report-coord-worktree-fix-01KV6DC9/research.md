# Research: Analysis Report Coord-Worktree Fix & Recovery UX

**Source**: Debugger Debbie five-paradigm investigation of GitHub issue #1989.  
**Date**: 2026-06-15

No external research required. All findings derived from direct code inspection
of the three affected modules. Decisions below are grounded in the Falsifier
and Five-Whys outputs from the investigation.

---

## Decision 1: Write-Path Override Strategy

**Decision**: After `_find_feature_directory()` resolves the mission handle
(coord-aware), derive the write destination by calling the **topology-blind**
`primary_feature_dir_for_mission(repo_root, resolved_feature_dir.name)`
and pass it to `write_analysis_report()`. Do not change `_find_feature_directory()`
itself.

**Critical correction (from /spec-kitty.analyze finding A1)**: The originally-drafted
approach used `candidate_feature_dir_for_mission`, but that primitive is **topology-aware**
— it routes through `resolve_mission_read_path`, which returns the coordination worktree
whenever one exists. Using it would reproduce the very bug under repair. The correct
primitive is `primary_feature_dir_for_mission`, which is "deliberately topology-blind" and
always returns the primary-checkout mission dir. It is already the sanctioned anchor used
elsewhere in `mission.py` (lines ~811 and ~2754).

**Rationale**: `_find_feature_directory()` is used for two purposes inside
`record_analysis()`: (a) resolving the placement ref for the dirty-tree
preflight (`_resolve_record_analysis_placement_ref`) and (b) providing the
mission slug for the write. Purpose (a) legitimately needs the coord-aware
path. Changing the resolver would fix (b) but risk breaking (a). Overriding
only the downstream `feature_dir` argument to `write_analysis_report()` is the
minimal change that preserves both purposes.

**Alternatives considered**:
- Add a `prefer_main_checkout: bool` parameter to `_find_feature_directory()` — rejected because it conflates read-path resolution (which should be coord-aware) with write-destination selection (which should always be main-checkout). Mixing these concerns in the resolver violates DIRECTIVE_001.
- Call `resolve_mission_read_path()` a second time with a `prefer_primary=True` flag — rejected because no such flag exists and adding it widens the resolver's scope beyond this fix's boundary.
- Use `get_main_repo_root(repo_root) / "kitty-specs" / feature_dir.name` directly — rejected as fragile; `primary_feature_dir_for_mission` encapsulates the correct, topology-blind path construction and is already the sanctioned primary-anchor primitive in `mission.py`.
- Use `candidate_feature_dir_for_mission` (the originally-drafted choice) — rejected because it is topology-aware and returns the coord worktree, reproducing the bug (see Critical correction above).

---

## Decision 2: New Reason-Code Placement

**Decision**: Add `ANALYSIS_REPORT_REASON_CARRIER_FORMAT = "carrier_format_not_wrapped"` as a module-level constant in `analysis_report.py`, alongside the existing implicit reason strings. Detect the carrier case in `check_analysis_report_current()` by checking `frontmatter.get("schema") == FINDINGS_SCHEMA_V1` immediately after a successful frontmatter parse and before the `artifact_type` equality check.

**Rationale**: The outer-wrapper format uses `artifact_type` as its identity
key; the carrier format uses `schema`. These two keys are mutually exclusive in
practice. Checking `schema == FINDINGS_SCHEMA_V1` before the `artifact_type`
check gives a reliable, non-overlapping signal. Using a named constant (rather
than an inline string) satisfies C-004 and Sonar S1192.

**Alternatives considered**:
- Check for carrier format in `_require_current_analysis_report()` by reading the file a second time — rejected because it duplicates the frontmatter parse already performed in `check_analysis_report_current()` and adds I/O without benefit.
- Return a typed `Reason` enum instead of a string — rejected as over-engineering; the existing pattern uses plain strings, and adding an enum introduces a new type boundary that all callers must update. The named string constant achieves the same stability guarantee.

---

## Decision 3: Error Message Format

**Decision**: For the carrier-format case, emit:
```
Error: analysis-report.md contains an analysis-findings/v1 carrier (written
       directly by an agent) but the implement gate requires the persisted
       outer-wrapper format (artifact_type: spec-kitty.analysis-report).
  Recovery: spec-kitty agent mission record-analysis \
            --mission <slug> --input-file <path-to-analysis-report.md>
```

For the missing case, emit:
```
  Missing: <path>
  Run: /spec-kitty.analyze to produce the report, then:
       spec-kitty agent mission record-analysis --mission <slug> --input-file -
```

**Rationale**: The recovery command for the carrier-format case can use the
`--input-file` flag to point at the existing carrier-format file; `record-analysis`
already reads `analysis-findings/v1` carrier frontmatter and wraps it.  The
`analysis_freshness.path` is available at the call site, so the exact file path
can be interpolated. The `mission_slug` is the third parameter of
`_require_current_analysis_report()` and is already available.

**Alternatives considered**:
- Auto-convert the carrier file in place without agent action — rejected per C-001 (auto-conversion hides the root cause and creates format-drift risk; recovery must be explicit and agent-initiated).
- Emit a separate `spec-kitty doctor` command — rejected; `doctor` is for environment health, not artifact recovery. The recovery action is a normal `record-analysis` invocation.

---

## Decision 4: Skill Template Placement

**Decision**: Append a caution block immediately after the existing step 7
`record-analysis` command examples in
`src/doctrine/missions/mission-steps/software-dev/analyze/prompt.md`.

**Rationale**: The existing step 7 already documents `record-analysis` as the
persistence step and shows the command. Adding a caution note in the same step
(rather than a new step) keeps the persistence guidance co-located. Agents
scanning the file will encounter the caution immediately after reading the
command.

**Alternatives considered**:
- Add a separate "Troubleshooting" section — rejected; the caution belongs at the point of action, not in a separate section an agent might not read.
- Update the carrier rules section (step 6) — rejected; the carrier rules concern the format the agent emits, not the persistence step. The distinction between carrier (agent output) and outer-wrapper (persisted artifact) is precisely what needs to be made explicit at step 7.
