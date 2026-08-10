# Quickstart: per-project sync consent ledgers

This mission verifies that hosted sync is default-denied and project-scoped.

## Operator setup

Use isolated state for tests and demos:

```bash
export SPEC_KITTY_HOME="$(mktemp -d)"
unset SPEC_KITTY_ENABLE_SAAS_SYNC
```

Do not use the operator's real `~/.spec-kitty` queues for migration tests.

## Expected behavior

1. A project with no explicit sync consent cannot send retained events, body uploads, daemon batches, or acknowledgements.
2. A project that opts in can send only its own project rows.
3. A second project on the same machine remains denied until it explicitly opts in.
4. `SPEC_KITTY_ENABLE_SAAS_SYNC` may expose or disable rollout surfaces but is not consent.
5. Legacy ambiguous rows remain local-only/refused until project ownership is proven.

## Evidence to collect

- Focused pytest output for each WP.
- Two-project integration proof.
- Migration count summary: imported, refused, ambiguous, unchanged.
- Status/doctor output showing project consent and ledger state.
- Closure dossier and GitHub comments for #3262/#585.
