# Documentation Generation

You are entering the **generate** step. The design step produced `plan.md`
naming Divio types, generator choices, navigation hierarchy, and source-of-
truth alignment. The runtime engine has dispatched this step with the
`implementer-ivan` profile loaded.

## Objective

Produce the documentation artifacts named in `plan.md`, faithful to the
plan's Divio assignments, generator choices, and navigation hierarchy. Do
not re-litigate planning decisions during this step; if the plan is wrong,
flag it and stop rather than improvising.

## Expected Outputs

| Artifact | Path |
|---|---|
| Documentation tree | `docs/**/*.md` (and generator-specific outputs) |
| Generator config | as named in `plan.md` (e.g. `docs/conf.py`) |

The composition guard for this step requires the documentation tree under
`docs/` to be non-empty before the mission can advance to `validate`.

## What This Step Must Produce

1. **Hand-authored Divio artifacts** — tutorials, how-tos, and explanations
   authored to the conventions of their type. A tutorial is a single
   linear path with a guaranteed outcome; a how-to solves a specific
   problem and assumes context; an explanation builds understanding and
   does not need to be actionable.
2. **Generator-driven reference** — invoke the generator named in
   `plan.md` (`sphinx-build`, `jsdoc`, `cargo doc`) with the configured
   flags. Capture the command and exit code in the mission's notes so
   reviewers can reproduce the build.
3. **Source-of-truth alignment** — reference outputs must be regenerable
   from the named source files. If docstrings or schemas are missing, fix
   the source rather than papering over with hand-written stubs.
4. **Navigation entry points** — landing pages, table-of-contents files,
   and cross-links so each Divio type is reachable from the docs root.
5. **Build verification** — confirm the generator runs to completion with
   zero new warnings beyond an established baseline.

## Doctrine References

When this step dispatches via composition, the action doctrine bundle at
`src/doctrine/missions/documentation/actions/generate/` is loaded into the
agent's governance context.

## Definition of Done

- Every artifact named in `plan.md` exists at its declared path.
- The generator named in `plan.md` builds cleanly; logs are captured.
- Reference content is traceable to source files; no hand-stubbed reference
  pages remain where a generator was promised.
- Navigation is wired so a reviewer can reach every Divio type from the
  docs root in three clicks or fewer.
