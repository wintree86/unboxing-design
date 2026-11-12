import hashlib
import json
import re
from urllib.parse import unquote, urlsplit
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
    public_docs = ["README.md", "README.ko.md"] + [
        f"docs/{language}/{topic}.md"
        for language in ("en", "ko")
        for topic in ("installation", "workflow", "contributing")
    ]
    assert {"LICENSE", *public_docs} <= manifest["files"].keys()
    # Check the extracted distribution, so links cannot silently depend on files
    # present only in the source checkout.
    checked_links = 0
    for name in public_docs:
        page = checkout / name
        prose = re.sub(r"```.*?```", "", page.read_text(), flags=re.S)
        for href in re.findall(r"\[[^\]]+\]\(([^)]+)\)", prose):
            url = urlsplit(href)
            if url.scheme or url.netloc or not url.path:
                continue
            target = (page.parent / unquote(url.path)).resolve()
            assert target.is_relative_to(checkout.resolve()) and target.is_file(), (name, href)
            checked_links += 1
    assert checked_links > 0
    for name, digest in manifest["files"].items():
        assert hashlib.sha256((checkout / name).read_bytes()).hexdigest() == digest
    skills = tmp_path / "installed"
    invoke(checkout / "install.py", "--skills-dir", skills, cwd=tmp_path)
    result = invoke(skills / "design-harness/scripts/design.py", "--project-root", tmp_path, "doctor", cwd=tmp_path)
    assert result["ok"] and result["skills_found"] == 3
