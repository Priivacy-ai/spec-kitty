---
name: spec-kitty.analyze
description: Cross-artifact consistency and quality analysis
user-invocable: true
---
## Startup Upgrade Check

Run this at most once per active agent session before the first Spec Kitty command workflow.
If you already ran `spec-kitty upgrade --agent-check --json` in this session, reuse that result and skip this block.
Do not run or announce an upgrade check again for later Spec Kitty commands in the same session.
Otherwise, before continuing, run:

```bash
spec-kitty upgrade --agent-check --json
```

If JSON `action` is `none`, continue.
If `action` is `auto_upgrade`, run `upgrade_command` before continuing. If it fails, tell the user and continue with the current Spec Kitty version.
If `action` is `guidance`, show `upgrade_note` briefly, then continue.
If `action` is `prompt`, ask the user with the host-native question UI when available:

`Spec Kitty {latest_version} is available. You are on {installed_version}. Upgrade now?`

Use these choices:

1. Upgrade now (recommended) - record `upgrade_now`, run `upgrade_command`, then continue.
2. Always keep me up to date - record `always`, run `upgrade_command`, then continue.
3. Not now - record `not_now`, then continue.
4. Never ask again - record `never_ask`, then continue.

Record the selected choice before continuing:

```bash
spec-kitty upgrade --agent-choice <upgrade_now|always|not_now|never_ask> --agent-latest <latest_version> --json
```

If no host-native question UI is available, present the same four choices in plain text and wait for the user.
In non-interactive hosts, choose `not_now` and continue.


## User Input

The content of the user's message that invoked this skill (everything after the skill invocation token, e.g. after `/spec-kitty.<command>` or `$spec-kitty.<command>`) is the User Input referenced elsewhere in these instructions.

You **MUST** consider this user input before proceeding (if not empty).

## Goal

Identify inconsistencies, duplications, ambiguities, and underspecified items across the three core artifacts (`spec.md`, `plan.md`, `tasks.md`) before implementation. This command MUST run only after `/tasks` has successfully produced a complete `tasks.md`.

## Operating Constraints

**NON-REMEDIATING**: Do **not** modify `spec.md`, `plan.md`, `tasks.md`, WP files, source code, or any remediation target. The only permitted file mutation is persisting this command's report to `kitty-specs/<mission>/analysis-report.md` via `spec-kitty agent mission record-analysis`. Offer an optional remediation plan only after the report is persisted (user must explicitly approve before any follow-up editing commands would be invoked manually).

**Charter Authority**: The project charter (`/charter/charter.md`) is **non-negotiable** within this analysis scope. Charter conflicts are automatically CRITICAL and require adjustment of the spec, plan, or tasks—not dilution, reinterpretation, or silent ignoring of the principle. If a principle itself needs to change, that must occur in a separate, explicit charter update outside `/analyze`.

## Execution Steps

### 1. Initialize Analysis Context

Run `spec-kitty agent mission check-prerequisites --json --include-tasks --mission <mission-slug>` once from repo root and parse JSON for feature_dir, available_docs, target_branch, and base_branch. Derive absolute paths:

- SPEC = feature_dir/spec.md
- PLAN = feature_dir/plan.md
- TASKS = feature_dir/tasks.md

Abort with an error message if any required file is missing (instruct the user to run missing prerequisite command).

### 2. Load Artifacts (Progressive Disclosure)

Load only the minimal necessary context from each artifact:

**From spec.md:**

- Overview/Context
- Functional Requirements
- Non-Functional Requirements
- User Stories
- Edge Cases (if present)

**From plan.md:**

- Architecture/stack choices
- Data Model references
- Phases
- Technical constraints

**From tasks.md:**

- Task IDs
- Descriptions
- Phase grouping
- Parallel markers [P]
- Referenced file paths

**From charter:**

- Load `/charter/charter.md` for principle validation

### 3. Build Semantic Models

Create internal representations (do not include raw artifacts in output):

- **Requirements inventory**: Each functional + non-functional requirement with a stable key (derive slug based on imperative phrase; e.g., "User can upload file" → `user-can-upload-file`)
- **User story/action inventory**: Discrete user actions with acceptance criteria
- **Task coverage mapping**: Map each task to one or more requirements or stories (inference by keyword / explicit reference patterns like IDs or key phrases)
- **Charter rule set**: Extract principle names and MUST/SHOULD normative statements

### 4. Detection Passes (Token-Efficient Analysis)

Focus on high-signal findings. Limit to 50 findings total; aggregate remainder in overflow summary.

#### A. Duplication Detection

- Identify near-duplicate requirements
- Mark lower-quality phrasing for consolidation

#### B. Ambiguity Detection

- Flag vague adjectives (fast, scalable, secure, intuitive, robust) lacking measurable criteria
- Flag unresolved placeholders (TODO, TKTK, ???, `<placeholder>`, etc.)

#### C. Underspecification

- Requirements with verbs but missing object or measurable outcome
- User stories missing acceptance criteria alignment
- Tasks referencing files or components not defined in spec/plan

#### D. Charter Alignment

- Any requirement or plan element conflicting with a MUST principle
- Missing mandated sections or quality gates from charter

#### E. Coverage Gaps

- Requirements with zero associated tasks
- Tasks with no mapped requirement/story
- Non-functional requirements not reflected in tasks (e.g., performance, security)

#### F. Inconsistency

- Terminology drift (same concept named differently across files)
- Data entities referenced in plan but absent in spec (or vice versa)
- Task ordering contradictions (e.g., integration tasks before foundational setup tasks without dependency note)
- Conflicting requirements (e.g., one requires Next.js while other specifies Vue)

### 5. Severity Assignment

