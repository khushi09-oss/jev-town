"""Saved factual meeting counts, committed only at recorded hour boundaries."""
from itertools import combinations
import json
import math
from pathlib import Path
from .world import WALKABLE


def validate_memories(memories, ids, day, hour=0):
    if not isinstance(memories,list) or len(memories)>435:
        raise ValueError('Invalid saved memories')
    seen=set()
    for memory in memories:
        if not isinstance(memory,dict) or set(memory)!={'residentIds','meetings','lastMetDay','lastMetHour'}:
            raise ValueError('Invalid saved memory fields')
        pair=memory['residentIds']
        if not isinstance(pair,list) or len(pair)!=2 or not all(isinstance(p,str) and p in ids for p in pair):
            raise ValueError('Unknown memory participants')
        if pair!=sorted(set(pair)) or tuple(pair) in seen:
            raise ValueError('Duplicate or unordered memory pair')
        seen.add(tuple(pair))
        for key,low,high in [('meetings',1,1_000_000),('lastMetDay',1,day),('lastMetHour',0,23)]:
            value=memory[key]
            if type(value) is not int or not low<=value<=high:
                raise ValueError('Invalid memory count or date')
        if (memory['lastMetDay'],memory['lastMetHour'])>=(day,hour):
            raise ValueError('Memory comes from a future meeting hour')


def memory_state(recording):
    state={tuple(p['residentIds']):dict(p) for p in recording.get('initialMemories',[])}
    for frame in recording['frames']:
        for memory in frame.get('memoryUpdates',[]):state[tuple(memory['residentIds'])]=dict(memory)
    return state


def record_meetings(recording,frame):
    state=memory_state(recording)
    updates=[]
    for chat in frame.get('conversations',[]):
        for pair in combinations(sorted(chat['participantIds']),2):
            count=state.get(pair,{}).get('meetings',0)+1
            if count>1_000_000:raise ValueError('Meeting count limit reached')
            updates.append({'residentIds':list(pair),'meetings':count,
                            'lastMetDay':recording['dayNumber']+(recording.get('startHour',0)+frame.get('tick',0))//24,
                            'lastMetHour':frame['clockHour']})
    frame['memoryUpdates']=sorted(updates,key=lambda p:p['residentIds'])


def remember_from(filename,identities):
    path=Path(filename).resolve()
    if path.suffix.lower()!='.json' or path.stat().st_size>5_000_000:
        raise ValueError('Memory source must be a saved JSON day under 5 MB')
    old=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(old,dict):raise ValueError('Memory source must be a recorded day')
    ids=[p['id'] for p in identities]
    if (type(old.get('schemaVersion')) is not int or old.get('schemaVersion')!=1 or
        type(old.get('hours')) is not int or old.get('hours')!=24 or old.get('worldId')!='tiny-town-v1' or
        type(old.get('startHour')) is not int or not 0<=old['startHour']<=23 or
        [p['id'] for p in old.get('residents',[])]!=ids or len(old.get('frames',[]))!=24 or
        type(old.get('dayNumber')) is not int or not 1<=old['dayNumber']<100_000 or 'initialMemories' not in old):
        raise ValueError('Use a complete memory-enabled recording with the same resident IDs')
    validate_memories(old['initialMemories'],ids,old['dayNumber'],old['startHour'])
    history={'dayNumber':old['dayNumber'],'startHour':old['startHour'],'initialMemories':old['initialMemories'],'frames':[]}
    for tick,frame in enumerate(old['frames']):
        if (not isinstance(frame,dict) or any(type(frame.get(key)) is not int for key in ('tick','sequence','clockHour')) or
            frame.get('tick')!=tick or frame.get('sequence')!=tick+1 or
            frame.get('clockHour')!=(old.get('startHour',0)+tick)%24 or
            [p['id'] for p in frame.get('residents',[])]!=ids):
            raise ValueError('Invalid memory recording sequence')
        members=set()
        for chat in frame.get('conversations',[]):
            if not isinstance(chat,dict) or chat.get('source')!='scripted':raise ValueError('Unsupported recorded conversation source')
            people=chat['participantIds']
            if len(people) not in (2,3,4) or len(set(people))!=len(people) or any(p not in ids or p in members for p in people):
                raise ValueError('Invalid recorded meeting')
            for person in people:
                entry=next((p for p in frame['residents'] if p['id']==person),None)
                interaction=entry.get('interaction') if entry else None
                if (not isinstance(interaction,dict) or entry['decision']['appliedAction']!='socialize' or
                    sorted([person,*interaction.get('partnerIds',[])])!=sorted(people)):
                    raise ValueError('Meeting does not match recorded partners')
            members.update(people)
            destinations=[next(p for p in frame['residents'] if p['id']==person)['destination'] for person in people]
            for destination in destinations:
                if not isinstance(destination,dict) or destination.get('locationId')!='square':raise ValueError('Meeting outside the square')
                for axis in ('x','y'):
                    value=destination.get(axis)
                    if type(value) not in (int,float) or not math.isfinite(value):raise ValueError('Invalid meeting position')
                if (math.floor(destination['x']/16),math.floor(destination['y']/16)) not in WALKABLE:
                    raise ValueError('Meeting position is not walkable')
            if (len({(p['x'],p['y']) for p in destinations})!=len(people) or
                max(p['x'] for p in destinations)-min(p['x'] for p in destinations)>16 or
                max(p['y'] for p in destinations)-min(p['y'] for p in destinations)>32):
                raise ValueError('Meeting partners are not nearby')
        expected=dict(frame)
        record_meetings(history,expected)
        validate_memories(frame.get('memoryUpdates'),ids,
                          old['dayNumber']+(old['startHour']+tick)//24,frame['clockHour']+1)
        if frame.get('memoryUpdates')!=expected['memoryUpdates']:
            raise ValueError('Saved memory counts disagree with recorded meetings')
        history['frames'].append(expected)
    memories=list(memory_state(history).values())
    next_day=old['dayNumber']+1+(1 if old['startHour'] else 0)
    if next_day>100_000:raise ValueError('Saved day limit reached')
    validate_memories(memories,ids,next_day)
    return next_day,memories
