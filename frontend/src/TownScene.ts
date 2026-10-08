import Phaser from 'phaser';
import { Playback, nightAlpha } from './playback';
import tokens from './design-tokens.json';
import world from './world.json';
import type { Identity } from './contracts';
import type { Point } from './contracts';

const urls = import.meta.glob('./assets/*.png', { eager: true, query: '?url', import: 'default' }) as Record<string, string>;
const hex = (color: string) => parseInt(color.slice(1), 16);
const rng = (seed: number) => () => { seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0; return seed / 4294967296; };

export class TownScene extends Phaser.Scene {
  people: Phaser.GameObjects.Sprite[] = [];
  shadows: Phaser.GameObjects.Ellipse[] = [];
  houses = new Map<string, Phaser.GameObjects.Image>();
  fronts = new Map<string, Phaser.GameObjects.Image>();
  interiors = new Map<string, Phaser.GameObjects.Graphics>();
  selection!: Phaser.GameObjects.Ellipse;
  nameplate!: Phaser.GameObjects.Text;
  tooltip!: Phaser.GameObjects.Text;
  lighting!: Phaser.GameObjects.Rectangle;
  lampGlows: Phaser.GameObjects.Graphics[] = [];
  selected: string | null = null;
  following = false;
  reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  ready = false;
  cameraChanged = false;
  private lastWidth = 0;
  private lastHeight = 0;
  private manualZoom = 0;
  constructor(public playback: Playback, public onSelect: (resident: Identity) => void,
              public onPan: () => void) { super('town'); }
  preload() {
    for (const [path, url] of Object.entries(urls)) {
      const key = path.split('/').pop()!.replace('.png', '');
      if (key === 'residents') this.load.spritesheet(key, url, { frameWidth: 24, frameHeight: 32 });
      else this.load.image(key, url);
    }
  }
  create() {
    const camera = this.cameras.main;
    camera.roundPixels = true;
    camera.setBackgroundColor(tokens.colors.grass);
    this.drawGround();
    this.drawScenery();
    this.playback.run.residents.forEach((identity, i) => {
      const shadow = this.add.ellipse(0, 0, 15, 5, 0x332a23, .22);
      this.shadows.push(shadow);
      const row = Number(identity.appearanceId.slice(-2));
      const sprite = this.add.sprite(0, 0, 'residents', row * 74 + 16).setOrigin(.5, 31 / 32);
      sprite.setInteractive({ useHandCursor: true });
      sprite.on('pointerup', (pointer:Phaser.Input.Pointer) => {if(pointer.getDistance()<6)this.onSelect(identity);});
      this.people.push(sprite);
    });
    this.selection = this.add.ellipse(0, 0, 22, 9).setStrokeStyle(2, 0xf7edd8).setVisible(false);
    this.nameplate = this.add.text(0, 0, '', { fontFamily: 'Georgia', fontSize: '14px', color: '#332a23',
      backgroundColor: '#f7edd8', padding: { x: 5, y: 3 } }).setOrigin(.5, 1).setVisible(false);
    this.tooltip = this.add.text(0,0,'',{fontFamily:'Georgia',fontSize:'14px',color:'#332a23',backgroundColor:'#f7edd8',padding:{x:6,y:4}}).setOrigin(.5,1).setDepth(10004).setVisible(false);
    this.lighting = this.add.rectangle(512, 320, 1024, 640, hex(tokens.colors.nightTint), 1).setAlpha(0).setDepth(10000);
    let drag: { x: number; y: number; scrollX: number; scrollY: number } | null = null;
    this.input.on('pointerdown', (p: Phaser.Input.Pointer) => { drag = { x: p.x, y: p.y, scrollX: camera.scrollX, scrollY: camera.scrollY }; });
    this.input.on('pointermove', (p: Phaser.Input.Pointer) => {
      if (!drag || !p.isDown || Math.hypot(p.x - drag.x, p.y - drag.y) < 5) return;
      this.following = false; this.onPan(); this.cameraChanged = true;
      camera.scrollX = Math.round(drag.scrollX - (p.x - drag.x) / camera.zoom);
      camera.scrollY = Math.round(drag.scrollY - (p.y - drag.y) / camera.zoom);
    });
    this.input.on('pointerup', () => { drag = null; });
    this.ready = true;
    this.fit(true);
    this.update(0, 0);
  }
  private drawGround() {
    const texture = this.textures.createCanvas('terrain', 1024, 640)!;
    const c = texture.context, random = rng(7);
    const ground = new Set(world.walkable.map(([x, y]) => `${x},${y}`));
    c.fillStyle = tokens.colors.grass; c.fillRect(0, 0, 1024, 640);
    for (let y = 0; y < 40; y++) for (let x = 0; x < 64; x++) {
      const water = x >= 57 && x < 60, bridge = y >= 22 && y < 25 && x >= 56 && x < 61;
      const garden = x >= 29 && x < 43 && y >= 27 && y < 35;
      const square = x >= 20 && x < 36 && y >= 14 && y < 24;
      const path = ground.has(`${x},${y}`);
      c.fillStyle = water ? tokens.colors.water : garden ? '#987852' : path ? square ? '#bdb59d' : tokens.colors.path : tokens.colors.grass;
      c.fillRect(x * 16, y * 16, 16, 16);
      for (let i = 0; i < 12; i++) {
        const dx = Math.floor(random() * 15), dy = Math.floor(random() * 15);
        c.fillStyle = water ? (i % 2 ? '#a0c6ce' : '#52899d') : path ? (i % 2 ? '#c8b48d' : '#ead3a6') : (i % 2 ? '#a0ae71' : '#829459');
        c.fillRect(x * 16 + dx, y * 16 + dy, i % 3 ? 1 : 2, 1);
      }
      if (square) {
        c.strokeStyle = '#a59e89'; c.lineWidth = 1;
        for (let yy = 0; yy < 16; yy += 8) { c.strokeRect(x*16+(yy ? 4 : 0), y*16+yy, 8, 7); c.strokeRect(x*16+(yy ? 12 : 8), y*16+yy, 8, 7); }
      }
      if (!path && !water && !garden) {
        // Broken grass clusters soften tile edges without changing navigable ground.
        for(let tuft=0;tuft<3;tuft++) {
          const px=x*16+2+Math.floor(random()*12),py=y*16+2+Math.floor(random()*12);
          c.fillStyle=tuft%2?'#78915a':'#9bac6d';
          c.fillRect(px,py,4,2);c.fillRect(px+1,py-2,1,3);c.fillRect(px+3,py-1,1,2);
        }
        for(const [dx,dy] of [[0,1],[1,0],[0,-1],[-1,0]]) {
          if(!ground.has(`${x+dx},${y+dy}`))continue;
          c.fillStyle='#acb57a';
          for(let edge=0;edge<16;edge+=4) {
            const px=x*16+(dx?dx>0?14:0:edge),py=y*16+(dy?dy>0?14:0:edge);
            c.fillRect(px,py,dx?2:3,dy?2:3);
          }
        }
      }
      if (bridge) {
        c.fillStyle = '#8b6643'; c.fillRect(x*16,y*16,16,16);
        c.fillStyle = '#c99d62'; c.fillRect(x*16+1,y*16,13,16);
        c.fillStyle = '#e0b77d'; c.fillRect(x*16+2,y*16+2,1,12);
      }
    }
    // Natural riverbanks, pebbles, and a timber-railed crossing.
    for (let y=0;y<640;y+=12) {
      if (y>=352 && y<400) continue;
      const bend=Math.round(Math.sin(y/43)*3);
      c.fillStyle='#52764d';c.fillRect(903+bend,y,6,11);c.fillRect(961,y+2,5,8);
      c.fillStyle='#c8c09b'; c.fillRect(907+bend,y+2,5,7); c.fillRect(960,y+3,4,6);
      c.fillStyle='#738b69'; c.fillRect(901+bend,y+4,5,4);
      c.fillStyle='#6c7771';c.fillRect(906+bend,y+6,5,4);c.fillRect(960,y+5,6,4);
      c.fillStyle='#bcc3b3';c.fillRect(907+bend,y+6,3,1);c.fillRect(961,y+5,3,1);
      c.fillStyle='#b2d4d4';c.fillRect(917+(y%5)*4,y+4,6,1);c.fillRect(945,y+8,7,1);
    }
    for (const y of [352,394]) {
      c.fillStyle='#604b37'; c.fillRect(895,y,83,4);
      for (let x=896;x<978;x+=16) c.fillRect(x,y-5,3,11);
    }
    // Garden beds have the same explicit collision rows as the Python grid.
    for (const x of [30,33,36,39,42]) for (let y=28;y<34;y++) {
      if(y===31) continue;
      c.fillStyle='#634c36'; c.fillRect(x*16+1,y*16+2,13,12);
      c.fillStyle='#3d6745'; c.fillRect(x*16+4,y*16+3,8,7);
      c.fillStyle='#749754'; c.fillRect(x*16+6,y*16+2,5,4);
      c.fillStyle=x%2?'#c69b47':'#b66551'; c.fillRect(x*16+6,y*16+6,3,3);
    }
    // Fence with a gap at the authored door and footpaths through the garden.
    c.fillStyle='#715b3e';
    c.fillRect(464,558,224,3); c.fillRect(464,437,83,3); c.fillRect(580,437,108,3);
    for (let x=464;x<=688;x+=16) { c.fillRect(x,551,3,12); if(x<548||x>580)c.fillRect(x,430,3,13); }
    texture.refresh();
    this.add.image(0, 0, 'terrain').setOrigin(0).setDepth(-1000);
  }
  private drawScenery() {
    const image = (key: string, x: number, y: number, depth = y) => this.add.image(x,y,key).setOrigin(.5,1).setDepth(depth);
    for (const b of world.buildings) {
      const [x,y,w,h] = b.footprintTiles;
      if(b.kind === 'garden') continue;
      const key = b.kind === 'cottage' ? b.id+'-roof' : b.kind;
      const house = image(key, x*16+w*8, (y+h)*16, (y+h)*16+2);
      this.houses.set(b.id, house);
      house.setInteractive({useHandCursor:true});
      house.on('pointerover',()=>this.tooltip?.setText(b.kind==='cottage'?`Cottage ${b.id.slice(-2)} · 5 residents`:b.kind[0].toUpperCase()+b.kind.slice(1)).setPosition(x*16+w*8,y*16).setVisible(true));
      house.on('pointerout',()=>this.tooltip?.setVisible(false));
      if(b.kind==='cottage')house.on('pointerup',(pointer:Phaser.Input.Pointer)=>{
        if(pointer.getDistance()>=6)return;
        const sleeper=this.playback.run.residents.find((p,i)=>p.homeId===b.id&&this.playback.entry(i).decision.appliedAction==='sleep');
        if(sleeper)this.onSelect(sleeper);
      });
      if(b.kind==='cottage') {
        this.fronts.set(b.id,image(b.id+'-front',x*16+w*8,(y+h)*16,(y+h)*16+3));
      }
      if(b.kind === 'cottage') {
        const floor = this.add.graphics().setDepth(y*16-1).setVisible(false);
        floor.fillStyle(0x765a3e); floor.fillRect(x*16,y*16,w*16,h*16);
        floor.lineStyle(1,0xa4855c);
        for(let yy=y*16;yy<(y+h)*16;yy+=8) floor.lineBetween(x*16,yy,(x+w)*16,yy);
        floor.lineStyle(3,0x544334); floor.strokeRect(x*16,y*16,w*16,h*16);
        this.interiors.set(b.id,floor);
      }
      const glow = this.add.graphics().setDepth(10001);
      for(const offset of b.kind==='cottage'?[-29,29]:[0]) {
        glow.fillStyle(0xffd17a,.14); glow.fillCircle(x*16+w*8+offset,(y+h)*16-22,18);
        glow.fillStyle(0xffd17a,.2); glow.fillCircle(x*16+w*8+offset,(y+h)*16-22,9);
      }
      glow.setBlendMode(Phaser.BlendModes.ADD);
      this.lampGlows.push(glow);
    }
    image('fountain',440,320,321);
    // Authored benches and cafe props: interaction slots remain individually spaced.
    for(const [x,y] of [[756,288],[820,384],[772,416]]) image('bench',x,y);
    for(const [x,y] of [[84,330],[148,330],[84,400],[148,400]]) image('table',x,y);
    const furniture=this.add.graphics();
    for(let row=0;row<3;row++) {
      furniture.fillStyle(0x745738); furniture.fillRect(64,338+row*32,160,3);
      furniture.fillStyle(0xb18b59); furniture.fillRect(64,335+row*32,160,3);
    }
    furniture.setDepth(333);
    for(let i=0;i<10;i++) {
      const x=264+(i%2)*32,y=436+Math.floor(i/2)*32;
      this.add.rectangle(x,y,14,6,0x805e3e).setDepth(y-10);
      this.add.rectangle(x,y-3,13,2,0xb89568).setDepth(y-9);
    }
    for(let i=0;i<10;i++) {
      const x=360+(i%5)*32,y=340+Math.floor(i/5)*32;
      this.add.rectangle(x,y,14,6,0x805e3e).setDepth(y-10);
      this.add.rectangle(x,y-3,13,2,0xb89568).setDepth(y-9);
    }
    const ground=new Set(world.walkable.map(([x,y])=>`${x},${y}`));
    const occupied = (x:number,y:number) => world.buildings.some(b => {
      const [bx,by,bw,bh]=b.footprintTiles; return x>=bx-1&&x<bx+bw+1&&y>=by-1&&y<by+bh+1;
    });
    const random=rng(15), placed:Point[]=[];
    for(let i=0;i<600;i++) {
      const tx=Math.floor(random()*64),ty=Math.floor(random()*40);
      if(tx>=56&&tx<61 || ground.has(`${tx},${ty}`) || occupied(tx,ty) || placed.some(p=>Math.hypot(p.x-tx,p.y-ty)<3)) continue;
      placed.push({x:tx,y:ty});
      const key=['tree-large','tree-medium','tree-small'][i%3];
      const obj=image(key,tx*16+8,ty*16+12);
      obj.setTint(i%4===0?0xd6dcba:0xffffff);
    }
    for(let i=0;i<180;i++) {
      const tx=Math.floor(random()*56),ty=Math.floor(random()*40);
      if(ground.has(`${tx},${ty}`)||occupied(tx,ty))continue;
      image('flowers',tx*16+8,ty*16+16);
    }
    // Dense low planting borders, all rooted outside the authoritative walkable grid.
    for(let ty=1;ty<39;ty++)for(let tx=1;tx<56;tx++) {
      if(ground.has(`${tx},${ty}`)||occupied(tx,ty))continue;
      const besidePath=[[0,1],[1,0],[0,-1],[-1,0]].some(([dx,dy])=>ground.has(`${tx+dx},${ty+dy}`));
      if(!besidePath||random()>.4)continue;
      const x=tx*16+5+Math.floor(random()*7),y=ty*16+10+Math.floor(random()*5);
      image('flowers',x,y).setFlipX(random()<.5);
    }
    for(const [x,y] of [[248,164],[376,164],[504,164],[632,164],[312,326],[584,326],[872,330],[312,572],[712,572],[232,402]]) {
      image('lamp',x,y);
      const glow=this.add.graphics().setDepth(10002);
      for(const [radius,alpha] of [[35,.05],[24,.08],[13,.18],[6,.32]]) { glow.fillStyle(0xffd17a,alpha); glow.fillCircle(x,y-36,radius); }
      glow.setBlendMode(Phaser.BlendModes.ADD);
      this.lampGlows.push(glow);
    }
  }
  fit(reset = false) {
    if (!this.ready) return;
    const width=this.scale.width,height=this.scale.height;
    if (!reset && width===this.lastWidth && height===this.lastHeight) return;
    this.lastWidth=width;this.lastHeight=height;
    this.cameras.main.setViewport(0,0,width,height);
    const available=Math.min(width/1024,height/640);
    // Fit must show the complete town on phones; 1x/2x/3x remain explicit close-up choices.
    // Leave room for map tools/legend on narrow views and protect rounded map edges.
    const fitHeight=Math.max(1,height-(width<600?144:2));
    const fitted=available>=1 ? Math.floor(available) : Math.min(Math.max(1,width-2)/1024,fitHeight/640);
    const zoom=this.manualZoom || fitted;
    this.cameras.main.setZoom(zoom).centerOn(512,320);
    if(this.selected) {
      const index=this.playback.run.residents.findIndex(p=>p.id===this.selected);
      if(index>=0)this.center(index);
    }
    this.cameras.main.scrollX=Math.round(this.cameras.main.scrollX);
    this.cameras.main.scrollY=Math.round(this.cameras.main.scrollY);
    this.cameraChanged=false;
    this.clampCamera();
  }
  zoom(value: number) { this.manualZoom=value; this.fit(true); }
  pan(dx:number,dy:number) {
    this.following=false;this.onPan();this.cameraChanged=true;
    this.cameras.main.scrollX=Math.round(this.cameras.main.scrollX+dx);
    this.cameras.main.scrollY=Math.round(this.cameras.main.scrollY+dy);
    this.clampCamera();
  }
  private clampCamera() {
    const cam=this.cameras.main,w=cam.width/cam.zoom,h=cam.height/cam.zoom;
    // Phaser zooms around the viewport center; scroll is measured before that transform.
    const centerX=cam.scrollX+cam.width/2,centerY=cam.scrollY+cam.height/2;
    cam.scrollX=Math.round((w>=1024?512:Phaser.Math.Clamp(centerX,w/2,1024-w/2))-cam.width/2);
    cam.scrollY=Math.round((h>=640?320:Phaser.Math.Clamp(centerY,h/2,640-h/2))-cam.height/2);
  }
  center(index:number) { const p=this.playback.position(index).position;this.cameras.main.centerOn(p.x,p.y);this.clampCamera(); }
  update(_time:number,delta:number) {
    if(!this.ready)return;
    this.playback.advance(delta/1000);
    this.fit();
    const hour=this.playback.run.startHour+this.playback.time;
    const night=nightAlpha(hour);
    this.lighting.setAlpha(night);
    const background=Phaser.Display.Color.Interpolate.ColorWithColor(
      Phaser.Display.Color.HexStringToColor(tokens.colors.grass),
      Phaser.Display.Color.HexStringToColor(tokens.colors.nightTint),100,night*100);
    this.cameras.main.setBackgroundColor(Phaser.Display.Color.GetColor(background.r,background.g,background.b));
    this.lampGlows.forEach(light=>light.setAlpha(night/.35));
    const selectedIndex=this.playback.run.residents.findIndex(p=>p.id===this.selected);
    const selectedHome=selectedIndex>=0 && this.playback.entry(selectedIndex).decision.appliedAction==='sleep' ? this.playback.run.residents[selectedIndex].homeId : null;
    this.houses.forEach((house,key)=>house.setVisible(key!==selectedHome));
    this.fronts.forEach((front,key)=>front.setVisible(key!==selectedHome));
    this.interiors.forEach((floor,key)=>floor.setVisible(key===selectedHome));
    this.people.forEach((sprite,i)=>{
      const identity=this.playback.run.residents[i],entry=this.playback.entry(i);
      const {position,facing,moving}=this.playback.position(i);
      const action=entry.decision.appliedAction;
      const seconds=this.playback.time*12+((this.playback.run.seed+i*17)%31+31)%31/31;
      const row=Number(identity.appearanceId.slice(-2))*74;
      let frame:number;
      if(moving) frame=facing*4+Math.floor(seconds*8)%4;
      else if(action==='wander')frame=16+facing*2+(this.reducedMotion?0:Math.floor(seconds*2)%2);
      else {
        let direction=action==='sleep'?0:facing;
        if(action==='socialize') {
          const neighbors=this.playback.run.residents.map((_,j)=>j).filter(j=>j!==i&&Math.floor(j/4)===Math.floor(i/4)&&this.playback.entry(j).decision.appliedAction==='socialize');
          if(neighbors.length) {
            const nearest=neighbors.sort((a,b)=>{
              const pa=this.playback.position(a).position,pb=this.playback.position(b).position;
              return Math.hypot(pa.x-position.x,pa.y-position.y)-Math.hypot(pb.x-position.x,pb.y-position.y);
            })[0];
            const other=this.playback.position(nearest).position;
            direction=Math.abs(other.x-position.x)>=Math.abs(other.y-position.y)?other.x>position.x?2:1:other.y>position.y?0:3;
          } else direction=0;
        }
        const start={eat:24,work:40,socialize:56,sleep:72}[action];const fps={eat:4,work:6,socialize:4,sleep:1}[action];
        frame=start+(action==='sleep'?0:direction*4)+Math.floor(seconds*fps)%(action==='sleep'?2:4);
      }
      sprite.setFrame(row+frame).setPosition(position.x,position.y).setDepth(position.y+1);
      const hidden=action==='sleep'&&!moving&&identity.homeId!==selectedHome;
      sprite.setVisible(!hidden);
      this.shadows[i].setPosition(position.x,position.y-1).setDepth(position.y).setVisible(!hidden&&action!=='sleep');
      if(i===selectedIndex) {
        this.selection.setPosition(position.x,position.y).setDepth(position.y+.5).setVisible(true);
        this.nameplate.setText(identity.name).setPosition(position.x,position.y-34).setDepth(10003).setVisible(true);
        if(this.following) {
          const cam=this.cameras.main,targetX=position.x-cam.width/(2*cam.zoom),targetY=position.y-cam.height/(2*cam.zoom);
          const ease=this.reducedMotion ? 1 : Math.min(1,delta/300);
          cam.scrollX=Math.round(cam.scrollX+(targetX-cam.scrollX)*ease);cam.scrollY=Math.round(cam.scrollY+(targetY-cam.scrollY)*ease);
        }
      }
    });
    if(selectedIndex<0) {this.selection.setVisible(false);this.nameplate.setVisible(false);}
    this.clampCamera();
  }
  inspect() { return this.people.map((sprite,i)=>({id:this.playback.run.residents[i].id,x:sprite.x,y:sprite.y,frame:sprite.frame.name,visible:sprite.visible})); }
}
