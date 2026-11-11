"""Synthetic fixture with independently known pixels and rendered rectangles."""

import copy
import json
from pathlib import Path
import struct
import zlib

from design_kit.context import ProjectContext
from design_kit.design_contract import file_ref
from design_kit.design_runs import DesignRun, atomic_json


def png(path, width, height, text_rgb=(17, 17, 17)):
    pixels = bytearray([255, 255, 255] * width * height)
    for y in range(100, min(144, height)):
        for x in range(20, min(140, width)):
            pixels[(y * width + x) * 3:(y * width + x) * 3 + 3] = bytes((17,17,17))
    for x, y, color in ((21,31,text_rgb), (31,111,(255,255,255))):
        pixels[(y * width + x) * 3:(y * width + x) * 3 + 3] = bytes(color)
    raw = b"".join(b"\0" + pixels[y * width * 3:(y+1) * width * 3] for y in range(height))
    def chunk(kind, body):
        return struct.pack(">I",len(body))+kind+body+struct.pack(">I",zlib.crc32(kind+body)&0xffffffff)
    path.write_bytes(b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",struct.pack(">IIBBBBB",width,height,8,2,0,0,0))+
                     chunk(b"IDAT",zlib.compress(raw))+chunk(b"IEND",b""))


def build(tmp_path):
    ctx = ProjectContext("test", tmp_path / "code", tmp_path / "hub")
    for p in (ctx.code_root / "designs", ctx.docs_root / "docs/design-harness/test"):
        p.mkdir(parents=True)
    def save(rel, value):
        path = ctx.resolve(rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(value, (dict,list)):
            atomic_json(path,value)
        else:
            path.write_text(value)
        return file_ref(ctx,rel)
    sources = [save("docs/prd.md", "실제 과업: 가게 이름을 읽고 입고 소식을 제보한다.")]
    brief = save("docs/design-harness/test/brief.md", "합성 렌더 fixture. 미적 품질/실제 폰트 테스트가 아님.")
    content = save("docs/design-harness/test/content.json", {"title":"달빛 가게", "report":"입고 제보"})
    observation_ref = save("docs/design-harness/test/ref.md", "Known synthetic source observation; composition and light analyzed.")
    manifest = {"schema_version":1,"run_id":"test","scope":"ui","sources":sources,"brief":brief,
                "theme":{"requested":"몽환적","interpretation":"고요한 밤의 가게","avoid":[]}, "content":content,
                "requirements":[{"id":"FR-1","screen_ids":["detail"]}],
                "screens":[{"id":"detail","states":["default"],"viewports":["mobile"],"content":["title","report"],
                            "actions":[{"id":"report","target":"@complete"}]}],
                "viewports":[{"id":"mobile","width":390,"height":844}],
                "comparison":[{"screen":"detail","state":"default","viewport":"mobile"}],
                "references":[{"id":"ref-1","url":"https://example.com/reference","observed_at":"2026-11-10T00:00:00Z",
                               "observation":observation_ref,"analysis":{k:"synthetic known observation" for k in
                               ("composition","typography","color_light","texture","product_translation")},
                               "adopt":"quiet depth","avoid":"copying the original composition"}], "candidates":[]}
    for cid in ("a", "b"):
        source = save(f"designs/{cid}.svg", f'<svg xmlns="http://www.w3.org/2000/svg"><g id="{cid}-root"/></svg>')
        observation = {"renderer":"synthetic-ground-truth", "captured_at":"2026-11-10T00:00:00Z", "saved_reopened":True,"nodes":[
            {"id":f"{cid}-root","parent":None,"type":"frame","name":"Screen","fill":"#ffffff","bounds":{"x":0,"y":0,"width":390,"height":844}},
            {"id":f"{cid}-title","parent":f"{cid}-root","type":"text","name":"Title","fill":"#111111","content":"달빛 가게","bounds":{"x":20,"y":30,"width":300,"height":20}},
            {"id":f"{cid}-button","parent":f"{cid}-root","type":"frame","name":"Report","fill":"#111111","bounds":{"x":20,"y":100,"width":120,"height":44}},
            {"id":f"{cid}-label","parent":f"{cid}-button","type":"text","name":"Label","fill":"#ffffff","content":"입고 제보","bounds":{"x":10,"y":10,"width":100,"height":20}}
        ]}
        png(ctx.resolve(f"designs/{cid}.png"),390,844)
        preview=file_ref(ctx,f"designs/{cid}.png")
        observation["artifacts"]={f"{cid}-root":{"source":source,"preview":preview}}
        readback = save(f"docs/design-harness/test/{cid}-readback.json",observation)
        fonts = save(f"docs/design-harness/test/{cid}-fonts.json", {
            "renderer":"synthetic-ground-truth", "captured_at":"2026-11-10T00:00:00Z",
            "source":source, "preview":preview,
            "runs":[{"node":f"{cid}-{suffix}","actual_font":"Known synthetic fixture font",
                     "glyph_count":5,"missing_glyphs":0,"method":"synthetic-ground-truth"}
                    for suffix in ("title","label")]})
        direction=save(f"docs/design-harness/test/{cid}-direction.md",f"Art direction {cid}: distinct composition.")
        manifest["candidates"].append({"id":cid,"version":1,"title":cid,"concept":f"Concept {cid}","direction":direction,
            "reference_ids":["ref-1"],"assets":[],"signature_features":[{"id":"quiet","description":"Quiet editorial title"}],
            "frames":[{"id":f"{cid}-default","screen":"detail","state":"default","viewport":"mobile", "source":source,
            "node_id":f"{cid}-root","preview":preview,"readback":readback,"font_observation":fonts,
            "content_nodes":{"title":f"{cid}-title","report":f"{cid}-label"}, "action_nodes":{"report":f"{cid}-button"},
            "signature_nodes":{"quiet":f"{cid}-title"},"allowed_overlaps":[]}]})
    return ctx,manifest


def update_observation(ctx, manifest, mutator, candidate=0):
    frame=manifest["candidates"][candidate]["frames"][0]
    path=ctx.resolve(frame["readback"]["path"])
    data=json.loads(path.read_text())
    mutator(data)
    atomic_json(path,data)
    frame["readback"]=file_ref(ctx,frame["readback"]["path"])


def start(ctx,manifest):
    run=DesignRun(ctx,"test")
    run.initialize(manifest)
    run.refresh("Initial source review and synthetic fixture preparation")
    assert run.prepare()["ok"]
    return run


def event(run,kind="direction",**overrides):
    return {"id":f"{kind}-1","kind":kind,"candidate_id":"a","version":1,"snapshot":run.status()["current_snapshot"],
            "actor":"user","authority":"Synthetic fixture user event; never a real user decision", "reason":"fixture",**overrides}


def review(run):
    evidence=run.directory/"independent.md"
    evidence.write_text("Synthetic independent review fixture; not a real independent review.")
    atomic_json(run.directory/"review.json",{"snapshot":run.status()["current_snapshot"],"candidate_id":"a",
        "reviewer_id":"reviewer","producer_id":"producer","independent":True,"verdict":"pass","unresolved":[],
        "evidence":file_ref(run.ctx,f"{run.rel}/independent.md")})
