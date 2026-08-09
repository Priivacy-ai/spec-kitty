# Approach Trace

## 2026-08-09 — Planning approach

1. Freeze the live store/sender census and reproduce cross-project open and implicit-grant failures.
2. Introduce one UUID-owned `sync.db`, one connection-owning unit of work, one grant writer, sequenced capture epochs, and a verifiable admission audience.
3. Move payload/status components behind the immutable context; add durable admission operations, history capabilities, and transport attempts without removing #3030 defenses.
4. Retire legacy grant writers and partition legacy state through daemon/current-writer layout participation, read-only WAL-aware snapshots, exact verification, atomic cutover, and no dual-read.
5. Serialize transport/result reconciliation against opt-out and publish atomic TTL-bound deny-only hints.
6. Consume the SaaS-owned per-write admission contract and split the six-project proof into conforming omission, bypass refusal, and stale-race parking.
7. Run reproducible process-warm/cold benchmarks plus full architecture, transaction, crash, mutation, cross-platform, contract, and issue-evidence gates before integration handoff.

The program orders the SaaS contract ahead of final core compatibility while allowing core store/migration work to proceed independently. Hosted mutation uses only a discovered Upsun branch environment; production remains read-only absent separate authority.
