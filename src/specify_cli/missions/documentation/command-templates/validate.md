# Documentation Validation

You are entering the **validate** step. The generate step produced the
documentation tree under `docs/` and the generator-driven reference
outputs. The runtime engine has dispatched this step with the
`reviewer-renata` profile loaded.

## Objective

Verify the documentation against the quality gates declared in `plan.md`
and the discovery brief in `spec.md`. Produce a canonical audit report that
records which gates passed, which failed, and what remediation is required
before publication.

## Expected Outputs

| Artifact | Path |
|---|---|
| Validation audit report | `kitty-specs/<mission-slug>/audit-report.md` |

The composition guard for this step requires `audit-report.md` to exist
before the mission can advance to `publish`. The audit report is the
canonical evidence the publish step relies on; it must be honest about
failures, not optimistic.

## Quality Gates to Evaluate

1. **Divio adherence** — each artifact matches the conventions of its
   declared type. Tutorials are linear and outcome-guaranteed; how-tos
   are problem-shaped; reference is exhaustive and regenerable;
   explanations build understanding without prescribing action.
2. **Completeness** — every HIGH-priority gap from `gap-analysis.md` is
   closed by a concrete artifact under `docs/`. Note any remaining gaps
   explicitly so they are not silently accepted.
3. **Accessibility** — heading hierarchy is sensible, alt text is present
   on diagrams and screenshots, code blocks declare a language for
   syntax highlighting, link text is descriptive (no bare "click here").
4. **Source-of-truth alignment** — sample reference pages are spot-checked
   against the source files declared in `plan.md`; reference content
   tracks the source and does not drift.
5. **Build health** — the generator builds cleanly with zero new
   warnings; broken cross-links and missing anchors are reported.
6. **Risk review** — risks named in `plan.md` are revisited; new risks
   surfaced during generate are recorded.

## Doctrine References

When this step dispatches via composition, the action doctrine bundle at
`src/doctrine/missions/documentation/actions/validate/` is loaded into the
agent's governance context.

## Definition of Done

- `audit-report.md` exists and records a pass/fail verdict for every gate
  above with cited evidence.
- Every failed gate carries a remediation owner and is either fixed
  in-step or explicitly deferred with operator sign-off.
- The report is honest enough that the publish step can rely on it as
  the canonical statement of release readiness.
