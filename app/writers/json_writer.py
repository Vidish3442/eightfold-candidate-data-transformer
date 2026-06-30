"""JSON writer — serialises pipeline output dicts to JSON files.

Isolated from the pipeline so future csv/xml writers can be added without
touching pipeline.py.  The writer creates any missing parent directories
automatically and returns a boolean success flag rather than raising so the
pipeline can handle write failures gracefully.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class JsonWriter:
    """Writes a plain Python dict to a JSON file on disk.

    The writer is stateless and may be reused across multiple ``write`` calls.
    Parent directories are created automatically so callers do not need to
    ``mkdir`` before calling ``write``.

    Serialisation uses ``json.dumps`` with ``indent=2``, ``ensure_ascii=False``
    (to preserve Unicode characters), and ``default=str`` (to handle any
    non-serialisable values such as ``datetime`` objects by converting them to
    their string representation).
    """

    def write(self, data: dict, path: Path) -> bool:
        """Serialise *data* as pretty-printed JSON and write it to *path*.

        Creates all parent directories of *path* if they do not already exist.
        The file is written with UTF-8 encoding.

        Parameters
        ----------
        data:
            A JSON-serialisable dict (e.g. the output of
            ``Candidate.model_dump(mode="json")`` or a projected output dict).
        path:
            Destination file path.  Any missing parent directories are created
            automatically with ``mkdir(parents=True, exist_ok=True)``.

        Returns
        -------
        bool
            ``True`` when the file was written successfully, ``False`` when an
            ``OSError`` or any other exception occurred (the error is logged as
            a warning and not re-raised).

        Example::

            writer = JsonWriter()
            ok = writer.write({"candidate_id": "abc123"}, Path("data/output/canonical_profile.json"))
            assert ok is True
        """
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            json_text = json.dumps(data, indent=2, ensure_ascii=False, default=str)
            path.write_text(json_text, encoding="utf-8")
            logger.debug("JsonWriter: wrote %d bytes to '%s'.", len(json_text), path)
            return True
        except OSError as exc:
            logger.warning("JsonWriter: OSError writing to '%s': %s", path, exc)
            return False
        except Exception as exc:  # noqa: BLE001
            logger.warning("JsonWriter: unexpected error writing to '%s': %s", path, exc)
            return False
