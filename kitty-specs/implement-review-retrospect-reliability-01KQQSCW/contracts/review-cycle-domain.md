# Contract: Review-Cycle Domain Boundary

## Scope

This contract covers #960, #962, #963, and fix-mode rejection context loading. It defines the shared invariant boundary used before status/state pointers change.

## Proposed Module

`src/specify_cli/review/cycle.py`

## Required Capabilities

### Create Rejected Review Cycle

Input:

- Repository root path.
- Mission slug.
- WP id.
- Feedback source file path.
- Reviewer or actor identity.
- Optional affected files.

Output:

- Written review-cycle artifact path.
- Canonical `review-cycle://...` pointer.
- `ReviewResult` for a rejected outbound `in_review` transition.

Failure behavior:

- Missing feedback file fails before artifact write.
- Empty feedback fails before artifact write.
- Invalid artifact frontmatter fails before pointer/result return.
- Pointer resolution failure fails before status transition.

### Validate Review Artifact

Input:

- `review-cycle-N.md` path.

Output:

- Parsed artifact metadata.

Required validation:

- YAML frontmatter exists.
- Required fields are present and non-empty.
- Cycle number is positive.
- Verdict is valid for the caller's requested path.
- Mission and WP identity match the requested context.

### Generate Canonical Pointer

Input:

- Mission slug.
- WP task-file slug.
- Review cycle artifact filename.

Output:

- `review-cycle://<mission>/<wp-task-file-slug>/review-cycle-N.md`

Rules:

- New rejected review state must persist this pointer form.
- Path traversal or malformed pointer segments are invalid.

### Resolve Pointer

Input:

- Repository root path.
- Pointer string.

Output:

- Resolved file path, warning list, and pointer kind.

Rules:

- `review-cycle://` resolves under `kitty-specs/<mission>/tasks/<wp-slug>/`.
- `feedback://` resolves legacy git-common-dir feedback paths and reports a deprecation warning.
- Operational sentinels resolve to no artifact and no warning.
- Unknown or missing pointers fail safely for mutation paths and warn for prompt-rendering paths.

## Adapter Requirements

- `src/specify_cli/cli/commands/agent/tasks.py` uses the boundary for `--to planned --review-feedback-file`.
- `src/specify_cli/cli/commands/agent/workflow.py` uses the boundary for fix-mode pointer resolution.
- `src/specify_cli/review/artifacts.py` remains the artifact dataclass/parser unless implementation discovers a small validation helper belongs there.
- `src/specify_cli/status/emit.py` remains the only status event persistence gateway.

## Regression Coverage

- #960: Reject from `in_review` with feedback file succeeds without manual `review_result`.
- #960: Invalid feedback fails before state mutation.
- #962: New persisted pointer is canonical `review-cycle://...`.
- #962: Legacy `feedback://` pointer resolves with deprecation warning.
- #963: Missing required frontmatter is rejected before pointer persistence.
- Fix-mode: focused rejection context loads from canonical pointer and ignores `action-review-claim` sentinel.
