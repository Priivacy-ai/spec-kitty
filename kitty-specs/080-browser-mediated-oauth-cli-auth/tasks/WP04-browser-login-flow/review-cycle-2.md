---
affected_files: []
cycle_number: 2
mission_slug: 080-browser-mediated-oauth-cli-auth
reproduction_command:
reviewed_at: '2026-04-09T18:15:32Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP04
---

**Issue**: SaaS team has landed the refresh token lifetime amendment (previously proposed in `contracts/saas-amendment-refresh-ttl.md`). The WP04 prompt is stale.

**Landed SaaS contract changes** (as of 2026-04-09):
1. `POST /oauth/token` response now includes `refresh_token_expires_in` (integer seconds) for all grant types
2. `POST /oauth/token` response now includes `refresh_token_expires_at` (ISO 8601 timestamp)
3. `GET /api/v1/me` response now includes `refresh_token_expires_at`
4. `POST /api/v1/ws-token/` request is now `Authorization: Bearer <access_token>` header + body `{"team_id": "..."}` (NOT body `{"access_token": "..."}`)

**CLI mission impact**:
- C-012 is no longer "pending"; refresh expiry is REQUIRED in token responses
- `StoredSession.refresh_token_expires_at` is REQUIRED `datetime`, not `Optional[datetime]`
- `_build_session()` in WP04 MUST set `refresh_token_expires_at` from the SaaS response (no None branch)
- `saas-amendment-refresh-ttl.md` is now OBSOLETE — will be marked LANDED/SUPERSEDED

**Next step**: Orchestrator will update all stale artifacts (spec.md, contracts/, data-model.md, WP01/WP04/WP05/WP07 task files) to match landed SaaS contract, then redispatch fresh implementer. Do not attempt to implement WP04 against the stale prompt.
