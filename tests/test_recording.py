import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

os.environ['JEV_MOCK'] = '1'
import town
from simulation.world import destination, path, WALKABLE


class AdapterTests(unittest.TestCase):
    def response(self, choice='work', confidence=.7, status=200):
        response=Mock(ok=status==200,status_code=status,headers={})
        response.json.return_value={'answers':{'next_action':{'choice':choice,'confidence':confidence}}}
        return response

    def test_invalid_choice_and_confidence_are_errors_not_wandering(self):
        for choice,confidence in [('fight',.8),('work',float('nan')),('work',float('inf')),
                                  ('work',-.1),('work',1.1),('work','high'),('work',True)]:
            with self.subTest(choice=choice,confidence=confidence),patch('town.requests.post',return_value=self.response(choice,confidence)):
                with self.assertRaises(town.DecisionError) as caught:
                    town.jev_decide(town.NPC('npc00'),14)
                self.assertEqual(caught.exception.code,'invalid_response')

    def test_retry_after_and_exhaustion_are_bounded(self):
        limited=self.response(status=429);limited.headers={'Retry-After':'3'}
        with patch('town.requests.post',side_effect=[limited,self.response()]) as post,patch('town.time.sleep') as sleep:
            self.assertEqual(town.jev_decide(town.NPC('npc00'),14),('work',.7))
            sleep.assert_called_once_with(3);self.assertEqual(post.call_count,2)
            self.assertEqual(post.call_args.kwargs['timeout'],60)
        limited.headers={'Retry-After':'NaN'}
        with patch('town.requests.post',return_value=limited) as post,patch('town.time.sleep') as sleep:
            with self.assertRaises(town.DecisionError) as caught:town.jev_decide(town.NPC('npc00'),14)
            self.assertEqual(caught.exception.code,'retries_exhausted')
            self.assertEqual(post.call_count,6);self.assertEqual(sleep.call_count,5)
            self.assertTrue(all(0<=call.args[0]<=60 for call in sleep.call_args_list))

    def test_diagnostic_response_redacts_key_and_authorization(self):
        response=self.response(status=401);response.text='Invalid Bearer secret-test-key / secret-test-key'
        with patch('town.KEY','secret-test-key'),patch('town.AUTH','Bearer secret-test-key'),patch('town.requests.post',return_value=response):
            with self.assertRaises(town.DecisionError) as caught:town.jev_decide(town.NPC('npc00'),14)
            self.assertNotIn('secret-test-key',str(caught.exception))
            self.assertIn('Invalid',str(caught.exception))

    def test_error_fallback_is_explicit_and_not_low_confidence(self):
        npc=town.NPC('npc00')
        error=town.DecisionError('http_503','Unavailable')
        with patch('town.KEY','test'),patch('town.jev_decide',side_effect=error),patch('town.ERROR_FALLBACK','stop'):
            before=(npc.hunger,npc.energy,npc.mood,npc.money)
            with self.assertRaises(town.DecisionError):town.step(npc,14)
            self.assertEqual(before,(npc.hunger,npc.energy,npc.mood,npc.money))
        with patch('town.KEY','test'),patch('town.jev_decide',side_effect=error),patch('town.ERROR_FALLBACK','mock'):
            town.step(npc,14)
        self.assertEqual(npc.decision_source,'error-mock');self.assertEqual(npc.error_code,'http_503')
        self.assertIsNone(npc.confidence);self.assertIsNone(npc.chosen_action);self.assertFalse(npc.fell_back)


class RecordingTests(unittest.TestCase):
    def test_all_30_same_action_have_unique_reachable_destinations(self):
        for action in town.ACTIONS:
            with self.subTest(action=action):
                destinations=[destination(i,action,14,7) for i in range(30)]
                self.assertEqual(len({(p['x'],p['y']) for p in destinations}),30)
                if action in ('wander', 'work'):
                    for i, a in enumerate(destinations):
                        for b in destinations[i + 1:]:
                            self.assertGreaterEqual((a['x']-b['x'])**2+(a['y']-b['y'])**2, 32**2)
                for p in destinations:
                    route=path((21,15),(p['x']//16,p['y']//16))
                    self.assertTrue(all(tile in WALKABLE for tile in route))
                    water=[y for x,y in route if 57<=x<60]
                    self.assertTrue(all(22<=y<25 for y in water))

    def test_bridge_is_only_crossing(self):
        route=path((55,21),(62,21))
        self.assertTrue(all(22<=y<25 for x,y in route if 57<=x<60))
        self.assertNotIn((5,4),WALKABLE);self.assertNotIn((26,18),WALKABLE)

    def test_mock_recording_has_contiguous_25_boundaries_and_no_secrets(self):
        with tempfile.TemporaryDirectory() as folder,patch('town.KEY',None),patch('town.plot'),patch('simulation.exports.export_replay',return_value=True),patch('town.requests.post',side_effect=AssertionError('No network')),contextlib.redirect_stdout(io.StringIO()):
            recording=town.main(output_dir=folder,show_chart=False)
            saved=json.loads((Path(folder)/'run.json').read_text())
            self.assertEqual(saved,recording)
        self.assertEqual(len(saved['residents']),30);self.assertEqual(len(saved['frames']),24)
        for h,frame in enumerate(saved['frames']):
            self.assertEqual(frame['sequence'],h+1)
            for i,resident in enumerate(frame['residents']):
                previous=saved['frames'][h-1]['residents'][i]['after'] if h else saved['initialSnapshot'][i]['stats']
                self.assertEqual(resident['before'],previous)
                self.assertTrue(all(0<=resident['after'][key]<=100 for key in ('hunger','energy','mood')))
                if resident['interaction']:
                    self.assertEqual(resident['decision']['appliedAction'], 'socialize')
                    for partner in resident['interaction']['partnerIds']:
                        other=next(p for p in frame['residents'] if p['id']==partner)
                        self.assertIn(resident['id'],other['interaction']['partnerIds'])
        serialized=json.dumps(saved)
        for forbidden in ('Authorization','JEV_KEY','Bearer','api.typesafe.ai'):
            self.assertNotIn(forbidden,serialized)

    def test_failed_hour_does_not_overwrite_last_good_recording(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'run.json';target.write_text('last-good-recording')
            with patch('town.KEY','test'),patch('town.ERROR_FALLBACK','stop'),patch('town.jev_decide',side_effect=town.DecisionError('network_error','Unavailable')):
                with self.assertRaises(town.DecisionError):town.main(output_dir=folder)
            self.assertEqual(target.read_text(),'last-good-recording')


if __name__=='__main__':unittest.main()
