# Quickstart — verifying Primary & Merge Vocabulary Disambiguation (Track 1)

How to confirm each Success Criterion after implementation. Run from the mission branch
`feat/terminology-primary-merge-disambiguation`.

## SC-001 — one canonical term per sense; no ambiguous touched passages
- Read `docs/context/orchestration.md` + `execution.md`: confirm distinct entries for the 4 primary senses
  (PRIMARY partition / Primary Branch / repository root checkout / target ref) and 3 merge operations
  (lane consolidation / branch integration / publish to origin), each with `Do NOT use when`.
- Proxy check: `git diff --name-only` the touched files; grep them for retired-alias phrases and confirm the
  residual set equals the classified-as-intentional set in `occurrence_map.yaml`:
  `git grep -nE "primary (surface|checkout|target|ref)" -- <touched files>` (Sense-C aliases legitimately
  persist until Track 2 — they must NOT appear in *this mission's* edited prose).

## SC-002 — 0 exempt/serialized identifiers changed
```
git diff | grep -E '^\-' | grep -E 'merge_target_branch|is_primary_artifact_kind|Surface\.PRIMARY|primary_branch|current_is_primary|MergeState|"(merge|squash|rebase)"|resolve_merge_target_branch|primary_repo_root|primary_candidate|WorktreeTopology\.PRIMARY|PRIMARY_CHECKOUT'
```
Expect **no output** (no exempt token removed/renamed). Cross-check the `occurrence_map.yaml` exceptions.

## SC-003 — single canonical resolver behavior
- `git grep -n "def resolve_primary_branch" src/` → one real definition (`core/git_ops.py`); `tasks_shared`
  is either removed or an explicit compat shim reflected in `tasks.py.__all__`.
- `grep -n "_resolve_primary_branch_for_recommendation" src/` → folded (delegates to canonical w/ `bias`)
  or explicitly scoped-out with a rationale comment.
- `uv run pytest tests/... -k "git_ops or tasks_compat_surface or mission_branch_context"` → green.

## SC-004 — one prose-glossary home
- `git grep -n "glossary/contexts" glossary/README.md` → **no** dead links (repointed to `docs/context/`).
- `ls glossary/` → legacy prose files relocated under `docs/context/`.
- `uv run python -m scripts.docs.relative_link_fixer --check` → clean.

## SC-005 — gates green, zero new suppressions
```
uv run pytest tests/docs/ tests/architectural/test_no_legacy_terminology.py -q
uv run python scripts/docs/anti_sprawl_ratchet.py --strict
uv run ruff check .
uv run mypy --strict <touched modules>
```
Confirm `test_mission_runtime_surface`, `test_shared_package_boundary`, `test_tasks_compat_surface` stay green
(exempt-surface pins). Prove the terminology guard actually executed over the new entries (guard-skip #2701).

## SC-006 — boundary recorded
- `spec.md` C-002/C-003 + this mission's issue matrix state Sense-C rename → Track 2 (#2730) and
  `src/glossary/` removal → #2727 in one place.

## Bulk-edit gate
- `occurrence_map.yaml` present, all 8 categories actioned, `change_mode: bulk_edit` — `implement` refuses
  the first WP without it (DIRECTIVE_035). The implement diff must comply with the per-category actions.
