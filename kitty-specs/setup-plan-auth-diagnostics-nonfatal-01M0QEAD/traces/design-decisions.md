# Design Decision Trace

| Decision | Outcome | Mission record |
|---|---|---|
| Auth authority | Canonical local session authority is the sole auth truth; queue scope remains routing only. | `DM-01M0QF4S8QJH5407ERW4AMCSCM.md` |
| Broader separation | Always finish local verification; refuse only unsafe hosted side effects; report structural problems separately. | `DM-01M0QFGDHP92N1C9YCE2RF5A5F.md` |
| Assessment failure | Failed session assessment is distinct from logged out and receives `SAAS_SYNC_AUTH_UNKNOWN`, but has no authentication verdict. This supersedes the earlier decision's tri-state state-model interpretation while preserving its diagnostic distinction. | Operator architecture correction, 2026-08-23; supersedes the state-model wording in `DM-01M0QKMB5KMS0SJWBQ8H8MDK91.md` and `DM-01M0QP53G8WMPN5AGR5Y3Q5NWZ.md` |
| Classification constraints | Local-only classification; refresh-capable sessions count as authenticated; no SaaS request. | `DM-01M0QNG6Y79TBRMVG6604HC0D1.md` |
| Engineering alignment | Existing Python stack, no dependency, local result authority, stable diagnostics, red-first matrix. | `DM-01M0QP53G8WMPN5AGR5Y3Q5NWZ.md` |

The earlier decision to preserve all non-auth setup-plan preflight severity was superseded by the broader-separation decision above. The structural detector remains authoritative and fail-closed for hosted delivery; only its effect on the local command result changes.

The historical Decision Moment files are append-only evidence of the interrogation path.
For implementation, the active model is `SessionAssessment(completed,
usable_session, reason)`: authenticated and logged out are conclusive outcomes only when
assessment completed; assessment failure is not a third authentication state.
