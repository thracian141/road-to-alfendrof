"""Draws the Baroness: every pose from tools/baroness_art.png, her scepter, her bolts, her blast, the knight she calls, her
skill icons and her portrait (original tools/baroness_photo.png with tools/baroness_crown.png).

    python tools/gen_baroness_sprites.py [--sheet contact_sheet.png]

The drawing is cut into the upper body (head, hair, the back arm resting on the hair, the bodice and belt), her front
arm (the purple upper sleeve, the pale blue lower sleeve and the hand), the gown below the belt, and her two boots. Each
pose lowers or leans the upper body, squashes or sways the gown, moves the boots, and puts her own front arm back turned
about the shoulder, with the scepter in her hand at its own angle and her fingers drawn back over its shaft.
"""

import colorsys
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
SPRITES = ROOT / "assets/sprites/baroness"
ICONS = ROOT / "assets/icons/baroness"
PORTRAIT = ROOT / "assets/portraits/baroness.png"
here = Path(__file__).resolve().parent

W, H = 84, 63
CX = 33
FLOOR = 62
# the drawing is 33 x 55 with its feet on row 54 and the middle of her body on column 14
OFF_X, OFF_Y = 19, 8

SRC = Image.open(here / "baroness_art.png").convert("RGBA")


def to_red(c):
    """The same shade in red: the drawing's purple gown, and the purple in her portrait's neckline."""
    h, sat, v = colorsys.rgb_to_hsv(*(k / 255 for k in c[:3]))
    r, g, b = colorsys.hsv_to_rgb(0.02, min(0.66, 0.26 + sat * 0.9), v * 0.9)
    return (round(r * 255), round(g * 255), round(b * 255)) + tuple(c[3:])


def redden(img, found=None):
    """Turn the purple pixels of `img` red; the places they were are added to `found` (the gown is told from the boots by it)."""
    for y in range(img.height):
        for x in range(img.width):
            c = img.getpixel((x, y))
            if c[3] and c[2] > c[1] + 30 and c[0] > c[1]:
                img.putpixel((x, y), to_red(c))
                if found is not None:
                    found.add((x, y))
    return img


GOWN_RED = set()
redden(SRC, GOWN_RED)

# where the parts meet, in the drawing
WAIST = 36          # first row of the gown below the belt
BOOTS = 49          # first row with boots in it
SHOULDER = (22, 20)
HAND = (27, 34)     # the middle of the front hand, hanging as drawn

GOLD = (236, 191, 58)
GOLD_DARK = (189, 149, 33)
GOLD_LIGHT = (255, 225, 138)
ORB_LIGHT = (160, 215, 255)
ORB = (70, 130, 235)
ORB_DARK = (55, 60, 175)
WHITE = (253, 253, 253)
GLOW = [(150, 210, 255), (95, 150, 250), (253, 253, 253)]
INDIGO_GLOW = [(140, 120, 245), (90, 70, 210), (210, 220, 255)]
PURPLE = (150, 62, 50)          # (named from when the gown was purple: it is red now)
PURPLE_DARK = (104, 38, 34)
PURPLE_LIGHT = (188, 106, 88)
LIPS_DARK = (110, 40, 45)


def blank(w=W, h=H):
    return Image.new("RGBA", (w, h), (0, 0, 0, 0))


def put(img, x, y, c):
    x, y = round(x), round(y)
    if 0 <= x < img.width and 0 <= y < img.height:
        img.putpixel((x, y), tuple(c[:3]) + (255,))


def is_purple(c):
    r, g, b = c[:3]
    return b > g + 30 and r > g


def split():
    """The upper body without the front arm, the front arm without its hand, the hand, the gown, and the two boots
    (each a picture the drawing's size, everything where it was)."""
    upper, arm, hand, gown = (Image.new("RGBA", SRC.size) for _ in range(4))
    back_boot, front_boot = Image.new("RGBA", SRC.size), Image.new("RGBA", SRC.size)
    for y in range(SRC.height):
        for x in range(SRC.width):
            c = SRC.getpixel((x, y))
            if c[3] == 0:
                continue
            if 20 <= y <= 35 and x >= (22 if y <= 24 else 23):
                (hand if y >= 32 and not (x >= 27 and y == 32) else arm).putpixel((x, y), c)
            elif y < WAIST:
                upper.putpixel((x, y), c)
            elif y < BOOTS or (y <= 50 and (x, y) in GOWN_RED):
                gown.putpixel((x, y), c)
            else:
                (back_boot if x < 16 else front_boot).putpixel((x, y), c)
    return upper, arm, hand, gown, back_boot, front_boot


