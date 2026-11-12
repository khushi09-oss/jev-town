import {describe,it,expect} from 'vitest';
import sample from './fixture-30.json';
import {parseRun} from './contracts';
import {Playback} from './playback';

describe('recorded dialogue',()=>{
  it.each(['speaker','participants','duplicate','missing','source','empty','long','control','id'])('rejects %s dialogue without accepting partial data',reason=>{
    const run=structuredClone(sample),frame=run.frames[14],chat=frame.conversations[0];
    if(reason==='speaker')chat.turns[0].speakerId='npc29';
    if(reason==='participants')chat.participantIds.pop();
    if(reason==='duplicate')frame.conversations.push(structuredClone(chat));
    if(reason==='missing')chat.turns=chat.turns.filter(t=>t.speakerId!==chat.participantIds[1]);
    if(reason==='source')chat.source='jev';
    if(reason==='empty')chat.turns[0].text='   ';
    if(reason==='long')chat.turns[0].text='x'.repeat(181);
    if(reason==='control')chat.turns[0].text='bad\u0000text';
    if(reason==='id')chat.id='chat-1-npc00';
    expect(()=>parseRun(run)).toThrow();
  });
  it('uses recorded turns only after everyone arrives, and freezes/reconstructs them',()=>{
    const p=new Playback(parseRun(sample));p.seek(14);
    expect(p.dialogue(0)?.current).toBeNull();
    const seen=new Set<string>();
    for(let tick=0;tick<=1000;tick++){
      p.seek(14+tick/1000);const view=p.dialogue(0);
      if(view?.current){
        seen.add(view.current.speakerId+view.current.text);
        for(const id of view.recording.participantIds)expect(p.arrived(p.run.residents.findIndex(q=>q.id===id))).toBe(true);
      }
    }
    expect(seen.size).toBe(p.run.frames[14].conversations![0].turns.length);
    p.seek(14.99);const before=p.dialogue(0);p.advance(5);expect(p.dialogue(0)).toEqual(before);
    p.seek(2);p.seek(14.99);expect(p.dialogue(0)).toEqual(before);
    for(const id of before!.recording.participantIds)expect(p.dialogue(p.run.residents.findIndex(q=>q.id===id))).toEqual(before);
    p.restart();expect(p.dialogue(0)).toBeNull();
  });
  it('does not invent scripts for old v1 meetings',()=>{
    const run=parseRun(sample);for(const frame of run.frames)delete frame.conversations;
    const p=new Playback(parseRun(run));p.seek(14.99);
    expect(p.conversation(0).length).toBeGreaterThan(0);expect(p.dialogue(0)).toBeNull();
  });
});
