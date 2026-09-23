"""Render semantic validation issues through the active YSH translator."""

from __future__ import annotations

from engineering.validation import ValidationIssue
from i18n.translator import Translator


def render_validation_issue(issue: ValidationIssue, translator: Translator | object) -> str:
    """Resolve one issue using the language active when presentation occurs."""
    translate = getattr(translator, "translate")
    if issue.code == "dependency_required":
        return translate("validation.suction_loss_required")
    key = f"validation.{issue.code}"
    arguments = dict(issue.params or {})
    if issue.field_key is not None:
        arguments["field_name"] = translate(issue.field_key)
    return translate(key, **arguments)
