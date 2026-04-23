---
work_package_id: WP08
title: Post-Tranche-B Operator Docs + CHANGELOG
dependencies:
- WP06
- WP07
requirement_refs:
- FR-011
- FR-013
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T039
- T040
- T041
- T042
- T043
- T044
agent: "claude:sonnet-4-6:reviewer:reviewer"
shell_pid: "32159"
history:
- event: created
  at: '2026-04-23T05:10:00Z'
  note: Initial generation from /spec-kitty.tasks
authoritative_surface: docs/trail-model.md
execution_mode: code_change
owned_files:
- docs/trail-model.md
- CHANGELOG.md
- tests/specify_cli/docs/test_trail_model_doc.py
tags: []
---

# WP08 — Post-Tranche-B Operator Docs + CHANGELOG

## Objective

Add four new subsections to `docs/trail-model.md` documenting everything Tranche B introduced (mode of work runtime enforcement, correlation links, SaaS read-model policy table, Tier 2 SaaS projection deferral), update `CHANGELOG.md` with Tranche A + Tranche B summaries plus the operator migration note, and add the doc-presence test that makes these doc changes mandatory for merge.

Also: add the "Host surfaces that teach the trail" subsection that was deferred from WP05/T021, linking to `docs/host-surface-parity.md`.

## Context

- **Decision records**: [ADR-001](../decisions/ADR-001-correlation-contract.md), [ADR-002](../decisions/ADR-002-mode-derivation.md), [ADR-003](../decisions/ADR-003-projection-policy.md), [ADR-004](../decisions/ADR-004-tier2-saas-deferral.md).
- **Baseline docs**: `docs/trail-model.md` currently documents the Tier 1 minimal viable trail, mode-of-work taxonomy (as documentation-only), trail tiers, SaaS projection (with a sentence-level "Tier 2 Local only in 3.2" note), retention/redaction, intake positioning, and the `#534` explain deferral.
- **What changes**: the taxonomy becomes runtime-enforced; correlation becomes a first-class contract; projection gets a named typed policy; Tier 2 deferral gets a named rationale; discoverability gets a pointer to the host-surface parity matrix.

## Branch Strategy

- **Planning base**: `main`.
- **Final merge target**: `main`.
- **Execution worktree**: allocated from `lanes.json` at implement time. WP08 depends on WP06 and WP07 so it can describe their shipped behaviours accurately.

## Subtask Guidance

### T039 — "Mode of Work (runtime-enforced)" subsection

**Purpose**: Upgrade the baseline mode taxonomy prose from documentation-only to runtime-enforced.

**File to modify**: `docs/trail-model.md`.

**Steps**:
1. Find the existing "Mode-of-Work Taxonomy" section.
2. Update the closing sentence ("Mode-of-work is a documentation-level taxonomy in 3.2. Runtime enforcement and automatic mode detection are deferred to Phase 5.") — **replace** with:
   ```
   Mode-of-work is derived deterministically at runtime from the CLI entry command and recorded on the `started` event as the `mode_of_work` field. Runtime enforcement is active: `profile-invocation complete --evidence` is rejected for invocations in `advisory` or `query` mode (see "Mode Enforcement at Tier 2 Promotion" below).
   ```
3. Immediately after the existing table, add a new subsection:

   ```markdown
   ### Mode Enforcement at Tier 2 Promotion

   `spec-kitty profile-invocation complete --evidence <path>` is rejected with `InvalidModeForEvidenceError` when the target invocation's `mode_of_work` is `advisory` or `query`. The enforcement runs **before** any write, so the invocation remains open and uncommitted — rerun `complete` without `--evidence` to close cleanly.

   Pre-mission records (invocations opened before this enforcement landed) have no `mode_of_work` field and are accepted by enforcement — legacy behaviour is preserved. See ADR-002-mode-derivation.md for the full derivation table and rationale.
   ```

### T040 — "Correlation Links" subsection

**Purpose**: Document the new append-only `artifact_link` / `commit_link` events.

