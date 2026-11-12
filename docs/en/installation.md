# Installation

[Home](../../README.md) · [한국어](../ko/installation.md) · [Workflow](workflow.md)

## Requirements

- Python 3.11 or later on macOS/Linux. No pip packages are required for installation or runtime.
- Codex or Claude Code with project skills enabled, or a host that loads `SKILL.md` instructions and runs local commands.
- For design work: browser/image observation and a design editor in the host. Pencil is the current integration. These tools, accounts, and any model/API access are not bundled.
- An existing target project; it does not need this repository's layout or a separate planning agent.

Native Windows is unsupported. WSL and individual company-managed hosts have not been verified. `doctor` checks local files and resolved paths, not host skill discovery or external services.

## Get a version

From Git:

```bash
git clone --branch v0.3.0 --depth 1 https://github.com/wintree86/unboxing-design.git
cd unboxing-design
```

Or download `design-kit-0.3.0.zip` and `design-kit-0.3.0.zip.sha256` from the [v0.3.0 release](https://github.com/wintree86/unboxing-design/releases/tag/v0.3.0), put them in the same directory, then:

```bash
# macOS; on Linux, use: sha256sum -c design-kit-0.3.0.zip.sha256
shasum -a 256 -c design-kit-0.3.0.zip.sha256
unzip design-kit-0.3.0.zip
cd design-kit-0.3.0
```

Run the installation commands from the cloned or extracted package root.

## Install into a project

Set an existing project directory, then choose your host:

```bash
PROJECT_DIR="/absolute/path/to/your-project"

# Codex
python3 install.py --target codex --project "$PROJECT_DIR"
python3 "$PROJECT_DIR/.agents/skills/design-harness/scripts/design.py" \
  --project-root "$PROJECT_DIR" doctor
```

```bash
# Claude Code, from the same package root
PROJECT_DIR="/absolute/path/to/your-project"
python3 install.py --target claude --project "$PROJECT_DIR"
python3 "$PROJECT_DIR/.claude/skills/design-harness/scripts/design.py" \
  --project-root "$PROJECT_DIR" doctor
```

Each installation copies all three skills and their runtime. It does not link back to the checkout. The installed runtime can run after the source checkout is moved or removed. Keep a release copy available for later updates/removal.

Expect `"ok": true`, `"version": "0.3.0"`, and `"skills_found": 3`. Start a new host session in the target project and select a skill. Codex uses `$design-bot`, `$design-harness`, `$design-implementation`; Claude Code uses the corresponding `/` names. If the skills do not appear, verify the target project, actual installed directories, and host policy. A doctor success alone does not prove host discovery.

## Explicit skills directory

For user-wide or custom hosts, use the host's actual skills directory:

```bash
python3 install.py --skills-dir /absolute/path/to/host/skills
```

Do not combine `--skills-dir` with `--target`. Project installation is preferable when teams need separate versions. Both host targets can coexist; each installation has its own receipt and must be updated separately.

## Project paths

No configuration file is required. By default, documents go under `<project>/docs/` and designs under `<project>/designs/`.

For separate document and code locations, put this in the target project's `design-kit.json`:

```json
{
  "schema_version": 1,
  "docs_root": "planning",
  "code_root": "app"
}
```

This means `<project>/planning/docs/` for documents and `<project>/app/designs/` for designs. Relative paths resolve against `--project-root`, not your shell's current directory or the configuration file's parent. Absolute paths are also supported. The [minimal example](../../examples/design-kit.json) uses the project itself for both roots.

## Update or remove

Obtain the version you want, review its changes, then run from that package root:

```bash
python3 install.py --target codex --project "$PROJECT_DIR" --upgrade
python3 install.py --target codex --project "$PROJECT_DIR" --remove
```

Use `--target claude` for that host. These are separate operations; removal is optional. There is no background update or automatic upload.

The installer compares owned files with `.design-kit-install.json`. It preserves unrelated skills, PRDs, designs, and decision history. A two-skill 0.2.x receipt can upgrade to the three-skill 0.3.x package. Conflicting names, symlinks, or local edits cause a failure instead of overwrite. Back up and reconcile the affected skill before retrying; do not delete the receipt to bypass the check.

## Common issues

| Symptom | Action |
|---|---|
| Project does not exist | Use an existing absolute project path. |
| Same-named skill or modified installation | Preserve the existing files and reconcile the conflict; rerun the installer. |
| Doctor succeeds but design tools fail | Check the host's actual browser/design-editor connection and permissions. |
| Reference site needs sign-in | Use the host's existing browser and official sign-in page; never put credentials in a skill. |
| Artifacts appear under an unexpected root | Inspect doctor output and `design-kit.json`; paths anchor to `--project-root`. |

The reference workflow checks Pinterest/Dribbble authentication and asks for sign-in when needed. If you explicitly choose public, signed-out research, it records that limitation. The CLI does not log in for you or guarantee session persistence.
