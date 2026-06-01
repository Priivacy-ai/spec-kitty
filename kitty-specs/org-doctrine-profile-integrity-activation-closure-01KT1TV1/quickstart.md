# Quickstart: Org Doctrine Profile Integrity Activation Closure

Walkthroughs that demonstrate each scenario's acceptance signal. These double as the seeds for the ATDD acceptance tests (charter C-011). Commands run from the repository root unless noted.

## Prerequisites

```bash
cd <repo-root>
pip install -e .            # or the project's dev install
PWHEADLESS=1 pytest -q      # baseline; note the pre-existing dead-symbol gate red state (R-011)
```

---

## 1. Profile lineage via DRG (Scenario 1, FR-001/002/003)

```bash
# A fixture pack declares a profile-to-profile specializes_from EDGE in its DRG fragment.
spec-kitty doctrine pack validate --pack fixtures/lineage-pack
# Expect: validates; the specializes_from edge is accepted from the fragment.
```
Assert (test): delegation traversal (`edges_from(child, DELEGATES_TO)`) returns no lineage edge.

## 2. Invalid profiles are visible (Scenarios 2/3, FR-005..010)

```bash
# Pack with one profile authored against an old schema (now invalid).
spec-kitty doctor doctrine            # human: pack shown DEGRADED, invalid profile listed by layer/path/error
spec-kitty doctor doctrine --json | jq '.packs[].invalid_profiles'
# Expect: [{ "layer": "...", "path": "...", "profile_id": null|"...", "error_summary": "..." }]
```
Assert: valid profiles still listed; `healthy=false` derives from `valid==discovered`, not snapshot presence; completes ≤ 2s.

## 3. Unknown activation IDs fail closed (Scenario 3, FR-011/012, NFR-003)

```bash
cp .kittify/config.yaml /tmp/before.yaml
spec-kitty charter activate directive nonexistent-directive ; echo "exit=$?"
diff /tmp/before.yaml .kittify/config.yaml && echo "config UNCHANGED"
# Expect: exit!=0, message names kind+missing id+recovery; config identical.
```

## 4. No-cascade warning (Scenario 4, FR-013)

```bash
spec-kitty charter activate mission-type research
# Expect: activation succeeds + warning naming skipped referenced kinds and the recovery command.
```

## 5. Cascade scope (Scenario 5, FR-014)

```bash
spec-kitty charter activate mission-type research --cascade agent-profile,tactic
spec-kitty charter list
# Expect: only agent-profiles + tactics cascade-activated; list reflects exactly that scope.
spec-kitty charter activate mission-type research --cascade all   # explicit all-kind shorthand
```

## 6. Shared-safe cascade deactivation (Scenario 6, FR-015, C-005)

```bash
spec-kitty charter deactivate mission-type research --cascade all
# Expect: exclusively-referenced artifacts deactivated; shared artifacts SKIPPED with the
# still-referencing active artifact named. No shared artifact silently removed.
```

## 7. Runtime context populated (Scenario 7, FR-017/018, NFR-004)

```bash
spec-kitty implement WP01 --agent claude     # claim path builds OperationalContext
# Assert (test): active model/profile/role/activity populated; require_active_profile() raises
# ContextPreconditionError when absent, with zero new worktrees/status events on failure.
```

## 8. Agent-profile + full catalog selectors (Scenarios 8/9, FR-022..026)

```bash
spec-kitty charter context --include agent-profile:python-pedro            # renders profile (human)
spec-kitty charter context --include agent-profile:python-pedro --json     # same, JSON
spec-kitty charter list --all                                              # built-in + org + project, by layer
```

## 9. Augmentation across every kind (Scenario 10, FR-028..032)

```bash
# Fixture pack authors enhances/overrides EDGES (in DRG fragments) for a directive, toolguide,
# mission step contract, and mission type.
spec-kitty doctrine pack validate --pack fixtures/augment-all-kinds
# Expect: validates without same-ID advisory; auto-emits augmentation edges for DRG-resident kinds;
# step-contract/mission-type merges preserve action-sequence ordering + step I/O.
```

## 10. Field authoring is rejected (hard cutover, FR-028, OQ-2-i)

```bash
# An artifact YAML that still uses the old FIELD form:
#   enhances: some-built-in        # <-- now illegal
spec-kitty doctrine pack validate --pack fixtures/legacy-field-pack
# Expect: validation ERROR — relationships are authored in DRG fragments, not fields.
```

## 11. Templates discoverable & resolvable (Scenario 11, FR-033/034)

```bash
spec-kitty charter list --all | grep -i template            # template kind listed
spec-kitty charter context --include template:software-dev/spec
# Expect: resolves the mission-qualified template; same name in another mission is a distinct id.
```

## 12. Malformed pack config fails closed (Scenario 12, FR-035)

```bash
# Corrupt the charter-pack shape in .kittify/config.yaml, then:
spec-kitty charter context --action plan
# Expect: CHARTER_PACK_CONFIG_INVALID + remediation; no activation state mutated.
```

---

## Gate checks (run before marking the mission done)

```bash
PWHEADLESS=1 pytest tests/architectural/test_layer_rules.py        # doctrine !-> charter (post-relocation)
PWHEADLESS=1 pytest tests/architectural/test_no_dead_symbols.py    # in-scope symbols green (FR-035/036)
ruff check . && mypy src                                           # DIRECTIVE_030
# Bulk-edit: occurrence_map.yaml fully classified; implement gate passes for field-retirement WPs.
```
