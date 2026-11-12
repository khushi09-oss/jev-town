import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from PIL import Image
from scripts.vision_compare import compare, expected_choice


class VisionComparisonTests(unittest.TestCase):
    def bundle(self, folder):
        import hashlib
        root = Path(folder)
        Image.new('RGB', (1120, 748)).save(root / 'scene.png')
        person = lambda i, x: {'id': f'npc{i:02d}', 'name': str(i), 'x': x, 'y': 200}
        cases = [{'id': f'case-{i}', 'image': 'scene.png',
                  'imageSha256': hashlib.sha256((root / 'scene.png').read_bytes()).hexdigest(),
                  'focal': person(0, 100),
                  'candidates': {'A': person(1, 90), 'B': person(2, 120), 'C': person(3, 150)}} for i in range(3)]
        (root / 'cases.json').write_text(json.dumps({'schemaVersion': 1, 'cases': cases}))
        return root

    def test_mock_is_offline_and_does_not_claim_model_accuracy(self):
        with tempfile.TemporaryDirectory() as folder, patch('scripts.vision_compare.requests.post') as post, \
                patch('scripts.vision_compare.load_dotenv') as load:
            report = compare(self.bundle(folder))
            post.assert_not_called()
            load.assert_not_called()
            self.assertEqual(report['requestsMade'], 0)
            self.assertTrue(all(row['correct'] is None for row in report['results']))
            self.assertEqual(report['mode'], 'mock-oracle')
            self.assertEqual(report['status'], 'complete')
            self.assertIsNone(report['summary']['image']['accuracy'])

    def test_live_sends_six_matched_requests_and_only_images_get_opt_in(self):
        response = Mock(ok=True, status_code=200)
        response.json.return_value = {'answers': {'neighbor': {'choice': 'A', 'confidence': .8}},
                                      'usage': {'input_tokens': 123}}
        with tempfile.TemporaryDirectory() as folder, patch.dict('os.environ', {'JEV_KEY': 'test-secret'}), \
                patch('scripts.vision_compare.requests.post', return_value=response) as post:
            report = compare(self.bundle(folder), live=True)
            self.assertEqual(post.call_count, 6)
            self.assertEqual(report['requestsMade'], 6)
            self.assertTrue(all(row['correct'] for row in report['results']))
            for i in range(0, 6, 2):
                pair = post.call_args_list[i:i+2]
                bodies = [call.kwargs['json'] for call in pair]
                text, image = sorted(bodies, key=lambda body: 'assets' in body)
                import copy
                stripped = copy.deepcopy(image)
                del stripped['assets']; del stripped['state']['scene']
                self.assertEqual(text, stripped)
                for call in pair:
                    self.assertFalse(call.kwargs['allow_redirects'])
                    self.assertEqual(call.kwargs['timeout'], 30)
                    self.assertEqual('TypeSafe-Danger-Zone-Images' in call.kwargs['headers'], 'assets' in call.kwargs['json'])
            self.assertNotIn('test-secret', json.dumps(report))

    def test_missing_process_key_and_invalid_answers_never_fabricate_success(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict('os.environ', {}, clear=True), \
                patch('scripts.vision_compare.load_dotenv', return_value=False), \
                patch('scripts.vision_compare.requests.post') as post:
            with self.assertRaises(ValueError): compare(self.bundle(folder), live=True)
            post.assert_not_called()
        for answer in [{'choice':'D','confidence':.8}, {'choice':'A','confidence':True},
                       {'choice':'A','confidence':float('nan')}]:
            response=Mock(ok=True,status_code=200)
            response.json.return_value={'answers':{'neighbor':answer}}
            with tempfile.TemporaryDirectory() as folder, patch.dict('os.environ', {'JEV_KEY':'test-secret'}), \
                    patch('scripts.vision_compare.requests.post',return_value=response) as post:
                report=compare(self.bundle(folder),live=True)
                self.assertEqual(report['error'],'invalid_response')
                self.assertIsNone(report['results'][0]['correct'])
                self.assertEqual(post.call_count,1)

    def test_live_loads_project_env_only_when_process_key_is_missing(self):
        def fake_load(*args, **kwargs):
            import os
            os.environ['JEV_KEY'] = 'file-test-secret'
        response = Mock(ok=True, status_code=200)
        response.json.return_value = {'answers': {'neighbor': {'choice': 'A', 'confidence': .8}}}
        with tempfile.TemporaryDirectory() as folder, patch.dict('os.environ', {}, clear=True), \
                patch('scripts.vision_compare.load_dotenv', side_effect=fake_load) as load, \
                patch('scripts.vision_compare.requests.post', return_value=response) as post:
            report = compare(self.bundle(folder), live=True)
            load.assert_called_once_with(Path(__file__).resolve().parents[1] / '.env', override=False)
            self.assertEqual(post.call_count, 6)
            self.assertEqual(report['status'], 'complete')
            self.assertNotIn('file-test-secret', json.dumps(report))

    def test_errors_stop_without_retries_or_leaking_response(self):
        response = Mock(ok=False, status_code=429, text='test-secret raw server body')
        with tempfile.TemporaryDirectory() as folder, patch.dict('os.environ', {'JEV_KEY': 'test-secret'}), \
                patch('scripts.vision_compare.requests.post', return_value=response) as post:
            report = compare(self.bundle(folder), live=True)
            self.assertEqual(post.call_count, 1)
            self.assertEqual(report['status'], 'stopped')
            self.assertEqual(report['error'], 'http_429')
            self.assertNotIn('test-secret', (Path(folder) / 'report-live.json').read_text())

    def test_ties_use_stable_id_and_inputs_are_validated_before_network(self):
        case = {'focal': {'x': 100, 'y': 100}, 'candidates': {
            'A': {'id': 'npc02', 'x': 90, 'y': 100}, 'B': {'id': 'npc01', 'x': 110, 'y': 100}}}
        self.assertEqual(expected_choice(case), 'B')
        with tempfile.TemporaryDirectory() as folder, patch('scripts.vision_compare.requests.post') as post:
            root = self.bundle(folder)
            data = json.loads((root / 'cases.json').read_text())
            for bad_path in ('../private.png', '.env'):
                data['cases'][0]['image'] = bad_path
                (root / 'cases.json').write_text(json.dumps(data))
                with self.assertRaises(ValueError): compare(root, live=True)
            post.assert_not_called()
