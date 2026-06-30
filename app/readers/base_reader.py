"""Abstract base class for all data readers in the pipeline.

A *reader* is responsible for loading raw content from a file on disk and
returning it in a form that the downstream parser or extractor stages can
consume.  Each concrete reader sub-class handles a specific file format
(plain text, PDF, JSON, etc.) and a specific return type.

This module provides the ``BaseReader`` ABC that enforces a common ``read``
interface across all reader implementations.
"""

from abc import ABC, abstractmethod
from pathlib import Path


class BaseReader(ABC):
    """Abstract base class that all concrete readers must subclass.

    Subclasses must implement :meth:`read`, which accepts a filesystem path
    and returns parsed content whose type is defined by the concrete class.

    Example usage::

        class MyReader(BaseReader):
            def read(self, path: Path) -> dict:
                return {"content": path.read_text()}
    """

    @abstractmethod
    def read(self, path: Path) -> dict:
        """Load and return content from *path*.

        Args:
            path: Absolute or relative :class:`~pathlib.Path` to the source
                file that should be read.

        Returns:
            Parsed content in a form suitable for downstream processing.
            The exact type depends on the concrete subclass (e.g. ``str``
            for ``ResumeReader``, ``ATSCandidate`` for ``ATSReader``).

        Raises:
            Any concrete implementation should catch IO and parsing errors
            internally, log a warning, and return a safe empty/default value
            rather than letting exceptions propagate to the caller.
        """
