# Quickstart — verifying Doctrine Catfooding

The catfooding smoke path: prove the 8 sections are activated doctrine and the charter compiled from them. Run from the repo root on the mission branch.

## 1. Every section is represented in activated doctrine (SC-001)
```bash
spec-kitty charter list                     # each of §1–§8 maps to ≥1 activated artifact
```
Cross-check against the section→artifact inventory in `data-model.md`.

## 2. No duplicate authority for the pre-covered sections (SC-002 / NFR-002)
```bash
# §4 extended 041, no NEW §4 directive was minted:
ls src/doctrine/directives/built-in/ | grep -iE 'test|scaffold'   # only 041, no new §4 directive
# §8 tiered-rigour references (does not re-author) tiered-standards:
grep -ril 'tiered-standards' src/doctrine/ | head
# §7 compress-history references clean-linear-commit-history (not re-authored):
grep -ril 'clean-linear-commit-history' src/doctrine/
```
Plus: each conversion WP's overlap-audit record shows an explicit augment-vs-create decision.

## 3. Doctrine is healthy (NFR-001)
```bash
spec-kitty doctor doctrine --json           # 0 skipped / 0 invalid artifacts
```
(Also run after each conversion, not only here.)

## 4. DRG is valid + fresh (PD-2 / wiring WP)
```bash
pytest tests/doctrine/drg/ -q               # cycle-free, no dangling/dup edges, regenerated == committed
```

## 5. Terminology canon holds (C-004 / NFR-004)
```bash
pytest tests/architectural/test_no_legacy_terminology.py -q
```

## 6. §1 stayed optional (C-006)
```bash
# the §1 cadence artifact is a styleguide/paradigm, and no directive carries enforcement: required for it
grep -rl 'enforcement: required' src/doctrine/ | xargs grep -il 'adversarial\|squad' || echo "OK: §1 not a required directive"
```

## 7. Charter compiled from the activated set (SC-003 / C-007)
```bash
# activate happened before generate; charter.md regenerated from activation; closure non-shallow:
sed -n '1,6p' .kittify/charter/charter.md    # version bumped past 1.1.5, reconciled not clobbered
test -f .kittify/charter/references.yaml && echo "references present"
spec-kitty doctor doctrine --json             # healthy after compile
```

## 8. Source doc is a faithful mirror + inventoried (SC-005)
```bash
test -f docs/development/quality-and-tech-debt-standing-orders.md && echo "source doc present"
PYTHONPATH=. python scripts/docs/check_docs_freshness.py --ci --link-check none   # inventory + frontmatter green
```

## Done-when
All 8 checks pass, `doctor doctrine` is healthy, the charter references the catfooding set with a complete closure, and #2196 reads as a functional epic (scope-tracker framing removed).
