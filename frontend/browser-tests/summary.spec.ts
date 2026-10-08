import {test,expect} from '@playwright/test';
import type {Page} from '@playwright/test';
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';

const sample=JSON.parse(readFileSync(resolve('src/fixture-30.json'),'utf8'));
async function ready(page:Page){await page.goto('/');await page.waitForFunction(()=>window.__town?.ready());}

test('highlights count the full recorded day and jump to a paused resident moment',async({page})=>{
  await ready(page);
  await page.getByRole('button',{name:'Play',exact:true}).click();
  await page.getByRole('button',{name:'Open day summary'}).click();
  await expect(page.locator('.day-highlight')).toHaveCount(3);
  const work=page.locator('[data-highlight-action="work"]');
  const scores=sample.residents.map((p:any,i:number)=>({id:p.id,hours:sample.frames.filter((f:any)=>f.residents[i].decision.appliedAction==='work').length}));
  const maximum=Math.max(...scores.map((p:any)=>p.hours));
  await expect(work.locator('.highlight-hours')).toContainText(`${maximum} recorded hours working`);
  const first=work.locator('[data-highlight-resident]').first();
  const id=await first.getAttribute('data-highlight-resident');
  const tick=Number(await first.getAttribute('data-highlight-tick'));
  const name=sample.residents.find((p:any)=>p.id===id).name;
  await first.focus();await page.keyboard.press('Enter');
  await expect(page.locator('#summary')).not.toBeVisible();
  await expect(page.locator('#inspector h2')).toHaveText(name);
  await expect(page.locator('#inspector .current-action')).toContainText('Working');
  await expect.poll(async()=>{const state=await page.evaluate(()=>window.__town!.state()) as any;return [state.time,state.playing,state.selected];}).toEqual([tick+.99,false,id]);
  await expect(page.getByRole('button',{name:'Follow resident'})).toBeFocused();
});

test('zero categories and all ties remain honest, bounded and reachable',async({page})=>{
  await ready(page);
  const run=JSON.parse(readFileSync(resolve('../tests/fixtures/occupancy-sleep.json'),'utf8'));
  await page.locator('#recording').setInputFiles({name:'all-rest.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(run))});
  await page.waitForFunction(()=>window.__town?.ready());
  await page.getByRole('button',{name:'Open day summary'}).click();
  await expect(page.locator('[data-highlight-action="socialize"]')).toContainText('No recorded socializing.');
  await expect(page.locator('[data-highlight-action="work"] [data-highlight-resident]')).toHaveCount(0);
  const rest=page.locator('[data-highlight-action="sleep"]');
  await expect(rest).toContainText('30 residents share the lead.');
  await expect(rest.locator('[data-highlight-resident]:visible')).toHaveCount(3);
  await rest.getByText('Show 27 more tied residents').click();
  await expect(rest.locator('[data-highlight-resident]:visible')).toHaveCount(30);
  await rest.getByRole('button',{name:'Watch Luca resting',exact:true}).click();
  await expect(page.locator('#inspector h2')).toHaveText('Luca');
  expect((await page.evaluate(()=>window.__town!.state()) as any).time).toBe(.99);
});

test('highlight names are escaped and opening the summary never changes replay state',async({page})=>{
  await ready(page);
  const run=structuredClone(sample);
  run.residents[0].name='<img src=x onerror="window.PWNED=1">';
  await page.locator('#recording').setInputFiles({name:'text-highlight.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(run))});
  await page.waitForFunction(()=>window.__town?.ready());
  await page.locator('#seek').fill('23.99');await page.waitForTimeout(80);
  const before=await page.evaluate(()=>window.__town!.state());
  const requests:string[]=[];page.on('request',r=>{if(r.resourceType()!=='image')requests.push(r.url());});
  await page.getByRole('button',{name:'Open day summary'}).click();
  await expect(page.locator('.day-highlights img')).toHaveCount(0);
  await expect(page.locator('.day-highlights')).toContainText('<img src=x onerror=');
  expect(await page.evaluate(()=>Object.hasOwn(window,'PWNED'))).toBe(false);
  expect(await page.evaluate(()=>window.__town!.state())).toEqual(before);
  expect(requests).toEqual([]);
});

test('mobile highlights and expanded ties fit without page overflow',async({page})=>{
  await page.setViewportSize({width:390,height:844});await ready(page);
  await page.getByRole('button',{name:'Open day summary'}).click();
  for(const card of await page.locator('.day-highlight').all()){
    await card.scrollIntoViewIfNeeded();const box=await card.boundingBox();
    expect(box!.x).toBeGreaterThanOrEqual(0);expect(box!.x+box!.width).toBeLessThanOrEqual(390);
  }
  expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBe(390);
  const last=page.locator('[data-highlight-action="sleep"] [data-highlight-resident]').first();
  await last.click();await expect(page.locator('#inspector')).toBeVisible();
  await expect(page.getByRole('button',{name:'Play',exact:true})).toBeInViewport();
});
