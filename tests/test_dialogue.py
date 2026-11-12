import copy
import unittest

from simulation.dialogue import scripted_conversations
from simulation.identities import manifest
from simulation.interactions import plan_interactions


def group(count):
    people = manifest(count)
    entries = [{'id': p['id'], 'before': {'hunger': 30, 'energy': 70, 'mood': 60},
                'decision': {'appliedAction': 'socialize'}} for p in people]
    plan_interactions(entries, 14, 7)
    return entries, people


class DialogueTests(unittest.TestCase):
    def test_one_recorded_script_per_group_without_mutating_world(self):
        for count in range(1, 31):
            entries, people = group(count)
            before = copy.deepcopy(entries)
            chats = scripted_conversations(entries, people, 14, 7)
            self.assertEqual(entries, before)
            self.assertEqual(chats, scripted_conversations(entries[::-1], people[::-1], 14, 7))
            self.assertEqual(len({p for c in chats for p in c['participantIds']}), count if count > 1 else 0)
            for chat in chats:
                self.assertEqual(chat['source'], 'scripted')
                self.assertTrue(2 <= len(chat['participantIds']) <= 4)
                self.assertTrue(2 <= len(chat['turns']) <= 4)
                self.assertEqual({t['speakerId'] for t in chat['turns']}, set(chat['participantIds']))
                self.assertTrue(all(0 < len(t['text']) <= 180 for t in chat['turns']))

    def test_personality_and_before_needs_shape_lines_not_actions(self):
        entries, people = group(2)
        normal = scripted_conversations(entries, people, 14, 7)
        people[1]['trait'] = 'lazy'
        lazy = scripted_conversations(entries, people, 14, 7)
        self.assertNotEqual(normal[0]['turns'][1]['text'], lazy[0]['turns'][1]['text'])
        entries[1]['before']['energy'] = 10
        tired = scripted_conversations(entries, people, 14, 7)
        self.assertIn('tired', tired[0]['turns'][1]['text'])
        self.assertTrue(all(p['decision']['appliedAction'] == 'socialize' for p in entries))

    def test_fallback_wander_and_lone_socializer_get_no_dialogue(self):
        entries, people = group(2)
        entries[1]['decision'].update(chosenAction='socialize', appliedAction='wander', fellBack=True)
        plan_interactions(entries, 14, 7)
        self.assertEqual(scripted_conversations(entries, people, 14, 7), [])
