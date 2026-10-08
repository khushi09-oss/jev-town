import {describe,it,expect} from 'vitest';
import sample from './fixture-6.json';
import townSample from './fixture-30.json';
import {parseRun} from './contracts';
import {dayHighlights} from './summary';

describe('recorded day highlights',()=>{
  it('finds every tied leader and their first interval without mutating the recording',()=>{
    const run=parseRun(sample),before=JSON.stringify(run);
    const result=dayHighlights(run);
    for(const highlight of result){
      const hours=run.residents.map((_,i)=>run.frames.filter(f=>f.residents[i].decision.appliedAction===highlight.action).length);
      expect(highlight.hours).toBe(Math.max(...hours));
      expect(highlight.winners.map(p=>p.id)).toEqual(run.residents.filter((_,i)=>hours[i]===highlight.hours).map(p=>p.id).sort());
      for(const winner of highlight.winners){
        const index=run.residents.findIndex(p=>p.id===winner.id);
        expect(winner.tick).toBe(run.frames.findIndex(f=>f.residents[index].decision.appliedAction===highlight.action));
      }
    }
    expect(JSON.stringify(run)).toBe(before);
  });
  it('counts applied actions, including error mock, instead of rejected model choices',()=>{
    const run=parseRun(sample);
    for(const frame of run.frames)for(const p of frame.residents)p.decision.appliedAction='wander';
    Object.assign(run.frames[7].residents[0].decision,{chosenAction:'work',appliedAction:'wander',fellBack:true});
    Object.assign(run.frames[8].residents[1].decision,{chosenAction:null,confidence:null,appliedAction:'work',decisionSource:'error-mock',errorCode:'network_error'});
    const work=dayHighlights(run).find(p=>p.action==='work')!;
    expect(work.hours).toBe(1);expect(work.winners).toEqual([{id:'npc01',tick:8}]);
  });
  it('zero-activity categories have no invented winners or moments',()=>{
    const run=parseRun(sample);
    for(const frame of run.frames)for(const p of frame.residents)p.decision.appliedAction='wander';
    expect(dayHighlights(run).every(p=>p.hours===0&&p.winners.length===0)).toBe(true);
  });
  it('handles a 30-way tie deterministically and uses elapsed ticks for shifted clocks',()=>{
    const run=parseRun(townSample);run.startHour=18;
    for(const frame of run.frames){frame.clockHour=(18+frame.tick)%24;for(const p of frame.residents)p.decision.appliedAction='sleep';}
    const rest=dayHighlights(run).find(p=>p.action==='sleep')!;
    expect(rest.hours).toBe(24);expect(rest.winners).toHaveLength(30);
    expect(rest.winners.every(p=>p.tick===0)).toBe(true);
  });
});
