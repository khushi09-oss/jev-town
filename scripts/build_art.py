r"""Author original resident rigs/terrain and slice the generated scenery family.

Source retained in art/source. All production pixels are nearest-neighbor sampled.
Run from project root: .\.venv\Scripts\python.exe scripts/build_art.py
"""
import json
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageColor

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from simulation.identities import manifest

OUT = ROOT / 'frontend' / 'src' / 'assets'
OUT.mkdir(parents=True, exist_ok=True)
INK = '#332a23'


def shade(color, factor):
    return tuple(min(255, round(c * factor)) for c in ImageColor.getrgb(color))


def resident(look, direction, pose, phase):
    im = Image.new('RGBA', (24, 32))
    d = ImageDraw.Draw(im)
    skin, hair, shirt = look['skin'], look['hair'], look['outfit']
    shadow, cloth = shade(skin, .75), shade(shirt, .72)
    bob = int((pose == 'walk' and phase % 2 == 1) or (pose == 'idle' and phase == 1))
    def rect(box, color):
        x, y, xx, yy = box
        d.rectangle((x, y + bob, xx, yy + bob), fill=color)
    # Shoes, trousers, sleeves, neck: four-direction rig, feet at (12,31).
    step = (1 if phase == 1 else -1 if phase == 3 else 0) if pose == 'walk' else 0
    d.rectangle((7, 26 - step, 10, 30 - step), fill=INK)
    d.rectangle((13, 26 + step, 16, 30 + step), fill=INK)
    d.rectangle((8, 26 - step, 10, 28 - step), fill='#586674')
    d.rectangle((13, 26 + step, 15, 28 + step), fill='#586674')
    rect((6, 16, 17, 26), INK)
    rect((7, 16, 16, 24), cloth)
    rect((8, 16, 15, 23), shirt)
    rect((10, 14, 13, 17), shadow)
    rect((10, 16, 13, 17), skin)
    arm_y = 18 if pose == 'socialize' and phase % 2 else 21
    rect((4, 17, 6, arm_y + 2), cloth)
    rect((5, arm_y, 6, arm_y + 3), skin)
    rect((17, 17, 19, 22), cloth)
    rect((17, 22, 18, 24), skin)
    # Head silhouette and directional face.
    rect((5, 4, 18, 14), INK)
    rect((6, 5, 17, 13), shadow)
    rect((7, 5, 16, 14), skin)
    rect((8, 7, 15, 14), shade(skin, 1.12))
    if direction == 'back':
        rect((6, 4, 17, 14), hair)
        rect((8, 11, 16, 14), shade(hair, .8))
    else:
        rect((6, 3, 17, 6), hair)
        rect((5, 5, 7, 10), hair)
        rect((16, 5, 18, 10), hair)
        if direction == 'down':
            rect((8, 9, 9, 10), INK)
            rect((14, 9, 15, 10), INK)
            rect((9, 9, 9, 9), '#f6ecd7')
            rect((14, 9, 14, 9), '#f6ecd7')
            rect((11, 12, 13, 12), '#975e4b')
        else:
            side = 8 if direction == 'left' else 15
            rect((side, 9, side + 1, 10), INK)
            rect((4 if direction == 'left' else 18, 10,
                  5 if direction == 'left' else 19, 11), skin)
    style = look['hairStyle']
    if style in ('curls', 'beard'):
        for x, y in ((5,4),(8,2),(11,3),(14,2),(17,4),(5,7),(17,7)):
            rect((x, y, x+2, y+2), hair)
            rect((x, y, x, y), shade(hair, 1.4))
        if style == 'curls':
            rect((5, 11, 6, 16), hair)
            rect((17, 11, 18, 16), hair)
        elif direction != 'back':
            rect((8, 13, 15, 15), hair)
            rect((10, 13, 13, 13), skin)
    if style == 'bun':
        rect((9, 0, 14, 3), hair)
        rect((10, 0, 13, 1), shade(hair, 1.12))
    if style == 'bob':
        rect((4, 5, 6, 14), hair)
        rect((17, 5, 19, 14), hair)
    if style == 'cap':
        rect((5, 2, 18, 6), '#315d7c')
        rect((6, 2, 16, 3), '#467b9c')
        rect((8 if direction != 'left' else 3, 6,
              20 if direction != 'left' else 15, 7), '#243e53')
    if look['id'] == 'npc05' or style == 'beard':
        rect((8, 17, 9, 22), '#344d3d')
        rect((14, 17, 15, 22), '#344d3d')
        rect((8, 22, 15, 25), '#344d3d')
        rect((9, 18, 9, 18), '#e0c788')
        rect((14, 18, 14, 18), '#e0c788')
    # Distinct held props and active gestures, not action-colored replacements.
    if pose == 'eat':
        rect((6, 22, 18, 23), '#e9dec5')
        rect((10, 21, 15, 21), '#be854a')
        rect((15, 12 if phase % 2 else 19, 17, 14 if phase % 2 else 21), skin)
    if pose == 'work':
        worker = int(look['id'][3:])
        if worker < 10:
            y = 11 if phase % 2 else 18
            rect((18, y, 18, y+7), '#906b41')
            rect((16, y, 20, y+2), '#667078')
            rect((17, y+5, 19, y+6), skin)
        elif worker < 20:
            y = 19 + phase % 2 * 3
            rect((18, y, 19, y+6), '#906b41')
            rect((17, y+5, 20, y+7), '#667078')
            rect((17, y, 19, y+1), skin)
        else:
            y = 19 + phase % 2 * 2
            rect((15, y, 20, y+5), '#bd9359')
            rect((17, y-1, 18, y), '#644b32')
            rect((15, y+1, 16, y+2), skin)
    if pose == 'socialize':
        rect((3, 14 if phase % 2 else 19, 5, 16 if phase % 2 else 21), skin)
    if pose == 'sleep':
        # Native horizontal sleeping pose, deliberately kept within the same bounds.
        im = Image.new('RGBA', (24, 32))
        d = ImageDraw.Draw(im)
        d.rectangle((2, 18, 21, 29), fill='#765b42')
        d.rectangle((3, 19, 8, 27), fill='#f4e8cf')
        d.rectangle((9, 19 + phase, 20, 27), fill=shirt)
        d.rectangle((4, 20, 9, 25), fill=skin)
        d.rectangle((3, 19, 5, 24), fill=hair)
        d.line((6, 22, 8, 22), fill=INK)
    return im


