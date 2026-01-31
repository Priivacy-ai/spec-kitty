# Feature Specification: MCP Server for Conversational Spec Kitty Workflow

**Feature Branch**: `099-mcp-server-for-conversational-spec-kitty-workflow`  
**Created**: 2026-01-29  
**Status**: Draft  
**Input**: User description: "implement an mcp server offering the current functionality of spec kitty so that the user doesnt have to learn the slash commands but can talk directly to the AI Agent"

## Clarifications

### Session 2026-01-29

- Q: Where should conversation state (discovery interviews, multi-turn context) be persisted? → A: Project-local `.kittify/` directory (e.g., `.kittify/mcp-sessions/`), stored indefinitely (not limited to 24 hours)
- Q: How should concurrent modifications from multiple MCP clients be handled? → A: Pessimistic locking (lock file before write, block others)
- Q: How should the MCP server discover available Spec Kitty projects? → A: The project name will come from the user prompt and verified by the MCP before actions are taken
- Q: Should the MCP server implement authentication/authorization for connecting clients? → A: API key authentication with configuration to disable it
- Q: How should server lifecycle be managed (startup, shutdown, restarts)? → A: Manual only (user starts/stops server explicitly)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Conversational Feature Creation (Priority: P1)

A developer wants to create a new feature specification by describing their idea in natural language to an AI agent, without learning any Spec Kitty slash commands or CLI syntax.

**Why this priority**: This is the core value proposition - replacing command-based interaction with natural conversation. Without this, the MCP server provides no meaningful improvement over existing slash commands.

**Independent Test**: Can be fully tested by connecting an MCP client (like Claude Desktop), describing a feature in plain English, and verifying that the server conducts a discovery interview and generates a complete specification in the project's `kitty-specs/` directory.

**Acceptance Scenarios**:

1. **Given** an MCP client is connected to the server and a Spec Kitty project path is specified, **When** the user says "I want to build a user authentication system", **Then** the server initiates a discovery interview asking relevant questions about the feature
2. **Given** the discovery interview is in progress, **When** the user answers each question, **Then** the server asks follow-up questions until sufficient context is gathered
3. **Given** discovery is complete, **When** the server has enough information, **Then** it creates a feature directory under `kitty-specs/###-feature-name/` and generates a complete `spec.md` file
4. **Given** a spec has been created, **When** the user asks "show me the spec", **Then** the server returns the content of the generated specification

---

### User Story 2 - Conversational Task Planning (Priority: P2)

After a specification exists, a developer wants to break it down into work packages through natural conversation, receiving intelligent suggestions for task breakdown and dependencies.

**Why this priority**: Task planning is the critical bridge between specification and implementation. It enables parallel development and clear work assignments, which are core to Spec Kitty's workflow model.

**Independent Test**: Can be tested by creating a feature spec first, then asking the AI "break this into tasks", and verifying that the server generates a `plan.md` with technical approach and a `tasks/` directory with individual work package files including dependency tracking.

**Acceptance Scenarios**:

1. **Given** a feature specification exists, **When** the user says "create a plan for this feature", **Then** the server generates a technical approach in `plan.md` and proposes work package breakdown
2. **Given** the server proposes work packages, **When** the user asks "what if we combine WP02 and WP03?", **Then** the server adjusts the breakdown and explains implications
3. **Given** work packages are finalized, **When** the server creates task files, **Then** each task includes dependencies parsed from the plan and stored in frontmatter
4. **Given** tasks are created, **When** the user asks "which tasks can I start now?", **Then** the server identifies all tasks with no unmet dependencies

---

### User Story 3 - Conversational Task Management (Priority: P2)

During implementation, a developer wants to update task status, move work packages between lanes, and track progress through natural language commands rather than CLI syntax.

**Why this priority**: Task management is a frequent operation during active development. Making it conversational eliminates context-switching and cognitive load.

**Independent Test**: Can be tested by creating tasks, then asking "move WP01 to doing" or "show me what's in review", and verifying that task frontmatter and the activity log are updated correctly.

