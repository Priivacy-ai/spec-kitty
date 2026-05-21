# Canonical Producer Lint (AST CI rule)

**Mission ID**: `01KS4XX4KYDMQHWQMZT4C11TM2`
**Mission slug**: `canonical-producer-lint-01KS4XX4`
**Parent tracker**: [Priivacy-ai/spec-kitty#1248](https://github.com/Priivacy-ai/spec-kitty/issues/1248) — Regression-prevention #2 (AST lint against hand-rolled event dicts)
**Index**: [Priivacy-ai/spec-kitty#1247](https://github.com/Priivacy-ai/spec-kitty/issues/1247) — post-rc14→rc22 regression-prevention plan
**Drift-class epic**: [Priivacy-ai/spec-kitty#1198](https://github.com/Priivacy-ai/spec-kitty/issues/1198) — hand-rolled event dict drift
**Target / merge branch**: `main` (lane mission, separate per producer repo)

## Problem Statement

The rc14→rc22 chain (7+ release-candidate peelings between 2026-05-15 and 2026-05-21) had a single repeating root cause: producers constructing event dicts by hand instead of routing through the canonical `spec_kitty_events.lifecycle.*Payload` pydantic models. Today the doctrine ("producers go through canonical pydantic") exists in three places — `start-here.md`, `spec-kitty-mission-workflow.md` Non-negotiables, and the reviewer-renata persona — and reviewer attention is the only thing enforcing it.

That enforcement model fails predictably under load. We know this because it failed seven times in eight releases of a single launch gate. Doctrine alone is insufficient when the hand-rolled shape is locally indistinguishable from the canonical shape until the wire validator rejects it (after which the operator burns 30-60 minutes peeling the next RC).

The structural intervention this mission delivers is an **AST-level CI lint** that fails any PR introducing the hand-rolled producer shape, with a documented exemption mechanism for the rare legitimate case.

## Motivation

- **Move enforcement from human reviewer to CI.** Reviewer-renata is one process; CI is every process. A lint that runs on every PR catches the next slip immediately at the cheapest possible moment.
- **Make the doctrine auditable.** Every exemption requires an inline tracker reference. That converts "we'll allow this once" into a trackable issue with a path to closure. Today there is no audit trail for hand-rolled producers — the rc14→rc22 chain happened because each peeling introduced a new producer that nobody knew existed.
- **Operationalize C-007.** The C-007 entry in `spec-kitty-mission-workflow.md` Non-negotiables says "producers construct events via canonical pydantic". This mission gives that line teeth: when a PR violates it, CI says no.
- **Drift-class epic #1198 closure path.** Combined with intervention #1 (canary CI gate, sibling subagent #1247), interventions #3 (`*_SUNSET` constants) and #4 (cron canary), this lint is the structural piece that addresses the drift class at the producer site itself rather than at the wire.

## Scope

### In Scope

1. **Shared lint script in `spec-kitty/`.** `scripts/lint_canonical_producers.py` — a stand-alone Python script using the stdlib `ast` module (no new pip deps). Single source of truth invoked by every producer repo's CI. Supports `--paths` (default: scan current repo's `src/`, `scripts/`, `tests/`), `--exempt-pattern` (regex enforcing tracker references), and exit code 0/1.
2. **AST visitor covering three violation classes:**
   - **(a)** `ast.Dict` literal whose keys include both string literal `"event_type"` and `"payload"`, when the literal is not the argument to a call against a known-canonical constructor (`spec_kitty_events.lifecycle.*Payload`, `EventEnvelope(...)`, `StatusEvent(...)`).
   - **(b)** `ast.FunctionDef` whose annotated return type is `dict[str, Any]` (or `Dict[str, Any]`) AND whose body assembles a dict literal containing `event_type` or `payload`.
   - **(c)** `payload=` keyword argument in a call to any identifier ending in `emit_*`, `enqueue_*`, or named `send_event`, when the value is an inline `ast.Dict` literal (not a pydantic model instance, not a `.model_dump()` call, not a name bound to a canonical model).
3. **Exemption mechanism.** Inline comment `# canonical-producer-exempt: <tracker-ref> — <reason>` on the violating line (or the line opening the literal). Tracker reference required: matches `(<repo>)?#\d+` by default. Tokenize-based lookup so comments don't show up in the AST. Missing or malformed tracker → still a violation (lint logs the suggestion: "exemption is missing tracker ref").
4. **Unit tests at `tests/lint/test_canonical_producers.py`.** Positive cases (each of the three violations triggers), negative cases (canonical pydantic construction, `.model_dump()`, model-bound names — none trigger), exempt cases (valid tracker passes, invalid tracker still fails), self-scan (lint the spec-kitty repo itself and confirm clean or document exemptions).
5. **`spec-kitty` repo CI workflow.** New file `.github/workflows/canonical-producer-lint.yml` running `python scripts/lint_canonical_producers.py --paths src scripts tests` on PRs touching Python.
6. **`spec-kitty-saas` repo CI workflow.** New file `.github/workflows/canonical-producer-lint.yml`. Clones `spec-kitty` at a pinned SHA (HEAD-of-main at the time of writing — captured in the workflow env), runs the script against `spec-kitty-saas`'s producer-bearing trees (`src/` if present; otherwise the repo's top-level Python tree excluding `apps/` which is owned by sibling subagent #258). NEW workflow file distinct from #258's `sunset-check.yml`.
7. **`spec-kitty-end-to-end-testing` repo CI workflow.** Same shape as saas. NEW workflow file distinct from #61's `cron-canary.yml`.
8. **Existing-exemption audit.** As part of WP implementation, run the script against each repo on its current main and document any genuine exemption needed (including the rc22-attempt1 deliberately-broken-event fixture if it still exists).
9. **Workspace-doc patches handed to the orchestrator.** Propose (as diff in the return contract) a 5-line section in `spec-kitty-mission-workflow.md` citing the rule and the inline-exempt format, plus a one-line cross-reference in the C-007 Non-negotiable. The orchestrator owns that file — this mission does not write to it from inside the worktree.

### Out of Scope (Non-Goals)

- **Refactoring existing hand-rolled producers.** The rc14→rc22 chain canonicalized every producer that mattered for Phase 4. This mission adds enforcement on the assumption that the producer tree is already clean; if the existing-exemption audit surfaces a real hand-rolled site, it gets exempted with a tracker reference and a follow-up issue, not refactored as part of this PR.
- **Adding the rule to `spec-kitty-events`.** That repo IS the canonical source; every producer dict there is canonical by definition. Exempt by repo.
- **Touching `spec-kitty-saas/apps/`.** Sibling subagent #258 owns `apps/sync/*` and `.github/workflows/sunset-check.yml`. The lint workflow this mission adds is a separate file that targets non-`apps/` Python only.
- **Ruff plugin form.** The issue mentions "ruff custom rule, or a stand-alone Python script". This mission picks the stand-alone script for portability across repos that may not share ruff configuration and to avoid the new-pip-dep operating-rule concern. A future mission can wrap it as a ruff plugin if value emerges.
- **Frontend code.** No frontend surfaces in scope; frontend-freddy is not triggered.
- **SaaS DB mutation, ingress-limit changes, final 3.2.0 cut.** All operating non-negotiables hold.

## Mission Philosophy (binding for every WP)

1. **`ast` stdlib only, no new pip deps.** The script must run with the Python interpreter every CI runner already has. Hard rule from operating non-negotiables and from intervention #1's experience that adding deps to producer repos cascades.
2. **False-positive budget < 5%.** Measured against the existing spec-kitty / saas / e2e Python codebase. If the rule fires on a canonical site, the rule is wrong — tighten the AST match before opening the PR. (Stop condition from the brief.)
3. **Producers construct via canonical models — including in this mission's own implementation.** The doctrine this mission operationalizes applies to the mission itself. The lint script does not emit events; the workflows do not introduce new producer code. If anything in this mission's diff matches the lint, that's a self-test failure and must be fixed before PR.
4. **Single source of truth in `spec-kitty/`.** Saas and e2e repos do not duplicate the script. They clone or fetch it at a pinned SHA so the lint definition lives in exactly one place. When the rule changes, all three repos pick it up together by repointing the SHA.
5. **`spec-kitty next` is the only entry point for WP state advancement.** No direct `status.events.jsonl` edits.
6. **`unset GITHUB_TOKEN` before every `gh` write.**

## Doctrine and Architecture Contract

| Tactic / doctrine | Path | Binding scope |
|---|---|---|
| C-007 canonical-producer non-negotiable | `spec-kitty-mission-workflow.md` § Non-negotiables | The doctrine being operationalized. Mission proposes the C-007 cross-reference. |
| `secure-design-checklist` | `src/doctrine/tactics/shipped/secure-design-checklist.tactic.yaml` | Applied to the lint script: input validation on `--paths`, no shell escapes in tracker-ref regex, deterministic exit codes. |
| `function-over-form-testing` | `src/doctrine/tactics/shipped/testing/function-over-form-testing.tactic.yaml` | Every test in `tests/lint/`. Observable outcomes (exit code, finding text) only; no assertions on visitor internals. |
| Drift-class epic #1198 | GitHub issue | Reference, don't duplicate. This lint is one of four interventions the epic catalogs. |

## Acceptance Criteria

| # | Criterion | Verification |
|---|---|---|
| AC-01 | `scripts/lint_canonical_producers.py` exists in `spec-kitty/`, runnable as `python scripts/lint_canonical_producers.py --paths <dir>...`, exits 0 on clean tree, exits 1 on violations. | Unit test + CI invocation. |
| AC-02 | AST visitor catches violation class (a): dict literal with `event_type`+`payload` keys outside a canonical-model call. | Fixture in `tests/lint/test_canonical_producers.py` (positive + negative). |
| AC-03 | AST visitor catches violation class (b): `dict[str, Any]`-returning function body building an event-shaped dict. | Fixture (positive + negative). |
| AC-04 | AST visitor catches violation class (c): inline dict as `payload=` kwarg to `emit_*` / `enqueue_*` / `send_event`. | Fixture (positive + negative). |
| AC-05 | Inline `# canonical-producer-exempt: <tracker-ref> — <reason>` comment with a valid tracker (matches `(<repo>)?#\d+`) suppresses the finding. Invalid/missing tracker still fails. | Fixture (valid exempt + invalid exempt). |
| AC-06 | `.github/workflows/canonical-producer-lint.yml` exists in spec-kitty, runs on PR, invokes the script against `src/`, `scripts/`, `tests/`. | Workflow file present; PR run visible. |
| AC-07 | `.github/workflows/canonical-producer-lint.yml` exists in spec-kitty-saas, clones spec-kitty at a pinned SHA (recorded in workflow env), invokes the script against `src/` (or repo Python tree excluding `apps/`). | Workflow file present; SHA pinned. |
| AC-08 | Same as AC-07 for spec-kitty-end-to-end-testing. | Workflow file present; SHA pinned. |
| AC-09 | Self-scan of spec-kitty / saas / e2e at writing time documented in mission artifacts. Any genuine exemption gets a tracker-bearing inline comment in the relevant repo's source. | `kitty-specs/.../existing-exemptions-audit.md`. |
| AC-10 | Mission return contract proposes a 5-line addition to `spec-kitty-mission-workflow.md` citing the rule + exempt format, plus a one-line cross-ref in the C-007 Non-negotiable. Orchestrator applies (not this mission). | `workflow_doc_patch_diff` field in return contract. |
| AC-11 | No new pip deps in any of the three repos. stdlib `ast` only. | `pyproject.toml` / `requirements.txt` diff = 0 lines. |
| AC-12 | False-positive rate on existing canonical code < 5%. | Self-scan output. If above, tighten rule. |
| AC-13 | Producers in this mission's own diff (lint script, tests, workflows) introduce no new event-producing call sites. | Manual intent-vs-outcome inspection. |

## References

- Drift-class epic: [#1198](https://github.com/Priivacy-ai/spec-kitty/issues/1198)
- Regression-prevention index: [#1247](https://github.com/Priivacy-ai/spec-kitty/issues/1247)
- This issue: [#1248](https://github.com/Priivacy-ai/spec-kitty/issues/1248)
- C-007 doctrine: `/Users/robert/spec-kitty-dev/spec-kitty-20260518-205752-xgdiSS/spec-kitty-mission-workflow.md` § Non-negotiables
- rc22 closing evidence: [e2e#41 closing comment](https://github.com/Priivacy-ai/spec-kitty-end-to-end-testing/issues/41#issuecomment-4506163993)
- Sibling subagents (parallel execution coordination):
  - #1247 (canary CI gates) — same repo, different `.github/workflows/canary-gate.yml`
  - #258 (SaaS sunset constants) — saas repo, owns `apps/` and `.github/workflows/sunset-check.yml`
  - #61 (cron canary) — e2e repo, owns `.github/workflows/cron-canary.yml`
