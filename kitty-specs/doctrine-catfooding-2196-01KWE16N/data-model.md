# Data Model — Doctrine Catfooding

The "entities" here are doctrine/charter artifacts, not runtime records. This models what is authored/edited and how the pieces relate.

## Entities

### DoctrineArtifact
- **Fields**: `kind` (directive | tactic | styleguide | toolguide | paradigm | procedure | template), `id`/`urn` (e.g. `directive:DIRECTIVE_043`), `title`, `body`, inline DRG refs (`requires`/`suggests`/`refines`), `enforcement` (directives only — for §1 this MUST NOT be `required`).
- **Location**: `src/doctrine/<kind>/built-in/<slug>.<kind>.yaml`.
- **Invariants**: passes the per-kind schema loader; passes `doctor doctrine --json` (contributes 0 skipped/invalid); passes the legacy-terminology guard; no two WPs own the same file (C-003).

### DRG (Doctrine Reference Graph)
- **Fields**: nodes (artifact URNs), edges (`requires`/`suggests`/`refines`/`specializes_from`).
- **Location**: `src/doctrine/graph.yaml` (generated, 2927 lines) — regenerated via the canonical CLI `spec-kitty doctrine regenerate-graph` (which composes the `drg/migration/extractor.py:generate_graph` extractor + calibrator); never the raw `python extractor.py` (no `__main__`) and never hand-edited.
- **Invariants**: cycle-free, no dangling/duplicate edges (`tests/doctrine/drg/test_shipped_graph_valid.py`, `test_drg_relations.py`); freshness (regenerated matches committed). **Single owner = wiring WP** (PD-2).

### Charter
- **Components**: activation state (`.kittify/config.yaml` `activated_<kind>` lists) ← `charter activate`; interview answers (`.kittify/charter/interview/answers.yaml` `selected_directives`/`selected_tactics`/…) ← `charter interview` / manual mirror; rendered bundle (`.kittify/charter/charter.md` + `references.yaml`) ← `charter generate`.
- **Invariants (C-007)**: activate precedes generate; the rendered reference closure is non-shallow (NFR-003); reconciles existing v1.1.5 (no clobber).

### AgentProfile
- **Fields**: `directives:` list (which directives the profile loads).
- **Location**: `src/doctrine/agent_profiles/built-in/*.agent.yaml`.
- **Invariant**: a new directive is inert for agent sessions until referenced here (C-002c). **Single owner = wiring WP.**

### SourceDoc
- **Location**: `docs/development/quality-and-tech-debt-standing-orders.md` (FR-001, new).
- **Invariants**: page-inventory row + 50-180 char frontmatter description (docs-freshness); faithful human-readable mirror of the activated set (SC-005).

## Section → artifact inventory (authoring targets)

| § | New artifacts | Extended/referenced artifacts | Directive # (PD-1) |
|---|---|---|---|
| §1 | cadence styleguide/paradigm | `adversarial-squad-deployment.procedure`, `brownfield-onboarding.paradigm` | — (not a directive) |
| §2 | frozen-baseline-ratchet tactic | `025-boy-scout-rule`, `planning-and-tracking.styleguide` (+024/040 xref) | — |
| §3 | tracer procedure + 3-file template | — | — |
| §4 | — | `041-tests-as-scaffold-not-friction`, `testing-principles.styleguide`, `test-first-bug-fixing.procedure` | — (extends 041) |
| §5a | arch-gate directive + gate-build tactic | — | **043** |
| §5b | post-merge-adjudication procedure | — | — |
| §6 | canonical/unification directive + tactic + terminology toolguide | — | **044** |
| §7 | PRs-only/read-intent directive(s) + worktree/no-version tactic (≥2 WPs) | `clean-linear-commit-history.tactic` (ref) | **045** (+046 if 2nd) |
| §8 | ownership-leeway + role-separation (styleguide ext + small tactic) | `planning-and-tracking.styleguide`, `tiered-standards.styleguide` (ref), mission-step prompts (align) | — |

Reserved-but-likely-unused: 047-049 (returned if no directive is warranted).

## Relationships / flow

```
SourceDoc ──mirrors──▶ activated DoctrineArtifacts
DoctrineArtifact ──inline edges──▶ DRG (graph.yaml, regen by wiring WP)
DoctrineArtifact ──referenced by──▶ AgentProfile.directives (wired by wiring WP)
DRG + activation(config.yaml) + answers.yaml ──charter generate──▶ Charter(charter.md + references.yaml)
```

## Lifecycle / ordering

`Foundation → {new-artifact conversions ∥ extend conversions} → wiring (profiles + single graph regen + DRG tests) → capstone (activate→mirror→generate→doctor)`.
