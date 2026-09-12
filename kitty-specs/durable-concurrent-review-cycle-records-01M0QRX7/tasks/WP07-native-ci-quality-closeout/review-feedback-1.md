# WP07 Review Feedback — Cycle 1

## Verdict

REJECTED. Native platform evidence is complete, but the recorded 95% value was
not enforced by the command that produced it.

## Evidence

- Hosted native run `32730562924` is valid and complete: Ubuntu job
  `97441630642`, macOS job `97441630431`, and Windows job `97441630612` each
  collected and passed the exact three SC-004 nodes.
- CI Quality run `32730563173` completed successfully.
- Diff-coverage job `97445991966` ran its critical-path command with
  `--fail-under=90`, but that command reported no covered changed lines.
- The reported `262` changed lines, `11` missing lines, and `95%` came from the
  separate full-diff advisory command, which omits `--fail-under=90` and is
  followed by `|| true`.

Therefore T031 and WP07's Definition of Done are not yet proven. The history
entry must not describe the full-diff percentage as enforced.

## Required correction

Within WP07 ownership:

1. Extend the existing critical-path diff-coverage include set in
   `.github/workflows/ci-quality.yml` to cover the mission's durability-critical
   production modules changed by this mission. Prefer the exact command/review
   module paths over converting the repository-wide advisory step into a new
   blanket policy.
2. Preserve the existing `origin/${{ github.base_ref }}` comparison and
   `--fail-under=90` enforcement. Do not weaken, bypass, or relabel the advisory
   command.
3. Update the fail-closed architecture/routing tests only if required by the
   existing parser contract, remaining within WP07's declared owned files.
4. Obtain a fresh completed CI Quality diff-coverage job whose enforced
   critical-path invocation reports the mission's covered changed lines and
   exits successfully at or above 90%.
5. Record the new run, job, report inputs, covered/missing lines, percentage,
   and enforced exit result through `spec-kitty agent tasks add-history`.

Native Linux/macOS/Windows evidence does not need redesign; rerunning it after
the workflow-only correction may occur automatically and must remain green if
triggered.

