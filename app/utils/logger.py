"""PipelineLogger — stage-by-stage human-readable progress logger.

Provides a thin wrapper around the standard :mod:`logging` module that
formats log lines with a fixed-width stage prefix so that multi-stage
pipeline output is easy to scan at a glance.

A module-level singleton ``pipeline_logger`` is exposed so that all
pipeline modules can share the same logger instance without having to
instantiate one themselves.

Example output::

    10:42:01  PhoneNormalizer          ✓  Normalized 3 phone numbers
    10:42:01  DateNormalizer           ⚠  Could not parse '2021/??'
    10:42:01  CandidateMatcher         ✗  No records to match
"""

import logging


class PipelineLogger:
    """Human-readable, stage-aligned logger for the transformation pipeline.

    Each log line is prefixed with a left-aligned 25-character stage name so
    that related log entries from different pipeline stages line up visually
    in the terminal.

    A ``StreamHandler`` writing to ``sys.stderr`` (the logging default) is
    added automatically.  Duplicate handlers are avoided: if the underlying
    :class:`logging.Logger` already has handlers attached (e.g. because
    ``PipelineLogger`` was instantiated more than once with the same *name*),
    no additional handler is added.

    Parameters
    ----------
    name:
        Name passed to :func:`logging.getLogger`.  Defaults to
        ``"pipeline"``.  Use distinct names when you need separate logger
        hierarchies.
    """

    def __init__(self, name: str = "pipeline") -> None:
        """Create (or reuse) a logger with the given *name*.

        Sets the log level to ``INFO`` and attaches a ``StreamHandler`` with
        a ``"HH:MM:SS  <message>"`` format if no handlers are already
        present on the logger.

        Parameters
        ----------
        name:
            Logger name passed to :func:`logging.getLogger`.
        """
        self._logger = logging.getLogger(name)
        self._logger.setLevel(logging.INFO)

        if not self._logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                fmt="%(asctime)s  %(message)s",
                datefmt="%H:%M:%S",
            )
            handler.setFormatter(formatter)
            self._logger.addHandler(handler)

    def info(self, stage: str, message: str) -> None:
        """Log *message* at INFO level with a left-aligned *stage* prefix.

        Parameters
        ----------
        stage:
            Short name identifying the pipeline stage (e.g.
            ``"PhoneNormalizer"``).  Padded or truncated to 25 characters.
        message:
            The log message body.
        """
        self._logger.info("%s %s", f"{stage:<25}", message)

    def warning(self, stage: str, message: str) -> None:
        """Log *message* at WARNING level with a ``⚠`` indicator.

        Parameters
        ----------
        stage:
            Short name identifying the pipeline stage.
        message:
            The log message body.
        """
        self._logger.warning("%s ⚠  %s", f"{stage:<25}", message)

    def error(self, stage: str, message: str) -> None:
        """Log *message* at ERROR level with a ``✗`` indicator.

        Parameters
        ----------
        stage:
            Short name identifying the pipeline stage.
        message:
            The log message body.
        """
        self._logger.error("%s ✗  %s", f"{stage:<25}", message)

    def success(self, stage: str, message: str) -> None:
        """Log *message* at INFO level with a ``✓`` indicator.

        Parameters
        ----------
        stage:
            Short name identifying the pipeline stage.
        message:
            The log message body.
        """
        self._logger.info("%s ✓  %s", f"{stage:<25}", message)


#: Module-level singleton shared across all pipeline modules.
pipeline_logger = PipelineLogger()
