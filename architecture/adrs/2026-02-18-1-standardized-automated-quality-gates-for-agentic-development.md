# Standardized Automated Quality Gates for Agentic Development

**Filename:** `2026-02-18-1-standardized-automated-quality-gates-for-agentic-development.md`

**Status:** Accepted

**Date:** 2026-02-18

**Deciders:** Spec Kitty maintainers

**Technical Story:** Improve early deterministic compliance checks for agent-driven workflows

---

## Context and Problem Statement

Spec Kitty increasingly relies on agentic implementation flows. When quality conventions are not enforced automatically at the earliest checkpoints, issues are discovered late in review or CI, causing expensive rework and context switching.

We already run Python-centric checks in CI and provide basic pre-commit guardrails (encoding + agent directory protection), but we lack:
- consistent commit-message linting aligned with repository conventions;
- standardized Markdown style checks for staged/changed documentation;
- a repeatable quality-gate pattern that can be propagated to generated projects.

This gap reduces deterministic feedback for agents and maintainers and increases manual cleanup effort.

## Decision Drivers

* Catch low-cost issues at the earliest enforcement points (file change, commit, CI).
* Reduce review churn and late-cycle rework.
* Provide deterministic checks that agents can satisfy without human interpretation.
* Align contributor behavior with repository standards.
* Reuse the same quality-gate model across Spec Kitty and downstream projects.

## Considered Options

* Keep current guardrails and rely on review/CI only.
* Add optional documentation and guidelines, but no hard gates.
* Standardize automated gates across pre-commit, commit-msg, and CI checks (CHOSEN).

## Decision Outcome

**Chosen option:** "Standardize automated gates across pre-commit, commit-msg, and CI checks", because it provides the highest leverage point for quality enforcement while remaining deterministic and tool-friendly for both humans and agents.

### Consequences

#### Positive

* Commit message quality is validated before commits are finalized.
* Markdown style issues are detected on staged or changed files before merge.
* CI enforces the same policy in shared infrastructure.
* Agents get faster, clearer, and lower-cost feedback loops.
* The pattern can be reused in generated projects through hook templates and doctrine guidance.

#### Negative

* Slightly higher local tooling requirements (Node + npx for commitlint/markdownlint checks).
* More gate failures during early adoption until contributor habits align.
* Additional maintenance for hook scripts and lint configuration.

#### Neutral

* Existing Python quality gates remain in place and are not replaced.
* Markdown style rules are intentionally pragmatic to avoid high migration cost.
* Checks focus on changed/staged files to avoid immediate whole-repository remediation.

### Confirmation

The decision is validated when:
- commit messages violating conventions are blocked locally and in CI;
- Markdown issues are caught before merge on changed files;
- maintainers report reduced rework for commit hygiene and docs style;
- generated projects can adopt the same hooks and policy with minimal customization.

Confidence level: high.

## Pros and Cons of the Options

### Keep current guardrails and rely on review/CI only

Maintain only existing encoding/agent checks and Python quality checks.

**Pros:**

* No additional tooling changes.
* No new contributor friction.

**Cons:**

* Late issue detection remains common.
* Manual review burden remains high.
* Agent loops remain less deterministic.

### Add optional documentation and guidelines, but no hard gates

Document expected commit and Markdown conventions without enforcement.

**Pros:**

* Low implementation effort.
* Flexible for contributors.

**Cons:**

* Compliance remains inconsistent.
* Drift and rework continue.
* Weak feedback quality for automated agents.

### Standardize automated gates across pre-commit, commit-msg, and CI checks (CHOSEN)

Enforce commit message and Markdown quality through hook templates and CI.

**Pros:**

* Earliest practical issue capture.
* Deterministic, machine-checkable policy.
* Better scaling for multi-agent development.

**Cons:**

* Requires maintaining additional lint integration.
* Introduces setup/runtime dependencies for local checks.

## More Information

- Hook templates: `src/doctrine/templates/git-hooks/`
- CI pipeline: `.github/workflows/ci-quality.yml`
- Initiative tracker impact: `docs/development/tracking/indoctrinated-kitty/`
