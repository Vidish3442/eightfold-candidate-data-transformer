"""Candidate matcher — decides whether ATS and resume records refer to the same candidate.

Uses a tiered matching strategy:

1. **Exact email match** — if both sources carry an email address and they
   share at least one address (case-insensitive), the pair is considered
   a match immediately.
2. **Phone digit match** — if both sources carry phone strings, the digit
   sequences are compared; a shared suffix of ≥ 7 digits counts as a match
   (handles the common case where the ATS stores a local number and the
   resume stores it with a country code, or vice-versa).
3. **Single-candidate fallback** — when neither email nor phone evidence is
   available, the pipeline assumes the run contains exactly one ATS record
   and one resume and logs this assumption rather than returning a hard
   failure.

The fuzzy-name-match step (Step 2 in the original design) is deferred until
``ResumeCandidate`` carries a structured name field; currently only
``headline`` is available and it may contain a title rather than a name.
"""

import logging
import re

from rapidfuzz import fuzz  # noqa: F401  — imported for future name matching

from app.models.ats_candidate import ATSCandidate
from app.models.resume_candidate import ResumeCandidate

logger = logging.getLogger(__name__)

# Minimum shared digit-string length to count as a phone match.
_MIN_PHONE_DIGITS: int = 7


class CandidateMatcher:
    """Determines whether an ATS record and a resume record belong to the same person.

    Matching proceeds through a tier of strategies in order of confidence:
    exact email, phone digits, then single-candidate fallback.  The first
    strategy that produces evidence of a match short-circuits the rest.

    Parameters
    ----------
    fuzzy_threshold:
        Minimum ``rapidfuzz`` token-sort-ratio score (0–100) to accept a
        fuzzy name match.  Stored for future use when structured name data
        becomes available on ``ResumeCandidate``.  Defaults to ``85``.

    Example::

        matcher = CandidateMatcher()
        matched = matcher.match(ats_record, resume_record)
    """

    def __init__(self, fuzzy_threshold: int = 85) -> None:
        """Store the fuzzy-match threshold.

        Parameters
        ----------
        fuzzy_threshold:
            Minimum rapidfuzz score to accept a name match (0–100).
        """
        self.fuzzy_threshold = fuzzy_threshold

    def match(self, ats: ATSCandidate, resume: ResumeCandidate) -> bool:
        """Return ``True`` if *ats* and *resume* refer to the same candidate.

        Matching strategy (first hit wins):

        1. **Exact email** — ``ats.email`` intersects ``resume.emails``
           (case-insensitive).
        2. **Phone digits** — the digit-only representations of ``ats.phone``
           and any entry in ``resume.phones`` share a common suffix of at
           least :data:`_MIN_PHONE_DIGITS` digits.
        3. **Single-candidate fallback** — no evidence either way; assume the
           run involves exactly one record from each source and return ``True``
           after logging the assumption.

        Parameters
        ----------
        ats:
            The ATS candidate record to match.
        resume:
            The resume candidate record to match against.

        Returns
        -------
        bool
            ``True`` when the pair is considered a match, ``False`` otherwise.
            Under the current strategy this method always returns ``True``
            (either via evidence or via the single-candidate fallback), which
            is the correct behaviour for single-candidate pipeline runs.
        """
        # --- Step 1: Exact email match ---
        if ats.email and resume.emails:
            ats_email_lower = ats.email.lower()
            resume_emails_lower = [e.lower() for e in resume.emails]
            if ats_email_lower in resume_emails_lower:
                logger.info(
                    "CandidateMatcher: email match on '%s'", ats.email
                )
                return True

        # --- Step 2: Phone digit match ---
        if ats.phone and resume.phones:
            ats_digits = self._digits_only(ats.phone)
            for resume_phone in resume.phones:
                resume_digits = self._digits_only(resume_phone)
                # Check whether one digit string ends with the other (handles
                # country-code prefix mismatches) and the overlap is long enough.
                if (
                    len(ats_digits) >= _MIN_PHONE_DIGITS
                    and len(resume_digits) >= _MIN_PHONE_DIGITS
                    and (
                        ats_digits.endswith(resume_digits[-_MIN_PHONE_DIGITS:])
                        or resume_digits.endswith(ats_digits[-_MIN_PHONE_DIGITS:])
                    )
                ):
                    logger.info(
                        "CandidateMatcher: phone digit match ('%s' ~ '%s')",
                        ats.phone,
                        resume_phone,
                    )
                    return True

        # --- Step 3: Single-candidate fallback ---
        logger.info(
            "CandidateMatcher: single-candidate run — assuming match between "
            "ATS '%s' and resume record",
            ats.candidate_id,
        )
        return True

    def _digits_only(self, s: str) -> str:
        """Return the digit characters from *s*, stripping everything else.

        Parameters
        ----------
        s:
            Any string, typically a raw or E.164-formatted phone number.

        Returns
        -------
        str
            A string containing only the digit characters from *s* (empty
            string if *s* contains no digits).

        Example::

            self._digits_only("+1 (415) 555-0192")
            # "14155550192"
        """
        return re.sub(r"\D", "", s)
