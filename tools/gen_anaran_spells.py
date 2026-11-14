"""Draws the five alternate spells of Anaran's light attack: a fireball for each, in six frames, with its own particles
around it (assets/sprites/anaran/spell_<name>_<0..5>.png), and a contact sheet to look at.

Requires Python 3 with Pillow:  python tools/gen_anaran_spells.py [assets dir] [sheet.png]

The fireballs fly to the right (the game turns them to face where they go), so the flames and embers trail to the
left. Each is 22 x 22 pixels with the ball in the middle (the hit box is smaller: 10 x 10).
"""
import math
import random
import sys
from pathlib import Path

from PIL import Image

SIZE = 22
FRAMES = 6
C = 10.5  # the middle of the picture


class Canvas:
    def __init__(self):
        self.img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
        self.px = self.img.load()

    def put(self, x, y, colour, alpha=255):
        x, y = round(x), round(y)
        if 0 <= x < SIZE and 0 <= y < SIZE:
            old = self.px[x, y]
            if alpha >= 255 or old[3] == 0:
                self.px[x, y] = colour + (alpha,)
            else:  # over what is there
                a = alpha / 255
                self.px[x, y] = tuple(round(c * a + o * (1 - a)) for c, o in zip(colour, old[:3])) + (max(old[3], alpha),)

    def disc(self, cx, cy, r, colour, alpha=255):
        for y in range(SIZE):
            for x in range(SIZE):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                    self.put(x, y, colour, alpha)

    def ring(self, cx, cy, r0, r1, colour, alpha=255, arc=None):
        for y in range(SIZE):
            for x in range(SIZE):
                d = math.hypot(x - cx, y - cy)
                if r0 <= d <= r1:
                    if arc is not None:
                        a = math.degrees(math.atan2(y - cy, x - cx)) % 360
                        lo, hi = arc
                        if not ((a - lo) % 360 <= (hi - lo) % 360):
                            continue
                    self.put(x, y, colour, alpha)

    def line(self, a, b, colour, alpha=255):
        (x0, y0), (x1, y1) = a, b
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        for i in range(int(steps) + 1):
            t = i / steps
            self.put(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, colour, alpha)


def polar(angle, r, cx=C, cy=C):
    return cx + math.cos(math.radians(angle)) * r, cy + math.sin(math.radians(angle)) * r


# ---- the black sun: a black ball with a golden corona and rays that turn, sparks drifting out
def sun(t):
    c = Canvas()
    for k in range(8):  # the rays, turning an eighth of a turn over the six frames
        angle = k * 45 + t * 7.5
        length = 4 if k % 2 == 0 else 2.5
        for i in range(int(length)):
            r = 6.0 + i
            colour = (255, 214, 70) if i < 2 else (255, 150, 30)
            x, y = polar(angle, r)
            c.put(x, y, colour)
    c.disc(C, C, 5.3, (255, 200, 60) if t % 2 == 0 else (255, 228, 120))  # the corona
    c.disc(C, C, 4.2, (12, 8, 20))  # the black sun
    c.put(C - 1.5, C - 2, (70, 36, 100))  # a violet sheen
    c.put(C - 0.5, C - 2.5, (46, 24, 72))
    for j in range(6):  # sparks drifting outwards
        angle = j * 60 + t * 20
        r = 9.0 + ((t + j * 2) % 3) * 0.5
        x, y = polar(angle, r)
        c.put(x, y, (255, 236, 150) if (t + j) % 2 else (255, 160, 40))
    return c.img


# ---- blood: a crimson ball that wobbles, with blobs round it and drips falling from it
def blood(t):
    c = Canvas()
    wobble = 0.5 * math.sin(t * math.pi / 3)
    c.disc(C, C, 4.7 + wobble, (84, 0, 12))
    c.disc(C, C, 4.0 + wobble, (130, 6, 22))
    c.disc(C - 0.5, C - 0.5, 2.8, (178, 16, 34))
    c.put(C - 1.5, C - 2, (255, 140, 150))
    c.put(C - 0.5, C - 2.5, (255, 96, 110))
    for j in range(3):  # blobs of blood orbiting
        x, y = polar(j * 120 + t * 30, 7.8)
        c.disc(x, y, 1.2, (150, 8, 24))
        c.put(x - 0.5, y - 0.5, (230, 60, 70))
    for j, dx in enumerate((-3, 1, 4)):  # drips falling from the ball
        y = 15 + ((t * 1.4 + j * 2.2) % 5)
        x = C + dx
        c.put(x, y, (200, 20, 40))
        c.put(x, y + 1, (140, 6, 22))
        if y < 17:
            c.put(x, y - 1, (110, 4, 18))
    rng = random.Random(t * 7 + 1)
    for _ in range(4):  # splatter behind
        c.put(rng.randint(1, 5), rng.randint(6, 15), (150, 8, 24))
    return c.img


