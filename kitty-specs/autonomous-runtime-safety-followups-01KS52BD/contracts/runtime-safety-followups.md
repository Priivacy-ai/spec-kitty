# Contract: Autonomous Runtime Safety Follow-ups

## Retrospect Synthesize

Command:

```bash
spec-kitty agent retrospect synthesize --mission <slug> [--apply] [--json]
```

Contract:

- Accepts every top-level field written by `spec-kitty retrospect create`.
- Default mode remains dry-run/non-mutating.
- `--apply` retains existing proposal application behavior.
- Missing record, malformed YAML, and OS I/O errors retain existing error
  classifications.

## Decision Closure

Command:

```bash
spec-kitty agent decision resolve <decision_id> --mission <slug> --final-answer "<answer>"
```

Contract:

- Resolving a `deferred` decision succeeds when an explicit final/default answer
  is provided.
- Closed decisions are not reported as `DEFERRED_WITHOUT_MARKER` if their inline
  marker has been removed.
- `decision open`, `decision defer`, and `decision cancel` public contracts are
  unchanged.

## Finalize Tasks Ownership Validation

Command:

```bash
spec-kitty agent mission finalize-tasks --mission <slug> --validate-only --json
spec-kitty agent mission finalize-tasks --mission <slug> --json
```

Contract:

- A WP `owned_files` entry under `kitty-specs/` fails validation unless an
  explicit mission-branch routing model is implemented.
- JSON errors include a stable code plus offending `wp_id` and `path`.
- Full finalization and validate-only mode enforce the same rule.

## Bulk-edit Planning Pre-flight

Command:

```bash
spec-kitty agent action implement WP## --mission <slug> --agent <agent>
```

Contract:

- If spec text triggers bulk-edit inference and the claimed WP owns
  `occurrence_map.yaml` or a mission planning artifact path, the warning is
  informational for that WP.
- Active rewrite WPs still require the existing bulk-edit state and occurrence
  map coverage.
- `--acknowledge-not-bulk-edit` remains available for true non-bulk-edit cases.

## Lane Computation

Command:

```bash
spec-kitty agent mission finalize-tasks --mission <slug> --json
```

Contract:

- WPs with overlapping `owned_files` collapse into the same execution lane when
  required for safety.
- Disjoint upstream workstreams are not collapsed solely because they feed a
  downstream fan-in WP.
- Fan-in synchronization is represented by lane dependencies.
- `lanes.json` remains consumable by existing merge flow.

## Focused-PR Documentation

Trigger:

```text
TARGET_BRANCH_NOT_SYNCHRONIZED
```

Docs must describe:

- Runtime-suggested focused branch command:
  `git switch -c kitty/pr/<slug>-to-main kitty/mission-<slug>`
- Push command:
  `git push -u origin kitty/pr/<slug>-to-main`
- PR into `main`.
- Direct mission-branch PR as the simpler path when the mission branch already
  has the lane merge.
- Do not reset, rebase, or force-push as remediation.
- Prefer squash-merge for autonomous orchestration commit piles.
