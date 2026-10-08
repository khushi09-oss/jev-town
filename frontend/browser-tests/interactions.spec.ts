import {test,expect} from '@playwright/test';
import type {Page} from '@playwright/test';
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';

async function ready(page:Page) {
  await page.goto('/');await page.waitForFunction(()=>window.__town?.ready());
  await page.locator('#seek').fill('14.99');
  await page.getByRole('button',{name:'30 residents'}).click();
  await page.getByRole('button',{name:/Bea social/}).click();
}

test('paused playback keeps control content stable for Safari clicks',async({page})=>{
  await page.goto('/');await page.waitForFunction(()=>window.__town?.ready());
  const changes=await page.evaluate(()=>new Promise<number>(resolve=>{
    let count=0;
    const observer=new MutationObserver(records=>{count+=records.length;});
    for(const id of ['population-count','play'])observer.observe(document.getElementById(id)!,{childList:true,subtree:true});
    setTimeout(()=>{observer.disconnect();resolve(count);},150);
  }));
  expect(changes).toBe(0);
});

test('named conversations, personality cues and partner selection survive seek and pause',async({page})=>{
  const errors:string[]=[],requests:string[]=[];
  page.on('pageerror',e=>errors.push(e.message));
  await ready(page);page.on('request',r=>{
    const url=new URL(r.url());
    // WebKit may reload the local portrait image when DOM rows are recreated.
    if(r.resourceType()==='image' && url.origin==='http://127.0.0.1:5173' && url.pathname==='/src/assets/portraits.png')return;
    requests.push(r.url());
  });
  await expect(page.locator('.personality-note')).toContainText('Enjoys company');
  await expect(page.locator('#inspector .caption')).toContainText('Chatting with Otto, June, Hugo');
  await expect(page.getByRole('button',{name:'Visit Otto',exact:true})).toBeVisible();
  const before=await page.evaluate(()=>window.__town!.state());
  await page.waitForTimeout(150);expect(await page.evaluate(()=>window.__town!.state())).toEqual(before);
  await page.locator('#seek').fill('14.1');
  await expect(page.locator('#inspector .caption')).toHaveText('Chatting with June at the town square.');
  await page.locator('#seek').fill('14.99');
  await expect(page.locator('#inspector .caption')).toContainText('Chatting');
  expect(await page.evaluate(()=>window.__town!.state())).toEqual(before);
  await page.getByRole('button',{name:'Visit Otto',exact:true}).click();
  await expect(page.locator('#inspector h2')).toHaveText('Otto');
  await expect(page.locator('.personality-note')).toContainText('slower pace');
  await expect(page.locator('#inspector .caption')).toContainText('Bea');
  await page.locator('#seek').fill('14.1');
  await expect(page.locator('#inspector .caption')).toContainText('Walking to meet');
  expect((await page.evaluate(()=>window.__town!.state()) as any).people.find((p:any)=>p.id==='npc05').chattingWith).toEqual([]);
  await page.keyboard.press('Escape');await page.getByRole('button',{name:'30 residents'}).click();
  await expect(page.locator('.resident-preference').filter({hasText:'energy to spare'})).toHaveCount(10);
  expect(errors).toEqual([]);expect(requests).toEqual([]);
});

test('legacy recordings load without named chats; malformed conversation import preserves replay',async({page})=>{
  await ready(page);
  const run=JSON.parse(readFileSync(resolve('src/fixture-30.json'),'utf8'));
  run.frames[14].residents[0].interaction.partnerIds[0]='npc99';
  await page.locator('#recording').setInputFiles({name:'bad-partners.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(run))});
  await expect(page.getByRole('status')).toContainText('Could not load');
  await expect(page.locator('#inspector .caption')).toContainText('Chatting');
  for(const frame of run.frames)for(const entry of frame.residents)delete entry.interaction;
  await page.locator('#recording').setInputFiles({name:'legacy.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(run))});
  await page.waitForFunction(()=>window.__town?.ready());
  await page.locator('#seek').fill('14.99');
  await page.getByRole('button',{name:'30 residents'}).click();await page.getByRole('button',{name:/Bea social/}).click();
  await expect(page.locator('.conversation-partners')).toHaveCount(0);
  await expect(page.locator('#inspector .caption')).toHaveText('Socializing at the town square.');
  await expect.poll(async()=>{
    const person=(await page.evaluate(()=>window.__town!.state()) as any).people.find((p:any)=>p.id==='npc00');
    return Number(person.frame)>=56&&Number(person.frame)<72&&!person.bubbleVisible;
  }).toBe(true);
});

test('conversation partner names are escaped in inspector and activity history',async({page})=>{
  await ready(page);
  const run=JSON.parse(readFileSync(resolve('src/fixture-30.json'),'utf8'));
  run.residents[5].name='<img src=x onerror="window.PWNED=1">';
  await page.locator('#recording').setInputFiles({name:'text-partner.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(run))});
  await page.waitForFunction(()=>window.__town?.ready());await page.locator('#seek').fill('14.99');
  await page.getByRole('button',{name:'30 residents'}).click();await page.getByRole('button',{name:/Bea social/}).click();
  await expect(page.locator('#inspector img')).toHaveCount(0);
  await expect(page.locator('#inspector .caption')).toContainText('<img src=x onerror=');
  await expect(page.locator('.events')).toContainText('<img src=x onerror=');
  expect(await page.evaluate(()=>Object.hasOwn(window,'PWNED'))).toBe(false);
});

for(const viewport of [{width:1440,height:900},{width:390,height:844}]){
  test(`baseline conversations and traits at ${viewport.width}px`,async({page})=>{
    await page.setViewportSize(viewport);await ready(page);
    await expect(page.locator('#inspector .caption')).toContainText('Chatting');
    await expect(page.getByRole('button',{name:'Play',exact:true})).toBeInViewport();
    await expect(page.getByRole('button',{name:'Visit Otto',exact:true})).toBeInViewport();
    expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBe(viewport.width);
    await expect(page).toHaveScreenshot(`conversation-${viewport.width}.png`);
  });
}