def portrait(look):
    im = Image.new('RGBA', (64,64), '#d6d1b4')
    d = ImageDraw.Draw(im)
    skin, hair, outfit = look['skin'], look['hair'], look['outfit']
    rng = random.Random(look['id'])
    d.ellipse((7,45,59,88), fill=INK)
    d.ellipse((9,46,57,85), fill=shade(outfit,.7))
    d.polygon([(19,46),(44,46),(52,64),(12,64)], fill=outfit)
    d.rectangle((26,38,38,49), fill=shade(skin,.8))
    d.ellipse((12,6,52,47), fill=hair)
    if look['hairStyle'] in ('curls','beard'):
        for _ in range(40):
            x,y=rng.randint(10,47),rng.randint(4,36)
            d.ellipse((x-3,y-3,x+4,y+4), fill=shade(hair,rng.choice([.7,1,1.35])))
    d.ellipse((19,13,46,45),fill=shade(skin,.8))
    d.ellipse((20,13,44,43),fill=skin)
    d.polygon([(22,16),(41,16),(43,30),(38,40),(25,39),(21,29)], fill=shade(skin,1.08))
    d.rectangle((23,24,27,25),fill=shade(hair,.7))
    d.rectangle((36,24,40,25),fill=shade(hair,.7))
    for x in (24,37):
        d.rectangle((x,27,x+3,30),fill=INK)
        d.point((x+1,27),fill='#fff3db')
    d.line((31,28,30,33,33,33),fill=shade(skin,.7))
    d.line((28,37,35,37),fill='#8d5143')
    d.line((29,38,33,38),fill='#efc197')
    d.rectangle((21,33,24,34),fill='#cf8b6b')
    d.rectangle((39,33,42,34),fill='#cf8b6b')
    # Hair frames the face; outfit cues remain identical to the full-body rig.
    if look['hairStyle']=='bob':
        d.polygon([(15,13),(21,8),(42,8),(50,17),(49,39),(44,43),(43,21),(22,20),(20,40),(15,37)], fill=hair)
        d.line((17,17,17,34),fill=shade(hair,1.6),width=2)
    elif look['hairStyle']=='bun':
        d.ellipse((22,1,40,15),fill=hair)
        d.polygon([(16,17),(21,9),(41,10),(47,20),(40,16),(23,17)],fill=hair)
        d.line((23,11,36,10),fill=shade(hair,1.1),width=2)
    elif look['hairStyle']=='cap':
        d.pieslice((12,3,52,31),180,360,fill='#315d7c')
        d.rectangle((13,15,53,19),fill='#243e53')
        d.line((22,7,41,7),fill='#467b9c',width=2)
    else:
        for _ in range(26):
            x,y=rng.randint(16,44),rng.randint(7,17)
            d.ellipse((x-3,y-3,x+3,y+3),fill=shade(hair,rng.choice([.8,1,1.4])))
        if look['hairStyle']=='beard':
            d.polygon([(21,34),(26,41),(37,43),(45,34),(43,43),(31,49),(22,43)],fill=hair)
            d.line((28,37,35,37),fill=INK)
    if look['hairStyle']=='beard':
        d.rectangle((19,47,23,62),fill='#344d3d')
        d.rectangle((43,47,47,62),fill='#344d3d')
        d.rectangle((22,56,45,63),fill='#344d3d')
    if look['id']=='npc00':
        d.rectangle((18,49,22,63),fill='#304e56')
        d.rectangle((43,49,47,63),fill='#304e56')
    return im


