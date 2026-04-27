# Documentation Design

You are entering the **design** step. The previous steps produced `spec.md`
(scope and audience) and `gap-analysis.md` (prioritized gaps). The runtime
engine has dispatched this step with the `architect-alphonso` profile
loaded.

## Objective

Plan the documentation structure, Divio type assignments, and generator
configuration in enough detail that the generate step can produce artifacts
without re-deciding architecture choices.

## Expected Outputs

| Artifact | Path |
|---|---|
| Documentation plan | `kitty-specs/<mission-slug>/plan.md` |

The composition guard for this step requires `plan.md` to exist before the
mission can advance to `generate`.

## What `plan.md` Must Cover

1. **Divio type planning** — for each prioritized gap from
   `gap-analysis.md`, name the Divio type that closes it (`tutorial`,
   `how-to`, `reference`, `explanation`) and why. Keep the four types
   distinct: do not collapse a tutorial into a how-to.
2. **Generator selection** — for any reference documentation, choose the
   generator that matches the source language: `JSDoc` for JS/TS, `Sphinx`
   (with autodoc + napoleon) for Python, `rustdoc` for Rust. Document the
   config file path (e.g. `docs/conf.py`, `jsdoc.json`, `Cargo.toml`
   `[package.metadata.docs.rs]`).
3. **Navigation hierarchy** — the directory layout under `docs/` and the
   table-of-contents structure. Tutorials, how-tos, reference, and
   explanations should each be findable without prior knowledge of the
   tree.
4. **ADR-style decisions** — record any architecturally significant choice
   (toolchain, theme, hosting target, accessibility commitments) as a
   short decision block with context, decision, and consequences.
5. **Source-of-truth alignment** — for reference docs, name the source
   files (docstrings, type annotations, schema files) the generator will
   pull from, so reviewers can confirm the generated output matches.
6. **Risks and mitigations** — generator availability, version drift,
   build-time dependencies, and CI implications.

## Doctrine References

When this step dispatches via composition, the action doctrine bundle at
`src/doctrine/missions/documentation/actions/design/` is loaded into the
agent's governance context.

## Definition of Done

- `plan.md` exists and addresses every section above.
- Every HIGH-priority gap from `gap-analysis.md` is mapped to a concrete
  Divio-typed deliverable.
- Generator choices name a config path that the generate step can invoke
  without further decisions.
