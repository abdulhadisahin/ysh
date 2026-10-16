# Engineering libraries (Phase 13)

Existing Kütüphaneler menu/ribbon actions open one modeless workspace. Eight
engineering groups contain explicitly defined datasets, rather than arbitrary
table exposure. A service factory is registered at composition; repositories,
category rows, parent pickers and provenance are loaded only when requested.
Source lookups happen on record selection and are cached, not queried per cell.
Search, ownership, verification and active filters operate on loaded rows.

UI -> controller -> EngineeringLibraryService -> existing repositories. There
is no UI SQL, project dependency, calculator call, startup seed, schema change,
or new dependency. Browse/selection never writes. All editor fields are
allowlisted. UUID references use record pickers and repository validation.
Application default systems are visibly nonpersistent and cannot be used as
database foreign keys until a user explicitly creates an actual system row.

Factory flags (`is_factory` / legacy `is_system`) protect core records. Pipe
geometry, standard metadata and corrosion records/links remain read-only where
ownership is ambiguous. Verified, partially verified, deprecated, and unknown
verification source/rule/property records are protected. Records explicitly
marked USER_SUPPLIED or UNVERIFIED are editable under the documented service
policy. This status does not imply that their engineering data is verified.
Factory overrides and ownership migrations are deferred. User constants may
have source/context metadata edited; factory constant metadata is protected.
Only user records with an `is_active` field can be activated/deactivated. No
general delete operation exists in this service/workspace. Legacy independent
dialog classes remain for compatibility; normal Library commands use this one
workspace, including existing categories.

Sources are edited separately before being chosen by a property/link editor.
Each Save performs one repository create/update transaction with FK constraints.
No multi-record create-and-link operation is offered, so a failure cannot leave
half a compound edit. Errors preserve the draft and use localized messages.
Cancel discards it; category/window changes require Save or Cancel first.
Null metadata remains null. No date, source, verification or temperature is
inferred. Raw numeric edit values retain precision; only display is formatted.
Controlled property identifiers have no interpolation or rule-resolution logic.

Pump rows are reference vessel data, not approved manufacturer curves or design
requirements. Stored legacy source text remains a source note. No production
engineering values or standards are seeded.

Existing project inputs/results, applied pipe snapshots and FormulaSteps are
never rewritten by a library edit. Fluid properties are not connected to rho,
nu or vapor pressure. Library Refresh/Close explicitly refreshes the small
System Context catalogs/navigation against the same saved context; project IDs,
revision, numeric inputs and cached results remain unchanged. Future explicit
calculations/reselections may read newly edited master data through the existing
workflows. Historical snapshot persistence and property/rule integration remain
later work.
