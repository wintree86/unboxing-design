"""Frozen behavior cases. Semantic judgments below are inputs, never pixel classifiers."""
import copy
import json
from pathlib import Path
import pytest
from design_factory import build, event, review, start
from design_kit.design_contract import DesignError, file_ref
from design_kit.design_runs import DesignRun, atomic_json

CASES=json.loads((Path(__file__).parent/'fixtures/design_harness/feedback_cases.json').read_text())['cases']

def feedback(run, **kw):
    return run.submit(event(run,'feedback',id='feedback-1',text='여백의 관계를 다시 검토해 주세요.',**kw))

def triage(run,classification='change_request',fid='feedback-1'):
    return run.submit({'id':'triage-'+fid,'kind':'triage','feedback_id':fid,'classification':classification,
                       'actor':'producer','reviewer_id':'maker','rationale':'Synthetic contextual classification, not keyword parsing'})

def visual(run, **kw):
    from design_factory import visual_review
    return visual_review(run,**kw)

def apply_feedback(run, verdict='for_review'):
    record={'feedback_id':'feedback-1','original_text':'여백의 관계를 다시 검토해 주세요.',
            'observation':'Book metadata is split across rows','hypothesis':'grouping is weak',
            'changed_relationships':'title, author and actions regrouped','preserved':'read and listen targets',
            'counterevidence':'button size alone does not resolve group proportion','remaining':'review required',
            'before':[run.manifest()['candidates'][0]['frames'][0]['preview']],
            'after':[run.manifest()['candidates'][0]['frames'][0]['preview']],
            'nodes':['a-title','a-button'],'result':verdict}
    atomic_json(run.directory/'application.json',record)
    return run.submit({'id':'apply-1','kind':'application','feedback_id':'feedback-1',
                       'snapshot':run.status()['current_snapshot'],'actor':'producer','reviewer_id':'maker',
                       'evidence':file_ref(run.ctx,run.rel+'/application.json')})

@pytest.mark.parametrize('case',CASES,ids=[c['id'] for c in CASES])
def test_feedback_regression(case,tmp_path):
    ctx,m=build(tmp_path); run=start(ctx,m); key=case['id']
    if key=='R01':
        (run.directory/'comparison-review.json').unlink()
        assert not run.prepare()['ok']
        with pytest.raises(DesignError):run.submit(event(run))
    elif key=='R02':
        p=run.directory/'comparison-review.json'; data=json.loads(p.read_text());data['snapshot']='old';atomic_json(p,data)
        assert not run.prepare()['ok']
    elif key=='R03':
        feedback(run)
        assert 'a' not in run.status()['eligible_candidate_ids']
        with pytest.raises(DesignError):run.submit(event(run))
        assert run.state()['events'][-1]['payload']['text']=='여백의 관계를 다시 검토해 주세요.'
    elif key=='R04':
        run.submit(event(run)); review(run);assert run.prepare('final')['ok'];run.submit(event(run,'final'))
        assert run.gate()['ok'];feedback(run);triage(run,'rejection')
        assert not run.gate()['ok']
        assert run.state()['selected']['event_id']=='direction-1' and run.state()['final_event']=='final-1'
    elif key=='R05':
        run.submit(event(run));before=copy.deepcopy(run.state()['selected']);feedback(run);triage(run,'preference')
        assert run.status()['selection_usable'] and run.state()['selected']==before
    elif key=='R06':
        run.submit(event(run,candidate_id='b')); before=copy.deepcopy(run.state()['selected'])
        feedback(run);triage(run,'rejection')
        assert run.status()['selection_usable'] and run.state()['selected']==before
    elif key=='R07':
        feedback(run,candidate_id=None,version=None,classification='diagnosis_only');run.refresh('Analysis only, no new design')
        resumed=DesignRun(ctx,'test')
        assert not resumed.status()['production_allowed'] and resumed.status()['analysis_allowed']
        assert not resumed.prepare()['ok']
    elif key=='R08':
        feedback(run,classification='diagnosis_only');
        feedback2=event(run,'feedback',id='hold-b',candidate_id='b',text='Stop B',classification='diagnosis_only');run.submit(feedback2)
        run.submit(event(run,'work_mode',id='resume-a',mode='design',hold_ids=['feedback-1'],reason='User resumes A'))
        assert run.status()['production_allowed_by_candidate']=={'a':True,'b':False}
        assert run.state()['selected'] is None
    elif key=='R09':
        run.submit(event(run,candidate_id='b',reason='B가 좋다'))
        assert run.state()['selected']['version']==1 and 'fixed_attributes' not in run.state()['selected']
        assert next(e for e in run.state()['events'] if e['kind']=='direction')['payload']['reason']=='B가 좋다'
    elif key=='R10':
        feedback(run);triage(run);apply_feedback(run,verdict='unresolved');visual(run)
        assert 'a' not in run.status()['eligible_candidate_ids']
    elif key=='R11':
        visual(run,reference_verdict='unresolved')
        assert not run.prepare()['ok']
        visual(run,reference_verdict='acceptable');assert run.prepare()['ok']
    elif key=='R12':
        visual(run,distinction_verdict='rework');assert not run.prepare()['ok']
        visual(run,purpose='visual',distinction_verdict='acceptable');assert run.prepare()['ok']
    elif key=='R13':
        m['presentation'][0]['preview']=m['candidates'][1]['frames'][0]['preview'];atomic_json(run.manifest_path,m)
        run.refresh('Review incorrect presented image');visual(run)
        assert not run.prepare()['ok']
        from design_kit.design_board import board_data
        assert board_data(run)[0]['presentation_errors']
    elif key=='R14':
        old=event(run,'feedback',id='old',version=0,snapshot='previous-observed',text='Past version comment')
        # Historical versions use positive version numbers; current is advanced independently.
        old['version']=1;m['candidates'][0]['version']=2;atomic_json(run.manifest_path,m);run.refresh('version two')
        run.submit(old);run.submit(old)
        assert len([e for e in run.state()['events'] if e['id']=='old'])==1
        assert not run.status()['feedback'][0]['active']
    elif key=='R15':
        feedback(run);triage(run);apply_feedback(run)
        assert 'a' not in run.status()['eligible_candidate_ids']
        visual(run);assert 'a' in run.status()['eligible_candidate_ids']
    elif key=='R16':
        run.submit(event(run));feedback(run);triage(run,'rejection')
        m['candidates'][0]['version']=2;m['presentation'][0]['version']=2
        atomic_json(run.manifest_path,m);run.refresh('Revise selected candidate to version two');apply_feedback(run)
        visual(run);assert run.prepare()['ok'];run.submit(event(run,id='direction-2',version=2))
        assert run.status()['selection_usable']
        assert len([e for e in run.state()['events'] if e['kind']=='direction'])==2


