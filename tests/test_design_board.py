from contextlib import contextmanager
from http.client import HTTPConnection
import json
import threading

from design_kit.design_board import BoardServer, board_html, export_board
from design_factory import build, start


@contextmanager
def running(run):
    server=BoardServer(run)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:yield server
    finally:server.shutdown();server.server_close();thread.join(timeout=2)


def request(server,method,path,body=None,headers=None):
    conn=HTTPConnection("127.0.0.1",server.server_port,timeout=20)
    h={"Origin":server.origin,"Content-Type":"application/json",**(headers or {})}
    conn.request(method,path,json.dumps(body) if body is not None else None,h)
    response=conn.getresponse();status=response.status;data=response.read();conn.close()
    return status,data


def test_board_saves_feedback_and_direction_survives_restart(tmp_path):
    ctx,m=build(tmp_path);run=start(ctx,m)
    with running(run) as server:
        status,page=request(server,"GET","/")
        assert status==200 and "디자인 방향 선택" in page.decode()
        snapshot=run.status()["current_snapshot"]
        payload={"id":"feedback-1","kind":"feedback","candidate_id":"a","snapshot":snapshot,"csrf":server.csrf,
                 "text":"빛은 좋지만 더 따뜻했으면 좋겠어요.","screen":"detail"}
        assert request(server,"POST","/event",payload)[0]==200
        payload.update(id="direction-1",kind="direction",reason="차분한 분위기")
        assert request(server,"POST","/event",payload)[0]==200
        assert request(server,"POST","/event",payload)[0]==200
    with running(run) as server:
        status,data=request(server,"GET","/status")
        assert status==200 and json.loads(data)["selected"]["candidate_id"]=="a"
        assert run.state()["phase"]=="refining"
        assert sum(e["kind"]=="direction" for e in run.state()["events"])==1
        assert any(e["payload"].get("text")=="빛은 좋지만 더 따뜻했으면 좋겠어요." for e in run.state()["events"])


def test_server_rejects_cross_origin_token_and_paths(tmp_path):
    ctx,m=build(tmp_path);run=start(ctx,m)
    with running(run) as server:
        payload={"id":"direction-1","kind":"direction","candidate_id":"a","snapshot":run.status()["current_snapshot"],"csrf":server.csrf}
        assert request(server,"POST","/event",payload,{"Origin":"https://other.test"})[0]==403
        assert request(server,"POST","/event",{**payload,"csrf":"wrong"})[0]==403
        assert request(server,"POST","/event",{**payload,"snapshot":"old"})[0]==409
        assert request(server,"POST","/event",{**payload,"kind":"final"})[0]==409
        assert request(server,"GET","/",headers={"Host":"evil.test"})[0]==403
        assert request(server,"GET","/images/../../docs/prd.md")[0]!=200
        assert request(server,"GET","/images/image-0.png")[0]==200
        assert run.state()["phase"]=="awaiting_direction"


def test_board_escapes_content_and_exports_preview_files(tmp_path):
    ctx,m=build(tmp_path);run=start(ctx,m)
    m["theme"]["requested"]="</script><script>alert('x')</script>"
    from design_kit.design_runs import atomic_json
    atomic_json(run.manifest_path,m)
    path=export_board(run,ctx.code_root/"designs/comparison")
    html=path.read_text()
    assert "</script><script>alert" not in html
    assert len(list((path.parent/"images").glob("*.png")))==2
    assert (path.parent/"board.js").is_file()
    assert "다운로드한 선택 기록" in html


def test_final_gallery_only_presents_selected_candidate(tmp_path):
    from design_factory import event,review
    from design_kit.design_board import board_data
    ctx,m=build(tmp_path);run=start(ctx,m);run.submit(event(run));review(run)
    assert run.prepare('final')['ok']
    data,_=board_data(run)
    assert [c['id'] for c in data['candidates']]==['a']
