import copy
import unittest

from scripts.make_visual_fixture import fixture
from simulation.visitors import bench_plans
from simulation.world import WALKABLE, path


class VisitorTests(unittest.TestCase):
    def test_plans_preserve_decisions_stats_and_original_recording(self):
        run = fixture(30)
        original = copy.deepcopy(run)
        plans = bench_plans(run)
        self.assertEqual(run, original)
        self.assertEqual(len(plans), 2)
        for plan in plans:
            self.assertEqual(len(plan['frames']), 24)
            for frame, changes in zip(run['frames'], plan['frames']):
                positions = {p['id']: p['destination'] for p in frame['residents']}
                for change in changes:
                    person = next(p for p in frame['residents'] if p['id'] == change['id'])
                    self.assertEqual(person['decision']['appliedAction'], 'wander')
                    self.assertIsNone(person['interaction'])
                    positions[person['id']] = change['destination']
                    tile = (change['destination']['x']//16, change['destination']['y']//16)
                    self.assertIn(tile, WALKABLE)
                    path((21,14), tile)
                coords = [(p['x'],p['y']) for p in positions.values()]
                self.assertEqual(len(coords), len(set(coords)))
        self.assertTrue(any(plans[0]['frames']))

    def test_no_visitors_when_everyone_is_asleep(self):
        plans = bench_plans(fixture(30, 'sleep'))
        self.assertTrue(all(not frame for plan in plans for frame in plan['frames']))


if __name__ == '__main__':
    unittest.main()
