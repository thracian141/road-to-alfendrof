"""Draws the Training Dummy: a burlap sack stuffed with straw on a wooden post, a crossbar for arms with straw tufts for
hands, a painted red-and-white target on its chest and a stitched face. Every pose is the same dummy tilted, squashed,
hopping or with its arms swung; plus its skill icons and portrait.

    python tools/gen_dummy.py [--sheet contact_sheet.png]
"""

import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
SPRITES = ROOT / "assets/sprites/dummy"
ICONS = ROOT / "assets/icons/dummy"
PORTRAIT = ROOT / "assets/portraits/dummy.png"

W, H = 84, 63
CX, FLOOR = 33, 62

OUT = (46, 30, 18)
SACK = (196, 168, 112)
SACK_DARK = (160, 132, 84)
SACK_LIGHT = (222, 198, 146)
STRAW = (232, 200, 92)
STRAW_DARK = (190, 150, 50)
WOOD = (120, 78, 44)
WOOD_DARK = (84, 52, 28)
WOOD_LIGHT = (156, 108, 64)
RED = (196, 44, 44)
WHITE = (240, 232, 214)
ROPE = (150, 120, 70)
STITCH = (60, 40, 26)


def put(img, x, y, c):
    x, y = round(x), round(y)
    if 0 <= x < img.width and 0 <= y < img.height:
        img.putpixel((x, y), tuple(c) + (255,))


def rect(img, x0, y0, x1, y1, c):
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            put(img, x, y, c)


