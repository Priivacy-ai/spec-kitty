# Data Model — Canonical Path-Trust & Guard-Capability Seams

**No new persistent entities.** This is a behavior-preserving refactor + CI/test-harness change. The "model"
here is the set of code seams whose authority is being consolidated.

## Seam objects (not data records)

| Seam | Kind | Authority it owns | Consumers |
|------|------|-------------------|-----------|
| `core/paths.py` safe-segment validator | pure function `(str) -> str` raising `ValueError` | "is this a safe single path segment?" (rejects empty, `.`, `..`, `/`, `\`, non-segment) | `primary_feature_dir_for_mission`, `resolve_mission_read_path`, and (via delegation) `merge.py`/`transaction.py`/`aggregate.py` |
| `core/utils.py::ensure_within_any` | pure function `(Path, *, roots, files=()) -> Path` raising `ValueError` | "is this resolved path under a trusted root (or an allowed exact file)?" | the 2 collapsed merge helpers; the XOR helper as a conditional caller |
| `_read_path_resolver.py` primitives | path constructors | `KITTY_SPECS_DIR/<segment>` assembly (now validating) | ~75–143 call sites (inherit validation; NOT re-routed) |

## Invariants
- **INV-1 (no-bad-segment):** no path-assembly primitive composes a `mission_slug`/segment that fails the canonical
  validator. Proven at the primitive (NFR-002), not per-caller.
- **INV-2 (real-format admit):** every currently-valid real-format value (full 26-char ULID, `<slug>-<mid8>` dir
  name, numeric-prefix slug, bare mid8) still validates (NFR-006).
- **INV-3 (containment unchanged):** `ensure_within_any` over the existing root sets yields the same accept/reject
  as today's three helpers; the XOR helper's worktrees-vs-kitty-specs distinction is preserved (NFR-001).
- **INV-4 (gate-unmaskable):** an edit to any guarded write-side surface triggers the full `tests/architectural/**`
  shard; a meta-test pins this so a future filter edit can't re-open the mask (NFR-004).
- **INV-5 (drift-proof ratchet):** a +1 line drift / surrounding rename does not flip the re-keyed ratchets; only a
  genuine new offender does (NFR-004). `test_no_write_side_rederivation._ALLOW_LIST:295` is untouched (C-007).
