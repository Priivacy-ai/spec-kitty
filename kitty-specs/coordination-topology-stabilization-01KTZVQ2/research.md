# Research: Coordination Topology Stabilization

**Source**: Validated Debugger Debbie investigation — eight parallel investigators, ~598k tokens, 194 tool calls. All decisions below are evidence-grounded with file:line references.

---

## Decision 1: Coord-Aware Read Primitive Design

**Decision**: Add a placement-aware `is_committed(file, repo_root, placement)` overload that uses `git cat-file -e <placement.ref>:<rel-path>` for the coordination branch, falling back to primary HEAD for flat topology.

**Rationale**: `is_committed()` in `_substantive.py:214-239` has been unchanged since issue #898 and hardcodes `git show HEAD:<path>`. The coordination placement resolver (`_commit_to_branch`, `resolve_placement_only`) already exists and handles the write path — the read path needs a symmetric twin. Using `git cat-file -e` is lighter than `git show` and returns a clear exit code without object content.

**Alternatives considered**:
- Re-read from the worktree filesystem: fails because the coord worktree may not be checked out during planning phases.
- Probe `origin/<coord-branch>`: adds a network round-trip and doesn't work offline.
- Mirror write-path by checking out the coord branch temporarily: too disruptive, would break concurrent operations.

**Confirmed by**: `_substantive.py:214-239` grep; `resolve_placement_only` in `src/specify_cli/placement/` traced; `git cat-file -e` exit-code contract confirmed via git docs.

---

## Decision 2: .worktrees/ Guard Strategy

**Decision**: Three-layer guard — (1) fix `_feature_dir_file_paths` root anchor, (2) add `path_is_under_worktrees` rejection at `safe_commit` and `BookkeepingTransaction.write_artifact`, (3) add `tests/architectural/test_worktrees_index_clean.py` ratchet. Then land cleanup PR (26 paths, `git rm -r --cached`).

**Rationale**: The root cause is `_feature_dir_file_paths` (implement.py:441) relativizing coord-worktree paths against the PRIMARY repo root. `git add --force` is used downstream, which stages anything including gitignored paths, and the safe_commit backstop validates staged-vs-requested but not requested-vs-policy. The `path_is_under_worktrees` predicate already exists in `merge.py:153` — reusing it avoids duplication.

**Alternatives considered**:
- Only fix the root anchor: leaves safe_commit unprotected from other callers.
- Only add architectural test: doesn't fix the root cause; new violations will re-occur.
- Fix and immediately land cleanup: the cleanup removes the 26 paths and changes `is_committed` behavior for the legacy mission, creating an ordering dependency that needs to be tested both before and after.

