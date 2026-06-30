"""Projector — applies runtime config (field selection, renaming, missing-field policy, confidence/provenance toggles) to reshape the canonical Candidate profile for output."""

import logging

from app.models.candidate import Candidate

logger = logging.getLogger(__name__)

# Maps config-facing field aliases to their canonical Candidate field names.
_CONFIG_TO_CANONICAL: dict[str, str] = {
    "email": "emails",
    "phone": "phones",
}

# Maps config rename keys that use aliases to their canonical equivalents.
_RENAME_KEY_CANONICAL: dict[str, str] = {
    "phone": "phones",
    "email": "emails",
}


class Projector:
    """Shapes the canonical ``Candidate`` dict for output according to runtime config.

    The projector applies four orthogonal transformations in a fixed order:

    1. **Field selection** — keep only the fields listed in ``config["fields"]``,
       plus ``candidate_id`` which is always included as the primary key.
    2. **Confidence / provenance toggles** — remove ``overall_confidence`` and/or
       ``provenance`` when the corresponding config flags are ``False``.
    3. **Missing-field policy** — omit empty values, preserve ``null``, or replace
       ``None`` with a configured default string.
    4. **Rename** — apply ``config["rename"]`` key mappings to the output dict.

    The projector is stateless beyond its stored config reference and may be
    reused across multiple ``project`` calls.
    """

    def __init__(self, config: dict) -> None:
        """Initialise the projector with a validated runtime configuration dict.

        Parameters
        ----------
        config:
            The configuration dict as returned by ``ConfigLoader.load`` and
            checked by ``ConfigValidator.validate``.  The projector reads the
            following keys: ``fields``, ``include_confidence``,
            ``include_provenance``, ``missing_policy``, and ``rename``.
        """
        self._config = config

    def project(self, candidate: Candidate) -> dict:
        """Transform *candidate* into a plain dict shaped by the runtime config.

        The transformation pipeline is applied in this order:

        1. Serialise the ``Candidate`` to a plain JSON-compatible dict.
        2. Apply field selection (config ``fields`` list), always retaining
           ``candidate_id``.
        3. Remove ``overall_confidence`` if ``include_confidence`` is ``False``.
        4. Remove ``provenance`` if ``include_provenance`` is ``False``.
        5. Apply the ``missing_policy``:
           - ``"omit"``: drop keys whose value is ``None``, ``[]``, or ``{}``.
           - ``None`` (Python ``None`` or YAML ``null``): keep ``None`` as-is.
           - Any other string: replace ``None`` values with that string.
        6. Apply ``rename`` mappings (config alias → target key name).

        Parameters
        ----------
        candidate:
            The canonical ``Candidate`` record produced by the merge stage.

        Returns
        -------
        dict
            A JSON-serialisable dict ready to be written to the output file.

        Example::

            projector = Projector(config)
            output = projector.project(candidate)
            # output contains only the configured fields with applied renames.
        """
        data: dict = candidate.model_dump(mode="json")

        # ------------------------------------------------------------------
        # Step 1: Field selection
        # ------------------------------------------------------------------
        selected_config_fields: list[str] = self._config.get(
            "fields", list(data.keys())
        )

        # Resolve config field aliases to canonical Candidate field names.
        selected_canonical: list[str] = [
            _CONFIG_TO_CANONICAL.get(f, f) for f in selected_config_fields
        ]

        # Build output with only selected fields.
        output: dict = {
            key: data[key] for key in selected_canonical if key in data
        }

        # Always include candidate_id as the primary key.
        if "candidate_id" not in output and "candidate_id" in data:
            output["candidate_id"] = data["candidate_id"]

        # ------------------------------------------------------------------
        # Step 2: Confidence / provenance toggles
        # ------------------------------------------------------------------
        if not self._config.get("include_confidence", True):
            output.pop("overall_confidence", None)

        if not self._config.get("include_provenance", True):
            output.pop("provenance", None)

        # ------------------------------------------------------------------
        # Step 3: Missing-field policy
        # ------------------------------------------------------------------
        missing_policy = self._config.get("missing_policy", None)

        if missing_policy == "omit":
            output = {
                k: v
                for k, v in output.items()
                if v is not None and v != [] and v != {}
            }
        elif missing_policy is None:
            # Keep None values as JSON null — no transformation needed.
            pass
        elif isinstance(missing_policy, str):
            # Replace None values with the configured default string.
            output = {
                k: (missing_policy if v is None else v) for k, v in output.items()
            }

        # ------------------------------------------------------------------
        # Step 4: Rename
        # ------------------------------------------------------------------
        rename_map: dict[str, str] = self._config.get("rename", {})
        for config_old, new_name in rename_map.items():
            # Resolve any config alias (e.g. "phone" → "phones") to the
            # canonical key name that is actually present in the output dict.
            canonical_old = _RENAME_KEY_CANONICAL.get(config_old, config_old)
            if canonical_old in output:
                output[new_name] = output.pop(canonical_old)
                logger.debug(
                    "Renamed output key '%s' → '%s'.", canonical_old, new_name
                )

        return output
