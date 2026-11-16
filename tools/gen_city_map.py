"""The campaign's maps: `python tools/gen_city_map.py` writes assets/ui/campaign/the_city.png (384x216: the Istanbul region
from the Black Sea down to the Sea of Marmara, the Bosphorus, the Golden Horn and Galata Tower), soon.png (the second map's
preview) and the little circles of the levels. Palette colours and ordered dithering only, no blending, so the pixels stay
crisp when the window scales them. Where the level circles go is in assets/campaign/campaign.ron."""
import math
import random
from collections import deque
from pathlib import Path

from PIL import Image

OUT = Path(__file__).resolve().parent.parent / "assets/ui/campaign"
W, H = 384, 216
BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]

INK = (14, 20, 40)
# the Black Sea, the Bosphorus and the Sea of Marmara: deep, mid, light, shallow
BLACK_SEA = [(20, 44, 92), (28, 62, 118), (44, 90, 148), (92, 150, 192)]
MARMARA = [(24, 78, 128), (36, 106, 156), (64, 142, 182), (118, 190, 208)]
STRAIT = [(30, 70, 122), (44, 98, 152), (72, 136, 180), (120, 182, 208)]
FOREST_D, FOREST, GRASS, FIELD, DRY, HILL = (34, 78, 50), (52, 106, 62), (98, 146, 76), (164, 168, 90), (196, 176, 112), (114, 124, 82)
SAND = (230, 216, 164)
ROOF_A, ROOF_B, STONE, STONE_D, PARK = (186, 116, 82), (216, 150, 98), (178, 170, 154), (130, 122, 114), (78, 138, 82)
GOLD, GOLD_D, WHITE = (255, 214, 92), (170, 120, 30), (250, 246, 232)


def lattice(seed):
    r = random.Random(seed)
    return {(x, y): r.random() for x in range(-2, 140) for y in range(-2, 100)}


def make_noise(seed, scale):
    table = lattice(seed)

    def noise(x, y):
        fx, fy = x / scale, y / scale
        x0, y0 = math.floor(fx), math.floor(fy)
        tx, ty = fx - x0, fy - y0
        tx, ty = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
        a, b = table[(x0, y0)], table[(x0 + 1, y0)]
        c, d = table[(x0, y0 + 1)], table[(x0 + 1, y0 + 1)]
        return (a + (b - a) * tx) * (1 - ty) + (c + (d - c) * tx) * ty

    return noise


big, mid, fine = make_noise(3, 40), make_noise(9, 14), make_noise(21, 5)


def dither(value, x, y):
    """`value` (0..1) against the ordered-dither threshold at this pixel."""
    return value * 16 > BAYER[y % 4][x % 4]


# ---- the water ----------------------------------------------------------------------------------------------------
# the Bosphorus, from the Black Sea in the north down to Marmara, and the Golden Horn off its end
BOSPHORUS = [(236, 14), (234, 34), (230, 50), (222, 64), (224, 78), (216, 92), (213, 106), (208, 120), (204, 134), (202, 150)]
GOLDEN_HORN = [(203, 138), (192, 134), (178, 124), (164, 116), (150, 106), (134, 100), (118, 96)]


def along(points, t):
    """The point `t` (0..1) of the way along a polyline."""
    segs = [math.dist(points[i], points[i + 1]) for i in range(len(points) - 1)]
    at = t * sum(segs)
    for i, s in enumerate(segs):
        if at <= s:
            f = at / s if s else 0
            return points[i][0] + (points[i + 1][0] - points[i][0]) * f, points[i][1] + (points[i + 1][1] - points[i][1]) * f
        at -= s
    return points[-1]


def dist_to_line(px, py, points):
    best = 1e9
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        dx, dy = x1 - x0, y1 - y0
        t = max(0, min(1, ((px - x0) * dx + (py - y0) * dy) / (dx * dx + dy * dy)))
        best = min(best, math.hypot(px - (x0 + dx * t), py - (y0 + dy * t)))
    return best


def north_coast(x):
    return 24 + 5 * math.sin(x / 17) + 4 * math.sin(x / 7.3 + 2) + 6 * big(x, 0)