UPPER, ARM, HAND_PX, GOWN, BACK_BOOT, FRONT_BOOT = split()


IRON_LIGHT = (196, 190, 212)
IRON = (138, 128, 160)
IRON_DARK = (70, 60, 88)


def scepter():
    """The royal scepter, upright: a flanged mace of dark steel. A gold spike on top; six steel flanges, hooked outwards
    like a crown of blades, clawing round a big blue gem; a gold collar; a thick steel haft with gold bands; a grip
    wrapped in purple leather; a heavy spiked pommel. Its grip (where her hand holds it) is returned with it."""
    rows = [
        ".....L.....",
        "....yGy....",
        "k....G....k",
        "Ik.kiGik.kI",
        ".IkilOdiIk.",
        "kIilWOOdiIk",
        "IkiOOOOOdkI",
        "kIilOOOdiIk",
        ".IkidddiIk.",
        "Ik.kiIIk.kI",
        "k..yGGGy..k",
        "...kIiIk...",
        "....kik....",
        "....yGy....",
        "....kik....",
        "....kik....",
        "....yLy....",
        "....kik....",
        "....kik....",
        "...yGGGy...",
        "....PpP....",
        "....PpP....",
        "....PpP....",
        "....PpP....",
        "...yGGGy...",
        "....kik....",
        "...kIiIk...",
        "..k.yLy.k..",
        "...kIiIk...",
        ".....k.....",
    ]
    tone = {"l": ORB_LIGHT, "O": ORB, "d": ORB_DARK, "W": WHITE, "G": GOLD, "y": GOLD_DARK, "L": GOLD_LIGHT,
            "p": PURPLE_LIGHT, "P": PURPLE_DARK, "i": IRON_LIGHT, "I": IRON, "k": IRON_DARK}
    img = Image.new("RGBA", (len(rows[0]), len(rows)))
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch != ".":
                img.putpixel((x, y), tone[ch] + (255,))
    return img, (5, 22)


SCEPTER, GRIP = scepter()
ORB_AT = (5, 6)


def rotate_point(p, pivot, degrees):
    """`p` turned `degrees` clockwise (on screen, y down) about `pivot`."""
    a = math.radians(degrees)
    dx, dy = p[0] - pivot[0], p[1] - pivot[1]
    return (pivot[0] + dx * math.cos(a) - dy * math.sin(a), pivot[1] + dx * math.sin(a) + dy * math.cos(a))


def paste_turned(img, part, pivot, degrees, at, dim=1.0):
    """Draw `part` turned `degrees` clockwise about its `pivot`, with the pivot at `at` on `img`."""
    pad = 40
    big = Image.new("RGBA", (part.width + 2 * pad, part.height + 2 * pad))
    big.paste(part, (pad, pad))
    rot = big.rotate(-degrees, resample=Image.NEAREST, center=(pivot[0] + pad, pivot[1] + pad))
    if dim != 1.0:
        px = rot.load()
        for y in range(rot.height):
            for x in range(rot.width):
                r, g, b, a = px[x, y]
                if a:
                    px[x, y] = (round(r * dim), round(g * dim), round(b * dim), a)
    img.alpha_composite(rot, (round(at[0]) - pivot[0] - pad, round(at[1]) - pivot[1] - pad))


