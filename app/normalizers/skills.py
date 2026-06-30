"""Skills normalizer — maps raw skill strings to canonical names.

Uses the alias table in ``app.constants.skills`` to convert the wide variety
of abbreviations, acronyms, and alternative spellings that appear in resumes
and ATS exports into a single canonical representation per skill.

Unknown skills (those not present in ``SKILL_ALIASES``) are returned with
their original casing preserved so that no information is lost.
"""

from app.constants.skills import SKILL_ALIASES


class SkillNormalizer:
    """Normalizes raw skill tokens to their canonical display names.

    Uses the ``SKILL_ALIASES`` dictionary for lookups.  Lookup is
    case-insensitive; the original casing is preserved when a skill is not
    found in the alias table.

    Example::

        sn = SkillNormalizer()
        sn.normalize("py")      # "Python"
        sn.normalize("k8s")     # "Kubernetes"
        sn.normalize("MyLib")   # "MyLib"  (unknown — original casing kept)
    """

    def normalize(self, raw: str) -> str:
        """Return the canonical name for *raw*, or *raw* itself if unknown.

        The lookup key is ``raw.strip().lower()``.  If found in
        ``SKILL_ALIASES`` the canonical value is returned; otherwise the
        stripped original string is returned unchanged.

        Parameters
        ----------
        raw:
            A raw skill string (e.g. ``"py"``, ``"k8s"``, ``"machine learning"``).

        Returns
        -------
        str
            The canonical skill name, or the original stripped string when
            the skill is not in the alias table.
        """
        key = raw.strip().lower()
        return SKILL_ALIASES.get(key, raw.strip())

    def normalize_list(self, raws: list[str]) -> list[str]:
        """Normalize each skill in *raws*, deduplicate, and return sorted.

        Each element is passed through :meth:`normalize`.  Duplicates are
        removed in a case-insensitive, first-seen fashion, and the final list
        is sorted alphabetically for deterministic output.

        Parameters
        ----------
        raws:
            A list of raw skill strings (may contain duplicates or aliases
            that map to the same canonical name).

        Returns
        -------
        list[str]
            Deduplicated, sorted list of canonical skill names.
        """
        seen: set[str] = set()
        ordered: list[str] = []
        for raw in raws:
            canonical = self.normalize(raw)
            key = canonical.lower()
            if key not in seen:
                seen.add(key)
                ordered.append(canonical)
        return sorted(ordered)
