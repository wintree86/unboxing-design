"""Deterministic measurements from rendered observations and exported PNG pixels.

No renderer settings are reported as actual glyph, device or usability measurements.
The PNG reader intentionally accepts only non-interlaced 8-bit RGB/RGBA exports.
"""

from __future__ import annotations

from collections import defaultdict
from itertools import combinations
import math
from pathlib import Path
import struct
import zlib

from .context import ProjectContext
from .design_contract import DesignError, cell, fingerprint, number, read_json, safe_path, validate_contract

PROFILE = {"id": "static-mobile-v1", "minimum_action_size": 44,
           "minimum_text_contrast": 4.5, "max_automatic_revisions": 2}


class PNG:
    def __init__(self, path: Path):
        data = path.read_bytes()
        if data[:8] != b"\x89PNG\r\n\x1a\n":
            raise DesignError("Expected a PNG preview")
        offset, compressed, header = 8, bytearray(), None
        while offset < len(data):
            if offset + 12 > len(data):
                raise DesignError("Truncated PNG chunk")
            length = struct.unpack(">I", data[offset:offset + 4])[0]
            kind = data[offset + 4:offset + 8]
            body = data[offset + 8:offset + 8 + length]
            if offset + length + 12 > len(data):
                raise DesignError("Truncated PNG data")
            crc = struct.unpack(">I", data[offset + 8 + length:offset + 12 + length])[0]
            if zlib.crc32(kind + body) & 0xffffffff != crc:
                raise DesignError("PNG CRC mismatch")
            if kind == b"IHDR":
                header = struct.unpack(">IIBBBBB", body)
            elif kind == b"IDAT":
                compressed.extend(body)
            elif kind == b"IEND":
                break
            offset += length + 12
        if not header:
            raise DesignError("PNG has no header")
        self.width, self.height, bits, color, compression, filtering, interlace = header
        if (bits != 8 or color not in (2, 6) or compression or filtering or interlace or
                not 0 < self.width * self.height <= 20_000_000):
            raise DesignError("PNG preview needs non-interlaced 8-bit RGB/RGBA, <=20M pixels")
        channels = 3 if color == 2 else 4
        stride = self.width * channels
        expected = (stride + 1) * self.height
        dec = zlib.decompressobj()
        raw = dec.decompress(compressed, expected + 1)
        if len(raw) != expected or not dec.eof:
            raise DesignError("PNG decompressed size mismatch")
        self.channels = channels
        self.pixels = bytearray(stride * self.height)
        for y in range(self.height):
            filter_type = raw[y * (stride + 1)]
            if filter_type not in range(5):
                raise DesignError("Unknown PNG filter")
            row = raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)]
            base = y * stride
            for x, v in enumerate(row):
                a = self.pixels[base + x - channels] if x >= channels else 0
                b = self.pixels[base + x - stride] if y else 0
                c = self.pixels[base + x - stride - channels] if y and x >= channels else 0
                if filter_type == 1:
                    v += a
                elif filter_type == 2:
                    v += b
                elif filter_type == 3:
                    v += (a + b) // 2
                elif filter_type == 4:
                    p = a + b - c
                    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                    v += a if pa <= pb and pa <= pc else b if pb <= pc else c
                self.pixels[base + x] = v & 255

    def rgb(self, x: int, y: int):
        i = (y * self.width + x) * self.channels
        if self.channels == 4 and self.pixels[i + 3] != 255:
            return None
        return tuple(self.pixels[i:i + 3])


def rgb(value):
    if not isinstance(value, str) or not value.startswith("#"):
        return None
    value = value[1:]
    if len(value) == 3:
        value = "".join(c * 2 for c in value)
    if len(value) == 8 and value[-2:].lower() == "ff":
        value = value[:6]
    if len(value) != 6:
        return None
    try:
        return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return None


def solid(fill):
    if isinstance(fill, list):
        visible = [f for f in fill if not isinstance(f, dict) or f.get("enabled", True)]
        return solid(visible[0]) if len(visible) == 1 else None
    if isinstance(fill, dict):
        return rgb(fill.get("color")) if fill.get("type") == "color" and fill.get("enabled", True) else None
    return rgb(fill)


def contrast(a, b):
    def luminance(color):
        components = [v / 255 for v in color]
        linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in components]
        return sum(w * v for w, v in zip((0.2126, 0.7152, 0.0722), linear))
    la, lb = luminance(a), luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def intersects(a, b):
    return min(a[0] + a[2], b[0] + b[2]) > max(a[0], b[0]) and min(a[1] + a[3], b[1] + b[3]) > max(a[1], b[1])


