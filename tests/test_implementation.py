import copy
import importlib.util
import json
from pathlib import Path
import struct
import zlib

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'skills/design-implementation/scripts/verify.py'
spec = importlib.util.spec_from_file_location('implementation_verify', SCRIPT)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def png(width=100, height=100):
    def chunk(name, data):
        return struct.pack('>I', len(data)) + name + data + struct.pack('>I', zlib.crc32(name + data))
    raw = (b'\0' + b'\x22\x33\x44\xff' * width) * height
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b'')


def make(root):
    code = root / 'app'; (code / 'lib').mkdir(parents=True)
    (code / 'lib/main.dart').write_text('Synthetic renderer source')
    evidence = root / 'evidence'; evidence.mkdir()
    def artifact(name, data):
        (evidence / name).write_bytes(data)
        return {'path': name, 'sha256': gate.digest(data)}
    fixture = artifact('fixture.json', b'{"books": []}')
    case = {'id':'empty-phone', 'context':{'platform':'ios','width':100,'height':100,'dpr':1,'text_scale':1,'locale':'ko','state':'empty','fixture_sha256':fixture['sha256'],'scroll':[0,0]},
            'max_box_delta_px':1, 'hierarchy':['header','empty','actions'], 'actions':['import','connect'],
            'elements':{'title':{'box':[10,10,80,20],'text':'첫 페이지','font_size':16,'fill':'#ffffff'},'button':{'box':[10,50,80,48],'text':'가져오기'}},
            'fixture':fixture, 'reference_png':artifact('reference.png',png())}
    case['reference_measurement'] = artifact('reference.json',json.dumps({k:case[k] for k in gate.MEASURED}).encode())
    contract = {'schema_version':1,'scope':'Synthetic empty screen only','decision':{'quote':'Synthetic instruction','source':'synthetic fixture, not a user approval'},'design_version':'fixture-v1','source_roots':['lib'],'cases':[case]}
    actual = {k:copy.deepcopy(case[k]) for k in ('id', *gate.MEASURED)}
    actual.update({'actual_png':artifact('actual.png',png()),'measured_by':'flutter-render-tree'})
    report = {'schema_version':1,'cases':[actual],'code_snapshot':artifact('code.json',json.dumps(gate.fingerprint(code,contract['source_roots'])).encode()),
              'visual_review':{'kind':'self','status':'pass','notes':'Synthetic known answer; no actual visual approval','unresolved':[]}}
    def save(*, rebind=True):
        contract_path=evidence/'contract.json';report_path=evidence/'report.json'
        contract_path.write_text(json.dumps(contract))
        if rebind:
            report['contract_sha256']=gate.digest(contract_path.read_bytes())
            for c in report['cases']:
                c['actual_measurement']=artifact(c['id']+'-actual.json',json.dumps({k:c[k] for k in gate.MEASURED}).encode())
            report['visual_review']['evidence_sha256']=gate.canonical_hash(report['cases'])
        report_path.write_text(json.dumps(report))
        return gate.verify(contract_path,report_path,code)
    assert save()['ok']
    return code,evidence,contract,report,save


