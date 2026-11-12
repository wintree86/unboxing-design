# 명령과 재개

이 스킬 폴더의 `scripts/design.py`가 실행기다. 설치 위치를 실제로 찾고 절대 경로를 사용한다. 저장소 checkout에서는 루트의 `design.py`도 같은 실행기를 호출한다. Python 3.11+와 macOS/Linux가 필요하며 pip 설치·모델 SDK·네트워크 다운로드는 없다.

아래의 `/absolute/...`는 실제 경로로 바꾼다. `--project-root`와 `--config`는 하위 명령 앞에 둔다. 상대 아티팩트 경로는 실행기 위치가 아니라 선택한 프로젝트 설정을 따른다.

```bash
python3 /absolute/skill/design-harness/scripts/design.py --project-root /absolute/project doctor
python3 /absolute/skill/design-harness/scripts/design.py --project-root /absolute/project discovery-check
python3 /absolute/skill/design-harness/scripts/design.py --project-root /absolute/project init --run RUN --source docs/prd.md --brief docs/design-harness/RUN/brief.md --theme '고요한 몽환'
python3 /absolute/skill/design-harness/scripts/design.py --project-root /absolute/project status --run RUN
python3 /absolute/skill/design-harness/scripts/design.py --project-root /absolute/project refresh --run RUN --reason '레퍼런스와 대표 후보 작성'
python3 /absolute/skill/design-harness/scripts/design.py --project-root /absolute/project prepare --run RUN --stage comparison
python3 /absolute/skill/design-harness/scripts/design.py --project-root /absolute/project board --run RUN --output designs/exports/design-harness/RUN/board
python3 /absolute/skill/design-harness/scripts/design.py --project-root /absolute/project serve --run RUN
python3 /absolute/skill/design-harness/scripts/design.py --project-root /absolute/project event --run RUN --file /absolute/actual-user-event.json
python3 /absolute/skill/design-harness/scripts/design.py --project-root /absolute/project gate --run RUN
```

`doctor`는 로컬 파일·설정만 검사한다. 도구 연결과 디자인 품질 검사가 아니다. `init` 전에 실제 PRD와 brief 파일을 만든다. 빈 manifest는 초안이며 `check/prepare`가 필요한 자료를 보고한다. manifest 형식은 [계약](contract.md), 제작 근거는 [시각 검토](visual-review.md)를 따른다.

`serve`는 127.0.0.1의 임의 포트를 출력하며 실제 폼 제출을 저장한다. `board`는 오프라인 파일로 선택 기록을 다운로드하며 `event`로 가져와야 저장된다. 에이전트가 실제 사용자를 대신해 선택 폼을 제출하지 않는다. 자동화 UI 테스트는 별도 합성 실행에서만 한다.

`pin docs/...`로 파일 참조를 얻는다. `observe --raw actual-nodes.json --mapping frames.json --output docs/.../readback.json --saved-reopened`는 실제 관찰을 포장한다. mapping은 root ID → `{source:'designs/..pen',preview:'designs/..png'}`이다. saved-reopened 플래그는 실제 저장·닫기·재열기 뒤에만 사용한다. 도구마다 다른 좌표 체계는 실제 출력과 대조하며 임의 보정해 통과시키지 않는다.

초기화 직후 draft, manifest 작성 뒤 refresh하면 exploring이다. 입력 변경 뒤 옛 측정이나 결정을 재사용하지 않는다. status가 stale이면 원인을 확인하고 refresh한다. 피드백 원문/화면/버전과 전후 이미지/미반영 이유를 남긴다. 설치 업데이트는 스킬 코드만 바꾸며 프로젝트의 실행 기록은 그대로 둔다. 변경된 실행기로 재개할 때 status와 같은 근거의 측정을 다시 확인한다.


v1 기록은 먼저 `status`로 읽고, 실제 이행 작업에서만 `upgrade --run RUN --reason '기존 원문 보존 후 v2 근거 연결'`을 실행한다. `refresh` 뒤 현재 snapshot에 대한 `comparison-review.json`과 `presentation`을 작성해야 새 선택이 가능하다. `event --file`은 실제 사용자 feedback/work_mode와 제작자 triage/application을 같은 원장에 기록한다. 상세 필드·권한·범위는 [v2 계약](contract.md)을 따른다. 검토자가 읽지 않은 과거 피드백을 검토 완료로 채우지 않는다.
