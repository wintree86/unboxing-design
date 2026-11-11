# Design Kit

레퍼런스 분석과 편집 가능한 구성 연구를 바탕으로 대표 화면 두 안을 만들고, 시각 검토와 실제 사용자 선택 후 확장하는 독립 스킬 패키지입니다.

- `design-bot`: 레퍼런스 탐색·구성 연구·대표 시안 제작.
- `design-harness`: 시각 검토·비교·사용자 결정·재개·최종 인계.
- 포함된 Python 실행기: 파일 지문, 정적 측정, 로컬 비교 보드, 결정 기록.

Python 3.11+, macOS/Linux가 필요합니다. 실행·설치에는 외부 Python 패키지, 모델 SDK, 허브 등록부가 필요 없습니다. Windows 네이티브는 POSIX 파일 잠금 때문에 지원하지 않습니다. 디자인 제작에는 호스트 에이전트의 웹/이미지 관찰과 디자인 편집 도구가 별도로 필요합니다. 최초 연결 경로는 Pencil이며 설치기가 MCP나 계정 설정을 변경하지 않습니다.

## 설치

이 폴더 전체를 새 Git 저장소의 루트로 사용하거나 압축을 풀어 사용합니다. 아래 명령은 이 패키지 루트에서 실행합니다. 프로젝트 경로는 실제 경로로 바꿉니다.

```bash
# Codex 프로젝트
python3 install.py --target codex --project /absolute/company-project

# Claude Code 프로젝트
python3 install.py --target claude --project /absolute/company-project

# 설치된 실행기로 확인
python3 /absolute/company-project/.agents/skills/design-harness/scripts/design.py --project-root /absolute/company-project doctor
```

Codex에는 `.agents/skills/`, Claude Code에는 `.claude/skills/`로 두 스킬과 실행기를 **복사**합니다. 두 폴더 사이 상대 참조를 유지하며 원본 checkout을 이동·삭제해도 실행됩니다. 설치 후 다음 대화에서 스킬을 사용합니다. 기존 스킬 인식이 갱신되지 않으면 새 세션을 시작합니다.

사용자 공통 설치는 `--skills-dir`에 실제 에이전트의 스킬 디렉토리를 지정합니다. 회사별 입력과 버전 관리에는 프로젝트 설치를 권장합니다. 자체 에이전트는 `skills/*/SKILL.md`를 로드하고 `design.py`를 호출할 수 있습니다. 런타임이 디자인을 생성하거나 에이전트를 자동 호출하지는 않습니다.

## 사용

Codex에서 `$design-bot`, `$design-harness`, Claude Code에서 `/design-bot`, `/design-harness`로 호출합니다. 예:

> design-bot과 design-harness로 docs/prd.md의 오늘 할 일 화면을 디자인해줘. 레퍼런스를 실제로 관찰하고, 대표 화면 두 안을 비교한 뒤 내 선택을 기다려줘.

기획서·브랜드 지침·기술 제약은 대상 프로젝트에 둡니다. 첫 단계에서 기존 자료를 읽고 연결 도구를 확인합니다. 별도 planner/wireframe 봇은 필요 없습니다. 구조 자료가 없으면 현재 에이전트가 필요한 요약을 작성합니다. 산출물은 프로젝트의 `docs/`와 `designs/`에 남습니다.

기본 설정 파일은 필요 없습니다. 문서와 코드 위치가 다르면 [설정 예제](examples/design-kit.json)를 프로젝트 루트의 `design-kit.json`으로 복사해 부모 경로를 지정합니다. 예를 들어 `docs_root: "planning"`은 `<project>/planning/docs/`에 문서를 저장한다는 뜻입니다. 상대 경로는 항상 `--project-root` 기준이며 절대 경로도 지원합니다.

실제 PRD와 brief를 작성한 뒤 checkout에서도 실행할 수 있습니다.

```bash
python3 design.py --project-root /absolute/company-project doctor
python3 design.py --project-root /absolute/company-project init --run first-study --source docs/prd.md --brief docs/design-harness/first-study/brief.md
python3 design.py --project-root /absolute/company-project status --run first-study
```

`init`은 빈 초안입니다. manifest·시안·관찰 근거를 작성한 뒤 `refresh`, `prepare --stage comparison`, `serve`로 이어갑니다. [명령](skills/design-harness/references/commands.md), [입력·도구](skills/design-harness/references/environment.md), [실행 계약](skills/design-harness/references/contract.md)을 참고하세요.

수치 통과가 미적 완성도나 사용자 만족을 뜻하지 않습니다. 실제 방향 선택 전에는 나머지 화면으로 확장하지 않습니다. 최종 인계에는 실제 독립 검토와 같은 버전의 사용자 결정이 필요합니다. 이 실행기는 시각 비평의 의미나 결정 출처의 진위를 인증하지 않습니다.

## 업데이트와 제거

검증한 Git 태그/커밋 또는 릴리스 압축 파일을 고정해 사용하세요. 자동 업데이트나 원격 업로드는 없습니다.

```bash
python3 install.py --target codex --project /absolute/company-project --upgrade
python3 install.py --target codex --project /absolute/company-project --remove
```

설치 영수증의 해시와 일치하는 두 스킬만 변경합니다. 같은 이름의 기존 스킬, 심볼릭 링크, 설치 후 사용자가 수정한 파일은 덮어쓰거나 삭제하지 않습니다. 충돌하면 해당 파일을 직접 보존·정리한 뒤 다시 실행합니다. 다른 스킬과 프로젝트의 PRD·디자인·결정 기록은 유지합니다. 두 에이전트의 스킬 디렉토리에 모두 설치했다면 각각 업데이트합니다.

## 검증과 배포 준비

런타임은 표준 라이브러리만 사용하며 개발 테스트에만 pytest가 필요합니다.

```bash
python3 -m pytest -q
python3 build_release.py --output /absolute/output-directory
```

고정 합성 회귀와 독립 임시 프로젝트에서 설치→원본 checkout 제거→비교 준비→선택 기록→새 프로세스 재개→입력 변경 감지를 검사합니다. 합성 이벤트는 실제 사용자 선택이 아닙니다. 회사 실자료·계정·기존 프로젝트 결과물은 배포물에 포함하지 않습니다.

`python3 examples/synthetic_board.py`는 새 임시 폴더에 정답을 아는 기계 검증용 보드를 만들고 실행 명령을 출력합니다. 제품 시안 예제가 아닙니다. Playwright MCP가 있으면 출력된 서버 URL을 연 뒤 `tests/browser_smoke.js`로 390/1200px의 이미지 로드·가로 넘침·선택 저장을 측정할 수 있습니다. 이 검사는 합성 선택을 제출하므로 실제 디자인 실행에 사용하지 않습니다.

`build_release.py`는 명시된 소스 목록만 ZIP으로 묶고 파일별 SHA-256을 기록합니다. 캐시·Git 이력·실행 결과물을 포함하지 않습니다. 패키지 버전은 `skills/design-harness/scripts/design_kit/__init__.py`에서 관리합니다. 원격 Git 저장소 생성·push는 별도 단계입니다.

현재 준비본은 내부 사용을 위한 소스 묶음입니다. 공개 배포 라이선스는 이 준비 단계에서 지정하지 않았습니다.
