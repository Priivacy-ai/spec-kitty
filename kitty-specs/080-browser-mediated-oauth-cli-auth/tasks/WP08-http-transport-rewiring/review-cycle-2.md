---
affected_files: []
cycle_number: 2
mission_slug: 080-browser-mediated-oauth-cli-auth
reproduction_command:
reviewed_at: '2026-04-09T18:15:59Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP08
---

**Issue**: SaaS team has landed the refresh token lifetime amendment AND corrected the `/api/v1/ws-token/` request schema. The WP08 prompt is stale relative to the landed contract.

**Landed SaaS contract changes** (as of 2026-04-09):
1. `POST /oauth/token` response now includes `refresh_token_expires_in` (integer seconds) and `refresh_token_expires_at` (ISO 8601 timestamp) for all grant types
2. `GET /api/v1/me` response now includes `refresh_token_expires_at`
3. `POST /api/v1/ws-token/` request is now `Authorization: Bearer <access_token>` header + body `{"team_id": "..."}` (NOT body `{"access_token": "..."}`)

**Partial work present in workspace** (uncommitted, from prior rate-limited attempt):
- `src/specify_cli/auth/http/__init__.py` — created (~900 bytes)
- `src/specify_cli/auth/http/transport.py` — created (~7KB, likely OAuthHttpClient)
- `src/specify_cli/sync/client.py` — modified (~121 lines changed)
- `src/specify_cli/tracker/saas_client.py` — modified (~109 lines changed)

**Fresh implementer must**:
1. Discard any stale partial work that assumed optional refresh_token_expires_at
2. Read the UPDATED WP08 prompt (will be regenerated after task file updates)
3. Complete remaining sync/*.py rewires (background.py, batch.py, body_transport.py, runtime.py, emitter.py, events.py)
4. Run the two hard grep audits (T045: zero CredentialStore/AuthClient hits; T046: ≥5 get_token_manager hits)

**Next step**: Orchestrator will update stale artifacts and redispatch. Do not attempt to implement WP08 against the stale prompt.
