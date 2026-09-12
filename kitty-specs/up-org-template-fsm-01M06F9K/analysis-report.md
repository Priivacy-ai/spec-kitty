---
schema_version: 1
artifact_type: spec-kitty.analysis-report
command: /spec-kitty.analyze
mission_slug: up-org-template-fsm-01M06F9K
mission_id: 01M06F9K630FKJ8NVY89QKDA3C
generated_at: '2026-08-17T00:17:04.233008+00:00'
analyzer_agent: claude-analysis-subagent
input_artifacts:
  spec.md:
    path: kitty-specs/up-org-template-fsm-01M06F9K/spec.md
    sha256: 6f8b3485a4de4139961eb91e294cf18eb3330f0a001b353c757d3d3c66094d6f
  plan.md:
    path: kitty-specs/up-org-template-fsm-01M06F9K/plan.md
    sha256: 93a40dbd20316698d94b55d00e404585aee3c1d6826e68109db3fab58817965f
  tasks.md:
    path: kitty-specs/up-org-template-fsm-01M06F9K/tasks.md
    sha256: f39299102c5567ce3b56525e597cc6c777b75393df996e27ee6c9679d489be62
  charter:
    path: .kittify/charter/charter.yaml
    sha256: b0cb6b6b5a27ca8376c5ef29bfa5c87eb64e6dcaa60e7d2330962341932b26c8
verdict: ready
issue_counts:
  low: 2
  critical: 0
  medium: 1
  high: 0
  info: 0
findings:
- id: F1
  severity: low
  category: coverage-drift
  summary: >-
    tasks.md's Requirements Coverage Summary maps SC-007 (zero behavior
    change with no org pack configured) to WP01, WP03, and WP04. WP01
    carries it explicitly (Objectives cites NFR-005; T005 is a dedicated
    "NFR-005 regression check" subtask). WP03 and WP04's own prompt bodies
    never name SC-007 or NFR-005 and have no dedicated subtask for
    "existing test suites pass unmodified with zero org packs configured"
    — WP03's T017 and WP04's T026 are explicitly labeled for SC-004/NFR-001
    (malformed-config fail-soft), a related but distinct property. A lane
    agent reading only its own WP prompt would not see SC-007 as an
    explicit deliverable there, though each WP's Test Strategy section
    does direct running the pre-existing suite, which would likely surface
    a gross regression as a side effect.
- id: F2
  severity: low
  category: prose-accuracy
  summary: >-
    tasks.md's Dependency & Execution Summary states "WP01 + WP02 + WP03
    deliver User Story 1 and User Story 2 (P1)". User Story 1's Acceptance
    Scenario 3 (charter list --all reporting the org tier as ORG at the
    flat path) is FR-006, delivered by WP05, not by WP01-WP03. WP01-WP03
    deliver User Story 1's resolution behavior (Acceptance Scenarios 1-2)
    but not its reporting scenario. Minor overstatement of MVP scope; does
    not affect any WP's implementation instructions.
- id: F3
  severity: medium
  category: tooling-defect
  summary: >-
    `spec-kitty agent mission record-analysis` itself embeds absolute host
    filesystem paths, including the operator's home-directory username,
    into this report's own `input_artifacts` block (the spec.md/plan.md/
    tasks.md/charter path entries) before committing it — a hygiene
    violation of this mission's own "no host paths, no usernames" rule,
    baked in by the recorder tool itself rather than by authored mission
    content. This is the same failure class `spec.md`'s Provenance section
    already documents one prior instance of. Caught and hand-corrected in
    this committed report (paths below are repo-relative) since persisting
    this report is this analysis's one permitted mutation; the underlying
    CLI defect (`collect_input_artifact_hashes` /
    `write_analysis_report` in `src/specify_cli/analysis_report.py`) is
    unfixed for every other invocation and is a candidate SPEC-KITTY-LEDGER
    entry.
---

# Cross-Artifact Consistency Check — up-org-template-fsm-01M06F9K (#3523)

## Scope

Reviewed `spec.md`, `plan.md`, `tasks.md`, `lanes.json`, `meta.json`, `status.json`,
and all six WP prompts (`tasks/WP01..WP06-*.md`) on branch `up-org-template-fsm`.
No spec/plan/tasks/WP file was modified — this is a read-only cross-artifact
analysis; the only mutation is this report.

