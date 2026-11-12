#!/usr/bin/env python3
"""Check recorded design/app measurements and their current artifacts; never render or approve UI."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

CONTEXT = {'platform', 'width', 'height', 'dpr', 'text_scale', 'locale', 'state', 'fixture_sha256', 'scroll'}
MEASURED = ('context', 'hierarchy', 'actions', 'elements')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical_hash(data):
    return digest(json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                             allow_nan=False).encode())


def read_json(path):
    if path.suffix.lower() == '.pen':
        raise ValueError('Pencil sources must be read through the design tool')
    return json.loads(path.read_text(encoding='utf-8'), parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))


def number(value, *, positive=False):
    return type(value) in (int, float) and math.isfinite(value) and (not positive or value > 0)


def required(condition, message):
    if not condition:
        raise ValueError(message)


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def unique_strings(values):
    return isinstance(values, list) and all(nonempty(v) for v in values) and len(values) == len(set(values))


def fingerprint(code_root, roots):
    required(isinstance(roots, list) and bool(roots) and unique_strings(roots), 'source_roots must be nonempty and unique')
    base = code_root.resolve()
    result = {}
    for rel in roots:
        path = base / rel
        required(not Path(rel).is_absolute() and path.resolve().is_relative_to(base), f'Source path escapes code root: {rel}')
        required(path.exists() and not path.is_symlink(), f'Missing or symlink source root: {rel}')
        for item in sorted(path.rglob('*') if path.is_dir() else [path]):
            required(not item.is_symlink(), f'Symlink source input is not supported: {item}')
            if not item.is_file() or '__pycache__' in item.parts or item.name == '.DS_Store':
                continue
            key = item.relative_to(base).as_posix()
            if item.suffix.lower() == '.pen':
                stat = item.stat()
                result[key] = {'size': stat.st_size, 'mtime_ns': stat.st_mtime_ns, 'opaque': True}
            else:
                result[key] = digest(item.read_bytes())
    required(bool(result), 'No source files found')
    return {'schema_version': 1, 'source_roots': roots, 'files': result}


def check_artifact(base, ref, *, png_size=None):
    required(isinstance(ref, dict) and nonempty(ref.get('path')) and nonempty(ref.get('sha256')), 'Artifact requires path and sha256')
    path = (base / ref['path']).resolve()
    required(path.suffix.lower() != '.pen', 'Use native_source stat for .pen; do not hash its bytes')
    data = path.read_bytes()
    required(digest(data) == ref['sha256'], f'Artifact changed: {ref["path"]}')
    if png_size is not None:
        required(len(data) >= 33 and data[:8] == b'\x89PNG\r\n\x1a\n' and data[12:16] == b'IHDR', f'Not a PNG: {path.name}')
        required(struct.unpack('>II', data[16:24]) == png_size, f'PNG dimensions differ from viewport/DPR: {path.name}')
    return path


def validate_case(case):
    required(isinstance(case, dict) and nonempty(case.get('id')), 'Case requires a stable id')
    context = case.get('context')
    required(isinstance(context, dict) and CONTEXT <= context.keys(), 'Incomplete comparison context')
    for key in ('width', 'height', 'dpr', 'text_scale'):
        required(number(context[key], positive=True), f'Invalid {key}')
    for key in ('platform', 'locale', 'state', 'fixture_sha256'):
        required(nonempty(context[key]), f'Invalid {key}')
    scroll = context['scroll']
    required(isinstance(scroll, list) and len(scroll) == 2 and all(number(n) for n in scroll), 'Invalid scroll')
    required(unique_strings(case.get('actions')), 'Invalid or duplicate action ids')
    required(unique_strings(case.get('hierarchy')) and case['hierarchy'], 'Missing or duplicate hierarchy ids')
    elements = case.get('elements')
    required(isinstance(elements, dict) and bool(elements), 'Case has no measured elements')
    for name, props in elements.items():
        required(nonempty(name) and isinstance(props, dict), 'Invalid element')
        box = props.get('box')
        required(isinstance(box, list) and len(box) == 4 and all(number(n) for n in box)
                 and box[2] > 0 and box[3] > 0, f'Invalid box: {name}')
    return (round(context['width'] * context['dpr']), round(context['height'] * context['dpr']))


def check_measurement(base, case, field):
    path = check_artifact(base, case[field])
    observed = read_json(path)
    required(isinstance(observed, dict), 'Measurement must be an object')
    for key in MEASURED:
        required(observed.get(key) == case[key], f'{case["id"]}: report differs from measured {key}')


def verify(contract_path, report_path, code_root):
    errors, counts = [], {'cases': 0, 'elements': 0, 'max_box_delta_px': 0.0}
    try:
        contract, report = read_json(contract_path), read_json(report_path)
        required(type(contract.get('schema_version')) is int and contract['schema_version'] == 1, 'Unsupported contract schema')
        required(type(report.get('schema_version')) is int and report['schema_version'] == 1, 'Unsupported report schema')
        required(nonempty(contract.get('scope')) and nonempty(contract.get('design_version')), 'Missing scope/design_version')
        decision = contract.get('decision', {})
        required(nonempty(decision.get('quote')) and nonempty(decision.get('source')), 'Missing existing user instruction/decision')
        base = contract_path.parent
        required(report.get('contract_sha256') == digest(contract_path.read_bytes()), 'Contract changed since measurement')
        native = contract.get('native_source')
        if native is not None:
            path = (base / native['path']).resolve()
            stat = path.stat()
            required(stat.st_size == native['size'] and stat.st_mtime_ns == native['mtime_ns'], 'Native design source changed; re-query through the design tool')
        snapshot = read_json(check_artifact(base, report['code_snapshot']))
        required(snapshot == fingerprint(code_root, contract['source_roots']), 'Code/input files changed since capture (including added/deleted files)')
        expected, actual = contract.get('cases'), report.get('cases')
        required(isinstance(expected, list) and bool(expected) and isinstance(actual, list), 'Missing cases')
        for cases in (expected, actual):
            required(all(isinstance(c, dict) and nonempty(c.get('id')) for c in cases), 'Invalid case id')
            required(len({c['id'] for c in cases}) == len(cases), 'Duplicate case ids')
        by_id = {c['id']: c for c in actual}
        required({c['id'] for c in expected} == set(by_id), 'Missing or unexpected screen/state cases')
        for wanted in expected:
            observed = by_id[wanted['id']]
            case_id = wanted['id']
            try:
                size = validate_case(wanted)
                validate_case(observed)
                required(wanted['context'] == observed['context'], f'{case_id}: comparison context differs')
                fixture = check_artifact(base, wanted['fixture'])
                required(digest(fixture.read_bytes()) == wanted['context']['fixture_sha256'], f'{case_id}: fixture context differs')
                check_artifact(base, wanted['reference_png'], png_size=size)
                check_artifact(base, observed['actual_png'], png_size=size)
                check_measurement(base, wanted, 'reference_measurement')
                check_measurement(base, observed, 'actual_measurement')
                required(observed.get('measured_by') in ('flutter-render-tree', 'browser-dom', 'native-accessibility'), f'{case_id}: actual render measurement required')
                tolerance = wanted.get('max_box_delta_px')
                required(number(tolerance) and tolerance >= 0, f'{case_id}: explicit finite geometry tolerance required')
                if wanted['hierarchy'] != observed['hierarchy']:
                    errors.append(f'{case_id}: hierarchy changed')
                if set(wanted['actions']) != set(observed['actions']):
                    errors.append(f'{case_id}: actions changed; missing={sorted(set(wanted["actions"])-set(observed["actions"]))}; extra={sorted(set(observed["actions"])-set(wanted["actions"]))}')
                old, new = wanted['elements'], observed['elements']
                if set(old) != set(new):
                    errors.append(f'{case_id}: elements changed; missing={sorted(set(old)-set(new))}; extra={sorted(set(new)-set(old))}')
                for name in old.keys() & new.keys():
                    counts['elements'] += 1
                    delta = max(abs(a-b) for a, b in zip(old[name]['box'], new[name]['box']))
                    counts['max_box_delta_px'] = max(counts['max_box_delta_px'], delta)
                    if delta > tolerance:
                        errors.append(f'{case_id}/{name}: box delta {delta:g}px > {tolerance:g}px')
                    for prop in old[name].keys() - {'box'}:
                        if prop not in new[name] or old[name][prop] != new[name][prop]:
                            errors.append(f'{case_id}/{name}: {prop} differs')
                counts['cases'] += 1
            except (OSError, ValueError, KeyError, TypeError) as exc:
                errors.append(f'{case_id}: {exc}')
        review = report.get('visual_review', {})
        required(review.get('kind') in ('self', 'independent') and review.get('status') == 'pass'
                 and nonempty(review.get('notes')) and review.get('unresolved') == [], 'Visual comparison absent or unresolved differences remain')
        required(review.get('evidence_sha256') == canonical_hash(actual), 'Visual review is stale for these captures/measurements')
    except (OSError, ValueError, KeyError, TypeError, AttributeError, OverflowError) as exc:
        errors.append(str(exc))
    return {'ok': not errors, 'status': 'MISMATCH' if errors else 'MATCHED', 'metrics': counts,
            'errors': errors, 'limits': 'Recorded evidence consistency only; capture provenance, full coverage, visual meaning and user approval require actual observation.'}


def cli(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('snapshot', 'verify'):
        command = sub.add_parser(name)
        command.add_argument('--code-root', type=Path, required=True)
        command.add_argument('--contract', type=Path, required=True)
        if name == 'snapshot':
            command.add_argument('--output', type=Path, required=True)
        else:
            command.add_argument('--report', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'snapshot':
            required(args.output.suffix.lower() == '.json', 'Snapshot output must be JSON, never a design source')
            required(not args.output.exists(), 'Snapshot already exists; preserve it and choose a new capture filename')
            result = fingerprint(args.code_root, read_json(args.contract)['source_roots'])
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            output = {'ok': True, 'files': len(result['files']), 'snapshot': str(args.output), 'sha256': digest(args.output.read_bytes())}
        else:
            output = verify(args.contract, args.report, args.code_root)
        print(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False))
        return 0 if output['ok'] else 1
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        print(json.dumps({'ok': False, 'status': 'MISMATCH', 'errors': [str(exc)]}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    sys.exit(cli())
