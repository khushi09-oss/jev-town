import copy
import unittest

from simulation.interactions import plan_interactions
from simulation.world import WALKABLE, path, destination


def entries(count, action='socialize'):
    return [{'id': f'npc{i:02d}', 'decision': {'appliedAction': action},
             'destination': {}} for i in range(count)]


class InteractionTests(unittest.TestCase):
    def test_conversation_slots_do_not_overlap_square_work_stations(self):
        workers = {(p['x'],p['y']) for p in (destination(i,'work',14,7) for i in range(30))}
        people = entries(30)
        plan_interactions(people,14,7)
        self.assertFalse(workers & {(p['destination']['x'],p['destination']['y']) for p in people})
    def test_socializers_share_small_groups_even_when_ids_are_far_apart(self):
        people = entries(30, 'wander')
        for i in (0, 12, 27):
            people[i]['decision']['appliedAction'] = 'socialize'
        plan_interactions(people, 14, 7)
        for i in (0, 12, 27):
            self.assertEqual(people[i]['interaction']['partnerIds'],
                             [f'npc{j:02d}' for j in (0, 12, 27) if i != j])
        self.assertIsNone(people[1]['interaction'])

    def test_every_occupancy_has_reciprocal_partners_and_unique_reachable_slots(self):
        for count in range(1, 31):
            people = entries(count)
            plan_interactions(people, 14, 7)
            positions = {(p['destination']['x'], p['destination']['y']) for p in people}
            self.assertEqual(len(positions), count)
            for p in people:
                dest = p['destination']
                self.assertTrue(all(tile in WALKABLE for tile in path((21, 15), (dest['x']//16, dest['y']//16))))
                if count == 1:
                    self.assertIsNone(p['interaction'])
                    continue
                partners = p['interaction']['partnerIds']
                self.assertTrue(1 <= len(partners) <= 3)
                for partner in partners:
                    other = next(q for q in people if q['id'] == partner)
                    self.assertIn(p['id'], other['interaction']['partnerIds'])
                    self.assertLessEqual(abs(dest['x']-other['destination']['x']), 16)
                    self.assertLessEqual(abs(dest['y']-other['destination']['y']), 32)

    def test_planning_is_deterministic_and_uses_applied_actions(self):
        people = entries(13)
        people[0]['decision'].update(chosenAction='socialize', appliedAction='wander', fellBack=True)
        other = copy.deepcopy(people[::-1])
        plan_interactions(people, 14, 7)
        plan_interactions(other, 14, 7)
        self.assertEqual(people, sorted(other, key=lambda p: p['id']))
        self.assertIsNone(people[0]['interaction'])
