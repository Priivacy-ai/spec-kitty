# Tracer: claim liveness (IC-LIVENESS / WP05)

> Post-tasks update: FR-008 (an allocator-side liveness consumer) was **withdrawn** — the lane
> allocator has no stale-claim decision. Liveness has one new consumer: the stale indicator
> (`core/stale_detection.py`, FR-007). The daemon keeps consuming via a re-export alias.

**Concern**: one `sync/daemon._is_process_alive` helper feeds both the stale-WP indicator and the
allocator stale-claim decision; no parallel `os.kill`.

## Planning intent
- Reuse existing psutil `sync/daemon._is_process_alive` (handles NoSuchProcess/AccessDenied) — do
  NOT add a second PID parse (C-002). Read shell_pid via `task_utils` frontmatter readers.
- Indicator `core/stale_detection.py` (today git-commit-timestamp idle) suppresses "stale" when the
  claiming process is live. Allocator consumer (FR-008) lives in `worktree_allocator.py` (IC-LANE).
- NFR-004: never raise on absent/unparseable/dead/recycled PID → conservative not-provably-alive.

## Implementation log
_(append: where the shared liveness call was centralized, both consumers wired to it, cross-platform
guard added, whether a second parse was avoided)_

## Close-out assessment
_(at close: exactly one liveness helper? indicator + allocator both consult it? no os.kill fork?)_
