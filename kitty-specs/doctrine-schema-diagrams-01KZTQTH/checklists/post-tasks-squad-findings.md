# Post-tasks adversarial squad — findings & disposition

**Pointcut**: post-tasks · **Mission**: doctrine-schema-diagrams-01KZTQTH · **Date**: 2026-08-12
**Lenses** (profile-loaded, read-only): reviewer-renata, planner-priti, python-pedro, architect-alphonso.
**Question**: fakeable/vacuous DoDs + decomposition realism across the 9 WPs.

All model claims were verified CORRECT against source by python-pedro:
`AgentProfileSchema` (`src/doctrine/agent_profiles/schema_models.py:185`) with nested
`AgentSpecialization` (`:78`) + kebab aliases (`populate_by_name=True`);
`MissionStep`/`MissionStepContract`/`MissionStepContractStep` nesting; `ActionIndex` frozen
dataclass; `list()` → `NodeKind`=16, `Relation`=15, `ArtifactKind`=12; three distinct
"anti pattern" entities (`ArtifactKind.ANTI_PATTERN`, `NodeKind.ANTI_PATTERN` string, `styleguides.AntiPattern` class).

## Folded (this revision)

| # | Sev | Finding (converged) | Fix |
|---|-----|---------------------|-----|
| 1 | HIGH | **Agent-profile diagram (FR-003 4th artefact) authored by no WP** — also the only shipped aliased+nested diagram that forces the drift guard's alias/recursion path (renata ×2). | WP05 T035: author the `@startyaml` agent-profile schema diagram (incl. nested `AgentSpecialization`) in `doctrine-kinds.md`; WP08 binds it in the table (the real forcing artefact). |
| 2 | HIGH | **"non-empty SVG" success predicate admits PlantUML error images** — spike/isolation green on the exact font/DNS failure they exist to catch (renata). | WP01 T003/DoD + WP03 T013: render with `-failfast2`; assert the SVG contains expected fixture `title`/key tokens AND no PlantUML error signature. |
| 3 | HIGH | **Fence class is `lang-plantuml` (DocFX/markdig), not `language-plantuml`** — the custom `language-*` emitter only covers kitty-specs pages; the mission diagrams are on the `lang-` side; stub test would validate the wrong assumption (pedro, renata). | WP02 T007/T010/DoD: recovery matches BOTH `lang-plantuml` and `language-plantuml`; render step FAILS CLOSED on any recognized-but-unrendered `@start*` fence ("all fences consumed" positive check); derive the class from a real DocFX build in ≥1 test, not only a stub. |
| 4 | MED | **StrEnum synthetic-member injection is literally infeasible** (empirically confirmed) (pedro, renata). | WP08 T027/T028: introspect kinds through a patchable seam `_artifact_kind_values()`; T028 monkeypatches THAT (real values + a synthetic string) AND a delete-a-disposition test (remove `anti_pattern`'s entry → guard FAILS) forces reading `list(ArtifactKind)`. Same patchable-seam approach for T030 nested-field injection (patch the extracted field set, not the frozen model). |
| 5 | MED | SANDBOX control universally skippable → "zero inbound" non-discriminating (renata). | WP03 T012: pin the fixture to `@startuml` (honors `!includeurl`); make the no-SANDBOX control a HARD assertion (listener IS hit) in an egress-allowed job; skip only where egress is genuinely blocked. |
| 6 | MED | Alt-text predicate circular (renata). | WP02 T011: assert `aria-label` equals the exact literal `title` string authored in the fixture. |
| 7 | MED | README pointer-lint is a narrow proxy + implementer-chosen cap + self-defining "covered" (renata). | WP09 T031/T033: define "covered" by an objective predicate (dirs under `src/doctrine/` with `__init__.py` + a bound kind/diagram); fix the cap in the WP (≤ 40 lines / ≤ 2 KB); add positive checks (required pointer links present, low non-link prose word-count) + forbid fenced code blocks echoing field names, not only pipe-tables. |
| 8 | MED | "zero suppressions" conflicts with the mandated `glossary_linker` mirror (needs one justified `# noqa: E402`) (pedro). | WP02 DoD: "no *unjustified* suppressions" — a single narrow, inline-justified `# noqa: E402` matching the canonical pattern is charter-sanctioned. |
| 9 | MED | `single_branch` flatten un-isolates whole-file `issue-matrix.json`/`acceptance-matrix.json` under parallel worktree lanes (alphonso). | Execution posture: serialize host-side lane integration (matrices updated one lane at a time). Recorded in tasks.md. `single_branch` retained (lower overhead) since content write-scopes are disjoint and status is append-only. |
| 10 | MED | DIR-012 tracking issue is prose-only, not a tracked/assigned artefact (priti). | Pre-implement gate: open the GitHub issue, assign HiC, record its number in WP01/WP02 `tracker_refs` + the issue-matrix row (before claiming WP01). |
| 11 | MED | plan.md Project Structure omits the load-bearing `plantuml_invoke.py` seam (alphonso). | plan.md: add `scripts/docs/plantuml_invoke.py` as the WP01-owned shared invoker consumed by WP02/WP03. |

## Folded (LOW / clarifications)

- WP02 T008/T009: reword "drop host `setup-java`" → "do NOT ADD `setup-java`" (it does not exist today; the real risk is adding it) (alphonso, pedro). Clarify docs-build-pr.yml already globs `scripts/docs/**`+`docs/**` so only docs-pages.yml's enumerated `paths:` needs the allowlist edit (alphonso).
- WP02: after wiring, `workflow_dispatch` the real `docs-pages.yml` path to confirm docker works in the deploy-job context, not only the standalone spike (pedro).
- WP08 T026: call out all THREE "anti pattern" entities; `ArtifactKind.ANTI_PATTERN` gets its own disposition without binding to the class/string (pedro).
- WP09: if WP08 lands first, consume its binding table rather than re-deriving the module→diagram mapping (alphonso).
- tasks.md: reconcile coverage map (C-001 also → WP03); state the WP05–07→WP01 gate is a conscious de-risk (avoid wasted authoring if the spike fails) (priti). plan.md: reword "IC-04 parallel with IC-01" → engine parallel, guard *run* waits on WP05–07 (priti); fix plan.md:3 branch header to `-impl` (alphonso).
- WP01/WP03: decide the spike workflow's fate — kept as a standing runner-capability canary (documented), not silently orphaned (priti).

## Positive verifications (no defect)

Dependency graph matches intended shape; **zero owned_files overlap** across all 9 WPs; WP01 blocking-gate enforced by the graph; sizing sane (2–6 subtasks, <700 lines); full FR/NFR/C coverage, no orphans; WP09 genuinely last/abandonable; `plantuml_invoke` single-owner/multi-consumer seam clean; workflow insertion slot REAL in both files (verified line numbers); `glossary_linker` code-fence skip makes post-glossary ordering safe+necessary; drift-guard under `tests/` is the right seam (no cross-lane import coupling); two-runner spike matrix covers both real deploy hosts (docs-build-pr=ubuntu-latest, docs-pages=blacksmith).
