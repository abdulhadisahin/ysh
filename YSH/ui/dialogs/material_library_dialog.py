"""Material-library dialog."""
from __future__ import annotations
import tkinter as tk
from collections.abc import Callable
from services.material_service import MaterialService
from ui.dialogs.library_dialog import LibraryDialog
class MaterialLibraryDialog(LibraryDialog):
    """Edits materials through :class:`MaterialService`."""
    def __init__(self,parent:tk.Misc,service:MaterialService,*,translate:Callable[[str],str]|None=None,localization_owner:object|None=None)->None:
        """Display the local material library."""
        super().__init__(parent,"Materials",(("name","Name"),("designation","Designation"),("standard","Standard"),("yield_strength_mpa","Yield Strength Rp0.2 (MPa)"),("roughness_mm","Average Roughness (mm)"),("source","Source")),(("name","Name"),("designation","Designation"),("standard","Standard"),("yield_strength_mpa","Yield Strength Rp0.2 (MPa)"),("roughness_mm","Average Roughness (mm)"),("description","Description"),("source","Source")),service.get_all_materials,service.create_material,service.update_material,service.delete_material,service.get_material,description="Local material properties used by calculations.",translate=translate,localization_owner=localization_owner,title_key="library.materials",description_key="library.description.materials",column_keys={"name":"library.name","designation":"library.designation","standard":"library.standard","yield_strength_mpa":"field.yield_strength","roughness_mm":"library.average_roughness","source":"field.source"})
