import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

from test_portable import PACKAGE, invoke


def old_pair(tmp_path):
    skills=tmp_path/'skills'
    invoke(PACKAGE/'install.py','--skills-dir',skills,cwd=tmp_path)
    # Emulate an unmodified owned 0.2.x receipt, retaining the source hashes of its two skills.
    shutil.rmtree(skills/'design-implementation')
    path=skills/'.design-kit-install.json';data=json.loads(path.read_text())
    data['version']='0.2.0';data['files']={p:h for p,h in data['files'].items() if not p.startswith('design-implementation/')}
    path.write_text(json.dumps(data))
    return skills


def test_two_skill_upgrade_preserves_project_records(tmp_path):
    skills=old_pair(tmp_path)
    record=tmp_path/'docs/decision.json';record.parent.mkdir();record.write_bytes(b'{"historical-choice":"keep"}')
    result=invoke(PACKAGE/'install.py','--skills-dir',skills,'--upgrade',cwd=tmp_path)
    assert result['skills']==3 and result['action']=='upgraded'
    assert (skills/'design-implementation/scripts/verify.py').is_file()
    assert record.read_bytes()==b'{"historical-choice":"keep"}'


def test_new_skill_name_collision_preserves_both_installed_and_company_files(tmp_path):
    skills=old_pair(tmp_path)
    company=skills/'design-implementation';company.mkdir();(company/'SKILL.md').write_text('Company-owned skill')
    original={p:p.read_bytes() for p in skills.rglob('*') if p.is_file()}
    assert not invoke(PACKAGE/'install.py','--skills-dir',skills,'--upgrade',cwd=tmp_path,ok=False)['ok']
    assert {p:p.read_bytes() for p in original}==original


def test_changed_old_skill_is_never_replaced_when_adding_new_skill(tmp_path):
    skills=old_pair(tmp_path)
    p=skills/'design-bot/SKILL.md';p.write_text('Local custom version')
    assert not invoke(PACKAGE/'install.py','--skills-dir',skills,'--upgrade',cwd=tmp_path,ok=False)['ok']
    assert p.read_text()=='Local custom version' and not (skills/'design-implementation').exists()


def test_installed_verifier_works_without_package_checkout(tmp_path):
    from test_implementation import make
    code,base,_,_,_=make(tmp_path/'fixture')
    checkout=tmp_path/'checkout';shutil.copytree(PACKAGE,checkout,ignore=shutil.ignore_patterns('.git','__pycache__','.pytest_cache','dist'))
    skills=tmp_path/'skills';invoke(checkout/'install.py','--skills-dir',skills,cwd=tmp_path)
    shutil.rmtree(checkout)
    result=invoke(skills/'design-implementation/scripts/verify.py','verify','--code-root',code,'--contract',base/'contract.json','--report',base/'report.json',cwd=tmp_path)
    assert result['ok'] and result['metrics']['cases']==1


def test_upgrade_rolls_back_all_owned_skills_if_new_skill_write_fails(tmp_path,monkeypatch):
    skills=old_pair(tmp_path)
    spec=importlib.util.spec_from_file_location('design_install',PACKAGE/'install.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    original={p:p.read_bytes() for p in skills.rglob('*') if p.is_file()}
    real=Path.rename
    def failing(self,target):
        if self.name=='design-implementation' and Path(target)==skills/'design-implementation':raise OSError('injected copy failure')
        return real(self,target)
    monkeypatch.setattr(Path,'rename',failing)
    import pytest
    with pytest.raises(OSError):module.transact(skills,upgrade=True)
    assert {p:p.read_bytes() for p in original}==original
    assert not (skills/'design-implementation').exists()
