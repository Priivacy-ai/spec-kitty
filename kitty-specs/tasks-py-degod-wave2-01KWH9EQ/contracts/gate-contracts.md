# Gate Contracts — tasks-py-degod-wave2-01KWH9EQ

Both gates live in NEW `tests/architectural/test_tasks_command_surface.py` and MUST be
non-vacuous per DIRECTIVE_043 / spec C-006: concrete floor + self-mutation proof +
shrink-only exception semantics. Both must be CI-visible (carry `fast` +
`architectural`-selected markers; never absorbed into `_gate_coverage_baseline.json`).

## Gate 1 — AST 0-inline-dumps (FR-007, SC-002)

- **Scope**: directory glob `src/specify_cli/cli/commands/agent/*.py` — ALL current and
  future siblings (closes move-next-door evasion). `src/specify_cli/agent_tasks_ports.py`
  is the ONE sanctioned `json.dumps` home (the Render adapter) and is deliberately
  outside the glob; a comment in the gate names this.
- **Detection** (AST, immune to docstrings/strings): flag
  1. `ast.Call` on `Attribute(value=Name(id=<json-alias>), attr="dumps")` — covering
     `import json` AND `import json as <alias>` (track import aliases per file);
  2. `from json import dumps` (+ `as <alias>`) and calls to that name;
  3. name-rebinding: any assignment whose RHS resolves to `json.dumps`/imported `dumps`,
     and calls to the bound name.
- **Allowlist**: empty frozenset at ship time (0 sites). Exceptions, if ever, are
  repo-relative paths, shrink-only (a growth assertion mirrors
  `test_integration_boundary.py`).
- **Non-vacuity**: one theater test per detection form (synthetic source string
  containing the offender → detector returns non-empty), per the
  `test_commit_target_kind_guard.py` pattern.
- **Failure message**: names file:line + the remediation ("route through
  ports.render.json_envelope — see kitty-specs/tasks-py-degod-wave2-01KWH9EQ/contracts/").

## Gate 2 — Whole-file LOC ceiling (FR-011, NFR-004, SC-001)

- **Form**: `len(tasks.py read_text().splitlines()) <= _CEILING` (plain scalar; CT1
  `composite_key` N/A — no line-keyed entries; rationale in research.md D5).
- **Ratchet-down protocol**: `_CEILING` starts at 4569 (current), each relocation WP
  lowers it to the achieved size in the same commit as the move; final value
  `min(achieved, 1400)`.
- **Escalation rule — mechanically backstopped**: the gate ships (at WP09) with a
  standing `assert _CEILING <= 1400` mission-cap assertion, so a ceiling above 1400 is a
  RED test, not a judgment call. If the honest final size exceeds 1400: the WP moves to
  `blocked`, the delta-from-4569 analysis goes to the Activity Log + a #2305 comment,
  and the operator decides — never a self-certified higher ceiling.
- **Non-vacuity**: self-mutation test — a synthetic source with `_CEILING + 1` lines
  makes the check function fail (test the extracted check function directly, not the
  live file).
- **Failure message**: current LOC, ceiling, and "add behavior to sibling modules, not
  the registration shim".

## Marker obligations (FR-009 tie-in)

The new gate file and the byte-freeze suite carry markers selected by existing CI gates
(`fast`; the architectural directory is additionally selected by the
`git_repo or integration or architectural` shard). Both files appear in the FR-009
marker-census artifact with their selecting gate named.

---

## Gate 2 — RETIRED (operator ruling, 2026-07-03)

The whole-file LOC ceiling served as the mission's ratchet-down instrument
(4569 → 1205, lowered same-commit per relocation WP, verified at accept) and
is retired with the mission on PR #2308: raw size metrics belong to Sonar's
quality gate, not pytest (tests-as-friction). The anti-regrowth intent lives
on as the registration-shim header guidance in tasks.py. Gate 1 (AST dumps —
semantic) remains suite-owned and standing.
