# Implementation Plan: Mission Handoff Package & Version Matrix

**Branch**: `2.x` | **Date**: 2026-02-23 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/045-mission-handoff-package-version-matrix/spec.md`

---

## Summary

Commit seven handoff artifact files to `kitty-specs/045-mission-handoff-package-version-matrix/handoff/` representing the canonical mission state for the plan-context-bootstrap-fix wave (feature 041, source commit `21ed0738f009ca35a2927528238a48778e41f1d4`) on branch `2.x`. Include a minimal shell script to regenerate the package from a clean checkout. No new Python modules, CLI subcommands, or exporter frameworks are introduced (C-lite scope).

---

## Technical Context

**Language/Version**: Python 3.11+ (SHA-256 fingerprinting, YAML→JSON conversion) + Bash
**Primary Dependencies**: spec-kitty `2.0.0`; spec-kitty-events `2.3.1`; spec-kitty-runtime `v0.2.0a0`
**Storage**: Filesystem — JSONL, JSON, Markdown files committed to `2.x`
**Testing**: pytest — `tests/integration/test_planning_workflow.py` + `tests/specify_cli/test_cli/test_agent_feature.py`
**Target Platform**: macOS / Linux (POSIX shell), Python 3.11+
**Performance Goals**: Generator script completes in < 5 seconds (no network, no compilation)
**Constraints**: No new Python modules; no CLI subcommands; generator must be idempotent; no silent overwrites
**Scale/Scope**: 7 committed files, one feature directory, one generator shell script

**Source commit anchor**:
- SHA: `21ed0738f009ca35a2927528238a48778e41f1d4`
- Description: Merge WP05 from 041-enable-plan-mission-runtime-support
- Date: 2026-02-22T09:47:49+01:00
- Significance: Final commit of the plan-context-bootstrap-fix wave on 2.x

---

## Constitution Check

*Gate: Must pass before implementation. Constitution: `.kittify/memory/constitution.md`*

| Gate | Requirement | Status |
|------|-------------|--------|
| Language | Python 3.11+ | ✅ — only stdlib + existing dependencies |
| Branch | Active development on 2.x | ✅ — target_branch = 2.x |
| Testing | 90%+ coverage for new code | ✅ — no new Python code; verification WP runs existing tests |
| Type checking | mypy --strict | ✅ — no new Python modules introduced |
| Dependencies | No `pip -e` or `rev = "main"` deps | ✅ — no dependency changes |
| No legacy compat | No 1.x backward-compat work | ✅ — 2.x-only, no 1.x references |
| spec-kitty-events | Use pinned commit/version | ✅ — events `2.3.1` unchanged |
| New commands | No unapproved CLI subcommands | ✅ — C-lite: shell script only |

**Post-design re-check**: No constitution conflicts introduced. Generator script is Bash-only; no Python modules added.

---

## Project Structure

All output files land under the existing 045 feature directory:

```
kitty-specs/045-mission-handoff-package-version-matrix/
├── spec.md              (existing)
├── plan.md              (this file)
├── research.md          (existing — Phase 0)
├── data-model.md        (existing — Phase 1)
├── quickstart.md        (Phase 1 — created below)
├── checklists/
│   └── requirements.md  (existing)
└── handoff/             ← created during implementation
    ├── namespace.json
    ├── artifact-manifest.json
    ├── artifact-tree.json
    ├── events.jsonl
    ├── version-matrix.md
    ├── verification.md
    └── generate.sh
