# 디자인 실행 계약 v2

`docs/design-harness/{run-id}/manifest.json`과 같은 폴더의 `state.json`이 실행 단위다. 기본 경로는 프로젝트의 `docs/`와 `designs/`다. design-kit.json의 docs_root/code_root는 각각 이 폴더를 포함하는 부모 경로다. 각 아티팩트 루트 밖으로 벗어나는 경로·심볼릭 링크는 거부한다.

## 원본과 근거

일반 파일 참조는 `{path, sha256}`다. `.pen`은 내용 파싱 없이 `{path, opaque:true, size, mtime_ns}`와 전용 MCP에서 얻은 별도 readback JSON을 함께 쓴다. 원본을 Save하고 닫았다 다시 열어 readback을 받는다. 메타데이터만으로 내용 동일성을 증명하지 않으며 최종 인계 시 전용 MCP 재조회가 필요하다.

새 manifest는 `schema_version:2`, `run_id`, `scope:ui|non_ui`, `sources`, `brief`를 가진다. UI에는 아래 필드가 필요하다. `init` 명령이 초안을 생성하며 빈 초안은 비교 검사를 통과하지 못한다.

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

[시각 검토 절차](visual-review.md)는 별도의 에이전트 작업이다. 새 실행의 첫 comparison은 대표 화면 하나의 후보를 대상으로 고정하고 최종 전체 coverage와 구분한다. `prepare` 통과는 구성 원리의 이해·시각 완성도·사용자 만족을 판정하지 않는다. 분석·구성 연구·이전/새 화면 비평과 기존 방향 선택을 거친 뒤 확장한다. 실행기는 검토의 현재성·연결·미해결 여부를 검사하며 의미 판단의 정확성은 보장하지 않는다.

콘텐츠 ID/행동 결과의 동일성은 같은 배치의 요구가 아니다. 구조 탐색에서는 후보별 정보 순서·묶음·탐색·입력 순서를 바꿀 수 있다. 원래 요구·명시적 사용자 결정과의 차이, 숨겨진 콘텐츠의 접근 경로를 기록한다. 이러한 탐색은 `exploring`에 보존하며 전체 콘텐츠 매핑이 없는 구조 스케치를 comparison gate 통과 UI로 취급하지 않는다. 기존 거절 원본·측정은 보존한다.

`prepare`는 원본/프리뷰/관찰 근거의 지문과 구조·렌더 관찰 결과를 묶어 `measurements.json`을 만든다. 기하와 실제 텍스트/행동 노드, PNG 크기를 검사한다. 단색 텍스트·배경의 선언 색이 실제 PNG의 해당 텍스트 영역에 불투명 픽셀로 모두 존재하는지 확인한 뒤 대비를 계산한다. 픽셀 좌표와 색·최솟값을 기록하며 사진 위 대비나 실제 폰트 로딩 검증으로 확대하지 않는다. 지원하지 않는 대상은 미측정으로 남긴다.

