---
work_package_id: WP05
title: spec-kitty charter resynthesize --topic (plan alias WP3.8)
dependencies:
- WP03
- WP04
requirement_refs:
- FR-010
- FR-011
- FR-012
- FR-013
- FR-017
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-phase-3-charter-synthesizer-pipeline-01KPE222
base_commit: 9d239e76b5e1eef0f31811a179a5de91ff0c8149
created_at: '2026-04-17T18:15:15.265337+00:00'
subtasks:
- T027
- T028
- T029
- T030
- T031
- T032
shell_pid: "74463"
agent: "claude:sonnet-4.6:implementer:implementer"
history:
- at: '2026-04-17T16:43:25Z'
  actor: tasks
  event: generated
authoritative_surface: src/charter/synthesizer/
execution_mode: code_change
mission_id: 01KPE222CD1MMCYEGB3ZCY51VR
mission_slug: phase-3-charter-synthesizer-pipeline-01KPE222
owned_files:
- src/charter/synthesizer/topic_resolver.py
- src/charter/synthesizer/resynthesize_pipeline.py
- src/specify_cli/cli/commands/charter.py
- tests/charter/synthesizer/test_topic_resolver.py
- tests/charter/synthesizer/test_orchestrator_resynthesize.py
- tests/charter/synthesizer/test_performance_envelopes.py
- tests/agent/cli/commands/test_charter_synthesize_cli.py
- tests/agent/cli/commands/test_charter_resynthesize_cli.py
tags: []
---

# WP05 · `spec-kitty charter resynthesize --topic`

## Objective

Close the operator-visible surface of Phase 3:

1. **Structured-selector resolver** with 3-tier local-first resolution: (1) project-local `<kind>:<slug>` for synthesizable kinds → (2) DRG URN against merged graph → (3) interview section label. No free-text (C-004), no silent fallback (FR-013).
2. **Bounded recomputation** that reuses WP03's staging/promote machinery; manifest is rewritten with a new `run_id` but **untouched artifacts retain their prior `content_hash`** (FR-017).
3. **CLI subcommands** `spec-kitty charter synthesize` + `spec-kitty charter resynthesize --topic <selector>` via Typer.
4. **Performance envelopes**: NFR-002 (< 30s full), NFR-003 (< 15s bounded), NFR-004 (< 5s fail-closed), SC-008 (< 2s on unresolved selector).

## Context

Read before writing code:
- [contracts/topic-selector.md](../contracts/topic-selector.md) — authoritative grammar + error shape. Must match exactly.
- [data-model.md §E-7](../data-model.md) — `TopicSelector` discriminated union; resolution order.
- [data-model.md §E-9](../data-model.md) — resynthesis lifecycle: same staging/promote, but only targeted artifacts replaced; manifest rewritten.
- [quickstart.md §2, §3, §4, §5](../quickstart.md) — operator UX for each tier + the unresolved-selector panel (exit code 2).
- Existing Typer command surfaces: `src/specify_cli/cli/commands/charter.py` and the neighbouring files for style/error-rendering conventions.

## Branch strategy

- Planning base: `main`
- Merge target: `main`
- Execution worktree: allocated by finalize-tasks (Lane A rejoin, after WP03)
- Branch name: `kitty/mission-phase-3-charter-synthesizer-pipeline-01KPE222-lane-a`

## Subtasks

### T027 — `topic_resolver.py` [P]

**File**: `src/charter/synthesizer/topic_resolver.py`

Public API:

```python
@dataclass(frozen=True)
class ResolvedTopic:
    targets: list[SynthesisTarget]
    matched_form: Literal["kind_slug", "drg_urn", "interview_section"]
    matched_value: str

def resolve(raw: str, project_artifacts, merged_drg, interview_sections) -> ResolvedTopic: ...
```

Resolution order exactly as in `contracts/topic-selector.md §1.4`:

