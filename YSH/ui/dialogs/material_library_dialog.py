"""Material-library dialog."""
from __future__ import annotations
import tkinter as tk
from services.material_service import MaterialService
from ui.dialogs.library_dialog import LibraryDialog
class MaterialLibraryDialog(LibraryDialog):
    """Edits materials through :class:`MaterialService`."""
    def __init__(self,parent:tk.Misc,service:MaterialService)->None:
        """Display the local material library."""
        super().__init__(parent,"Materials",(("name","Name"),("designation","Designation"),("standard","Standard"),("yield_strength_mpa","Yield Strength (MPa)"),("roughness_mm","Roughness (mm)"),("source","Source")),(("name","Name"),("designation","Designation"),("standard","Standard"),("yield_strength_mpa","Yield Strength (MPa)"),("roughness_mm","Roughness (mm)"),("description","Description"),("source","Source")),service.get_all_materials,service.create_material,service.update_material,service.delete_material,service.get_material)
