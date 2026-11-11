# 디자인 실행 계약 v1

`docs/design-harness/{run-id}/manifest.json`과 같은 폴더의 `state.json`이 실행 단위다. 기본 경로는 프로젝트의 `docs/`와 `designs/`다. design-kit.json의 docs_root/code_root는 각각 이 폴더를 포함하는 부모 경로다. 각 아티팩트 루트 밖으로 벗어나는 경로·심볼릭 링크는 거부한다.

## 원본과 근거

일반 파일 참조는 `{path, sha256}`다. `.pen`은 내용 파싱 없이 `{path, opaque:true, size, mtime_ns}`와 전용 MCP에서 얻은 별도 readback JSON을 함께 쓴다. 원본을 Save하고 닫았다 다시 열어 readback을 받는다. 메타데이터만으로 내용 동일성을 증명하지 않으며 최종 인계 시 전용 MCP 재조회가 필요하다.

manifest는 `schema_version:1`, `run_id`, `scope:ui|non_ui`, `sources`, `brief`를 가진다. UI에는 아래 필드가 필요하다. `init` 명령이 초안을 생성하며 빈 초안은 비교 검사를 통과하지 못한다.

- `theme`: 사용자 원문 `requested`, 이번 제품에 대한 `interpretation`, `avoid` 배열.
- `content`: 콘텐츠 ID → 실제 문자열인 JSON 파일 참조.
- `requirements`: `{id, screen_ids}` 또는 `{id, exclusion_reason}` 배열.
- `screens`: `{id, states, viewports, actions, content}` 배열. action은 `{id, target}`이며 target은 실제 화면 또는 `@back`, `@complete`, `@external`이다. content는 모든 후보가 동일하게 보여줄 콘텐츠 ID 목록이다.
- `viewports`: `{id, width, height}` 배열.
- `comparison`: `{screen,state,viewport}` 배열. 전체 coverage와 별도로 고정한 대표 비교 범위다.
- `references`: `{id,url,observed_at,observation,analysis,adopt,avoid}` 배열. observation은 실제 이미지 열람 증거/시각 관찰 기록의 파일 참조이고 `analysis`에는 composition, typography, color_light, texture, product_translation을 적는다. 검색 결과 설명만 읽었으면 추가하지 않는다. 원작자 미상은 기록하며 관찰 사실을 만들지 않는다.
- `candidates`: `{id,version,title,concept,direction,reference_ids,assets,signature_features,frames}` 배열. version은 양의 정수, direction은 아트디렉션 문서 참조, signature_features는 `{id,description}` 배열이다.

frame은 `{id,screen,state,viewport,source,node_id,preview,readback,content_nodes,action_nodes,signature_nodes,allowed_overlaps}`다. 세 nodes 필드는 각각 콘텐츠/행동/중심표현 ID → 실제 노드 ID 매핑이다. allowed_overlaps는 `{nodes:[id,id],reason}` 배열이며 실제 형제 겹침만 허용한다. 모든 중심 표현이 모든 상태에 장식으로 들어갈 필요는 없지만 후보 전체에는 관찰 가능한 적용 노드가 있어야 한다.

readback JSON은 `{renderer, captured_at, saved_reopened, nodes:[...], artifacts:{rootID:{source,preview}}}`다. 각 노드는 실제 도구로 읽은 `{id,parent,type,name,bounds:{x,y,width,height},content,fill,problems}`를 포함한다. bounds는 선언값이 아닌 렌더된 값이다. 프레임 node_id를 시작점으로 해당 하위 트리를 대조한다. 폰트·접근성·실제 클릭 검증은 이 형식만으로 증명되지 않는다.

## 측정과 판정

[시각 검토 절차](visual-review.md)는 별도의 에이전트 작업이다. 새 실행의 첫 comparison은 대표 화면 하나의 후보를 대상으로 고정하고 최종 전체 coverage와 구분한다. `prepare` 통과는 구성 원리의 이해·시각 완성도·사용자 만족을 판정하지 않는다. 분석·구성 연구·이전/새 화면 비평과 기존 방향 선택을 거친 뒤 확장한다. 현재 CLI가 이 의미 검토를 강제한다고 주장하지 않는다.

콘텐츠 ID/행동 결과의 동일성은 같은 배치의 요구가 아니다. 구조 탐색에서는 후보별 정보 순서·묶음·탐색·입력 순서를 바꿀 수 있다. 원래 요구·명시적 사용자 결정과의 차이, 숨겨진 콘텐츠의 접근 경로를 기록한다. 이러한 탐색은 `exploring`에 보존하며 전체 콘텐츠 매핑이 없는 구조 스케치를 comparison gate 통과 UI로 취급하지 않는다. 기존 거절 원본·측정은 보존한다.

`prepare`는 원본/프리뷰/관찰 근거의 지문과 구조·렌더 관찰 결과를 묶어 `measurements.json`을 만든다. 기하와 실제 텍스트/행동 노드, PNG 크기를 검사한다. 단색 텍스트·배경의 선언 색이 실제 PNG의 해당 텍스트 영역에 불투명 픽셀로 모두 존재하는지 확인한 뒤 대비를 계산한다. 픽셀 좌표와 색·최솟값을 기록하며 사진 위 대비나 실제 폰트 로딩 검증으로 확대하지 않는다. 지원하지 않는 대상은 미측정으로 남긴다.

