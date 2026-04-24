from runtime.seams.presentation_sink import PresentationSink


class NullSink:
    """No-op PresentationSink for use in tests and offline contexts."""

    def write_line(self, text: str) -> None:
        pass

    def write_status(self, message: str) -> None:
        pass

    def write_json(self, data: object) -> None:
        pass


assert isinstance(NullSink(), PresentationSink)  # structural check
