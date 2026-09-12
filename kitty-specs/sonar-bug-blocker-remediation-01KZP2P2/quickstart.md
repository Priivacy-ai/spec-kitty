# Quickstart: Verifying the Sonar BUG/BLOCKER Remediation

How to confirm the mission met its success criteria. No data model or API contracts apply
(this is an in-place correctness/test-integrity remediation).

## 1. No suppressions were added (NFR-001, SC-003)

```bash
# Expect ZERO added lines introducing a suppression to clear an issue:
git diff <merge-base>..HEAD -- '*.py' | grep -E '^\+' | grep -Ei 'noqa|type:\s*ignore|nosonar' || echo "clean: no suppressions added"
```

## 2. Affected tests green + lint clean (NFR-002, SC-004)

```bash
# Scoped run over the changed test files (fast; full suite is CI's job):
PWHEADLESS=1 python -m pytest <changed test files> -p no:cacheprovider -q
ruff check <changed files>
mypy <changed src files>          # zero NEW findings vs base
```

## 3. Recoverable assertions bite (NFR-003)

For each S5863 assertion fixed with recovered intent, the red-first evidence is the commit sequence
(or a captured failing run) showing the corrected assertion failing against the pre-fix behavior,
then passing after the fix. Deletions carry an inline/one-line rationale.

## 4. Sonar surface cleared (NFR-004, SC-001, SC-002)

After the fix branch is analyzed by SonarCloud (post-merge or on the PR analysis):

```bash
# BUG count -> expect 0
curl -s "https://sonarcloud.io/api/issues/search?componentKeys=Priivacy-ai_spec-kitty&types=BUG&issueStatuses=OPEN,CONFIRMED&ps=1" | python3 -c "import sys,json;print('BUG open:',json.load(sys.stdin)['total'])"
# BLOCKER count -> expect 0
curl -s "https://sonarcloud.io/api/issues/search?componentKeys=Priivacy-ai_spec-kitty&impactSeverities=BLOCKER&issueStatuses=OPEN,CONFIRMED&ps=1" | python3 -c "import sys,json;print('BLOCKER open:',json.load(sys.stdin)['total'])"
```

Any residual item must carry a written, reviewed false-positive rationale (not a suppression) — call
it out in the PR body. SonarCloud re-analysis is post-merge for the project surface (a gate-unmask
shape), so pair the code fix with this verification method in the hand-off.
