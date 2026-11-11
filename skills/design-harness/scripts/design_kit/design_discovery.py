"""Validate the reference-first handoff, not the aesthetic quality of its ideas."""

import hashlib
import json

from .context import ProjectContext

DISCOVERY_PATH = "docs/design-discovery/manifest.json"
COMPOSITION_FIELDS = ("first_focus", "grouping", "reading_flow", "image_role")


def validate_discovery(ctx: ProjectContext, *, expected_request_id: str | None = None) -> dict:
    errors = []
    metrics = {"required": 0, "provisional": 0, "references": 0, "hypotheses": 0}
    report = {"ok": False, "kind": "structural_only", "metrics": metrics, "errors": errors}

    def text(value):
        return isinstance(value, str) and bool(value.strip())

    def rows(data, key, *, optional=False):
        value = data.get(key)
        if not isinstance(value, list) or (not optional and not value) or any(not isinstance(r, dict) for r in value):
            errors.append(f"{key}: expected {'an' if optional else 'a nonempty'} array of objects")
            return []
        return value

    def indexed(data, key, *, optional=False):
        found = {}
        for row in rows(data, key, optional=optional):
            ident = row.get("id")
            if not text(ident) or ident in found:
                errors.append(f"{key}: invalid or duplicate id")
            else:
                found[ident] = row
        return found

    def artifact(value, digest=None):
        if not text(value) or not value.startswith(("docs/", "designs/")):
            errors.append(f"Invalid artifact path: {value!r}")
            return False
        prefix = value.split("/")[0]
        root = ctx.resolve(prefix).resolve()
        path = ctx.resolve(value).resolve()
        if not path.is_relative_to(root) or not path.is_file() or not path.stat().st_size:
            errors.append(f"Missing/unsafe artifact: {value}")
            return False
        if digest is not None and hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            errors.append(f"Source changed: {value}")
            return False
        return True

    try:
        data = json.loads(ctx.resolve(DISCOVERY_PATH).read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError) as exc:
        errors.append(f"Cannot read discovery: {exc}")
        return report
    if not isinstance(data, dict):
        errors.append("Discovery must be an object")
        return report
    if type(data.get("schema_version")) is not int or data["schema_version"] != 1:
        errors.append("Discovery schema_version must be 1")
    if data.get("status") != "ready_for_wireframe":
        errors.append("Discovery is not ready_for_wireframe")
    if expected_request_id is not None and data.get("request_id") != expected_request_id:
        errors.append("Discovery does not belong to this workflow request")
    if data.get("scope") not in ("ui", "non_ui"):
        errors.append("Discovery scope must be ui or non_ui")
    sources = set()
    for source in rows(data, "sources"):
        source_path = source.get("path")
        if not text(source_path) or not source_path.startswith("docs/") or not source_path.endswith((".md", ".json", ".txt")):
            errors.append("Discovery sources must be docs/ text artifacts")
        elif not text(source.get("sha256")):
            errors.append("Source sha256 is required")
        elif artifact(source.get("path"), source["sha256"]):
            sources.add(source["path"])
    artifact("docs/design-discovery/brief.md")
    if data.get("scope") == "non_ui":
        if not text(data.get("reason")):
            errors.append("non_ui discovery requires a source-based reason")
        report["ok"] = not errors
        return report

    required = indexed(data, "required")
    provisional = indexed(data, "provisional", optional=True)
    metrics.update(required=len(required), provisional=len(provisional))
    if set(required) & set(provisional):
        errors.append("A requirement cannot also be provisional")
    for ident, row in required.items():
        source = row.get("source")
        if not text(source) or source.split("#", 1)[0] not in sources:
            errors.append(f"{ident}: required condition needs a source")
        for key in ("statement", "acceptance"):
            if not text(row.get(key)):
                errors.append(f"{ident}: missing {key}")
    for ident, row in provisional.items():
        for key in ("current", "reason", "alternatives"):
            if not text(row.get(key)):
                errors.append(f"{ident}: missing {key}")

    refs = indexed(data, "references")
    hypotheses = indexed(data, "hypotheses")
    metrics.update(references=len(refs), hypotheses=len(hypotheses))
    for ident, row in refs.items():
        for key in ("url", "observed_at", "observation", "adopt", "avoid"):
            if not text(row.get(key)):
                errors.append(f"{ident}: missing {key}")
        artifact(row.get("evidence"))
    if data.get("mode") == "reuse":
        if not text(data.get("reuse_reason")):
            errors.append("reuse requires a reason and a decision source")
        decision = data.get("decision_source")
        if not text(decision) or decision.split("#", 1)[0] not in sources:
            errors.append("reuse requires a current decision source")
    elif data.get("mode") != "explore" or len(hypotheses) < 2:
        errors.append("explore requires at least two composition hypotheses")
    compositions = set()
    for ident, row in hypotheses.items():
        for key in (*COMPOSITION_FIELDS, "translation", "tradeoff"):
            if not text(row.get(key)):
                errors.append(f"{ident}: missing {key}")
        links = row.get("reference_ids")
        if not isinstance(links, list) or not links or any(not text(v) or v not in refs for v in links):
            errors.append(f"{ident}: reference_ids must link observed references")
        composition = tuple(row.get(k) if text(row.get(k)) else "" for k in COMPOSITION_FIELDS)
        if composition in compositions:
            errors.append(f"{ident}: duplicate composition; palette changes are not structure alternatives")
        compositions.add(composition)
    report["ok"] = not errors
    return report
