"""Additive v4 -> v5 library schema; deliberately contains no engineering seeds."""
from __future__ import annotations

import sqlite3

from engineering.provenance import SourceType, VerificationStatus

# Values come only from controlled domain enums, never user-provided SQL.
_SOURCE_TYPES = ", ".join(f"'{item.value}'" for item in SourceType)
_VERIFICATION = ", ".join(f"'{item.value}'" for item in VerificationStatus)
_STATUS = f"verification_status TEXT CHECK(verification_status IN ({_VERIFICATION}))"

TABLES: dict[str, str] = {
    "sources": f"""
        id TEXT PRIMARY KEY NOT NULL,
        source_type TEXT NOT NULL CHECK(source_type IN ({_SOURCE_TYPES})),
        source_organization TEXT, document TEXT, part TEXT, section TEXT, article TEXT,
        table_reference TEXT, formula_reference TEXT, revision TEXT,
        effective_date TEXT, verification_date TEXT, {_STATUS}, notes TEXT,
        created_at TEXT NOT NULL, modified_at TEXT NOT NULL
    """,
    "rule_sets": f"""
        id TEXT PRIMARY KEY NOT NULL, code TEXT NOT NULL COLLATE NOCASE,
        name TEXT NOT NULL, organization TEXT, revision TEXT, effective_date TEXT,
        {_STATUS}, source_id TEXT REFERENCES sources(id),
        is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1)),
        created_at TEXT NOT NULL, modified_at TEXT NOT NULL, UNIQUE(code, revision)
    """,
    "systems": """
        id TEXT PRIMARY KEY NOT NULL, code TEXT NOT NULL COLLATE NOCASE UNIQUE,
        name_tr TEXT NOT NULL, name_en TEXT,
        is_factory INTEGER NOT NULL DEFAULT 0 CHECK(is_factory IN (0, 1)),
        is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1))
    """,
    "circuits": """
        id TEXT PRIMARY KEY NOT NULL, system_id TEXT NOT NULL REFERENCES systems(id),
        code TEXT NOT NULL COLLATE NOCASE, name_tr TEXT NOT NULL, name_en TEXT,
        is_factory INTEGER NOT NULL DEFAULT 0 CHECK(is_factory IN (0, 1)),
        is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1)),
        UNIQUE(system_id, code)
    """,
    "fluids": """
        id TEXT PRIMARY KEY NOT NULL, code TEXT NOT NULL COLLATE NOCASE UNIQUE,
        name_tr TEXT NOT NULL, name_en TEXT,
        is_factory INTEGER NOT NULL DEFAULT 0 CHECK(is_factory IN (0, 1)),
        is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1))
    """,
    "fluid_properties": f"""
        id TEXT PRIMARY KEY NOT NULL, fluid_id TEXT NOT NULL REFERENCES fluids(id),
        property_name TEXT NOT NULL, value REAL NOT NULL, unit TEXT NOT NULL,
        reference_temperature_c REAL, source_id TEXT REFERENCES sources(id),
        {_STATUS}, created_at TEXT NOT NULL, modified_at TEXT NOT NULL
    """,
    "material_properties": f"""
        id TEXT PRIMARY KEY NOT NULL, material_id TEXT NOT NULL REFERENCES materials(id),
        property_name TEXT NOT NULL, value REAL NOT NULL, unit TEXT NOT NULL,
        reference_temperature_c REAL, source_id TEXT REFERENCES sources(id),
        rule_set_id TEXT REFERENCES rule_sets(id), {_STATUS},
        created_at TEXT NOT NULL, modified_at TEXT NOT NULL
    """,
    "pipe_standard_metadata": """
        standard_id TEXT PRIMARY KEY NOT NULL REFERENCES pipe_standards(id),
        standard_family TEXT, source_id TEXT REFERENCES sources(id)
    """,
    "pipe_size_metadata": """
        pipe_size_id TEXT PRIMARY KEY NOT NULL REFERENCES pipe_sizes(id),
        nps TEXT, schedule TEXT, manufacturing_tolerance REAL, tolerance_unit TEXT,
        source_id TEXT REFERENCES sources(id)
    """,
    "engineering_constant_metadata": """
        constant_id TEXT PRIMARY KEY NOT NULL REFERENCES engineering_constants(id),
        source_id TEXT REFERENCES sources(id), rule_set_id TEXT REFERENCES rule_sets(id),
        system_id TEXT REFERENCES systems(id), circuit_id TEXT REFERENCES circuits(id),
        selection_reason TEXT
    """,
    "corrosion_allowance_sources": """
        corrosion_circuit_id TEXT PRIMARY KEY NOT NULL REFERENCES corrosion_allowance_circuits(id),
        source_id TEXT REFERENCES sources(id), rule_set_id TEXT REFERENCES rule_sets(id),
        circuit_id TEXT REFERENCES circuits(id)
    """,
}

# PK/UNIQUE indexes already cover parent IDs, codes, and circuits.system_id.
# Each explicit index supports one otherwise-unindexed foreign-key lookup.
INDEXES: dict[str, tuple[str, str]] = {
    "idx_rule_sets_source": ("rule_sets", "source_id"),
    "idx_fluid_properties_fluid": ("fluid_properties", "fluid_id"),
    "idx_fluid_properties_source": ("fluid_properties", "source_id"),
    "idx_material_properties_material": ("material_properties", "material_id"),
    "idx_material_properties_source": ("material_properties", "source_id"),
    "idx_material_properties_rule": ("material_properties", "rule_set_id"),
    "idx_pipe_standard_metadata_source": ("pipe_standard_metadata", "source_id"),
    "idx_pipe_size_metadata_source": ("pipe_size_metadata", "source_id"),
    "idx_constant_metadata_source": ("engineering_constant_metadata", "source_id"),
    "idx_constant_metadata_rule": ("engineering_constant_metadata", "rule_set_id"),
    "idx_constant_metadata_system": ("engineering_constant_metadata", "system_id"),
    "idx_constant_metadata_circuit": ("engineering_constant_metadata", "circuit_id"),
    "idx_corrosion_sources_source": ("corrosion_allowance_sources", "source_id"),
    "idx_corrosion_sources_rule": ("corrosion_allowance_sources", "rule_set_id"),
    "idx_corrosion_sources_circuit": ("corrosion_allowance_sources", "circuit_id"),
}


def create_v5_schema(connection: sqlite3.Connection) -> None:
    """Create new, empty relations without altering existing rows or columns."""
    for table, definition in TABLES.items():
        connection.execute(f"CREATE TABLE {table} ({definition})")
    for name, (table, column) in INDEXES.items():
        connection.execute(f"CREATE INDEX {name} ON {table} ({column})")
