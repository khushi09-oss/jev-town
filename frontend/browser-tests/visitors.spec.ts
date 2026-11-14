import {test,expect} from '@playwright/test';

test('visitor can discover a neighbor, place a bench, watch a response and undo without requests',async({page})=>{
  const errors:string[]=[],requests:string[]=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('/');await page.waitForFunction(()=>window.__town?.ready());
  page.on('request',r=>{if(['fetch','xhr'].includes(r.resourceType()))requests.push(r.url());});
  await expect(page.getByRole('heading',{name:/A small town/})).toBeVisible();
  await page.getByRole('button',{name:'Meet a neighbor',exact:true}).click();
  await expect(page.locator('#welcome')).toBeHidden();
  await expect(page.locator('#inspector')).toBeVisible();
  await page.keyboard.press('Escape');
  await page.getByRole('button',{name:'Pause',exact:true}).click();
  await page.locator('#seek').fill('14.75');
  await page.getByRole('button',{name:'Place a bench',exact:true}).click();
  await page.getByRole('button',{name:/Park gate/}).click();
  await expect(page.locator('#bench-feedback')).toContainText('Detours begin at 15:00');
  await page.getByRole('button',{name:'Watch the first visitors'}).click();
  await expect(page.locator('#inspector .caption')).toContainText('your bench');
  await page.evaluate(()=>new Promise<void>(resolve=>requestAnimationFrame(()=>requestAnimationFrame(()=>resolve()))));
  const after=await page.evaluate(()=>window.__town!.state());
  await page.locator('#seek').fill('10');await page.locator('#seek').fill('15.99');
  await page.evaluate(()=>new Promise<void>(resolve=>requestAnimationFrame(()=>requestAnimationFrame(()=>resolve()))));
  expect(await page.evaluate(()=>window.__town!.state())).toEqual(after);
  await page.getByRole('button',{name:'Place a bench',exact:true}).click();
  await page.getByRole('button',{name:'Remove bench and restore routes'}).click();
  await expect(page.locator('#bench-feedback')).toContainText('Choose one');
  expect(requests).toEqual([]);expect(errors).toEqual([]);
});

test('baseline living simulation welcome and bench response',async({page})=>{
  await page.goto('/');await page.waitForFunction(()=>window.__town?.ready());
  await expect(page).toHaveScreenshot('welcome-desktop.png');
  await page.getByRole('button',{name:'Place a bench',exact:true}).click();
  await page.getByRole('button',{name:/Garden view/}).click();
  await page.getByRole('button',{name:'Watch the first visitors'}).click();
  await expect(page.locator('#inspector .caption')).toContainText('your bench');
  await expect(page).toHaveScreenshot('bench-desktop.png');
  await page.setViewportSize({width:390,height:844});
  await expect(page).toHaveScreenshot('bench-phone.png');
});

test('a real town moment opens its resident and keyboard day tools preserve playback',async({page})=>{
  await page.goto('/');await page.waitForFunction(()=>window.__town?.ready());
  await page.getByRole('button',{name:'Explore',exact:true}).click();
  await page.locator('#seek').fill('14.99');
  await expect(page.locator('#town-moment')).toBeVisible();
  await page.locator('#town-moment').click();
  await expect(page.locator('#inspector .caption')).toContainText('Chatting');
  const selected=(await page.evaluate(()=>window.__town!.state()) as {selected:string}).selected;
  await page.locator('#day-tools summary').focus();await page.keyboard.press('Space');
  await expect(page.locator('#day-tools')).toHaveAttribute('open','');
  expect((await page.evaluate(()=>window.__town!.state()) as {playing:boolean}).playing).toBe(false);
  await page.keyboard.press('Escape');
  await expect(page.locator('#day-tools')).not.toHaveAttribute('open','');
  expect((await page.evaluate(()=>window.__town!.state()) as {selected:string}).selected).toBe(selected);
});

for(const [width,height] of [[320,900],[375,667],[390,844],[768,900],[1440,900]])test(`exploration stays readable and reachable at ${width}px`,async({page})=>{
  await page.setViewportSize({width,height});await page.goto('/');await page.waitForFunction(()=>window.__town?.ready());
  await expect(page.getByRole('button',{name:'Explore town',exact:true})).toBeInViewport();
  await page.getByRole('button',{name:'Meet a neighbor',exact:true}).click();
  await expect(page.locator('#follow')).toBeInViewport();
  await expect(page.getByRole('button',{name:'Whole town',exact:true})).toBeInViewport();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBe(width);
  if(width<=600)expect((await page.evaluate(()=>window.__town!.state()) as any).camera.zoom).toBe(1);
  await page.screenshot({path:`../.artifacts/living-simulation-${width}.png`});
});
