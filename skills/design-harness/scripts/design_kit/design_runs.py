"""Restartable design decisions with a single atomic event/state ledger."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import tempfile
import uuid

from .context import ProjectContext
from .design_contract import (DesignError, ID, canonical, direction_fingerprint, file_ref,
                              fingerprint, read_json, safe_path, text, validate_contract)
from .design_measure import PROFILE, measure_bundle


def atomic_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".design-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def now():
    return datetime.now(timezone.utc).isoformat()


class DesignRun:
    def __init__(self, ctx: ProjectContext, run_id: str):
        if not isinstance(run_id, str) or not ID.fullmatch(run_id):
            raise DesignError("Invalid run id")
        self.ctx, self.run_id = ctx, run_id
        self.rel = f"docs/design-harness/{run_id}"
        self.directory = safe_path(ctx, f"{self.rel}/manifest.json").parent
        self.manifest_path = self.directory / "manifest.json"
        self.state_path = self.directory / "state.json"

    @contextmanager
    def locked(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        # Recheck containment after directory creation and before following local state files.
        for name in ("state.json", "manifest.json", ".lock", "measurements.json", "selection.json", "review.json"):
            safe_path(self.ctx, f"{self.rel}/{name}")
        with (self.directory / ".lock").open("a") as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)

    def manifest(self):
        value = read_json(self.manifest_path)
        if not isinstance(value, dict) or value.get("run_id") != self.run_id:
            raise DesignError("Manifest does not belong to this run")
        return value

    def state(self):
        value = read_json(self.state_path)
        if (not isinstance(value, dict) or value.get("run_id") != self.run_id or
                value.get("schema_version") != 1 or not isinstance(value.get("events"), list)):
            raise DesignError("Malformed run ledger")
        return value

    def initialize(self, manifest: dict):
        with self.locked():
            if self.state_path.exists():
                raise DesignError("Run already exists; use status/refresh to resume")
            if not isinstance(manifest, dict) or manifest.get("run_id") != self.run_id:
                raise DesignError("Run id mismatch")
            if self.manifest_path.exists():
                if canonical(self.manifest()) != canonical(manifest):
                    raise DesignError("Interrupted initialization has different inputs; preserve and review the existing manifest")
            else:
                atomic_json(self.manifest_path, manifest)
            state = {"schema_version": 1, "run_id": self.run_id, "phase": "draft",
                     "snapshot": fingerprint(manifest, self.ctx), "created_at": now(),
                     "automatic_revisions": 0, "max_automatic_revisions": PROFILE["max_automatic_revisions"],
                     "selected": None, "final_event": None, "events": []}
            self._save(state)
            return state

    def _save(self, state):
        state["updated_at"] = now()
        atomic_json(self.state_path, state)
        # These are projections, never read as authority by the gate. Regenerate after a crash.
        for filename, kinds in (("feedback.jsonl", {"feedback"}), ("decisions.jsonl", {"direction", "final"})):
            path = safe_path(self.ctx, f"{self.rel}/{filename}")
            output = "".join(canonical(e) + "\n" for e in state["events"] if e["kind"] in kinds)
            fd, temp = tempfile.mkstemp(prefix=".projection-", dir=self.directory)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as stream:
                    stream.write(output)
                os.replace(temp, path)
            finally:
                if os.path.exists(temp):
                    os.unlink(temp)

    def _event(self, state, kind, payload, ident=None):
        ident = ident or uuid.uuid4().hex
        if not isinstance(ident, str) or not ID.fullmatch(ident):
            raise DesignError("Invalid event id")
        existing = next((e for e in state["events"] if e["id"] == ident), None)
        if existing:
            if existing["kind"] != kind or canonical(existing["payload"]) != canonical(payload):
                raise DesignError("Event id already used with different content")
            return False
        state["events"].append({"id": ident, "kind": kind, "at": now(), "payload": payload})
        return True

    def status(self):
        with self.locked():
            state, manifest = self.state(), self.manifest()
            actual = fingerprint(manifest, self.ctx)
            return {**state, "recorded_phase": state["phase"], "phase": state["phase"] if actual == state["snapshot"] else "stale",
                    "current_snapshot": actual, "manifest": str(self.manifest_path)}

    def refresh(self, reason: str, *, automatic=False):
        if not text(reason):
            raise DesignError("Refresh requires a concrete change/review reason")
        with self.locked():
            state, manifest = self.state(), self.manifest()
            if state["phase"] == "blocked":
                raise DesignError("Automatic revision budget exhausted; explicit user budget event required")
            if automatic:
                if state["automatic_revisions"] >= state["max_automatic_revisions"]:
                    state["phase"] = "blocked"
                    self._event(state, "budget_exhausted", {"reason": reason})
                    self._save(state)
                    return state
                state["automatic_revisions"] += 1
            selected = state.get("selected")
            keep = bool(selected and selected["direction_snapshot"] == direction_fingerprint(manifest, selected["candidate_id"]))
            old = state["snapshot"]
            state.update(snapshot=fingerprint(manifest, self.ctx), phase="refining" if keep else "exploring", final_event=None)
            if not keep:
                state["selected"] = None
            self._event(state, "refresh", {"reason": reason, "before": old, "after": state["snapshot"],
                                            "preserved_direction": keep, "automatic": automatic})
            self._save(state)
            return state

    def _current(self, state, manifest):
        if fingerprint(manifest, self.ctx) != state["snapshot"]:
            raise DesignError("Run is stale; review changed inputs then refresh with a reason")

    def _review(self, manifest, snapshot, candidate_id):
        review = read_json(safe_path(self.ctx, f"{self.rel}/review.json"))
        if not isinstance(review, dict):
            raise DesignError("Review must be an object")
        if (review.get("snapshot") != snapshot or review.get("candidate_id") != candidate_id or
                review.get("independent") is not True or review.get("verdict") != "pass" or
                review.get("unresolved") != [] or not text(review.get("reviewer_id")) or
                not text(review.get("producer_id")) or review["reviewer_id"] == review["producer_id"]):
            raise DesignError("Final needs a current independent passing review without unresolved issues")
        evidence = review.get("evidence")
        if not isinstance(evidence, dict) or file_ref(self.ctx, evidence.get("path")) != evidence:
            raise DesignError("Review evidence missing or changed")
        return review

    def prepare(self, stage="comparison"):
        with self.locked():
            state, manifest = self.state(), self.manifest()
            self._current(state, manifest)
            if stage not in ("comparison", "final"):
                raise DesignError("Unknown measurement stage")
            if manifest.get("scope") == "non_ui":
                report = validate_contract(manifest, self.ctx)
                if report["ok"]:
                    state.update(phase="ready_for_build", non_ui_snapshot=state["snapshot"])
                    self._event(state, "non_ui", {"reason": manifest["reason"], "snapshot": state["snapshot"]})
                    self._save(state)
                return report
            phases = ("exploring", "awaiting_direction") if stage == "comparison" else ("refining", "awaiting_final")
            if state["phase"] not in phases:
                raise DesignError(f"Cannot prepare {stage} from {state['phase']}")
            selected = state.get("selected")
            candidate_id = selected["candidate_id"] if selected else None
            if stage == "final":
                if not selected or selected["direction_snapshot"] != direction_fingerprint(manifest, candidate_id):
                    raise DesignError("Selected direction changed; return to exploration")
                self._review(manifest, state["snapshot"], candidate_id)
            report = measure_bundle(manifest, self.ctx, stage=stage, candidate_id=candidate_id if stage == "final" else None)
            atomic_json(safe_path(self.ctx, f"{self.rel}/measurements.json"), report)
            if report["ok"]:
                state["phase"] = "awaiting_direction" if stage == "comparison" else "awaiting_final"
                self._event(state, "measured", {"stage": stage, "snapshot": state["snapshot"], "frames": len(report["frames"])})
                self._save(state)
            return report

    def _authority(self, payload, kind):
        if payload.get("actor") not in ("user", "delegated") or not text(payload.get("authority")):
            raise DesignError("Decision needs actual user authority, not an automated quality score")
        if payload["actor"] == "delegated":
            delegation = payload.get("delegation")
            if not isinstance(delegation, dict) or file_ref(self.ctx, delegation.get("path")) != delegation:
                raise DesignError("Missing/changed explicit delegation record")
            path = safe_path(self.ctx, delegation["path"])
            if path.suffix != ".json":
                raise DesignError("Delegation record must be JSON")
            record = read_json(path)
            if (not isinstance(record, dict) or not isinstance(record.get("allowed_decisions"), list) or
                    kind not in record["allowed_decisions"] or not text(record.get("user_source")) or
                    record.get("run_id") != self.run_id):
                raise DesignError("Delegation does not cover this run/decision")

    def _measurement_current(self, manifest, stage, candidate_id=None):
        saved = read_json(safe_path(self.ctx, f"{self.rel}/measurements.json"))
        fresh = measure_bundle(manifest, self.ctx, stage=stage, candidate_id=candidate_id)
        if not fresh["ok"] or canonical(saved) != canonical(fresh):
            raise DesignError("Measurement report stale, edited, or incomplete; prepare again")
        return fresh

    def submit(self, payload: dict):
        if not isinstance(payload, dict) or not text(payload.get("id")):
            raise DesignError("Event requires id and object payload")
        kind = payload.get("kind")
        if kind not in ("direction", "final", "feedback", "budget"):
            raise DesignError("Unknown event kind")
        with self.locked():
            state, manifest = self.state(), self.manifest()
            # Check idempotency before phase checks; a browser retry may arrive after transition.
            existing = next((e for e in state["events"] if e["id"] == payload["id"]), None)
            if existing:
                self._event(state, kind, payload, payload["id"])
                return state
            self._current(state, manifest)
            if payload.get("snapshot") != state["snapshot"]:
                raise DesignError("Selection refers to a different candidate snapshot")
            self._authority(payload, kind)
            if kind == "budget":
                limit = payload.get("max_automatic_revisions")
                if type(limit) is not int or limit <= state["automatic_revisions"] or not text(payload.get("reason")):
                    raise DesignError("Explicit budget extension must exceed spent revisions and explain why")
                state.update(max_automatic_revisions=limit, phase="refining" if state.get("selected") else "exploring")
            else:
                candidates = {c["id"]: c for c in manifest.get("candidates", [])}
                cid = payload.get("candidate_id")
                if not isinstance(cid, str) or cid not in candidates:
                    raise DesignError("Unknown candidate")
                candidate = candidates[cid]
                if payload.get("version") != candidate["version"]:
                    raise DesignError("Event refers to a different candidate version")
                if kind == "feedback":
                    if not text(payload.get("text")):
                        raise DesignError("Feedback needs the original user text")
                    screen = payload.get("screen")
                    if screen is not None and screen not in {s["id"] for s in manifest.get("screens", [])}:
                        raise DesignError("Unknown feedback screen")
                elif kind == "direction":
                    if state["phase"] != "awaiting_direction":
                        raise DesignError("Run is not awaiting a direction decision")
                    self._measurement_current(manifest, "comparison")
                    state.update(phase="refining", selected={"candidate_id": cid, "version": candidate["version"],
                                 "direction_snapshot": direction_fingerprint(manifest, cid), "event_id": payload["id"]})
                elif kind == "final":
                    if state["phase"] != "awaiting_final" or not state.get("selected") or state["selected"]["candidate_id"] != cid:
                        raise DesignError("Run is not awaiting final decision for this selected direction")
                    if state["selected"]["direction_snapshot"] != direction_fingerprint(manifest, cid):
                        raise DesignError("Selected direction changed")
                    self._review(manifest, state["snapshot"], cid)
                    self._measurement_current(manifest, "final", cid)
                    state.update(phase="ready_for_build", final_event=payload["id"])
            self._event(state, kind, payload, payload["id"])
            self._save(state)
            if kind == "final":
                atomic_json(safe_path(self.ctx, f"{self.rel}/selection.json"), self._selection(state, manifest))
            return state

    def _selection(self, state, manifest):
        selected = state["selected"]
        candidate = next(c for c in manifest["candidates"] if c["id"] == selected["candidate_id"])
        return {"schema_version": 1, "run_id": self.run_id, "snapshot": state["snapshot"],
                "candidate_id": candidate["id"], "version": candidate["version"],
                "direction_event": selected["event_id"], "final_event": state["final_event"],
                "sources": manifest["sources"], "candidate": candidate}

    def gate(self, *, expected_request_id=None):
        try:
            with self.locked():
                state, manifest = self.state(), self.manifest()
                self._current(state, manifest)
                if expected_request_id is not None and manifest.get("request_id") != expected_request_id:
                    raise DesignError("Design belongs to a different workflow request")
                if state["phase"] != "ready_for_build":
                    raise DesignError(f"Design is {state['phase']}, not ready_for_build")
                if manifest.get("scope") == "non_ui":
                    report = validate_contract(manifest, self.ctx)
                    if state.get("non_ui_snapshot") != state["snapshot"]:
                        raise DesignError("non_ui reason has not been validated for this snapshot")
                    return report
                selected = state.get("selected")
                if not selected or selected["direction_snapshot"] != direction_fingerprint(manifest, selected["candidate_id"]):
                    raise DesignError("No current direction selection")
                for kind, ident in (("direction", selected["event_id"]), ("final", state.get("final_event"))):
                    event = next((e for e in state["events"] if e["id"] == ident and e["kind"] == kind), None)
                    if not event or event["payload"].get("candidate_id") != selected["candidate_id"]:
                        raise DesignError(f"Missing {kind} event")
                    self._authority(event["payload"], kind)
                    if kind == "final" and event["payload"].get("snapshot") != state["snapshot"]:
                        raise DesignError("Final decision is stale")
                self._review(manifest, state["snapshot"], selected["candidate_id"])
                report = self._measurement_current(manifest, "final", selected["candidate_id"])
                expected = self._selection(state, manifest)
                path = safe_path(self.ctx, f"{self.rel}/selection.json")
                if not path.exists():
                    # Recover a projection interrupted after the authoritative ledger commit.
                    atomic_json(path, expected)
                if read_json(path) != expected:
                    raise DesignError("Published selection differs from the authoritative ledger")
                return {**report, "selection": str(path)}
        except (DesignError, OSError, KeyError, TypeError, ValueError) as exc:
            return {"ok": False, "errors": [str(exc)], "kind": "design_handoff"}
