import copy
import unittest
import tempfile
import json
import os
import contextlib
import io
from unittest.mock import patch
from pathlib import Path
from simulation.memories import remember_from
from simulation.identities import manifest
from scripts.make_visual_fixture import fixture
from simulation.memories import memory_state, record_meetings, validate_memories


class MemoryTests(unittest.TestCase):
    def test_shifted_clock_records_midnight_and_carries_to_the_next_midnight(self):
        run=fixture(6,'socialize',with_memories=True)
        run['startHour']=18
        for frame in run['frames']:
            frame['clockHour']=(18+frame['tick'])%24
            for update in frame['memoryUpdates']:
                update['lastMetDay']=1+(18+frame['tick'])//24
                update['lastMetHour']=frame['clockHour']
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'run.json';path.write_text(json.dumps(run))
            day,memories=remember_from(path,manifest(6))
            self.assertEqual(day,3)
            self.assertTrue(all(p['lastMetDay']==2 for p in memories))

    def test_two_saved_days_preserve_memory_without_changing_decisions_or_stats(self):
        with patch.dict(os.environ,{'JEV_MOCK':'1'}):
            import town
        with tempfile.TemporaryDirectory() as folder,patch.object(town,'KEY',None),patch.object(town,'plot'), \
                patch('simulation.exports.export_replay',return_value=True), \
                patch('town.requests.post',side_effect=AssertionError('No network')),contextlib.redirect_stdout(io.StringIO()):
            first=town.main(6,output_dir=Path(folder)/'first',show_chart=False)
            path=Path(folder)/'first'/'run.json'
            original=path.read_bytes()
            second=town.main(6,output_dir=Path(folder)/'second',show_chart=False,remember_from=path)
            self.assertEqual(path.read_bytes(),original)
            self.assertEqual(second['dayNumber'],2)
            self.assertEqual(second['initialMemories'],remember_from(path,manifest(6))[1])
            self.assertTrue(second['initialMemories'])
            for a,b in zip(first['frames'],second['frames']):self.assertEqual(a['residents'],b['residents'])
            day,memories=remember_from(Path(folder)/'second'/'run.json',manifest(6))
            self.assertEqual(day,3)
            previous=memory_state(first)
            for memory in memories:self.assertEqual(memory['meetings'],previous[tuple(memory['residentIds'])]['meetings']*2)
            with self.assertRaises(ValueError):remember_from(Path(folder)/'.env',manifest(6))
    def test_reunions_use_past_counts_and_carry_to_next_day_without_mutation(self):
        run=fixture(6,'socialize',with_memories=True)
        self.assertNotIn('again',run['frames'][0]['conversations'][0]['turns'][0]['text'])
        self.assertIn('shared 1 break before',run['frames'][1]['conversations'][0]['turns'][0]['text'])
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'run.json';path.write_text(json.dumps(run))
            day,memories=remember_from(path,manifest(6))
            self.assertEqual(day,2)
            self.assertTrue(all(p['meetings']==24 for p in memories))
            original=path.read_bytes()
            run['frames'][0]['memoryUpdates'][0]['meetings']=True
            path.write_text(json.dumps(run))
            with self.assertRaises(ValueError):remember_from(path,manifest(6))
            tampered=json.loads(original)
            tampered['frames'][0]['residents'][1]['destination']['x']+=64
            path.write_text(json.dumps(tampered))
            with self.assertRaises(ValueError):remember_from(path,manifest(6))
            tampered=json.loads(original)
            tampered['frames'][0]['tick']=False
            path.write_text(json.dumps(tampered))
            with self.assertRaises(ValueError):remember_from(path,manifest(6))
            path.write_bytes(original)
            self.assertEqual(remember_from(path,manifest(6)),(day,memories))

    def test_pair_counts_are_once_per_group_and_before_updates_stay_immutable(self):
        run={'dayNumber':1,'initialMemories':[],'frames':[]}
        frame={'clockHour':9,'conversations':[{'participantIds':['npc00','npc01','npc02']}]}
        before=copy.deepcopy(run)
        record_meetings(run,frame)
        self.assertEqual(len(frame['memoryUpdates']),3)
        self.assertEqual(run,before)
        run['frames'].append(frame)
        self.assertTrue(all(p['meetings']==1 for p in memory_state(run).values()))
        second={'clockHour':10,'conversations':[{'participantIds':['npc00','npc01']}]}
        record_meetings(run,second)
        self.assertEqual(second['memoryUpdates'][0]['meetings'],2)
        self.assertEqual(memory_state(run)[('npc00','npc01')]['meetings'],1)

    def test_invalid_initial_pairs_counts_and_future_dates_are_rejected(self):
        valid={'residentIds':['npc00','npc01'],'meetings':2,'lastMetDay':1,'lastMetHour':10}
        validate_memories([valid],['npc00','npc01'],2)
        for update in [{'residentIds':['npc00','npc00']},{'meetings':True},{'meetings':0},
                       {'lastMetDay':2},{'lastMetHour':24}]:
            with self.assertRaises(ValueError):validate_memories([{**valid,**update}],['npc00','npc01'],2)
        with self.assertRaises(ValueError):validate_memories([valid,valid],['npc00','npc01'],2)
