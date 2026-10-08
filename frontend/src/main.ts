import Phaser from 'phaser';
import './style.css';
import { actions, parseRun } from './contracts';
import type { Identity, Action } from './contracts';
import { Playback, nightAlpha } from './playback';
import { TownScene } from './TownScene';
import sample6 from './fixture-6.json';
import sample30 from './fixture-30.json';
import portraits from './assets/portraits.png?url';
import tokens from './design-tokens.json';

declare global {
  interface Window {
    __TINY_TOWN_RECORDING__?: unknown;
    __town?: { state: () => unknown; seek: (time: number) => void; ready: () => boolean };
  }
}
const paths: Record<string,string> = {
  home:'M3 10 12 2l9 8M5 9v12h14V9M10 21v-7h4v7',
  eat:'M5 2v7m3-7v7M3 2v7c0 3 7 3 7 0M6 11v11M18 2c-5 3-5 9 0 9v11V2',
  work:'m3 21 10-10m-2-8 4-2 7 7-4 4-7-9m-1 9 3 3',
  sleep:'M3 5v17M3 18h18v4M5 9h5v6H5zm6 3h10v6H3',
  socialize:'M9 7a3 3 0 1 0-6 0 3 3 0 1 0 6 0m11 1a3 3 0 1 0-6 0 3 3 0 1 0 6 0M1 21v-5c0-4 10-4 10 0v5m2 0v-4c0-4 10-4 10 0v4',
  wander:'M12 6a2 2 0 1 0 0-4 2 2 0 1 0 0 4m-5 8 4-6 4 5 5 1M10 10l-1 7-5 5m6-7 4 7',
  play:'m8 3 13 9L8 21V3',pause:'M7 3v18M17 3v18',restart:'M4 10a8 8 0 1 1 1 9M4 3v7h7',
  close:'m5 5 14 14M19 5 5 19',follow:'M12 3v4m0 10v4M3 12h4m10 0h4M12 8a4 4 0 1 0 0 8 4 4 0 1 0 0-8',
  chart:'M3 2v20h19M7 17V9m6 8V4m6 13v-6'
};
const icon = (key:string) => `<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="${paths[key]||paths.home}"/></svg>`;
const labels: Record<Action,string> = {eat:'Eating',work:'Working',sleep:'Sleeping',socialize:'Socializing',wander:'Wandering'};
const escapeHTML = (value: string) => value.replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]!));
const places: Record<string,string> = {bakery:'the bakery',square:'the town square',workshop:'the workshop',garden:'the garden',park:'the park'};
const $ = <T extends HTMLElement = HTMLElement>(selector:string) => document.querySelector<T>(selector)!;
const app=$('#app');
app.innerHTML=`
  <header><h1>${icon('home')} Tiny Town</h1><div class="clock" id="clock">Day 1 · 14:00</div>
    <div class="header-actions"><span id="mode" class="mode"></span><button id="population-button" aria-haspopup="dialog">${icon('socialize')}<span id="population-count"></span></button><button id="summary-button" aria-label="Open day summary">${icon('chart')}</button></div></header>
  <main id="main"><section id="viewport" aria-label="Town replay"><div id="canvas-host" tabindex="0" role="application" aria-label="Town map. Arrow keys pan; select residents through the population button."></div>
    <div class="map-tools"><label>Zoom <select id="zoom" aria-label="Map zoom"><option value="0">Fit</option><option value="1">1×</option><option value="2">2×</option><option value="3">3×</option></select></label><button id="fit">Recenter</button></div>
    <div id="legend" class="legend" aria-label="Current action counts"></div><div id="status" role="status" hidden></div>
  </section><aside id="inspector" aria-label="Selected resident" hidden></aside></main>
  <footer><div class="timeline"><input id="seek" aria-label="Seek replay time" type="range" min="0" max="24" step="0.01" value="14.75"><div class="hour-labels">${Array.from({length:9},(_,i)=>`<span>${String(i*3).padStart(2,'0')}</span>`).join('')}</div></div>
    <div class="controls"><button id="play" aria-label="Play">${icon('play')}<span>Play</span></button><div class="speeds" aria-label="Playback speed">${[1,2,4].map(s=>`<button data-speed="${s}" aria-pressed="${s===1}">${s}×</button>`).join('')}</div>
    <button id="restart">${icon('restart')}<span>Restart</span></button><label class="loop"><input id="loop" type="checkbox">Loop</label><span id="follow-state">Observing the town</span><span id="current-time"></span>
    <label class="import-button">Load recording<input id="recording" type="file" accept=".json,application/json"></label></div></footer>
  <dialog id="population"><div class="drawer-heading"><h2>Our neighbors</h2><button data-close="population" aria-label="Close population">${icon('close')}</button></div><p class="muted">Select a resident to see how their day is going.</p><label>Sort by <select id="sort"><option value="name">Name</option><option value="trait">Personality</option><option value="action">Action</option></select></label><div id="resident-list"></div></dialog>
  <dialog id="summary"><div class="drawer-heading"><h2>A day in Tiny Town</h2><button data-close="summary" aria-label="Close day summary">${icon('close')}</button></div><p class="muted">Recorded actions, after any confidence fallback.</p><div id="summary-content"></div></dialog>`;

