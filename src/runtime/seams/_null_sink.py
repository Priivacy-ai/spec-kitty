from runtime.seams.presentation_sink import PresentationSink


class NullSink:
    """No-op PresentationSink for use in tests and offline contexts."""

    def write_line(self, text: str) -> None:
        """Discard `text`. Intentional no-op — see class docstring."""

    def write_status(self, message: str) -> None:
        """Discard `message`. Intentional no-op — see class docstring."""

    def write_json(self, data: object) -> None:
        """Discard `data`. Intentional no-op — see class docstring."""


assert isinstance(NullSink(), PresentationSink)  # structural check
