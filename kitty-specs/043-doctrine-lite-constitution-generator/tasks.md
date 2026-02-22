---
feature_slug: 043-doctrine-lite-constitution-generator
feature_title: Doctrine-Lite Deterministic Constitution Generator
total_work_packages: 6
total_subtasks: 24
lane: planned
---

# Work Packages

## WP01 Constitution Simplification

- [ ] Remove `selected_agent_profiles` from doctrine selection schema.
- [ ] Remove agent config schemas and exports.
- [ ] Remove `agents.yaml` from sync outputs and CLI status reporting.
- [ ] Update tests for new 3-file sync output.

## WP02 Deterministic Catalog + Resolver

- [ ] Add doctrine catalog loader module.
- [ ] Validate selected directives/paradigms/template set.
- [ ] Keep tool validation strict.
- [ ] Update resolver diagnostics/tests.

## WP03 Constitution Generate Command

- [ ] Add `constitution generate` command.
- [ ] Support `--force`, `--mission`, `--json`.
- [ ] Emit deterministic markdown.
- [ ] Trigger sync post-write.

## WP04 Prompt Governance Context

- [ ] Add governance context rendering helper.
- [ ] Inject context into template prompts.
- [ ] Inject context into WP prompts.
- [ ] Add prompt-builder tests.

## WP05 Doctrine Asset Slimming

- [ ] Remove scaffold-only doctrine directories.
- [ ] Add concrete paradigm artifact(s) if missing.
- [ ] Ensure docs/schema references remain valid.

## WP06 Validation

- [ ] Run updated constitution unit tests.
- [ ] Run CLI constitution command tests.
- [ ] Run runtime doctor + next prompt tests.
- [ ] Verify no regressions in selected broader suites.
