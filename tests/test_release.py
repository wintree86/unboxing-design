import hashlib
import json
from pathlib import Path
import zipfile

from test_portable import PACKAGE, invoke


def test_release_is_repeatable_complete_and_installable(tmp_path):
    first = invoke(PACKAGE / "build_release.py", "--output", tmp_path / "first", cwd=tmp_path)
    second = invoke(PACKAGE / "build_release.py", "--output", tmp_path / "second", cwd=tmp_path)
    assert first["sha256"] == second["sha256"]
    assert hashlib.sha256(Path(first["archive"]).read_bytes()).hexdigest() == first["sha256"]
    extracted = tmp_path / "extracted"
    with zipfile.ZipFile(first["archive"]) as archive:
        names = archive.namelist()
        assert not any("__pycache__" in name or "/real/" in name or "/.git/" in name for name in names)
        archive.extractall(extracted)
    checkout = next(extracted.iterdir())
    manifest = json.loads((checkout / "package-manifest.json").read_text())
    assert len(names) == manifest["file_count"] + 1
    for name, digest in manifest["files"].items():
        assert hashlib.sha256((checkout / name).read_bytes()).hexdigest() == digest
    skills = tmp_path / "installed"
    invoke(checkout / "install.py", "--skills-dir", skills, cwd=tmp_path)
    result = invoke(skills / "design-harness/scripts/design.py", "--project-root", tmp_path, "doctor", cwd=tmp_path)
    assert result["ok"] and result["skills_found"] == 2
