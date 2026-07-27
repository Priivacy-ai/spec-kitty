# Research — unshim-wave2-01KWMCAX (Phase 0)

Decisions derive from the pre-planning 3-lens squad (debugger-debbie, planner-priti, architect-alphonso) + the post-spec 2-lens pass (reviewer-renata, paula-patterns), all 2026-07-03 against main @ 47fed302d / branch tip. Divergences adjudicated from source, never averaged.

## D1 — Census authority chain (spec rev 2 → occurrence-map ledger)

Issue bodies are stale: #2291 said 49 test files (live: **78 files / ~497 sites** — renata verified 417 plain-import lines and 80 single-line patch-targets exactly); #2290 said 2 CLI callers (live: **4** incl. a defect) and implied ~2 files of tests (live: **23**). Squad counting methods diverged on patch-strings (renata 80 strict single-line vs paula ~140 co-occurrence incl. multi-line `patch.dict` constructs); orchestrator re-greps got 80/78 on single-line methods. **Resolution: the plan-phase `occurrence_map.yaml` is the BINDING enumerator** — built with multi-line-aware analysis, it settles the count and doubles as the FR-002 interception-proof ledger (every patch-string row carries an `interception_proof` field the implement WPs must populate; renata's fakeable-at-scale mitigation).

## D2 — The monkeypatch injection seam (the one non-1:1 src caller)

`next_cmd.py:52-58` `_runtime_bridge_module()` probes `sys.modules["specify_cli.next.runtime_bridge"]` before importing canonical — a deliberate test seam with 2 injector tests (`test_selector_resolution.py:502,548` via `patch.dict(sys.modules, ...)`). While the shim lives, legacy-key injection works (alias = same object); after deletion it silently no-ops → vacuous pass. **Seam + both injectors re-key together to `runtime.next.runtime_bridge` in one change (FR-001), with consumption proven via the `captured`-dict side-effect (~:484-497), not exit-code green.**

## D3 — No prerequisite work exists (two roadmap claims falsified)

(a) `runtime.next.*` is already the sanctioned surface — `test_shared_package_boundary.py` forbids only the retired `spec_kitty_runtime` external package; nothing gates `_internal_runtime` imports (convention, not boundary; contrast `test_mission_runtime_surface.py` MR-1 which IS strict). No "public surface first" step. (b) The roadmap's "WS1 unblocks the next-shim deletion": `src/mission_runtime/` (4 files) imports neither `specify_cli.next` nor `runtime.next` — no edge, not a blocker. WS1 folds in as governance (#2327) because it's roadmap-committed and un-tracked, not because anything depends on it.

## D4 — Charter shims: full delete (operator-doctrine override of the cheaper path)

Alphonso recommended register-don't-delete (deletion = 23 test files + a 6-test lock-gate). Overruled: the HiC rescission of version-boundary deferrals means registering `charter_*` at a `removal_target_release` recreates the rescinded pattern. Full delete is sized honestly: 4 src callers — incl. the squad-found **defect at `charter_runtime/preflight/runner.py:36`** (canonical imports its own legacy shim) — 23 test files (charter_lint 10 / charter_preflight 11, of which 5 are CI-only shards to run locally / charter_freshness 4), 3 package deletions, and the `test_charter_runtime_shim_paths.py` retirement (6 tests; `test_canonical_paths_import` re-homes since it pins canonical imports) with a per-test disposition table (renata's anti-hand-wave fold).

## D5 — charter_activate settled: canonical, not a shim (convergent renata+paula)

246-LOC substantive module (defines the `AffectedMission`/`StepRemovalWarning` types + emit/find/scan functions consumed by `activate.py:141`; docstring records the intentional `specify_cli` placement; re-exports nothing). The pre-planning census's "4th unmarked shim" claim was FALSE. FR-007 collapsed to documented-canonical record; the `test_no_dead_symbols.py:517-518` rows STAY (dead symbols in a live module — category_b burn-down wave's business, not shim residue).

## D6 — WS1 allowed-exception pre-decision (paula's hidden-hazard finding)

The layer landscape places `mission_runtime` below `specify_cli`, but `mission_runtime/resolution.py` carries 10+ real lazy upward imports into `specify_cli.{core,missions,coordination,mission_metadata,status}`. A rule that reds on them = unbounded debt discovery mid-mission; a rule that silently allows everything = vacuous. **Pre-decided: the LayerRule names the upward edges as a documented allowed-exception set with recorded rationale; converting them to violations is a carved-out future mission. Non-vacuity is proven by a COMMITTED, CI-selected negative test** (renata: a throwaway theater run self-regresses) rejecting a synthetic out-of-set import.

## D7 — Spine co-tenancy → sequential DAG topology (paula)

C-005 (atomic delete+drain) forces the spine edits (`shim-registry.yaml`, `test_shim_registry_schema.py:44-45` presence-asserts, `_baselines.yaml`) to spread across the delete/prune WPs — they cannot be centralized. Parallel lanes would have ≥4 WPs racing on 2–3 shared files (the co-tenancy class that flattened docs Mission B). **Single sequential DAG; A-repoint splits by directory cluster** (patch-strings and plain imports co-locate in files, so a risk-class split would violate file ownership); per-WP proof discipline replaces risk-class isolation. 10-WP prior.

## D8 — Governance-doc drift is in scope (renata's DoD gap)

`docs/architecture/05_ownership_manifest.yaml` and `05_ownership_map.md` are LIVE docs asserting "keep the glossary shim registered until…"/"remove in 3.3.0" — false post-merge. NFR-002's grep excludes prose, so FR-011 binds the scrub explicitly. CHANGELOG gets a breaking-removal entry; NO version bump (deletions don't touch `specify_cli/__init__.py` — verified, stated to preempt reviewer demands). Historical ADRs/archives stay immutable (occurrence-map: leave-as-is).

## D9 — Tracker semantics

#612/#613 are CLOSED extraction antecedents (parent #391) — the PR references, never re-closes. #2327 (WS1) native-parented under #1868 — `in-mission partial`, WS2–WS6 stay open. #2072 Obligation B verified NOT in any Wave 2 surface; closeout posts the operator-facing prerequisite note on #2293. #2034 (CI marker hole) → NFR-005 obligation on every new/relocated test. Roadmap wave-numbering discrepancy (user "Wave 3" vs roadmap "Wave 4" for #2293) noted — cosmetic, resolved by naming issues not waves.
