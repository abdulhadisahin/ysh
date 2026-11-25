"""Small, merge-preserving user-local preferences, never project data."""
import json
import logging
from pathlib import Path
from tempfile import NamedTemporaryFile


class UserSettings:
    def __init__(self, path):
        self.path = Path(path)

    def read(self):
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, ValueError, UnicodeError):
            return {}

    def update(self, **changes):
        temporary = None
        try:
            # Preserve unknown keys, including legacy language preferences.
            data = self.read()
            if all(data.get(key) == value for key, value in changes.items()):
                return
            data.update(changes)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.path.parent,
                                    suffix=".tmp", delete=False) as stream:
                temporary = Path(stream.name)
                json.dump(data, stream, ensure_ascii=False)
            temporary.replace(self.path)
        except OSError:
            logging.getLogger(__name__).warning("Unable to persist user preferences.")
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass

    def session(self):
        value = self.read().get("project_session", {})
        return value if isinstance(value, dict) else {}

    def remember(self, project_id, module=None):
        session = self.session()
        tabs = session.get("tabs", {})
        tabs = dict(tabs) if isinstance(tabs, dict) else {}
        if module is not None:
            tabs[str(project_id)] = module
        self.update(project_session={"last_project_id": str(project_id), "tabs": tabs})
