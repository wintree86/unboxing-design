#!/usr/bin/env python3
"""Installed entry point; the sibling runtime travels with this skill."""

import os
import sys

if __name__ == "__main__":
    if sys.version_info < (3, 11) or os.name != "posix":
        sys.exit("Design Kit requires Python 3.11+ on macOS/Linux (POSIX file locks).")
    from design_kit.design_harness import cli
    sys.exit(cli())
