# Research: Mission Handoff Package & Version Matrix

**Feature**: 045-mission-handoff-package-version-matrix
**Date**: 2026-02-23
**Branch**: 2.x

---

## Decision 1: Source commit for the plan-context-bootstrap-fix wave

**Decision**: Use `21ed0738f009ca35a2927528238a48778e41f1d4` as the canonical `source_commit` for the namespace tuple.

**Rationale**: This is the merge commit for WP05 of `041-enable-plan-mission-runtime-support` on local 2.x (2026-02-22T09:47:49+01:00), which completed the plan-mission wiring fix. The fix introduced: mission-runtime.yaml schema, four command templates, test coverage for context bootstrap, and dependency parsing. This is the commit the "PLAN mission wiring fix is already merged and validated" gate refers to.

**Alternatives considered**: The last origin/2.x commit (92999a92 — SaaS feature flag gate) is not the right anchor; it postdates the fix and is not the bootstrap-fix completion point.

---

## Decision 2: Event stream source

**Decision**: Export `kitty-specs/045-.../status.events.jsonl` as the handoff event stream. If the file is empty or absent at time of handoff generation (the 045 feature has just been specified), emit a single synthetic bootstrap event recording: event_id (ULID), event_type=`handoff_package_created`, feature_slug, source_commit, generated_at.

**Rationale**: 045 is the canonical container (per user decision C). The spec does not require replaying 041's WP lifecycle — it requires replaying THIS wave's mission context. The bootstrap event anchors the package to a known point in time. If status events accumulate before the handoff WP runs, they are included verbatim.

**Alternatives considered**: Exporting 041's status.events.jsonl was ruled out (user explicitly: "do not repurpose 041"). Exporting 2.x branch-wide events is out of scope.

---

## Decision 3: Artifact manifest snapshot format

**Decision**: Export `src/specify_cli/missions/software-dev/expected-artifacts.yaml` to `handoff/artifact-manifest.json` as a plain JSON object at source_commit. No schema transformation — keys map directly from YAML to JSON.

**Rationale**: The existing `expected-artifacts.yaml` at `21ed0738` already defines the authoritative software-dev mission artifact contract. Capturing it as-is at that commit SHA is deterministic and self-documenting. Downstream consumers can diff against a later version to detect manifest drift.

**YAML → JSON conversion**: Use Python's `json.dumps(yaml.safe_load(...))` pattern. No external tools required — stdlib only.

---

## Decision 4: Artifact tree fingerprinting

**Decision**: Compute SHA-256 fingerprints using Python `hashlib.sha256`. Walk `kitty-specs/045-.../` recursively, excluding `handoff/` to prevent self-referential recursion. Each entry: `{ "path": "<relative>", "sha256": "<hex>", "size_bytes": <int>, "status": "present" | "absent" }`.

**Rationale**: SHA-256 is the standard fingerprint used elsewhere in the dossier system (`content_hash_sha256` in `MissionDossierArtifactIndexedPayload`). Consistent with the PRD §8.5 parity hash contract.

**Absent artifact detection**: Cross-reference the manifest snapshot's `required_always` + `required_by_step["specify"]` entries against the walked tree. Any manifest entry whose `path_pattern` resolves to no match is emitted as `"status": "absent"`.

---

## Decision 5: Generator script technology

**Decision**: Shell script (`generate.sh`) using Python inline invocations for SHA-256 and YAML→JSON. No new Python module or CLI subcommand.

**Rationale**: C-lite scope — minimal footprint, no new subsystem. A single shell script with embedded Python one-liners is self-contained and runnable on any POSIX system with Python 3.11+ and the spec-kitty virtual environment activated. The script embeds `SOURCE_COMMIT` and `SOURCE_BRANCH` as variables, satisfying the "walks declared source ref/scope" requirement via `git show` for the source_commit.

**Script safety**: Default mode is dry-run/report. `--write` flag required to emit files to disk. Existing handoff files are never silently overwritten.

---

## Decision 6: Version matrix note format

**Decision**: Markdown file (`version-matrix.md`) with structured H3 headings and inline code blocks for all version strings. No separate YAML schema file.

**Machine-scannable convention**: Each version pin appears as `` `key=value` `` or `` `key: value` `` in a fenced code block labeled `versions`, e.g.:
```versions
spec-kitty=2.0.0
spec-kitty-events=2.3.1
spec-kitty-runtime=v0.2.0a0
source-commit=21ed0738f009ca35a2927528238a48778e41f1d4
source-branch=2.x
```
CI tooling can `grep` this block without parsing prose.

---

## Decision 7: Test coverage for the 4 verification scenarios

**Decision**: The 4 setup-plan context scenarios are already covered by:

| Scenario | Test | File |
|---------|------|------|
| (a) Fresh session + multiple features → ambiguity error | `test_setup_plan_ambiguous_context_returns_candidates` | `tests/integration/test_planning_workflow.py:145` |
| (b) Fresh session + explicit `--feature` → success | `test_setup_plan_explicit_feature_reports_spec_path` | `tests/integration/test_planning_workflow.py:103` |
| (c) Explicit feature + missing spec.md → hard error | `test_setup_plan_missing_spec_reports_absolute_path` | `tests/integration/test_planning_workflow.py:182` |
| (d) Invalid feature slug → validation error | `test_errors_when_spec_missing` + slug tests | `tests/specify_cli/test_cli/test_agent_feature.py:650` |

**Verification note WP** must run these tests on branch 2.x at source_commit and record stdout/exit codes.

**Re-run command**:
```bash
pytest tests/integration/test_planning_workflow.py::test_setup_plan_ambiguous_context_returns_candidates \
       tests/integration/test_planning_workflow.py::test_setup_plan_explicit_feature_reports_spec_path \
       tests/integration/test_planning_workflow.py::test_setup_plan_missing_spec_reports_absolute_path \
       tests/specify_cli/test_cli/test_agent_feature.py \
       -v -k "setup_plan or planning_workflow or ambig or missing_spec or invalid_slug" \
       --tb=short 2>&1 | tee handoff/verification-run.txt
```

---

## Resolved Clarifications

All `[NEEDS CLARIFICATION]` markers from the spec are resolved by the above decisions. No outstanding clarifications remain.