class Pose:
    def __init__(self, drop=0, lean=0, arm=(5, 14), sc=10, feet=(0, 0, 0, 0), sway=0, flare=0, glow=0, glow_colours=None,
                 behind=False, mouth=False, extra=None, bob=0):
        """`drop`: upper body lowered (the gown squashed to match); `lean`: the head moved this far forward, sheared down to
        the waist; `arm`: where the front hand points from the shoulder; `sc`: the scepter's angle (0 upright, 90 pointing
        ahead, clockwise); `feet`: (back boot dx, back boot lift, front boot dx, front boot lift); `sway`: the hem swung
        forward; `flare`: the hem spread out; `glow`: 0 to 3, light round the orb; `behind`: the arm and scepter go behind
        her; `extra`: drawn last; `bob`: everything but the boots lowered."""
        self.drop, self.lean, self.arm, self.sc, self.feet = drop, lean, arm, sc, feet
        self.sway, self.flare, self.glow, self.behind, self.mouth, self.extra = sway, flare, glow, behind, mouth, extra
        self.glow_colours = glow_colours or GLOW
        self.bob = bob

    def at(self, x, y):
        """Where a pixel (x, y) of the drawing's upper body lands."""
        shift = round(self.lean * (WAIST - y) / WAIST)
        return (OFF_X + x + shift, OFF_Y + y + self.drop + self.bob)


def draw_boots(img, p):
    bdx, blift, fdx, flift = p.feet
    for boot, dx, lift in ((BACK_BOOT, bdx, blift), (FRONT_BOOT, fdx, flift)):
        for y in range(BOOTS, SRC.height):
            for x in range(SRC.width):
                c = boot.getpixel((x, y))
                if c[3]:
                    put(img, OFF_X + x + dx, OFF_Y + y - lift, c)


