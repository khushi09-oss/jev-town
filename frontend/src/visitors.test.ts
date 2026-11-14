import {expect,it} from 'vitest';
import sample from './fixture-30.json';
import plans from './bench-plans.json';
import {parseRun} from './contracts';
import {VisitorSession} from './visitors';
import {Playback} from './playback';

it('branches only future routes, preserves needs and decisions, and restores the original day',()=>{
  const base=parseRun(sample),session=new VisitorSession(base,plans);
  const changed=session.place('park-gate',14.75);
  expect(changed.frames.slice(0,15)).toEqual(base.frames.slice(0,15));
  expect(changed.frames[15]).not.toEqual(base.frames[15]);
  changed.frames.forEach((frame,h)=>frame.residents.forEach((person,i)=>{
    expect(person.decision).toEqual(base.frames[h].residents[i].decision);
    expect(person.after).toEqual(base.frames[h].residents[i].after);
  }));
  const playback=new Playback(changed);
  for(let h=0;h<24;h++){playback.seek(h+.95);base.residents.forEach((_,i)=>playback.position(i));}
  expect(session.visibleAt(14)).toBe(false);
  expect(session.visibleAt(14.75)).toBe(true);
  expect(()=>session.place('garden-view',16)).toThrow();
  expect(session.reset()).toEqual(base);
  expect(session.visibleAt(20)).toBe(false);
});

it('rejects unavailable sites and placement at the end of the day without changing state',()=>{
  const session=new VisitorSession(parseRun(sample),plans);
  expect(()=>session.place('anywhere',12)).toThrow();
  for(const time of [23,24,NaN,-1])expect(()=>session.place('park-gate',time)).toThrow();
  expect(session.event).toBeNull();
});
