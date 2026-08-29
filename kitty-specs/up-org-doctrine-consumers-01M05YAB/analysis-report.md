---
schema_version: 1
artifact_type: spec-kitty.analysis-report
command: /spec-kitty.analyze
mission_slug: up-org-doctrine-consumers-01M05YAB
mission_id: 01M05YABKNFE7C69BNRVZS35X8
generated_at: '2026-08-16T19:43:31.159095+00:00'
analyzer_agent: claude
input_artifacts:
  spec.md:
    path: <repo-root>/kitty-specs/up-org-doctrine-consumers-01M05YAB/spec.md
    sha256: 8e4285b3b3b7e875ba18af5f2405d2e754f675f1d324c5a7c745c813c8ec8054
  plan.md:
    path: <repo-root>/kitty-specs/up-org-doctrine-consumers-01M05YAB/plan.md
    sha256: be645865ee61589e8193215841fba38b215a31cb9e2d70ea92cae6a7a7ba53e5
  tasks.md:
    path: <repo-root>/kitty-specs/up-org-doctrine-consumers-01M05YAB/tasks.md
    sha256: 6e64d410465cda282fc3ff98a9b7e85c3bbe2dac23a86dea9cd23796e4dbee9e
  charter:
    path: <repo-root>/.kittify/charter/charter.yaml
    sha256: b0cb6b6b5a27ca8376c5ef29bfa5c87eb64e6dcaa60e7d2330962341932b26c8
verdict: ready
issue_counts:
  low: 0
  high: 0
  medium: 1
  critical: 0
  info: 0
findings:
- id: F-01
  severity: medium
  category:
  summary:
---

# Cross-Artifact Consistency Analysis — up-org-doctrine-consumers-01M05YAB (issue #3516)

## Scope and method

Read spec.md, plan.md, research.md, data-model.md, contracts/org-tier-resolution-contract.md,
tasks.md, lanes.json, and all five WP prompt files (WP01–WP05) in the mission directory. Cross-
checked WP frontmatter (`owned_files`, `create_intent`, `dependencies`) against the actual
checkout state (file existence via direct filesystem checks, not narrative), and ran direct
searches (`wc -l`, `grep`) for sizing, subtask-id uniqueness, and hygiene rather than trusting
prose claims.

Per the task's "already established" list, the following were **not** re-litigated: the spec's
four corrections to the originating issue's framing, the six `MissionStepContractRepository(`
construction-site verdicts (D-001), the surface-over-delete decision on discarded delegation
results (D-005), the L mission-size classification, and the live 347→348 DRG node-count
measurement in this checkout.

## 1. Lockstep constraints (highest-value check) — both verified from frontmatter

**Pair A** — `specify_cli/review/gate_bindings.py` and
`specify_cli/mission_step_contracts/executor.py`:

- WP02's frontmatter `owned_files` lists both `src/specify_cli/mission_step_contracts/executor.py`
  and `src/specify_cli/review/gate_bindings.py` — confirmed inside a single work package.
- WP02's prompt body states the constraint explicitly and prominently, under a
  "MANDATORY LOCKSTEP CONSTRAINT — READ BEFORE STARTING" header, before the Objective section —
  a lane agent reading only its own prompt (not tasks.md) will see it.

**Pair B** — `specify_cli/mission_loader/command.py` and
`runtime/next/runtime_bridge_composition.py`:

- WP03's frontmatter `owned_files` lists both `src/runtime/next/runtime_bridge_composition.py`
  and `src/specify_cli/mission_loader/command.py` — confirmed inside a single work package.
- WP03's prompt body states the constraint under the same style of header, with an added note
  reconciling a line-number drift between the spec's citation (line 284) and the current on-disk
  location (line 252) — correctly resolved by "locate by name, not line number," not left as an
  unaddressed contradiction.

Both pairs pass: no split, and both prompts self-document the constraint rather than relying on
the lane agent having read tasks.md's separate "Lockstep pairs" section.

