"""Build-only frozen payload probe; never included in the release directory.

Run only against a disposable profile supplied as the first argument. The
probe uses the same PYZ, runtime hooks and collected files as D243.exe.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import time
import traceback


def main() -> None:
    """Exercise the frozen payload without touching the normal user profile."""
    if len(sys.argv) != 2:
        raise SystemExit("Supply one disposable profile directory.")
    profile = Path(sys.argv[1]).resolve()
    profile.mkdir(parents=True, exist_ok=True)
    os.environ["LOCALAPPDATA"] = str(profile)
    started = time.perf_counter()
    checks: dict[str, object] = {"frozen": bool(getattr(sys, "frozen", False))}
    result_path = profile / "package_probe.json"
    try:
        import tkinter as tk
        from YSH.app import YSHApplication
        from paths import ApplicationPaths
        from ui import assets
        from ui.widgets.asset_loader import AssetImageLoader
        from ui.widgets.formula_view import FormulaReferencePanel
        from engineering.pipe_design.calculator import PipeDesignCalculator
        from engineering.pipe_design.models import PipeDiameterInput, WallThicknessInput
        from engineering.transfer_pump.v2_models import TransferPumpDesignInput
        from ui.widgets.transfer_pump_chart import TransferPumpChartModel

        app = YSHApplication()
        original_mainloop = tk.Tk.mainloop

        def mainloop(root: tk.Tk, *args: object, **kwargs: object) -> None:
            window = app._main_window
            root.update()
            checks["window_constructed_s"] = round(time.perf_counter() - started, 2)
            checks["main_window"] = bool(root.winfo_viewable())
            checks["tcl"] = str(root.tk.call("info", "patchlevel"))
            checks["tk"] = str(root.tk.call("package", "require", "Tk"))
            checks["bundled_tcl_path"] = str(root.tk.call("info", "library"))
            checks["bundled_tk_path"] = str(root.tk.getvar("tk_library"))
            assert "_tcl_data" in str(checks["bundled_tcl_path"])
            assert "_tk_data" in str(checks["bundled_tk_path"])
            paths = ApplicationPaths()
            assert paths.user_root.is_relative_to(profile)
            for getter in (assets.d243_main_logo_path, assets.d243_watermark_logo_path,
                           assets.d243_production_icon_path, assets.d243_logo_path):
                assert getter() is not None
            for key in assets.ACTION_ICON_FILENAMES:
                assert assets.action_icon_path(key) is not None
            for key in assets.FORMULA_ASSET_FILENAMES:
                image = AssetImageLoader.load(root, assets.formula_asset_path(key), 200)
                assert image is not None
            checks["branding_png_alpha_resize"] = "PASS"
            assert FormulaReferencePanel._render_mathtext_image(root, r"h_f=6.4\times10^6\frac{fLQ^2}{D_i^5}") is not None
            checks["mathtext_fonts"] = "PASS"
            pipe = PipeDesignCalculator()
            assert pipe.calculate_diameter(PipeDiameterInput(20, 2)).diameter_mm > 0
            assert pipe.calculate_wall_thickness(WallThicknessInput(
                100, 16, 195, 1.8, .85, 1)).bend_allowance_mm == 0
            checks["pipe_calculator"] = "PASS"
            from engineering.head_loss.v2_models import DischargeV2Input
            from engineering.suction_npsh.v2_models import SuctionV2Input, ENPYV2Input
            from engineering.pipe_design.transfer import PipeInputState, PipeValues
            from engineering.formula.discharge import hydraulic_steps
            from engineering.formula.suction import suction_steps
            from engineering.formula.transfer import design_steps
            manual = PipeInputState(manual_values=PipeValues(
                actual_internal_diameter_mm=101, flow_rate_m3_h=20))
            discharge = app._discharge_head_loss_service.calculate_v2(DischargeV2Input(
                pipe_input=manual, kinematic_viscosity_m2s=2e-6,
                pipe_length_m=20, roughness_mm=.015, geodetic_head_m=2))
            suction = app._suction_npsh_service.calculate_v2(SuctionV2Input(
                pipe_input=manual, viscosity=2, viscosity_unit="cSt",
                pipe_length_m=20, roughness_mm=.015), ENPYV2Input(
                suction_pressure=1.01325, suction_pressure_unit="bar",
                vapour_pressure=.023, vapour_pressure_unit="bar",
                density_kg_m3=1000, static_suction_height_m=2))
            assert discharge.pipe_friction_loss_m >= 0 and suction.hydraulic.pipe_friction_loss_m >= 0
            checks["discharge_calculator"] = "PASS"
            checks["suction_enpy_calculator"] = "PASS"
            design = app._transfer_pump_service.calculate_v2(TransferPumpDesignInput(
                transfer_volume_m3=120, target_transfer_time_h=3))
            assert design.required_flow_m3_h == 40
            checks["transfer_design_calculator"] = "PASS"
            for steps in (hydraulic_steps(discharge), suction_steps(suction), design_steps(design)):
                panel = FormulaReferencePanel(root, lambda: [], window._translate,
                                              step_provider=lambda used=steps: used)
                panel.toggle()
                root.update_idletasks()
                assert panel._content.winfo_children()
                panel.destroy()
            checks["typed_formula_step_renderer"] = "PASS"
            pages = window._pages
            assert {"pipe_design", "transfer_pump", "discharge_head_loss", "suction_npsh"} <= pages.keys()
            for key, page in pages.items():
                window._page_host.select(window._page_host._page_keys[key])
                root.update()
                page._formula_panel.toggle()
                root.update()
                assert page._formula_panel.expanded
                page._formula_panel.toggle()
                checks[key + "_page_formula"] = "PASS"
            # A real TkAgg canvas is exercised even with an empty factory library.
            chart = pages["transfer_pump"]._chart
            chart.winfo_ismapped = lambda: True
            chart.render(TransferPumpChartModel((), (), None, None, None, None))
            root.update_idletasks()
            assert chart._canvas is not None
            checks["tkagg"] = "PASS"
            persistence = app._project_persistence_service
            project = persistence.create_project("PACKAGING PROBE - disposable data")
            persistence.save({"pipe_design": {"probe": "saved"}})
            persistence.close()
            _, state = persistence.open(project.id)
            assert state["pipe_design"]["probe"] == "saved"
            checks["project_create_save_reopen"] = "PASS"
            for database in (app._project_database, app._library_database):
                with database.connection() as connection:
                    assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
                    assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            checks["sqlite_foreign_keys_integrity"] = "PASS"
            window._open_material_library()
            root.update()
            assert window._library_window.winfo_exists()
            window._library_window._close()
            checks["library"] = "PASS"
            window._open_calculation_history()
            root.update()
            assert window._history_window.winfo_exists()
            window._history_window._close()
            checks["history"] = "PASS"
            window._close()
            checks["normal_close"] = "PASS"

        tk.Tk.mainloop = mainloop
        try:
            app.run()
        finally:
            tk.Tk.mainloop = original_mainloop
        assert checks["main_window"]
        checks["result"] = "PASS"
    except BaseException:
        checks["result"] = "FAIL"
        checks["traceback"] = traceback.format_exc()
    result_path.write_text(json.dumps(checks, ensure_ascii=False, indent=2), encoding="utf-8")
    if checks["result"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