def test_legacy_status_is_read_only_and_upgrade_preserves_original_bytes(tmp_path):
    ctx,m=build(tmp_path);m['schema_version']=1;m.pop('presentation')
    run=DesignRun(ctx,'test');run.initialize(m)
    old=run.state();old['schema_version']=1
    atomic_json(run.state_path,old)
    before={p:p.read_bytes() for p in (run.state_path,run.manifest_path)}
    assert run.status()['upgrade_required']
    assert all(p.read_bytes()==data for p,data in before.items())
    run.upgrade('Explicit compatibility transition for synthetic fixture')
    for p,data in before.items(): assert p.with_name(p.stem+'-v1.json').read_bytes()==data
    assert not (run.directory/'comparison-review.json').exists()
    assert not run.prepare()['ok']


def test_post_choice_reclassification_requires_new_choice(tmp_path):
    ctx,m=build(tmp_path);run=start(ctx,m);feedback(run,classification='preference');run.submit(event(run))
    triage(run,'rejection');apply_feedback(run);visual(run)
    assert not run.status()['selection_usable']
    assert run.prepare()['ok'];run.submit(event(run,id='new-choice'))
    assert run.status()['selection_usable']


def test_producer_cannot_release_hold(tmp_path):
    ctx,m=build(tmp_path);run=start(ctx,m);feedback(run,classification='diagnosis_only')
    with pytest.raises(DesignError,match='resume'):triage(run,'preference')
    with pytest.raises(DesignError):run.submit(event(run,'work_mode',mode='design',hold_ids=['feedback-1'],actor='producer'))
    assert not run.status()['production_allowed']


def test_application_changed_after_review_invalidates_review(tmp_path):
    ctx,m=build(tmp_path);run=start(ctx,m);feedback(run);triage(run);apply_feedback(run);visual(run)
    assert 'a' in run.status()['eligible_candidate_ids']
    payload=dict(run.state()['events'][-1]['payload'],id='apply-2')
    run.submit(payload)
    assert 'a' not in run.status()['eligible_candidate_ids']


def test_fabricated_node_or_after_image_cannot_resolve_feedback(tmp_path):
    ctx,m=build(tmp_path);run=start(ctx,m);feedback(run);triage(run);apply_feedback(run);visual(run)
    p=run.directory/'application.json';data=json.loads(p.read_text());data['nodes']=['invented'];atomic_json(p,data)
    payload=dict(next(e['payload'] for e in run.state()['events'] if e['kind']=='application'),id='bad-apply',
                 evidence=file_ref(ctx,run.rel+'/application.json'))
    run.submit(payload);visual(run)
    assert 'a' not in run.status()['eligible_candidate_ids']


def test_review_file_cannot_enter_its_own_fingerprint(tmp_path):
    from design_kit.design_contract import validate_contract
    ctx,m=build(tmp_path);run=start(ctx,m)
    m['inputs']=[file_ref(ctx,run.rel+'/comparison-review.json')]
    assert not validate_contract(m,ctx)['ok']


def test_run_wide_application_covers_multiple_candidates(tmp_path):
    ctx,m=build(tmp_path);run=start(ctx,m);feedback(run,candidate_id=None,version=None);triage(run);apply_feedback(run)
    p=run.directory/'application.json';data=json.loads(p.read_text())
    data['after']=[c['frames'][0]['preview'] for c in m['candidates']]
    data['nodes']=['a-title','b-title'];atomic_json(p,data)
    payload=dict(next(e['payload'] for e in run.state()['events'] if e['kind']=='application'),id='apply-all',
                 evidence=file_ref(ctx,run.rel+'/application.json'))
    run.submit(payload);visual(run)
    assert run.prepare()['ok'] and run.status()['eligible_candidate_ids']==['a','b']


def test_non_ui_handoff_respects_explicit_hold(tmp_path):
    ctx,m=build(tmp_path);m.update(scope='non_ui',reason='Synthetic backend task')
    run=DesignRun(ctx,'test');run.initialize(m);run.refresh('Backend scope');assert run.prepare()['ok']
    feedback(run,candidate_id=None,version=None,classification='diagnosis_only')
    assert not run.gate()['ok'] and not run.prepare()['ok']


def test_revision_budget_also_blocks_production_permission(tmp_path):
    ctx,m=build(tmp_path);run=start(ctx,m);run.submit(event(run))
    for reason in ('First correction','Second correction','Third exceeds budget'):
        run.refresh(reason,automatic=True)
    status=run.status()
    assert status['phase']=='blocked' and not status['production_allowed']
    assert status['production_allowed_by_candidate']=={'a':False,'b':False}
    assert not status['expansion_allowed'] and status['eligible_candidate_ids']==[]
    assert status['selected']['candidate_id']=='a'