## 2. WP04 → WP05 file-collision dependency — confirmed non-functional in both prompts

Both `src/charter/activation/mission_type_profiles.py` and `tests/charter/test_mission_type_profiles.py`
appear in both WP04's and WP05's `owned_files`. WP04's prompt has a dedicated "File-collision
note (why WP05 depends on this WP)" section stating explicitly "Do not treat this as evidence
FR-008 needs anything from FR-004's governance-slot logic — it doesn't," and refusing a
hypothetical instruction to parallelize. WP05's prompt has the mirrored note ("This WP depends on
WP04 purely because both edit ... a file collision, not a functional dependency"). Both correctly
warn against "optimising" the pair into parallel execution.

## 3. Ownership, lanes, coverage

- `owned_files` are pairwise disjoint across all five WPs **except** the deliberate WP04/WP05
  overlap on `mission_type_profiles.py` / its test file, which is resolved by the WP04→WP05
  dependency edge (not a violation — the two are sequential, not concurrent).
- `create_intent` is correct in every WP: `src/charter/activation/org_expected_artifacts.py` and
  `tests/charter/test_org_expected_artifacts.py` (WP05) are the only two files anywhere in the
  mission's `create_intent` fields, and both are confirmed absent from the current checkout
  (genuinely new). Every other file referenced in every WP's `owned_files` (executor.py,
  gate_bindings.py, runtime_bridge_composition.py, mission_loader/command.py,
  mission_type_profiles.py, manifest.py, org_pack_config.py, and all listed test files) was
  confirmed to already exist on disk — correctly modified-not-created.
- Dependency graph: WP01 (no deps) → {WP02, WP03, WP04} (dep: WP01) → WP05 (dep: WP04). Acyclic.
- `lanes.json` shows exactly 4 lanes (lane-a=WP01, lane-b=WP02, lane-c=WP03, lane-d=WP04+WP05),
  with a `collapse_report` entry explicitly naming `write_scope_overlap` as the rule that merged
  WP04/WP05 into one lane, evidence citing the overlapping `mission_type_profiles.py` /
  test-file globs — matches the plan's own stated intent exactly.
