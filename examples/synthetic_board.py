#!/usr/bin/env python3
"""Create an isolated mechanical demo. These are not design-quality or user-decision evidence."""

import json
from pathlib import Path
import shlex
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "tests"), str(ROOT / "skills/design-harness/scripts")]
from design_factory import build
from design_kit.design_runs import DesignRun


if __name__ == "__main__":
    project = Path(tempfile.mkdtemp(prefix="design-kit-synthetic-"))
    ctx, manifest = build(project / "artifacts")
    (project / "design-kit.json").write_text(json.dumps({
        "schema_version": 1, "docs_root": "artifacts/hub", "code_root": "artifacts/code"}), encoding="utf-8")
    manifest["run_id"] = "browser"
    run = DesignRun(ctx, "browser")
    run.initialize(manifest)
    run.refresh("Known synthetic fixture; not a product design or actual user decision")
    result = run.prepare()
    if not result["ok"]:
        sys.exit(json.dumps(result))
    print(json.dumps({"synthetic": True, "project": str(project), "frames": result["metrics"]["delivered_frames"],
        "serve_command": shlex.join([sys.executable, str(ROOT / "design.py"), "--project-root", str(project),
                                     "serve", "--run", "browser"])}, ensure_ascii=False, indent=2))
