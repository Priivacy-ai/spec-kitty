# Tracer: Approach — verdict-seam-boundary-hardening-01KZG179

> What we tried, what worked, what we'd do differently. Append during implementation.

## Planning phase

- **Research-squad-first grounding.** Before writing the spec, dispatched a 3-lens read-only research squad (paula-patterns on façade/guard, debugger-debbie on the arbiter crash, researcher-robbie on parity/infra) to verify the issue-body claims against `upstream/main` tip. This paid off: the issue bodies undercounted the façade surface (10 symbols not 8), the consumer set (8 not 6), and missed 4 collateral submodule-object imports and the guard-widening blast radius. Grounding before speccing prevented planning against stale numbers.
- **Pre-planning point-cut squad (brownfield/campsite).** A 2-lens squad (foldable-issue/conflict sweep + campsite/Sonar census) ran before the plan. It surfaced two strong on-theme folds (#3217, #3216), relationship drift (#2275 now closed by merged #3211), rebase-collision watch (PR #3247/#3209), and a per-file campsite ledger that became the per-WP campsite steps.
- **Squad point-cut cadence chosen:** pre-spec research → pre-planning brownfield → (planned) post-tasks anti-laziness → pre-merge aggregate.
- **Commit/push on point-cuts** (operator directive): spec committed+pushed to fork `origin`; planning point-cut next.

## What worked / to reconsider

- Read-only fencing of scout agents (no `git checkout`/`stash`, shared working tree) avoided the HEAD-detach hazard.

## Implementation phase

_(append as encountered)_
