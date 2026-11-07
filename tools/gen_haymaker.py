"""Draws the Haymaker: every pose from tools/haymaker.png, his scythe, his skill icons and his portrait.

    python tools/gen_haymaker.py [--sheet contact_sheet.png]

The drawing is cut into an upper body (head and shirt, without the arms) and the legs. Each pose shifts, leans and
squashes those, bends the legs, draws the arms again in the drawing's colours (tan skin under a short dark sleeve) and puts the scythe in both hands: a black shaft bound in red, a skull at the blade's root and a long
jagged blade with a glowing red edge. Swings leave dark red trails; the spin's launch is a pillar of red energy.

His drawings are bigger than everyone else's (the scythe reaches far): `PAD_X` extra columns on both sides and
`PAD_Y` extra rows above and below, so the picture's centre is where the normal drawing's is and the game places
it the same way.
"""

import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
SPRITES = ROOT / "assets/sprites/haymaker"
ICONS = ROOT / "assets/icons/haymaker"
PORTRAIT = ROOT / "assets/portraits/haymaker.png"

PAD_X, PAD_Y = 40, 30
W, H = 84 + 2 * PAD_X, 63 + 2 * PAD_Y
CX = 33 + PAD_X           # body centre
FLOOR = 62 + PAD_Y        # the row his feet stand on
# the drawing is 33 x 54 with its feet on row 53
OFF_X, OFF_Y = 17 + PAD_X, 9 + PAD_Y

SKIN = (228, 195, 158)
SKIN_SHADE = (201, 165, 125)
SKIN_LIGHT = (251, 217, 181)
BACK_SKIN, BACK_SHADE = (201, 165, 125), (170, 136, 100)
SLEEVE = (38, 42, 42)
SLEEVE_DARK = (27, 31, 31)
SLEEVE_LIGHT = (50, 57, 57)

SHAFT = (30, 22, 28)
SHAFT_LIGHT = (70, 52, 62)
WRAP = (128, 14, 24)
WRAP_LIGHT = (190, 40, 46)
BLADE = (58, 60, 72)
BLADE_DARK = (28, 28, 38)
BLADE_EDGE = (214, 218, 228)
RUNE = (200, 24, 34)
BONE = (214, 204, 180)
BONE_SHADE = (150, 138, 116)
EYE = (255, 40, 40)

TRAIL = [(60, 4, 10), (110, 10, 18), (160, 22, 30), (215, 60, 60), (255, 150, 140)]
ENERGY = [(80, 2, 8), (140, 10, 20), (200, 26, 34), (255, 90, 80), (255, 190, 170)]

here = Path(__file__).resolve().parent
SRC = Image.open(here / "haymaker.png").convert("RGBA")

HIP = 33
BACK_SHOULDER = (6, 18)
FRONT_SHOULDER = (25, 18)


def blank():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def put(img, x, y, c):
    x, y = round(x), round(y)
    if 0 <= x < img.width and 0 <= y < img.height:
        img.putpixel((x, y), tuple(c) + (255,) if len(c) == 3 else tuple(c))


def is_skin(c):
    """The drawing's tan skin (light, mid, shade and highlight)."""
    r, g, b = c[:3]
    return r > 190 and 140 < g < 225 and 100 < b < 190 and r - b > 50


def split():
    """The upper body without its arms (rows above the hips), and the legs."""
    upper = Image.new("RGBA", (SRC.width, HIP), (0, 0, 0, 0))
    legs = Image.new("RGBA", (SRC.width, SRC.height - HIP), (0, 0, 0, 0))
    for y in range(SRC.height):
        for x in range(SRC.width):
            c = SRC.getpixel((x, y))
            if c[3] == 0:
                continue
            if y < HIP:
                if (x <= 11 and 20 <= y <= 29 and is_skin(c)) or (x >= 22 and 20 <= y and is_skin(c)):
                    continue
                upper.putpixel((x, y), c)
            elif not (x >= 24 and y <= 35 and is_skin(c)):
                legs.putpixel((x, y - HIP), c)
    return upper, legs


