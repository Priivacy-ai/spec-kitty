# Quickstart: MCP Server for Conversational Spec Kitty Workflow

**Feature**: 099-mcp-server-for-conversational-spec-kitty-workflow  
**Date**: 2026-01-29  
**Purpose**: Get started with the Spec Kitty MCP server in minutes

## Prerequisites

- Python 3.11+ installed
- spec-kitty CLI installed (`pip install spec-kitty-cli`)
- A Spec Kitty project initialized (or create one with `spec-kitty init`)
- An MCP-compatible AI client (Claude Desktop, Cursor, etc.)

## Installation

The MCP server is included with spec-kitty. No additional installation required.

```bash
# Verify installation
spec-kitty --version

# Check MCP server command availability
spec-kitty mcp --help
```

## Server Startup

### Basic Startup (No Authentication)

```bash
# Start server on default port (8000)
spec-kitty mcp start

# Server output:
# ✓ MCP Server started
#   Host: 127.0.0.1
#   Port: 8000
#   Auth: disabled
#   Transport: stdio
# 
# Ready to accept MCP connections...
```

### With Authentication

```bash
# Generate API key
export SPEC_KITTY_MCP_API_KEY="your-secret-key-here"

# Start server with auth enabled
spec-kitty mcp start --auth

# Server output:
# ✓ MCP Server started
#   Host: 127.0.0.1
#   Port: 8000
#   Auth: enabled
#   Transport: stdio
#
# ⚠️  API Key required for all connections
```

### Custom Port

```bash
# Use different port
spec-kitty mcp start --port 9000
```

### Server Lifecycle

```bash
# Stop server: Press Ctrl+C in terminal
# Server will gracefully shut down, releasing all locks

# Check server health (from another terminal)
curl http://localhost:8000/health

# Response:
# {"status": "healthy", "version": "0.12.0", "active_projects": 2}
```

## MCP Client Configuration

### Claude Desktop

Add to `~/.config/claude/config.json` (macOS/Linux) or `%APPDATA%\Claude\config.json` (Windows):

```json
{
  "mcpServers": {
    "spec-kitty": {
      "command": "spec-kitty",
      "args": ["mcp", "start", "--transport", "stdio"],
      "env": {
        "SPEC_KITTY_MCP_API_KEY": "your-api-key-if-auth-enabled"
      }
    }
  }
}
```

**Without Authentication**:
```json
{
  "mcpServers": {
    "spec-kitty": {
      "command": "spec-kitty",
      "args": ["mcp", "start", "--transport", "stdio"]
    }
  }
}
```

### Cursor

Add to `.cursor/mcp.json` in your project:

```json
{
  "mcpServers": {
    "spec-kitty": {
      "command": "spec-kitty",
      "args": ["mcp", "start", "--transport", "stdio"],
      "env": {
        "SPEC_KITTY_MCP_API_KEY": "your-api-key-if-auth-enabled"
      }
    }
  }
}
```

### Other MCP Clients

Any MCP-compatible client can connect using:
- **Command**: `spec-kitty mcp start --transport stdio`
- **Protocol**: MCP over stdio
- **Environment**: Set `SPEC_KITTY_MCP_API_KEY` if auth enabled

## First Tool Invocation

### Example 1: Create a Feature Specification

**In Claude/Cursor (natural language)**:
```
In project /Users/me/my-project, I want to create a feature for user authentication with email and password.
```

**Behind the scenes (MCP tool call)**:
```json
{
  "tool": "feature_operations",
  "parameters": {
    "project_path": "/Users/me/my-project",
    "operation": "specify",
    "arguments": {
      "description": "user authentication with email and password"
    }
  }
}
```

**Expected Response**:
```
✓ Feature specification created: 099-user-authentication-example
  Spec file: /Users/me/my-project/kitty-specs/099-user-authentication-example/spec.md

I've created a specification for user authentication. The discovery interview gathered:
- Authentication methods: email/password
- User roles: end user, admin
- Security requirements: password hashing, session management

Would you like to proceed with creating a technical plan?
```

### Example 2: List Tasks

**Natural language**:
```
In project /Users/me/my-project, show me the tasks for feature 099-user-authentication-example
```

**MCP tool call**:
```json
{
  "tool": "task_operations",
  "parameters": {
    "project_path": "/Users/me/my-project",
    "operation": "list_tasks",
    "feature_slug": "099-user-authentication-example"
  }
}
```

**Response**:
```
Tasks for 099-user-authentication-example:

Planned (2):
- WP01: Database schema for users table
- WP02: Password hashing and validation

Doing (1):
- WP03: Session management endpoints

For Review (0):
(none)

Done (0):
(none)
```

### Example 3: Move Task to Review

**Natural language**:
```
In project /Users/me/my-project, WP03 is ready for review
```

