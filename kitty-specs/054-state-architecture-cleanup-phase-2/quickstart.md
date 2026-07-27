# Quickstart: State Architecture Cleanup Phase 2

**Feature**: 054-state-architecture-cleanup-phase-2

## Verification Commands

After implementation, run these commands to verify the cleanup:

### Full test suite

```bash
cd /Users/robert/ClaudeCowork/Spec-Kitty-Cowork/spec-kitty
PWHEADLESS=1 pytest tests/ -q
```

### Per-area targeted tests

```bash
# Atomic write utility
pytest tests/specify_cli/test_atomic_write.py -v

# State contract consistency
pytest tests/specify_cli/test_state_contract.py -v

# Acceptance (regressions + dedup)
pytest tests/specify_cli/test_acceptance_regressions.py -v
pytest tests/specify_cli/test_canonical_acceptance.py -v

# Status emit (legacy bridge hardening)
pytest tests/status/test_emit.py -v

# Feature metadata (still uses atomic write after extraction)
pytest tests/specify_cli/test_feature_metadata.py -v

# Manifest / verify / diagnostics (active-mission removal)
pytest tests/cross_cutting/packaging/test_manifest_cli_filtering.py -v
pytest tests/test_dashboard/test_diagnostics.py -v

# Mission resolution
pytest tests/runtime/test_project_resolver.py -v
```

### Code quality

```bash
ruff check src/
ruff format --check src/
```

### Verify active-mission removal

```bash
# Should return zero hits in production code (only migrations and tests)
grep -r "active.mission" src/specify_cli/ --include="*.py" \
  | grep -v "__pycache__" \
  | grep -v "upgrade/migrations/"
```

### Verify .gitignore alignment

```bash
# references.yaml should be ignored
git check-ignore .kittify/constitution/references.yaml
# Should output: .kittify/constitution/references.yaml

# answers.yaml should NOT be ignored
git check-ignore .kittify/constitution/interview/answers.yaml
# Should output nothing (not ignored)
```

## Implementation Order

1. **WP01**: Shared atomic_write utility (no deps)
2. **WP02**: Active-mission fallback removal (no deps)
3. **WP03**: Dead mission code deletion (after WP02)
4. **WP04**: Atomic write conversion of 9 paths (after WP01)
5. **WP05**: Constitution Git policy (no deps)
6. **WP06**: Acceptance deduplication (no deps)
7. **WP07**: Legacy bridge hardening (no deps)
8. **WP08**: Vault notes update (after WP01-WP07)

Parallelization: WP01, WP02, WP05, WP06, WP07 can run concurrently.