UPPER, LEGS = split()


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


def arm(img, shoulder, target, bend=1, back=False):
    """One arm, as thick as the drawing's: the bare arm under a short dark sleeve, a big fist."""
    elbow, wrist = two_bone(shoulder, target, 8, 10, bend)
    skin, shade = (BACK_SKIN, BACK_SHADE) if back else (SKIN, SKIN_SHADE)
    # upper arm and forearm 5 pixels thick, the forearm swelling a little towards the elbow
    line(img, shoulder, elbow, skin, 5)
    line(img, elbow, wrist, skin, 4)
    line(img, (elbow[0], elbow[1]), (elbow[0] + (wrist[0] - elbow[0]) * 0.5, elbow[1] + (wrist[1] - elbow[1]) * 0.5), skin, 5)
    line(img, (shoulder[0], shoulder[1] + 2), (elbow[0], elbow[1] + 2), shade, 1)
    line(img, (elbow[0], elbow[1] + 2), (wrist[0], wrist[1] + 2), shade, 1)
    if not back:
        line(img, (elbow[0], elbow[1] - 2), (wrist[0], wrist[1] - 2), SKIN_LIGHT, 1)
    mx, my = shoulder[0] + (elbow[0] - shoulder[0]) * 0.55, shoulder[1] + (elbow[1] - shoulder[1]) * 0.55
    line(img, shoulder, (mx, my), SLEEVE_DARK if back else SLEEVE, 6)
    if not back:
        line(img, (shoulder[0], shoulder[1] - 2), (mx, my - 2), SLEEVE_LIGHT, 1)
    # the fist
    for dy in (-2, -1, 0, 1, 2):
        for dx in (-2, -1, 0, 1, 2):
            if abs(dx) == 2 and abs(dy) == 2:
                continue
            put(img, wrist[0] + dx, wrist[1] + dy, shade if dy >= 1 else skin)
    if not back:
        put(img, wrist[0] - 1, wrist[1] - 1, SKIN_LIGHT)
    return elbow, wrist


