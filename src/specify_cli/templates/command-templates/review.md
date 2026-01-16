---
description: Perform structured code review and kanban transitions for completed task prompt files.
scripts:
  sh: spec-kitty agent check-prerequisites --json --include-tasks
  ps: spec-kitty agent -Json -IncludeTasks
---
*Path: [templates/commands/review.md](templates/commands/review.md)*


## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Location Pre-flight Check (CRITICAL for AI Agents)

Before proceeding with review, verify you are in the correct working directory by running the shared pre-flight validation:

```python
```

**What this validates**:
- Current branch follows the feature pattern like `001-feature-name`
- You're not attempting to run from `main` or any release branch
- The validator prints clear navigation instructions if you're outside the feature worktree

**Path reference rule:** When you mention directories or files, provide either the absolute path or a path relative to the project root (for example, `kitty-specs/<feature>/tasks/`). Never refer to a folder by name alone.

This is intentional - worktrees provide isolation for parallel feature development.

## Outline

1. Run `{SCRIPT}` from repo root; capture `FEATURE_DIR`, `AVAILABLE_DOCS`, and `tasks.md` path.

2. Determine the review target:
   - If user input specifies a filename, validate it exists under `tasks/` (flat structure, check `lane: "for_review"` in frontmatter).
   - Otherwise, select the oldest file in `tasks/` (lexical order is sufficient because filenames retain task ordering).
   - Abort with instructional message if no files are waiting for review.

3. Load context for the selected task:
   - Read the prompt file frontmatter (lane MUST be `for_review`); note `task_id`, `phase`, `agent`, `shell_pid`, and `dependencies` (if present).
   - Read the body sections (Objective, Context, Implementation Guidance, etc.).
   - Consult supporting documents as referenced: constitution, plan, spec, data-model, contracts, research, quickstart, code changes.
   - Review the associated code in the repository (diffs, tests, docs) to validate the implementation.
   - **Workspace-per-WP checks** (v0.11.0+):
     * dependency_check: If this WP has `dependencies: [WP##, ...]` in frontmatter, verify each dependency WP is merged to main before review; confirm your branch includes those commits.
     * dependent_check: Identify any WPs that list this WP as a dependency (scan `tasks/*.md`); list them with their current lane.
     * rebase_warning: If you request changes AND any dependents exist, warn those agents that a rebase is required and provide a concrete rebase command.
     * verify_instruction: Cross-check dependency declarations against actual code coupling (imports, shared modules, API contracts) and flag mismatches.