**Acceptance Scenarios**:

1. **Given** tasks exist in various lanes, **When** the user says "what tasks are ready to work on?", **Then** the server lists all tasks in the "planned" lane
2. **Given** a task is in "planned" lane, **When** the user says "I'm starting work on WP01", **Then** the server moves WP01 to "doing" lane and updates the activity log
3. **Given** implementation is complete, **When** the user says "WP01 is ready for review", **Then** the server moves WP01 to "for_review" lane with a timestamp
4. **Given** multiple agents are working, **When** the user asks "what is everyone working on?", **Then** the server shows current task assignments and status across all work packages

---

### User Story 4 - Conversational Workspace Management (Priority: P3)

A developer working on a work package wants to create, switch between, and manage git worktrees through conversational commands without memorizing workspace CLI syntax.

**Why this priority**: Workspace management is essential for parallel development but is used less frequently than specification and task operations. It's important but not blocking for initial adoption.

**Independent Test**: Can be tested by asking "start working on WP01", verifying a worktree is created at `.worktrees/###-feature-WP01/`, then asking "switch to WP02" and confirming the working directory changes.

**Acceptance Scenarios**:

1. **Given** work packages exist, **When** the user says "start implementing WP01", **Then** the server creates a worktree at `.worktrees/###-feature-WP01/` with its own git branch
2. **Given** WP02 depends on WP01, **When** the user says "implement WP02 after WP01", **Then** the server creates WP02's worktree branching from WP01's branch
3. **Given** multiple worktrees exist, **When** the user asks "show my workspaces", **Then** the server lists all active worktrees with their branches and status
4. **Given** a work package is complete, **When** the user says "merge WP01 into main", **Then** the server executes the merge workflow with preflight validation

---

### User Story 5 - Multi-Project Management (Priority: P3)

A developer working on multiple Spec Kitty projects wants to switch context between projects and query information across them through natural conversation.

**Why this priority**: Multi-project support enables the global server architecture to shine. While valuable for developers managing multiple codebases, it's not essential for single-project workflows.

**Independent Test**: Can be tested by initializing two Spec Kitty projects, connecting the MCP server, asking "list my projects", then "switch to project X" and "show features", verifying operations target the correct project's `.kittify/` directory.

**Acceptance Scenarios**:

1. **Given** the MCP server is running, **When** the user says "show features in /path/to/my-project", **Then** the server validates the path contains `.kittify/` and lists features from that project's `kitty-specs/` directory
2. **Given** a user is working with one project, **When** the user says "in /path/to/other-project, show features", **Then** the server switches context to the specified project and lists its features
3. **Given** a project path is specified in a command, **When** the user says "show features", **Then** the server lists features from the currently active project context
4. **Given** no project is specified in the command or context, **When** the user issues a command, **Then** the server prompts "Which project would you like to work with? Please include the project path in your next message."

---

### User Story 6 - Conversational Review and Acceptance (Priority: P2)

A reviewer wants to examine work packages, request changes, and accept/reject implementations through natural dialogue with the AI, without learning review command syntax.

**Why this priority**: Review and acceptance are critical quality gates. Making them conversational reduces friction in the feedback loop and enables more thorough reviews.

**Independent Test**: Can be tested by moving a task to "for_review", then saying "review WP01", providing feedback like "the authentication logic needs tests", and verifying the task moves back to "doing" with feedback recorded.

**Acceptance Scenarios**:

1. **Given** a work package is in "for_review" lane, **When** the user says "review WP01", **Then** the server displays the work package details and prompts for feedback
2. **Given** the review is in progress, **When** the user says "this looks good, approve it", **Then** the server moves WP01 to "done" lane and records approval in the activity log
3. **Given** changes are needed, **When** the user says "WP01 needs better error handling", **Then** the server moves WP01 back to "doing" with the feedback note
4. **Given** a feature is complete, **When** the user says "accept feature 099", **Then** the server merges all approved work packages and updates feature status

