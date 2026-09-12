# Data Model: Meta.json Fail-Closed Read Routing

No new persisted data. This mission reshapes the *decode seam* and the *comparator*; the "entities" are code contracts and the read-site taxonomy.

## Seam tiers (after the mission)

| Tier | Symbol (target home) | Signature | Owns | I/O |
|------|----------------------|-----------|------|-----|
| **L1** | `kernel.meta_decode.decode_meta` (NEW) | `(raw: str \| bytes, *, on_malformed="raise") -> dict \| None` | the single **malformed** definition + `kernel.meta_decode.MetaDecodeError` | none |
| **L2** | `specify_cli.mission_metadata._parse_meta_text` (re-expressed) + `parse_meta_file` (NEW public) | `(path: Path, *, on_malformed, encoding) -> dict \| None` | file open + **empty→benign** short-circuit | reads file |
| **L3** | `specify_cli.core.paths.load_meta_fail_closed` (re-expressed) | `(feature_dir: Path) -> dict` (raises on corrupt, `None`/`{}` on missing per contract) | dir-level fail-closed policy | reads `feature_dir/meta.json` |

**Malformed set (L1, defined once)**: `json.JSONDecodeError`; `UnicodeDecodeError` (explicit `raw.decode("utf-8")` of `bytes` *before* `json.loads`, because `json.loads(bytes)` auto-detects encoding and would raise `JSONDecodeError`, not `UnicodeDecodeError`); non-`dict` top level. `on_malformed`: `"raise"` → `MetaDecodeError`; `"empty"` → `{}`; `"none"` → `None`.

### Error-type & message translation per tier (load-bearing)

| Tier | Raises on malformed | Rationale |
|------|---------------------|-----------|
| **L1** `decode_meta` | `class MetaDecodeError(ValueError)` (kernel) | Extends `ValueError` so every existing `except ValueError` boundary keeps catching by inheritance (L3 `paths.py:677`, `decisions/service.py`, `upgrade/feature_meta.py`). NOT `KittyInternalConsistencyError` (which is not a `ValueError` → would leak). |
| **L2** `_parse_meta_text` / `parse_meta_file` | `ValueError` with **legacy path-named message** (`"Malformed JSON in {path}"`, `"Expected JSON object in {path}, got {type}"`) | Preserves the message-pinned regressions (`test_mission_metadata.py:95,101`, `test_feature_metadata.py:85,92`, `test_load_meta_fail_closed_authority.py`). L2 owns the path-named message; L1 owns the malformed definition. |
| **L3** `load_meta_fail_closed` | `MissionMetaReadError` (via its existing `except ValueError` wrap) | `MetaDecodeError`-is-`ValueError` means the current `except ValueError` at `paths.py:677` still catches. |
| **Site E** `merge_driver._load_json_object` | `EventLogMergeError(path)` (thin wrapper catches `MetaDecodeError`) | Preserves `test_merge_driver_wrappers_2709.py:112-116`. |

