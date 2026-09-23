"""Runtime language selection and local preference persistence for YSH."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from pathlib import Path

from i18n.translator import Translator


LanguageChangeListener = Callable[[], None]


class LanguagePreferenceStore:
    """Persist the non-sensitive interface language outside project state."""

    def __init__(self, path: Path) -> None:
        """Create a preference store at one application-data path."""
        self._path = path

    def load(self) -> str:
        """Return the saved language code or English for absent/invalid data."""
        if not self._path.exists():
            return "en"
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            logging.getLogger(__name__).warning("Unable to read language preference.")
            return "en"
        language = data.get("language") if isinstance(data, dict) else None
        return language if language in {"en", "tr"} else "en"

    def save(self, language: str) -> None:
        """Persist one normalized language code without touching project data."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self._path.with_suffix(".tmp")
        temporary_path.write_text(
            json.dumps({"language": language}, ensure_ascii=False),
            encoding="utf-8",
        )
        temporary_path.replace(self._path)


class LocalizationManager:
    """Coordinate translation lookup, runtime refreshes, and user preference."""

    def __init__(self, settings_path: Path) -> None:
        """Load the application language and initialize its translation registry."""
        self._store = LanguagePreferenceStore(settings_path)
        self._translator = Translator(self._store.load())
        self._listeners: list[LanguageChangeListener] = []

    @property
    def language(self) -> str:
        """Return the active application language code."""
        return self._translator.language

    def translate(self, key: str, **kwargs: object) -> str:
        """Resolve a stable translation key through the active catalogue."""
        return self._translator.translate(key, **kwargs)

    def set_language(self, language: str) -> None:
        """Persist a selected language and refresh registered live UI surfaces."""
        previous_language = self._translator.language
        self._translator.set_language(language)
        self._store.save(self._translator.language)
        logger = logging.getLogger(__name__)
        logger.info(
            "LOCALIZATION language: %s -> %s; listeners: %d",
            previous_language,
            self._translator.language,
            len(self._listeners),
        )
        for listener in tuple(self._listeners):
            owner = getattr(listener, "__self__", None)
            listener_name = (
                owner.__class__.__name__
                if owner is not None
                else getattr(listener, "__qualname__", repr(listener))
            )
            try:
                logger.info("LOCALIZATION refresh: %s", listener_name)
                listener()
                logger.info("LOCALIZATION refresh complete: %s", listener_name)
            except Exception:
                logger.exception("LOCALIZATION refresh failed: %s", listener_name)

    def register(self, listener: LanguageChangeListener) -> None:
        """Register one live UI refresh callback without invoking it immediately."""
        self._listeners.append(listener)
