import {parseRun} from './contracts';
import type {Run,Entry} from './contracts';

export type BenchPlan = {id:string;name:string;x:number;y:number;
  frames:{id:string;destination:Entry['destination']}[][]};

export class VisitorSession {
  event: {site:BenchPlan;placedAt:number;effectiveTick:number}|null=null;
  constructor(public base:Run,public plans:BenchPlan[]) {}
  place(id:string,time:number):Run {
    if(this.event)throw Error('Remove the existing bench before choosing another site.');
    const site=this.plans.find(p=>p.id===id);
    if(!site || !Number.isFinite(time) || time<0 || time>=23)throw Error('Choose an available site before the final hour.');
    const effectiveTick=Math.floor(time)+1,run=structuredClone(this.base);
    for(let tick=effectiveTick;tick<24;tick++){
      for(const change of site.frames[tick]){
        const person=run.frames[tick].residents.find(p=>p.id===change.id);
        if(!person || person.decision.appliedAction!=='wander')throw Error('Incompatible bench plan');
        person.destination={...change.destination};
      }
    }
    const checked=parseRun(run);
    this.event={site,placedAt:time,effectiveTick};
    return checked;
  }
  visibleAt(time:number){return this.event!==null && time>=this.event.placedAt;}
  reset(){this.event=null;return this.base;}
}
