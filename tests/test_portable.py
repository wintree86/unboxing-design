import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from design_factory import build

PACKAGE = Path(__file__).resolve().parents[1]


def invoke(script, *args, cwd, ok=True):
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    result = subprocess.run([sys.executable, "-S", str(script), *map(str, args)], cwd=cwd,
                            env=env, capture_output=True, text=True, timeout=30)
    assert (result.returncode == 0) == ok, result.stdout + result.stderr
    return json.loads(result.stdout)


@pytest.mark.parametrize("target,folder", [("codex", ".agents"), ("claude", ".claude")])
def test_installed_pair_runs_after_source_checkout_is_removed(tmp_path, target, folder):
    checkout = tmp_path / "package checkout"
    shutil.copytree(PACKAGE, checkout, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "dist"))
    project = tmp_path / "company project"
    project.mkdir()
    outside = tmp_path / "unrelated working directory"
    outside.mkdir()
    receipt = invoke(checkout / "install.py", "--target", target, "--project", project, cwd=outside)
    assert receipt["skills"] == 2 and receipt["files"] > 10
    skills = project / folder / "skills"
    script = skills / "design-harness/scripts/design.py"
    shutil.rmtree(checkout)
    doctor = invoke(script, "--project-root", project, "doctor", cwd=outside)
    assert doctor["ok"] and doctor["skills_found"] == 2
    assert Path(doctor["docs_root"]) == project
    assert not any(p.is_symlink() for p in skills.rglob("*"))

    # Known synthetic rendered geometry, pixels and decisions: no real user approval.
    ctx, manifest = build(project / "artifacts")
    (project / "design-kit.json").write_text(json.dumps({
        "schema_version": 1, "docs_root": "artifacts/hub", "code_root": "artifacts/code"}))
    def cli(*args, ok=True):
        return invoke(script, "--project-root", project, *args, cwd=outside, ok=ok)
    assert cli("init", "--run", "test", "--source", "docs/prd.md", "--brief",
               "docs/design-harness/test/brief.md")["phase"] == "draft"
    ctx.resolve("docs/design-harness/test/manifest.json").write_text(json.dumps(manifest))
    cli("refresh", "--run", "test", "--reason", "Synthetic installation fixture")
    measurement = cli("prepare", "--run", "test")
    assert measurement["ok"] and measurement["metrics"]["delivered_frames"] == 2
    board = cli("board", "--run", "test", "--output", "designs/board")
    page = Path(board["board"])
    assert page.is_file() and len(list((page.parent / "images").glob("*.png"))) == 2
    assert "DESIGN KIT / STUDY" in page.read_text()
    state = cli("status", "--run", "test")
    assert state["phase"] == "awaiting_direction" and state["selected"] is None
    event = {"id": "synthetic-choice", "kind": "direction", "candidate_id": "a", "version": 1,
             "snapshot": state["current_snapshot"], "actor": "user",
             "authority": "Synthetic test event, not an actual user choice", "reason": "Fixture"}
    event_file = outside / "synthetic-event.json"
    event_file.write_text(json.dumps(event))
    first = cli("event", "--run", "test", "--file", event_file)
    second = cli("event", "--run", "test", "--file", event_file)
    assert first == second
    resumed = cli("status", "--run", "test")
    assert resumed["phase"] == "refining" and resumed["selected"]["candidate_id"] == "a"
    ctx.resolve("docs/prd.md").write_text("Changed requirement after selection")
    assert cli("status", "--run", "test")["phase"] == "stale"
    assert not cli("gate", "--run", "test", ok=False)["ok"]
    assert not (outside / "docs").exists()
    assert not (skills / "docs").exists()


def test_install_conflict_and_modified_upgrade_preserve_existing_files(tmp_path):
    skills = tmp_path / "skills"
    (skills / "design-bot").mkdir(parents=True)
    existing = skills / "design-bot/SKILL.md"
    existing.write_text("Company-specific original")
    install = PACKAGE / "install.py"
    assert not invoke(install, "--skills-dir", skills, cwd=tmp_path, ok=False)["ok"]
    assert existing.read_text() == "Company-specific original"
    assert not (skills / "design-harness").exists()
    fresh = tmp_path / "fresh"
    assert invoke(install, "--skills-dir", fresh, cwd=tmp_path)["action"] == "installed"
    assert invoke(install, "--skills-dir", fresh, cwd=tmp_path)["action"] == "unchanged"
    changed = fresh / "design-bot/SKILL.md"
    changed.write_text("A local change")
    for option in ("--upgrade", "--remove"):
        assert not invoke(install, "--skills-dir", fresh, option, cwd=tmp_path, ok=False)["ok"]
        assert changed.read_text() == "A local change"
        assert (fresh / "design-harness/SKILL.md").is_file()