def main():
    looks = manifest()
    sheet = Image.new('RGBA',(24*74,32*30))
    portraits = Image.new('RGBA',(64*6,64*5))
    preview = Image.new('RGBA',(6*96,192),'#f7edd8')
    animations = {'walk': {'start':0,'length':16,'fps':8},
                  'idle': {'start':16,'length':8,'fps':2},
                  'eat': {'start':24,'length':16,'fps':4},
                  'work': {'start':40,'length':16,'fps':6},
                  'socialize': {'start':56,'length':16,'fps':4},
                  'sleep': {'start':72,'length':2,'fps':1}}
    for i, look in enumerate(looks):
        frames = [resident(look,d,'walk',p) for d in ('down','left','right','back') for p in range(4)]
        frames += [resident(look,d,'idle',p) for d in ('down','left','right','back') for p in range(2)]
        frames += [resident(look,d,act,p) for act in ('eat','work','socialize')
                   for d in ('down','left','right','back') for p in range(4)]
        frames += [resident(look,'down','sleep',p) for p in range(2)]
        for f, frame in enumerate(frames):
            sheet.paste(frame,(f*24,i*32))
        face=portrait(look)
        portraits.paste(face,((i%6)*64,(i//6)*64))
        if i<6:
            preview.paste(face.resize((96,96),Image.Resampling.NEAREST),(i*96,0))
            preview.paste(frames[16].resize((48,64),Image.Resampling.NEAREST),(i*96+24,108))
    sheet.save(OUT/'residents.png')
    portraits.save(OUT/'portraits.png')
    preview.save(OUT/'identity-review.png')
    source=Image.open(ROOT/'art/source/scenery-atlas.png').convert('RGBA')
    objects=['home-01','home-02','home-03','home-04','home-05','home-06','bakery','workshop',
             'tree-large','tree-medium','tree-small','fountain','bench','lamp','flowers','table']
    sizes=[(112,96)]*6+[(160,112),(176,144),(80,96),(64,80),(48,64),(56,64),(40,24),(16,48),(32,24),(40,32)]
    scenery={}
    for i,(name,size) in enumerate(zip(objects,sizes)):
        x,y=i%4,i//4
        cell=source.crop((round(x*source.width/4),round(y*source.height/4),round((x+1)*source.width/4),round((y+1)*source.height/4)))
        alpha=cell.getchannel('A')
        bbox=alpha.point(lambda v:255 if v>100 else 0).getbbox()
        assert bbox, f'Missing {name}'
        crop=cell.crop(bbox)
        # Transparent edge cleanup, followed by native nearest-neighbor sampling.
        crop.putalpha(crop.getchannel('A').point(lambda v:255 if v>120 else 0))
        crop=crop.resize(size,Image.Resampling.NEAREST)
        crop.save(OUT/f'{name}.png')
        if name.startswith('home-'):
            roof=Image.new('RGBA',size);front=Image.new('RGBA',size)
            roof.paste(crop.crop((0,0,size[0],56)),(0,0))
            front.paste(crop.crop((0,56,size[0],size[1])),(0,56))
            roof.save(OUT/f'{name}-roof.png');front.save(OUT/f'{name}-front.png')
        scenery[name]={'path':f'{name}.png','size':size,'authorship':'Generated original scenery family; see art/source/scenery-atlas.png'}
    from simulation.world import destination
    atlas={'version':1,'framesPerResident':74,'frameSize':[24,32],'feetPivot':[12,31],
           'collisionFootprint':[10,6],'animations':animations,'residents':looks,
           'portraitSize':[64,64],'scenery':scenery,
           'interactionAnchors': {action:[destination(i,action,14,7) for i in range(30)]
                                  for action in ('eat','work','sleep','socialize','wander')},
           'license':'Project-original authored pixel rigs and generated scenery; no commercial game assets.'}
    (OUT/'manifest.json').write_text(json.dumps(atlas,indent=2))
    print('Built 30 matching portraits, 2,220 animation cells, and isolated layered scenery')


if __name__=='__main__':
    main()
