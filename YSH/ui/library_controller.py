"""Display-independent read/edit state machine for the engineering libraries."""
from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from services.engineering_library_service import EngineeringLibraryService, LibraryError
from services.library_catalog import CATEGORY_BY_CODE
from engineering.fire.library import FIRE_CATEGORIES, UNITS
from engineering.fire.enums import FireSourceStatus


class EditMode(StrEnum):
    """Editing is explicit; browsing never writes a repository."""
    BROWSE = "BROWSE"
    CREATE = "CREATE"
    EDIT = "EDIT"


class LibraryController:
    """Keep failed form drafts intact and write only on a Save action."""
    def __init__(self, service: EngineeringLibraryService) -> None:
        """Configure state without loading any library category."""
        self.service = service
        self.category = "systems"
        self.parent_id: UUID | None = None
        self.records: tuple = ()
        self.selected: object | None = None
        self.mode = EditMode.BROWSE
        self.draft: dict[str, object] = {}
        self.error_key: str | None = None

    def browse(self, category: str, parent_id: UUID | None = None) -> None:
        """Load one category; unsaved edits must first be saved or canceled."""
        if self.mode is not EditMode.BROWSE:
            raise LibraryError("library2.error.finish_edit")
        records = self.service.list_records(category,parent_id)
        self.category, self.parent_id = category, parent_id
        self.records, self.selected, self.error_key = records, None, None

    def filtered(self, search: str = "", active: bool | None = None,
                 ownership: str | None = None, verification: str | None = None) -> tuple:
        """Filter loaded rows without per-cell source or property queries."""
        result = []
        for row in self.records:
            if active is not None and getattr(row,"is_active",None) is not active:
                continue
            if ownership and self.service.ownership(self.category,row) != ownership:
                continue
            source = getattr(row,"reference",row)
            if verification and getattr(source,"verification_status",None) != verification:
                continue
            if search.casefold() not in str(row).casefold():
                continue
            result.append(row)
        return tuple(result)

    def select(self, identity: UUID) -> None:
        """Select an existing row without opening an editor or recalculating anything."""
        if self.mode is not EditMode.BROWSE:
            raise LibraryError("library2.error.finish_edit")
        key = CATEGORY_BY_CODE[self.category].key_field
        self.selected = next((r for r in self.records if getattr(r,key) == identity),None)
        if self.selected is None:
            raise LibraryError("library2.error.missing")

    def begin(self, *, create: bool) -> None:
        """Start a fresh draft or copy full-precision fields from a user record."""
        definition = CATEGORY_BY_CODE[self.category]
        if definition.model is None or not create and (
            self.selected is None or not self.service.can_edit(self.category,self.selected)):
            raise LibraryError("library2.error.protected")
        self.mode = EditMode.CREATE if create else EditMode.EDIT
        self.draft = {} if create else self.service.form_values(self.category,self.selected)
        if create:
            for field in definition.fields:
                if field.kind == 'bool': self.draft[field.name] = True
                if field.name == definition.parent_field or field.name == definition.key_field:
                    if self.parent_id: self.draft[field.name] = self.parent_id
        if create and self.category in FIRE_CATEGORIES:
            self.draft['unit']=UNITS[FIRE_CATEGORIES[self.category]]
            self.draft['source_status']=FireSourceStatus.SOURCE_REQUIRED
            self.draft['service']='water' if self.category=='fire_hw' else 'foam'
        self.error_key = None

    def cancel(self) -> None:
        """Discard unsaved values without a repository write."""
        self.mode, self.draft, self.error_key = EditMode.BROWSE, {}, None

    def save(self) -> bool:
        """Perform one service call; errors retain every entered form value."""
        if self.mode is EditMode.BROWSE:
            return False
        definition = CATEGORY_BY_CODE[self.category]
        identity = getattr(self.selected,definition.key_field) if self.mode is EditMode.EDIT else None
        try:
            self.service.save(self.category,self.draft,identity)
        except LibraryError as error:
            self.error_key = error.key
            return False
        self.cancel()
        try:
            self.browse(self.category,self.parent_id)
        except LibraryError:
            self.records,self.selected = (),None
            self.error_key = "library2.saved_refresh_required"
        return True