프로젝트 정적 디자인 프로필은 모든 검사 대상 텍스트 4.5:1, 매핑된 주 행동 44×44 design px다. 큰 글자 예외는 사용하지 않는다. 기준 출처는 [대비](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html), [확대 목표 크기](https://www.w3.org/WAI/WCAG22/Understanding/target-size-enhanced)이며 WCAG 전체 준수나 실제 기기 터치 측정을 의미하지 않는다. 정책/경계 회귀는 배포 저장소의 `tests/fixtures/design_harness/policy.json`과 `cases.json`에 고정한다.

## 결정과 재개

`state.json`의 이벤트 목록이 원장이다. feedback.jsonl/decisions.jsonl/selection.json은 원장으로부터 생성하는 읽기용 사본이다. 잠금+원자적 저장으로 상태와 이벤트를 함께 기록한다. 같은 ID/내용의 이벤트는 멱등이며 같은 ID/다른 내용은 거부한다.

상태: draft → exploring → awaiting_direction → refining → awaiting_final → ready_for_build. 입력/원본이 변경되면 status가 stale을 반환한다. `refresh`는 변경 이유를 기록하고 현재 측정·인계 허용을 무효화한다. 과거 최종 이벤트와 원문은 삭제하지 않는다. 입력 및 선택된 아트디렉션이 같으면 방향 선택을 보존해 refining으로 돌아가며, 다르면 exploring으로 돌아가 새 선택을 받는다. 자동 수정 상한에 이르면 blocked로 보존한다.

사용자 선택 이벤트에는 `id`, `kind:direction|final`, `candidate_id`, `snapshot`, `actor:user|delegated`, `authority`(실제 사용자 메시지 출처 또는 로컬 비교 보드의 명시적 제출), `reason`이 필요하다. delegated는 별도 `{path,sha256}` 위임 기록과 `allowed_decisions`에 이번 kind가 있어야 한다. 구조 검사는 사용자 발언의 진위를 인증하지 않으므로 에이전트가 출처를 만들어 넣어서는 안 된다. 무응답은 결정이 아니다.

final 준비에는 현재 snapshot과 후보를 대조한 `review.json`이 필요하다. 아래 v2 후보 검토 항목에 snapshot을 붙이고 independent=true로 기록하며 동일 생성자/평가자는 독립 리뷰로 인정하지 않는다. evidence는 실제 검토 기록 참조다. 최종 사용자 결정까지 동일 버전으로 연결돼야 구현자가 소비할 수 있다.

non_ui는 출처와 reason을 검증한 후 UI 후보와 선호 결정을 생략한다. UI의 빈 화면을 non_ui로 표시해 우회하지 않는다.

## 최종 폰트·이미지 근거

후보 assets 배열은 실제 이미지 파일 참조다(이미지가 없으면 빈 배열). 관찰된 이미지 fill의 상대 경로는 이 목록에 있어야 하며, 이미지 파일만 바꿔도 stale이 된다. 비교 단계의 실제 폰트/글리프는 미확인으로 표시할 수 있지만 최종 단계에서는 각 frame.font_observation 참조가 필수다.

font_observation JSON은 renderer, captured_at, source, preview, runs를 가진다. source/preview는 동일 렌더의 파일 참조다. runs는 모든 텍스트 노드에 대해 node, actual_font, glyph_count, missing_glyphs=0, method(renderer-glyph-run 또는 chromium-platform-fonts)를 기록한다. 선언된 fontFamily만 기록해서는 안 된다. synthetic-ground-truth는 합성 렌더 fixture에만 허용한다. 도구가 실제 폰트 관찰을 지원하지 않으면 최종 단계가 미완료인 것이 맞다. 이 검사기는 근거의 생성자를 인증하지 않으므로 실제 도구 조회를 대신 작성하지 않는다.

[brief 템플릿](templates/brief.md)과 [수정 기록 템플릿](templates/revision.md)을 사용한다.

## 선행 탐색과 구조 인계

새 실행의 inputs에는 `docs/design-discovery/manifest.json`과 실제 구조 산출물을 파일 참조로 연결한다. 기존 `docs/wireframes/manifest.json`이 있으면 사용하고, 없으면 [환경 지침](environment.md)에 따라 `docs/design-discovery/structure.md`를 작성해 연결한다. 필수 요구사항과 layout_choices의 provisional/user_confirmed를 분리해 소비한다. 임시 배치 재설계는 허용하되 조건·정보 접근·상태 매핑과 전후 이유를 동기화한다. 조건이나 원문 결정이 바뀌면 입력 지문 변경으로 관련 비교·결정·확정을 다시 검토한다. 기존 실행의 과거 입력을 소급 생성해 이전 관찰로 기록하지 않는다. 선행 탐색은 `ready_for_wireframe`, 와이어프레임은 `ready_for_design`, 최종 구현 인계는 `ready_for_build`로 서로 다른 상태다.


## v2 피드백·검토·제시본

v1은 `status`와 초안 보드로 읽을 수 있지만 새 UI 선택/인계에는 v2 근거가 필요하다. `upgrade --run RUN --reason ...`은 manifest/state 원본 바이트를 `manifest-v1.json`/`state-v1.json`에 보관하고 버전을 전환한다. 선택/피드백 역사와 파일을 보존하며 없는 검토·제시본을 생성하지 않는다. 설치만으로 실행 파일을 이행하지 않는다. 프로젝트 설정 `design-kit.json`은 여전히 schema_version 1이다.

- `references`에 `role:primary_layout|supporting_visual`, `scene`, `task`, `apply_to`, `exclude`를 기록한다. observation 문서와 표시용 `preview`는 별도 파일 참조다. PNG/JPEG/WebP 캡처를 지원하며 Markdown 관찰 기록도 보드에서 연결한다.
- `presentation`은 `{id,role:current|previous|reference|rejected,candidate_id,version,frame_id,node_id,source,preview}` 배열이다. current는 등록 후보의 모든 프레임/버전/원본/PNG와 정확히 일치해야 한다. 원본 위치는 휴대 가능한 source.path이며 도구 URI는 이 프로젝트 루트에서 해결한다. Pen 캔버스의 비교 보드에도 역할과 연결된 실제 프레임을 표시한다. 불일치 초안은 열람할 수 있지만 선택할 수 없다.
- `feedback`은 `id,kind,actor,authority,snapshot,text`를 보존한다. 후보 지정 시 `candidate_id,version`, 필요 시 `screen`, `classification`을 가진다. 후보가 없으면 실행 전체이며, 과거 snapshot/version 피드백은 현재에 자동 전파하지 않는다. 현재 접수된 미처리 피드백은 refresh 뒤에도 남는다.
- 분류는 `untriaged|preference|change_request|rejection|diagnosis_only`다. 제작자 분류는 `triage` 이벤트의 `feedback_id,classification,actor:producer,reviewer_id,rationale`로 기록한다. 비차단 취향·질문은 기존 선택을 유지한다. 거절/변경 요청 뒤 기존 선택은 역사이며 적용·재검토 뒤 새 방향 선택으로 진행한다.
- `application` 이벤트는 `feedback_id,snapshot,actor:producer,reviewer_id,evidence`를 가진다. evidence는 JSON 파일 참조이며 `feedback_id,original_text,observation,hypothesis,changed_relationships,preserved,counterevidence,remaining,before:[file-ref],after:[file-ref],nodes:[id],result:for_review|unresolved`를 기록한다. 미해결 기록은 보존하되 gate를 풀지 않는다. for_review는 사용자 수용이 아니다.
- `work_mode` 이벤트는 실제 사용자 권한·현재 snapshot·reason과 `mode:diagnosis_only|design`을 갖는다. 후보 생략은 전체 실행이다. design 재개는 해제할 `hold_ids`를 명시한다. 제작자의 triage나 refresh로 사용자 중지를 해제하지 않는다.

`comparison-review.json`은 manifest 바깥에 두어 자기 지문 순환을 피한다. 최상위는 `{snapshot,purpose:structure|visual|both,distinction:{verdict:acceptable|rework,observation},candidates:[...]}`다. 후보 기록은 아래와 같다.

```text
candidate_id, version, reviewer_id, producer_id, independent,
verdict:pass, unresolved:[], evidence:<실제 검토 문서 참조>,
feedback_ids:[관련 비차단 취향 제외 피드백 ID],
feedback_events:[각 관련 피드백의 원문/분류/적용 이벤트 ID 순서],
observations:[{region,nodes:[실제 노드 ID],finding}],
regressions:<손실/잔여 문제와 없다고 판단한 관찰>,
reference_usage:[{reference_id,verdict:acceptable|unresolved,source_region,
  task_fit,retained,changed,study_evidence:<파일 참조>,product_nodes:[실제 노드 ID]}]
```

상태의 feedback 항목에 각 원문의 updates가 제공된다. 검토자는 실제로 읽은 이벤트까지만 기록한다. 자기 검토는 reviewer_id=producer_id, independent=false로 표시할 수 있다. 최종 `review.json`은 같은 후보 기록에 snapshot을 붙이며 independent=true와 서로 다른 실제 검토자/제작자를 요구한다. 두 검토 모두 실제 화면·관련 피드백 변경에 따라 갱신한다.

`prepare(comparison)`은 기술 report와 후보별 visual_review/readiness_errors를 구분한다. 적격 후보가 하나 이상이면 그 후보만 선택할 수 있다. `submit(direction/final)`과 `gate`에서 같은 조건을 재검사하므로 UI 숨김만으로 보호하지 않는다. `status`는 production_allowed_by_candidate, expansion_allowed, selection_usable, eligible_candidate_ids를 제공한다. 직접 디자인 도구의 물리적 호출 차단이나 이미 배포한 결과의 자동 롤백은 제공하지 않는다.
