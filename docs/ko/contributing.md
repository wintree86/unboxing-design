# 기여 안내

[처음으로](../../README.ko.md) · [English](../en/contributing.md) · [설치 안내](installation.md)

## 개발 환경

설치된 복사본이 아닌 이 원본 저장소에서 수정합니다. macOS/Linux와 Python 3.11 이상이 필요합니다. pytest는 개발 테스트용이며 설치된 실행기는 외부 Python 패키지를 사용하지 않습니다.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install pytest
.venv/bin/python -m pytest -q
```

실행 명령·결과·미확인 범위를 함께 기록합니다. 기능 테스트·근거 일관성·시각 판단·독립 검토·사용자 수용은 서로 다른 주장입니다.

## 원본 구조

| 경로 | 역할 |
|---|---|
| `skills/design-bot/` | 시각 탐색·디자인 지침 |
| `skills/design-harness/` | 비교·결정 지침과 scripts/design_kit/ 공통 Python 실행기 |
| `skills/design-implementation/` | 승인 시안 구현 지침·검사기 |
| `install.py` | 영수증 기반 설치·업데이트·제거 |
| `build_release.py` | 재현 가능한 ZIP과 파일별 manifest |
| `tests/`, `examples/` | 합성 fixture·독립 설치 테스트·예제 |
| `docs/en/`, `docs/ko/` | 언어별 사용자 문서 |

실행기에 개발자 절대 경로·회사 등록부·모델 SDK·자격 증명·비공개 프로젝트 자료를 추가하지 않습니다. 공통 로직을 소비 저장소에 복제하지 않습니다. [AGENTS.md](../../AGENTS.md)의 유지보수 규칙을 따릅니다.

## 변경과 검증

설치 변경은 충돌·로컬 수정 보존·롤백·두 호스트 폴더·원본 checkout 제거 후 실행을 검증합니다. 근거 검사 변경은 정답을 아는 합성 자료와 사용 허가된 실샘플로 확인하며 실패한 디자인을 통과시키기 위해 허용 오차를 늘리지 않습니다. 합성 결정을 실제 승인 이력으로 사용하지 않습니다.

영어·한국어 README와 관련 안내를 함께 갱신합니다. GitHub와 릴리스 ZIP 모두에서 작동하도록 상대 링크를 유지합니다. 고급 스킬 참조 문서는 현재 한국어이며 번역 범위를 과장하지 않습니다.

재현 가능한 버그는 [GitHub 이슈](https://github.com/wintree86/unboxing-design/issues), 변경은 [Pull Request](https://github.com/wintree86/unboxing-design/pulls)로 제안할 수 있습니다. 버전·Python/OS·실행 명령·예상/실제 결과·민감 정보를 제거한 최소 fixture를 포함합니다. 비공개 디자인·토큰·브라우저 프로필·재배포 권한 없는 레퍼런스는 제외합니다.

## 배포물 만들기

```bash
python3 build_release.py --output /absolute/path/to/release-output
```

`design-kit-VERSION.zip`과 `.zip.sha256` 체크섬이 만들어집니다. ZIP에는 두 README·언어별 가이드·LICENSE·스킬·실행기·테스트·예제·파일별 SHA-256 manifest가 포함됩니다. Git 이력·캐시·로컬 실행 결과·회사 프로젝트 자료는 제외합니다. 버전은 `skills/design-harness/scripts/design_kit/__init__.py`에서 관리합니다.

배포 전 테스트를 실행하고 빈 디렉터리에 ZIP을 풀어 임시 Codex·Claude Code 프로젝트에 설치합니다. 설치된 doctor와 구현 검사기 진입점, 무관한 파일 보존, 패키지 문서 링크를 확인합니다. 로컬 패키징은 공개 전송을 하지 않으며 버전 태그 push와 릴리스 업로드는 유지보수자가 별도로 수행합니다.

릴리스 시 실행기 버전·빠른 시작 태그·압축 파일명·릴리스 노트를 일치시킵니다. 공개한 버전 태그는 변경하지 않습니다.

## 라이선스

[MIT 라이선스](../../LICENSE)로 배포합니다. 재배포 시 라이선스와 저작권 고지를 유지합니다. 기여물은 해당 라이선스와 호환되어야 하며 기여할 권한이 있는 자료만 포함합니다.
