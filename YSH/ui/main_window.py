"""Main Tkinter window for YSH."""

from __future__ import annotations

import logging
import math
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import messagebox, ttk
from uuid import UUID

from core.constants import (
    WINDOW_HEIGHT,
    WINDOW_MINIMUM_HEIGHT,
    WINDOW_MINIMUM_WIDTH,
    WINDOW_WIDTH,
)
from core.project import Project
from services.project_service import (
    ProjectConflictError,
    ProjectService,
    ProjectValidationError,
)
from services.material_service import MaterialService
from services.pipe_size_service import PipeSizeService
from services.engineering_constant_service import EngineeringConstantService
from services.corrosion_allowance_circuit_service import CorrosionAllowanceCircuitService
from services.pipe_design_service import PipeDesignService
from services.transfer_pump_service import TransferPumpService
from services.discharge_head_loss_service import DischargeHeadLossService
from services.suction_npsh_service import SuctionNPSHService
from services.project_persistence_service import ProjectPersistenceService
from engineering.validation import ValidationError, ValidationIssue
from i18n.validation import render_validation_issue
from ui.dialogs.material_library_dialog import MaterialLibraryDialog
from ui.dialogs.pipe_size_library_dialog import PipeSizeLibraryDialog
from ui.dialogs.constants_library_dialog import ConstantsLibraryDialog
from ui.dialogs.corrosion_allowance_circuit_library_dialog import CorrosionAllowanceCircuitLibraryDialog
from ui.pages.pipe_design_page import PipeDesignPage
from ui.pages.transfer_pump_page import TransferPumpPage
from ui.pages.discharge_head_loss_page import DischargeHeadLossPage
from ui.pages.suction_npsh_page import SuctionNPSHPage
from ui.dialogs.new_project_dialog import NewProjectDialog
from ui.dialogs.open_project_dialog import OpenProjectDialog
from ui.dialogs.save_project_as_dialog import SaveProjectAsDialog
from ui.widgets.project_summary import ProjectSummary
from ui.widgets.status_bar import StatusBar
from ui.widgets.scrollable_frame import ScrollableFrame
from ui.widgets.scrollable_page_host import ScrollablePageHost
from ui.widgets.scrollable_treeview import ScrollableTreeview
from ui.widgets.engineering_components import EmptyState
from ui.assets import d243_main_logo_path, ysh_ship_bottom_left_path, ysh_ship_top_right_path
from ui.widgets.asset_loader import AssetImageLoader
from ui.widgets.rounded_button import (
    ADD_BUTTON_PALETTE,
    DELETE_BUTTON_PALETTE,
    EDIT_BUTTON_PALETTE,
    HEADER_COMMAND_PALETTE,
    NEUTRAL_BUTTON_PALETTE,
    RoundedButtonPalette,
    create_rounded_button,
)
from ui.theme import apply_theme, colors, configure_project_tree
from ui.theme.spacing import LG, MD, SM, XL
from i18n.manager import LocalizationManager
from i18n.translator import Translator
from YSH.product import PRODUCT_FULL_NAME, PRODUCT_SHORT_NAME, PRODUCT_SUBTITLE

LOGGER = logging.getLogger(__name__)

HEADER_LOGO_TARGET_SIZE = 180

FILE_MENU_INDEX = {
    "new": 0,
    "open": 1,
    "save": 2,
    "save_as": 3,
    "close": 4,
    "delete": 5,
    "exit": 7,
}
MENU_CASCADE_INDEX = {"file": 0, "library": 1, "project": 2, "help": 3}

