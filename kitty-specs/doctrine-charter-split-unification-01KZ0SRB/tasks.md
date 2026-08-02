# Tasks: Doctrine-Charter Split — Single-Path Authority Foundation

**Mission**: `doctrine-charter-split-unification-01KZ0SRB` · **Branch**: `feat/doctrine-charter-split-unification`
**Input**: [plan.md](./plan.md) (IC-01..IC-06), [spec.md](./spec.md) (16 FR / 5 NFR / 5 C),
[research.md](./research.md) (D1..D9 — post-plan squad decisions, all anchors verified live).

> Foundation-first mission (no bulk edit, no occurrence_map). **14 work packages.** Ownership is disjoint at
> file granularity (squad-verified: `write_scope` is a per-file path list, not a glob → no cross-lane
> collisions; research.md D2). The wheel **cutover** (#3101) is a deferred follow-on — this mission is the
> single read/path authority + wiring + packaging **groundwork**.

## Branch strategy

Planning artifacts were generated on `feat/doctrine-charter-split-unification`. Each WP's execution worktree is
allocated per computed lane from `lanes.json` at `finalize-tasks`. Completed changes merge back into
`feat/doctrine-charter-split-unification` unless the operator redirects the landing branch.

## Dependency waves (research.md D8)

- **Wave 0 (parallel, no deps):** WP01, WP02, WP03, WP04, WP05, WP07, WP10, WP12, WP14
- **Wave 1 (deps):** WP06 ⟵WP05 · WP08 ⟵WP07 · WP09 ⟵WP07 · WP13 ⟵WP10(soft)
- **Wave 2 (sink — LAST):** WP11 ⟵{WP01,WP02,WP03,WP06} (+ full AST literal census)

## Issue-matrix seed (coord worktree; DIR-012 assign-to-HiC on claim; C-005)

| Issue | P | Owning WP | Verdict (filled in coord worktree at review) |
|-------|---|-----------|----------------------------------------------|
| #3150 dashboard presence probe | P1 | WP02 | (pending) |
| #3140 meta.json fail-closed | P1 | WP07 (+08/09) | (pending) |
| #3149 CI path-filter | — | WP14 | (pending) |
| #3107 inert parity gate | — | WP14 | (pending) |
| #3102 closeout | P2 | WP14 | (pending) |
| #2831 / #2992 (investigate) | P0/P1 | WP14 (timeboxed, default DEFER) | (pending) |

## Work Packages

### WP01 — Retire charter/context.py OR-gate → charter.yaml-only presence (IC-01)

FR-002: retire `charter/context.py:249` `OR charter.md` presence gate → `charter.yaml`-only; confirm FR-001
bundle-constant home (already exists). Prose readers (`:300-302`, `:366-371`) unchanged.
- **Depends on**: none. **Prompt**: [tasks/WP01-retire-context-or-gate.md](./tasks/WP01-retire-context-or-gate.md)

### WP02 — Dashboard presence-probe split (IC-01, #3150)

FR-003: split `dashboard/charter_path.py::resolve_project_charter_path` — presence keys `charter.yaml`
(survives md-deletion), body still reads `charter.md`.
- **Depends on**: none. **Prompt**: [tasks/WP02-dashboard-presence-probe-split.md](./tasks/WP02-dashboard-presence-probe-split.md)

### WP03 — analysis_report hashes charter.yaml (IC-01)

FR-004: `analysis_report.py` hash `charter.yaml`; remove **both** `charter.md` hash entries (`:191` companion
+ `:192` legacy).
- **Depends on**: none. **Prompt**: [tasks/WP03-analysis-report-hash-yaml.md](./tasks/WP03-analysis-report-hash-yaml.md)

### WP04 — Scope the status-collector legacy charter.md gate (IC-01)

FR-006: scope the `_status_collectors.py:85-87` legacy `charter.md` gate explicitly + a `charter.md`-only
regression test (or remove if unsupported).
- **Depends on**: none. **Prompt**: [tasks/WP04-status-collector-legacy-gate-scope.md](./tasks/WP04-status-collector-legacy-gate-scope.md)

### WP05 — RetrospectiveGovernance schema + emitter (IC-02)

FR-005a+b: add `RetrospectiveGovernance` sub-model to `charter/schemas.py` (pure data, no `specify_cli`
import); wire emitter to populate `governance.retrospective`; extend `_prune_optional_empties` to omit an
empty/None block (NFR-005 byte-stability, research.md D3).
- **Depends on**: none. **Prompt**: [tasks/WP05-retrospective-governance-schema-emitter.md](./tasks/WP05-retrospective-governance-schema-emitter.md)

### WP06 — Retrospective yaml-first resolver (IC-02)

FR-005c: `retrospective/{policy,mode,gate}.py` resolve **yaml-first** (precedence) with `charter.md`
frontmatter as overridden secondary; collapse the 3 `_CHARTER_REL` to one shared definition.
- **Depends on**: WP05. **Prompt**: [tasks/WP06-retrospective-yaml-first-resolver.md](./tasks/WP06-retrospective-yaml-first-resolver.md)

### WP07 — meta.json fail-closed authority + caller census (IC-03, #3140)

FR-007: emit the caller census (`notes/meta-load-census.md`; disambiguate the TWO `load_meta` defs, D4);
publish ONE public `load_meta_fail_closed` reusing `core/paths` (import stays function-local); route the
`mission_runtime`/`runtime` callers so the two red `test_mission_status_aggregate` tests go green.
- **Depends on**: none. **Prompt**: [tasks/WP07-meta-fail-closed-authority-census.md](./tasks/WP07-meta-fail-closed-authority-census.md)

### WP08 — Route meta callers batch A (IC-03)

FR-007: route the census's unwrapped/divergent callers, batch A (coordination + migration + audit + status).
- **Depends on**: WP07. **Prompt**: [tasks/WP08-meta-fail-closed-route-batch-a.md](./tasks/WP08-meta-fail-closed-route-batch-a.md)

### WP09 — Route meta callers batch B + full-census contract (IC-03)

FR-007: route the census's unwrapped/divergent callers, batch B (merge + dashboard + cli + doc_analysis +
tracker + acceptance); NFR-003 full-census contract test lands here.
- **Depends on**: WP07. **Prompt**: [tasks/WP09-meta-fail-closed-route-batch-b.md](./tasks/WP09-meta-fail-closed-route-batch-b.md)

