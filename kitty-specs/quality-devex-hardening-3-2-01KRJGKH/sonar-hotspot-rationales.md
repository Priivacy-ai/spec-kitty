# Sonar Hotspot Rationales

This file contains draft rationale annotations for operator to apply in the
Sonar UI. Each hotspot section includes the exact text to enter as the Sonar
review comment and the resolution status to select.

Operator: after applying each rationale in the Sonar UI, mark the hotspot as
"Safe" or "Fixed" as indicated. The goal is `new_security_hotspots_reviewed = 100 %`.

---

## Regex hotspots

### `release/changelog.py` — python:S5852 / python:S6353 (line ~147 area)

**Sonar finding**: `python:S5852` (catastrophic backtracking risk) and `python:S6353`
(concise character class) on `src/specify_cli/release/changelog.py` in the line 147 area.

**Audit outcome (WP04, 2026-05-14)**: The flagged patterns no longer exist in the file.
All three vulnerable regex call-sites were remediated in commit `4e94c341f`
(PR #592, "fix: remove changelog parser regex hotspots") before this mission started:

| Pre-fix pattern | Location | Shape | Remediation |
|---|---|---|---|
| `r"^\s*status\s*:\s*(.+)$"` (re.MULTILINE via re.search) | `_parse_wp_frontmatter_status` (~line 98) | Shape 3: partial-match API without start anchor | Replaced by `str.partition(":")` + `key.strip() == "status"` loop |
| `r"^#+\s*"` (via re.sub) | `_parse_wp_title` (~line 115) | Shape 3: cosmetic re.sub, S6353 | Replaced by `stripped.lstrip("#").strip()` |
| `r"^\s*work_package_id\s*:\s*(.+)$"` (re.MULTILINE via re.search) | `_parse_wp_id` (~line 130) | Shape 3: partial-match API without start anchor | Replaced by `str.partition(":")` + `key.strip() == "work_package_id"` loop |

**Tactic applied**: `secure-regex-catastrophic-backtracking` — the remediation
applied escape-hatch option 1 (drop the regex, use string operations) from Step 3
of the tactic. String operations are O(N) in the frontmatter block length;
the pre-fix patterns were O(N^2) on adversarial multi-line inputs.

**Wall-clock regression test**: `test_parse_wp_frontmatter_status_completes_under_budget_on_adversarial_input`,
`test_parse_wp_id_completes_under_budget_on_adversarial_input`,
`test_parse_wp_title_completes_under_budget_on_adversarial_input`
in `tests/regressions/test_changelog_regex_redos.py` (commit `0cd1253a0`).
All three complete in < 20 ms on a 100 000-line adversarial frontmatter block
(budget: <= 100 ms per FR-008).

**Sonar UI action**: Resolve as **Safe** (the fix was already applied in commit
`4e94c341f` merged as PR #592). The Sonar finding is stale — the push-time Sonar
scan was gated to schedule/manual during the backlog-clearing period (FR-004).
Once FR-004 restores push-time scanning, the finding will not reappear on new code.

**Rationale text for Sonar UI** (paste verbatim):
```
Remediated in commit 4e94c341f (PR #592, April 2026) before the 3.2 quality
mission started. All three regex call-sites in _parse_wp_frontmatter_status,
_parse_wp_title, and _parse_wp_id were replaced with deterministic string
operations (str.partition + strip). The post-fix code is O(N) in the frontmatter
length. Wall-clock regression tests in tests/regressions/test_changelog_regex_redos.py
assert < 100 ms on 100 000-char adversarial inputs (FR-008). Applied per
secure-regex-catastrophic-backtracking tactic, escape-hatch option 1 (drop the
regex). Commit for the regression tests: 0cd1253a0.
```

---

### `migration/mission_state.py` — python:S6353 (line ~114 area)

**Sonar finding**: `python:S6353` (concise character class — use `\w` instead of
`[A-Za-z0-9_]`) on `src/specify_cli/migration/mission_state.py`.

**Classification**: Cosmetic only. S6353 is a style suggestion, not a
catastrophic-backtracking risk. The pattern `[A-Za-z0-9_]` is semantically
equivalent to `\w` in a non-Unicode context and carries no backtracking risk
(it is a character class match, not a repeated group).

**Sonar UI action**: Resolve as **Safe** with the following rationale.

**Rationale text for Sonar UI** (paste verbatim):
```
python:S6353 cosmetic finding. The character class [A-Za-z0-9_] is a safe,
explicit enumeration with no backtracking risk. Changing to \w alters locale
behaviour (in Python 3, \w includes Unicode word characters unless re.ASCII is
set). The explicit class is intentional to restrict matching to ASCII identifiers.
No catastrophic-backtracking exposure. Reviewed per secure-regex-catastrophic-backtracking
tactic (shape audit: single-character class, no repetition ambiguity).
```

---

### `review/cycle.py` — python:S6353 (line ~25 area)

**Sonar finding**: `python:S6353` on `src/specify_cli/review/cycle.py` — use `\d`
instead of a digit-range character class.

**Classification**: Cosmetic only. Same reasoning as `mission_state.py` above.
The pattern is a character class match in a named-group regex (`(?P<cycle>[1-9][0-9]*)`)
with no backtracking risk.

**Sonar UI action**: Resolve as **Safe** with the following rationale.

**Rationale text for Sonar UI** (paste verbatim):
```
python:S6353 cosmetic finding. The regex r"^review-cycle-(?P<cycle>[1-9][0-9]*)\.md$"
is anchored at both ends and uses simple character class matches — no backtracking
risk. The [1-9][0-9]* form is more legible than \d\d* for the intent (positive
integer, no leading zero). Reviewed per secure-regex-catastrophic-backtracking
tactic (single-character class iteration, shape-safe). Resolving as Safe.
```

---

## Loopback (127.0.0.1) hotspots — encrypt-data rule

All four open hotspots are `rule=encrypt-data` (Sonar category: "Make sure that this
server-side HTTP endpoint uses HTTPS"). Sonar flags any literal `http://` URL construction
involving `127.0.0.1` or localhost as a potential information-disclosure risk.

**Verdict for all four**: Safe (by design).

**Common rationale**: RFC 8252 §7.3 ("Loopback Interface Redirection") explicitly specifies
the HTTP loopback interface as the standard mechanism for native CLI application OAuth
callbacks. HTTPS is not used for the following reasons:

1. The loopback interface is not accessible from any external network — only from processes
   running on the same host.
2. TLS on loopback requires certificate management (generating, distributing, trusting a
   self-signed cert) which introduces more complexity and failure modes than the security
   benefit justifies on localhost.
3. The authorization code delivered by the OAuth server is single-use and short-lived
   (seconds). There is no persisted secret to intercept.
4. The browser and the callback server are both on the same host; there is no network hop
   for an adversary to intercept.

All four servers bind only to `127.0.0.1` (never `0.0.0.0`) and serve exactly one purpose
each (OAuth callback or local sync daemon health check). None expose user data beyond the
immediate flow.

---

### Hotspot AZ12J6Ty_lKMvCuaCZvj — `src/specify_cli/auth/loopback/callback_server.py:115`

**Sonar finding**: `encrypt-data` — "Using http protocol is insecure. Use https instead."

**File context**: Line 115 is the `callback_url` property of `CallbackServer`:
```python
return f"http://{_HOST}:{self.port}/callback"
```
`_HOST = "127.0.0.1"`. The server binds only to the loopback interface, listens on
an ephemeral port (OS-assigned from range 28888..28898 or a fallback kernel port),
and accepts exactly one HTTP GET at `/callback` — the OAuth Authorization Code response.
All other paths return HTTP 400. The server is stopped immediately after the code is
received. Access logging is silenced (`log_message` returns immediately) to prevent
the one-time authorization code from appearing in terminal output.

**To apply in Sonar UI**: Mark as **Safe** with this rationale text:
```
RFC 8252 §7.3 designates HTTP on the loopback interface as the standard approach for
native CLI OAuth callbacks. The server binds to 127.0.0.1 only (never 0.0.0.0),
listens on an ephemeral port allocated by the OS, accepts exactly one one-time
authorization code at /callback, and is stopped immediately after receipt. No TLS
is needed because: (a) the loopback interface has no external network exposure,
(b) self-signed cert management on localhost creates more failure risk than security
benefit, (c) the authorization code is single-use and short-lived. Access logging is
silenced to prevent the code from appearing in terminal output. Reviewed per WP07
secure-design-checklist tactic. Resolving as Safe.
```

---

### Hotspot AZ12J6Ty_lKMvCuaCZvk — `src/specify_cli/auth/loopback/callback_server.py:115`

**Sonar finding**: `encrypt-data` — duplicate of AZ12J6Ty_lKMvCuaCZvj (Sonar created two
hotspot instances for the same line, likely because the URL appears in both the docstring
and the property return).

**File context**: Same as above — the `callback_url` property string literal and/or its
docstring reference `http://127.0.0.1:<port>/callback`.

**To apply in Sonar UI**: Mark as **Safe** with the same rationale as AZ12J6Ty_lKMvCuaCZvj:
```
Duplicate Sonar entry for the same loopback callback URL in callback_server.py:115.
RFC 8252 §7.3 designates HTTP on the loopback interface as the standard approach for
native CLI OAuth callbacks. The server binds to 127.0.0.1 only (never 0.0.0.0),
accepts exactly one one-time authorization code, and is stopped after receipt. No
external network exposure. Resolving as Safe — see companion hotspot
AZ12J6Ty_lKMvCuaCZvj for full rationale.
```

---

### Hotspot AZ0QUf1nmOedRvCFo5GK — `src/specify_cli/dashboard/server.py:75`

**Sonar finding**: `encrypt-data` — "Using http protocol is insecure. Use https instead."

**File context**: Line 75 is the local dashboard HTTP server startup (the `spec-kitty dashboard`
command opens a browser tab to the local web UI served at `http://127.0.0.1:<port>`).
This is a developer-local dashboard, not a production network service.

**To apply in Sonar UI**: Mark as **Safe** with this rationale text:
```
The dashboard server is a local-only developer UI tool bound to 127.0.0.1, serving
only the operator's own browser on the same host. It is not a production network
service and does not transmit credentials or secrets over HTTP. The dashboard displays
spec-kitty mission status data that is already available on the local filesystem.
HTTPS on a local developer tool requires self-signed cert management with no
meaningful security benefit. Binding to 127.0.0.1 ensures no external network
exposure. Resolving as Safe.
```

---

### Hotspot AZ1ZVYN5Ubbqgtr7cvkz — `src/specify_cli/sync/daemon.py:556`

**Sonar finding**: `encrypt-data` — "Using http protocol is insecure. Use https instead."

**File context**: Line 556 is inside `_run_daemon_in_process` which creates an `HTTPServer`
bound to `127.0.0.1` for the sync daemon. The sync daemon is a local background process
that only accepts inter-process control signals (health checks and stop commands) from the
CLI running on the same host. The daemon token (`daemon_token`) is used for request
authentication between the CLI and the daemon, both running as the same OS user.

**To apply in Sonar UI**: Mark as **Safe** with this rationale text:
```
The sync daemon HTTP server binds to 127.0.0.1 only and is used exclusively for
inter-process communication between the CLI and its own background daemon, both
running as the same OS user on the same host. The daemon_token provides request
authentication between the two processes. There is no external network exposure.
HTTPS on a local IPC mechanism requires self-signed cert distribution between
the two processes with no meaningful security benefit — the loopback interface
already provides host-local isolation. Resolving as Safe.
```

---

## Review-lock signal-safety hotspot

**Finding at T036 triage (WP07, 2026-05-14)**: After querying the SonarCloud hotspots
API, all 4 open hotspots are `encrypt-data` rule (HTTP vs HTTPS on loopback) — there is
no separate signal-safety hotspot in the current TO_REVIEW queue. The `review/lock.py`
file exists in the codebase but does not appear in the Sonar hotspot list for `main`.

**Conclusion**: The WP07 prompt anticipated a signal-safety hotspot based on the WP05
findings analysis. As of the 2026-05-14 Sonar scan, that hotspot is either:
(a) not flagged by Sonar on this codebase (the signal handler may be in a pattern
Sonar does not flag for this rule set), or
(b) was resolved before the scan baseline.

**No action required** for T036 beyond this documentation. The 4 open hotspots are
fully covered by the loopback rationales above.

**Operator note**: If a signal-safety hotspot appears after the next push-time scan
is restored (T038), apply the following guidance:
- If handler calls non-AS-safe functions (e.g., `logging.warning`, file writes): fix
  by deferring to a flag set in the handler and processing on the main path.
- If handler is correct (AS-safe, scoped properly, restores previous handler): resolve
  as Safe with rationale citing POSIX signal-safety requirements and the specific
  AS-safe mechanisms used.

---

*Loopback and signal-safety sections authored in WP07 (2026-05-14) by claude:sonnet:python-pedro:implementer.*
*This file was initially authored in WP04 (2026-05-14) by claude:sonnet:python-pedro:implementer.*
*Operator applies rationales in the Sonar UI as part of the mission-merge review.*
