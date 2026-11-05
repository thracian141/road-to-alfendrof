"""Generate 16px PS/Xbox control glyphs with transparent backgrounds."""
from pathlib import Path
from PIL import Image, ImageDraw
OUT = Path(__file__).resolve().parents[1] / 'assets/ui/controls'
OUT.mkdir(parents=True, exist_ok=True)
FONT = {'A':['010','101','111','101','101'], 'B':['110','101','110','101','110'], 'X':['101','101','010','101','101'], 'Y':['101','101','010','010','010'], 'L':['100','100','100','100','111'], 'R':['110','101','110','101','101'], 'T':['111','010','010','010','010'], '1':['010','110','010','010','111'], '2':['110','001','010','100','111']}
def text(d, label, color):
    x = (16 - len(label)*4+1)//2
    for c in label:
        for y,row in enumerate(FONT[c]):
            for dx,p in enumerate(row):
                if p=='1': d.point((x+dx,y+5),fill=color)
        x+=4
for family in ['ps','xbox']:
    for action in ['dpad','stick','pause','block','light','heavy','ultimate','roll_left','roll_right']:
        im=Image.new('RGBA',(16,16));d=ImageDraw.Draw(im);white='#e3e7f0';dark='#202637'
        if action in ['block','light','heavy','ultimate']:
            color=({'block':'#78aaff','light':'#ef9bde','heavy':'#70dbb3','ultimate':'#ff887a'} if family=='ps' else {'block':'#70db87','light':'#70acff','heavy':'#f1d776','ultimate':'#ef887e'})[action]
            d.ellipse((1,1,14,14),fill=dark,outline=white)
            if family=='xbox': text(d,{'block':'A','light':'X','heavy':'Y','ultimate':'B'}[action],color)
            elif action=='block':
                d.line((5,5,10,10),fill=color);d.line((10,5,5,10),fill=color)
            elif action=='light': d.rectangle((5,5,10,10),outline=color)
            elif action=='heavy': d.line((7,4,11,10,4,10,7,4),fill=color)
            else: d.ellipse((5,5,10,10),outline=color)
        elif action.startswith('roll'):
            d.rounded_rectangle((0,2,15,13),radius=2,fill=dark,outline=white)
            text(d,('L1' if family=='ps' else 'LB') if action=='roll_left' else ('R1' if family=='ps' else 'RB'),white)
        elif action=='pause':
            d.rounded_rectangle((1,3,14,12),radius=2,fill=dark,outline=white)
            for y in [5,7,9]: d.line((5,y,10,y),fill=white)
        elif action=='dpad':
            d.polygon([(5,1),(10,1),(10,5),(14,5),(14,10),(10,10),(10,14),(5,14),(5,10),(1,10),(1,5),(5,5)],fill=dark,outline=white)
            d.point((7,3),fill=white);d.point((7,12),fill=white);d.point((3,7),fill=white);d.point((12,7),fill=white)
        else:
            d.ellipse((1,1,14,14),fill=dark,outline=white);d.ellipse((4,4,11,11),outline=white);text(d,'L',white)
        im.save(OUT/f'{family}_{action}.png')
