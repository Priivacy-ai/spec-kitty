"""Shared exceptions for the doctrine package."""


class DoctrineArtifactLoadError(Exception):
    """Raised when a doctrine artifact file cannot be loaded or parsed.

    Used when YAML is malformed or the file content is not a valid dict.
    Callers that load artifact directories should catch this and continue,
    issuing a warning rather than aborting the full load.
    """


class DoctrineResolutionCycleError(Exception):
    """Raised when a cycle is detected in doctrine artifact references.

    A cycle in the reference graph (e.g. Tactic A → Tactic B → Tactic A)
    would cause infinite resolution loops and is always a configuration error.

    Attributes:
        cycle: Ordered list of (artifact_type, artifact_id) tuples forming the cycle.
    """

    def __init__(self, cycle: list[tuple[str, str]]) -> None:
        self.cycle = cycle
        path_str = " → ".join(f"{t}/{i}" for t, i in cycle)
        super().__init__(f"Cycle detected in doctrine artifact references: {path_str}")
