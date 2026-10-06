"""Editable D243 circuit/corrosion-allowance library dialog."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from services.corrosion_allowance_circuit_service import CorrosionAllowanceCircuitService
from ui.dialogs.library_dialog import LibraryDialog


class CorrosionAllowanceCircuitLibraryDialog(LibraryDialog):
    """Manage editable D243 defaults without claiming an external standard."""

    def __init__(self, parent: tk.Misc, service: CorrosionAllowanceCircuitService, *, translate: Callable[[str], str] | None = None, localization_owner: object | None = None) -> None:
        def get_item(item_id: object) -> object:
            return next(item for item in service.get_all_circuits() if item.id == item_id)

        super().__init__(
            parent, "Devre / Korozyon Artımı Kütüphanesi",
            (("display_name", "Devre"), ("code", "Kod"), ("default_corrosion_allowance_mm", "Varsayılan Korozyon Artımı (mm)"), ("is_active", "Aktif")),
            (("display_name", "Devre"), ("code", "Kod"), ("default_corrosion_allowance_mm", "Varsayılan Korozyon Artımı (mm)"), ("description", "Açıklama"), ("is_active", "Aktif")),
            service.get_all_circuits, service.create_circuit, service.update_circuit,
            service.delete_circuit, get_item,
            description="D243 için düzenlenebilir varsayılan korozyon artımı değerleri.",
            translate=translate, localization_owner=localization_owner,
            title_key="library.corrosion_allowance_circuits",
            column_keys={"display_name": "field.circuit", "code": "field.circuit_code", "default_corrosion_allowance_mm": "field.default_corrosion_allowance", "is_active": "library.active"},
            field_key_overrides={"display_name": "field.circuit", "code": "field.circuit_code", "default_corrosion_allowance_mm": "field.default_corrosion_allowance"},
        )
