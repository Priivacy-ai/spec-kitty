# Contract: gate exemption (FR-007) + coord staleness (FR-008/009) + actor (FR-005/006)

## Runtime-state gate exemption (FR-007, C-004)

| # | Given | When | Then |
|---|-------|------|------|
| 1 | a diff touching the running mission's OWN `status.events.jsonl` | the diff-compliance gate runs | that file is exempt (`source="runtime-state"`, no violation); NO `occurrence_map` entry needed |
| 2 | a diff renaming ANOTHER mission's runtime files | the gate runs | those are NOT exempt (feature_dir mismatch) |
| 3 | a `spec.md`/`plan.md`/`tasks.md` change under the same feature_dir | the gate runs | still classifies (reviewable surface not exempt) |
| 4 | a non-runtime file under the mission's feature_dir | the gate runs | still classifies/violates per the normal rules |

- The exemption branch fires BEFORE the path-heuristic classifier (mirroring the existing move/exception
  exemptions). `check_review_diff_compliance` threads the mission's own `feature_dir` + the named allowlist
  into `assess_file`/`classify_path`.

## Coord staleness (FR-008/009, C-003/C-005)

| # | Given | When | Then |
|---|-------|------|------|
| 1 | coord tip is a strict ancestor of `target_branch` | `doctor coordination --check-staleness` | reports stale (non-blocking); `finalize-tasks` prints a non-blocking WARN + recovery command |
| 2 | strict-ancestor + coord worktree clean | `doctor coordination --fix` | fast-forwards the coord branch to include target's new commits |
| 3 | coord diverged (not strict-ancestor) OR coord worktree dirty | `doctor coordination --fix` | FAILS LOUD with a unified diff; mutates nothing |

- `--fix` stays MINIMIZED (C-003): it does the Gap-1 fast-forward only. It does NOT grow into a general
  "repair arbitrary drifted content" command. The reconciliation gate (`review_artifact_consistency`, now
  in `merge/`) is preserved as a fail-loud net, not deleted (NFR-003).

## Actor identity (FR-005/006, C-002/C-007)

| # | Given | When | Then |
|---|-------|------|------|
| 1 | compact `--agent tool:model:profile:role`, no dispatch Op | claim runs | actor = `{role, tool, profile, model}` parsed; `tool` is the bare token, not the whole string |
| 2 | partial `--agent tool::` (missing segments) | claim runs | absent segments stay `None` on the actor — NO synthetic `unknown-model`/`{tool}-default` |
| 3 | `--model` without `--invocation-id` | claim runs | still RAISES (unchanged — C-002/C-007 provenance) |
| 4 | a correctly-parsed dict actor | emitted to the SaaS fanout | accepted (`Union[str,Dict]`), not rejected as non-string |
| 5 | (US2 AC-3) manual review claim succeeds | after the FR-002 fix | no `--force` needed; merge shows no false "hollow reviews" — NOTE: satisfied by FR-002, confirmed by the NFR-002 repro, not by FR-005/006 alone |