def line(img, a, b, c, width=1):
    (x0, y0), (x1, y1) = a, b
    n = int(max(abs(x1 - x0), abs(y1 - y0), 1))
    for k in range(n + 1):
        t = k / n
        for ox in range(-(width // 2), width - width // 2):
            for oy in range(-(width // 2), width - width // 2):
                put(img, x0 + (x1 - x0) * t + ox, y0 + (y1 - y0) * t + oy, c)


def outline(img):
    """A dark one-pixel outline round everything drawn."""
    out = img.copy()
    for y in range(img.height):
        for x in range(img.width):
            if img.getpixel((x, y))[3]:
                continue
            if any(0 <= x + dx < img.width and 0 <= y + dy < img.height and img.getpixel((x + dx, y + dy))[3]
                   for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                out.putpixel((x, y), OUT + (255,))
    return out


def tuft(img, x, y, direction):
    """A tuft of straw sticking out (a hand)."""
    for k in range(-2, 3):
        line(img, (x, y + k * 0.7), (x + direction * (4 + abs(k) % 2 * 2), y + k * 1.4), STRAW if k % 2 else STRAW_DARK)


def dummy(arms=(0, 0), squash=0, mouth=False, eyes="x"):
    """The dummy standing on its post. `arms`: how far each arm (back, front) is swung up (+) or down (-), in degrees;
    `squash`: rows taken out of the post (crouching)."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # the post and its foot (a cross of planks on the floor)
    post_top = 34 + squash
    rect(img, CX - 2, post_top, CX + 2, FLOOR - 3, WOOD)
    line(img, (CX - 2, post_top), (CX - 2, FLOOR - 3), WOOD_LIGHT)
    line(img, (CX + 2, post_top), (CX + 2, FLOOR - 3), WOOD_DARK)
    rect(img, CX - 11, FLOOR - 2, CX + 11, FLOOR, WOOD_DARK)
    rect(img, CX - 10, FLOOR - 2, CX + 10, FLOOR - 2, WOOD)
    # the body: a stuffed sack, tied with rope at the waist
    top = 14 + squash
    for y in range(top + 8, 40 + squash):
        half = 9 if y < 36 + squash else 7
        for x in range(CX - half, CX + half + 1):
            shade = SACK_LIGHT if x < CX - half + 3 else SACK_DARK if x > CX + half - 3 else SACK
            put(img, x, y, shade)
    rect(img, CX - 8, 36 + squash, CX + 8, 37 + squash, ROPE)
    # straw poking out of the seams
    for x, y in ((CX - 9, top + 12), (CX + 9, top + 16), (CX - 6, 39 + squash), (CX + 5, 40 + squash)):
        put(img, x, y, STRAW)
        put(img, x + (1 if x > CX else -1), y + 1, STRAW_DARK)
    # the target on its chest
    tx, ty = CX + 1, top + 17
    for r, c in ((6, RED), (4.5, WHITE), (3, RED), (1.4, WHITE)):
        for y in range(int(ty - r), int(ty + r) + 1):
            for x in range(int(tx - r), int(tx + r) + 1):
                if (x - tx) ** 2 + (y - ty) ** 2 <= r * r:
                    put(img, x, y, c)
    # the head: a round sack, tied at the neck, a stitched face
    hx, hy = CX, top + 3
    for y in range(hy - 7, hy + 6):
        for x in range(hx - 7, hx + 8):
            if ((x - hx) / 7.2) ** 2 + ((y - hy) / 6.6) ** 2 <= 1:
                put(img, x, y, SACK_LIGHT if y < hy - 3 else SACK_DARK if y > hy + 3 else SACK)
    rect(img, hx - 3, hy + 5, hx + 3, hy + 6, ROPE)
    # straw hair
    for k in range(-5, 6, 2):
        line(img, (hx + k, hy - 6), (hx + k + (1 if k > 0 else -1), hy - 9), STRAW if k % 4 else STRAW_DARK)
    # face: two stitched X eyes (or dots), a stitched mouth
    for ex in (hx - 1, hx + 4):
        if eyes == "x":
            for d in (-1, 1):
                put(img, ex + d, hy - 2 + d, STITCH)
                put(img, ex - d, hy - 2 + d, STITCH)
            put(img, ex, hy - 2, STITCH)
        else:
            put(img, ex, hy - 2, STITCH)
    if mouth:
        rect(img, hx, hy + 1, hx + 3, hy + 3, STITCH)
    else:
        for x in range(hx - 1, hx + 5):
            put(img, x, hy + 2, STITCH if x % 2 else SACK_DARK)
    # the crossbar arms, swung about the shoulders, straw tufts for hands
    sy = top + 11
    for side, lift in ((-1, arms[0]), (1, arms[1])):
        a = math.radians(-lift)
        ex = CX + side * (9 + 10 * math.cos(a))
        ey = sy + 10 * math.sin(a) * (1 if side > 0 else 1)
        line(img, (CX + side * 8, sy), (ex, ey), WOOD, 3)
        line(img, (CX + side * 8, sy - 1), (ex, ey - 1), WOOD_LIGHT)
        tuft(img, ex, ey, side)
    return outline(img)


def place(src, dx=0, dy=0, angle=0, pivot=(CX, FLOOR)):
    """The dummy moved and tilted (about its foot)."""
    img = src.rotate(angle, resample=Image.NEAREST, center=pivot) if angle else src
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    out.paste(img, (dx, dy), img)
    return out


def frames():
    out = {}
    base = dummy()
    out["idle_0"] = base
    out["idle_1"] = place(dummy(arms=(-4, -4)), angle=2)
    # it gets about by hopping on its post
    for i in range(6):
        hop = (0, 3, 5, 5, 3, 0)[i]
        out[f"walk_{i}"] = place(dummy(arms=(10, 10) if hop > 2 else (0, 0)), dy=-hop, angle=(-3, -2, 0, 0, 2, 3)[i])
    out["crouch"] = dummy(squash=6, arms=(-10, -10))
    out["crouch_soft_0"] = dummy(squash=6, arms=(-10, 20))
    out["crouch_soft_1"] = dummy(squash=6, arms=(-10, -30))
    out["crouch_hard_0"], out["crouch_hard_1"] = out["crouch_soft_0"], out["crouch_soft_1"]
    out["jump_up"] = dummy(arms=(40, 40))
    out["jump_top"] = place(dummy(arms=(20, 20)), angle=-4)
    out["jump_fall"] = dummy(arms=(60, 60), mouth=True)
    out["air_soft_0"] = dummy(arms=(10, 50))
    out["air_soft_1"] = dummy(arms=(10, -40))
    out["air_hard_0"], out["air_hard_1"] = dummy(arms=(50, 50)), dummy(arms=(-40, -40))
    # knocked about: tilting back on its post, then wobbling
    out["hurt_0"] = place(dummy(arms=(30, -20), mouth=True), angle=12)
    out["hurt_1"] = place(dummy(arms=(-20, 30), mouth=True), angle=6)
    out["block"] = dummy(arms=(70, 70), squash=2)
    # knocked over: flat on the floor
    ko = dummy(arms=(-30, -30), mouth=True, eyes="x")
    ko = ko.rotate(90, resample=Image.NEAREST, center=(CX, FLOOR - 20), expand=False)
    bb = ko.getbbox()
    piece = ko.crop(bb)
    out["ko"] = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    out["ko"].paste(piece, (CX - piece.width // 2, FLOOR + 1 - piece.height), piece)
    # the "attacks": a flop of the front arm, both arms, a wobble
    out["soft_0"] = dummy(arms=(0, 60))
    out["soft_1"] = place(dummy(arms=(0, -20)), angle=-4)
    out["hard_0"] = dummy(arms=(60, 60))
    out["hard_1"] = place(dummy(arms=(30, 30)), angle=-3)
    out["hard_2"] = place(dummy(arms=(-30, -30)), angle=-6)
    out["hard_3"] = dummy(arms=(-10, -10))
    for i in range(6):
        out[f"summon_{i}"] = place(dummy(arms=(20 * (i % 2), 20 * ((i + 1) % 2)), mouth=i % 2 == 1), angle=(-6, 6, -8, 8, -4, 0)[i])
    out["speak_0"] = base
    out["speak_1"] = dummy(mouth=True)
    # the roll: it tips over and rolls along the floor, then stands back up
    out["roll_0"] = dummy(squash=6)
    for k in range(1, 9):
        out[f"roll_{k}"] = place(dummy(squash=8), angle=-45 * k, pivot=(CX, FLOOR - 24), dy=0)
    out["roll_9"] = dummy(squash=4)
    return out


def icon(kind):
    img = Image.new("RGBA", (24, 24), (60, 46, 30, 255))
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 23, 23), outline=(20, 12, 8))
    d.rectangle((1, 1, 22, 22), outline=(150, 120, 80))
    if kind == "light":
        for r, c in ((7, RED), (5, WHITE), (3, RED), (1, WHITE)):
            d.ellipse((12 - r, 12 - r, 12 + r, 12 + r), fill=c)
    elif kind == "heavy":
        for x in (7, 16):
            for r, c in ((4, RED), (2, WHITE), (1, RED)):
                d.ellipse((x - r, 12 - r, x + r, 12 + r), fill=c)
    else:
        mini = dummy().crop((CX - 12, 4, CX + 13, FLOOR + 1)).resize((14, 22), Image.NEAREST)
        img.alpha_composite(mini.rotate(12, resample=Image.NEAREST), (5, 1))
    return img


def portrait():
    head = dummy().crop((CX - 12, 4, CX + 12, 28))
    img = Image.new("RGBA", (40, 40), (70, 90, 60, 255))
    big = head.resize((40, 40), Image.NEAREST)
    img.alpha_composite(big)
    return img


def main():
    SPRITES.mkdir(parents=True, exist_ok=True)
    ICONS.mkdir(parents=True, exist_ok=True)
    out = frames()
    for name, img in out.items():
        img.save(SPRITES / f"{name}.png")
    for kind in ("light", "heavy", "special"):
        icon(kind).save(ICONS / f"{kind}.png")
    portrait().save(PORTRAIT)
    if "--sheet" in sys.argv:
        names = sorted(out)
        cols = 8
        rows = (len(names) + cols - 1) // cols
        sheet = Image.new("RGBA", (cols * W, rows * H + 40), (110, 130, 150, 255))
        d = ImageDraw.Draw(sheet)
        for k, name in enumerate(names):
            x0, y0 = (k % cols) * W, (k // cols) * H
            sheet.alpha_composite(out[name], (x0, y0))
            d.text((x0 + 2, y0 + 2), name, fill=(255, 255, 255, 255))
        for i, kind in enumerate(("light", "heavy", "special")):
            sheet.alpha_composite(icon(kind), (i * 28, rows * H + 8))
        sheet.alpha_composite(portrait(), (100, rows * H))
        sheet.resize((sheet.width * 2, sheet.height * 2), Image.NEAREST).save(sys.argv[sys.argv.index("--sheet") + 1])
    print(f"wrote {len(out)} drawings to {SPRITES}")


if __name__ == "__main__":
    main()
