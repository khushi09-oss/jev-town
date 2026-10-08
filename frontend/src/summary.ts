import type {Run} from './contracts';

const categories = [
  {action:'socialize',title:'Most social'},
  {action:'work',title:'Most work'},
  {action:'sleep',title:'Most rest'}
] as const;

export function dayHighlights(run: Run) {
  return categories.map(category=>{
    const scores=run.residents.map((person,index)=>({
      id:person.id,
      hours:run.frames.filter(frame=>frame.residents[index].decision.appliedAction===category.action).length,
      tick:run.frames.findIndex(frame=>frame.residents[index].decision.appliedAction===category.action)
    }));
    const hours=Math.max(...scores.map(p=>p.hours));
    const winners=hours ? scores.filter(p=>p.hours===hours).sort((a,b)=>a.id.localeCompare(b.id))
      .map(({id,tick})=>({id,tick})) : [];
    return {...category,hours,winners};
  });
}