---

### Edge Cases

- **What happens when an MCP client connects but no project is specified?** The server prompts the user to specify a project path in their request (e.g., "Which project would you like to work with? Please include the project path or name in your next message."). The server validates the path contains a `.kittify/` directory before proceeding.

- **How does the system handle concurrent modifications from multiple MCP clients?** The server implements pessimistic locking: when a client begins modifying state files, it acquires a lock file (e.g., `.kittify/.lock-WP01`) that blocks other clients from writing to the same resource. If a lock is held, other clients receive an error message like "WP01 is currently being modified by another client. Retry in a moment." Locks are automatically released on operation completion or timeout (e.g., 5 minutes).

- **What happens when a user asks an ambiguous question like "show status"?** The server should clarify intent (e.g., "Do you want to see: (A) feature status, (B) task lane status, (C) git branch status, or (D) server health?").

- **How does the system handle discovery interruptions?** If a discovery interview is interrupted mid-conversation (client disconnects or user switches topics), the server should save partial state and offer to resume when reconnected.

- **What happens when a user tries to perform operations on a non-Spec Kitty project?** The server should detect the absence of `.kittify/` directory and offer to initialize the project or switch to a valid project.

- **How does the server handle invalid project paths or missing dependencies?** The server should validate project structure on startup and during operations, providing actionable error messages (e.g., "Project missing .kittify/config.yaml. Run initialization first.").

- **What happens when multiple users work on the same feature simultaneously?** The server should detect git conflicts during merge operations and guide users through resolution using conversational prompts.

- **How does authentication work when API key is enabled?** MCP clients must include the API key in the connection headers or initial handshake. If authentication fails, the server returns an error message "Authentication required. Please configure your MCP client with a valid API key." If authentication is disabled in server configuration, all local clients are trusted without requiring keys.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST implement an MCP server that exposes all current Spec Kitty CLI commands as conversational tools
- **FR-002**: System MUST support conversational discovery interviews for feature creation, maintaining state across multiple back-and-forth exchanges
- **FR-003**: System MUST read and write all state to project-local `.kittify/` directories (no centralized database), including conversation state stored in `.kittify/mcp-sessions/`
- **FR-004**: System MUST support managing multiple Spec Kitty projects from a single server instance, with project paths specified in user prompts and verified before operations
- **FR-005**: System MUST allow users to specify which project to operate on via natural language in their prompts (e.g., "in project X, show features"), validating the project path exists and contains `.kittify/` directory before executing operations
- **FR-006**: System MUST expose the following workflow operations as MCP tools:
  - Feature specification creation (`/spec-kitty.specify` equivalent)
  - Feature planning (`/spec-kitty.plan` equivalent)
  - Task breakdown (`/spec-kitty.tasks` equivalent)
  - Implementation workflow (`/spec-kitty.implement` equivalent)
  - Review workflow (`/spec-kitty.review` equivalent)
  - Acceptance workflow (`/spec-kitty.accept` equivalent)
- **FR-007**: System MUST expose task management operations:
  - List tasks by lane
  - Move tasks between lanes
  - Add task history entries
  - Query task status and dependencies
- **FR-008**: System MUST expose workspace management operations:
  - Create git worktrees for work packages
  - Switch between worktrees
  - List active worktrees
  - Merge workflows with preflight validation
- **FR-009**: System MUST expose agent configuration operations:
  - List/add/remove supported AI agents
  - Update agent context files
  - Sync agent configurations
- **FR-010**: System MUST expose system operations:
  - Check project dependencies
  - Validate project structure
  - List available missions
  - Report server health
