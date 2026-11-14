"""Draws the Goblin King: every pose from tools/goblin_king_art.png, his coins, his goblins, his skill icons and his
portrait.

    python tools/gen_goblin_king_sprites.py [--sheet contact_sheet.png]

The drawing is cut into an upper body (crown, head, fur collar and red robe, without the arms) and the legs. Each pose
shifts, leans and squashes those and puts his own arms back, turned about the shoulder to point at a hand position,
with short dark nails added at the fingertips; a kick or a clinging grip turns his own leg about the hip the same way. His goblins are Anaran's goblins (the same art style) recoloured into his livery: olive
skin, a red tunic with a gold belt and a little red cap, red eyes.
"""

import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
SPRITES = ROOT / "assets/sprites/goblin_king"
ICONS = ROOT / "assets/icons/goblin_king"
PORTRAIT = ROOT / "assets/portraits/goblin_king.png"

W, H = 84, 63
CX = 33                   # body centre
FLOOR = 62                # the row his feet stand on
# the drawing is 33 x 54 with its feet on row 53
OFF_X, OFF_Y = 17, 9

SKIN = (149, 188, 114)
SKIN_LIGHT = (177, 231, 131)
SKIN_SHADE = (124, 157, 94)
BACK_SKIN, BACK_SHADE = (124, 157, 94), (100, 128, 76)
ROBE = (184, 89, 89)
ROBE_DARK = (165, 71, 71)
ROBE_LIGHT = (200, 127, 127)
FUR = (240, 237, 229)
PANTS = (138, 113, 170)
PANTS_DARK = (114, 95, 139)
PANTS_LIGHT = (161, 134, 195)
CLAW = (240, 237, 229)
OUTLINE = (40, 30, 52)
MOUTH = (90, 22, 26)
TOOTH = (255, 253, 248)
GOLD = (241, 214, 65)
GOLD_DARK = (198, 157, 46)
GOLD_LIGHT = (255, 245, 170)
SCRATCH = [(150, 40, 40), (220, 90, 80), (255, 220, 210)]

here = Path(__file__).resolve().parent
SRC = Image.open(here / "goblin_king_art.png").convert("RGBA")

HIP = 33
# where the arms and legs join, in the drawing
BACK_SHOULDER = (8, 21)
FRONT_SHOULDER = (25, 21)
# a kick swings the leg from the knee (the trousers above it stay as drawn)
KNEE = 9
BACK_HIP = (7, HIP + KNEE)
FRONT_HIP = (21, HIP + KNEE)
# short dark nails, like Gray Persona's
NAIL = (90, 30, 34)


def blank():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def put(img, x, y, c):
    x, y = round(x), round(y)
    if 0 <= x < img.width and 0 <= y < img.height:
        img.putpixel((x, y), tuple(c) + (255,) if len(c) == 3 else tuple(c))


def is_skin(c):
    r, g, b = c[:3]
    return g > r + 15 and g > b + 15


def split():
    """The upper body without its arms (rows above the hips), the legs, and each arm and leg on its own (on a picture
    the drawing's size, where it was)."""
    upper = Image.new("RGBA", (SRC.width, HIP), (0, 0, 0, 0))
    legs = Image.new("RGBA", (SRC.width, SRC.height - HIP), (0, 0, 0, 0))
    back_arm, front_arm = Image.new("RGBA", SRC.size), Image.new("RGBA", SRC.size)
    back_leg, front_leg = Image.new("RGBA", SRC.size), Image.new("RGBA", SRC.size)
    for y in range(SRC.height):
        for x in range(SRC.width):
            c = SRC.getpixel((x, y))
            if c[3] == 0:
                continue
            if y < HIP or (x >= 24 and y <= 36 and is_skin(c)):
                if x <= 11 and 20 <= y <= 29 and is_skin(c):
                    back_arm.putpixel((x, y), c)
                elif x >= 22 and 20 <= y and is_skin(c):
                    front_arm.putpixel((x, y), c)
                else:
                    upper.putpixel((x, y), c)
            else:
                legs.putpixel((x, y - HIP), c)
                sy = y - HIP
                if sy >= KNEE:
                    front = x >= 15
                    (front_leg if front else back_leg).putpixel((x, y), c)
    # short dark nails on the fingertips: the pixels of each hand furthest from its shoulder
    for img, (sx, sy) in ((back_arm, BACK_SHOULDER), (front_arm, FRONT_SHOULDER)):
        pts = [(x, y) for y in range(img.height) for x in range(img.width) if img.getpixel((x, y))[3]]
        pts.sort(key=lambda q: -((q[0] - sx) ** 2 + (q[1] - sy) ** 2))
        for q in pts[:3]:
            img.putpixel(q, NAIL + (255,))
    return upper, legs, back_arm, front_arm, back_leg, front_leg


