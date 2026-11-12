"""Design harness command line; generation stays with connected agent/design tools."""

import argparse
import json
from pathlib import Path
import sys

from .context import build_context, ProjectContext
from .design_board import BoardServer, export_board
from .design_contract import DesignError, file_ref, read_json, safe_path, validate_contract
from .design_runs import DesignRun, atomic_json, now
from .design_discovery import validate_discovery
from . import __version__


def active_run(ctx: ProjectContext) -> DesignRun:
    active = read_json(safe_path(ctx, "docs/design-harness/active.json"))
    if not isinstance(active, dict):
        raise DesignError("Invalid active design pointer")
    return DesignRun(ctx, active.get("run_id"))


def validate_active(ctx: ProjectContext, *, expected_request_id=None):
    try:
        return active_run(ctx).gate(expected_request_id=expected_request_id)
    except (DesignError, OSError, TypeError, ValueError) as exc:
        return {"ok": False, "kind": "design_handoff", "errors": [str(exc)]}


def cli(argv=None):
    parser = argparse.ArgumentParser(prog="design-kit", description="레퍼런스·시안 비교·결정·재개를 관리하는 독립 디자인 하네스")
    parser.add_argument("--version", action="version", version=f"Design Kit {__version__}")
    parser.add_argument("--project-root", type=Path, default=Path.cwd(), help="Project directory; defaults to cwd")
    parser.add_argument("--config", type=Path, help="Configuration file; defaults to PROJECT/design-kit.json")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="Inspect local runtime and configured paths; does not connect external tools")
    discovery = commands.add_parser("discovery-check", help="Validate the reference-first structural handoff")
    discovery.add_argument("--request-id")
    init = commands.add_parser("init")
    init.add_argument("--run", required=True)
    init.add_argument("--source", action="append", required=True)
    init.add_argument("--brief", required=True)
    init.add_argument("--theme", default="")
    init.add_argument("--scope", choices=["ui", "non_ui"], default="ui")
    init.add_argument("--reason", default="")
    init.add_argument("--request-id")
    for command in ("status", "refresh", "check", "prepare", "event", "gate", "board", "serve", "observe", "upgrade"):
        child = commands.add_parser(command)
        child.add_argument("--run", required=True)
        if command in ("refresh", "upgrade"):
            child.add_argument("--reason", required=True)
            child.add_argument("--automatic", action="store_true")
        if command in ("check", "prepare"):
            child.add_argument("--stage", choices=["comparison", "final"], default="comparison")
        if command == "event":
            child.add_argument("--file", type=Path, required=True)
        if command == "board":
            child.add_argument("--output", required=True, help="designs/ path for standalone comparison board")
        if command == "serve":
            child.add_argument("--port", type=int, default=0)
        if command == "observe":
            child.add_argument("--raw", type=Path, required=True, help="JSON containing actual rendered nodes from MCP")
            child.add_argument("--mapping", type=Path, required=True, help="JSON: root node id -> {source:path,preview:path}")
            child.add_argument("--output", required=True, help="docs/ path for normalized observation")
            child.add_argument("--renderer", default="pencil-mcp")
            child.add_argument("--saved-reopened", action="store_true", help="Use only after actual Save, close, reopen and MCP observation")
    pin = commands.add_parser("pin")
    pin.add_argument("path")
    args = parser.parse_args(argv)
    try:
        ctx = build_context(args.project_root, args.config)
        if args.command == "doctor":
            skills = Path(__file__).resolve().parents[3]
            paths = [skills / name / "SKILL.md" for name in ("design-bot", "design-harness")]
            assets = Path(__file__).parent / "design_board_assets"
            output = {"ok": all(p.is_file() for p in paths) and all((assets / p).is_file() for p in ("board.js", "board.css")),
                      "version": __version__, "python": sys.version.split()[0],
                      "skills_found": sum(p.is_file() for p in paths), "skills_expected": 2,
                      "docs_root": str(ctx.docs_root), "code_root": str(ctx.code_root),
                      "external_tools": "unverified: connect a design editor and visual observation tools in the host agent"}
        elif args.command == "discovery-check":
            output = validate_discovery(ctx, expected_request_id=args.request_id)
        elif args.command == "pin":
            output = file_ref(ctx, args.path)
        else:
            run = DesignRun(ctx, args.run)
            if args.command == "init":
                manifest = {"schema_version": 2, "run_id": args.run, "scope": args.scope,
                            "sources": [file_ref(ctx, p) for p in args.source], "brief": file_ref(ctx, args.brief),
                            "theme": {"requested": args.theme, "interpretation": "", "avoid": []},
                            "requirements": [], "screens": [], "viewports": [], "comparison": [], "references": [], "candidates": []}
                if args.request_id:
                    manifest["request_id"] = args.request_id
                if args.scope == "non_ui":
                    manifest["reason"] = args.reason
                output = run.initialize(manifest)
                atomic_json(safe_path(ctx, "docs/design-harness/active.json"), {"run_id": args.run})
            elif args.command == "status":
                state = run.status()
                output = {k: state.get(k) for k in ("run_id", "phase", "recorded_phase", "current_snapshot", "selected", "automatic_revisions", "manifest", "work_mode", "production_allowed", "production_allowed_by_candidate", "analysis_allowed", "expansion_allowed", "selection_usable", "eligible_candidate_ids", "readiness_errors", "feedback", "active_holds", "upgrade_required")}
                output["event_count"] = len(state["events"])
            elif args.command == "upgrade":
                output = run.upgrade(args.reason)
            elif args.command == "refresh":
                state = run.refresh(args.reason, automatic=args.automatic)
                output = {k: state.get(k) for k in ("phase", "snapshot", "selected", "automatic_revisions")}
            elif args.command == "check":
                selected = run.state().get("selected") or {}
                output = validate_contract(run.manifest(), ctx, stage=args.stage, candidate_id=selected.get("candidate_id"))
            elif args.command == "prepare":
                output = run.prepare(args.stage)
            elif args.command == "event":
                state = run.submit(read_json(args.file))
                output = {"phase": state["phase"], "selected": state.get("selected"), "event_count": len(state["events"])}
            elif args.command == "gate":
                output = run.gate()
            elif args.command == "board":
                output = {"board": str(export_board(run, safe_path(ctx, args.output)))}
            elif args.command == "serve":
                server = BoardServer(run, args.port)
                print(json.dumps({"url": server.origin, "run_id": run.run_id}, ensure_ascii=False), flush=True)
                try:
                    server.serve_forever()
                except KeyboardInterrupt:
                    pass
                finally:
                    server.server_close()
                return 0
            elif args.command == "observe":
                raw, mapping = read_json(args.raw), read_json(args.mapping)
                nodes = raw.get("nodes") if isinstance(raw, dict) else raw
                if not isinstance(nodes, list) or not nodes or not isinstance(mapping, dict) or not mapping:
                    raise DesignError("Expected raw node array and nonempty frame artifact mapping")
                if not args.output.startswith("docs/") or not args.output.endswith(".json"):
                    raise DesignError("Observation output must be a docs/ JSON file")
                observation = {"renderer": args.renderer, "captured_at": now(), "saved_reopened": args.saved_reopened,
                               "nodes": nodes, "artifacts": {ident: {"source": file_ref(ctx, entry["source"]),
                                "preview": file_ref(ctx, entry["preview"])} for ident, entry in mapping.items()}}
                atomic_json(safe_path(ctx, args.output), observation)
                output = file_ref(ctx, args.output)
            else:
                raise DesignError("Unknown action")
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0 if output.get("ok", True) else 1
    except (DesignError, OSError, KeyError, TypeError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(cli())
