"""Unit tests for app.normalizers.date.DateNormalizer.

Tests cover ISO date strings, natural-language month/year formats, ongoing
sentinel values, empty input, and the normalize_date_range helper.  All
tests use inline data and do not touch the filesystem.
"""

import pytest

from app.normalizers.date import DateNormalizer


class TestDateNormalizerSingleValue:
    """Tests for DateNormalizer.normalize() with individual date strings."""

    def setup_method(self) -> None:
        """Instantiate a shared DateNormalizer for each test method."""
        self.normalizer = DateNormalizer()

    def test_iso_date(self) -> None:
        """An ISO-style YYYY-MM date string should round-trip correctly."""
        result, success = self.normalizer.normalize("2021-03")
        assert success is True
        assert result == "2021-03"

    def test_month_year(self) -> None:
        """A natural-language month-year string should convert to YYYY-MM."""
        result, success = self.normalizer.normalize("March 2021")
        assert success is True
        assert result == "2021-03"

    def test_present(self) -> None:
        """'Present' should be treated as an ongoing marker (None, True)."""
        result, success = self.normalizer.normalize("Present")
        assert success is True
        assert result is None

    def test_current(self) -> None:
        """'current' (lowercase) should also be treated as ongoing."""
        result, success = self.normalizer.normalize("current")
        assert success is True
        assert result is None

    def test_now(self) -> None:
        """'Now' should also be treated as an ongoing sentinel."""
        result, success = self.normalizer.normalize("Now")
        assert success is True
        assert result is None

    def test_empty(self) -> None:
        """An empty string should return (None, False)."""
        result, success = self.normalizer.normalize("")
        assert success is False
        assert result is None

    def test_none_input(self) -> None:
        """A None-like empty value should return (None, False) gracefully.

        DateNormalizer.normalize() accepts str; passing an empty string
        is the canonical way to signal absence.
        """
        result, success = self.normalizer.normalize("")
        assert success is False
        assert result is None

    def test_four_digit_year(self) -> None:
        """A bare four-digit year string should parse to YYYY-01."""
        result, success = self.normalizer.normalize("2019")
        assert success is True
        # dateparser resolves bare years to January of that year by default.
        assert result is not None
        assert result.startswith("2019")


class TestDateNormalizerRange:
    """Tests for DateNormalizer.normalize_date_range()."""

    def setup_method(self) -> None:
        """Instantiate a shared DateNormalizer for each test method."""
        self.normalizer = DateNormalizer()

    def test_normalize_date_range_both_valid(self) -> None:
        """Both valid dates should normalize and success should be True."""
        start, end, success = self.normalizer.normalize_date_range("March 2021", "June 2023")
        assert success is True
        assert start == "2021-03"
        assert end == "2023-06"

    def test_normalize_date_range_present(self) -> None:
        """Start is a valid date; end is 'Present' — success should be True."""
        start, end, success = self.normalizer.normalize_date_range("March 2021", "Present")
        assert success is True
        assert start == "2021-03"
        assert end is None

    def test_normalize_date_range_both_none(self) -> None:
        """Both inputs being None should yield success=False."""
        start, end, success = self.normalizer.normalize_date_range(None, None)
        assert success is False
        assert start is None
        assert end is None

    def test_normalize_date_range_only_end(self) -> None:
        """Only an end date provided should still succeed."""
        start, end, success = self.normalizer.normalize_date_range(None, "December 2022")
        assert success is True
        assert start is None
        assert end == "2022-12"
