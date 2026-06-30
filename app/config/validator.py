"""Config validator — validates the shape of a loaded config dict before the pipeline runs."""

import logging

logger = logging.getLogger(__name__)

_VALID_MERGE_STRATEGIES: frozenset[str] = frozenset(
    {"union", "prefer_first", "prefer_last"}
)


class ConfigValidator:
    """Validates the structural integrity of a loaded configuration dict.

    The validator checks that required keys are present with the expected
    types and that nested values like merge strategies are drawn from the
    permitted set.  It does *not* check business-logic constraints such as
    whether listed field names actually exist on the ``Candidate`` model.

    All discovered errors are collected and returned together so callers can
    surface the complete list of problems in one pass rather than fixing
    issues one at a time.
    """

    def validate(self, config: dict) -> tuple[bool, list[str]]:
        """Check *config* for structural validity and return a result summary.

        Validation rules applied (in order):

        1. ``fields`` must be present and be a ``list``.
        2. ``source_priority``, if present, must be a ``dict``.
        3. Each value in ``source_priority`` must be either:
           - a ``list`` (scalar priority list), or
           - a ``dict`` with a ``"merge"`` key whose value is one of
             ``"union"``, ``"prefer_first"``, ``"prefer_last"``.
        4. ``missing_policy``, if present, must be ``None``, ``"omit"``, or
           any other ``str``.
        5. ``rename``, if present, must be a ``dict``.
        6. ``include_confidence``, if present, must be a ``bool``.
        7. ``include_provenance``, if present, must be a ``bool``.

        Parameters
        ----------
        config:
            The configuration dict as returned by ``ConfigLoader.load``.

        Returns
        -------
        tuple[bool, list[str]]
            ``(True, [])`` when all rules pass.
            ``(False, [error_message, ...])`` when one or more rules fail.
            Each failing rule contributes exactly one error string to the list.

        Example::

            validator = ConfigValidator()
            ok, errors = validator.validate({"fields": ["full_name", "emails"]})
            assert ok is True and errors == []
        """
        errors: list[str] = []

        # Rule 1: 'fields' must be present and be a list.
        if "fields" not in config or not isinstance(config["fields"], list):
            errors.append("Missing or invalid 'fields' key — must be a list")

        # Rule 2: 'source_priority', if present, must be a dict.
        source_priority = config.get("source_priority")
        if source_priority is not None and not isinstance(source_priority, dict):
            errors.append("'source_priority' must be a dict")
        elif isinstance(source_priority, dict):
            # Rule 3: validate each entry in source_priority.
            for key, value in source_priority.items():
                if isinstance(value, list):
                    # Scalar priority list — valid as-is.
                    pass
                elif isinstance(value, dict):
                    merge_strategy = value.get("merge")
                    if merge_strategy not in _VALID_MERGE_STRATEGIES:
                        msg = (
                            f"Invalid merge strategy for '{key}': must be "
                            "'union', 'prefer_first', or 'prefer_last'"
                        )
                        errors.append(msg)
                else:
                    msg = (
                        f"Invalid merge strategy for '{key}': must be "
                        "'union', 'prefer_first', or 'prefer_last'"
                    )
                    errors.append(msg)

        # Rule 4: 'missing_policy', if present, must be None or a string.
        if "missing_policy" in config:
            missing_policy = config["missing_policy"]
            if missing_policy is not None and not isinstance(missing_policy, str):
                errors.append("Invalid 'missing_policy' value")

        # Rule 5: 'rename', if present, must be a dict.
        if "rename" in config and not isinstance(config["rename"], dict):
            errors.append("'rename' must be a dict")

        # Rule 6: 'include_confidence', if present, must be bool.
        if "include_confidence" in config and not isinstance(
            config["include_confidence"], bool
        ):
            errors.append("'include_confidence' must be bool")

        # Rule 7: 'include_provenance', if present, must be bool.
        if "include_provenance" in config and not isinstance(
            config["include_provenance"], bool
        ):
            errors.append("'include_provenance' must be bool")

        for error in errors:
            logger.warning("Config validation error: %s", error)

        return (len(errors) == 0, errors)