4. Conduct the review with **adversarial mindset**:

   **CRITICAL**: Your job is to FIND PROBLEMS, not just verify checkboxes. Assume the implementation has issues until proven otherwise.

   ### 4.1 Completeness Scrutiny

   **Beyond checkbox-ticking:**
   - [ ] ALL subtasks from the prompt actually implemented (not just mentioned in comments)
   - [ ] ALL acceptance criteria from spec actually satisfied (test them, don't assume)
   - [ ] ALL files mentioned in prompt actually created/modified (grep to verify)
   - [ ] ALL error cases handled (not just happy path)
   - [ ] ALL edge cases from spec addressed (check the "Edge Cases" section)

   **Red flags**:
   - ❌ Comments saying "TODO: implement X" or "FIXME: handle Y"
   - ❌ Functions that return hardcoded/mock data instead of real implementation
   - ❌ Tests that pass but don't actually validate the requirement
   - ❌ Incomplete error messages ("Error occurred" instead of actionable detail)
   - ❌ Missing validation for user input or external data
   - ❌ Deferred features ("will implement in future PR")

   ### 4.2 Implementation Quality Scrutiny

   **Code actually works:**
   - [ ] Run the actual code (don't just read it) - does it execute without errors?
   - [ ] Test with invalid inputs - does it fail gracefully with helpful errors?
   - [ ] Check return values - are they the actual result or mocked placeholders?
   - [ ] Verify database/file operations - are changes persisted or just in-memory?
   - [ ] Check API calls - do they actually call the API or return fake data?

   **Anti-patterns to reject:**
   - ❌ **Simulated results**: `return {"status": "success", "data": "simulated"}`
   - ❌ **Mock implementations**: `def fetch_data(): return []  # TODO: implement API call`
   - ❌ **Pass-through functions**: `def process(x): return x  # Will add validation later`
   - ❌ **Commented-out logic**: `# This should validate input but skipping for now`
   - ❌ **Empty exception handlers**: `except Exception: pass  # Ignoring errors`

   ### 4.3 Efficiency & Performance Scrutiny

   **Implementation is efficient, not just correct:**
   - [ ] No O(n²) algorithms where O(n) or O(log n) possible
   - [ ] No redundant file reads (read once, cache if needed)
   - [ ] No unnecessary subprocess calls (use library if available)
   - [ ] No polling when event-driven approach possible
   - [ ] No synchronous blocking when async available (if performance-critical)

   **Red flags**:
   - ❌ Nested loops over large datasets without justification
   - ❌ Reading same file multiple times in a loop
   - ❌ Running same grep/find command repeatedly
   - ❌ `time.sleep()` in loops without exponential backoff
   - ❌ Loading entire dataset into memory when streaming possible

   ### 4.4 Test Quality Scrutiny

   **Tests actually validate requirements, not just pass:**
   - [ ] Tests cover failure cases, not just happy path
   - [ ] Tests use real data, not just `test_value = "test"`
   - [ ] Tests verify behavior, not implementation details
   - [ ] Test names describe WHAT is being tested, not HOW
   - [ ] Assertions check meaningful outcomes, not just "no exception raised"

   **Red flags**:
   - ❌ Tests that always pass (assert True, assert 1 == 1)
   - ❌ Tests with no assertions
   - ❌ Tests that don't actually call the code being tested
   - ❌ Mock-heavy tests that don't validate real behavior
   - ❌ Tests marked skip/xfail without explanation

   ### 4.5 Error Handling & Robustness Scrutiny

   **Code fails safely and informatively:**
   - [ ] All external calls wrapped in try/except with specific exceptions
   - [ ] Error messages are actionable (tell user what to do)
   - [ ] Resource cleanup happens even on error (files closed, connections released)
   - [ ] Invalid input rejected with clear validation errors
   - [ ] Edge cases explicitly handled (empty lists, None values, zero-length strings)

   **Red flags**:
   - ❌ `except Exception: pass` (swallowing all errors)
   - ❌ Generic error messages ("An error occurred")
   - ❌ No cleanup in exception handlers (file handles leaked)
   - ❌ Assumptions about input validity without validation
   - ❌ No fallback behavior when external service fails

   ### 4.6 Cross-Platform Compatibility Scrutiny

   **Code works on Linux, macOS, AND Windows:**
   - [ ] Path operations use `pathlib.Path`, not string concatenation
   - [ ] No hardcoded `/` or `\` in paths
   - [ ] No POSIX-only commands (grep, find, lsof) without Windows alternatives
   - [ ] No assumptions about line endings (use universal newlines)
   - [ ] No assumptions about case sensitivity (macOS insensitive, Linux sensitive)

   **Red flags**:
   - ❌ `os.path.join` with `/` hardcoded
   - ❌ Shell commands without platform detection
   - ❌ Signal handling without Windows compatibility (signal.SIGKILL, etc.)
   - ❌ File permissions logic that assumes POSIX
   - ❌ Symlinks without fallback for Windows

   ### 4.7 Security Scrutiny (CRITICAL - ALWAYS CHECK)

   **Treat every implementation as potentially vulnerable until proven secure.**

   #### 4.7.1 Injection Vulnerabilities

   **SQL Injection:**
   - [ ] All database queries use parameterized queries/ORMs (NEVER string concatenation)
   - [ ] No `f"SELECT * FROM {table}"` or similar patterns
   - [ ] Table/column names validated against whitelist if user-provided

   **Command Injection:**
   - [ ] All shell commands use list form: `["ls", "-la", user_file]` not `f"ls -la {user_file}"`
   - [ ] No `os.system(f"rm {path}")` or `subprocess.run(f"git commit -m '{msg}'")`
   - [ ] User input to shell commands validated/escaped
   - [ ] Subprocess calls use `shell=False` (default)

   **Path Traversal:**
   - [ ] File paths validated before access (no `../../../etc/passwd`)
   - [ ] Paths resolved and checked: `Path(user_input).resolve()` stays within allowed directory
   - [ ] No direct concatenation: `f"{base_dir}/{user_file}"` → use `Path(base_dir) / sanitize(user_file)`

   **Template Injection:**
   - [ ] User input in templates is escaped
   - [ ] No `eval()`, `exec()`, `compile()` on user data
   - [ ] YAML/JSON parsing uses safe loaders (yaml.safe_load, not yaml.load)

   **Red flags:**
   - ❌ `f"SELECT * FROM users WHERE name = '{user_input}'"`
   - ❌ `subprocess.run(f"git clone {url}", shell=True)`
   - ❌ `open(f"data/{user_filename}")` without path validation
   - ❌ `yaml.load()` instead of `yaml.safe_load()`
   - ❌ `eval(user_expression)` or `exec(user_code)`

   #### 4.7.2 Authentication & Authorization

   **If code handles auth/authz:**
   - [ ] Authentication required before privileged operations
   - [ ] Authorization checked (not just authentication)
   - [ ] Session tokens cryptographically secure (not guessable)
   - [ ] No hardcoded credentials or API keys
   - [ ] Password hashing uses modern algorithms (bcrypt, argon2, scrypt)

   **Red flags:**
   - ❌ `if username == "admin":` (no password check)
   - ❌ `token = "secret123"` hardcoded
   - ❌ `hashlib.md5(password)` or `hashlib.sha1(password)` for passwords
   - ❌ Predictable tokens: `token = str(user_id) + timestamp`
   - ❌ No authorization: user A can access user B's data

   #### 4.7.3 Sensitive Data Handling

   **Secrets must never leak:**
   - [ ] No passwords/tokens/keys in logs, error messages, or stack traces
   - [ ] No secrets in git commits (even in test data)
   - [ ] Environment variables used for secrets, not config files
   - [ ] Secrets redacted in debug output: `password=***` not `password=hunter2`
   - [ ] No secrets in URLs (query parameters logged by proxies)

   **Red flags:**
   - ❌ `logger.info(f"Connecting with password: {password}")`
   - ❌ `config.yaml` containing `api_key: sk-abc123...`
   - ❌ `print(f"Token: {token}")` in production code
   - ❌ Exception messages exposing tokens: `"API call failed with key {api_key}"`
   - ❌ `url = f"https://api.com?secret={secret}"` (secrets in URLs)

   #### 4.7.4 Data Validation & Sanitization

   **Never trust user input:**
   - [ ] All user input validated against expected format
   - [ ] String lengths limited (prevent DoS via huge inputs)
   - [ ] Numeric values range-checked
   - [ ] File uploads validated (type, size, content)
   - [ ] URLs validated and normalized before use

   **Red flags:**
   - ❌ No validation: `user_age = int(request.get('age'))` (what if negative? 99999999?)
   - ❌ No length limits: `name = input()` (what if 1GB string?)
   - ❌ No type validation: assuming input is string when could be list/dict
   - ❌ No allowlist: accepting any file extension instead of specific types
   - ❌ Trusting client-side validation (always validate server-side)

   #### 4.7.5 File System Security

   **File operations must be safe:**
   - [ ] File permissions set appropriately (not world-readable for sensitive files)
   - [ ] Temp files created securely (`tempfile.NamedTemporaryFile`, not `/tmp/predictable`)
   - [ ] File deletions validated (not deleting outside project)
   - [ ] Symlink attacks prevented (resolve symlinks before security checks)
   - [ ] Race conditions prevented (TOCTOU: time-of-check vs time-of-use)

   **Red flags:**
   - ❌ `open("/tmp/myapp_123", "w")` (predictable temp file)
   - ❌ `os.chmod(file, 0o777)` (world-writable)
   - ❌ `if os.path.exists(file): os.remove(file)` (race condition)
   - ❌ Not checking if path is symlink before security checks
   - ❌ Following symlinks without validating destination

   #### 4.7.6 Dependency Security

   **Dependencies must be trustworthy:**
   - [ ] All dependencies pinned or have minimum version (no `package` without version)
   - [ ] No suspicious/unmaintained packages (check PyPI, npm, etc.)
   - [ ] Dependency licenses compatible with project
   - [ ] No dependencies with known vulnerabilities (check CVE databases)
   - [ ] Minimal dependency set (fewer dependencies = smaller attack surface)

   **Red flags:**
   - ❌ `dependencies = ["some-random-package"]` (no version, unknown maintainer)
   - ❌ Adding dependency for feature that could be implemented in 10 lines
   - ❌ Using deprecated packages with security vulnerabilities
   - ❌ Transitive dependencies not reviewed

   #### 4.7.7 Cryptography (If Applicable)

   **Crypto must be correct:**
   - [ ] Using established libraries (cryptography, nacl), not rolling own
   - [ ] Using modern algorithms (AES-256-GCM, ChaCha20-Poly1305)
   - [ ] Random values use `secrets` module, not `random`
   - [ ] No weak algorithms (MD5, SHA1 for security, DES, RC4)
   - [ ] Proper key management (keys not hardcoded)

   **Red flags:**
   - ❌ `random.randint()` for security tokens (use `secrets.token_bytes()`)
   - ❌ Implementing own encryption algorithm
   - ❌ `hashlib.md5()` for password hashing (use bcrypt/argon2)
   - ❌ Keys in code: `AES_KEY = b"sixteen byte key"`
   - ❌ Using ECB mode (use GCM or CBC with authentication)

   #### 4.7.8 API Security (If Applicable)

   **APIs must be secure:**
   - [ ] Authentication required for non-public endpoints
   - [ ] Rate limiting implemented (prevent abuse)
   - [ ] CORS configured properly (not `allow-origin: *` in production)
   - [ ] Input validated at API boundary
   - [ ] Output doesn't leak sensitive info in error messages

   **Red flags:**
   - ❌ No authentication on sensitive endpoints
   - ❌ No rate limiting (API can be DoS'd)
   - ❌ `Access-Control-Allow-Origin: *` with credentials
   - ❌ Detailed error messages exposing internals: `"SQL error: table users not found"`
   - ❌ No input size limits (can send 1GB JSON)

   #### 4.7.9 Privilege & Permission Issues

   **Principle of least privilege:**
   - [ ] Code runs with minimum required permissions
   - [ ] No unnecessary sudo/admin rights required
   - [ ] Privilege escalation only when absolutely needed and validated
   - [ ] No SUID binaries or equivalent
   - [ ] File operations respect user permissions

   **Red flags:**
   - ❌ Requiring sudo when not needed
   - ❌ Creating world-writable files
   - ❌ Assuming root/admin privileges
   - ❌ Not checking permissions before operations
   - ❌ Privilege escalation without user confirmation

   #### 4.7.10 Mandatory Security Verification Commands

   **For EVERY work package, run these checks:**

   ```bash
   # 1. Injection check
   grep -rn "subprocess.run.*shell=True" <files>
   grep -rn 'f".*{.*}"' <files> | grep -i "select\|insert\|delete\|update\|exec\|eval"
   # Expected: Empty or justified

   # 2. Secret exposure check
   git diff | grep -i "password\|secret\|token\|api_key" | grep -v "# "
   # Expected: Empty or all in test fixtures/examples

   # 3. Unsafe operations check
   grep -rn "rm -rf\|shutil.rmtree\|os.remove" <files>
   # Verify: All have path validation before deletion

   # 4. Crypto check
   grep -rn "random\.\|md5\|sha1" <files>
   # Verify: Using secrets module for security, not random

   # 5. Exception handling check
   grep -rn "except.*:$" <files> | grep -v "pass  #"
   # Verify: All have comments explaining why catching broad exception

   # 6. Eval/exec check
   grep -rn "eval\|exec\|compile" <files>
   # Expected: Empty unless absolutely necessary and input validated

   # 7. YAML safety check
   grep -rn "yaml\.load[^_]" <files>
   # Expected: Empty (should use yaml.safe_load)
   ```

   **If ANY security check fails → AUTOMATIC REJECTION**

   ### 4.8 Logical Fallacies & Design Flaws Scrutiny

   **Design makes sense, logic is sound:**
   - [ ] No circular dependencies (A depends on B depends on A)
   - [ ] No race conditions (proper locking/synchronization)
   - [ ] No assumption that operations are atomic when they're not
   - [ ] No missing null checks before dereferencing
   - [ ] State management is consistent (no orphaned state)

   **Red flags**:
   - ❌ `if x is not None: x.method()` after code that could set x = None
   - ❌ Checking file exists, then reading (race condition)
   - ❌ Multiple processes modifying same file without locking
   - ❌ Assuming list is non-empty without checking
   - ❌ Using mutable default arguments: `def foo(items=[]):`

   ### 4.9 Documentation & Maintainability Scrutiny

   **Code is understandable and maintainable:**
   - [ ] Complex logic has explanatory comments (why, not what)
   - [ ] Public functions have docstrings with examples
   - [ ] Magic numbers replaced with named constants
   - [ ] Cryptic variable names replaced with descriptive ones
   - [ ] Non-obvious behavior documented

   **Red flags**:
   - ❌ Functions longer than 50 lines without clear sections
   - ❌ No docstrings on public APIs
   - ❌ Magic numbers: `if count > 42:` without explanation
   - ❌ Single-letter variables in complex logic: `x`, `y`, `z`
   - ❌ Surprising behavior not documented

   ### 4.10 Verification Commands (ACTUALLY RUN THESE)

   **Don't assume - verify:**
   ```bash
   # 1. Grep for red flags
   grep -rn "TODO\|FIXME\|HACK\|XXX" <changed_files>
   grep -rn "simulated\|mock_\|fake_" <changed_files>
   grep -rn "pass  # " <changed_files>  # Empty exception handlers

   # 2. Run tests (actually execute, don't just check they exist)
   pytest <test_files> -v --tb=short
   # Verify: All pass, coverage >80%, no skipped tests

   # 3. Run linter (check code quality)
   ruff check <changed_files>
   # Verify: No errors, minimal warnings

   # 4. Test actual behavior (not just unit tests)
   # Example: If implementing file sync, create file, sync, verify synced
   # Example: If implementing dashboard, start it, access URL, verify response

   # 5. Check for performance issues
   grep -rn "sleep\|time.sleep" <changed_files>
   # Justify each sleep - is it necessary or lazy coding?

   # 6. Check error handling
   grep -rn "except.*:" <changed_files>
   # Each exception handler should be specific, not generic

   # 7. Verify documentation updated
   # If README/docs mention this feature, verify they're current
   ```

   ### 4.11 Adversarial Test Cases

   **Think like an attacker/user trying to break it:**
   - Run with empty input - does it crash or handle gracefully?
   - Run with extremely large input - does it OOM or handle gracefully?
   - Run with malicious input - does it validate/escape properly?
   - Run with missing dependencies - does it provide helpful error?
   - Run concurrent operations - does it handle race conditions?
   - Run on different platforms - does it work on all target platforms?
   - Kill process mid-operation - is state left in consistent state?

   ### 4.12 Review Decision Criteria

   **REJECT (send back to planned) if ANY of these:**
   - Any TODOs/FIXMEs in production code (tests OK)
   - Any simulated/mocked functionality (except in tests)
   - Any empty exception handlers without justification
   - Tests don't actually run the code or use mocks everywhere
   - Missing error handling for external operations (file I/O, network, subprocess)
   - Performance issue that will cause problems at scale
   - Security vulnerability (injection, data exposure, unsafe operations)
   - Cross-platform issue on target platforms
   - Incomplete implementation of stated requirements
   - Logical flaw or race condition

   **APPROVE ONLY if ALL of these:**
   - Every subtask fully implemented (no shortcuts)
   - All tests pass and actually validate behavior
   - Error handling comprehensive and helpful
   - No performance red flags or justified if present
   - No security issues (ran all security checks in 4.7.10)
   - Works on all target platforms (or platform-specific code isolated)
   - Code is maintainable and documented
   - No logical flaws or race conditions
   - All verification commands (4.10) executed and passed

   **Default stance: REJECT.** Only approve when you've actively tried to find problems and found none. "Looks good" is not good enough - you must prove it's good.

5. Decide outcome:
  - **Needs changes**:
     * **CRITICAL**: Insert detailed feedback in the `## Review Feedback` section (located immediately after the frontmatter, before Objectives). This is the FIRST thing implementers will see when they re-read the prompt.
     * Use a clear structure:
       ```markdown
       ## Review Feedback

       **Status**: ❌ **Needs Changes**

       **Key Issues**:
       1. [Issue 1] - Why it's a problem and what to do about it
       2. [Issue 2] - Why it's a problem and what to do about it

       **What Was Done Well**:
       - [Positive note 1]
       - [Positive note 2]

       **Action Items** (must complete before re-review):
       - [ ] Fix [specific thing 1]
       - [ ] Add [missing thing 2]
       - [ ] Verify [validation point 3]
       ```
     * Update frontmatter:
       - Set `lane: "planned"`
       - Set `review_status: "has_feedback"`
       - Set `reviewed_by: <YOUR_AGENT_ID>`
       - Clear `assignee` if needed
     * Append a new entry in the prompt's **Activity Log** with timestamp, reviewer agent, shell PID, and summary of feedback.
     * Run `spec-kitty agent move-task <FEATURE> <TASK_ID> planned --note "Code review complete: [brief summary of issues]"` (use the PowerShell equivalent on Windows) so the move and history update are staged consistently.
  - **Approved**:
     * Append Activity Log entry capturing approval details (capture shell PID via `echo $$` or helper script, e.g., `2025-11-11T13:45:00Z – claude – shell_pid=1234 – lane=done – Approved without changes`).
     * Update frontmatter:
       - Sets `lane: "done"`
       - Sets `review_status: "approved without changes"` (or your custom status)
       - Sets `reviewed_by: <YOUR_AGENT_ID>`
       - Updates `agent: <YOUR_AGENT_ID>` and `shell_pid: <YOUR_SHELL_PID>`
       - Appends Activity Log entry with reviewer's info (NOT implementer's)
       - Handles git operations (add new location, remove old location)
     * **Alternative:** For custom review statuses, use `--review-status "approved with minor notes"` or `--target-lane "planned"` for rejected tasks.
     * Use helper script to mark the task complete in `tasks.md` (see Step 7).

7. Update `tasks.md` automatically:
   - Run `spec-kitty agent mark-status --task-id <TASK_ID> --status done` (POSIX) or `spec-kitty agent -TaskId <TASK_ID> -Status done` (PowerShell) from repo root.
   - Confirm the task entry now shows `[X]` and includes a reference to the prompt file in its notes.

7. Produce a review report summarizing:
   - Task ID and filename reviewed.
  - Approval status and key findings.
   - Tests executed and their results.
   - Follow-up actions (if any) for other team members.
   - Reminder to push changes or notify teammates as per project conventions.

Context for review: {ARGS} (resolve this to the prompt's relative path, e.g., `kitty-specs/<feature>/tasks/WPXX.md`)

All review feedback must live inside the prompt file, ensuring future implementers understand historical decisions before revisiting the task.
