from core.project_repository import ProjectRepository


class ProjectService:
    """Placeholder service layer for project operations."""

    def __init__(self, repository: ProjectRepository | None = None) -> None:
        self.repository = repository or ProjectRepository()
