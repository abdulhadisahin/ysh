"""Small offline translation registry without external dependencies."""

from __future__ import annotations

import logging
from collections.abc import Mapping

from i18n.messages_en import MESSAGES
from i18n.messages_tr import MESSAGES as TURKISH_MESSAGES


class Translator:
    """Resolve stable message keys for internal compatibility contracts."""

    def __init__(self, language: str = "en") -> None:
        """Create a translator with English registered by default."""
        self._language = "en"
        self._catalogues: dict[str, Mapping[str, str]] = {
            "en": MESSAGES,
            "tr": TURKISH_MESSAGES,
        }
        self.set_language(language)

    @property
    def language(self) -> str:
        """Return the active normalized language code."""
        return self._language

    def set_language(self, language: str) -> None:
        """Select a supported catalogue, safely falling back to English."""
        self._language = language if language in self._catalogues else "en"

    def register(self, language: str, messages: Mapping[str, str]) -> None:
        """Register a complete or incremental offline language catalogue."""
        self._catalogues[language] = dict(messages)

    def translate(self, key: str, **kwargs: object) -> str:
        """Return a formatted message or a readable fallback for missing keys."""
        message = self._catalogues.get(self._language, {}).get(key)
        if message is None:
            message = self._catalogues["en"].get(key)
        if message is None:
            logging.getLogger(__name__).warning("Missing translation key: %s", key)
            return key
        return message.format(**kwargs)
