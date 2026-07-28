# YSH Roadmap

## Guiding principle

Work proceeds only from confirmed engineering and product requirements. Each
phase preserves the existing technology and architecture constraints: Python
3.14, Windows, Tkinter, SQLite, offline operation, Repository Pattern, Service
Layer, and Clean Architecture.

## Phase 1 — Project understanding and foundation

- [x] Record project constraints and development rules.
- [x] Document architectural boundaries and responsibilities.
- [ ] Review the existing project structure and any supplied requirements.
- [ ] Confirm supported engineering calculation domains and terminology.
- [ ] Confirm units, assumptions, precision, rounding, and validation policy.

## Phase 2 — Requirement definition

- [ ] Define each calculation workflow, required inputs, outputs, and error
  conditions.
- [ ] Define calculation traceability and any persistence requirements.
- [ ] Define the required Windows user workflows and acceptance criteria.
- [ ] Confirm data-retention and local database requirements.

## Phase 3 — Domain and application design

- [ ] Specify domain concepts and engineering calculation rules.
- [ ] Specify service-layer use cases and their input/output contracts.
- [ ] Specify repository abstractions needed by the confirmed use cases.
- [ ] Review the design for SOLID compliance and architecture boundaries.

## Phase 4 — Implementation

- [ ] Implement confirmed domain behavior.
- [ ] Implement services and repository abstractions.
- [ ] Implement SQLite repository infrastructure.
- [ ] Implement Tkinter workflows using the service layer.
- [ ] Add validation, error handling, and user feedback required by the
  confirmed workflows.

## Phase 5 — Verification and release readiness

- [ ] Verify engineering calculations against approved examples.
- [ ] Verify persistence and offline operation.
- [ ] Verify critical workflows on supported Windows environments.
- [ ] Review code for PEP 8, type hints, public API docstrings, duplication,
  and architectural compliance.
- [ ] Prepare installation, operation, and maintenance documentation.

## Current status

Documentation and development guardrails are in place. The next step is to
review the existing project material and obtain the confirmed functional
requirements before application implementation begins.
