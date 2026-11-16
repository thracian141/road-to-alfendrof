"""The campaign's maps: `python tools/gen_city_map.py` writes assets/ui/campaign/the_city.png (576 x 324, drawn at two screen
pixels a pixel in the default window: central Istanbul as on a map, the Golden Horn, the old city on its peninsula, the
Bosphorus, Uskudar and Kadikoy, the Sea of Marmara below, with Galata Tower and Hagia Sophia), soon.png (the second map's
preview) and the little circles of the levels.

The look is a painted village map: round tree crowns with a lit side, red roofed houses on tan ground, patchwork fields,
stone quays and foam along the coast. Everything is drawn from palette colours with no blending, so the pixels stay crisp.
The land's shape is traced from a street map (coordinates below are in that map's pixels, scaled by MAP). Where the level
circles go is in assets/campaign/campaign.ron, in map units (384 x 216)."""
import math
import random
from collections import deque
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "assets/ui/campaign"
W, H = 576, 324
MAP = 0.288                      # texels per pixel of the street map the shapes were traced from
BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]
rnd = random.Random(1453)

INK = (20, 24, 40)
DEEP, MID, LIGHT, SHALLOW, FOAM = (34, 96, 146), (50, 128, 176), (86, 168, 200), (142, 208, 214), (232, 244, 238)
GRASS_D, GRASS, GRASS_L, MEADOW = (60, 126, 52), (92, 160, 62), (136, 190, 76), (170, 204, 90)
LEAF_D, LEAF, LEAF_L, LEAF_H = (28, 72, 40), (46, 110, 48), (76, 150, 58), (130, 196, 84)
DIRT, DIRT_D, SAND, STONE, STONE_D, STONE_L = (206, 186, 138), (184, 160, 112), (234, 220, 170), (176, 172, 164), (124, 120, 116), (214, 210, 200)
ROOF_R, ROOF_O, ROOF_D, WALL, WALL_D = (196, 72, 48), (218, 106, 60), (150, 52, 44), (238, 222, 184), (170, 140, 104)
FIELD_Y, FIELD_G, FIELD_L = (222, 206, 88), (164, 192, 70), (196, 214, 96)
GOLD, WHITE = (255, 214, 92), (250, 246, 232)


def make_noise(seed, scale):
    r = random.Random(seed)
    table = {(x, y): r.random() for x in range(-2, int(W / scale) + 6) for y in range(-2, int(H / scale) + 6)}

    def noise(x, y):
        fx, fy = x / scale, y / scale
        x0, y0 = math.floor(fx), math.floor(fy)
        tx, ty = fx - x0, fy - y0
        tx, ty = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
        a, b, c, d = table[(x0, y0)], table[(x0 + 1, y0)], table[(x0, y0 + 1)], table[(x0 + 1, y0 + 1)]
        return (a + (b - a) * tx) * (1 - ty) + (c + (d - c) * tx) * ty

    return noise


big, mid, fine = make_noise(3, 60), make_noise(9, 20), make_noise(21, 6)


def dither(value, x, y):
    return value * 16 > BAYER[y % 4][x % 4]


def pt(p):
    return (p[0] * MAP, p[1] * MAP)


# ---- the shape of the land: traced from the street map -----------------------------------------------------------
# all the water east and south of the European shore (the Bosphorus, the Marmara and its coasts), as a polygon
SEA = [(738, -10), (772, 60), (742, 150), (690, 212), (650, 292), (704, 330), (690, 372), (716, 424), (696, 476), (640, 520),
       (540, 548), (420, 542), (340, 566), (270, 604), (130, 664), (-10, 730), (-10, 1190), (2010, 1190), (1700, 1190),
       (1560, 1086), (1400, 1040), (1250, 980), (1180, 930), (1136, 852), (1040, 834), (1000, 780), (1048, 700), (1030, 610),
       (990, 524), (930, 430), (900, 332), (950, 250), (1022, 170), (1100, 92), (1190, -10)]
# the Golden Horn: a channel from the top left down to the strait (x, y, half width)
GOLDEN_HORN = [(236, -30, 26), (290, 70, 30), (372, 168, 34), (466, 252, 38), (556, 304, 42), (650, 304, 46), (730, 286, 50)]

