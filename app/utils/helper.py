"""General utility helpers used across the pipeline.

Provides small, stateless helper functions for common data-manipulation tasks
such as list deduplication, safe string operations, and dictionary cleaning.
These utilities are intentionally side-effect-free and do not import from
other pipeline modules so that they can be reused anywhere without creating
circular dependencies.
"""


def deduplicate_list(items: list[str]) -> list[str]:
    """Return *items* with duplicates removed, preserving first-seen order.

    Comparison is case-insensitive: ``"Python"`` and ``"python"`` are
    treated as the same element and only the first occurrence is kept.

    Parameters
    ----------
    items:
        A list of strings that may contain duplicates.

    Returns
    -------
    list[str]
        A new list containing the first occurrence of each unique string
        (case-insensitively), in original insertion order.

    Example::

        deduplicate_list(["Python", "python", "Go"])
        # ["Python", "Go"]
    """
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def safe_lower(s: str | None) -> str | None:
    """Return ``s.lower()`` if *s* is not ``None``, otherwise return ``None``.

    Avoids ``AttributeError`` when calling ``.lower()`` on optional strings
    scattered throughout the pipeline.

    Parameters
    ----------
    s:
        A string to lowercase, or ``None``.

    Returns
    -------
    str | None
        The lowercased string, or ``None`` when *s* is ``None``.

    Example::

        safe_lower("Hello")  # "hello"
        safe_lower(None)     # None
    """
    if s is None:
        return None
    return s.lower()


def strip_none_values(d: dict) -> dict:
    """Return a copy of *d* with all ``None``-valued keys removed.

    Only top-level keys are inspected; nested dicts are not recursed into.

    Parameters
    ----------
    d:
        Any dictionary.  Keys whose value is ``None`` will be omitted from
        the returned dict.

    Returns
    -------
    dict
        A new dictionary containing only entries where the value is not
        ``None``.

    Example::

        strip_none_values({"a": 1, "b": None, "c": "x"})
        # {"a": 1, "c": "x"}
    """
    return {k: v for k, v in d.items() if v is not None}


def flatten_list(nested: list[list]) -> list:
    """Flatten one level of nesting from *nested*.

    Only the first level of nesting is removed; deeper nesting is left
    intact.  This is intentionally shallow to avoid surprising behaviour
    when list elements are themselves lists of lists.

    Parameters
    ----------
    nested:
        A list whose elements are themselves lists.

    Returns
    -------
    list
        A single flat list containing all elements from the sub-lists.

    Example::

        flatten_list([[1, 2], [3, 4], [5]])
        # [1, 2, 3, 4, 5]
    """
    return [item for sublist in nested for item in sublist]
