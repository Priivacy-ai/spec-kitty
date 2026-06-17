"""Topology-true characterization net for the write-side context-factory adoption.

Mission B (``write-side-context-factory-adoption-01KV9W0X``) WP01 — the
*clean-before-touch* gate (D-9 / IC-CHARNET). Every later adoption WP proves
itself by **deleting** an inline re-derivation and showing this net stays green
(NFR-003, verification-by-deletion). The fixtures here are reused by every
downstream adoption WP and by WP08's keystone — they are built once, real, and
topology-true (NFR-002): full 26-char ULID ``mission_id``, a REAL coordination
``git worktree``, and a REAL git submodule (``.git`` *file*).

The binding design rule (paula's live-evidence trap, A-1/B-3): the net drives
the write sites **without** an explicit ``repo_root=`` and **without** mocking
the root/surface, from a non-primary CWD, so the re-derivation arm the adoption
deletes is actually exercised. A test that passes ``repo_root=`` is blind to the
swap and is worthless here.
"""