def scythe(img, grip, angle, length=56, blade=26, flip=False, trim=True):
    """The scythe held at `grip` (the front hand, about a third of the way up the shaft), the shaft pointing along
    `angle` (degrees: 0 = forward, -90 = up, 90 = down) towards the blade. The blade leaves the top of the shaft
    sideways and curls back towards the hands; `flip` puts it on the other side. Without `trim` (a small icon) there
    are no red bindings, no skull and no rune line. Returns (top of the shaft, tip)."""
    a = math.radians(angle)
    ux, uy = math.cos(a), math.sin(a)
    gx, gy = grip
    bottom = (gx - ux * length * 0.36, gy - uy * length * 0.36)
    top = (gx + ux * length * 0.64, gy + uy * length * 0.64)
    side = -1 if flip else 1
    nx, ny = -uy * side, ux * side

    # the blade first, so the shaft and skull sit over its root
    back_pts, edge_pts = [], []
    n = 24
    for k in range(n + 1):
        t = k / n
        # centre line: out sideways, curling back down the shaft towards the tip
        cxp = top[0] + nx * blade * t - ux * blade * 0.62 * t * t + ux * 2 * (1 - t)
        cyp = top[1] + ny * blade * t - uy * blade * 0.62 * t * t + uy * 2 * (1 - t)
        half = 4.2 * min(1.0, blade / 22) * (1 - t) ** 0.9 + 0.3
        # the direction across the blade at this point (towards the shaft's top = the back)
        tx, ty = nx - ux * 1.24 * t, ny - uy * 1.24 * t
        tl = max(math.hypot(tx, ty), 0.001)
        px_, py_ = -ty / tl, tx / tl
        if px_ * ux + py_ * uy < 0:
            px_, py_ = -px_, -py_
        # serrations along the back
        notch = 1.4 if k % 4 == 2 and 0.1 < t < 0.8 else 0.0
        back_pts.append((cxp + px_ * (half + notch), cyp + py_ * (half + notch)))
        edge_pts.append((cxp - px_ * half, cyp - py_ * half))
    draw = ImageDraw.Draw(img)
    poly = [(round(x), round(y)) for x, y in back_pts + edge_pts[::-1]]
    draw.polygon(poly, fill=BLADE + (255,), outline=BLADE_DARK + (255,))
    # the cutting edge (the inner curve) bright, a red rune line glowing along the middle
    for k in range(n):
        line(img, edge_pts[k], edge_pts[k + 1], BLADE_EDGE)
    for k in range(2, n - 6 if trim else 2):
        mx = (back_pts[k][0] + edge_pts[k][0]) / 2
        my = (back_pts[k][1] + edge_pts[k][1]) / 2
        if k % 3 != 0:
            put(img, mx, my, RUNE)
    tip = edge_pts[-1]
    put(img, tip[0], tip[1], (255, 255, 255))

    # the shaft: black, bound in red at three places, a spike at the bottom
    line(img, bottom, top, SHAFT, 2)
    line(img, (bottom[0] - nx * 0.5, bottom[1] - ny * 0.5), (top[0] - nx * 0.5, top[1] - ny * 0.5), SHAFT_LIGHT, 1)
    for f in (0.14, 0.5, 0.86) if trim else ():
        wx, wy = bottom[0] + (top[0] - bottom[0]) * f, bottom[1] + (top[1] - bottom[1]) * f
        line(img, (wx - ux, wy - uy), (wx + ux, wy + uy), WRAP, 3)
        put(img, wx, wy, WRAP_LIGHT)
    spike = (bottom[0] - ux * 5, bottom[1] - uy * 5)
    line(img, bottom, spike, BLADE_EDGE, 1)
    line(img, (bottom[0] + nx, bottom[1] + ny), spike, BLADE, 1)
    if not trim:
        return top, tip
    # a little skull where the blade meets the shaft, red eyes
    sx, sy = top[0] - ux * 1.5, top[1] - uy * 1.5
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            if abs(dx) + abs(dy) <= 3:
                put(img, sx + dx, sy + dy, BONE if dy < 1 else BONE_SHADE)
    put(img, sx - 1, sy - 0.4, EYE)
    put(img, sx + 1, sy - 0.4, EYE)
    put(img, sx, sy + 1.6, BLADE_DARK)
    return top, tip


