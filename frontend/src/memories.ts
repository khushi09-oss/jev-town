import type {Run} from './contracts';

export function familiarNeighbors(run:Run,time:number,index:number){
  if(run.initialMemories===undefined)return null;
  const state=new Map(run.initialMemories.map(memory=>[memory.residentIds.join(':'),memory]));
  for(const frame of run.frames.slice(0,Math.floor(Math.max(0,Math.min(24,time))))){
    for(const memory of frame.memoryUpdates ?? [])state.set(memory.residentIds.join(':'),memory);
  }
  const id=run.residents[index].id;
  return [...state.values()].filter(memory=>memory.residentIds.includes(id)).map(memory=>({
    ...memory,person:run.residents.find(p=>p.id===memory.residentIds.find(other=>other!==id))!
  })).sort((a,b)=>b.meetings-a.meetings||a.person.id.localeCompare(b.person.id));
}
