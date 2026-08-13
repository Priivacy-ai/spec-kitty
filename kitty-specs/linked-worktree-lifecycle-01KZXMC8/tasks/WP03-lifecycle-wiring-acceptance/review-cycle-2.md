---
affected_files: []
cycle_number: 2
mission_slug: linked-worktree-lifecycle-01KZXMC8
reproduction_command:
reviewed_at: '2026-08-13T18:41:13Z'
reviewer_agent: user
wp_id: WP03
---

**Blocker 1:** Добавить один сквозной production-CLI тест на реальном linked worktree: create -> status/context -> setup-plan/tasks -> implement/review -> next -> accept, со снимком branch/HEAD/tracked status primary до и после и доказанным RED до production-fix.

**Blocker 2:** Заменить локальный guard пяти функций на repo-wide census всех mission-scoped lifecycle consumers с фиксированным shrink-only allowlist только foundation-callers; доказать mutation sensitivity для повторного root/selector lookup после получения MissionOperationContext.
