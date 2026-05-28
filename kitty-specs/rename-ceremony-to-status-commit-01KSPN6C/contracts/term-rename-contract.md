# Term-Rename Contract

**Mission**: `rename-ceremony-to-status-commit-01KSPN6C`
**Date**: 2026-05-28

This terminology rename does not introduce or modify any API, payload, webhook, or wire format. The "contract" is a lexical replacement specification: source → target, plus the doctrine-prose semantic-rewrite ruleset.

The per-occurrence map (file, line, context, replacement) lives in [`../occurrence_map.yaml`](../occurrence_map.yaml). This contract gives the **rules** the occurrence map applies.

---

## Lexical Replacement Rules

### Rule R1 — Commit-class noun phrases

When the source text refers to an auto-commit recording workflow state change, replace with `status commit` (preserve surrounding case for the head noun).

| Source pattern | Replacement |
|---|---|
| `ceremony commit` | `status commit` |
| `ceremony commits` | `status commits` |
| `ceremony write` | `status commit` |
| `ceremony writes` | `status commits` |
| `ceremony write operation` | `status commit operation` |
| `ceremony write operations` | `status commit operations` |
| `status-writing operation` | `status commit operation` |
| `status-writing operations` | `status commit operations` |
| `status-writing command` | `status commit operation` |
| `status-writing commands` | `status commit operations` |

### Rule R2 — Workflow-sense bare "ceremony" noun

When the source text uses bare "ceremony" to refer to the multi-phase mission workflow (specify/plan/tasks/implement/review/merge), apply a semantic rewrite rather than a mechanical substitution. The replacement is whichever phrase preserves intent.

| Source pattern (context) | Replacement |
|---|---|
| `the full ceremony` | `the full mission workflow` |
| `full-ceremony` (compound modifier) | `full-mission-workflow` |
| `specify/plan/tasks ceremony` | `specify/plan/tasks workflow` |
| `Feature merge ceremony` | `Feature merge workflow` |
| `inflating them with ceremony` | `inflating them with workflow overhead` |
| `no ceremony` (idiom, "no overhead") | `no extra workflow steps` |
| `parts of the ceremony` | `parts of the mission workflow` |
| `after ceremony` (in test/lifecycle context) | `after the mission workflow runs` |
| `ceremony surfaces` | `status commit surfaces` |
| `degrades to ceremony` (English idiom: empty ritual) | `degrades to performative gesture` |

Rule R2 is intentionally non-mechanical. The reviewer should accept any wording that conveys "workflow" or "phases" when the original meant the multi-step process, not the commit class.

### Rule R3 — Code identifiers

When the source text is a Python identifier (constant, function, attribute), rename per Python convention and propagate to all callers.

| Source identifier | Replacement | File scope |
|---|---|---|
| `E2E_CEREMONY_BRANCH` | `E2E_STATUS_COMMIT_BRANCH` | `tests/e2e/conftest.py` |
| `_checkout_e2e_ceremony_branch` | `_checkout_e2e_status_commit_branch` | `tests/e2e/conftest.py` |

### Rule R4 — String literals used as IDs / branch names

When the source is a literal string used as a fixture ID or branch name, replace following kebab-case convention.

| Source literal | Replacement |
|---|---|
| `"e2e-ceremony"` (branch-name value) | `"e2e-status-commit"` |
| `"mission-merge-ceremony"` (fixture ID) | `"mission-merge-workflow"` |

Note: `mission-merge-ceremony` is reclassified per Rule R2 (workflow_sense) — it is a fixture for the **merge workflow** procedure, not a commit class.

### Rule R5 — Documentation prose

Prose in `docs/` and `src/doctrine/` follows Rules R1 and R2 by context. The doctrine guideline `inflating them with ceremony` is a workflow-overhead idiom; `ceremony commit was authored manually` is commit-class.

### Rule R6 — Proposed config-flag name (doc-only)

The proposed flag name in the F-09 findings doc is rewritten verbatim:

| Source | Replacement |
|---|---|
| `vcs.allow_ceremony_commits_on_target_branch` | `vcs.allow_status_commits_on_target_branch` |

No code-side change because the flag does not exist in live code (verified at plan time).

---

## Acceptance Contract (CI-enforceable)

A change conforms to this contract if and only if, after the merge:

1. `grep -rn 'ceremony' src/ tests/ docs/ --include='*.py' --include='*.md' --include='*.yaml'` returns zero hits.
2. `grep -rn 'status-writing' src/ tests/ docs/ --include='*.py' --include='*.md' --include='*.yaml'` returns zero hits.
3. The architectural test `tests/architectural/test_no_legacy_terminology.py` passes (it executes the two greps above plus identifier-symbol checks).
4. `.kittify/glossaries/spec_kitty_core.yaml` contains one `surface: status commit` entry with `status: active` and two entries with `status: deprecated` for the legacy terms.
5. The full `pytest` suite passes.
6. `mypy --strict` passes.
7. `ruff check .` passes.

---

## Out-of-Contract

These are explicitly NOT governed by this contract:

- Git commit messages in history.
- Files under `kitty-specs/` (historical mission artifacts).
- The user's local working-directory path (`spec-kitty-dev/ceremony/spec-kitty`).
- Any new code or behavior — this is a pure rename.
