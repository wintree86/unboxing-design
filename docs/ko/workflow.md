# 사용 흐름

[처음으로](../../README.ko.md) · [English](../en/workflow.md) · [설치 안내](installation.md)

## 현재 단계에 맞는 스킬

| 시작점 | 스킬 | 산출물 |
|---|---|---|
| 기획서 또는 새 시각 방향 | `design-bot` | 관찰한 레퍼런스·구성 연구·편집 가능한 대표 시안 |
| 시안 비교·피드백 적용·작업 재개 | `design-harness` | 버전과 연결된 비교·결정·미해결 피드백·인계 근거 |
| 승인 시안 구현 또는 앱과의 차이 수정 | `design-implementation` | 앱 코드·실제 렌더 측정·차이 보고 |

기존 기획·브랜드 자산·기술 제약·사용자 결정을 먼저 사용합니다. 정리된 기획서가 없으면 현재 에이전트가 필요한 맥락을 요약할 수 있습니다. 별도 기획·와이어프레임 에이전트는 필수가 아니며 추가 에이전트를 자동 실행하지 않습니다.

## 1. 탐색과 디자인

새 방향은 실제 앱과 Pinterest 상세를 관찰하고 출처를 기록하며 위계·탐색·밀도·구성이 어떻게 다른지 연구합니다. 검색 요약이나 로딩 중인 캡처를 시각 근거로 사용하지 않습니다.

편집 가능한 구성 연구를 만든 뒤 대표 화면의 두 방향을 제작합니다. 사용자가 다른 범위를 지정하면 우선합니다. 시각 목업에는 대표 콘텐츠·필요 이미지·표면·서체·조작 디테일이 포함됩니다. 구조 스케치는 완성된 시각 목업과 구분합니다.

선택한 방향을 수정할 때는 그 안의 이전·수정 버전을 비교합니다. 원인 조사만 요청받았다면 새 디자인을 만들지 않고 원인을 정리합니다. 브라우저 인증은 [레퍼런스 세션 절차](../../skills/design-bot/references/reference-session.md)를 따르며 프로젝트에 자격 증명을 저장하지 않습니다.

## 2. 비교·결정·재개

동일한 과업·콘텐츠·상태·뷰포트로 비교합니다. 편집 원본·실제 PNG·측정·시각 선택의 이유를 보존합니다. 로컬 보드에서 검토·결정을 기록할 수 있지만 수치 통과를 미적 승인으로 대신하지 않습니다.

피드백과 실제 사용자 결정을 제시한 버전에 연결합니다. 미분류 피드백·거절·변경 요청은 해당 범위의 선택·확장·인계를 제한합니다. 원인 조사 중지는 실제 사용자의 제작 재개 지시로 해제합니다. 과거 결정은 이력으로 보존하고 합성 테스트 이벤트나 무응답을 승인으로 쓰지 않습니다.

새 방향은 사용자가 선택한 뒤 확장합니다. 최종 인계에는 하네스가 요구하는 현재 시각 검토·독립 검토 근거·사용자 결정이 필요합니다. 실행기는 근거의 연결을 검사하며 검토자·사용자 주장의 진위를 인증하지 않습니다. [하네스 계약](../../skills/design-harness/references/contract.md)을 참고하세요.

## 3. 구현과 실제 앱 비교

이미 선택한 버전을 구현하라는 사용자 지시를 사용합니다. 같은 승인을 다시 요구하거나 새 서비스명을 전체 배치 재설계의 허락으로 해석하지 않습니다.

기준 버전·화면/상태/기기 범위·데이터 fixture·언어·글자 배율·뷰포트·자산을 고정합니다. 대표 화면 하나를 구현한 뒤 같은 조건으로 렌더해 관찰·측정하고, 공통 컴포넌트와 다른 화면을 확장합니다.

실제 UI의 좌표·크기·문구·행동·위계·스타일·필수 이미지를 측정합니다. 소스 상수·빌드 성공·기능 테스트를 렌더 측정으로 대신하지 않습니다. 미구현 기능을 이유로 승인된 조작을 다른 행동으로 바꾸지 않습니다.

[구현 계약](../../skills/design-implementation/references/contract.md)은 `contract.json`·`report.json`·측정 파일 형식을 설명합니다. 실제 렌더 경로는 [캡처 안내](../../skills/design-implementation/references/capture.md)를 따릅니다. 이 파일들을 준비한 뒤 설치된 검사기를 실행합니다.

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

Claude Code는 `.agents`를 `.claude`로 바꿉니다. 코드·문서 루트가 분리되어 있으면 실제 설정 경로를 사용합니다. 스냅샷은 덮어쓰지 않습니다. 변경 후 새 근거 세트로 다시 캡처하고 이전 실패를 보존합니다.

`MISMATCH`는 종료코드 1을 반환합니다. `MATCHED`는 제출 근거와 측정이 일치한다는 뜻이며 전체 범위·캡처 출처·미적 품질·독립 검토·사용자 수용을 인증하지 않습니다. 담당 에이전트가 검사기를 호출해야 하며 모든 구현·완료 보고를 가로채는 전역 훅은 아닙니다.

기능 결과·실측 디자인 차이·미구현/미검증 범위를 별도로 보고합니다. 자기 검토를 독립 리뷰로 기록하지 않습니다.

## 산출물 위치

| 산출물 | 기본 위치 |
|---|---|
| 선행 레퍼런스 탐색 | `docs/design-discovery/` |
| 디자인 실행·피드백·비교·결정 | `docs/design-harness/{run-id}/` |
| 구현 비교 근거 | `docs/design-implementation/{run-id}/` |
| 편집 원본·내보낸 이미지 | `designs/` |

설치된 스킬 안에 프로젝트 산출물을 쓰지 않습니다. `.pen` 내용은 전용 디자인 도구로 읽고 수정하며 일반 JSON처럼 파싱하지 않습니다. 파일 크기·수정 시각은 별도 기록할 수 있습니다.

## CLI와 언어 범위

CLI는 로컬 상태 확인, 기존 소스/brief를 사용한 실행 초기화, 측정 준비, 비교 보드, 이벤트 기록, 재개를 제공합니다. `init`은 초안을 만들며 시안이나 완성된 manifest를 생성하지 않습니다. [명령 참조](../../skills/design-harness/references/commands.md)와 [환경 계약](../../skills/design-harness/references/environment.md)을 참고하세요.

한국어·영어 사용 안내를 제공하지만 상세 계약·스킬 본문과 보드의 일부 문구는 현재 한국어입니다. 영어 UI 전체와 모든 에이전트 호스트를 검증한 패키지는 아닙니다.