### WP10 — Delete layer edge + AST charter-import gate (IC-04)

FR-008: delete `synthesize_pipeline.py:68` `import specify_cli` (`importlib.metadata` only) + a non-vacuous
AST-walk charter→specify_cli import gate (pytestarch is green with the edge present; self-mutation proof).
- **Depends on**: none. **Prompt**: [tasks/WP10-charter-import-layer-gate.md](./tasks/WP10-charter-import-layer-gate.md)

### WP11 — Charter path-literal authority gate (IC-04, SINK)

FR-016: AST path-literal authority gate banning inline `.kittify/charter/charter.{yaml,md}` builders outside
`charter/bundle.py` + new `charter.md` presence gates; seed the frozen shrink-only allowlist from a full AST
census (residue at `invocation/empty_charter.py`, `charter_runtime/lint/…`, `doctrine/versioning.py`,
`doctrine/spdd_reasons/activation.py`, D6; decide the `src/doctrine/**` scope). **Lands last.**
- **Depends on**: WP01, WP02, WP03, WP06. **Prompt**: [tasks/WP11-charter-path-literal-authority-gate.md](./tasks/WP11-charter-path-literal-authority-gate.md)

### WP12 — Wheel packaging groundwork (IC-05)

FR-009 + FR-010: mint `src/kernel/pyproject.toml` (`spec-kitty-kernel`, zero first-party deps); fix
`src/doctrine/pyproject.toml` (add `spec-kitty-kernel` dep + hatchling build-hook carrying the repo-root
sibling `packs/`, D7); execute a real `hatch build` recorded in research.md §D7; non-vacuous closure test.
**No cutover** (C-002 — root wheel unchanged).
- **Depends on**: none. **Prompt**: [tasks/WP12-wheel-packaging-groundwork.md](./tasks/WP12-wheel-packaging-groundwork.md)

### WP13 — Charter-wheel assessment + ADR (IC-05)

FR-011: charter-wheel assessment + ADR draft (extractable-in-principle; kernel→doctrine→charter no-partial
sequencing; extends `2026-04-25-1`; deferred-issue list).
- **Depends on**: WP10 (soft). **Prompt**: [tasks/WP13-charter-wheel-assessment-adr.md](./tasks/WP13-charter-wheel-assessment-adr.md)

### WP14 — CI hygiene + parity gate + docs (IC-06, #3149/#3107/#3102)

FR-012 (#3149 add `cli/commands/charter/**` to `doctrine-charter-tests.yml`), FR-013 (#3107 repoint **both**
parity fixtures + regen `docs/api/{cli-commands,agent-subcommands}.md`; assert the test RAN GREEN), FR-014
(#3102 closeout in PR body), FR-015 (timeboxed investigate #2831/#2992; default defer-with-reason).
- **Depends on**: none. **Prompt**: [tasks/WP14-ci-hygiene-parity-docs.md](./tasks/WP14-ci-hygiene-parity-docs.md)

## ATDD red test per WP (charter C-011 — committed failing-first)

| WP | ATDD red |
|----|----------|
| WP01 | context "missing" gate passes with `charter.yaml` present + `charter.md` **deleted** (currently the OR-bridge masks it) |
| WP02 | dashboard presence probe returns present with `charter.md` deleted (#3150) |
| WP03 | analysis-report staleness computes with `charter.md` absent; hashes `charter.yaml` |
| WP04 | `charter.md`-only status-collector shape resolves (backward-compat) |
| WP05 | `charter generate` emits `governance.retrospective`; omits when empty (byte-stable) |
| WP06 | yaml-wins over md-frontmatter; both-present precedence; legacy-md-only still resolves |
| WP07 | the two `test_mission_status_aggregate::TestLoadCoordUnavailableFailsClosed` reds → green |
| WP08/09 | NFR-003 full-census: corrupt + non-dict `meta.json` yields typed/None across the enumerated set |
| WP10 | AST charter-import gate **fails with the edge present** (self-mutation) |
| WP11 | literal gate fails on a re-introduced inline charter path literal (self-mutation) |
| WP12 | closure test fails if `kernel` dep or `packs/` hook removed; real `hatch build` lands `packs/built-in/` as doctrine sibling |
| WP13 | ADR review (document deliverable) |
| WP14 | `test_docs_cli_reference_parity` runs GREEN (not skipped); path-filter triggers on `cli/commands/charter/**` |
