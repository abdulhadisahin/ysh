# YSH Architecture

## Purpose

YSH uses Clean Architecture to keep engineering calculation rules independent
from the Windows interface and SQLite storage. The architecture is constrained
to Python 3.14, Tkinter, and SQLite, and operates entirely offline after
installation.

## Dependency direction

Dependencies point inward. Outer layers may depend on inner layers; inner
layers must not depend on Tkinter, SQLite, operating-system details, or other
infrastructure concerns.

```
Tkinter UI  ─┐
SQLite      ─┼──> Service Layer ───> Domain
Repositories ─┘
```

## Architectural responsibilities

### Domain

The domain contains engineering concepts, calculation rules, units and
validation rules that belong to the problem domain. It remains independent of
GUI widgets and database access.

### Service Layer

Services implement application use cases and coordinate domain logic with
repositories. A service defines the business operation performed for a user
workflow and provides a stable boundary for the user interface.

### Repository Pattern

Repositories provide persistence-oriented interfaces required by services.
Their SQLite implementations handle database-specific work. Services use the
repository abstractions rather than issuing SQL directly.

### Tkinter user interface

The Tkinter layer presents input and output, gathers user actions, and displays
validation feedback. It delegates business operations to services and does not
contain calculation logic or SQL.

### SQLite persistence

SQLite is the local persistence mechanism. Database access is contained within
repository implementations and related infrastructure code. The database must
not require a network connection or cloud-hosted service.

## Key boundaries

| Concern | Permitted location | Not permitted |
| --- | --- | --- |
| Engineering calculation logic | Domain and, where applicable, services | Tkinter callbacks or SQL repositories |
| Workflow orchestration | Services | Tkinter widgets or raw SQLite access from UI |
| SQL and database connection handling | SQLite repository implementations | Domain or UI |
| User interaction and display | Tkinter UI | Domain entities or repositories |

## Architectural rules

- The UI communicates with application behavior through the Service Layer.
- Repositories are accessed through their abstractions by services.
- SQLite-specific types, SQL, and connection details do not cross into domain
  or UI code.
- Domain behavior must remain testable without Tkinter or a production database.
- New requirements must preserve these dependency boundaries; no substitute
  technologies are introduced without an explicit project instruction.

## Quality attributes

The architecture supports offline operation, maintainability, testability,
clear separation of responsibilities, and safe evolution of calculation
features. SOLID principles guide class and interface design.
