# Operator Quick-Start: TeamSpace Mission-State Repair

## Prerequisites

- `spec-kitty-cli` v3.2.0rc4+ installed
- PR #1017 merged (confirmed 2026-05-11)
- This machine: export `SPEC_KITTY_ENABLE_SAAS_SYNC=1` before any doctor commands
- Each repo pulled to clean `main` HEAD

## Per-Repo Repair Steps

```bash
export SPEC_KITTY_ENABLE_SAAS_SYNC=1
WORKSPACE=/Users/robert/spec-kitty-dev/spec-kitty-20260511-103721-tglUge

for REPO in spec-kitty spec-kitty-saas spec-kitty-events; do
  cd $WORKSPACE/$REPO

  # 1. Baseline audit
  git checkout main && git pull --ff-only origin main
  spec-kitty doctor mission-state --audit --json > ../$REPO.before.audit.json
  echo "=== $REPO BEFORE ===" && cat ../$REPO.before.audit.json | python3 -m json.tool

  # 2. Repair
  spec-kitty doctor mission-state --fix

  # 3. Post-repair audit
  spec-kitty doctor mission-state --audit --json > ../$REPO.after.audit.json
  spec-kitty doctor mission-state --teamspace-dry-run --json > ../$REPO.dry-run.json

  # 4. Verify zero blockers
  python3 -c "import json; d=json.load(open('../$REPO.after.audit.json')); assert d['missions_with_teamspace_blockers']==0, f'BLOCKERS REMAIN: {d}'; print('OK: zero blockers')"

  # 5. Create repair branch and PR
  git checkout -b repair/teamspace-mission-state-history
  git add .kittify/migrations/mission-state/ kitty-specs/
  git commit -m "repair: TeamSpace mission-state history — deterministic repair manifest"
  gh pr create --base main \
    --title "repair: TeamSpace mission-state history ($REPO)" \
    --body "Closes spec-kitty#979. Parent: spec-kitty#920."
done
```

## Acceptance Gates (per repo)

| Gate | Command | Expected |
|------|---------|---------|
| Zero blockers post-repair | `--audit --json` | `missions_with_teamspace_blockers == 0` |
| Dry-run passes | `--teamspace-dry-run --json` | `envelope_validation_errors == []` |
| Manifest exists | `ls .kittify/migrations/mission-state/` | At least one manifest file |
| PR raised | `gh pr list` | PR linked to #979 and #920 |