**Empty/whitespace-only (NOT L1's concern — C-010)**: a benign short-circuit at L2 or the caller (`→ {}` where currently contracted). L1 never sees empty as a special case beyond what `json.loads("")` would raise; callers that contract empty→benign must short-circuit before calling L1, or use L2's `on_malformed` mapping deliberately.

## VCS-lock comparator (after the mission)

| Symbol (target home) | Signature | Semantics |
|----------------------|-----------|-----------|
| `kernel.vcs_lock.VCS_LOCK_META_FIELDS` (NEW, single named declaration) | `frozenset[str] = {"vcs", "vcs_locked_at"}` | the only field-set; no inline-literal duplicates (NFR-002) |
| `kernel.vcs_lock.is_vcs_lock_only_change` (NEW) | `(before: Mapping \| None, after: Mapping) -> bool` | **absent ≠ present-but-null** (C-005): a field present-but-`null` is a real value distinct from absent, via a sentinel — not `.get()==.get()` |

**Retired**: `ref_advance._VCS_LOCK_META_FIELDS`, `ref_advance._is_vcs_lock_only_meta_change` (`.get()` semantics — absent==null), `implement_cores._VCS_LOCK_META_FIELDS`, `implement_cores._is_vcs_lock_only_meta_diff` (sentinel semantics). The kernel comparator adopts the sentinel (absent≠null) semantics as canonical; this changes `ref_advance`'s verdict on the present-but-null arm by design (US2 AC1).

## The five read sites (routing target + red-first injection seam)

| Site | Symbol | Input | Routes onto | Corrupt-arm outcome to preserve | Injection seam |
|------|--------|-------|-------------|-------------------------------|----------------|
| **A** | `ref_advance._meta_change_is_vcs_lock_only` | worktree file read + `git show HEAD:path` stdout `str` | kernel L1 | today: silent `None`→treats all changed; after: fail loud | `git_repo` fixture (real `git show`) |
| **B** | `ref_advance._committed_meta_object` | `git show HEAD:path` stdout `str` | kernel L1 | today: silent `None`; after: fail loud | `git_repo` fixture |
| **C** | `implement_cores._is_self_write_only_diff` (decode at `implement_cores.py:427`) | `source.read_bytes()` `bytes` | kernel L1 | today: `None`→`return False`; after: fail loud (the `:471` byte-compare is NOT a decode — untouched; keep the read **inline** for `test_trio_seam_only`) | on-disk file (**no** `git_repo` — unit-testable) |
| **D** | `implement_cores._committed_meta_mapping` | `GitPort.show_blob` `bytes` | kernel L1 | today: silent `None`; after: fail loud | injectable `GitPort` fake (**no** real git / `git_repo` marker) |
| **E** | `merge_driver._load_json_object:174` | on-disk temp blob `Path` | public L2 (`parse_meta_file`) via a wrapper | preserve empty→`{}`; **two error arms** — malformed→currently-unnamed `JSONDecodeError`, non-object→already-named `EventLogMergeError`; wrapper catches `MetaDecodeError`→`EventLogMergeError(path)` | on-disk file |

**Not a site**: `merge_driver._parse_json_document:337` decodes the issue/row-matrix document (raises `RowMatrixMergeError`), **not** `meta.json` — out of scope; the FR-010 gate must exclude it. Only sites **A/B** (ref_advance shells out to real `git show`) carry `[integration, git_repo]`; C/D/E are unit-testable without real git.

## Governance gates (invariants after the mission)

| Gate (test symbol) | Invariant |
|--------------------|-----------|
| `test_inline_meta_read_floor` | inline `json.loads` over meta paths ≤ floor 7 (unchanged; L1 in kernel is excluded) |
| `test_routed_load_meta_floor` | `live - MARGIN(4) <= ROUTED_LOAD_META_FLOOR < live`, anti-vacuity `live > floor`; `ROUTED_CALLEES` extended with `decode_meta` + `parse_meta_file` **once, in IC-05**; floor re-pinned to `fresh_live - 3`. Routing ICs (02/03/04) are census-neutral — they route onto these still-uncounted names, so the gate stays green at 130/134 until IC-05. |
| `test_no_unaccounted_load_meta_call_sites` | `load_meta` call-site ledger stays exact |
| FR-010 enumeration gate (NEW) | 0 `json.loads`/`json.load` over **meta content** outside kernel L1 — scoped by an argument/path allow-set that **excludes** `_parse_json_document:337` (row-matrix) and the kernel L1 itself |
| FR-010 completeness gate (NEW) | 0 un-routed `meta.json` bypass reads beyond the enumerated set |
| NFR-004 ratchet (`test_layer_rules`) | `git/ref_advance.py` imports 0 `specify_cli` modules |
| allow-list controls (existing) | `test_allowlist_matches_floor` (==) + `test_allowlist_shrink_only`; #3240 recorded as deviation |

## State: corrupt-vs-benign decision (per read)

```
read bytes/text/path
  ├─ missing file ........→ caller benign contract (e.g. {} or None)   [preserved]
  ├─ empty/whitespace ....→ caller/L2 benign short-circuit (→ {})      [preserved, C-010]
  ├─ valid dict ..........→ dict                                        [behavior-preserving]
  └─ malformed ...........→ MetaDecodeError (fail loud, names meta.json + source id)  [NEW behavior — was silent]
```
