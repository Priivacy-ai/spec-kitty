# Tasks: Charter Pack Usage Journey

**Mission**: `charter-pack-usage-journey-01KYWWTF` · **Branch**: `feat/charter-pack-usage-journey`
**Input**: [plan.md](./plan.md) (IC-01..IC-09), [spec.md](./spec.md) (12 FR / 4 NFR / 5 C),
[research.md](./research.md), [notes/research-synthesis.md](./notes/research-synthesis.md)

> Behavioural mission (no bulk edit, no occurrence_map). 8 work packages, ~1 IC → 1 WP (IC-05 folded into
> WP02). Ownership is disjoint (squad-verified); only WP08 has dependencies. The 8 journey acceptance tests +
> 3 squad-added guards (bare-project resolver regression, FR-006 JSON present-signal, `frozenset()` opt-out)
> are the behavioural net — each rides the WP whose behaviour it guards.

## Branch strategy

Planning artifacts were generated on `feat/charter-pack-usage-journey`. Each WP's execution worktree is
allocated per computed lane from `lanes.json` at `finalize-tasks`. Completed changes merge back into
`feat/charter-pack-usage-journey` unless the operator redirects the landing branch.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----|
| T001 | Rewrite `is_charter_empty` → bundle-presence + routability split | WP01 | |
| T002 | Update `_MATCH_REASON`; campsite-delete dead docstring + `charter_activated_urns` (keep `PackContext`) | WP01 | |
| T003 | Journey tests 1-3: empty→net; apply-no-compile→net (#3104); apply+compile→net off (NO_MATCH honest) | WP01 | [P] |
| T004 | Journey 3 org-pack safety + SC-005 bootstrapped-empty + `frozenset()` opt-out pins | WP01 | [P] |
| T005 | NFR-001 perf spy (≤1 `PackContext.from_config` + 1 `stat`, no URN load) | WP01 | [P] |
| T010 | Truthful default `apply` output — name `spec-kitty charter generate` | WP02 | |
| T011 | `apply --compile` chains `charter generate --no-from-interview` (git-worktree doc) | WP02 | |
| T012 | Campsite: hoist the 2 identical `path`/`apply` resolve-or-exit blocks | WP02 | |
| T013 | Journey 7 truthful-output test | WP02 | [P] |
| T014 | IC-05 convergence test (document-as-equivalent; catalog-shape from same activation input) | WP02 | [P] |
| T020 | Retarget `context.py` presence gate → `bundle.CHARTER_YAML` (prose renders only when present) | WP03 | |
| T021 | NEW CLI sibling `_resolve_charter_bundle_path` in `_common.py`; route `_status_collectors:62` through it | WP03 | |
| T022 | Soft-retarget `context_json._project_charter_json_block` + reconcile 2nd site `cli/.../context.py:158` | WP03 | |
| T023 | Journeys 4-5 (bundle authority, survives `charter.md` deletion) + FR-006 `--json` present-signal test | WP03 | [P] |
| T030 | Thread `PackContext.activated_directives` into `_resolve_directives_selection`/`resolve_project_governance` | WP04 | |
| T031 | Three-state guard (filter only when `is not None`; `None`→catalog default) | WP04 | |
| T032 | Journey 6 (5 not 29) + bare-project regression; verify 5 consumers; don't touch M1 `:187/:250` | WP04 | [P] |
| T040 | `render_critical_section_include` returns honest placeholder (never `None`) | WP05 | |
| T041 | US4.1 test: `section:terminology-canon` + `section:code-review-checklist` resolve (#3095/#3094/#2552) | WP05 | [P] |
| T050 | Redirect `spec-kitty.analyze` skill + command-skills manifest + docs → `agent mission record-analysis` | WP06 | |
| T051 | US4.2 verify: no documented-but-absent command; scope-guard vs #849/#851/#853 | WP06 | [P] |
| T060 | New path-filtered workflow (`src/doctrine/**` + `src/charter/**` + `src/specify_cli/invocation/**`) | WP07 | |
| T061 | US4.3: skip-with-green for unrelated PRs; no double-charge of main-CI gates | WP07 | [P] |
| T070 | Document `apply`→`generate` two-step + empty-charter dispatch in the charter journey guides | WP08 | |
| T071 | Freshen page-inventory + docs-index; run terminology guard | WP08 | [P] |

## Work Packages

### WP01 — Dispatch-net predicate: bundle-presence + org-pack-safe routability (IC-01)

- **Goal**: fix the #3104 P1 regression — applying a pack without compiling must keep the generic-agent net.
- **Priority**: P1 (MVP — ship first, alone). **Independent test**: dispatch an unmatched request after
  `apply minimal` (no compile) → falls back to generic agent, NOT `ROUTER_NO_MATCH`.
- **Requirements**: FR-001, FR-002, NFR-001, NFR-004, SC-001, SC-005. **Subtasks**: T001–T005.
- **Depends on**: none. **Prompt**: [tasks/WP01-dispatch-net-predicate.md](./tasks/WP01-dispatch-net-predicate.md)

### WP02 — `apply --compile` bridge + truthful output + convergence assert (IC-02 + IC-05)

- **Goal**: chain the existing compile seam (opt-in) and make default `apply` name the exact next command.
- **Priority**: P1. **Independent test**: `apply --compile` produces `charter.yaml` in one step; default
  `apply` output names `spec-kitty charter generate`.
- **Requirements**: FR-003, FR-004, FR-008, SC-004. **Subtasks**: T010–T014.
- **Depends on**: none. **Prompt**: [tasks/WP02-apply-compile-bridge.md](./tasks/WP02-apply-compile-bridge.md)

### WP03 — Read-surface presence-gate retarget → charter.yaml authority (IC-03)

- **Goal**: `charter context`/`charter status` reflect activations once compiled; survive `charter.md` delete.
- **Priority**: P1. **Independent test**: after compile, `charter context --action implement` renders the
  activated set; delete `charter.md` → still works.
- **Requirements**: FR-005, FR-006, SC-002. **Subtasks**: T020–T023.
- **Depends on**: none (sole owner of `context.py` + `context_json.py`).
  **Prompt**: [tasks/WP03-read-surface-retarget.md](./tasks/WP03-read-surface-retarget.md)

### WP04 — Single directive authority: retire the catalog-fallback (IC-04)

- **Goal**: `resolve_project_governance` returns the activated set (5), never the 29-catalog fallback.
- **Priority**: P2. **Independent test**: apply-5 + compile → `resolve_project_governance().directives` == 5
  (journey 6, RED today); bare project → catalog default (not 0).
- **Requirements**: FR-007, SC-003. **Subtasks**: T030–T032.
- **Depends on**: none (shares `resolver.py` with M1's *landed* changes — verify, don't revert).
  **Prompt**: [tasks/WP04-single-directive-authority.md](./tasks/WP04-single-directive-authority.md)

### WP05 — Advertised section selectors resolve (IC-06)

- **Goal**: `section:terminology-canon`/`section:code-review-checklist` resolve instead of dead-ending.
- **Priority**: P2. **Independent test**: the selector renders a section or an honest placeholder — never
  "No charter section found for selector".
- **Requirements**: FR-010, SC-007. **Subtasks**: T040–T041.
- **Depends on**: none (primary graceful-degrade is dependency-free).
  **Prompt**: [tasks/WP05-section-selectors-resolve.md](./tasks/WP05-section-selectors-resolve.md)

### WP06 — `spec-kitty analyze` surface reconciliation (IC-07)

- **Goal**: the documented `analyze` surface and the CLI agree — no documented-but-absent command.
- **Priority**: P2. **Independent test**: every doc/skill reference resolves to a real CLI invocation.
- **Requirements**: FR-011, SC-007. **Subtasks**: T050–T051.
- **Depends on**: none. **Prompt**: [tasks/WP06-analyze-surface-reconcile.md](./tasks/WP06-analyze-surface-reconcile.md)

### WP07 — Path-filtered doctrine/charter CI workflow (IC-08)

- **Goal**: fast isolated CI for `src/doctrine/**` + `src/charter/**` + `src/specify_cli/invocation/**`.
- **Priority**: P2. **Independent test**: a doctrine/charter PR triggers the workflow; a PR touching none of
  the filtered paths skips-with-green.
- **Requirements**: FR-012, SC-007. **Subtasks**: T060–T061.
- **Depends on**: none. **Prompt**: [tasks/WP07-path-filtered-ci.md](./tasks/WP07-path-filtered-ci.md)

### WP08 — Journey documentation (IC-09)

- **Goal**: document `apply`→`generate` two-step + empty-charter dispatch in the charter journey guides.
- **Priority**: P3 (documents delivered behaviour). **Independent test**: docs freshen check passes; the
  two-step is documented.
- **Requirements**: FR-009. **Subtasks**: T070–T071.
- **Depends on**: WP01, WP02, WP03. **Prompt**: [tasks/WP08-journey-docs.md](./tasks/WP08-journey-docs.md)

## Execution waves

- **Wave 1 (parallel, independent lanes)**: WP01 (MVP — ship first), WP02, WP03, WP04, WP05, WP06, WP07.
- **Wave 2 (gated)**: WP08 (after WP01/02/03).

## MVP

**WP01** — it stops the active P1 dispatch regression, is foundational, and is independently shippable.
WP01+WP02+WP03 together complete the full P1 usage journey (US1+US2).
