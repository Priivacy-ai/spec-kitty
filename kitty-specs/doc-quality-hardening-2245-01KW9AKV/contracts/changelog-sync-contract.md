# Contract: CHANGELOG canonical→root sync

**Surface**: `scripts/docs/sync_changelog.py` (NEW) + a blocking test.

## `generate_root(canonical_text: str) -> str`

- Input: full canonical `docs/changelog/CHANGELOG.md` text (YAML frontmatter + body).
- Output: root `CHANGELOG.md` text = canonical **body after the frontmatter block**, byte-stable.
- Must produce a valid Keep-a-Changelog document consumable by `scripts/release/extract_changelog.py` (reads root at repo cwd, `utf-8-sig`).

## CLI

- `python scripts/docs/sync_changelog.py --write` → regenerates root from canonical.
- `python scripts/docs/sync_changelog.py --check` → exit `1` if `read(root) != generate(read(canonical))`, naming the divergence.

## Invariant (FR-007 / INV-4)

`read(root) == generate(read(canonical))` at all times. Link fixes (FR-006) are applied to the canonical and flow to root via regeneration.

## Tests

- Red-first divergence test (SC-003): the *current* files diverge (frontmatter + the stale `architecture/2.x/05_ownership_map.md` line) → `--check` fails; after FR-006 fix + regenerate → passes.
- Editing one file without the other → `--check` fails.
