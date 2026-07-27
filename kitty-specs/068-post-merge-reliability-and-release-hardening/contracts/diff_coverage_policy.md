# Contract: WP03 Diff-Coverage Policy Validation

**Owns**: FR-010, FR-011, FR-012

## Verification-first protocol

WP03 is **verification-first**. The order is locked:

1. **FR-010** runs first: a written validation report against current `ci-quality.yml` behavior on a representative large PR sample. **No code changes yet.**
2. After the validation report, a fork:
   - **FR-011** fires if validation shows current main already satisfies the policy intent → close #455 with evidence, tighten docs/messages, no workflow change.
   - **FR-012** fires if validation shows residual mismatch → adjust the workflow so only the intended critical-path surface produces hard failures.

WP03 SHALL NOT modify `.github/workflows/ci-quality.yml` before authoring the validation report.

## Validation report (FR-010)

**File**: `kitty-specs/068-post-merge-reliability-and-release-hardening/wp03-validation-report.md`

The report contains the `DiffCoverageValidationReport` dataclass rendered as markdown:

```markdown
# WP03 Diff-Coverage Validation Report

**Validated at commit**: `<sha>`
**Workflow path**: `.github/workflows/ci-quality.yml`
**Sample PR**: #<id> — <description>

## Critical-path threshold (enforced)
- Threshold: <X>%
- Current behavior: hard-fails if diff coverage on critical-path files < <X>%
- Critical-path file list source: `<config-path-or-pattern>`

## Full-diff threshold (advisory)
- Threshold: <Y>%
- Current behavior: emits a separate report; never hard-fails

## Findings
- [ ] Critical-path enforce/advisory split is correctly implemented
- [ ] Hard-fail surfaces match the intended critical-path file set
- [ ] Advisory report is clearly labeled as advisory in CI output
- [ ] Large PRs that meet critical-path coverage but miss full-diff coverage pass the build

## Decision
**[ ] close_with_evidence** — current main already satisfies the policy intent. Issue #455 closed with link to this report.
**[ ] tighten_workflow** — residual mismatch found. Workflow adjusted per FR-012.

## Rationale
<one paragraph>
```

## FR-011 path: close with evidence

If the validation report's `decision` is `close_with_evidence`:

1. WP03 closes issue #455 with a comment linking to:
   - This validation report
   - The current `ci-quality.yml` line ranges that implement the enforce/advisory split
   - The example large PR that passes correctly under the current policy
2. WP03 tightens documentation and CI output messages so future contributors immediately understand which surface is enforced and which is advisory:
   - Add a "Diff coverage policy" section to `docs/explanation/` (or wherever CI policy is documented)
   - Update CI step names in `ci-quality.yml` to be self-explanatory (e.g., "diff-coverage (critical-path, enforced)" vs "diff-coverage (full-diff, advisory)")
3. **No workflow logic changes.**

## FR-012 path: tighten workflow

If the validation report's `decision` is `tighten_workflow`:

1. WP03 modifies `.github/workflows/ci-quality.yml` so:
   - The hard-fail surface is exactly the intended critical-path file set
   - Full-diff coverage runs as advisory only
   - CI output identifies enforced vs advisory surfaces explicitly
2. WP03 adds an integration test (or a curated synthetic PR test) demonstrating that a large PR meeting critical-path coverage but missing full-diff coverage now passes.
3. WP03 closes issue #455 with a comment linking to the workflow diff and the new test.

## Test surface

| Test | FR | Asserts |
|---|---|---|
| `test_validation_report_authored` | FR-010 | the validation report file exists and has all required sections |
| `test_decision_is_recorded` | FR-010 | the report has exactly one of `close_with_evidence` or `tighten_workflow` checked |
| `test_validation_report_close_path_populated` | FR-010, FR-011 | when `decision == close_with_evidence`, the report has a non-empty rationale (≥ 50 chars) AND either an empty findings list (no policy mismatches) or each finding carries an explicit "satisfied by" rationale. This is the **content gate** that prevents WP03 from shipping a vacuous report. |
| `test_close_with_evidence_does_not_modify_workflow` | FR-011 | if the decision is `close_with_evidence`, `git diff main -- .github/workflows/ci-quality.yml` is empty |
| `test_tighten_workflow_passes_large_pr_sample` | FR-012 | (only if FR-012 fires) a synthetic large PR meeting critical-path but missing full-diff passes |

## NFR-006 interaction

NFR-006 is pinned to commit `7307389a`. If WP03 takes the FR-012 path and changes the threshold or include-list, NFR-006 is re-evaluated against the post-WP03 threshold rather than blocking WP03's change. This carve-out is documented in NFR-006's body in `spec.md`.