1. If `raw` contains `:` AND LHS ∈ `{"directive","tactic","styleguide"}`, search the **project-local** artifact set by `(kind, slug)`. Hit → expand `targets = [matched]`; return.
2. Else if `raw` contains `:`, parse as DRG URN and search the merged shipped+project graph. Hit → expand `targets = [every project-local artifact whose provenance source_urns contains this URN]`. Zero-match → `ResolvedTopic` with empty targets + caller renders EC-4 "no-op with diagnostic" (no writes, no model call).
3. Else search interview section labels (exact string match). Hit → expand `targets = [every project-local artifact whose provenance source_section equals this label]`.
4. No hit in any step → raise `TopicSelectorUnresolvedError` (T028).

Step 1 winning over step 2 when both could apply is the **local-first rule** that makes `tactic:how-we-apply-directive-003` route to the project artifact (US-3).

### T028 — Structured-error surface

Inside `topic_resolver.resolve`, on unresolved:

```python
raise TopicSelectorUnresolvedError(
    raw=raw,
    attempted_forms=[...],  # per §2.1 of the contract
    candidates=_nearest_candidates(raw, project_artifacts, merged_drg, interview_sections, limit=5),
)
```

`_nearest_candidates` computes Levenshtein distance across all three candidate surfaces, returns the top 5 as `[{kind, value, distance}, ...]`. Stdlib-only (`difflib.SequenceMatcher` is fine, or a small hand-rolled Levenshtein — avoid new dependencies per plan.md).

CLI renders via `rich`-panel helper — panel title `Cannot resolve --topic "<raw>"`, exit code 2, no files written, no model call. This is the SC-008 surface.

### T029 — `resynthesize_pipeline.py`

**File**: `src/charter/synthesizer/resynthesize_pipeline.py`

Public entry: `run(request, adapter, topic: str) -> SynthesisManifest`.

Flow:
1. Load current manifest from `.kittify/charter/synthesis-manifest.yaml`. If absent → structured error: "no prior synthesis to resynthesize from".
2. Load every provenance sidecar — build an in-memory map `urn → ProvenanceEntry` and `section → [urn]`.
3. Call `topic_resolver.resolve(topic, ...)` → `ResolvedTopic`. Empty targets → return current manifest unchanged + diagnostic (EC-4; no writes, no model call).
4. Construct a **bounded** `SynthesisRequest` whose `target` set is `ResolvedTopic.targets`.
5. Call WP02's `synthesize_pipeline.run(bounded_request, adapter)` → `[(body, provenance), ...]` for targeted artifacts only.
6. Stage via WP03's `write_pipeline.promote` — but the staging tree only contains the regenerated artifacts. The promote step must **preserve** untouched files in the live tree.
7. After promote, rebuild `SynthesisManifest`:
   - Replace entries for regenerated artifacts.
   - **Retain prior `content_hash` and `provenance_path` for untouched artifacts** (FR-017).
   - New `run_id` (ULID); new `created_at`.
