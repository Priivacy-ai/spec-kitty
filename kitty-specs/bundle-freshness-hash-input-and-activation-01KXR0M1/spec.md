# Mission Specification: Bundle-Freshness Content-Identity — Missing-File Robustness + Directive-Activation Visibility

**Mission Branch**: `gk/2758-2759` (single_branch; stacked on `fix/2681-synthesized-drg-stale` / PR #2732)
**Created**: 2026-07-17
**Status**: Draft (converged after 3 spec + 2 plan adversarial-squad rounds — activation identity = resolved directives only)
**Input**: GitHub issues #2758 and #2759 (both from the #2732 alignment squad), bundled: two faces of the same `bundle_content_hash` seam.

## Context & Background *(informational)*

PR #2732 (this mission's base) re-based `synthesized_drg` freshness on a **content-identity hash** of
four bundle files (`compute_bundle_content_hash`, `src/charter/bundle.py:133`;
`BUNDLE_CONTENT_HASH_FILES` = governance/directives/references/metadata.yaml, bundle.py:47). The reader
`_compute_synthesized_drg` (`computer.py:349`) returns `stale` when `stored is None or current is None
or stored != current` (computer.py:428), after gating on `synced_bundle.state == "fresh"`
(computer.py:413).

The #2732 alignment squad flagged two remaining blind spots (#2758, #2759). Both hinge on: *what
constitutes the synthesized-DRG content identity?*

**Design (converged across 5 squad rounds).** `synthesized_drg` attests the tracked **`graph.yaml`**,
so the identity must hash **exactly the activation input that varies `graph.yaml`** — and nothing
else. Verified in `src/specify_cli/cli/commands/charter/_synthesis.py`: the graph's `SynthesisRequest`
derives its activation content **only** from `selected_directives` (→ `drg_nodes`, `_synthesis.py:97-107`),
resolved as `[] if pack_context.activated_directives is None else resolve_config_activated_roots(repo_root).directives`
(the #2577 absent→`[]` rule, `_synthesis.py:76-79`). `selected_paradigms` is *set* on the interview
snapshot (`_synthesis.py:85`) but **inert** — nothing in `src/charter/synthesizer/` consumes it
(`_EXPANDED_SECTIONS = {selected_directives, language_scope}`, no paradigm consumer), so a
paradigm-only change leaves `graph.yaml` byte-identical. No other activation kind reaches the graph.

Therefore the mission (**Option C**, converged): **remove `references.yaml`** from the identity (closes
#2758) and **add a digest of the resolved directive set** (absent→`[]`), obtained via a shared
charter-side helper called by BOTH the synthesizer and `compute_bundle_content_hash` — so the
fingerprint attests the graph *by construction*. Including paradigms (or the 8-key config superset, or
`_load_default_pack` effective-sets) was squad-rejected: each attests a different object than
`graph.yaml` → false-stale + version-coupling.

Grounded facts (verified on this branch):

- `resolve_config_activated_roots` (`compiler.py:212`) is the documented shared charter-layer seam used
  by both `compile_charter` (references.yaml) and the synthesizer (graph.yaml); returns bare canonical
  ids (install-location-independent).
- `compute_bundle_content_hash` returns `None` (never raises) on any missing/unreadable input
  (bundle.py:170-175); the reader maps `None` → `stale`.
- `charter activate`/`deactivate` write only `config.yaml` (`pack_manager.py:448`,`:519`); reader,
  `promote()` (write_pipeline.py:685), and `resynthesize` (resynthesize_pipeline.py:205) all route
  through the single `compute_bundle_content_hash` recipe (`project_drg.py:311` *preserves* on the
  built_in_only toggle, does not recompute — correct). So the identity change needs **no** reader/activate edit.
- **#2721 coordination resolved.** Option C touches `activate`/`deactivate` not at all; S-A/S-B are
  merged on-branch; open S-C (#2724) is orthogonal `template_set` work.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — A missing/prunable derived bundle file must not cause an unrecoverable permanent-stale (Priority: P1)

A project reaches a non-`built_in_only` synthesized graph while `references.yaml` is absent (squad-traced,
matches the landed fixture: `references.yaml` is gitignored and not in
`CANONICAL_MANIFEST.gitignore_required_entries`, so a fresh clone/checkout of a committed-untracked
state — or a literal `rm`/`unlink` — leaves it absent while a tracked non-`built_in_only` graph exists).
Today `promote()` stores `bundle_content_hash = None`, the reader recomputes `None`, and `charter status`
reports **`stale` permanently** — `charter synthesize` re-stores `None` and never self-heals (distinct
from a legacy-`None`, which self-heals once the file reappears).

**Why P1**: the state is **unrecoverable by the very command the remediation advertises** (`charter synthesize`).

**Independent Test** (red-first, C-011): reuse
`test_computer.py::test_synthesized_drg_stale_when_a_bundle_file_is_missing` (landed by `13caf4ca8`):
seed a full fresh bundle at a non-`built_in_only` state, `unlink()` `references.yaml`; assert pre-fix
permanent `stale`, post-fix a **stable, non-stale** state.

**Acceptance Scenarios**:

1. **Given** a real `graph.yaml`, a manifest not declaring `built_in_only`, present-and-matching triad
   + directive inputs, and `references.yaml` absent, **When** `charter status` runs, **Then**
   `synthesized_drg` is **not** `stale` on account of the missing `references.yaml`, and `charter
   synthesize` persists no `bundle_content_hash = None`.
2. **Given** the state that today yields permanent `stale`, **When** the operator reads `charter status`,
   **Then** state + `remediation` are internally consistent (asserted against `charter status` output).
3. **Given** a legacy project with stored `bundle_content_hash = None` (pre-#2732, schema "2"), **When**
   the standard generate→synthesize flow runs, **Then** the existing self-heal is preserved (FR-003 —
   a distinct starting state from FR-007, with its own anchor).

---

### User Story 2 — Directive activation must be visible to the freshness signal (Priority: P2)

A user runs `charter activate directive <id>` (or `deactivate`) and immediately runs `charter status`.
Because activation writes only `config.yaml`, the hash is unchanged, so `synthesized_drg` reports
**`fresh`** even though the directives the graph is built from changed → false-`fresh`.

**Why P2**: transiently-wrong-but-self-correcting; but a false-`fresh` exactly when trusted.

**Scope of "activation" for `synthesized_drg` (load-bearing correctness point).** `synthesized_drg`
attests `graph.yaml`, whose activation-derived content is **directives only**. So activating/deactivating
a **directive** that changes the resolved set MUST flip to `stale`; activating **any other kind** —
paradigm (inert), tactic, toolguide, procedure, styleguide, agent-profile, mission-step-contract,
mission-type — does **not** change `graph.yaml` and MUST leave `synthesized_drg = fresh`. Reporting
`stale` there is a *false-stale* / no-op-synthesis churn (the graph re-synthesizes byte-identically).
Their effect on `references.yaml`/runtime context is the separate scoped-out concern.

**Independent Test** (red-first, C-011): on a project at `synthesized_drg = fresh`, activate (and
separately deactivate) a **directive** with an effective change to the resolved set; assert pre-fix
`fresh` (4-file recipe ignores config), post-fix `stale`. Assert activating a **paradigm** and a
**tactic** leaves `fresh` (the false-stale boundary guard). Assert a **no-op** (re-activating an id that
does not change the resolved directive set) is unchanged. Derive ids from the resolver / monkeypatch the
resolution seam — never hardcode `default.yaml` content.

**Acceptance Scenarios**:

1. **Given** `synthesized_drg = fresh`, **When** the user activates a **`directive`** that changes the
   resolved directive set, **Then** `charter status` reports `synthesized_drg = stale`.
2. **Given** `synthesized_drg = fresh`, **When** the user **deactivates** a previously-active directive,
   **Then** the signal reports `stale`.
3. **Given** `synthesized_drg = fresh`, **When** the user activates a **paradigm** or a **tactic** (a
   non-graph-varying kind), **Then** `synthesized_drg` stays `fresh` (correct — NOT a false-fresh, NOT
   the #2759 bug).
4. **Given** a **no-op** for the resolved directive set (re-activating a resolved id; a validation
   failure that writes nothing; a `deactivate` no-op early-return), **When** `charter status` runs,
   **Then** the signal is unchanged.
5. **Given** a directive activation followed by `spec-kitty charter synthesize`, **When** `charter
   status` runs, **Then** it returns to `fresh`.
6. **Given** a `config.yaml` whose activated stem no longer resolves in the catalog (config drift),
   **When** `charter status` runs, **Then** it reports a recoverable `stale` (the freshness read does
   NOT crash), and `charter synthesize` surfaces the actionable resolution error.

---

### Edge Cases

- **Identity mirrors the synthesizer by construction.** The activation contribution is the resolved
  directive set (absent→`[]` per #2577), computed via the shared helper both the synthesizer and the
  hash call — so no-op stability, absent-key handling, and "materializing activate genuinely changes the
  graph" (the `[]`→non-empty first-activation, which the #2577 comment notes DOES change synthesis) are
  all correct by construction. No `_load_default_pack` content enters the identity.
- **Config-drift / resolver failure (never-raise, OQ-4).** `resolve_config_activated_roots` eagerly
  resolves all activated kinds and raises `UnknownArtifactIdError` (a `ValueError`) on a stem that no
  longer resolves. `compute_bundle_content_hash` MUST catch this (and `CharterPackConfigError` + parse
  errors) → `None` → recoverable `stale`, never crash `charter status` (this path did not exist pre-mission).
- **Missing sync-triad file** handled upstream by the `synced_bundle.state == "fresh"` gate
  (computer.py:413), remediation `charter sync`; preserve this ordering.
- **`references.yaml` unreadable / BOM / CRLF**: existing per-file guards
  (`tests/charter/test_bundle_content_hash.py`) stay green for the remaining triad.
- **`built_in_only` projects**: the `built_in_only` branch (computer.py:367) is a PASS state; not pushed to `stale`/`missing`.
- **Out of scope — process-level `config.yaml` races** (`commit_plan` single unlocked save).

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Remove `references.yaml` from `BUNDLE_CONTENT_HASH_FILES` so a missing/pruned `references.yaml` cannot force `bundle_content_hash = None` / permanent stale. | US1 | High | Open |
| FR-002 | Add to the identity a canonical digest of **the resolved directive set** (`[] if activated_directives is None else resolve_config_activated_roots(...).directives`) — the sole activation input that varies `graph.yaml` — via a shared charter-side helper called by BOTH the synthesizer and `compute_bundle_content_hash`. Do NOT include paradigms (inert) or other kinds. | US2 | High | Open |
| FR-003 | Preserve the legacy-`None` self-heal (pre-#2732 schema-"2" manifest → `fresh` via generate→synthesize) — distinct anchor from FR-007. | US1 | High | Open |
| FR-004 | One hash recipe (`compute_bundle_content_hash`) consumed by reader/`promote`/`resynthesize`; one directive-resolution authority (the shared helper wrapping `resolve_config_activated_roots`). No second content-identity authority, no second config-activation reader, no `specify_cli → charter` inversion. | US1, US2 | High | Open |
| FR-005 | Reader state + `remediation` internally consistent: any `stale` advertises a resolving remediation. For a malformed/drifted-config `stale`, `charter synthesize` surfaces an actionable error (fix→synthesize heals), not a silent `None` re-store. | US1, US2 | High | Open |
| FR-006 | After `spec-kitty charter synthesize`, the signal returns to `fresh` for the directive-activation, missing-`references.yaml`, and recipe-migration paths. | US1, US2 | High | Open |
| FR-007 | A #2732-era stored hash (schema "3", real 4-file hash) that no longer matches the new recipe self-heals to `fresh` in one `synthesize`; no schema bump. | US1 | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Hot-path preservation | The `bundle.py → charter.compiler` import MUST be **function-local** inside `compute_bundle_content_hash` (deferred), matching the reader's deferred bundle import (computer.py:422): `charter/__init__` imports `.bundle` before the heavy `.compiler`, and the reader keeps the bundle import off the `spec-kitty next` startup path. | Performance | High | Open |
| NFR-002 | Latency | The freshness read now runs `resolve_config_activated_roots` → `load_doctrine_catalog()` (a doctrine-tree load) per `charter status` — heavier than a config read. Keep `test_performance_envelopes.py::TestNfr002FreshnessComputeUnder2Seconds` load-bearing (it must reach the graph-hash branch); confirm < 2s and cache the resolution within one `compute_freshness` call if needed. | Performance | High | Open |
| NFR-003 | Fail-posture | Reader never crashes AND never creates a new permanent stale; catch resolver exceptions (`UnknownArtifactIdError`, `CharterPackConfigError`, parse/OS errors) → `None` → recoverable `stale`. | Reliability | High | Open |
| NFR-004 | Diff coverage | ≥90% on new lines. `src/charter/*` IS in the CI-enforced `critical_paths` gate; `src/specify_cli/*` (reader `computer.py`, synthesizer `_synthesis.py`) is **not** — self-police there. | Quality | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Attest the graph, minimally | Identity = (existing bundle inputs − `references.yaml`) + a digest of the resolved directive set. Not paradigms (inert), not the 8-key superset, not `_load_default_pack` effective-sets — all squad-verified to attest a different object → false-stale/false-fresh. | Technical | High | Open |
| C-002 | Backward-compat (C-012) | No bundle-manifest schema bump; the recipe change is one self-healing stale (FR-007). | Technical | High | Open |
| C-003 | One recipe, don't multiply lists | One write-side recipe; edit **only** `BUNDLE_CONTENT_HASH_FILES` for the file set; do NOT alter `computer._BUNDLE_FILES` (computer.py:137 — drives the separate `synced_bundle` signal; a non-regression AC if it must be touched). | Technical | High | Open |
| C-004 | Dead-symbol gate (charter C-007) | The new shared directive-resolution helper is public in `charter` with two real callers (`_synthesis.py`, `bundle.py`) → satisfies `test_no_dead_symbols`; declare `__all__`. | Technical | High | Open |
| C-005 | ATDD-first (charter C-011) | Each WP lands a red-first test before implementation. | Process | High | Open |
| C-006 | Terminology canon | `Mission` not `feature`; run `test_no_legacy_terminology.py` pre-push. | Technical | Medium | Open |
| C-007 | Stacked-on-#2732 base | Applies cleanly on `fix/2681-synthesized-drg-stale`; PR dependent on #2732; extend #2732's mechanism. | Process | High | Open |

### Key Entities

- **Synthesized-DRG content identity**: post-mission = (existing bundle inputs − `references.yaml`) + the directive-activation digest.
- **Directive-activation digest** *(new; not a file)*: a deterministic digest of the resolved directive set (absent→`[]`), from the shared helper.
- **Shared directive resolver** *(new, charter-side)*: the single function returning the resolved directive list the synthesizer feeds the graph; called by `_synthesis.py` and `compute_bundle_content_hash`.
- **`references.yaml`**: removed from the identity; content-correctness out of scope.

## Scope Boundary — Explicitly Out of Scope

- **Non-directive activation visibility in `synthesized_drg`.** Activating a paradigm/tactic/…/mission-type
  does not change `graph.yaml`, so `synthesized_drg` correctly stays `fresh`; flagging stale there would
  be a false-stale. (If a future synthesizer change makes paradigms — or other kinds — actually feed the
  graph, the shared helper is the single place to extend, keeping identity and graph coupled.)
- **Interview-answer-derived graph variation.** `graph.yaml` also derives from interview *answers*
  (`language_scope` → styleguide targets; table-driven `mission_type`/`testing_philosophy`/`risk_appetite`
  sections), none of which are in the identity. This is a pre-existing #2732-era gap, out of scope; a
  `fresh` `synthesized_drg` does not imply currency vs an unre-synthesized interview-answer change.
- **`references.yaml` content-correctness vs `config.yaml`** (runtime context; ADR-deferred
  `06_unified_charter_bundle.md:52-56`); **`activated_kinds`**; **process-level races**.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: No reachable state leaves `synthesized_drg` permanently `stale` due to a missing/pruned
  `references.yaml`; regression test asserts `charter status` output (state + remediation).
- **SC-002**: After `charter activate`/`deactivate` of a **directive** that changes the resolved set,
  `charter status` reports `stale` in-session and returns to `fresh` after `synthesize` (red-first→green
  for both activate and deactivate). Activating a **paradigm** and a **tactic** stays `fresh` (false-stale
  boundary guard).
- **SC-003**: A no-op for the resolved directive set (re-activate a resolved id; validation failure;
  deactivate no-op) produces zero freshness-state change; ids derived from the resolver, not hardcoded.
- **SC-004**: `charter status/activate/deactivate/synthesize` each stay < 2s (spot-measured, the envelope
  test reaching the graph-hash branch); the identity does not move on a `default.yaml`/roster change that
  does not change the project's resolved directive set.
- **SC-005**: Targeted surfaces pass (`tests/charter/**`, `tests/specify_cli/charter_freshness/**`,
  `_synthesis`/pack-manager tests); ≥90% diff coverage (specify_cli side self-policed); `ruff`/`mypy
  --strict` clean, zero new suppressions; terminology + dead-symbol gates green.

## Resolved Design Decision & Residual Open Questions

**Resolved (5 squad rounds):** Option C with the activation contribution = a digest of the resolved
directive set, via a shared helper (attest the graph by construction). Rejected: recompile (A), marker
(B), 8-key `_load_default_pack` effective-set, directives+paradigms (paradigms inert), raw config-key
hashing. OQ-6/OQ-7 dissolved.

**Residual open questions for tasks/implement (mostly closed):**

- **OQ-1**: keep the sync triad + swap `references.yaml` → directive digest = one recipe change / one
  migration stale (FR-007). Confirm the triad stays (orthogonal to activation).
- **OQ-3**: remediation `spec-kitty charter synthesize` (correct for the graph); document `fresh` ≠
  `references.yaml`/interview-answer currency.
- **OQ-4**: catch `UnknownArtifactIdError`/`CharterPackConfigError`/parse in `compute_bundle_content_hash`
  → `None` → recoverable stale; red-first drifted-stem + malformed-config tests; the `synthesize` error
  path is actionable (FR-005).
- **OQ-5**: extract the directive resolution (`_synthesis.py:76-79`) into the shared charter helper;
  refactor `_synthesis.py` to call it (behavior-preserving, guarded by `test_synthesize_path_parity`);
  synthesizer keeps `selected_paradigms = config_roots.paradigms` directly (inert, unchanged);
  `bundle.py` hashes `",".join(sorted(directives))` via `hash_content`.
- **OQ-6 (perf)**: confirm the per-`charter status` catalog load stays < 2s; cache within one
  `compute_freshness` if needed.
