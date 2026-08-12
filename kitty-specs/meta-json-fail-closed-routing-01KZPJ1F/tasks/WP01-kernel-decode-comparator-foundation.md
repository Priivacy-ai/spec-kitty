---
work_package_id: WP01
title: Kernel decode + comparator foundation
dependencies: []
requirement_refs:
- C-008
- C-010
- C-011
- FR-001
- FR-002
- FR-006
- NFR-001
planning_base_branch: feat/meta-json-l1-seam-routing-3259
merge_target_branch: feat/meta-json-l1-seam-routing-3259
branch_strategy: Planning artifacts for this mission were generated on feat/meta-json-l1-seam-routing-3259. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/meta-json-l1-seam-routing-3259 unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
history:
- at: '2026-08-10'
  note: Authored by /spec-kitty.tasks (post-plan-squad model).
agent_profile: python-pedro
authoritative_surface: src/kernel/
create_intent:
- src/kernel/meta_decode.py
- src/kernel/vcs_lock.py
- tests/architectural/test_meta_decode_l1.py
execution_mode: code_change
owned_files:
- src/kernel/meta_decode.py
- src/kernel/vcs_lock.py
- src/specify_cli/mission_metadata.py
- src/specify_cli/core/paths.py
- tests/architectural/test_meta_decode_l1.py
- tests/specify_cli/test_meta_fail_closed_full_census_contract.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile:

```
/ad-hoc-profile-load python-pedro
```

Apply its initialization, boundaries, directives, and tactics. Then read this WP, `spec.md`, `plan.md`, `data-model.md` (the seam + error-translation tables), and `research.md` (D1/D2/D4).

## Objective

Build the foundation the whole mission routes onto: a **kernel-resident** L1 pure-decode primitive and the **unified VCS-lock comparator**, then re-express L2 and L3 on top. This WP is **additive + refactor only — no private parser is deleted here** (their five call sites still resolve), and it is **census-neutral**: it must not change the routed-census count out of band, and it must not add the new symbols to `ROUTED_CALLEES` (WP05 does that).

Kernel placement is load-bearing: `git/ref_advance.py` (site A, WP02) is git plumbing and may not import `specify_cli` (C-003), and L2 (`mission_metadata.py`) imports `specify_cli.core.*` — so the decoder and comparator MUST live in `src/kernel/` (the zero-dependency root), which every layer may depend on.

## Context

- Live census on this branch: routed **134**, floor **130**, margin **4**. Measure with:
  `python -c "from tests.architectural.test_inline_meta_read_gate import scan_routed_load_meta_calls, SRC_ROOT; print(len(scan_routed_load_meta_calls(SRC_ROOT)))"`
- Existing seam: L2 `mission_metadata._parse_meta_text` (~:331); L3 `core.paths.load_meta_fail_closed` (~:638, `except ValueError`→`MissionMetaReadError` at ~:677). The `core.paths`↔`mission_metadata` cycle rests on one back-edge: `paths.py:670` deferred-imports `mission_metadata.load_meta`.
- Kernel error base today is `kernel.errors.KittyInternalConsistencyError` — **NOT a ValueError**. Do not extend it for `MetaDecodeError`.

### Subtask T001 — kernel/meta_decode.py: `decode_meta` + `MetaDecodeError(ValueError)`

Create `src/kernel/meta_decode.py` (stdlib `json` only — kernel imports nothing from `specify_cli`/`charter`/`doctrine`):

```python
class MetaDecodeError(ValueError):
    """Raised when meta.json content is malformed. Subclasses ValueError so every
    existing `except ValueError` boundary (L2/L3/callers) keeps catching by inheritance."""

def decode_meta(raw: str | bytes, *, on_malformed: Literal["raise", "empty", "none"] = "raise") -> dict[str, Any] | None:
    ...
```

- Malformed set (define ONCE here): `json.JSONDecodeError`; `UnicodeDecodeError`; non-`dict` top level.
- **Explicit utf-8 decode is load-bearing**: do `text = raw.decode("utf-8") if isinstance(raw, bytes) else raw` BEFORE `json.loads`. `json.loads(b"\xff\xfe")` auto-detects and raises `JSONDecodeError` — only an explicit decode raises `UnicodeDecodeError`, which the malformed contract requires.
- `on_malformed`: `"raise"`→`MetaDecodeError`; `"empty"`→`{}`; `"none"`→`None`. **`None` means malformed only** — empty/whitespace is NOT L1's concern (C-010; a caller/L2 short-circuit).

### Subtask T002 [P] — kernel/vcs_lock.py: field-set + comparator (absent ≠ null)

Create `src/kernel/vcs_lock.py`:
```python
VCS_LOCK_META_FIELDS: frozenset[str] = frozenset({"vcs", "vcs_locked_at"})

def is_vcs_lock_only_change(before: Mapping[str, Any] | None, after: Mapping[str, Any]) -> bool:
    """True iff the only differing keys are VCS_LOCK_META_FIELDS. Distinguishes an ABSENT
    field from a present-but-None field (C-005) via a sentinel — NOT `.get()==.get()`."""
```
- Use a `_MISSING` sentinel so `absent != present-but-None`. This adopts the `implement_cores._is_vcs_lock_only_meta_diff` semantics as canonical; it deliberately changes `ref_advance`'s old `.get()` verdict on the present-but-null arm (US2 AC1 — that's WP02's concern, not a bug here).
- Accept `before=None` (the committed side may be absent).

