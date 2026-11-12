"""Feedback and visual-review contracts, separate from geometric measurement.

Semantic verdicts are supplied by an identified reviewer. This module validates
scope/currentness/evidence, not aesthetics or the meaning of free text.
"""
from .design_contract import DesignError, canonical, file_ref, read_json, safe_path, text

CLASSIFICATIONS = {'untriaged', 'preference', 'change_request', 'rejection', 'diagnosis_only'}


def feedback_view(state, manifest):
    candidates = {c['id']: c for c in manifest.get('candidates', [])}
    result = []
    for event in state['events']:
        if event['kind'] != 'feedback':
            continue
        p = event['payload']; cid = p.get('candidate_id') or None
        context = event.get('feedback_context', {})
        active = context.get('active', p.get('snapshot') == state['snapshot'] and
                             (cid is None or p.get('version') == candidates.get(cid, {}).get('version')))
        classification = p.get('classification', 'untriaged')
        application = None
        updates = [event['id']]
        for update in state['events']:
            q = update['payload']
            if q.get('feedback_id') != event['id']:
                continue
            if update['kind'] in ('triage', 'application'): updates.append(update['id'])
            if update['kind'] == 'triage': classification = q['classification']
            if update['kind'] == 'application': application = q
        result.append({'id': event['id'], 'candidate_id': cid, 'screen': p.get('screen'),
                       'version': p.get('version'), 'text': p['text'], 'active': active,
                       'classification': classification, 'application': application, 'updates': updates})
    return result


def related(feedback, cid):
    return [f for f in feedback if f['active'] and f['candidate_id'] in (None, cid)]


def review_feedback_ids(feedback, cid):
    return [f['id'] for f in related(feedback, cid) if f['classification'] != 'preference']


def holds(state, feedback):
    held = {f['id']: f['candidate_id'] for f in feedback
            if f['active'] and f['classification'] == 'diagnosis_only'}
    for e in state['events']:
        if e['kind'] == 'work_mode':
            p = e['payload']
            if p['mode'] == 'diagnosis_only': held[e['id']] = p.get('candidate_id') or None
            else:
                for ident in p['hold_ids']: held.pop(ident, None)
    return held


def pinned(ctx, ref):
    if not isinstance(ref, dict) or file_ref(ctx, ref.get('path')) != ref:
        raise DesignError('Missing or changed review/application evidence')
    return safe_path(ctx, ref['path'])


def application_record(ctx, item, snapshot):
    p = item.get('application')
    if not p or p.get('snapshot') != snapshot:
        raise DesignError(f"Feedback {item['id']} has no current application")
    path = pinned(ctx, p.get('evidence'))
    if path.suffix != '.json': raise DesignError('Application evidence must be JSON')
    record = read_json(path)
    fields = ('observation', 'hypothesis', 'changed_relationships', 'preserved', 'counterevidence', 'remaining')
    if (not isinstance(record, dict) or record.get('feedback_id') != item['id'] or
            record.get('original_text') != item['text'] or not all(text(record.get(k)) for k in fields) or
            record.get('result') != 'for_review' or not isinstance(record.get('nodes'), list) or
            not record['nodes'] or not all(text(n) for n in record['nodes'])):
        raise DesignError('Application needs original text, relationships, preserved scope, counterevidence and reviewable nodes')
    for key in ('before', 'after'):
        if not isinstance(record.get(key), list) or not record[key]:
            raise DesignError('Application needs before and after evidence')
        for ref in record[key]: pinned(ctx, ref)
    return record


def feedback_errors(ctx, feedback, cid, snapshot, active_holds):
    errors = []
    if any(scope in (None, cid) for scope in active_holds.values()):
        errors.append('Diagnosis only: explicit user resume is required')
    for item in related(feedback, cid):
        if item['classification'] == 'untriaged': errors.append(f"Untriaged feedback: {item['id']}")
        elif item['classification'] in ('change_request', 'rejection'):
            try: application_record(ctx, item, snapshot)
            except (DesignError, OSError, TypeError, KeyError) as exc: errors.append(str(exc))
    return errors


def selection_usable(state, manifest, feedback, active_holds):
    selected = state.get('selected')
    if not selected: return False
    cid = selected['candidate_id']
    if any(scope in (None, cid) for scope in active_holds.values()): return False
    decision_index = next((i for i,e in enumerate(state['events']) if e['id'] == selected['event_id']), -1)
    later_ids = {e['id'] for e in state['events'][decision_index+1:]}
    return not any(any(eid in later_ids for eid in f['updates']) and f['classification'] in
                   ('untriaged', 'change_request', 'rejection') for f in related(feedback, cid))


