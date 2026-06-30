"""Reader for resume documents (.txt and PDF).

Extracts plain text from a resume file so the downstream parser and
extractor stages can work with a single, uniform string regardless of the
original file format.

Supported formats:
- ``.txt`` — read directly as UTF-8 text.
- ``.pdf`` — text layer extracted via *PyMuPDF* (``fitz``).  Scanned PDFs
  that contain only rasterised images will produce an empty string; a
  warning is logged in that case.

All errors are caught internally; a warning is logged and ``""`` is
returned so the pipeline degrades gracefully rather than crashing.
"""

import logging
from pathlib import Path

import fitz  # PyMuPDF

from app.readers.base_reader import BaseReader

logger = logging.getLogger(__name__)


class ResumeReader(BaseReader):
    """Extracts plain text from a ``.txt`` or PDF resume file.

    Text is returned as a single string with page breaks joined by newlines.
    No parsing or section detection is done here; that is the responsibility
    of :class:`~app.parsers.resume_parser.ResumeParser`.

    Example usage::

        reader = ResumeReader()
        text = reader.read(Path("data/input/resume.pdf"))
        print(text[:200])
    """

    def read(self, path: Path) -> str:
        """Extract and return plain text from *path*.

        For ``.txt`` files the content is returned verbatim (UTF-8 decoded).
        For all other extensions the file is treated as a PDF and the text
        layer is extracted using *PyMuPDF*.  If the extracted text is empty
        or whitespace-only (e.g. scanned image PDF) a warning is logged and
        ``""`` is returned.

        Args:
            path: :class:`~pathlib.Path` to the resume file (``.txt`` or
                ``.pdf`` / any extension that PyMuPDF can handle).

        Returns:
            The full extracted plain text of the document, or ``""`` when
            extraction fails or yields no usable text.

        Warns:
            Logs a ``WARNING``-level message via the module logger when:
            - A PDF yields no extractable text (scanned or empty document).
            - Any exception occurs during reading or PDF processing.
        """
        try:
            if path.suffix.lower() == ".txt":
                return path.read_text(encoding="utf-8")

            # Treat everything else as a PDF
            pages: list[str] = []
            with fitz.open(str(path)) as doc:
                for page in doc:
                    pages.append(page.get_text())

            text: str = "\n".join(pages)

            if not text.strip():
                logger.warning(
                    "ResumeReader: No extractable text found — "
                    "scanned PDF or empty document: '%s'",
                    path,
                )
                return ""

            return text

        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "ResumeReader: failed to read '%s': %s", path, exc
            )
            return ""
