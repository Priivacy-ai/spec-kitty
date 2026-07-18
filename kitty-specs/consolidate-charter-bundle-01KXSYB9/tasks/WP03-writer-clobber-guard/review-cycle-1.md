# WP03 review-cycle-1 — incomplete slice (code sound, complete it)

**The code is sound** (partial-merge write via WP01 helper, clobber removed, `_write_references_yaml` retired, bootstrap, #2758 preflight re-messaged, spec-kitty's own charter.yaml regenerated). Two completions are required before this slice is a green, self-contained whole (NFR-005 aggregate-green + the WP02-review init-pointer finding):

## 1. Own + fix the retired-contract tests (now in your owned_files)
Your write-contract change (no `charter.md` write, no `references.yaml`, `force` a no-op) breaks tests asserting the OLD contract. They are now yours — update them to the new charter.yaml partial-write world:
- `tests/charter/test_compiler.py` (5 failing) — assert the new `write_compiled_charter` behavior (partial-merge; no charter.md/references write; bootstrap on absent charter.yaml).
- `tests/charter/test_generator.py::test_write_compiled_charter_rejects_symlink_even_with_force` — the old force-clobber-rejects-symlink contract is retired; update or remove per the new no-op-force semantics.
(The cross-cutting `tests/merge/test_profile_charter_e2e.py` 3 reds are assigned to WP07's final sweep — NOT yours.)

## 2. Mint the `charter:` pointer when bootstrapping charter.yaml (close the init-pointer gap)
The WP02 review confirmed `spec-kitty init` never mints the `charter:` pointer, so a project that hasn't run the WP07 migration (esp. a NEW project) falls to the config-activation branch **permanently** — turning WP02's transitional dual-branch into a permanent split-brain.
- In `_bootstrap_charter_yaml` (or the generate path), when you create `charter.yaml`, also **write `charter: .kittify/charter/charter.yaml` into `config.yaml`** (comment-preserving; do not clobber other keys).
- Do NOT touch `init.py` (fenced #2519 surface) — minting at first-generate covers new projects; WP07's migration covers direct-upgrade.
- Commit this repo's own `config.yaml` pointer as part of the change; add a test that a bootstrap mints the pointer.

Re-run gates (`uv run` in the lane), then move back to `for_review`.
