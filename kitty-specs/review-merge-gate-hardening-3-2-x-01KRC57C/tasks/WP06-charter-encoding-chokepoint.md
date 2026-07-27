---
work_package_id: WP06
title: Charter encoding chokepoint
dependencies: []
requirement_refs:
- FR-016
- FR-017
- FR-018
- FR-019
- FR-020
- FR-021
- FR-022
planning_base_branch: fix/3.2.x-review-merge-gate-hardening
merge_target_branch: fix/3.2.x-review-merge-gate-hardening
branch_strategy: Planning artifacts for this mission were generated on fix/3.2.x-review-merge-gate-hardening. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/3.2.x-review-merge-gate-hardening unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-review-merge-gate-hardening-3-2-x-01KRC57C
base_commit: fb6a45d54c20041636a147d70c43b3f6d94544b9
created_at: '2026-05-12T13:13:48.269449+00:00'
subtasks:
- T032
- T033
- T034
- T035
- T036
- T037
- T038
agent: "claude:opus:reviewer:reviewer"
shell_pid: "492717"
history:
- at: '2026-05-12'
  actor: planner
  event: created
agent_profile: implementer-ivan
authoritative_surface: src/charter/_io.py
execution_mode: code_change
mission_id: 01KRC57CNW5JCVBRV8RAQ2ARXZ
mission_slug: review-merge-gate-hardening-3-2-x-01KRC57C
owned_files:
- pyproject.toml
- src/charter/_io.py
- src/charter/_diagnostics.py
- src/charter/compiler.py
- src/charter/sync.py
- src/charter/interview.py
- src/charter/ERROR_CODES.md
- tests/charter/test_encoding_chokepoint.py
- tests/charter/test_unsafe_bypass.py
- tests/charter/test_provenance_dual_storage.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else below, load the assigned agent profile so your behavior, boundaries, and governance scope match the role:

```
/ad-hoc-profile-load implementer-ivan
```

The profile establishes your identity (Implementer Ivan), primary focus (writing and verifying production-grade code), and avoidance boundary (no architectural redesign; no scope expansion beyond what this WP authorizes). If the profile load fails, stop and surface the error — do not improvise a role.

## Objective

Introduce a single ingestion chokepoint at the charter-content boundary that detects source encoding, records provenance, normalizes to UTF-8, and fails loudly on mixed/ambiguous content (with `--unsafe` bypass). Promote `charset-normalizer` to a direct dependency. Stay within NFR-004's 5-module budget.

