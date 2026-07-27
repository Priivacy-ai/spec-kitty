# Quickstart — Validating Test Suite Acceleration

How to verify the mission's outcomes: faster runs **and** preserved coverage.

## 1. Establish baselines (before any change)

```bash
# Serial wall-clock baseline for the critical shard (charter) and the whole suite
.venv/bin/pytest tests/charter -m "fast and not windows_ci" -q -p no:cacheprovider --durations=25
time .venv/bin/pytest tests/ -q -p no:cacheprovider   # whole-suite serial baseline

# Record collected node counts per shard (coverage-neutrality reference)
.venv/bin/pytest tests/charter --collect-only -q | sort > /tmp/charter-serial.nodeids
```

## 2. Safe-now wave (IC-01) — expect ≥60s/push saved, zero coverage change

```bash
# Reduced ULID volume runs by default; full volume still reachable:
.venv/bin/pytest <ulid_test> -q                              # reduced (fast)
SPEC_KITTY_ULID_VOLUME_FULL=1 .venv/bin/pytest <ulid_test> -q  # full (nightly parity)

# Charter timing floors now pass under load (no flake):
.venv/bin/pytest tests/charter/test_integration.py -q
```

## 3. HOME isolation (IC-02) — the master enabler

```bash
# Regression test proves two workers get distinct homes and never touch real state:
.venv/bin/pytest tests/ -k worker_home_isolation -q
# Real home must be untouched after a parallel run:
ls -la ~/.spec-kitty 2>/dev/null   # mtime/inode unchanged vs. before the run
```

## 4. Collection equivalence + ratchet (IC-07) before any flip

```bash
# Equivalence: serial vs parallel must collect identical nodeids
.venv/bin/pytest tests/charter -n auto --dist loadfile --collect-only -q | sort > /tmp/charter-par.nodeids
diff /tmp/charter-serial.nodeids /tmp/charter-par.nodeids   # must be empty

# Ratchet: 3 consecutive green parallel runs
for i in 1 2 3; do .venv/bin/pytest tests/charter -m "fast and not windows_ci" \
  -n auto --dist loadfile -q || { echo "ratchet FAILED run $i"; break; }; done
```

## 5. Local parallel default (IC-06) — expect ≥2× on ≥4 cores

```bash
# Parallel suite (daemon/port tests run separately, serial):
PWHEADLESS=1 .venv/bin/pytest tests/ -n auto --dist loadfile -p no:cacheprovider \
  --deselect tests/sync/test_orphan_sweep.py
PWHEADLESS=1 .venv/bin/pytest tests/sync/test_orphan_sweep.py -n0 -q   # serial pass

# Compare wall-clock to the step-1 baseline: target ≥2× faster.
```

## 6. Coverage parity (NFR-004)

```bash
# New-code coverage ≥90%; overall coverage not below baseline.
.venv/bin/pytest <changed_paths> --cov=src --cov-report=term-missing -q
```

## Done criteria (maps to Success Criteria)

- SC-001/NFR-001: local full-suite ≥2× faster, real `~/.spec-kitty` untouched.
- SC-002/NFR-002: charter shard wall-clock ≤ ~5 min in CI.
- SC-003/NFR-004/NFR-007: identical collected nodeids; coverage % not lower.
- SC-004/NFR-005: 3 consecutive green parallel runs, no new flakes.
- SC-005/NFR-003: ≥60s/push removed by the safe-now wave.
- SC-006: regression test proves worker home isolation.