def trail(img, centre, radius, a0, a1, width=4, ry=None):
    """The dark red smear of a swing: an arc (or an ellipse, with `ry`) round `centre` from angle `a0` to `a1`
    (degrees: 0 = forward, positive = down), thin and dark where it starts, wide and bright where the blade is."""
    cx, cy = centre
    ry = radius if ry is None else ry
    steps = int(abs(a1 - a0) * max(radius, ry) / 18) + 12
    for k in range(steps + 1):
        f = k / steps
        a = math.radians(a0 + (a1 - a0) * f)
        lanes = max(1, round(width * f))
        for lane in range(lanes):
            s = 1 - lane / (radius * 1.0)
            col = TRAIL[min(4, int(f * 4.5) - lane // 2)] if f * 4.5 - lane // 2 >= 0 else TRAIL[0]
            put(img, cx + math.cos(a) * radius * s, cy + math.sin(a) * ry * s, col)


def speed_lines(img, x0, x1, y, n=3, gap=4):
    """Dark red streaks behind a thrust."""
    for k in range(n):
        yy = y + (k - n // 2) * gap
        off = (k * 5) % 7
        line(img, (x0 + off, yy), (x1 - off, yy), TRAIL[1 + k % 2])


def pillar(img, cx, top, bottom, seed=0, half=12):
    """A pillar of red energy from `top` down past `bottom`: flickering tongues, white hot in the middle."""
    for k in range(-half, half + 1):
        x = cx + k
        edge = abs(k) / half
        reach = (bottom - top) * (1 - edge * 0.6) * (0.7 + 0.3 * math.sin(k * 1.9 + seed))
        for t in range(int(reach)):
            f = t / max(reach, 1)
            heat = (1 - edge) * (1 - f)
            col = ENERGY[4] if heat > 0.7 else ENERGY[3] if heat > 0.45 else ENERGY[2] if heat > 0.25 else ENERGY[1] if heat > 0.1 else ENERGY[0]
            if edge > 0.75 and (t + k + seed) % 3 == 0:
                continue
            put(img, x + math.sin(t * 0.5 + k + seed) * edge * 2, top + t, col)


class Pose:
    def __init__(self, dx=0, drop=0, lean=0, squash=0, legs=(0, 0, 0, 0), bend=(0, 0), spread=0, tuck=0):
        """`dx`: body moved forward; `drop`: upper body lowered (the legs squashed to match by `squash`);
        `lean`: the head moved this far forward at the top, sheared down to the hips; `legs`: (back leg dx, back
        foot lift, front leg dx, front foot lift); `bend`: each shin swung back (+) or forward (-); `spread`: knees
        apart; `tuck`: feet pulled up under him."""
        self.dx, self.drop, self.lean, self.squash = dx, drop, lean, squash
        self.legs, self.bend, self.spread, self.tuck = legs, bend, spread, tuck

    def shoulder(self, which):
        sx, sy = BACK_SHOULDER if which == "back" else FRONT_SHOULDER
        return (sx + OFF_X + self.dx + round(self.lean * (HIP - sy) / HIP), sy + OFF_Y + self.drop)


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


def pose(p, grip, angle, flip=False, hands=7, behind=False, front_bend=-1, back_bend=1, length=56, blade=26,
         before=None, after=None, free_back=None, weapon=True):
    """Draw him holding the scythe in both hands: the front hand at `grip` (relative to his front shoulder), the
    back hand `hands` pixels further down the shaft (or at `free_back`, relative to the back shoulder, if given).
    `behind` draws the scythe behind him; without `weapon` his hands are empty."""
    img = blank()
    bs, fs = p.shoulder("back"), p.shoulder("front")
    g = (fs[0] + grip[0], fs[1] + grip[1])
    a = math.radians(angle)
    back_hand = (bs[0] + free_back[0], bs[1] + free_back[1]) if free_back else (g[0] - math.cos(a) * hands, g[1] - math.sin(a) * hands)
    if before:
        before(img)
    if behind and weapon:
        scythe(img, g, angle, length, blade, flip)
    arm(img, bs, back_hand, back_bend, back=True)
    draw_legs(img, p)
    draw_upper(img, p)
    if not behind and weapon:
        scythe(img, g, angle, length, blade, flip)
    arm(img, fs, g, front_bend)
    if after:
        after(img, fs)
    return img


def tilt(img, degrees, pivot):
    return img.rotate(degrees, resample=Image.NEAREST, center=pivot)


def frames():
    out = {}
    # out of an attack he holds the scythe in his front hand only; the back arm is free
    # idle: crouched a little, the scythe upright in his fist with the blade hanging over his head
    for i in range(2):
        p = Pose(drop=1 + i, squash=1, spread=2, lean=1)
        out[f"idle_{i}"] = pose(p, (6, 11), -78 - i * 2, free_back=(-3, 15 - i))
    # walk: a prowl, scythe carried forward, the free arm swinging
    for i in range(6):
        ph = i / 6 * 2 * math.pi
        s = math.sin(ph) * 4
        p = Pose(drop=1 if i % 3 else 2, lean=2, legs=(round(-s), max(0, round(math.cos(ph) * 3)), round(s), max(0, round(-math.cos(ph) * 3))))
        out[f"walk_{i}"] = pose(p, (7, 9), -66 - round(s), free_back=(-3 - round(s * 1.5), 14))
    cp = Pose(drop=9, squash=9, spread=3, lean=2)
    out["crouch"] = pose(cp, (8, 9), -45, free_back=(4, 11))
    # crouching light: the blade swept low along the floor, back to front
    out["crouch_soft_0"] = pose(cp, (-8, 9), 175, flip=True, behind=True)
    out["crouch_soft_1"] = pose(Pose(drop=10, squash=10, spread=4, lean=5, dx=2), (12, 12), 12, flip=True,
                                after=lambda im, fs: trail(im, (fs[0] - 6, FLOOR - 4), 54, 170, 360, 4, ry=8))
    out["crouch_hard_0"] = pose(cp, (-6, 7), 0, flip=True)
    out["crouch_hard_1"] = pose(Pose(drop=9, squash=9, spread=4, lean=5, dx=2), (14, 6), 0, flip=True, length=60,
                                before=lambda im: speed_lines(im, CX - 10, CX + 20, FLOOR - 18))
    # jumping: knees up as he rises, tucked at the top, reaching down as he falls
    for name, tuck, lean, ang in (("jump_up", 5, 2, -60), ("jump_top", 9, 3, -40), ("jump_fall", 2, 1, -70)):
        out[name] = pose(Pose(tuck=tuck, spread=2, lean=lean), (6, 7), ang, free_back=(-9, 3 + tuck // 3))
    ap = Pose(tuck=8, spread=2, lean=3)
    # air light: raised high behind, then hacked down in front
    out["air_soft_0"] = pose(Pose(tuck=8, spread=2, lean=-3), (-2, -12), -130, hands=8)
    out["air_soft_1"] = pose(Pose(tuck=8, spread=2, lean=6, dx=2), (12, 6), 40,
                             after=lambda im, fs: trail(im, (fs[0] - 2, fs[1] + 2), 50, -110, 55, 5))
    # air heavy: the hook thrown out and down
    out["air_hard_0"] = pose(Pose(tuck=8, spread=2, lean=-2), (-8, 4), 15, flip=True)
    out["air_hard_1"] = pose(Pose(tuck=8, spread=2, lean=6, dx=2), (15, 6), 15, flip=True, length=62,
                             before=lambda im: speed_lines(im, CX - 16, CX + 14, FLOOR - 34))
    # hurt: thrown back
    for i in range(2):
        p = Pose(dx=-1 - i, lean=-4 - i * 3, legs=(-1, 0, 2, 2), bend=(0, -2))
        out[f"hurt_{i}"] = pose(p, (0, 12 - i * 3), -110 + i * 20, hands=10, free_back=(-10, 2 - i * 6))
    # block: the shaft held upright in front of him in one fist, the other arm up behind it
    out["block"] = pose(Pose(drop=3, squash=3, lean=-1, spread=2), (8, 6), -84, free_back=(6, 4))
    # knocked out: flat on his back, the scythe dropped beside him
    ko = pose(Pose(), (2, 14), -100, free_back=(-4, 14), weapon=False)
    ko = tilt(ko, 90, pivot=(CX, FLOOR - 9))
    piece = ko.crop(ko.getbbox())
    ko2 = blank()
    ko2.alpha_composite(piece, (CX - piece.width // 2, FLOOR + 1 - piece.height))
    scythe(ko2, (CX + 26, FLOOR - 2), 178, 56, 22, False)
    out["ko"] = ko2

    # light (alternating swings): A, an overhead hack forward and down; B, a rising backhand from low behind
    out["punch_0"] = pose(Pose(lean=-5, spread=3, legs=(-2, 0, 3, 0), bend=(1, 0)), (-10, -10), -130, hands=8)
    out["punch_mid_0"] = pose(Pose(lean=1, spread=3, legs=(-3, 0, 4, 0)), (4, -12), -70, hands=8,
                              after=lambda im, fs: trail(im, (fs[0] - 4, fs[1] + 6), 48, -150, -80, 3))
    strike_a = Pose(dx=3, lean=7, drop=3, squash=3, spread=4, legs=(-4, 0, 6, 0), bend=(3, -1))
    out["punch_1"] = pose(strike_a, (14, 6), 16,
                          after=lambda im, fs: trail(im, (fs[0] - 4, fs[1] + 4), 56, -140, 40, 6))
    out["punch_mid_1"] = pose(Pose(dx=2, lean=4, drop=2, squash=2, spread=4, legs=(-3, 0, 5, 0)), (10, 12), 70, hands=8)
    out["punch_2"] = pose(Pose(lean=-4, drop=4, squash=4, spread=3, legs=(-3, 0, 2, 0)), (-10, 12), 160, flip=True, behind=True)
    out["punch_mid_2"] = pose(Pose(lean=1, drop=3, squash=3, spread=3, legs=(-3, 0, 4, 0)), (4, 14), 110, flip=True,
                              after=lambda im, fs: trail(im, (fs[0] - 2, fs[1] - 2), 48, 170, 110, 3))
    strike_b = Pose(dx=3, lean=6, spread=3, legs=(-4, 0, 6, 0), bend=(2, 0))
    out["punch_3"] = pose(strike_b, (14, 0), -35, flip=True,
                          after=lambda im, fs: trail(im, (fs[0] - 6, fs[1] + 2), 54, 150, 320, 6))
    out["punch_mid_3"] = pose(Pose(dx=2, lean=3, spread=3, legs=(-3, 0, 5, 0)), (6, -10), -80, flip=True, hands=8)
    # the soft drawings every character has (his light uses the swings above)
    out["soft_0"], out["soft_1"] = out["punch_0"], out["punch_1"]

    # heavy: coiled with the hook drawn back, the thrust, all the way out, the yank
    out["hard_0"] = pose(Pose(lean=-6, drop=3, squash=3, spread=3, legs=(-4, 0, 3, 0)), (-12, 6), 0, flip=True, hands=9)
    out["hard_1"] = pose(Pose(dx=2, lean=4, spread=3, legs=(-4, 0, 5, 0)), (6, 5), 0, flip=True,
                         before=lambda im: speed_lines(im, CX - 30, CX - 4, FLOOR - 40))
    out["hard_2"] = pose(Pose(dx=4, lean=8, drop=2, squash=2, spread=4, legs=(-6, 0, 7, 0), bend=(4, -1)), (18, 5), -2,
                         flip=True, length=66, blade=28, free_back=(-12, 6),
                         before=lambda im: speed_lines(im, CX - 36, CX + 6, FLOOR - 40, 4, 3))
    out["hard_3"] = pose(Pose(dx=-1, lean=-7, drop=2, squash=2, spread=4, legs=(-5, 0, 4, 0), bend=(-1, 2)), (-4, 6), -6,
                         flip=True, hands=9,
                         after=lambda im, fs: speed_lines(im, fs[0] + 34, fs[0] + 60, fs[1] + 6, 3, 3))

    # the lunge (light finisher): coiled low, flying forward with the blade raised, hacking down, sweeping across
    out["kick_0"] = pose(Pose(drop=8, squash=8, spread=3, lean=4, legs=(-3, 0, 3, 0)), (-8, 4), 170, flip=True, behind=True)
    fly = Pose(tuck=6, lean=8, dx=3, legs=(-6, 7, 3, 1), bend=(6, -2))
    out["kick_1"] = pose(fly, (6, -10), -60, hands=9,
                         before=lambda im: speed_lines(im, CX - 34, CX - 10, FLOOR - 30, 3, 5))
    out["kick_2"] = pose(fly, (14, 8), 45,
                         after=lambda im, fs: trail(im, (fs[0] - 2, fs[1] + 2), 54, -120, 60, 6))
    out["kick_3"] = pose(fly, (16, 4), 8, flip=True,
                         after=lambda im, fs: trail(im, (fs[0] - 4, fs[1] + 4), 52, 160, 380, 5, ry=20))

    # speaking: scythe resting on his shoulder, blade behind his head
    for i in range(2):
        img = pose(Pose(lean=i, spread=2), (-4, 2), -150, flip=True, behind=True, free_back=(-2, 14))
        if i:
            for x in range(14, 18):
                put(img, OFF_X + x + 1, OFF_Y + 12, (70, 18, 22))
        out[f"speak_{i}"] = img

    # the spin special: wound up, four drawings of the scythe going round him, the launch, the fall, the landing
    out["reap_0"] = pose(Pose(drop=6, squash=6, spread=4, lean=-4, legs=(-3, 0, 3, 0)), (-12, 6), 180, flip=True, behind=True)
    sp = Pose(drop=3, squash=3, spread=4, lean=1)
    ring = lambda a0, a1: (lambda im, fs: trail(im, (CX, FLOOR - 26), 50, a0, a1, 5, ry=14))
    out["reap_1"] = pose(sp, (12, 8), 0, flip=True, length=60, after=ring(-200, 0))
    out["reap_2"] = pose(Pose(drop=3, squash=3, spread=4, lean=3), (2, 10), 15, length=30, blade=20, after=ring(-110, 90))
    out["reap_3"] = pose(Pose(drop=3, squash=3, spread=4, lean=-1), (-16, 8), 180, length=60, after=ring(-20, 180))
    out["reap_4"] = pose(Pose(drop=3, squash=3, spread=4, lean=-2), (-6, 10), 175, flip=True, length=30, blade=20, behind=True,
                         after=ring(70, 270))
    out["reap_5"] = pose(Pose(tuck=0, lean=0, legs=(1, 0, -1, 0), bend=(-1, 1)), (2, -18), -90, hands=10, flip=True,
                         before=lambda im: pillar(im, CX, FLOOR - 16, FLOOR + PAD_Y))
    out["reap_6"] = pose(Pose(tuck=8, spread=3, lean=2), (6, 2), -40, free_back=(-9, 4))
    out["reap_7"] = pose(Pose(drop=9, squash=9, spread=4, lean=3), (8, 10), 10, flip=True, hands=9)
    for i, src in enumerate(["reap_0", "reap_0", "reap_1", "reap_3", "reap_5", "reap_7"]):
        out[f"summon_{i}"] = out[src]

    # the roll: a tight ball (the scythe on his back) turned in eighths, then rising
    out["roll_0"] = pose(Pose(drop=9, squash=9, lean=4, spread=2), (4, 10), -40, free_back=(2, 12))
    ball = pose(Pose(drop=14, squash=14, lean=5, tuck=4), (2, 8), -90, length=30, blade=14, hands=4)
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


def outlined(layer, colour=(10, 4, 8)):
    """The layer with a one-pixel dark outline round everything drawn on it."""
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
    """A square tile in the other fighters' style: a diagonal gradient from `light` (top left) to `dark`, a bright
    rim on the top and left edges, a dark one on the bottom and right."""
    img = Image.new("RGBA", (24, 24))
    for y in range(24):
        for x in range(24):
            t = (x + y) / 46
            # banded, like the others: four steps
            t = round(t * 4) / 4
            img.putpixel((x, y), tuple(round(light[k] + (dark[k] - light[k]) * t) for k in range(3)) + (255,))
    rim = tuple(min(255, c + 70) for c in light)
    for k in range(24):
        put(img, k, 0, (12, 6, 10))
        put(img, 0, k, (12, 6, 10))
        put(img, k, 23, (12, 6, 10))
        put(img, 23, k, (12, 6, 10))
    for k in range(1, 23):
        put(img, k, 1, rim)
        put(img, 1, k, rim)
        put(img, k, 22, tuple(c // 2 for c in dark))
        put(img, 22, k, tuple(c // 2 for c in dark))
    return img


def icon(kind):
    layer = Image.new("RGBA", (24, 24), (0, 0, 0, 0))
    if kind == "light":
        img = icon_base((176, 40, 48), (60, 8, 16))
        # a white crescent slash across the tile, the scythe that cut it in the corner
        for k in range(34):
            a = math.radians(-170 + k * 5)
            f = k / 33
            for lane in range(1 + round(f * 2.4)):
                put(layer, 13 + math.cos(a) * (10 - lane), 14 + math.sin(a) * (10 - lane), (255, 244, 238) if lane == 0 else (255, 130, 120))
        scythe(layer, (5, 19), -50, 18, 9, trim=False)
    elif kind == "heavy":
        img = icon_base((110, 100, 124), (34, 28, 44))
        # the hook thrown out: the shaft across, the blade hooking back on the right, red streaks behind
        scythe(layer, (5, 7), 0, 22, 10, False, trim=False)
        for y, x0, n in ((15, 2, 8), (18, 4, 9), (21, 2, 6)):
            line(layer, (x0, y), (x0 + n, y), (220, 40, 48))
            put(layer, x0 + n, y, (255, 150, 140))
    else:
        img = icon_base((96, 12, 22), (16, 4, 8))
        # a pillar of red energy, and the spin's ring round it with the blade riding it
        pillar(layer, 12, 3, 22, half=5)
        for k in range(72):
            a = math.radians(k * 5)
            col = (255, 230, 220) if 0 <= k < 12 else (255, 90, 80) if k < 40 else (150, 16, 26)
            for lane in (0, 1) if k < 30 else (0,):
                put(layer, 12 + math.cos(a) * (9 - lane), 15 + math.sin(a) * (4 - lane * 0.5), col)
    img.alpha_composite(outlined(layer))
    return img


def portrait():
    """His face from the photo (tools/haymaker_photo.jpg), cropped square and shrunk to 40 x 40 in 48 colours."""
    photo = Image.open(here / "haymaker_photo.jpg").convert("RGB")
    face = photo.crop((66, 72, 226, 232)).resize((40, 40), Image.LANCZOS)
    return face.quantize(48, method=Image.Quantize.MEDIANCUT).convert("RGBA")


def main():
    SPRITES.mkdir(parents=True, exist_ok=True)
    ICONS.mkdir(parents=True, exist_ok=True)
    for old in SPRITES.glob("*.png"):
        old.unlink()
    out = frames()
    for name, img in out.items():
        img.save(SPRITES / f"{name}.png")
    for kind in ("light", "heavy", "special"):
        icon(kind).save(ICONS / f"{kind}.png")
    portrait().save(PORTRAIT)
    if "--sheet" in sys.argv:
        path = sys.argv[sys.argv.index("--sheet") + 1]
        names = sorted(out)
        cols = 8
        rows = (len(names) + cols - 1) // cols
        sheet = Image.new("RGBA", (cols * W, rows * H), (110, 130, 150, 255))
        d = ImageDraw.Draw(sheet)
        for k, name in enumerate(names):
            x0, y0 = (k % cols) * W, (k // cols) * H
            d.line([(x0, y0 + FLOOR + 1), (x0 + W, y0 + FLOOR + 1)], fill=(80, 96, 112, 255))
            sheet.alpha_composite(out[name], (x0, y0))
            d.text((x0 + 2, y0 + 2), name, fill=(255, 255, 255, 255))
        sheet.resize((sheet.width * 2, sheet.height * 2), Image.NEAREST).save(path)
    print(f"wrote {len(out)} drawings to {SPRITES}")


if __name__ == "__main__":
    main()
