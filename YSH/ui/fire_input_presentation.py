"""Input-convention hints only; never engineering/source findings or value corrections."""
from dataclasses import dataclass

from engineering.input_parsing import parse_engineering_float
from engineering.validation import ValidationError


@dataclass(frozen=True, slots=True)
class InputClarification:
    field_name: str
    message_key: str
    category: str = 'UI_INPUT_CLARIFICATION'


def foam_percent_clarifications(text: str) -> tuple[InputClarification, ...]:
    """Warn about possible fraction/percent confusion without guessing user intent."""
    try:
        percent = parse_engineering_float(text, field_name='fire.ui.concentration',
            field_key='fire.ui.concentration', allow_empty=True)
    except ValidationError:
        return ()  # Invalid input belongs to existing calculation validation.
    if percent is not None and 0 < percent < 1:
        return (InputClarification('foam_fraction', 'fire.ui.percent_low'),)
    return ()