```

No changes to `src/`, `tests/`, or any other feature directory.

---

## Phase 0: Research

*Research is complete. See [research.md](research.md) for all decisions and rationale.*

**Key resolved decisions**:

1. **Source commit**: `21ed0738f009ca35a2927528238a48778e41f1d4` — final WP05 merge for 041.
2. **Event stream**: Export `status.events.jsonl` from the 045 feature dir; if empty, emit a single synthetic bootstrap event.
3. **Manifest snapshot**: `yaml.safe_load` + `json.dumps` — stdlib only, no external conversion tools.
4. **Fingerprinting**: `hashlib.sha256` — consistent with dossier system's `content_hash_sha256` convention.
5. **Generator**: Bash script with embedded Python one-liners; dry-run by default; `--write` required.
6. **Version matrix**: Markdown + `versions` fenced code block for CI machine-scanning.
7. **Test coverage**: All 4 setup-plan scenarios are already covered in `tests/integration/test_planning_workflow.py` and `tests/specify_cli/test_cli/test_agent_feature.py`.

---

## Phase 1: Design & Contracts

*Design artifacts are complete. See [data-model.md](data-model.md) for full schemas.*

### Handoff Package Contract (summary)

Seven files committed to `handoff/`. Schemas in `data-model.md`. Highlights:

**namespace.json** — identity anchor:
```json
{
  "schema_version": "1",
  "project_scope_id": "<repo-basename>",
  "feature_slug": "045-mission-handoff-package-version-matrix",
  "source_branch": "2.x",
  "source_commit": "21ed0738f009ca35a2927528238a48778e41f1d4",
  "mission_key": "software-dev",
  "manifest_version": "1",
  "step_id": null,
  "generated_at": "<ISO 8601 UTC>"
}
```

**artifact-manifest.json** — expected artifact contract at source_commit:
- Direct JSON export of `src/specify_cli/missions/software-dev/expected-artifacts.yaml`
- Extra fields: `source_commit`, `captured_at`

**artifact-tree.json** — actual state of feature directory:
- Recursive walk of `kitty-specs/045-.../` (excluding `handoff/`)
- Per-file: `path`, `sha256`, `size_bytes`, `status: present | absent`
- Absent entries cross-referenced from manifest's `required_always` + `required_by_step["specify"]`

**events.jsonl** — event log export:
- Verbatim copy of `status.events.jsonl`; OR single bootstrap event if log is empty
- One sorted-key JSON object per line; UTF-8

**version-matrix.md** — version pins + replay:
- Machine-scannable `versions` code block (key=value per line)
- Pins: `spec-kitty=2.0.0`, `spec-kitty-events=2.3.1`, `spec-kitty-runtime=v0.2.0a0`, `source-commit=...`, `source-branch=2.x`
- At least one executable replay command with the concrete 045 feature slug
- All 6 artifact classes from the software-dev mission taxonomy listed with path patterns

**verification.md** — test evidence:
- 4-scenario coverage table with pass/fail per scenario
- Branch, commit SHA, run date, re-run command
- Must be written AFTER running pytest and observing actual output

**generate.sh** — minimal reproducibility script:
- Default: dry-run (print what would be written)
- `--write`: emit files to `handoff/` (or `--output-dir`)
- `--force`: allow overwriting existing files
- Embeds `SOURCE_COMMIT` and `SOURCE_BRANCH` as shell variables
- Steps: namespace.json → artifact-manifest.json → artifact-tree.json → events.jsonl → version-matrix.md
- Note: does NOT run tests or generate verification.md (manual step documented in script comments)

### Key Invariants

1. `namespace.json::source_commit` == `SOURCE_COMMIT` variable in `generate.sh`
2. `artifact-manifest.json::source_commit` == `namespace.json::source_commit`
3. `artifact-tree.json` MUST NOT contain entries from `handoff/`
4. `events.jsonl` MUST preserve original insertion order
5. All timestamps MUST be ISO 8601 UTC (`Z` suffix)
6. `generate.sh` MUST default to dry-run; `--write` activates file output

---

## Work Package Sketch

*(Informational. Formal WPs generated by `/spec-kitty.tasks`.)*

| WP | Title | Blocking? |
|----|-------|-----------|
| WP01 | Scaffold `handoff/` directory + commit `namespace.json` | Yes (all others depend on it) |
| WP02 | Generate and commit `artifact-manifest.json` + `artifact-tree.json` | No (parallel with WP03) |
| WP03 | Export and commit `events.jsonl` (or bootstrap event) | No (parallel with WP02) |
| WP04 | Write and commit `generate.sh` | After WP01-WP03 (must match their content) |
| WP05 | Write and commit `version-matrix.md` | After WP01 (needs namespace fields) |
| WP06 | Run tests + write and commit `verification.md` | After WP01-WP05 (evidence gate) |

All WPs commit to `2.x`. No worktrees needed for a pure documentation/artifact task — implementors may use worktrees for parallel safety per 0.11.0+ conventions.

---

## Acceptance Replay Command

The following command, when run from a clean 2.x checkout after all WPs are merged, should produce output equivalent to the committed handoff package:

```bash
bash kitty-specs/045-mission-handoff-package-version-matrix/handoff/generate.sh \
  --output-dir /tmp/045-handoff-verify \
  --write
diff -r kitty-specs/045-mission-handoff-package-version-matrix/handoff/ /tmp/045-handoff-verify/ \
  --exclude=generated_at \
  --exclude=captured_at
```

Any diff beyond timestamp fields indicates the committed package is stale and should be regenerated.
