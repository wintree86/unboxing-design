# Design Kit

레퍼런스 분석과 편집 가능한 구성 연구를 바탕으로 새 방향은 대표 두 안, 기존 방향 수정은 전후 비교로 만들고, 시각 검토와 실제 사용자 선택 후 확장하는 독립 스킬 패키지입니다.

- `design-bot`: 레퍼런스 탐색·구성 연구·대표 시안 제작.
- `design-harness`: 시각 검토·비교·사용자 결정·재개·최종 인계.
- `design-implementation`: 승인 시안의 코드 구현·동일 조건 실제 화면 비교·변경/누락 검사.
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

Codex에는 `.agents/skills/`, Claude Code에는 `.claude/skills/`로 세 스킬과 실행기를 **복사**합니다. 설치된 스킬 폴더 사이 상대 참조를 유지하며 원본 checkout을 이동·삭제해도 실행됩니다. 설치 후 다음 대화에서 스킬을 사용합니다. 기존 스킬 인식이 갱신되지 않으면 새 세션을 시작합니다.

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

디자인 시안·목업은 대표 범위에서 실제 콘텐츠·필요 이미지·표면·조작 디테일이 반영된 모습을 뜻합니다. 구조안과 구분하며 새 시각 방향은 실제 앱과 Pinterest의 핀 상세·연결 작품을 함께 관찰합니다. 자세한 기준은 [완성 목업](skills/design-bot/references/finished-mockup.md)에 있습니다.

자료 탐색을 시작할 때 Pinterest·Dribbble의 기존 로그인 세션을 확인합니다. 로그인되어 있지 않으면 공개 페이지가 열리더라도 사용자에게 로그인을 요청하고, 같은 브라우저의 공식 화면으로 연결한 뒤 완료 응답을 받아 검색/작품 상세를 재검증합니다. 사용자가 명시적으로 비로그인 진행을 선택하면 공개 경로를 사용합니다. “계정 연결을 확인해줘”라는 요청도 같은 절차로 처리합니다. 공개 탐색 가능 여부와 인증 완료는 구분하며, 로그인 유지 자체는 브라우저가 관리합니다. 스킬 파일에 자격 증명을 저장하거나 CLI에서 자동 로그인하는 기능은 아닙니다. [인증 준비 절차](skills/design-bot/references/reference-session.md).

수치 통과가 미적 완성도나 사용자 만족을 뜻하지 않습니다. 실제 방향 선택 전에는 나머지 화면으로 확장하지 않습니다. 최종 인계에는 실제 독립 검토와 같은 버전의 사용자 결정이 필요합니다. 이 실행기는 시각 비평의 의미나 결정 출처의 진위를 인증하지 않습니다.

## 업데이트와 제거

검증한 Git 태그/커밋 또는 릴리스 압축 파일을 고정해 사용하세요. 자동 업데이트나 원격 업로드는 없습니다.

```bash
python3 install.py --target codex --project /absolute/company-project --upgrade
python3 install.py --target codex --project /absolute/company-project --remove
```

설치 영수증의 해시와 일치하는 소유 스킬만 변경합니다. 같은 이름의 기존 스킬, 심볼릭 링크, 설치 후 사용자가 수정한 파일은 덮어쓰거나 삭제하지 않습니다. 충돌하면 해당 파일을 직접 보존·정리한 뒤 다시 실행합니다. 다른 스킬과 프로젝트의 PRD·디자인·결정 기록은 유지합니다. 두 에이전트의 스킬 디렉토리에 모두 설치했다면 각각 업데이트합니다.

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


- v2 피드백 원장과 작업 모드를 따른다. 새 방향 탐색은 대표 두 안, 기존 선택 방향 수정은 한 안의 전후, 원인 조사 전용은 분석·문서로 분기한다. 미분류/거절/변경 요청은 해당 범위의 새 선택·확장·인계를 제한하며 원인 조사 중지는 실제 사용자 재개 지시로만 해제한다. 기존 결정은 역사로 보존한다.
- 비교 검토는 실제 산출물과 피드백 원문/분류/적용 이벤트에 묶고 자기 검토/독립 검토를 구분한다. 제시본 역할·버전·원본·PNG를 등록한다. 자동 검사는 근거 연결을 검사하며 미관·피드백 의미를 판정하지 않는다. v1은 비파괴 조회하고 명시적 upgrade로 전환한다.

## 승인 시안 구현

`$design-implementation`으로 특정 버전의 화면을 구현하거나 현재 앱과의 불일치를 조사합니다. [스킬](skills/design-implementation/SKILL.md), [입력 계약](skills/design-implementation/references/contract.md), [실제 캡처](skills/design-implementation/references/capture.md)를 따릅니다. 기존 사용자 구현 지시를 재사용하며 새 승인을 일괄 요구하지 않습니다.

대표 화면에서 구성·문구·주요 행동·스타일·자산·좌표를 실제 앱과 비교하고 범위를 확장합니다. 기능 테스트 성공으로 시각 비교를 대신하지 않습니다. `verify.py`는 누락, 조건 불일치, 코드/캡처 변경, 제출 측정의 차이, 미해결 시각 검토를 실패로 반환합니다. 실제 렌더링·미적 판단·독립 리뷰·사용자 승인 인증은 수행하지 않습니다. 에이전트가 검사를 호출하지 않는 모든 환경을 자동으로 차단하는 전역 훅은 아닙니다.

0.2.x의 기존 두 스킬 설치는 로컬 수정이 없으면 0.3.x의 세 스킬로 업그레이드됩니다. 기존 실행 문서/선택을 변경하지 않으며 `design-implementation`이라는 다른 스킬이 있으면 충돌로 보존합니다.
