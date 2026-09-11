"""Logical publisher identity shared by command and reader processes.

A harness can export SPEC_KITTY_ZEITGEIST_SESSION_ID to join its subprocesses.
Codex's thread identifier provides that boundary automatically. Unidentified
processes remain distinct. This selector is not the relay's opaque session_ref:
publication uses the raw session reference returned by the SaaS lease issuer.
"""

from __future__ import annotations

import hashlib
import os
import re
import uuid

_SESSION_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
_PROCESS_NAMESPACE = uuid.uuid4()


def logical_session_id() -> str:
    """Return the current logical agent selector, refusing malformed overrides."""
    explicit = os.environ.get("SPEC_KITTY_ZEITGEIST_SESSION_ID")
    if explicit is not None:
        if not _SESSION_PATTERN.fullmatch(explicit):
            raise ValueError("SPEC_KITTY_ZEITGEIST_SESSION_ID must be a 1-128 character ASCII identifier")
        return explicit
    thread = os.environ.get("CODEX_THREAD_ID")
    if thread:
        # Namespace a harness-local selector; never derive a relay egress ref.
        return "codex-" + hashlib.sha256(thread.encode()).hexdigest()  # noqa: TID251 -- harness identity, not charter hashing
    # A fork inherits the namespace but has a different PID. Computing the
    # value avoids lazy-initialization races between fan-out threads.
    return uuid.uuid5(_PROCESS_NAMESPACE, str(os.getpid())).hex
