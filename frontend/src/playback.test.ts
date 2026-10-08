import { describe, it, expect } from 'vitest';
import sample from './fixture-30.json';
import six from './fixture-6.json';
import { parseRun, actions } from './contracts';
import { Playback, nightAlpha } from './playback';
import { route } from './routes';
import world from './world.json';

describe('versioned recording',()=>{
  it('loads older v1 recordings without inventing conversation partners',()=>{
    const legacy=structuredClone(parseRun(sample));
    for(const frame of legacy.frames)for(const entry of frame.residents)delete entry.interaction;
    const p=new Playback(parseRun(legacy));p.seek(14.99);
    expect(p.partners(0)).toEqual([]);expect(p.conversation(0)).toEqual([]);
  });
  it.each(['unknown','self','duplicate','asymmetric','distant','overlap','fallback','group'])('rejects %s conversation metadata',reason=>{
    const bad=structuredClone(parseRun(sample)),entries=bad.frames[14].residents;
    const first=entries[0],partner=entries.find(p=>p.id===first.interaction!.partnerIds[0])!;
    if(reason==='unknown')first.interaction!.partnerIds[0]='npc99';
    if(reason==='self')first.interaction!.partnerIds[0]=first.id;
    if(reason==='duplicate')first.interaction!.partnerIds[1]=first.interaction!.partnerIds[0];
    if(reason==='asymmetric')partner.interaction=null;
    if(reason==='distant')partner.destination.x=first.destination.x+64;
    if(reason==='overlap')Object.assign(partner.destination,first.destination);
    if(reason==='fallback')Object.assign(first.decision,{appliedAction:'wander',fellBack:true});
    if(reason==='group')partner.interaction!.partnerIds=['npc00'];
    expect(()=>parseRun(bad)).toThrow();
  });
  it('accepts 24 intervals and 25 boundaries for 30 stable people',()=>{
    const run=parseRun(sample);expect(run.frames).toHaveLength(24);expect(run.residents).toHaveLength(30);
    const playback=new Playback(run);playback.seek(0);expect(playback.stats(0)).toEqual(run.initialSnapshot[0].stats);
    playback.seek(24);expect(playback.stats(0)).toEqual(run.frames[23].residents[0].after);
  });
  it.each(['duplicate','missing','sequence','choice','confidence','stats','water','continuity'])('rejects %s recordings',reason=>{
    const bad=structuredClone(sample);
    if(reason==='duplicate')bad.residents[1].id=bad.residents[0].id;
    if(reason==='missing')bad.frames[3].residents.pop();
    if(reason==='sequence')bad.frames[3].sequence=3;
    if(reason==='choice')Object.assign(bad.frames[3].residents[0].decision,{chosenAction:'fight'});
    if(reason==='confidence')bad.frames[3].residents[0].decision.confidence=NaN;
    if(reason==='stats')bad.frames[3].residents[0].after.mood=101;
    if(reason==='water')bad.frames[3].residents[0].destination.x=58*16+8;
    if(reason==='continuity')bad.frames[3].residents[0].before.money+=1;
    expect(()=>parseRun(bad)).toThrow();
  });
});
describe('deterministic replay',()=>{
  it('conversations wait for arrival and reconstruct identically after seeking',()=>{
    const p=new Playback(parseRun(sample));p.seek(14.99);
    expect(p.conversation(0).map(q=>q.id)).toEqual(p.entry(0).interaction!.partnerIds);
    const partners=p.conversation(0);
    p.seek(3);p.seek(14.99);expect(p.conversation(0)).toEqual(partners);
    p.seek(14.1);
    for(let i=0;i<30;i++)for(const partner of p.conversation(i)){
      expect(p.arrived(i)).toBe(true);expect(p.arrived(p.run.residents.indexOf(partner))).toBe(true);
    }
    expect(p.run.residents.some((_,i)=>p.partners(i).length>0&&!p.arrived(i))).toBe(true);
    const state=p.conversation(0);p.advance(1);expect(p.conversation(0)).toEqual(state);
  });
  it('pause freezes clock and reconstructed positions',()=>{
    const p=new Playback(parseRun(six));const before=p.position(0);p.advance(10);
    expect(p.time).toBe(14.75);expect(p.position(0)).toEqual(before);
  });
  it('seeking to the same time is independent of play history',()=>{
    const p=new Playback(parseRun(sample));p.seek(7.35);const state=p.position(20);
    p.playing=true;p.advance(3);p.seek(23.95);p.seek(7.35);expect(p.position(20)).toEqual(state);
  });
  it('speed compresses travel and clock; end stops, loop and restart reuse the run',()=>{
    const p=new Playback(parseRun(sample));p.restart();p.playing=true;p.speed=4;p.advance(3);expect(p.time).toBe(1);
    p.seek(23.9);p.advance(3);expect(p.time).toBe(24);expect(p.playing).toBe(false);
    p.loop=true;p.playing=true;p.advance(3);expect(p.time).toBe(1);
    p.restart();expect(p.time).toBe(0);expect(p.run).toEqual(parseRun(sample));
  });
  it('needs commit only at recorded boundaries',()=>{
    const p=new Playback(parseRun(sample));p.seek(14.999);expect(p.stats(0)).toEqual(sample.frames[14].residents[0].before);
    p.seek(15);expect(p.stats(0)).toEqual(sample.frames[14].residents[0].after);
  });
  it('every resident at every hour has a route within the speed cap',()=>{
    const p=new Playback(parseRun(sample));for(let h=0;h<24;h++)for(let i=0;i<30;i++){
      p.seek(h+.999);expect(()=>p.position(i)).not.toThrow();expect(p.position(i).position).toEqual({x:p.entry(i).destination.x,y:p.entry(i).destination.y});
    }
  });
  it('bridge is the only crossing and roofs/fountain/crops block outdoor routes',()=>{
    const points=route({x:888,y:344},{x:1000,y:344});
    const water=points.filter(p=>p.x>=57*16&&p.x<60*16);expect(water.length).toBeGreaterThan(0);
    expect(water.every(p=>p.y>=22*16&&p.y<25*16)).toBe(true);
    const ground=new Set(world.walkable.map(([x,y])=>`${x},${y}`));
    expect(ground.has('5,4')).toBe(false);expect(ground.has('26,18')).toBe(false);expect(ground.has('33,29')).toBe(false);
  });
  it('counts always use applied decisions',()=>{
    const p=new Playback(parseRun(sample));expect(Object.values(p.counts()).reduce((a,b)=>a+b,0)).toBe(30);
    expect(Object.keys(p.counts())).toEqual([...actions]);
  });
  it('night is legible and dawn clears',()=>{expect(nightAlpha(23)).toBe(.35);expect(nightAlpha(14)).toBe(0);expect(nightAlpha(6)).toBe(.175);});
});
