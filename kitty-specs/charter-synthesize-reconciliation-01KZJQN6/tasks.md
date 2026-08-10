# Work Packages: Charter Synthesize Reconciliation

**Mission**: charter-synthesize-reconciliation-01KZJQN6 (mid8 01KZJQN6)
**Branch**: `fix/charter-synthesize-reconciliation` (planning-base = merge-target; PRs into `main`)
**Contract**: preserve-and-warn (ledger `01KZJV6H7TW63M6ZGNM05XKM2S`)

Spine (P0, independently landable): **WP01–WP05**. Folds (P2): **WP06 (#2777)**, **WP07 (#3052)**.
Each WP co-delivers its focused tests (ATDD; the committed
`tests/charter/synthesizer/test_synthesize_node_preservation.py` is the spine acceptance anchor).

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Reconcile value objects: `SynthesizeMode`, `ReconciliationDelta`, `ReconciliationConflict` | WP01 | |
| T002 | Extract/share `_merge_project_overlay` + `_rewrite_manifest` as reusable primitives | WP01 | |
| T003 | Reconcile the graph overlay against on-disk at the synthesize seam (preserve backed) | WP01 | |
| T004 | Reconcile the manifest (`_rewrite_manifest` + `manifest_override`) on the synthesize path | WP01 | |
| T005 | Return a `ReconciliationDelta` from `synthesize` (back-compatible signature, default preserve); detect+classify conflicts and **populate `delta.conflicts` in-memory** | WP01 | |
| T006 | Tests: committed preserve test green; no-op byte-stability (graph+manifest); manifest version-skew | WP01 | |
| T007 | Validate the merged (preserved+emitted) overlay, not just the emitted one | WP02 | |
| T008 | Receive WP01's classified conflicts via a widened `validate()` signature (detection+classification is WP01) | WP02 | |
| T009 | Suppress preserved / raise new-emit (decision only); `delta.conflicts` is populated by WP01 (no sidecar) | WP02 | |
| T010 | Tests: preserved duplicate-triple → report; preserved dangling-endpoint → report; new-emit still raises | WP02 | |
| T011 | Map CLI flags → `SynthesizeMode`; preserve-and-warn default output | WP03 | |
| T012 | `--prune` removes divergent content and lists every deletion | WP03 | |
| T013 | `--dry-run` reports the reconciliation delta and writes nothing | WP03 | |
| T014 | Narrow non-zero refusal: orphaned removal without `--prune`; unparseable overlay | WP03 | |
| T015 | Reuse the DRG conflict-object shape for refusal/prune/dry-run messaging | WP03 | |
| T016 | Tests: prune remove+list; prune no-op; dry-run non-empty+empty (no write); corrupt-overlay refuse | WP03 | |
| T017 | Route `_attempt_auto_refresh` to preserve mode (exit-0, non-destructive) | WP04 | |
| T018 | Re-stamp `synthesized_drg` fresh after a non-destructive heal (decoupled from destructive rebuild) | WP04 | |
| T019 | Install a references-parity extension point (stub) for WP06 to implement | WP04 | |
| T020 | Tests: authoring-only edit → implement proceeds, 0 loss, freshness fresh, not re-blocked | WP04 | |
| T021 | Pass CLI flags explicitly (`prune=False, dry_run=False`) at the activate/deactivate in-process `charter_synthesize` call sites (no `OptionInfo` sentinel silent-prune) | WP05 | |
| T022 | Rename `run_resynthesize_pipeline` (calls full synthesize) to reflect intent; update imports | WP05 | |
| T023 | Tests: activate/deactivate preserve backed content | WP05 | |
| T023b | Regression: activate AND deactivate over a backed overlay never prune once `--prune` exists (#3270 guard) | WP05 | |
| T024 | Implement references-parity refresh helper (targeted `generate`) honoring #2772 charter.md | WP06 | |
| T025 | Wire the helper into WP04's extension point; run only for the references-parity cause | WP06 | |
| T026 | Tests: references recompiled; curated charter.md 0 bytes changed | WP06 | |
| T027 | Populate `source_urns` for consumer-pack interview sections (no fabrication) | WP07 | |
| T028 | Ensure `emit_project_layer` emits the declared edges; DRG lint passes | WP07 | |
| T029 | Tests: positive edge emission + negative no-fabrication; lint green | WP07 | |

## Work Packages

### WP01 — Library reconciliation seam (preserve-and-succeed) *(P0 spine, foundation)*
- **Goal**: Make `orchestrator.synthesize` reconcile overlay + manifest against on-disk, preserving backed content and returning a delta; default drops nothing.
- **Priority**: P0. **Dependencies**: none. **Est.**: ~350–450 lines (raised from ~230 to reflect its 7 post-tasks amendments — merge seam, manifest override, conflict detection+classification, validator.py SSOT extraction, atomic write, backed/orphaned probing, delta+tests — it is the sole foundation lane).
- **Independent test**: committed `test_synthesize_node_preservation.py` passes; no-op byte-stability; manifest version-skew reconcile.
- **Subtasks**: T001–T006. **Prompt**: `tasks/WP01-library-reconciliation-seam.md`.

### WP02 — Merged-overlay conflict routing (report, not crash) *(P0 spine)*
- **Goal**: Validate the merged overlay; route preserved-content conflicts to the DRG report channel; keep new-emit collisions hard-error.
- **Priority**: P0. **Dependencies**: WP01. **Est.**: ~190 lines.
- **Independent test**: preserved duplicate-triple/dangling-endpoint → reported (no crash); new-emit collision still raises.
- **Subtasks**: T007–T010. **Prompt**: `tasks/WP02-merged-overlay-conflict-routing.md`.

### WP03 — CLI preserve/prune/dry-run + narrow refusal *(P0 spine)*
- **Goal**: CLI consumes the delta: preserve-and-warn default; `--prune` removes+lists; `--dry-run` reports+no-write; refuse only for unpreservable cases.
- **Priority**: P0. **Dependencies**: WP01, WP02. **Est.**: ~250 lines.
- **Independent test**: prune remove+list; prune no-op; dry-run non-empty+empty (no write); corrupt overlay refuses.
- **Subtasks**: T011–T016. **Prompt**: `tasks/WP03-cli-preserve-prune-dryrun.md`.

### WP04 — Non-destructive boundary heal that clears stale *(P0 spine)*
- **Goal**: `_attempt_auto_refresh` consumes preserve mode and clears `synthesized_drg`; installs the references-parity extension point.
- **Priority**: P0. **Dependencies**: WP01, WP03. **Est.**: ~200 lines.
- **Independent test**: authoring-only edit → implement proceeds, 0 loss, freshness fresh, not re-blocked.
- **Subtasks**: T017–T020. **Prompt**: `tasks/WP04-boundary-heal-clears-stale.md`.

### WP05 — Activation coverage + naming footgun *(P0 spine)*
- **Goal**: activate/deactivate pass the CLI flags explicitly (`prune=False, dry_run=False`) at the
  in-process `charter_synthesize` call sites so no `OptionInfo` sentinel silently prunes once WP03
  adds `--prune`; rename the mis-named `run_resynthesize_pipeline`.
- **Priority**: P0 (rename is P3 polish within). **Dependencies**: WP01, **WP03** (the `--prune`
  param must exist before activation can pass `prune=False`). **Est.**: ~150 lines.
- **Independent test**: activate/deactivate preserve backed content; sentinel-prune regression (T023b).
- **Subtasks**: T021–T023, T023b. **Prompt**: `tasks/WP05-activation-coverage-rename.md`.

### WP06 — References-parity auto-refresh completion (#2777) *(P2 fold)*
- **Goal**: Targeted `generate` for the references-parity stale cause, honoring the landed #2772 charter.md contract.
- **Priority**: P2. **Dependencies**: WP04. **Est.**: ~170 lines.
- **Independent test**: references recompiled; curated charter.md 0 bytes changed.
- **Subtasks**: T024–T026. **Prompt**: `tasks/WP06-references-parity-refresh.md`.

### WP07 — Edge wiring from evidence (#3052) *(P2 fold)*
- **Goal**: Populate `source_urns` for consumer-pack sections so synthesize emits charter-relevant edges; no fabrication.
- **Priority**: P2. **Dependencies**: WP01. **Est.**: ~170 lines.
- **Independent test**: positive edge emission + negative no-fabrication; DRG lint green.
- **Subtasks**: T027–T029. **Prompt**: `tasks/WP07-edge-wiring-from-evidence.md`.

## Dependency graph

```
WP01 ──┬── WP02 ── WP03 ──┬── WP04 ── WP06
       │                  └── WP05
       └── WP07
```

WP05 depends on WP03 (the `--prune` param must exist before activation can pass `prune=False`
explicitly at its in-process `charter_synthesize` call site); WP05's WP01 dependency is transitively
satisfied through WP03←WP02←WP01.

## MVP / recommended first lane

**WP01** is the foundation and the MVP slice: it makes the release-blocking data-loss test pass.
The P0 spine (WP01→WP02→WP03→WP04, plus WP05) is releasable without the P2 folds (WP06, WP07).

**Spine-independence caveat (post-tasks squad):** the spine self-heals the **authoring-only**
stale cause. **US2 Acceptance Scenario 3 → FR-011 → WP06 (P2)**: references-parity drift →
`references.yaml` recompiled + curated `charter.md` unchanged is delivered by the P2 fold **WP06**
(#2777); WP04 installs only the stub hook. So the **spine does NOT fully deliver US2** — AC3 is a
P2 dependency, not spine work. Until WP06 lands, an operator whose stale cause is references-parity
is not auto-healed for that specific cause.

**WP03↔WP02 edge is partial/integration only (post-tasks squad).** WP03's **non-conflict**
deliverables — flag→mode mapping, `--prune`, `--dry-run`, and the narrow refusal — gate **only on
WP01** (the library delta + preserve default). WP03 needs **WP02 only for conflict-warning
rendering** (surfacing preserved-conflict lines the CLI prints). The `WP03 depends on WP02` edge is
kept but is **partial/integration**: if WP02 slips, WP03's non-conflict UX can still be built and
tested against WP01; only the conflict-warning presentation waits on WP02.

## Post-tasks squad pass

Two adversarial lenses reviewed this breakdown; findings are folded as
"🔴 Post-tasks squad amendments" sections in WP01, WP02, WP03, WP04, WP07. The three blockers —
all in WP01/WP02 — were: (1) drive the FR-009 post-condition from the merged graph or the
post-condition re-deletes preserved `graph.yaml`; (2) corrupt-overlay fail-closed must live at the
library seam; (3) the WP01→WP02 conflict interface is **in-memory** — WP01 detects, classifies,
and populates `delta.conflicts`, then passes them to a **widened `validate()` signature**; WP02
performs the suppress-vs-raise decision only. There is **no** `.reconcile-conflicts.json` sidecar.
The reconciliation remediation vocabulary and its distinct `kind`s (`duplicate_triple`,
`preserved_dangling_endpoint`) are defined in `reconcile.py` (modeled after — not reusing —
`src/doctrine/drg/merge.py`), and the shared structured duplicate/dangling detection helpers are
extracted once in `src/doctrine/drg/validator.py`. Read the amendments before implementing.
