# Research — Mission Registry and API Boundary Doctrine

## R-1 — Cache key composition

**Decision**: Triple `(mtime_ns, file_size, sorted_dirent_names_hash)` per cache entry.

**Rationale**: mtime alone is insufficient on filesystems where the resolution truncates to seconds (some macOS / Windows configs) or where a process rewrites a file with identical mtime (the "atomic write via tempfile + rename" pattern preserves mtime if the rename happens within the same second). The `(file_size, sorted_dirent_names_hash)` triple gives us a content-aware-enough cache key without reading file contents. The `dirent_names_hash` covers the "file added or removed" case for directory-shaped cache entries (e.g. `tasks/` listing).

**Alternatives considered**:
- mtime-only: rejected — known false-negative on the daemon-driven `status.json` rewrites this mission's boyscout WP01 addresses.
- mtime + content hash: rejected — content hashing every file on every cache-stale check defeats the purpose of caching. The size+dirent triple gives equivalent invalidation at 3 stat-syscall cost.
- inotify watcher: rejected per ADR `2026-05-03-1-dashboard-mission-registry-and-cache.md` § Rejected Alternatives.

## R-2 — Cache invalidation strategy

**Decision**: Poll-on-read. Every public registry method begins with a stat-call against the cache key components, compares to the cached key, and re-scans only on mismatch.

**Rationale**: matches the ADR's process-level switch rationale; no new dependency; bounded 3-stat-call cost per request. The stat-call cost is overwhelmingly dwarfed by the file-walk cost we are avoiding. For a 144-mission project: 3 syscalls per stale-check vs ~720 file `open()` syscalls per uncached scan.

**Alternatives considered**:
- Periodic background re-scan (every N seconds): rejected — adds a thread that must be managed, and consumers polling at higher frequency than N would still see stale data.
- inotify / fsnotify watcher: rejected per ADR (operational cost; cross-platform support).
- TTL-based cache expiry (e.g., 5-second TTL): rejected — race condition where a mid-poll mutation arrives just after the cache fill but before the TTL expires; the user sees stale data for up to 5 seconds with no signal that a fresh mtime is available.

## R-3 — Cache scope

**Decision**: Two registries — `MissionRegistry` for collection-level reads, `WorkPackageRegistry` for per-mission tasks/. Each cache key is independent.

**Rationale**: a single WP status change should not invalidate the entire project's mission listing. Per-mission cache scoping means a `status.events.jsonl` write for one mission only invalidates that mission's WP cache, plus the lane-counts entry for that mission in the mission-list cache. The mission-list cache itself uses its own key derived from the directory listing of `kitty-specs/`.

**Alternatives considered**:
- Single global cache: rejected — invalidation domino effect.
- Per-file cache (one cache entry per `meta.json`, `status.events.jsonl`, etc.): rejected — too granular; cache-key bookkeeping cost exceeds the benefit at our scale.

## R-4 — Doctrine YAML schema

**Decision**: New artefacts go in `src/doctrine/directives/shipped/` and `src/doctrine/paradigms/shipped/` using the existing schema; if the schema rejects (no `referenced_tests:` field, etc.), escalate to a small schema extension PR that lands inside this mission.

**Rationale**: the existing shipped-doctrine repository is the canonical home; no reason to invent a new location. The schema evolution risk is a known unknown — Phase 0 research cannot resolve it without inspecting the schema validator (out-of-band for the planning gate). Defer to WP02 implementation; if schema extension is needed, it ships in WP02.

**Alternatives considered**:
- Custom artefact format: rejected — bypasses existing tooling; future readers cannot find the new artefacts via doctrine list/show commands.
- Skip the new directives entirely (just ship the architectural tests): rejected — directives without doctrine entries are tribal knowledge; the "passing test, no documented rule" anti-pattern.

## R-5 — Architectural test discovery

**Decision**: Mark every new test file with `pytestmark = pytest.mark.architectural`; CI's existing architectural job picks them up automatically (`pytest tests/architectural/ -m architectural`).

**Rationale**: matches the existing pattern (every test under `tests/architectural/` already uses this marker). No CI configuration change needed.

## R-6 — Test fixture mtime-bumping

