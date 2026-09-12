# Pre-Merge Actions — `skill-trigger-routing-suite-01KYVRB9`

This mission's FR-005 acceptance criterion is recorded `pass` (see
`acceptance-matrix.json`), but that verdict is explicitly bounded: it
covers everything provable without pushing or opening a PR (all three
post-review workflow defects fixed and harness-proven), and it explicitly
excludes one thing — an actual GitHub Actions execution of the
`workflow_dispatch` trigger. That residue does not belong only in a JSON
evidence string; it is a tracked, required action here.

## Required post-merge confirmation

**A maintainer must manually dispatch
`.github/workflows/skill-trigger-routing.yml` via `workflow_dispatch` once
this mission lands on its target branch**, with `MUSTER_ENDPOINT` /
`MUSTER_API_KEY` configured as repository secrets, and confirm the run
produces the outcome described below. This is the only end-to-end
confirmation that has not happened yet.

### What it must show

Lifted verbatim from FR-005's acceptance-matrix evidence field (the
"real-CI half" of that criterion, as opposed to the local/harness-proven
half):

> These three fixes are local/harness-proven, not yet exercised by an
> actual GitHub Actions execution of workflow_dispatch (this pass's
> constraints excluded pushing/opening a PR); a maintainer dispatching the
> workflow for real is the remaining end-to-end confirmation, but the
> workflow can now reach every one of its own steps, which it previously
> could not.

Concretely, a successful confirming run must show, in the Actions log and
in the branch's git history:

1. The "Run behavioral trigger-routing manifest (FR-003/FR-004)" step
   completes and prints a captured exit code (0 or 1) rather than aborting
   the job — this is the `bash -e {0}` / exit-code-handling fix
   (`d3d71b9cb`).
2. The "Warm npm cache for pinned muster CLI (C-003)" step succeeds against
   the runner's genuinely cold `~/.npm` cache and the subsequent
   `npx --offline` invocation resolves `@garrison-hq/muster@1.2.1` without
   an `ENOTCACHED` failure — the offline-cache warm-up fix (`1db820696`).
3. The "Commit evidence artifact" step's `git push` succeeds (not a `403`)
   — the `contents: write` permissions fix (`016f3a601`) — and a new file
   lands under `conformance/skills/trigger-evidence/` on the branch the
   workflow ran on (not only in the workflow log).
4. The newly committed evidence artifact validates GREEN against
   `conformance/scripts/check-evidence-artifact-shape.mjs` and contains
   `runsErrored` (present, even if `0`) for every case (NFR-003).
5. The run's discrimination-control case reports `passed: false` with
   `runsErrored: 0` (a real, healthy-endpoint discrimination result per
   FR-004) — not a dead-endpoint false positive.

## Why this is required, not merely nice-to-have

Three real defects in this workflow (exit-code handling, npm-cache
warm-up, push permissions) were found and fixed *after* the workflow was
first authored, purely by local/harness reproduction — the workflow itself
was never actually run by GitHub Actions before this document was written.
A harness proves the fix logic; it does not prove GitHub Actions' own
runner environment, secrets wiring, and branch-protection interaction
behave as predicted. Until the dispatch above has actually happened and
produced the outcome described, FR-005's `pass` verdict rests on
harness-proof plus static analysis of `protect-main.yml`, not on a real
execution.

## Closing this out

Once the confirming run completes as described, record its run URL and the
five observations above in this mission's history (`spec-kitty agent
tasks add-history WP04 --note "..."`) and delete or strike through this
document's "Required post-merge confirmation" section — do not leave it
open-ended after the confirmation has actually happened.
