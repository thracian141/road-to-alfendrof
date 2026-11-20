"""Hand-plotted roll drawings, painted into the existing native sprite canvases.

Each pose has its own silhouette, folded legs, arms, hand and foot placements.
Gray Persona is excluded: her roll intentionally transforms her into a bat.
Only the small head/costume swatches come from idle; no whole-body rotation,
shrinking a crouch, inverse kinematics, or generated-image artwork is used.
"""
from pathlib import Path
from PIL import Image, ImageDraw
import math, json, zipfile

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'tools/previews/animation_review/roll_drawings'
OUT.mkdir(parents=True, exist_ok=True)

# Head rectangle, jacket, shadow, highlight, trousers, trouser shadow, skin,
# skin shadow, shoe and sole. All swatches belong to the original idle palette.
DESIGNS = {
 'baroness': ((25,8,42,29),(155,69,57),(131,55,45),(167,85,74),(155,69,57),(139,58,47),(215,190,168),(188,158,133),(109,87,80),(72,53,49)),
 'anaran': ((23,8,43,28),(179,61,61),(145,49,50),(196,77,75),(179,61,61),(112,28,36),(251,205,174),(229,174,137),(235,168,83),(187,133,64)),
 'ayz': ((25,6,43,25),(240,241,250),(186,192,216),(250,250,255),(246,142,32),(196,98,26),(238,196,158),(222,174,134),(162,162,162),(234,234,234)),
 'evilayz': ((25,8,43,27),(15,14,5),(69,63,39),(5,5,0),(9,113,223),(59,157,229),(17,59,97),(33,81,121),(93,93,93),(21,21,21)),
 'cowboy': ((27,8,41,24),(56,42,40),(37,28,27),(84,66,60),(112,112,118),(88,88,94),(214,180,149),(199,160,128),(150,98,56),(98,62,34)),
 'junkhead': ((25,5,42,25),(12,12,15),(8,8,10),(26,26,30),(112,112,118),(62,62,68),(214,180,149),(199,160,128),(162,162,162),(234,234,234)),
 'scribe': ((26,8,42,27),(84,90,54),(58,64,38),(105,110,68),(190,138,42),(146,98,32),(238,196,158),(222,174,134),(34,34,38),(70,70,78)),
 'goblin_king': ((24,4,44,29),(184,89,89),(165,71,71),(200,127,127),(138,113,170),(114,95,139),(149,188,114),(124,157,94),(149,188,114),(124,157,94)),
 'haymaker': ((25,9,44,28),(38,42,42),(27,31,31),(50,57,57),(95,139,97),(77,116,79),(228,195,158),(201,165,125),(70,70,74),(186,186,190)),
 'katmata': ((25,8,44,28),(229,240,240),(199,207,207),(237,247,247),(110,132,181),(75,90,124),(199,171,146),(166,140,116),(122,88,61),(139,99,67)),
}

