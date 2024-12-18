from __future__ import annotations

import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional

import structlog


class OrchestrationLogger:
    def __init__(
        self,
        service_name: str = "orchestrator",
        env: str = "development",
        log_level: str = "INFO",
        json_output: bool = False,
        extra_processors: Optional[list] = None,
    ):
        self.service_name = service_name
        self.env = env
        self.log_level = log_level
        self.json_output = json_output

        # Configure standard logging
        logging.basicConfig(
            format="%(message)s",
            stream=sys.stdout,
            level=getattr(logging, log_level.upper()),
        )

        shared_processors = [
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
        ]

        if json_output:
            formatter = structlog.processors.JSONRenderer()
        else:
            formatter = structlog.dev.ConsoleRenderer(colors=True)

        structlog.configure(
            processors=shared_processors + [formatter],
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            cache_logger_on_first_use=True,
        )

        self.logger = structlog.get_logger(self.service_name, env=self.env)

    def get_logger(
        self, context: Optional[Dict[str, Any]] = None
    ) -> structlog.BoundLogger:
        """Get a logger instance with optional additional context."""
        if context:
            return self.logger.bind(**context)
        return self.logger

    @staticmethod
    def add_event_context(
        logger: structlog.BoundLogger, event_id: str, event_type: str
    ) -> structlog.BoundLogger:
        """Add event-specific context to a logger instance."""
        return logger.bind(
            event_id=event_id,
            event_type=event_type,
            event_timestamp=datetime.utcnow().isoformat(),
        )

    @staticmethod
    def add_task_context(
        logger: structlog.BoundLogger, task_id: str, task_name: str
    ) -> structlog.BoundLogger:
        """Add task-specific context to a logger instance."""
        return logger.bind(task_id=task_id, task_name=task_name)

    @staticmethod
    def add_pipeline_context(
        logger: structlog.BoundLogger, pipeline_id: str, pipeline_name: str
    ) -> structlog.BoundLogger:
        """Add pipeline-specific context to a logger instance."""
        return logger.bind(pipeline_id=pipeline_id, pipeline_name=pipeline_name)


def get_default_logger() -> structlog.BoundLogger:
    """
    Get a default logger instance with basic configuration.
    Useful for quick setup in development.

    Returns:
        A configured structlog logger instance
    """
    logger_config = OrchestrationLogger()
    return logger_config.get_logger()


# Example usage
if __name__ == "__main__":
    # Create logger with custom configuration
    logger_config = OrchestrationLogger(
        service_name="orchestrator2",
        env="development",
        log_level="DEBUG",
        json_output=False,
    )

    # Get base logger
    logger = logger_config.get_logger()

    # Log with different levels
    logger.debug("Debug message", extra_field="value")
    logger.info("Info message", status="running")
    logger.warning("Warning message", alert_level="medium")
    logger.error("Error message", error_code=500)

    # Add context for a specific pipeline
    pipeline_logger = OrchestrationLogger.add_pipeline_context(
        logger, pipeline_id="123", pipeline_name="data_processing"
    )
    pipeline_logger.info("Pipeline started")

    # Add context for a specific task
    task_logger = OrchestrationLogger.add_task_context(
        pipeline_logger, task_id="456", task_name="data_validation"
    )
    task_logger.info("Task processing", progress=50)
