"""Record immutable before/after boundaries with authoritative destinations."""
import json
import os
from .world import destination
from .interactions import plan_interactions


def stats(npc):
    return {name: getattr(npc, name) for name in ('hunger', 'energy', 'mood', 'money')}


def start_recording(town, identities, seed, mode):
    return {'schemaVersion': 1, 'runId': f'tiny-town-{seed}-{mode}-v1', 'seed': seed,
            'mode': mode, 'fixtureKind': 'simulation', 'hours': 24, 'startHour': 0,
            'worldId': 'tiny-town-v1', 'residents': [
                {k: p[k] for k in ('id','name','trait','appearanceId','homeId')} for p in identities],
            'initialSnapshot': [{'id': n.name, 'stats': stats(n), 'position':
                {k:v for k,v in destination(i,'socialize',0,seed).items() if k in ('x','y')}}
                for i,n in enumerate(town)], 'frames': []}


def append_frame(recording, before, after, tick):
    entries = []
    for i,(old,new) in enumerate(zip(before, after)):
        entries.append({'id': new.name, 'before': stats(old), 'after': stats(new),
                        'decision': {'chosenAction': new.chosen_action, 'confidence': new.confidence,
                            'appliedAction': new.last, 'fellBack': new.fell_back,
                            'decisionSource': new.decision_source, 'errorCode': new.error_code},
                        'destination': destination(i,new.last,tick,recording['seed'])})
    plan_interactions(entries, tick, recording['seed'])
    recording['frames'].append({'tick':tick,'clockHour':tick%24,'sequence':tick+1,'residents':entries})
    if any(n.decision_source=='error-mock' for n in after):
        recording['mode']='mixed'


def write_recording(recording, path):
    if len(recording['frames']) != 24:
        raise ValueError('Only a complete 24-hour recording can replace run.json')
    temporary = path.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(recording, ensure_ascii=False, allow_nan=False, indent=2),encoding='utf-8')
    os.replace(temporary, path)
