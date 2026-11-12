#!/usr/bin/env python3
"""Install the skills as a self-contained, versioned package. No network access."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "skills/design-harness/scripts"))
from design_kit import __version__

NAMES = ("design-bot", "design-harness", "design-implementation")
RECEIPT = ".design-kit-install.json"
IGNORED = {"__pycache__", ".DS_Store", ".pytest_cache"}


def inventory(base, names=NAMES):
    result = {}
    for name in names:
        folder = base / name
        if folder.is_symlink() or not folder.is_dir():
            raise ValueError(f"Expected an ordinary skill directory: {folder}")
        for path in sorted(folder.rglob("*")):
            if path.is_symlink():
                raise ValueError(f"Symlink is not owned by this installer: {path}")
            if any(part in IGNORED for part in path.relative_to(base).parts) or path.suffix == ".pyc":
                continue
            if path.is_file():
                result[path.relative_to(base).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def transact(destination, *, upgrade=False, remove=False):
    receipt_path = destination / RECEIPT
    if receipt_path.is_symlink():
        raise ValueError(f"Refusing symlink receipt: {receipt_path}")
    old = None
    owned = ()
    if receipt_path.exists():
        old = json.loads(receipt_path.read_text(encoding="utf-8"))
        if not isinstance(old, dict) or old.get("package") != "design-kit" or old.get("schema_version") != 1:
            raise ValueError("Unrecognized installation receipt; existing files preserved")
        files = old.get("files")
        if not isinstance(files, dict) or not files or not all(isinstance(k, str) for k in files):
            raise ValueError("Invalid owned file inventory")
        owned = tuple(sorted({name.split("/")[0] for name in files}))
        if not set(owned) <= set(NAMES):
            raise ValueError("Unknown owned skill; existing files preserved")
        if inventory(destination, owned) != files:
            raise ValueError("Installed skills were modified; preserve your edits before upgrading/removing")
    elif any((destination / name).exists() or (destination / name).is_symlink() for name in NAMES):
        raise ValueError("A same-named skill already exists without an owned receipt; existing files preserved")

    if old and not remove:
        for name in set(NAMES) - set(owned):
            if (destination / name).exists() or (destination / name).is_symlink():
                raise ValueError(f"New skill collides with an unowned directory: {name}")
    if remove and old is None:
        raise ValueError("No owned Design Kit installation found")
    source_files = inventory(ROOT / "skills") if not remove else {}
    if old and not remove and source_files == old["files"]:
        return {"ok": True, "action": "unchanged", "skills": len(NAMES), "files": len(source_files), "destination": str(destination)}
    if old and not remove and not upgrade:
        raise ValueError("An older package is installed; use --upgrade after reviewing the new version")

    receipt = {"schema_version": 1, "package": "design-kit", "version": __version__, "files": source_files}
    # Stage every skill before changing any installed directory. Roll back ordinary I/O failures.
    with tempfile.TemporaryDirectory(prefix=".design-kit-stage-", dir=destination) as temporary:
        stage = Path(temporary)
        if not remove:
            for name in NAMES:
                shutil.copytree(ROOT / "skills" / name, stage / name,
                                ignore=shutil.ignore_patterns(*IGNORED, "*.pyc"))
            if inventory(stage) != source_files:
                raise ValueError("Package changed while staging; installation cancelled")
            (stage / RECEIPT).write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        moved, written = [], []
        try:
            if old:
                for name in (*owned, RECEIPT):
                    (destination / name).rename(stage / (name + ".previous"))
                    moved.append(name)
            if not remove:
                for name in (*NAMES, RECEIPT):
                    (stage / name).rename(destination / name)
                    written.append(name)
        except BaseException:
            for name in reversed(written):
                (destination / name).rename(stage / (name + ".failed"))
            for name in reversed(moved):
                (stage / (name + ".previous")).rename(destination / name)
            raise
    return {"ok": True, "action": "removed" if remove else "upgraded" if old else "installed",
            "skills": len(owned) if remove else len(NAMES), "files": len(old["files"] if remove else source_files), "destination": str(destination)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=("codex", "claude"))
    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument("--project", type=Path, help="Existing project; install into its agent-specific skills folder")
    scope.add_argument("--skills-dir", type=Path, help="Explicit skills directory (including user-wide installations)")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--upgrade", action="store_true")
    action.add_argument("--remove", action="store_true", help="Remove only unchanged, receipt-owned skills")
    args = parser.parse_args(argv)
    if sys.version_info < (3, 11) or os.name != "posix":
        parser.error("Python 3.11+ on macOS/Linux is required")
    if args.project and not args.target:
        parser.error("--project requires --target codex or claude")
    if args.skills_dir and args.target:
        parser.error("--skills-dir is explicit; omit --target")
    try:
        if args.project:
            project = args.project.expanduser().resolve()
            if not project.is_dir():
                raise ValueError(f"Project does not exist: {project}")
            destination = project / (".agents" if args.target == "codex" else ".claude") / "skills"
            if destination.parent.is_symlink() or destination.is_symlink():
                raise ValueError("Project skills path is a symlink; use --skills-dir explicitly if that location is intended")
        else:
            destination = args.skills_dir.expanduser().resolve()
        if args.remove and not destination.is_dir():
            raise ValueError("No installation directory found")
        destination.mkdir(parents=True, exist_ok=True)
        lock = destination / ".design-kit.lock"
        if lock.is_symlink():
            raise ValueError("Refusing symlink installation lock")
        import fcntl
        with lock.open("a") as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            result = transact(destination, upgrade=args.upgrade, remove=args.remove)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