def test_upgrade_and_remove_only_owned_files(tmp_path):
    checkout = tmp_path / "release"
    shutil.copytree(PACKAGE, checkout, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "dist"))
    project = tmp_path / "project"
    project.mkdir()
    install = checkout / "install.py"
    invoke(install, "--target", "codex", "--project", project, cwd=tmp_path)
    skills = project / ".agents/skills"
    (skills / "company-skill").mkdir()
    (skills / "company-skill/SKILL.md").write_text("Unrelated skill")
    (project / "docs").mkdir()
    (project / "docs/decision.md").write_text("Saved project decision")
    original = checkout / "skills/design-bot/SKILL.md"
    original.write_text(original.read_text() + "\nSynthetic version update.\n")
    assert not invoke(install, "--target", "codex", "--project", project, cwd=tmp_path, ok=False)["ok"]
    assert invoke(install, "--target", "codex", "--project", project, "--upgrade", cwd=tmp_path)["action"] == "upgraded"
    assert (skills / "design-bot/SKILL.md").read_text() == original.read_text()
    assert invoke(install, "--target", "codex", "--project", project, "--remove", cwd=tmp_path)["action"] == "removed"
    assert not (skills / "design-bot").exists() and not (skills / "design-harness").exists()
    assert (skills / "company-skill/SKILL.md").read_text() == "Unrelated skill"
    assert (project / "docs/decision.md").read_text() == "Saved project decision"


def test_project_install_does_not_follow_global_skill_symlinks(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    global_settings = tmp_path / "global-settings"
    global_settings.mkdir()
    (project / ".agents").symlink_to(global_settings, target_is_directory=True)
    assert not invoke(PACKAGE / "install.py", "--target", "codex", "--project", project,
                      cwd=tmp_path, ok=False)["ok"]
    assert list(global_settings.iterdir()) == []


def test_existing_symlink_skill_is_preserved(tmp_path):
    skills = tmp_path / "skills"
    skills.mkdir()
    original = tmp_path / "company-original"
    original.mkdir()
    (original / "SKILL.md").write_text("Original company skill")
    (skills / "design-bot").symlink_to(original, target_is_directory=True)
    assert not invoke(PACKAGE / "install.py", "--skills-dir", skills, cwd=tmp_path, ok=False)["ok"]
    assert (skills / "design-bot").is_symlink()
    assert (original / "SKILL.md").read_text() == "Original company skill"
    assert not (skills / "design-harness").exists()


@pytest.mark.parametrize("config", [{}, {"schema_version": True}, {"schema_version": 1, "docs_root": 2},
                                   {"schema_version": 1, "doc_root": "."}])
def test_bad_config_fails_explicitly_without_writing(tmp_path, config):
    (tmp_path / "design-kit.json").write_text(json.dumps(config))
    result = invoke(PACKAGE / "design.py", "--project-root", tmp_path, "doctor", cwd=tmp_path, ok=False)
    assert not result["ok"] and not (tmp_path / "docs").exists()


def test_external_config_paths_anchor_to_project_not_cwd(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    config = tmp_path / "external.json"
    config.write_text(json.dumps({"schema_version": 1, "docs_root": "notes", "code_root": "source"}))
    result = invoke(PACKAGE / "design.py", "--project-root", project, "--config", config, "doctor", cwd=tmp_path)
    assert Path(result["docs_root"]) == project / "notes"
    assert Path(result["code_root"]) == project / "source"


def test_local_skill_links_survive_installation(tmp_path):
    import re
    skills = tmp_path / "skills"
    invoke(PACKAGE / "install.py", "--skills-dir", skills, cwd=tmp_path)
    links = []
    for doc in skills.rglob("*.md"):
        for link in re.findall(r"\[[^\]]+\]\(([^)]+)\)", doc.read_text()):
            if "://" not in link and not link.startswith("#"):
                target = (doc.parent / link.split("#")[0]).resolve()
                assert target.is_relative_to(skills) and target.is_file(), (doc, link)
                links.append(link)
    assert len(links) >= 20
