# Design Decision Trace

| Decision | Outcome | Mission record |
|---|---|---|
| Auth authority | Canonical local session authority is the sole auth truth; queue scope remains routing only. | `DM-01M0QF4S8QJH5407ERW4AMCSCM.md` |
| Broader separation | Always finish local verification; refuse only unsafe hosted side effects; report structural problems separately. | `DM-01M0QFGDHP92N1C9YCE2RF5A5F.md` |
| Unknown auth | Unknown is distinct from logged out and receives `SAAS_SYNC_AUTH_UNKNOWN`. | `DM-01M0QKMB5KMS0SJWBQ8H8MDK91.md` |
| Classification constraints | Local-only classification; refresh-capable sessions count as authenticated; no SaaS request. | `DM-01M0QNG6Y79TBRMVG6604HC0D1.md` |
| Engineering alignment | Existing Python stack, no dependency, local result authority, stable diagnostics, red-first matrix. | `DM-01M0QP53G8WMPN5AGR5Y3Q5NWZ.md` |

The earlier decision to preserve all non-auth setup-plan preflight severity was superseded by the broader-separation decision above. The structural detector remains authoritative and fail-closed for hosted delivery; only its effect on the local command result changes.
