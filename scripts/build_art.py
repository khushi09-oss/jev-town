r"""Author original resident rigs/terrain and slice the generated scenery family.

Source retained in assets/source. All production pixels are nearest-neighbor sampled.
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
    if style in ('short', 'bun', 'cap') and direction != 'back':
        rect((10, 18, 13, 20), '#eee0c4')
        rect((10, 18, 10, 18), shade(shirt, 1.15))
    if style in ('curls', 'beard'):
        bib = '#304e56' if style == 'curls' else '#344d3d'
        rect((8, 17, 9, 22), bib)
        rect((14, 17, 15, 22), bib)
        rect((8, 22, 15, 25), bib)
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
    backgrounds = ['#b5c0a4', '#dcc093', '#cec9b1', '#acc3c7', '#d4b5b7', '#c5c697']
    im = Image.new('RGBA', (64,64), backgrounds[int(look['id'][3:]) % 6])
    d = ImageDraw.Draw(im)
    skin, hair, outfit = look['skin'], look['hair'], look['outfit']
    style = look['hairStyle']
    rng = random.Random(look['id'])
    # Three-quarter bust, stepped silhouettes and clustered highlights at native 64px.
    d.polygon([(7,64),(10,52),(20,46),(27,44),(42,45),(54,51),(59,64)], fill=INK)
    d.polygon([(9,64),(12,53),(22,48),(43,48),(52,53),(57,64)], fill=shade(outfit,.72))
    d.polygon([(17,64),(19,51),(26,47),(43,48),(49,64)], fill=outfit)
    d.polygon([(27,40),(40,39),(40,48),(35,52),(27,48)], fill=shade(skin,.78))
    d.polygon([(29,41),(38,41),(38,48),(34,49),(29,47)], fill=skin)
    if style in ('short', 'bun', 'cap'):
        d.polygon([(26,49),(34,52),(41,48),(43,64),(24,64)], fill='#eee0c4')
        d.polygon([(22,48),(26,49),(28,55),(23,53),(20,59),(17,64),(19,51)], fill=shade(outfit,1.15))
        d.polygon([(41,48),(44,49),(48,64),(43,64),(40,54)], fill=shade(outfit,.85))
        for y in (54,59): d.rectangle((21,y,22,y+1), fill='#d9b66e')
    d.line((13,55,15,63), fill=shade(outfit,1.13), width=2)
    d.line((51,55,52,63), fill=shade(outfit,.6), width=2)
    d.ellipse((12,6,52,48), fill=shade(hair,.6))
    d.ellipse((14,7,51,47), fill=hair)
    if style in ('curls','beard'):
        for _ in range(48):
            x,y=rng.randint(11,48),rng.randint(5,37)
            d.ellipse((x-3,y-3,x+4,y+4), fill=shade(hair,.72))
            d.ellipse((x-2,y-3,x+2,y+1), fill=shade(hair,rng.choice([1,1.35,1.55])))
    d.ellipse((18,26,24,35), fill=shade(skin,.8))
    d.ellipse((45,25,50,34), fill=shade(skin,.82))
    d.polygon([(23,14),(40,12),(47,20),(47,34),(42,42),(34,45),(26,42),(21,34),(21,23)], fill=shade(skin,.76))
    d.polygon([(24,15),(39,14),(44,20),(45,33),(40,40),(33,42),(26,39),(23,32),(23,23)], fill=skin)
    d.polygon([(26,17),(38,16),(41,21),(40,31),(34,35),(26,31),(24,24)], fill=shade(skin,1.12))
    # Raised brows and large warm eyes, with a smaller far eye.
    d.line((25,24,29,23,31,24), fill=shade(hair,.7))
    d.line((38,23,42,23,44,24), fill=shade(hair,.7))
    for x,w in ((25,5),(39,4)):
        d.rectangle((x,27,x+w,32), fill=INK)
        d.rectangle((x,28,x+w,31), fill='#f2e5c8')
        d.rectangle((x+2,27,x+w-1,32), fill='#614733')
        d.rectangle((x+3,28,x+w-1,31), fill=INK)
        d.point((x+2,28), fill='#fff6de')
    d.line((35,29,34,34,37,34), fill=shade(skin,.72))
    d.point((36,32), fill=shade(skin,1.23))
    d.line((30,37,33,38,39,36), fill='#804c3b')
    d.line((33,39,37,38), fill=shade(skin,1.23))
    d.rectangle((25,34,28,35), fill=shade(skin,.94))
    d.rectangle((41,33,43,34), fill=shade(skin,.94))
    if style=='bob':
        d.polygon([(14,17),(21,8),(40,7),(51,16),(51,39),(47,44),(44,39),(46,22),(38,16),(32,21),(24,19),(21,39),(16,40)], fill=hair)
        for x,y in ((18,18),(22,13),(30,12),(42,13),(48,22)):
            d.line((x,y,x-1,y+9), fill=shade(hair,1.5))
    elif style=='bun':
        d.ellipse((20,0,38,13),fill=shade(hair,.7))
        d.ellipse((22,1,37,10),fill=hair)
        d.polygon([(16,21),(20,12),(31,9),(43,13),(49,23),(42,19),(35,14),(26,21),(21,29),(18,34)],fill=hair)
        for points in ((22,6,30,3,34,5),(20,17,26,13,32,12),(35,12,40,15,44,20)):
            d.line(points,fill=shade(hair,1.18))
        d.line((18,24,19,31),fill=shade(hair,1.15),width=2)
    elif style=='cap':
        d.polygon([(15,16),(16,10),(22,5),(34,3),(45,7),(50,15),(47,18),(17,18)],fill='#243e53')
        d.polygon([(17,14),(20,9),(28,5),(38,5),(46,10),(48,15)],fill='#315d7c')
        d.line((22,9,28,6,36,6),fill='#5689a5',width=2)
        d.polygon([(17,15),(43,15),(55,18),(54,21),(31,20),(19,18)],fill='#243e53')
        d.line((32,17,50,18),fill='#467b9c')
        d.polygon([(21,20),(27,19),(26,23),(22,24)],fill=hair)
    else:
        for _ in range(22):
            x,y=rng.randint(17,45),rng.randint(8,17)
            d.ellipse((x-3,y-3,x+3,y+3),fill=shade(hair,rng.choice([.8,1,1.4])))
        d.polygon([(20,16),(28,12),(36,13),(31,19),(26,18),(22,24)],fill=hair)
        if style=='curls':
            for x,y in ((16,26),(17,34),(46,30),(46,38)):
                d.ellipse((x-2,y-2,x+3,y+3),fill=shade(hair,.8))
                d.point((x,y-1),fill=shade(hair,1.4))
            for x in (21,47):
                d.rectangle((x,33,x+1,36),fill='#cba75c')
                d.point((x,33),fill='#f0d78d')
        if style=='beard':
            d.polygon([(23,34),(28,40),(37,41),(46,33),(45,43),(36,48),(28,46),(23,41)],fill=hair)
            for x,y in ((25,38),(28,43),(32,44),(39,42),(43,37)):
                d.line((x,y,x+1,y+2),fill=shade(hair,1.4))
            d.line((31,38,38,37),fill=INK)
            d.line((33,38,37,38),fill='#f3ddbc')
    if style in ('curls','beard'):
        bib = '#304e56' if style=='curls' else '#344d3d'
        d.rectangle((20,49,23,63),fill=bib)
        d.rectangle((43,49,46,63),fill=bib)
        d.rectangle((22,57,45,63),fill=bib)
        for x in (22,44): d.rectangle((x,52,x+1,53),fill='#d5b56b')
        d.line((28,60,39,60),fill=shade(bib,1.45))
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
    portrait_signatures = set()
    for i, look in enumerate(looks):
        frames = [resident(look,d,'walk',p) for d in ('down','left','right','back') for p in range(4)]
        frames += [resident(look,d,'idle',p) for d in ('down','left','right','back') for p in range(2)]
        frames += [resident(look,d,act,p) for act in ('eat','work','socialize')
                   for d in ('down','left','right','back') for p in range(4)]
        frames += [resident(look,'down','sleep',p) for p in range(2)]
        assert len(frames) == 74 and all(frame.size == (24,32) and frame.getbbox() for frame in frames)
        for f, frame in enumerate(frames):
            sheet.paste(frame,(f*24,i*32))
        face=portrait(look)
        assert face.size == (64,64) and face.tobytes() == portrait(look).tobytes(), 'Portrait must be deterministic'
        colors = {color for _, color in face.getcolors(64 * 64)}
        assert ImageColor.getrgb(look['outfit']) + (255,) in colors, 'Portrait must retain outfit color'
        portrait_signatures.add(face.tobytes())
        portraits.paste(face,((i%6)*64,(i//6)*64))
        if i<6:
            preview.paste(face.resize((96,96),Image.Resampling.NEAREST),(i*96,0))
            preview.paste(frames[16].resize((48,64),Image.Resampling.NEAREST),(i*96+24,108))
    assert len(portrait_signatures) == 30, 'Every resident must have a distinct portrait'
    sheet.save(OUT/'residents.png')
    portraits.save(OUT/'portraits.png')
    preview.save(ROOT/'assets/reference/residents.png')
    source=Image.open(ROOT/'assets/source/scenery-atlas.png').convert('RGBA')
    objects=['home-01','home-02','home-03','home-04','home-05','home-06','bakery','workshop',
             'tree-large','tree-medium','tree-small','fountain','bench','lamp','flowers','table']
    sizes=[(112,96)]*6+[(160,112),(176,144),(80,96),(64,80),(48,64),(56,64),(40,24),(16,48),(32,24),(40,32)]
    scenery={}
    for i,(name,size) in enumerate(zip(objects,sizes)):
        x,y=i%4,i//4
        cell=source.crop((round(x*source.width/4),round(y*source.height/4),round((x+1)*source.width/4),round((y+1)*source.height/4)))
        if name in ('flowers', 'bench', 'table'):
            # The tall trees/fountain above bleed into these cells; discard that strip.
            cell = cell.crop((0, cell.height // 4, cell.width, cell.height))
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
        scenery[name]={'path':f'{name}.png','size':size,'authorship':'Generated original scenery family; see assets/source/scenery-atlas.png'}
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