def reach(img, pivot):
    """The direction from `pivot` to the furthest pixel of a limb (where its hand or foot is)."""
    pts = [(x, y) for y in range(img.height) for x in range(img.width) if img.getpixel((x, y))[3]]
    far = max(pts, key=lambda q: (q[0] - pivot[0]) ** 2 + (q[1] - pivot[1]) ** 2)
    return (far[0] - pivot[0], far[1] - pivot[1])


def turned(img, limb, pivot, direction, at, stretch=1.0):
    """Draw `limb` (a picture the drawing's size) turned about its `pivot` so it points along `direction`, with the
    pivot at `at` on `img`; `stretch` draws it that much longer (thrown out in a strike)."""
    if stretch != 1.0:
        w, h = limb.size
        big = limb.resize((round(w * stretch), round(h * stretch)), Image.NEAREST)
        limb = big
        pivot = (round(pivot[0] * stretch), round(pivot[1] * stretch))
    d0 = reach(limb, pivot)
    angle = math.degrees(math.atan2(direction[1], direction[0]) - math.atan2(d0[1], d0[0]))
    pad = 40
    big = Image.new("RGBA", (limb.width + 2 * pad, limb.height + 2 * pad))
    big.paste(limb, (pad, pad))
    rot = big.rotate(-angle, resample=Image.NEAREST, center=(pivot[0] + pad, pivot[1] + pad))
    img.paste(rot, (round(at[0]) - pivot[0] - pad, round(at[1]) - pivot[1] - pad), rot)


UPPER, LEGS, BACK_ARM, FRONT_ARM, BACK_LEG, FRONT_LEG = split()


