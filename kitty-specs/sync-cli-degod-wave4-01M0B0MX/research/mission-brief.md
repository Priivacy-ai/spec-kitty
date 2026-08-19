# Mission Brief — Wave-4 sync degod: `cli/commands/sync.py` + `calibration/walker.py`

**Program:** degod/unshim, Wave 4 (CLI-split half). **File a #1797 child** (sanitization epic) — no dedicated issue exists.
Branch off `upstream/main` (`5662774daa`). Pre-spec grounding from a 4-lens research squad (decomposition · architectural-compat · mechanical-slices+golden-surface · scope/tracking). Feeds `/spec-kitty.specify`.

---

## 1. Scope (operator: "all 3 files; ensure compatibility to architectural design")

**IN:**
- **Slice 1 — `calibration/walker.py`** (533 LOC): complete the partial named-constant set; clear 14 `S1192` duplicated-URN-literal smells. Mechanical, single-file, behavior-preserving.
- **Slice 2 — `cli/commands/sync.py` Tier 1**: mechanical smell sweep (nested ternaries, literal hoists, malformed suppressions) — behavior-preserving.
- **Slice 3 — `cli/commands/sync.py` Tier 2**: the **CLI-split degod** — decompose the 6,332-LOC god-module into ports + pure cores + thin command shells, retiring the **three `# noqa: C901`** (`sync_workspace` L2988, `status` L5387 cc 90, `doctor` L5991 cc 73).

**OUT (sequenced Wave-4 follow-on, do NOT fold):** the `sync/emitter.py` (2671) / `transport_attempts.py` (2416) / `queue` / `daemon.py` (1527) **adapter-consolidation** — a *different* refactor shape gated on OPEN seams this mission doesn't need (#2173 Phase-2 DI, WS4 daemon-identity, WS6 versioned-contract ADR). Folding it in makes the mission unbounded.

## 2. Architectural-compatibility checklist (the operator's first-class constraint)

Every WP is bound by these. Source: `docs/plans/refactor/degod-unshim-roadmap.md:59-65` + the arch-gate suite.

