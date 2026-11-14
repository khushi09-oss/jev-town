import {test,expect} from '@playwright/test';
import type {Page} from '@playwright/test';
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';

const sample=JSON.parse(readFileSync(resolve('src/fixture-30.json'),'utf8'));
async function selectBea(page:Page){
  await page.locator('#seek').fill('14.99');
  await page.getByRole('button',{name:'30 residents'}).click();
  await page.getByRole('button',{name:/Bea social/}).click();
  // Selection resizes the camera; WebKit can expose the previous inverse transform until its next render.
  await page.waitForFunction(()=>{
    const c=(window.__town!.state() as any).camera;
    const host=document.getElementById('canvas-host')!;
    return c.scaleWidth===host.clientWidth && c.scaleHeight===host.clientHeight &&
      Math.abs((c.right-c.left)*c.zoom-c.width)<1 && Math.abs((c.bottom-c.top)*c.zoom-c.height)<1;
  });
}
async function ready(page:Page){await page.goto('/');await page.waitForFunction(()=>window.__town?.ready());await selectBea(page);}

test('recorded speech freezes, seeks deterministically and makes no decision requests',async({page})=>{
  const errors:string[]=[],requests:string[]=[];page.on('pageerror',e=>errors.push(e.message));
  await ready(page);page.on('request',r=>{if(r.resourceType()!=='image')requests.push(r.url());});
  const text=await page.locator('#speech-bubble').textContent();
  await expect(page.locator('#speech-bubble')).toContainText('Scripted dialogue');
  const before=await page.evaluate(()=>window.__town!.state());
  await page.waitForTimeout(200);expect(await page.evaluate(()=>window.__town!.state())).toEqual(before);
  await page.locator('#seek').fill('14');await expect(page.locator('#speech-bubble')).toBeHidden();
  await page.locator('#seek').fill('14.99');await expect(page.locator('#speech-bubble')).toHaveText(text!);
  await expect.poll(async()=>await page.evaluate(()=>window.__town!.state())).toEqual(before);
  const people=(before as any).people,group=sample.frames[14].conversations[0];
  const speakers=people.filter((p:any)=>group.participantIds.includes(p.id)&&p.bubbleVisible);
  expect(speakers).toHaveLength(1);expect(speakers[0].id).toBe(speakers[0].dialogue.speakerId);
  await page.locator('#day-tools summary').click();await page.getByRole('button',{name:'Restart',exact:true}).click();await expect(page.locator('#speech-bubble')).toBeHidden();
  expect(errors).toEqual([]);expect(requests).toEqual([]);
});

test('keyboard opens a paused transcript and partner selection preserves the meeting',async({page})=>{
  await ready(page);
  await page.locator('#seek').fill('14.1');
  await page.getByRole('button',{name:'Play',exact:true}).click();
  await page.getByRole('button',{name:'Read conversation',exact:true}).focus();await page.keyboard.press('Enter');
  await expect(page.locator('#conversation')).toBeVisible();
  expect((await page.evaluate(()=>window.__town!.state()) as any).playing).toBe(false);
  await expect(page.locator('.dialogue-waiting')).toContainText('Waiting for all neighbors');
  await expect(page.locator('#conversation')).toContainText('No text model was called');
  await page.keyboard.press('Escape');await expect(page.locator('#conversation')).toBeHidden();
  await expect(page.locator('#inspector h2')).toHaveText('Bea');
  await expect(page.getByRole('button',{name:'Read conversation',exact:true})).toBeFocused();
  await page.locator('#seek').fill('14.99');
  await page.locator('#speech-bubble').click();
  await expect(page.locator('.dialogue-turns li')).toHaveCount(4);
  await page.locator('#conversation').getByRole('button',{name:'Visit Otto',exact:true}).click();
  await expect(page.locator('#inspector h2')).toHaveText('Otto');
  await expect(page.getByRole('button',{name:'Play',exact:true})).toBeInViewport();
});

test('legacy meetings invent no dialogue; malformed scripts preserve the last valid replay',async({page})=>{
  await ready(page);const before=await page.evaluate(()=>window.__town!.state());
  const bad=structuredClone(sample);bad.frames[14].conversations[0].turns[0].speakerId='npc29';
  await page.locator('#recording').setInputFiles({name:'bad-script.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(bad))});
  await expect(page.getByRole('status')).toContainText('Could not load');
  expect(await page.evaluate(()=>window.__town!.state())).toEqual(before);
  const legacy=structuredClone(sample);for(const frame of legacy.frames)delete frame.conversations;
  await page.locator('#recording').setInputFiles({name:'legacy-meetings.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(legacy))});
  await page.waitForFunction(()=>window.__town?.ready());await selectBea(page);
  await expect(page.locator('#speech-bubble')).toBeHidden();await expect(page.locator('#read-conversation')).toHaveCount(0);
  await expect(page.locator('.conversation-partners')).toBeVisible();
});

test('imported dialogue and speaker names remain plain text',async({page})=>{
  await ready(page);const run=structuredClone(sample),attack='<img src=x onerror="window.PWNED=1">';
  run.residents[5].name=attack;
  for(const turn of run.frames[14].conversations[0].turns)turn.text=attack;
  await page.locator('#recording').setInputFiles({name:'text-only.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(run))});
  await page.waitForFunction(()=>window.__town?.ready());await selectBea(page);
  await expect(page.locator('#speech-bubble')).toContainText(attack);
  await page.locator('#speech-bubble').click();
  await expect(page.locator('#conversation')).toContainText(attack);
  await expect(page.locator('#speech-bubble img, #conversation img')).toHaveCount(0);
  expect(await page.evaluate(()=>Object.hasOwn(window,'PWNED'))).toBe(false);
});

for(const viewport of [{width:1440,height:900},{width:390,height:844}]){
  test(`baseline readable dialogue at ${viewport.width}px`,async({page})=>{
    await page.setViewportSize(viewport);await ready(page);
    const bubble=page.locator('#speech-bubble');await expect(bubble).toBeInViewport();
    const box=(await bubble.boundingBox())!;expect(box.x+box.width).toBeLessThanOrEqual(viewport.width);
    expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBe(viewport.width);
    await expect(page).toHaveScreenshot(`speech-${viewport.width}.png`);
    await bubble.click();await expect(page.locator('.dialogue-turns')).toBeVisible();
    await expect(page.locator('.dialogue-turns li p')).toHaveText(sample.frames[14].conversations[0].turns.map((turn:any)=>turn.text));
    expect((await page.evaluate(()=>window.__town!.state()) as any).selected).toBe('npc00');
    await expect(page).toHaveScreenshot(`transcript-${viewport.width}.png`);
  });
}
