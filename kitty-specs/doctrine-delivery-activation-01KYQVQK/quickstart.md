# Quickstart — Verifying Doctrine Delivery Activation

All commands from a lane worktree use `uv run` (bare `python`/`pytest` import PRIMARY src). Run ONLY the
targeted node-ids below — NEVER the full `tests/architectural/` suite locally (it breaks the session; CI
owns the sweep).

## Verify the core delivery (IC-01)

```bash
# Profile channel now delivers suggests-linked doctrine with `when`:
uv run pytest tests/doctrine/drg/test_reachability.py -q
uv run pytest tests/charter/test_action_bundle_delivery.py tests/charter/test_every_load_delivery.py -q
# Ad-hoc check the delivered set for a PROFILE (NOT resolve_context, which is the action channel):
uv run python -c "from doctrine.drg.reachability import profile_channel_reachable; from doctrine.drg.migration import build_merged_graph; g=build_merged_graph(); print(sorted(profile_channel_reachable(g, {'agent_profile:architect-alphonso'})))"
# → expect paradigm:domain-driven-design + C4/refactoring artefacts (RED before FR-001). See contracts/suggests-delivery-walk.md A0-A2.
```

## Verify reconciliation (IC-05) — no silent golden movement

```bash
uv run pytest tests/doctrine/drg/test_reachability.py -q                        # pins reconciled
uv run pytest tests/architectural/test_no_authored_applies_edge.py -q           # histogram claims
uv run pytest tests/architectural/test_no_dead_symbols.py -q                    # allowlist shrunk, green
# Confirm every moved golden has a ledger row:
grep -n "deferred" docs/plans/doctrine/delivery-reachability-wiring-table.md
```

## Verify companion delivery (IC-03/IC-04)

```bash
# C4 templates reachable via template:instantiates from action:documentation/design; anti-patterns edge-reached:
uv run pytest tests/doctrine/drg/ -q -k "instantiates or anti_pattern or c4"
uv run spec-kitty doctrine validate 2>&1 | tail -20   # graph loads clean
```

## Verify hygiene items

```bash
# #3075 writer discovery gate + registration + Protocol typing:
uv run pytest tests/architectural/test_drg_writer_discovery.py -q
uv run mypy --strict src/charter/progressive_disclosure.py src/charter/context.py   # 0 ignores
# #3062 schema-error UX + asset source-path:
uv run pytest tests/doctrine/assets/ -q -k "source_path"
uv run spec-kitty doctrine validate   # a bad top-level key → structured issue, not a traceback
# #2532 extraction behaviour-preserving:
uv run pytest tests/charter/ -q -k "context or delivery or reference"
# fixture hermeticity (was local-only false-red):
uv run pytest tests/charter/test_every_load_delivery.py -q   # green even with ambient context-state.json
```

## Success signals

- SC-001 `architect-alphonso`/implementer channels deliver A/B/C/E with `when`.
- SC-002 wiring-table deferred set < 50, each move ledgered.
- SC-003 allowlist shrunk for wired symbols, `test_no_dead_symbols` green.
- SC-004 C4 templates + anti-patterns edge-reachable.
- SC-005 #3075/#3062/#2532 closable; discovery gate green + non-vacuous; consumer tests green; fixture
  false-red gone.
- SC-006 `ruff` + `mypy --strict` clean, net-removal of `# type: ignore`.
