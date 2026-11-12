"""Local comparison board: exported previews plus explicit, version-bound decisions."""

from __future__ import annotations

import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import secrets
import shutil
from urllib.parse import parse_qs, urlparse

from .design_contract import DesignError, cell, fingerprint, safe_path, file_ref
from .design_runs import DesignRun

ASSET_DIR = Path(__file__).parent / "design_board_assets"


def board_data(run: DesignRun):
    manifest, status = run.manifest(), run.status()
    assets, candidates = {}, []
    viewports = {v["id"]: v for v in manifest.get("viewports", [])}
    def image_asset(ref, *, document=False):
        if not isinstance(ref, dict):
            return None
        path = safe_path(run.ctx, ref["path"])
        suffix = path.suffix.lower()
        allowed = ('.png','.jpg','.jpeg','.webp') if not document else ('.md','.txt','.json','.png','.jpg','.jpeg','.webp')
        if suffix not in allowed or not path.is_file(): return None
        existing = next((name for name, value in assets.items() if value == path), None)
        if existing: return f'images/{existing}'
        name = f"image-{len(assets)}{suffix}"
        assets[name] = path
        return f"images/{name}"
    for candidate in manifest.get("candidates", []):
        if (status["phase"] in ("awaiting_final", "ready_for_build") and
                candidate["id"] != (status.get("selected") or {}).get("candidate_id")):
            continue
        frames = []
        for frame in candidate.get("frames", []):
            if not isinstance(frame.get("preview"), dict):
                continue
            path = safe_path(run.ctx, frame["preview"]["path"])
            if path.suffix.lower() != ".png" or not path.is_file():
                raise DesignError("Board previews must be existing PNG exports")
            url = image_asset(frame["preview"])
            frames.append({"id": frame["id"], "cell": list(cell(frame)), "image": url,
                           "width": viewports.get(frame["viewport"], {}).get("width", 390)})
        candidates.append({"id": candidate["id"], "version": candidate["version"],
                           "title": candidate["title"], "concept": candidate["concept"], "frames": frames,
                           "direction_image": image_asset(candidate.get("board")),
                           "features": [f["description"] for f in candidate.get("signature_features", [])]})
    data = {"run_id": run.run_id, "snapshot": status["current_snapshot"], "phase": status["phase"],
            "theme": manifest.get("theme", {}).get("requested", ""), "candidates": candidates,
            "cells": [list(cell(c)) for c in manifest.get("comparison", [])],
            "selected": status.get("selected"),
            "eligible_candidate_ids": status['eligible_candidate_ids'],
            "production_allowed": status['production_allowed'],
            "production_allowed_by_candidate": status['production_allowed_by_candidate'],
            "work_mode": status['work_mode'], "readiness_errors": status['readiness_errors'],
            "presentation_errors": status['presentation_errors'],
            "presentation": [{**{k:e.get(k) for k in ('id','role','candidate_id','version','frame_id','node_id')},
                               'image':image_asset(e.get('preview'))} for e in manifest.get('presentation',[])],
            "references": [{"id": r["id"], "url": r["url"], "adopt": r["adopt"], "avoid": r["avoid"],
                            "image": image_asset(r.get("preview") or r.get("observation")),
                            "observation": image_asset(r.get("observation"), document=True)}
                           for r in manifest.get("references", [])]}
    return data, assets


