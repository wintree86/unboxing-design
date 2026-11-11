"""Resolve artifact roots from an explicit project, independent of the caller's cwd."""

from dataclasses import dataclass
import json
from pathlib import Path


@dataclass
class ProjectContext:
    name: str | None
    code_root: Path
    docs_root: Path

    def resolve(self, rel: str) -> Path:
        if rel == "docs" or rel.startswith("docs/"):
            return self.docs_root / rel
        return self.code_root / rel


def build_context(project_root: Path, config: Path | None = None) -> ProjectContext:
    project = project_root.expanduser().resolve()
    if not project.is_dir():
        raise ValueError(f"Project directory does not exist: {project}")
    path = (config.expanduser().resolve() if config else project / "design-kit.json")
    data = {}
    if config or path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or type(data.get("schema_version")) is not int or data["schema_version"] != 1:
            raise ValueError("design-kit.json requires schema_version: 1")
        unknown = set(data) - {"schema_version", "docs_root", "code_root"}
        if unknown:
            raise ValueError(f"Unknown configuration fields: {', '.join(sorted(unknown))}")

    def root(key):
        value = data.get(key, ".")
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{key} must be a nonempty path string")
        candidate = Path(value).expanduser()
        # Relative configuration paths always refer to the selected project.
        return (candidate if candidate.is_absolute() else project / candidate).resolve()

    return ProjectContext(None, root("code_root"), root("docs_root"))
