/** Presentation only: use recording time so pause and seek freeze/reconstruct the river. */
export function ambientPixels(time:number,reducedMotion:boolean){
  const phase=reducedMotion?0:time*36;
  return Array.from({length:24},(_,i)=>({x:916+(i*13)%38,y:Math.floor((i*29+phase)%640)}))
    .filter(p=>p.y<350||p.y>400);
}