# ---- lightning: a white-hot core in a cyan glow, arcs that jump to new places every frame
def electric(t):
    c = Canvas()
    c.disc(C, C, 6.6, (60, 170, 255), 120)
    c.disc(C, C, 5.0, (110, 215, 255), 200)
    c.disc(C, C, 3.2, (210, 245, 255))
    c.disc(C, C, 2.0, (255, 255, 224))
    c.put(C, C, (255, 255, 255))
    rng = random.Random(100 + t)
    for _ in range(4):  # arcs, jagged lines out from the core
        angle = rng.uniform(0, 360)
        points = [(C, C)]
        for step in range(1, 5):
            jitter = rng.uniform(-28, 28)
            points.append(polar(angle + jitter, step * 2.4))
        for a, b in zip(points, points[1:]):
            c.line(a, b, (90, 170, 255), 200)
        for a, b in zip(points, points[1:]):
            c.line((a[0] + 0.0, a[1]), (b[0], b[1] + 0.0), (240, 252, 255))
    for _ in range(5):  # sparks
        x, y = polar(rng.uniform(0, 360), rng.uniform(6.5, 10))
        c.put(x, y, (255, 240, 90))
    return c.img


# ---- fire: a red-orange head with a tail of flames behind it and embers lifting off
def fire(t):
    c = Canvas()
    head = (14.0, C)
    for dx in range(0, 13):  # the tail of flames: a wavy tongue that narrows to a point
        wave = 1.3 * math.sin(t * math.pi / 3 + dx * 0.75) * (dx / 13)
        half = max(0.0, 4.6 * (1 - dx / 13) ** 1.5) + 0.5 * math.sin(t * 2.1 + dx * 1.3)
        x = head[0] - dx
        for colour, share in (((214, 46, 18), 1.0), ((255, 120, 24), 0.68), ((255, 214, 70), 0.36)):
            h = half * share
            for y in range(SIZE):
                if abs(y - (C + wave)) <= h:
                    c.put(x, y, colour)
    c.disc(head[0], head[1], 4.4, (214, 46, 18))
    c.disc(head[0] + 0.3, head[1], 3.3, (255, 120, 24))
    c.disc(head[0] + 0.6, head[1], 2.0, (255, 214, 70))
    c.put(head[0] + 0.5, head[1], (255, 250, 200))
    rng = random.Random(200 + t)
    for _ in range(7):  # embers lifting off behind
        x = rng.uniform(1.5, 9)
        y = C + rng.uniform(-6, 6) - (9 - x) * 0.2
        c.put(x, y, (255, 160, 40) if rng.random() < 0.6 else (255, 224, 110))
    return c.img


# ---- water: a blue ball with a ripple round it, droplets orbiting and bubbles drifting up behind
def water(t):
    c = Canvas()
    c.ring(C, C, 6.0, 7.0, (140, 205, 255), 150, arc=((t * 60) % 360, (t * 60 + 250) % 360))
    c.disc(C, C, 4.7, (20, 70, 180))
    c.disc(C, C, 4.1, (40, 110, 225))
    c.disc(C - 0.4, C - 0.4, 2.9, (70, 155, 245))
    c.put(C - 1.5, C - 2, (225, 245, 255))
    c.put(C - 0.5, C - 2.5, (225, 245, 255))
    c.put(C - 1.5, C - 1, (180, 225, 255))
    for j in range(5):  # droplets orbiting
        x, y = polar(j * 72 + t * 30, 8.4)
        c.put(x, y, (170, 225, 255))
        c.put(x + 1, y, (170, 225, 255))
        c.put(x, y - 1, (240, 252, 255))
    for j in range(3):  # bubbles behind, drifting up
        x = 2.5 + j * 2.6
        y = 15 - ((t * 1.2 + j * 2.3) % 9)
        for dx, dy in ((0, -1), (-1, 0), (1, 0), (0, 1)):
            c.put(x + dx, y + dy, (190, 235, 255), 200)
        c.put(x - 0.5, y - 0.5, (255, 255, 255))
    return c.img


SPELLS = {"sun": sun, "blood": blood, "electric": electric, "fire": fire, "water": water}

if __name__ == "__main__":
    assets = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "assets"
    folder = assets / "sprites" / "anaran"
    folder.mkdir(parents=True, exist_ok=True)
    for name, draw in SPELLS.items():
        for t in range(FRAMES):
            draw(t).save(folder / f"spell_{name}_{t}.png")
    print("wrote", len(SPELLS) * FRAMES, "pictures to", folder)
    if len(sys.argv) > 2:  # a contact sheet: a row of frames for each spell, 10x, on a dark ground
        scale = 10
        sheet = Image.new("RGBA", (FRAMES * SIZE * scale, len(SPELLS) * SIZE * scale), (36, 38, 56, 255))
        for row, (name, draw) in enumerate(SPELLS.items()):
            for t in range(FRAMES):
                big = draw(t).resize((SIZE * scale, SIZE * scale), Image.NEAREST)
                sheet.alpha_composite(big, (t * SIZE * scale, row * SIZE * scale))
        sheet.save(sys.argv[2])
        print("wrote", sys.argv[2])