This WP addresses [#644](https://github.com/Priivacy-ai/spec-kitty/issues/644) (narrowed slice) and satisfies FR-016 through FR-022, FR-033, FR-034 in [`../spec.md`](../spec.md), plus NFR-001, NFR-004, NFR-007, NFR-008.

Reference contracts:
- [`../contracts/charter-io-chokepoint.md`](../contracts/charter-io-chokepoint.md)
- [`../contracts/encoding-provenance-schema.md`](../contracts/encoding-provenance-schema.md)
- [`../data-model.md`](../data-model.md) §3

## Context

The charter subsystem has 18 `read_text(encoding="utf-8")` call sites across 8 modules. The audit in `research.md` R-7 confirms only three are real **ingest boundaries** (external sources entering the system): `compiler.py:594`, `sync.py:151`, `interview.py:283,398`. The other five are re-reads of files already normalized through an ingest — they remain unchanged in this WP.

The chokepoint sits at `src/charter/_io.py` and exposes `load_charter_file()` / `load_charter_bytes()`. Detection order: BOM sniff → strict UTF-8 → `charset-normalizer` ≥ 0.85 confidence → fail with `CHARTER_ENCODING_AMBIGUOUS`. The `--unsafe` flag bypasses the fail with the highest-confidence candidate; the bypass is recorded in provenance.

Provenance has dual storage per HiC decision: per-mission (`kitty-specs/<mission>/.encoding-provenance.jsonl`) preferred, centralized (`.kittify/encoding-provenance/global.jsonl`) for non-mission-scoped content. Same record schema; no duplication.

**Hard constraint — NFR-004**: this WP touches **at most 5 unrelated modules** (new `_io.py` + new `_diagnostics.py` + 3 retrofit sites = 5). If implementation forces broader retrofit, **escalate to scope review — do not silently broaden.**

## Branch Strategy

- **Planning/base branch**: `fix/3.2.x-review-merge-gate-hardening`
- **Final merge target**: `main` (after PR review)
- **Execution worktree**: assigned by `spec-kitty implement WP06`. WP06 is independent; runs in parallel with WP02/WP04/WP05/WP07.

## Subtasks

### T032 [P] — Promote `charset-normalizer` to a direct dependency

**Purpose**: declare an intentional version contract for the encoding detector. It's already in our supply chain transitively via `requests` at 3.4.7; this promotion makes our use deliberate and immune to upstream-requests detector changes.

**Steps**:

1. Edit `pyproject.toml` `[project.dependencies]` to include `"charset-normalizer>=3.4,<4"`. Place alphabetically with the other direct deps.
2. Run `uv lock` to regenerate `uv.lock`. The lock should show `charset-normalizer` as a direct constraint (not just transitive).
3. Sanity-check the install:
   ```bash
   uv sync
   uv run python -c "from charset_normalizer import from_bytes; print(from_bytes(b'hello').best())"
   ```

**Files**: `pyproject.toml`, `uv.lock`

**Validation**:
- [ ] `uv tree` shows `charset-normalizer` at top level (direct dep).
- [ ] CI install passes.

### T033 [P] — `CharterEncodingDiagnostic` StrEnum

**Purpose**: typed source of truth for the two charter-encoding diagnostic codes.

**Steps**:

1. Create `src/charter/_diagnostics.py`:
   ```python
   """Charter-encoding diagnostic codes.

   See: src/charter/ERROR_CODES.md (hand-maintained mirror until the
   code-to-docs flow envisioned in GitHub #645 ships).
   """

   from enum import StrEnum


   class CharterEncodingDiagnostic(StrEnum):
       AMBIGUOUS = "CHARTER_ENCODING_AMBIGUOUS"
       NOT_NORMALIZED = "CHARTER_ENCODING_NOT_NORMALIZED"
   ```

**Files**: `src/charter/_diagnostics.py` (new)

**Validation**:
- [ ] mypy strict passes.
- [ ] StrEnum members match `data-model.md` §3.

### T034 — Create `src/charter/_io.py` (the chokepoint)

**Purpose**: the single ingestion boundary. Returns `CharterContent`; writes provenance; raises with `CHARTER_ENCODING_AMBIGUOUS` when detection fails (and `--unsafe` is not set).

**Steps**:

1. Create `src/charter/_io.py` per the contract in `contracts/charter-io-chokepoint.md`:
   ```python
   """Single ingestion chokepoint for charter content.

   Detects source encoding, records provenance, normalizes to UTF-8.
   See: src/charter/ERROR_CODES.md
   """

   from __future__ import annotations
   from dataclasses import dataclass
   from datetime import datetime, timezone
   from pathlib import Path
   import json
   import os

   from charset_normalizer import from_bytes
   from ._diagnostics import CharterEncodingDiagnostic


   _CONFIDENCE_THRESHOLD = 0.85


   @dataclass(frozen=True)
   class CharterContent:
       text: str
       source_encoding: str
       confidence: float
       source_path: Path | None
       normalization_applied: bool


   class CharterEncodingError(Exception):
       def __init__(self, code: CharterEncodingDiagnostic, body: str):
           super().__init__(code.value)
           self.code = code
           self.body = body


   def load_charter_file(path: Path, *, unsafe: bool = False) -> CharterContent:
       data = path.read_bytes()
       return _load_inner(data, source_path=path, unsafe=unsafe)


   def load_charter_bytes(data: bytes, *, origin: str, unsafe: bool = False) -> CharterContent:
       return _load_inner(data, source_path=None, unsafe=unsafe, origin=origin)


   def _load_inner(
       data: bytes,
       *,
       source_path: Path | None,
       unsafe: bool,
       origin: str | None = None,
   ) -> CharterContent:
       # 1. BOM sniff.
       if data.startswith(b"\xef\xbb\xbf"):
           text = data[3:].decode("utf-8")
           content = CharterContent(text, "utf-8-sig", 1.0, source_path, True)
           _write_provenance(content, bypass_used=False)
           return content

       # 2. Strict UTF-8.
       try:
           text = data.decode("utf-8")
           content = CharterContent(text, "utf-8", 1.0, source_path, False)
           _write_provenance(content, bypass_used=False)
           return content
       except UnicodeDecodeError:
           pass

       # 3. charset-normalizer.
       match = from_bytes(data).best()
       if match is not None:
           confidence = 1.0 - match.chaos
           if confidence >= _CONFIDENCE_THRESHOLD or unsafe:
               text = str(match)
               content = CharterContent(
                   text=text,
                   source_encoding=match.encoding,
                   confidence=confidence,
                   source_path=source_path,
                   normalization_applied=True,
               )
               _write_provenance(content, bypass_used=unsafe)
               return content

       # 4. Fail.
       raise CharterEncodingError(
           CharterEncodingDiagnostic.AMBIGUOUS,
           _build_ambiguous_body(data, source_path, match),
       )


   def _write_provenance(content: CharterContent, *, bypass_used: bool) -> None:
       record = _build_provenance_record(content, bypass_used=bypass_used)
       provenance_path = _route_provenance_path(content.source_path)
       provenance_path.parent.mkdir(parents=True, exist_ok=True)
       with provenance_path.open("a", encoding="utf-8") as f:
           f.write(json.dumps(record, sort_keys=True) + "\n")


   def _route_provenance_path(source_path: Path | None) -> Path:
       """Per FR-022: per-mission for paths under kitty-specs/<mission>/;
       centralized for everything else.
       """
       if source_path is None:
           return Path(".kittify/encoding-provenance/global.jsonl")
       resolved = source_path.resolve()
       parts = resolved.parts
       if "kitty-specs" in parts:
           idx = parts.index("kitty-specs")
           mission_dir = Path(*parts[: idx + 2])
           return mission_dir / ".encoding-provenance.jsonl"
       return Path(".kittify/encoding-provenance/global.jsonl")
   ```
2. Implement `_build_provenance_record()` per `data-model.md` §3 (`event_id` via ULID, `at` ISO-8601 UTC, `mission_id` resolved from `<mission>/meta.json` when path is per-mission).
3. Implement `_build_ambiguous_body()` to produce the operator-facing diagnostic body per `contracts/charter-io-chokepoint.md` (named file, candidate list with confidences, mixed-content signal description, three remediation options including `--unsafe`).

**Files**: `src/charter/_io.py` (new)

**Validation**:
- [ ] mypy strict passes.
- [ ] Unit tests covering each detection branch + provenance routing (in T038).

### T035 — Retrofit 3 ingest sites

**Purpose**: replace `read_text(encoding="utf-8")` calls at the three ingest boundaries with `load_charter_file()`.

**Steps**:

1. **`src/charter/compiler.py:594`**: change `yaml.load(path.read_text(encoding="utf-8"))` → `yaml.load(load_charter_file(path).text)`. Add the import at the top: `from ._io import load_charter_file`.
2. **`src/charter/sync.py:151`**: change `charter_path.read_text("utf-8")` → `load_charter_file(charter_path).text`. Add the import.
3. **`src/charter/interview.py:283 and 398`**: same pattern at both locations.
4. **Do NOT modify** `context.py`, `hasher.py`, `language_scope.py`, `compact.py`, `neutrality/lint.py`. These are re-reads of normalized files; they remain explicit UTF-8.
5. If implementation reveals a 4th ingest site (e.g., a code path that ingests bytes from the SaaS payload without going through `sync.py`), STOP and surface it for scope review — do not silently retrofit it.

**Files**: `src/charter/compiler.py`, `src/charter/sync.py`, `src/charter/interview.py`

**Validation**:
- [ ] All 3 sites use `load_charter_file()`.
- [ ] Module count touched by this WP = 5 (new `_io.py`, new `_diagnostics.py`, 3 retrofits). NFR-004 budget respected.
- [ ] Existing charter tests pass.

### T036 — `--unsafe` bypass

**Purpose**: operator escape hatch for `CHARTER_ENCODING_AMBIGUOUS`. Propagates from the CLI down to `load_charter_file(..., unsafe=True)`.

**Steps**:

1. Identify the CLI commands that ingest charter content: `spec-kitty charter compile`, `spec-kitty charter sync`, the interview command. For each, add a `--unsafe` flag.
2. Plumb the flag through to `load_charter_file(..., unsafe=True)`. Pattern:
   ```python
   @app.command()
   def compile(..., unsafe: bool = typer.Option(False, "--unsafe", help="Bypass CHARTER_ENCODING_AMBIGUOUS using highest-confidence decode; logs bypass_used=true.")):
       ...
       content = load_charter_file(path, unsafe=unsafe)
   ```
3. Document the flag's danger in its `--help` text: "Use only when you've inspected the file and accept the operational risk; the bypass is recorded in `.encoding-provenance.jsonl`."

**Files**: CLI command modules under `src/specify_cli/cli/commands/charter*.py` (or wherever charter CLI lives — likely under `agent/charter*` per the agent action convention). Adjust `owned_files` if the actual location differs.

**Validation**:
- [ ] `--unsafe` propagates to the chokepoint.
- [ ] Bypass produces a successful read with `bypass_used: true` in provenance (test in T038).

### T037 [P] — `ERROR_CODES.md`; glossary entries delegated to WP03

**Purpose**: per-subsystem doc (FR-033). Glossary entries are owned by WP03 in this mission (see WP06 frontmatter — glossary file is NOT in WP06's `owned_files`).

**Steps**:

1. Create `src/charter/ERROR_CODES.md` per the layout in `data-model.md` §5. Two sections: `CHARTER_ENCODING_AMBIGUOUS`, `CHARTER_ENCODING_NOT_NORMALIZED`. Each with "When it fires", "JSON stability", "Remediation", "Body example".
2. Update `src/charter/_diagnostics.py` class docstring to reference `src/charter/ERROR_CODES.md` explicitly (already in T033's template).
3. **Glossary entries delegated to WP03**. In WP06's PR description, list the glossary entries this WP requires:
   - `encoding chokepoint`
   - `encoding provenance`
   - `unsafe bypass`

   WP03's implementer reads this list and adds the entries when authoring `.kittify/glossaries/spec_kitty_core.yaml` (which WP03 owns). Use the canonical definitions in `data-model.md` §6.

**Files**: `src/charter/ERROR_CODES.md` (new). **Do NOT touch the glossary file** — that's WP03's territory.

**Validation**:
- [ ] Section count in ERROR_CODES.md == StrEnum member count (2).
- [ ] Cross-reference test (in T038): every member has a section.

### T038 — Regression tests

**Purpose**: prove every part of the chokepoint contract.

**Steps**:

1. Create `tests/charter/test_encoding_chokepoint.py`:
   - `test_pure_utf8_ingest_records_provenance_without_normalization` — `confidence=1.0`, `normalization_applied=False`, `source_encoding="utf-8"`.
   - `test_cp1252_ingest_normalizes_and_records_provenance` — `normalization_applied=True`, `source_encoding="cp1252"`, provenance record present.
   - `test_bom_sniff_recognized` — UTF-8-BOM file.
   - `test_ambiguous_content_raises_without_unsafe` — mixed cp1252/UTF-8 input raises `CharterEncodingError(AMBIGUOUS)`.
2. Create `tests/charter/test_unsafe_bypass.py`:
   - `test_unsafe_bypass_succeeds_on_ambiguous_input` — same input as above, `unsafe=True` succeeds.
   - `test_unsafe_bypass_records_bypass_used_flag` — provenance record has `bypass_used: true`.
3. Create `tests/charter/test_provenance_dual_storage.py`:
   - `test_per_mission_routing` — ingest of `kitty-specs/<m>/charter/x.yaml` writes to `kitty-specs/<m>/.encoding-provenance.jsonl`.
   - `test_centralized_routing` — ingest of `.kittify/charter/y.yaml` writes to `.kittify/encoding-provenance/global.jsonl`.
   - `test_no_duplication` — single ingest produces exactly one record across both files.

**Files**: 3 new test files under `tests/charter/`.

**Validation**:
- [ ] All tests pass.
- [ ] Reverting T034's routing makes the routing tests fail — proves they exercise the contract.

## Definition of Done

- [ ] T032–T038 acceptance checks pass.
- [ ] FR-016 through FR-022, FR-033, FR-034 cited in commits.
- [ ] NFR-004 verified by counting modules touched (≤ 5).
- [ ] Glossary updated; ERROR_CODES.md authored.

## Risks and Reviewer Guidance

**Risk**: scope creep into the 5 deferred re-read sites. **STOP if more than 5 modules need modification.** Reviewer should verify the diff touches at most 5 modules.

**Risk**: `charset-normalizer` returning a candidate with confidence >= 0.85 on actually-ambiguous content. The detector is heuristic; the threshold is empirically tuned. If a real-world ambiguous file passes the threshold, this is a separate bug — not a WP06 regression. Operators have `--unsafe` for explicit acceptance.

**Reviewer focus**:
- T034: detection order matches the contract exactly.
- T035: only 3 retrofit sites; the 5 deferred sites are untouched.
- T038: every contract assertion has a test.

## Suggested implement command

```bash
spec-kitty agent action implement WP06 --agent claude --mission review-merge-gate-hardening-3-2-x-01KRC57C
```

## Activity Log

- 2026-05-12T13:13:50Z – claude:sonnet:implementer-ivan:implementer – shell_pid=464158 – Assigned agent via action command
- 2026-05-12T13:24:21Z – claude:sonnet:implementer-ivan:implementer – shell_pid=464158 – WP06 ready: chokepoint + 3 retrofits + dual provenance + unsafe bypass + ERROR_CODES.md + 3 test files. NFR-004 budget respected (5 modules: _io.py, _diagnostics.py, compiler.py, sync.py, interview.py). Deferred sites (context.py, hasher.py, language_scope.py, compact.py, neutrality/lint.py) unchanged. Glossary entries delegated to WP03: encoding chokepoint, encoding provenance, unsafe bypass. 13 new tests pass; 735 existing charter tests pass (1 unrelated skipped).
- 2026-05-12T13:25:30Z – claude:opus:reviewer:reviewer – shell_pid=492717 – Started review via action command
- 2026-05-12T13:27:50Z – claude:opus:reviewer:reviewer – shell_pid=492717 – Review passed: FR-016/017/018/019/020/021/022 implemented via _io.py chokepoint; NFR-004 module count = 5 (_io.py, _diagnostics.py, compiler.py, sync.py, interview.py); 5 deferred sites untouched; detection order verified: BOM -> strict UTF-8 -> charset-normalizer >=0.85 -> fail/--unsafe bypass; provenance routing per-mission vs global with no duplication; 13 targeted tests + 735 charter tests pass; glossary delegation to WP03 honored.
