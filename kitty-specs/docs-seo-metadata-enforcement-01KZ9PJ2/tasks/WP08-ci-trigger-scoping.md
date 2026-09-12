---
work_package_id: WP08
title: CI trigger scoping
dependencies: []
requirement_refs:
- NFR-007
tracker_refs: []
planning_base_branch: feat/docs-seo-metadata-enforcement
merge_target_branch: feat/docs-seo-metadata-enforcement
branch_strategy: Planning artifacts for this mission were generated on feat/docs-seo-metadata-enforcement. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/docs-seo-metadata-enforcement unless the human explicitly redirects the landing branch.
subtasks:
- T039
- T040
- T041
agent: "claude:opus-5:reviewer-renata:reviewer"
shell_pid: "64642"
history:
- at: '2026-08-05T19:58:15Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: .github/workflows/docs-freshness.yml
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- .github/workflows/docs-freshness.yml
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP08 – CI trigger scoping

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`

## Objective

Stop `docs-freshness` from running on pull requests that touch no documentation surface.

Small WP, one file — but it carries a real footgun and a real correctness trap, both documented below.

## Context

**Current state**: `.github/workflows/docs-freshness.yml` declares:
```yaml
on:
  pull_request:
  push:
    branches: [main]
```
No path filter. It runs on **every** pull request.

**Does that block unrelated PRs today?** Not usually. These gates are whole-tree scans and `main` is green, so a PR touching no docs scans the same clean tree and passes. What it actually costs is CI *time* — checkout, `uv sync`, and five checks on every PR. The operator's concern (decision `01KZ9Q2CMWF5H7TEXDFRSJ6SWD`) is that cost, and the possibility of docs problems surfacing on unrelated work.

**The classic footgun, and why it does not apply here**: a *required* status check that gets skipped by a path filter leaves PRs pending forever, because GitHub treats required-but-not-run as incomplete. This was checked against live branch protection during planning:

```
$ gh api repos/Priivacy-ai/spec-kitty/branches/main/protection --jq '.required_status_checks.contexts'
["drift-detector"]
```

`docs-freshness` is **not** a required context. The filter is safe. T040 re-verifies this rather than trusting a planning-time snapshot.

## Subtasks

### T039 — Add a `paths:` filter covering every gate input

**Purpose**: Scope the workflow to changes that could actually affect its outcome.

**⚠️ The correctness trap**: the filter must cover every input the gates **read**, not merely `docs/**`. A filter narrower than the true input set silently stops guarding real changes — which is the *same failure shape* this entire mission exists to repair, reintroduced in a new place. Do not shortcut this.

**Steps**:
1. Enumerate what the four gate steps actually read:

   | Step | Reads |
   |---|---|
   | `related_validator.py --strict` | `docs/**`, `scripts/docs/**` |
   | `description_length_check.py --strict` | `docs/**`, `scripts/docs/**` |
   | `relative_link_fixer.py --check` | `docs/**`, `scripts/docs/**` |
   | `docs_structural_lint.py --styleguide …` | `docs/**`, `packs/built-in/assets/docs_structural_lint.py`, `packs/built-in/styleguides/common-docs.styleguide.yaml` |
   | `sync_changelog.py --check` / `sync_contributing.py --check` | `docs/**`, `CHANGELOG.md`, `CONTRIBUTING.md`, `scripts/docs/**` |
   | `check_docs_freshness.py --ci` | `docs/**`, `scripts/docs/**` |

   Read the workflow yourself and confirm this list is complete before writing the filter — steps may have been added since planning.

2. Add the filter to the `pull_request` trigger. At minimum:
   ```yaml
   on:
     pull_request:
       paths:
         - 'docs/**'
         - 'scripts/docs/**'
         - 'packs/built-in/assets/docs_structural_lint.py'
         - 'packs/built-in/styleguides/common-docs.styleguide.yaml'
         - 'CHANGELOG.md'
         - 'CONTRIBUTING.md'
         - '.github/workflows/docs-freshness.yml'
     push:
       branches: [main]
   ```
3. Include the workflow file itself, so a change to the filter re-triggers the workflow.
4. **Leave the `push: branches: [main]` trigger unfiltered.** A full scan on every push to main is the cheap way to detect that main has gone red, which is what the whole-tree-scan model depends on.
5. Note in your WP notes that after WP01/WP06 land, `scripts/docs/_published_pages.py` is also a gate input — it is already covered by the `scripts/docs/**` glob, but confirm rather than assume.

**Files**: `.github/workflows/docs-freshness.yml`

**Validation**:
- [ ] Every path read by every step is covered
- [ ] Workflow file itself included
- [ ] `push: main` trigger left unfiltered
- [ ] YAML valid

### T040 — Verify the required-check safety precondition still holds

**Purpose**: The filter is only safe because `docs-freshness` is not a required status check. Re-verify rather than trusting a planning-time snapshot — branch protection can change.

**Steps**:
1. ```bash
   unset GITHUB_TOKEN
   gh api repos/Priivacy-ai/spec-kitty/branches/main/protection \
     --jq '.required_status_checks.contexts'
   ```
   (`unset GITHUB_TOKEN` is required in this repo — the ambient token has limited scopes; keyring auth has full `repo` scope.)
2. Confirm `docs-freshness` is **absent** from the returned contexts.
3. **If it is present, stop.** Do not add the filter — a skipped required check leaves every non-docs PR pending forever. Report the finding and escalate; the decision that authorised this change assumed the opposite.

**Validation**:
- [ ] Required contexts listed and recorded
- [ ] `docs-freshness` confirmed absent
- [ ] If present: filter NOT added, finding escalated

### T041 — Record the filter's input-set invariant

**Purpose**: The filter has an invariant that is not self-evident from reading it, and violating it degrades CI silently. Write it down (DIRECTIVE_003, DIRECTIVE_037).

**Steps**:
1. Add a comment above the `paths:` block, matching the explanatory style already used in that workflow and in `docs-pages.yml`'s concurrency block. It must state:
   - **The invariant**: the filter must cover every path the gate steps *read*, not just `docs/**`. Adding a step that reads a new path requires extending this list.
   - **Why it is safe**: `docs-freshness` is not a required status check (verified in T040); if that ever changes, this filter becomes a PR-blocking hazard and must be removed.
   - **Why `push: main` stays unfiltered**: the gates are whole-tree scans, so a full run on main is how a red tree is detected.
2. Keep it concise — a paragraph, not an essay.

**Files**: `.github/workflows/docs-freshness.yml`

**Validation**:
- [ ] Comment states the input-set invariant
- [ ] Comment states the required-check dependency and its failure mode
- [ ] Comment explains the unfiltered `push` trigger

## Branch Strategy

- **Planning base branch**: `feat/docs-seo-metadata-enforcement`
- **Final merge target**: `feat/docs-seo-metadata-enforcement`
- Execution worktrees are allocated per computed lane from `lanes.json`. Consume the resolved path.
- This mission reaches `origin/main` only through a pull request.

## Definition of Done

- [ ] `paths:` filter added to the `pull_request` trigger
- [ ] Filter covers every path every gate step reads, verified against the current workflow
- [ ] Workflow file itself included in the filter
- [ ] `push: branches: [main]` left unfiltered
- [ ] Required-check absence re-verified against live branch protection
- [ ] Input-set invariant documented in a comment
- [ ] YAML valid; no other workflow steps modified

## Risks

| Risk | Mitigation |
|---|---|
| **Filter narrower than the gates' true inputs → silent loss of guarding** | T039 enumerates per step and requires re-reading the workflow, not trusting this list |
| Branch protection changed since planning → skipped required check deadlocks PRs | T040 re-verifies live and hard-stops if it finds otherwise |
| Future step added that reads a new path, filter not extended | T041 documents the invariant at the point of change |
| Filtering `push: main` hides a red tree | T039 explicitly leaves that trigger unfiltered |

## Reviewer Guidance

1. **Re-derive the input set independently.** Read every `run:` line in the workflow and list the paths each command reads. Compare against the filter. A missing path is a silent guarding loss — the exact bug class this mission exists to fix.
2. **Confirm T040 was actually run** and its output recorded, not assumed from this prompt.
3. **Check `push: branches: [main]` is still unfiltered.**
4. **Verify the workflow file itself is in the filter** — otherwise a future filter change does not re-trigger.
5. **Confirm no gate step was modified** — this WP changes triggers only.

## Activity Log

- 2026-08-05T20:19:01Z – claude:opus-5:implementer-ivan:implementer – shell_pid=55785 – Assigned agent via action command
- 2026-08-05T20:25:48Z – claude:opus-5:implementer-ivan:implementer – shell_pid=55785 – Scoped docs-freshness pull_request trigger to its true input set; push:main left unfiltered. T040 re-verified live branch protection: gh api repos/Priivacy-ai/spec-kitty/branches/main/protection --jq '.required_status_checks.contexts' returned ["drift-detector"] — docs-freshness absent, so the filter is safe. Derived the input set by reading every run: line and the scripts they invoke, and found one gate input the planning table missed: check_docs_freshness.py sub-check 2 (check_cli_reference_freshness) does 'from specify_cli import app' and walks the live Typer surface, with REF-MISSING/REF-EXTRA at error severity — so src/specify_cli/** is a real input and is now in the filter. Also added pyproject.toml and uv.lock (uv sync builds the env that walk imports). Documented residual gap: relative_link_fixer --check and related_validator assert cross-tree link targets exist (docs pages reference src/, tests/, kitty-specs/, packs/, .github/), an unbounded set no path filter can express — the unfiltered push:main whole-tree scan is its backstop. scripts/docs/_published_pages.py (WP01/WP06) confirmed covered by the scripts/docs/** glob. YAML parses; 12 steps unchanged; diff is additive trigger+comment only.
- 2026-08-05T20:26:26Z – claude:opus-5:reviewer-renata:reviewer – shell_pid=64642 – Started review via action command
- 2026-08-05T20:36:06Z – user – shell_pid=64642 – Review passed (reviewer-renata verified on merits; transition deferred to orchestrator because the mission-level issue-matrix gate blocked it). Full reviewer evidence recorded in the review transcript.