# A literal drawing plan for each frame. Polygon corners are in sprite pixels.
# body, two folded trouser silhouettes, then two arms as shoulder/elbow/wrist
# polylines. Hands plant on the floor only in the support and landing poses.
POSES = [
 dict(head=(41,35,-12), body=[(29,40),(36,39),(42,44),(39,49),(30,54),(24,51),(23,46)],
      legs=[[(25,49),(31,51),(27,56),(29,60),(24,61),(19,56),(20,52)],[(30,50),(35,48),(43,53),(43,57),(38,61),(33,59),(36,55),(30,55)]],
      arms=[[(29,44),(24,50),(29,57)],[(38,44),(44,49),(47,57)]], feet=[(24,60,1),(36,60,1)]),
 dict(head=(45,44,-38), body=[(24,39),(31,39),(40,43),(43,49),(38,54),(30,51),(23,46)],
      legs=[[(24,43),(29,46),(23,52),(27,57),(24,60),(18,55),(17,50)],[(28,45),(33,47),(35,52),(32,59),(27,59),(29,53),(25,50)]],
      arms=[[(36,46),(39,54),(40,61)],[(40,48),(47,54),(48,61)]],feet=[(24,57,1),(29,59,1)]),
 dict(head=(46,49,-70), body=[(20,43),(25,39),(31,40),(36,47),(42,51),(44,57),(39,61),(31,62),(24,58),(20,52)],
      legs=[[(25,42),(25,36),(31,32),(37,34),(40,40),(36,44),(32,38),(30,39)],[(25,44),(31,39),(36,38),(43,43),(43,47),(38,49),(35,45),(30,47)]],
      arms=[[(37,51),(39,43),(33,40)],[(40,53),(43,47),(38,43)]],feet=[(37,40,-1),(40,46,-1)]),
 dict(head=(40,51,-125),body=[(20,43),(24,38),(29,38),(32,45),(38,51),(40,57),(35,62),(27,62),(21,58),(18,50)],
      legs=[[(25,42),(25,35),(29,30),(34,31),(36,35),(33,40),(31,37),(30,43)],[(28,44),(34,37),(39,35),(44,39),(46,45),(42,48),(38,42),(34,47)]],
      arms=[[(33,51),(37,44),(35,38)],[(36,54),(43,49),(43,42)]],feet=[(33,33,-1),(43,43,-1)]),
 dict(head=(26,48,-205),body=[(23,40),(28,37),(35,39),(40,44),(44,51),(43,58),(38,62),(31,61),(25,55),(21,47)],
      legs=[[(34,40),(40,39),(45,43),(46,49),(41,53),(36,51),(40,47),(36,45)],[(32,43),(38,43),(41,49),(37,55),(31,55),(28,51),(34,50),(35,48)]],
      arms=[[(28,44),(32,38),(38,41)],[(27,48),(32,54),(37,51)]],feet=[(38,51,-1),(30,53,-1)]),
 dict(head=(25,42,-285),body=[(29,36),(35,36),(41,40),(45,47),(42,53),(35,56),(28,54),(23,49),(23,43)],
      legs=[[(36,47),(42,47),(46,53),(44,59),(39,60),(40,55),(36,53)],[(32,49),(37,50),(35,56),(31,59),(26,59),(27,55),(30,54)]],
      arms=[[(28,46),(25,53),(24,59)],[(30,44),(36,48),(39,53)]],feet=[(40,60,1),(28,59,1)]),
 dict(head=(31,38,-330),body=[(28,42),(34,40),(40,44),(42,50),(37,55),(29,54),(25,49)],
      legs=[[(28,50),(32,53),(26,57),(27,61),(22,61),(20,56),(24,53)],[(35,51),(41,50),(46,55),(43,61),(38,61),(40,56),(35,56)]],
      arms=[[(28,44),(22,51),(22,59)],[(36,45),(43,51),(47,58)]],feet=[(24,61,1),(40,61,1)]),
 dict(head=(38,36,-15),body=[(28,41),(35,40),(40,44),(39,49),(34,53),(27,53),(24,48)],
      legs=[[(27,49),(32,52),(28,57),(30,61),(24,61),(21,56),(23,52)],[(33,50),(39,49),(43,54),(40,61),(35,61),(36,56),(31,55)]],
      arms=[[(28,44),(24,51),(27,58)],[(37,45),(43,51),(44,59)]],feet=[(25,61,1),(37,61,1)]),
 dict(head=(35,30,-5),body=[(27,37),(34,36),(40,40),(39,47),(35,51),(27,51),(24,45)],
      legs=[[(27,48),(32,50),(27,55),(27,61),(22,61),(21,55),(23,51)],[(33,48),(38,48),(43,53),(42,61),(37,61),(37,55),(32,54)]],
      arms=[[(28,39),(23,45),(26,51)],[(38,40),(43,46),(42,52)]],feet=[(23,61,1),(39,61,1)]),
 dict(head=(34,24,0),body=[(27,31),(34,30),(40,34),(39,44),(35,48),(27,48),(24,41)],
      legs=[[(27,45),(32,47),(27,53),(26,61),(21,61),(21,54),(23,49)],[(33,45),(38,46),(42,52),(43,61),(38,61),(37,54),(32,51)]],
      arms=[[(27,34),(23,40),(28,44)],[(38,34),(43,40),(40,46)]],feet=[(22,61,1),(40,61,1)]),
]

def rgba(c):return (*c,255)