mask = Image.new("L", (W, H), 0)
draw = ImageDraw.Draw(mask)
draw.polygon([pt(p) for p in SEA], fill=255)
for (x0, y0, r0), (x1, y1, r1) in zip(GOLDEN_HORN, GOLDEN_HORN[1:]):
    steps = 30
    for k in range(steps + 1):
        t = k / steps
        cx, cy, r = (x0 + (x1 - x0) * t) * MAP, (y0 + (y1 - y0) * t) * MAP, (r0 + (r1 - r0) * t) * MAP
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=255)
# Maiden's Tower sits on a rock in the strait
KIZ = pt((830, 272))
draw.ellipse((KIZ[0] - 3, KIZ[1] - 2, KIZ[0] + 3, KIZ[1] + 3), fill=0)
water = [[mask.getpixel((x, y)) > 127 for x in range(W)] for y in range(H)]


def distance(source):
    """Steps from every pixel to the nearest pixel where `source(x, y)` is true."""
    d = [[999] * W for _ in range(H)]
    q = deque()
    for y in range(H):
        for x in range(W):
            if source(x, y):
                d[y][x] = 0
                q.append((x, y))
    while q:
        x, y = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < W and 0 <= ny < H and d[ny][nx] > d[y][x] + 1:
                d[ny][nx] = d[y][x] + 1
                q.append((nx, ny))
    return d


from_land = distance(lambda x, y: not water[y][x])       # for water: how far from the shore
from_water = distance(lambda x, y: water[y][x])          # for land: how far from the sea


# where things are, in street-map pixels: (x, y, half width, half height, strength)
CITY = [(470, 420, 330, 200, 1.3), (640, 170, 260, 250, 1.2), (180, 300, 260, 250, 1.1), (1110, 250, 290, 220, 1.2),
        (1290, 800, 360, 230, 1.25), (1750, 640, 420, 260, 0.9), (1850, 140, 300, 190, 0.8), (60, 780, 140, 110, 0.7),
        (1500, 920, 220, 130, 0.8), (1050, 1040, 150, 90, 0.7)]
FOREST = [(1450, 330, 200, 150, 1.0), (1700, 120, 220, 100, 0.8), (90, 60, 170, 110, 0.8), (1180, 985, 110, 60, 0.9),
          (880, 20, 120, 80, 0.8), (610, 420, 70, 50, 0.6), (1980, 380, 80, 200, 0.9), (1600, 440, 140, 90, 0.6)]


def zone(x, y, zones):
    sx, sy = x / MAP, y / MAP
    s = 0.0
    for cx, cy, rx, ry, k in zones:
        s = max(s, (1 - math.hypot((sx - cx) / rx, (sy - cy) / ry)) * k)
    return max(0.0, min(1.0, s + (mid(x, y) - 0.5) * 0.5))


img = Image.new("RGB", (W, H))
px = img.load()

# ---- sea ----------------------------------------------------------------------------------------------------------
for y in range(H):
    for x in range(W):
        if not water[y][x]:
            continue
        d = from_land[y][x]
        if d <= 1:
            c = FOAM if (x + y) % 3 else SHALLOW
        elif d <= 4:
            c = SHALLOW
        elif d <= 10:
            c = LIGHT if dither(0.3 + (10 - d) * 0.09, x, y) else MID
        else:
            c = MID if big(x, y) > 0.45 or dither(0.55, x, y) else DEEP
        # long ripples
        if c in (MID, DEEP) and ((x * 3 + y * 7 + int(mid(x, y) * 9)) % 31 == 0 and fine(x, y) > 0.35):
            c = LIGHT
        px[x, y] = c

# ---- land ground ---------------------------------------------------------------------------------------------------
for y in range(H):
    for x in range(W):
        if water[y][x]:
            continue
        d = from_water[y][x]
        city = zone(x, y, CITY)
        n = mid(x, y) * 0.6 + fine(x, y) * 0.4
        if d <= 1:
            c = SAND if fine(x, y) > 0.35 else DIRT
        elif d == 2:
            c = STONE if (x + y) % 2 else STONE_L
        elif city > 0.4:
            c = DIRT if dither(0.55 + (n - 0.5), x, y) else DIRT_D
        else:
            c = GRASS if n > 0.42 else GRASS_D
            if fine(x, y) > 0.72 and dither(0.5, x, y):
                c = GRASS_L
            if big(x + 100, y) > 0.62 and dither(0.4, x, y):
                c = MEADOW
        px[x, y] = c


