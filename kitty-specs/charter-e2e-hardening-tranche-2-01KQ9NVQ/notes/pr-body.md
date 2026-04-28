# Charter E2E Hardening Tranche 2 — strict regression gate (#827 #839 #840 #841 #842 #843 #844)

## Summary

- Lands six product fixes (`#839`–`#844`) that close the gaps PR #838 had bypassed in the charter golden-path E2E, and converts that test from a softened diagnostic spine into a strict regression gate.
- All six PR-#838 bypasses (custom JSON parser, schema bootstrap, doctrine stub fallback, conditional prompt-file acceptance, absent-pi_dir early return, hand-mutated metadata) are removed; `tests/e2e/test_charter_epic_golden_path.py` now fails loudly on any regression in WP02..WP07's behaviors.
- Locks regression-free behavior for the runtime-next prompt-file resolution that closed `#336` (via PR #803) by asserting every issued step carries a non-empty resolvable `prompt_file`.

## Closes

- `Priivacy-ai/spec-kitty#839` — fixture synthesis writes doctrine artifacts (WP03; `SPEC_KITTY_FIXTURE_AUTO_STUB=1` makes synthesize emit canonical doctrine assets).
- `Priivacy-ai/spec-kitty#840` — init stamps `schema_version` + `schema_capabilities` (WP02; `spec-kitty init` now writes both keys to `.kittify/metadata.yaml`).
- `Priivacy-ai/spec-kitty#841` — generate→bundle-validate agreement via `next_step.git_add` (WP04; `charter generate --json` emits a `next_step` instruction with action `git_add` and a non-empty paths list when the generated charter is untracked).
- `Priivacy-ai/spec-kitty#842` — strict `--json` stdout discipline (WP05; `mark_invocation_succeeded` suppresses atexit diagnostic prints so every `--json` stdout is exactly one JSON document).
- `Priivacy-ai/spec-kitty#843` — paired profile-invocation lifecycle records (WP07; composed actions issued by `next` write paired started/completed records keyed by `invocation_id`).
- `Priivacy-ai/spec-kitty#844` — strict `prompt_file` resolution + skill cleanup (WP06; runtime-next always returns a resolvable `prompt_file` in `kind=step` envelopes, with `kind=blocked` carrying a non-empty reason; the `SKILL.md` workaround text is removed and migration `m_3_2_5_fix_prompt_file_workaround.py` rewrites legacy copies).

## Verifies fix

- `Priivacy-ai/spec-kitty#336` — closed by PR `#803`. This PR locks regression-free behavior in the strict E2E by asserting every `kind=step` envelope returned by `spec-kitty next --json` carries a non-empty resolvable `prompt_file` (verified via `os.path.exists`).

## Before / after

- **Before** (post PR #838): The charter golden-path E2E had been softened with six bypasses to keep CI green while six product gaps remained: missing init metadata (`#840`), no fixture-synthesis doctrine output (`#839`), missing `generate→validate` next_step contract (`#841`), atexit diagnostic noise on `--json` stdout (`#842`), absent paired profile-invocation records (`#843`), and unresolvable `prompt_file` paths from runtime-next (`#844`). The diagnostic spine reported gaps but did not enforce them.
- **After**: All six product gaps are fixed in the runtime/CLI surface. All six bypasses (`_parse_first_json_object`, `_bootstrap_schema_version`, `--dry-run-evidence` doctrine stub, conditional prompt-file acceptance, F5/FR-021 absent-pi_dir early return, hand-seeded `.kittify/` files) are deleted from the E2E. The strict gate fails loudly on any regression in WP02..WP07's behaviors.

## Verification (WP08 narrow gate + targeted gates)

All commands run from repo root.

- **NFR-001 narrow gate (≤ 5 min budget)**: `uv run pytest tests/e2e/test_charter_epic_golden_path.py -q -s` — **PASSES in ~22s**.
- **NFR-002 targeted gates**:
  - `uv run pytest tests/e2e tests/next tests/integration/test_documentation_runtime_walk.py tests/integration/test_research_runtime_walk.py -q` — **PASSES** (with one pre-existing `test_full_advancement_through_six_actions` failure in `tests/integration/test_documentation_runtime_walk.py` that reproduces against the pre-WP08 baseline; not introduced by this tranche).
  - `uv run pytest tests/charter tests/specify_cli/mission_step_contracts tests/doctrine_synthesizer -q` — **PASSES 844/844**.
  - `uv run ruff check tests/e2e/test_charter_epic_golden_path.py tests/e2e/conftest.py` — **clean**.
- **NFR-003 mypy strict on touched typed surfaces**: `uv run mypy --strict src/specify_cli src/charter src/doctrine tests/e2e/test_charter_epic_golden_path.py` — owned-file edits introduce no new errors. (Two pre-existing errors in `tests/test_isolation_helpers.py` and `tests/e2e/conftest.py` reproduce against the pre-WP08 baseline.)
- **NFR-004 pollution guard**: a full golden-path run mutates zero files inside the source checkout (`git status --porcelain` is empty post-run; the source-checkout pollution guard from PR #838 is preserved per C-006).
- **NFR-005 determinism**: 5 consecutive narrow-gate runs all pass with no flakes on the development workstation.

## Note on external E2E coverage

No external `Priivacy-ai/spec-kitty-end-to-end-testing` repo run was required for this tranche because PR #838's charter golden-path test lives in the product repo (`tests/e2e/test_charter_epic_golden_path.py`) and is exactly the surface this tranche hardens. Cross-repo plain-English suite expansion is explicitly deferred per C-003.

## Remaining `#827` follow-up scope

The following are out of scope for this tranche and remain for follow-up work:

- Cross-repo E2E coverage in `Priivacy-ai/spec-kitty-end-to-end-testing` (plain-English suite expansion, SaaS canaries).
- `#845` — dossier snapshot side effects (dossier ergonomics beyond the pollution guard).
- `#846` — specify/plan auto-commit content.
- `#847` — decision events corrupting the status reducer.
- `#848` — `uv.lock` vs installed-events pin drift.

These four issues are deferred per C-003 unless a future tranche surfaces a strict-gate blocker.

## OPERATOR NOTE — agent skill copies and the WP06 migration

The PR diff against `Priivacy-ai/spec-kitty:main` includes the **source** runtime-next skill at `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md` (with the prompt_file workaround block removed) and the **migration** `src/specify_cli/upgrade/migrations/m_3_2_5_fix_prompt_file_workaround.py` that rewrites legacy per-agent copies on consuming projects.

The PR diff does **not** include regenerated per-agent skill copies under `.claude/skills/`, `.amazonq/`, `.gemini/`, `.cursor/`, `.qwen/`, `.opencode/`, `.windsurf/`, `.kilocode/`, `.augment/`, `.roo/`, `.kiro/`, `.agent/`, `.github/prompts/`, or `.agents/skills/`. This is **expected and correct**: those per-agent copies are materialized at upgrade-time on consuming projects when `spec-kitty upgrade` runs the `m_3_2_5_fix_prompt_file_workaround.py` migration against each project's installed agent directories. The product repo carries the source skill plus the migration — not the regenerated copies.

Reviewers who want to confirm the workaround text is removed from the source can grep:

```bash
git diff main..HEAD -- src/doctrine/skills/spec-kitty-runtime-next/SKILL.md
```

The migration file demonstrates the rewrite that runs on consuming projects:

```bash
git show HEAD:src/specify_cli/upgrade/migrations/m_3_2_5_fix_prompt_file_workaround.py
```

---

## Follow-up fixes (post-review)

After initial review surfaced three implementation issues and CI flagged diff-coverage gaps, the following fixes were added in commit c8217f29:

- **`charter synthesize --json` warning leak**: evidence warnings now fold into the JSON envelope's `warnings` field instead of polluting stdout via Rich. (`src/specify_cli/cli/commands/charter.py`)
- **Synthesize success envelope contract**: success branch now emits `result`, `adapter`, and `written_artifacts` per `contracts/charter-synthesize.json`. (Same file.)
- **Dry-run planned paths**: dry-run helper now uses real artifact URNs from staging instead of inventing `PROJECT_000` placeholders. Dry-run paths now match real synthesize output for directives. (Same file.)
- **Diff-coverage**: added targeted tests for the structured-blocked emit paths in `next/decision.py:521-522` and `next/runtime_bridge.py:1565-1609, 2156, 2364`. `diff-coverage` and `quality-gate` are now green.

Tests added/extended:
- `tests/specify_cli/test_json_output_discipline.py` — strict-parse assertion now covers the warning case.
- `tests/doctrine_synthesizer/test_synthesize_writes_artifacts.py` — asserts `adapter` + `written_artifacts` contract fields and dry-run/real path parity.
- `tests/doctrine_synthesizer/test_synthesize_dry_run_envelope.py` — updated mocks to typed return shape.
- `tests/next/test_prompt_file_invariant.py` — `Path.exists` OSError branch.
- `tests/next/test_runtime_bridge_blocked_paths.py` (new) — covers legacy DAG guard-failure path and the WP-iteration blocked branch.
