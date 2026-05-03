# Quickstart — Mission Registry and API Boundary Doctrine

A copy-pasteable verification walk-through for the artefacts this mission ships. Use this after the implementation lands to confirm everything is wired correctly.

## Prerequisites

- `feature/650-dashboard-ui-ux-overhaul` checked out at the merge commit for this mission.
- `uv sync --frozen`.
- Python 3.13.12 (or whichever pyenv has installed from the `.python-version` priority list).

## Step 1 — Run the full test suite

```bash
.venv/bin/python -m pytest tests/test_dashboard/ tests/architectural/ tests/sync/test_daemon_intent_gate.py -q --timeout=120
```

Expected: 361+ passed (baseline 361 + new tests). The new tests:
- `tests/test_dashboard/test_scanner_entrypoint_parity.py` (boyscout baseline)
- `tests/test_dashboard/test_mission_registry.py` (registry unit tests)
- `tests/architectural/test_transport_does_not_import_scanner.py`
- `tests/architectural/test_url_naming_convention.py`
- `tests/architectural/test_resource_models_have_links.py`

## Step 2 — Confirm the architectural boundary holds

```bash
.venv/bin/python -m pytest tests/architectural/test_transport_does_not_import_scanner.py -v
```

Expected: 3 tests pass (main scan + positive meta-test + negative meta-test).

To verify the test catches violations, temporarily add to `src/dashboard/api/routers/features.py`:

```python
from specify_cli.dashboard.scanner import scan_all_features  # noqa: F401
```

Re-run the test. It should fail with a message naming `features.py` and the directive. Revert.

## Step 3 — Inspect the doctrine artefacts

```bash
ls src/doctrine/directives/shipped/api-dependency-direction.directive.yaml
ls src/doctrine/directives/shipped/rest-resource-orientation.directive.yaml
ls src/doctrine/paradigms/shipped/hateoas-lite.paradigm.yaml
```

Each file should exist and pass the doctrine schema test:

```bash
.venv/bin/python -m pytest tests/doctrine/ -q
```

## Step 4 — Run the dashboard with the registry wired in

```bash
.venv/bin/spec-kitty dashboard --kill 2>/dev/null
.venv/bin/spec-kitty dashboard --transport fastapi --port 9337 --open
```

Browse `http://127.0.0.1:9337/api/features` — same JSON shape as before, but the backing data flow is now via the registry. Browse `http://127.0.0.1:9337/api/kanban/<any-mission-id>` — same shape.

## Step 5 — Verify syscall reduction

```bash
# Find the dashboard PID
DASHBOARD_PID=$(pgrep -f "spec-kitty dashboard" | head -1)

# Trace open() syscalls for 30 seconds while curl-polling /api/features
strace -c -e trace=openat,stat,statx -p "$DASHBOARD_PID" 2>/tmp/strace-after.txt &
STRACE_PID=$!

for _ in $(seq 30); do
    curl -s http://127.0.0.1:9337/api/features > /dev/null
    sleep 1
done

kill $STRACE_PID 2>/dev/null
wait $STRACE_PID 2>/dev/null
cat /tmp/strace-after.txt | tail -20
```

Expected (NFR-001): the `openat` count divided by the request count (30) is ≤ 5 in steady state. Compare to the pre-mission baseline (~720 `openat` per request) recorded in WP06's release-checklist artefact.

The bench script `scripts/bench_registry_syscalls.py` automates this comparison and writes a JSON report.

## Step 6 — Verify the boyscout WP01 artefacts

```bash
# Scanner entry-point audit table is present in the docstring:
grep -A 30 "Entry-point audit" src/specify_cli/dashboard/scanner.py | head -35

# No assume-unchanged files:
git ls-files -v | grep "^h " | grep "kitty-specs/" || echo "(none — clean)"

# Scanner parity baseline test exists and passes:
.venv/bin/python -m pytest tests/test_dashboard/test_scanner_entrypoint_parity.py -v
```

## Step 7 — Check the ADR is now Accepted

```bash
head -10 architecture/2.x/adr/2026-05-03-1-dashboard-mission-registry-and-cache.md
```

Expected: `**Status**: Accepted` (was `Proposed` before this mission).

```bash
grep "2026-05-03-1" architecture/2.x/adr/README.md
```

Expected: the README index row reads `Accepted`.

## Step 8 — CLI parity

```bash
.venv/bin/spec-kitty dashboard --json | jq '.missions | length'
```

Expected: same count as `curl http://127.0.0.1:9337/api/features | jq '.features | length'`. Both consumers now read through the registry.

## Step 9 — Stop the dashboard

```bash
.venv/bin/spec-kitty dashboard --kill
```

## Troubleshooting

- **`/api/features` returns 500**: most likely a `MissionRegistry` cache-key bug. Check the dashboard process logs (or run `--transport fastapi` in the foreground for a tracebask).
- **Architectural test fails after a refactor**: a router added a forbidden import. The failure message names the file and the import; switch to the registry per the contract migration guide in `contracts/registry-interface.md`.
- **Bench script reports > 5 syscalls per request**: the registry's cache-stale check is leaking; check that `list_missions()` is called on a `MissionRegistry` instance held on `app.state` (not constructed per-request).
- **Doctrine test fails on `referenced-tests:` field**: the schema needs the additive extension promised in WP02. Check that the schema PR landed.
