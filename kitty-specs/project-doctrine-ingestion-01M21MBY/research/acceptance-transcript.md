# Project doctrine ingestion acceptance

Reviewer: reviewer-renata (resolved through `spec-kitty agent profile show`).
Date: 2026-09-08 UTC. Source: dev CLI from the v3.2.6.1-based PR branch.

A fresh throwaway Git repository and isolated HOME were used. SaaS sync was disabled
with `SPEC_KITTY_ENABLE_SAAS_SYNC=0`. `spec-kitty` below denotes the source checkout's
`.venv/bin/spec-kitty`. No project artifact was activated individually.

The five scaffolded YAML files had all TODOs replaced with `Acceptance project doctrine marker`.
The profile used canonical `collaboration.operating-procedures: [acceptance-procedure]`,
directive references as `{code, name, rationale}`, and tactic/styleguide references as
`{id, rationale}`. The glossary seed contained lowercase `acceptance handoff`, definition
`Transfer of operational responsibility.`, confidence `1.0`, and status `active`.

## Command transcript

```text
$ git init
exit: 0

$ git -c user.name=Acceptance -c user.email=acceptance@example.test commit --allow-empty -m "Initial acceptance fixture"
exit: 0

$ spec-kitty init --ai claude --non-interactive .
exit: 0

$ spec-kitty charter interview --defaults
exit: 0

$ spec-kitty charter generate
exit: 0

$ spec-kitty charter synthesize
exit: 0

$ spec-kitty charter new procedure acceptance-procedure
exit: 0

$ spec-kitty charter new tactic acceptance-tactic
exit: 0

$ spec-kitty charter new directive ACCEPTANCE_DIRECTIVE
exit: 0

$ spec-kitty charter new styleguide acceptance-styleguide
exit: 0

$ spec-kitty charter new agent_profile acceptance-profile
exit: 0

$ spec-kitty charter validate .kittify/doctrine
exit: 0

$ spec-kitty charter activate agent-profile acceptance-profile --cascade all
exit: 0

$ spec-kitty charter list --json
exit: 0

$ spec-kitty charter activate agent-profile acceptance-profile --cascade all --resynthesize
exit: 0

$ spec-kitty charter context --action implement --mission-type software-dev --include procedure:acceptance-procedure
exit: 0

$ spec-kitty charter context --action implement --mission-type software-dev --include agent-profile:acceptance-profile
exit: 0

$ spec-kitty charter context --action implement --mission-type software-dev
exit: 0

$ spec-kitty charter status
exit: 0

$ spec-kitty glossary validate .kittify/glossaries/team_domain.yaml
exit: 0

$ spec-kitty glossary list --scope team_domain
exit: 0

$ spec-kitty glossary show "acceptance handoff"
exit: 0
```

## Verified output and stored artifacts

```text
5 artifact(s) passed validation.
Activated: acceptance-profile, acceptance-procedure, acceptance-tactic,
           ACCEPTANCE_DIRECTIVE, acceptance-styleguide (verified in charter list JSON)
Procedure include: Steps: Acceptance project doctrine marker
Profile include: all four referenced IDs rendered
Default implement context: ACCEPTANCE_DIRECTIVE listed
Artifacts: 5 (live doctrine files: 5)
Provenance: 5 visible sidecar(s)
Manifest coverage: 5/5
Synthesized DRG: FRESH
Glossary seed: Valid (1 terms)
Glossary list: acceptance handoff (team_domain)
Glossary show: Transfer of operational responsibility.
```

The manifest contains all five authored source paths and `built_in_only: false`.
Each provenance sidecar has the matching artifact URN, source path and content hash.
The generic empty-seed provenance prose is replaced with project-authored provenance.

```text
PASS: all five activated by cascade
PASS: procedure text rendered
PASS: profile renders all four references
PASS: default context contains project directive
PASS: manifest includes five artifacts
PASS: manifest not built-in only
PASS: provenance meaningful for five artifacts
PASS: manifest contains five authored source paths
PASS: status project DRG
PASS: glossary list term
PASS: glossary show definition
```

All 22 commands exited zero. Two initial harness assertions incorrectly compared a
normalized directive filename to its case-preserving URN and counted derived graph.yaml
as a sixth authored source. Corrected assertions were run against the same final
transcript and filesystem state; all eleven checks passed. No product rerun was used
to hide a failing result.