8. Write manifest last (via WP03's machinery).
9. Return the new manifest.

Key subtlety: WP03's `write_pipeline` was designed for full synthesis. Either (a) extend it to accept an `existing_manifest` parameter that determines which entries to preserve, or (b) add a thin `resynthesize_pipeline._rewrite_manifest(existing, new_entries, run_id)` helper here that computes the merged entry list. Prefer (b) — keeps WP03's pipeline simple; this WP owns the manifest-rewrite semantics.

Wire `orchestrator.resynthesize` (WP01's lazy-import seam) to delegate here.

### T030 — CLI subcommands [P]

**File**: `src/specify_cli/cli/commands/charter.py` (edit — add two subcommands)

Typer subcommands:

```python
@charter_app.command("synthesize")
def charter_synthesize(
    adapter: str = typer.Option("production", help="..."),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None: ...

@charter_app.command("resynthesize")
def charter_resynthesize(
    topic: str = typer.Option(..., "--topic", help="Structured selector: <kind>:<slug> | <drg-urn> | <interview-section>"),
    adapter: str = typer.Option("production", help="..."),
) -> None: ...
```

- `--adapter fixture` opts into the fixture adapter (R-0-5; quickstart §6). Default is `"production"`.
- `--dry-run` (synthesize only) stages + validates but does not promote; prints the staged file list.
- On any `SynthesisError`, render via the shared `rich`-panel helper (`src/charter/synthesizer/errors.py`), exit code 1 for most errors, exit code 2 for `TopicSelectorUnresolvedError` (matches `contracts/topic-selector.md §2.2`).

### T031 — Performance envelope tests [P]

**File**: `tests/charter/synthesizer/test_performance_envelopes.py`

CI-tolerant timing assertions using the fixture adapter:
- Full synthesis on a ≤10-answer representative interview: < 30s (NFR-002).
- Bounded `resynthesize --topic` (single target): < 15s (NFR-003).
- Fail-closed from detected validation failure to return: < 5s (NFR-004).
- `TopicSelectorUnresolvedError` return on a cold cache: < 2s (SC-008).

Use `pytest-timeout` (already in the test stack) with reasonable slack so CI flakiness doesn't trigger false alarms. Don't sleep; measure.

### T032 — Tests

**Files**:
- `tests/charter/synthesizer/test_topic_resolver.py` — table-driven: at least 12 cells covering (tier × hit/miss/ambiguous/zero-match). Include the US-3 case exactly as written (`tactic:how-we-apply-directive-003` resolves to tier 1, not tier 2). Include `directive:DIRECTIVE_003` resolving tier 2 (shipped URN, no local artifact). `TopicSelectorUnresolvedError.candidates` ordering deterministic.
- `tests/charter/synthesizer/test_orchestrator_resynthesize.py` — end-to-end:
  - US-2 (DRG URN): only affected artifacts regenerate; others byte-identical (≥ 95%, SC-006).
  - US-3 (kind+slug, local-first): exactly one artifact regenerated.
  - US-4 (interview section): all derived artifacts regenerated; unrelated artifacts unchanged.
  - Manifest rewrite preserves prior `content_hash` for untouched entries (FR-017).
  - EC-4 zero-match: no writes, no model call, diagnostic result.
- `tests/agent/cli/commands/test_charter_synthesize_cli.py` — Typer CLI: `--dry-run` doesn't promote; `--adapter fixture` works; happy-path emits manifest.
- `tests/agent/cli/commands/test_charter_resynthesize_cli.py` — CLI: resolved selector writes bounded change; unresolved selector renders panel + exits 2 + writes nothing.

## Definition of Done

- All 6 subtasks complete.
- `pytest tests/charter/synthesizer/test_{topic_resolver,orchestrator_resynthesize,performance_envelopes}.py tests/agent/cli/commands/test_charter_*_cli.py` green.
- `mypy --strict` clean on WP05 files.
- Coverage ≥ 90% on new modules (NFR-001).
- All performance envelopes (NFR-002/003/004, SC-008) met in CI.
- CLI help text matches quickstart.md examples.
- All 20 FRs covered across WP01-WP05 — re-run `spec-kitty agent tasks map-requirements --mission phase-3-charter-synthesizer-pipeline-01KPE222 --json` and confirm `unmapped_functional == []`.

## Risks & premortem

- **R-5 · Selector ambiguity escalation** — Mitigation: structured error enumeration teaches the affordance; C-004 rejects free-text at the CLI layer, not inside the resolver.
- **Manifest rewrite drift** — Mitigation: `test_orchestrator_resynthesize.py` asserts byte-identical `content_hash` on untouched manifest entries; any change-control on this path needs a test update.
- **CLI exit-code drift** — The contract says exit 2 on unresolved; tests pin this. Any WP that changes exit codes without updating `contracts/topic-selector.md` is a regression.

## Reviewer guidance

1. `topic_resolver.resolve` — step order exactly matches `contracts/topic-selector.md §1.4`; local-first for synthesizable kinds is the key correctness property.
2. `resynthesize_pipeline.run` — manifest rewrite preserves untouched entries' `content_hash`; regenerated entries get fresh values. The 95% SC-006 threshold is a floor, not a target.
3. `test_topic_resolver.py` — do the 12 cells actually exercise the tier order, or do they just happy-path tier 1?
4. CLI panels — do they actually render via `rich` and exit with the documented code, or do they drop through to Typer's default error handling?
5. Performance tests — CI tolerance; no sleep; `pytest-timeout` slack set carefully.

## Next command

```bash
spec-kitty agent action implement WP05 --agent <your-agent>
```

## Activity Log

- 2026-04-17T18:15:16Z – claude:sonnet-4.6:implementer:implementer – shell_pid=74463 – Assigned agent via action command