def frame_measure(frame, view, content, ctx, *, assets=(), final=False):
    errors, contrast_samples = [], []
    observation = read_json(safe_path(ctx, frame["readback"]["path"]))
    if not isinstance(observation, dict) or not isinstance(observation.get("nodes"), list):
        raise DesignError("Malformed rendered observation")
    if not observation.get("renderer") or not observation.get("captured_at"):
        errors.append("Observation missing renderer/time")
    if observation.get("saved_reopened") is not True:
        errors.append("Saved source was not reopened and observed")
    all_nodes = {}
    for n in observation["nodes"]:
        if not isinstance(n, dict) or not isinstance(n.get("id"), str) or n["id"] in all_nodes:
            raise DesignError("Invalid/duplicate observation node")
        all_nodes[n["id"]] = n
    root_id = frame["node_id"]
    if root_id not in all_nodes:
        raise DesignError("Frame node absent from saved readback")
    artifacts = observation.get("artifacts", {})
    if (not isinstance(artifacts, dict) or artifacts.get(root_id) !=
            {"source": frame["source"], "preview": frame["preview"]}):
        errors.append("Observation is not bound to this saved source and exported preview")
    nodes, abs_bounds = {}, {}

    def visit(ident, trail=()):
        if ident in trail:
            raise DesignError("Observation parent cycle")
        node = all_nodes[ident]
        b = node.get("bounds")
        if not isinstance(b, dict) or not all(number(b.get(k)) for k in ("x", "y", "width", "height")):
            raise DesignError("Missing/non-finite rendered bounds")
        if ident == root_id:
            bounds = (0, 0, b["width"], b["height"])
        else:
            parent = node.get("parent")
            if not isinstance(parent, str) or parent not in all_nodes:
                return None
            parent_bounds = visit(parent, trail + (ident,))
            if parent_bounds is None:
                return None
            bounds = (parent_bounds[0] + b["x"], parent_bounds[1] + b["y"], b["width"], b["height"])
        nodes[ident], abs_bounds[ident] = node, bounds
        return bounds

    for ident in all_nodes:
        visit(ident)
    known_assets = {safe_path(ctx, a["path"]) for a in assets}
    for node in nodes.values():
        fills = node.get("fill", [])
        for fill in fills if isinstance(fills, list) else [fills]:
            if not isinstance(fill, dict) or fill.get("type") != "image" or not fill.get("enabled", True):
                continue
            url = fill.get("url")
            if (not isinstance(url, str) or not url or ":" in url or
                    (safe_path(ctx, frame["source"]["path"]).parent / url).resolve() not in known_assets):
                errors.append(f"Image asset is not a pinned local source: {node['id']}")
    root = abs_bounds[root_id]
    if root[2:] != (view["width"], view["height"]):
        errors.append("Rendered frame dimensions do not match viewport")
    clipping, zero, groups = [], [], defaultdict(list)
    for ident, node in nodes.items():
        if abs_bounds[ident][2] <= 0 or abs_bounds[ident][3] <= 0:
            zero.append(ident)
        if node.get("problems"):
            clipping.append(ident)
        if ident != root_id:
            groups[node.get("parent")].append(ident)
            x, y, w, h = abs_bounds[ident]
            if x < 0 or y < 0 or x + w > root[2] or y + h > root[3]:
                if ident not in clipping:
                    clipping.append(ident)
    overlaps = {tuple(sorted((a, b))) for siblings in groups.values() for a, b in combinations(siblings, 2)
                if intersects(abs_bounds[a], abs_bounds[b])}
    allowed = set()
    for exception in frame.get("allowed_overlaps", []):
        pair = exception.get("nodes")
        if (not isinstance(pair, list) or len(pair) != 2 or not all(isinstance(x, str) for x in pair) or
                pair[0] == pair[1] or not isinstance(exception.get("reason"), str) or not exception["reason"].strip()):
            errors.append("Invalid intentional overlap exception")
            continue
        pair = tuple(sorted(pair))
        if pair not in overlaps or pair in allowed:
            errors.append("Unknown/duplicate intentional overlap exception")
        allowed.add(pair)
    unexpected_overlaps = sorted(overlaps - allowed)
    if clipping:
        errors.append(f"Clipped nodes: {clipping}")
    if zero:
        errors.append(f"Non-positive nodes: {zero}")
    if unexpected_overlaps:
        errors.append(f"Unintentional sibling overlaps: {unexpected_overlaps}")
    for content_id, ident in frame["content_nodes"].items():
        if ident not in nodes or nodes[ident].get("content") != content[content_id]:
            errors.append(f"Missing/wrong rendered content: {content_id}")
    action_sizes = {}
    for aid, ident in frame["action_nodes"].items():
        if ident not in nodes:
            errors.append(f"Action node absent: {aid}")
            continue
        w, h = abs_bounds[ident][2:]
        action_sizes[aid] = [w, h]
        if min(w, h) < PROFILE["minimum_action_size"]:
            errors.append(f"Action smaller than 44 design px: {aid}")
    for signature, ident in frame["signature_nodes"].items():
        if ident not in nodes:
            errors.append(f"Signature node absent: {signature}")
    png = PNG(safe_path(ctx, frame["preview"]["path"]))
    scale = png.width / view["width"]
    if scale <= 0 or png.height / view["height"] != scale:
        errors.append("Preview aspect ratio differs from rendered viewport")

    def background(ident):
        current = ident
        parent = nodes[ident].get("parent")
        while parent in nodes:
            if any(sibling != current and intersects(abs_bounds[sibling], abs_bounds[ident])
                   for sibling in groups[parent]):
                return None
            n = nodes[parent]
            if n.get("opacity", 1) != 1 or n.get("effect"):
                return None
            fill = n.get("fill")
            if fill:
                return solid(fill)
            current = parent
            parent = n.get("parent")
        return None

    for ident, node in nodes.items():
        if node.get("type") != "text" or not node.get("content"):
            continue
        fg, bg = solid(node.get("fill")), background(ident)
        sample = {"node": ident, "method": "exact_opaque_colors_observed_in_exported_png", "measured": False}
        if fg is not None and bg is not None and fg != bg and node.get("opacity", 1) == 1 and not node.get("effect"):
            x, y, w, h = abs_bounds[ident]
            found = {}
            for py in range(max(0, math.floor(y * scale)), min(png.height, math.ceil((y + h) * scale))):
                for px in range(max(0, math.floor(x * scale)), min(png.width, math.ceil((x + w) * scale))):
                    color = png.rgb(px, py)
                    if color in (fg, bg):
                        found.setdefault(color, [px, py])
                    if len(found) == 2:
                        break
                if len(found) == 2:
                    break
            if len(found) == 2:
                sample.update(measured=True, foreground=list(fg), background=list(bg),
                              foreground_pixel=found[fg], background_pixel=found[bg], ratio=contrast(fg, bg))
        if not sample["measured"]:
            errors.append(f"Text contrast unmeasured (requires opaque solid text/background pixels): {ident}")
        elif sample["ratio"] < PROFILE["minimum_text_contrast"]:
            errors.append(f"Text contrast below 4.5: {ident}")
        contrast_samples.append(sample)
    fonts_verified = False
    if final:
        font = read_json(safe_path(ctx, frame["font_observation"]["path"]))
        text_nodes = {n["id"] for n in nodes.values() if n.get("type") == "text" and n.get("content")}
        runs = font.get("runs", []) if isinstance(font, dict) else []
        if (not isinstance(font, dict) or not font.get("renderer") or not font.get("captured_at") or
                font.get("source") != frame["source"] or font.get("preview") != frame["preview"] or
                not isinstance(runs, list) or not all(isinstance(r, dict) for r in runs) or
                {r.get("node") for r in runs} != text_nodes or
                any(not r.get("actual_font") or not number(r.get("glyph_count"), positive=True) or
                    r.get("missing_glyphs") != 0 or r.get("method") not in ("renderer-glyph-run", "chromium-platform-fonts", "synthetic-ground-truth") or
                    (r.get("method") == "synthetic-ground-truth" and observation.get("renderer") != "synthetic-ground-truth") for r in runs)):
            errors.append("Actual font/glyph observation is missing, incomplete, or not bound to this render")
        else:
            fonts_verified = True
    return {"id": frame["id"], "ok": not errors, "errors": errors, "renderer": observation.get("renderer"),
            "nodes": len(nodes), "width": root[2], "height": root[3], "preview_size": [png.width, png.height],
            "clipped": clipping, "overlaps": unexpected_overlaps, "intentional_overlaps": len(allowed),
            "action_sizes": action_sizes, "text_contrast": contrast_samples,
            "unverified": ([] if fonts_verified else ["actual_font_files_and_glyphs"]) +
                          ["screen_reader", "device_interaction", "reflow", "image_background_contrast"]}