@pytest.mark.parametrize('mutation,expected', [
    ('box','box delta'),('text','text differs'),('style','fill differs'),
    ('missing_element','elements changed'),('extra_element','elements changed'),
    ('missing_action','actions changed'),('new_action','actions changed'),
    ('reorder','hierarchy changed'),('context','context differs'),
    ('missing_case','cases'),('duplicate_case','Duplicate case'),
    ('source_change','Code/input'),('source_added','Code/input'),('source_deleted','source root'),
    ('screenshot','Artifact changed'),('dimensions','PNG dimensions'),
    ('stale_review','Visual review is stale'),('unresolved','unresolved'),
    ('config_measurement','actual render measurement'),('raw_mismatch','report differs'),
    ('no_decision','user instruction'),('no_elements','no measured elements'),
])
def test_known_drift_cannot_pass_despite_successful_functional_checks(tmp_path,mutation,expected):
    code,base,contract,report,save=make(tmp_path)
    c=report['cases'][0]; rebind=True
    report['functional_tests']={'passed':79,'clipped':0}  # Does not excuse a design mismatch.
    if mutation=='box':c['elements']['title']['box'][0]+=2
    elif mutation=='text':c['elements']['title']['text']='나만의 조용한 서재'
    elif mutation=='style':c['elements']['title']['fill']='#000000'
    elif mutation=='missing_element':del c['elements']['button']
    elif mutation=='extra_element':c['elements']['sample']=copy.deepcopy(c['elements']['button'])
    elif mutation=='missing_action':c['actions'].remove('connect')
    elif mutation=='new_action':c['actions'].append('sample')
    elif mutation=='reorder':c['hierarchy'].reverse()
    elif mutation=='context':c['context']['locale']='en'
    elif mutation=='missing_case':report['cases']=[]
    elif mutation=='duplicate_case':report['cases'].append(copy.deepcopy(c))
    elif mutation=='source_change':(code/'lib/main.dart').write_text('Changed after capture')
    elif mutation=='source_added':(code/'lib/new.dart').write_text('New input after capture')
    elif mutation=='source_deleted':(code/'lib/main.dart').unlink();(code/'lib').rmdir()
    elif mutation=='screenshot':(base/'actual.png').write_bytes(png(101,100))
    elif mutation=='dimensions':
        data=png(101,100);(base/'actual.png').write_bytes(data);c['actual_png']['sha256']=gate.digest(data)
    elif mutation=='stale_review':report['visual_review']['evidence_sha256']='0'*64;rebind=False
    elif mutation=='unresolved':report['visual_review']['unresolved']=['Missing listening controls']
    elif mutation=='config_measurement':c['measured_by']='Dart constants'
    elif mutation=='raw_mismatch':c['elements']['title']['box'][0]+=1;report['visual_review']['evidence_sha256']=gate.canonical_hash(report['cases']);rebind=False
    elif mutation=='no_decision':contract['decision']={}
    elif mutation=='no_elements':c['elements']={}
    result=save(rebind=rebind)
    assert not result['ok'] and result['status']=='MISMATCH'
    assert any(expected in error for error in result['errors']),result


def test_fixed_geometry_boundary_and_matching_case(tmp_path):
    _,_,_,report,save=make(tmp_path)
    report['cases'][0]['elements']['title']['box'][0]+=1
    result=save();assert result['ok'] and result['metrics']=={'cases':1,'elements':2,'max_box_delta_px':1}
    report['cases'][0]['elements']['title']['box'][0]+=.001
    assert not save()['ok']


def test_changed_baseline_and_old_snapshot_cannot_pass(tmp_path):
    _,_,contract,_,save=make(tmp_path)
    contract['scope']='A different baseline after capture'
    result=save(rebind=False)
    assert not result['ok'] and 'Contract changed' in result['errors'][0]


def test_native_stat_change_requires_design_tool_readback(tmp_path):
    _,base,contract,_,save=make(tmp_path)
    native=base/'opaque.native';native.write_bytes(b'opaque non-Pencil fixture')
    stat=native.stat();contract['native_source']={'path':native.name,'size':stat.st_size,'mtime_ns':stat.st_mtime_ns}
    assert save()['ok']
    native.write_bytes(b'changed opaque fixture')
    assert not save()['ok']


def test_cli_keeps_failed_evidence_unchanged_and_snapshot_is_append_only(tmp_path,capsys):
    code,base,_,report,save=make(tmp_path)
    report['cases'][0]['actions'].append('extra');save()
    files={p:p.read_bytes() for p in base.iterdir()}
    assert gate.cli(['verify','--code-root',str(code),'--contract',str(base/'contract.json'),'--report',str(base/'report.json')])==1
    assert {p:p.read_bytes() for p in files}==files
    assert gate.cli(['snapshot','--code-root',str(code),'--contract',str(base/'contract.json'),'--output',str(base/'code.json')])==1
    assert 'MISMATCH' in capsys.readouterr().out


def test_pencil_content_read_is_refused_before_filesystem_access():
    with pytest.raises(ValueError,match='design tool'):gate.read_json(Path('not-present.pen'))
