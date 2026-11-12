"""File/coverage contracts for design runs. This does not grade creative quality."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import re
from urllib.parse import urlparse

from .context import ProjectContext

ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,99}$")


class DesignError(ValueError):
    """An incomplete, stale or invalid design contract."""


def canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"), parse_constant=lambda s: _invalid(s))
    except (OSError, UnicodeError, ValueError) as exc:
        raise DesignError(f"Cannot read JSON {path}: {exc}") from exc


def _invalid(value):
    raise DesignError(f"Non-finite JSON number: {value}")


def text(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def number(value, *, positive=False) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and (not positive or value > 0)


def safe_path(ctx: ProjectContext, rel: str) -> Path:
    if not isinstance(rel, str) or not rel.startswith(("docs/", "designs/")):
        raise DesignError(f"Expected docs/ or designs/ path: {rel!r}")
    root = ctx.docs_root / "docs" if rel.startswith("docs/") else ctx.code_root / "designs"
    path = ctx.resolve(rel).resolve()
    if not path.is_relative_to(root.resolve()):
        raise DesignError(f"Path escapes its root: {rel}")
    return path


def file_ref(ctx: ProjectContext, rel: str) -> dict:
    path = safe_path(ctx, rel)
    if not path.is_file() or path.stat().st_size == 0:
        raise DesignError(f"Missing or empty file: {rel}")
    if path.suffix.lower() == ".pen":
        # Opaque format: never decode or inspect it. The MCP readback is separately pinned.
        st = path.stat()
        return {"path": rel, "opaque": True, "size": st.st_size, "mtime_ns": st.st_mtime_ns}
    return {"path": rel, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def refs_in(value):
    if isinstance(value, dict):
        if "path" in value:
            yield value
        for k, child in value.items():
            if k != "path":
                yield from refs_in(child)
    elif isinstance(value, list):
        for child in value:
            yield from refs_in(child)


def fingerprint(manifest: dict, ctx: ProjectContext) -> str:
    """Include observed file identities, so editing files without updating JSON is stale too."""
    inventory = []
    for ref in refs_in(manifest):
        try:
            inventory.append(file_ref(ctx, ref.get("path")))
        except (DesignError, OSError) as exc:
            inventory.append({"path": ref.get("path"), "error": str(exc)})
    return digest({"manifest": manifest, "actual_files": inventory})


def direction_fingerprint(manifest: dict, candidate_id: str) -> str:
    candidate = next((c for c in manifest.get("candidates", []) if c.get("id") == candidate_id), None)
    if not candidate:
        return ""
    return digest({"sources": manifest.get("sources"), "theme": manifest.get("theme"),
                   "content": manifest.get("content"), "direction": candidate.get("direction"),
                   "concept": candidate.get("concept"), "references": candidate.get("reference_ids"),
                   "signature_features": candidate.get("signature_features")})


def cell(frame: dict) -> tuple:
    return (frame.get("screen"), frame.get("state"), frame.get("viewport"))


def validate_contract(manifest: dict, ctx: ProjectContext, *, stage="comparison", candidate_id=None) -> dict:
    errors = []
    metrics = {"requirements": 0, "screens": 0, "references": 0, "candidates": 0,
               "expected_frames": 0, "delivered_frames": 0, "files": 0}

    def check(condition, message):
        if not condition:
            errors.append(message)
        return condition

    def rows(value, label, *, empty=False):
        if not check(isinstance(value, list) and (empty or bool(value)) and
                     all(isinstance(x, dict) for x in value), f"{label}: expected object array"):
            return []
        return value

    def strings(value, label, *, empty=False):
        if not check(isinstance(value, list) and (empty or bool(value)) and
                     all(text(x) for x in value), f"{label}: expected string array"):
            return []
        check(len(value) == len(set(value)), f"{label}: duplicate values")
        return value

    def index(value, label, *, empty=False):
        result = {}
        for row in rows(value, label, empty=empty):
            ident = row.get("id")
            if check(isinstance(ident, str) and ID.fullmatch(ident) is not None and ident not in result,
                     f"{label}: invalid/duplicate id {ident!r}"):
                result[ident] = row
        return result

    def pin(value, label):
        if not check(isinstance(value, dict) and "path" in value, f"{label}: missing file reference"):
            return None
        try:
            actual = file_ref(ctx, value["path"])
            metrics["files"] += 1
            check(actual == value, f"{label}: file identity changed: {value['path']}")
            return safe_path(ctx, value["path"])
        except (DesignError, OSError) as exc:
            errors.append(f"{label}: {exc}")
            return None

    def result():
        return {"ok": not errors, "kind": "contract_only", "errors": errors, "metrics": metrics}

    if not check(isinstance(manifest, dict), "Manifest must be an object"):
        return result()
    check(type(manifest.get("schema_version")) is int and manifest["schema_version"] in (1, 2), "schema_version must be 1 or 2")
    check(isinstance(manifest.get("run_id"), str) and ID.fullmatch(manifest["run_id"]) is not None, "Invalid run_id")
    check(stage in ("comparison", "final"), "Invalid validation stage")
    check(manifest.get("scope") in ("ui", "non_ui"), "scope must be ui or non_ui")
    source_paths = []
    for source in rows(manifest.get("sources"), "sources"):
        pin(source, "source")
        source_paths.append(source.get("path"))
    check(len(source_paths) == len(set(str(x) for x in source_paths)), "Duplicate sources")
    pin(manifest.get("brief"), "brief")
    if manifest.get("scope") == "non_ui":
        check(text(manifest.get("reason")), "non_ui requires a source-related reason")
        return result()
    if manifest.get('schema_version') == 2:
        review_paths = {f"docs/design-harness/{manifest.get('run_id')}/{name}" for name in ('comparison-review.json','review.json')}
        check(not any(ref.get('path') in review_paths for ref in refs_in(manifest)), 'Review JSON must stay outside its own artifact fingerprint')
        errors.extend(presentation_errors(manifest, ctx))
        for reference in rows(manifest.get('references'), 'references'):
            if not isinstance(reference, dict): continue
            check(reference.get('role') in ('primary_layout', 'supporting_visual'), 'Reference needs an explicit usage role')
            check(all(text(reference.get(k)) for k in ('scene', 'task', 'apply_to', 'exclude')), 'Reference needs scene/task/application boundaries')
            if reference.get('preview') is not None: pin(reference['preview'], 'reference.preview')
    theme = manifest.get("theme")
    if check(isinstance(theme, dict), "theme must be an object"):
        check(text(theme.get("requested")) and text(theme.get("interpretation")), "Missing requested theme or interpretation")
        strings(theme.get("avoid"), "theme.avoid", empty=True)
    content_file = pin(manifest.get("content"), "content")
    content = {}
    if content_file:
        if not check(content_file.suffix == ".json", "content must reference JSON"):
            content_file = None
    if content_file:
        try:
            raw = read_json(content_file)
            if check(isinstance(raw, dict) and bool(raw) and all(text(k) and text(v) for k, v in raw.items()),
                     "content: expected ID to nonempty text map"):
                content = raw
        except DesignError as exc:
            errors.append(str(exc))
    views = index(manifest.get("viewports"), "viewports")
    for v in views.values():
        check(number(v.get("width"), positive=True) and number(v.get("height"), positive=True), "Invalid viewport size")
    screens = index(manifest.get("screens"), "screens")
    metrics["screens"] = len(screens)
    full_cells = set()
    actions_by_screen = {}
    content_by_screen = {}
    for ident, screen in screens.items():
        states = strings(screen.get("states"), f"{ident}.states")
        viewport_ids = strings(screen.get("viewports"), f"{ident}.viewports")
        for v in viewport_ids:
            check(v in views, f"Unknown viewport: {v}")
        full_cells.update((ident, s, v) for s in states for v in viewport_ids)
        actions = index(screen.get("actions"), f"{ident}.actions")
        for a in actions.values():
            check(a.get("target") in list(screens) + ["@back", "@complete", "@external"], f"Invalid action target: {a.get('target')}")
            if "states" in a:
                a = dict(a)
                a["states"] = strings(a["states"], "action.states")
                actions[a["id"]] = a
                check(set(a["states"]) <= set(states), "Unknown action state")
        actions_by_screen[ident] = actions
        content_ids = strings(screen.get("content"), f"{ident}.content")
        for c in content_ids:
            check(c in content, f"Unknown content: {c}")
        state_content = screen.get("state_content", {})
        if not check(isinstance(state_content, dict), "state_content must be an object"):
            state_content = {}
        parsed_state_content = {}
        for state, values in state_content.items():
            check(state in states, "Unknown content state")
            parsed_state_content[state] = strings(values, "state_content values", empty=True)
            for c in parsed_state_content[state]:
                check(c in content, f"Unknown state content: {c}")
        for state in states:
            content_by_screen[(ident, state)] = content_ids + parsed_state_content.get(state, [])
    requirements = index(manifest.get("requirements"), "requirements")
    metrics["requirements"] = len(requirements)
    covered_screens = set()
    for r in requirements.values():
        if "screen_ids" in r:
            check("exclusion_reason" not in r, "Requirement cannot be both mapped and excluded")
            for ident in strings(r["screen_ids"], "requirement.screen_ids"):
                check(ident in screens, f"Unknown requirement screen: {ident}")
                covered_screens.add(ident)
        else:
            check(text(r.get("exclusion_reason")), "Unmapped requirement lacks exclusion reason")
    check(set(screens) <= covered_screens, "Screen without requirement mapping")
    comparison = set()
    for item in rows(manifest.get("comparison"), "comparison"):
        key = cell(item)
        if not all(text(k) for k in key):
            errors.append("Invalid comparison cell")
            continue
        check(key in full_cells and key not in comparison, f"Unknown/duplicate comparison cell: {key}")
        comparison.add(key)
    references = index(manifest.get("references"), "references")
    metrics["references"] = len(references)
    observed_urls = set()
    for ref in references.values():
        check(ref.get("access_status", "observed") == "observed", "Unobserved/failed reference cannot support a candidate")
        url = ref.get("url")
        valid_url = isinstance(url, str) and urlparse(url).scheme in ("http", "https") and bool(urlparse(url).netloc)
        check(valid_url, "Reference missing source URL")
        if valid_url:
            check(url not in observed_urls, "Duplicate reference URL")
            observed_urls.add(url)
        check(text(ref.get("observed_at")), "Reference has no actual observation time")
        pin(ref.get("observation"), "reference observation")
        analysis = ref.get("analysis")
        if check(isinstance(analysis, dict), "Reference has no visual analysis"):
            for key in ("composition", "typography", "color_light", "texture", "product_translation"):
                check(text(analysis.get(key)), f"Reference analysis missing {key}")
        check(text(ref.get("adopt")) and text(ref.get("avoid")), "Reference must explain adoption and exclusions")
    candidates = index(manifest.get("candidates"), "candidates")
    metrics["candidates"] = len(candidates)
    if stage == "final":
        check(candidate_id in candidates, "Final validation requires a known selected candidate")
    frame_ids = set()
    used_nodes = set()
    for ident, candidate in candidates.items():
        check(type(candidate.get("version")) is int and candidate["version"] > 0, "Candidate version must be positive integer")
        check(text(candidate.get("title")) and text(candidate.get("concept")), "Missing candidate title/concept")
        pin(candidate.get("direction"), "art direction")
        if "board" in candidate:
            pin(candidate["board"], "art direction preview")
        for asset in rows(candidate.get("assets"), "candidate.assets", empty=True):
            pin(asset, "candidate asset")
        for rid in strings(candidate.get("reference_ids"), "candidate.reference_ids"):
            check(rid in references, f"Unknown reference: {rid}")
        signatures = index(candidate.get("signature_features"), "signature_features")
        for signature in signatures.values():
            check(text(signature.get("description")), "Missing signature description")
        frames = rows(candidate.get("frames"), f"{ident}.frames")
        keys = set()
        applied_signatures = set()
        for frame in frames:
            fid = frame.get("id")
            if not check(isinstance(fid, str) and ID.fullmatch(fid) is not None and fid not in frame_ids,
                         "Invalid/duplicate global frame id"):
                continue
            frame_ids.add(fid)
            key = cell(frame)
            if not all(text(k) for k in key):
                errors.append(f"Invalid frame cell: {fid}")
                continue
            check(key in full_cells and key not in keys, f"Unknown/duplicate frame cell: {key}")
            keys.add(key)
            for name in ("source", "preview", "readback"):
                file = pin(frame.get(name), f"{fid}.{name}")
                if file and name == "readback":
                    check(file.suffix == ".json", "readback must reference MCP/renderer JSON, never .pen")
                if file and name == "preview":
                    check(file.suffix.lower() == ".png", "preview must be a PNG export")
            if stage == "final" and ident == candidate_id:
                file = pin(frame.get("font_observation"), f"{fid}.font_observation")
                if file:
                    check(file.suffix == ".json", "font_observation must be JSON")
            node = frame.get("node_id")
            check(text(node), f"{fid}: missing actual frame node")
            node_key = (str(frame.get("source", {}).get("path")), str(node)) if isinstance(frame.get("source"), dict) else ("", str(node))
            check(node_key not in used_nodes, f"{fid}: same source node reused across states")
            used_nodes.add(node_key)
            expected_actions = {a for a, details in actions_by_screen.get(key[0], {}).items()
                                if "states" not in details or key[1] in details["states"]}
            for field, expected in (("content_nodes", content_by_screen.get((key[0], key[1]), [])),
                                    ("action_nodes", expected_actions)):
                mapping = frame.get(field)
                if check(isinstance(mapping, dict) and all(text(k) and text(v) for k, v in mapping.items()), f"{fid}: invalid {field}"):
                    check(set(mapping) == set(expected), f"{fid}: inconsistent {field} coverage")
            mapping = frame.get("signature_nodes")
            if check(isinstance(mapping, dict) and all(text(k) and text(v) for k, v in mapping.items()), f"{fid}: invalid signature_nodes"):
                check(set(mapping) <= set(signatures), f"{fid}: unknown signature")
                applied_signatures.update(mapping)
            rows(frame.get("allowed_overlaps", []), f"{fid}.allowed_overlaps", empty=True)
        check(set(signatures) <= applied_signatures, f"{ident}: missing signature application")
        expected_cells = full_cells if stage == "final" and ident == candidate_id else comparison
        check(expected_cells <= keys, f"{ident}: missing required screen/state/viewport")
        if stage == "comparison" or ident == candidate_id:
            metrics["expected_frames"] += len(expected_cells)
            metrics["delivered_frames"] += len(expected_cells & keys)
    return result()


def presentation_errors(manifest, ctx):
    """Bind presented current frames to registered candidate/version/source/preview."""
    if manifest.get('scope') == 'non_ui': return []
    entries = manifest.get('presentation')
    if not isinstance(entries, list) or not entries or any(not isinstance(e,dict) for e in entries):
        return ['Presentation registry is missing; drafts may be viewed but not selected']
    errors, current, ids = [], set(), set()
    candidates = manifest.get('candidates')
    if not isinstance(candidates,list) or any(not isinstance(c,dict) or not isinstance(c.get('frames'),list) or
        any(not isinstance(f,dict) or not text(f.get('id')) for f in c['frames']) for c in candidates):
        return ['Presentation needs valid candidate frames']
    expected = {(c.get('id'), f['id']): (c, f) for c in candidates for f in c['frames']}
    for e in entries:
        ident=e.get('id'); role=e.get('role')
        if not text(ident) or ident in ids: errors.append('Presentation needs unique IDs')
        ids.add(str(ident))
        if role not in ('current','previous','reference','rejected'): errors.append('Unknown presentation role')
        for field in ('source','preview'):
            try:
                if file_ref(ctx, e.get(field,{}).get('path')) != e.get(field): errors.append('Presentation file identity changed')
            except (DesignError, OSError, AttributeError) as exc: errors.append(str(exc))
        if not text(e.get('node_id')): errors.append('Presentation needs actual source frame node')
        if role == 'current':
            key=(e.get('candidate_id'),e.get('frame_id'))
            if key not in expected: errors.append('Presentation refers to an unknown current frame');continue
            c,f=expected[key]
            if key in current: errors.append('Duplicate current presentation frame')
            current.add(key)
            if e.get('version') != c['version'] or any(e.get(k) != f.get(k) for k in ('node_id','source','preview')):
                errors.append('Presentation candidate/frame/preview version mismatch')
    if current != set(expected): errors.append('Current presentation does not cover registered frames')
    return errors
