# Post-Task Adversarial Checkup Squad — Findings & Resolutions

**Date**: 2026-07-22 · **Phase**: post-task, pre-implementation · **Squad**: 3 Opus specialists (read-only)
**Lenses**: reviewer-renata (implementability/anti-laziness) · paula-patterns (cross-WP ownership/integration) · python-pedro (implementer feasibility)
**Verdict pre-fix**: NOT ready for implementation (3 blockers). **Post-fix**: resolved into frontmatter/lanes + data-model + WP prompts. Ready.

All claims verified against source before fixing.

## Blockers (3) → resolutions

| # | Lens(es) | Finding (verified) | Resolution |
|---|----------|--------------------|------------|
| B1 | pedro-F1 | **WP06 join keys on the wrong URN → permanently decorative gate.** The handler `spec-kitty-pre-review` is a GATE_REGISTRY name, but the canonical mission_step_contract URN is `mission_step_contract:software-dev/review` (`drg.py:271,389`); `_candidate_urn(handler)` → None → `active` always empty → permanent NO_COVERAGE. data-model §5 step 1 (gate on contract URN) contradicted step 3 (gate on handler). | **data-model §3/§5** (alphonso): gate on the **owning review-contract URN**; handler = plain `GATE_REGISTRY[b.handler]` dict lookup, not a DRG candidate. **WP06 T028/T031** (priti): predicate rewritten; positive arm uses a real activated contract URN, not a self-fulfilling mock. |
| B2 | renata-F1, paula-F1, pedro-F2 (+ my check) | **WP07/08/09 frontmatter `dependencies: []`** — gating reads frontmatter, so WP09 ("lands last") was claimable at parallel-group 0 with none of its deps present (ModuleNotFoundError / ungoverned stubbing). | **Fixed**: WP07→[WP05], WP09→[WP06,WP08], WP08 stays [] (genuinely independent — base-stable types + detached-base capture). Re-ran `finalize-tasks` → `lanes.json` recomputed (lane-i ← lane-f,lane-h; lane-g ← lane-e). Commit f082a258. |
| B3 | renata-F2, paula-F2 | **`is_consumer_repo` machinery deletion disowned** — field in WP03's file, reader in WP09's (lands last); no WP can single-own the cross-file deletion (the reader outlives its file's owner). | **WP03** deletes the probe `_is_spec_kitty_source_repo` (its file); **WP09** removes the reader + `_PRE_REVIEW_CONSUMER_REPO_REASON` (its file); the dead `GateAuthoritiesUnavailable.is_consumer_repo` FIELD is a tracked fast-follow (cannot be single-owned in this strangler). "Zero vestigial" downgraded honestly. |

## Substantive (HIGH/MEDIUM) → resolutions

| # | Lens | Finding | Resolution |
|---|------|---------|------------|
| pedro-F4 | pedro | **`parse_results` input mis-shaped** — `HeadRunResult` is already-parsed → portable impl has nothing to parse → collapses to NO_COVERAGE (decorative regression). | **data-model §1** + **WP02**: introduce `RawRunResult(returncode, stdout, stderr, output_artifact_path)` produced WITHOUT parsing; `parse_results(raw)`. |
| pedro-F3 | pedro | **Thin-alias only survives if the call-site stays on it** — `_do_move_task:1911` must keep calling `_mt_run_pre_review_gate` (forwarder), or the observability monkeypatch no-ops; and the 11 escape-hatch tests call it DIRECTLY → post-alias they drive full dispatch, needing an activated review-binding fixture. | **WP09 T040/T045**: forwarder mandated (do not repoint :1911); T045 budgets the escape-hatch activation fixtures. |
| renata-F3 | renata | **Pre-existing-baseline-failure → NOT blocked** asserted nowhere end-to-end (WP03 only tested the newly-failing direction). | **WP03**: add a red-at-baseline consumer test asserting NO_NEW_FAILURES via the head↔baseline diff. |
| renata-F4, pedro-F6 | renata+pedro | **Parity capture-from-base is a *fallback* with a *hand-typed* provenance SHA** → circular oracle still possible; terminal-outcome capture under-specified. | **WP08 T037**: detached `git worktree` at `e4ef6e850` MANDATORY; capture script asserts the SHA + machine-emits it into fixture headers; forcing TIMED_OUT/CANCELLED specified. |
| paula-F4 | paula | **GateHandler dispatch convention mismatch** — WP04 `.run(ctx)` dataclass vs WP09 bare-callable. | **data-model §4** + **WP04/WP09**: pin `get_gate_handler(name).run(ctx)`. |
| paula-F5 | paula | **`TransitionGateContext` has no owned home** (WP04 offered `gate_registry.py` OR an unowned `_gate_context.py`). | Pin single home = `gate_registry.py`; strike the sibling option; WP06/WP09 import it. |
| pedro-F5 | pedro | **WP02↔WP03 bidirectional import cycle** (shared dataclasses). Note: `_gate_coverage` is a runtime importlib, NOT a static import — no cycle from tests/, no authority move needed. | **WP02**: `from __future__ import annotations` + lazy in-method imports. |
| pedro-F7 | pedro | **WP05 `exclude_defaults` would drop other legitimate defaults** (`optional=False`). | **WP05 T022**: targeted `data.pop("gates", None)` instead. |
| paula-F6 | paula | WP08's declared `[WP04]` dep spurious. | Frontmatter `[]`; body reworded to "no code dep". |
| renata-F5 | renata | WP02 "import lives ONLY here" false at WP02 acceptance time. | Reworded: private copy here; always-on import removed by WP03 T011. |

## Guards confirmed faithfully carried (no action — do not re-flag)
- Non-vacuous resolution + non-`software-dev` negative control (WP06 T031): concrete research/documentation fixtures, empty-graph rejection.
- Per-handler fail-open / no cross-suppression (WP08 T039, WP09 T041): concrete, line-anchored.
- #2534 erroneous-activation closure (WP09 T046): structural (import spy / `sys.modules`), non-gameable.
- WP02 encapsulation without editing pre_review_gate.py (transient strangler duplication) — clean by design.
- Handler-name/edge-string agreement (`spec-kitty-pre-review`, `in_progress->for_review`) pinned across WP04/05/06/09.

## Net
The mission would have shipped a **decorative gate** (B1) and handed an implementer **WP09 first** (B2). Both caught pre-implementation. Fixes applied to frontmatter/lanes (re-finalized), data-model/contracts (alphonso), and 7 WP prompts (priti). Fast-follow tracked: cross-file `is_consumer_repo` field cleanup.
