import copy
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path

import pytest

from design_kit.design_contract import DesignError, file_ref, validate_contract
from design_kit.design_measure import PROFILE, contrast, measure_bundle
from design_kit.design_runs import DesignRun, atomic_json
from design_factory import build, event, png, review, start, update_observation

FIXTURES=Path(__file__).parent/"fixtures/design_harness"
CASES=json.loads((FIXTURES/"cases.json").read_text())["cases"]


@pytest.mark.parametrize("case",CASES,ids=[c["id"] for c in CASES])
def test_frozen_regression(case,tmp_path,monkeypatch):
    ctx,m=build(tmp_path)
    key=case["id"]
    frame=m["candidates"][0]["frames"][0]
    if key=="complete-comparison":
        r=measure_bundle(m,ctx)
        assert r["ok"] and r["metrics"]["delivered_frames"]==2
        assert len(r["frames"])==2 and sum(f["nodes"] for f in r["frames"])==8
        return
    if key=="unobserved-reference": m["references"][0].pop("observation")
    elif key=="missing-reference-source": m["references"][0]["url"]=""
    elif key=="duplicate-reference": m["references"].append(copy.deepcopy(m["references"][0]))
    elif key=="source-changed": ctx.resolve("docs/prd.md").write_text("Changed requirement")
    elif key=="preview-changed": ctx.resolve(frame["preview"]["path"]).write_bytes(b"not the original PNG")
    elif key=="missing-state": m["screens"][0]["states"].append("error");m["comparison"].append({"screen":"detail","state":"error","viewport":"mobile"})
    elif key=="wrong-content": update_observation(ctx,m,lambda d:d["nodes"][1].update(content="wrong"))
    elif key=="wrong-action-target": m["screens"][0]["actions"][0]["target"]="missing-screen"
    elif key=="wrong-viewport": update_observation(ctx,m,lambda d:d["nodes"][0]["bounds"].update(width=389))
    elif key=="missing-signature": frame["signature_nodes"]={}
    elif key=="clipped-text": update_observation(ctx,m,lambda d:d["nodes"][1].update(problems="partially clipped"))
    elif key in ("overlapping-siblings","declared-overlay"):
        def overlay(d):
            for i in ("one","two"):
                d["nodes"].append({"id":i,"parent":"a-root","type":"rectangle","name":i,"bounds":{"x":20,"y":200,"width":50,"height":50}})
        update_observation(ctx,m,overlay)
        if key=="declared-overlay":frame["allowed_overlaps"]=[{"nodes":["one","two"],"reason":"known intentional decoration"}]
    elif key=="unknown-overlay-exception": frame["allowed_overlaps"]=[{"nodes":["a-title","a-button"],"reason":"not actually intersecting"}]
    elif key.startswith("contrast-"):
        monkeypatch.setattr("design_kit.design_measure.contrast",lambda a,b:4.5 if key=="contrast-at-boundary" else 4.499999)
    elif key.startswith("target-"):
        update_observation(ctx,m,lambda d:d["nodes"][2]["bounds"].update(height=44 if key=="target-at-boundary" else 43.99))
    elif key=="malformed-root":m=[]
    elif key=="malformed-numbers":m["viewports"][0]["width"]=float("nan")
    elif key=="path-escape":m["brief"]={"path":"docs/../../outside.md","sha256":"x"}
    elif key=="symlink-escape":
        outside=tmp_path/"outside.md";outside.write_text("outside")
        (ctx.docs_root/"docs/link.md").symlink_to(outside)
        m["brief"]={"path":"docs/link.md","sha256":hashlib.sha256(b"outside").hexdigest()}
    elif key.startswith("non-ui-"):
        m.update(scope="non_ui",reason="Backend-only queue change from the source")
        if key=="non-ui-without-reason":m.pop("reason")
        run=DesignRun(ctx,"test");run.initialize(m);run.refresh("Read backend scope")
        r=run.prepare()
        assert r["ok"]==(case["expected"]=="pass")
        assert run.gate()["ok"]==(case["expected"]=="pass")
        return
    else:
        run=start(ctx,m)
        if key=="no-user-decision":assert not run.gate()["ok"];return
        if key=="stale-measurements":
            p=run.directory/"measurements.json";r=json.loads(p.read_text());r["snapshot"]="old";atomic_json(p,r)
            with pytest.raises(DesignError,match="Measurement"):run.submit(event(run))
            return
        if key=="stale-user-selection":
            with pytest.raises(DesignError,match="snapshot"):run.submit(event(run,snapshot="old"))
            return
        if key=="revision-limit":
            run.refresh("automatic correction one",automatic=True)
            run.refresh("automatic correction two",automatic=True)
            assert run.refresh("third correction",automatic=True)["phase"]=="blocked"
            assert not run.gate()["ok"]
            return
        if key=="concurrent-decisions":
            def select(cid):
                try:run.submit(event(run,id=f"choose-{cid}",candidate_id=cid));return True
                except DesignError:return False
            with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(select,["a","b"]))
            assert results.count(True)==1
            assert sum(e["kind"]=="direction" for e in run.state()["events"])==1
            return
        selected=event(run);run.submit(selected)
        if key=="duplicate-event":
            run.submit(selected)
            assert sum(e["kind"]=="direction" for e in run.state()["events"])==1
        elif key=="conflicting-event-id":
            with pytest.raises(DesignError,match="different content"):run.submit({**selected,"candidate_id":"b"})
        elif key=="resume-keeps-decisions":
            resumed=DesignRun(ctx,"test")
            assert resumed.status()["selected"]==run.state()["selected"]
            assert resumed.refresh("Review with no direction change")["selected"]==run.state()["selected"]
        elif key=="direction-change-invalidates-selection":
            m["candidates"][0]["concept"]="A completely different direction";atomic_json(run.manifest_path,m)
            assert run.status()["phase"]=="stale"
            assert run.refresh("Changed concept after feedback")["selected"] is None
        elif key=="final-requires-independent-review":
            with pytest.raises(DesignError):run.prepare("final")
            review(run)
            p=run.directory/"review.json";r=json.loads(p.read_text());r["reviewer_id"]=r["producer_id"];atomic_json(p,r)
            with pytest.raises(DesignError,match="independent"):run.prepare("final")
        elif key=="complete-final":
            review(run)
            assert run.prepare("final")["ok"]
            run.submit(event(run,"final"))
            assert run.gate()["ok"]
            assert json.loads((run.directory/"selection.json").read_text())["candidate_id"]=="a"
            ctx.resolve(frame["source"]["path"]).write_text("source edit after selection")
            assert not run.gate()["ok"]
        else:pytest.fail(f"Unhandled frozen case {key}")
        return
    report=measure_bundle(m,ctx)
    assert report["ok"]==(case["expected"]=="pass"),report


