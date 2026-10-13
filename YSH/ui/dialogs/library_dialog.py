"""Reusable ttk editor for local engineering-library records."""

from __future__ import annotations

import tkinter as tk
import logging
from collections.abc import Callable, Sequence
from tkinter import messagebox, ttk
from typing import Any
from uuid import UUID

from engineering.input_parsing import parse_engineering_float
from engineering.validation import ValidationError
from i18n.validation import render_validation_issue
from i18n.translator import Translator
from ui.theme.spacing import MD, SM
from ui.widgets.scrollable_treeview import ScrollableTreeview
from ui.widgets.engineering_components import EmptyState
from ui.formatting import format_user_number

LOGGER = logging.getLogger(__name__)


class LibraryDialog:
    """Provide a consistent searchable CRUD surface for a service-backed library."""

    def __init__(
        self,
        parent: tk.Misc,
        title: str,
        columns: Sequence[tuple[str, str]],
        fields: Sequence[tuple[str, str]],
        list_items: Callable[[], Sequence[Any]],
        create_item: Callable[..., Any],
        update_item: Callable[[Any], Any],
        delete_item: Callable[[UUID], None],
        get_item: Callable[[UUID], Any],
        *,
        description: str = "",
        allow_create: bool = True,
        allow_delete: bool = True,
        translate: Callable[[str], str] | None = None,
        localization_owner: object | None = None,
        title_key: str | None = None,
        column_keys: dict[str, str] | None = None,
        description_key: str | None = None,
        display_value_keys: dict[str, str] | None = None,
        field_key_overrides: dict[str, str] | None = None,
    ) -> None:
        """Create a modal library editor using only supplied service operations."""
        # Standalone library editors must match the Turkish-only D243 shell;
        # the main window still supplies its active translator explicitly.
        self._translate = translate or Translator("tr").translate
        self._localization_owner = localization_owner
        self._title = title
        self._title_key = title_key
        self._column_keys = column_keys or {}
        self._description_key = description_key
        self._display_value_keys = display_value_keys or {}
        self._field_key_overrides = field_key_overrides or {}
        self._columns = columns
        self._fields = fields
        self._list_items = list_items
        self._create_item = create_item
        self._update_item = update_item
        self._delete_item = delete_item
        self._get_item = get_item
        self._description = description
        self._allow_create = allow_create
        self._allow_delete = allow_delete
        self._dialog = tk.Toplevel(parent)
        self._dialog.title(self._text(title_key, title))
        self._dialog.transient(parent)
        self._dialog.geometry("980x620")
        self._dialog.minsize(760, 460)
        self._build()
        self._refresh()
        self._dialog.grab_set()
        self._dialog.bind("<Escape>", lambda _event: self._close())
        if localization_owner is not None:
            register = getattr(localization_owner, "register_localizable", None)
            if callable(register):
                register(self)

    def _build(self) -> None:
        frame = ttk.Frame(self._dialog, style="Dialog.TFrame", padding=MD)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(3, weight=1)
        self._title_label = ttk.Label(frame, text=self._text(self._title_key, self._title), style="DialogTitle.TLabel")
        self._title_label.grid(
            row=0, column=0, sticky="w"
        )
        if self._description:
            self._description_label = ttk.Label(frame, text=self._text(self._description_key, self._description), style="DialogHint.TLabel");self._description_label.grid(
                row=1, column=0, sticky="w", pady=(SM // 2, 0)
            )
        toolbar = ttk.Frame(frame)
        self._toolbar = toolbar
        toolbar.grid(row=2, column=0, sticky="ew", pady=(MD, SM))
        self._search_label = ttk.Label(toolbar, text=self._translate("library.search"))
        self._search_label.pack(side="left")
        self._search = tk.StringVar()
        self._search.trace_add("write", lambda *_args: self._refresh())
        ttk.Entry(toolbar, textvariable=self._search, width=40).pack(
            side="left", padx=(SM, 0)
        )
        if self._allow_create:
            self._add_button = ttk.Button(toolbar, text=self._translate("common.add"), command=self._add, style="Primary.TButton");self._add_button.pack(side="right")
        self._tree_container = ScrollableTreeview(
            frame,
            columns=[key for key, _ in self._columns],
            show="headings",
            selectmode="browse",
        )
        self._tree = self._tree_container.tree
        self._tree.configure(style="Library.Treeview")
        numeric_columns = {
            "yield_strength_mpa", "roughness_mm", "outside_diameter_mm",
            "wall_thickness_mm", "inside_diameter_mm", "value",
        }
        for key, label in self._columns:
            self._tree.heading(key, text=label)
            self._tree.column(
                key, width=150, anchor="e" if key in numeric_columns else "w"
            )
        self._tree_container.grid(row=3, column=0, sticky="nsew")
        self._empty_state = EmptyState(frame, "library", "Kütüphane boş", "Yeni kayıt ekleyerek kütüphaneyi doldurabilirsiniz.", image_size=160)
        self._empty_state.grid(row=3, column=0, sticky="nsew")
        self._empty_state.grid_remove()
        self._tree.bind("<<TreeviewSelect>>", self._show_selected_details)
        self._tree.bind("<Double-1>", lambda _event: self._edit())
        self._tree.bind("<Return>", lambda _event: self._edit())
        self._tree.bind("<Delete>", lambda _event: self._delete())
        self._status = tk.StringVar(value="")
        self._details = tk.StringVar(value="")
        bottom = ttk.Frame(frame)
        bottom.grid(row=4, column=0, sticky="ew", pady=(SM, 0))
        ttk.Label(bottom, textvariable=self._status, style="Info.TLabel").pack(side="left")
        ttk.Label(bottom, textvariable=self._details, wraplength=500, style="Info.TLabel").pack(
            side="left", padx=(MD, 0)
        )
        actions = ttk.Frame(frame)
        actions.grid(row=5, column=0, sticky="e", pady=(SM, 0))
        self._edit_button = ttk.Button(actions, text=self._translate("common.edit"), command=self._edit, style="Secondary.TButton");self._edit_button.pack(side="left")
        if self._allow_delete:
            self._delete_button = ttk.Button(actions, text=self._translate("common.delete"), command=self._delete, style="Danger.TButton");self._delete_button.pack(
                side="left", padx=(SM, 0)
            )
        self._close_button = ttk.Button(actions, text=self._translate("common.close"), command=self._close, style="Neutral.TButton");self._close_button.pack(
            side="left", padx=(MD, 0)
        )

    def _refresh(self) -> None:
        selected = self._tree.selection()
        for row in self._tree.get_children():
            self._tree.delete(row)
        query = self._search.get().casefold().strip()
        records = list(self._list_items())
        visible = 0
        for item in records:
            values = tuple(self._display(item, key) for key, _ in self._columns)
            if not query or query in " ".join(values).casefold():
                self._tree.insert("", "end", iid=str(item.id), values=values)
                visible += 1
        self._status.set(
            self._translate("library.no_records") if not visible else self._translate("library.record_count", count=visible)
        )
        (self._tree_container.grid_remove if not visible else self._tree_container.grid)()
        (self._empty_state.grid if not visible else self._empty_state.grid_remove)()
        if selected and self._tree.exists(selected[0]):
            self._tree.selection_set(selected[0])
            self._show_selected_details()
        else:
            self._details.set("")

    def _display(self, item: Any, key: str) -> str:
        value = getattr(item, key)
        if value is None:
            return self._translate("library.not_verified")
        if key == "default_corrosion_allowance_mm":
            return format_user_number(float(value))
        if key == "is_active":
            return "Evet" if value else "Hayır"
        return self._translate(self._display_value_keys[value]) if value in self._display_value_keys else str(value)

    def refresh_texts(self) -> None:
        """Refresh the open library shell without replacing rows or selection."""
        self._search_label.configure(text=self._translate("library.search"))
        title = self._text(self._title_key, self._title)
        self._dialog.title(title)
        self._title_label.configure(text=title)
        if hasattr(self, "_description_label"):
            self._description_label.configure(text=self._text(self._description_key, self._description))
        for key, _label in self._columns:
            self._tree.heading(key, text=self._text(self._column_keys.get(key), _label))
        self._add_button.configure(text=self._translate("common.add")) if hasattr(self,"_add_button") else None
        self._edit_button.configure(text=self._translate("common.edit"))
        self._delete_button.configure(text=self._translate("common.delete")) if hasattr(self,"_delete_button") else None
        self._close_button.configure(text=self._translate("common.close"))
        self._show_selected_details()

    def _text(self, key: str | None, fallback: str) -> str:
        """Resolve a semantic display key while retaining legacy dialog support."""
        return self._translate(key) if key is not None else fallback

    def _show_selected_details(self, _event: object | None = None) -> None:
        item = self._selected()
        if item is None:
            self._details.set("")
            return
        self._details.set(
            " | ".join(
                f"{self._text(self._column_keys.get(key), label)}: {self._display(item, key)}"
                for key, label in self._columns
            )
        )

    def _selected(self) -> Any | None:
        selected = self._tree.selection()
        return self._get_item(UUID(selected[0])) if selected else None

    def _add(self) -> None:
        self._open_editor(None)

    def _edit(self) -> None:
        item = self._selected()
        if item is not None:
            self._open_editor(item)

    def _open_editor(self, item: Any | None) -> None:
        editor = tk.Toplevel(self._dialog)
        editor.title(
            self._translate("dialog.library_record_edit")
            if item is not None
            else self._translate("dialog.library_record_add")
        )
        editor.transient(self._dialog)
        editor.grab_set()
        body = ttk.Frame(editor, style="Dialog.TFrame", padding=MD)
        body.grid()
        variables: dict[str, tk.StringVar] = {}
        for row, (key, label) in enumerate(self._fields):
            ttk.Label(
                body, text=f"{self._field_label(key, label)}:"
            ).grid(row=row, column=0, sticky="w", pady=SM // 2)
            initial = "" if item is None or getattr(item, key) is None else str(getattr(item, key))
            variables[key] = tk.StringVar(value="Evet" if item is None and key == "is_active" else initial)
            ttk.Entry(body, textvariable=variables[key], width=48).grid(
                row=row, column=1, sticky="ew", padx=(SM, 0), pady=SM // 2
            )

        def save() -> None:
            try:
                values = {key: self._convert(key, variable.get().strip()) for key, variable in variables.items()}
                if item is None:
                    self._create_item(**values)
                else:
                    for key, value in values.items():
                        setattr(item, key, value)
                    self._update_item(item)
            except ValidationError as error:
                messagebox.showerror(
                    self._translate("dialog.error"),
                    render_validation_issue(error.issue, _TranslatorAdapter(self._translate)),
                    parent=editor,
                )
                return
            except (ValueError, LookupError):
                LOGGER.exception("Library record validation failed unexpectedly.")
                messagebox.showerror(
                    self._translate("dialog.error"),
                    self._translate("validation.unexpected_error"),
                    parent=editor,
                )
                return
            editor.destroy()
            self._refresh()

        buttons = ttk.Frame(body)
        buttons.grid(row=len(self._fields), column=1, sticky="e", pady=(MD, 0))
        ttk.Button(buttons, text=self._translate("common.cancel"), command=editor.destroy, style="Neutral.TButton").pack(side="left")
        ttk.Button(buttons, text=self._translate("common.save"), command=save, style="Success.TButton").pack(side="left", padx=(SM, 0))
        editor.bind("<Return>", lambda _event: save())
        editor.bind("<Escape>", lambda _event: editor.destroy())
        editor.focus_set()

    def _convert(self, key: str, value: str) -> object:
        labels = {
            "yield_strength_mpa": "Akma Dayanımı Rp0,2 (MPa)",
            "roughness_mm": "Ortalama Pürüzlülük (mm)",
            "outside_diameter_mm": "Dış Çap (mm)",
            "wall_thickness_mm": "Et Kalınlığı (mm)",
            "inside_diameter_mm": "İç Çap (mm)",
            "value": "Mühendislik Sabiti Değeri",
            "default_corrosion_allowance_mm": "Varsayılan Korozyon Artımı (mm)",
        }
        field_name = labels.get(key, key.replace("_", " ").title())
        field_key = self._field_key_overrides.get(key, self._field_key(key))
        if key == "yield_strength_mpa":
            return parse_engineering_float(value, field_name=field_name, allow_empty=True, field_key=field_key)
        if key in {"roughness_mm", "outside_diameter_mm", "wall_thickness_mm", "inside_diameter_mm", "value", "default_corrosion_allowance_mm"}:
            return parse_engineering_float(value, field_name=field_name, field_key=field_key)
        if key == "is_active":
            return value.strip().casefold() in {"1", "evet", "true"}
        return value

    @staticmethod
    def _field_key(key: str) -> str | None:
        """Map editable record attributes to stable validation field keys."""
        return {
            "nominal_diameter": "field.dn",
            "outside_diameter_mm": "field.outside_diameter",
            "wall_thickness_mm": "field.wall_thickness",
            "inside_diameter_mm": "field.inside_diameter",
            "standard": "field.standard",
            "name": "field.material_name",
            "designation": "field.designation",
            "yield_strength_mpa": "field.yield_strength_rp02",
            "roughness_mm": "field.average_roughness",
            "source": "field.source",
            "description": "project.description",
            "display_name": "library.engineering_constant",
            "unit": "library.unit",
            "value": "field.constant_value",
            "code": "field.circuit_code",
            "default_corrosion_allowance_mm": "field.default_corrosion_allowance",
        }.get(key)

    def _field_label(self, key: str, fallback: str) -> str:
        """Return the localized label for an editable field."""
        field_key = self._field_key_overrides.get(key, self._field_key(key))
        return self._translate(field_key) if field_key is not None else fallback

    def _delete(self) -> str:
        if not self._allow_delete:
            return "break"
        item = self._selected()
        if item is None:
            return "break"
        label = getattr(item, "display_name", getattr(item, "name", getattr(item, "key", "kayıt")))
        if messagebox.askyesno(
            self._translate("dialog.delete_library_record"),
            self._translate("confirm.delete_library_record", label=label),
            parent=self._dialog,
        ):
            try:
                self._delete_item(item.id)
            except ValidationError as error:
                messagebox.showerror(
                    self._translate("dialog.error"),
                    render_validation_issue(error.issue, _TranslatorAdapter(self._translate)),
                    parent=self._dialog,
                )
                return "break"
            except (ValueError, LookupError):
                LOGGER.exception("Unable to delete library record.")
                messagebox.showerror(
                    self._translate("dialog.error"),
                    self._translate("validation.unexpected_error"),
                    parent=self._dialog,
                )
                return "break"
            self._refresh()
        return "break"

    def _close(self) -> str:
        """Unregister and close the library editor dialog."""
        if self._localization_owner is not None:
            unregister = getattr(self._localization_owner, "unregister_localizable", None)
            if callable(unregister):
                unregister(self)
        self._dialog.grab_release()
        self._dialog.destroy()
        return "break"

class _TranslatorAdapter:
    """Adapt a translation callable to the semantic validation renderer."""

    def __init__(self, translate: Callable[[str], str]) -> None:
        """Store the active translation callable."""
        self.translate = translate
