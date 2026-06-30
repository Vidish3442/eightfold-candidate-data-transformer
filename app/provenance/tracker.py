"""Central provenance registry — records field→source→confidence mappings for every merge decision.

The ``ProvenanceTracker`` is instantiated once per pipeline run and passed into the
``MergeEngine``.  Every merge helper registers the sources it considered and which
value it chose, so the full audit trail can be serialised into
``Candidate.provenance`` at the end of the pipeline.
"""

from app.models.provenance import ProvenanceEntry


class ProvenanceTracker:
    """Central registry that accumulates field-level source/confidence information.

    The tracker records, for every canonical field, which source(s) provided a
    value and with what confidence.  After the merge and confidence stages have
    run, ``to_provenance_entries`` converts the registry into a sorted list of
    ``ProvenanceEntry`` objects suitable for embedding in the canonical
    ``Candidate`` record.

    The tracker is designed to be created fresh for each pipeline run so that
    records from different candidates never bleed into one another.

    Example::

        tracker = ProvenanceTracker()
        tracker.register("full_name", "ats", 0.95)
        tracker.register("full_name", "resume", 0.85)
        entries = tracker.to_provenance_entries(
            winning_sources={"full_name": "ats"},
            notes={"full_name": "ats preferred per config"},
        )
    """

    def __init__(self) -> None:
        """Initialise an empty provenance registry.

        The internal ``_registry`` maps each canonical field name to a nested
        dict of source-name → confidence, e.g.::

            {
                "full_name": {"ats": 0.95, "resume": 0.85},
                "emails":    {"ats": 0.95, "resume": 0.85},
            }
        """
        self._registry: dict[str, dict[str, float]] = {}

    def register(self, field: str, source: str, confidence: float) -> None:
        """Record that *source* contributed to *field* with *confidence*.

        If the same (field, source) pair is registered more than once, the
        higher confidence value is retained.  This makes it safe to call
        ``register`` from multiple merge helpers without worrying about order.

        Parameters
        ----------
        field:
            Canonical field name, e.g. ``"full_name"`` or ``"skills"``.
        source:
            Source identifier, e.g. ``"ats"`` or ``"resume"``.
        confidence:
            Confidence score in the range ``[0.0, 1.0]`` for this source's
            contribution to the field.

        Example::

            tracker.register("full_name", "ats", 0.95)
            tracker.register("full_name", "ats", 0.90)  # keeps 0.95
        """
        if field not in self._registry:
            self._registry[field] = {}

        existing = self._registry[field].get(source, 0.0)
        self._registry[field][source] = max(existing, confidence)

    def get_sources(self, field: str) -> list[str]:
        """Return all source names that contributed to *field*.

        Parameters
        ----------
        field:
            Canonical field name to look up.

        Returns
        -------
        list[str]
            Source names in registration order.  Returns an empty list when
            *field* has not been registered.

        Example::

            tracker.register("emails", "ats", 0.95)
            tracker.register("emails", "resume", 0.85)
            tracker.get_sources("emails")  # ["ats", "resume"]
        """
        if field not in self._registry:
            return []
        return list(self._registry[field].keys())

    def get_confidence(self, field: str, source: str) -> float:
        """Return the confidence recorded for *source* on *field*.

        Parameters
        ----------
        field:
            Canonical field name.
        source:
            Source identifier to look up.

        Returns
        -------
        float
            The stored confidence value, or ``0.0`` when the (field, source)
            pair has not been registered.

        Example::

            tracker.register("skills", "ats", 0.95)
            tracker.get_confidence("skills", "ats")    # 0.95
            tracker.get_confidence("skills", "resume") # 0.0 (not registered)
        """
        return self._registry.get(field, {}).get(source, 0.0)

    def to_provenance_entries(
        self,
        winning_sources: dict[str, str],
        notes: dict[str, str | None] | None = None,
    ) -> list[ProvenanceEntry]:
        """Build a sorted list of ``ProvenanceEntry`` objects from the registry.

        One ``ProvenanceEntry`` is produced for each registered field.  The
        list is sorted alphabetically by field name so the output is
        deterministic regardless of registration order.

        Parameters
        ----------
        winning_sources:
            Mapping of canonical field name → winning source identifier.
            When a field is present in the registry but absent from this dict,
            the first registered source for that field is used as the winner.
        notes:
            Optional mapping of field name → human-readable explanation of the
            merge decision.  When *notes* is ``None`` or a field has no entry,
            ``ProvenanceEntry.note`` is set to ``None``.

        Returns
        -------
        list[ProvenanceEntry]
            One entry per registered field, sorted by ``field`` name.

        Example::

            entries = tracker.to_provenance_entries(
                winning_sources={"full_name": "ats"},
                notes={"full_name": "ats preferred per config"},
            )
        """
        effective_notes: dict[str, str | None] = notes or {}
        entries: list[ProvenanceEntry] = []

        for field in sorted(self._registry.keys()):
            source_map = self._registry[field]
            all_sources = list(source_map.keys())
            max_confidence = max(source_map.values()) if source_map else 0.0

            # Fall back to the first registered source when the winner is not specified.
            winner = winning_sources.get(field, all_sources[0] if all_sources else "unknown")

            entries.append(
                ProvenanceEntry(
                    field=field,
                    sources=all_sources,
                    winning_source=winner,
                    confidence=max_confidence,
                    note=effective_notes.get(field),
                )
            )

        return entries

    def clear(self) -> None:
        """Reset the registry, removing all registered fields and sources.

        Useful in tests or when reusing a tracker instance across pipeline
        runs (though a fresh instance per run is preferred).

        Example::

            tracker.clear()
            assert tracker.get_sources("full_name") == []
        """
        self._registry.clear()