**Decision**: Helper function `bump_mtime(path: Path, delta_seconds: float = 1.0) -> None` in a new test util module under `tests/test_dashboard/_helpers.py`. Implementation: `os.utime(path, (now, now + delta_seconds))`.

**Rationale**: `os.utime` is stdlib, cross-platform, and works on Python 3.11+. `delta_seconds=1.0` is large enough to cross any filesystem mtime resolution boundary. The helper is shared by the registry unit tests so each test asserting cache invalidation uses the same primitive.

**Alternatives considered**:
- Sleep + write a marker byte: rejected — slow; sleep adds ≥1 second per test; mtime-mocking via `unittest.mock` would defeat the purpose of the test.
- Manipulate the in-memory cache directly via a private attribute: rejected — couples tests to implementation; refactoring the cache shape would break every test.

## R-7 — Boyscout T02 scope

**Decision**: Defer the implementation choice to WP01's reviewer with a documented rationale. Two acceptable directions:
- **(a)** Trace the daemon mutation source and stop the auto-mutation if the rewrite is producing stale data (e.g., a stale `mission_number` backfill).
- **(b)** Gitignore `kitty-specs/*/status.json` (the materialised snapshot) while keeping `kitty-specs/*/status.events.jsonl` (the canonical event log) tracked. Add a `# documented in WP01 review` comment in `.gitignore`.

**Rationale**: both are reversible. (a) is more correct if the daemon is producing genuinely stale data (the rewrite is a bug to fix); (b) is more correct if the snapshot is meant to be a derived artifact (fast-cache for the dashboard) that does not belong in version control. The WP01 reviewer judges based on the daemon trace findings.

## R-8 — Doctrine cross-link mechanism

**Decision**: Use a `referenced_tests:` field in the directive YAML pointing at the test file path (relative to repo root). If the schema validator rejects this field, escalate to a small additive schema PR within the same WP02.

**Rationale**: the existing shipped doctrine has no formal cross-link to enforcement tests today (the FastAPI handler-purity test, for example, is referenced only in the test docstring). Adding `referenced_tests:` makes the rule → enforcement chain machine-discoverable for future doctrine browsers.

**Alternatives considered**:
- Free-form `metadata:` block: rejected — no schema validation means typos go undetected.
- Test docstring link only: rejected — unidirectional and not discoverable from the doctrine artefact.

## R-9 — `ResourceModel` marker placement

**Decision**: Add `ResourceModel` and the `Link` Pydantic model to `src/dashboard/api/models.py` (alongside the existing models).

**Rationale**: cohesion with the existing model file; the architectural test `test_resource_models_have_links.py` walks this single module to find subclasses. A separate `resource_model.py` would split the import surface for no benefit.

**Note**: per spec C-006, no resource response actually subclasses `ResourceModel` in this mission. The marker class lands here so mission B can subclass it; the test in FR-011 lights up empty until then.

## R-10 — Performance verification methodology

**Decision**: `scripts/bench_registry_syscalls.py` spawns the dashboard under both transports (registry vs scanner-only), runs `strace -c -e trace=openat,stat,statx -p <pid>` for 30 seconds while the dashboard is being polled, captures the syscall counts, and writes a JSON report with the comparison.

**Rationale**: NFR-001 (≤5 syscalls per warm-cache request) is a syscall-count claim; the only honest way to verify is to count syscalls. `strace -c` summarises by syscall name; the JSON report is an artefact the WP06 reviewer pastes into the release record.

**Alternatives considered**:
- Count `open()` calls in Python via `monkeypatch.setattr(builtins, 'open', counted_open)`: rejected — only catches Python-level opens, misses any file I/O happening through `os.read` / `pathlib.Path.read_text` (which both go through low-level syscalls).
- Use Linux `bpftrace`: rejected — requires kernel headers and root; `strace` is universally available.
- Run on macOS: deferred — `strace` is Linux-only; macOS uses `dtruss`. The bench script targets Linux first; macOS adaptation is a follow-up if needed.

---

## Open questions

None blocking Phase 1 design. All decisions resolved.

The boyscout T02 direction (R-7) is intentionally deferred to WP01's reviewer; that is the documented mechanism, not an open question.
