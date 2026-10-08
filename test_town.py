import unittest
from unittest.mock import Mock, patch

import town


class PersonalityTests(unittest.TestCase):
    def test_identical_stats_produce_different_personality_choices(self):
        choices = [town.mock_decide(town.NPC('npc', trait=trait,
                   hunger=30, energy=45, mood=60, money=40), 14)[0]
                   for trait in ('lazy', 'social', 'workaholic')]
        self.assertEqual(choices, ['sleep', 'socialize', 'work'])

    def test_urgent_needs_override_personality(self):
        for trait in ('lazy', 'social', 'workaholic'):
            with self.subTest(trait=trait):
                self.assertEqual(town.mock_decide(town.NPC('npc', trait=trait,
                                 hunger=80), 14)[0], 'eat')
                self.assertEqual(town.mock_decide(town.NPC('npc', trait=trait,
                                 energy=10), 14)[0], 'sleep')

    def test_personality_is_sent_to_jev(self):
        response = Mock(ok=True, status_code=200)
        response.json.return_value = {'answers': {'next_action':
                                     {'choice': 'work', 'confidence': 0.9}}}
        with patch('town.requests.post', return_value=response) as post:
            self.assertEqual(town.jev_decide(town.NPC('npc', trait='workaholic'), 14),
                             ('work', 0.9))
        self.assertEqual(post.call_args.kwargs['json']['state']['personality'],
                         'workaholic')

    def test_nighttime_overrides_personality(self):
        for trait in ('lazy', 'social', 'workaholic'):
            for hour in (0, 5, 22, 23):
                with self.subTest(trait=trait, hour=hour):
                    self.assertEqual(town.mock_decide(town.NPC('npc', trait=trait),
                                     hour)[0], 'sleep')

    def test_low_confidence_still_falls_back_and_clamps_stats(self):
        npc = town.NPC('npc', trait='workaholic', hunger=99, mood=99, money=0)
        with patch('town.KEY', 'test'), patch('town.MIN_CONFIDENCE', 0.2), \
                patch('town.jev_decide', return_value=('work', 0.1)):
            self.assertEqual(town.step(npc, 14), 0.1)
        self.assertTrue(npc.fell_back)
        self.assertEqual(npc.last, 'wander')
        self.assertEqual((npc.hunger, npc.mood, npc.money), (100, 100, 0))

    def test_simulation_records_balanced_traits_and_action_totals(self):
        with patch('town.KEY', None), patch('town.export_html'), patch('town.plot') as plot:
            town.main(n_npcs=6, ticks=2)
        history = plot.call_args.args[0]
        for hour in history:
            self.assertEqual(set(hour['trait_counts']), {'lazy', 'social', 'workaholic'})
            self.assertTrue(all(sum(counts.values()) == 2
                                for counts in hour['trait_counts'].values()))
            self.assertEqual(sum(hour['counts'].values()), 6)


if __name__ == '__main__':
    unittest.main()
