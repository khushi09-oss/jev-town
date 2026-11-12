// Capture actual replay pixels; DOM markers identify the four actors, not the expected answer.
import {chromium} from '../frontend/node_modules/playwright/index.mjs';
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {resolve,join} from 'node:path';
import {pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';

const root=resolve('.artifacts/vision');mkdirSync(root,{recursive:true});
const recording=readFileSync('examples/run.json'),run=JSON.parse(recording);
const hour=9,first=run.frames[hour].residents.find(p=>p.id==='npc06');
assert.equal(first.interaction?.partnerIds.length,3,'Expected the seed-7 June meeting');
const group=[first.id,...first.interaction.partnerIds].sort();
const browser=await chromium.launch();
try{
  const page=await browser.newPage({viewport:{width:1440,height:900},deviceScaleFactor:1});
  const errors=[];let externalRequests=0;
  page.on('pageerror',e=>errors.push(e.message));
  page.on('request',request=>{if(/^https?:/.test(request.url()))externalRequests++;});
  await page.goto(pathToFileURL(resolve('examples/town.html')).href);
  await page.waitForFunction(()=>window.__town?.ready());
  await page.locator('#seek').fill(String(hour+.99));
  await page.getByLabel('Map zoom',{exact:true}).selectOption('3');
  await page.waitForFunction(()=>{
    const c=window.__town.state().camera,host=document.getElementById('canvas-host');
    return c.scaleWidth===host.clientWidth&&c.scaleHeight===host.clientHeight&&Math.abs((c.right-c.left)*c.zoom-c.width)<1;
  });
  // Frame this fixed seed-7 meeting without selecting anyone (nameplates can hide other actors).
  await page.locator('#canvas-host').focus();
  for(const key of ['ArrowLeft','ArrowLeft','ArrowLeft','ArrowLeft','ArrowLeft','ArrowUp','ArrowUp'])await page.keyboard.press(key);
  await page.waitForFunction(()=>{
    const c=window.__town.state().camera;
    return Math.abs((c.left+c.right)/2-352)<1 && Math.abs((c.top+c.bottom)/2-256)<1;
  });
  const cases=[];
  for(const [index,focalId] of group.slice(0,3).entries()){
    const state=await page.evaluate(()=>window.__town.state());
    const person=id=>{
      const identity=run.residents.find(p=>p.id===id),position=state.people.find(p=>p.id===id);
      const entry=run.frames[hour].residents.find(p=>p.id===id);
      assert.equal(entry.decision.appliedAction,'socialize');
      assert.equal(position.x,entry.destination.x);assert.equal(position.y,entry.destination.y);
      assert.equal(position.visible,true);
      return {id,name:identity.name,x:position.x,y:position.y};
    };
    const focal=person(focalId),candidates=Object.fromEntries(group.filter(id=>id!==focalId).map((id,i)=>['ABC'[i],person(id)]));
    await page.evaluate(({focal,candidates,camera})=>{
      document.querySelectorAll('.vision-marker').forEach(element=>element.remove());
      for(const [label,p] of Object.entries({F:focal,...candidates})){
        const x=(p.x-camera.left)*camera.zoom,y=(p.y-camera.top)*camera.zoom;
        if(x<20||x>camera.width-20||y<110||y>camera.height-20)throw Error('Actor outside capture');
        const tag=document.createElement('span');tag.className='vision-marker';tag.textContent=label;
        tag.style.cssText=`position:absolute;left:${x-10}px;top:${y-100}px;width:20px;text-align:center;background:#f7edd8;color:#332a23;border:1px solid #332a23;font:bold 16px system-ui;pointer-events:none`;
        document.getElementById('canvas-host').append(tag);
      }
    },{focal,candidates,camera:state.camera});
    const image=`case-${index}.png`;
    const png=await page.locator('#canvas-host').screenshot({path:join(root,image)});
    cases.push({id:`case-${index}`,image,imageSha256:createHash('sha256').update(png).digest('hex'),focal,candidates});
  }
  assert.deepEqual(errors,[]);
  assert.equal(externalRequests,0,'Replay capture must stay offline');
  writeFileSync(join(root,'cases.json'),JSON.stringify({schemaVersion:1,
    recordingSha256:createHash('sha256').update(recording).digest('hex'),
    runId:run.runId,elapsedHour:hour+.99,viewport:{width:1440,height:900},
    description:'Three focal views of one saved mock meeting; same structured coordinates in both conditions.',cases},null,2)+'\n');
  console.log(`Captured three labeled replay scenes in ${root}`);
}finally{await browser.close();}