## Structural constraint 1 — WP01 is a hard prerequisite for WP03

Confirmed independently in the WP prompt *bodies*, not only in `tasks.md`:

- `tasks/WP03-org-tier-template-resolvers.md` carries a dedicated
  "MANDATORY PREREQUISITE" section before any subtask content, quoting
  `plan.md`'s IC-01→IC-03 ordering rationale verbatim and instructing the
  implementer to verify WP01 actually landed (the mission-scoped override
  probe must already exist in `specify_cli/runtime/resolver.py`) before
  writing any code.
- `tasks/WP01-converge-resolver-tier1-probe.md`'s own Notes/Risks sections
  state it is "the exact prerequisite WP03 depends on" and warn against
  scope-creeping the org tier into WP01.
- Verified directly against the live tree: `src/doctrine/resolver.py`
  (~line 172) has the two-shape tier-1 probe (mission-scoped, then global);
  `src/specify_cli/runtime/resolver.py` (~line 283) currently has only the
  global probe — the drift WP01 exists to close is real, not a stale claim.

`lanes.json` enforces this via lane grouping: `lane-a = [WP01, WP02, WP03]`,
`depends_on_lanes: []`, with the WP-level dependency graph (WP03 depends on
WP01, WP02) requiring in-lane sequencing. The `collapse_report` explicitly
records the write-scope overlap and dependency: `{wp_a: WP01, wp_b: WP03,
rule: write_scope_overlap, evidence: "... WP03 depends on WP01"}`.

## Structural constraint 2 — WP04/WP06 file collision on `runtime_bridge_io.py`

