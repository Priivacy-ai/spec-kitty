# Labeled corpus — post-integration ("un-terminable work") detector

This directory is the **measurement oracle** (SC-003) for the authoring-time
detector in `src/specify_cli/tasks_authoring/post_integration_warning.py`.

The detector makes **no open-world claim**. Its precision/recall target is
scoped to this fixed, committed corpus:

- **100% recall** on every fixture under `positive/` — each MUST warn.
- **0 false positives** on every fixture under `negative/` — each MUST NOT warn.

If you change the trigger set (bump `TRIGGER_SET_VERSION`), reconcile it against
this corpus in the same change.

## `positive/` — the #3590 shapes (MUST warn)

Work packages whose acceptance criteria can only be satisfied **after
integration**, so they cannot be terminated from their own diff. These embody
the #3590 trap shapes ("enable the real system", "prove it with controls",
"observe five consecutive runs"), phrased with genuine post-integration
language that carries a trigger phrase:

| File | #3590 shape | Trigger phrase(s) it carries |
|------|-------------|------------------------------|
| `enable_the_real_system.md` | "enable the real system" | `in CI once enabled`, `after merge`, `once merged` |
| `prove_it_with_controls.md` | "prove it with controls" | `on a branch the forge will run`, `merge-blocked-when-absent` |
| `observe_consecutive_runs.md` | "observe five consecutive runs" | `consecutive runs`, `post-merge` |

**Reconciliation note.** The bare marketing phrases "enable the real system"
and "prove it with controls" contain no post-integration signal on their own —
flagged by the post-tasks reviewer. Rather than overfit the trigger set to
those literals (which would risk firing on ordinary work), the positive
fixtures give each #3590 shape **genuine post-integration phrasing** that
embeds the contract's enumerable trigger set. The trigger set stays the
contract's versioned list; the corpus supplies the real phrasing.

## `negative/` — adversarial near-misses (MUST NOT warn)

Work packages that *mention* CI or merge but whose completion is observable in
their own diff. These are the point of the corpus: a detector that warns here
is wrong.

| File | Source | Why it must stay silent |
|------|--------|-------------------------|
| `adds_ci_workflow_file.md` | crafted | Adds a CI workflow file; correctness is in the diff. |
| `implements_merge_helper.md` | crafted | Implements a `merge` helper; verified by shipped unit tests. |
| `real_repo_wp02_preflight_validation.md` | **real repo** — `kitty-specs/017-smarter-feature-merge-with-preflight/tasks/WP02-preflight-validation.md` | A real merge-preflight WP that mentions merge/CI heavily; completion is in its diff. |
| `real_repo_wp06_cli_commands.md` | **real repo** — `kitty-specs/004-modular-code-refactoring/tasks/WP06-cli-commands.md` | A real CLI-commands WP that mentions CI; completion is in its diff. |

The two `real_repo_*` fixtures are verbatim copies of existing work packages in
this repository. They keep the corpus from being self-serving: the detector
must stay silent on genuine, historical code work, not just on hand-tuned
negatives.
