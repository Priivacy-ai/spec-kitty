# Data Model — Sync CLI Degod (Wave 4)

No datastore change. The "entities" are the decomposition's structural units and the frozen contract.

## Structural units

| Unit | Kind | Role |
|------|------|------|
| `SyncPorts` | frozen dataclass + `default_ports()` | Bundles the injectable adapters (the `TasksPorts` shape). |
| `Render` port | adapter | Console emit + `--json` envelopes (reused Protocol). |
| `GitOps` / `Clock` / `FsReader` ports | adapter | Reused from `agent_tasks_ports.py`. |
| `DeliveryQueue` port | adapter (new) | SaaS dispatch/delivery. |
| `AuthorityGate` — **read** port | adapter (delegates to `preflight`) | Coord/owner READ authority. |
| `AuthorityGate` — **write** port | adapter (delegates to `sharing_client`) | share/unshare/opt-in/opt-out WRITE authority. **Distinct from the read port; never unified (INV-2).** |
| `AuthorityGate` — **admission** surface | adapter (delegates to `target_authority`) | Delivery-target/receiver ADMISSION (`_assert_event_sync_runtime_authority`, `_assert_delivery_target_matches_context`, `_resolve_gated_receiver`) — read-shaped, bound to the dispatch path. A **third** authority the two-bucket taxonomy omitted (architect A-2). Adapters **delegate** to canonical surfaces, never re-implement (DIRECTIVE_044). |
| `sync_status_core` / `sync_doctor_core` / `sync_dispatch_core` / `sync_purge_core` / `sync_store_report_core` | pure core | No-I/O decision/gate/summary logic returning dataclasses. |
| `cmd_*` shells + `cli/commands/sync.py` husk | shell | parse → open ports → call core → render; `app` host + re-export block. |
| Golden-CLI-characterization contract | frozen spec | The observable behavior of the 22 subcommands. |
| `_REQUIRED_SCOPE` (walker.py) | lookup table | Raw URN literals → named constants. |

## Invariants
- **INV-1 (behavior)**: the observable CLI contract of all 22 subcommands is byte-stable pre/post decomposition (golden test).
- **INV-2 (authority non-unification)**: the read, write, and delivery-admission authorities are distinct ports/classes with no shared authority class (arch-test-guarded). Non-unification is of **ports/classes, not call flows** — `_open_project_dispatch_runtime` and `opt_out` legitimately mix read+write in one flow and are frozen verbatim (C-007), not "purified".
- **INV-3 (boundary)**: new modules live under `specify_cli.sync.*`; zero `runtime` package import; no new `status`/`dossier`→sync edge.
- **INV-4 (seam)**: `sync.<name>` monkeypatch seams resolve after relocation; patched callees are reached through the shell (~60 patch-tests co-gate).
- **INV-5 (complexity)**: the 3 `# noqa: C901` are removed; zero net-new `C901`/`S3776` suppressions; each shell/core ≤ 15 complexity, each module ≤ 800 LOC.
- **INV-6 (frozen deferrals)**: no daemon reuse/kill/lifecycle behavior change; no env-var deletion; no `primary_feature_dir_for_mission` reference.
