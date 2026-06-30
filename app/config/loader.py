"""Config loader — reads and parses config.yaml into a Python dict."""

import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Reads and deserialises a YAML configuration file into a plain Python dict.

    The loader is intentionally minimal: it performs no schema validation
    (that responsibility belongs to ``ConfigValidator``) and returns an empty
    dict rather than raising on any file or parse error so the pipeline can
    degrade gracefully when configuration is unavailable.
    """

    def load(self, path: Path) -> dict:
        """Read *path* and return its contents parsed as a YAML mapping.

        The method is safe to call even when the file does not exist or
        contains malformed YAML — both cases are logged as warnings and an
        empty dict is returned so callers can apply sensible defaults.

        Parameters
        ----------
        path:
            Filesystem path to the YAML configuration file.

        Returns
        -------
        dict
            Parsed YAML content as a Python dict.  Returns ``{}`` when the
            file cannot be read or its content is not a YAML mapping.

        Example::

            loader = ConfigLoader()
            config = loader.load(Path("config.yaml"))
            fields = config.get("fields", [])
        """
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            logger.warning("Could not read config file '%s': %s", path, exc)
            return {}

        try:
            result = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            logger.warning("Failed to parse config file '%s': %s", path, exc)
            return {}

        if result is None:
            logger.warning("Config file '%s' is empty; using defaults.", path)
            return {}

        return result