def contour(im, points, base, shadow, highlight=None):
    d=ImageDraw.Draw(im)
    d.polygon(points,fill=rgba(base))
    # Color clusters at folds, not a black stroke surrounding every part.
    d.line(points[-3:]+[points[0]],fill=rgba(shadow),width=1)
    if highlight and len(points)>4:d.line(points[1:3],fill=rgba(highlight),width=1)

def arm(im, points, c, near=True):
    _,jacket,dark,light,_,_,skin,skin_dark,_,_=c
    a,b,w=points
    # The sleeve is short on the T-shirt characters, long on the robed ones.
    d=ImageDraw.Draw(im)
    d.line(points,fill=rgba(skin if short_sleeve else jacket),width=4)
    d.rectangle((b[0]-2,b[1]-2,b[0]+1,b[1]+1),fill=rgba(skin if short_sleeve else jacket))
    if short_sleeve:
        end=(round(a[0]+(b[0]-a[0])*.35),round(a[1]+(b[1]-a[1])*.35))
        d.line([a,end],fill=rgba(jacket),width=5)
    else:
        d.line([a,b],fill=rgba(jacket),width=5)
    d.line([(b[0],b[1]+2),(w[0],w[1]+1)],fill=rgba(skin_dark if short_sleeve else dark),width=1)
    d.line([(a[0],a[1]-1),(b[0],b[1]-1)],fill=rgba(light if not short_sleeve else skin),width=1)
    if c == DESIGNS['baroness']:
        # Her pale-blue lower sleeves fold with the elbows; the upper sleeves
        # stay red. Leave the small skin hand visible at the wrist.
        d.line([b,w],fill=(185,213,213,255),width=4)
        d.line([(b[0],b[1]+2),(w[0],w[1]+1)],fill=(136,172,175,255),width=1)
    # Closed hands, except the planted supporting hands (horizontal palm).
    d.polygon([(w[0]-2,w[1]-1),(w[0],w[1]-2),(w[0]+2,w[1]-1),(w[0]+2,w[1]+1),(w[0]-1,w[1]+1)],fill=rgba(skin))
    d.line([(w[0]-1,w[1]+1),(w[0]+2,w[1]+1)],fill=rgba(skin_dark))

def foot(im, where, c, inverted=False, k=0):
    x,y,facing=where
    shoe=FOOT_SPRITES[k]
    if inverted:
        shoe=shoe.rotate(90,resample=Image.Resampling.NEAREST,expand=True)
        im.alpha_composite(shoe,(round(x-shoe.width/2),round(y-shoe.height/2)))
    else:
        im.alpha_composite(shoe,(x-4,y+2-shoe.height))


def place_head(im, source, rect, pose):
    x,y,angle=pose
    head=source.crop(rect)
    if angle:head=head.rotate(angle,resample=Image.Resampling.NEAREST,expand=True)
    im.alpha_composite(head,(round(x-head.width/2),round(y-head.height/2)))

# One continuous skirt silhouette per pose. The fabric bridges the knees,
# rather than tracing two independently folded trouser legs.
BARONESS_GOWNS = [
    [(24,48),(34,47),(44,52),(44,57),(39,60),(28,61),(20,58),(18,54)],
    [(24,41),(33,44),(37,50),(34,58),(28,60),(22,59),(17,54),(17,49)],
    [(23,44),(24,36),(30,31),(37,33),(43,40),(45,46),(39,50),(31,48)],
    [(23,44),(24,35),(29,29),(35,30),(42,34),(46,40),(47,46),(41,49),(33,47)],
    [(31,39),(40,38),(46,42),(47,49),(42,54),(32,57),(27,52),(29,46)],
    [(30,46),(41,46),(47,52),(45,59),(39,61),(28,60),(25,56)],
    [(27,49),(40,49),(47,54),(44,60),(38,62),(24,62),(19,57),(22,53)],
    [(26,48),(38,48),(44,53),(42,60),(36,62),(25,62),(20,57),(22,52)],
    [(26,47),(38,47),(44,52),(43,60),(36,62),(23,62),(20,56),(22,51)],
    [(26,44),(38,45),(42,51),(44,60),(37,62),(22,62),(20,55),(22,49)],
]


