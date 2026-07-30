# Quickstart — Post-Consolidation Write Surface and Authoring Finish

Operator/agent walkthrough of the shipped behaviour. Terminology: **E1** = lane consolidation (`spec-kitty merge`, Target Ref survives); **E2** = publish-to-trunk (Target Ref deleted, content on the Primary Branch).

## 1. Post-consolidation evidence write succeeds (the #3033 fix)

```bash
# A mission has been consolidated (E1) and published to trunk (E2):
# its feature branch (Target Ref) is deleted; content is on main.
git checkout main            # the repository-root checkout carrying the consolidated content

# Record post-consolidation evidence on a classified PRIMARY artifact:
spec-kitty safe-commit kitty-specs/<mission>/retrospective.yaml
# BEFORE: refused — HEAD (main) != the deleted Target Ref.
# AFTER : committed to the CONSOLIDATED surface (this checkout). Exit 0, clean tree.
```

If you are on a checkout that does NOT carry the mission's consolidated content:

```bash
spec-kitty safe-commit kitty-specs/<mission>/retrospective.yaml
# Refuses with a recovery instruction naming a checkout that carries the content.
# It does NOT force a checkout and leaves no residue.
```

Coord-partitioned writes (issue-matrix / tracer / acceptance) via the write seam behave the same — committed on the CONSOLIDATED surface in E2 instead of refused.

## 2. Accept a mission with a negative invariant, zero hand-edited JSON (#2318)

```bash
# Register + execute a negative invariant (condition that must NOT hold):
spec-kitty agent mission acceptance-verdict --mission <mission> \
  --negative-invariant no-todos \
  --description "No TODO markers remain in shipped modules" \
  --verification-command "! grep -rn 'TODO' src/<area>/"

# Preflight — a malformed invariant is REPORTED, not a crash:
spec-kitty accept --mission <mission> --diagnose
#   reports which invariant/criterion is malformed and why; exits non-zero.

# An all-pass matrix persists a fresh verdict:
spec-kitty accept --mission <mission>
#   persisted overall_verdict == pass (not a stale "pending").
```

The accept mission-step prompt now drives `acceptance-verdict` — no instruction to hand-edit JSON.

## 3. Cite an issue by same-repo GitHub URL (#1738)

```markdown
<!-- In spec.md's **Input** field or any plan/tasks doc: -->
**Input**: … see https://github.com/Priivacy-ai/spec-kitty/issues/320 …
```

- The completeness gate now discovers `#320` from the URL (same as `#320` literal) and records its source file.
- An unrelated **cross-repo** GitHub URL in prose is ignored — it does NOT newly require an issue-matrix row (green missions stay green).

## 4. Terminology (foundation of #3080)

- The glossary (`docs/context/orchestration.md`) names **`consolidate`/`consolidation`** canonical for the lane-consolidation sense; that sense of "merge" is a legacy alias.
- The drift guard fails CI if new code/docs use a lane-consolidation-sense "merge" phrasing; git-merge and publish-to-origin "merge" uses are unaffected.
- The full `spec-kitty merge` → `consolidate` command/code/docs rename remains **#3080**.

## Verification (red-first)

- `#3033` P0: `tests/…/test_<...>_post_consolidation_write.py` — red-first `safe-commit` on an E2 mission, flips to green after Lane A.
- `#3073`: refused write leaves 0 untracked files.
- `#2318`: all-pass persists `pass`; malformed invariant reported not crashed.
- `#1738`: same-repo URL discovered; cross-repo URL does not block.
- Terminology: new forbidden phrasing fails the guard; git-merge/publish uses stay green.