**Confirmed by**: `implement.py:441` read; `merge.py:153` `path_is_under_worktrees` confirmed; `git ls-tree origin/main .worktrees/` confirmed 26 paths; squash commit 6518c852a (PR #1825) identified as origin.

---

## Decision 3: Accept Gate — Write-Aware Baseline vs. Path Exclusion

**Decision**: Use both strategies in combination: (a) baseline snapshot before any accept-owned write for the dirty-tree gate, and (b) exclude accept-owned derived paths from the git-status check, mirroring the #1814 pattern.

**Rationale**: The baseline-snapshot approach alone doesn't protect against concurrent daemon materialization (status.json re-writes, log items 10/25). The path-exclusion approach alone doesn't protect against accept writing to a location the gate doesn't know about in future. The #1814 pattern already exists and is tested — extend it to include `acceptance-matrix.json` and status-view paths.

**Alternatives considered**:
- Lock the working tree during accept: not feasible for a CLI tool with concurrent daemon activity.
- Only fix `--no-commit` (mutate_matrix): necessary but not sufficient — failure exits also leave residue.
- Fold residue into a commit on all exit paths as the sole fix: doesn't resolve the snapshot-before-write ordering for the failure-exit case.

**Confirmed by**: `accept.py:284` mutate_matrix=True even in --no-commit; `_commit_residual_acceptance_artifacts` at accept.py:74-108 only called on success path (accept.py:369-376); `__init__.py:752-754` matrix write in mutate_matrix guard.

---

## Decision 4: next Query Fail-Closed Error Type

**Decision**: Introduce `MISSION_NOT_FOUND` as a structured named error code with fields: `error_code`, `handle`, `remediation`. Exit 1 in both human and `--json` modes. Do not reuse existing error codes.

**Rationale**: The two "unknown" branches in `runtime_bridge.py:3074-3097` return a valid-shaped Decision object with `state="unknown"` and exit 0. JSON consumers cannot distinguish "mission not found" from "mission in an unknown state". A new named code is unambiguous and grep-friendly.

**Alternatives considered**:
- Reuse `MISSION_AMBIGUOUS_SELECTOR`: semantically wrong (no candidates, not ambiguous).
- Return empty JSON with exit 1: loses the error code, hard to act on.
- Log a warning and continue: doesn't surface the error to CI/automation.

**Confirmed by**: `runtime_bridge.py:3074-3097` read (two branches confirmed); exit-0 confirmed via subprocess test during investigation; `_resolve_mission_slug:331-357` StatusReadPathNotFound swallow confirmed.

---

## Decision 5: Ownership Warning Routing — Hard Error Threshold

**Decision**: Literal paths (no glob metacharacters) matching zero files → hard error with basename nearest-match suggestion. Glob patterns matching zero files → warning (soft, existing behavior). Planned-new-file annotation `create_intent: true` → suppress zero-match error.

**Rationale**: Literal paths are almost always typos or stale references (the mission-131 case confirms). Glob patterns can legitimately match zero files during in-flight work (e.g., `tests/specify_cli/test_*_new_feature.py` before tests are written). The two cases have different severity. The `create_intent` annotation is the clean escape hatch for legitimate planned-new-file cases.

**Alternatives considered**:
- Hard error for all zero-match entries (globs too): too aggressive for in-flight work.
- Keep as warning with just better routing: C-006 explicitly requires a hard error for literals; warning is confirmed insufficient.

**Confirmed by**: `validate_glob_matches` at `cli/commands/agent/tasks.py:267-295`; `ownership_warnings` JSON field confirmed unconsumed by prompt grep; mission-131 phantom path confirmed via tasks.md inspection.

---

## Decision 6: Stale-Assertion Message-Content Pattern

**Decision**: Classify the AST containment target: if the removed literal is the right-hand operand of an `in` operator whose left-hand operand is a message-capture expression (`str(…)`, `repr(…)`, `.message`, `.stderr`, `.stdout`, `.output`, `excinfo.value`, capsys/capfd capture), suppress the finding or emit at `info` grade with label `message-content-check`.

**Rationale**: The existing `not in` exemption (stale_assertions.py) already handles the inverse case. The message-capture pattern is a well-defined AST shape — it's not ambiguous. An info-grade finding preserves visibility for the operator while preventing false CI signal.

**Alternatives considered**:
- Global suppression of all `in`-operator assertions: too broad (many legitimate stale-assertion findings use `in`).
- Require explicit `# noqa` per test: too much annotation burden.
- Drop message-content findings entirely (not even info grade): loses the signal for cases where a diagnostic has been silently removed.

**Confirmed by**: `stale_assertions.py:350` (`_literal_findings_for_assertion`) read; existing `not in` exemption at :~390 confirmed; `changed_literals` last-wins dict bug at :~280 confirmed (multi-site removal drops all but the last site).

---

## Decision 7: Retrospective Triggering — merge Postcondition Pattern

**Decision**: Add a single postcondition check at the end of `spec-kitty merge` (in `src/specify_cli/cli/commands/merge.py` or `merge/executor.py`): if `kitty-specs/<slug>/retrospective.yaml` does not exist, invoke the shared `_run_retrospective_learning_capture` path or emit `RetrospectiveSkipped` to `status.events.jsonl`. Consolidate with the `run_terminus` dead-code path (which already has skip-event semantics) rather than adding a third implementation.

**Rationale**: The current capture is gated only on the `spec-kitty next` terminal-decision branch, which merge-completed missions never cross. The `run_terminus` function exists in `retrospective_terminus.py` but is dead code — retrospective.skipped events are unreachable in production. Consolidating avoids a third implementation and closes the dead-code debt.

**Alternatives considered**:
- Trigger from the accept gate: would fire too early (before merge); accept may run multiple times.
- Add a new `spec-kitty retro` CLI command the user must run: adds operator burden; the directive says "always-on".
- Only emit a skip event (no actual capture attempt): loses learnings when the retrospective could run.

**Confirmed by**: `retrospective_terminus.py` read — `run_terminus` is unreachable; `_run_retrospective_learning_capture` in `merge/executor.py` traced; `generator.py:684` "helped only by contrast" rule read.

---

## PR #1895 Coordination Note

PR #1895 (fork branch `stijn-dejongh/spec-kitty`, mission `name-vs-authority-remediation-01KTYGTE`) is reportedly in-flight and claims fixes for:
- #1884 FR-001 (IS-COMMITTED gate — aligns with IC-01)
- #1885 fail-closed query hardening (aligns with IC-05)

**Action before dispatching IC-01 and IC-05**: Review PR #1895's actual diff against `origin/main`. If its fixes land first, IC-01 and IC-05 WPs should be scoped to extend/harden rather than re-implement. If not yet merged, coordinate to avoid duplicate effort.
