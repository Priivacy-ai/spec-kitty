# Sync Architecture

spec-kitty 2.x enables teams to synchronise project state across multiple developers and
machines. In practice, this means several people -- or AI agents -- can edit specifications
concurrently, sometimes while completely disconnected from the network, and have their changes
merge cleanly when they reconnect.

The core idea behind the sync system is **event sourcing**. Rather than syncing the current
*state* of a project (which would require deciding whose copy wins when two people edit the same
thing), spec-kitty syncs *events* -- individual records of what changed. Each event is small,
self-contained, and causally ordered, so the system can merge concurrent work from different nodes
without conflicts.

This approach delivers three key properties:

- **Offline-first**: Every developer has a complete local copy and can work without a network
  connection. Events queue up locally and sync later.
- **Conflict-free merging**: Because events carry causal ordering information, the system can
  deterministically reconstruct the same final state regardless of the order events arrive.
- **Complete audit trail**: Every change is preserved as an immutable event, providing a full
  history of who changed what and when.

The rest of this page explains the data model that makes this possible, the three paths events
travel between nodes, and how authentication ties it all together.


## The Event Model

Every change in the sync system is represented as an **event** -- an immutable record describing
something that happened. Events flow between the CLI and the server, and each node applies them
in causal order to build its local view of the project.

An event contains the following fields:

| Field | Purpose |
|---|---|
| `event_id` | A globally unique identifier (UUID) for this event. No two events anywhere in the system share the same ID, which makes deduplication straightforward. |
| `event_type` | A string describing what happened, such as `feature_created` or `wp_status_changed`. The event type determines how the payload is interpreted. |
| `aggregate_id` | The identifier of the entity this event relates to -- a project, feature, or work package. |
| `aggregate_type` | The kind of entity (`project`, `feature`, `work_package`). Together with `aggregate_id`, this pinpoints exactly what was affected. |
| `lamport_clock` | A logical clock value used for causal ordering (see below). |
| `node_id` | Identifies which CLI instance or server produced this event. Each installation has a stable node ID. |
| `payload` | A JSON object containing the actual data -- the new title, the updated status, the added content, and so on. |
| `timestamp` | Wall-clock time when the event was created. Used only for display purposes; **not** used for ordering. |

### Causal ordering with Lamport clocks

Wall-clock timestamps are unreliable for ordering distributed events -- clocks drift, time zones
differ, and two machines may record the same second for unrelated changes. spec-kitty uses
**Lamport clocks** instead.

A Lamport clock is a simple logical counter that follows two rules:

1. Every time a node creates a new event, it increments its own clock.
2. When a node receives an event from another node, it sets its clock to the maximum of its own
   clock and the received event's clock, then increments.

These rules guarantee **causal consistency**: if event A caused event B (directly or
transitionally), then B's Lamport clock value is always higher than A's. Events from different
nodes that happen concurrently -- neither caused the other -- may have any relative clock values,
and the system merges them deterministically using conflict-free rules so that every node
converges to the same final state.


## Real-Time Sync (WebSocket)

When the CLI is online and authenticated, it opens a persistent WebSocket connection to the
server. This is the primary sync path and provides the lowest-latency experience -- changes
appear on other connected clients within moments.

The lifecycle of a WebSocket session works as follows:

1. **Authentication**: The CLI exchanges its JWT access token for a short-lived WebSocket token
   via a REST API call, then includes that token in the WebSocket handshake. This avoids sending
   the long-lived JWT over the WebSocket protocol. (See
   [Authentication Flow](#authentication-flow) below for the full picture.)

2. **Snapshot**: On successful connection, the server sends a `snapshot` message containing the
   current state of the project. This brings the CLI up to date before any incremental events
   arrive.

3. **Bidirectional events**: Once the snapshot is applied, both sides exchange `event` messages
   as changes occur. When a developer creates a feature locally, an event is sent to the server,
   which broadcasts it to other connected clients in the same team. When another client creates a
   work package, the event flows back.

4. **Heartbeat**: A `ping`/`pong` exchange every 20 seconds keeps the connection alive and
   detects network failures promptly.

5. **Team isolation**: Each WebSocket connection is scoped to a team-specific channel group.
   Events from one team are never visible to members of another team.

This path provides the best user experience but requires an active network connection. When the
network is unavailable, events are handled by the offline queue instead.


## Offline Queue & Batch Sync

Developers are not always connected. An AI agent running in a CI pipeline, a developer on an
aeroplane, or a flaky office Wi-Fi connection -- all of these are normal operating conditions for
spec-kitty. The offline queue ensures no work is ever lost.

### How the queue works

When the CLI cannot reach the server, events are written to a **local SQLite database** instead
of being sent over WebSocket. The SQLite store acts as a durable, ordered queue. Events
accumulate with their Lamport clock values intact, preserving causal ordering even while offline.

Developers can work for minutes, hours, or days without a connection. Every change they make --
creating features, updating work packages, moving tasks through the Kanban board -- is captured
as events in the local queue.

### Syncing later

When connectivity returns, there are two ways events leave the queue:

- **Manual sync**: The developer runs `spec-kitty sync now`, which triggers an immediate batch
  upload.
- **Automatic reconnection**: When the CLI re-establishes a WebSocket connection, queued events
  are flushed automatically.

The batch sync process uploads events in chunks of up to **1,000 per request**, with
**gzip compression** to minimise bandwidth. The server processes each event individually and
returns a per-event success or failure status, so a single problematic event does not block the
rest of the batch.

After pushing local events, the CLI pulls any new events from the server that arrived while the
node was offline. This bidirectional exchange ensures all nodes converge to the same state.

The result: developers can work completely offline without losing any changes, and synchronisation
happens cleanly whenever they reconnect.


## Authentication Flow

The sync system uses JSON Web Tokens (JWT) for authentication, with a layered token design that
balances security with convenience.

```
Username + Password
    |
    v
POST /api/v1/token/ --> Access Token (1h) + Refresh Token (7d)
    |                        |
    v                        v
API calls /              POST /api/v1/token/refresh/ --> New Access Token
WS token exchange
    |
    v
POST /api/v1/ws-token/ --> Ephemeral WS Token (5min)
    |
    v
WebSocket handshake
```

### Token types and lifetimes

- **Access token** (1 hour): Used for all REST API calls and to obtain WebSocket tokens. Short
  lifetime limits the damage if a token is intercepted.
- **Refresh token** (7 days): Used solely to obtain new access tokens without re-entering
  credentials. Stored securely and never sent to the WebSocket endpoint.
- **WebSocket token** (5 minutes): An ephemeral, single-use token obtained by exchanging a valid
  access token. Its very short lifetime ensures that even if captured, it is useless almost
  immediately.

### Automatic refresh

The CLI handles token renewal transparently. When an access token expires, the CLI automatically
uses the refresh token to obtain a new one. This cycle continues until the refresh token itself
expires (after 7 days of inactivity), at which point the developer must re-authenticate with
their username and password.

### Credential storage

Tokens are stored in `~/.spec-kitty/credentials.json`. See the
[Configuration Reference](../reference/configuration.md#server-configuration-2x) for the file
format and security considerations.


## See Also

- [Authentication How-To](../how-to/authenticate.md) -- step-by-step guide to logging in and
  managing credentials
- [Server Sync How-To](../how-to/sync-to-server.md) -- how to push and pull events
- [CLI Commands Reference](../reference/cli-commands.md#spec-kitty-auth) -- `spec-kitty auth`
  subcommands
- [Configuration Reference](../reference/configuration.md#server-configuration-2x) -- server
  and credential settings
