import {describe,it,expect} from 'vitest';
import sample from '../../tests/fixtures/memories.json';
import legacy from './fixture-6.json';
import {parseRun} from './contracts';
import {familiarNeighbors} from './memories';

describe('saved resident memories',()=>{
  it('dates meeting memories correctly when a recording crosses midnight from a shifted start',()=>{
    const shifted=structuredClone(sample);shifted.startHour=18;
    for(const frame of shifted.frames){
      frame.clockHour=(18+frame.tick)%24;
      for(const update of frame.memoryUpdates){update.lastMetDay=1+Math.floor((18+frame.tick)/24);update.lastMetHour=frame.clockHour;}
    }
    const run=parseRun(shifted);
    expect(familiarNeighbors(run,6,0)?.every(p=>p.lastMetDay===1 && p.lastMetHour===23)).toBe(true);
    expect(familiarNeighbors(run,7,0)?.every(p=>p.lastMetDay===2 && p.lastMetHour===0)).toBe(true);
  });
  it('starts day two with saved familiarity rather than counting playback as new meetings',()=>{
    const next=parseRun(sample);
    next.dayNumber=2;next.initialMemories=structuredClone(next.frames[23].memoryUpdates!);
    for(const frame of next.frames)for(const update of frame.memoryUpdates!){update.meetings+=24;update.lastMetDay=2;}
    const run=parseRun(next);
    expect(familiarNeighbors(run,0,0)?.map(p=>p.meetings)).toEqual([24,24,24]);
    expect(familiarNeighbors(run,24,0)?.map(p=>p.meetings)).toEqual([48,48,48]);
    expect(familiarNeighbors(run,0,0)?.map(p=>p.meetings)).toEqual([24,24,24]);
  });
  it('commits once at the hour boundary and reconstructs without changing the recording',()=>{
    const run=parseRun(sample),before=JSON.stringify(run);
    expect(familiarNeighbors(run,.99,0)).toEqual([]);
    expect(familiarNeighbors(run,1,0)?.map(p=>p.meetings)).toEqual([1,1,1]);
    expect(familiarNeighbors(run,24,0)?.map(p=>p.meetings)).toEqual([24,24,24]);
    expect(familiarNeighbors(run,1,0)).toEqual(familiarNeighbors(run,1,0));
    expect(JSON.stringify(run)).toBe(before);
    expect(familiarNeighbors(parseRun(legacy),24,0)).toBeNull();
  });
  it.each(['self','unknown','duplicate','count','future','missing','forged'])('rejects %s memory data',reason=>{
    const run=structuredClone(sample);
    const update=run.frames[0].memoryUpdates[0];
    if(reason==='self')update.residentIds[1]=update.residentIds[0];
    if(reason==='unknown')update.residentIds[1]='npc29';
    if(reason==='duplicate')run.frames[0].memoryUpdates.push(structuredClone(update));
    if(reason==='count')update.meetings=2;
    if(reason==='future')update.lastMetDay=2;
    if(reason==='missing')run.frames[0].memoryUpdates.pop();
    if(reason==='forged')run.frames[0].conversations=[];
    expect(()=>parseRun(run)).toThrow();
  });
});
