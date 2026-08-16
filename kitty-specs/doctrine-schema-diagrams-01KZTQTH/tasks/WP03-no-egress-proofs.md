---
work_package_id: WP03
title: 'Security proofs: SANDBOX behavioral + no-egress corpus isolation'
dependencies:
- WP02
- WP05
- WP06
- WP07
requirement_refs:
- C-001
- NFR-002
planning_base_branch: feat/doctrine-schema-diagrams-impl
merge_target_branch: feat/doctrine-schema-diagrams-impl
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-schema-diagrams-impl. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-schema-diagrams-impl unless the human explicitly redirects the landing branch.
subtasks:
- T012
- T013
- T014
phase: Phase 4 - Security proofs
history:
- at: '2026-08-12T16:41:10Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/docs/test_plantuml_no_egress_corpus.py
create_intent:
- tests/docs/test_plantuml_sandbox_negative.py
- tests/docs/test_plantuml_no_egress_corpus.py
execution_mode: code_change
model: ''
owned_files:
- tests/docs/test_plantuml_sandbox_negative.py
- tests/docs/test_plantuml_no_egress_corpus.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP03 – Security proofs: SANDBOX behavioral + no-egress corpus isolation

## ⚡ Do This First: Load Agent Profile

Use `/ad-hoc-profile-load` to load `python-pedro` (implementer) and behave per its guidance first.

---

## Objectives & Success Criteria

Prove **behaviorally** that no doctrine content egresses — not by flag presence, not by "build fails".

**Definition of Done:**

1. **SANDBOX negative test**: an **`@startuml`** diagram (which honors `!includeurl`; `@startyaml` may
   not attempt the fetch at all, making "zero inbound" non-discriminating) containing `!includeurl
   http://127.0.0.1:<port>/x` renders under `-DPLANTUML_SECURITY_PROFILE=SANDBOX` and the local listener
   records **zero** inbound. The **control is a HARD assertion, not skippable**: in an egress-allowed
   job (no `--network=none`), the same diagram WITHOUT SANDBOX **must hit** the listener — proving the
   test discriminates. Skip the control ONLY where egress is genuinely blocked by the environment, never
   in the primary proof job.
2. **No-egress corpus isolation test**: the **actual authored schema-diagram corpus** (all `@startyaml`
   blocks under `docs/architecture/*.md`, discovered dynamically — NOT a hand-picked sample) renders
   under `docker run --network=none` and passes. This is the hard gate (not the ≤60s budget).
3. **URL-grep secondary lint**: scan the rendered SVG corpus for external URLs / `xlink:href` to remote
   hosts; fail on any. This is a cheap backstop, not the primary proof.

## Context & Constraints

- **Source of truth**: [contracts/no-egress-proof.md](../contracts/no-egress-proof.md) (both proofs are
  BLOCKING CI gates), [plan.md](../plan.md) IC-01. **Depends on WP02** (render step) + **WP05–WP07**
  (the authored corpus this test must cover — "not a sample").
- Reuse `scripts/docs/plantuml_invoke.py` (WP01) + `scripts/docs/plantuml_render.py` (WP02).
- Docker-gated; CI-Linux is the hard gate. Locally, skip if docker/image unavailable but keep the
  listener/URL-grep logic unit-testable with a canned SVG.

## Subtasks & Detailed Guidance

### Subtask T012 – SANDBOX behavioral negative test

- **Purpose**: prove SANDBOX actually blocks egress directives (NFR-002(a), reviewer MEDIUM).
- **Steps**:
  1. Start a local TCP listener on `127.0.0.1:<port>` in the test (stdlib `socket`/`http.server` in a
     thread) that records any inbound connection.
  2. Author an **`@startuml`** fixture with `!includeurl http://127.0.0.1:<port>/x` (NOT `@startyaml` —
     it may not honor `!includeurl`, so a no-op would fake-pass "zero inbound").
  3. Render it under SANDBOX via the invoker. Assert the listener saw **zero** inbound.
  4. **Control (HARD, not xfail)**: in an egress-allowed context (no `--network=none`), render the same
     fixture WITHOUT SANDBOX and **assert the listener IS hit** — this proves the fetch is real and
     SANDBOX is the control. Skip only where the environment itself blocks all egress, never in the
     primary proof job.
- **Files**: `tests/docs/test_plantuml_sandbox_negative.py`.
- **ATDD**: RED-first.

### Subtask T013 – No-egress corpus isolation test

- **Purpose**: prove the real corpus renders offline (NFR-002(b), reviewer HIGH — the hard gate).
- **Steps**:
  1. **Dynamically discover** every ` ```plantuml ` `@startyaml` block under `docs/architecture/*.md`
     (the WP05–WP07 diagrams). Fail if zero found (guards against a vacuous pass).
  2. Render each under `docker run --network=none`; assert each yields a valid SVG that carries the
     diagram's title/key tokens and has **no PlantUML error signature** (reuse WP01's `svg_is_error`) —
     a mere "non-empty SVG" would green-light a font/DNS error image, defeating the gate.
  3. Assert the set rendered equals the set discovered (no silent skips).
- **Files**: `tests/docs/test_plantuml_no_egress_corpus.py`.
- **Notes**: this is why WP03 depends on WP05–WP07 — the corpus must exist. Discovery-by-scan keeps it
  honest ("not a sample").

### Subtask T014 – URL-grep secondary lint  `[P]`

- **Purpose**: cheap backstop for accidental remote refs.
- **Steps**: grep the rendered SVGs (and the `@startyaml` sources) for `http(s)://` external hosts /
  remote `xlink:href`; allow only local/data URIs; fail otherwise. Label it clearly as secondary.
- **Files**: fold into `tests/docs/test_plantuml_no_egress_corpus.py`.

## Branch Strategy

- **Strategy**: merge back into `feat/doctrine-schema-diagrams-impl`.
- **Planning base branch**: `feat/doctrine-schema-diagrams-impl`
- **Merge target branch**: `feat/doctrine-schema-diagrams-impl`

## Test Strategy

- `PWHEADLESS=1 python3 -m pytest tests/docs/test_plantuml_sandbox_negative.py tests/docs/test_plantuml_no_egress_corpus.py -q`.
- Docker + a real corpus required for the full assertions; both run in CI.

## Risks & Mitigations

- **Runner blocks all egress anyway** → the non-SANDBOX control can't distinguish. Mitigation: make the
  control a documented xfail/skip; the primary assertion (listener zero-inbound under SANDBOX) still holds.
- **Vacuous pass (empty corpus)** → false green. Mitigation: fail if discovery finds zero diagrams.

## Review Guidance

- Confirm the SANDBOX test is behavioral (listener), not "build fails".
- Confirm the corpus test discovers dynamically and fails on empty.
- Confirm zero external URLs in the rendered corpus.
- Reviewer ≠ implementer; verify RED-first + that removing SANDBOX flips the negative test.

## Activity Log

> Append newest entries at the END, chronological.
