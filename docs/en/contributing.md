# Contributing

[Home](../../README.md) · [한국어](../ko/contributing.md) · [Installation](installation.md)

## Development setup

Work in this source repository, not an installed copy. Python 3.11+ on macOS/Linux is required. Only development tests need pytest; the installed runtime has no third-party Python dependencies.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install pytest
.venv/bin/python -m pytest -q
```

Report the command, results, and unverified scope. Functional tests, evidence consistency, visual judgment, independent review, and user acceptance are different claims.

## Source layout

| Path | Purpose |
|---|---|
| `skills/design-bot/` | Visual discovery and design instructions |
| `skills/design-harness/` | Comparison and decision instructions; shared Python runtime under `scripts/design_kit/` |
| `skills/design-implementation/` | Approved-design implementation instructions and verifier |
| `install.py` | Receipt-based installation, upgrade, and removal |
| `build_release.py` | Deterministic ZIP and per-file manifest |
| `tests/`, `examples/` | Synthetic fixtures, portability tests, and examples |
| `docs/en/`, `docs/ko/` | Paired user documentation |

Keep portable runtime code independent of developer-specific paths, company registries, model SDKs, credentials, and private project data. Do not duplicate common logic in consuming repositories. Read the maintenance rules in [AGENTS.md](../../AGENTS.md).

## Changes and verification

For installer changes, verify conflicts, local-edit preservation, rollback, both host directories, and execution after the source checkout is removed. For evidence checks, use known synthetic answers and permitted real samples; do not alter tolerances just to pass a failing design. Never turn synthetic decisions into actual approval records.

Keep the English/Korean READMEs and relevant paired guides consistent. Preserve relative links so documentation works in GitHub and the release ZIP. Advanced skill references currently remain Korean; identify translation coverage honestly.

Use [GitHub issues](https://github.com/wintree86/unboxing-design/issues) for reproducible bugs and [pull requests](https://github.com/wintree86/unboxing-design/pulls) for changes. Include the version, Python/OS, exact command, expected/observed result, and a minimal sanitized fixture. Exclude private designs, tokens, browser profiles, and unlicensed reference material.

## Build a distribution

```bash
python3 build_release.py --output /absolute/path/to/release-output
```

The output contains `design-kit-VERSION.zip` and its `.zip.sha256` checksum. The ZIP includes both READMEs, paired guides, LICENSE, skills, runtime, tests, examples, and a per-file SHA-256 manifest. It excludes Git history, caches, local run artifacts, and company project data. Versioning lives in `skills/design-harness/scripts/design_kit/__init__.py`.

Before publishing, run the tests, extract the ZIP into a clean directory, and install it into disposable Codex and Claude Code projects. Verify the installed doctor and the implementation verifier entry point, preserve unrelated files, and check all packaged documentation links. Local packaging does not publish anything; pushing a version tag and uploading the release are separate maintainer actions.

For a release, make sure the version in the runtime, quick-start tag, archive names, and release notes agree. Published version tags should stay stable.

## License

The package is distributed under the [MIT License](../../LICENSE). Retain the license and copyright notice when redistributing. Contributions should be compatible with that license; include only material you are entitled to contribute.