def draw_gown(img, p):
    """The gown from the belt to the hem. Crouching squashes it evenly (every row keeps a share) and lets the hem pool
    wider on the floor, covering the boots, so it stays a gown and never turns into shorts."""
    src_rows = list(range(WAIST, 51))
    pool = min(2, p.drop // 3)
    top = OFF_Y + WAIST + p.drop + p.bob
    bottom = OFF_Y + 50 + p.bob + pool
    n = max(6, bottom - top + 1)
    rows = [src_rows[round(k * (len(src_rows) - 1) / (n - 1))] for k in range(n)]
    for ny, sy in enumerate(rows):
        t = ny / max(1, n - 1)
        sway = round(p.sway * t)
        spread = round((p.flare + p.drop // 2) * t)
        # the row is stretched out to be wider (never torn down the middle): each place takes the nearest drawn pixel
        row = [x for x in range(SRC.width) if GOWN.getpixel((x, sy))[3]]
        if not row:
            continue
        lx, rx = row[0], row[-1]
        width = rx - lx + 1
        wide = width + 2 * spread
        for dx in range(wide):
            c = GOWN.getpixel((lx + dx * width // wide, sy))
            if not c[3]:
                # a gap in the drawing (a boot showing through): take the nearest gown pixel to either side
                c = next((GOWN.getpixel((x, sy)) for k in range(1, width) for x in (lx + dx * width // wide - k, lx + dx * width // wide + k) if lx <= x <= rx and GOWN.getpixel((x, sy))[3]), c)
            if c[3]:
                put(img, OFF_X + lx - spread + dx + sway, top + ny, c)


def draw_upper(img, p):
    for y in range(WAIST):
        for x in range(SRC.width):
            c = UPPER.getpixel((x, y))
            if c[3]:
                put(img, *p.at(x, y), c)
    if p.mouth:
        put(img, *p.at(16, 13), LIPS_DARK)
        put(img, *p.at(17, 13), LIPS_DARK)
        put(img, *p.at(16, 14), (200, 120, 110))
        put(img, *p.at(17, 14), (200, 120, 110))


def arm_angle(p):
    rest = math.atan2(HAND[1] - SHOULDER[1], HAND[0] - SHOULDER[0])
    want = math.atan2(p.arm[1], p.arm[0])
    return math.degrees(want - rest)


def shoulder_at(p):
    return p.at(*SHOULDER)


def hand_at(p):
    s = shoulder_at(p)
    h = rotate_point(HAND, SHOULDER, arm_angle(p))
    return (s[0] + h[0] - SHOULDER[0], s[1] + h[1] - SHOULDER[1])


def orb_at(p):
    h = hand_at(p)
    o = rotate_point(ORB_AT, GRIP, p.sc)
    return (h[0] + o[0] - GRIP[0], h[1] + o[1] - GRIP[1])


def draw_arm(img, p):
    dim = 0.85 if p.behind else 1.0
    angle = arm_angle(p)
    s = shoulder_at(p)
    paste_turned(img, ARM, SHOULDER, angle, s, dim)
    paste_turned(img, SCEPTER, GRIP, p.sc, hand_at(p), dim)
    # her fingers closed over the shaft
    paste_turned(img, HAND_PX, SHOULDER, angle, s, dim)
    if p.glow:
        glow(img, orb_at(p), p.glow, p.glow_colours)


def glow(img, centre, level, colours):
    """Light round the orb: a few motes, a ring, then a ring with rays and a white heart."""
    cx, cy = round(centre[0]), round(centre[1])
    light, mid, white = colours
    if level >= 1:
        for dx, dy in ((0, -4), (4, 0), (0, 4), (-4, 0)):
            put(img, cx + dx, cy + dy, light)
    if level >= 2:
        for k in range(16):
            a = k / 16 * 2 * math.pi
            if k % 2 == 0:
                put(img, cx + round(math.cos(a) * 4), cy + round(math.sin(a) * 4), mid)
        for dx, dy in ((3, -3), (-3, -3), (3, 3), (-3, 3)):
            put(img, cx + dx, cy + dy, light)
    if level >= 3:
        for k in range(24):
            a = k / 24 * 2 * math.pi
            put(img, cx + round(math.cos(a) * 5), cy + round(math.sin(a) * 5), mid if k % 2 else light)
        for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
            for r in (6, 7):
                put(img, cx + dx * r, cy + dy * r, light if r == 6 else white)
        put(img, cx, cy, white)


def pose(p):
    img = blank()
    if p.behind:
        draw_arm(img, p)
    draw_boots(img, p)
    draw_gown(img, p)
    draw_upper(img, p)
    if not p.behind:
        draw_arm(img, p)
    if p.extra:
        p.extra(img, p)
    return img


def tilt(img, degrees, pivot):
    return img.rotate(degrees, resample=Image.NEAREST, center=pivot)


def ward(img, p):
    """The block: a pale blue arc of light held up in front of her."""
    cx, cy = p.at(14, 24)
    for k in range(-12, 13):
        a = math.radians(k * 4.5)
        for r, c in ((16, (185, 225, 255)), (17, (110, 165, 245))):
            put(img, cx + math.cos(a) * r, cy + 4 + math.sin(a) * r * 1.15, c)


def swoosh(start, end, radius=17):
    """A faint arc where the scepter has just swung through (drawn into the frame)."""
    def draw(img, p):
        sx, sy = shoulder_at(p)
        steps = 18
        for k in range(steps + 1):
            a = math.radians(start + (end - start) * k / steps - 90)
            c = (215, 200, 245) if k % 3 else (170, 190, 250)
            put(img, sx + math.cos(a) * radius, sy + math.sin(a) * radius, c)
    return draw


def frames():
    out = {}
    stand = dict(arm=(5, 14), sc=0)
    # idle: a breath
    out["idle_0"] = pose(Pose(**stand))
    out["idle_1"] = pose(Pose(drop=1, arm=(5, 14), sc=0))
    # walk: the boots step in turn under a swaying hem, a little bob, the scepter swinging with her
    for i in range(6):
        ph = i / 6 * 2 * math.pi
        s = math.sin(ph)
        lift = lambda c: max(0, round(c * 2))
        p = Pose(bob=(0, 1, 1, 0, 1, 1)[i], arm=(5 + round(s * 2), 14), sc=0,
                 feet=(round(-s * 3), lift(math.cos(ph)), round(s * 3), lift(-math.cos(ph))), sway=round(s * 2))
        out[f"walk_{i}"] = pose(p)
    # crouch: sunk down into her gown, the scepter held across
    crouch = dict(drop=9, flare=1)
    out["crouch"] = pose(Pose(**crouch, arm=(9, 9), sc=30))
    # the low light: the scepter drawn back, then swept out low along the floor
    out["crouch_soft_0"] = pose(Pose(**crouch, lean=-2, arm=(2, 12), sc=-25))
    out["crouch_soft_1"] = pose(Pose(**crouch, lean=4, arm=(15, 7), sc=112))
    out["crouch_hard_0"], out["crouch_hard_1"] = out["crouch_soft_0"], out["crouch_soft_1"]
    # jumping: boots tucked up under a flaring hem
    out["jump_up"] = pose(Pose(feet=(1, 4, -1, 3), flare=1, sway=-1, arm=(8, 11), sc=30))
    out["jump_top"] = pose(Pose(feet=(1, 6, -1, 6), flare=2, arm=(10, 7), sc=45))
    out["jump_fall"] = pose(Pose(feet=(0, 2, 0, 1), flare=2, sway=1, arm=(7, 11), sc=20))
    # the air light: the scepter levelled, then bolts flying off it
    air = dict(feet=(1, 5, -1, 5), flare=2)
    out["air_soft_0"] = pose(Pose(**air, arm=(12, 5), sc=60, glow=1))
    out["air_soft_1"] = pose(Pose(**air, lean=-1, arm=(16, 2), sc=90, glow=2))
    out["air_hard_0"], out["air_hard_1"] = out["air_soft_0"], out["air_soft_1"]
    # hurt: thrown back
    out["hurt_0"] = pose(Pose(lean=-4, drop=1, arm=(1, 14), sc=-25, sway=-1))
    out["hurt_1"] = pose(Pose(lean=-7, drop=1, arm=(-4, 12), sc=-50, sway=-2))
    # block: the scepter held up across her, a ward of light in front
    out["block"] = pose(Pose(lean=-1, arm=(11, -2), sc=-15, extra=ward))
    # knocked out: flat on her back
    ko = pose(Pose(arm=(4, 14), sc=0))
    # turned on a wider canvas: on the frame itself the head would swing off the left edge and be cut off
    pad = 40
    big = Image.new("RGBA", (W + 2 * pad, H + 2 * pad), (0, 0, 0, 0))
    big.alpha_composite(ko, (pad, pad))
    ko = tilt(big, 90, (CX + pad, FLOOR - 9 + pad))
    piece = ko.crop(ko.getbbox())
    flat = blank()
    flat.alpha_composite(piece, (CX - piece.width // 2, FLOOR + 1 - piece.height))
    out["ko"] = flat
    # a plain jab with the scepter (drawn for completeness: her standing light is the spray)
    out["soft_0"] = pose(Pose(lean=-2, arm=(2, 14), sc=-20))
    out["soft_1"] = pose(Pose(lean=3, arm=(16, 3), sc=95))
    # the blast: the scepter raised as the orb gathers it, brighter, then thrust ahead as it goes, and the recovery
    indigo = INDIGO_GLOW
    out["hard_0"] = pose(Pose(lean=-2, arm=(10, -7), sc=40, glow=1, glow_colours=indigo))
    out["hard_1"] = pose(Pose(lean=-3, arm=(10, -8), sc=45, glow=2, glow_colours=indigo))
    out["hard_2"] = pose(Pose(lean=3, arm=(17, 0), sc=90, glow=3, glow_colours=indigo, sway=1))
    out["hard_3"] = pose(Pose(lean=1, arm=(10, 9), sc=40))
    # the knight: the scepter lifted, raised high and blazing, then pointed at the enemy (the charge), the recovery
    out["summon_0"] = pose(Pose(arm=(9, 7), sc=30))
    out["summon_1"] = pose(Pose(lean=-1, arm=(9, -5), sc=30, glow=1))
    out["summon_2"] = pose(Pose(lean=-2, arm=(10, -7), sc=40, glow=2))
    out["summon_3"] = pose(Pose(lean=-2, arm=(11, -5), sc=50, glow=3))
    out["summon_4"] = pose(Pose(lean=3, arm=(16, -6), sc=70, glow=1, sway=1))
    out["summon_5"] = pose(Pose(lean=1, arm=(8, 10), sc=25))
    # speaking: a little gesture with the scepter, her mouth open on the second
    out["speak_0"] = pose(Pose(**stand))
    out["speak_1"] = pose(Pose(arm=(9, 8), sc=35, mouth=True))
    # the charged spray: the scepter pointed, the orb glowing brighter in three stages, the release (she rocks back),
    # the recovery
    out["cast_0"] = pose(Pose(arm=(12, 6), sc=65))
    for k in range(3):
        out[f"cast_{k + 1}"] = pose(Pose(lean=-k, arm=(16, 2), sc=88, glow=k + 1))
    out["cast_4"] = pose(Pose(lean=-3, arm=(17, 0), sc=92, sway=-1, glow=1))
    out["cast_5"] = pose(Pose(arm=(10, 8), sc=40))
    # the spin: wound up with the scepter behind her, then swung round her: ahead, overhead, behind, low, and back
    out["spin_0"] = pose(Pose(lean=2, arm=(-9, 6), sc=-70, behind=True))
    out["spin_1"] = pose(Pose(lean=3, arm=(16, 2), sc=95, sway=1, extra=swoosh(-40, 60, 20)))
    out["spin_2"] = pose(Pose(lean=0, arm=(8, -8), sc=-55, extra=swoosh(100, 20, 20)))
    out["spin_3"] = pose(Pose(lean=-2, arm=(-11, 2), sc=-95, behind=True, sway=-1, extra=swoosh(20, -60, 20)))
    out["spin_4"] = pose(Pose(lean=2, drop=2, arm=(13, 10), sc=150, sway=1, extra=swoosh(220, 140, 18)))
    out["spin_5"] = pose(Pose(lean=1, arm=(8, 10), sc=30))
    # The same individually drawn shoulder-roll sequence as the other fighters.
    # Importing here also keeps full regeneration from restoring the old spin.
    from paint_roll_frames import baroness_rolls
    out.update(baroness_rolls(out["idle_0"]))
    return out


def bolts():
    """A speck of blue energy, one of a spray: a bright two-pixel head with a short blue tail (it flickers between two)."""
    out = []
    for k in range(2):
        img = Image.new("RGBA", (5, 4))
        for y in (1, 2):
            put(img, 4, y, WHITE if k == 0 else ORB_LIGHT)
            put(img, 3, y, ORB_LIGHT if k == 0 else WHITE)
            put(img, 2, y, ORB if k == 0 else ORB_LIGHT)
        put(img, 1, 1 + k, ORB_DARK if k == 0 else ORB)
        put(img, 0, 1 + (1 - k), ORB_DARK)
        out.append(img)
    return out


def blasts():
    """The blast: a ball of energy, white at the heart, blue, deepening to indigo at the edge, with a tail behind it and
    sparks turning round it (four drawings)."""
    out = []
    for k in range(4):
        img = Image.new("RGBA", (18, 14))
        cx, cy = 11, 7
        for y in range(14):
            for x in range(18):
                dx, dy = (x - cx) / 6.0, (y - cy) / 5.5
                # the tail stretches out behind (to the left)
                if x < cx:
                    dx = (x - cx) / (9.0 + (k % 2))
                d = math.hypot(dx, dy)
                if d <= 0.35:
                    put(img, x, y, WHITE)
                elif d <= 0.6:
                    put(img, x, y, (170, 215, 255))
                elif d <= 0.82:
                    put(img, x, y, (70, 125, 240))
                elif d <= 1.0:
                    put(img, x, y, (75, 55, 190))
        for j in range(3):
            a = (k / 4 + j / 3) * 2 * math.pi
            put(img, cx + round(math.cos(a) * 6.5), cy + round(math.sin(a) * 5.5), (200, 225, 255))
        out.append(img)
    return out


# Mounted charge shares the roster's native pixel scale.
from paint_knight import knight, FRAMES as KNIGHT_FRAMES, SIZE as KNIGHT_SIZE


def outlined(layer, colour=(10, 6, 14)):
    out = Image.new("RGBA", layer.size)
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
            put(img, x, y, (12, 6, 14))
    for k in range(1, 23):
        put(img, k, 1, rim)
        put(img, 1, k, rim)
        put(img, k, 22, tuple(c // 2 for c in dark))
        put(img, 22, k, tuple(c // 2 for c in dark))
    return img


def icon(kind):
    layer = Image.new("RGBA", (24, 24))
    if kind == "light":
        img = icon_base((90, 120, 200), (24, 30, 80))
        # the scepter pointing ahead, a spray of little bolts fanning out from its orb
        paste_turned(layer, SCEPTER, GRIP, 60, (6, 17))
        bolt = bolts()[0]
        for x, y in ((14, 6), (18, 9), (19, 14), (15, 12), (11, 4)):
            layer.alpha_composite(bolt, (x - 2, y - 2))
    elif kind == "heavy":
        img = icon_base((110, 90, 210), (30, 20, 70))
        # the blast flying, the scepter swung round behind it
        layer.alpha_composite(blasts()[0], (5, 4))
        paste_turned(layer, SCEPTER, GRIP, 140, (8, 17))
    else:
        img = icon_base((160, 110, 190), (50, 24, 70))
        # the knight charging
        k = knight(0)
        k = k.crop(k.getbbox())
        k = k.resize((22, 19), Image.NEAREST)
        layer.alpha_composite(k, (1, 3))
    img.alpha_composite(outlined(layer))
    return img


def portrait():
    """Keep her original face; use only the generated crown above her forehead."""
    photo = Image.open(here / "baroness_photo.png").convert("RGB")
    face = photo.crop((10, 0, 310, 300)).resize((40, 40), Image.Resampling.LANCZOS)
    face = redden(face.quantize(48, method=Image.Quantize.MEDIANCUT).convert("RGBA"))
    crown = Image.open(here / "baroness_crown.png").convert("RGBA")
    # The forehead begins at row 10. Never take facial pixels from the generated edit.
    face.paste(crown.crop((0, 0, 40, 10)), (0, 0))
    # A faint rose tint on the existing mouth, without changing its shape.
    for y in (29, 30):
        for x in range(17, 23):
            r, g, b, a = face.getpixel((x, y))
            face.putpixel((x, y), (min(255, r + 2), max(0, g - 1), b, a))
    return face


def main():
    SPRITES.mkdir(parents=True, exist_ok=True)
    ICONS.mkdir(parents=True, exist_ok=True)
    out = frames()
    for name, img in out.items():
        img.save(SPRITES / f"{name}.png")
    for i, img in enumerate(bolts()):
        img.save(SPRITES / f"bolt_{i}.png")
    for i, img in enumerate(blasts()):
        img.save(SPRITES / f"blast_{i}.png")
    for i in range(KNIGHT_FRAMES):
        knight(i).save(SPRITES / f"knight_{i}.png")
    for kind in ("light", "heavy", "special"):
        icon(kind).save(ICONS / f"{kind}.png")
    portrait().save(PORTRAIT)
    if "--sheet" in sys.argv:
        path = sys.argv[sys.argv.index("--sheet") + 1]
        names = sorted(out)
        cols = 8
        rows = (len(names) + cols - 1) // cols
        sheet = Image.new("RGBA", (cols * W, rows * H + 2 * (KNIGHT_SIZE[1] + 12) + 48), (110, 130, 150, 255))
        d = ImageDraw.Draw(sheet)
        for k, name in enumerate(names):
            x0, y0 = (k % cols) * W, (k // cols) * H
            d.line([(x0, y0 + FLOOR + 1), (x0 + W, y0 + FLOOR + 1)], fill=(80, 96, 112, 255))
            sheet.alpha_composite(out[name], (x0, y0))
            d.text((x0 + 2, y0 + 2), name, fill=(255, 255, 255, 255))
        y0 = rows * H
        for i in range(KNIGHT_FRAMES):
            sheet.alpha_composite(knight(i), ((i % 4) * (KNIGHT_SIZE[0] + 8), y0 + (i // 4) * (KNIGHT_SIZE[1] + 12)))
        y0 += 2 * (KNIGHT_SIZE[1] + 12)
        for i, b in enumerate(blasts()):
            sheet.alpha_composite(b, (i * 20, y0))
        for i, b in enumerate(bolts()):
            sheet.alpha_composite(b, (i * 8, y0 + 24))
        for i, kind in enumerate(("light", "heavy", "special")):
            sheet.alpha_composite(icon(kind), (84 + i * 26, y0))
        sheet.alpha_composite(portrait(), (164, y0))
        sheet.resize((sheet.width * 2, sheet.height * 2), Image.NEAREST).save(path)
    print(f"wrote {len(out)} drawings to {SPRITES}")


if __name__ == "__main__":
    main()