let playback: Playback;
try {
  playback=new Playback(parseRun(window.__TINY_TOWN_RECORDING__ ?? (new URLSearchParams(location.search).get('stage')==='six'?sample6:sample30)));
} catch { playback=new Playback(parseRun(sample30));showError('The embedded recording is invalid. Showing the local mock sample.'); }
let selected: string|null=null,game:Phaser.Game,scene:TownScene;
let resizeObserver:ResizeObserver;
let lastViewKey='',lastPopulationKey='';

function portrait(identity:Identity,large=false) {
  const index=Number(identity.appearanceId.slice(-2));
  const scale=large?1.5:.625;
  return `<span class="portrait ${large?'large':''}" aria-hidden="true" style="background-image:url('${portraits}');background-size:${384*scale}px ${320*scale}px;background-position:${-(index%6)*64*scale}px ${-Math.floor(index/6)*64*scale}px"></span>`;
}
function selectResident(identity:Identity) {
  selected=identity.id;scene.selected=selected;
  $('#inspector').hidden=false;$('#main').classList.add('has-inspector');
  lastViewKey='';renderInspector();
  if(scene.ready)scene.center(playback.run.residents.findIndex(p=>p.id===selected));
  $('#follow').focus();
}
function closeInspector() {
  selected=null;scene.selected=null;scene.following=false;
  $('#inspector').hidden=true;$('#main').classList.remove('has-inspector');
  $('#canvas-host').focus();
}
function renderInspector() {
  const index=playback.run.residents.findIndex(p=>p.id===selected);
  if(index<0)return;
  const identity=playback.run.residents[index],entry=playback.entry(index),stats=playback.stats(index),decision=entry.decision;
  const accordion=$<HTMLDetailsElement>('#decision-details')?.open;
  const focusId=document.activeElement instanceof HTMLElement && $('#inspector').contains(document.activeElement) ? document.activeElement.id : null;
  const location=places[entry.destination.locationId]||`their cottage (${identity.homeId.slice(-2)})`;
  const events=playback.run.frames.slice(Math.max(0,playback.hour-3),playback.hour+1).map(f=>({hour:f.clockHour,entry:f.residents[index]})).reverse();
  $('#inspector').innerHTML=`<div class="inspector-top"><div class="identity">${portrait(identity,true)}<div><h2>${escapeHTML(identity.name)}</h2><p>Resident ${index+1}</p><span class="trait">${identity.trait}</span></div></div><button id="close-inspector" aria-label="Close resident inspector">${icon('close')}</button></div>
    <button id="follow" aria-pressed="${scene.following}">${icon('follow')}<span>${scene.following?'Following':'Follow resident'}</span></button>
    <section><h3>Currently</h3><div class="current-action">${icon(decision.appliedAction)}<strong>${labels[decision.appliedAction]}</strong></div><p class="caption">${labels[decision.appliedAction]} at ${location}.</p></section>
    <section><h3>Needs</h3>${(['hunger','energy','mood'] as const).map(key=>`<div class="need"><label for="${key}-bar">${key==='hunger'?'Hunger ↑':key[0].toUpperCase()+key.slice(1)}</label><meter id="${key}-bar" min="0" max="100" value="${stats[key]}"></meter><span>${stats[key]}%</span></div>`).join('')}<p class="money">Money <strong>${stats.money}</strong></p><p class="muted small">Higher hunger means hungrier. Needs update on the hour.</p></section>
    <section><h3>Today</h3><div class="resident-timeline">${playback.run.frames.map(f=>`<span title="${f.clockHour}:00 — ${labels[f.residents[index].decision.appliedAction]}" style="background:var(--${f.residents[index].decision.appliedAction})"></span>`).join('')}</div><div class="timeline-captions"><span>00</span><span>06</span><span>12</span><span>18</span><span>24</span></div></section>
    <section><h3>Observed events</h3><ol class="events">${events.map(e=>`<li><time>${String(e.hour).padStart(2,'0')}:00</time> ${labels[e.entry.decision.appliedAction]} at ${places[e.entry.destination.locationId]||'home'}</li>`).join('')}</ol></section>
    <details id="decision-details" ${accordion?'open':''}><summary>Decision details</summary><dl><dt>Chosen action</dt><dd>${decision.chosenAction||'No valid API choice'}</dd><dt>Confidence</dt><dd>${decision.confidence===null?'Unavailable':decision.confidence.toFixed(2)}</dd><dt>Confidence fallback</dt><dd>${decision.fellBack?'Wander applied':'None'}</dd><dt>Source</dt><dd>${decision.decisionSource}</dd><dt>Error fallback</dt><dd>${escapeHTML(decision.errorCode||'None')}</dd></dl></details>`;
  $('#close-inspector').onclick=closeInspector;
  $('#follow').onclick=()=>{scene.following=!scene.following;renderInspector();if(scene.following)scene.center(index);};
  if(focusId)document.getElementById(focusId)?.focus({preventScroll:true});
}
function startScene() {
  resizeObserver?.disconnect();
  if(game)game.destroy(true);
  scene=new TownScene(playback,selectResident,()=>{if(selected)renderInspector();});
  game=new Phaser.Game({type:Phaser.CANVAS,parent:'canvas-host',width:$('#canvas-host').clientWidth,height:$('#canvas-host').clientHeight,
    pixelArt:true,antialias:false,roundPixels:true,audio:{noAudio:true},banner:false,scene,
    scale:{mode:Phaser.Scale.NONE},fps:{target:60}});
  resizeObserver=new ResizeObserver(()=>{
    if(!scene.ready)return;
    game.scale.resize($('#canvas-host').clientWidth,$('#canvas-host').clientHeight);
    scene.fit(true);
  });
  resizeObserver.observe($('#canvas-host'));
}
function renderPopulation() {
  const focusResident=(document.activeElement as HTMLElement)?.dataset?.resident;
  const order=$<HTMLSelectElement>('#sort').value;
  const people=[...playback.run.residents];
  people.sort((a,b)=>{
    const value=(p:Identity)=>order==='action'?playback.entry(playback.run.residents.indexOf(p)).decision.appliedAction:order==='trait'?p.trait:p.name;
    return value(a).localeCompare(value(b))||a.name.localeCompare(b.name);
  });
  $('#resident-list').innerHTML=people.map(p=>{const i=playback.run.residents.indexOf(p);return `<button class="resident-row" data-resident="${p.id}">${portrait(p)}<span><strong>${escapeHTML(p.name)}</strong><small>${p.trait}</small></span><span class="row-action">${icon(playback.entry(i).decision.appliedAction)}${labels[playback.entry(i).decision.appliedAction]}</span></button>`;}).join('');
  $('#resident-list').querySelectorAll<HTMLButtonElement>('button').forEach(button=>button.onclick=()=>{
    $<HTMLDialogElement>('#population').close();selectResident(playback.run.residents.find(p=>p.id===button.dataset.resident)!);
    scene.center(playback.run.residents.findIndex(p=>p.id===selected));
  });
  if(focusResident)document.querySelector<HTMLButtonElement>(`[data-resident="${focusResident}"]`)?.focus({preventScroll:true});
}
function renderSummary() {
  const count=playback.run.residents.length;
  const hours=playback.run.frames.map(f=>{
    const counts=Object.fromEntries(actions.map(a=>[a,f.residents.filter(p=>p.decision.appliedAction===a).length]));
    return `<div class="summary-hour"><span>${String(f.clockHour).padStart(2,'0')}</span><div class="stack">${actions.map(a=>`<span style="width:${counts[a]/count*100}%;background:var(--${a})" title="${a}: ${counts[a]}"></span>`).join('')}</div><span>${Math.round(f.residents.reduce((s,p)=>s+p.after.hunger,0)/count)} / ${Math.round(f.residents.reduce((s,p)=>s+p.after.energy,0)/count)} / ${Math.round(f.residents.reduce((s,p)=>s+p.after.mood,0)/count)}</span></div>`;
  });
  const groups=['social','workaholic','lazy'].map(trait=>{
    const ids=new Set(playback.run.residents.filter(p=>p.trait===trait).map(p=>p.id));
    const entries=playback.run.frames.flatMap(f=>f.residents.filter(p=>ids.has(p.id)));
    return `<tr><th>${trait}<small>${entries.length} decisions</small></th>${actions.map(a=>`<td>${entries.length?Math.round(entries.filter(p=>p.decision.appliedAction===a).length/entries.length*100):0}%</td>`).join('')}</tr>`;
  });
  $('#summary-content').innerHTML=`<h3>Action share by personality</h3><div class="table-scroll"><table><thead><tr><th>Trait</th>${actions.map(a=>`<th>${a}</th>`).join('')}</tr></thead><tbody>${groups.join('')}</tbody></table></div><h3>Hour by hour</h3><p class="small muted">Right column: average hunger / energy / mood after each hour.</p>${hours.join('')}<p>Low-confidence fallbacks: ${playback.run.frames.flatMap(f=>f.residents).filter(p=>p.decision.fellBack).length}. Error-mock decisions: ${playback.run.frames.flatMap(f=>f.residents).filter(p=>p.decision.errorCode).length}.</p>`;
}
function showError(message:string) {
  const status=$('#status');status.hidden=false;status.textContent=message;
  const retry=document.createElement('button');retry.textContent='Retry load';retry.onclick=()=>$<HTMLInputElement>('#recording').click();status.append(retry);
}
$('#population-button').onclick=()=>{renderPopulation();$<HTMLDialogElement>('#population').showModal();};
$('#summary-button').onclick=()=>{renderSummary();$<HTMLDialogElement>('#summary').showModal();};
document.querySelectorAll<HTMLButtonElement>('[data-close]').forEach(b=>b.onclick=()=>$<HTMLDialogElement>(`#${b.dataset.close}`).close());
$('#sort').onchange=renderPopulation;
$('#play').onclick=()=>{if(playback.time===24)playback.restart();playback.playing=!playback.playing;};
$('#restart').onclick=()=>playback.restart();
$('#seek').oninput=()=>playback.seek(Number($<HTMLInputElement>('#seek').value));
$('#loop').onchange=()=>{playback.loop=$<HTMLInputElement>('#loop').checked;};
document.querySelectorAll<HTMLButtonElement>('[data-speed]').forEach(b=>b.onclick=()=>{playback.speed=Number(b.dataset.speed) as 1|2|4;});
$('#zoom').onchange=()=>scene.zoom(Number($<HTMLSelectElement>('#zoom').value));
$('#fit').onclick=()=>{scene.following=false;scene.zoom(0);$<HTMLSelectElement>('#zoom').value='0';};
$('#recording').onchange=async()=>{
  const file=$<HTMLInputElement>('#recording').files?.[0];if(!file)return;
  try {
    if(file.size>5_000_000)throw Error('Recording too large');
    const run=parseRun(JSON.parse(await file.text()));
    const candidate=new Playback(run);
    for(let h=0;h<24;h++){candidate.seek(h+.5);for(let i=0;i<run.residents.length;i++)candidate.position(i);}
    candidate.restart();candidate.playing=false;
    playback=candidate;selected=null;$('#inspector').hidden=true;$('#main').classList.remove('has-inspector');
    lastViewKey='';lastPopulationKey='';$('#status').hidden=true;startScene();
  } catch {showError('Could not load this recording. Check schema version, resident IDs, stats, and destinations. The current replay is still available.');}
  $<HTMLInputElement>('#recording').value='';
};
document.addEventListener('keydown',e=>{
  if(e.key==='Escape') { if(!$<HTMLDialogElement>('#population').open&&!$<HTMLDialogElement>('#summary').open)closeInspector();return; }
  if(e.target instanceof HTMLInputElement || e.target instanceof HTMLSelectElement || e.target instanceof HTMLButtonElement || (e.target instanceof HTMLElement&&e.target.closest('dialog')))return;
  if(e.code==='Space') {e.preventDefault();$('#play').click();}
  if(e.target===$('#canvas-host')) { const movement:Record<string,[number,number]>={ArrowLeft:[-32,0],ArrowRight:[32,0],ArrowUp:[0,-32],ArrowDown:[0,32]};if(movement[e.key]){e.preventDefault();scene.pan(...movement[e.key]);} }
});
function renderUI() {
  const raw=playback.run.startHour+playback.time,clock=raw%24,h=Math.floor(clock),m=Math.floor((clock-h)*60);
  const time=`${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}`;
  $('#clock').textContent=`Day ${Math.floor(raw/24)+1} · ${time}${playback.time===24?' · complete':''}`;
  $('#current-time').textContent=time;
  document.body.classList.toggle('night',nightAlpha(clock)>.12);
  $('#mode').textContent=playback.run.fixtureKind==='staged'?'Mock · sample':playback.run.mode==='jev'?'Jev replay':playback.run.mode==='mixed'?'Mixed replay':'Mock replay';
  $('#population-count').textContent=`${playback.run.residents.length} residents`;
  $('#play').innerHTML=`${icon(playback.playing?'pause':'play')}<span>${playback.playing?'Pause':'Play'}</span>`;
  $('#play').setAttribute('aria-label',playback.playing?'Pause':'Play');
  if(document.activeElement!==$('#seek'))$<HTMLInputElement>('#seek').value=String(playback.time);
  $('#follow-state').textContent=scene?.following?`Following ${playback.run.residents.find(p=>p.id===selected)?.name}`:'Observing the town';
  document.querySelectorAll<HTMLButtonElement>('[data-speed]').forEach(b=>b.setAttribute('aria-pressed',String(Number(b.dataset.speed)===playback.speed)));
  const key=`${playback.run.runId}:${playback.hour}:${selected}:${playback.time===24}`;
  if(key!==lastViewKey){lastViewKey=key;const counts=playback.counts();$('#legend').innerHTML=actions.map(a=>`<span>${icon(a)}<span>${a[0].toUpperCase()+a.slice(1)}</span><b>${counts[a]}</b></span>`).join('');if(selected)renderInspector();}
  const popKey=`${playback.run.runId}:${playback.hour}`;
  if(popKey!==lastPopulationKey && $<HTMLDialogElement>('#population').open){lastPopulationKey=popKey;renderPopulation();}
  requestAnimationFrame(renderUI);
}
startScene();renderUI();
window.__town={ready:()=>scene.ready,seek:(t)=>playback.seek(t),state:()=>({time:playback.time,playing:playback.playing,speed:playback.speed,loop:playback.loop,selected,following:scene.following,
  camera:{width:scene.cameras.main.width,height:scene.cameras.main.height,scaleWidth:scene.scale.width,scaleHeight:scene.scale.height,
    scrollX:scene.cameras.main.scrollX,scrollY:scene.cameras.main.scrollY,zoom:scene.cameras.main.zoom},
  mode:playback.run.mode,counts:playback.counts(),people:scene.inspect(),stats:playback.run.residents.map((_,i)=>playback.stats(i))})};
