# Research: Task Workflow Bug Fixes

**Mission**: task-workflow-bug-fixes-01KV69BZ
**Date**: 2026-06-15
**Source**: Debbie's five-paradigm investigation + Alphonso architectural review

---

## IC-01 — map-requirements spec.md topology fix

### Root cause confirmed

**Decision**: Use `primary_feature_dir_for_mission` for spec.md path resolution in `map-requirements`.

**Rationale**: `resolve_feature_dir_for_slug` (the current call at tasks.py:3535) delegates to `resolve_mission_read_path`, which applies coord-worktree priority: when `.worktrees/<slug>-<mid8>-coord/` exists, it returns the coord path. The coord worktree is populated with `plan.md` and `tasks/` but spec.md is never staged there — it lives only in the primary checkout. The failure therefore triggers exclusively after `setup-plan` has run and the coord worktree has been materialised.

`primary_feature_dir_for_mission` (in `feature_dir_resolver.py`) is the topology-blind counterpart already used by `finalize-tasks` (mission.py:2769 sets `planning_dir = _primary_dir` with an explicit comment explaining why input artifacts must come from primary). The same discipline applies to spec.md in `map-requirements`.

**Alternatives considered**:
- Copy spec.md into the coord worktree during `setup-plan` — rejected: this adds coupling and risks stale copies; the correct fix is targeted resolver discipline.
- Use `resolve_action_context` from `mission_runtime` — rejected: heavier import, no benefit for a read-only path lookup.

### Surgical change

```
tasks.py line ~3535:
  BEFORE: feature_dir = resolve_feature_dir_for_slug(main_repo_root, mission_slug)
          spec_md = feature_dir / SPEC_MD_FILENAME

  AFTER:  feature_dir = resolve_feature_dir_for_slug(main_repo_root, mission_slug)
          primary_dir = primary_feature_dir_for_mission(main_repo_root, mission_slug)
          spec_md = primary_dir / SPEC_MD_FILENAME
```

`primary_feature_dir_for_mission` is already exported from `specify_cli.missions.feature_dir_resolver`. Import is either already present or requires one line.

### Regression guard

Test must assert: given a coord worktree directory on disk for the mission, `spec.md` is resolved from the primary checkout path. The test can create a tmp directory as a mock coord worktree without running real git; mock `CoordinationWorkspace.worktree_path` to return a temp dir that exists.

---

## IC-02 — validate_glob_matches create_intent YAML example

### Root cause confirmed

**Decision**: Extend the per-path error string in `validate_glob_matches` to include an inline YAML fragment.

**Rationale**: The current message tail ("If this file will be created by this WP, add it to 'create_intent' in the WP frontmatter.") names the field but does not show the YAML syntax. Agents parsing the error must know from training data or docs that `create_intent` is a list field in WP frontmatter YAML. The issue requests a ready-to-paste example, reducing recovery time for automated agents and human authors alike.

The `_nearest_match_suggestion` string is appended before the create_intent hint (when a close filename is found), so both can coexist in the same message without conflict.

The enhanced error must stay within NFR-003's 300-character ceiling. Measurement of the proposed text:

```
WP01: owned_files path 'src/new_module.py' is a literal file path that matches
zero files in the repository. If this file will be created during implementation,
declare it in the WP frontmatter:
  create_intent:
    - src/new_module.py
```

Length: ~220 characters for a typical path — well within the 300-char ceiling.

**Alternatives considered**:
- Link to documentation URL — rejected: link rot risk; inline YAML is self-contained.
- Add a separate `"hint"` JSON field alongside `"error"` — rejected: overcomplicates the JSON schema; the hint belongs in the per-path error string where it's co-located with the offending path.

### Surgical change

```
ownership/validation.py, validate_glob_matches(), else branch (~line 370-382):
  BEFORE:
    msg += (
        " If this file will be created by this WP, add it to "
        "'create_intent' in the WP frontmatter."
    )

  AFTER:
    msg += (
        " If this file will be created during implementation, "
        f"declare it in the WP frontmatter:\n  create_intent:\n    - {pattern}"
    )
```

### Regression guard

Parametrize an existing or new test: call `validate_glob_matches` with a manifest whose `owned_files` contains a literal path not present on disk and no `create_intent`. Assert:
- `result.passed` is `False`
- `result.errors[0]` contains the string `"create_intent"`
- `result.errors[0]` contains the offending path string

---

## Standing constraints verified

| Constraint | Verification |
|---|---|
| C-001 (sanctioned resolver) | `primary_feature_dir_for_mission` is from `feature_dir_resolver.py` — the module owned by the architectural path test |
| C-002 (field name exact) | `create_intent` appears verbatim in the new error string |
| C-003 (independent revert) | IC-01 and IC-02 touch different modules; neither depends on the other |
| mypy --strict | Both changes use existing types; no new type annotations required |
| ruff | No new control flow; complexity unchanged |