class MainWindow:
    """Creates and runs the primary YSH desktop window."""

    def __init__(
        self,
        root: tk.Tk,
        project_service: ProjectService,
        on_close: Callable[[], None],
        material_service: MaterialService | None = None,
        pipe_size_service: PipeSizeService | None = None,
        engineering_constant_service: EngineeringConstantService | None = None,
        corrosion_allowance_circuit_service: CorrosionAllowanceCircuitService | None = None,
        pipe_design_service: PipeDesignService | None = None,
        transfer_pump_service: TransferPumpService | None = None,
        discharge_head_loss_service: DischargeHeadLossService | None = None,
        suction_npsh_service: SuctionNPSHService | None = None,
        project_persistence_service: ProjectPersistenceService | None = None,
        localization: LocalizationManager | None = None,
    ) -> None:
        """Create the window and configure its layout and close lifecycle."""
        self._on_close = on_close
        self._project_service = project_service
        self._material_service = material_service
        self._pipe_size_service = pipe_size_service
        self._engineering_constant_service = engineering_constant_service
        self._corrosion_allowance_circuit_service = corrosion_allowance_circuit_service
        self._pipe_design_service = pipe_design_service
        self._transfer_pump_service = transfer_pump_service
        self._discharge_head_loss_service = discharge_head_loss_service
        self._suction_npsh_service = suction_npsh_service
        self._project_persistence_service = project_persistence_service
        self._localization = localization
        self._localizable_components: list[object] = []
        self._translate = (
            localization.translate if localization is not None else Translator().translate
        )
        self._active_project: Project | None = None
        self._root = root
        self._root.title(self._window_title())
        self._root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self._root.minsize(WINDOW_MINIMUM_WIDTH, WINDOW_MINIMUM_HEIGHT)
        self._root.protocol("WM_DELETE_WINDOW", self._close)
        self._root.iconname(PRODUCT_SHORT_NAME)
        apply_theme(self._root)
        self._create_layout()
        self._refresh_projects()
        if self._localization is not None:
            self._localization.register(self._refresh_all_localized_ui)

    def _text(self, key: str, **values: object) -> str:
        """Return a translated UI string, including in isolated UI tests."""
        translator = getattr(self, "_translate", Translator().translate)
        return translator(key, **values)

    def _window_title(self) -> str:
        """Return the localized product title with an optional active project."""
        title = PRODUCT_FULL_NAME
        active_project = getattr(self, "_active_project", None)
        if active_project is not None:
            return f"{title} — {active_project.display_name}"
        return title

    def _refresh_window_title(self) -> None:
        """Apply the current localized product identity to the native window."""
        self._root.title(self._window_title())

    def _create_layout(self) -> None:
        self._root.columnconfigure(0, weight=1)
        self._root.rowconfigure(1, weight=1)
        self._create_menu_bar()

        header = ttk.Frame(self._root, style="Header.TFrame", padding=(LG, SM, LG, SM))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=0)
        header.columnconfigure(1, weight=1)
        identity = ttk.Frame(header, style="HeaderBrand.TFrame", padding=(0, SM // 2))
        identity.grid(row=0, column=0, sticky="w")
        self._header_logo_source_image: tk.PhotoImage | None = None
        self._header_logo_image: tk.PhotoImage | None = None
        self._add_header_logo(identity)
        brand_text = ttk.Frame(identity, style="HeaderBrand.TFrame")
        brand_text.pack(side="left")
        self._header_title = ttk.Label(brand_text, text=PRODUCT_SHORT_NAME, style="HeaderTitle.TLabel")
        self._header_title.pack(anchor="w")
        self._header_subtitle = ttk.Label(
            brand_text,
            text=PRODUCT_SUBTITLE,
            style="HeaderSubtitle.TLabel",
        )
        self._header_subtitle.pack(anchor="w", pady=(2, 0))
        # The locked D243 emblem is displayed by ``_add_header_logo`` when
        # supplied; legacy decorative ship art is not part of this shell.
        if self._localization is not None:
            self._language_value = tk.StringVar(value=self._language_display_name())

        toolbar = ttk.Frame(header, style="Ribbon.TFrame", padding=(MD, 0, 0, 0))
        toolbar.grid(row=0, column=1, sticky="e")
        self._ribbon_project = self._create_ribbon_group(toolbar, "ribbon.project")
        self._toolbar_new = self._create_header_button(self._ribbon_project, self._translate("action.new"), self._open_new_project, style="RoundedAdd.TButton", palette=ADD_BUTTON_PALETTE, icon_name="new")
        self._toolbar_new.pack(side="left")
        self._toolbar_open = self._create_header_button(self._ribbon_project, self._translate("action.open"), self._open_project, style="RoundedEdit.TButton", palette=EDIT_BUTTON_PALETTE, icon_name="open")
        self._toolbar_open.pack(side="left", padx=(SM, 0))
        self._toolbar_save = self._create_header_button(self._ribbon_project, self._translate("action.save"), self._save_project, style="RoundedAdd.TButton", palette=ADD_BUTTON_PALETTE, icon_name="save")
        self._toolbar_save.pack(side="left", padx=(SM, 0))
        self._toolbar_save_as = self._create_header_button(self._ribbon_project, self._translate("action.save_as"), self._save_project_as, style="RoundedNeutral.TButton", palette=NEUTRAL_BUTTON_PALETTE, icon_name="save_as")
        self._toolbar_save_as.pack(side="left", padx=(SM, 0))
        self._ribbon_library = self._create_ribbon_group(toolbar, "ribbon.data_library")
        self._toolbar_materials = self._create_header_button(self._ribbon_library, self._translate("menu.library.materials"), self._open_material_library, style="RoundedNeutral.TButton", palette=NEUTRAL_BUTTON_PALETTE, icon_name="library_materials")
        self._toolbar_materials.pack(side="left")
        self._toolbar_pipe_sizes = self._create_header_button(self._ribbon_library, self._translate("menu.library.pipe_sizes"), self._open_pipe_size_library, style="RoundedNeutral.TButton", palette=NEUTRAL_BUTTON_PALETTE, icon_name="library_pipe_sizes")
        self._toolbar_pipe_sizes.pack(side="left", padx=(SM, 0))
        self._toolbar_constants = self._create_header_button(self._ribbon_library, self._translate("menu.library.engineering_constants"), self._open_constants_library, style="RoundedNeutral.TButton", palette=NEUTRAL_BUTTON_PALETTE, icon_name="library_engineering_constants")
        self._toolbar_constants.pack(side="left", padx=(SM, 0))
        self._toolbar_circuits = self._create_header_button(self._ribbon_library, self._translate("menu.library.corrosion_allowance_circuits"), self._open_corrosion_allowance_circuit_library, style="RoundedNeutral.TButton", palette=NEUTRAL_BUTTON_PALETTE, icon_name="library_corrosion_circuits")
        self._toolbar_circuits.pack(side="left", padx=(SM, 0))
        self._ribbon_help = self._create_ribbon_group(toolbar, "ribbon.help")
        self._toolbar_about = self._create_header_button(self._ribbon_help, self._translate("menu.help.about"), self._show_about, style="RoundedNeutral.TButton", palette=NEUTRAL_BUTTON_PALETTE, icon_name="about")
        self._toolbar_about.pack(side="left")

        workspace = ttk.Frame(self._root, style="Main.TFrame", padding=(LG, MD, LG, LG))
        workspace.grid(row=1, column=0, sticky="nsew")
        workspace.columnconfigure(0, minsize=248, weight=0)
        workspace.columnconfigure(1, weight=1)
        workspace.rowconfigure(0, weight=1)

        navigation = ttk.Frame(
            workspace,
            style="SidebarPanel.TFrame",
            padding=MD,
            width=248,
        )
        navigation.grid(row=0, column=0, sticky="nsew")
        navigation.columnconfigure(0, weight=1)
        navigation.rowconfigure(3, weight=1)
        self._sidebar_title = ttk.Label(navigation, text=self._translate("project.projects"), style="SidebarTitle.TLabel")
        self._sidebar_title.grid(row=0, column=0, sticky="w", pady=(0, SM))
        self._project_search_label = ttk.Label(
            navigation,
            style="SidebarSearchLabel.TLabel",
        )
        self._project_search_label.grid(row=1, column=0, sticky="w")
        self._project_search = tk.StringVar()
        self._project_search.trace_add("write", lambda *_args: self._refresh_projects())
        self._project_search_entry = ttk.Entry(navigation, textvariable=self._project_search)
        self._project_search_entry.grid(row=2, column=0, sticky="ew", pady=(SM // 2, MD))

        content = ttk.Frame(workspace, style="Workspace.TFrame")
        content.grid(row=0, column=1, sticky="nsew", padx=(LG, 0))
        content.columnconfigure(0, weight=1)
        content.rowconfigure(0, weight=1)

        self._project_tree_container = ScrollableTreeview(
            navigation,
            columns=("name", "modified"),
            show="headings",
            height=12,
        )
        self._projects_tree = self._project_tree_container.tree
        self._projects_tree.heading("name", text=self._translate("project.name"))
        self._projects_tree.heading("modified", text=self._translate("project.modified"))
        self._projects_tree.column("name", width=142, anchor="w")
        self._projects_tree.column("modified", width=86, anchor="w")
        self._projects_tree.configure(style="Project.Treeview")
        configure_project_tree(self._projects_tree)
        self._project_tree_container.grid(row=3, column=0, sticky="nsew")
        self._project_empty_state = None
        # Headless test fixtures intentionally expose no Tk interpreter.
        if hasattr(navigation, "tk"):
            self._project_empty_state = EmptyState(
                navigation, "project", "Henüz proje yok",
                "Başlamak için yeni bir proje oluşturun veya mevcut bir projeyi açın.",
                "Yeni ve Aç komutlarını kullanabilirsiniz.", image_size=145,
            )
            self._project_empty_state.grid(row=3, column=0, sticky="nsew")
            self._project_empty_state.grid_remove()
        self._projects_tree.bind("<Double-1>", self._open_selected_project)
        self._projects_tree.bind("<Return>", self._open_selected_project)
        self._projects_tree.bind("<Delete>", self._delete_project)
        actions = ttk.Frame(navigation, style="SidebarActions.TFrame", padding=(0, SM, 0, 0))
        actions.grid(row=4, column=0, sticky="ew", pady=(SM, 0))
        actions.columnconfigure(0, weight=1)
        actions.columnconfigure(1, weight=1)
        self._sidebar_new = self._create_sidebar_button(actions, self._translate('action.new'), self._open_new_project, style="RoundedAdd.TButton", palette=ADD_BUTTON_PALETTE, icon_name="new")
        self._sidebar_new.grid(row=0, column=0, sticky="ew", padx=(0, SM // 2))
        self._sidebar_open = self._create_sidebar_button(actions, self._translate("action.open"), self._open_selected_project, style="RoundedEdit.TButton", palette=EDIT_BUTTON_PALETTE, icon_name="open")
        self._sidebar_open.grid(row=0, column=1, sticky="ew", padx=(SM // 2, 0))
        self._sidebar_save = self._create_sidebar_button(actions, self._translate("action.save"), self._save_project, style="RoundedAdd.TButton", palette=ADD_BUTTON_PALETTE, icon_name="save")
        self._sidebar_save.grid(row=1, column=0, sticky="ew", padx=(0, SM // 2), pady=(SM // 2, 0))
        self._sidebar_delete = self._create_sidebar_button(actions, self._translate("action.delete"), self._delete_project, style="RoundedDelete.TButton", palette=DELETE_BUTTON_PALETTE, icon_name="delete")
        self._sidebar_delete.grid(row=1, column=1, sticky="ew", padx=(SM // 2, 0), pady=(SM // 2, 0))
        self._sidebar_refresh = self._create_sidebar_button(actions, self._translate("action.refresh"), self._refresh_projects, style="RoundedNeutral.TButton", palette=NEUTRAL_BUTTON_PALETTE, icon_name="refresh")
        self._sidebar_refresh.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(SM // 2, 0))
        self._project_summary = ProjectSummary(navigation, self._translate)
        self._project_summary.grid(row=5, column=0, sticky="ew", pady=(MD, 0))

        self._page_host = ScrollablePageHost(content)
        self._page_host.grid(row=0, column=0, sticky="nsew")
        if self._pipe_design_service is not None:
            self._pipe_design_page = self._add_scrollable_page("pipe_design", self._translate("page.pipe.tab"),lambda parent:PipeDesignPage(parent,self._pipe_design_service, self._translate))
            self._pipe_design_page.set_dirty_callback(self._mark_workspace_dirty)
        if self._transfer_pump_service is not None and self._engineering_constant_service is not None:
            self._transfer_pump_page = self._add_scrollable_page("transfer_pump", self._translate("page.transfer.tab"),lambda parent:TransferPumpPage(parent,self._transfer_pump_service,self._engineering_constant_service, self._translate))
        if self._discharge_head_loss_service is not None and self._engineering_constant_service is not None:
            self._discharge_head_loss_page = self._add_scrollable_page("discharge_head_loss", self._translate("page.discharge.tab"),lambda parent:DischargeHeadLossPage(parent,self._discharge_head_loss_service,self._engineering_constant_service,self._material_service, self._translate))
        if self._suction_npsh_service is not None and self._engineering_constant_service is not None:
            self._suction_npsh_page = self._add_scrollable_page("suction_npsh", self._translate("page.suction.tab"),lambda parent:SuctionNPSHPage(parent,self._suction_npsh_service,self._material_service,self._engineering_constant_service, self._translate))

        self._pages = {key: getattr(self, attribute) for key, attribute in (("pipe_design", "_pipe_design_page"), ("transfer_pump", "_transfer_pump_page"), ("discharge_head_loss", "_discharge_head_loss_page"), ("suction_npsh", "_suction_npsh_page")) if hasattr(self, attribute)}
        self.register_localizable(self._project_summary)
        for page in self._pages.values():
            self.register_localizable(page)
        self._attach_dirty_callbacks()

        self._status_bar = StatusBar(self._root, self._translate)
        self._status_bar.grid(row=2, column=0, sticky="ew")
        self.register_localizable(self._status_bar)

    @staticmethod
    def _create_header_button(
        parent: tk.Misc,
        text: str,
        command: Callable[[], object],
        *,
        style: str,
        palette: RoundedButtonPalette,
        icon_name: str,
    ) -> tk.Widget:
        """Create one restrained command inside the unified D243 shell."""
        return create_rounded_button(
            parent,
            text,
            command,
            style="HeaderCommand.TButton",
            palette=HEADER_COMMAND_PALETTE,
            outside_background=colors.NAVY,
            icon_name=icon_name,
            icon_only=True,
            tooltip_text=text,
            # Keep the full composed action tile visible with a six-pixel
            # breathing margin inside the slightly tighter header surface.
            icon_size=72,
            square_size=86,
        )

    def _add_header_logo(self, parent: ttk.Frame) -> None:
        """Show the locked D243 emblem only when the approved asset exists."""
        logo_path = d243_main_logo_path()
        if logo_path is None:
            return
        try:
            loaded = AssetImageLoader.load(self._root, logo_path, HEADER_LOGO_TARGET_SIZE)
            if loaded is None:
                return
            self._header_logo_source_image = loaded.source
            self._header_logo_image = loaded.rendered
            logo_plate = ttk.Frame(parent, style="HeaderLogoPlate.TFrame")
            logo_plate.pack(side="left", padx=(0, MD))
            logo = ttk.Label(
                logo_plate,
                image=self._header_logo_image,
                style="HeaderLogoPlate.TLabel",
            )
            logo.pack()
        except tk.TclError:
            LOGGER.warning(
                "Unable to load optional D243 header logo: %s",
                logo_path,
                exc_info=True,
            )

    @staticmethod
    def _create_sidebar_button(
        parent: tk.Misc,
        text: str,
        command: Callable[[], object],
        *,
        style: str,
        palette: RoundedButtonPalette,
        icon_name: str,
    ) -> tk.Widget:
        """Create a project-sidebar action that blends into its neutral panel."""
        return create_rounded_button(
            parent,
            text,
            command,
            style=style,
            palette=palette,
            outside_background=colors.SIDEBAR_SURFACE,
            icon_name=icon_name,
            # Sidebar labels retain their readable native text lane while
            # giving the complete icon composition a six-pixel vertical margin.
            icon_size=36,
            minimum_height=48,
            horizontal_padding=18,
        )

    def _add_decorative_image(
        self,
        parent: ttk.Frame,
        image_path: Path | None,
        *,
        maximum_width: int,
        maximum_height: int,
        style: str,
    ) -> ttk.Label | None:
        """Create a non-critical, proportionally scaled decorative image label."""
        photo_image = getattr(tk, "PhotoImage", None)
        if image_path is None or not callable(photo_image):
            return None
        try:
            image = photo_image(master=self._root, file=str(image_path))
            scale = max(
                1,
                math.ceil(
                    max(
                        image.width() / maximum_width,
                        image.height() / maximum_height,
                    )
                ),
            )
            scaled_image = image.subsample(scale, scale)
            label = ttk.Label(parent, image=scaled_image, style=style)
            if image_path == ysh_ship_top_right_path():
                self._header_ship_source_image = image
                self._header_ship_image = scaled_image
                self._header_ship_dimensions = (maximum_width, maximum_height)
            else:
                self._sidebar_ship_image = scaled_image
            return label
        except tk.TclError:
            LOGGER.warning(
                "Unable to load optional YSH decorative artwork: %s",
                image_path,
                exc_info=True,
            )
            return None

    def _update_header_artwork_visibility(self, event: tk.Event[tk.Misc]) -> None:
        """Resize header artwork before hiding it in constrained shell widths."""
        if self._header_ship_label is None:
            return
        if event.width < 900:
            self._header_ship_label.grid_remove()
            return
        if event.width < 1080:
            dimensions = (140, 44)
        elif event.width < 1280:
            dimensions = (200, 60)
        else:
            dimensions = (260, 76)
        self._resize_header_ship(*dimensions)
        self._header_ship_label.grid()

    def _resize_header_ship(self, maximum_width: int, maximum_height: int) -> None:
        """Scale the approved header ship proportionally for the available width."""
        if (
            self._header_ship_label is None
            or self._header_ship_source_image is None
            or self._header_ship_dimensions == (maximum_width, maximum_height)
        ):
            return
        image = self._header_ship_source_image
        scale = max(
            1,
            math.ceil(
                max(
                    image.width() / maximum_width,
                    image.height() / maximum_height,
                )
            ),
        )
        self._header_ship_image = image.subsample(scale, scale)
        self._header_ship_label.configure(image=self._header_ship_image)
        self._header_ship_dimensions = (maximum_width, maximum_height)

    def _update_sidebar_artwork_visibility(self, event: tk.Event[tk.Misc]) -> None:
        """Hide sidebar artwork when functional project controls need its space."""
        if self._sidebar_ship_label is None:
            return
        if event.height < 680:
            self._sidebar_ship_label.grid_remove()
        else:
            self._sidebar_ship_label.grid()

    def _create_ribbon_group(self, parent: tk.Misc, title_key: str) -> ttk.Frame:
        """Create one compact ribbon group using an existing command callback."""
        group = ttk.Frame(parent, style="CommandGroup.TFrame", padding=(0, 0))
        group.pack(side="left", padx=(0, MD), fill="y")
        label = ttk.Label(group, text=self._translate(title_key), style="CommandGroupTitle.TLabel")
        label.pack(anchor="w", pady=(0, 2))
        commands = ttk.Frame(group, style="CommandGroupCommands.TFrame")
        commands.pack(anchor="w")
        group._ribbon_title_key = title_key  # type: ignore[attr-defined]
        group._ribbon_label = label  # type: ignore[attr-defined]
        commands._ribbon_group = group  # type: ignore[attr-defined]
        return commands

    def _add_scrollable_page(self,page_key:str,title:str,factory:Callable[[tk.Misc],tk.Misc])->tk.Misc:
        """Register every primary calculation page through the shared host."""
        return self._page_host.add_scrollable_page(title,factory,page_key)

    def register_localizable(self, component: object) -> None:
        """Register one live UI surface for the deterministic refresh transaction."""
        if component not in self._localizable_components:
            self._localizable_components.append(component)

    def unregister_localizable(self, component: object) -> None:
        """Remove a destroyed transient UI surface from the refresh transaction."""
        if component in self._localizable_components:
            self._localizable_components.remove(component)

    def _refresh_all_localized_ui(self) -> None:
        """Refresh every registered live surface without partial-refresh failure."""
        LOGGER.info("LOCALIZATION full refresh start: components=%d", len(self._localizable_components))
        try:
            self.refresh_texts()
            LOGGER.info("LOCALIZATION component refresh: MainWindow")
        except Exception:
            LOGGER.exception("LOCALIZATION component refresh failed: MainWindow")
        for refresh_shell in (self._refresh_menu_texts, self._refresh_notebook_tab_titles):
            try:
                refresh_shell()
            except Exception:
                LOGGER.exception("LOCALIZATION shell refresh failed: %s", refresh_shell.__name__)
        for component in tuple(self._localizable_components):
            refresh = getattr(component, "refresh_texts", None)
            if not callable(refresh):
                continue
            try:
                LOGGER.info("LOCALIZATION component refresh: %s", component.__class__.__name__)
                refresh()
            except Exception:
                LOGGER.exception("LOCALIZATION component refresh failed: %s", component.__class__.__name__)
        LOGGER.info("LOCALIZATION full refresh complete")

    def _language_display_name(self) -> str:
        """Return the current language's compact header-selector label."""
        language = self._localization.language if self._localization is not None else "en"
        return self._translate(
            "language.turkish" if language == "tr" else "language.english"
        )

    def _change_language(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        """Persist the user-selected application language without touching pages' state."""
        if self._localization is None:
            return
        selected = self._language_value.get()
        language = "tr" if selected == self._translate("language.turkish") else "en"
        self._localization.set_language(language)

    def refresh_texts(self) -> None:
        """Refresh visible navigation and registered pages without recreating them."""
        self._refresh_window_title()
        self._header_title.configure(text=PRODUCT_SHORT_NAME)
        self._header_subtitle.configure(text=PRODUCT_SUBTITLE)
        self._toolbar_new.configure(text=self._translate("action.new"))
        self._toolbar_open.configure(text=self._translate("action.open"))
        self._toolbar_save.configure(text=self._translate("action.save"))
        self._toolbar_save_as.configure(text=self._translate("action.save_as"))
        self._toolbar_materials.configure(text=self._translate("menu.library.materials"))
        self._toolbar_pipe_sizes.configure(text=self._translate("menu.library.pipe_sizes"))
        self._toolbar_constants.configure(text=self._translate("menu.library.engineering_constants"))
        self._toolbar_circuits.configure(text=self._translate("menu.library.corrosion_allowance_circuits"))
        self._toolbar_about.configure(text=self._translate("menu.help.about"))
        for commands in (
            self._ribbon_project,
            self._ribbon_library,
            self._ribbon_help,
        ):
            group = commands._ribbon_group  # type: ignore[attr-defined]
            group._ribbon_label.configure(  # type: ignore[attr-defined]
                text=self._translate(group._ribbon_title_key)  # type: ignore[attr-defined]
            )
        self._sidebar_title.configure(text=self._translate("project.projects"))
        self._project_search_label.configure(text=self._translate("project.search"))
        self._projects_tree.heading("name", text=self._translate("project.name"))
        self._projects_tree.heading("modified", text=self._translate("project.modified"))
        self._sidebar_new.configure(text=f"+ {self._translate('action.new')}")
        self._sidebar_open.configure(text=self._translate("action.open"))
        self._sidebar_save.configure(text=self._translate("action.save"))
        self._sidebar_delete.configure(text=self._translate("action.delete"))
        self._sidebar_refresh.configure(text=self._translate("action.refresh"))
        self._refresh_menu_texts()
        self._refresh_notebook_tab_titles()

    def _refresh_notebook_tab_titles(self) -> None:
        """Update existing tab captions without changing selected notebook state."""
        page_titles = {
            "pipe_design": "page.pipe.tab",
            "transfer_pump": "page.transfer.tab",
            "discharge_head_loss": "page.discharge.tab",
            "suction_npsh": "page.suction.tab",
        }
        selected_tab = self._page_host.select()
        for page_name in getattr(self, "_pages", {}):
            self._page_host.set_page_title(page_name, self._translate(page_titles[page_name]))
        if selected_tab:
            self._page_host.select(selected_tab)

    def _export_all_page_states(self) -> dict[str, object]:
        """Collect page-owned persistence contracts into one V1 workspace."""
        return {
            "schema_version": 1,
            **{
                key: page.export_state()
                for key, page in getattr(self, "_pages", {}).items()
            },
        }

    def _load_all_page_states(self, state: dict[str, object]) -> None:
        """Restore each registered page only after state validation succeeds."""
        if state.get("schema_version") != 1:
            raise ValidationError(ValidationIssue("project_state_unsupported"))
        for key, page in self._pages.items(): page.load_state(dict(state.get(key, {})))

    def _clear_all_pages(self) -> None:
        """Restore clean/default state on every primary calculation page."""
        for page in getattr(self, "_pages", {}).values():
            page.clear_state()

    def _attach_dirty_callbacks(self) -> None:
        """Route page edits to optional project dirty tracking."""
        for page in self._pages.values(): page.set_dirty_callback(self._mark_project_dirty)

    def _mark_project_dirty(self) -> None:
        """Mark only an active optional project dirty."""
        if self._project_persistence_service is not None and self._active_project is not None:
            self._project_persistence_service.mark_dirty()
            self._file_menu.entryconfigure(FILE_MENU_INDEX["save"], state="normal")

    def _create_menu_bar(self) -> None:
        menu_bar = tk.Menu(self._root)
        self._menu_bar = menu_bar
        self._file_menu = tk.Menu(menu_bar, tearoff=False)
        self._file_menu.add_command(
            label=self._translate("menu.file.new_project"),
            command=self._open_new_project,
        )
        self._file_menu.add_command(label=self._translate("menu.file.open_project"), command=self._open_project)
        self._file_menu.add_command(label=self._translate("menu.file.save_project"), command=self._save_project)
        self._file_menu.add_command(label=self._translate("menu.file.save_project_as"), command=self._save_project_as)
        self._file_menu.add_command(
            label=self._translate("menu.file.close_project"),
            command=self._close_project,
        )
        self._file_menu.add_command(label=self._translate("menu.file.delete_project"), command=self._delete_project)
        self._file_menu.add_separator()
        self._file_menu.add_command(label=self._translate("menu.file.exit"), command=self._close)
        menu_bar.add_cascade(label=self._translate("menu.file"), menu=self._file_menu)

        library_menu = tk.Menu(menu_bar, tearoff=False)
        library_menu.add_command(label=self._translate("menu.library.materials"), command=self._open_material_library)
        library_menu.add_command(label=self._translate("menu.library.pipe_sizes"), command=self._open_pipe_size_library)
        library_menu.add_command(
            label=self._translate("menu.library.engineering_constants"),
            command=self._open_constants_library,
        )
        library_menu.add_command(
            label=self._translate("menu.library.corrosion_allowance_circuits"),
            command=self._open_corrosion_allowance_circuit_library,
        )
        self._library_menu = library_menu
        menu_bar.add_cascade(label=self._translate("menu.library"), menu=library_menu)

        project_menu = tk.Menu(menu_bar, tearoff=False)
        project_menu.add_command(label=self._translate("menu.project.refresh"), command=self._refresh_projects)
        self._project_menu = project_menu
        menu_bar.add_cascade(label=self._translate("menu.project"), menu=project_menu)

        help_menu = tk.Menu(menu_bar, tearoff=False)
        help_menu.add_command(label=self._translate("menu.help.about"), command=self._show_about)
        self._help_menu = help_menu
        menu_bar.add_cascade(label=self._translate("menu.help"), menu=help_menu)
        self._root.configure(menu=menu_bar)

    def _refresh_menu_texts(self) -> None:
        """Refresh the main menu shell without changing menu callbacks or state."""
        self._menu_bar.entryconfigure(MENU_CASCADE_INDEX["file"], label=self._translate("menu.file"))
        self._menu_bar.entryconfigure(MENU_CASCADE_INDEX["library"], label=self._translate("menu.library"))
        self._menu_bar.entryconfigure(MENU_CASCADE_INDEX["project"], label=self._translate("menu.project"))
        self._menu_bar.entryconfigure(MENU_CASCADE_INDEX["help"], label=self._translate("menu.help"))
        for index, key in (
            (FILE_MENU_INDEX["new"], "menu.file.new_project"),
            (FILE_MENU_INDEX["open"], "menu.file.open_project"),
            (FILE_MENU_INDEX["save"], "menu.file.save_project"),
            (FILE_MENU_INDEX["save_as"], "menu.file.save_project_as"),
            (FILE_MENU_INDEX["close"], "menu.file.close_project"),
            (FILE_MENU_INDEX["delete"], "menu.file.delete_project"),
            (FILE_MENU_INDEX["exit"], "menu.file.exit"),
        ):
            self._file_menu.entryconfigure(index, label=self._translate(key))
        self._library_menu.entryconfigure(0, label=self._translate("menu.library.materials"))
        self._library_menu.entryconfigure(1, label=self._translate("menu.library.pipe_sizes"))
        self._library_menu.entryconfigure(2, label=self._translate("menu.library.engineering_constants"))
        self._library_menu.entryconfigure(3, label=self._translate("menu.library.corrosion_allowance_circuits"))
        self._project_menu.entryconfigure(0, label=self._translate("menu.project.refresh"))
        self._help_menu.entryconfigure(0, label=self._translate("menu.help.about"))
        self._root.configure(menu=self._menu_bar)
        update = getattr(self._root, "update_idletasks", None)
        if callable(update):
            update()

    def _open_material_library(self) -> None:
        """Open the service-backed material-library editor."""
        if self._material_service is not None:
            MaterialLibraryDialog(self._root, self._material_service, translate=self._translate, localization_owner=self)

    def _open_pipe_size_library(self) -> None:
        """Open the service-backed pipe-size-library editor."""
        if self._pipe_size_service is not None:
            PipeSizeLibraryDialog(self._root, self._pipe_size_service, translate=self._translate, localization_owner=self)

    def _open_constants_library(self) -> None:
        """Open the service-backed engineering-constants editor."""
        if self._engineering_constant_service is not None:
            ConstantsLibraryDialog(self._root, self._engineering_constant_service, translate=self._translate, localization_owner=self)

    def _open_corrosion_allowance_circuit_library(self) -> None:
        """Open the editable D243 circuit/corrosion-allowance library."""
        if self._corrosion_allowance_circuit_service is not None:
            CorrosionAllowanceCircuitLibraryDialog(self._root, self._corrosion_allowance_circuit_service, translate=self._translate, localization_owner=self)

    def _open_new_project(self) -> None:
        """Open the new-project dialog after resolving an active dirty state."""
        if not self._resolve_unsaved_changes():
            return
        try:
            metadata = NewProjectDialog(
                self._root,
                translate=self._translate,
                localization_owner=self,
            ).show()
        except Exception:
            LOGGER.exception("Unable to display the New Project dialog.")
            messagebox.showerror(
                self._translate("dialog.error"),
                self._translate("validation.unexpected_error"),
                parent=self._root,
            )
            return
        if metadata is not None:
            self._create_project(*metadata)

    def _open_project(self) -> None:
        if not self._resolve_unsaved_changes():
            return
        try:
            project_source = getattr(
                self,
                "_project_persistence_service",
                self._project_service,
            )
            if hasattr(project_source, "get_all_projects") and not project_source.get_all_projects():
                messagebox.showinfo(
                    self._text("dialog.information"),
                    self._text("message.no_projects_available"),
                    parent=self._root,
                )
                return
            dialog = OpenProjectDialog(
                self._root,
                project_source,
                self._text,
                self,
            )
            project = dialog.show()
        except Exception:
            LOGGER.exception("Unable to display the Open Project dialog.")
            messagebox.showerror(
                self._text("dialog.error"),
                self._text("validation.unexpected_error"),
                parent=self._root,
            )
            return
        if project is not None:
            self._activate_project(project)

    def _open_selected_project(self, event: tk.Event[tk.Misc] | None = None) -> str:
        """Open the selected project through the same transactional workflow."""
        if event is not None:
            item_id = self._projects_tree.identify_row(event.y)
            if item_id:
                self._projects_tree.selection_set(item_id)
        selected = self._projects_tree.selection()
        if not selected:
            messagebox.showinfo(
                self._text("dialog.information"),
                self._text("message.select_project_to_open"),
                parent=self._root,
            )
            return "break"
        if not self._resolve_unsaved_changes():
            return "break"
        try:
            source = getattr(self, "_project_persistence_service", None) or self._project_service
            self._activate_project(source.get_project(UUID(selected[0])))
        except Exception:
            LOGGER.exception("Unable to open selected project.")
            messagebox.showerror(
                self._translate("dialog.error"),
                self._translate("validation.unexpected_error"),
                parent=self._root,
            )
        return "break"

    def _create_project(
        self,
        name: str,
        description: str,
        notes: str,
    ) -> bool:
        try:
            persistence = getattr(self, "_project_persistence_service", None)
            if persistence is None:
                raise RuntimeError("Project persistence is unavailable.")
            project = persistence.create_project(name, description, notes)
        except ProjectValidationError:
            messagebox.showerror(
                self._translate("dialog.error"),
                self._translate(
                    "validation.required",
                    field_name=self._translate("field.project_name"),
                ),
                parent=self._root,
            )
            return False
        except ProjectConflictError:
            messagebox.showerror(
                self._translate("dialog.error"),
                self._translate("validation.project_duplicate_name"),
                parent=self._root,
            )
            return False
        except ValueError:
            messagebox.showerror(
                self._translate("dialog.error"),
                self._translate("validation.unexpected_error"),
                parent=self._root,
            )
            return False
        except Exception:
            LOGGER.exception("Unable to create a project.")
            messagebox.showerror(
                self._translate("dialog.error"),
                self._translate("validation.unexpected_error"),
                parent=self._root,
            )
            return False
        self._refresh_projects()
        self._clear_all_pages()
        self._activate_project(project, self._text("message.project_created"))
        return True

    def _activate_project(
        self,
        project: Project,
        message: str | None = None,
    ) -> None:
        persistence = getattr(self, "_project_persistence_service", None)
        previous_project = self._active_project
        previous_state = self._export_all_page_states()
        try:
            if persistence is not None:
                has_saved_state = getattr(
                    persistence, "has_saved_state", lambda _project_id: True
                )(project.id)
                _, state = persistence.open(project.id)
                if has_saved_state:
                    self._load_all_page_states(state)
                else:
                    self._clear_all_pages()
        except Exception:
            LOGGER.exception("Unable to load project '%s'.", project.id)
            try:
                self._load_all_page_states(previous_state)
                if persistence is not None:
                    if previous_project is None:
                        persistence.close()
                    else:
                        persistence.open(previous_project.id)
            except Exception:
                LOGGER.exception("Unable to restore the prior project workspace.")
            messagebox.showerror(
                self._translate("dialog.error"),
                self._translate("validation.unexpected_error"),
                parent=self._root,
            )
            return
        self._active_project = project
        if hasattr(self, "_projects_tree"):
            self._refresh_projects()
        self._refresh_window_title()
        self._project_summary.set_project(project)
        self._file_menu.entryconfigure(FILE_MENU_INDEX["close"], state="normal")
        self._file_menu.entryconfigure(FILE_MENU_INDEX["save"], state="disabled")
        self._status_bar.set_message(
            message or self._text("message.project_opened")
        )

    def _close_project(self) -> None:
        """Close the optional project without disabling calculations."""
        if not self._resolve_unsaved_changes():
            return
        self._active_project = None
        self._refresh_window_title()
        self._project_summary.clear()
        persistence = getattr(self, "_project_persistence_service", None)
        if persistence is not None:persistence.close()
        self._clear_all_pages()
        if hasattr(self, "_projects_tree"):
            self._refresh_projects()
        self._file_menu.entryconfigure(FILE_MENU_INDEX["close"], state="disabled")
        self._file_menu.entryconfigure(FILE_MENU_INDEX["save"], state="disabled")
        self._status_bar.set_message(self._text("message.project_closed"))

    def _mark_workspace_dirty(self) -> None:
        """Enable saving after a genuine calculation-page edit."""
        if self._project_persistence_service is not None and self._active_project is not None:
            self._project_persistence_service.mark_dirty()
            self._file_menu.entryconfigure(FILE_MENU_INDEX["save"], state="normal")

    def _save_project(self) -> bool:
        """Persist the active pipe-design page through the workspace service."""
        if self._project_persistence_service is None or self._active_project is None:
            messagebox.showerror(self._translate("dialog.error"), self._translate("validation.project_selection_required"), parent=self._root)
            return False
        try:
            self._project_persistence_service.save(self._export_all_page_states())
        except ValidationError as error:
            messagebox.showerror(self._translate("dialog.error"), render_validation_issue(error.issue, type("T", (), {"translate": self._translate})()), parent=self._root)
            return False
        except Exception:
            LOGGER.exception("Unable to save project.")
            messagebox.showerror(self._translate("dialog.error"), self._translate("validation.unexpected_error"), parent=self._root)
            return False
        self._file_menu.entryconfigure(FILE_MENU_INDEX["save"], state="disabled")
        self._status_bar.set_message(self._translate("message.project_saved"))
        return True

    def _save_project_as(self) -> None:
        """Copy the current four-page workspace into a newly created project."""
        if self._project_persistence_service is None:
            messagebox.showerror(
                self._translate("dialog.error"),
                self._translate("validation.unexpected_error"),
                parent=self._root,
            )
            return
        metadata = SaveProjectAsDialog(
            self._root,
            self._translate,
            self,
        ).show()
        if metadata is None:
            return
        try:
            project = self._project_persistence_service.create_project(*metadata)
            self._project_persistence_service.save(self._export_all_page_states())
        except ProjectValidationError:
            messagebox.showerror(
                self._translate("dialog.error"),
                self._translate(
                    "validation.required",
                    field_name=self._translate("field.project_name"),
                ),
                parent=self._root,
            )
            return
        except ProjectConflictError:
            messagebox.showerror(
                self._translate("dialog.error"),
                self._translate("validation.project_duplicate_name"),
                parent=self._root,
            )
            return
        except ValueError:
            messagebox.showerror(
                self._translate("dialog.error"),
                self._translate("validation.unexpected_error"),
                parent=self._root,
            )
            return
        except Exception:
            LOGGER.exception("Unable to save the project as a new project.")
            messagebox.showerror(
                self._translate("dialog.error"),
                self._translate("validation.unexpected_error"),
                parent=self._root,
            )
            return
        self._active_project = project
        self._refresh_projects()
        self._refresh_window_title()
        self._project_summary.set_project(project)
        self._file_menu.entryconfigure(FILE_MENU_INDEX["close"], state="normal")
        self._file_menu.entryconfigure(FILE_MENU_INDEX["save"], state="disabled")
        self._status_bar.set_message(self._translate("message.project_saved"))

    def _delete_project(self, _event: tk.Event[tk.Misc] | None = None) -> str | None:
        """Confirm deletion of a selected project through persistence services."""
        if self._project_persistence_service is None:
            return "break"
        selected = self._projects_tree.selection()
        if not selected:
            messagebox.showinfo(
                self._translate("dialog.delete_project"),
                self._translate("validation.project_selection_required"),
                parent=self._root,
            )
            return "break"
        try:
            project_id = UUID(selected[0])
        except ValueError:
            messagebox.showerror(
                self._translate("dialog.error"),
                self._translate("validation.project_selection_required"),
                parent=self._root,
            )
            return "break"
        if self._active_project is not None and self._active_project.id == project_id:
            if not self._resolve_unsaved_changes():
                return "break"
        if not messagebox.askyesno(self._translate("dialog.delete_project"), self._translate("confirm.delete_project"), parent=self._root):
            return "break"
        try:
            self._project_persistence_service.delete(project_id)
        except ProjectNotFoundError:
            messagebox.showerror(
                self._translate("dialog.error"),
                self._translate("validation.project_not_found"),
                parent=self._root,
            )
            return "break"
        except Exception:
            LOGGER.exception("Unable to delete project '%s'.", project_id)
            messagebox.showerror(
                self._translate("dialog.error"),
                self._translate("validation.unexpected_error"),
                parent=self._root,
            )
            return "break"
        if self._active_project is not None and self._active_project.id == project_id:
            self._active_project = None
            self._refresh_window_title()
            self._project_summary.clear()
            self._clear_all_pages()
            self._file_menu.entryconfigure(FILE_MENU_INDEX["close"], state="disabled")
            self._file_menu.entryconfigure(FILE_MENU_INDEX["save"], state="disabled")
        self._refresh_projects()
        self._status_bar.set_message(self._translate("message.project_deleted"))
        return "break"

    def _resolve_unsaved_changes(self) -> bool:
        """Resolve one dirty active project before a destructive navigation action."""
        persistence = getattr(self, "_project_persistence_service", None)
        if persistence is None or self._active_project is None or not persistence.is_dirty:
            return True
        choice = messagebox.askyesnocancel(
            self._translate("dialog.unsaved_changes"),
            self._translate("confirm.unsaved_changes"),
            parent=self._root,
        )
        if choice is None:
            return False
        return self._save_project() if choice else True

    def _refresh_projects(self) -> None:
        """Refresh only saved-project metadata without changing workspace state."""
        try:
            source = (
                getattr(self, "_project_persistence_service", None)
                or self._project_service
            )
            selected = getattr(self._projects_tree, "selection", lambda: ())()
            projects = (
                source.get_all_projects()
                if hasattr(source, "get_all_projects")
                else source.list_projects()
            )
            search = getattr(self, "_project_search", None)
            query = "" if search is None else search.get().casefold().strip()
            for item_id in self._projects_tree.get_children():
                self._projects_tree.delete(item_id)
            for project in projects:
                searchable = " ".join(
                    (project.display_name, project.description, project.notes)
                ).casefold()
                if not query or query in searchable:
                    self._add_project(project)
            is_empty = not self._projects_tree.get_children()
            tree_container = getattr(self, "_project_tree_container", None)
            empty_state = getattr(self, "_project_empty_state", None)
            if tree_container is not None and empty_state is not None:
                (tree_container.grid_remove if is_empty else tree_container.grid)()
                (empty_state.grid if is_empty else empty_state.grid_remove)()
            if (
                selected
                and hasattr(self._projects_tree, "exists")
                and self._projects_tree.exists(selected[0])
            ):
                self._projects_tree.selection_set(selected[0])
        except Exception:
            LOGGER.exception("Unable to refresh the saved project list.")
            messagebox.showerror(
                self._translate("dialog.error"),
                self._translate("validation.unexpected_error"),
                parent=self._root,
            )

    def _add_project(self, project: Project) -> None:
        self._projects_tree.insert(
            "",
            "end",
            iid=str(project.id),
            values=(
                f"● {project.display_name}" if self._active_project is not None and project.id == self._active_project.id else project.display_name,
                project.modified_at.astimezone().strftime("%Y-%m-%d %H:%M"),
            ),
            tags=("active_project",) if self._active_project is not None and project.id == self._active_project.id else (),
        )

    def _show_about(self) -> None:
        messagebox.showinfo(
            self._translate("dialog.about_ysh"),
            self._translate("message.about_ysh"),
            parent=self._root,
        )

    def _close(self) -> None:
        if not self._resolve_unsaved_changes():
            return
        self._on_close()
        self._root.destroy()