def board_html(data, *, csrf="", online=False):
    esc = html.escape
    phase = data["phase"]
    choosing = phase in ("awaiting_direction", "awaiting_final") and bool(data.get("eligible_candidate_ids"))
    final = phase == "awaiting_final"
    title = "전체 디자인 확정" if final else "디자인 방향 선택"
    notice = {"awaiting_direction": "대표 화면을 비교하고 이어갈 방향을 선택해 주세요.",
              "refining": "방향 선택이 저장되었습니다. 선택한 방향을 전체 화면으로 확장합니다.",
              "awaiting_final": "선택한 방향의 전체 화면을 검토하고 확정해 주세요.",
              "ready_for_build": "최종 결정이 저장되었습니다. 이 버전으로 구현을 시작할 수 있습니다.",
              "stale": "자료가 변경되었습니다. 재측정 후 새 비교 보드를 열어 주세요."}.get(phase, "시안 준비 중입니다. 현재 화면에 피드백을 남길 수 있습니다.")
    radio = "".join(f'<div class="choice"><input type="radio" id="choose-{esc(c["id"])}" name="candidate_id" value="{esc(c["id"])}" required><label for="choose-{esc(c["id"])}">{esc(c["title"])}</label></div>'
                    for c in data["candidates"] if c["id"] in data.get("eligible_candidate_ids", []) and (not final or c["id"] == (data.get("selected") or {}).get("candidate_id")))
    options = '<option value="">전체 제시본</option>' + "".join(f'<option value="{esc(c["id"])}">{esc(c["title"])}</option>' for c in data["candidates"])
    versions = esc(json.dumps({c["id"]:c["version"] for c in data["candidates"]}))
    choice_form = f'''<section class="decision" aria-labelledby="decision-title"><h2 id="decision-title">{title}</h2>
<form id="decision" action="/event" method="post" aria-labelledby="decision-title">
<input type="hidden" name="versions" value="{versions}"><input type="hidden" name="csrf" value="{esc(csrf)}"><input type="hidden" name="snapshot" value="{esc(data['snapshot'])}">
<input type="hidden" name="kind" value="{'final' if final else 'direction'}"><fieldset><legend>이어갈 시안 (필수)</legend>{radio}</fieldset>
<label for="reason">선택 이유 또는 꼭 유지할 점 (선택)</label><textarea id="reason" name="reason" rows="2" maxlength="4000"></textarea>
<button type="submit">{title if online else '선택 기록 다운로드'}</button></form></section>''' if choosing else ""
    if data.get('work_mode') == 'diagnosis_only': notice = '지정한 범위의 원인 조사 중입니다. 중지한 범위는 사용자 제작 재개 지시가 있어야 진행할 수 있습니다.'
    elif phase == 'review_pending': notice = '현재 버전의 검토 근거를 연결해야 선택·인계할 수 있습니다.'
    elif phase == 'feedback_pending': notice = '피드백을 검토 중입니다. 현재 선택·인계 조건을 다시 확인해야 합니다.'
    heading = '원인 조사와 피드백' if data.get('work_mode') == 'diagnosis_only' else ('전체 디자인 검토' if final else '디자인 비교와 피드백')
    issues = data.get('presentation_errors', [])
    issue_html = ''.join(f'<li>{esc(str(issue))}</li>' for issue in issues)
    history_html = ''.join(f'<li><p>{esc(str(e.get("role")))} · {esc(str(e.get("candidate_id") or e.get("id")))} · v{esc(str(e.get("version")))}</p>' +
                          (f'<img class="reference-image" src="{esc(e["image"])}" alt="{esc(str(e.get("role")))} 제시본">' if e.get('image') else '') + '</li>'
                          for e in data.get('presentation', []) if e.get('role') != 'current')
    encoded = json.dumps({**data, "online": online}, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    reference_items = "".join(f'<li><a href="{esc(r["url"])}" target="_blank" rel="noopener noreferrer">{esc(r["id"])}</a>' +
                             (f'<img class="reference-image" src="{esc(r["image"])}" alt="{esc(r["id"])} 실제 관찰 캡처" loading="lazy">' if r.get("image") else "") +
                             (f'<p><a href="{esc(r["observation"])}" target="_blank" rel="noopener">관찰 기록 열기</a></p>' if r.get('observation') else '<p>관찰 기록 미연결</p>') +
                             f'<p>{esc(r["adopt"])}</p><p class="muted">그대로 가져오지 않을 점: {esc(r["avoid"])}</p></li>' for r in data["references"])
    return f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>디자인 비교 · {esc(data['run_id'])}</title><link rel="stylesheet" href="board.css"><script defer src="board.js"></script></head>
<body><header><p class="eyebrow">DESIGN KIT / STUDY</p><h1>{esc(heading)}</h1><p class="theme">{esc(data['theme'])}</p>
<p id="run-status" role="status">{esc(notice)}</p><p class="muted">{'선택과 피드백은 이 실행에 저장됩니다.' if online else '파일 보기 모드입니다. 다운로드한 선택 기록을 하네스에 가져와야 저장됩니다.'}</p></header>
<main><nav class="scene-controls" aria-label="비교 조건"><label for="scene">같이 볼 화면</label><select id="scene" name="scene"></select>
<label for="scale">표시 배율</label><select id="scale" name="scale"><option value="fit">화면에 맞춤</option><option value="1">원래 크기</option><option value="1.5">150%</option></select></nav>
<p class="muted">동일한 내용과 행동을 담은 정적 시안입니다. 이미지를 눌러 확대할 수 있습니다.</p><section id="gallery" class="gallery" aria-label="시안 나란히 비교"></section>
{choice_form}<ul class="error" id="presentation-errors">{issue_html}</ul>
<section class="feedback" aria-labelledby="feedback-title"><h2 id="feedback-title">마음에 든 점과 바꾸고 싶은 점</h2>
<form id="feedback" action="/event" method="post" aria-labelledby="feedback-title">
<input type="hidden" name="versions" value="{versions}"><input type="hidden" name="csrf" value="{esc(csrf)}"><input type="hidden" name="snapshot" value="{esc(data['snapshot'])}"><input type="hidden" name="kind" value="feedback">
<input type="hidden" name="screen" id="feedback-screen"><label for="feedback-candidate">시안</label><select id="feedback-candidate" name="candidate_id">{options}</select>
<label for="feedback-intent">요청 종류</label><select id="feedback-intent" name="classification">
<option value="untriaged">의견 남기기</option><option value="change_request">수정 요청</option><option value="rejection">부적합 · 다시 검토</option><option value="diagnosis_only">원인 조사 요청 · 제작 중지</option><option value="preference">질문 · 취향 메모</option></select>
<label for="feedback-text">의견 (필수)</label><textarea id="feedback-text" name="text" rows="4" maxlength="4000" required placeholder="예: 빛은 좋지만 조금 더 따뜻했으면 좋겠어요."></textarea>
<button type="submit">{'피드백 저장' if online else '피드백 기록 다운로드'}</button><p id="feedback-status" role="status"></p></form></section>
<details><summary>이전·거절·참조 제시본</summary><ul>{history_html}</ul></details>
<details><summary>참고한 작품과 적용한 원리</summary><ul class="references">{reference_items}</ul></details>
<noscript><p>화면 전환·확대에는 JavaScript가 필요합니다. 온라인 모드에서는 아래 폼 제출로 선택과 의견을 저장할 수 있습니다.</p></noscript>
</main><dialog id="zoom" aria-labelledby="zoom-title"><form method="dialog"><button autofocus>닫기</button></form><h2 id="zoom-title">시안 확대</h2><img id="zoom-image" alt=""></dialog>
<script id="board-data" type="application/json">{encoded}</script></body></html>'''


def export_board(run: DesignRun, destination: Path):
    allowed_root = (run.ctx.code_root / "designs").resolve()
    if not destination.resolve().is_relative_to(allowed_root):
        raise DesignError("Export board must be in the project's designs/ directory")
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "images").mkdir(exist_ok=True)
    data, assets = board_data(run)
    for name, path in assets.items():
        shutil.copy2(path, destination / "images" / name)
    for name in ("board.css", "board.js"):
        shutil.copy2(ASSET_DIR / name, destination / name)
    (destination / "index.html").write_text(board_html(data), encoding="utf-8")
    return destination / "index.html"


class BoardServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, run: DesignRun, port=0):
        self.run, self.csrf = run, secrets.token_urlsafe(32)
        super().__init__(("127.0.0.1", port), BoardHandler)
        self.origin = f"http://127.0.0.1:{self.server_port}"


class BoardHandler(BaseHTTPRequestHandler):
    server: BoardServer

    def log_message(self, format, *args):
        pass  # Feedback and local authorization tokens do not belong in server logs.

    def respond(self, status, data, mime="application/json; charset=utf-8"):
        body = data.encode() if isinstance(data, str) else data
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(body)

    def host_allowed(self):
        return self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"

    def do_GET(self):
        if not self.host_allowed():
            self.respond(403, '{"error":"Invalid local host"}')
            return
        try:
            path = urlparse(self.path).path
            if path == "/":
                data, _ = board_data(self.server.run)
                self.respond(200, board_html(data, csrf=self.server.csrf, online=True), "text/html; charset=utf-8")
            elif path in ("/board.js", "/board.css"):
                self.respond(200, (ASSET_DIR / path[1:]).read_bytes(), "text/javascript; charset=utf-8" if path.endswith(".js") else "text/css; charset=utf-8")
            elif path == "/status":
                data, _ = board_data(self.server.run)
                self.respond(200, json.dumps(data, ensure_ascii=False))
            elif path.startswith("/images/"):
                _, assets = board_data(self.server.run)
                name = path.removeprefix("/images/")
                if name not in assets:
                    raise DesignError("Unknown preview")
                self.respond(200, assets[name].read_bytes(), mimetypes.guess_type(assets[name].name)[0] or "text/plain")
            else:
                self.respond(404, '{"error":"Not found"}')
        except (DesignError, OSError, KeyError, ValueError) as exc:
            self.respond(409, json.dumps({"error": str(exc)}, ensure_ascii=False))

    def do_POST(self):
        if not self.host_allowed() or self.path != "/event" or self.headers.get("Origin") != self.server.origin:
            self.respond(403, '{"error":"Only this local comparison board may submit"}')
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 16384:
                raise DesignError("Invalid event size")
            raw = self.rfile.read(length)
            is_json = self.headers.get("Content-Type", "").startswith("application/json")
            form = json.loads(raw) if is_json else {k: values[0] for k, values in parse_qs(raw.decode()).items()}
            if not isinstance(form, dict) or not isinstance(form.get("csrf"), str) or not secrets.compare_digest(form["csrf"], self.server.csrf):
                self.respond(403, '{"error":"Invalid form token"}')
                return
            if form.get("kind") not in ("direction", "final", "feedback"):
                raise DesignError("Unsupported board action")
            manifest = self.server.run.manifest()
            cid = form.get("candidate_id")
            candidate = next((c for c in manifest["candidates"] if c["id"] == cid), None)
            if not candidate and (form["kind"] != "feedback" or cid):
                raise DesignError("Unknown candidate")
            version = form.get('version')
            if version is None and form.get('versions'):
                version = json.loads(form['versions']).get(cid)
            if version is None and candidate:
                if form.get('snapshot') != self.server.run.status()['current_snapshot']:
                    raise DesignError('Older board must provide its observed candidate version')
                version = candidate['version']
            payload = {"id": form.get("id") or secrets.token_hex(16), "kind": form["kind"],
                       "snapshot": form.get("snapshot"), "candidate_id": cid or None, "version": version if candidate else None,
                       "actor": "user", "authority": "Explicit submit in the local comparison board",
                       "reason": str(form.get("reason", ""))[:4000]}
            if form["kind"] == "feedback":
                payload["classification"] = form.get("classification", "untriaged")
                payload["text"] = str(form.get("text", ""))[:4000]
                if form.get("screen"):
                    payload["screen"] = form["screen"]
            state = self.server.run.submit(payload)
            if is_json:
                self.respond(200, json.dumps({"ok": True, "phase": state["phase"], "event_id": payload["id"]}))
            else:
                self.send_response(303)
                self.send_header("Location", "/")
                self.end_headers()
        except (DesignError, OSError, KeyError, TypeError, ValueError) as exc:
            self.respond(409, json.dumps({"error": str(exc)}, ensure_ascii=False))