def paint(character, i, source, c):
    global short_sleeve
    p=POSES[i]
    rect,jacket,dark,light,pants,pants_dark,skin,skin_dark,shoe,sole=c
    short_sleeve=character in ('ayz','evilayz','cowboy','junkhead','haymaker','katmata','goblin_king')
    im=Image.new('RGBA',(84,63))
    # Far hand/leg behind the torso, with its palette shade rather than an
    # unrelated dark outline. Near arm overlaps head/torso at a tucked roll.
    arm(im,p['arms'][0],c,False)
    if character == 'baroness':
        gown = BARONESS_GOWNS[i]
        contour(im,gown,pants,pants_dark,light)
        d=ImageDraw.Draw(im)
        # Short cloth creases stop inside the skirt, never forming a crotch split.
        a,b=gown[1],gown[4]
        middle=(round((a[0]+b[0])/2),round((a[1]+b[1])/2))
        d.line([a,middle],fill=rgba(pants_dark),width=1)
        for k in range(2):
            foot(im,p['feet'][k],c,2<=i<=4,k)
    else:
        for k,leg in enumerate(p['legs']):
            contour(im,leg,pants_dark if k==0 else pants,pants_dark,highlight=None)
            d=ImageDraw.Draw(im)
            d.line(leg[1:3],fill=rgba(pants),width=1)
            if k==1:d.point(leg[2],fill=rgba(tuple(min(255,v+12) for v in pants)))
            foot(im,p['feet'][k],c,2<=i<=4,k)
    if character in ('anaran','gray_persona'):
        # Separate folds behind the round back, attached at the shoulders.
        cape=[(x-3,y) for x,y in p['body']]
        contour(im,cape,(14,14,16) if character=='anaran' else (8,8,11),(4,4,6),(34,34,38))
    contour(im,p['body'],jacket,dark,light)
    # Carry the idle drawing's actual fabric pixels into the newly drawn
    # silhouette. This retains embroidered robes, waistcoat panels and shirt
    # wrinkles instead of replacing them with large flat-colored shapes.
    swatches = {
      'anaran':(24,34,40,51), 'ayz':(27,27,42,41),
      'evilayz':(27,29,42,43), 'cowboy':(28,27,39,42),
      'junkhead':(27,27,39,42), 'scribe':(34,27,41,43),
      'gray_persona':(29,29,40,40), 'goblin_king':(28,31,39,44),
      'haymaker':(28,28,41,41), 'katmata':(27,28,41,42),
      'baroness':(28,29,41,44)
    }
    patch=source.crop(swatches[character])
    xs=[q[0] for q in p['body']];ys=[q[1] for q in p['body']]
    x0,x1,y0,y1=min(xs),max(xs),min(ys),max(ys)
    family=[jacket,dark,light]
    if character=='anaran':family.append(pants_dark)
    for yy in range(y0,y1+1):
        for xx in range(x0,x1+1):
            if im.getpixel((xx,yy))!=rgba(jacket):continue
            tx=min(patch.width-1,(xx-x0)*patch.width//max(1,x1-x0+1))
            ty=min(patch.height-1,(yy-y0)*patch.height//max(1,y1-y0+1))
            color=patch.getpixel((tx,ty))
            if color[3] and min(sum((color[j]-q[j])**2 for j in range(3)) for q in family)<1800:
                im.putpixel((xx,yy),color)
    d=ImageDraw.Draw(im)
    # Painted cloth panels and fold clusters. The outer arc is the curved back;
    # the inner crease is the belly folding around the thighs.
    fold_paths = [
      ([(25,44),(27,42),(33,41)],[(29,48),(33,47),(36,47)]),
      ([(24,42),(29,41),(35,43)],[(29,47),(34,49),(37,50)]),
      ([(21,47),(22,43),(25,41)],[(24,51),(27,56),(32,58)]),
      ([(20,46),(22,41),(25,40)],[(23,51),(26,57),(31,59)]),
      ([(26,39),(30,39),(35,41)],[(38,49),(40,54),(37,58)]),
      ([(30,38),(34,38),(38,40)],[(30,51),(35,53),(39,51)]),
      ([(28,44),(32,42),(35,43)],[(28,49),(32,51),(36,51)]),
      ([(27,45),(30,42),(34,42)],[(29,49),(33,50),(36,48)]),
      ([(26,41),(28,38),(33,38)],[(28,46),(33,48),(36,46)]),
      ([(26,37),(28,33),(33,32)],[(28,43),(33,45),(36,43)]),
    ]
    d.line(fold_paths[i][1],fill=rgba(dark),width=2)
    d.line(fold_paths[i][0],fill=rgba(light),width=1)
    if 2 <= i <= 5:
        # The near knee and shin cross the chest in the tuck. They are drawn
        # over the torso rather than disappearing behind a featureless ball.
        contour(im,p['legs'][1],pants,pants_dark)
        d=ImageDraw.Draw(im)
        leg=p['legs'][1]
        d.line(leg[1:3],fill=rgba(tuple(min(255,v+12) for v in pants)),width=2)
        d.line(leg[3:5],fill=rgba(pants_dark),width=1)
        foot(im,p['feet'][1],c,2<=i<=4,1)
    d=ImageDraw.Draw(im)
    if character=='scribe':
        # The white shirt/red tie is a short folded strip on the visible chest.
        a=p['arms'][1][0];b=p['body'][-3]
        d.line([a,b],fill=(240,241,250,255),width=3)
        d.line([(a[0],a[1]+1),b],fill=(175,48,48,255),width=1)
    if character=='goblin_king':
        for x,y in p['body'][:3]:d.rectangle((x-1,y,x+1,y+1),fill=(240,237,229,255))
    if character=='anaran':
        d.line(p['body'][2:4],fill=(187,133,64,255),width=1)
    if character=='baroness':
        # The gold waist trim follows the folded gown, rather than remaining
        # horizontal while her body turns over her shoulder.
        d.line(p['body'][-3:-1],fill=(189,149,33,255),width=2)
        d.line(p['body'][-3:-1],fill=(236,191,58,255),width=1)
    if character=='katmata' and i in (0,1,6,7,8,9):
        x,y=p['body'][1];d.point((x,y+3),fill=(90,170,111,255))
    # A solid neck beneath the head crop closes gaps created by head tilt.
    hx,hy,angle=p['head'];shoulder=p['arms'][1][0]
    d.line([(hx,hy+3),shoulder],fill=rgba(skin_dark),width=5)
    place_head(im,source,rect,p['head'])
    arm(im,p['arms'][1],c)
    # Upper-arm tattoo follows the upper arm, rather than floating in midair.
    if character in ('junkhead','cowboy'):
        a=p['arms'][0][0]
        d=ImageDraw.Draw(im);d.point((a[0]-1,a[1]+2),fill=(196,36,40,255) if character=='junkhead' else (40,45,77,255))
    return im

def baroness_rolls(source):
    """Native hand-plotted poses, also used by her full sprite generator."""
    global FOOT_SPRITES
    FOOT_SPRITES = [source.crop(box) for box in [(20,57,34,63),(39,57,51,63)]]
    return {f'roll_{i}': paint('baroness', i, source, DESIGNS['baroness']) for i in range(10)}

def main():
    global FOOT_SPRITES
    preview=Image.new('RGBA',(84*10*3,63*(len(DESIGNS)+1)*3),(70,78,91,255))
    for row,(character,c) in enumerate(DESIGNS.items()):
        folder=ROOT/'assets/sprites'/character
        source=Image.open(folder/'idle_0.png').convert('RGBA')
        pad=(40,30) if character=='haymaker' else (0,0)
        if character=='haymaker':source=source.crop((40,30,124,93))
        shoes={
          'baroness':[(20,57,34,63),(39,57,51,63)],
          'anaran':[(18,54,27,63),(38,54,47,63)],
          'ayz':[(16,55,29,63),(40,55,53,63)],
          'evilayz':[(16,55,29,63),(40,55,53,63)],
          'cowboy':[(20,49,30,62),(40,49,52,62)],
          'junkhead':[(19,56,30,63),(39,56,51,63)],
          'scribe':[(20,55,30,63),(40,55,51,63)],
          'gray_persona':[(21,54,31,63),(40,54,50,63)],
          'goblin_king':[(17,56,29,63),(40,56,52,63)],
          'haymaker':[(16,55,29,63),(39,55,52,63)],
          'katmata':[(18,56,30,63),(38,56,51,63)]
        }
        FOOT_SPRITES=[source.crop(box) for box in shoes[character]]
        dst=OUT/character;dst.mkdir(exist_ok=True)
        for i in range(10):
            im=paint(character,i,source,c)
            if character=='haymaker':
                padded=Image.new('RGBA',(164,123));padded.alpha_composite(im,pad);im=padded
            im.save(dst/f'roll_{i}.png')
            small=im.crop((pad[0],pad[1],pad[0]+84,pad[1]+63))
            preview.alpha_composite(small.resize((252,189),Image.Resampling.NEAREST),(i*252,row*189))
    # The training dummy is a sack on a rigid wooden stand, not a humanoid.
    # Its separate drawings foreshorten the sack, target and crossbar as the
    # stand tips over; no human knees or hands are grafted onto it.
    dummy=Image.open(ROOT/'assets/sprites/dummy/idle_0.png').convert('RGBA')
    dst=OUT/'dummy';dst.mkdir(exist_ok=True)
    phases=[
      ((33,43),(33,29,0),((33,48),(33,60)),((22,62),(44,62)),((14,41),(52,41))),
      ((33,44),(45,37,-45),((28,47),(20,57)),((12,54),(26,62)),((20,33),(45,55))),
      ((34,47),(47,48,-80),((28,43),(17,36)),((12,28),(21,45)),((28,32),(40,60))),
      ((33,46),(36,54,-150),((30,39),(28,28)),((17,25),(40,28)),((20,48),(47,43))),
      ((33,46),(24,51,-220),((38,41),(48,34)),((42,26),(55,42)),((25,35),(42,56))),
      ((33,46),(23,39,-290),((40,49),(48,59)),((40,62),(58,58)),((27,57),(40,33))),
      ((33,44),(31,31,-345),((33,51),(33,60)),((22,62),(44,62)),((15,43),(51,42))),
      ((33,43),(34,30,-5),((33,50),(33,60)),((22,62),(44,62)),((14,42),(52,40))),
      ((33,39),(33,26,0),((33,47),(33,60)),((22,62),(44,62)),((14,37),(52,37))),
      ((33,35),(33,22,0),((33,43),(33,60)),((22,62),(44,62)),((14,33),(52,33))),
    ]
    for i,(center,head,post,base,crossbar) in enumerate(phases):
        im=Image.new('RGBA',(84,63));d=ImageDraw.Draw(im)
        for points in [post,base,crossbar]:
            d.line(points,fill=(46,30,18,255),width=5)
            d.line(points,fill=(120,78,44,255),width=3)
            d.line([(x-1,y-1) for x,y in points],fill=(156,108,64,255),width=1)
        x,y=center
        d.polygon([(x-7,y-10),(x+7,y-9),(x+10,y-3),(x+8,y+8),(x+3,y+11),(x-6,y+9),(x-10,y+2),(x-9,y-5)],fill=(160,132,84,255))
        d.polygon([(x-6,y-9),(x+4,y-8),(x+7,y-2),(x+5,y+8),(x-4,y+8),(x-8,y+1)],fill=(196,168,112,255))
        d.line([(x-6,y-7),(x-7,y),(x-4,y+7)],fill=(222,198,146,255),width=2)
        # The painted target narrows while the sack turns side-on.
        rx=(6,5,3,5,4,3,5,6,6,6)[i]
        for r,color in [(1,(196,44,44)),(.72,(240,232,214)),(.44,(196,44,44)),(.18,(240,232,214))]:
            d.ellipse((x-round(rx*r),y-round(6*r),x+round(rx*r),y+round(6*r)),fill=rgba(color))
        for end in crossbar:
            ex,ey=end
            d.line([(ex-2,ey-2),(ex+3,ey-2)],fill=(232,200,92,255))
            d.line([(ex-3,ey),(ex+3,ey)],fill=(190,150,50,255))
            d.line([(ex-2,ey+2),(ex+2,ey+2)],fill=(232,200,92,255))
        place_head(im,dummy,(25,7,42,27),head)
        im.save(dst/f'roll_{i}.png')
        preview.alpha_composite(im.resize((252,189),Image.Resampling.NEAREST),(i*252,len(DESIGNS)*189))
    preview.save(OUT/'contact_sheet.png')
    print('Painted ten distinct roll drawings for each of',len(DESIGNS)+1,'characters.')

if __name__=='__main__':main()

