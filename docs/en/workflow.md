# Workflow

[Home](../../README.md) · [한국어](../ko/workflow.md) · [Installation](installation.md)

## Choose the right stage

| Starting point | Skill | Expected output |
|---|---|---|
| A brief or a new visual direction | `design-bot` | Observed references, composition studies, editable representative designs |
| Designs to compare, feedback to apply, or work to resume | `design-harness` | A comparison tied to versions, decisions, unresolved feedback, and handoff evidence |
| An approved design to implement or an app that differs from it | `design-implementation` | Application code, actual rendered measurements, and a difference report |

Use the existing project brief, brand assets, technical constraints, and user decisions. If there is no structured brief, the current agent can summarize the necessary context; no separate planning or wireframe agent is required. These skills do not automatically launch additional agents.

## 1. Explore and design

For a new direction, observe real applications and relevant Pinterest details, record source attribution, and study how hierarchy, navigation, density, and composition differ. Search summaries and unloaded screenshots are not visual evidence.

Create editable composition studies, then two directions for a representative screen, unless the user specifies another scope. A visual mockup includes representative content, needed images, surfaces, typography, and control details. A structural sketch is not a finished visual mockup.

For an existing selected direction, compare the previous and revised version of that direction. For investigation-only work, document causes without silently producing new designs. Browser authentication follows the [reference-session procedure](../../skills/design-bot/references/reference-session.md); do not store credentials in the project.

## 2. Compare, decide, and resume

Compare the same tasks, content, states, and viewport. Preserve native sources, actual PNG exports, measurements, and the reasoning behind the visual choices. The local board supports review and decision recording, but a passing numeric check is not aesthetic approval.

Record feedback and actual user decisions against the presented version. Unclassified feedback, rejected work, and change requests restrict the affected selection, expansion, or handoff. An investigation hold requires an actual instruction to resume production. Preserve earlier decisions as history; do not substitute synthetic test events or silence for approval.

Expand a new direction after the user's selection. Final handoff requires the relevant current visual review, independent-review evidence, and user decision specified by the harness. The runtime checks evidence relationships, not whether a claimed reviewer or user is genuine. See the [harness contract](../../skills/design-harness/references/contract.md).

## 3. Implement and compare the real application

Use the user's existing instruction to implement the selected version. Do not require the same approval again or reinterpret a new app name as permission to redesign the layout.

Fix the reference version, screen/state/device scope, data fixture, locale, text scale, viewport, and assets. Implement one representative screen, render it under the same conditions, then inspect and measure it before expanding shared components and other screens.

Measure the actual UI: element positions/sizes, text, actions, hierarchy, style, and required imagery. Source constants, successful builds, or functional tests are not rendered measurements. Missing features do not justify replacing the approved controls with unrelated actions.

The [implementation contract](../../skills/design-implementation/references/contract.md) defines `contract.json`, `report.json`, and measurements. Use the [capture guide](../../skills/design-implementation/references/capture.md) for the host's actual rendering path. Once those files exist, run the installed checker, for example:

```bash
PROJECT_DIR="/absolute/path/to/your-project"
SKILL_DIR="$PROJECT_DIR/.agents/skills/design-implementation"
EVIDENCE_DIR="$PROJECT_DIR/docs/design-implementation/first-screen"

python3 "$SKILL_DIR/scripts/verify.py" snapshot \
  --code-root "$PROJECT_DIR" --contract "$EVIDENCE_DIR/contract.json" \
  --output "$EVIDENCE_DIR/code.json"
python3 "$SKILL_DIR/scripts/verify.py" verify \
  --code-root "$PROJECT_DIR" --contract "$EVIDENCE_DIR/contract.json" \
  --report "$EVIDENCE_DIR/report.json"
```

For Claude Code, change `.agents` to `.claude`. Use the configured code/document roots when they are separate. The snapshot is append-only; after changes, capture again into a new evidence set rather than overwriting previous failures.

`MISMATCH` returns exit code 1. `MATCHED` means the submitted evidence and measurements agree. It does not prove complete coverage, capture provenance, visual quality, independent review, or user acceptance. The agent must invoke the checker; this is not a global hook that intercepts every implementation or completion report.

Report functional results, measured design differences, and unimplemented/unverified scope separately. Self-review must not be labeled independent review.

## Where work lives

| Artifact | Default location |
|---|---|
| Reference-first discovery | `docs/design-discovery/` |
| Design runs, feedback, comparisons, decisions | `docs/design-harness/{run-id}/` |
| Implementation evidence | `docs/design-implementation/{run-id}/` |
| Native design sources and exported images | `designs/` |

Do not write project artifacts inside the installed skills. `.pen` content must be read and edited through the dedicated design tool, not parsed as ordinary JSON. Filesystem size/mtime may be recorded separately.

## CLI and language boundaries

The CLI can check local setup, initialize a run from existing source/brief files, prepare measurements, serve a board, record events, and resume. `init` creates a draft; it does not generate designs or a complete manifest. See the [command reference](../../skills/design-harness/references/commands.md) and [environment contract](../../skills/design-harness/references/environment.md).

These English guides explain the supported workflow. Detailed contracts and much of the skill prose are currently Korean, as are some board labels. The package has not been validated as a fully localized English UI or across every agent host.
