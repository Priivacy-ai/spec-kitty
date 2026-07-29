# Contract — Asset Resolution and Operator Surface

**Requirements**: FR-003, FR-004, FR-005, FR-006, FR-007, FR-008 · **Criteria**: SC-003, SC-008
**Constraints**: C-001, C-002

## Library contract

```python
# src/doctrine/assets/repository.py
class AssetRepository(BaseDoctrineRepository[AssetManifest]):
    _schema = AssetManifest
    _glob = "*.asset.yaml"

    def _project_scan(self, root: Path) -> Iterable[Path]: ...   # rglob — base is non-recursive
    def resolve_path(self, asset_id: str) -> Path: ...           # typed error on miss or escape
    def source_path(self, asset_id: str) -> Path: ...            # which manifest declared it

# src/doctrine/service.py
class DoctrineService:
    @property
    def assets(self) -> AssetRepository: ...
```

### Obligations

| # | Obligation |
|---|---|
| A-1 | Resolution merges built-in, organisation and project tiers; the more specific tier wins and the shadowed tier is **reported**. |
| A-2 | Built-in blob paths anchor at the **parent** of `<root>/assets/built-in`; org and project paths anchor at the directory itself. |
| A-3 | Overlay discovery **recurses** — an org-pack manifest at `assets/<pack>/x.asset.yaml` is found. |
| A-4 | Containment is enforced by `doctrine.drg.org_pack_config.resolve_relative_path_within_root`. Traversal and symlink escapes raise a typed error (NFR-006). The `specify_cli` validator helper must **not** be imported (C-001). |
| A-5 | The project-tier asset directory comes from the single hoisted kind mapping (IC-02), so scaffold and resolver cannot disagree. |
| A-6 | Resolution never returns a bare identifier where a caller expects a path, and never returns an empty result where a caller reads it as success. |

## Operator contract

```
spec-kitty doctrine asset list [--json]
spec-kitty doctrine asset path <asset-id> [--json]
spec-kitty doctrine new --kind asset <name>          # scaffold parity with `validate`
```

| # | Obligation |
|---|---|
| A-7 | `path` prints a resolvable filesystem path and exits 0; an unknown id exits non-zero with the id named. |
| A-8 | Both visible paths appear in `docs/api/cli-commands.md` — a new Typer path trips `REF-MISSING` otherwise. |
| A-9 | **No automatic install.** Assets are resolved from package data; nothing is written into a consumer repository (C-002). |

## Acceptance shape

**SC-003 runs against a built wheel in a clean environment**, with the repository root absent from
resolution inputs. In-repo the dev-layout fallback in `resolve_doctrine_root()` means the criterion
cannot fail, so an in-repo test proves nothing.

**FR-008 is the proof by first user**: `tests/docs/test_docs_structural_lint.py:50-53` stops reaching
through `_REPO_ROOT` and goes through the resolution surface.

**SC-008 is doc-as-test**: the published how-to's commands execute against a fresh project. Today
`docs/doctrine/create-a-doctrine-artifact.md` contains "asset" zero times while `review-gates.md`
cites it as the asset how-to, and `doctrine-kinds.md` claims no built-in assets exist.

## Interaction with delivery

Per D4 assets are **also** delivered in the action bundle — see
[`activation-delivery.md`](activation-delivery.md). Resolution alone would leave assets reachable only
by someone who already knows the identifier, which is the dead end this mission exists to close.
