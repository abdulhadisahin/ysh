# YSH Development Rules

## Scope and technology

- Target Python version: 3.14.
- Target platform: Windows desktop.
- User interface: Tkinter.
- Persistent storage: SQLite.
- The application must operate fully offline after installation.
- Do not introduce cloud services, external APIs, internet dependencies, or
  replacement technologies unless explicitly instructed.

## Architecture

- Preserve Clean Architecture boundaries described in
  [ARCHITECTURE.md](ARCHITECTURE.md).
- Use the Repository Pattern for persistence access.
- Use the Service Layer for application use cases.
- Keep engineering calculation logic outside Tkinter callbacks and SQLite
  repositories.
- Keep SQL and SQLite connection handling outside domain and UI code.
- Do not rename modules or redesign the architecture unless explicitly
  instructed.

## Code quality

- Follow PEP 8.
- Add type hints to all code.
- Provide docstrings for every public class and public method.
- Apply SOLID principles and favor clear single responsibilities.
- Avoid duplication; extract shared behavior only when it has a stable,
  meaningful responsibility.
- Prefer explicit, readable code over clever or implicit behavior.
- Maintain production-quality error handling and input validation.

## Change discipline

- Implement the agreed requirement only; do not expand scope without approval.
- Confirm missing calculation requirements, units, assumptions, persistence
  behavior, or user workflow details before making a consequential assumption.
- Keep changes focused and compatible with the established module structure.
- Update relevant documentation when a confirmed requirement changes behavior,
  architecture, or operational expectations.
- Do not add application source code when a task is documentation-only.

## Verification expectations

- Verify calculation behavior against agreed engineering requirements.
- Verify invalid input and boundary conditions.
- Verify repository behavior against SQLite persistence requirements.
- Verify service workflows independently from the graphical interface where
  practical.
- Verify critical Tkinter workflows on Windows.