**Steps**:
1. Find the "Trail Tiers" section.
2. Immediately before "Tier 2 — Evidence Artifact" (or at a logical adjacent spot), add:

   ```markdown
   ### Correlation Links (Tier 1 extension)

   `spec-kitty profile-invocation complete` accepts two additional flags that append correlation events to the invocation JSONL:

   - `--artifact <path>` — repeatable. Each value appends one `{event: "artifact_link", invocation_id, kind, ref, at}` line to `.kittify/events/profile-invocations/<id>.jsonl`. Refs are stored repo-relative when the resolved path is under the checkout, absolute otherwise.
   - `--commit <sha>` — singular. Appends one `{event: "commit_link", invocation_id, sha, at}` line.

   Both events are append-only (never mutate existing lines) and readable by a single-file scan. Readers that do not recognise these event types may safely skip the line — the same additive-reader invariant that protects `glossary_checked`.

   See ADR-001-correlation-contract.md for the design; contracts/profile-invocation-complete.md for the CLI shape.
   ```

### T041 — "SaaS Read-Model Policy" subsection + table

**Purpose**: Mirror the `POLICY_TABLE` into an operator-readable doc so projection behaviour can be predicted without reading code.

**Steps**:
1. Find the "SaaS Projection" section.
2. Replace the existing short paragraph and Projection-behaviour table with an expanded subsection that presents the 16-row policy table:

   ```markdown
   ## SaaS Read-Model Policy

   Projection is conditional on `CheckoutSyncRouting.effective_sync_enabled`. When sync is disabled for a checkout, no events are emitted — even if the user is authenticated. When sync is enabled and the user is authenticated, Spec Kitty consults `src/specify_cli/invocation/projection_policy.py::POLICY_TABLE` to decide per `(mode_of_work, event)` what to project.

   | mode_of_work | event | project | include_request_text | include_evidence_ref |
   |--------------|-------|---------|----------------------|----------------------|
   | advisory | started | yes | no | no |
   | advisory | completed | yes | no | no |
   | advisory | artifact_link | no | — | — |
   | advisory | commit_link | no | — | — |
   | task_execution | started | yes | yes | no |
   | task_execution | completed | yes | yes | yes |
   | task_execution | artifact_link | yes | no | no |
   | task_execution | commit_link | yes | no | no |
   | mission_step | started | yes | yes | no |
   | mission_step | completed | yes | yes | yes |
   | mission_step | artifact_link | yes | no | no |
   | mission_step | commit_link | yes | no | no |
   | query | any | no | — | — |

   Pre-mission records (no `mode_of_work`) project under the `task_execution` rules — the legacy 3.2.0a5 behaviour is preserved for them.

   Policy is additive and resolvable from code/config alone. See ADR-003-projection-policy.md for the rationale.
   ```

### T042 — "Tier 2 SaaS Projection — Deferred" subsection

**Purpose**: Decisively document that Tier 2 evidence stays local-only in 3.2.x.

**Steps**:
1. Find the existing Tier 2 note in the projection table / section.
2. Add the following subsection after the SaaS Read-Model Policy table:

   ```markdown
   ## Tier 2 SaaS Projection — Deferred

   **Status**: Tier 2 evidence artifacts (`.kittify/evidence/<invocation_id>/evidence.md` and `record.json`) are **local-only** in the 3.2.x release line. They are not uploaded to SaaS. This decision was finalised by the Phase 4 closeout mission (ADR-004-tier2-saas-deferral.md).

   **Reasoning**:
   1. The shipped 3.2.0a5 baseline already behaves this way; operators observing the product today see local-only evidence.
   2. SaaS projection of evidence bodies requires privacy, redaction, and size-limit design that lies outside the Phase 4 closeout scope.
   3. Future projection remains possible without contract change — a later epic can read the existing local artifact and emit its own envelope.

   **Revisit trigger**: any of (a) a named future epic accepts SaaS evidence projection as scope, (b) operators actively request the feature with a concrete use case, (c) a regulatory or audit requirement mandates centralised retention.
   ```

### T043 — CHANGELOG.md update

**Purpose**: Capture both tranches in the unreleased section with a migration note (FR-013).

