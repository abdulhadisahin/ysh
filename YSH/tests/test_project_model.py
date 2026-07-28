"""Tests for the Project domain model."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from core.project import Project


def test_project_generates_uuid_automatically() -> None:
    """A new project receives a UUID identifier."""
    project = Project(name="Demo")

    assert isinstance(project.id, UUID)


def test_project_generates_timezone_aware_timestamps() -> None:
    """A new project receives timezone-aware lifecycle timestamps."""
    project = Project(name="Demo")

    assert project.created_at.tzinfo is not None
    assert project.modified_at.tzinfo is not None


def test_project_serialization_round_trip_preserves_data() -> None:
    """Project serialization and deserialization preserve all fields."""
    project = Project(name="Demo", description="Description", notes="Notes")

    restored_project = Project.from_dict(project.to_dict())

    assert restored_project == project


def test_project_touch_updates_modified_timestamp() -> None:
    """Touch replaces an earlier modification timestamp."""
    project = Project(name="Demo")
    project.modified_at = datetime(2000, 1, 1, tzinfo=timezone.utc)

    project.touch()

    assert project.modified_at > datetime(2000, 1, 1, tzinfo=timezone.utc)
