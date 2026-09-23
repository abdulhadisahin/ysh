"""Engineering-constants-library dialog."""
from __future__ import annotations
import tkinter as tk
from collections.abc import Callable
from services.engineering_constant_service import EngineeringConstantService
from ui.dialogs.library_dialog import LibraryDialog
class ConstantsLibraryDialog(LibraryDialog):
    """Edits engineering constants through their service."""
    def __init__(self,parent:tk.Misc,service:EngineeringConstantService,*,translate:Callable[[str],str]|None=None,localization_owner:object|None=None)->None:
        """Display the editable engineering constants."""
        super().__init__(parent,"Engineering Constants",(("display_name","Engineering Constant"),("value","Value"),("unit","Unit"),("source","Source")),(("display_name","Engineering Constant"),("value","Value"),("unit","Unit"),("description","Description"),("source","Source")),service.get_all_constants,service.create_constant,service.update_constant,service.delete_constant,lambda item_id: next(item for item in service.get_all_constants() if item.id==item_id),description="Approved constants used by the calculation engine.",allow_create=False,allow_delete=False,translate=translate,localization_owner=localization_owner,title_key="library.constants",description_key="library.description.constants",column_keys={"display_name":"library.engineering_constant","value":"library.value","unit":"library.unit","source":"field.source"},display_value_keys={"Corrosion Allowance":"constant.corrosion_allowance","Design Pressure":"constant.design_pressure","Display Decimal Places":"constant.display_decimal_places","Safety Factor":"constant.safety_factor","Weld Factor":"constant.weld_factor"})
