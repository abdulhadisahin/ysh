from pathlib import Path
from i18n import messages_en, messages_tr

ROOT = Path(__file__).resolve().parents[1]


def test_minimum_wall_fills_the_empty_standard_wall_slot_and_is_labelled():
    page = (ROOT / 'ui/pages/pipe_design_page.py').read_text(encoding='utf-8')
    assert "'pipe.minimum_wall' if fallback" in page and 'fallback=nominal is None and minimum is not None' in page
    assert messages_tr.MESSAGES['pipe.minimum_wall'] != messages_en.MESSAGES['pipe.minimum_wall']


def test_result_numbers_never_wrap():
    cards = (ROOT / 'ui/widgets/cards.py').read_text(encoding='utf-8')
    assert "wraplength=0 if ' ' not in text.strip()" in cards