- FR coverage: tasks.md's Requirement → Work-Package table maps all of FR-001–008 (including
  FR-006a) to at least one WP (FR-001/002/005→WP02, FR-003→WP01, FR-004→WP04, FR-006/006a/007→WP03,
  FR-008→WP05). FR-006a and the SC- ids are absent from the *structured* `requirement_refs`
  frontmatter field on every WP that needs them (WP02, WP03, WP05), but each of those WPs carries
  an explicit "Tooling note" in prose stating why (spec-kitty's `map-requirements` command rejects
  both `FR-NNNa` and `SC-` shapes) and asserting the requirement is still fully in scope — this
  matches the reported tooling defect (#3519) rather than being an actual coverage gap. FR-006a's
  T012 and FR-005/006/006a's shared-fixture tests (T010/T013/T014) genuinely implement and test
  the requirement despite the structural field's limitation.

## 4. Resolver-shape distinction and other spec-vs-WP fidelity checks

- The `org_dirs: list[Path]` vs `load_validated_graph`'s single `org_root: Path` distinction is
  stated explicitly, and only, in WP02 (the one WP that touches both shapes — FR-001/FR-005 use
  the list shape via WP01's helper; FR-002 resolves the single-path shape inline, per contract
  C-2, deliberately not through the shared helper). No other WP conflates the two shapes; WP01,
  WP03, WP04 each use only the list shape and say so.
- WP05's `ManifestRegistry` cache-key writeup matches the described defect precisely: process-
  global cache keyed only on `mission_type`, sole caller (`sync/namespace.py`'s
  `resolve_manifest_version`) has no `repo_root` in scope, and the WP is explicit that this is
  "real, budgeted scope for this WP... not optional cleanup," with the fix shape
  (`repo_root: Path | None = None`, cache key becomes `(mission_type, tuple(sorted org roots))`)
  matching data-model.md's own recommended shape exactly.
- Every FR's proof mechanism (T008/T010/T013/T014/T016/T018/T026/T027) is a stated
  before/after count or boolean delta (347→348 DRG nodes, `None`→contract object, `[]`→non-empty
  gates, 0→1 WARNING record, `required_always` count/content delta), never merely "no exception
  raised" or "test passes."

## 5. FR-007 deviation from data-model.md's sketch — see finding F-01

WP03 deliberately implements FR-007 as inline iteration over `result.steps` inside
`_dispatch_via_composition`, rather than the two new properties on `StepContractExecutionResult`
that data-model.md and contract C-3 both specify — done specifically to avoid touching
`executor.py`, a file owned by the concurrent WP02. The decision is sound (same externally
observable WARNING behavior; avoids an undeclared file collision) and WP03's own prompt clearly
instructs the deviation with rationale, so an implementer following WP03 will not be confused.
The finding is that data-model.md and contracts/org-tier-resolution-contract.md were not updated
to match — those two artifacts still describe an interface that will not be built. Rated medium:
non-blocking for implementation, but a real documentation inconsistency in exactly the artifact
(contracts/) whose stated purpose is to prevent needing to read another IC's source to conform.

## 6. Sizing and hygiene

- Subtask IDs: T001–T027, all 27 globally unique, contiguous, matching the WP-by-WP subtask
  totals (WP01: T001–T004, WP02: T005–T010, WP03: T011–T016, WP04: T017–T020, WP05: T021–T027 =
  4+6+6+4+7 = 27). No collisions or gaps.
- WP prompt file sizes (`wc -l`): WP01 264, WP02 303, WP03 336, WP04 221, WP05 346 lines — all
  well under the 700 ceiling.
- Hygiene sweep across the mission directory: no no host-absolute paths, no
  username string, no non-generic absolute local paths (the only absolute paths found are
  `/tmp/org-pack-quickstart/...` in quickstart.md — a generic, portable example scratch path, not
  a host-specific leak). No U+2011 (non-breaking hyphen) or other invisible/lookalike characters
  (zero-width space/joiner, non-breaking space, BOM) found anywhere under the mission directory.

## Verdict

Structural rule: any high/critical finding → `blocked`. This analysis produced one `medium`
finding and zero `high`/`critical` findings, so the computed verdict is **`ready`**, matching the
carrier's `verdict_hint`.

## What was verified independently vs. taken on report

**Verified independently** (read source, ran commands, did not take the mission's own claims at
face value): both lockstep pairs' frontmatter `owned_files` and prompt-body statements; WP04/WP05
file-collision framing in both prompts; `lanes.json`'s 4-lane structure and collapse-report
rule/evidence; `owned_files` pairwise disjointness; `create_intent` correctness against actual
on-disk file existence (via direct filesystem checks); dependency-graph acyclicity; FR-001–008
(incl. FR-006a) → WP coverage table; the resolver-shape distinction's placement (present only
where both shapes coexist); the `ManifestRegistry` cache-key defect description; subtask-ID
uniqueness and WP prompt file sizing (via `grep`/`wc -l`); hygiene sweep for host paths, usernames,
and invisible/lookalike characters (via `grep`); the FR-007 data-model.md/contract-vs-WP03
deviation (read all three artifacts directly and diffed the described interfaces); confirmation
that `unresolved_candidates` already exists pre-mission on `StepContractStepResult` and that no
`has_unresolved_delegations`/`all_unresolved_candidates` properties exist yet.

**Taken on report** (per the task's explicit "already established" list, not re-verified): the six
`MissionStepContractRepository(` construction-site verdicts, the surface-over-delete decision on
discarded delegation results, the L mission sizing, the live 347→348 DRG measurement, and the
existence of the two tooling defects now filed as #3519.
