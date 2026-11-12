# Design Kit

[English](README.md) · **한국어**

제품 기획에서 시각 디자인·사용자 결정·승인 시안 구현까지 연결하는 독립 스킬 패키지입니다. Codex 또는 Claude Code 프로젝트에 설치하며 산출물과 작업 이력은 해당 프로젝트에 보존합니다.

| 스킬 | 역할 |
|---|---|
| [design-bot](skills/design-bot/SKILL.md) | 실제 레퍼런스 관찰, 구성 연구, 편집 가능한 대표 시안 제작 |
| [design-harness](skills/design-harness/SKILL.md) | 시안 비교, 피드백·사용자 결정 기록, 재개, 인계 근거 검사 |
| [design-implementation](skills/design-implementation/SKILL.md) | 승인 시안 구현 및 실제 렌더된 앱과의 비교 |

함께 제공되는 Python 도구는 근거 연결·변경 감지·로컬 비교 보드를 담당합니다. 디자인 생성이나 모델 호출을 하지 않으며 시각적 판단을 대신하지 않습니다.

## 빠른 시작

**Python 3.11+**, **macOS 또는 Linux**, 기존 대상 프로젝트가 필요합니다. 설치와 실행에는 Python 표준 라이브러리만 사용합니다. 브라우저·이미지 관찰·디자인 편집 도구는 호스트 에이전트에 별도로 연결해야 하며, 현재 디자인 연동은 Pencil 기준입니다.

```bash
git clone --branch v0.3.0 --depth 1 https://github.com/wintree86/unboxing-design.git
cd unboxing-design

# 이미 존재하는 대상 프로젝트 경로로 바꿉니다.
PROJECT_DIR="/absolute/path/to/your-project"
python3 install.py --target codex --project "$PROJECT_DIR"
python3 "$PROJECT_DIR/.agents/skills/design-harness/scripts/design.py" \
  --project-root "$PROJECT_DIR" doctor
```

Claude Code는 `--target claude`를 사용하고 설치 경로는 `.claude/skills/`로 바뀝니다. doctor 결과의 `"ok": true`, `"skills_found": 3`이 로컬 설치 확인 기준입니다. 외부 도구 연결 성공을 뜻하지는 않습니다.

대상 프로젝트에서 새 에이전트 세션을 열고 Codex에 다음처럼 요청합니다.

```text
$design-bot과 $design-harness로 docs/prd.md의 주요 화면을 디자인해줘.
실제 레퍼런스를 관찰하고 대표 화면 두 안을 비교한 뒤 내 선택을 기다려줘.
```

이미 선택한 디자인을 구현할 때는 다음처럼 요청합니다.

```text
$design-implementation으로 선택한 디자인을 구현해줘.
같은 크기·상태·언어·데이터에서 실제 앱과 기준을 비교하고,
기능 테스트와 남은 디자인 차이를 따로 보고해줘.
```

Claude Code의 호출 이름은 `/design-bot`, `/design-harness`, `/design-implementation`입니다.

## 문서

| 주제 | 한국어 | English |
|---|---|---|
| 설치·업데이트·설정·문제 해결 | [설치 안내](docs/ko/installation.md) | [Installation](docs/en/installation.md) |
| 디자인·피드백·구현·검증 한계 | [사용 흐름](docs/ko/workflow.md) | [Workflow](docs/en/workflow.md) |
| 테스트·패키징·기여 규칙 | [기여 안내](docs/ko/contributing.md) | [Contributing](docs/en/contributing.md) |

[버전별 다운로드](https://github.com/wintree86/unboxing-design/releases)에서 설치용 ZIP과 SHA-256 체크섬을 제공합니다. 팀에서는 검증한 버전을 고정해 사용하세요. 기존 두 스킬 설치도 프로젝트 산출물을 유지하면서 세 스킬로 업그레이드할 수 있습니다.

## 지원 범위와 라이선스

한국어·영어 입문 문서를 제공합니다. 상세 스킬·참조 문서와 비교 보드의 일부 문구는 현재 한국어이며, UI 전체 다국어화를 완료한 버전은 아닙니다. 호스트 에이전트에는 원하는 언어로 산출물을 작성하도록 요청할 수 있습니다.

POSIX 파일 잠금을 사용하므로 Windows 네이티브는 지원하지 않습니다. 로컬 검사 통과를 미적 완성도·사용자 승인 진위·외부 도구 연결 성공으로 해석하지 않습니다. 구현 검사기는 제출된 측정과 근거를 검사하며 실제 앱 캡처·시각 검토는 담당 에이전트가 수행합니다.

[MIT 라이선스](LICENSE)로 배포합니다. 브라우저 계정·모델 이용 권한·디자인 도구는 별도 설정하며 설치기는 MCP 설정을 변경하거나 자격 증명을 저장하지 않습니다.
