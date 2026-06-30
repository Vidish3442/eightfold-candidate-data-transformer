"""Reader for ATS JSON exports.

Reads ``data/input/ats.json`` (or any path provided at call time) and
returns a fully-validated :class:`~app.models.ats_candidate.ATSCandidate`
instance.  Errors during file I/O or JSON parsing are handled gracefully:
a warning is logged and a minimal ``ATSCandidate(candidate_id="UNKNOWN")``
is returned so the pipeline can continue without crashing.
"""

import json
import logging
from pathlib import Path

from app.models.ats_candidate import ATSCandidate
from app.readers.base_reader import BaseReader

logger = logging.getLogger(__name__)


class ATSReader(BaseReader):
    """Reads an ATS JSON export file and returns an :class:`ATSCandidate`.

    This reader is intentionally narrow in scope: it handles file I/O and
    JSON deserialization only.  Field-level normalization and validation are
    delegated to the Pydantic model and downstream normalizer stages.

    Example usage::

        reader = ATSReader()
        candidate = reader.read(Path("data/input/ats.json"))
        print(candidate.candidate_id)
    """

    def read(self, path: Path) -> ATSCandidate:
        """Load and parse an ATS JSON file into an :class:`ATSCandidate`.

        The file is read as UTF-8 text and parsed with :func:`json.loads`.
        The resulting dict is passed directly to the ``ATSCandidate``
        Pydantic constructor, which validates types and applies ``extra="ignore"``
        to discard unknown vendor fields.

        Args:
            path: :class:`~pathlib.Path` to the ATS JSON file.

        Returns:
            A populated :class:`ATSCandidate` on success, or a minimal
            ``ATSCandidate(candidate_id="UNKNOWN")`` when the file cannot be
            read or the JSON cannot be parsed.

        Warns:
            Logs a ``WARNING``-level message via the module logger if an
            :class:`OSError` (file not found, permission denied, etc.) or
            :class:`json.JSONDecodeError` is encountered.
        """
        try:
            raw: str = path.read_text(encoding="utf-8")
            data: dict = json.loads(raw)
            return ATSCandidate(**data)
        except json.JSONDecodeError as exc:
            logger.warning(
                "ATSReader: failed to parse JSON from '%s': %s", path, exc
            )
            return ATSCandidate(candidate_id="UNKNOWN")
        except OSError as exc:
            logger.warning(
                "ATSReader: could not read file '%s': %s", path, exc
            )
            return ATSCandidate(candidate_id="UNKNOWN")
