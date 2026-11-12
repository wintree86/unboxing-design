# Design Kit

**English** · [한국어](README.ko.md)

A portable skill package for taking a product brief through visual design, user decisions, and implementation that stays faithful to the approved design. Install it into a Codex or Claude Code project; your project keeps its own artifacts and history.

| Skill | Responsibility |
|---|---|
| [design-bot](skills/design-bot/SKILL.md) | Observe references, study composition, and create editable representative designs. |
| [design-harness](skills/design-harness/SKILL.md) | Compare designs, record feedback and decisions, resume work, and check handoff evidence. |
| [design-implementation](skills/design-implementation/SKILL.md) | Implement an approved design and compare it with the actual rendered application. |

The included Python tools check recorded evidence, track changes, and serve a local comparison board. They do not generate designs, call models, or replace visual judgment.

## Quick start

Requirements: **Python 3.11+**, **macOS or Linux**, and an existing target project. Installation and runtime use only the Python standard library. Your host agent needs its own browser/visual observation and design editing tools; Pencil is the current design integration.

```bash
git clone --branch v0.3.0 --depth 1 https://github.com/wintree86/unboxing-design.git
cd unboxing-design

# Replace this with an existing project directory.
PROJECT_DIR="/absolute/path/to/your-project"
python3 install.py --target codex --project "$PROJECT_DIR"
python3 "$PROJECT_DIR/.agents/skills/design-harness/scripts/design.py" \
  --project-root "$PROJECT_DIR" doctor
```

For Claude Code, use `--target claude`; its installed path starts with `.claude/skills/`. A successful doctor result reports `"ok": true` and `"skills_found": 3`. It does not verify external tool connections.

Start a new agent session in the target project. In Codex, try:

```text
Use $design-bot and $design-harness to design the main screen from docs/prd.md.
Observe real references, compare two representative directions, and wait for my choice.
```

For an approved design:

```text
Use $design-implementation to implement the selected design.
Compare the real app with the reference at the same size, state, language, and data.
Report functional tests and remaining design differences separately.
```

Claude Code exposes the same skills as `/design-bot`, `/design-harness`, and `/design-implementation`.

## Documentation

| Topic | English | 한국어 |
|---|---|---|
| Installation, updates, configuration, troubleshooting | [Installation](docs/en/installation.md) | [설치 안내](docs/ko/installation.md) |
| Design, feedback, implementation, verification limits | [Workflow](docs/en/workflow.md) | [사용 흐름](docs/ko/workflow.md) |
| Tests, packaging, contribution guidelines | [Contributing](docs/en/contributing.md) | [기여 안내](docs/ko/contributing.md) |

[Versioned downloads](https://github.com/wintree86/unboxing-design/releases) include an installable ZIP and SHA-256 checksum. Pin a version when sharing a workflow with a team. Existing two-skill installations can upgrade to the three-skill package without replacing project artifacts.

## Scope and license

English and Korean onboarding documentation are included. Detailed skill/reference files and some comparison-board labels are currently Korean; this is not a fully localized UI release. You can ask the host agent to write its deliverables in your preferred language.

Native Windows is unsupported because the runtime uses POSIX file locking. A local check passing does not establish design quality, genuine user approval, or successful external tool access. The implementation verifier checks submitted measurements and evidence; the agent must capture and review the real application.

[MIT License](LICENSE). Browser accounts, model access, and design tools are configured separately; the installer does not change MCP settings or store credentials.
