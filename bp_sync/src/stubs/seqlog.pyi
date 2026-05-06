from logging import Handler

class SeqLogHandler(Handler):
    def __init__(
        self,
        server_url: str,
        api_key: str | None = None,
        batch_size: int = 10,
        auto_flush_timeout: float = 1.0,
    ) -> None: ...