def test_profile_frozen_before_implementation():
    policy=json.loads((FIXTURES/"policy.json").read_text())
    assert all(policy[key]==value for key,value in PROFILE.items())
    assert contrast((0,0,0),(255,255,255))==21
    assert contrast((118,118,118),(255,255,255))>4.5
    assert contrast((119,119,119),(255,255,255))<4.5


@pytest.mark.parametrize("bad",[None,True,{},[{}],{"default":[{}]}])
def test_malformed_state_content_fails_without_crash(tmp_path,bad):
    ctx,m=build(tmp_path);m["screens"][0]["state_content"]=bad
    assert not measure_bundle(m,ctx)["ok"] if bad!={} else measure_bundle(m,ctx)["ok"]


def test_delegation_cannot_expand_to_final(tmp_path):
    ctx,m=build(tmp_path);run=start(ctx,m)
    p=run.directory/"delegation.json"
    atomic_json(p,{"run_id":"test","user_source":"synthetic fixture","allowed_decisions":["direction"]})
    authority={"actor":"delegated","delegation":file_ref(ctx,f"{run.rel}/delegation.json")}
    run.submit(event(run,**authority));review(run);assert run.prepare("final")["ok"]
    with pytest.raises(DesignError,match="does not cover"):run.submit(event(run,"final",**authority))


def test_expected_request_and_recover_projection(tmp_path):
    ctx,m=build(tmp_path);m["request_id"]="request-new";run=start(ctx,m)
    run.submit(event(run));review(run);run.prepare("final");run.submit(event(run,"final"))
    (run.directory/"selection.json").unlink()
    assert run.gate(expected_request_id="request-new")["ok"]
    assert not run.gate(expected_request_id="request-old")["ok"]


def test_final_requires_actual_font_observation(tmp_path):
    ctx,m=build(tmp_path)
    m['candidates'][0]['frames'][0].pop('font_observation')
    run=start(ctx,m);run.submit(event(run));review(run)
    report=run.prepare('final')
    assert not report['ok'] and any('font_observation' in e for e in report['errors'])
    assert run.state()['phase']=='refining'


def test_missing_glyph_rejects_final(tmp_path):
    ctx,m=build(tmp_path);frame=m['candidates'][0]['frames'][0]
    path=ctx.resolve(frame['font_observation']['path']);font=json.loads(path.read_text())
    font['runs'][0]['missing_glyphs']=1;atomic_json(path,font)
    frame['font_observation']=file_ref(ctx,frame['font_observation']['path'])
    assert not measure_bundle(m,ctx,stage='final',candidate_id='a')['ok']


def test_unpinned_image_and_changed_asset_rejected(tmp_path):
    ctx,m=build(tmp_path)
    def image_node(d):
        d['nodes'].append({'id':'photo','parent':'a-root','type':'frame','name':'photo',
            'fill':{'type':'image','url':'photo.png'},'bounds':{'x':20,'y':200,'width':50,'height':50}})
    update_observation(ctx,m,image_node)
    ctx.resolve('designs/photo.png').write_bytes(ctx.resolve('designs/a.png').read_bytes())
    assert not measure_bundle(m,ctx)['ok']
    m['candidates'][0]['assets']=[file_ref(ctx,'designs/photo.png')]
    assert measure_bundle(m,ctx)['ok']
    ctx.resolve('designs/photo.png').write_bytes(b'changed image')
    assert not measure_bundle(m,ctx)['ok']


def test_interrupted_initialization_recovers_identical_manifest(tmp_path):
    ctx,m=build(tmp_path);run=DesignRun(ctx,'test');atomic_json(run.manifest_path,m)
    state=run.initialize(m)
    assert state['phase']=='draft' and state['events']==[]
    with pytest.raises(DesignError,match='already exists'):run.initialize(m)


def test_failed_reference_cannot_be_claimed_as_observed(tmp_path):
    ctx,m=build(tmp_path);m['references'][0]['access_status']='login_required'
    assert not validate_contract(m,ctx)['ok']


def test_public_fallback_preserves_failed_attempt_separately(tmp_path):
    ctx,m=build(tmp_path)
    m['reference_attempts']=[{'url':'https://example.com/private','status':'login_required','observation':None}]
    m['references'][0].update(url='https://example.com/public-original',access_status='observed')
    assert validate_contract(m,ctx)['ok']
