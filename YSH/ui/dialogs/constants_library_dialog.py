"""Engineering-constants-library dialog."""
from __future__ import annotations
import tkinter as tk
from services.engineering_constant_service import EngineeringConstantService
from ui.dialogs.library_dialog import LibraryDialog
class ConstantsLibraryDialog(LibraryDialog):
    """Edits engineering constants through their service."""
    def __init__(self,parent:tk.Misc,service:EngineeringConstantService)->None:
        """Display the editable engineering constants."""
        super().__init__(parent,"Engineering Constants",(("key","Key"),("display_name","Display Name"),("value","Value"),("unit","Unit"),("source","Source")),(("key","Key"),("display_name","Display Name"),("value","Value"),("unit","Unit"),("description","Description"),("source","Source")),service.get_all_constants,service.create_constant,service.update_constant,service.delete_constant,lambda item_id: next(item for item in service.get_all_constants() if item.id==item_id))