def measure_bundle(manifest, ctx: ProjectContext, *, stage="comparison", candidate_id=None):
    report = validate_contract(manifest, ctx, stage=stage, candidate_id=candidate_id)
    report.update(kind="recorded_render_and_png_pixels", stage=stage, candidate_id=candidate_id,
                  profile=PROFILE.copy(), frames=[], limitations=[
                      "Recorded observations must come from real tools; this verifier cannot authenticate their producer.",
                      "Static geometry and opaque-solid PNG pixel contrast only; not accessibility or usability certification.",
                      "Opaque .pen metadata plus MCP saved readback; re-read the source via MCP at final handoff."])
    if not report["ok"]:
        return report
    content = read_json(safe_path(ctx, manifest["content"]["path"])) if manifest["scope"] == "ui" else {}
    report["snapshot"] = fingerprint(manifest, ctx)
    if manifest["scope"] == "non_ui":
        return report
    views = {v["id"]: v for v in manifest["viewports"]}
    comparison = {cell(c) for c in manifest["comparison"]}
    for candidate in manifest["candidates"]:
        if stage == "final" and candidate["id"] != candidate_id:
            continue
        for frame in candidate["frames"]:
            if stage == "comparison" and cell(frame) not in comparison:
                continue
            try:
                measured = frame_measure(frame, views[frame["viewport"]], content, ctx,
                                         assets=candidate.get("assets", []), final=stage == "final")
                measured["candidate_id"] = candidate["id"]
                report["frames"].append(measured)
                report["errors"].extend(f"{frame['id']}: {error}" for error in measured["errors"])
            except (DesignError, OSError, ValueError, KeyError, TypeError, struct.error, zlib.error) as exc:
                report["errors"].append(f"{frame['id']}: {exc}")
    report["ok"] = not report["errors"]
    return report
