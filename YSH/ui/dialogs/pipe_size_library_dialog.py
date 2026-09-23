"""Pipe-size-library dialog."""
from __future__ import annotations
import tkinter as tk
from collections.abc import Callable
from services.pipe_size_service import PipeSizeService
from ui.dialogs.library_dialog import LibraryDialog
class PipeSizeLibraryDialog(LibraryDialog):
    """Edits pipe sizes through :class:`PipeSizeService`."""
    def __init__(self,parent:tk.Misc,service:PipeSizeService,*,translate:Callable[[str],str]|None=None,localization_owner:object|None=None)->None:
        """Display the local pipe-size library."""
        super().__init__(parent,"Pipe Sizes",(("nominal_diameter","DN"),("outside_diameter_mm","Outside Diameter (mm)"),("wall_thickness_mm","Wall Thickness (mm)"),("inside_diameter_mm","Inside Diameter (mm)"),("standard","Standard")),(("nominal_diameter","DN"),("outside_diameter_mm","Outside Diameter (mm)"),("wall_thickness_mm","Wall Thickness (mm)"),("inside_diameter_mm","Inside Diameter (mm)"),("standard","Standard"),("description","Description")),service.get_all_pipe_sizes,service.create_pipe_size,service.update_pipe_size,service.delete_pipe_size,service.get_pipe_size,description="Local standard pipe dimensions.",translate=translate,localization_owner=localization_owner,title_key="library.pipe_sizes",description_key="library.description.pipe_sizes",column_keys={"outside_diameter_mm":"library.outside_diameter","wall_thickness_mm":"library.wall_thickness","inside_diameter_mm":"library.inside_diameter","standard":"library.standard"})
