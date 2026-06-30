"""Location normalizer — parses raw location strings/dicts into structured records.

Converts the variety of location representations found in resumes and ATS
exports into a uniform ``{"city": ..., "state": ..., "country": ...}``
dictionary.  Country values are resolved to ISO 3166-1 alpha-2 codes using
``pycountry``; if resolution fails the original string is kept so no data
is lost.
"""

import logging

import pycountry

logger = logging.getLogger(__name__)


class LocationNormalizer:
    """Normalizes raw location data into a structured city/state/country dict.

    Accepts three input forms:

    * ``None`` — returns a blank location dict.
    * ``str``  — attempts to parse as ``"City, State, Country"`` or
                 ``"City, State"`` by splitting on commas.
    * ``dict`` — reads the ``city``, ``state``, and ``country`` keys
                 (missing keys default to ``None``).

    The ``country`` value is always passed through :meth:`_resolve_country`
    which attempts to convert it to an ISO 3166-1 alpha-2 code.

    Example::

        ln = LocationNormalizer()
        ln.normalize("San Francisco, CA, US")
        # {"city": "San Francisco", "state": "CA", "country": "US"}

        ln.normalize({"city": "London", "country": "United Kingdom"})
        # {"city": "London", "state": None, "country": "GB"}
    """

    def normalize(
        self, raw: dict[str, str | None] | str | None
    ) -> dict[str, str | None]:
        """Parse *raw* into a structured location dictionary.

        Parameters
        ----------
        raw:
            The location to normalize.  May be ``None``, a plain string
            (``"City, State, Country"`` or ``"City, State"``), or a dict
            with optional keys ``city``, ``state``, ``country``.

        Returns
        -------
        dict[str, str | None]
            A dictionary with exactly the keys ``city``, ``state``, and
            ``country``.  Each value is either a stripped string or ``None``.
            ``country`` is resolved to an ISO 3166-1 alpha-2 code where
            possible.
        """
        if raw is None:
            return {"city": None, "state": None, "country": None}

        city: str | None = None
        state: str | None = None
        country_raw: str | None = None

        if isinstance(raw, str):
            parts = [p.strip() for p in raw.split(",")]
            if len(parts) >= 3:
                city = parts[0] or None
                state = parts[1] or None
                country_raw = parts[2] or None
            elif len(parts) == 2:
                city = parts[0] or None
                state = parts[1] or None
            elif len(parts) == 1:
                city = parts[0] or None
        else:
            city = raw.get("city") or None
            state = raw.get("state") or None
            country_raw = raw.get("country") or None

        resolved_country = self._resolve_country(country_raw)
        return {"city": city, "state": state, "country": resolved_country}

    def _resolve_country(self, raw: str | None) -> str | None:
        """Attempt to resolve *raw* to an ISO 3166-1 alpha-2 country code.

        Uses ``pycountry.countries.lookup`` which accepts country names,
        alpha-2 codes, alpha-3 codes, and numeric codes.  When lookup
        succeeds the two-letter alpha-2 code is returned.  When lookup
        fails (unknown name or abbreviation) the original *raw* string is
        returned unchanged so that no location data is discarded silently.

        Parameters
        ----------
        raw:
            A country string in any form recognised by ``pycountry``
            (e.g. ``"United States"``, ``"US"``, ``"USA"``, ``"840"``),
            or ``None``.

        Returns
        -------
        str | None
            The ISO 3166-1 alpha-2 code on success, the original *raw*
            string when lookup fails, or ``None`` when *raw* is empty/None.
        """
        if not raw:
            return None
        try:
            country = pycountry.countries.lookup(raw)
            return country.alpha_2
        except LookupError:
            logger.debug("Could not resolve country '%s' to ISO alpha-2; keeping as-is", raw)
            return raw
