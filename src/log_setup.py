import logging
import sys

import structlog


def setup_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
    )
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="%H:%M:%S"),
            structlog.processors.StackInfoRenderer(),
            structlog.dev.ConsoleRenderer(colors=True),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
