# Implementation Plan: Sync CLI Degod — Wave 4

**Branch**: `refactor/wave4-sync-degod` | **Date**: 2026-08-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/sync-cli-degod-wave4-01M0B0MX/spec.md`

## Summary

Decompose `cli/commands/sync.py` (6,332 LOC, 22 subcommands, 3× `# noqa: C901`) into injectable
ports + pure decision cores + thin command shells, behind a golden-CLI-characterization test that
freezes the observable behavior first — and complete `calibration/walker.py`'s named-constant set as
a standalone campsite slice. Zero behavior change. The approach follows the established degod
template (`runtime_bridge` #2531 six-seam split — closest analogue; coord-authority trio
#2464/#2465/#2508 shell+core+executor; `agent_tasks_ports.py` port set), stays within the program's
non-negotiable invariants (golden-first, ports-on-shell, CoordRead≠CoordWrite, boundary placement,
ratchet non-mutation), and explicitly defers env-var deletion (WS6) and daemon-lifecycle behavior
(WS4). Grounding: [research/mission-brief.md](./research/mission-brief.md); post-spec squad findings
folded into the spec ([research/squad-findings-post-spec.md](./research/squad-findings-post-spec.md)).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: None new. Reuses existing internals — `typer`, `rich`, `specify_cli.sync.*`, `specify_cli.tracker`, `specify_cli.auth`, `specify_cli.delivery`, and the `agent_tasks_ports.py` port protocols (`Render`/`GitOps`/`Clock`/`FsReader`).
**Storage**: N/A (SQLite ledger/queue + YAML config reached only through the existing sync runtime adapters; no schema change).
**Testing**: `pytest` targeted at `tests/sync/`, `tests/cli/commands/test_sync_*`, `tests/calibration/`, and a new `tests/characterization/test_sync_*`; the ~60 existing `sync`-monkeypatch tests as an explicit co-gate; `ruff` + `mypy --strict` on changed files. Real-port/daemon tests run serially (`-n0`); `SPEC_KITTY_ENABLE_SAAS_SYNC=1` to exercise non-skip render arms.
**Target Platform**: Spec Kitty CLI (Linux/macOS).
**Project Type**: single (Python package under `src/specify_cli/`).
**Performance Goals**: N/A — behavior-preserving refactor; no runtime-path change.
**Constraints**: complexity ≤ 15 (retire the 3 `# noqa: C901`; zero net-new `C901`/`S3776` suppressions); cores/ports under `specify_cli.sync.*` (never `runtime`/new-top-package; no new `status`/`dossier`→sync edge); ports injected on the shell, one adapter per port; CoordRead≠CoordWrite (two ports, arch-test-guarded); golden-CLI-char test lands first without mutating DIR-041 ratchets; no daemon-lifecycle behavior change, no env-var deletion, no `primary_feature_dir_for_mission` reference.
**Scale/Scope**: ~10 WPs decomposing 6,332 LOC + the walker/Tier-1 campsite (consistent with the `tasks.py` degod precedent, 10/10 WPs on a smaller file).

**Supply-chain security**: Not applicable — no dependency is added, upgraded, or removed in any ecosystem. No `research.md` supply-chain decision or lifecycle-script review is required.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Single canonical authority** (`DIRECTIVE_044`): PASS — reuse the existing `agent_tasks_ports.py` port protocols and the `runtime_bridge`/trio patterns; do not fork a second port abstraction.
- **Architectural alignment / gate discipline** (`DIRECTIVE_001`/`043`): PASS — the decomposition is bound by the layer/boundary/ratchet/writer-census gates (NFR-004, C-001) and adds a new two-authority arch-test (FR-004); it retires suppressions rather than adding them.
- **ATDD-first** (`acceptance-test-first`): PASS — the golden-CLI-characterization harness lands **before** any extraction (FR-001, C-003) and every extraction keeps it green.
- **Campsite discipline** (`DIRECTIVE_025`): PASS — the mechanical campsite (walker.py + sync.py Tier-1 + marker/dead-symbol/golden-count tidy) lands **first**, tidy-first before the structural change.
- **Terminology canon**: PASS — sync has user-facing prose; the terminology guard is a pre-push gate (NFR-004).

No violations → Complexity Tracking is empty.

## Project Structure

### Documentation (this mission)

```
kitty-specs/sync-cli-degod-wave4-01M0B0MX/
├── plan.md, spec.md
├── research/
│   ├── mission-brief.md              # 4-lens grounding squad
│   ├── squad-findings-post-spec.md   # post-spec adversarial squad
│   ├── env-census.md                 # FR-007 (produced during implement)
│   └── (research.md consolidation)
├── data-model.md, quickstart.md
├── contracts/
│   └── sync-cli-characterization-contract.md
└── tasks.md (/spec-kitty.tasks — later)
```

### Source Code (repository root)

```
src/specify_cli/cli/commands/sync.py        # SHRINKS to thin command shells + husk re-export block
src/specify_cli/sync/                        # NEW cores + ports live here (specify_cli.sync.*):
  sync_ports.py                              #   SyncPorts frozen dataclass + default_ports()
  sync_status_core.py sync_doctor_core.py    #   PURE decision/gate cores
  sync_dispatch_core.py sync_purge_core.py sync_store_report_core.py
  sync_render.py sync_runtime.py             #   ADAPTERS (Console emit; runtime/config I/O)
  sync_dispatch_exec.py sync_purge_exec.py sync_authority.py   # ADAPTERS (delivery; census readers; read/WRITE authority — two ports)
src/specify_cli/calibration/walker.py        # constant-completion (campsite)

tests/characterization/test_sync_*.py        # NEW golden-CLI harness (freeze 22 commands)
tests/architectural/test_sync_two_authority.py  # NEW arch-test (FR-004)
tests/sync/, tests/cli/commands/test_sync_*, tests/calibration/  # existing suites stay green
```

**Structure Decision**: single package. New cores/ports nest under `specify_cli.sync.*` (a legal
inbound direction — `cli.commands.sync` already imports `specify_cli.sync.consent`), never `runtime`
or a new top-level package (C-001). **The `@app.command`-decorated thin shells STAY in
`cli/commands/sync.py`** (the seam anchor — Typer binds the callback at decoration time, so moving a
decorated command would change which callable Typer invokes; a risk the `runtime_bridge` #2531
precedent never exercised). The extracted logic goes to `specify_cli.sync.*` cores/adapters; the
husk keeps the `app` host + a guarded re-export block, and relocated shells reach any monkeypatched
callee via **late-bound `sync_module.<name>` attribute access** (never `from .sync import <name>`
early-binding) so `monkeypatch.setattr("…commands.sync.<name>", …)` still intercepts (C-005). The
husk is measured against a separate, larger LOC ceiling than the extracted `sync_*` modules (SC-001's
≤800 applies to the focused modules, not the app-host husk).

## Complexity Tracking

*No Charter Check violations — table intentionally empty.*

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into executable WPs.

### IC-01 — Mechanical campsite (lands first, standalone)

- **Purpose**: Clear the litter on the target surfaces before structural change: complete `walker.py`'s named-constant set (S1192 → 0) and fix `sync.py` Tier-1 smells (S3358 ternaries, S1192 re-inlines, S7632 suppression-format), plus pytest-marker / dead-symbol / golden-count tidy.
- **Relevant requirements**: FR-005, FR-006, NFR-003.
- **Affected surfaces**: `src/specify_cli/calibration/walker.py` (independent — no degod dep); `src/specify_cli/cli/commands/sync.py` (Tier-1 only).
- **Sequencing/depends-on**: split into two — `walker.py` is fully independent (day-one, parallelizable); `sync.py` Tier-1 lands **after** the golden net (IC-02) and before the degod churn (WP-translation guard #5), so its `S3358` ternary extractions are under characterization protection.
- **Risks**: `walker.py` guard is `tests/calibration/test_walker.py` (frozenset-equality); Tier-1 must correct suppression *format*, never delete a guarded `except` (FR-006); re-verify the finding set against a fresh Sonar run (drift caveat).

### IC-02 — Characterization safety net (blocks all extraction)

- **Purpose**: Freeze the observable behavior before any structural change — the golden-CLI-characterization harness over all 22 subcommands (flags/exit-codes/`--json`, the coord exit-0 silent-skip arm, `status --check` exit-2), with the under-characterized commands (`status` full human-render, `doctor` branches, `sync_workspace`, `diagnose --json`) each frozen before their own extraction; establish the ~60 patch-tests as a co-gate baseline; add the FR-004 two-authority arch-test.
- **Relevant requirements**: FR-001, FR-004, NFR-001, C-003.
- **Affected surfaces**: `tests/characterization/test_sync_*.py` (new), `tests/architectural/test_sync_two_authority.py` (new).
- **Sequencing/depends-on**: precedes IC-03/IC-04/IC-05; the two-authority arch-test may land with the authority-port extraction but its intent is defined here.
- **Risks**: golden must not be satisfied by `--json`-happy-path only (FR-001); must not mutate DIR-041 ratchets (C-003); enable `SPEC_KITTY_ENABLE_SAAS_SYNC=1` to reach non-skip arms; HOME isolation + `PYTHONPATH=<worktree>/src` for subprocess strict-JSON.

### IC-03 — Port/adapter seam (injectable infra)

- **Purpose**: Extract the injectable adapters behind a `SyncPorts` frozen dataclass + `default_ports()` (the `TasksPorts` shape): `Render` (Console + JSON emit), `sync_runtime`/config I/O, delivery/`DeliveryQueue` port (the injectable seam only — **not** the `emitter`/`transport_attempts`/`queue` internals, which are out of scope), census readers, and the authority adapters. Reuse `Render`/`GitOps`/`Clock`/`FsReader`.
- **Authority is THREE surfaces, not two** (architect finding A-2): (1) coord/owner **READ**, (2) share/unshare/opt-* **WRITE**, (3) delivery-target/receiver **ADMISSION** (`_assert_event_sync_runtime_authority` L620, `_assert_delivery_target_matches_context` L653, `_resolve_gated_receiver` L799) — read-shaped but bound to the dispatch path. The invariant is non-unification of **ports/classes**, not of call flows: `_open_project_dispatch_runtime` and `opt_out` legitimately mix read+write and are frozen verbatim (C-007), not purified. `sync_authority.py` adapters **delegate** to the canonical surfaces (`preflight.run_preflight`, `sharing_client`, `target_authority`) — they do not re-implement them (DIRECTIVE_044). The FR-004 two-authority arch-test scopes its discriminator to an explicit symbol/module allowlist (distinct from `test_2093_authority_invariant.py`).
- **Relevant requirements**: FR-002, FR-004, C-001, C-002, C-007.
- **Affected surfaces**: `specify_cli/sync/sync_ports.py`, `sync_render.py`, `sync_runtime.py`, `sync_dispatch_exec.py`, `sync_purge_exec.py`, `sync_authority.py`.
- **Sequencing/depends-on**: IC-02 (golden green first). The adapter extractions **serialize on `sync.py`** — they are NOT parallel lanes (each shrinks the same file; see WP-translation guards). The purge subsystem (self-contained L3490-4358; pedro-confirmed disjoint — own `_RawCensus`/openers) is the one genuinely-isolatable extraction.
- **Risks**: one adapter per port; each relocated consent/grant writer needs a **1:1 census-key swap** (drop old `relpath::qualname::…` key, add equivalent — never a net addition; `test_sync_writer_census.py`); patched callees reached via late-bound `sync_module.<name>` (C-005); no new `status`/`dossier`→sync edge (C-001).

### IC-04 — Pure decision cores (stub-testable)

- **Purpose**: Extract the no-I/O decision logic — `sync_status_core` (row build + `evaluate_boundary_coherence` gate), `sync_doctor_core` (report build), `sync_dispatch_core` (batching + exit-code map), `sync_purge_core` (census differentials + verdict), `sync_store_report_core` (per-project-store/consent/tracker summaries) — as pure functions returning dataclasses (the `gates_core.py` shape). Each gets focused unit tests.
- **Relevant requirements**: FR-002, NFR-002.
- **Affected surfaces**: `specify_cli/sync/sync_*_core.py` (new pure modules).
- **Sequencing/depends-on**: consumes IC-03 port types; feeds IC-05. The three shared render helpers `_render_per_project_store` (used by **both** `status` L5583 and `doctor` L6200), `_render_consent_readability`, `_render_tracker_egress` each currently **print AND mutate `issues`**; their compute-half lands in `sync_store_report_core` **before** both the status and doctor degods, and the shells call the render-half — decoupling status↔doctor (pedro finding Pd-2).
- **Risks**: the `status`/`doctor` cores **do not pre-exist** — I/O is interleaved between row emissions (`_check_server_connection` L5524, `scan_sync_daemons` L5541 run mid-table-build). Extraction is a **gather-all-I/O → pure core → render** *restructure*, not a relocate (architect A-1); the full-human-render golden freeze (FR-001, not `--json`-only) is the load-bearing safety net for this reorder. Cores must be truly I/O-free (no `Console`/`print`); every new branch/helper needs a focused test in the same WP.

### IC-05 — Monster degods + command shells (retire the C901s)

- **Purpose**: Rewrite `status` (cc 90), `doctor` (cc 73), and `sync_workspace` as thin shells (parse → open ports → call core → render), **retiring the three `# noqa: C901`**; move the remaining command bodies into `cmd_*.py` shells.
- **Relevant requirements**: FR-003, NFR-002, SC-001.
- **Affected surfaces**: `cli/commands/sync.py` command bodies → `specify_cli/sync/cmd_*.py`; the C901 sites.
- **Sequencing/depends-on**: `status`/`doctor` depend on IC-03 (render/authority/store-report) + IC-04 (status/doctor cores) + IC-02 (their golden snapshots frozen first). `sync_workspace` depends on IC-03 (render/runtime) — its daemon read/guard code relocates intact (C-004), behavior pinned by the golden test.
- **Risks**: each shell must carry no decision logic (SC-001); daemon reuse/kill/lifecycle behavior unchanged (C-004).

### IC-06 — Husk finalize + governance closeout

- **Purpose**: (husk *scaffold* — the guarded re-export block + late-bound convention — lands EARLY as a prerequisite edge, WP-translation guard #2; this concern is the husk *finalize*.) Finalize the `cli/commands/sync.py` husk (Typer `app` + guarded re-export/lazy-accessor block so `sync.<private>` seams resolve — C-005); re-pin the arch-gate baselines against `upstream/main` (dead-symbol/module, ratchet, golden-count, CLI-count, writer-census); produce `docs/plans/code-quality/sync-env-census.md` (inventory only, set-unchanged guard — FR-007); file the deferred follow-on issue(s) at merge (FR-008).
- **Relevant requirements**: FR-007, FR-008, NFR-004, C-005.
- **Affected surfaces**: `cli/commands/sync.py` (`__init__`/husk), `tests/architectural/_baselines.yaml` + baseline artifacts, `docs/plans/code-quality/sync-env-census.md`, the tracker.
- **Sequencing/depends-on**: last (after IC-03/04/05 land); the census can be produced any time.
- **Risks**: re-pin against the true merge-base (`upstream/main`), not stale fork origin; if the merge-base surfaces pre-existing red, open a tracking issue per DIR-013 before treating it as baseline; the husk re-export is necessary-not-sufficient — verify the ~60 patch-tests green (NFR-001).

## WP-translation guards (post-plan adversarial squad)

The IC map is *concerns*, not work packages. When `/spec-kitty.tasks` translates it, honor these
sequencing guards (full evidence: [research/squad-findings-post-plan.md](./research/squad-findings-post-plan.md)):

1. **Adapters serialize on `sync.py` — NOT parallel lanes.** Every adapter/core extraction deletes a
   body from the single `cli/commands/sync.py` and adds a call-through there, so all such WPs share
   `sync.py` as an `owned_file`. Parallel worktree lanes require disjoint `owned_files`; these WPs
   are a **dependency chain** (each rebases on the prior's shrunk file) or a single owning lane —
   never fanned out. (The purge subsystem is the one disjoint block, but it still edits `sync.py` to
   remove its body.)
2. **Husk-scaffold is an early prerequisite edge.** The guarded re-export block + late-bound
   `sync_module.<name>` convention must exist **before the first private relocates**, or the ~60
   patch-tests break mid-mission. Split "husk-scaffold" (early — right after the golden net) from
   "husk-finalize" (last — baseline re-pin + census + issue). `@app.command` shells stay in `sync.py`.
3. **IC-05 → ≥4 WPs**: `status` (cc 90), `doctor` (cc 73), `sync_workspace` each their own WP
   (each a gather-I/O→core→render restructure retiring one `# noqa: C901`), plus a remaining-shell-split WP. *(Post-tasks note: the separate `cmd_*.py` shell-split WP is SUPERSEDED by guard #2 — `@app.command` shells stay in `sync.py`; the ~19 non-monster bodies shrink in place as their helpers extract, and WP12 asserts none exceeds complexity 15.)*
4. **IC-03 → ~5 sequential WPs** (render, runtime/config, purge, store-report+authority, dispatch),
   chained on `sync.py`.
5. **Only `walker.py` is genuinely pre-golden.** `sync.py` Tier-1 (esp. the `S3358` ternary
   extractions) lands **after** the 22-command golden net (WP01), not before. Split the campsite:
   walker (day-one, independent) vs sync Tier-1 (post-golden).
6. **Gap-freeze snapshots gate to their extraction WP, not WP01.** The under-characterized commands
   (`status` full human-render, `doctor` non-json table + arms, `sync_workspace`, `diagnose --json`)
   are frozen *inside* their own extraction WP; a "golden done" tick on WP01 must not satisfy FR-001
   for the monsters. `sync_workspace`'s substantive arms need `get_vcs`/`_detect_workspace_context`
   stubs (a monkeypatch-golden). The FR-004 two-authority arch-test lands with the authority-port WP.
7. **FR-007 anti-deletion guard is an executable test**, not just prose in `env-census.md`.
8. **Test env**: `SPEC_KITTY_ENABLE_SAAS_SYNC=1` (correct name) to reach non-skip render arms;
   `SPEC_KITTY_SYNC_DISABLE=1` is orthogonal (disables work/gate, not render) — pairing both is the
   hermetic-golden combo. Real-port/daemon suites run `-n0`. Set a fast `review.test_command` to avoid
   the claim-time full-suite hang on these WPs.
