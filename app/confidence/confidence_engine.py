"""Confidence engine — computes per-field and overall confidence scores from provenance registry data and source weights."""

import logging

from app.provenance.tracker import ProvenanceTracker
from app.constants.weights import (
    SOURCE_WEIGHTS,
    FIELD_IMPORTANCE,
    NORMALIZATION_FAILURE_PENALTY,
    AGREEMENT_BOOST,
    MAX_CONFIDENCE,
)

logger = logging.getLogger(__name__)


class ConfidenceEngine:
    """Computes field-level and overall confidence scores for a candidate profile.

    The engine reads provenance data from a ``ProvenanceTracker`` instance and
    applies source reliability weights, cross-source agreement bonuses, and
    normalization failure penalties to produce a confidence score for every
    registered field.  A weighted average across all fields yields the
    ``overall_confidence`` value stored on the canonical ``Candidate`` record.

    The engine is stateless beyond its reference to the tracker, so a single
    instance may be reused across multiple calls within the same pipeline run
    as long as the tracker is not mutated between calls.
    """

    def __init__(self, tracker: ProvenanceTracker) -> None:
        """Initialise the confidence engine with a populated provenance tracker.

        Parameters
        ----------
        tracker:
            A ``ProvenanceTracker`` that has already had all merge decisions
            registered.  The engine reads from the tracker but never mutates it.
        """
        self._tracker = tracker

    def compute_field_confidence(
        self, field: str, normalization_failed: bool = False
    ) -> float:
        """Compute a confidence score for a single canonical field.

        The score is derived from the maximum source weight among all sources
        that contributed to the field, with an optional agreement boost when
        multiple sources agreed and an optional normalization failure penalty.

        Parameters
        ----------
        field:
            Canonical field name (e.g. ``"full_name"``, ``"emails"``).
        normalization_failed:
            ``True`` when the normalizer could not convert the raw value to a
            canonical form (e.g. a phone number that fails E.164 parsing).
            Subtracts ``NORMALIZATION_FAILURE_PENALTY`` from the score.

        Returns
        -------
        float
            Confidence score in the range ``[0.0, MAX_CONFIDENCE]``, rounded
            to four decimal places.  Returns ``0.0`` when no sources have been
            registered for the field.

        Example::

            engine.compute_field_confidence("full_name")             # 0.95
            engine.compute_field_confidence("emails", normalization_failed=True)
        """
        sources = self._tracker.get_sources(field)
        if not sources:
            logger.debug("No sources registered for field '%s'; returning 0.0.", field)
            return 0.0

        # Base score: maximum weight among all contributing sources.
        max_weight = max(SOURCE_WEIGHTS.get(src, 0.5) for src in sources)
        score = max_weight

        # Agreement boost when multiple sources contributed.
        if len(sources) > 1:
            score += AGREEMENT_BOOST
            logger.debug(
                "Field '%s': agreement boost applied (+%s).", field, AGREEMENT_BOOST
            )

        # Normalization failure penalty.
        if normalization_failed:
            score -= NORMALIZATION_FAILURE_PENALTY
            logger.debug(
                "Field '%s': normalization failure penalty applied (-%s).",
                field,
                NORMALIZATION_FAILURE_PENALTY,
            )

        # Clamp to [0.0, MAX_CONFIDENCE].
        score = min(MAX_CONFIDENCE, max(0.0, score))
        return round(score, 4)

    def compute_overall_confidence(self, field_confidences: dict[str, float]) -> float:
        """Compute a weighted average confidence score across all fields.

        Each field is weighted by its entry in ``FIELD_IMPORTANCE``; fields not
        present in the importance table default to a weight of ``0.5``.  Fields
        whose weight resolves to zero are excluded from the calculation.

        Parameters
        ----------
        field_confidences:
            Mapping of canonical field name → field-level confidence score,
            as produced by iterating ``compute_field_confidence`` over all
            registered fields.

        Returns
        -------
        float
            Weighted average confidence in the range ``[0.0, MAX_CONFIDENCE]``,
            rounded to four decimal places.  Returns ``0.0`` when
            ``field_confidences`` is empty or all weights are zero.

        Example::

            fc = {"full_name": 0.99, "emails": 0.99, "phones": 0.95}
            engine.compute_overall_confidence(fc)  # 0.9767…
        """
        if not field_confidences:
            return 0.0

        total_weighted = 0.0
        total_weight = 0.0

        for field, confidence in field_confidences.items():
            weight = FIELD_IMPORTANCE.get(field, 0.5)
            if weight <= 0.0:
                continue
            total_weighted += confidence * weight
            total_weight += weight

        if total_weight == 0.0:
            return 0.0

        overall = total_weighted / total_weight
        overall = min(MAX_CONFIDENCE, max(0.0, overall))
        return round(overall, 4)

    def compute_all(
        self, normalization_failures: set[str] | None = None
    ) -> tuple[dict[str, float], float]:
        """Compute field confidences for all registered fields plus overall confidence.

        Convenience method that iterates over every field currently in the
        tracker registry, calls ``compute_field_confidence`` for each, then
        passes the resulting mapping to ``compute_overall_confidence``.

        Parameters
        ----------
        normalization_failures:
            Set of canonical field names whose normalization failed.  Each name
            in this set causes ``NORMALIZATION_FAILURE_PENALTY`` to be applied
            to that field's score.  Defaults to an empty set when ``None``.

        Returns
        -------
        tuple[dict[str, float], float]
            A two-element tuple:

            - ``field_confidences``: mapping of field name → confidence score.
            - ``overall``: the weighted average across all fields.

        Example::

            fc, overall = engine.compute_all(normalization_failures={"phones"})
            print(fc)      # {"full_name": 0.99, "emails": 0.99, "phones": 0.8}
            print(overall) # 0.9456
        """
        normalization_failures = normalization_failures or set()

        field_confidences: dict[str, float] = {}
        for field in self._tracker._registry.keys():
            failed = field in normalization_failures
            field_confidences[field] = self.compute_field_confidence(
                field, normalization_failed=failed
            )

        overall = self.compute_overall_confidence(field_confidences)
        logger.debug(
            "compute_all: %d fields processed, overall confidence=%.4f.",
            len(field_confidences),
            overall,
        )
        return field_confidences, overall
