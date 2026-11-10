# ==============================================================================
# CALYX COMMON MODULE: STRUCTURED LOGGING CONFIGURATION
# ==============================================================================
# Concept Explanation for Beginners:
# In local development, you might be used to using `print("User logged in")`.
# In Kubernetes production clusters, hundreds of pods run simultaneously.
# If every pod simply prints raw text, logs get scrambled and diagnosing a bug
# becomes impossible.
# "Structured Logging" outputs standardized log messages containing the service name,
# log level (DEBUG, INFO, ERROR), timestamp, and message. Kubernetes log aggregators
# (like Promtail, Grafana Loki, or Elasticsearch) ingest these streams and allow
# instant filtering by service and error code!
# ==============================================================================

import sys
from loguru import logger


def configure_logger(service_name: str, log_level: str = "INFO"):
    """
    Configures the Loguru logger with structured formatting suitable for
    Kubernetes stdout ingestion.
    
    Parameters:
    - service_name: Name of the microservice executing the log (e.g. 'calyx-auth-service')
    - log_level: Minimum severity level to output (e.g. 'INFO', 'DEBUG')
    """
    # Remove any default handler to prevent duplicated log outputs
    logger.remove()

    # Define a custom log format:
    # Example output:
    # 2026-11-10T15:00:00.000Z | INFO     | calyx-auth-service | user_id=42 | Token issued successfully
    log_format = (
        "<green>{time:YYYY-MM-DDTHH:mm:ss.SSSZ}</green> | "
        "<level>{level: <8}</level> | "
        f"<cyan>{service_name}</cyan> | "
        "<level>{message}</level>"
    )

    # Attach stdout stream sink with colorization and formatting
    logger.add(
        sys.stdout,
        format=log_format,
        level=log_level.upper(),
        colorize=True,
        enqueue=False  # Direct synchronous logging avoids thread locking on Windows
    )

    logger.info(f"Logger initialized for service: {service_name} at level: {log_level}")
    return logger