**Steps**:
1. Open `CHANGELOG.md`.
2. Under the existing `## [Unreleased - 3.2.0]` header, add:

   ```markdown
   ### Added

   - **Host-surface parity matrix** at `docs/host-surface-parity.md` — authoritative record of how each of the 15 supported host surfaces teaches the advise/ask/do governance-injection contract. Closes the remaining `#496` host-surface breadth rollout.
   - **Mode of work runtime derivation** — every `advise`, `ask`, `do` invocation now records its `mode_of_work` (`advisory`, `task_execution`, `mission_step`, `query`) on the `started` event. Derivation is from the CLI entry command.
   - **Correlation links** — `spec-kitty profile-invocation complete` accepts `--artifact <path>` (repeatable) and `--commit <sha>` (singular); each appends an additive event to the invocation JSONL for single-file request→artifact/commit correlation.
   - **SaaS read-model policy** at `src/specify_cli/invocation/projection_policy.py` — typed module mapping `(mode, event)` to projection rules. Documented in `docs/trail-model.md`.
   - **Tier 2 SaaS projection decision** — decisively documented as deferred in `docs/trail-model.md`. Tier 2 evidence stays local-only in 3.2.x.
   - **README Governance layer subsection** — entry point for operators discovering the advise/ask/do surface.

   ### Changed

   - `spec-kitty profile-invocation complete --evidence` is now mode-gated: rejected on `advisory` / `query` invocations with `InvalidModeForEvidenceError`. Rejection occurs before any write; the invocation stays open.
   - `_propagate_one` consults the new projection policy after the sync-gate and authentication lookup. Existing `task_execution` / `mission_step` projection behaviour is preserved exactly.
   - Dashboard user-visible wording: the mission selector, current-mission header, overview heading, analysis heading, and empty-state prompt now read "Mission Run" / "mission" instead of "Feature". Backend identifiers (CSS classes, HTML IDs, cookie keys, API route segments, JSON field names) are unchanged.

   ### Deferred

   - `spec-kitty explain` (issue #534) remains deferred to Phase 5 pending DRG glossary addressability (#499, #759).

   ### Migration notes

   **No operator action required for routine upgrade.** The trail model is additive:

   - Pre-mission invocation records (no `mode_of_work`) continue to accept `--evidence` and project under legacy `task_execution` rules.
   - Existing SaaS dashboards see no change for `task_execution` / `mission_step` traffic.
   - New advisory events now appear in the SaaS timeline as minimal entries without body — this is a deliberate behaviour change documented in the SaaS Read-Model Policy table.
   ```

Keep the shape consistent with existing CHANGELOG entries (Added / Changed / Fixed / Deferred sections as appropriate).

### T044 — Doc-presence test

**Purpose**: Make the doc changes mandatory for merge.

**File to create**: `tests/specify_cli/docs/test_trail_model_doc.py`

```python
"""WP08 — docs/trail-model.md subsection presence regression tests."""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
TRAIL = REPO_ROOT / "docs/trail-model.md"
CHANGELOG = REPO_ROOT / "CHANGELOG.md"


def test_trail_model_has_mode_enforcement_subsection() -> None:
    content = TRAIL.read_text()
    assert "### Mode Enforcement at Tier 2 Promotion" in content


def test_trail_model_has_correlation_links_subsection() -> None:
    content = TRAIL.read_text()
    assert "### Correlation Links (Tier 1 extension)" in content


def test_trail_model_has_saas_read_model_policy_section() -> None:
    content = TRAIL.read_text()
    assert "## SaaS Read-Model Policy" in content


def test_trail_model_has_saas_policy_table_header() -> None:
    """The 16-row policy table must be present in operator doc."""
    content = TRAIL.read_text()
    assert "| mode_of_work | event | project | include_request_text | include_evidence_ref |" in content


def test_trail_model_has_tier2_deferral_subsection() -> None:
    content = TRAIL.read_text()
    assert "## Tier 2 SaaS Projection — Deferred" in content


def test_trail_model_has_host_surfaces_subsection() -> None:
    """Pulled forward from WP05/T021."""
    content = TRAIL.read_text()
    assert "## Host surfaces that teach the trail" in content
    assert "host-surface-parity.md" in content


def test_trail_model_mode_prose_updated() -> None:
    """The documentation-only disclaimer must be gone."""
    content = TRAIL.read_text()
    assert "Mode-of-work is a documentation-level taxonomy in 3.2" not in content
    assert "Runtime enforcement is active" in content


def test_changelog_unreleased_has_both_tranches() -> None:
    content = CHANGELOG.read_text()
    # Find the Unreleased section
    assert "## [Unreleased - 3.2.0]" in content
    unrel_idx = content.index("## [Unreleased - 3.2.0]")
    next_h2 = content.find("\n## ", unrel_idx + 1)
    section = content[unrel_idx : next_h2 if next_h2 != -1 else len(content)]
    assert "host-surface parity matrix" in section.lower()
    assert "mode of work" in section.lower() or "mode_of_work" in section.lower()
    assert "correlation link" in section.lower()
    assert "projection policy" in section.lower() or "read-model policy" in section.lower()
    assert "deferred" in section.lower()  # Tier 2 deferral and/or #534


def test_changelog_mentions_534_deferral() -> None:
    content = CHANGELOG.read_text()
    assert "#534" in content  # issue ref somewhere in changelog unreleased or existing text
```

Also add a "Host surfaces that teach the trail" subsection at an appropriate location in `docs/trail-model.md` (typically near the end or in a Discoverability section):

```markdown
## Host surfaces that teach the trail

The advise/ask/do surface is taught to host LLMs through per-host skill packs. See [`docs/host-surface-parity.md`](host-surface-parity.md) for the authoritative matrix of supported hosts and each host's parity status.
```

## Definition of Done

- [ ] `docs/trail-model.md` contains six new/updated subsections: Mode Enforcement at Tier 2 Promotion, Correlation Links, SaaS Read-Model Policy (with 16-row table), Tier 2 SaaS Projection — Deferred, Host surfaces that teach the trail, and the updated mode-of-work prose.
- [ ] `CHANGELOG.md` unreleased section has both tranches' Added / Changed / Deferred entries plus the Migration notes subsection.
- [ ] `tests/specify_cli/docs/test_trail_model_doc.py` exists and all 9+ assertions pass.
- [ ] Doc is valid markdown; links resolve.
- [ ] No code changes (only docs + test).

## Risks

- **Doc drift from implementation**: the policy table text must exactly match `POLICY_TABLE` in code. Mitigation: cross-check before commit. A stricter follow-up could parse both and assert equivalence, but out of scope for this WP.
- **Broken cross-references**: links to `docs/host-surface-parity.md` must resolve; link to the WP05-created file is a forward reference at the time WP08 is authored, but WP08 only merges after WP05, so the link is live by WP08 merge time.
- **CHANGELOG formatting conflicts**: if another mission lands entries in Unreleased before this one merges, conflict resolution may require re-ordering the Added/Changed blocks. Mitigation: resolve conflicts at merge with the release owner; keep the WP08 entries as a cohesive block.

## Reviewer Guidance

Reviewer should:
- Render the updated `docs/trail-model.md` in a markdown viewer and read it end-to-end.
- Cross-check the 16-row policy table against `POLICY_TABLE` in `src/specify_cli/invocation/projection_policy.py` — they must agree exactly.
- Verify the CHANGELOG unreleased section reads coherently (both tranches in a single pass).
- Run the new test file and confirm all assertions pass.
- Confirm no code files under `src/` were modified.

## Activity Log

- 2026-04-23T06:12:11Z – claude:sonnet-4-6:implementer:implementer – shell_pid=25080 – Started implementation via action command
- 2026-04-23T06:15:46Z – claude:sonnet-4-6:implementer:implementer – shell_pid=25080 – Post-Tranche-B docs complete: 6 trail-model.md subsections + CHANGELOG + 9 doc-presence tests
- 2026-04-23T06:16:06Z – claude:sonnet-4-6:reviewer:reviewer – shell_pid=32159 – Started review via action command
- 2026-04-23T06:17:15Z – claude:sonnet-4-6:reviewer:reviewer – shell_pid=32159 – Docs + CHANGELOG approved: 6 trail-model.md subsections present; 16-row policy table matches WP07 POLICY_TABLE (4 spot checks pass); CHANGELOG has both tranches + migration notes + #534; 9/9 tests pass; mypy clean; commit 86ab7af0 touches exactly 3 files (docs/trail-model.md, CHANGELOG.md, tests/specify_cli/docs/test_trail_model_doc.py) — no src/ changes.
