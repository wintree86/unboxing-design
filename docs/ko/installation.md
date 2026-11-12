# 설치 안내

[처음으로](../../README.ko.md) · [English](../en/installation.md) · [사용 흐름](workflow.md)

## 준비 사항

- macOS/Linux와 Python 3.11 이상. 설치·실행에 pip 패키지는 필요 없습니다.
- 프로젝트 스킬을 사용할 수 있는 Codex 또는 Claude Code. 자체 호스트는 `SKILL.md`를 읽고 로컬 명령을 실행해야 합니다.
- 디자인 작업에는 호스트의 브라우저·이미지 관찰·디자인 편집 도구가 필요합니다. 현재 연동은 Pencil 기준이며 도구·계정·모델/API 이용 권한은 포함하지 않습니다.
- 기존 대상 프로젝트. 이 저장소와 같은 폴더 구조나 별도 기획 에이전트는 필요 없습니다.

Windows 네이티브는 지원하지 않습니다. WSL과 개별 회사 관리 호스트는 미검증입니다. `doctor`는 로컬 파일·경로를 검사하며 호스트의 스킬 인식이나 외부 서비스 접속을 검사하지 않습니다.

## 버전 받기

Git으로 받습니다.

```bash
git clone --branch v0.3.0 --depth 1 https://github.com/wintree86/unboxing-design.git
cd unboxing-design
```

또는 [v0.3.0 릴리스](https://github.com/wintree86/unboxing-design/releases/tag/v0.3.0)에서 `design-kit-0.3.0.zip`과 `design-kit-0.3.0.zip.sha256`을 같은 폴더에 받은 뒤 실행합니다.

```bash
# macOS. Linux에서는: sha256sum -c design-kit-0.3.0.zip.sha256
shasum -a 256 -c design-kit-0.3.0.zip.sha256
unzip design-kit-0.3.0.zip
cd design-kit-0.3.0
```

이후 설치 명령은 복제하거나 압축을 푼 패키지 루트에서 실행합니다.

## 프로젝트에 설치

이미 존재하는 프로젝트 경로를 지정하고 호스트를 선택합니다.

```bash
PROJECT_DIR="/absolute/path/to/your-project"

# Codex
python3 install.py --target codex --project "$PROJECT_DIR"
python3 "$PROJECT_DIR/.agents/skills/design-harness/scripts/design.py" \
  --project-root "$PROJECT_DIR" doctor
```

```bash
# 같은 패키지 루트에서 Claude Code에 설치
PROJECT_DIR="/absolute/path/to/your-project"
python3 install.py --target claude --project "$PROJECT_DIR"
python3 "$PROJECT_DIR/.claude/skills/design-harness/scripts/design.py" \
  --project-root "$PROJECT_DIR" doctor
```

세 스킬과 실행기를 복사하며 원본 checkout에 심볼릭 링크로 연결하지 않습니다. 원본을 이동·삭제해도 설치된 실행기는 동작합니다. 향후 업데이트·제거용으로 릴리스 사본을 보관하면 편리합니다.

결과의 `"ok": true`, `"version": "0.3.0"`, `"skills_found": 3`을 확인합니다. 대상 프로젝트에서 새 호스트 세션을 열어 스킬을 선택합니다. Codex는 `$design-bot`·`$design-harness`·`$design-implementation`, Claude Code는 같은 이름의 `/` 명령을 사용합니다. 목록에 보이지 않으면 대상 프로젝트·설치 폴더·호스트 정책을 확인하세요. doctor 성공만으로 호스트 인식을 입증하지는 않습니다.

## 직접 스킬 경로 지정

사용자 공통 설치나 자체 호스트는 실제 스킬 경로를 지정합니다.

```bash
python3 install.py --skills-dir /absolute/path/to/host/skills
```

`--skills-dir`와 `--target`은 함께 사용하지 않습니다. 팀별 버전 분리에는 프로젝트 설치를 권장합니다. 두 호스트에 동시에 설치할 수 있으며 각 설치 영수증과 업데이트는 별개입니다.

## 프로젝트 경로

설정 파일 없이 문서는 `<project>/docs/`, 디자인은 `<project>/designs/`에 저장됩니다.

문서와 코드가 분리된 경우 대상 프로젝트 루트에 `design-kit.json`을 둡니다.

```json
{
  "schema_version": 1,
  "docs_root": "planning",
  "code_root": "app"
}
```

문서는 `<project>/planning/docs/`, 디자인은 `<project>/app/designs/`를 사용합니다. 상대 경로의 기준은 항상 `--project-root`이며 셸 현재 폴더나 설정 파일이 있는 폴더가 아닙니다. 절대 경로도 지원합니다. [최소 예제](../../examples/design-kit.json)는 둘 다 프로젝트 자체를 사용합니다.

## 업데이트와 제거

사용할 버전을 받고 변경 내용을 검토한 뒤 해당 패키지 루트에서 실행합니다.

```bash
python3 install.py --target codex --project "$PROJECT_DIR" --upgrade
python3 install.py --target codex --project "$PROJECT_DIR" --remove
```

Claude Code는 `--target claude`로 바꿉니다. 업데이트와 제거는 별도 작업이며 제거는 필요할 때만 실행합니다. 백그라운드 자동 업데이트·업로드는 없습니다.

설치기는 `.design-kit-install.json`의 소유 파일과 현재 지문을 대조합니다. 다른 스킬·PRD·디자인·결정 이력은 유지합니다. 0.2.x의 두 스킬도 0.3.x의 세 스킬로 업그레이드할 수 있습니다. 이름 충돌·심볼릭 링크·로컬 수정이 있으면 덮어쓰지 않고 실패합니다. 해당 스킬을 백업하고 충돌을 정리한 뒤 다시 실행하세요. 검사를 피하려고 영수증을 삭제하지 않습니다.

## 문제 해결

| 증상 | 확인할 내용 |
|---|---|
| 프로젝트가 없다는 오류 | 이미 존재하는 절대 경로 지정 |
| 동일 이름 스킬·수정된 설치 오류 | 기존 파일을 보존하고 충돌을 정리한 뒤 재시도 |
| doctor는 성공하지만 디자인 도구 실패 | 호스트의 실제 브라우저·디자인 편집기 연결과 권한 |
| 레퍼런스 사이트 로그인 필요 | 기존 브라우저의 공식 로그인 화면 사용; 스킬에 자격 증명 저장 금지 |
| 산출물이 예상과 다른 곳에 저장됨 | doctor와 design-kit.json 확인; 기준은 --project-root |

Pinterest·Dribbble 탐색 절차는 인증 상태를 확인하고 필요하면 로그인을 요청합니다. 사용자가 명시적으로 비로그인 공개 탐색을 선택하면 한계를 기록하고 진행합니다. CLI가 자동 로그인하거나 세션 유지를 보장하지는 않습니다.