def south_coast(x):
    if x < 215:
        return 152 + 7 * math.sin(x / 38 + 1) + 4 * math.sin(x / 9) + 4 * big(x, 90)
    return 150 + (x - 215) * 0.42 + 6 * math.sin(x / 23) + 3 * math.sin(x / 7)


water = [[False] * W for _ in range(H)]
for y in range(H):
    for x in range(W):
        # the strait opens out at the Black Sea end and is narrow in the middle
        width = 4.4 + 0.5 * math.sin(y / 9) + (max(0, 34 - y) * 0.35)
        horn = dist_to_line(x, y, GOLDEN_HORN) < 1.6 + (x - 118) / 70
        water[y][x] = y < north_coast(x) or y > south_coast(x) or dist_to_line(x, y, BOSPHORUS) < width or horn
# the Princes' Islands: land in the sea, south east
for ix, iy, r in ((262, 182, 4), (272, 186, 3), (282, 180, 3), (252, 190, 3)):
    for y in range(iy - r, iy + r + 1):
        for x in range(ix - r, ix + r + 1):
            if math.hypot(x - ix, y - iy) <= r and 0 <= x < W and 0 <= y < H:
                water[y][x] = False
# Maiden's Tower: a speck of rock in the strait mouth
water[146][207] = water[146][208] = water[147][207] = water[147][208] = False

