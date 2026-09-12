---
title: "The asset doctrine kind — what exists, what is missing, and why it lands independently"
description: "Surface-by-surface inventory of the asset kind, proof that the payload already ships while addressing does not, and the dependency verdict against the open #3023 adjudication."
doc_status: active
updated: '2026-07-28'
related:
- kitty-specs/doctrine-delivery-reachability-01KYMXD6/spec.md
- docs/adr/3.x/2026-07-26-2-doctrine-artefact-pack-layout-convention.md
---
# Asset Kind Wiring — Findings

**Origin.** Pre-spec discovery for this mission, 2026-07-28, scoping
[#3037](https://github.com/Priivacy-ai/spec-kitty/issues/3037) (*"The asset doctrine kind has no
resolution or install path for consumers"*).

Measured on `upstream/main` @ `ed470756e`.

---

## 1. Inventory — what exists today

The kind exists (delivered by `doctrine-template-asset-kinds-01KX2YQ7`). What is missing is
**addressing**, not packaging.

| Surface | Location | State |
|---|---|---|
| Enum + plural + glob | `src/doctrine/artifact_kinds.py:60,75,108` | present — `ASSET = "asset"`, plural `assets`, glob `*.asset.yaml` |
| Excluded from charter activation | `src/doctrine/artifact_kinds.py:201-203` | `_NON_AUGMENTATION_ELIGIBLE_KINDS = {TEMPLATE, ASSET, ANTI_PATTERN}` |
| Model | `src/doctrine/assets/models.py:27-53` | `AssetManifest(id, mime, path, title)`, frozen, `extra="forbid"` |
| Package exports | `src/doctrine/assets/__init__.py:5-8` | **model only — no repository, no resolver** |
| Pack validation | `src/specify_cli/doctrine/pack_validator.py:187, 598-700` | `_validate_asset_manifests` -> path containment + mime check |
| DRG node kind | `src/doctrine/drg/models.py:42` | `NodeKind.ASSET` |
| DRG extraction | `src/doctrine/drg/migration/extractor.py:757` | nodes are minted |
| DRG uniqueness | `src/doctrine/drg/merge.py:205-220` | `duplicate_asset_id` hard-fail |
| Org-pack tier | `src/doctrine/drg/org_pack_loader.py:110` | org packs may declare assets |
| Transitive refs | `src/doctrine/drg/query.py:154, 240` | `assets: list[str]` of **bare ids** |
| Step-contract executor | `src/specify_cli/mission_step_contracts/executor.py:41` | `ArtifactKind.ASSET -> NodeKind.ASSET` |
| CLI `doctrine validate` | `src/specify_cli/cli/commands/doctrine.py:682` | `.asset.yaml` in `_SUFFIX_TO_KIND` — present |
| CLI `doctrine new` | `src/specify_cli/cli/commands/doctrine.py` | `_CANONICAL_KIND_SINGULAR_TO_PLURAL` has 8 kinds, **no asset** |
| `DoctrineService` | `src/doctrine/service.py:65-158` | 9 repository properties; **`assets` absent** |
| `_PROJECT_KIND_DIRS` | `src/doctrine/service.py:19-24` | 4 kinds; **no `assets`** |
| `charter/context.py` | — | **zero `asset` mentions** — assets never reach an agent-facing context |

## 2. The three claims in #3037, tested

**"No `AssetRepository`" — CONFIRMED.** `src/doctrine/assets/__init__.py` exports the model only.

**"Resolution returns ids, never paths" — CONFIRMED, and worse.**
`ResolveTransitiveRefsResult.assets` holds bare ids. Grepping `\.assets\b` across `src/` yields
only `doctrine/assets/__init__.py`, the `pack_validator` import, and an unrelated
`skills/registry.py`. **No production code reads the assets bucket at all.** The four hand-authored
`requires` edges (`src/doctrine/drg/migration/hand_authored_overlay.py:244-300`) carry a comment
conceding they exist for *"deployment-manifest completeness rather than an activation trigger"* —
i.e. the absence of a consumer is already known and recorded.

**"The one shipped asset is reached by a hard-coded repo path" — CONFIRMED.**
The asset is `src/doctrine/assets/built-in/docs_structural_lint.py` (686 lines) with sidecar
`docs_structural_lint.py.asset.yaml` (`id: common-docs-structural-lint`). It is genuinely
self-contained (stdlib + `ruamel.yaml`; styleguide supplied via `--styleguide` /
`SPEC_KITTY_STYLEGUIDE`). It is reached by `tests/docs/test_docs_structural_lint.py:50-53`:

```python
_LINT_ASSET_PATH = (_REPO_ROOT / "src/doctrine/assets/built-in/docs_structural_lint.py")
```

followed by `importlib.util.spec_from_file_location` at lines 64-77.

## 3. The payload already ships — this is an addressing problem

Verified by building the wheel (`uv build --wheel` -> `spec_kitty_cli-3.2.6-py3-none-any.whl`) and
listing it: `doctrine/assets/built-in/docs_structural_lint.py`, `...py.asset.yaml` and the
accompanying `README.md` are all **present in the distribution**.

This materially shrinks the slice. Consumers already have the bytes; they cannot name them.

## 4. Parity surfaces — what "wired correctly" requires

Compared against `glossary_pack` (most recently wired) and `agent_profile` (the only repository
that already tracks source paths):

| Surface | Reference implementation | Asset needs |
|---|---|---|
| Repository | `BaseDoctrineRepository[T]` (`src/doctrine/base.py:82`) | new `AssetRepository`; `_schema = AssetManifest`, `_glob = "*.asset.yaml"` |
| Recursive overlay scan | `StyleguideRepository._project_scan` -> rglob (`base.py:140-146` default is **non-recursive**) | **required** — see trap 1 |
| Source-path tracking | `AgentProfileRepository._source_paths` (`agent_profiles/repository.py:248, 488, 568`) | **required** — the base class records only a layer *label* in `_provenance: dict[str,str]`, never the file |
| Service property | `service.py:140-147` (`glossary_packs`) | `assets` property |
| Activation wrapper | `charter/resolver.py:136-140` `__getattr__` delegation | **free** — no change needed |
| Path resolution | *nothing exists for any kind* | new `resolve_path(id) -> Path` reusing `org_pack_config.resolve_relative_path_within_root` |
| Operator CLI | `spec-kitty doctrine validate/new/pack` | `doctrine asset list` / `path <id>` (+ optional explicit `install`) |
| DRG node projection | works at built-in + org tier | project tier is #3038 |
| Docs | `doctrine-kinds.md`, `create-a-doctrine-artifact.md`, `docs/api/cli-commands.md` | required (freshness gate) |

## 5. Dependency verdict — lands independently

**#3023 (repo-local pack destination) does NOT block it.** The resolution mechanism is
tier-generic by construction: `BaseDoctrineRepository` already takes `built_in_dir` / `org_dirs` /
`project_dir` and merges them; the built-in tier already hosts a real asset; the org tier already
admits assets (`org_pack_loader.py:110` plus the validator's `assets/` pass). ADR
`2026-07-26-2` pins `<type>/<pack>/[<category>/]<name>` and the post-extraction rotation — so
whichever way #3023 goes, an asset is found by *"glob `*.asset.yaml` under the `assets/` type dir;
anchor blob paths at that type dir."* **The adjudication changes the pack segment name, not the
algorithm.**

**#3038 is entangled in exactly one line, separably.** `DoctrineService._project_dir`
(`service.py:48-53`) does `_PROJECT_KIND_DIRS.get(artifact, artifact)`; with no `assets` key the
project tier silently becomes `.kittify/doctrine/assets/` (plural), diverging from the singular
convention of the four mapped kinds. Adding `"assets": "asset"` is *literally half* of #3038's
proposed fix. **#3038's second half is orthogonal**: `_KIND_TO_NODE_KIND`
(`src/charter/synthesizer/project_drg.py:44-62`) governs charter-synthesis targets, not general
project-tier discovery. Nothing in asset resolution touches it.

**#3036 is orthogonal.** Verified by inspection (no mutation):
`tests/architectural/test_no_dead_doctrine_paths.py` asserts exact equality on a one-element list
containing `src/doctrine/graph.yaml` inside `doctrine-daphne.agent.yaml`. Strip that repo-local
reference and `[] == [(...)]` is False -> RED. The gate does not tolerate the coupling, it
**requires** it. Corroborating: `src/doctrine/graph.yaml` **does not exist** — the graph is sharded
into per-kind `src/doctrine/<kind>.graph.yaml` — so the pinned text is a mention of a deleted file.
No asset code path is involved; the two proceed in parallel.

## 6. Blast radius — zero, if scoped to resolve-not-auto-install

Built-in doctrine is **package data, not project-installed**. A `path` / `list` command resolves
inside site-packages via `resolve_doctrine_root()` (`src/charter/catalog.py:153-179`,
`importlib.resources` first, dev-layout fallback). **No upgrade migration is required and nothing
new lands in any consumer project on upgrade.**

An explicit operator-invoked `doctrine asset install <id> --to <dir>` also needs no migration.
Only *automatic* install-on-upgrade would, and there is a direct model
(`m_2_0_11_install_skills.py`). **Auto-install is deliberately excluded from this mission** — it
converts a zero-blast-radius change into one that mutates every consumer repo.

## 7. Sizing

PR #3007 for comparison: **180 files, +17,679 / -900**.

- **New source (2):** `src/doctrine/assets/repository.py` (~150 lines incl. source-anchor tracking
  and `resolve_path`); optionally a `_doctrine_asset.py` CLI split.
- **Edited source (4-6):** `assets/__init__.py`, `service.py` (property + one `_PROJECT_KIND_DIRS`
  line), `cli/commands/doctrine.py` (subapp + scaffold kind map), optionally `_doctrine_collect.py`
  and `_doctrine_health.py`.
- **Tests (3 new + 1 repointed):** repository three-tier resolution / rglob discovery / containment
  negatives; a CLI test; an org-tier fixture test; and `tests/docs/test_docs_structural_lint.py:50-77`
  **repointed off `_REPO_ROOT`** — that repoint is #3037's own acceptance proof.
- **Docs (3 + changelog):** the two doc defects below, plus `docs/api/cli-commands.md`.

**~13-18 files, ~900-1,300 lines.** One reviewable PR. `src/specify_cli/__init__.py` is untouched,
so no version bump is forced; a CHANGELOG entry is still warranted.

Baseline confirmed green: `tests/doctrine/test_template_asset_e2e.py`,
`tests/doctrine/drg/test_extractor_asset.py`, `tests/doctrine/test_artifact_kinds.py` — **50
passed**; `tests/docs/test_docs_structural_lint.py` — **29 passed**.

## 8. Two documentation defects found in passing

- `docs/doctrine/doctrine-kinds.md:50-52` states asset is *"a newer, loose-contract kind ... with
  no built-in artifacts yet"* — **false**, there is one and it ships.
- `docs/development/review-gates.md:~226` cites `docs/doctrine/create-a-doctrine-artifact.md` as
  the how-to for shipping an asset. That file is 193 lines containing the word "asset" **zero**
  times.

This matters beyond tidiness: #3037's actual complaint is that *"ship executable logic as an
asset"* — the documented remedy for repo-coupled doctrine — is not followable. Landing the
mechanism without the docs leaves the complaint standing.

## 9. Top three traps

1. **Anchor asymmetry plus the non-recursive overlay glob.** `_built_in_dir("assets")` returns
   `<root>/assets/built-in` and blob paths anchor at its **parent** (`path:
   built-in/docs_structural_lint.py` proves it), while `_org_dirs` / `_project_dir` return
   `<root>/assets` where the anchor **is** the dir. Get it wrong and built-in resolution silently
   produces `.../assets/built-in/built-in/...`. Compounding: `BaseDoctrineRepository._project_scan`
   (`base.py:140-146`) is a **non-recursive** `glob`, so an org-pack manifest at the ADR-mandated
   `assets/<pack>/x.asset.yaml` is never discovered — override to `rglob` (styleguide precedent).
2. **A second path-escape surface.** Containment lives only in
   `specify_cli.doctrine.pack_validator`. The resolver lives in `doctrine`, which **may not import
   `specify_cli`** (dependency direction `kernel <- doctrine <- charter <- specify_cli`), so
   `_check_asset_path_containment` cannot be reused — call
   `doctrine.drg.org_pack_config.resolve_relative_path_within_root` directly. Anyone who "just
   joins the paths" ships a symlink/`..` escape the validator would have caught.
3. **The CLI-reference freshness gate.** A new visible Typer path trips `REF-MISSING` in
   `scripts/docs/check_cli_reference_freshness.py` against the 4,950-line
   `docs/api/cli-commands.md` (`tests/docs/test_check_cli_reference_freshness.py`).
