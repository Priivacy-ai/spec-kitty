# WP01 — Verification Evidence

**Run on branch:** main
**Run at (UTC):** 2026-04-29T05:15:40Z
**Operator:** claude:opus-4-7:researcher-robbie:researcher

## T001 — Regression-guard test results

Command:

```bash
uv run pytest \
  tests/next/test_retrospective_terminus_wiring.py \
  tests/retrospective/test_gate_decision.py \
  tests/doctrine_synthesizer/test_path_traversal_rejection.py \
  -q --tb=short
```

Aggregate result: `109 passed in 20.52s`.

| Test file | Outcome | Notes |
|---|---|---|
| `tests/next/test_retrospective_terminus_wiring.py` | PASS | 12 tests passed (real-bridge rollback / no-completion-event guard intact) |
| `tests/retrospective/test_gate_decision.py` | PASS | 38 tests passed (gate-decision policy guard intact) |
| `tests/doctrine_synthesizer/test_path_traversal_rejection.py` | PASS | 59 tests passed (path-traversal rejection guard intact) |

Terminal evidence at `_artifacts/regression-guard-output.txt`.

## T002 — `runtime_bridge.py` + `retrospective/schema.py` invariants

NOTE on path: the spec brief said `src/charter/retrospective/schema.py`. Actual modern path is `src/specify_cli/retrospective/schema.py` (verified via `find src -name schema.py -path '*retrospective*'`). The brief's "Risks & Mitigations" explicitly anticipates this drift; resolved path documented here.

- **Retrospective gate placement (composition path) — PASS:** `src/specify_cli/next/runtime_bridge.py:1109-1147`. The gate runs in the `elif decision.kind == "terminal" and did_complete_step:` branch BEFORE `sync_emitter.emit_mission_run_completed(mc_payload)` is called at line 1147. Quote: *"Any blocking decision propagates as ``MissionCompletionBlocked`` and prevents ``MissionRunCompleted`` from being emitted, keeping the audit trail honest."* (lines 1115-1117).

- **Retrospective gate placement (legacy DAG path, buffered emitter) — PASS:** `src/specify_cli/next/runtime_bridge.py:1740-1795`. The legacy `runtime_next_step` path uses a `_BufferingRuntimeEmitter` that records emit calls without firing them; the gate consults the result and either flushes (allowed) or discards the buffer plus restores state (blocked). Quote: *"terminal + opt-in + gate blocks → discard buffer (no events ever leave the bridge) AND restore state.json + truncate run.events.jsonl to pre-call shape."* (lines 1755-1757).

- **Mixed-case ID acceptance — PASS:** `src/specify_cli/retrospective/schema.py:194` defines `_SLUG_REGEX = r"^[A-Za-z0-9._-]{1,128}$"`. The alphabet is explicitly described in the docstring (lines 180-193) as accepting lowercase glossary terms AND mixed-case doctrine artifact ids: *"e.g. ``DIRECTIVE_001``, ``TACTIC_phase_2``, ``PROCEDURE-v2``"*. Both `DIRECTIVE_NEW_EXAMPLE` and `PROJECT_001` match this regex.

- **Path-traversal rejection — PASS:** `src/specify_cli/retrospective/schema.py:197-206`, the `_validate_safe_slug` AfterValidator. Quote: *"if ``..`` in value: raise ValueError(\"identifier must not contain '..': path-traversal sequences are forbidden\")"* (lines 202-205). Leading-dot rejection is on lines 198-201. Defense in depth via `_assert_within` is mentioned at line 193.

## T003 — Golden-path helper invariants

- **`_parse_first_json_object` uses full-stdout `json.loads` — PASS:** `tests/e2e/test_charter_epic_golden_path.py:116-129`. At line 126: `parsed = json.loads(stdout)` — operates on the FULL stdout, no regex pre-extraction, no first-`{` slicing. Docstring (lines 119-124) explicitly forbids preprocessing: *"``json.loads(stdout)`` MUST succeed without preprocessing. Trailing text after the JSON envelope is a contract violation..."*

- **`_run_next_and_assert_lifecycle` HARD-FAILS on missing trail — PASS:** `tests/e2e/test_charter_epic_golden_path.py:598-608`. Quote: `if not lifecycle_path.is_file(): raise AssertionError("WP05 / #843 / FR-011: ... does not exist after `next` issued an action. WP05 must write a `started` lifecycle record at issuance time.")`. No permissive return / no warning-only branch — the function raises `AssertionError` and aborts.

- **Real-synthesizer call (no `.kittify/doctrine` seeding) — PASS:** `tests/e2e/test_charter_epic_golden_path.py:389-412`. Pre-condition assertion at lines 395-399: `assert not doctrine_path.exists(), ("Test pre-condition: .kittify/doctrine/ must not exist before \`charter synthesize\` runs (we do not hand-seed it).")`. Then `charter synthesize --json` is invoked via the public CLI at line 401-402 against the real synthesizer. Post-condition asserts the directory was created BY the synthesizer (lines 408-412).

## Disposition

**Verdict:** GO

All three regression-guard test files pass (109/109). All five source-level invariants (2 in runtime_bridge.py + 2 in retrospective/schema.py + 3 in golden-path helpers) are present and intact in current `main`.

FR-009: VERIFIED INTACT
FR-010: VERIFIED INTACT

No production-code changes made by this WP. WP02/WP03/WP04 may proceed without absorbing any C-003 escalations from this verification baseline.