# distance from the coast, for the shallow tones
dist = [[99] * W for _ in range(H)]
queue = deque()
for y in range(H):
    for x in range(W):
        if water[y][x] and any(0 <= x + dx < W and 0 <= y + dy < H and not water[y + dy][x + dx] for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            dist[y][x] = 0
            queue.append((x, y))
while queue:
    x, y = queue.popleft()
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx, ny = x + dx, y + dy
        if 0 <= nx < W and 0 <= ny < H and water[ny][nx] and dist[ny][nx] > dist[y][x] + 1:
            dist[ny][nx] = dist[y][x] + 1
            queue.append((nx, ny))
land_dist = [[99] * W for _ in range(H)]
queue = deque()
for y in range(H):
    for x in range(W):
        if not water[y][x] and any(0 <= x + dx < W and 0 <= y + dy < H and water[y + dy][x + dx] for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            land_dist[y][x] = 0
            queue.append((x, y))
while queue:
    x, y = queue.popleft()
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx, ny = x + dx, y + dy
        if 0 <= nx < W and 0 <= ny < H and not water[ny][nx] and land_dist[ny][nx] > land_dist[y][x] + 1:
            land_dist[ny][nx] = land_dist[y][x] + 1
            queue.append((nx, ny))

# the built-up parts: (x, y, radius, strength)
CITIES = [(176, 144, 30, 1.0), (190, 126, 17, 1.0), (236, 144, 24, 0.95), (46, 112, 26, 0.8), (96, 90, 16, 0.6), (150, 70, 14, 0.6),
          (262, 100, 16, 0.7), (130, 130, 18, 0.75), (300, 124, 20, 0.55), (84, 150, 14, 0.5)]


def urban(x, y):
    c = 0.0
    for cx, cy, r, s in CITIES:
        c = max(c, (1 - math.hypot(x - cx, (y - cy) * 1.15) / r) * s)
    return c + (mid(x, y) - 0.5) * 0.6 + (fine(x, y) - 0.5) * 0.25


img = Image.new("RGB", (W, H))
px = img.load()
for y in range(H):
    for x in range(W):
        if water[y][x]:
            # Marmara is a little greener than the Black Sea; the strait is the same blue as the Black Sea
            pal = MARMARA if y > south_coast(x) - 3 else BLACK_SEA
            d = dist[y][x]
            depth = 3 - min(3, d // 3) if d < 9 else 0
            # shallow at the coast, deeper away from it, with the odd ripple
            level = 3 if d <= 1 else 2 if d <= 4 else 1 if (d <= 9 or not dither(0.5 + (big(x, y) - 0.5), x, y)) else 0
            if level == 0 and fine(x, y) > 0.72 and (x + y) % 3 == 0:
                level = 1
            if level == 1 and fine(x, y) > 0.8 and (x * 3 + y) % 5 == 0:
                level = 2
            px[x, y] = pal[level]
            continue
        # land
        c = urban(x, y)
        n = mid(x, y) * 0.6 + fine(x, y) * 0.4
        if land_dist[y][x] == 0:
            px[x, y] = SAND if dither(0.7, x, y) else DRY
        elif c > 0.5:
            block = ((x // 3) * 7 + (y // 3) * 13 + (x // 6) * (y // 5)) % 5
            street = x % 6 == 0 or y % 5 == 0
            px[x, y] = STONE_D if street else (ROOF_A, ROOF_B, STONE, ROOF_B, ROOF_A)[block] if not (block == 4 and fine(x, y) > 0.6) else PARK
        elif c > 0.28:
            roof = dither((c - 0.28) / 0.22, x, y)
            if roof:
                px[x, y] = (ROOF_A, ROOF_B, STONE)[(x // 3 + y // 3) % 3] if (x + y) % 2 == 0 else STONE
            else:
                px[x, y] = GRASS if n > 0.45 else FIELD
        else:
            forest = big(x, y) * 0.7 + fine(x, y) * 0.3
            hill = mid(x + 60, y - 30)
            if forest > 0.56 and dither(min(1, (forest - 0.5) * 4), x, y):
                px[x, y] = FOREST_D if hill > 0.55 else FOREST
            elif n > 0.55 and dither((n - 0.5) * 3, x, y):
                px[x, y] = FIELD
            elif hill > 0.62 and dither((hill - 0.6) * 4, x, y):
                px[x, y] = HILL
            else:
                px[x, y] = GRASS

# the Golden Horn's far bank: a thin sand line already comes from the coast, now the bridges and the landmarks


def put(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        px[x, y] = c


def strait_edges(y):
    """Where the water of the strait starts and ends along row `y`."""
    xs = [x for x in range(150, 300) if water[y][x]]
    return min(xs), max(xs)


def bridge(y):
    """A suspension bridge over the strait: a deck, two towers and cables."""
    left, right = strait_edges(y)
    left, right = left - 5, right + 5
    mid_x = (left + right) // 2
    towers = (left + 3, right - 3)
    for x in range(left, right + 1):
        put(x, y, INK)
        put(x, y - 1, (214, 210, 200))
        if x % 4 == 0:
            put(x, y - 2, (255, 230, 150))
    for tx in towers:
        for k in range(2, 9):
            put(tx, y - k, INK)
            put(tx + 1, y - k, STONE_D)
    # the cables hang from the towers down to the deck in the middle
    for x in range(towers[0], towers[1] + 1):
        t = (x - towers[0]) / (towers[1] - towers[0])
        sag = 6 * (1 - (2 * t - 1) ** 2) * -1 + 6
        put(x, y - 8 + round(sag) - 1, (206, 206, 214))
    for x in range(left, towers[0]):
        t = (x - left) / max(1, towers[0] - left)
        put(x, y - 1 - round(7 * t), (206, 206, 214))
    for x in range(towers[1] + 1, right + 1):
        t = (right - x) / max(1, right - towers[1])
        put(x, y - 1 - round(7 * t), (206, 206, 214))


bridge(88)
bridge(60)


def mosque(cx, cy, dome_r, minarets):
    for dy in range(-dome_r, 1):
        w = int(math.sqrt(max(0, dome_r * dome_r - dy * dy)))
        for dx in range(-w, w + 1):
            put(cx + dx, cy + dy, (232, 226, 210) if dy < -dome_r // 2 else (196, 186, 170))
    for dx in range(-dome_r - 1, dome_r + 2):
        put(cx + dx, cy + 1, STONE_D)
    for mx in minarets:
        for k in range(0, 8):
            put(cx + mx, cy - k + 1, (236, 232, 220))
        put(cx + mx, cy - 8, (180, 70, 60))
        put(cx + mx, cy - 9, (180, 70, 60))


mosque(176, 150, 4, (-7, 7, -7 + 14, 8))
mosque(162, 152, 3, (-5, 5))


def tower(cx, base):
    """Galata Tower: a round stone tower with a balcony and a pointed cap."""
    for k in range(0, 14):
        w = 2 if k < 9 else 3
        for dx in range(-w, w + 1):
            put(cx + dx, base - k, (214, 200, 176) if dx < 1 else (156, 144, 128))
    for dx in range(-4, 5):
        put(cx + dx, base - 9, (120, 108, 96))
    for k in range(0, 6):
        for dx in range(-3 + k // 2, 4 - k // 2):
            put(cx + dx, base - 14 - k, (176, 66, 58) if dx < 1 else (128, 44, 40))
    put(cx, base - 20, GOLD)


tower(190, 132)
put(207, 145, WHITE)
put(208, 145, WHITE)

# ---- lettering (3 x 5 capitals) ------------------------------------------------------------------------------------
FONT = {
    "A": "010101111101101", "B": "110101110101110", "C": "011100100100011", "D": "110101101101110", "E": "111100110100111",
    "G": "011100101101011", "H": "101101111101101", "I": "111010010010111", "K": "101101110101101", "L": "100100100100111",
    "M": "101111111101101", "N": "110101101101101", "O": "010101101101010", "P": "110101110100100", "R": "110101110101101",
    "S": "011100010001110", "T": "111010010010010", "U": "101101101101111", "B ": "", " ": "000000000000000",
}


def text(x, y, s, color, shadow=INK, gap=1):
    for ch in s:
        glyph = FONT.get(ch, FONT[" "])
        for i, bit in enumerate(glyph):
            if bit == "1":
                gx, gy = x + i % 3, y + i // 3
                put(gx + 1, gy + 1, shadow)
                put(gx, gy, color)
        x += 3 + gap


text(150, 8, "BLACK SEA", (176, 206, 236))
text(244, 64, "BOSPHORUS", (240, 236, 214))
text(70, 190, "MARMARA", (176, 214, 232))
text(112, 104, "GOLDEN HORN", (240, 236, 214))
text(166, 164, "ISTANBUL", (255, 240, 200))

# ---- the frame and a compass --------------------------------------------------------------------------------------
for x in range(W):
    for k in (0, 1, H - 1, H - 2):
        put(x, k, INK)
    put(x, 2, SAND)
    put(x, H - 3, SAND)
for y in range(H):
    for k in (0, 1, W - 1, W - 2):
        put(k, y, INK)
    put(2, y, SAND)
    put(W - 3, y, SAND)
cx, cy = 356, 190
for k in range(-8, 9):
    put(cx, cy + k, INK)
    put(cx + k, cy, INK)
for k in range(1, 7):
    put(cx, cy - k, WHITE)
put(cx - 1, cy - 8, WHITE)
put(cx + 1, cy - 8, WHITE)
put(cx, cy - 9, WHITE)
text(cx - 1, cy - 16, "N" if False else "N", WHITE)

OUT.mkdir(parents=True, exist_ok=True)
img.save(OUT / "the_city.png")


# ---- the second map: not there yet --------------------------------------------------------------------------------
def mist():
    soon = Image.new("RGB", (W, H))
    sp = soon.load()
    r = random.Random(5)
    n1, n2 = make_noise(31, 46), make_noise(44, 17)
    tones = [(18, 20, 36), (26, 30, 52), (38, 44, 72), (58, 66, 98), (92, 102, 132)]
    for y in range(H):
        for x in range(W):
            v = n1(x, y) * 0.65 + n2(x, y) * 0.35 + (0.15 if abs(y - H / 2) < 40 else 0) * (1 - abs(y - H / 2) / 40)
            level = min(4, int(v * 5.2))
            if dither(v * 5.2 - level, x, y) and level < 4:
                level += 1
            sp[x, y] = tones[max(0, level - 1)]
    for _ in range(90):
        x, y = r.randrange(W), r.randrange(H)
        sp[x, y] = (200, 206, 230)
    # a question mark, big
    glyph = ["01110", "11011", "00011", "00110", "01100", "00000", "01100"]
    scale = 9
    ox, oy = W // 2 - 5 * scale // 2, H // 2 - 7 * scale // 2 - 6
    for gy, row in enumerate(glyph):
        for gx, bit in enumerate(row):
            if bit == "1":
                for yy in range(scale):
                    for xx in range(scale):
                        X, Y = ox + gx * scale + xx, oy + gy * scale + yy
                        sp[X + 2, Y + 2] = INK
                for yy in range(scale):
                    for xx in range(scale):
                        X, Y = ox + gx * scale + xx, oy + gy * scale + yy
                        sp[X, Y] = (236, 232, 214) if yy < scale - 2 and xx < scale - 2 else (170, 166, 150)
    for x in range(W):
        for k in (0, 1, H - 1, H - 2):
            sp[x, k] = INK
        sp[x, 2] = (110, 116, 150)
        sp[x, H - 3] = (110, 116, 150)
    for y in range(H):
        for k in (0, 1, W - 1, W - 2):
            sp[k, y] = INK
        sp[2, y] = (110, 116, 150)
        sp[W - 3, y] = (110, 116, 150)
    return soon


mist().save(OUT / "soon.png")


# ---- the level circles (28 x 28) ----------------------------------------------------------------------------------
def disc(size, ring, fill, ring_w=3, mark=None, spikes=False, glow=None):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    p = im.load()
    c = (size - 1) / 2
    for y in range(size):
        for x in range(size):
            d = math.hypot(x - c, y - c)
            r_out = size / 2 - 2
            if d <= r_out + 1 and d > r_out:
                p[x, y] = INK + (255,)
            elif d <= r_out and d > r_out - ring_w:
                p[x, y] = ring + (255,) if (x + y) % 7 else tuple(min(255, v + 30) for v in ring) + (255,)
            elif d <= r_out - ring_w and d > r_out - ring_w - 1:
                p[x, y] = INK + (255,)
            elif d <= r_out - ring_w - 1:
                p[x, y] = fill + (255,)
    if spikes:
        for k in range(5):
            a = -math.pi / 2 + (k - 2) * 0.55
            sx, sy = c + math.cos(a) * (size / 2 - 2), c + math.sin(a) * (size / 2 - 2)
            for t in range(1, 5):
                x, y = round(sx + math.cos(a) * t), round(sy + math.sin(a) * t)
                if 0 <= x < size and 0 <= y < size:
                    p[x, y] = GOLD + (255,) if t < 4 else WHITE + (255,)
    if mark:
        for (x, y) in mark(c):
            if 0 <= x < size and 0 <= y < size:
                p[x, y] = WHITE + (255,)
    return im


def check(c):
    ci = int(c)
    pts = [(ci - 5 + k, ci + k) for k in range(4)] + [(ci - 2 + k, ci + 3 - k) for k in range(8)]
    return pts + [(x, y + 1) for x, y in pts]


def lock(c):
    pts = []
    for x in range(-3, 4):
        for y in range(0, 6):
            pts.append((round(c) + x, round(c) + y - 1))
    for k in range(-2, 3):
        pts.append((round(c) + k, round(c) - 5))
    for k in range(-5, -1):
        pts.append((round(c) - 2, round(c) + k))
        pts.append((round(c) + 2, round(c) + k))
    return pts


disc(28, (255, 200, 70), (60, 40, 20)).save(OUT / "node_open.png")
disc(28, (92, 200, 110), (24, 70, 40), mark=check).save(OUT / "node_done.png")
disc(28, (120, 120, 134), (40, 40, 52), mark=lock).save(OUT / "node_locked.png")
disc(32, (255, 214, 92), (110, 30, 30), ring_w=4, spikes=True).save(OUT / "node_boss.png")
for i in range(2):
    ring = Image.new("RGBA", (40, 40), (0, 0, 0, 0))
    p = ring.load()
    for y in range(40):
        for x in range(40):
            d = math.hypot(x - 19.5, y - 19.5)
            r = 17 + i
            if r - 1 <= d <= r + 0.6:
                p[x, y] = (255, 255, 255, 255) if (x + y + i) % 4 < 2 else (255, 214, 92, 255)
    ring.save(OUT / f"node_select_{i}.png")
print("wrote", sorted(p.name for p in OUT.glob("*.png")))
