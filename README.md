# YSH — Engineering Calculation System

YSH is a Windows desktop application for performing and managing engineering
calculations. It is designed for dependable, maintainable, fully offline use
after installation.

## Technology and operating constraints

- Python 3.14
- Windows desktop application
- Tkinter graphical user interface
- SQLite local database
- No cloud services, external APIs, or internet connection required after
  installation

## Engineering standards

The project follows Clean Architecture with a Repository Pattern and Service
Layer. Code must comply with SOLID principles, PEP 8, comprehensive type hints,
and public-class and public-method docstrings. Changes are expected to be
production quality and maintain the agreed architecture.

## Intended development flow

1. Confirm the calculation requirement, inputs, outputs, units, assumptions,
   and validation rules.
2. Model the required domain concepts and use cases without coupling them to
   Tkinter or SQLite.
3. Add repository abstractions and SQLite implementations as required.
4. Implement services that coordinate domain rules and persistence.
5. Implement the Tkinter presentation flow using the service layer only.
6. Test calculations, validation, persistence, and user-facing workflows.

## Documentation

- [Architecture](ARCHITECTURE.md)
- [Development rules](RULES.md)
- [Roadmap](ROADMAP.md)

## Status

The project is in its development-preparation phase. Application source code is
not introduced by this documentation set.

# ysh
