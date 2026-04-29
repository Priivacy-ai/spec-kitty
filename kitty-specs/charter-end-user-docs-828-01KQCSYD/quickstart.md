# Implementer Quickstart: Charter End-User Docs Parity (#828)

**Audience**: The agent or person executing the Generate phase work packages.
**Date**: 2026-04-29

---

## Context

This mission produces documentation, not product code. Every work package writes or updates Markdown files in `docs/` using the DocFX format (toc.yml hierarchy). No source Python changes are needed.

The spec is at:
`kitty-specs/charter-end-user-docs-828-01KQCSYD/spec.md`

The IA design is at:
`kitty-specs/charter-end-user-docs-828-01KQCSYD/data-model.md`

The gap analysis is at:
`kitty-specs/charter-end-user-docs-828-01KQCSYD/research.md`

---

## Branch and Version

- **Branch**: `docs/charter-end-user-docs-828`
- **spec-kitty version**: Use `uv run spec-kitty` (3.2.0a5), not the ambient PATH binary.
- **Machine rule**: If any command touches hosted auth, tracker, or sync, prepend `SPEC_KITTY_ENABLE_SAAS_SYNC=1`.

---

## Verifying CLI Content

Before writing any CLI reference content, run the real `--help` output:

```bash
# Always use uv run spec-kitty, not spec-kitty from PATH
uv run spec-kitty charter --help
uv run spec-kitty charter interview --help
uv run spec-kitty charter generate --help
uv run spec-kitty charter synthesize --help     # doctrine synthesis (primary synthesis verb)
uv run spec-kitty charter resynthesize --help   # partial resynthesis
uv run spec-kitty charter status --help
SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run spec-kitty charter sync --help  # syncs charter.md to YAML config (NOT SaaS push)
uv run spec-kitty charter lint --help
uv run spec-kitty charter bundle --help         # verify this exists before writing a section for it
uv run spec-kitty charter bundle validate --help
uv run spec-kitty next --help
uv run spec-kitty profiles --help
uv run spec-kitty profiles list --help
uv run spec-kitty ask --help
uv run spec-kitty advise --help
uv run spec-kitty do --help
uv run spec-kitty profile-invocation --help
uv run spec-kitty profile-invocation complete --help
uv run spec-kitty mission --help
uv run spec-kitty glossary --help
uv run spec-kitty retrospect --help
uv run spec-kitty retrospect summary --help
uv run spec-kitty agent retrospect synthesize --help
uv run spec-kitty agent decision --help
```

If a subcommand returns `Error: No such command`, do not include a section for it in the reference — note it as "not yet available" or omit it. `agent retrospect synthesize` currently defaults to dry-run, requires `--mission <mission>`, and mutates only with `--apply`; do not document a `--dry-run` flag unless `--help` shows one.

---

## Writing a New Page

1. Create the file at the path in `data-model.md`.
2. Add a DocFX frontmatter block (see existing pages for format, e.g. `docs/how-to/setup-governance.md`).
3. Register the page in the appropriate `toc.yml` (see Section 5 of `data-model.md`).
4. Remove the `TODO: register in docs nav` marker if migrating from an existing stub.
5. Verify no `[TODO: ...]` placeholders remain before marking the WP complete.

---

## Updating an Existing Page

1. Read the file first (`Read` tool or `cat`).
2. Identify stale sections (e.g., "Spec Kitty 2.x" prerequisite in `setup-governance.md`).
3. Update in place — do not rewrite sections that are still accurate.
4. Add a "See also" block at the bottom linking to the new related pages.

---

## Terminology Note

Use **charter bundle** (not "doctrine bundle") when referring to the bundle concept or CLI group, and use `charter bundle validate` when documenting validation commands. Use this consistently in all pages to match what users see in `--help` output.

Use **charter synthesize** (not "charter context") when describing doctrine synthesis. `charter context` is a different subcommand with a different purpose — do not use it as a synonym for synthesis.

Use **retrospect** (not "retro") for the retrospective command group: `spec-kitty retrospect summary`, `spec-kitty agent retrospect synthesize`.

---

## Invariants to Maintain

These must be true in every page you produce:

| Invariant | How to check |
|---|---|
| `charter.md` is the only human-edited governance file | State this explicitly when describing the governance layer |
| No false claim that custom mission retrospective is deferred | Verify against `mission-runtime.yaml` first |
| Documentation mission phases match `mission-runtime.yaml` | Run `grep -r 'documentation' src/specify_cli/missions/documentation/` |
| CLI flags match `--help` output | Never assume — always run the command |
| Compact-context limitation acknowledged | Check if issue #787 is open/closed; link or omit accordingly |
| No `TODO: register in docs nav` remains | Grep before marking WP done: `grep -r 'TODO: register' docs/` |

---

## Running Docs Tests

```bash
uv run pytest tests/docs/ -q
```

Run after each WP before committing. Zero failures required.

---

## Smoke-Testing a Command Snippet

When you add a code block that calls `spec-kitty`, test it against a temp directory:

```bash
TMPDIR=$(mktemp -d)
cd "$TMPDIR"
git init -q
uv run spec-kitty init  # or whatever the snippet requires
# run the snippet
cd -
rm -rf "$TMPDIR"
```

Never run smoke tests inside the spec-kitty source repo. The `SPEC_KITTY_ENABLE_SAAS_SYNC=1` flag is required for any snippet that would otherwise contact hosted services.

---

## Page Order Recommendation

Implement pages in this order (matches work packages planned by /spec-kitty.tasks):

1. Gap analysis doc: `kitty-specs/charter-end-user-docs-828-01KQCSYD/gap-analysis.md`
2. IA / TOC files: `docs/toc.yml`, `docs/3x/toc.yml`, section toc.yml files
3. `docs/3x/` hub pages (index, charter-overview, governance-files)
4. `docs/tutorials/charter-governed-workflow.md`
5. `docs/how-to/setup-governance.md` (update) + four new how-to pages
6. Three explanation pages
7. Three new reference pages + `cli-commands.md` update
8. `docs/migration/from-charter-2x.md` + `docs/2x/index.md` archive label
9. Retrospective root stub (`docs/retrospective-learning-loop.md` → redirect)
10. Validation pass (tests, links, CLI flag check, snippet smoke)
11. Release handoff artifact

---

## Release Handoff

When all pages are done, produce:
`kitty-specs/charter-end-user-docs-828-01KQCSYD/release-handoff.md`

Use the template in `plan.md` Section "Release Handoff Template".
