---
affected_files: []
cycle_number: 1
mission_slug: ox-alpha-spec-reviewer-01M0N82A
reproduction_command:
reviewed_at: '2026-08-22T20:03:44Z'
reviewer_agent: user
wp_id: WP02
---

# WP02 review cycle 1 — changes requested

Audience: WP02 implementer.

## Blockers

1. **Consent-bound bytes can diverge from the externally transmitted specification.** `SpecSnapshot` accepts independent `payload` and `text` fields ([preflight.py](../../../../../.worktrees/ox-alpha-spec-reviewer-01M0N82A-lane-b/src/specify_cli/spec_review/preflight.py):131-138), while `build_prompt()` sends only `snapshot.text` ([prompt.py](../../../../../.worktrees/ox-alpha-spec-reviewer-01M0N82A-lane-b/src/specify_cli/spec_review/prompt.py):31-37). The manifest commits the digest of `payload`, not an independently supplied `text`. A direct local probe constructed unequal values and showed `payload-mismatch-transmitted=True`. Make one canonical immutable buffer authoritative (or enforce an exact UTF-8-derived text invariant in `SpecSnapshot`) and add a teeth test that mismatched bytes/text cannot reach the prompt.

2. **`SpecReviewRun` does not enforce the `spec-review-run/v1` status contract.** Although annotated as `ReviewStatus`, `SpecReviewRun` accepts the string `"not-in-contract"` with an empty finding list and a diagnostic ([models.py](../../../../../.worktrees/ox-alpha-spec-reviewer-01M0N82A-lane-b/src/specify_cli/spec_review/models.py):215-218,247-261). The local probe printed `unknown-status-accepted=True`. This contradicts the schema enum. Validate the runtime enum/status, require the schema-required summary as a non-optional final value, and cover unknown status, missing summary, all allowed failure states, and summary consistency.

3. **Manifest-wide consent drift is not implemented or proven.** `confirm_and_load_spec()` recomputes transport, route, rubric and schema solely from the already-captured disclosure ([preflight.py](../../../../../.worktrees/ox-alpha-spec-reviewer-01M0N82A-lane-b/src/specify_cli/spec_review/preflight.py):172-180), so it only observes a changed spec file. The sole drift test mutates/deletes `spec.md` ([test_preflight.py](../../../../../.worktrees/ox-alpha-spec-reviewer-01M0N82A-lane-b/tests/specify_cli/spec_review/test_preflight.py):48-63). Implement a recheck API or enforce one immutable send bundle so later route/transport/rubric/schema values cannot diverge, and add parameterized teeth tests for every manifest component with a zero-send spy.

4. **Required validation gates do not pass.** In the fixed local environment, `uv run --no-sync ruff check src/specify_cli/spec_review tests/specify_cli/spec_review` fails on trailing whitespace in `test_parser.py:41`; strict mypy fails on the optional `summary` accessed at `test_models.py:81-83`; targeted pytest passes 15 tests but reports only **86%** total branch coverage (models 84%, parser 77%), below the required 90%. Remove the four `# type: ignore` suppressions in the owned tests rather than relying on them, fix the lint/type defects, and add the missing boundary/schema/scanner/privacy cases until the stated coverage gate is met.

5. **Required scanner and contract teeth coverage is incomplete.** The scanner test exercises only token assignment, email and PEM ([test_preflight.py](../../../../../.worktrees/ox-alpha-spec-reviewer-01M0N82A-lane-b/tests/specify_cli/spec_review/test_preflight.py):66-89), not credential URLs, phones, corporate markers, entropy strings, decoys, or Unicode/BOM behavior required by T010. The parser tests also do not exercise malformed JSON/UTF-8, bool-as-integer, all field bounds, or raw-source-safe failures. Add production-path tests; do not construct synthetic result objects in place of parser/preflight behavior.

6. **Dead-code checklist fails at this WP boundary.** `parse_review_response*()` has no production caller outside its own module; the production grep finds only definitions in `src/specify_cli/spec_review/parser.py`. Add an owned production composition caller or explicitly move/defer this uncalled surface to the WP that owns its service integration before re-review.

## Non-blocking baseline evidence

The four PlantUML pre-review collection errors are **baseline/environmental, not introduced by WP02**: `tests.docs.test_plantuml_invoke`, `test_plantuml_no_egress_corpus`, `test_plantuml_render`, and `test_plantuml_sandbox_negative` all fail on Windows because `scripts/docs/plantuml_invoke.py` imports unavailable `fcntl`. That script has identical blob `d4a416a5a0bea4962a701a072fa2bbc14ffe03a4` at planning base `d1503d79` and current HEAD, and neither it nor the four tests is in either WP02 commit. This finding is recorded rather than masked; it is outside WP02 owned-file scope and requires separate cross-platform remediation.

## Re-review evidence required

- Red→green commits still show the test-first sequence, including reversion-sensitive manifest and snapshot-invariant cases.
- `uv run --no-sync ruff check src/specify_cli/spec_review tests/specify_cli/spec_review` exits 0.
- `uv run --no-sync mypy --strict src/specify_cli/spec_review tests/specify_cli/spec_review` exits 0 without blanket or test-local ignores.
- The four targeted test files pass and targeted branch coverage is at least 90%.
- Report the 4 PlantUML failures separately as unchanged baseline/environment evidence; do not relabel them as a WP02 regression.
