"""Unit tests for app.normalizers.phone.PhoneNormalizer.

Tests cover standard US numbers, international numbers, unparseable strings,
empty input, and the batch normalize_list helper.  All tests use inline data
and do not touch the filesystem.
"""

import pytest

from app.normalizers.phone import PhoneNormalizer


class TestPhoneNormalizerSingleValue:
    """Tests for PhoneNormalizer.normalize() with individual phone strings."""

    def setup_method(self) -> None:
        """Instantiate a shared PhoneNormalizer for each test method."""
        self.normalizer = PhoneNormalizer()

    def test_valid_us_number(self) -> None:
        """A valid US number with dashes should be converted to E.164."""
        result, success = self.normalizer.normalize("+1-415-555-0192")
        assert success is True
        assert result == "+14155550192"

    def test_valid_us_number_parentheses_format(self) -> None:
        """A parenthesised US number should also normalize to E.164."""
        result, success = self.normalizer.normalize("(415) 555-0192", default_region="US")
        assert success is True
        assert result == "+14155550192"

    def test_valid_international(self) -> None:
        """A UK number with international prefix should normalize to E.164."""
        result, success = self.normalizer.normalize("+44 20 7946 0958")
        assert success is True
        # E.164 strips spaces and parentheses; must start with the UK code.
        assert result.startswith("+44")
        assert success is True

    def test_unparsable_number(self) -> None:
        """An unparseable string should be returned as-is with success=False."""
        raw = "not-a-phone"
        result, success = self.normalizer.normalize(raw)
        assert success is False
        assert result == raw

    def test_empty_string(self) -> None:
        """An empty string should be returned as-is with success=False."""
        result, success = self.normalizer.normalize("")
        assert success is False
        assert result == ""

    def test_random_text_no_digits(self) -> None:
        """A string of letters and symbols is not a valid phone number."""
        raw = "abcdefg!!"
        result, success = self.normalizer.normalize(raw)
        assert success is False
        assert result == raw


class TestPhoneNormalizerList:
    """Tests for PhoneNormalizer.normalize_list()."""

    def setup_method(self) -> None:
        """Instantiate a shared PhoneNormalizer for each test method."""
        self.normalizer = PhoneNormalizer()

    def test_normalize_list_mixed(self) -> None:
        """A list of valid and invalid numbers should be processed element-wise."""
        raws = ["+1-415-555-0192", "not-a-phone", "+44 20 7946 0958"]
        results = self.normalizer.normalize_list(raws)

        assert len(results) == 3

        e164_us, ok_us = results[0]
        assert ok_us is True
        assert e164_us == "+14155550192"

        raw_bad, ok_bad = results[1]
        assert ok_bad is False
        assert raw_bad == "not-a-phone"

        e164_uk, ok_uk = results[2]
        assert ok_uk is True
        assert e164_uk.startswith("+44")

    def test_normalize_list_empty_list(self) -> None:
        """An empty input list should return an empty result list."""
        assert self.normalizer.normalize_list([]) == []

    def test_normalize_list_all_valid(self) -> None:
        """All entries should succeed when all numbers are valid."""
        raws = ["+14155550192", "+14155550193"]
        results = self.normalizer.normalize_list(raws)
        assert all(ok for _, ok in results)

    def test_normalize_list_all_invalid(self) -> None:
        """All entries should fail when all numbers are invalid."""
        raws = ["foo", "bar", ""]
        results = self.normalizer.normalize_list(raws)
        assert all(not ok for _, ok in results)
