# Issue matrix — modular-per-package-ci-01M025GV

One row per issue referenced in the mission's PRIMARY-partition artifacts (spec.md, plan.md, tasks.md, research.md). Non-terminal `in-mission` verdicts must be resolved to a terminal verdict before the mission's `done`/merge transition.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #3447 | Modular per-package CI (kernel/doctrine/packs own workflows → Sonar) + automated asset/prompt regeneration | in-mission | Mission umbrella. Spec/plan/tasks/research approved; WP01 kernel POC (lane-a 3a46ee2a0, partial — guard-delegation folded into WP03), WP02 regen tool delivered + independently reviewed (lane-b 012f7c456, 242356332). WP03–WP06 in progress. Resolve to terminal before merge. |
| #3379 | Source-prompt edit → silent generated-copy drift → late parity-gate failure | in-mission | Fixed by WP02: `spec-kitty regen [--check]` self-service regeneration of the 168 committed fixtures (lane-b 012f7c456, review nits 242356332; independent review APPROVE; `regen --check` reports 168 fresh; 319 fixture+regen tests green). CI automation of the fix lands in WP04. |
