# Design Decisions

> Capture the rationale that would otherwise evaporate.

**Prompting questions**
- What decision was made?
- What alternatives were considered?
- What was the rationale — why this option over the others?

---

## Entries

<!-- YYYY-MM-DD — Decision: [what]. Alternatives: [what else]. Rationale: [why this one]. -->

## 2026-09-07 — planning
- Authentication state is the only hosted switch; no offline switch (plan DM 01M1XMCXWJNG6J8HF4YRQRSF6T).
- `[team_kitty] server_url` replaces `[sync].server_url` with no alias (plan DM 01M1XMHB8FWZJR23540JXM6817).
- Packaged default `https://team.spec-kitty.ai` reverses D-5; ADR is WP01 and lands before WP02.
- Owned checkouts publish moments like any checkout; `OWNED_SYNC_UNSUPPORTED` deleted (specify DM 01M1XKZMZH44PGGM0WWW6GRGVV).
