import {test,expect} from '@playwright/test';
import type {Page} from '@playwright/test';
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';

const sample=JSON.parse(readFileSync(resolve('../tests/fixtures/memories.json'),'utf8'));
async function load(page:Page,run=sample){
  await page.goto('/');await page.waitForFunction(()=>window.__town?.ready());
  await page.locator('#recording').setInputFiles({name:'memories.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(run))});
  await page.waitForFunction(()=>window.__town?.ready() && (window.__town.state() as any).people.length===6);
  await page.locator('#population-button').click();await page.locator('[data-resident="npc00"]').click();
}

test('familiarity follows completed hours, survives seeks and links to a neighbor',async({page})=>{
  await load(page);
  const errors:string[]=[],requests:string[]=[];page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>{if(r.resourceType()!=='image')requests.push(r.url());});
  await page.locator('#seek').fill('0.99');await expect(page.locator('.memory-empty')).toBeVisible();
  await page.locator('#seek').fill('1');
  await expect(page.locator('[data-familiar]')).toHaveCount(3);
  await expect(page.locator('[data-familiar="npc01"]')).toContainText('1 meeting');
  await page.locator('#seek').fill('12.99');await expect(page.locator('[data-familiar="npc01"]')).toContainText('12 meetings');
  await page.locator('#seek').fill('1');await expect(page.locator('[data-familiar="npc01"]')).toContainText('1 meeting');
  await page.locator('[data-familiar="npc01"]').focus();await page.keyboard.press('Enter');
  await expect(page.locator('#inspector h2')).toHaveText('Milo');
  await expect(page.locator('[data-familiar="npc00"]')).toContainText('1 meeting');
  await page.locator('#day-tools summary').click();await page.getByRole('button',{name:'Restart',exact:true}).click();await expect(page.locator('.memory-empty')).toBeVisible();
  expect(errors).toEqual([]);expect(requests).toEqual([]);
});

test('invalid memory import preserves replay; legacy recordings invent no familiarity',async({page})=>{
  await load(page);await page.locator('#seek').fill('1');
  await expect(page.locator('[data-familiar]')).toHaveCount(3);
  const bad=structuredClone(sample);bad.frames[0].memoryUpdates[0].meetings=99;
  await page.locator('#recording').setInputFiles({name:'bad-memory.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(bad))});
  await expect(page.getByRole('status')).toContainText('Could not load');
  await expect(page.locator('[data-familiar="npc01"]')).toContainText('1 meeting');
  const legacy=JSON.parse(readFileSync(resolve('src/fixture-6.json'),'utf8'));
  await page.locator('#recording').setInputFiles({name:'legacy.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(legacy))});
  await page.waitForFunction(()=>window.__town?.ready());await page.locator('#population-button').click();
  await page.locator('[data-resident="npc00"]').click();await expect(page.locator('#familiar-title')).toHaveCount(0);
});

test('familiar neighbor names stay text and reunion lines use previous meetings',async({page})=>{
  const run=structuredClone(sample);run.residents[1].name='<img src=x onerror="window.PWNED=1">';
  await load(page,run);await page.locator('#seek').fill('1.99');
  await expect(page.locator('.familiar-neighbors')).toContainText('<img src=x onerror=');
  await expect(page.locator('.familiar-neighbors img')).toHaveCount(0);
  await page.getByRole('button',{name:'Read conversation',exact:true}).click();
  await expect(page.locator('#conversation')).toContainText('shared 1 break before');
  expect(await page.evaluate(()=>Object.hasOwn(window,'PWNED'))).toBe(false);
});

for(const width of [1440,390])test(`baseline familiar neighbors at ${width}px`,async({page})=>{
  await page.setViewportSize({width,height:width===1440?900:844});await load(page);
  await page.locator('#seek').fill('2');
  await expect(page.locator('[data-familiar="npc01"]')).toContainText('2 meetings');
  await page.locator('#familiar-title').scrollIntoViewIfNeeded();
  await expect(page.locator('[data-familiar="npc01"]')).toBeInViewport();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBe(width);
  await expect(page).toHaveScreenshot(`memories-${width}.png`);
});
