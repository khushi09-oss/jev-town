import {test,expect} from '@playwright/test';

for(const viewport of [{width:375,height:667},{width:390,height:844},{width:430,height:932}]){
  test(`mobile overview fits the complete town at ${viewport.width}px`,async({page,browserName})=>{
    await page.setViewportSize(viewport);
    const errors:string[]=[];page.on('pageerror',error=>errors.push(error.message));
    await page.goto('/');await page.waitForFunction(()=>window.__town?.ready());
    const camera=()=>page.evaluate(()=>((window.__town!.state()) as {camera:{width:number;height:number;zoom:number;left:number;right:number;top:number;bottom:number}}).camera);
    await expect.poll(async()=>{const c=await camera();return c.width/c.zoom;}).toBeGreaterThanOrEqual(1024-.01);
    await expect.poll(async()=>{const c=await camera();return c.height/c.zoom;}).toBeGreaterThanOrEqual(640-.01);
    await expect.poll(async()=>{const c=await camera();return c.left<=1&&c.top<=1&&c.right>=1023&&c.bottom>=639;}).toBe(true);
    const zoom=page.getByLabel('Map zoom');
    expect(await zoom.evaluate(element=>parseFloat(getComputedStyle(element).fontSize))).toBeGreaterThanOrEqual(14);
    expect((await zoom.boundingBox())!.width).toBeGreaterThanOrEqual(72);
    await expect(zoom).toHaveValue('0');
    await expect(page.getByRole('button',{name:'Play',exact:true})).toBeInViewport();
    expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBe(viewport.width);
    await page.screenshot({path:`../.artifacts/mobile-${browserName}-${viewport.width}.png`});
    await zoom.selectOption('1');await expect.poll(async()=>(await camera()).zoom).toBe(1);
    await page.getByRole('button',{name:'Recenter'}).click();await expect(zoom).toHaveValue('0');
    await expect.poll(async()=>{const c=await camera();return c.width/c.zoom;}).toBeGreaterThanOrEqual(1024-.01);
    await expect.poll(async()=>{const c=await camera();return c.left<=1&&c.top<=1&&c.right>=1023&&c.bottom>=639;}).toBe(true);
    expect(errors).toEqual([]);
  });
}

test('mobile fit survives selection and browser viewport changes',async({page,browserName})=>{
  await page.setViewportSize({width:390,height:844});
  await page.goto('/');await page.waitForFunction(()=>window.__town?.ready());
  await page.getByRole('button',{name:'30 residents'}).click();await page.getByRole('button',{name:/Bea social/}).click();
  for(const viewport of [{width:390,height:680},{width:844,height:390},{width:390,height:844}]){
    await page.setViewportSize(viewport);
    await expect.poll(async()=>{const c=(await page.evaluate(()=>window.__town!.state()) as any).camera;return Math.min(c.width/c.zoom/1024,c.height/c.zoom/640);}).toBeGreaterThanOrEqual(.999);
    await expect.poll(async()=>{const c=(await page.evaluate(()=>window.__town!.state()) as any).camera;return c.left<=1&&c.top<=1&&c.right>=1023&&c.bottom>=639;}).toBe(true);
    await expect(page.getByRole('button',{name:'Play',exact:true})).toBeInViewport();
    await expect(page.locator('#inspector h2')).toHaveText('Bea');
  }
  await page.screenshot({path:`../.artifacts/mobile-${browserName}-selected.png`});
});

test('mobile close-up pan stays inside the town at both edges',async({page})=>{
  await page.setViewportSize({width:390,height:844});await page.goto('/');await page.waitForFunction(()=>window.__town?.ready());
  await page.getByLabel('Map zoom').selectOption('2');
  const camera=async()=>(await page.evaluate(()=>window.__town!.state()) as any).camera;
  for(const key of ['ArrowLeft','ArrowRight','ArrowUp','ArrowDown']){
    await page.locator('#canvas-host').evaluate((element,key)=>{
      for(let i=0;i<40;i++)element.dispatchEvent(new KeyboardEvent('keydown',{key,bubbles:true}));
    },key);
    await expect.poll(async()=>{const c=await camera();return c.left>=-1&&c.right<=1025&&c.top>=-1&&c.bottom<=641;}).toBe(true);
    const c=await camera();
    expect(key==='ArrowLeft'?Math.abs(c.left):key==='ArrowRight'?Math.abs(c.right-1024):key==='ArrowUp'?Math.abs(c.top):Math.abs(c.bottom-640)).toBeLessThanOrEqual(1);
  }
});