**MCP tool call**:
```json
{
  "tool": "task_operations",
  "parameters": {
    "project_path": "/Users/me/my-project",
    "operation": "move_task",
    "feature_slug": "099-user-authentication-example",
    "task_id": "WP03",
    "lane": "for_review"
  }
}
```

**Response**:
```
✓ Task WP03 moved to for_review lane
  Updated: kitty-specs/099-user-authentication-example/tasks/WP03.md
  Activity log updated with timestamp
```

## Multi-Project Setup

The MCP server manages multiple projects simultaneously. Specify project path in each request:

**Example**:
```
In project /Users/me/project-a, show features
In project /Users/me/project-b, create a feature for payment processing
```

The server validates each project path and operates on the correct `.kittify/` directory.

## Authentication Configuration

### Enabling Authentication

```bash
# Generate a secure API key
API_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

# Save to environment
export SPEC_KITTY_MCP_API_KEY="$API_KEY"

# Start server with auth
spec-kitty mcp start --auth
```

### Disabling Authentication (Local Development)

```bash
# Start without --auth flag
spec-kitty mcp start
```

**Security Note**: Only disable authentication on trusted local machines. Enable auth if server is accessible over network.

### Rotating API Key

```bash
# Generate new key
NEW_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

# Update environment
export SPEC_KITTY_MCP_API_KEY="$NEW_KEY"

# Restart server
# (Ctrl+C to stop, then `spec-kitty mcp start --auth`)

# Update MCP client configuration with new key
```

## Troubleshooting

### Port Already in Use

**Error**: `Address already in use: port 8000`

**Solution**:
```bash
# Use different port
spec-kitty mcp start --port 9000

# Or kill process using port 8000
lsof -ti:8000 | xargs kill -9
```

### Lock Timeout

**Error**: `Resource WP01 is currently locked by another client`

**Solution**:
- Wait 5 minutes for lock to timeout automatically
- Or manually remove stale lock file:
  ```bash
  rm /path/to/project/.kittify/.lock-WP01
  ```

### Session Resumption Not Working

**Problem**: Server doesn't remember previous conversation context

**Check**:
1. Verify session files exist:
   ```bash
   ls -la /path/to/project/.kittify/mcp-sessions/
   ```
2. Check MCP client is passing `session_id` in requests
3. Verify session JSON is valid:
   ```bash
   cat /path/to/project/.kittify/mcp-sessions/<session-id>.json | jq .
   ```

**Fix**:
- If session file corrupted, delete it and start new session
- If session_id not passed, update MCP client to include it

### Project Not Found

**Error**: `Project path does not contain .kittify/ directory`

**Solution**:
1. Verify project is initialized:
   ```bash
   ls -la /path/to/project/.kittify/
   ```
2. If missing, initialize project:
   ```bash
   cd /path/to/project
   spec-kitty init
   ```
3. Use absolute path in MCP requests (not relative)

### Authentication Failure

**Error**: `Authentication required. Please configure your MCP client with a valid API key.`

**Solution**:
1. Verify API key is set in environment:
   ```bash
   echo $SPEC_KITTY_MCP_API_KEY
   ```
2. Update MCP client config with correct key
3. Restart MCP client to pick up new environment variable

## Advanced Usage

### Health Check Endpoint

```bash
# Check server status
curl http://localhost:8000/health

# Response:
{
  "status": "healthy",
  "version": "0.12.0",
  "active_projects": 3,
  "uptime_seconds": 3600
}
```

### List Available Tools

From MCP client, discover available tools:

```
List available spec-kitty tools
```

**Response**:
```
Available tools:
1. feature_operations - Execute Spec Kitty feature workflow operations
2. task_operations - Manage work package tasks and lanes
3. workspace_operations - Create and manage git worktrees for work packages
4. system_operations - Server health, project validation, and configuration
```

### Server Configuration

Check current server configuration:

```json
{
  "tool": "system_operations",
  "parameters": {
    "operation": "server_config"
  }
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "host": "127.0.0.1",
    "port": 8000,
    "auth_enabled": false,
    "transport": "stdio",
    "lock_timeout_seconds": 300,
    "active_projects": 3
  }
}
```

## Next Steps

1. **Explore workflows**: Try creating features, planning, and managing tasks via conversation
2. **Test multi-turn conversations**: Start a feature specification and observe session persistence
3. **Manage multiple projects**: Switch between projects by specifying different paths
4. **Review logs**: Check server logs for debugging (if implemented)
5. **Read documentation**: See [data-model.md](data-model.md) for entity details, [research.md](research.md) for implementation patterns

## Support

For issues or questions:
- Check troubleshooting section above
- Review [spec.md](spec.md) for requirements and edge cases
- Inspect `.kittify/mcp-sessions/` for session state
- Check lock files in `.kittify/.lock-*` for concurrency issues
