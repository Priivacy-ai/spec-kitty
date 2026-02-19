# Architecture Experiments

This directory captures architecture-level hypotheses that need evidence before we commit to an ADR or implementation direction.

## Purpose

Use experiments to answer questions like:

- "Is our current approach measurably wasteful?"
- "Will this optimization preserve quality?"
- "Which option gives better tradeoffs under realistic workloads?"

An experiment is not a permanent decision. It is a structured way to collect evidence.

## When to Use This Directory

Create an experiment when:

- The team has a strong theory but no hard data yet.
- Multiple options are plausible and tradeoffs are unclear.
- A change can materially affect cost, latency, quality, or developer ergonomics.

Use an ADR instead when:

- The architectural decision is ready to be recorded as accepted/proposed/superseded.
- Alternatives and consequences are already clear enough to commit.

## Lifecycle

| Status | Meaning |
|--------|---------|
| `Proposed` | Hypothesis and plan drafted |
| `Running` | Instrumentation and execution in progress |
| `Analyzed` | Results collected and interpreted |
| `Promoted` | Outcome converted into ADR/spec implementation work |
| `Closed` | Experiment completed with no immediate follow-up |

## File Naming Convention

`YYYY-MM-DD-short-hypothesis-title.md`

Examples:

- `2026-02-16-context-window-efficiency-and-budgeting.md`
- `2026-02-20-provider-routing-cost-vs-latency.md`

## Required Sections

Every experiment document should include:

1. Problem statement
2. Hypothesis
3. Success and failure criteria
4. Metrics and instrumentation plan
5. Experiment phases
6. Risks and mitigations
7. Decision gate (what happens next)

## Index

| Experiment | Status | Focus |
|------------|--------|-------|
| [2026-02-16-context-window-efficiency-and-budgeting](2026-02-16-context-window-efficiency-and-budgeting.md) | Proposed | Reduce unnecessary prompt context while preserving task outcomes |
