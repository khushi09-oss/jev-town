"""Authored staging for visual QA, clearly tagged as a mock sample, not Jev output."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from simulation.identities import manifest
from simulation.world import destination, point
from simulation.interactions import plan_interactions


def fixture(count, forced_action=None):
    people=manifest(count)
    stats={p['id']:{'hunger':30+i%5*8,'energy':75-i%7*3,'mood':60+i%5*5,'money':40}
           for i,p in enumerate(people)}
    initial=[{'id':p['id'],'stats':dict(stats[p['id']]),'position':
              {key:value for key,value in destination(i,'socialize',0,7).items() if key in ('x','y')}}
             for i,p in enumerate(people)]
    frames=[]
    effects={'eat':(-40,5,3,-5),'work':(10,-15,-6,20),'sleep':(6,25,0,0),
             'socialize':(8,-6,22,-4),'wander':(6,-4,-4,0)}
    for tick in range(24):
        residents=[]
        for i,p in enumerate(people):
            action='sleep' if tick<6 or tick>=22 else ['socialize','eat','sleep','work','wander','socialize'][(i+tick-14)%6]
            if forced_action:
                action=forced_action
            before=dict(stats[p['id']])
            after={k:max(0,min(100,before[k]+delta)) if k!='money' else max(0,before[k]+delta)
                   for k,delta in zip(('hunger','energy','mood','money'),effects[action])}
            residents.append({'id':p['id'],'before':before,'after':after,
                'decision':{'chosenAction':action,'appliedAction':action,'confidence':0.9,
                'fellBack':False,'decisionSource':'mock','errorCode':None},
                'destination':destination(i,action,tick,7)})
            stats[p['id']]=after
        plan_interactions(residents, tick, 7)
        frames.append({'tick':tick,'clockHour':tick,'sequence':tick+1,'residents':residents})
    return {'schemaVersion':1,'runId':f'visual-sample-{count}-v1','seed':7,'mode':'mock',
            'fixtureKind':'staged','hours':24,'startHour':0,'worldId':'tiny-town-v1',
            'residents':[{k:v for k,v in p.items() if k in ('id','name','trait','appearanceId','homeId')} for p in people],
            'initialSnapshot':initial,'frames':frames}


if __name__=='__main__':
    for count in (6,30):
        run=fixture(count)
        (ROOT/f'frontend/src/fixture-{count}.json').write_text(json.dumps(run))
    for action in ('eat','work','sleep','socialize','wander'):
        (ROOT/f'tests/fixtures/occupancy-{action}.json').write_text(json.dumps(fixture(30,action)))
