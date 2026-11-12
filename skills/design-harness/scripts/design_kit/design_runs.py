"""Restartable design decisions with a single atomic event/state ledger."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import json
import os
import shutil
from pathlib import Path
import tempfile
import uuid

from .context import ProjectContext
from .design_contract import (DesignError, ID, canonical, direction_fingerprint, file_ref,
                              fingerprint, read_json, safe_path, text, validate_contract, presentation_errors)
from .design_measure import PROFILE, measure_bundle
from .design_feedback import (CLASSIFICATIONS, feedback_view, related, holds, feedback_errors,
                              selection_usable, visual_review, application_record)


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
        for name in ("state.json", "manifest.json", ".lock", "measurements.json", "selection.json", "review.json", "comparison-review.json"):
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
                value.get("schema_version") not in (1, 2) or not isinstance(value.get("events"), list)):
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
            state = {"schema_version": 2, "run_id": self.run_id, "phase": "draft",
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

    def _readiness(self, state, manifest):
        feedback = feedback_view(state, manifest)
        active_holds = holds(state, feedback)
        legacy = state['schema_version'] < 2 or manifest.get('schema_version') != 2
        errors = {}
        presentation = presentation_errors(manifest, self.ctx)
        for candidate in manifest.get('candidates', []):
            cid = candidate['id']
            issues = feedback_errors(self.ctx, feedback, cid, state['snapshot'], active_holds)
            if legacy: issues.append('Legacy run: explicit upgrade and current visual evidence required')
            issues.extend(presentation)
            try: visual_review(self.ctx, self.directory, manifest, state, feedback, cid)
            except (DesignError, OSError, KeyError, TypeError, ValueError) as exc: issues.append(str(exc))
            errors[cid] = issues
        production = {c['id']: not any(scope in (None, c['id']) for scope in active_holds.values())
                      for c in manifest.get('candidates', [])}
        usable = selection_usable(state, manifest, feedback, active_holds)
        selected = state.get('selected')
        if selected and selected['direction_snapshot'] != direction_fingerprint(manifest, selected['candidate_id']):
            usable = False
        return {'feedback': feedback, 'active_holds': active_holds,
                'work_mode': 'diagnosis_only' if active_holds else 'design',
                'analysis_allowed': True, 'production_allowed': all(production.values()) and not any(v is None for v in active_holds.values()),
                'production_allowed_by_candidate': production, 'selection_usable': usable,
                'expansion_allowed': usable and not errors.get(selected['candidate_id']) if selected else False,
                'eligible_candidate_ids': [cid for cid, issues in errors.items() if not issues],
                'readiness_errors': errors, 'presentation_errors': presentation, 'upgrade_required': legacy}

    def upgrade(self, reason):
        if not text(reason): raise DesignError('Upgrade requires a review reason')
        with self.locked():
            state, manifest = self.state(), self.manifest()
            if state['schema_version'] == 2 and manifest.get('schema_version') == 2: return state
            # Preserve original files before explicitly transitioning. No review or choice is invented.
            for name, value in (('state-v1.json', state), ('manifest-v1.json', manifest)):
                target = safe_path(self.ctx, f'{self.rel}/{name}')
                if not target.exists(): shutil.copy2(self.directory / name.replace('-v1', ''), target)
            current_feedback = feedback_view(state, manifest)
            for e in state['events']:
                if e['kind'] == 'feedback' and 'feedback_context' not in e:
                    e['feedback_context'] = {'active': next(f['active'] for f in current_feedback if f['id'] == e['id'])}
            manifest['schema_version'] = 2
            atomic_json(self.manifest_path, manifest)
            state.update(schema_version=2, snapshot=fingerprint(manifest, self.ctx), phase='exploring')
            self._event(state, 'upgrade', {'reason': reason, 'from_version': 1, 'to_version': 2})
            self._save(state)
            return state

    def status(self):
        with self.locked():
            state, manifest = self.state(), self.manifest()
            actual = fingerprint(manifest, self.ctx)
            readiness = self._readiness(state, manifest)
            phase = state['phase']
            if not readiness['production_allowed'] and not any(readiness['production_allowed_by_candidate'].values()): phase = 'diagnosis_only'
            elif state.get('selected') and not readiness['selection_usable']: phase = 'feedback_pending'
            elif phase == 'awaiting_direction' and not readiness['eligible_candidate_ids']: phase = 'feedback_pending'
            elif phase in ('awaiting_final', 'ready_for_build') and state.get('selected') and readiness['readiness_errors'].get(state['selected']['candidate_id']):
                phase = 'review_pending'
            if actual != state['snapshot']:
                phase = 'stale'
                readiness.update(expansion_allowed=False, selection_usable=False, eligible_candidate_ids=[])
            return {**state, **readiness, 'recorded_phase': state['phase'], 'phase': phase,
                    'current_snapshot': actual, 'manifest': str(self.manifest_path)}

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
            state.update(snapshot=fingerprint(manifest, self.ctx), phase="refining" if keep else "exploring")
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
        state = self.state()
        return visual_review(self.ctx, self.directory, manifest, state,
                             feedback_view(state, manifest), candidate_id, final=True)

    def prepare(self, stage="comparison"):
        with self.locked():
            state, manifest = self.state(), self.manifest()
            self._current(state, manifest)
            if stage not in ("comparison", "final"):
                raise DesignError("Unknown measurement stage")
            if manifest.get("scope") == "non_ui":
                if holds(state, feedback_view(state, manifest)):
                    return {'ok': False, 'errors': ['Diagnosis only: explicit user resume is required']}
                report = validate_contract(manifest, self.ctx)
                if report["ok"]:
                    state.update(phase="ready_for_build", non_ui_snapshot=state["snapshot"])
                    self._event(state, "non_ui", {"reason": manifest["reason"], "snapshot": state["snapshot"]})
                    self._save(state)
                return report
            phases = ("exploring", "awaiting_direction", "refining", "awaiting_final", "ready_for_build") if stage == "comparison" else ("refining", "awaiting_final")
            if state["phase"] not in phases:
                raise DesignError(f"Cannot prepare {stage} from {state['phase']}")
            selected = state.get("selected")
            candidate_id = selected["candidate_id"] if selected else None
            readiness = self._readiness(state, manifest)
            if stage == "final":
                if not readiness['selection_usable']:
                    raise DesignError('Selected direction has unresolved feedback or requires a new choice')
                if readiness['readiness_errors'].get(candidate_id):
                    raise DesignError('; '.join(readiness['readiness_errors'][candidate_id]))
                if not selected or selected["direction_snapshot"] != direction_fingerprint(manifest, candidate_id):
                    raise DesignError("Selected direction changed; return to exploration")
                self._review(manifest, state["snapshot"], candidate_id)
            report = measure_bundle(manifest, self.ctx, stage=stage, candidate_id=candidate_id if stage == "final" else None)
            atomic_json(safe_path(self.ctx, f"{self.rel}/measurements.json"), report)
            report['technical_ok'] = report['ok']
            report['visual_review'] = readiness['readiness_errors']
            report['eligible_candidate_ids'] = readiness['eligible_candidate_ids']
            if not readiness['eligible_candidate_ids']:
                report['ok'] = False
                report['errors'].append('No candidate is ready: current visual review, feedback handling and presentation are required')
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
        if kind not in ("direction", "final", "feedback", "budget", "triage", "application", "work_mode"):
            raise DesignError("Unknown event kind")
        with self.locked():
            state, manifest = self.state(), self.manifest()
            # Check idempotency before phase checks; a browser retry may arrive after transition.
            existing = next((e for e in state["events"] if e["id"] == payload["id"]), None)
            if existing:
                self._event(state, kind, payload, payload["id"])
                return state
            if kind in ('feedback', 'triage', 'application', 'work_mode'):
                return self._submit_feedback(state, manifest, payload)
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
                if kind == "direction":
                    readiness = self._readiness(state, manifest)
                    if cid not in readiness['eligible_candidate_ids']:
                        raise DesignError('; '.join(readiness['readiness_errors'].get(cid, ['Candidate not ready'])))
                    if state["phase"] != "awaiting_direction":
                        raise DesignError("Run is not awaiting a direction decision")
                    self._measurement_current(manifest, "comparison")
                    state.update(phase="refining", selected={"candidate_id": cid, "version": candidate["version"],
                                 "direction_snapshot": direction_fingerprint(manifest, cid), "event_id": payload["id"]})
                elif kind == "final":
                    readiness = self._readiness(state, manifest)
                    if not readiness['selection_usable'] or readiness['readiness_errors'].get(cid):
                        raise DesignError('Current feedback/review/presentation blocks final decision')
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

    def _submit_feedback(self, state, manifest, payload):
        kind = payload['kind']
        candidates = {c['id']: c for c in manifest.get('candidates', [])}
        cid = payload.get('candidate_id') or None
        feedback = feedback_view(state, manifest)
        if kind in ('feedback', 'work_mode'):
            self._authority(payload, kind)
            if cid is not None and cid not in candidates:
                # Feedback about removed candidates is history, never an active instruction.
                if kind != 'feedback': raise DesignError('Unknown work-mode candidate')
        if kind == 'feedback':
            if not text(payload.get('text')) or not text(payload.get('snapshot')):
                raise DesignError('Feedback needs original user text and observed snapshot')
            if cid is not None and (type(payload.get('version')) is not int or payload['version'] < 1):
                raise DesignError('Candidate feedback needs the observed version')
            classification = payload.get('classification', 'untriaged')
            if classification not in CLASSIFICATIONS: raise DesignError('Unknown feedback classification')
            active = (payload['snapshot'] == fingerprint(manifest, self.ctx) and
                      (cid is None or payload['version'] == candidates.get(cid, {}).get('version')))
            self._event(state, kind, payload, payload['id'])
            state['events'][-1]['feedback_context'] = {'active': active}
        elif kind == 'work_mode':
            if not text(payload.get('reason')) or payload.get('mode') not in ('design', 'diagnosis_only'):
                raise DesignError('Work mode needs explicit user reason and valid mode')
            if payload.get('snapshot') != fingerprint(manifest, self.ctx): raise DesignError('Work mode snapshot changed')
            if payload['mode'] == 'design':
                active = holds(state, feedback)
                ids = payload.get('hold_ids')
                if not isinstance(ids, list) or not ids or any(i not in active for i in ids):
                    raise DesignError('Resume must name active hold IDs')
                if cid is not None and any(active[i] not in (cid,) for i in ids):
                    raise DesignError('Resume may not expand its candidate scope')
            self._event(state, kind, payload, payload['id'])
        else:
            if payload.get('actor') != 'producer' or not text(payload.get('reviewer_id')):
                raise DesignError('Triage/application needs an identified producer, not user approval')
            item = next((f for f in feedback if f['id'] == payload.get('feedback_id')), None)
            if not item: raise DesignError('Unknown feedback ID')
            if kind == 'triage':
                if payload.get('classification') not in CLASSIFICATIONS or not text(payload.get('rationale')):
                    raise DesignError('Triage needs classification and contextual rationale')
                if item['classification'] == 'diagnosis_only' and payload['classification'] != 'diagnosis_only':
                    raise DesignError('Producer cannot release a user diagnosis hold; use explicit resume')
            else:
                self._current(state, manifest)
                if payload.get('snapshot') != state['snapshot']: raise DesignError('Application snapshot changed')
                # An unresolved application is valid history but never clears the gate.
                from .design_feedback import pinned
                path = pinned(self.ctx, payload.get('evidence'))
                if path.suffix != '.json': raise DesignError('Application must reference JSON')
                record = read_json(path)
                if not isinstance(record, dict) or record.get('feedback_id') != item['id']:
                    raise DesignError('Application refers to different feedback')
            self._event(state, kind, payload, payload['id'])
        self._save(state)
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
                    if holds(state, feedback_view(state, manifest)):
                        raise DesignError('Diagnosis only: explicit user resume is required')
                    report = validate_contract(manifest, self.ctx)
                    if state.get("non_ui_snapshot") != state["snapshot"]:
                        raise DesignError("non_ui reason has not been validated for this snapshot")
                    return report
                readiness = self._readiness(state, manifest)
                if not readiness['selection_usable']:
                    raise DesignError('Current feedback invalidates selected direction')
                selected = state.get("selected")
                if readiness['readiness_errors'].get(selected['candidate_id']):
                    raise DesignError('; '.join(readiness['readiness_errors'][selected['candidate_id']]))
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