def line(img, a, b, colour, width=1):
    (x0, y0), (x1, y1) = a, b
    steps = int(math.ceil(max(abs(x1 - x0), abs(y1 - y0), 1)))
    for k in range(steps + 1):
        t = k / steps
        x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
        for ox in range(-(width // 2), width - width // 2):
            for oy in range(-(width // 2), width - width // 2):
                put(img, x + ox, y + oy, colour)


def two_bone(shoulder, hand, upper, fore, bend):
    (sx, sy), (hx, hy) = shoulder, hand
    dx, dy = hx - sx, hy - sy
    dist = max(math.hypot(dx, dy), 0.001)
    ux, uy = dx / dist, dy / dist
    if dist >= upper + fore - 0.01:
        reach = upper + fore - 0.01
        return (sx + ux * upper, sy + uy * upper), (sx + ux * reach, sy + uy * reach)
    a = (upper * upper - fore * fore + dist * dist) / (2 * dist)
    h = math.sqrt(max(upper * upper - a * a, 0))
    return (sx + ux * a - uy * h * bend, sy + uy * a + ux * h * bend), (hx, hy)


def arm(img, shoulder, target, bend=1, back=False, stretch=1.0):
    """One of his own arms, turned at the shoulder to point at `target` (the back one darker, being further away)."""
    limb = BACK_ARM if back else FRONT_ARM
    pivot = BACK_SHOULDER if back else FRONT_SHOULDER
    if back:
        limb = Image.eval(limb, lambda v: v)
        px = limb.load()
        for y in range(limb.height):
            for x in range(limb.width):
                r, g, b, a = px[x, y]
                if a and (r, g, b) != NAIL:
                    px[x, y] = (r * 85 // 100, g * 85 // 100, b * 85 // 100, a)
    turned(img, limb, pivot, (target[0] - shoulder[0], target[1] - shoulder[1]), shoulder, stretch)


def leg(img, hip, foot, bend=-1, back=False, stretch=1.0):
    """One of his own legs, turned at the hip to point at `foot` (a kick, a grip)."""
    limb = BACK_LEG if back else FRONT_LEG
    pivot = BACK_HIP if back else FRONT_HIP
    turned(img, limb, pivot, (foot[0] - hip[0], foot[1] - hip[1]), hip, stretch)


class Pose:
    def __init__(self, dx=0, drop=0, lean=0, squash=0, legs=(0, 0, 0, 0), bend=(0, 0), spread=0, tuck=0, hide=None):
        """`dx`: body moved forward; `drop`: upper body lowered (the legs squashed to match by `squash`); `lean`: the
        head moved this far forward at the top, sheared down to the hips; `legs`: (back leg dx, back foot lift, front
        leg dx, front foot lift); `bend`: each shin swung back (+) or forward (-); `spread`: knees apart; `tuck`: feet
        pulled up under him; `hide`: "back", "front" or "both" legs left out (drawn out by `leg` instead)."""
        # (a lean is kept small: the body stays close to the drawing's posture)
        self.dx, self.drop, self.lean, self.squash = dx, drop, round(lean * 0.3), squash
        self.legs, self.bend, self.spread, self.tuck, self.hide = legs, bend, spread, tuck, hide

    def shoulder(self, which):
        sx, sy = BACK_SHOULDER if which == "back" else FRONT_SHOULDER
        return (sx + OFF_X + self.dx + round(self.lean * (HIP - sy) / HIP), sy + OFF_Y + self.drop)

    def hip(self, which):
        hx, hy = BACK_HIP if which == "back" else FRONT_HIP
        # (the rows a crouch or a tuck takes out of the thighs move the knee up)
        cut = {4 + (k * 7) % 12 for k in range(min(self.squash + self.tuck, 12))}
        above = sum(1 for r in cut if r < KNEE)
        return (hx + OFF_X + self.dx, hy + OFF_Y + self.drop - self.tuck - above)


def draw_legs(img, p):
    keep = list(range(LEGS.height))
    for k in range(min(p.squash + p.tuck, 12)):
        row = 4 + (k * 7) % 12
        if row in keep and len(keep) > 9:
            keep.remove(row)
    back_dx, back_lift, front_dx, front_lift = p.legs
    rows = LEGS.height
    for ny, sy in enumerate(keep):
        for x in range(LEGS.width):
            c = LEGS.getpixel((x, sy))
            if c[3] == 0:
                continue
            front = x >= 15 if sy >= 7 else x >= 13
            if sy >= KNEE and (p.hide == "both" or (p.hide == "front" and front) or (p.hide == "back" and not front)):
                continue
            low = max(0.0, (sy - 8) / (rows - 8))
            spread = round(p.spread * min(1.0, sy / 10)) * (1 if front else -1)
            bend = (p.bend[1] if front else -p.bend[0]) * low
            tuck_back = -p.tuck * 0.6 * low * (1 if front else 0.5)
            dx = (front_dx if front else back_dx) + spread + bend + tuck_back
            lift = (front_lift if front else back_lift) * min(1.0, sy / (rows - 1))
            y = OFF_Y + HIP + p.drop + ny - round(lift) - p.tuck
            put(img, OFF_X + x + p.dx + round(dx), y, c)


def draw_upper(img, p):
    for y in range(UPPER.height):
        shift = round(p.lean * (HIP - y) / HIP)
        for x in range(UPPER.width):
            c = UPPER.getpixel((x, y))
            if c[3]:
                put(img, OFF_X + x + p.dx + shift, OFF_Y + y + p.drop, c)


def head_at(p, x, y):
    """Where a pixel of the drawing's head (x, y) lands in pose `p`."""
    return (OFF_X + x + p.dx + round(p.lean * (HIP - y) / HIP), OFF_Y + y + p.drop)


def mouth(img, p, wide=2):
    """His mouth opened (talking, biting): dark inside, teeth top and bottom."""
    for y in range(12, 13 + wide):
        for x in range(14, 20):
            put(img, *head_at(p, x, y), MOUTH)
    for x in range(14, 20, 2):
        put(img, *head_at(p, x, 12), TOOTH)
        put(img, *head_at(p, x + 1, 12 + wide), TOOTH)


def pose(p, back_hand, front_hand, back_bend=1, front_bend=-1, back_leg=None, front_leg=None, before=None, after=None, back_over=False, reach_=1.0):
    """Draw a pose: each hand at a point relative to its shoulder; `back_leg`/`front_leg` (foot relative to the hip,
    knee bend) draw that leg out instead of the drawing's. `back_over` draws the back arm over the body (swung across)."""
    img = blank()
    if before:
        before(img, p)
    bs, fs = p.shoulder("back"), p.shoulder("front")
    if not back_over:
        arm(img, bs, (bs[0] + back_hand[0], bs[1] + back_hand[1]), back_bend, back=True)
    # (a back leg kicked forward swings out in front of him)
    kicked = back_leg and back_leg[0][0] > 0
    if back_leg and not kicked:
        bh = p.hip("back")
        leg(img, bh, (bh[0] + back_leg[0][0], bh[1] + back_leg[0][1]), back_leg[1], back=True, stretch=reach_)
    draw_legs(img, p)
    draw_upper(img, p)
    if kicked:
        bh = p.hip("back")
        leg(img, bh, (bh[0] + back_leg[0][0], bh[1] + back_leg[0][1]), back_leg[1], back=True, stretch=reach_)
    if front_leg:
        fh = p.hip("front")
        leg(img, fh, (fh[0] + front_leg[0][0], fh[1] + front_leg[0][1]), front_leg[1], stretch=reach_)
    if back_over:
        arm(img, bs, (bs[0] + back_hand[0], bs[1] + back_hand[1]), back_bend, stretch=reach_)
    arm(img, fs, (fs[0] + front_hand[0], fs[1] + front_hand[1]), front_bend, stretch=reach_)
    if after:
        after(img, p)
    return img


def coin(img, cx, cy, edge=False):
    """A gold coin, 5 wide (3 seen edge on)."""
    rows = [".XXX.", "XXGXX", "XGGGX", "XXGXX", ".XXX."] if not edge else [".X.", "XGX", "XGX", "XGX", ".X."]
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            if ch != ".":
                put(img, cx - len(row) // 2 + c, cy - 2 + r, GOLD_DARK if ch == "X" else GOLD)
    put(img, cx - (0 if edge else 1), cy - 1, GOLD_LIGHT)


def tilt(img, degrees, pivot):
    return img.rotate(degrees, resample=Image.NEAREST, center=pivot)


def frames():
    out = {}
    # idle: hunched, claws ready, a breath
    for i in range(2):
        p = Pose(drop=1 + i, squash=1, spread=1, lean=2)
        out[f"idle_{i}"] = pose(p, (-8, 7 - i), (6, 12 - i))
    # walk: a trot, leaning in, long strides with the feet kicked high and a bounce, arms pumping against the legs
    for i in range(6):
        ph = i / 6 * 2 * math.pi
        s = math.sin(ph) * 6
        lift = lambda c: max(0, round(c * 6))
        p = Pose(drop=(0, 2, 1, 0, 2, 1)[i], lean=6, legs=(round(-s), lift(math.cos(ph)), round(s), lift(-math.cos(ph))),
                 bend=(max(0, round(math.cos(ph) * 3)), max(0, round(-math.cos(ph) * 3))))
        out[f"walk_{i}"] = pose(p, (-8 + round(s), 6), (7 - round(s), 9))
    cp = Pose(drop=9, squash=9, spread=3, lean=3)
    out["crouch"] = pose(cp, (-7, 8), (8, 11))
    # crouching light: a low swipe along the floor
    out["crouch_soft_0"] = pose(cp, (2, 12), (-4, 10))
    out["crouch_soft_1"] = pose(Pose(drop=9, squash=9, spread=4, lean=5, dx=1), (2, 12), (17, 15))
    out["crouch_hard_0"] = out["crouch"]
    out["crouch_hard_1"] = out["crouch_soft_1"]
    # jumping: knees up as he rises, tucked at the top, claws out as he falls
    for name, tuck, lean, hands in (("jump_up", 5, 2, ((-9, 4), (8, 8))), ("jump_top", 9, 3, ((-9, 3), (9, 6))), ("jump_fall", 2, 1, ((-8, 6), (7, 10)))):
        out[name] = pose(Pose(tuck=tuck, spread=2, lean=lean), *hands)
    ap = Pose(tuck=8, spread=2, lean=4)
    # air light: claws raised, then raked down in front
    out["air_soft_0"] = pose(Pose(tuck=8, spread=2, lean=-2), (-9, 3), (9, 1))
    out["air_soft_1"] = pose(ap, (-8, 6), (14, 9))
    out["air_hard_0"] = out["air_soft_0"]
    out["air_hard_1"] = out["air_soft_1"]
    # hurt: thrown back
    for i in range(2):
        p = Pose(dx=-1 - i, lean=-4 - i * 3, legs=(-1, 0, 2, 2), bend=(0, -2))
        out[f"hurt_{i}"] = pose(p, (-10, 2 - i * 6), (3, 12 - i * 4))
    # block: forearms crossed in front of his face
    bp = Pose(drop=3, squash=3, lean=-1, spread=2)
    out["block"] = pose(bp, (12, -4), (4, -6), back_bend=-1, front_bend=1)
    # knocked out: flat on his back
    ko = pose(Pose(), (-4, 13), (4, 13))
    ko = tilt(ko, 90, pivot=(CX, FLOOR - 9))
    piece = ko.crop(ko.getbbox())
    ko2 = blank()
    ko2.alpha_composite(piece, (CX - piece.width // 2, FLOOR + 1 - piece.height))
    out["ko"] = ko2

    # the flailing light: for each limb a wind-up and a strike
    # 0: back hand clawing over the top
    out["flail_0"] = pose(Pose(dx=-3, lean=-7, spread=3, legs=(-2, 0, 3, 0)), (-6, -10), (-2, 10))
    out["flail_1"] = pose(Pose(dx=8, lean=11, drop=2, squash=2, spread=4, legs=(-5, 0, 7, 0), bend=(3, -1)), (17, 4), (-6, 8),
                          back_bend=-1, back_over=True, reach_=1.25)
    # 1: front hand slapping across
    out["flail_2"] = pose(Pose(dx=-3, lean=-6, spread=3), (-4, 10), (-8, -6), front_bend=1)
    out["flail_3"] = pose(Pose(dx=8, lean=10, drop=2, squash=2, spread=4, legs=(-5, 0, 7, 0), bend=(3, -1)), (-8, 8), (20, 4),
                          reach_=1.3)
    # 2: a hop and a flying kick, high, all of him thrown into it
    out["flail_4"] = pose(Pose(dx=-2, lean=-5, tuck=4, spread=1, hide="front"), (-8, 2), (6, 4), front_leg=((4, 0), -1))
    out["flail_5"] = pose(Pose(dx=8, lean=-9, tuck=7, hide="front"), (-10, -4), (2, 0), front_leg=((26, -10), -1), reach_=1.35)
    # 3: knee up, then a low kick straight out
    out["flail_6"] = pose(Pose(dx=-2, lean=-4, spread=1, hide="front"), (-6, 6), (4, 6), front_leg=((8, 2), -1))
    out["flail_7"] = pose(Pose(dx=7, lean=-8, hide="front"), (-10, 2), (-4, 6), front_leg=((26, 0), -1), reach_=1.35)
    out["soft_0"], out["soft_1"] = out["flail_2"], out["flail_3"]

    # the bite (light finisher): crouched, leaping jaws first, the chomp
    out["kick_0"] = pose(Pose(dx=-3, drop=10, squash=10, spread=4, lean=6), (-4, 12), (4, 12))
    # flying at them flat out, jaws wide, arms reaching, legs trailing
    fly = Pose(dx=8, lean=12, hide="both")
    trail = dict(back_leg=((-18, -2), 1), front_leg=((-16, 2), 1))
    out["kick_1"] = pose(fly, (16, -2), (20, 2), reach_=1.2, after=lambda im, p: mouth(im, p, 3), **trail)
    chomp = Pose(dx=12, lean=11, hide="both")
    out["kick_2"] = pose(chomp, (18, 6), (22, 8), reach_=1.2, after=lambda im, p: mouth(im, p, 3), **trail)
    out["kick_3"] = pose(Pose(dx=10, lean=9, drop=2, hide="both"), (16, 8), (20, 10), reach_=1.15, after=lambda im, p: mouth(im, p, 1), **trail)

    # the pounce: crouched and charging (shaking), leaping claws first, clinging and clawing (two), dropping off
    for i in range(2):
        p = Pose(drop=12, squash=12, spread=4, lean=5, dx=i)
        out[f"pounce_{i}"] = pose(p, (4, 14), (10, 13))
    lp = Pose(lean=13, dx=9, hide="both")
    out["pounce_2"] = pose(lp, (18, -6), (22, -2), back_leg=((-20, -2), 1), front_leg=((-16, 2), 1), reach_=1.25)
    cling = Pose(lean=5, dx=2, hide="both")
    grip = (((8, 13), 1), ((12, 11), 1))
    out["pounce_3"] = pose(cling, (14, -8), (18, 10), back_leg=grip[0], front_leg=grip[1])
    out["pounce_4"] = pose(cling, (18, 8), (12, -10), back_leg=grip[0], front_leg=grip[1])
    out["pounce_5"] = pose(Pose(drop=7, squash=7, spread=3, lean=2), (2, 12), (8, 12))
    for i, src in enumerate(["pounce_0", "pounce_1", "pounce_2", "pounce_5"]):
        out[f"hard_{i}"] = out[src]

    # throwing gold (the special): reaching into his robe, a fistful of coins up behind, the throw, the follow-through
    out["summon_0"] = pose(Pose(lean=1), (-2, 12), (-6, 9))
    out["summon_1"] = pose(Pose(lean=-1), (-2, 12), (-8, 8), after=lambda im, p: coin(im, p.shoulder("front")[0] - 7, p.shoulder("front")[1] + 6))
    out["summon_2"] = pose(Pose(lean=-4, spread=2), (-6, 8), (-10, -8), front_bend=1,
                           after=lambda im, p: (coin(im, p.shoulder("front")[0] - 11, p.shoulder("front")[1] - 11), coin(im, p.shoulder("front")[0] - 7, p.shoulder("front")[1] - 12, True)))
    out["summon_3"] = out["summon_2"]

    def flung(im, p):
        fs = p.shoulder("front")
        # a fistful flung out: a bunch of coins in the air
        for k, (dx, dy) in enumerate(((18, -14), (22, -17), (26, -12), (20, -20), (29, -18), (24, -22), (31, -13))):
            coin(im, fs[0] + dx, fs[1] + dy, k % 3 == 1)
    out["summon_4"] = pose(Pose(dx=2, lean=6, spread=3, legs=(-3, 0, 4, 0)), (-6, 10), (16, -10), after=flung)
    out["summon_5"] = pose(Pose(dx=1, lean=3, spread=2), (-4, 12), (12, 4))

    # speaking: a pointing claw, his mouth open on the second
    for i in range(2):
        p = Pose(lean=i, spread=1)
        out[f"speak_{i}"] = pose(p, (-8, 7), (9, 8 - 2 * i), after=(lambda im, p: mouth(im, p, 1)) if i else None)

    # the roll: a tight ball turned in eighths, then rising
    out["roll_0"] = pose(Pose(drop=9, squash=9, lean=4, spread=2), (4, 10), (8, 10))
    ball = pose(Pose(drop=14, squash=14, lean=5, tuck=4), (8, 8), (10, 8))
    bb = ball.getbbox()
    centre = ((bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2)
    for k in range(1, 9):
        r = tilt(ball, -45 * k, centre)
        rb = r.getbbox()
        moved = blank()
        moved.alpha_composite(r, (0, FLOOR - rb[3] + 1))
        out[f"roll_{k}"] = moved
    out["roll_9"] = out["crouch"]
    return out


def coin_drawings():
    """A pile of coins (thrown in a bunch, lying in a heap): two drawings, the glint moving from one coin to another."""
    out = []
    spots = [(3, 8, False), (8, 8, False), (13, 8, True), (5, 5, False), (10, 5, False), (8, 2, True)]
    for frame in range(2):
        img = Image.new("RGBA", (17, 11), (0, 0, 0, 0))
        for k, (x, y, edge) in enumerate(spots):
            coin(img, x, y, edge)
        gx, gy, _ = spots[3 + frame]
        put(img, gx, gy - 1, (255, 255, 255))
        out.append(img)
    return out


def goblins():
    """Anaran's goblins in the Goblin King's livery: olive skin, a red tunic with a gold belt, red eyes, a little red cap."""
    out = []
    for i in range(8):
        g = Image.open(ROOT / f"assets/sprites/anaran/goblin_{i}.png").convert("RGBA")
        px = g.load()
        top = None
        for y in range(g.height):
            for x in range(g.width):
                r, gg, b, a = px[x, y]
                if a == 0:
                    continue
                if top is None:
                    top = y
                if gg > r + 15 and gg > b + 10:
                    # green skin: olive, a little more yellow and darker
                    px[x, y] = (min(255, int(r * 1.05 + 18)), int(gg * 0.88), int(b * 0.7), a)
                elif r > gg + 25 and gg > b and r < 200:
                    # brown tunic: royal red
                    lum = (r + gg + b) / 3
                    px[x, y] = (min(255, int(lum * 2.0 + 30)), int(lum * 0.55), int(lum * 0.55), a)
                elif r > 200 and gg > 170 and b < 100:
                    # yellow eyes and the belt buckle: red eyes stay small, so only the eyes (high up) change
                    px[x, y] = (230, 50, 40, a) if y < 12 else (GOLD + (a,))
        # a little red cap on the top of the head
        cols = [x for x in range(g.width) if any(px[x, y][3] for y in range(top, top + 3))] if top is not None else []
        if cols:
            mid = (min(cols) + max(cols)) // 2
            for k, w in enumerate((1, 3, 5)):
                for dx in range(-(w // 2), w // 2 + 1):
                    y = top - 3 + k
                    if 0 <= y < g.height:
                        px[mid + dx, y] = (ROBE_DARK if k == 2 else ROBE) + (255,)
            if top - 4 >= 0:
                px[mid, top - 4] = GOLD + (255,)
        out.append(g)
    return out


def outlined(layer, colour=(10, 6, 8)):
    out = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    w, h = layer.size
    for y in range(h):
        for x in range(w):
            if layer.getpixel((x, y))[3]:
                continue
            if any(0 <= x + dx < w and 0 <= y + dy < h and layer.getpixel((x + dx, y + dy))[3] for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                out.putpixel((x, y), colour + (255,))
    out.alpha_composite(layer)
    return out


def icon_base(light, dark):
    img = Image.new("RGBA", (24, 24))
    for y in range(24):
        for x in range(24):
            t = round((x + y) / 46 * 4) / 4
            img.putpixel((x, y), tuple(round(light[k] + (dark[k] - light[k]) * t) for k in range(3)) + (255,))
    rim = tuple(min(255, c + 70) for c in light)
    for k in range(24):
        for (x, y) in ((k, 0), (0, k), (k, 23), (23, k)):
            put(img, x, y, (12, 6, 10))
    for k in range(1, 23):
        put(img, k, 1, rim)
        put(img, 1, k, rim)
        put(img, k, 22, tuple(c // 2 for c in dark))
        put(img, 22, k, tuple(c // 2 for c in dark))
    return img


def icon(kind):
    layer = Image.new("RGBA", (24, 24), (0, 0, 0, 0))
    if kind == "light":
        img = icon_base((120, 170, 80), (30, 60, 24))
        # a clawed hand raking down, three scratches, a coin knocked loose
        for k in (-3, 0, 3):
            line(layer, (9 + k, 4), (15 + k, 16), SCRATCH[1])
            put(layer, 15 + k, 16, SCRATCH[2])
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                put(layer, 7 + dx, 5 + dy, SKIN)
        coin(layer, 18, 19)
    elif kind == "heavy":
        img = icon_base((150, 120, 190), (40, 26, 60))
        # the pounce: a goblin silhouette flying in with both claws out, speed lines behind
        for y, x0 in ((9, 2), (13, 1), (17, 3)):
            line(layer, (x0, y), (x0 + 6, y), (255, 220, 120))
        line(layer, (9, 14), (17, 10), SKIN, 5)
        for dy in (-2, -1, 0, 1, 2):
            put(layer, 18, 9 + dy, SKIN)
        put(layer, 19, 8, (230, 40, 40))
        put(layer, 20, 12, NAIL)
        put(layer, 19, 6, NAIL)
        line(layer, (9, 15), (5, 19), PANTS, 3)
    else:
        img = icon_base((200, 150, 40), (70, 40, 10))
        # coins showered in arcs, a goblin's capped head popping up from one
        for k, (x, y, e) in enumerate(((6, 6, False), (12, 4, True), (18, 7, False), (16, 13, True))):
            coin(layer, x, y, e)
        g = goblins()[0].crop((8, 0, 24, 14)).resize((12, 10), Image.NEAREST)
        layer.alpha_composite(g, (3, 12))
    img.alpha_composite(outlined(layer))
    return img


def portrait():
    """His face from the photo (tools/goblin_king_photo.png), cropped square and shrunk to 40 x 40: the skin turned goblin
    green and a long pointed goblin ear drawn over his own."""
    import colorsys
    photo = Image.open(here / "goblin_king_photo.png").convert("RGB")
    face = photo.crop((425, 425, 2550, 2550)).resize((40, 40), Image.LANCZOS)
    px = face.load()
    for y in range(40):
        for x in range(40):
            r, g, b = px[x, y]
            h, l, sat = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
            # skin (warm, light, not grey): green, keeping its light and shade
            if 0.0 <= h <= 0.11 and 0.3 < l < 0.92 and sat > 0.18 and r > b + 20:
                nr, ng, nb = colorsys.hls_to_rgb(0.25, l * 0.78, min(0.55, sat * 0.6 + 0.12))
                px[x, y] = (round(nr * 255), round(ng * 255), round(nb * 255))
    # the goblin ear over his own (left side of the picture), pointing up and out, blurred like the rest of the photo
    from PIL import ImageFilter
    ear = Image.new("RGBA", (40, 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(ear)
    d.polygon([(4, 23), (9, 22), (10, 31), (6, 34), (0, 9)], fill=SKIN + (255,), outline=(60, 80, 40, 255))
    d.line([(2, 13), (7, 25), (7, 31)], fill=SKIN_SHADE + (255,))
    d.line([(1, 10), (4, 20)], fill=SKIN_LIGHT + (255,))
    ear = ear.filter(ImageFilter.GaussianBlur(1.1))
    face = face.convert("RGBA")
    face.alpha_composite(ear)
    img = face.convert("RGB").quantize(48, method=Image.Quantize.MEDIANCUT).convert("RGBA")
    return img


def main():
    SPRITES.mkdir(parents=True, exist_ok=True)
    ICONS.mkdir(parents=True, exist_ok=True)
    out = frames()
    for name, img in out.items():
        img.save(SPRITES / f"{name}.png")
    for i, img in enumerate(coin_drawings()):
        img.save(SPRITES / f"coin_{i}.png")
    for i, img in enumerate(goblins()):
        img.save(SPRITES / f"goblin_{i}.png")
    for kind in ("light", "heavy", "special"):
        icon(kind).save(ICONS / f"{kind}.png")
    portrait().save(PORTRAIT)
    if "--sheet" in sys.argv:
        path = sys.argv[sys.argv.index("--sheet") + 1]
        names = sorted(out)
        cols = 8
        rows = (len(names) + cols - 1) // cols + 1
        sheet = Image.new("RGBA", (cols * W, rows * H), (110, 130, 150, 255))
        d = ImageDraw.Draw(sheet)
        for k, name in enumerate(names):
            x0, y0 = (k % cols) * W, (k // cols) * H
            d.line([(x0, y0 + FLOOR + 1), (x0 + W, y0 + FLOOR + 1)], fill=(80, 96, 112, 255))
            sheet.alpha_composite(out[name], (x0, y0))
            d.text((x0 + 2, y0 + 2), name, fill=(255, 255, 255, 255))
        y0 = (rows - 1) * H
        for i, g in enumerate(goblins()):
            sheet.alpha_composite(g, (i * 34, y0 + 4))
        for i, c in enumerate(coin_drawings()):
            sheet.alpha_composite(c, (8 * 34 + i * 12, y0 + 10))
        for i, kind in enumerate(("light", "heavy", "special")):
            sheet.alpha_composite(icon(kind), (8 * 34 + 30 + i * 26, y0 + 30))
        sheet.alpha_composite(portrait(), (8 * 34 + 110, y0 + 4))
        sheet.resize((sheet.width * 2, sheet.height * 2), Image.NEAREST).save(path)
    print(f"wrote {len(out)} drawings to {SPRITES}")


if __name__ == "__main__":
    main()
