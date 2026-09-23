"""Completeness checks for the built-in English and Turkish catalogues."""

from __future__ import annotations

from i18n.messages_en import MESSAGES as ENGLISH_MESSAGES
from i18n.messages_tr import MESSAGES as TURKISH_MESSAGES


def test_english_and_turkish_catalogues_expose_the_same_keys() -> None:
    """Ordinary UI text must not rely on an English fallback in Turkish mode."""
    assert set(ENGLISH_MESSAGES) == set(TURKISH_MESSAGES)
