# scripts/

Development and maintenance scripts for the spec-kitty project.

Scripts here are **not part of the distributed package**. They exist to support
local development workflows, CI chores, and repository maintenance tasks that
do not belong in the installed CLI.

## Subdirectories

- `chores/` - Routine maintenance tasks such as glossary compilation and artifact
  generation. Run these when updating source artifacts that have a derived output
  (e.g., compiling glossary markdown into Contextive YAML).

- `git-hooks/` - Hook scripts installed into `.git/hooks/` during project setup.
  See the project constitution for the canonical list of required hooks and their
  enforcement rules.

- `release/` - Scripts supporting the release pipeline. Invoked by CI workflows;
  do not run manually unless you understand the full release process (see
  `CONTRIBUTING.md`).

- `tasks/` - Task management helpers for the Spec Kitty CLI development workflow.
  These complement the `spec-kitty agent` commands during active feature work.

## Usage

All scripts assume they are run from the **repository root**. Most require the
project virtual environment to be active.

Scripts are standalone executables or importable modules as documented in their
own docstrings. If a script has CI usage, the corresponding workflow step in
`.github/workflows/` is the authoritative invocation example.
