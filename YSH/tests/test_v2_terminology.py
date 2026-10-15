"""V2 visible terminology and numerical freeze contracts, without a display."""
from pathlib import Path
from types import SimpleNamespace
import pytest
from i18n.terminology import TERMS_TR, MESSAGE_SYMBOLS
from i18n.translator import Translator
from ui.pages.pipe_design_page import PipeDesignPage
from ui.pages.discharge_head_loss_page import DischargeHeadLossPage
from ui.pages.suction_npsh_page import SuctionNPSHPage
from ui.widgets.formula_view import _MATHTEXT_LINES

ROOT = Path(__file__).resolve().parents[1]

@pytest.mark.parametrize(("symbol", "term"), [
    ("v", "Kaynak faktörü"),
    ("Hgeo", "Statik basma yüksekliği"),
    ("HEgeo", "Statik emme yüksekliği"),
    ("NPSHr", "Gerekli Net Pozitif Emme Yüksekliği"),
    ("ENPYm", "Mevcut Net Pozitif Emme Yüksekliği"),
    ("D", "Gerekli teorik iç çap"), ("Di", "Boru iç çapı"),
    ("k", "Mutlak pürüzlülük"), ("K", "Lokal kayıp katsayısı"),
])
def test_locked_terms(symbol, term):
    assert TERMS_TR[symbol] == term
    assert Translator("tr").translate(f"engineering.{symbol}") == term

def test_every_visible_alias_uses_the_authoritative_term_in_both_languages():
    for language in ("tr", "en"):
        tr = Translator(language)
        for key, symbol in MESSAGE_SYMBOLS.items():
            assert tr.translate(key) == tr.translate(f"engineering.{symbol}")

def _sections(page):
    stub = SimpleNamespace(_translate=Translator("tr").translate,
        _diameter_result=None, _wall_result=None, _last_result=None,
        _last_loss=None, _last_enpy=None)
    return page._formula_sections(stub)

def test_actual_pipe_formula_flow_uses_v_including_mathtext():
    sections = _sections(PipeDesignPage)
    text = "\n".join(section.text for section in sections)
    equation = "s0 = (da × pc) / ((20 × σallow × v) + pc)"
    assert all(not section.asset_names for section in sections)
    assert equation in text
    assert "v | Kaynak faktörü | −" in text
    assert not any(line.startswith("w |") for line in text.splitlines()) and "σallow × w" not in text
    assert r"allow}}v" in _MATHTEXT_LINES[equation]
    assert r"allow}}w" not in _MATHTEXT_LINES[equation]

def test_actual_hydraulic_formula_variables_keep_physical_quantities_distinct():
    for page in (DischargeHeadLossPage, SuctionNPSHPage):
        sections = _sections(page)
        assert all(not section.asset_names for section in sections)
        text = "\n".join(section.text for section in sections)
        assert "Di | Boru iç çapı | mm" in text
        assert "k | Mutlak pürüzlülük | mm" in text
        assert "D | Boru iç çapı" not in text
        assert "V = 4Q / (πDi²)" in text
    discharge = "\n".join(s.text for s in _sections(DischargeHeadLossPage))
    assert "Hgeo | Statik basma yüksekliği | m" in discharge
    assert "K | Lokal kayıp katsayısı | −" in discharge
    assert "hf | Boru sürtünme kaybı | m" in discharge
    assert "hL | Lokal yük kaybı | m" in discharge
    suction = "\n".join(s.text for s in _sections(SuctionNPSHPage))
    assert "HEgeo | Statik emme yüksekliği | m" in suction
    assert "NPSHr | Gerekli Net Pozitif Emme Yüksekliği | m" in suction
    assert "ΔENPY = ENPYm − NPSHr" in suction
    assert "ENPYm | Mevcut Net Pozitif Emme Yüksekliği | m" in suction

def test_transfer_flow_symbols_are_preserved_without_a_new_allowable_flow():
    assert "qallow" not in {s.lower() for s in TERMS_TR}
    source = (ROOT / "ui/pages/transfer_pump_page.py").read_text(encoding="utf-8")
    assert "Q12" in source and "Qpump = m × Vfuel + b" in source
    assert "qallow" not in source.lower()
    assert "Q" in TERMS_TR

def test_representative_engineering_values_match_pre_phase_snapshot():
    """Frozen values were captured with Python 3.14.8 before presentation edits."""
    from engineering.pipe_design.calculator import PipeDesignCalculator
    from engineering.pipe_design.models import PipeDiameterInput,WallThicknessInput
    from engineering.head_loss.calculator import DischargeHeadLossCalculator
    from engineering.head_loss.models import DischargeHeadLossInput
    from engineering.suction_npsh.calculator import SuctionNPSHCalculator
    from engineering.suction_npsh.models import SuctionNPSHInput
    from engineering.transfer_pump.calculator import TransferPumpCalculator
    from engineering.transfer_pump.models import TransferPumpInput
    from core.local_loss_item import LocalLossItem
    from core.pump_reference import PumpReference
    p=PipeDesignCalculator()
    w=p.calculate_wall_thickness(WallThicknessInput(100,16,195,1.8,.85,1,True,300))
    d=DischargeHeadLossCalculator().calculate(DischargeHeadLossInput(100,20,2e-6,20,.015,7,[LocalLossItem('X',1,3)]))
    s=SuctionNPSHCalculator().calculate(SuctionNPSHInput(100,20,2e-6,20,.015,[LocalLossItem('X',1,3)],120000,3000,850,2))
    t=TransferPumpCalculator().calculate(TransferPumpInput(250,[PumpReference('A',100,20),PumpReference('B',200,30),PumpReference('C',300,40)]))
    values = {
        "diameter": p.calculate_diameter(PipeDiameterInput(100, 2)).diameter_mm,
        "stress": w.allowable_stress_mpa,
        "base": w.base_wall_thickness_mm,
        "bend": w.bend_allowance_mm,
        "wall": w.final_wall_thickness_mm,
        "discharge_pipe": d.pipe_friction_loss_m,
        "discharge_local": d.local_loss_m,
        "suction": s.suction_line_loss_m,
        "enpy": s.enpym_available_m,
        "slope": t.regression_model.slope,
        "intercept": t.regression_model.intercept,
        "r_squared": t.regression_model.r_squared,
        "time": t.estimated_emptying_time_hours,
    }

    assert values == {
        "base": 0.8612955320294277,
        "bend": 0.11483940427059035,
        "diameter": 132.9807601338109,
        "discharge_local": 0.0768,
        "discharge_pipe": 0.1179633563757915,
        "enpy": 11.841330398732161,
        "intercept": 10.0,
        "r_squared": 1.0,
        "slope": 0.1,
        "stress": 108.33333333333333,
        "suction": 0.1947633563757915,
        "time": 7.142857142857143,
        "wall": 1.976134936300018
    }