프로젝트 정적 디자인 프로필은 모든 검사 대상 텍스트 4.5:1, 매핑된 주 행동 44×44 design px다. 큰 글자 예외는 사용하지 않는다. 기준 출처는 [대비](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html), [확대 목표 크기](https://www.w3.org/WAI/WCAG22/Understanding/target-size-enhanced)이며 WCAG 전체 준수나 실제 기기 터치 측정을 의미하지 않는다. 정책/경계 회귀는 배포 저장소의 `tests/fixtures/design_harness/policy.json`과 `cases.json`에 고정한다.

## 결정과 재개

`state.json`의 이벤트 목록이 원장이다. feedback.jsonl/decisions.jsonl/selection.json은 원장으로부터 생성하는 읽기용 사본이다. 잠금+원자적 저장으로 상태와 이벤트를 함께 기록한다. 같은 ID/내용의 이벤트는 멱등이며 같은 ID/다른 내용은 거부한다.

상태: draft → exploring → awaiting_direction → refining → awaiting_final → ready_for_build. 입력/원본이 변경되면 status가 stale을 반환한다. `refresh`는 변경 이유를 기록하고 측정·최종 결정을 무효화한다. 입력 및 선택된 아트디렉션이 같으면 방향 선택을 보존해 refining으로 돌아가며, 다르면 exploring으로 돌아가 새 선택을 받는다. 자동 수정 상한에 이르면 blocked로 보존한다.

사용자 선택 이벤트에는 `id`, `kind:direction|final`, `candidate_id`, `snapshot`, `actor:user|delegated`, `authority`(실제 사용자 메시지 출처 또는 로컬 비교 보드의 명시적 제출), `reason`이 필요하다. delegated는 별도 `{path,sha256}` 위임 기록과 `allowed_decisions`에 이번 kind가 있어야 한다. 구조 검사는 사용자 발언의 진위를 인증하지 않으므로 에이전트가 출처를 만들어 넣어서는 안 된다. 무응답은 결정이 아니다.

final 준비에는 현재 snapshot과 후보를 대조한 `review.json`이 필요하다. `{snapshot,candidate_id,reviewer_id,producer_id,independent:true,verdict:pass,evidence,unresolved:[]}`이며 동일 생성자/평가자는 독립 리뷰로 인정하지 않는다. evidence는 실제 검토 기록 참조다. 최종 사용자 결정까지 동일 버전으로 연결돼야 구현자가 소비할 수 있다.

non_ui는 출처와 reason을 검증한 후 UI 후보와 선호 결정을 생략한다. UI의 빈 화면을 non_ui로 표시해 우회하지 않는다.

## 최종 폰트·이미지 근거

후보 assets 배열은 실제 이미지 파일 참조다(이미지가 없으면 빈 배열). 관찰된 이미지 fill의 상대 경로는 이 목록에 있어야 하며, 이미지 파일만 바꿔도 stale이 된다. 비교 단계의 실제 폰트/글리프는 미확인으로 표시할 수 있지만 최종 단계에서는 각 frame.font_observation 참조가 필수다.

font_observation JSON은 renderer, captured_at, source, preview, runs를 가진다. source/preview는 동일 렌더의 파일 참조다. runs는 모든 텍스트 노드에 대해 node, actual_font, glyph_count, missing_glyphs=0, method(renderer-glyph-run 또는 chromium-platform-fonts)를 기록한다. 선언된 fontFamily만 기록해서는 안 된다. synthetic-ground-truth는 합성 렌더 fixture에만 허용한다. 도구가 실제 폰트 관찰을 지원하지 않으면 최종 단계가 미완료인 것이 맞다. 이 검사기는 근거의 생성자를 인증하지 않으므로 실제 도구 조회를 대신 작성하지 않는다.

[brief 템플릿](templates/brief.md)과 [수정 기록 템플릿](templates/revision.md)을 사용한다.

## 선행 탐색과 구조 인계

새 실행의 inputs에는 `docs/design-discovery/manifest.json`과 실제 구조 산출물을 파일 참조로 연결한다. 기존 `docs/wireframes/manifest.json`이 있으면 사용하고, 없으면 [환경 지침](environment.md)에 따라 `docs/design-discovery/structure.md`를 작성해 연결한다. 필수 요구사항과 layout_choices의 provisional/user_confirmed를 분리해 소비한다. 임시 배치 재설계는 허용하되 조건·정보 접근·상태 매핑과 전후 이유를 동기화한다. 조건이나 원문 결정이 바뀌면 입력 지문 변경으로 관련 비교·결정·확정을 다시 검토한다. 기존 실행의 과거 입력을 소급 생성해 이전 관찰로 기록하지 않는다. 선행 탐색은 `ready_for_wireframe`, 와이어프레임은 `ready_for_design`, 최종 구현 인계는 `ready_for_build`로 서로 다른 상태다.
