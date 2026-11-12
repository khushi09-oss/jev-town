"""Bounded, opt-in Jev vision probe. Only explicit live mode can load project .env."""
import argparse
import base64
import hashlib
import json
import math
import os
from pathlib import Path
import re
import time
import uuid
from datetime import datetime, timezone

from PIL import Image
from dotenv import load_dotenv
import requests

URL = 'https://api.typesafe.ai/v1/systemone'
MODEL = 'jev-1.14.0'


def expected_choice(case):
    focal = case['focal']
    return min(case['candidates'], key=lambda key: (
        sum((case['candidates'][key][axis] - focal[axis]) ** 2 for axis in ('x', 'y')),
        case['candidates'][key]['id']))


def load_cases(root):
    path = root / 'cases.json'
    if path.stat().st_size > 1_000_000:
        raise ValueError('Case manifest too large')
    data = json.loads(path.read_text(encoding='utf-8'))
    cases = data.get('cases', [])
    if data.get('schemaVersion') != 1 or not isinstance(cases, list) or len(cases) != 3:
        raise ValueError('Expected exactly three version-1 cases')
    seen = set()
    for case in cases:
        if not isinstance(case.get('id'), str) or not re.fullmatch(r'case-[0-2]', case['id']) or case['id'] in seen:
            raise ValueError('Invalid or duplicate case ID')
        seen.add(case['id'])
        if set(case.get('candidates', {})) != {'A', 'B', 'C'}:
            raise ValueError('Expected three labeled neighbors')
        people = [case['focal'], *case['candidates'].values()]
        if len({p['id'] for p in people}) != 4:
            raise ValueError('Residents must be distinct')
        for person in people:
            if set(person) != {'id','name','x','y'} or not re.fullmatch(r'npc(?:[012][0-9])', person['id']) or not isinstance(person['name'], str) or not 1 <= len(person['name']) <= 50:
                raise ValueError('Invalid resident identity')
            for axis, limit in [('x', 1024), ('y', 640)]:
                value = person[axis]
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= limit:
                    raise ValueError('Invalid resident coordinates')
        image = (root / case['image']).resolve()
        if image.parent != root or image.suffix.lower() != '.png' or image.stat().st_size > 16 * 1024**2:
            raise ValueError('Images must be local PNG files inside the bundle')
        raw = image.read_bytes()
        if hashlib.sha256(raw).hexdigest() != case['imageSha256']:
            raise ValueError('Screenshot hash mismatch')
        with Image.open(image) as picture:
            if picture.format != 'PNG' or getattr(picture, 'n_frames', 1) != 1 or not all(280 <= side <= 1568 for side in picture.size):
                raise ValueError('Screenshot must be a still PNG, 280–1568 pixels per side')
            picture.verify()
        case['_png'] = raw  # Freeze the verified bytes for both conditions and the reported hash.
    return cases


def request_body(case, with_image, root):
    # Both conditions receive identical coordinates and rules: this tests redundant visual context.
    body = {'model': MODEL, 'state': {'focal': case['focal'], 'candidates': case['candidates']},
            'questions': {'neighbor': {'type': 'choice', 'instructions':
                'Choose the nearest eligible neighbor to focal, using Euclidean distance between feet coordinates. '
                'All three candidates are available socializers. Break equal-distance ties by lowest resident ID. '
                'F marks focal; A/B/C mark candidates if a scene image is present. x increases right, y down.',
                'criteria': {key: f"Approach {person['name']} ({person['id']})." for key, person in case['candidates'].items()}}}}
    if with_image:
        reference = str(uuid.uuid4())
        body['state']['scene'] = reference
        body['assets'] = {reference: {'type': 'image', 'format': 'png',
            'data_base64': base64.b64encode(case['_png']).decode('ascii')}}
    return body


def save_report(root, report, live):
    report['summary'] = {}
    for condition in ('structured', 'image'):
        scored = [row for row in report['results'] if row['condition'] == condition and isinstance(row['correct'], bool)]
        report['summary'][condition] = {'scoredCases': len(scored),
            'accuracy': sum(row['correct'] for row in scored) / len(scored) if scored else None}
    destination = root / ('report-live.json' if live else 'report-mock.json')
    temporary = destination.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    temporary.replace(destination)


