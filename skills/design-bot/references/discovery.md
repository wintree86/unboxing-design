# 와이어프레임 전 레퍼런스 탐색 계약

`Reference Discovery Before Wireframes` 또는 기획에서 새 화면 구성을 시작할 때 사용한다. 순서는 **기획 해석 → 실제 앱/Pinterest 관찰 → 구성 원리 해석 → 우리 콘텐츠의 구조 가설 → 와이어프레임**이다. 기존 시안은 비교 자료이며 그 좌표·위계를 기본 정답으로 두지 않는다.

## 조사와 인계

1. PRD·사용자 결정에서 필수 과업·정보·결과·정책을 ID/원문 위치/수용 기준과 함께 `required`로 추출한다. PRD가 제안한 화면 배치도 명시적 제약인지 검토한다. ‘오른쪽 하단 버튼’, ‘3열 카드’처럼 에이전트가 택한 배치는 `provisional`로 둔다. 사용자 결정은 그 표현이 고정한 범위만 유지한다. ‘시간순 타임라인’은 사진 크기와 제목 위치의 확정이 아니다.
2. 실제 앱에서는 과업·흐름을, Pinterest·Dribbble의 실제 검색·핀/작품 상세와 연결된 원작자 작품에서는 구성·표현의 가능성을 관찰한다. 구조 탐색 뒤의 시각 시안은 [완성 목업 기준](finished-mockup.md)에 따라 이미지·표면·디테일까지 이어가며 이 단계의 구조 가설을 완성 목업으로 취급하지 않는다. 같은 화면 유형·과업과 다른 구성을 함께 탐색한다. 검색 요약·접근 실패는 관찰 근거로 세지 않는다. 관찰 이미지/캡처는 `designs/references/discovery/`, 원문·검색어·탈락 이유·제약은 `docs/design-discovery/brief.md`에 남긴다. 특정 출처 요청을 충족하지 못했다면 명시하고, 필수 관찰을 못 했다면 `blocked`로 남긴다.
3. **시선의 시작 → 정보 묶음 → 읽기/이동 순서 → 사진과 텍스트의 역할**을 설명하고, 이를 우리 콘텐츠에 적용한 구조 가설 2~3개를 만든다. 각각 유지할 필수 조건, 재배치할 요소, 접근 경로, 장단점을 적는다. 색/서체 목록만으로 가설을 대체하지 않는다. 예: ‘최신 제보 사진으로 진입 → 핵심 설명 → 이전 기록 압축’과 ‘날짜별 기록 묶음 → 선택한 기록에서 사진 확대’를 비교한다.
4. `manifest.json`과 brief를 화면 구조 담당에게 넘긴다. 별도 담당이 없으면 현재 에이전트가 [구조 요약](../../design-harness/references/environment.md)을 작성한다. 다음 단계는 가설별 핵심 구조안을 만들고 요구사항 보존/정보 접근을 검토한다. 추천안으로 진행할 수 있지만 추천을 사용자 확정으로 적지 않는다. 추가 승인 단계는 만들지 않는다. 작은 수정은 기존 관찰·확정 근거가 유효할 때 `mode: reuse`와 변경 범위·재사용 사유를 기록한다.

## manifest.json

```json
{
  "schema_version": 1,
  "status": "ready_for_wireframe",
  "request_id": "워크플로우가 전달한 Discovery request_id",
  "scope": "ui",
  "mode": "explore",
  "sources": [{"path": "docs/prd.md", "sha256": "실제 파일 SHA-256"}],
  "required": [{"id": "FR-1", "source": "docs/prd.md#기록", "statement": "최근 기록부터 읽는다", "acceptance": "전체 기록에 접근하며 최근순이 유지된다"}],
  "provisional": [{"id": "L-1", "current": "동일 크기 카드", "reason": "초기 설명용 배치", "alternatives": "최신 기록 강조 또는 날짜 그룹"}],
  "references": [{"id": "R-1", "url": "실제 작품 URL", "observed_at": "실제 열람 시각", "evidence": "designs/references/discovery/observed.png", "observation": "큰 사진 뒤에 작은 기록이 이어진다", "adopt": "신규 정보와 과거 정보의 비중 차이", "avoid": "우리 콘텐츠에는 없는 구매 흐름"}],
  "hypotheses": [
    {"id": "H-1", "reference_ids": ["R-1"], "first_focus": "최신 사진", "grouping": "최신과 과거", "reading_flow": "사진→설명→이전 기록", "image_role": "첫 기록의 중심", "translation": "우리 제보 사진과 본문을 하나의 큰 단위로 묶는다", "tradeoff": "첫 화면 노출 기록 수 감소"},
    {"id": "H-2", "reference_ids": ["R-1"], "first_focus": "날짜와 짧은 본문", "grouping": "날짜별 기록", "reading_flow": "날짜→요약→선택 기록", "image_role": "기록별 썸네일", "translation": "강조 원리를 날짜 제목에 적용하고 사진은 선택 후 확대한다", "tradeoff": "사진 전체를 보려면 한 단계 이동"}
  ]
}
```

예시는 형식 설명이며 실제 조사 근거가 아니다. `provisional`은 빈 배열을 허용한다. 모든 항목에는 고유 ID가 필요하다. `mode: reuse`는 `reuse_reason`과 `sources`에 포함한 `decision_source`가 필요하며 기존 관찰과 가설을 남긴다. 비 UI는 `scope: non_ui`, 원문에 근거한 `reason`, sources와 brief로 통과하고 시각 조사를 강제하지 않는다.

검증기는 이번 실행 ID, 입력 지문, 필수/임시 분리, 관찰 근거 파일, 가설 연결, 구성 필드의 동일 여부를 검사한다. 다른 문구로 쓴 같은 배치를 자동 판별하거나 실제 이미지 열람·미적 품질을 증명하지는 않는다. 의미와 원본 관찰은 제작자가 실제 도구로 확인하고 근거를 남겨야 한다.

## 후속 재설계

와이어프레임은 필수 조건을 `requirements`로 보존하고 모든 화면의 `layout_choices`를 `provisional` 또는 근거가 있는 `user_confirmed`로 분류한다. 시각 디자인은 임시 배치의 사진 비중·텍스트 위계·그룹·밀도·컴포넌트·순서를 함께 바꿀 수 있다. 변경 전후의 필수 조건 매핑과 정보 접근 경로를 기록하고 와이어프레임 계약을 갱신한다. 필수 조건/사용자 확정을 바꿔야 할 때만 해당 결정을 다시 다룬다. 구조 선택 후의 두 번째 레퍼런스 검토는 색·서체·이미지·여백을 함께 구체화하는 단계다.
