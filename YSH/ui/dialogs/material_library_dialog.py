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
        super().__init__(parent,"Malzeme Kütüphanesi",(("name","Ad"),("designation","Tanım"),("standard","Standart"),("yield_strength_mpa","Akma Dayanımı Rp0,2 (MPa)"),("roughness_mm","Ortalama Pürüzlülük (mm)"),("source","Kaynak")),(("name","Ad"),("designation","Tanım"),("standard","Standart"),("yield_strength_mpa","Akma Dayanımı Rp0,2 (MPa)"),("roughness_mm","Ortalama Pürüzlülük (mm)"),("description","Açıklama"),("source","Kaynak")),service.get_all_materials,service.create_material,service.update_material,service.delete_material,service.get_material,description="Hesaplamalarda kullanılan yerel malzeme özellikleri.",translate=translate,localization_owner=localization_owner,title_key="library.materials",description_key="library.description.materials",column_keys={"name":"library.name","designation":"library.designation","standard":"library.standard","yield_strength_mpa":"field.yield_strength","roughness_mm":"library.average_roughness","source":"field.source"})
