---
work_package_id: WP02
title: Pure-Python retrospective generator + record schema
dependencies:
- WP01
requirement_refs:
- FR-006
- FR-007
- FR-010
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
- T010
- T011
- T012
phase: Foundation
assignee: ''
agent: claude
history:
- timestamp: '2026-05-19T13:29:59Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/retrospective/generator.py
execution_mode: code_change
model: claude-sonnet-4-6
owned_files:
- src/specify_cli/retrospective/generator.py
- src/specify_cli/retrospective/schema.py
- tests/retrospective/test_generator.py
- tests/retrospective/fixtures/missions/**
role: implementer
tags: []
---

# Work Package Prompt: WP02 — Pure-Python Retrospective Generator + Record Schema

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Internalize the avoidance boundary. Do not write code outside this WP's `owned_files`.

## Objective

Implement the deterministic pure-Python retrospective generator that reads mission artifacts and produces a schema-valid `RetrospectiveRecord`. The generator is called by the runtime at mission completion (WP04) and by the CLI surfaces (WP05). It must be byte-deterministic given the same inputs, sub-second on a representative mission, and produce records that distinguish "ran with findings" from "ran with no findings" (per FR-007) and proposals as `low` vs `structural` risk classes (per FR-010).

## Context

The generator architecture decision is recorded in [DM-01KS051316C8Z0SDEKZ2B088CS](../decisions/DM-01KS051316C8Z0SDEKZ2B088CS.md) and the ADR at [`architecture/3.x/adr/2026-05-19-1-retrospective-default-policy-architecture.md`](../../../architecture/3.x/adr/2026-05-19-1-retrospective-default-policy-architecture.md). Key constraints:

- Pure-Python module, NOT a profile invocation. Sub-second latency is the headline ask.
- Generator reads from disk but its output for a given (mission, policy, repo_root) input is byte-stable.
- The schema is in [contracts/retrospective-record.schema.json](../contracts/retrospective-record.schema.json) and [data-model.md § RetrospectiveRecord](../data-model.md#retrospectiverecord).
- Empty findings are explicit (`findings_status: ran_no_findings`) — NOT the same as a missing or failed record.
- Generation MUST NOT mutate doctrine / DRG / glossary. Proposals are data; application happens elsewhere (WP05 `synthesize` path).

## Branch Strategy

- Planning base: `main`
- Final merge target: `main`
- Execution worktree resolved via `lanes.json` after `finalize-tasks`. `spec-kitty implement WP02` enters the workspace.

## Subtasks

### T007 — Define the `RetrospectiveRecord` types

**Purpose**: Codify the on-disk record schema as Python types matching `contracts/retrospective-record.schema.json`.

**Steps**:

1. Extend `src/specify_cli/retrospective/schema.py` (preserve any existing types — additive only per NFR-007). Add types:
   - `Actor { kind: Literal["human","agent","runtime"]; id: str; display: str | None }`
   - `Provenance { kind: ProvenanceKind; command: str | None; invoked_at: str; policy_resolved_from: dict[str,str] }`
     - `ProvenanceKind = Literal["runtime_post_completion","runtime_strict_gate","explicit_create","backfill","synthesize_fabricate"]`
   - `EvidenceRef { id: str; kind: Literal["file","event_range","external"]; path: str | None; range: str | None; url: str | None }`
   - `Finding { id: str; category: FindingCategory; summary: str; details: str | None; evidence_refs: list[str] }`
     - `FindingCategory = Literal["process","tooling","spec_quality","review_loop","design","implementation","doc","other"]`
   - `Proposal { id: str; category: ProposalCategory; risk_class: Literal["low","structural"]; summary: str; details: str | None; evidence_refs: list[str]; suggested_action: str; auto_applicable: bool }`
     - `ProposalCategory = Literal["glossary","drg","doctrine","tooling","process","other"]`
   - `FindingsStatus = Literal["has_findings","ran_no_findings"]` — **persisted records may only be these two values per data-model.md invariants**
   - `RetrospectiveRecord` — full top-level shape with `schema_version: Literal[1] = 1`, mission identity fields, `created_at`, `created_by: Actor`, `provenance: Provenance`, `policy_source: dict[str,str]`, `findings_status: FindingsStatus`, `helped`, `not_helpful`, `gaps`, `proposals`, `evidence_refs`, `generator_version: str`, optional `provenance_history: list[Provenance]`.
2. Use dataclasses with `from dataclasses import dataclass, field; from typing import Literal` (no Pydantic dependency unless already in use — confirm by reading `pyproject.toml`).
3. Add a `validate_record(record: RetrospectiveRecord) -> None` function that raises `RecordValidationError` for:
   - `findings_status == "has_findings"` AND all four lists empty
   - `findings_status == "ran_no_findings"` AND any list non-empty
   - `findings_status` not in the two allowed values (catches code paths that try to persist `missing` or `failed`)
   - `provenance.kind == "synthesize_fabricate"` AND `findings_status != "ran_no_findings"` (FR-014 invariant, also enforced in WP03 writer)
   - any `Finding.evidence_refs[*]` or `Proposal.evidence_refs[*]` referring to an `id` not in top-level `evidence_refs[]`

**Files**:
- `src/specify_cli/retrospective/schema.py` (extend, ~180 lines added)

**Validation**:
- [ ] Round-trip: a record serialized to JSON via stdlib `dataclasses.asdict` matches the JSON Schema in contracts/
- [ ] `validate_record` catches each invariant violation with a clear error message

---

### T008 — Implement `generate_retrospective(mission_handle, policy, repo_root)`

**Purpose**: Pure-Python function that reads mission artifacts and produces a `RetrospectiveRecord`. Byte-deterministic given the same inputs.

**Steps**:

1. Create `src/specify_cli/retrospective/generator.py` with `GENERATOR_VERSION = "1.0"` and `generate_retrospective(mission_handle: str, policy: RetrospectivePolicy, repo_root: Path) -> RetrospectiveRecord`.
2. Resolve mission handle via the canonical resolver (`spec-kitty agent context resolve` style; use the in-process API, NOT a subprocess call). Get `feature_dir`, `mission_id`, `mission_slug`, `mission_number`, `friendly_name`, `mission_type`, `target_branch`.
3. Read in this order (each as a typed step; missing optional artifacts are tolerated and recorded as `gaps` rather than errors):
   - `feature_dir/meta.json`
   - `feature_dir/spec.md`
   - `feature_dir/plan.md`
   - `feature_dir/research.md` (optional)
   - `feature_dir/data-model.md` (optional)
   - `feature_dir/contracts/` (optional)
   - `feature_dir/quickstart.md` (optional)
   - `feature_dir/tasks.md`
   - `feature_dir/tasks/WP*.md`
   - `feature_dir/status.events.jsonl`
   - `feature_dir/mission-review-report.md` (optional)
   - Charter context via the in-process API if charter exists
4. Build `evidence_refs` list with `id`s like `e-001`, `e-002`, ... stable across runs (assign by sorted file path then by lamport for event ranges).
5. Build `helped`, `not_helpful`, `gaps`, `proposals` per T009.
6. Resolve `findings_status` per T010.
7. Set `policy_source` from the policy's source_map (passed by the caller; the generator does not re-resolve policy).
8. Set `provenance` per the caller's intent (typically `runtime_post_completion` from the runtime; `explicit_create` / `backfill` / etc. when the CLI calls).
9. Run `validate_record(record)` before returning. Validation failure is a generator bug — raise.

**Files**:
- `src/specify_cli/retrospective/generator.py` (new, ~250 lines)

**Validation**:
- [ ] Two consecutive calls with identical inputs produce byte-identical records (after JSON serialization with sort_keys)
- [ ] Wall-clock < 500ms locally for a representative mission (4 WPs, ~30 events); CI assertion < 2.0s (NFR-005)
- [ ] Missing optional artifacts produce `gaps` entries with structured `summary` like `"plan.md present but data-model.md missing"`, NOT exceptions

---

### T009 — Findings classification from evidence

**Purpose**: Derive `helped`, `not_helpful`, `gaps`, `proposals` from mission artifacts.

**Steps**:

1. **Heuristic classification rules** (start lean; refine via fixture missions):

   | Source | Goes into |
   |---|---|
   | WPs completed without rejection cycles | `helped` (process/implementation category) |
   | WPs with ≥ 1 rejection cycle (review → planned) | `not_helpful` (review_loop category) with evidence_ref pointing at the event range |
   | Open `[NEEDS CLARIFICATION:` markers in spec.md | `gaps` (spec_quality category) |
   | FRs without `requirement_refs` mapping (FR not landed in any WP) | `gaps` (spec_quality category) |
   | Charter or DRG terminology drift detected | `proposals` (glossary category) — risk_class `structural` |
   | Successful tactic/procedure adoption visible in artifacts | `proposals` (process category) — risk_class `low` if `flag_not_helpful` shape, else `structural` |
   | Documented assumptions in spec.md Assumptions section | `gaps` (spec_quality) IF the assumption proved wrong (look for related rejection cycles), else not surfaced |

2. Each `Finding` and `Proposal` MUST carry at least one `evidence_refs` entry. If you cannot point to evidence, do not generate the finding.

3. Stable ordering: sort each list by `category` (alphabetical) then `summary` (alphabetical). Stable across runs.

4. **Quality bar** (R-4 in spec.md): avoid generating low-signal noise. If the only "helped" entry would be "Mission completed successfully", omit it — that's not a finding, it's a tautology.

**Files**:
- `src/specify_cli/retrospective/generator.py` (extend, ~120 lines)

**Validation**:
- [ ] On a mission with zero rejection cycles, zero open clarifications, and no terminology drift: generator returns `findings_status = ran_no_findings` (NOT a "Mission completed successfully" tautology)
- [ ] On a mission with 2 rejection cycles, 1 open clarification, and 1 successful tactic adoption: each appears with an evidence_ref

---

### T010 — `findings_status` resolution per FR-007

**Purpose**: Persisted records distinguish `has_findings` from `ran_no_findings`. Never `missing` or `failed` in a persisted record (those are event-payload-only states).

**Steps**:

1. After T009 populates the four lists, compute:
   ```python
   if any([record.helped, record.not_helpful, record.gaps, record.proposals]):
       record.findings_status = "has_findings"
   else:
       record.findings_status = "ran_no_findings"
   ```
2. Document in a code comment that `missing` and `failed` are NOT valid persisted-record states (per data-model.md invariants). The Python `Literal` type from T007 already enforces this at the type level.

**Files**:
- `src/specify_cli/retrospective/generator.py` (extend, ~20 lines)

**Validation**:
- [ ] Empty findings → `ran_no_findings`; non-empty → `has_findings`
- [ ] No code path can produce `missing` or `failed` in a `RetrospectiveRecord` (mypy strict catches this; if mypy is not strict for this file, add `# type: assert never` patterns)

---

### T011 — Proposal `risk_class` classification

**Purpose**: Classify each proposal as `low` or `structural` so WP04/WP05 can enforce FR-010 (no auto-apply of structural changes).

**Steps**:

1. Today's only `low` class is `flag_not_helpful` (per [research.md R-7](../research.md#r-7--agent-retrospect-synthesize-fabrication-fallback-fr-14)). Implement this as an allowlist:
   ```python
   LOW_RISK_PROPOSAL_KINDS = frozenset({"flag_not_helpful"})
   ```
2. Every proposal's `risk_class` is derived from its `suggested_action` kind (e.g. a structured marker like `"flag_not_helpful: <term>"` in `suggested_action` → `low`; everything else → `structural`).
3. `auto_applicable` is `True` only when `risk_class == "low"` AND policy has `apply_low_risk_changes=True`. (Policy check happens at apply time, not authoring time; for now `auto_applicable` reflects only the risk class.)

**Files**:
- `src/specify_cli/retrospective/generator.py` (extend, ~30 lines)

**Validation**:
- [ ] A `flag_not_helpful` proposal has `risk_class == "low"`
- [ ] A glossary-rename proposal has `risk_class == "structural"`
- [ ] No proposal can have `risk_class == "structural"` AND `auto_applicable == True`

---

### T012 — Unit tests + 3 fixture missions

**Purpose**: Lock generator behavior against three real-shape mission fixtures.

**Steps**:

1. Create three fixture missions under `tests/retrospective/fixtures/missions/`:
   - `simple-clean/` — minimal artifacts, zero rejection cycles, no open clarifications. Expected: `ran_no_findings`.
   - `mid-with-rejections/` — typical 4-WP mission with 2 rejection cycles and 1 successful tactic adoption. Expected: 1 `not_helpful`, 1 `proposals` entry.
   - `large-with-gaps/` — 6-WP mission with rejections, open `[NEEDS CLARIFICATION:` markers, and FRs that lack WP mappings. Expected: rich findings across all four lists.
   Each fixture is a self-contained directory with `meta.json`, `spec.md`, `plan.md`, `tasks.md`, `tasks/WP*.md`, `status.events.jsonl`. Keep them small (under 50 lines each) but realistic.
2. Create `tests/retrospective/test_generator.py` with:
   - `TestGeneratorDeterminism` — assert two consecutive calls produce byte-identical records
   - `TestGeneratorPerformance` — assert wall-clock < 2.0s for the largest fixture
   - `TestFindingsClassification` — per-fixture expectations
   - `TestFindingsStatus` — `has_findings` vs `ran_no_findings`
   - `TestRiskClass` — proposal classification
3. Snapshot the largest fixture's generated record at `tests/retrospective/fixtures/expected/large-with-gaps.expected.yaml` for regression detection. Use `pytest-snapshot` if already in deps, else manual JSON compare with sort_keys.

**Files**:
- `tests/retrospective/test_generator.py` (new, ~280 lines)
- `tests/retrospective/fixtures/missions/simple-clean/` (new fixture, ~6 files)
- `tests/retrospective/fixtures/missions/mid-with-rejections/` (new fixture, ~6 files)
- `tests/retrospective/fixtures/missions/large-with-gaps/` (new fixture, ~8 files)
- `tests/retrospective/fixtures/expected/large-with-gaps.expected.yaml` (snapshot, ~80 lines)

**Validation**:
- [ ] `uv run pytest tests/retrospective/test_generator.py -q` exits 0
- [ ] Coverage on `src/specify_cli/retrospective/generator.py` ≥ 90%
- [ ] Snapshot match for the large fixture

---

## Definition of Done

- [ ] All 6 subtasks complete
- [ ] `uv run pytest tests/retrospective/test_generator.py tests/retrospective/test_policy.py -q` exits 0 (WP01 tests stay green)
- [ ] Coverage on `src/specify_cli/retrospective/generator.py` ≥ 90%
- [ ] `uv run ruff check src/specify_cli/retrospective/ tests/retrospective/` exits 0
- [ ] Wall-clock under 2.0s on the largest fixture (NFR-005)
- [ ] Public exports added to `src/specify_cli/retrospective/__init__.py`: `RetrospectiveRecord`, `generate_retrospective`, `GENERATOR_VERSION`
- [ ] No edits outside `owned_files`

## Risks & Reviewer Guidance

- **R-4 (generator quality)**: SC-004 sanity-checks the generator against three real completed missions in `kitty-specs/` (e.g. `068-post-merge-reliability-and-release-hardening`). This check happens at mission-review time, not in this WP, but the reviewer should manually invoke `python -c "from specify_cli.retrospective import generate_retrospective; ..."` on one real mission and inspect the output for noise vs signal.
- **R-1 (scope creep into application)**: do NOT mutate doctrine/DRG/glossary in this WP. Proposals are data only.
- **Reviewer**: verify byte-determinism with two consecutive runs; verify the `ran_no_findings` path on the clean fixture; spot-check at least one real mission for output quality.

## Next

After this WP merges, WP03 (Writer/Events/Reducer) can consume generated records.

Implementation command:

```bash
spec-kitty agent action implement WP02 --agent claude
```
