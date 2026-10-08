import { test, expect } from '@playwright/test';
import type { Page } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

async function ready(page:Page) { await page.goto('/');await page.waitForFunction(()=>window.__town?.ready()); }
async function seek(page:Page,time:number) { await page.locator('#seek').fill(String(time));await page.waitForTimeout(60); }
test('playback has no network decisions and pause freezes every sprite',async({page})=>{
  const errors:string[]=[],requests:string[]=[];page.on('pageerror',e=>errors.push(e.message));
  await ready(page);page.on('request',r=>requests.push(r.url()));
  await page.getByRole('button',{name:'Play',exact:true}).click();await page.waitForTimeout(250);
  await page.getByRole('button',{name:'Pause',exact:true}).click();await page.waitForTimeout(60);
  const before=await page.evaluate(()=>window.__town!.state());await page.waitForTimeout(300);
  expect(await page.evaluate(()=>window.__town!.state())).toEqual(before);
  await seek(page,7.35);const position=await page.evaluate(()=>window.__town!.state());
  await seek(page,22);await seek(page,7.35);expect(await page.evaluate(()=>window.__town!.state())).toEqual(position);
  await page.getByRole('button',{name:'4×',exact:true}).click();await page.getByLabel('Loop',{exact:true}).check();
  await page.getByRole('button',{name:'Restart',exact:true}).click();
  expect((await page.evaluate(()=>window.__town!.state()) as any).time).toBe(0);
  expect(requests).toEqual([]);expect(errors).toEqual([]);
});
test('keyboard population selection, follow, seek, and Escape',async({page})=>{
  await ready(page);await page.getByRole('button',{name:'30 residents'}).click();
  await page.getByRole('button',{name:/Bea social/}).focus();await page.keyboard.press('Enter');
  await expect(page.locator('#inspector')).toBeVisible();await expect(page.locator('#inspector h2')).toHaveText('Bea');
  await expect.poll(async()=>((await page.evaluate(()=>window.__town!.state())) as any).camera.width).toBe(1120);
  await page.getByRole('button',{name:'Follow resident'}).click();await seek(page,15);
  await expect(page.locator('#inspector h2')).toHaveText('Bea');
  expect((await page.evaluate(()=>window.__town!.state()) as any).following).toBe(true);
  await page.locator('#canvas-host').focus();await page.keyboard.press('ArrowRight');
  expect((await page.evaluate(()=>window.__town!.state()) as any).following).toBe(false);
  await page.keyboard.press('Escape');await expect(page.locator('#inspector')).toBeHidden();
  await expect.poll(async()=>((await page.evaluate(()=>window.__town!.state())) as any).camera.width).toBe(1440);
});
test('invalid recordings preserve the last valid frame',async({page})=>{
  await ready(page);const before=await page.evaluate(()=>window.__town!.state());
  await page.locator('#recording').setInputFiles({name:'bad.json',mimeType:'application/json',buffer:Buffer.from('{"schemaVersion":999}')});
  await expect(page.getByRole('status')).toContainText('Could not load');expect(await page.evaluate(()=>window.__town!.state())).toEqual(before);
});
test('selected sleeping resident reveals their own home',async({page})=>{
  await ready(page);await seek(page,23.99);await page.getByRole('button',{name:'30 residents'}).click();
  await page.getByRole('button',{name:/Bea social/}).click();
  const people=(await page.evaluate(()=>window.__town!.state()) as any).people;
  expect(people.find((p:any)=>p.id==='npc00').visible).toBe(true);
  expect(people.filter((p:any)=>p.visible)).toHaveLength(5);
});
test('mobile inspector and playback remain reachable, reduced-motion follow works',async({page})=>{
  await page.setViewportSize({width:390,height:844});await page.emulateMedia({reducedMotion:'reduce'});await ready(page);
  await page.getByRole('button',{name:'30 residents'}).click();await page.getByRole('button',{name:/Bea social/}).click();
  const inspector=await page.locator('#inspector').boundingBox();expect(inspector!.height).toBeLessThanOrEqual(844*.45+1);
  await expect.poll(async()=>((await page.evaluate(()=>window.__town!.state())) as any).camera.height).toBeLessThan(300);
  await expect(page.getByRole('button',{name:'Play',exact:true})).toBeInViewport();
  await page.getByRole('button',{name:'Follow resident'}).click();await page.keyboard.press('Escape');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBe(390);
});
test('zoom, manual pan, timeline boundaries, speed and end of day',async({page})=>{
  await ready(page);await page.getByLabel('Map zoom').selectOption('2');
  await expect.poll(async()=>((await page.evaluate(()=>window.__town!.state())) as any).camera.zoom).toBe(2);
  const previous=(await page.evaluate(()=>window.__town!.state()) as any).camera.scrollX;
  await page.locator('#canvas-host').focus();await page.keyboard.press('ArrowRight');
  expect((await page.evaluate(()=>window.__town!.state()) as any).camera.scrollX).toBeGreaterThan(previous);
  await page.getByRole('button',{name:'Recenter'}).click();await page.getByRole('button',{name:'4×',exact:true}).click();
  await seek(page,23.99);await page.getByRole('button',{name:'Play',exact:true}).click();
  await expect.poll(async()=>((await page.evaluate(()=>window.__town!.state())) as any).time).toBe(24);
  await expect(page.getByRole('button',{name:'Play',exact:true})).toBeVisible();
  await page.getByLabel('Loop',{exact:true}).check();await page.getByRole('button',{name:'Play',exact:true}).click();
  await page.getByRole('button',{name:'Pause',exact:true}).click();
  expect((await page.evaluate(()=>window.__town!.state()) as any).time).toBeLessThan(1);
});
test('self-contained file replay opens offline without any requests',async({page})=>{
  const requests:string[]=[],errors:string[]=[];page.on('request',r=>{if(!r.url().startsWith('file:')&&!r.url().startsWith('data:'))requests.push(r.url());});page.on('pageerror',e=>errors.push(e.message));
  await page.goto('file:///'+resolve('../.artifacts/export/town.html').replaceAll('\\','/'));
  await page.waitForFunction(()=>window.__town?.ready());await expect(page.getByRole('button',{name:'30 residents'})).toBeVisible();
  expect(requests).toEqual([]);expect(errors).toEqual([]);
});
test('all 30 residents can occupy each action without overlapping anchors',async({page})=>{
  await ready(page);
  for(const action of ['eat','work','sleep','socialize','wander']){
    const run=JSON.parse(readFileSync(resolve(`../tests/fixtures/occupancy-${action}.json`),'utf8'));
    await page.locator('#recording').setInputFiles({name:`${action}.json`,mimeType:'application/json',buffer:Buffer.from(JSON.stringify(run))});
    await expect(page.getByRole('status')).toBeHidden();await page.waitForFunction(()=>window.__town?.ready());await seek(page,14.99);
    const state=await page.evaluate(()=>window.__town!.state()) as any;
    expect(state.counts[action]).toBe(30);expect(new Set(state.people.map((p:any)=>`${p.x},${p.y}`)).size).toBe(30);
      if(action==='socialize')expect(state.people.filter((p:any)=>p.bubbleVisible)).toHaveLength(8);
      if(action!=='sleep')expect(state.people.filter((p:any)=>p.visible)).toHaveLength(30);
      if(action==='work'||action==='wander') for(let i=0;i<30;i++)for(let j=i+1;j<30;j++){
        const a=state.people[i],b=state.people[j];expect((a.x-b.x)**2+(a.y-b.y)**2).toBeGreaterThanOrEqual(32**2);
      }
    if(action==='eat'){
      const rows=new Set(state.people.map((p:any)=>p.y));expect(rows.size).toBe(3);
      const ordered=[...rows].sort((a:any,b:any)=>a-b) as number[];
      expect(ordered[1]-ordered[0]).toBeGreaterThanOrEqual(32);
    }
    await page.screenshot({path:`../.artifacts/occupancy-${action}.png`});
  }
});
test('recorded names are text, never executable markup',async({page})=>{
  await ready(page);
  const run=JSON.parse(readFileSync(resolve('src/fixture-30.json'),'utf8'));
  run.residents[0].name='<img src=x onerror="window.PWNED=1">';
  await page.locator('#recording').setInputFiles({name:'text.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(run))});
  await page.waitForFunction(()=>window.__town?.ready());await page.getByRole('button',{name:'30 residents'}).click();
  await expect(page.locator('#resident-list img')).toHaveCount(0);
  await expect(page.locator('#resident-list')).toContainText('<img src=x onerror=');
  expect(await page.evaluate(()=>Object.hasOwn(window,'PWNED'))).toBe(false);
});
test('baseline desktop daylight, inspector, night, population, summary',async({page})=>{
  await ready(page);await seek(page,14);await expect(page).toHaveScreenshot('desktop-day.png');
  await page.getByRole('button',{name:'30 residents'}).click();await page.getByRole('button',{name:/Bea social/}).click();
  await expect(page).toHaveScreenshot('desktop-bea.png');await page.keyboard.press('Escape');await seek(page,23);
  await expect(page).toHaveScreenshot('desktop-night.png');await seek(page,14);
  await page.getByRole('button',{name:'30 residents'}).click();await expect(page).toHaveScreenshot('desktop-population.png');
  await page.keyboard.press('Escape');await page.getByRole('button',{name:'Open day summary'}).click();await expect(page).toHaveScreenshot('desktop-summary.png');
});
test('baseline mobile daylight, inspector, night, population, summary',async({page})=>{
  await page.setViewportSize({width:390,height:844});await ready(page);await seek(page,14);await expect(page).toHaveScreenshot('mobile-day.png');
  await page.getByRole('button',{name:'30 residents'}).click();await page.getByRole('button',{name:/Bea social/}).click();
  await expect(page).toHaveScreenshot('mobile-bea.png');await page.keyboard.press('Escape');await seek(page,23);await expect(page).toHaveScreenshot('mobile-night.png');await seek(page,14);
  await page.getByRole('button',{name:'30 residents'}).click();await expect(page).toHaveScreenshot('mobile-population.png');await page.keyboard.press('Escape');
  await page.getByRole('button',{name:'Open day summary'}).click();await expect(page).toHaveScreenshot('mobile-summary.png');
});
