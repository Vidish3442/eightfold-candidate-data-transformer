"""Phone number normalizer — converts raw phone strings to E.164 format.

Uses the ``phonenumbers`` library to parse and reformat any phone string
into the standard E.164 representation (e.g. ``+14155550192``).  When
parsing fails the original raw string is returned unchanged so that
downstream stages can still store the value rather than losing it entirely.
"""

import logging

import phonenumbers

logger = logging.getLogger(__name__)


class PhoneNormalizer:
    """Normalizes raw phone number strings to E.164 format.

    Wraps the ``phonenumbers`` library with error handling so that
    unparseable strings never raise exceptions into the calling pipeline.

    Example::

        normalizer = PhoneNormalizer()
        e164, ok = normalizer.normalize("+1-415-555-0192")
        # e164 == "+14155550192", ok == True
    """

    def normalize(self, raw: str, default_region: str = "US") -> tuple[str, bool]:
        """Parse *raw* and return its E.164 representation.

        Parameters
        ----------
        raw:
            The raw phone string to normalize (e.g. ``"(415) 555-0192"``).
        default_region:
            ISO 3166-1 alpha-2 country code used as a hint when *raw* does
            not include a country calling code.  Defaults to ``"US"``.

        Returns
        -------
        tuple[str, bool]
            A two-element tuple ``(result, success)`` where *result* is the
            E.164 string on success or the original *raw* string on failure,
            and *success* is ``True`` iff normalization succeeded.
        """
        try:
            parsed = phonenumbers.parse(raw, default_region)
            e164 = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
            return (e164, True)
        except phonenumbers.NumberParseException as e:
            logger.warning("Phone normalization failed for '%s': %s", raw, e)
            return (raw, False)
        except Exception as e:  # noqa: BLE001
            logger.warning("Phone normalization failed for '%s': %s", raw, e)
            return (raw, False)

    def normalize_list(
        self, raws: list[str], default_region: str = "US"
    ) -> list[tuple[str, bool]]:
        """Normalize each phone string in *raws*.

        Parameters
        ----------
        raws:
            A list of raw phone strings to normalize.
        default_region:
            ISO 3166-1 alpha-2 region hint passed to each :meth:`normalize`
            call.  Defaults to ``"US"``.

        Returns
        -------
        list[tuple[str, bool]]
            A list of ``(result, success)`` tuples in the same order as
            *raws*, one entry per input element.
        """
        return [self.normalize(raw, default_region) for raw in raws]
