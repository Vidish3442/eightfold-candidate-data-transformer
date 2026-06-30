"""Unit tests for app.matcher.candidate_matcher.CandidateMatcher.

Tests cover email-based matching, phone-digit-based matching, and the
single-candidate fallback assumption.  All tests use inline data constructed
directly from the Pydantic models — no file I/O required.
"""

import pytest

from app.matcher.candidate_matcher import CandidateMatcher
from app.models.ats_candidate import ATSCandidate
from app.models.resume_candidate import ResumeCandidate


def _make_ats(
    candidate_id: str = "ATS-001",
    email: str | None = None,
    phone: str | None = None,
    full_name: str | None = None,
) -> ATSCandidate:
    """Build a minimal ATSCandidate for use in tests.

    Parameters
    ----------
    candidate_id:
        Unique ATS record identifier.
    email:
        Optional email address for matching tests.
    phone:
        Optional raw phone string for matching tests.
    full_name:
        Optional full name for future name-matching tests.

    Returns
    -------
    ATSCandidate
        A validated ATSCandidate instance.
    """
    return ATSCandidate(
        candidate_id=candidate_id,
        email=email,
        phone=phone,
        full_name=full_name,
    )


def _make_resume(
    emails: list[str] | None = None,
    phones: list[str] | None = None,
) -> ResumeCandidate:
    """Build a minimal ResumeCandidate for use in tests.

    Parameters
    ----------
    emails:
        List of email strings extracted from the resume.
    phones:
        List of phone strings extracted from the resume.

    Returns
    -------
    ResumeCandidate
        A validated ResumeCandidate instance.
    """
    return ResumeCandidate(
        emails=emails or [],
        phones=phones or [],
    )


class TestCandidateMatcherEmailMatch:
    """Tests for the exact-email matching strategy."""

    def setup_method(self) -> None:
        """Create a shared CandidateMatcher instance."""
        self.matcher = CandidateMatcher()

    def test_exact_email_match(self) -> None:
        """Identical emails (same case) in both sources should produce a match."""
        ats = _make_ats(email="alice@example.com")
        resume = _make_resume(emails=["alice@example.com"])
        assert self.matcher.match(ats, resume) is True

    def test_exact_email_match_case_insensitive(self) -> None:
        """Email comparison must be case-insensitive."""
        ats = _make_ats(email="Alice@Example.COM")
        resume = _make_resume(emails=["alice@example.com"])
        assert self.matcher.match(ats, resume) is True

    def test_email_in_list_match(self) -> None:
        """ATS email matching any one of several resume emails should succeed."""
        ats = _make_ats(email="alice@example.com")
        resume = _make_resume(emails=["other@example.com", "alice@example.com"])
        assert self.matcher.match(ats, resume) is True


class TestCandidateMatcherPhoneMatch:
    """Tests for the phone-digit matching strategy."""

    def setup_method(self) -> None:
        """Create a shared CandidateMatcher instance."""
        self.matcher = CandidateMatcher()

    def test_phone_digit_match_same_digits(self) -> None:
        """Identical digit sequences in both sources should produce a match."""
        ats = _make_ats(phone="+14155550192")
        resume = _make_resume(phones=["(415) 555-0192"])
        assert self.matcher.match(ats, resume) is True

    def test_phone_digit_match_with_country_code_prefix(self) -> None:
        """ATS phone with country code should match resume's local number."""
        ats = _make_ats(phone="+14155550192")
        resume = _make_resume(phones=["4155550192"])
        assert self.matcher.match(ats, resume) is True


class TestCandidateMatcherFallback:
    """Tests for the single-candidate fallback assumption."""

    def setup_method(self) -> None:
        """Create a shared CandidateMatcher instance."""
        self.matcher = CandidateMatcher()

    def test_single_candidate_fallback(self) -> None:
        """No overlap data should still return True via the fallback assumption."""
        ats = _make_ats(email=None, phone=None)
        resume = _make_resume(emails=[], phones=[])
        assert self.matcher.match(ats, resume) is True

    def test_different_email_no_phone(self) -> None:
        """Different emails with no phone data triggers fallback and returns True."""
        ats = _make_ats(email="alice@example.com", phone=None)
        resume = _make_resume(emails=["bob@example.com"], phones=[])
        assert self.matcher.match(ats, resume) is True

    def test_no_ats_email_but_resume_has_email(self) -> None:
        """Missing ATS email with a resume email should fall through to fallback."""
        ats = _make_ats(email=None, phone=None)
        resume = _make_resume(emails=["carol@example.com"], phones=[])
        assert self.matcher.match(ats, resume) is True


class TestCandidateMatcherThreshold:
    """Tests for custom fuzzy_threshold initialization."""

    def test_custom_threshold_stored(self) -> None:
        """A custom fuzzy_threshold value should be stored on the instance."""
        matcher = CandidateMatcher(fuzzy_threshold=90)
        assert matcher.fuzzy_threshold == 90

    def test_default_threshold(self) -> None:
        """The default fuzzy_threshold should be 85."""
        matcher = CandidateMatcher()
        assert matcher.fuzzy_threshold == 85
