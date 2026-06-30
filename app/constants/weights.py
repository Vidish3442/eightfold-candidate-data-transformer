"""Source reliability weights and field importance constants.

These values are used by the confidence-scoring and merge stages to compute
field-level and overall confidence scores for the canonical ``Candidate``
record.

Design notes
------------
- ``SOURCE_WEIGHTS`` reflect how reliable each data source is on average.
  ATS data (structured, vendor-maintained) scores highest; recruiter notes
  (free-form, subjective) score lowest.
- ``FIELD_IMPORTANCE`` weights are used in the weighted average that produces
  ``Candidate.overall_confidence``.  Identity fields (name, email, ID) carry
  full weight; decorative fields (headline, links) carry less.
- ``NORMALIZATION_FAILURE_PENALTY`` is subtracted from a field's confidence
  when the normalizer cannot convert the raw value to a canonical form
  (e.g. a phone number that fails E.164 parsing).
- ``AGREEMENT_BOOST`` is added when two or more sources independently supply
  the same value for a field, increasing confidence.
- ``MAX_CONFIDENCE`` caps any computed score so that 1.0 (certainty) is never
  claimed programmatically.
"""

# ---------------------------------------------------------------------------
# Source reliability weights
# ---------------------------------------------------------------------------

SOURCE_WEIGHTS: dict[str, float] = {
    "ats": 0.95,
    "resume": 0.85,
    "recruiter": 0.70,
}
"""Base reliability weight for each data source (range 0.0–1.0)."""

# ---------------------------------------------------------------------------
# Field importance weights (used in overall_confidence weighted average)
# ---------------------------------------------------------------------------

FIELD_IMPORTANCE: dict[str, float] = {
    "candidate_id": 1.0,
    "full_name": 1.0,
    "emails": 1.0,
    "phones": 0.9,
    "location": 0.7,
    "skills": 0.85,
    "experience": 0.9,
    "education": 0.85,
    "certifications": 0.75,
    "headline": 0.5,
    "years_experience": 0.6,
    "links": 0.5,
}
"""Relative importance of each canonical field when computing overall confidence."""

# ---------------------------------------------------------------------------
# Confidence adjustment constants
# ---------------------------------------------------------------------------

NORMALIZATION_FAILURE_PENALTY: float = 0.15
"""Confidence penalty applied when a raw value cannot be normalized (e.g. bad phone format)."""

AGREEMENT_BOOST: float = 0.05
"""Confidence bonus applied when two or more sources supply the same value for a field."""

MAX_CONFIDENCE: float = 0.99
"""Hard ceiling for any computed confidence score — 1.0 (certainty) is never programmatically claimed."""
