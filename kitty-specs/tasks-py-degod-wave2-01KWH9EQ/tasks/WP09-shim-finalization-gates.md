---
work_package_id: WP09
title: Registration-shim finalization + AST gate + shim disposition
dependencies:
- WP08
requirement_refs:
- FR-007
- FR-008
- FR-011
tracker_refs: []
planning_base_branch: degod-follow-ups
merge_target_branch: degod-follow-ups
branch_strategy: Planning artifacts for this mission were generated on degod-follow-ups. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into degod-follow-ups unless the human explicitly redirects the landing branch.
subtasks:
- T039
- T040
- T041
- T042
- T043
phase: Phase 4 - Closure
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "953772"
history:
- at: '2026-07-02T12:53:55Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/agent/tasks.py
- src/specify_cli/cli/commands/agent/tasks_ports.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP09 – Registration-shim finalization + AST gate + shim disposition

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## ⚠️ IMPORTANT: Review Feedback

Check the `review_ref` field in the event log before starting; address all feedback.

---

## Objectives & Success Criteria

Close Stream B and Stream A's gate: `tasks.py` reaches its final registration-shim shape
(FR-003 of the plan's IC-07: wrappers + the 4 small bodies + the seam surface); the AST
0-inline-dumps gate lands with per-form theater tests (FR-007); the `tasks_ports.py`
7-line shim's disposition is decided and executed with rationale (FR-008); the final LOC
ceiling is recorded as `min(achieved, 1400)` with the delta-from-4569 rationale (FR-011).

Success: SC-001 + SC-002 delivered and non-vacuous; full parity green; tracer files
carry the close-out appends.

## Context & Constraints

- `contracts/gate-contracts.md` — BOTH gate specs, verbatim requirements (evasion forms,
  theater tests, ceiling protocol, marker obligations).
- `research.md` D5/D6 (gate patterns: `test_protection_resolver_call_sites.py` walk +
  `test_commit_target_kind_guard.py` theater pattern), D7 (final seam surface).
- Spec FR-011: if the honest final `tasks.py` exceeds 1400 LOC, STOP and escalate to the
  operator with the delta analysis — never record a higher self-certified ceiling.
- #2289 boundary: ONLY `tasks_ports.py` is in scope (the unshim cluster owns the rest);
  the fence comment on #2289 recorded this mission's ownership.

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: degod-follow-ups
- **Merge target branch**: degod-follow-ups

## Subtasks & Detailed Guidance

### Subtask T039 – Final `tasks.py` registration-shim sweep

- **Purpose**: Everything not wrapper/small-body/seam-surface leaves or dies.
- **Steps**:
  1. Inventory what remains: `grep -nE '^(def|class) ' src/specify_cli/cli/commands/agent/tasks.py`. Legitimate residents: the `@app.command` wrappers (9), `list_tasks`/`add_history`/`validate_workflow`/`list_dependents` bodies, module `console`/app setup, the seam-surface import block, `__all__` (existing 7 names — extend ONLY if an external `from tasks import X` requires it; check `grep -rn "from specify_cli.cli.commands.agent.tasks import" src/`).
  2. Relocate stragglers to their right home (`tasks_shared.py` for cross-family; the family module for single-family) using the established recipe; delete dead residue (verify dead: zero references in src/ AND tests/).
  3. Consider (and document) whether wrappers stay as `@app.command` decorators or convert to the template's `app.command(name=...)(fn)` block — choose whichever keeps the `--help` byte fixtures green (they pin help output, not registration style; prefer the smaller diff).
- **Files**: `tasks.py` + destination modules.

### Subtask T040 – AST 0-inline-dumps gate + theater tests

- **Purpose**: FR-007/SC-002, non-vacuous per C-006.
- **Steps**: Extend `tests/architectural/test_tasks_command_surface.py` (the WP01 placeholder):
  1. Walk every `src/specify_cli/cli/commands/agent/*.py` (rglob the directory, skip `__pycache__`) parsing with `ast.parse`.
  2. Detect all four forms (gate-contracts.md Gate 1): `json.dumps` attribute calls (tracking `import json as <alias>`), `from json import dumps` (+alias) calls, and rebinding assignments + calls.
  3. Empty allowlist frozenset + a growth assertion; failure message names file:line + the remediation.
  4. Theater tests: one synthetic-source proof PER form (call the detector on a string containing the offender; assert non-empty).
  5. `src/specify_cli/agent_tasks_ports.py` is outside the glob BY DESIGN (the one sanctioned dumps home) — comment this.
- **Files**: `tests/architectural/test_tasks_command_surface.py`.

### Subtask T041 – `tasks_ports.py` shim disposition (FR-008)

- **Steps**:
  1. Evidence: `grep -rn "from specify_cli.cli.commands.agent.tasks_ports import\|from .tasks_ports import\|cli.commands.agent.tasks_ports" src/ tests/` — enumerate every importer.
  2. Decide: (a) importers exist and are external/numerous → RETAIN the shim with a dated docstring rationale; (b) importers are few and internal → re-point them to `specify_cli.agent_tasks_ports` and DELETE the shim.
  3. Record the decision + evidence in `tracers/design-decisions.md` AND the Activity Log. Either way the AST gate + LOC ceiling must hold.
- **Files**: `tasks_ports.py` (+ importers if deleting).

### Subtask T042 – Final LOC ceiling + delta rationale + THE MISSION-CAP BACKSTOP

- **Steps**:
  1. Measure final `tasks.py` LOC. Set `_CEILING = min(achieved, 1400)`. A comment block records: final LOC, the 4569 baseline, the delta, and the per-WP ratchet history (from git log of the constant).
  2. **Mechanical backstop (squad HIGH — the escalation must be enforced, not prose)**: add a standing assertion in the gate file — `assert _CEILING <= 1400, "ceiling above the mission cap is an operator escalation (FR-011), never self-certified"`. This makes any `_CEILING > 1400` a RED test in its own right; the only path past 1400 is the blocked+escalate arm.
  3. If achieved > 1400: STOP — do NOT set a higher ceiling. Move this WP to blocked (`spec-kitty agent tasks move-task WP09 --to blocked --mission tasks-py-degod-wave2-01KWH9EQ`), post the delta analysis (which residents keep it above 1400 and why) to the Activity Log AND a comment on #2305, and wait for the operator.
- **Files**: `tests/architectural/test_tasks_command_surface.py`.

### Subtask T043 – Full parity + arch gates + tracer close-out

- **Steps**: Full parity guard; the WHOLE `tests/architectural/` suite (this WP claims two arch gates — prove the neighborhood is green: any pre-existing RED must already be issue-tracked per C-007, cross-base-verified); targeted surface; mypy strict on every touched file pair; ruff; append close-out notes to all three tracers (what the relocation actually cost, ceiling achieved, disposition decision).

## Test Strategy

```bash
PWHEADLESS=1 pytest tests/architectural/ -q -p no:cacheprovider   # full arch sweep (gate-owner WP)
PWHEADLESS=1 pytest tests/specify_cli/cli/commands/agent/ tests/tasks/ -q -p no:cacheprovider
python -m mypy --strict src/specify_cli/cli/commands/agent/tasks.py src/specify_cli/cli/commands/agent/tasks_ports.py tests/architectural/test_tasks_command_surface.py
```

## Risks & Mitigations

- **Ceiling honesty pressure**: the escalation rule exists precisely so this WP doesn't
  over-relocate unsafely or self-certify — use it.
- **Gate theater**: per-form theater tests are mandatory; a single generic proof is a
  review rejection.
- **Shim deletion breaking an unseen importer**: the grep evidence step; when in doubt,
  retain with rationale (retention is cheap; breakage is not).
- **`__all__` extension temptation**: the charter `__all__` MUST does NOT bind this
  module; extend only on demonstrated external-import need.

## Review Guidance

- Run both gates, then verify each theater test by temporarily neutering its detector
  locally (must fail).
- Verify the ceiling comment block's delta math against `git log -p` of the constant.
- Verify the shim decision's grep evidence is reproducible.
- `grep -nE '^(def|class) '` on final `tasks.py` — every resident justified by T039's
  taxonomy.

## Activity Log

> Append at the END, chronological. Format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`

- 2026-07-02T12:53:55Z – system – Prompt created.
- 2026-07-02T19:03:13Z – claude:fable:python-pedro:implementer – shell_pid=856859 – Assigned agent via action command
- 2026-07-02T19:58:22Z – claude:fable:python-pedro:implementer – shell_pid=856859 – Ready for review: T039 sweep tasks.py 1470->1206 (def census = exactly the 9 @app.command wrappers; 12 stragglers relocated to family modules as explicit-as re-export seams); T040 AST 0-inline-dumps gate (4 evasion forms + 4 per-form theater tests + string-immunity; shrink-only 9-file allowlist of pre-existing non-tasks siblings, tasks*.py asserted at 0); T041 shim DELETED (zero-importer census, 8514ee77c); T042 _CEILING=min(1206,1400)=1206 + standing assert _CEILING<=1400; T043 arch suite 610 passed/4 skipped after adjudicating 4 mission-introduced gate drifts (dead-symbol burn-down x2, coord-authority census 9->7 render-seam drain, cross-base green on degod-follow-ups); parity 3014 passed, only known pre-existing REDs (#2307 fr011, sphinx e2e); mypy --strict + ruff clean; tracers appended (a323b68da)
- 2026-07-02T19:59:40Z – claude:opus:reviewer-renata:reviewer – shell_pid=953772 – Started review via action command
- 2026-07-02T20:12:45Z – user – shell_pid=953772 – Review passed (reviewer-renata). tasks.py=1206 LOC, def-census EXACTLY the 9 @app.command wrappers; 12 stragglers relocated verbatim-modulo-strict-typing as 'as' re-export seams; seam batteries 230 green; arch suite 610 passed/4 skipped(env); mypy --strict + ruff clean. JUDGMENT A (AST allowlist deviation): HONEST use of gate-contracts.md's own shrink-only exception mechanism, NOT weakening — the 9 allowlisted siblings are genuinely pre-existing (0 mission commits each; dumps sites blame Feb/Jun 2026, pre-mission) and belong to the #2289-#2293 unshim fence; tasks-family surface ships at 0 dumps (verified all 16 tasks*.py); hard tasks*-exclusion assert + shrink-only count ratchet(<=9) + stale-entry eviction ALL adversarially verified to FIRE; theater tests drive the REAL _json_dumps_offenders detector across 4 forms + string-immunity. JUDGMENT B (4 arch-drift adjudications): all ROOT fixes in the shrink direction — 2 dead-symbol burn-downs have genuine live callers via _tasks.<attr> seam (grep-verified); coord-authority baseline 9->7 + WRITE_FLOOR 9->7 are DECREASES (no floor/baseline increase anywhere) matching WP04 render-seam drain, anti-masking margin gate PASSES. FR-008 shim DELETED with reproduced zero-importer census; tracers #12-#15 on canonical degod-follow-ups. FLAG for orchestrator: at mission-accept, FR-007/SC-002 acceptance-matrix evidence should note the whole-glob '0 sites' holds for tasks-family+no-new-sites MODULO 9 quarantined pre-existing non-tasks siblings (#2289-#2293).
