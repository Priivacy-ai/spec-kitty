**Issue 1: The required dossier sync grep gate still fails.**

The WP objective and T005 require:

```bash
grep -r "from specify_cli.sync" src/specify_cli/dossier/ --include="*.py"
```

to return empty output. It currently returns:

```text
src/specify_cli/dossier/emitter_adapter.py:``EventEmitter._emit`` from specify_cli.sync.events:
```

This is docstring text rather than an executable import, but it still fails the exact acceptance gate. Reword the docstring in `src/specify_cli/dossier/emitter_adapter.py` so the literal `from specify_cli.sync` text does not appear under `src/specify_cli/dossier/`, then rerun the T005 grep command.

**Issue 2: The dossier emitter adapter has no production registration in the reviewed change set.**

`src/specify_cli/dossier/events.py` now routes all dossier event emission through `fire_dossier_event(...)`, and `fire_dossier_event(...)` returns `None` when no emitter has been registered. In this WP diff, the only occurrences of `register_dossier_emitter` are its own definition and docstring in `src/specify_cli/dossier/emitter_adapter.py`; no runtime path registers the sync emitter.

That creates a behavioral gap relative to the WP objective's "No behavioral changes" requirement: the four dossier event helpers can silently drop events unless another later WP wires the registration. Either wire the production registration in this WP's owned surface or explicitly split/record that registration as a dependency before approval, with a test that exercises real registration rather than only patching `fire_dossier_event`.

**Verification Notes**

Passed locally:

- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check ...`
- `UV_CACHE_DIR=/tmp/uv-cache uv run mypy --strict src/specify_cli/identity/project.py src/specify_cli/identity/__init__.py`
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/dossier -q`
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/architectural/test_dossier_sync_boundary.py -v`
- identity import and shim smoke test
- node id compatibility spot check against `specify_cli.sync.clock.generate_node_id`

Failed locally:

- The T005 grep command above fails because of the docstring literal.
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/sync -q` failed in this sandbox with 9 failures involving writes under `/Users/robert/.spec-kitty` / readonly queue state and daemon startup. These appear environment-related, but the WP still needs a clean sync-suite run before approval.

**Downstream Note**

WP02 is already in progress and its task body references the WP01 dossier emitter adapter, even though its frontmatter does not declare `WP01` as a dependency. After WP01 is fixed and merged back into the mission branch, the WP02 lane should rebase:

```bash
git -C /Users/robert/spec-kitty-dev/spec-kitty-20260430-205349-CaQX7V/spec-kitty/.worktrees/p1-dependency-cycle-cleanup-01KQFXVC-lane-b rebase kitty/mission-p1-dependency-cycle-cleanup-01KQFXVC
```
