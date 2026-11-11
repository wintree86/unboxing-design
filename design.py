#!/usr/bin/env python3
"""Run Design Kit from a checkout without installing Python packages."""

from pathlib import Path
import runpy

if __name__ == "__main__":
    import sys
    script = Path(__file__).resolve().parent / "skills/design-harness/scripts/design.py"
    sys.path.insert(0, str(script.parent))
    runpy.run_path(str(script), run_name="__main__")
