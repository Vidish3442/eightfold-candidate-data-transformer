"""Date normalizer — converts raw date strings to YYYY-MM format.

Uses ``dateparser`` to handle the wide variety of date representations that
appear in resumes and ATS exports (e.g. "March 2021", "03/2021", "2021-03").
Special sentinel values such as "Present", "Current", and "Now" are
interpreted as *ongoing* and returned as ``(None, True)`` — meaning the
field normalized successfully but there is no concrete date value.
"""

import logging

import dateparser

logger = logging.getLogger(__name__)

# Sentinel words that mean "this position/study is still ongoing".
_ONGOING_TOKENS: frozenset[str] = frozenset({"present", "current", "now"})


class DateNormalizer:
    """Normalizes raw date strings to ISO ``YYYY-MM`` format.

    Wraps ``dateparser.parse`` with special-case handling for ongoing markers
    and graceful fallback when a date string cannot be interpreted.

    Example::

        dn = DateNormalizer()
        result, ok = dn.normalize("March 2021")
        # result == "2021-03", ok == True

        result, ok = dn.normalize("Present")
        # result is None, ok == True  (ongoing — no end date)
    """

    def normalize(self, raw: str) -> tuple[str | None, bool]:
        """Parse *raw* and return a ``YYYY-MM`` string or ``None``.

        Parameters
        ----------
        raw:
            The raw date string to normalize.  May be any format that
            ``dateparser`` understands, e.g. ``"2021-03"``, ``"March 2021"``,
            ``"03/2021"``, or an ongoing sentinel like ``"Present"``.

        Returns
        -------
        tuple[str | None, bool]
            ``(result, success)`` where:

            * ``(None, False)``  — *raw* was empty or ``None``.
            * ``(None, True)``   — *raw* is an ongoing sentinel ("Present" etc.).
            * ``("YYYY-MM", True)`` — normalization succeeded.
            * ``(raw, False)``   — *raw* could not be parsed; original returned.
        """
        if not raw:
            return (None, False)

        stripped = raw.strip()

        if stripped.lower() in _ONGOING_TOKENS:
            return (None, True)

        # A bare four-digit year should stay as YYYY, not gain a spurious month.
        import re as _re
        if _re.match(r"^\d{4}$", stripped):
            return (stripped, True)

        try:
            parsed = dateparser.parse(
                stripped,
                settings={
                    "PREFER_DAY_OF_MONTH": "first",
                    "RETURN_AS_TIMEZONE_AWARE": False,
                },
            )
            if parsed is None:
                logger.warning("Date normalization returned None for '%s'", raw)
                return (raw, False)
            return (parsed.strftime("%Y-%m"), True)
        except Exception as e:  # noqa: BLE001
            logger.warning("Date normalization failed for '%s': %s", raw, e)
            return (raw, False)

    def normalize_date_range(
        self,
        start_raw: str | None,
        end_raw: str | None,
    ) -> tuple[str | None, str | None, bool]:
        """Normalize a start/end date pair.

        Normalizes both dates independently and returns them together with a
        combined success flag.  At least one of the two dates must normalize
        successfully for *success* to be ``True``.

        Parameters
        ----------
        start_raw:
            Raw start-date string, or ``None`` when not available.
        end_raw:
            Raw end-date string, or ``None`` when not available (e.g.
            ``"Present"`` has already been handled upstream, but this method
            also accepts sentinel strings directly).

        Returns
        -------
        tuple[str | None, str | None, bool]
            ``(start_normalized, end_normalized, success)`` where each
            normalized value is either a ``"YYYY-MM"`` string, ``None``
            (ongoing or absent), or the original raw string (parse failure).
            *success* is ``True`` iff at least one date normalized without
            error.
        """
        start_result: str | None = None
        end_result: str | None = None
        start_ok = False
        end_ok = False

        if start_raw is not None:
            start_result, start_ok = self.normalize(start_raw)
        if end_raw is not None:
            end_result, end_ok = self.normalize(end_raw)

        return (start_result, end_result, start_ok or end_ok)
