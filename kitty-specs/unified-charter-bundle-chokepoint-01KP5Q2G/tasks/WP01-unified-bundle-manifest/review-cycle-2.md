---
affected_files: []
cycle_number: 2
mission_slug: unified-charter-bundle-chokepoint-01KP5Q2G
reproduction_command:
reviewed_at: '2026-04-14T11:48:43Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP01
---

**Issue 1**: `bundle validate` does not enforce the contract's git-tracking requirement for tracked files. In [src/specify_cli/cli/commands/charter_bundle.py](/Users/robert/spec-kitty-dev/spec-kitty-charter-14-April/spec-kitty/.worktrees/unified-charter-bundle-chokepoint-01KP5Q2G-lane-a/src/specify_cli/cli/commands/charter_bundle.py:134), `_classify_paths()` only checks `Path.exists()`. The contract requires tracked files to both exist and be tracked via `git ls-files`. I reproduced this with a temporary repo where `.kittify/charter/charter.md` exists but is never `git add`ed; `validate --json` still exits `0` with `bundle_compliant: true`. Fix by checking git tracking status for `manifest.tracked_files` and by adding an integration test that fails when `charter.md` is untracked.

**Issue 2**: The validator does not enumerate all undeclared files under `.kittify/charter/` as informational warnings. In [src/specify_cli/cli/commands/charter_bundle.py](/Users/robert/spec-kitty-dev/spec-kitty-charter-14-April/spec-kitty/.worktrees/unified-charter-bundle-chokepoint-01KP5Q2G-lane-a/src/specify_cli/cli/commands/charter_bundle.py:85), `_enumerate_out_of_scope_files()` explicitly ignores any undeclared file that is not in the hard-coded warning map or one of the two prefixes. The contract says to enumerate files under `.kittify/charter/` that are not declared by the manifest and treat them as warnings. I reproduced this with `.kittify/charter/custom-notes.txt`; the command still returns success with `out_of_scope_files: []` and `warnings: []`. Fix by warning on every undeclared file under `.kittify/charter/` and extend the CLI tests to cover an arbitrary ancillary file, not just `references.yaml` / `context-state.json`.

**Issue 3**: The checked-in occurrence artifact does not satisfy the verifier required by the WP. [kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/occurrences/WP01.yaml](/Users/robert/spec-kitty-dev/spec-kitty-charter-14-April/spec-kitty/kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/occurrences/WP01.yaml:4) uses a mapping-shaped `categories` payload, but `python scripts/verify_occurrences.py kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/occurrences/WP01.yaml` fails with `WP01: 'categories' is empty or missing`. Fix the artifact to the verifier's expected schema and rerun the verifier until it exits `0`.

**Issue 4**: The WP's required strict type-check command is not green. Running `mypy --strict src/charter/bundle.py src/specify_cli/cli/commands/charter_bundle.py` fails in this workspace, so the Definition of Done is not met. Fix the typing surface so that this exact command passes in the repository as required by the WP prompt.

**Downstream note**: WP02 depends on WP01. After fixing the above and re-landing WP01, the downstream lane work should be rebased before WP02 review continues.
