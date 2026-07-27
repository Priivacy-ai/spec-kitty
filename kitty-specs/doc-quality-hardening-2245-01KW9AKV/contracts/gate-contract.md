# Contract: the body-link gate

**Surface**: `scripts/docs/relative_link_fixer.py::check_dead_body_links` + `--check` CLI + `tests/docs/test_relative_link_fixer.py::TestLiveTreeGate`.

## `check_dead_body_links(repo_root: Path) -> list[Unresolvable]`

- Scans every Markdown file under `docs/` **not** matched by `EXCLUDE_PREFIXES`.
- For each inline body link that `is_bare_relative` (skips `http(s)`, `mailto:`, `#anchor`, absolute `/…`, reference-style, raw HTML), resolves `repo_root / normpath(file_dir / target)` and records an `Unresolvable(file, link, line)` if absent.
- **Post-mission**: `EXCLUDE_PREFIXES == ()` → covers all of `docs/` incl. `docs/adr/`, `docs/changelog/`, `docs/architecture/`, `docs/archive/`, `docs/plans/user_journey/`.
- **Determinism (NFR-002)**: returns findings sorted by `(file, line, link)`.
- **Non-vacuity (FR-004/INV-2)**: raises/fails if zero files or zero links were examined.

## `--check` CLI

- `python scripts/docs/relative_link_fixer.py --check --repo-root .` → exit `0` iff no dead links; exit `1` otherwise.
- **Failure output (NFR-003)**: one line per offender as `file:line -> target`, enumerating **all** offenders (not a summary count).

## Gate-unmask dry-run (C-007 / INV-5)

- A mode/flag (or test) runs `check_dead_body_links` with `EXCLUDE_PREFIXES=()` over the integrated branch and requires zero dead links **before merge** — the gate cannot validate its own unmask within its PR.

## Tests

- `TestLiveTreeGate` (`@pytest.mark.fast`, blocking): zero dead links on the live tree (full scope post-flip); `_KNOWN_GAPS` re-pinned to `frozenset()`.
- `test_gate_excludes_immutable_subtrees` (`:264`): **inverted** — post-mission the gate must NOT exclude `docs/adr/`.
- Deliberate-breakage test (SC-002): ≥2 planted bad links → all reported with correct `(file, line, target)`.