| # | Invariant | Concrete rule for this degod |
|---|-----------|------------------------------|
| A | **CoordRead ≠ CoordWrite authority** (never unify) | `status`/`doctor`/`_require_daemon_owner_coherence` READ; `share`/`unshare`/`opt-in`/`opt-out` WRITE → **separate ports/adapters**; no unified `SyncAuthority`. |
| B | **Ports on the shell, not the frozen `MissionExecutionContext`; one adapter per port** | Inject git/subprocess, clock, ledger/queue, SaaS HTTP, renderer as default-param ports (the `TasksPorts`/`default_ports()` shape, `agent_tasks_ports.py:447/456`). Reuse `Render`/`GitOps`/`Clock`/`FsReader`; add sync-specific `DeliveryQueue`, `AuthorityGate` (two-authority). |
| C | **Golden-CLI-char test FIRST** — *replaces* file:line ratchets (DIR-041) | Land a characterization test freezing all 22 commands' flags/exit-codes/`--json` **before any extraction**. MUST NOT mutate the positional-anchor allowlists (`test_ratchet_positional_anchor_ban.py` stands watch). |
| D | **Ambiguity → typed error, never silent** | Extracted target/project resolvers raise typed errors on ambiguity — but the **coord exit-0 silent-skip** arm (SaaS-disabled guard) is a *documented behavior to freeze*, not an ambiguity swallow. Distinguish them. |
| E | **Stay OUT of `primary_feature_dir_for_mission`** (FR-011 recursion) | sync is currently clean (grep-verified); keep it — mission-dir composition goes through the sanctioned resolver seam only. |
| F | **Shared-package boundary** | Cores/ports live under **`specify_cli.sync.*`** — NOT `runtime` (layer order forbids upward import; `test_layer_rules.py`), NOT a new top-level `src/` package (`test_no_unregistered_src_packages`). Keep the zero-`runtime`-import boundary; consume events/tracker only via the existing public adapter seam (no `_internal`, no SDK re-export — `test_shared_package_boundary.py`, `test_events_tracker_public_imports.py`). |
| G | **Sync writer census** | Extracted consent/grant writers stay inside the census roots (`src/specify_cli/sync/` + `cli/commands/sync.py`); a new/renamed writer registers as census growth (`test_sync_writer_census.py`, #3108). |
| H | **status→sync / dossier→sync boundary** (#862) | sync may import status/dossier reads; they must never import the new sync modules. |
| I | **Complexity ≤15, no new suppressions** | Retire the 3 `# noqa: C901` via extraction (lookup/build/emit phases). Preserve the pre-existing justified `BLE001`/`S105`/`S608`/`PLC0415`; add none. |

## 3. Wave-4 prerequisite ruling (in-scope vs deferred)

- **IN:** the CLI-split + adapter-consolidation of `sync.py` (needs neither WS4 nor WS6 — it is "adapter-shaped, safe last"); the golden-char harness; retiring the 3 `C901`; the walker tidy.
- **DEFERRED — env-var DELETION → WS6.** WS6 versioned-contract policy ADR is not yet written. This mission may produce the `SPEC_KITTY_*` **census/inventory only**; delete nothing. (Retire-candidates flagged: `SPEC_KITTY_SYNC_READONLY_IDENTITY`, `SPEC_KITTY_NO_AUTO_CUTOVER`.)
- **DEFERRED — daemon-lifecycle BEHAVIOR change → WS4.** Characterize + wrap the daemon surface (`_require_daemon_owner_coherence` L1357, `sync_workspace` D-3 checks, orphan scan L5232, cutover-protocol L4706) behind read/write ports and **freeze current behavior**; do NOT alter reuse/kill/lifecycle semantics (WS4/C-007 territory).

## 4. Decomposition plan (feeds the WP structure)

Target layout — a `sync_commands/` package under `specify_cli.cli.commands` (or nest cores in `specify_cli.sync.*`), mirroring the `runtime_bridge` (#2531) six-seam split (the closest analogue: large, I/O-heavy, many monkeypatched privates) and the coord-authority trio (#2464/#2465/#2508) shell+core+executor pattern:

```
__init__.py            # `app` Typer + guarded re-export/monkeypatch-compat block (husk)
sync_ports.py          # SyncPorts frozen dataclass + default_ports(); reuse Render/GitOps/Clock/FsReader; + DeliveryQueue, AuthorityGate
sync_status_core.py    # PURE: build_status_rows() + evaluate_boundary_coherence()->BoundaryVerdict
sync_doctor_core.py    # PURE: build_doctor_report()->DoctorReport
sync_dispatch_core.py  # PURE: batching + exit-code decisions
sync_purge_core.py     # PURE: census differentials + verdict (self-contained subsystem L3490-4358)
sync_store_report_core.py  # PURE: per-project-store/consent/tracker summary
sync_render.py         # ADAPTER: all Console emit + JSON envelopes (Render port)
sync_runtime.py        # ADAPTER: runtime-open/lifecycle + config I/O
sync_dispatch_exec.py  # ADAPTER: SaaSQueue delivery
sync_purge_exec.py     # ADAPTER: census readers + purge executors
sync_authority.py      # ADAPTER: gate/authority — two-authority (read vs write) preserved
cmd_*.py               # thin shells: parse args -> open ports -> call core -> render
```

**WP ordering (≈10 WPs — consistent with the tasks.py degod precedent, 10/10):**
- **WP00 (campsite, tidy-first):** `walker.py` S1192 constant-completion + `sync.py` Tier-1 mechanical + pytest-marker/dead-symbol/golden-count tidy. Behavior-preserving.
- **WP01 (blocks all):** golden-CLI-characterization harness — freeze 22 commands' flags/exit-codes/`--json` incl. the coord exit-0 silent-skip and `status --check` exit-2 arms; close the GAPs (§5). Model on `tests/characterization/` (trio) + the `runtime_bridge` parity-oracle + AST compat-surface guard.
- **Parallel adapter extractions:** WP02 `sync_render`, WP03 `sync_runtime`+config, WP04 `sync_purge_*` (self-contained; drops `purge` cc 26); then WP05 `sync_store_report`+`sync_authority`, WP06 `sync_dispatch_*`.
- **Sequential monster degods:** **WP07 `status`** (cc 90 → build/gate cores + shell), **WP08 `doctor`** (cc 73), **WP09 `sync_workspace`** — each **retires a `# noqa: C901`**.
- **WP10:** command-shell split + husk finalize (`__init__.py` re-export block, `__module__` kept, lazy accessors for monkeypatched privates).

## 5. Golden-test-first GAPs (freeze BEFORE Tier-2 extraction)

Most subcommands already have `CliRunner` golden coverage. Priority freeze list (gaps):
1. **`workspace`** — no CLI golden at all (and a `C901` target).
2. **`status` full human-render** (non-`--check`, the cc-90 build path) — only `--check --json` is well-covered.
3. **`doctor`** — pin the non-json render + each `--json` branch as snapshots.
4. **`diagnose --json`** — broaden beyond the single existing test.
The `status --check --json` JSON contract is specified at `kitty-specs/mvp-cli-sync-boundary-completion-01KRX11M/contracts/sync-status-output.md`.

## 6. Mechanical-slice findings (with the drift caveat)

**⚠️ `sync.py` has drifted from the 2026-08-12 Sonar snapshot** the scoping doc was written against (6,261→6,332 LOC); several Tier-1 findings are **already banked**. `walker.py` has NOT drifted.

**walker.py (Slice 1):** complete the constant set at L48-57 — add directive URNs `DIRECTIVE_024/025/028/029/030/034` (3-4× each), the tactic/toolguide URNs (`acceptance-test-first`, `quality-gate-verification`, `stopping-conditions`, `autonomous-operation-protocol`, `change-apply-smallest-viable-diff`, `tdd-red-green-refactor`, `efficient-local-tooling`, `problem-decomposition`), the action-URN prefixes (`software-dev/implement|specify|retrospect`), and the agent-profile URNs (`researcher-robbie` 8×, `curator-carla` 6×); **fix 2 re-inlined existing constants** (`DIRECTIVE_010` L150, `DIRECTIVE_037` L157). Guard: `tests/calibration/test_walker.py` (frozensets resolve byte-identical).

**sync.py Tier 1 (Slice 2) — re-verify against a fresh Sonar run; the exact snapshot findings don't all reproduce by line:**
- **S3358 (5, live):** L184, L2209, L2212, L4640, L6043 (L184≡L6043 → shared `_depth_color(pct)` helper kills both).
- **S1192 (partial):** `"bold yellow"` const exists but re-inlined at L6217/L6286; `"[dim]Unavailable[/dim]"` raw ×4 at L2200-2203; `":memory:"` **absent** (resolved).
- **S7632:** candidates are em-dash `# noqa … — …` at L1865/L1889/L3694/L3720 + L4799; verify vs fresh Sonar.
- **S5713:** **no `class X(Exception)`** — resolved.

## 7. Test hazards (carry into every WP)

- **Real-port/daemon tests run serially `-n0`** (ports 9400-9449 not HOME-isolated). Parallel = `--dist loadfile`, never bare `load`.
- **`SAAS_SYNC_ENV_VAR` (`SPEC_KITTY_ENABLE_SAAS_SYNC`) must be `1`** to exercise the non-skip render arms (autouse `_enable_saas_flag` fixture); else you hit the exit-0 silent-skip.
- **`SPEC_KITTY_SYNC_DISABLE`/`SPEC_KITTY_SYNC_MINIMAL_IMPORT`** disable sync AND skip the pre-review gate — config, not code faults.
- **`logged_out_on_connected_teamspace`** is a CI-env red, not a code red.
- **HOME isolation mandatory** (pin `HOME`/`LOCALAPPDATA` to `tmp_path`); **subprocess strict-JSON tests need `PYTHONPATH=<worktree>/src`** (+ the shadow-venv PATH footgun — prepend `.venv/bin`).
- **Never run the full suite** (~1h, breaks the session); target `tests/sync/`, `tests/cli/commands/test_sync_*`, `tests/calibration/`, `tests/characterization/`. CI is the release authority.

## 8. Arch-gate baselines to update (campsite order: tidy-first → golden-char → functional)

Dead-symbol/dead-module baselines (`test_no_dead_symbols.py`/`test_no_dead_modules.py` — every new public symbol needs a live importer); `_baselines.yaml` ratchet (growth fails, shrink warns; sync entries L400-445); `_golden_count_baseline.json` (`tests/sync` ceiling 75 — use frozenset-equality not `len==N`, or the `# golden-count:` escape hatch); CLI-count baseline (`test_real_typer_app_visible_count_within_tolerance` — a pure split shouldn't move it; re-pin vs `upstream/main` merge-base, NOT fork origin); `test_sync_writer_census.py`; correct pytest markers (post-Wave-0, mis-marked `unit`/`contract` tests run **nowhere**). Pre-push: `pytest tests/architectural/test_no_legacy_terminology.py` (sync has user-facing prose).

## 9. Tracking & scope boundary

- **File a #1797 child** scoped to walker + sync Tier-1/Tier-2 CLI-split. Advances #1797/#2173; closes no epic; does not close #2293 (category_b).
- Roadmap "link #612/#613" note is **stale** (both CLOSED in Wave 2∥). #2164 CLOSED. WS4 reaper #2261 CLOSED (reuse/kill deferred, C-007).
- **PR collisions: none** — target files collision-free (adjacent sync PRs #2890/#3544/#3545/#3529/#3554 touch other files).

## 10. Risks

- **Golden-test coverage gaps (§5)** are the extraction risk — the cc-90 `status` full-render and `workspace` are under-characterized; freeze them first or extraction can silently change behavior.
- **Monkeypatch-compat** — many `_*` privates are patched by tests; the husk must keep `tasks._name` / `sync._name` seams resolvable (runtime_bridge's guarded re-export + lazy-accessor pattern).
- **Two-authority discipline (A)** is the load-bearing invariant — a careless "SyncAuthority" merge is the #2160-class regression.
- **Baseline drift** — re-pin counts vs `upstream/main`, not stale fork origin.
</content>
