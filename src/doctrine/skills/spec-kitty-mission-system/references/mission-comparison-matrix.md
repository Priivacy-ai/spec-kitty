# Mission Comparison Matrix

Side-by-side comparison of the 4 built-in Spec Kitty missions.

## Overview

| | software-dev | research | plan | documentation |
|---|---|---|---|---|
| **Domain** | software | research | planning | documentation |
| **Steps** | 9 (DAG) | 6 (state machine) | 4 (linear) | 6 (phases) |
| **Has WP iteration** | Yes (implement, review) | Yes (implement, review) | No | Yes (implement, review) |
| **Has loops** | No | Yes (gather_more) | No | No |
| **Default** | Yes | No | No | No |

## Required Artifacts

| Artifact | software-dev | research | plan | documentation |
|---|:---:|:---:|:---:|:---:|
| `spec.md` | Required | Required | Required | Required |
| `plan.md` | Required | Required | Required | Required |
| `tasks.md` | Required | Required | Required | Required |
| `findings.md` | — | Required | — | — |
| `gap-analysis.md` | — | — | — | Required |
| `data-model.md` | Optional | — | — | — |
| `quickstart.md` | Optional | — | — | Optional |

## Step Sequences

### software-dev
```
discovery → specify → plan → tasks_outline → tasks_packages → tasks_finalize → implement → review → accept
```

### research
```
scoping → methodology → gathering ⇄ synthesis → output → done
```
Note: `gathering ⇄ synthesis` loop allows iterative evidence collection.

### plan
```
specify → research → plan → review
```

### documentation
```
discover → audit → design → generate → validate → publish
```

## Guards by Mission

### software-dev

| Transition | Guard |
|---|---|
| specify → plan | `artifact_exists("spec.md")` |
| plan → implement | `artifact_exists("plan.md")` AND `artifact_exists("tasks.md")` |
| implement → review | `all_wp_status("done")` |
| review → done | `gate_passed("review_approved")` |

### research

| Transition | Guard |
|---|---|
| scoping → methodology | `artifact_exists("spec.md")` |
| methodology → gathering | `artifact_exists("plan.md")` |
| gathering → synthesis | `event_count("source_documented", 3)` |
| synthesis → output | `artifact_exists("findings.md")` |
| output → done | `gate_passed("publication_approved")` |

### plan

No guards defined — transitions are manual.

### documentation

No guards in state machine — validation checks run during acceptance:
`all_divio_types_valid`, `no_conflicting_generators`, `templates_populated`,
`gap_analysis_complete`.

## Agent Context

| Mission | Personality |
|---|---|
| software-dev | TDD practices, library-first architecture, tests before code |
| research | Research integrity, methodological rigor, evidence documentation |
| plan | (No explicit agent context) |
| documentation | (No explicit agent context) |

## Recommended Tools

| Mission | Required | Recommended |
|---|---|---|
| software-dev | filesystem, git | code-search, test-runner, docker |
| research | filesystem, git | web-search, pdf-reader, citation-manager, arxiv-search |
| plan | (not specified) | (not specified) |
| documentation | (not specified) | (not specified) |

## When to Choose Each Mission

| Scenario | Mission |
|---|---|
| Build a new feature with code changes | software-dev |
| Fix a bug or refactor existing code | software-dev |
| Evaluate technology options before deciding | research |
| Conduct a literature review or competitive analysis | research |
| Plan a project roadmap or architecture | plan |
| Design a system without implementing it yet | plan |
| Write tutorials, API docs, or how-to guides | documentation |
| Fill gaps in existing documentation | documentation |
| Document a specific feature or component | documentation |
