# Renata Review — Sync Diagnose Canonical Event-Type Registry

**Reviewer**: Reviewer Renata (built-in profile,
`src/doctrine/agent_profiles/built-in/reviewer-renata.agent.yaml`)
**Date**: 2026-05-21
**Mission**: `sync-diagnose-canonical-allowlist-01KS4F8H`
**Anchor**: `Priivacy-ai/spec-kitty#1222`
**Mode**: design-review (pre-implementation pass over spec / plan /
tasks / WP01).

## Identity declaration

I am Reviewer Renata. I evaluate code, designs, and documents for
quality, correctness, and adherence to standards. I provide structured,
actionable feedback. I am a quality gate, not an implementer — I do not
rewrite the work myself.

## Scope of this review

- `spec.md`
- `plan.md`
- `tasks.md`
- `tasks/WP01.md`
- `checklists/requirements.md`
- `analyze.md`

I do not yet review the implementation (no code has been written at
this phase). I will return for a code-review pass after the
implement-review loop.

## Review by directive

### Directive 001 — Architectural Integrity

| Check | Verdict | Note |
|---|---|---|
| Component boundary respected | PASS | The change is confined to `specify_cli.sync.diagnose`. The emitter's outbound gate is explicitly out of scope and preserved. The status-model package is not touched. |
| Single responsibility per module | PASS | `diagnose.py` retains its role (validate queued events). `emitter.py` retains its role (gate outbound emission). The two were previously conflated via a shared `VALID_EVENT_TYPES`; the plan disentangles them — that is an *improvement* in architectural integrity, not a violation. |
| New cross-package dependency | NEUTRAL | The plan adds an import of `spec_kitty_events.conformance.validators._EVENT_TYPE_TO_MODEL`. The same import already exists in production at `src/specify_cli/status/lifecycle_events.py:210`, so this does not introduce a *new* cross-package dependency — it re-uses an existing one. Plan.md documents the precedent. |

### Directive 024 — Locality of Change

| Check | Verdict | Note |
|---|---|---|
| Scope matches stated objective | PASS | Spec, plan, tasks, and WP01 all explicitly list the diff surface: `diagnose.py`, `test_diagnose.py`, mission dir. No template, migration, or doc edits planned. |
| No drive-by edits planned | PASS | Mission scope explicitly excludes "other tools with their own allowlist" — they are documented as `#1198` follow-ups in `mission-review.md`, not fixed here. |

### Directive 030 — Test and Typecheck Quality Gate

| Check | Verdict | Note |
|---|---|---|
| Tests planned before implementation | PASS | TDD order is explicit in `WP01.md` → "Test first". |
| Drift-detector covers FR-004 | PASS | `test_drift_detector_picks_up_new_registry_entries` uses `monkeypatch.setitem` against `_EVENT_TYPE_TO_MODEL` and reloads `KNOWN_EVENT_TYPES` to prove the registry is the genuine source of truth. |
| Existing tests preserved | PASS | Plan documents that `tests/sync/test_diagnose.py::TestExtendedEnvelope::test_unknown_event_type` continues to assert rejection via a substring predicate that matches the widened error message ("not in canonical registry or local payload rules" still satisfies `"event_type" in e.lower() or "unknown" in e.lower()`). |
| Outbound-gate tests preserved | PASS | FR-007 + explicit smoke step in WP01 T003. |
| Static checks | NEUTRAL | This is a typed Python project; `ruff` will run via CI; no new type complexity. |

### Directive 032 — Conceptual Alignment

| Check | Verdict | Note |
|---|---|---|
| Glossary alignment | PASS | The constant name `KNOWN_EVENT_TYPES` is glossary-aligned (recognition surface), distinct from `VALID_EVENT_TYPES` (outbound gate). The two concepts are now named differently — that is a small but real conceptual-clarity win. |
| Doctrine alignment | PASS | Mission directly concretises the canonical-registry doctrine tracked under `#1198`. Mission documents the doctrine connection in spec.md and analyze.md. |

## Drift-class hazard scan

| Hazard | Verdict | Note |
|---|---|---|
| Hand-rolled event dict in producer | PASS | The mission is recognition-only; no event emission is added. Tests construct envelopes via the existing `_make_valid_event` helper (already in the codebase and used by every test in `test_diagnose.py`); per NFR-004 any payload-shape construction goes through canonical pydantic models. |
| New producer not routed through `spec_kitty_events` pydantic models | PASS | No new producer. |
| Silent guard bypass | PASS | The change *narrows* the false-positive surface (unknown-event noise) while preserving the rejection path for genuinely unknown types (FR-003 + existing `test_unknown_event_type`). |
| Recognition vs. emission conflation | PASS — FIXED | This is the doctrine-concretising point: the two contracts are now distinct symbols (`KNOWN_EVENT_TYPES` vs. `VALID_EVENT_TYPES`). The plan documents *why* — the prior conflation was the root cause of the bug. |

## Operating-rule compliance (from `start-here.md`)

| Rule | Verdict |
|---|---|
| Producers use canonical `spec_kitty_events.lifecycle` pydantic models | PASS — no new producer in scope; test envelopes use the existing canonical-shaped helper |
| No new pip dependencies | PASS — only re-uses already-pinned `spec_kitty_events` |
| `unset GITHUB_TOKEN` before `gh` writes | PLANNED — will execute at PR creation |
| No direct push to `main`; PR-based | PLANNED — branch is `kitty/mission-sync-diagnose-canonical-allowlist-01KS4F8H` |
| Reviewer is `reviewer-renata` | PASS — this review |
| `frontend-freddy` for frontend code | N/A — backend only |

## Findings

### Blockers

**None.**

### Suggestions (non-blocking)

1. **(advisory)** The drift-detector test relies on `importlib.reload`
   to pick up the monkeypatched registry. Confirm during implementation
   that no other module under test caches `KNOWN_EVENT_TYPES` at import
   time in a way that would defeat the reload. (Note: only
   `diagnose.py` imports/computes the recognition set, so the reload
   should be sufficient; the implementer should still verify.)

2. **(advisory)** When updating the error message in
   `_validate_extended_envelope`, keep the offending `event_type` value
   in the message — both for operator readability and to satisfy the
   FR-003 wording.

## Verdict

**APPROVE for implement-review loop.**

No blockers. Two non-blocking advisories captured above. The
implementer (WP01) may proceed directly into TDD. Renata will return
for the code-review pass during the implement-review loop.
