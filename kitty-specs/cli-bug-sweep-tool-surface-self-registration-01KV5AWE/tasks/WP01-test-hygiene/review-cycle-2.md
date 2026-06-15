---
affected_files: []
cycle_number: 2
mission_slug: cli-bug-sweep-tool-surface-self-registration-01KV5AWE
reproduction_command:
reviewed_at: '2026-06-15T11:32:28Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP01
review_artifact_override_at: "2026-06-15T11:42:13Z"
review_artifact_override_actor: "operator"
review_artifact_override_wp_id: "WP01"
review_artifact_override_reason: "Review cycle 2 passed: T001 xfail removed, T002 docstring states mismatched-mid8 invariant, T003 covers both mission_branch_name and lane_branch_name pathological cases. Issue-matrix filled. --skip-review-artifact-check: cycle-2 fix pass, review-cycle-2.md is implementation context not a rejection record."
---

**Issue 1 (T002 — Docstring does not state the required invariant)**

The acceptance criterion for T002 is: `_human_slug_for_mid8_branch` has a docstring stating the invariant. The WP task file specifies the invariant text as: "Strip the embedded mid8 only when it matches mission_id's mid8; mismatched mid8 is not stripped."

The pre-existing docstring at `src/specify_cli/lanes/branch_naming.py` line 135 reads:

    """Return human slug without numeric prefix or duplicate own mid8 suffix."""

This describes the happy-path return value but says nothing about the guard keying specifically on `mission_id`'s mid8, nor that a mismatched embedded mid8 is not stripped. A future maintainer reading only this docstring would not understand why the pathological test (T003) exists or what invariant it guards. The implementer reported this as "docstring confirmed present" and made no change to the file — the diff shows zero changes to `branch_naming.py`.

**Required fix:** Update the docstring on `_human_slug_for_mid8_branch` to include the invariant about the mismatched case. Either replace or extend the existing docstring. The wording in the task spec is a good starting point:

    """Strip the embedded mid8 only when it matches mission_id's mid8; mismatched mid8 is not stripped.

    Returns the human slug without numeric prefix and without a trailing mid8
    that duplicates this mission's own mid8.
    """

Do not change the function body.

---

**Issue 2 (T003 — lane_branch_name pathological case not covered)**

The WP task file at Subtask T003 step 4 states: "Also cover `lane_branch_name` with the same pathological slug if the existing test suite covers it — confirm both functions have coverage." The existing suite has `test_lane_branch_name_does_not_double_existing_mid8_suffix` (line 98) which covers the matching-mid8 case for `lane_branch_name`. Therefore a parallel pathological test was warranted and required.

The new test added by T003 (`test_mission_branch_name_does_not_strip_different_mid8_suffix`, line 280) covers only `mission_branch_name`. No analogous test for `lane_branch_name` with a mismatched mid8 suffix was added.

**Required fix:** Add a second test in `tests/core/test_branch_naming_human_slug.py` covering the `lane_branch_name` pathological case, for example:

    def test_lane_branch_name_does_not_strip_different_mid8_suffix() -> None:
        """lane_branch_name with mismatched slug mid8 does not strip the embedded token."""
        slug = "my-feature-AAAA1111"
        ulid = "01KV3NGSDCJ272573TF6T6NWDW"  # mid8 = 01KV3NGS
        result = lane_branch_name(slug, "lane-a", mission_id=ulid)
        # "AAAA1111" != "01KV3NGS" so it is NOT stripped; own mid8 is appended normally.
        assert result == "kitty/mission-my-feature-AAAA1111-01KV3NGS-lane-a"

Verify `ruff check` and `mypy --strict` pass on the file after both fixes.
