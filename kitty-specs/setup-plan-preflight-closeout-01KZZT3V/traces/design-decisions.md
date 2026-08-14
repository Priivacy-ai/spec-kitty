# Tracer: design-decisions

One entry per finding: `YYYY-MM-DD · actor · <text>`.

---

2026-08-14 · codex · Git policy использует verified caller-owned linked checkout, но Mission identity и mission_anchor_root остаются только за MissionOperationContext; auth и SaaS gates сохраняют прежний приоритет.

2026-08-14 · codex · WP01: active Git checkout выбирает filesystem-only resolve_same_repository_worktree_root по linked-worktree marker и normalized common-dir identity; helper не читает Mission metadata, а MissionOperationContext остаётся единственной authority identity/anchor.
