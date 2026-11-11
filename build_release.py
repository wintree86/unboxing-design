#!/usr/bin/env python3
"""Build a deterministic ZIP from the explicit distribution allowlist."""

import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "skills/design-harness/scripts"))
from design_kit import __version__

FILES = ("README.md", "AGENTS.md", ".gitignore", "pytest.ini", "design.py", "install.py", "build_release.py")
DIRECTORIES = ("skills", "tests", "examples")


def build(output):
    payload = {}
    paths = [ROOT / p for p in FILES]
    for name in DIRECTORIES:
        paths.extend((ROOT / name).rglob("*"))
    for path in sorted(paths):
        rel = path.relative_to(ROOT)
        if any(p in {"__pycache__", ".pytest_cache", ".DS_Store"} for p in rel.parts) or path.suffix == ".pyc":
            continue
        if path.is_symlink():
            raise ValueError(f"Distribution inputs must not be symlinks: {rel}")
        if path.is_dir():
            continue
        payload[rel.as_posix()] = path.read_bytes()
    manifest = {"package": "design-kit", "version": __version__, "file_count": len(payload),
                "files": {name: hashlib.sha256(data).hexdigest() for name, data in payload.items()}}
    payload["package-manifest.json"] = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f"design-kit-{__version__}.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as stream:
        for name, data in sorted(payload.items()):
            info = zipfile.ZipInfo(f"design-kit-{__version__}/{name}", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            info.create_system = 3
            stream.writestr(info, data)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix(".zip.sha256").write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    return {"ok": True, "version": __version__, "archive": str(archive.resolve()),
            "files": manifest["file_count"], "bytes": archive.stat().st_size, "sha256": digest}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    print(json.dumps(build(args.output.expanduser().resolve()), indent=2))