- **FR-011**: System MUST maintain conversation context across multiple exchanges to support discovery interviews, persisting state indefinitely in project-local `.kittify/mcp-sessions/` directory
- **FR-012**: System MUST validate project structure before operations and return actionable error messages if validation fails
- **FR-013**: System MUST implement pessimistic file-level locking when multiple clients modify the same project state (acquire lock before write, block other clients until lock is released)
- **FR-014**: System MUST preserve all existing Spec Kitty behaviors (git commits, activity logs, frontmatter updates, checklist generation)
- **FR-015**: System MUST support both stdio (standard input/output) and SSE (Server-Sent Events) transports for MCP communication
- **FR-016**: System MUST provide detailed operation logs for debugging and audit trails
- **FR-017**: System MUST wrap and reuse existing CLI code rather than reimplementing functionality, ensuring the MCP implementation remains independent from and parallel to the CLI interface
- **FR-018**: System MUST implement optional API key authentication for connecting MCP clients, with configuration to disable authentication for trusted local environments
- **FR-019**: System MUST support manual lifecycle management only (user explicitly starts and stops the server via command), with no automatic restart or system service integration

### Architectural Constraints

- **AC-001**: The MCP server SHALL act as a thin wrapper around existing `spec-kitty` CLI commands and core library functions, invoking the same code paths used by the CLI rather than duplicating logic
- **AC-002**: The MCP implementation SHALL be architecturally independent from the CLI implementation, allowing both interfaces to evolve separately while sharing the same core functionality
- **AC-003**: Changes to core Spec Kitty workflows (feature creation, task management, workspace operations) SHALL automatically be available to both CLI and MCP interfaces without requiring parallel modifications
- **AC-004**: The MCP server SHALL translate conversational input into structured parameters for existing CLI functions, maintaining a clear separation between the conversational interface layer and the business logic layer

### Key Entities

- **MCPServer**: The main server instance that handles MCP protocol communication, manages multiple project contexts, and routes tool invocations to appropriate handlers. Acts as a thin conversational wrapper around existing CLI code.
- **ProjectContext**: Represents a single Spec Kitty project with its path, active feature, current mission, and cached state (metadata, tasks, worktrees)
- **ConversationState**: Tracks multi-turn discovery interviews including the current phase (discovery/clarification/generation), answered questions, pending questions, and accumulated context. Persisted indefinitely in `.kittify/mcp-sessions/` directory.
- **MCPTool**: Represents an exposed MCP tool with its name, description, input schema, and handler function. Each tool translates conversational input into structured parameters and delegates to existing CLI functions or core library modules.
- **OperationResult**: Encapsulates the result of a tool invocation including success status, generated artifacts (files, commits), updated state, and any error messages or warnings
- **CLIAdapter**: An abstraction layer that wraps existing CLI commands and core library functions, providing a consistent interface for the MCP server to invoke Spec Kitty operations without duplicating business logic

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can create a complete feature specification through conversational interaction without consulting Spec Kitty documentation or learning slash command syntax
- **SC-002**: Discovery interviews successfully gather sufficient context with an average of 3-5 questions per feature (matching current `/spec-kitty.specify` behavior)
- **SC-003**: All existing Spec Kitty CLI workflows are accessible via MCP tools with 100% functional parity
- **SC-004**: The server successfully manages at least 3 concurrent projects without state corruption or cross-project interference
- **SC-005**: File operations on `.kittify/` directories complete without conflicts when multiple clients operate on different work packages simultaneously
- **SC-006**: 95% of conversational commands are correctly interpreted and routed to the appropriate tool without requiring clarification
- **SC-007**: Server startup completes within 2 seconds (manual start by user) and tool invocation latency is under 500ms for read operations
- **SC-008**: Conversation state persists indefinitely in project-local storage, allowing users to resume interrupted workflows at any time (not limited to 24 hours)
- **SC-009**: Error messages provide actionable guidance (e.g., "missing dependency", "invalid project structure") with suggested remediation steps
- **SC-010**: The server handles 100 concurrent MCP requests without degradation in response time or accuracy
- **SC-011**: Core workflow modifications (bug fixes, feature enhancements) in the CLI codebase automatically benefit the MCP interface without requiring parallel changes to MCP tool implementations
