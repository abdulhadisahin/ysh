from i18n import messages_en, messages_tr
from i18n.catalog_text import PAIRS, catalog_text, text_key, fluid_display_name


def test_catalog_text_translates_known_and_keeps_unknown():
    tr = lambda k: messages_tr.MESSAGES.get(k, k)
    en = lambda k: messages_en.MESSAGES.get(k, k)
    assert catalog_text(tr, 'Seawater') == 'Deniz Suyu'
    assert catalog_text(en, 'Seawater') == 'Seawater'
    assert catalog_text(tr, 'My own fluid') == 'My own fluid'


def test_pairs_unique_and_catalogs_in_parity():
    assert len({e for e, _ in PAIRS}) == len(PAIRS)
    assert len({text_key(e) for e, _ in PAIRS}) == len(PAIRS)
    assert set(messages_tr.MESSAGES) == set(messages_en.MESSAGES)
    for key in ('catalog.classification.HEAVY_FUEL', 'catalog.classification.CONTROL_AIR', 'catalog.classification.STARTING_AIR'):
        assert key in messages_tr.MESSAGES


def test_fluid_display_name_respects_edits():
    assert fluid_display_name('SEAWATER', 'Seawater') == 'Deniz Suyu'
    assert fluid_display_name('SEAWATER', 'Edited') == 'Edited'
