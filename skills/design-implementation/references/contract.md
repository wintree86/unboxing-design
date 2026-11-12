# 구현 계약과 검사기 입력

기준은 현재 사용자 요청에서 특정된 화면/버전이다. 하네스 최종 gate가 없더라도 실제 구현 지시를 근거로 범위를 기록할 수 있다. 과거 gate를 소급 통과시키거나 다른 후보를 선택 처리하지 않는다. 승인된 디자인을 검증 편의에 맞춰 고치지 않는다.

## 기록

- 사용자 결정 원문과 메시지/이벤트 위치, 디자인 버전·프레임 ID, 원본 도구 조회와 PNG.
- 현재 단계의 전체 대상 화면·상태 목록. 대표 화면 하나를 먼저 할 때는 이번 범위와 후속 범위를 명시한다.
- 화면별 데이터 fixture, 언어, 글자 배율, 플랫폼, 가용 viewport와 DPR, 상태 및 스크롤 위치. 서로 다른 상태/크기를 비교해 수정하지 않는다.
- 요소별 코드 연결, 화면 좌표의 `box: [x,y,width,height]`, 원문, 역할/행동 ID, 폰트·색·자산/표면 등 관찰한 속성. 승인된 모든 주요 영역을 포함한다. 최소 한 요소만 등록해 전체 화면 완료로 보고하지 않는다.
- 반응형 규칙, 기능 구현 상태, 의도적 차이의 근거. 의도적 변경은 해당 사용자 지시를 붙여 새 계약 버전으로 작성한다. 구현자가 기준 삭제/허용 오차 확대를 통해 차이를 승인할 수 없다.

## 파일 형식

`contract.json`은 다음 구조다. 실제 프로젝트 값으로 채우고 파일 참조는 계약 폴더 기준 상대 경로를 사용한다.

```json
{
  "schema_version": 1,
  "scope": "Representative library, empty state only; other screens pending",
  "decision": {"quote": "Use this design", "source": "actual user message identifier"},
  "design_version": "selected-version",
  "source_roots": ["lib", "assets", "pubspec.yaml", "pubspec.lock"],
  "native_source": {"path": "../../../designs/ui/current.pen", "size": 1, "mtime_ns": 1},
  "cases": [{
    "id": "library-empty-phone",
    "context": {"platform": "ios", "width": 412, "height": 920, "dpr": 1, "text_scale": 1, "locale": "ko", "state": "empty", "fixture_sha256": "64 hex chars", "scroll": [0, 0]},
    "reference_png": {"path": "reference.png", "sha256": "64 hex chars"},
    "reference_measurement": {"path": "reference-nodes.json", "sha256": "64 hex chars"},
    "fixture": {"path": "fixture.json", "sha256": "64 hex chars"},
    "max_box_delta_px": 1,
    "hierarchy": ["header", "empty-content", "actions", "navigation"],
    "actions": ["import", "connect-library"],
    "elements": {
      "empty-title": {"box": [24, 430, 364, 39], "text": "첫 페이지를 열어 볼까요?", "font_size": 25}
    }
  }]
}
```

예제 요소 한 개는 형식을 설명할 뿐 전체 화면 회귀 세트가 아니다. `native_source`는 .pen처럼 일반 읽기가 금지된 원본의 stat만 담는다. Figma 같은 원격 원본은 이 항목을 생략하고 버전/조회 근거를 `reference_measurement`에 보존한다. 원격 최신성은 도구로 다시 조회한다.

`report.json`:

```json
{
  "schema_version": 1,
  "contract_sha256": "current contract file hash",
  "code_snapshot": {"path": "code.json", "sha256": "64 hex chars"},
  "cases": [{
    "id": "library-empty-phone",
    "context": {},
    "actual_png": {"path": "actual.png", "sha256": "64 hex chars"},
    "actual_measurement": {"path": "actual-nodes.json", "sha256": "64 hex chars"},
    "measured_by": "flutter-render-tree",
    "hierarchy": [], "actions": [], "elements": {}
  }],
  "visual_review": {
    "kind": "self",
    "status": "pass",
    "evidence_sha256": "hash of cases array in canonical JSON",
    "notes": "Observed reference and app: hierarchy, density, typography, imagery/surfaces and control details",
    "unresolved": []
  }
}
```

`reference_measurement`와 `actual_measurement` JSON은 각각 `context`, `hierarchy`, `actions`, `elements`를 포함해야 하며 계약/보고서의 값과 같아야 한다. 디자인 도구의 원시 조회와 앱 원시 측정은 별도로 보존하고 정규화 파일에 출처를 연결한다.

`context`, `hierarchy`, `actions`, `elements`는 실제 측정값이다. 시안 값을 복사하지 않는다. `measured_by`는 `flutter-render-tree`, `browser-dom` 또는 `native-accessibility` 중 실제 경로다. 스타일 속성은 측정 가능한 값을 그대로 사용하며 표기 정규화 근거를 남긴다. 파일 경로는 보고서가 계약과 다른 폴더에 있을 때도 계약 폴더 기준이다.

## 명령

`SKILL_DIR`은 현재 읽은 스킬의 실제 디렉터리다.

```sh
python3 "$SKILL_DIR/scripts/verify.py" snapshot --code-root /absolute/app --contract /absolute/contract.json --output /absolute/code.json
python3 "$SKILL_DIR/scripts/verify.py" verify --code-root /absolute/app --contract /absolute/contract.json --report /absolute/report.json
```

`snapshot`은 계약의 source_roots 전체 파일 집합을 기록한다. 모든 렌더 입력(소스·자산·폰트·의존 lock·플랫폼 설정)을 source_roots에 포함한다. 소스 수정 뒤에는 앱을 다시 실행/캡처하고 새 snapshot을 만든다. 검사기는 나열되지 않은 입력의 존재나 캡처 시각의 진위를 판정하지 못한다.

JSON 지문은 파일 바이트의 SHA-256, 시각 리뷰의 cases 지문은 `json.dumps(cases, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()`의 SHA-256이다. 검증은 읽기 전용이며 통과 여부를 입력 파일에 덮어쓰지 않는다. 결과는 `MATCHED` 또는 `MISMATCH`, 실패 시 종료코드 1이다. 스키마 오류·누락·지문 변경도 실패다. 단일 전체 이미지 유사도 점수로 작은 중요 조작의 누락을 통과시키지 않는다.

허용 오차는 기준을 기록할 때 실제 렌더러 차이를 설명할 수 있는 값으로 정한다. 숫자를 변경할 때는 기존 실샘플과 알려진 합성 케이스를 모두 재실행한다. 플랫폼 글리프/안티앨리어싱 차이는 별도 영역으로 관찰하고 기능·레이아웃 변경까지 허용하는 근거로 확대하지 않는다.
