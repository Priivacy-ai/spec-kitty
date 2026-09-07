# Mission Specification: Team Kitty launch defaults for the CLI

**Mission Branch**: `feat/team-kitty-launch-defaults`
**Created**: 2026-09-07
**Status**: Draft
**Input**: User description: "3980" (GitHub issue #3980, execution plan for launch blocker #1621 under epic #1091)

## Confirmed Intent

A person installs a launch build of the CLI fresh, or an agent acts inside a
mission on their behalf, and runs ordinary commands with nothing hosted
configured. Team Kitty must work out of the box: signing in and minting a
relay capability target the packaged hosted address, every lane transition
and lifecycle beat publishes a moment to the team's Zeitgeist relay from any
kind of checkout, and local operation is never blocked by hosted state. The
retired "sync" transport and its leftover switches disappear from the
product; one explicit offline switch replaces them.

Interview answers (four Decision Moments, all resolved): silent local
operation with a one-time non-blocking sign-in hint; owned checkouts publish
moments like any other checkout; target precedence is environment override,
then configured server address, then packaged default, with the resolved
target visible to the user; the enable flag is deleted, hosted features are
always present, and authentication state is the only switch: no session and
no service token means no hosted request of any kind (plan Decision Moment,
2026-09-07, superseding the earlier offline-switch idea).

## Domain Language

Canonical terms from [Context: Team Kitty and Zeitgeist](../../docs/context/team-kitty.md):

- **Team Kitty** — the hosted product. Do not say "the SaaS sync".
- **Team workspace** — the tenant a person belongs to. "Teamspace" is a
  compatibility identifier, not a term for new prose.
- **Zeitgeist relay** — the per-team presence-and-moments relay Team Kitty
  provisions. Do not say "sync server".
- **Moment** — one bounded status event the CLI publishes to the relay.
- **Admission** — the server-side decision that a repository belongs to a
  team; together with membership it is the only gate. Do not say "consent"
  or "opt-in".
- **Authenticated** — the CLI holds a usable session or service token. It
  is the only on/off switch for hosted behavior: `auth login` turns hosted
  behavior on, `auth logout` turns it off. There is no separate offline
  switch.
- **Sync** — a retired transport. The word must not appear in new
  operator-facing text, identifiers, or configuration.

## Bulk-edit declaration

This mission retires the identifiers `SPEC_KITTY_ENABLE_SAAS_SYNC`,
`SPEC_KITTY_SYNC_DISABLE`, `SPEC_KITTY_SYNC_MINIMAL_IMPORT`, the error code
`OWNED_SYNC_UNSUPPORTED`, and the `sync_active` / `is_saas_sync_enabled`
gate across the codebase, replacing them with authentication state and two
explicitly named opt-outs. Per-category rules are captured in
`occurrence_map.yaml` during planning; historical artifacts under
`kitty-specs/`, `kitty-ops/`, and archived docs are not rewritten.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Works out of the box (Priority: P1)

A person installs a launch build, runs `spec-kitty status` in a project with
no hosted configuration and no session, then later runs `spec-kitty auth
login`. Nothing asks for a server address; sign-in lands on Team Kitty.

**Why this priority**: The launch gate (#1621) is defined by exactly this.

**Independent Test**: Fresh isolated home, no environment variables, no
config: run a normal command, then sign in against a stub server that
records the requested address.

**Acceptance Scenarios**:

1. **Given** no hosted configuration and no session, **When** a normal
   command runs interactively, **Then** it completes locally and prints one
   non-blocking hint to sign in, and the same hint is not printed again on
   that machine.
2. **Given** no hosted configuration, **When** `auth login` runs, **Then**
   the flow targets the packaged hosted address without any setup step.
3. **Given** a non-interactive, JSON, `--help`, or `--version` invocation,
   **When** it runs without a session, **Then** its output contains no hint
   and no prompt.

---

### User Story 2 - Target precedence is explicit and visible (Priority: P1)

A developer targets the development deployment through the configured
server address, or a self-hoster overrides it through the environment, and
can always see which target is in effect and why.

**Why this priority**: A silent wrong target sends moments to the wrong
place; the launch build must not break existing developer setups.

**Independent Test**: Matrix of {environment override, configured address,
neither} against {packaged default}, asserting the resolved target and the
displayed source.

**Acceptance Scenarios**:

1. **Given** only a configured server address, **When** any hosted operation
   resolves its target, **Then** the configured address wins over the
   packaged default with no warning.
2. **Given** an environment override and a configured address that
   disagree, **When** a hosted operation resolves its target, **Then** it
   fails closed naming both values, exactly as today.
3. **Given** any of the three sources, **When** `auth login` or `auth status`
   runs, **Then** the output shows the resolved target and names its source
   (environment, configuration, or packaged default).

---

### User Story 3 - Owned checkouts publish moments (Priority: P1)

An agent working in an owned checkout moves a work package; the team's
relay receives the same moment it would from a lane worktree.

**Why this priority**: Today this path refuses outright once hosted
features are on; it would break every owned-checkout mission at launch.

**Independent Test**: Real repository with an owned checkout and a stub
relay; move a work package and assert one published moment with the same
shape as the worktree case.

**Acceptance Scenarios**:

1. **Given** an owned checkout and a resolvable capability, **When** a work
   package moves lanes, **Then** the move succeeds and one moment reaches
   the relay.
2. **Given** an owned checkout and no capability, **When** a work package
   moves lanes, **Then** the move succeeds locally and no error is raised.

---

### User Story 4 - Authentication is the switch, two honest opt-outs (Priority: P2)

An operator in an air-gapped or CI environment simply holds no session and
no service token and sees no hosted traffic of any kind; `auth logout`
turns hosted behavior off on a personal machine. An orchestrator that must
skip the pre-review gate, or a process that must not register moment
handlers at import, uses a switch whose name says what it does.

**Why this priority**: Replaces four overloaded leftovers with the one
switch the product already has plus two named opt-outs; without it the
retired vocabulary keeps leaking into operator guidance.

**Independent Test**: With no session and no token, drive a lane transition
and a readiness probe against a recording stub and assert zero requests;
run `auth logout` on an authenticated machine and repeat; exercise each
opt-out in isolation.

**Acceptance Scenarios**:

1. **Given** no session and no service token, **When** any command runs,
   **Then** no hosted request is attempted, including moments and readiness
   probes, and local behavior is unchanged.
2. **Given** an authenticated machine, **When** `auth logout` runs, **Then**
   subsequent commands attempt no hosted request until `auth login`.
3. **Given** the retired enable flag is present in the environment, **When**
   any command runs, **Then** it has no effect and a one-time deprecation
   notice names authentication as the switch.
4. **Given** the pre-review gate opt-out, **When** a work package moves to
   review, **Then** only the gate is skipped and nothing hosted changes.

---

### User Story 5 - Logged out never blocks local work (Priority: P2)

A person whose session expired, or who is not a member of the admitted
team, keeps working locally with guidance rather than refusals.

**Why this priority**: Issues #2875 and #2695 describe today's fail-closed
and inconsistent behavior; launch defaults make that the common case.

**Independent Test**: Expired session, revoked membership, unreachable
relay, and unadmitted repository, each against local mission commands and
the tracker command group.

**Acceptance Scenarios**:

1. **Given** an expired or missing session, **When** a local mission command
   runs, **Then** it completes and the moment is dropped silently.
2. **Given** an expired or missing session, **When** a hosted-only command
   runs (tracker, ticket import), **Then** it fails with the sign-in
   guidance, never with a "not enabled" message.
3. **Given** an unreachable relay, **When** a work package moves lanes,
   **Then** the move completes within the existing bounded time and the
   user is not prompted.

### Edge Cases

- A configured server address that is malformed or blank is treated as
  absent, not as a disagreement.
- The one-time hint must survive concurrent invocations without being
  printed twice and must not be persisted into project files.
- The retired flag set to any value, truthy or falsy, has no effect.
- A service token in the environment counts as authenticated, so CI that
  wants hosted behavior supplies one and CI that does not simply omits it.
- An owned checkout whose repository is not admitted publishes nothing and
  still completes the move.
- Existing machines carrying the retired names in their persisted
  environment file continue to work; the provisioning migration stops
  seeding the retired names.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Packaged hosted default | As a person on a launch build, I want sign-in and capability minting to target the packaged hosted address when nothing is configured, so that no setup step precedes first use. | High | Approved |
| FR-002 | Target precedence | As a developer or self-hoster, I want the environment override to win over the configured address, and the configured address to win over the packaged default, so that existing setups keep their target. | High | Approved |
| FR-003 | Disagreement fails closed | As an operator, I want an environment override that disagrees with the configured address to fail closed naming both, so that a wrong target is never chosen silently. | High | Approved |
| FR-004 | Target visibility | As a user, I want `auth login` and `auth status` to show the resolved target and its source, so that I can tell where hosted traffic goes. | High | Approved |
| FR-005 | One-time sign-in hint | As a person without a session, I want ordinary interactive commands to complete and show one non-blocking sign-in hint once per machine, so that I am informed without being interrupted. | High | Approved |
| FR-006 | Clean machine output | As an automation author, I want non-interactive, JSON, help, and version invocations to carry no hint and no prompt, so that output stays deterministic. | High | Approved |
| FR-007 | Owned checkouts publish | As an agent in an owned checkout, I want a lane move to publish the same moment as from a lane worktree, so that the hosted view is complete. | High | Approved |
| FR-008 | Guard removed | As a maintainer, I need the owned-checkout refusal removed, so that no code path refuses a move because hosted features are present. | High | Approved |
| FR-009 | Enable flag deleted | As an operator, I want hosted features always available without an enable flag, with sign-in guidance when logged out, so that "not enabled" never appears. | High | Approved |
| FR-010 | Authentication is the switch | As an operator, I want no hosted request of any kind, including moments and readiness probes, whenever I hold no session and no service token, and `auth logout` to restore that state, so that air-gapped and CI use needs no extra switch. | High | Approved |
| FR-011 | Named opt-outs | As an orchestrator, I want the pre-review gate skip and the moment-handler import gate to have their own explicitly named switches, so that neither borrows a retired name. | Medium | Approved |
| FR-012 | Deprecation notice | As a user with the retired names in my environment, I want them ignored with a one-time notice naming authentication as the switch, so that migration is discoverable. | Medium | Approved |
| FR-013 | Logged out degrades | As a person whose session lapsed or membership ended, I want local mission commands to complete and hosted-only commands to fail with sign-in guidance, so that I am never wedged. | High | Approved |
| FR-014 | Provisioning follows | As an upgrader, I want the environment-file provisioning to stop seeding retired names, so that new machines carry no dead configuration. | Medium | Approved |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Bounded hosted cost | A lane move with an unreachable relay or absent credential completes within the existing fan-out bound of 10 seconds and typically within 1 second; an unauthenticated machine adds zero network time. | Performance | High | Approved |
| NFR-002 | Zero egress unauthenticated | With no session and no service token, a recording stub observes 0 hosted requests across a full specify-to-review cycle, including readiness. | Reliability | High | Approved |
| NFR-003 | Deterministic machine output | 100% of JSON, `--help`, `--version`, and non-TTY invocations produce byte-identical output with and without a session, except for fields that carry session state by contract. | Compatibility | High | Approved |
| NFR-004 | No credential leakage | The resolved target display and every notice contain no token, session, or capability value; verified by a redaction test over all new output strings. | Security | High | Approved |
| NFR-005 | Non-vacuous evidence | Every behavior change has a witnessed failing-first check through its existing entry point on the base and a passing check afterwards; no fixture stubs the change away. | Testability | High | Approved |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Canonical authority | Reuse the existing target-resolution, credential-resolution, readiness, and moment-publishing authorities; introduce no second reading of any of them. | Architecture | High | Approved |
| C-002 | Vocabulary | New identifiers (the two opt-outs) use Team Kitty vocabulary; no new `SAAS_`, `SYNC_`, or `TEAMSPACE` identifiers. `SPEC_KITTY_SAAS_URL` and `SPEC_KITTY_SAAS_TOKEN` keep their names as overrides. | Terminology | High | Approved |
| C-003 | Bulk edit governed | Retirement of the named identifiers runs through the occurrence-classification workflow; historical archives are not rewritten. | Process | High | Approved |
| C-004 | Scope | No version bump, no SaaS-side change, no relay change, no non-interactive CI sign-in (#3277), no tracker control-plane redesign, no first-run announcement copy. | Scope | High | Approved |
| C-005 | Decision record | The packaged default is a reversal of decision D-5 and is recorded as its own architecture decision record before implementation. | Governance | High | Approved |
| C-006 | Tracker hygiene | Issues #1621, #3980, #2875, #2695 are claimed with a comment naming this mission and carry issue-matrix rows; #3154 and #3892 are referenced, not closed. | Process | Medium | Approved |

### Key Entities *(include if feature involves data)*

- **Hosted target**: the address hosted operations use, with a source
  (environment, configuration, packaged default).
- **Session**: the person's signed-in state with Team Kitty; absent,
  expired, or valid.
- **Capability**: the relay-scoped grant minted after admission; present or
  absent per repository.
- **Sign-in hint state**: the per-machine record that the one-time hint has
  been shown.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A fresh install completes `auth login` against Team Kitty with
  zero configuration steps.
- **SC-002**: 100% of the target-precedence matrix cells resolve to the
  expected address and display the expected source.
- **SC-003**: An owned-checkout lane move publishes exactly one moment,
  identical in shape to the lane-worktree case.
- **SC-004**: Unauthenticated, zero hosted requests are observed across a
  full mission cycle; logged-out users complete every local command.
- **SC-005**: Zero occurrences of the retired identifiers remain in
  operator-facing text, live code, or shipped configuration templates;
  historical archives unchanged.
- **SC-006**: All new behavior is red-first witnessed; the full
  architectural gate suite stays at or below its baseline counts.

## Sources and Assumptions

- Issues: #3980 (execution plan), #1621 (launch blocker), #1091 (epic),
  #2875, #2695 (degrade when logged out), #3154 (vocabulary), #3892 (auth
  lifecycle), #3277 (CI sign-in, out of scope).
- Context page: `docs/context/team-kitty.md` (PR #3982), read at
  spec-kitty `d6e8fe423`, EXPERIMENTAL-zeitgeist `9b6553e`,
  EXPERIMENTAL-spec-kitty-saas `93e2ad2`.
- Assumption: CI producers that want no hosted behavior carry no session
  and no service token; nothing else is required.