def put(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        px[x, y] = c


occ = [[False] * W for _ in range(H)]


def blocked(x0, y0, x1, y1):
    for y in range(max(0, y0), min(H, y1 + 1)):
        for x in range(max(0, x0), min(W, x1 + 1)):
            if occ[y][x] or water[y][x] or from_water[y][x] <= 2:
                return True
    return False


def claim(x0, y0, x1, y1):
    for y in range(max(0, y0), min(H, y1 + 1)):
        for x in range(max(0, x0), min(W, x1 + 1)):
            occ[y][x] = True


# ---- fields (a patchwork, away from the city) ---------------------------------------------------------------------
for cx, cy, fw, fh, vertical in [(1650, 950, 300, 190, False), (1880, 830, 250, 150, True), (150, 90, 220, 140, False),
                                  (1560, 560, 200, 120, True), (1960, 990, 160, 120, False), (420, 120, 150, 100, True)]:
    x0, y0 = int((cx - fw / 2) * MAP), int((cy - fh / 2) * MAP)
    x1, y1 = int((cx + fw / 2) * MAP), int((cy + fh / 2) * MAP)
    if any(not (0 <= x < W and 0 <= y < H) or water[y][x] for x in (x0, x1) for y in (y0, y1)):
        continue
    if zone((x0 + x1) / 2, (y0 + y1) / 2, CITY) > 0.5:
        continue
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if water[y][x]:
                continue
            stripe = ((x if vertical else y) // 3) % 2
            colour = (FIELD_Y if (x0 // 40 + y0 // 40) % 2 else FIELD_G) if stripe else FIELD_L
            if x in (x0, x1) or y in (y0, y1):
                colour = GRASS_D
            px[x, y] = colour
    claim(x0, y0, x1, y1)

# ---- roads: tan lanes between the town centres --------------------------------------------------------------------
TOWNS = [(480, 430), (640, 200), (330, 300), (1100, 240), (1260, 800), (1000, 560), (1500, 700), (1750, 500), (1850, 160), (520, 160)]
for i, (ax, ay) in enumerate(TOWNS):
    for bx, by in TOWNS[i + 1:]:
        if math.hypot(ax - bx, ay - by) > 700:
            continue
        steps = int(math.hypot(ax - bx, ay - by) * MAP)
        wobble = rnd.random() * 6
        for k in range(steps):
            t = k / steps
            x = (ax + (bx - ax) * t) * MAP + math.sin(t * 9 + wobble) * 2.5
            y = (ay + (by - ay) * t) * MAP + math.cos(t * 7 + wobble) * 2.5
            ix, iy = int(x), int(y)
            if 0 <= ix < W - 1 and 0 <= iy < H - 1 and not water[iy][ix] and from_water[iy][ix] > 2 and zone(ix, iy, CITY) < 0.6:
                put(ix, iy, DIRT)
                put(ix + 1, iy, DIRT_D)

# ---- houses ---------------------------------------------------------------------------------------------------------


def house(x, y, w, h, roof):
    """A house: a roof with a lit left slope over a cream wall, shadow to the right and below."""
    rh = 3 if h < 6 else 4
    for dy in range(rh):
        for dx in range(-dy // 2, w + dy // 2 + 1):
            c = roof if dx < w * 0.55 else ROOF_D
            if dy == 0:
                c = (255, 168, 120) if roof == ROOF_O else (236, 110, 84)
            put(x + dx, y + dy, c)
    for dy in range(rh, h):
        for dx in range(w + 1):
            put(x + dx, y + dy, WALL if dx < w - 1 else WALL_D)
    put(x + w // 2, y + h - 1, (96, 64, 48))
    for dx in range(w + 2):
        put(x + dx + 1, y + h, DIRT_D)
    put(x + w + 1, y + rh, DIRT_D)


for _ in range(26000):
    x, y = rnd.randrange(6, W - 14), rnd.randrange(6, H - 14)
    city = zone(x, y, CITY)
    if city < 0.3 or rnd.random() > (city - 0.1) ** 0.5:
        continue
    w, h = rnd.choice((5, 6, 6, 7, 8)), rnd.choice((5, 6, 6, 7))
    if blocked(x - 1, y - 1, x + w + 2, y + h + 2):
        continue
    house(x, y, w, h, rnd.choice((ROOF_R, ROOF_R, ROOF_O, ROOF_O, ROOF_D)))
    claim(x - 1, y - 1, x + w + 2, y + h + 2)


# ---- trees ----------------------------------------------------------------------------------------------------------
def tree(cx, cy, r):
    """A round crown: dark underside, lit upper left, a few highlights."""
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            d = math.hypot(dx, dy)
            if d <= r + 0.3:
                lit = (dx + dy) / (2 * r + 0.01)
                c = LEAF_D if lit > 0.45 else LEAF if lit > 0.0 else LEAF_L
                if d > r - 0.7 and lit > 0:
                    c = LEAF_D
                put(cx + dx, cy + dy, c)
    for k in range(r):
        put(cx - r // 2 + (k % 2), cy - r // 2 - 1 + k // 2, LEAF_H if k % 2 == 0 else LEAF_L)
    put(cx + r // 2, cy + r + 1, (30, 64, 36))


trees = []
for _ in range(60000):
    x, y = rnd.randrange(4, W - 4), rnd.randrange(4, H - 4)
    forest, city = zone(x, y, FOREST), zone(x, y, CITY)
    chance = forest ** 1.1 * 0.8 + (city * 0.08 if 0.3 < city < 0.8 else 0) + (0.012 if city < 0.3 else 0)
    if rnd.random() > chance:
        continue
    r = rnd.choice((3, 3, 4, 4, 5)) if forest > 0.3 else rnd.choice((2, 3, 3))
    if blocked(x - r, y - r, x + r, y + r + 1):
        continue
    trees.append((y, x, r))
    claim(x - r + 1, y - r + 1, x + r - 1, y + r - 1)
for y, x, r in sorted(trees):
    tree(x, y, r)

# ---- boulders and quays ---------------------------------------------------------------------------------------------
for _ in range(120):
    x, y = rnd.randrange(8, W - 8), rnd.randrange(8, H - 8)
    if blocked(x - 2, y - 2, x + 3, y + 2) or zone(x, y, CITY) > 0.5:
        continue
    for dy in range(-1, 2):
        for dx in range(-2, 3):
            if abs(dx) + abs(dy) <= 2:
                put(x + dx, y + dy, STONE_L if dx + dy < 0 else STONE if dx + dy == 0 else STONE_D)
    claim(x - 2, y - 2, x + 3, y + 2)
# Haydarpasa's piers on the Asian shore
for k, y0 in enumerate((596, 612, 630)):
    px0 = int(995 * MAP)
    py0 = int(y0 * MAP)
    for dx in range(0, 12 - k * 2):
        put(px0 - dx, py0, STONE_L)
        put(px0 - dx, py0 + 1, STONE_D)

# ---- landmarks --------------------------------------------------------------------------------------------------------


def minaret(x, y, h):
    for k in range(h):
        put(x, y - k, (240, 236, 224))
    put(x, y - h, (190, 70, 60))
    put(x, y - h - 1, (190, 70, 60))
    put(x - 1, y - h // 2, STONE_D)
    put(x + 1, y - h // 2, STONE_D)


def mosque(cx, cy, r, minarets):
    for dy in range(-r, 2):
        w = int(math.sqrt(max(0, r * r - dy * dy)))
        for dx in range(-w, w + 1):
            put(cx + dx, cy + dy, (208, 214, 226) if dx + dy < -r * 0.4 else (150, 160, 184) if dx + dy > r * 0.4 else (178, 186, 206))
    for dx in range(-r - 2, r + 3):
        put(cx + dx, cy + 2, STONE_D)
        put(cx + dx, cy + 3, DIRT_D)
    for mx, my in minarets:
        minaret(cx + mx, cy + my, 11)
    put(cx, cy - r - 1, GOLD)


mosque(int(640 * MAP), int(420 * MAP), 7, ((-12, 0), (12, 0), (-10, 8), (10, 8)))        # Hagia Sophia
mosque(int(560 * MAP), int(470 * MAP), 5, ((-9, 0), (9, 0)))                              # the Blue Mosque
mosque(int(246 * MAP), int(318 * MAP), 4, ((-6, 0),))
mosque(int(1110 * MAP), int(168 * MAP), 5, ((-8, 0), (8, 0)))                            # Uskudar


def maiden_tower():
    cx, cy = int(KIZ[0]), int(KIZ[1])
    for dy in range(-6, 1):
        for dx in range(-2, 3):
            put(cx + dx, cy + dy, (240, 236, 226) if dx < 1 else (190, 186, 178))
    for dx in range(-3, 4):
        put(cx + dx, cy - 3, STONE_D)
    for k in range(3):
        for dx in range(-2 + k, 3 - k):
            put(cx + dx, cy - 7 - k, (184, 70, 56))
    put(cx, cy - 11, GOLD)


maiden_tower()


def galata_tower(cx, base):
    """Galata Tower: a tall round stone tower, a balcony under its pointed cap."""
    for k in range(0, 21):
        w = 3 if k < 13 else 4
        for dx in range(-w, w + 1):
            put(cx + dx, base - k, (222, 206, 176) if dx < 0 else (188, 168, 140) if dx < w - 1 else (136, 116, 96))
        if k % 4 == 1:
            put(cx - 1, base - k, (74, 60, 50))
    for dx in range(-6, 7):
        put(cx + dx, base - 13, STONE_D)
        put(cx + dx, base - 14, (96, 88, 82))
    for k in range(0, 10):
        for dx in range(-4 + k // 2, 5 - k // 2):
            put(cx + dx, base - 21 - k, (190, 74, 60) if dx < 1 else (140, 52, 46))
    put(cx, base - 31, GOLD)
    put(cx, base - 32, GOLD)


GALATA = (int(590 * MAP), int(268 * MAP))
galata_tower(GALATA[0], GALATA[1])

# the Galata Bridge across the Golden Horn's mouth
for x in range(int(535 * MAP), int(640 * MAP)):
    t = (x - int(535 * MAP)) / (int(640 * MAP) - int(535 * MAP))
    y = int((335 - 12 * t) * MAP) + 0
    if water[y][x] or water[y + 1][x]:
        put(x, y, STONE_L)
        put(x, y + 1, STONE_D)
        put(x, y - 1, (110, 100, 96) if x % 3 == 0 else STONE_L)

# ---- ships ------------------------------------------------------------------------------------------------------------
ships = []
for _ in range(900):
    x, y = rnd.randrange(10, W - 20), rnd.randrange(10, H - 10)
    if water[y][x] and from_land[y][x] > 9 and all(abs(x - a) + abs(y - b) > 40 for a, b in ships):
        ships.append((x, y))
        if len(ships) >= 16:
            break
for i, (x, y) in enumerate(ships):
    big_ship = i % 3 == 0
    length = 14 if big_ship else 9
    hull, cabin = ((70, 74, 96), (220, 90, 70)) if big_ship else (WHITE, (60, 90, 140))
    for dx in range(length):
        put(x + dx, y, hull)
        put(x + dx, y - 1, hull)
        put(x + dx, y + 1, (40, 60, 90))
    put(x + length, y, hull)
    for dx in range(2, length - 3):
        put(x + dx, y - 2, cabin)
    put(x + length - 4, y - 3, WHITE)
    for dx in range(-8, 0):                       # a wake
        if dx % 2:
            put(x + dx, y, FOAM)

# ---- lettering (3 x 5 capitals) -----------------------------------------------------------------------------------------
FONT = {
    "A": "010101111101101", "B": "110101110101110", "C": "011100100100011", "D": "110101101101110", "E": "111100110100111",
    "G": "011100101101011", "H": "101101111101101", "I": "111010010010111", "K": "101101110101101", "L": "100100100100111",
    "M": "101111111101101", "N": "110101101101101", "O": "010101101101010", "P": "110101110100100", "R": "110101110101101",
    "S": "011100010001110", "T": "111010010010010", "U": "101101101101111", " ": "000000000000000",
}


def text_on(x, y, s, color, scale=2, shadow=INK):
    """`s` in 3 x 5 capitals, `scale` texels a dot, with a drop shadow."""
    start = x
    for layer in (shadow, color):
        x = start
        off = 1 if layer == shadow else 0
        for ch in s:
            glyph = FONT.get(ch, FONT[" "])
            for i, bit in enumerate(glyph):
                if bit == "1":
                    for sy in range(scale):
                        for sx in range(scale):
                            put(x + (i % 3) * scale + sx + off, y + (i // 3) * scale + sy + off, layer)
            x += 4 * scale


text_on(int(1100 * MAP), int(30 * MAP), "BOSPHORUS", (214, 238, 244))
text_on(int(60 * MAP), int(840 * MAP), "MARMARA", (200, 232, 242))
text_on(int(430 * MAP), int(205 * MAP), "GOLDEN HORN", (226, 244, 246), 1)
text_on(int(440 * MAP), int(560 * MAP), "ISTANBUL", WHITE, 2)

# ---- the frame ------------------------------------------------------------------------------------------------------
for x in range(W):
    for k in (0, 1, 2, H - 1, H - 2, H - 3):
        put(x, k, INK)
    put(x, 3, SAND)
    put(x, H - 4, SAND)
for y in range(H):
    for k in (0, 1, 2, W - 1, W - 2, W - 3):
        put(k, y, INK)
    put(3, y, SAND)
    put(W - 4, y, SAND)

OUT.mkdir(parents=True, exist_ok=True)
img.save(OUT / "the_city.png")


# ---- the second map: not there yet --------------------------------------------------------------------------------
def mist():
    soon = Image.new("RGB", (W, H))
    sp = soon.load()
    r = random.Random(5)
    n1, n2 = make_noise(31, 70), make_noise(44, 24)
    tones = [(18, 20, 36), (26, 30, 52), (38, 44, 72), (58, 66, 98), (92, 102, 132)]
    for y in range(H):
        for x in range(W):
            v = n1(x, y) * 0.65 + n2(x, y) * 0.35 + (0.15 if abs(y - H / 2) < 60 else 0) * (1 - abs(y - H / 2) / 60)
            level = min(4, int(v * 5.2))
            if dither(v * 5.2 - level, x, y) and level < 4:
                level += 1
            sp[x, y] = tones[max(0, level - 1)]
    for _ in range(140):
        sp[r.randrange(W), r.randrange(H)] = (200, 206, 230)
    glyph = ["01110", "11011", "00011", "00110", "01100", "00000", "01100"]
    scale = 13
    ox, oy = W // 2 - 5 * scale // 2, H // 2 - 7 * scale // 2 - 8
    for gy, row in enumerate(glyph):
        for gx, bit in enumerate(row):
            if bit == "1":
                for yy in range(scale):
                    for xx in range(scale):
                        sp[ox + gx * scale + xx + 3, oy + gy * scale + yy + 3] = INK
                for yy in range(scale):
                    for xx in range(scale):
                        sp[ox + gx * scale + xx, oy + gy * scale + yy] = (236, 232, 214) if yy < scale - 3 and xx < scale - 3 else (170, 166, 150)
    for x in range(W):
        for k in (0, 1, 2, H - 1, H - 2, H - 3):
            sp[x, k] = INK
        sp[x, 3] = (110, 116, 150)
        sp[x, H - 4] = (110, 116, 150)
    for y in range(H):
        for k in (0, 1, 2, W - 1, W - 2, W - 3):
            sp[k, y] = INK
        sp[3, y] = (110, 116, 150)
        sp[W - 4, y] = (110, 116, 150)
    return soon


mist().save(OUT / "soon.png")


# ---- the level circles (28 x 28) ----------------------------------------------------------------------------------
def disc(size, ring, fill, ring_w=3, mark=None, spikes=False):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    p = im.load()
    c = (size - 1) / 2
    for y in range(size):
        for x in range(size):
            d = math.hypot(x - c, y - c)
            r_out = size / 2 - 2
            if r_out < d <= r_out + 1:
                p[x, y] = INK + (255,)
            elif r_out - ring_w < d <= r_out:
                p[x, y] = ring + (255,) if (x + y) % 7 else tuple(min(255, v + 30) for v in ring) + (255,)
            elif r_out - ring_w - 1 < d <= r_out - ring_w:
                p[x, y] = INK + (255,)
            elif d <= r_out - ring_w - 1 and fill is not None:
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
# the last level's ring is hollow, so Galata Tower shows through it
disc(36, (255, 214, 92), None, ring_w=4, spikes=True).save(OUT / "node_boss.png")
for i in range(2):
    ring = Image.new("RGBA", (44, 44), (0, 0, 0, 0))
    p = ring.load()
    for y in range(44):
        for x in range(44):
            d = math.hypot(x - 21.5, y - 21.5)
            r = 19 + i
            if r - 1 <= d <= r + 0.6:
                p[x, y] = (255, 255, 255, 255) if (x + y + i) % 4 < 2 else (255, 214, 92, 255)
    ring.save(OUT / f"node_select_{i}.png")
print("wrote", sorted(p.name for p in OUT.glob("*.png")))
