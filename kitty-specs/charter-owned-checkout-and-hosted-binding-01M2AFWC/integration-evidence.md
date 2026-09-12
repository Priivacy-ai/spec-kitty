# Integration and retrospective evidence

Canonical acceptance passed, followed by canonical merge into the PR branch
`codex/issue-4250-charter-owned-checkout`. Source integration is `04a849a`.
Both work packages are done. This is local feature integration; GitHub main and
the deployed CLI have not changed.

## Independent integration checks

- The two changed test modules ran together against the integrated checkout,
  without a cross-lane import override: 20 passed in 72.25 seconds.
- Integrated `make test-fast`: 1787 passed, 5 skipped, 5 warnings in 347.60 seconds.
  The command used the already populated project environment and four workers.
- Canonical `spec-kitty review --mode post-merge`: pass; both work packages done,
  no dead public symbols, no broad-exception findings, issue matrix present.
  The adjacent `mission-review-report.md` records this mechanical gate.
- Project runtime versions match the lock: Typer 0.24.2 and Click 8.3.3. The
  separately installed Spec Kitty tool reports Typer 0.27.2 and Click 8.5.0;
  that warning is not a mismatch in the tested project environment.
- Retrospective synthesis dry run proposed no automatic changes. No global
  doctrine or installed tool configuration was changed.

## Lessons beyond the generated retrospective

The generated retrospective describes runtime events, but omits several useful
findings from this work:

1. Review baselines must use the same declared command and source as the candidate.
   A 300-second review timeout was insufficient for an otherwise passing suite;
   this limitation is recorded in Spec Kitty issue 3046. Independent test logs
   supplement, rather than replace, the canonical gate.
2. Pytest's configured source path can override an environment-only `PYTHONPATH`.
   A cross-lane test initially loaded the old CLI and failed one test. An explicit
   pytest source override established the intended dependency during review;
   final integrated tests now pass without that override.
3. Source-level charter behavior and installed CLI bootstrap are different claims.
   Existing global asset bootstrap issue 4017 still needs resolution before the
   installed Factory consumer can be claimed verified. No global asset guard was
   bypassed to manufacture a successful bootstrap.
4. First explicit doctrine activation can discard previously effective defaults.
   Independent before/after resolver checks found this in five related projects.
   Their fixes were returned for review, and upstream issue 4253 records the CLI
   defect. Future activation reviews must compare resolved directive and procedure
   models, including all pack inputs, rather than only inspect new config entries.

These checks establish the CLI change's source readiness. Whole-program
adversarial review, production adoption, and Factory handoff remain separate
unfinished gates under SaaS issue 1711.