def visual_review(ctx, directory, manifest, state, feedback, cid, *, final=False):
    path = safe_path(ctx, f"docs/design-harness/{state['run_id']}/" + ('review.json' if final else 'comparison-review.json'))
    review = read_json(path)
    if not isinstance(review, dict) or review.get('snapshot') != state['snapshot']:
        raise DesignError('Visual review is missing or refers to an old snapshot')
    if not final:
        if review.get('purpose') not in ('structure', 'visual', 'both'):
            raise DesignError('Comparison review needs an explicit purpose')
        distinction = review.get('distinction', {})
        if not isinstance(distinction, dict) or distinction.get('verdict') != 'acceptable' or not text(distinction.get('observation')):
            raise DesignError('Comparison distinction needs review; color change is not automatically UX diversity')
        entries = review.get('candidates')
        if not isinstance(entries, list) or any(not isinstance(x,dict) for x in entries):
            raise DesignError('Visual review needs candidate records')
        matches = [r for r in entries if r.get('candidate_id') == cid]
        if len(matches) != 1: raise DesignError('Visual review needs one current candidate record')
        review = matches[0]
    candidate = next(c for c in manifest['candidates'] if c['id'] == cid)
    if (review.get('candidate_id') != cid or review.get('version') != candidate['version'] or
            review.get('verdict') != 'pass' or review.get('unresolved') != [] or
            not text(review.get('reviewer_id')) or not text(review.get('producer_id')) or
            type(review.get('independent')) is not bool):
        raise DesignError('Visual review needs current version, identified reviewer and no unresolved issues')
    if final and (review['independent'] is not True or review['reviewer_id'] == review['producer_id']):
        raise DesignError('Final needs an independent review')
    if review['independent'] and review['reviewer_id'] == review['producer_id']:
        raise DesignError('Self review cannot be labelled independent')
    if review.get('feedback_ids') != review_feedback_ids(feedback, cid):
        raise DesignError('Visual review does not cover the current feedback frontier')
    if review.get('feedback_events') != [eid for f in related(feedback, cid) if f['classification'] != 'preference' for eid in f['updates']]:
        raise DesignError('Visual review predates feedback triage/application updates')
    pinned(ctx, review.get('evidence'))
    observations = review.get('observations')
    if (not isinstance(observations, list) or not observations or
            any(not isinstance(o,dict) or not text(o.get('region')) or not text(o.get('finding')) or
                not isinstance(o.get('nodes'),list) or not o['nodes'] or not all(text(n) for n in o['nodes'])
                for o in observations) or not text(review.get('regressions'))):
        raise DesignError('Visual review needs region/node observations and remaining regressions')
    known_nodes = set()
    previews = set()
    for frame in candidate['frames']:
        observed = read_json(pinned(ctx, frame['readback']))
        known_nodes.update(n['id'] for n in observed['nodes'])
        previews.add(canonical(frame['preview']))
    if any(node not in known_nodes for o in observations for node in o['nodes']):
        raise DesignError('Visual review refers to unobserved product nodes')
    for item in related(feedback, cid):
        if item['classification'] not in ('change_request', 'rejection'): continue
        application = application_record(ctx, item, state['snapshot'])
        allowed_previews, allowed_nodes = set(previews), set(known_nodes)
        if item['candidate_id'] is None:
            for other in manifest['candidates']:
                for frame in other['frames']:
                    allowed_previews.add(canonical(frame['preview']))
                    observed = read_json(pinned(ctx, frame['readback']))
                    allowed_nodes.update(n['id'] for n in observed['nodes'])
        after = {canonical(ref) for ref in application['after']}
        nodes = set(application['nodes'])
        if not after <= allowed_previews or not nodes <= allowed_nodes or not after & previews or not nodes & known_nodes:
            raise DesignError('Feedback application is not linked to current previews and observed nodes')
    usages = review.get('reference_usage')
    if not isinstance(usages, list) or not usages or any(not isinstance(u,dict) for u in usages):
        raise DesignError('Visual review needs reference scene/translation assessment')
    if {u.get('reference_id') for u in usages} != set(candidate['reference_ids']):
        raise DesignError('Visual review must cover the candidate references')
    for u in usages:
        if (u.get('verdict') != 'acceptable' or not all(text(u.get(k)) for k in
            ('source_region', 'task_fit', 'retained', 'changed'))):
            raise DesignError('Reference task mismatch or translation remains unresolved')
        pinned(ctx, u.get('study_evidence'))
        nodes = u.get('product_nodes')
        if not isinstance(nodes,list) or not nodes or not set(nodes) <= known_nodes:
            raise DesignError('Reference translation needs observed product nodes')
    return review
