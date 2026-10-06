"""Standard-filtered pipe-size-library dialog."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable, Sequence
from tkinter import ttk
from uuid import UUID

from core.pipe_size import PipeSize
from core.pipe_standard import PipeStandard
from engineering.validation import ValidationError, ValidationIssue
from services.pipe_size_service import PipeSizeService
from ui.dialogs.library_dialog import LibraryDialog
from ui.theme.spacing import MD, SM


class PipeSizeLibraryDialog(LibraryDialog):
    """Edit dimensions belonging only to the visibly selected pipe standard."""

    def __init__(
        self,
        parent: tk.Misc,
        service: PipeSizeService,
        *,
        translate: Callable[[str], str] | None = None,
        localization_owner: object | None = None,
    ) -> None:
        self._pipe_size_service = service
        self._standard = tk.StringVar()
        self._standard_ids: dict[str, UUID] = {}
        self._selected_standard_id: UUID | None = None
        super().__init__(
            parent,
            "Boru Ölçüleri Kütüphanesi",
            (("nominal_diameter", "DN"), ("outside_diameter_mm", "Dış Çap (mm)"),
             ("wall_thickness_mm", "Et Kalınlığı (mm)"), ("inside_diameter_mm", "İç Çap (mm)"),
             ("standard", "Standart")),
            (("nominal_diameter", "DN"), ("outside_diameter_mm", "Dış Çap (mm)"),
             ("wall_thickness_mm", "Et Kalınlığı (mm)"), ("inside_diameter_mm", "İç Çap (mm)"),
             ("description", "Açıklama")),
            self._list_selected_standard_sizes,
            self._create_selected_standard_size,
            service.update_pipe_size,
            service.delete_pipe_size,
            service.get_pipe_size,
            description="Anma çapı seçimi için kullanılan yerel standart boru ölçüleri.",
            translate=translate,
            localization_owner=localization_owner,
            title_key="library.pipe_sizes",
            description_key="library.description.pipe_sizes",
            column_keys={"outside_diameter_mm": "library.outside_diameter", "wall_thickness_mm": "library.wall_thickness", "inside_diameter_mm": "library.inside_diameter", "standard": "library.standard"},
        )
        self._standard_label = ttk.Label(self._toolbar, text=self._translate("field.pipe_standard"))
        self._standard_label.pack(side="left", padx=(MD, 0))
        self._standard_box = ttk.Combobox(self._toolbar, textvariable=self._standard, state="readonly", width=28)
        self._standard_box.pack(side="left", padx=(SM, 0))
        self._standard_box.bind("<<ComboboxSelected>>", self._on_standard_changed)
        self._load_standards()

    def _load_standards(self) -> None:
        """Fill the selector from active standard entities using friendly names."""
        self._standard_ids.clear()
        labels: list[str] = []
        preferred_label = ""
        for standard in self._pipe_size_service.get_available_standards():
            label = self._friendly_standard_label(standard, labels)
            labels.append(label)
            self._standard_ids[label] = standard.id
            if standard.code == PipeSizeService.DEFAULT_STANDARD_CODE:
                preferred_label = label
        self._standard_box.configure(values=labels)
        self._standard.set(preferred_label or (labels[0] if labels else ""))
        self._selected_standard_id = self._standard_ids.get(self._standard.get())
        self._refresh()

    @staticmethod
    def _friendly_standard_label(standard: PipeStandard, used_labels: Sequence[str]) -> str:
        """Avoid raw migration identifiers while retaining a readable disambiguator."""
        label = standard.display_name
        return label if label not in used_labels else f"{label} ({standard.source})"

    def _on_standard_changed(self, _event: object | None = None) -> None:
        self._selected_standard_id = self._standard_ids.get(self._standard.get())
        self._refresh()

    def _list_selected_standard_sizes(self) -> Sequence[PipeSize]:
        """Return no cross-standard rows; selection is mandatory for this screen."""
        if self._selected_standard_id is None:
            return ()
        return self._pipe_size_service.get_pipe_sizes_for_standard(self._selected_standard_id)

    def _create_selected_standard_size(self, **values: object) -> PipeSize:
        """Create dimensions explicitly bound to the selected standard."""
        if self._selected_standard_id is None:
            raise ValidationError(ValidationIssue("pipe_standard_required"))
        return self._pipe_size_service.create_pipe_size(**values, standard_id=self._selected_standard_id)

    def _refresh(self) -> None:
        super()._refresh()
        if not hasattr(self, "_standard_box"):
            return
        if self._selected_standard_id is None:
            self._status.set(self._translate("pipe.standard.no_available"))
        elif not self._tree.get_children():
            self._status.set(self._translate("pipe.standard.no_geometry"))

    def refresh_texts(self) -> None:
        super().refresh_texts()
        self._standard_label.configure(text=self._translate("field.pipe_standard"))
