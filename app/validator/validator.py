"""Output validator — validates a Candidate object against the Pydantic schema before projection.

Runs a round-trip ``model_validate(model_dump())`` on a ``Candidate`` instance
to ensure the object is still schema-valid after all upstream merge and
confidence mutations.  Any ``ValidationError`` details are collected and
returned as plain strings so the pipeline can log them without re-raising.
"""

import logging
from pydantic import ValidationError

from app.models.candidate import Candidate

logger = logging.getLogger(__name__)


class OutputValidator:
    """Validates a canonical ``Candidate`` object against its Pydantic schema.

    Performs a round-trip re-validation (``model_validate(model_dump())``) so
    that any field constraint violations introduced by post-merge mutations
    (e.g. an out-of-range ``overall_confidence``) are caught before the
    candidate is passed to the projector and writer.

    The validator never raises; it always returns a tuple so the pipeline can
    decide whether to abort, warn, or continue.
    """

    def validate(self, candidate: Candidate) -> tuple[bool, list[str]]:
        """Re-validate *candidate* by serialising and re-parsing it.

        Calls ``Candidate.model_validate(candidate.model_dump())`` to trigger
        all field-level Pydantic validators.  Any ``ValidationError`` is caught,
        its individual error messages are collected into a list of human-readable
        strings, and ``(False, errors)`` is returned.  On success the method
        returns ``(True, [])``.

        This method is deliberately non-raising: callers decide how to handle
        failures.  A warning is emitted to the logger for each individual
        validation error when validation fails.

        Parameters
        ----------
        candidate:
            The canonical ``Candidate`` record to re-validate.

        Returns
        -------
        tuple[bool, list[str]]
            ``(True, [])`` when the candidate passes schema validation, or
            ``(False, errors)`` where *errors* is a list of error message
            strings when validation fails.

        Example::

            validator = OutputValidator()
            valid, errors = validator.validate(candidate)
            if not valid:
                print("Validation failed:", errors)
        """
        try:
            Candidate.model_validate(candidate.model_dump())
            return (True, [])
        except ValidationError as exc:
            errors: list[str] = []
            for error in exc.errors():
                msg = f"{'.'.join(str(loc) for loc in error['loc'])}: {error['msg']}"
                logger.warning("OutputValidator: %s", msg)
                errors.append(msg)
            return (False, errors)