Use this heuristic to prioritize findings:

- **CRITICAL**: Violates charter MUST, missing core spec artifact, or requirement with zero coverage that blocks baseline functionality
- **HIGH**: Duplicate or conflicting requirement, ambiguous security/performance attribute, untestable acceptance criterion
- **MEDIUM**: Terminology drift, missing non-functional task coverage, underspecified edge case
- **LOW**: Style/wording improvements, minor redundancy not affecting execution order

### 6. Produce Compact Analysis Report

The report MUST begin with a structured **`analysis-findings/v1`** YAML frontmatter carrier, immediately followed by the human-readable Markdown body. The recorder computes the verdict and issue counts **from this carrier only** — report prose is presentation and is NEVER parsed for severity. Emit the carrier exactly in this shape:

```yaml
---
schema: analysis-findings/v1
findings:
  - id: A1            # stable finding id (same id used in the body table)
    severity: high    # one of: low | medium | high | critical (closed vocabulary; no other values)
    category: coverage
    summary: "One-line description of the finding."
counts: {critical: 0, high: 1, medium: 0, low: 0, info: 0}   # MUST equal the findings[] tally per severity
verdict_hint: blocked   # OPTIONAL author hint; the recorder COMPUTES the verdict — if your hint disagrees, recording FAILS LOUDLY
---
```

Carrier rules (binding — a violation makes `record-analysis` fail on the write path):
- `findings[].severity` MUST be one of `low`, `medium`, `high`, `critical`. Any other value fails schema validation.
- `counts` per-severity values MUST equal the actual `findings[]` tally. `info` is a presentation-only bucket and never affects the verdict.
- The verdict is derived from structure: **any `high` or `critical` finding → `blocked`; otherwise → `ready`.** Do not rely on prose wording.
- If you include `verdict_hint`, it MUST match the computed verdict, or recording fails loudly.
- A report with **no** findings emits `findings: []` and `counts: {critical: 0, high: 0, medium: 0, low: 0, info: 0}` → verdict `ready`.

After the closing `---`, draft the Markdown body with the following structure:

## Specification Analysis Report

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| A1 | Duplication | HIGH | spec.md:L120-134 | Two similar requirements ... | Merge phrasing; keep clearer version |

(Add one row per finding; generate stable IDs prefixed by category initial.)

**Coverage Summary Table:**

| Requirement Key | Has Task? | Task IDs | Notes |
|-----------------|-----------|----------|-------|

**Charter Alignment Issues:** (if any)

**Unmapped Tasks:** (if any)

**Metrics:**

- Total Requirements
- Total Tasks
- Coverage % (requirements with >=1 task)
- Ambiguity Count
- Duplication Count
- Critical Issues Count

### 7. Persist Report Artifact

Save the Markdown report body to `kitty-specs/<mission>/analysis-report.md` by running the recorder with a temp report file outside the repository checkout:

```bash
spec-kitty agent mission record-analysis --mission <mission-slug> --input-file <path-to-temp-report.md> --json
```

If your host supports piping reliable multiline stdin, this equivalent form is acceptable:

```bash
spec-kitty agent mission record-analysis --mission <mission-slug> --input-file - --json
```

The report file you pass MUST start with the `analysis-findings/v1` carrier from step 6. The recorder derives the verdict and counts from it; a malformed carrier (unknown severity, `counts` not matching the `findings[]` tally, or a disagreeing `verdict_hint`) makes the recorder fail loudly — fix the carrier and re-run.

Treat persistence failure as command failure. The command is not complete until the JSON response reports success and names `analysis-report.md`.

> **⚠️ Caution — Do not write `analysis-report.md` directly**
>
> The `analysis-findings/v1` carrier (step 6) is the **input format** for `record-analysis`,
> not the **persisted format**. `record-analysis` wraps the carrier in the outer-wrapper
> format (`artifact_type: spec-kitty.analysis-report`) that the implement gate accepts.
>
> Writing `analysis-report.md` directly — without piping through `record-analysis` — leaves
> the file in carrier format, which the implement gate rejects with `carrier_format_not_wrapped`.
> If this happens, recover by running:
> ```bash
> spec-kitty agent mission record-analysis --mission <mission-slug> --input-file analysis-report.md --json
> ```

### 8. Provide Next Actions

At end of report, output a concise Next Actions block:

- If CRITICAL issues exist: Recommend resolving before `/implement`
- If only LOW/MEDIUM: User may proceed, but provide improvement suggestions
- Provide explicit command suggestions: e.g., "Run /spec-kitty.specify with refinement", "Run /plan to adjust architecture", "Manually edit tasks.md to add coverage for 'performance-metrics'"

### 9. Offer Remediation

Ask the user: "Should all of these findings be addressed before moving on to implementation? I can suggest concrete remediation edits for the findings you want to resolve." (Do NOT apply edits automatically.)

## Operating Principles

### Context Efficiency

- **Minimal high-signal tokens**: Focus on actionable findings, not exhaustive documentation
- **Progressive disclosure**: Load artifacts incrementally; don't dump all content into analysis
- **Token-efficient output**: Limit findings table to 50 rows; summarize overflow
- **Deterministic results**: Rerunning without changes should produce consistent IDs and counts

### Analysis Guidelines

- **NEVER modify source/planning files** other than the required `analysis-report.md` persistence step
- **NEVER hallucinate missing sections** (if absent, report them accurately)
- **Prioritize charter violations** (these are always CRITICAL)
- **Use examples over exhaustive rules** (cite specific instances, not generic patterns)
- **Report zero issues gracefully** (emit success report with coverage statistics)

## Context

(User's invocation context is provided in the User Input section above.)