Confirmed in both WP bodies, each restating it independently (not only
cross-referencing the other's prompt):

- `tasks/WP04-org-tier-fsm-discovery.md` opens with a "FILE COLLISION WITH
  WP06" callout naming the exact functions each WP owns
  (`_build_discovery_context` / `_runtime_template_key`'s `project_tiers`
  vs. `_template_key_for_file` / `_resolve_runtime_template_in_root`) and
  states explicitly: "Do not let anyone 'optimize' WP04 and WP06 back into
  parallel work packages."
- `tasks/WP06-desilence-walk-b-failures.md` carries the mirror-image
  callout, explicitly labeling it "a file collision, not a functional
  dependency" and repeating the NFR-003 review-not-CI text in full so the
  WP06 prompt is self-sufficient for a lane agent that only reads its own
  file.

`lanes.json` enforces this: `lane-b = [WP04, WP06]`, `depends_on_lanes:
["lane-a"]`. `collapse_report` records `{wp_a: WP04, wp_b: WP06, rule:
write_scope_overlap, evidence: "overlapping globs:
'src/runtime/next/runtime_bridge_io.py' ... WP06 depends on WP04"}`.

**`lanes.json` lane shape matches the required structure exactly**: 3 lanes
— `lane-a = {WP01, WP02, WP03}`, `lane-b = {WP04, WP06}`, `lane-c = {WP05}`
— with `lane-c` also gated on `lane-a` (WP05 depends on WP02/WP03).

## Carried constraints (3)

All three confirmed present in every WP prompt body where applicable:

1. **`charter.drg.resolve_org_roots` via lazy import, never direct
   `doctrine.*`** — present in WP03 ("Three things that cost a round if
   rediscovered" #1, with the five existing call-site citations), WP04
   ("Use `charter.drg.resolve_org_roots` via the existing lazy-import
   pattern" section), WP06 (adapted: "any code you add here ... must still
   route through `context.org_roots` or the lazy `charter.drg` facade").
   Not restated in WP01/WP02/WP05 because none of them add a new
   `resolve_org_roots` call site — correctly scoped.
2. **No `try/except Exception` around `resolve_org_roots`** — present in
   WP03 (constraint #2, T012/T014 steps, Risks section), WP04 (T021 step 3,
   explicitly "same DEC-005 discipline as WP03"). Not restated in WP01/WP02
   (no such call added there) or WP05/WP06 (no new `resolve_org_roots` call
   site) — correctly scoped.
3. **`_tier_to_origin` needs an `ORG` entry** — implemented in WP02 (T008,
   T009) and referenced as "already landed" context in WP03's constraint
   #3 so WP03 doesn't re-touch `template_resolver.py`.

## Coverage — 12 FRs, verified from frontmatter

Every WP's YAML frontmatter `requirement_refs` field (not `tasks.md`'s
summary table) was read directly:

| WP | requirement_refs (frontmatter) |
|----|----|
| WP01 | FR-001, NFR-005 |
| WP02 | FR-002, FR-012 |
| WP03 | FR-003, FR-004, FR-005, NFR-001, NFR-004 |
| WP04 | FR-007, FR-008, FR-009, NFR-001, NFR-003, NFR-004 |
| WP05 | FR-006, NFR-006 |
| WP06 | C-005, FR-010, FR-011, NFR-003 |

Union: FR-001 through FR-012, all present exactly once as a primary owner —
full 12/12 FR coverage confirmed from frontmatter, not from `tasks.md`'s own
coverage table (which agrees).

**SC-001–008** (cannot be registered structurally per upstream #3519 —
`map-requirements` rejects `SC-*`) — confirmed present in prose in the WP
body that owns them:

| SC | Located in | Confirmed |
|----|----|----|
| SC-001 | WP03 Objectives ("Success criteria" list, FR-003/FR-004 rows) | Yes |
| SC-002 | WP01 T003 ("the exact measurement plan.md's Verification Design table requires for FR-001") | Yes |
| SC-003 | WP04 Objectives, T022/T023 ("SC-003 part 3" / "part 2") | Yes |
| SC-004 | WP03 T017 title, WP04 T026 title (both literally "NFR-001.../SC-004") | Yes |
| SC-005 | WP06 Objectives ("Success criteria (FR-010, FR-011, SC-005)") | Yes |
| SC-006 | WP05 Objectives ("Success criteria (FR-006, SC-006)") | Yes |
| SC-007 | Claimed for WP01/WP03/WP04 by `tasks.md`; only WP01 names it explicitly | **F1 (low)** |
| SC-008 | WP04 T025 title ("Position-parity test (NFR-004/SC-008)") | Yes |

## Ownership, lanes, dependency graph

- `owned_files` disjoint across all six WPs except the three declared
  overlaps (WP01/WP03 on `specify_cli/runtime/resolver.py` +
  `tests/runtime/test_resolver_unit.py`; WP02/WP03 on
  `src/doctrine/resolver.py` + `tests/doctrine/test_resolver.py`; WP04/WP06
  on `src/runtime/next/runtime_bridge_io.py` +
  `tests/runtime/test_bridge_io.py`) — matches `lanes.json`'s
  `collapse_report` exactly (3 `write_scope_overlap` events, 0 unexplained).
- `create_intent: []` on all six WPs — correct: this mission only edits
  existing modules, no new file is planned anywhere in `spec.md`/`plan.md`.
- Dependency graph: WP01(–) → WP02(–) → WP03(WP01,WP02) → WP04(WP02) →
  WP05(WP02,WP03) → WP06(WP04). Acyclic; a valid topological order exists
  (WP01, WP02, WP03, WP04, WP05, WP06).

## Spec-vs-WP-instructions, artifact by artifact

All four resolution/discovery sites (`doctrine/resolver.py`,
`specify_cli/runtime/resolver.py`, FSM Walk A `discovery.py`, FSM Walk B
`runtime_bridge_io.py`) have their exact spec-mandated fix (org tier
between LEGACY/project-legacy and GLOBAL_MISSION/user-global, sourced from
`resolve_org_roots`, first-match-wins, no swallowing) reproduced with
citations in WP03 (first two) and WP04 (last two).

The **third FSM wiring site**, `src/specify_cli/mission_loader/command.py`
(`_build_discovery_context`, confirmed live at line 187, called from
`run_custom_mission` at line 94), gets outsized emphasis in WP04 exactly as
the operator brief requires: its own subtask (T022), its own "Mission-loader
coverage gate" section naming the real CI job and test-collection paths, and
a Risks-section callout that this is "the easiest mistake." Verified
directly against `.github/workflows/ci-quality.yml:1437-1462`: the
`mission-loader-coverage` job runs exactly
`tests/unit/mission_loader/ tests/integration/test_mission_run_command.py`
with `--cov=src/specify_cli/mission_loader --cov-fail-under=90` — matches
WP04's citation verbatim, not a stale reference.

## Verification design — tier named, not "test passes"

Every WP's Objectives & Success Criteria section names the resolved tier
explicitly (`tier == ResolutionTier.ORG`, `tier == ResolutionTier.OVERRIDE`,
or the FSM string tier `"org"` where no `ResolutionTier` applies) rather
than "a passing test." Matches `plan.md`'s per-FR Verification Design table
row for row across WP01/WP02/WP03/WP04/WP05; WP06's FR-010/FR-011 are
diagnostic-presence requirements, not tier-resolution requirements, and are
correctly verified as "named warning present" rather than a tier.

## NFR-003 — no automated gate for `src/runtime/next/**`

Both WP04 and WP06 state, verbatim in each prompt's own body (not only by
cross-reference): the architectural gate does not scan
`src/runtime/next/**` (#3522 named explicitly in both); compliance is
"verified by review, not by CI"; the PR description MUST state this
explicitly and name #3522; "a green CI run ... is not evidence." Confirmed
directly against `tests/architectural/test_runtime_charter_doctrine_boundary.py`
that `_RUNTIME_ROOT` is hardcoded to `src/specify_cli`.

## Subtask IDs, sizing, hygiene

- **Subtask IDs**: T001–T036 all present exactly once in `tasks.md`'s
  Subtask Index table (verified by table-row count = 36, no duplicates).
- **Sizing**: `wc -l` on every mission markdown file — largest is
  `tasks/WP04-org-tier-fsm-discovery.md` at 403 lines; all files well under
  the 700-line ceiling.
- **Hygiene**: grepped the full mission directory (`spec.md`, `plan.md`,
  `tasks.md`, all six WP prompts) for host paths (`/home/[a-z]+`,
  `/Users/[a-z]+`) and the operator's username — zero hits in the
  human-authored artifacts. The one non-existent citation in the mission
  (`spec.md`'s `_rnd/spikes/up-org-template-fsm.md`) is explicitly flagged
  by `spec.md` itself and re-confirmed by `plan.md`'s "Verification gap"
  note as deliberately non-retrievable provenance, not a silent broken
  citation — confirmed directly that no `_rnd/` directory exists in this
  checkout, matching the spec's own claim. **However**, the `record-analysis`
  recorder tool used to persist *this* report initially wrote four absolute
  host paths (with username) into its own `input_artifacts` frontmatter —
  see **F3**; hand-corrected to repo-relative paths before this report was
  finalized.
- Spot-checked ~15 load-bearing `file:line` citations (enum locations,
  tier-1 probe blocks, `_build_discovery_context` sites, `_tier_to_origin`,
  `_HAS_BUILT_IN_CONTENT_DIR`, CI job definitions) directly against the live
  tree — all resolve to real code matching the cited claims, with only
  minor line-number drift that each WP prompt already tells implementers to
  re-verify live rather than trust.

## Findings

| ID | Severity | Summary |
|----|----|----|
| F1 | low | SC-007/NFR-005 claimed as covered by WP03/WP04 in `tasks.md`'s coverage table, but neither WP prompt body names it or carries a dedicated subtask (unlike WP01's explicit T005). |
| F2 | low | `tasks.md`'s "MVP Scope" line overstates WP01-WP03 as delivering all of User Story 1, when Acceptance Scenario 3 (FR-006) is WP05's. |
| F3 | medium | The `record-analysis` recorder tool embedded absolute host paths + username into this report's own `input_artifacts` block; hand-corrected before finalizing, but the CLI defect itself is unfixed. |

No high/critical findings. F1/F2 are documentation/labeling gaps in
`tasks.md`'s summary framing, not defects in what a lane agent is
instructed to build — the underlying behavior each SC exists to guard is
either tested anyway (SC-007, via each WP's own Test Strategy running the
pre-existing suite) or does not affect any WP's actual subtasks (F2 is a
scope-summary imprecision only). F3 is a tooling defect discovered and
remediated in-place during this analysis's one permitted mutation (this
report); it says nothing about the mission's spec/plan/tasks/WP readiness
but is worth an upstream ledger entry so it doesn't recur silently on the
next mission's analyze pass.

## Verdict

`critical: 0, high: 0` → **ready** (structural: any high/critical would
force `blocked`; none found — F3 is medium, which does not block).
