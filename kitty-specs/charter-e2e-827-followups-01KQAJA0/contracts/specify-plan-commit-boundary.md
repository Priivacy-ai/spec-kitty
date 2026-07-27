# Contract — Specify/Plan Auto-Commit Boundary (post-#846)

Maps to FR-012, FR-013, FR-014, FR-015, FR-016 and INV-846-{1,2,3,4} in `data-model.md`.

## Surface inventory

There are two Python-side auto-commit paths that today land mission artifacts on the target branch:

| Path | Location | What it commits today | What this mission changes |
|---|---|---|---|
| `mission create` | `src/specify_cli/cli/commands/agent/mission.py` (the create command's `safe_commit` call) | `meta.json` + the empty `spec.md` scaffold | Drop `spec.md` from the create-time commit. The agent commits the populated `spec.md` after writing substantive content. |
| `setup-plan` | `src/specify_cli/cli/commands/agent/mission.py` near line 973 (`_commit_to_branch(plan_file, …)`) | `plan.md` after the slash-template populates it | Gate the commit on `is_substantive(plan, "plan")`. Add an entry-time check that `spec.md` is committed AND substantive; if not, do not write or commit `plan.md`. |

The `/spec-kitty.specify` slash-template instructs the agent to commit substantive `spec.md` content; that commit happens outside Python and is unchanged by this mission.

## Boundary (post-fix)

After this WP lands:

1. **`mission create`** does not commit `spec.md` at all. Empty scaffolds remain untracked at create time.
2. **`setup-plan` entry**: the command verifies that `spec.md` is BOTH committed (tracked + present in HEAD) AND substantive. If either fails, the command emits `phase_complete=False` with a `blocked_reason` and returns without writing or committing `plan.md`.
3. **`setup-plan` exit**: the existing `_commit_to_branch(plan_file, …)` call is gated on `is_substantive(plan_path, "plan")`. If false, emit `phase_complete=False / blocked_reason` and skip the commit.
4. Workflow status JSON reflects all of the above accurately. A non-substantive or uncommitted-substantive state is **incomplete**, never "ready".

## `is_substantive(file_path, kind)` definition (revised — section-presence only)

```python
def is_substantive(file_path: Path, kind: Literal["spec", "plan"]) -> bool:
    """Return True iff the file contains substantive (non-template) content for the given artifact kind."""
    body = file_path.read_text(encoding="utf-8")
    return _has_required_sections(body, kind)
```

Required sections per kind:

| kind | Required signal (must be present AND not template-placeholder) |
|---|---|
| `spec` | At least one row in a Functional Requirements table that has an `FR-\d{3}` ID followed by non-empty description content. The row must NOT consist entirely of template placeholders like `[NEEDS CLARIFICATION …]` or `[e.g., …]`. |
| `plan` | A populated Technical Context section where `Language/Version` (and at least one peer field like `Primary Dependencies`) contains a real value — NOT a placeholder like `[e.g., Python 3.11 …]` or `[NEEDS CLARIFICATION …]`. |

The earlier "byte-length OR section-presence" formulation was rejected. Byte-length-only would pass scaffold + arbitrary prose, recreating the failure mode this mission exists to fix. See research.md R7 (revised) for the rationale.

## `is_committed(file_path, repo_root)` definition

```python
def is_committed(file_path: Path, repo_root: Path) -> bool:
    """Return True iff the file is git-tracked AND present at HEAD."""
    # subprocess: `git ls-files --error-unmatch <rel>` and `git cat-file -e HEAD:<rel>`
```

Used at the `setup-plan` entry gate to enforce INV-846-2.

## Producer obligations (`src/specify_cli/cli/commands/agent/mission.py`)

### `mission create`

```python
# OLD (today):
safe_commit(repo_path=..., files_to_commit=[meta_file, spec_file, ...], commit_message="...")

# NEW (post-fix):
safe_commit(repo_path=..., files_to_commit=[meta_file, ...],  # spec_file omitted
            commit_message="Add meta and scaffolding for feature ...")
# The empty spec.md scaffold remains on disk but untracked. The agent commits it
# after writing substantive content (existing slash-template behavior).
```

### `setup-plan`

```python
# Entry gate (top of setup-plan):
if not is_committed(spec_path, repo_root) or not is_substantive(spec_path, "spec"):
    return {
        "phase_complete": False,
        "blocked_reason": (
            "spec.md must be committed and substantive before the plan phase can begin. "
            "Populate Functional Requirements and commit, then re-run setup-plan."
        ),
        # no plan.md written, no commit made
    }

# ... write plan.md from template, allow agent population ...

# Exit gate (replace the existing _commit_to_branch(plan_file, ...) call):
if is_substantive(plan_path, "plan"):
    _commit_to_branch(plan_file, mission_slug, "plan", repo_root, target_branch, json_output)
    payload["phase_complete"] = True
else:
    payload["phase_complete"] = False
    payload["blocked_reason"] = (
        "plan.md content is not substantive yet; populate Technical Context with real values "
        "and re-run setup-plan to commit."
    )
    # do NOT commit
```

## Consumer obligations (workflow status reporters, `mission setup-plan --json`, dashboard)

- Treat `phase_complete=False` with `blocked_reason` containing the substantive-content phrase as **incomplete**, never as "ready".
- Do not silently retry or auto-advance.

## Regression test contract (`tests/integration/test_specify_plan_commit_boundary.py`)

```
GIVEN a fresh `mission create` invocation
WHEN we inspect the resulting commits
THEN spec.md is NOT committed (it exists on disk but is untracked)
  AND meta.json IS committed
```

```
GIVEN a fresh mission with an UNCOMMITTED, populated spec.md (real FR rows)
WHEN setup-plan runs
THEN no plan.md is committed
  AND JSON output reports phase_complete=False with a blocked_reason naming "committed and substantive"
```

```
GIVEN a fresh mission with a COMMITTED spec.md that is ONLY scaffold (empty FR table)
WHEN setup-plan runs
THEN no plan.md is committed
  AND JSON output reports phase_complete=False with a blocked_reason naming substantive content
```

```
GIVEN a fresh mission with a COMMITTED, SUBSTANTIVE spec.md (≥1 FR row populated)
AND the agent has populated plan.md with a real Technical Context
WHEN setup-plan runs
THEN plan.md IS committed
  AND JSON output reports phase_complete=True
```

```
GIVEN the same setup as above BUT plan.md is left as template placeholder
WHEN setup-plan runs
THEN plan.md is NOT committed
  AND JSON output reports phase_complete=False with a substantive-plan blocked_reason
```

## Template documentation (`src/specify_cli/missions/<mission-type>/command-templates/{specify,plan}.md`)

Each template file gets a short "Commit Boundary" subsection explaining:

- Why the workflow may refuse to write or commit `plan.md`.
- What "substantive content" means operationally for this artifact.
- How to advance the workflow: populate substantive content, commit it (for spec.md) or re-run setup-plan (for plan.md).

## What this contract does NOT change

- The location of `spec.md` / `plan.md`.
- The shape of the slash-template instructions (the agent still writes substantive content into `spec.md` and `plan.md` from the slash-template flow).
- The set of required sections beyond the explicit pair listed above.
- Any auto-commit behavior outside the two paths in the inventory above (e.g. `agent acceptance`, `agent tasks`, etc.).
- Existing missions whose `spec.md` was already committed empty by the pre-fix `mission create`. Those legacy missions remain on disk; their "spec phase complete" state is determined by the same entry gate (`is_committed AND is_substantive`). A legacy empty-but-committed `spec.md` will be reported as incomplete until the agent populates and re-commits it.