def compare(bundle, live=False):
    root = Path(bundle).resolve()
    cases = load_cases(root)
    if live and not os.environ.get('JEV_KEY'):
        load_dotenv(Path(__file__).resolve().parents[1] / '.env', override=False)
    key = os.environ.get('JEV_KEY') if live else None
    if live and not key:
        raise ValueError('JEV_KEY is missing from the process environment and project .env.')
    report = {'mode': 'live' if live else 'mock-oracle', 'model': MODEL, 'status': 'running',
              'startedAtUTC': datetime.now(timezone.utc).isoformat(),
              'requestLimit': 6, 'requestsMade': 0, 'concurrency': 1, 'retries': 0,
              'manifestSha256': hashlib.sha256((root / 'cases.json').read_bytes()).hexdigest(),
              'limitation': 'Three views of one mock meeting; redundant coordinates in both conditions. Not evidence of general vision quality or improved town behavior.',
              'results': []}
    save_report(root, report, live)
    for index, case in enumerate(cases):
        # Counterbalance order; do not let successful results decide which requests run next.
        for condition in (['structured', 'image'] if index % 2 == 0 else ['image', 'structured']):
            expected = expected_choice(case)
            row = {'caseId': case['id'], 'condition': condition, 'expected': expected,
                   'imageSha256': case['imageSha256'], 'choice': expected if not live else None,
                   'confidence': None, 'correct': None, 'elapsedMs': None, 'inputTokens': None}
            if live:
                headers = {'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}
                if condition == 'image': headers['TypeSafe-Danger-Zone-Images'] = 'true'
                report['requestsMade'] += 1
                save_report(root, report, live)  # A crash leaves the in-flight attempt marked running, never complete.
                started = time.monotonic()
                try:
                    response = requests.post(URL, json=request_body(case, condition == 'image', root),
                                             headers=headers, timeout=30, allow_redirects=False)
                    if not response.ok or response.status_code != 200:
                        raise ValueError(f'http_{response.status_code}')
                    try:
                        data = response.json()
                    except ValueError:
                        raise ValueError('invalid_response') from None
                    answer = data['answers']['neighbor']
                    choice, confidence = answer['choice'], answer['confidence']
                    if (choice not in case['candidates'] or isinstance(confidence, bool) or
                        not isinstance(confidence, (float, int)) or not math.isfinite(confidence) or not 0 <= confidence <= 1):
                        raise ValueError('invalid_response')
                    row.update(choice=choice, confidence=confidence, correct=choice == expected)
                    usage = data.get('usage')
                    tokens = usage.get('input_tokens') if isinstance(usage, dict) else None
                    if isinstance(tokens, int) and not isinstance(tokens, bool) and tokens >= 0: row['inputTokens'] = tokens
                except requests.RequestException:
                    report.update(status='stopped', error='network_error')
                except (ValueError, KeyError, TypeError, AttributeError) as error:
                    code = str(error)
                    report.update(status='stopped', error=code if re.fullmatch(r'http_\d{3}', code) else 'invalid_response')
                row['elapsedMs'] = round((time.monotonic() - started) * 1000, 2)
            report['results'].append(row)
            save_report(root, report, live)
            if report['status'] == 'stopped': return report
    report['status'] = 'complete'
    save_report(root, report, live)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, default=Path('.artifacts/vision'))
    parser.add_argument('--live', action='store_true', help='Make at most six billed requests; load project .env if process JEV_KEY is absent; no retries')
    options = parser.parse_args()
    try:
        result = compare(options.bundle, live=options.live)
    except (ValueError, KeyError, TypeError, OSError):
        # Do not echo arbitrary filenames, server bodies, payloads or credentials.
        parser.exit(1, 'Experiment not started: check the bundle and JEV_KEY in the environment or project .env for --live.\n')
    print(f"{result['mode']}: {result['status']}; {result['requestsMade']}/6 requests. Report saved inside the bundle.")
    if result['status'] == 'stopped': raise SystemExit(1)