### Subtask T003 — Re-express L2 + public `parse_meta_file`

In `src/specify_cli/mission_metadata.py`:
- `_parse_meta_text` reads the file, then delegates decode to `decode_meta`. **Keep the empty→benign short-circuit at L2** (C-010) and **preserve the legacy path-named messages** — on malformed, re-raise a `ValueError` with the exact existing text (`"Malformed JSON in {path}"`, `"Expected JSON object in {path}, got {type}"`) so `test_mission_metadata.py:95,101` and `test_feature_metadata.py:85,92` stay green. (L1 owns the malformed *definition*; L2 owns the path-named *message*.)
- Add a public `parse_meta_file(path: Path, *, on_malformed="raise", encoding="utf-8") -> dict | None` that path-holding callers (WP04's merge_driver) use instead of the private `_parse_meta_text`.

### Subtask T004 — Re-express L3 on kernel L1 (relieve the cycle)

In `src/specify_cli/core/paths.py`, re-express `load_meta_fail_closed` to decode via kernel L1 directly, **removing the `paths.py:670` `mission_metadata.load_meta` back-edge** (this relieves the `core.paths`↔`mission_metadata` cycle — verified). L3 already treats empty-as-corrupt (it calls `load_meta(on_malformed="raise")`), so it does NOT need L2's empty short-circuit. Preserve the `except ValueError`→`MissionMetaReadError` wrap — since `MetaDecodeError` IS a `ValueError`, the existing `except` still catches.

**Ledger row eviction (same commit — load-bearing):** removing the internal `load_meta` call at `paths.py:676` invalidates the frozen census row `_ACCOUNTED_SITES[("src/specify_cli/core/paths.py","load_meta_fail_closed")] = (1, "authority")` in `tests/specify_cli/test_meta_fail_closed_full_census_contract.py:228`, firing the `stale` arm of `test_no_unaccounted_load_meta_call_sites`. In the SAME commit, delete that ledger row (the test's own stale-arm message prescribes "if you just routed the site, delete its row"). This file is in WP01's ownership.

### Subtask T005 [P] — L1 unit tests

Create `tests/architectural/test_meta_decode_l1.py` (**declare `pytestmark`** — e.g. `[pytest.mark.unit]` — new file needs a marker). Cover, for `str` AND `bytes`:
- valid dict → mapping;
- `on_malformed="none"` → `None` for malformed JSON, `b"\xff\xfe\x00"` (assert it went through the `UnicodeDecodeError` path), and non-object (`"[1,2,3]"`);
- `on_malformed="empty"` → `{}` for the same three;
- `on_malformed="raise"` → `pytest.raises(MetaDecodeError)` for the same three, and assert `issubclass(MetaDecodeError, ValueError)`.

### Subtask T006 — Measure census + confirm gates green

- Measure the routed census before and after this WP. Re-expressing L3 (T004) drops L3's internal `load_meta` call, so the census may fall 134→133 — still in band `[130,134]`, gate stays green. **Record the before/after numbers in your WP notes.** Do NOT touch `ROUTED_LOAD_META_FLOOR` or `ROUTED_CALLEES`.
- **Publish the neutrality baseline for the parallel dependents (WP02/03/04):** record in your WP notes the per-site *counted* (`ROUTED_CALLEES`) contribution of all five bypass sites — expected **0 each** (they use raw `json.loads`/private parsers, not `load_meta`). This gives the three parallel routing WPs a pre-verified "routing onto `decode_meta`/`parse_meta_file` is census-neutral" baseline instead of discovering a drop at test time (the floor band has only a ~2-count cushion after WP01's drop to 133).
- Run: `PWHEADLESS=1 python -m pytest tests/architectural/test_inline_meta_read_gate.py tests/specify_cli/test_meta_fail_closed_full_census_contract.py tests/architectural/test_meta_decode_l1.py tests/specify_cli/test_mission_metadata.py tests/specify_cli/test_feature_metadata.py -q` → all green.

## Branch Strategy

Planning/base branch: `feat/meta-json-l1-seam-routing-3259`. Final merge target: `feat/meta-json-l1-seam-routing-3259`. Execution worktrees are allocated per computed lane from `lanes.json` (created by `finalize-tasks`); do not create branches manually — `spec-kitty implement WP01` prepares the workspace.

## Definition of Done

- `kernel/meta_decode.py` (`decode_meta` + `MetaDecodeError(ValueError)`, explicit utf-8 decode) and `kernel/vcs_lock.py` (field-set + absent≠null comparator) exist, kernel-pure (no `specify_cli` import).
- L2 re-expressed via L1 with the empty short-circuit + legacy messages intact; public `parse_meta_file` added.
- L3 re-expressed on L1; the `paths.py:670` back-edge removed; `MissionMetaReadError` wrap preserved.
- `test_meta_decode_l1.py` green; the two message-pinned suites green; the three named gates green; census recorded and in band.
- `ruff` + `mypy --strict` clean on all touched files. No `ROUTED_CALLEES`/floor change.

## Reviewer guidance

Verify: `MetaDecodeError` subclasses `ValueError`; the explicit utf-8 decode (feed `b"\xff\xfe"` mentally — must be `UnicodeDecodeError`, not `JSONDecodeError`); L2's legacy messages byte-identical; L3 no longer imports `mission_metadata.load_meta`; census in band with no `ROUTED_CALLEES`/floor edit; no private parser deleted yet.
