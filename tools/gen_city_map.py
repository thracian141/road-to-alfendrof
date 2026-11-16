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

# ---- the city, seen from above: blocks of roofs with streets between them --------------------------------------------------
def put(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        px[x, y] = c


def shade(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c)


TERRACOTTA = [(196, 84, 58), (212, 112, 70), (178, 70, 52), (224, 136, 88), (204, 98, 64)]
CONCRETE = [(214, 200, 176), (230, 216, 190), (190, 178, 160), (240, 230, 206), (204, 190, 168)]
ROOF_BLUE = [(120, 150, 146), (140, 168, 160)]
STREET, STREET_L = (140, 126, 114), (164, 150, 134)
PARK_G, PARK_L, PARK_D = (96, 154, 70), (132, 186, 84), (68, 128, 58)
PLAZA = (216, 200, 164)

# how old the roofs are, by district, in street-map pixels: (x, y, half width, half height, share of terracotta roofs)
OLD = [(470, 420, 340, 200, 0.85), (640, 200, 280, 260, 0.6), (1110, 250, 260, 220, 0.5), (190, 300, 280, 260, 0.45),
       (1290, 800, 330, 220, 0.3)]
PARKS = [(700, 395, 70, 45), (880, 8, 120, 90), (1180, 985, 110, 62), (1450, 330, 230, 150), (80, 60, 170, 110), (1640, 450, 120, 80),
         (610, 560, 60, 30), (1720, 130, 180, 80)]


def terracotta_share(x, y):
    sx, sy = x / MAP, y / MAP
    best = 0.3
    for cx, cy, rx, ry, k in OLD:
        best = max(best, (1 - math.hypot((sx - cx) / rx, (sy - cy) / ry)) * k + 0.1)
    return best + (mid(x, y) - 0.5) * 0.5


def park_amount(x, y):
    sx, sy = x / MAP, y / MAP
    s = 0.0
    for cx, cy, rx, ry in PARKS:
        s = max(s, 1 - math.hypot((sx - cx) / rx, (sy - cy) / ry))
    return s + (mid(x, y) - 0.5) * 0.4


# a seed for each block of buildings; a block gets the direction of the nearest shore, so the streets follow the coast
CELL = 13
seeds = {}
for gy in range(-1, H // CELL + 2):
    for gx in range(-1, W // CELL + 2):
        for _ in range(rnd.choice((1, 2, 2, 3))):
            seeds.setdefault((gx, gy), []).append((gx * CELL + rnd.random() * CELL, gy * CELL + rnd.random() * CELL))


def shore_angle(x, y):
    xi, yi = max(1, min(W - 2, int(x))), max(1, min(H - 2, int(y)))
    gx = from_water[yi][min(W - 1, xi + 3)] - from_water[yi][max(0, xi - 3)]
    gy = from_water[min(H - 1, yi + 3)][xi] - from_water[max(0, yi - 3)][xi]
    return math.atan2(gy, gx) + math.pi / 2


blocks = {}
for cell_key, pts in seeds.items():
    for i, (sx, sy) in enumerate(pts):
        xi, yi = int(max(0, min(W - 1, sx))), int(max(0, min(H - 1, sy)))
        near_shore = from_water[yi][xi] < 22
        angle = shore_angle(sx, sy) if near_shore else mid(sx, sy) * 3.0 + rnd.random() * 0.4
        angle += rnd.choice((0, 0, 0.12, -0.12))
        is_park = park_amount(sx, sy) > 0.35 and rnd.random() < 0.92
        old = rnd.random() < terracotta_share(sx, sy)
        blocks[(cell_key, i)] = {
            "angle": angle,
            "park": is_park,
            "old": old,
            "cw": rnd.choice((3, 3, 4)) if old else rnd.choice((4, 4, 5, 6)),
            "ch": rnd.choice((3, 4, 4)) if old else rnd.choice((4, 5, 6)),
            "seed": rnd.randrange(1 << 20),
        }

for y in range(H):
    for x in range(W):
        if water[y][x]:
            continue
        gx, gy = x // CELL, y // CELL
        best = second = (1e9, None)
        for cy in range(gy - 1, gy + 2):
            for cx in range(gx - 1, gx + 2):
                for i, (sx, sy) in enumerate(seeds.get((cx, cy), ())):
                    d = (x - sx) ** 2 + (y - sy) ** 2
                    if d < best[0]:
                        second, best = best, (d, ((cx, cy), i))
                    elif d < second[0]:
                        second = (d, ((cx, cy), i))
        d1, d2 = math.sqrt(best[0]), math.sqrt(second[0])
        block = blocks[best[1]]
        water_d = from_water[y][x]
        if water_d <= 1:
            px[x, y] = SAND if fine(x, y) > 0.4 else DIRT
        elif water_d == 2:
            px[x, y] = STONE_L if (x + y) % 2 else STONE
        elif water_d == 3:
            px[x, y] = STREET_L if (x // 3) % 2 else STREET
        elif d2 - d1 < 1.0 + (0.5 if block["old"] else 0.0):
            px[x, y] = STREET if (x + y) % 5 else STREET_L
        elif block["park"]:
            n = fine(x, y)
            c = PARK_L if n > 0.62 else PARK_G if n > 0.34 else PARK_D
            sx, sy = seeds[best[1][0]][best[1][1]]
            # a sand path winding through, and a pond in the middle of the bigger parks
            if abs(((x - sx) * 0.7 + (y - sy) * 0.7 + 4 * math.sin((y - sy) / 3.0)) % 14 - 7) < 0.7:
                c = SAND
            px[x, y] = c
        else:
            sx, sy = seeds[best[1][0]][best[1][1]]
            a = block["angle"]
            u = (x - sx) * math.cos(a) + (y - sy) * math.sin(a) + 100
            v = -(x - sx) * math.sin(a) + (y - sy) * math.cos(a) + 100
            cw, ch = block["cw"], block["ch"]
            ci, cj = int(u // cw), int(v // ch)
            h = (ci * 73856093 ^ cj * 19349663 ^ block["seed"]) & 0xFFFF
            pal = TERRACOTTA if block["old"] else (ROOF_BLUE if h % 11 == 0 else CONCRETE)
            roof = shade(pal[h % len(pal)], 0.92 + (h >> 4) % 17 / 100)
            iu, iv = u - ci * cw, v - cj * ch
            if iu >= cw - 1 or iv >= ch - 1:
                roof = shade(roof, 0.62)                    # the shadow side of the building
            elif iu < 1 and iv < 1:
                roof = shade(roof, 1.1)
            px[x, y] = roof

occ = [[False] * W for _ in range(H)]


def plaza(x0, y0, x1, y1, colour=PLAZA):
    """Clear a rectangle to bare ground (a landmark's grounds)."""
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if 0 <= x < W and 0 <= y < H and not water[y][x] and from_water[y][x] > 2:
                px[x, y] = colour if (x + y) % 9 else shade(colour, 0.94)


def disc_shaded(cx, cy, r, base, light, dark):
    """A dome seen from above and a little from the south: lit from the upper left."""
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            d = math.hypot(dx, dy)
            if d <= r + 0.2:
                t = (dx + dy) / (2 * r + 0.01)
                c = light if t < -0.25 else dark if t > 0.35 else base
                if d > r - 0.8 and t > 0.1:
                    c = shade(dark, 0.8)
                put(cx + dx, cy + dy, c)
    put(cx - r // 3, cy - r // 3, shade(light, 1.15))


LEAD = ((146, 156, 176), (196, 204, 220), (96, 108, 130))        # the grey blue of an old dome: base, light, dark
GOLD_C = (255, 214, 92)


def minaret(x, y, height):
    """A slender minaret: a white shaft with a balcony and a pointed grey cap, throwing a shadow to the right."""
    for k in range(height):
        put(x, y - k, (244, 240, 230))
        put(x + 1, y - k + 1, (150, 140, 130))
    for dx in (-1, 0, 1):
        put(x + dx, y - height * 2 // 3, (200, 194, 184))
    put(x, y - height, (92, 98, 112))
    put(x, y - height - 1, (92, 98, 112))
    put(x, y - height - 2, GOLD_C)


def mosque(cx, cy, scale=1.0, minarets=4, court=True):
    """A classical Ottoman mosque: a big central dome with half domes around it, corner domelets, a forecourt and minarets."""
    r = int(5 * scale)
    plaza(cx - r - 8, cy - r - 5, cx + r + 8, cy + r + (9 if court else 5))
    for dy in range(-r - 2, r + 3):
        for dx in range(-r - 2, r + 3):
            put(cx + dx, cy + dy, (226, 206, 176) if dx + dy < 0 else (190, 166, 134))
    for ox, oy in ((-r, 0), (r, 0), (0, -r), (0, r)):
        disc_shaded(cx + ox, cy + oy, max(2, r // 2 + 1), *LEAD)
    for ox, oy in ((-r - 1, -r - 1), (r + 1, -r - 1), (-r - 1, r + 1), (r + 1, r + 1)):
        disc_shaded(cx + ox, cy + oy, max(1, r // 4 + 1), *LEAD)
    disc_shaded(cx, cy, r, *LEAD)
    put(cx, cy - r - 1, GOLD_C)
    if court:
        for dy in range(r + 3, r + 9):
            for dx in range(-r - 2, r + 3):
                put(cx + dx, cy + dy, (214, 196, 160) if (dx + dy) % 5 else (180, 164, 132))
        for dx in (-r - 2, r + 2):
            for dy in range(r + 3, r + 9):
                put(cx + dx, cy + dy, (168, 144, 112))
    corners = [(-r - 3, -r - 2), (r + 3, -r - 2), (-r - 3, r + 2), (r + 3, r + 2), (-r - 3, r + 8), (r + 3, r + 8)]
    for mx, my in corners[:minarets]:
        minaret(cx + mx, cy + my, int(10 * scale) + 2)


def hagia_sophia(cx, cy):
    """Hagia Sophia: a huge central dome between two half domes, ochre buttressed walls, four minarets at the corners."""
    plaza(cx - 12, cy - 11, cx + 12, cy + 12, (206, 192, 160))
    for dy in range(-6, 7):
        for dx in range(-8, 9):
            put(cx + dx, cy + dy, (226, 178, 134) if dx + dy < 4 else (184, 134, 98))
    for dx in range(-8, 9, 4):
        for dy in (-7, 7):
            put(cx + dx, cy + dy, (150, 104, 76))
            put(cx + dx, cy + dy + (1 if dy > 0 else -1), (150, 104, 76))
    disc_shaded(cx - 6, cy, 3, *LEAD)
    disc_shaded(cx + 6, cy, 3, *LEAD)
    disc_shaded(cx, cy, 5, *LEAD)
    for ox, oy in ((-9, -7), (9, -7), (-9, 7), (9, 7)):
        minaret(cx + ox, cy + oy, 12)


def suleymaniye(cx, cy):
    """The Suleymaniye: a big dome and two half domes in a walled complex of domed courtyards, two tall and two short minarets."""
    plaza(cx - 18, cy - 12, cx + 18, cy + 14, (204, 190, 158))
    for x in range(cx - 17, cx + 18):
        for y in (cy - 11, cy + 13):
            put(x, y, (176, 150, 120))
    for y in range(cy - 11, cy + 14):
        for x in (cx - 17, cx + 17):
            put(x, y, (176, 150, 120))
    for k in range(-14, 15, 4):
        disc_shaded(cx + k, cy + 11, 1, *LEAD)
        disc_shaded(cx + k, cy - 9, 1, *LEAD)
    for dy in range(-6, 7):
        for dx in range(-7, 8):
            put(cx + dx, cy - 1 + dy, (228, 198, 160) if dx + dy < 3 else (190, 154, 118))
    disc_shaded(cx, cy - 7, 2, *LEAD)
    disc_shaded(cx, cy + 5, 2, *LEAD)
    disc_shaded(cx, cy - 1, 5, *LEAD)
    for ox, oy, h in ((-9, -6, 14), (9, -6, 14), (-9, 6, 11), (9, 6, 11)):
        minaret(cx + ox, cy + oy, h)


def topkapi(cx, cy):
    """Topkapi Palace: courtyards with walls, low pavilions with green lead roofs, gardens, and the tower over the gate."""
    plaza(cx - 16, cy - 9, cx + 16, cy + 9, (208, 194, 162))
    for x0, x1 in ((cx - 16, cx - 5), (cx - 5, cx + 5), (cx + 5, cx + 16)):
        for x in range(x0, x1 + 1):
            put(x, cy - 8, (170, 146, 116))
            put(x, cy + 8, (170, 146, 116))
        for y in range(cy - 8, cy + 9):
            put(x0, y, (170, 146, 116))
    for y in range(cy - 8, cy + 9):
        put(cx + 16, y, (170, 146, 116))
    # gardens
    for y in range(cy + 2, cy + 8):
        for x in range(cx + 6, cx + 15):
            put(x, y, PARK_G if (x + y) % 4 else PARK_L)
    for x0, y0, w, h in ((cx - 14, cy - 6, 6, 4), (cx - 3, cy - 6, 7, 5), (cx + 7, cy - 6, 6, 4), (cx - 13, cy + 2, 5, 4), (cx - 2, cy + 1, 5, 5)):
        for y in range(y0, y0 + h):
            for x in range(x0, x0 + w):
                put(x, y, (96, 144, 128) if x < x0 + w - 1 and y < y0 + h - 1 else (60, 100, 90))
    disc_shaded(cx + 8, cy - 4, 2, (170, 168, 150), (214, 212, 194), (110, 108, 96))
    for k in range(7):
        put(cx - 10, cy - 7 - k, (226, 214, 190))
        put(cx - 9, cy - 7 - k, (186, 170, 140))
    for dx in range(-2, 3):
        put(cx - 10 + dx, cy - 14, (96, 140, 124))
    put(cx - 10, cy - 16, GOLD_C)


def grand_bazaar(cx, cy):
    plaza(cx - 8, cy - 5, cx + 8, cy + 5, (190, 170, 140))
    for y in range(cy - 4, cy + 5):
        for x in range(cx - 7, cx + 8):
            put(x, y, (176, 152, 124))
    for dx in range(-6, 7, 3):
        for dy in range(-3, 5, 3):
            disc_shaded(cx + dx, cy + dy, 1, *LEAD)


def galata_tower(cx, base):
    """Galata Tower: a round stone tower on its hill with a ring of windows, a balcony and a grey conical cap."""
    plaza(cx - 8, base - 4, cx + 8, base + 5, (200, 184, 150))
    for k in range(0, 22):
        w = 3 if k < 15 else 4
        for dx in range(-w, w + 1):
            c = (234, 216, 180) if dx < 0 else (200, 178, 142) if dx < w - 1 else (140, 118, 96)
            put(cx + dx, base - k, c)
        if k % 5 == 2 and k < 14:
            put(cx - 1, base - k, (84, 68, 56))
            put(cx + 1, base - k, (84, 68, 56))
    for dx in range(-6, 7):
        put(cx + dx, base - 15, (110, 100, 94))
        put(cx + dx, base - 16, (170, 160, 150))
    for k in range(0, 11):
        for dx in range(-4 + k // 2, 5 - k // 2):
            put(cx + dx, base - 22 - k, (138, 146, 162) if dx < 1 else (92, 100, 118))
    put(cx, base - 33, GOLD_C)
    put(cx, base - 34, GOLD_C)


def maiden_tower():
    """The Maiden's Tower: a small white tower with a red dome on its own rock off the Asian shore."""
    cx, cy = int(KIZ[0]), int(KIZ[1])
    for dy in range(-1, 3):
        for dx in range(-5, 6):
            if abs(dx) + abs(dy) * 2 <= 6:
                put(cx + dx, cy + dy + 1, STONE if (dx + dy) % 2 else STONE_D)
    for dy in range(-7, 1):
        for dx in range(-2, 3):
            put(cx + dx, cy + dy, (246, 242, 232) if dx < 1 else (196, 192, 184))
    for dx in range(-3, 4):
        put(cx + dx, cy - 4, (150, 146, 140))
    for k in range(3):
        for dx in range(-2 + k, 3 - k):
            put(cx + dx, cy - 8 - k, (190, 74, 58))
    put(cx, cy - 12, GOLD_C)


def dolmabahce():
    """Dolmabahce Palace: a long white palace along the Bosphorus shore with a domed ceremonial hall and a garden."""
    x0, y0 = int(752 * MAP), int(8 * MAP)
    x1, y1 = int(776 * MAP), int(112 * MAP)
    for t in range(0, 101):
        x = x0 + (x1 - x0) * t // 100 - 8
        y = y0 + (y1 - y0) * t // 100
        for k in range(-2, 4):
            put(x + k, y, (244, 240, 232) if k < 2 else (190, 186, 178))
            put(x + k, y + 1, (244, 240, 232) if k < 2 else (190, 186, 178))
        if t % 14 == 6:
            put(x, y - 1, (190, 74, 58))
        for k in range(-6, -2):
            put(x + k, y, PARK_G if (x + y + k) % 3 else PARK_L)
    cx, cy = x0 + (x1 - x0) // 2 - 8, y0 + (y1 - y0) // 2
    disc_shaded(cx, cy - 1, 3, (226, 214, 196), (250, 246, 238), (168, 150, 132))
    put(cx, cy - 5, GOLD_C)


def haydarpasa(cx, cy):
    """Haydarpasa Station: a U shaped neo gothic building opening on the sea, four pointed corner towers, a long pier."""
    plaza(cx - 9, cy - 8, cx + 9, cy + 8, (200, 186, 156))
    for y in range(cy - 7, cy + 8):
        for x in range(cx - 4, cx + 9):
            if x >= cx + 3 or y < cy - 3 or y > cy + 3:
                put(x, y, (196, 184, 156) if (x + y) % 6 else (170, 158, 132))
    for x in range(cx - 4, cx + 9):
        for y in (cy - 7, cy + 7):
            put(x, y, (90, 100, 122))
    for tx, ty in ((cx - 4, cy - 7), (cx - 4, cy + 7), (cx + 8, cy - 7), (cx + 8, cy + 7)):
        for k in range(6):
            put(tx, ty - k, (214, 202, 176))
        for k in range(1, 4):
            for dx in range(-(3 - k), 4 - k):
                put(tx + dx, ty - 5 - k, (76, 92, 118))
        put(tx, ty - 9, GOLD_C)
    for dx in range(1, 14):
        put(cx - 5 - dx, cy, (170, 160, 150))
        put(cx - 5 - dx, cy + 1, (110, 104, 98))


def selimiye(cx, cy):
    """Selimiye Barracks: a huge pale yellow square building round a courtyard, with a tower at each corner."""
    plaza(cx - 11, cy - 11, cx + 11, cy + 11, (206, 192, 150))
    for y in range(cy - 10, cy + 11):
        for x in range(cx - 10, cx + 11):
            inner = abs(x - cx) < 7 and abs(y - cy) < 7
            put(x, y, (200, 184, 130) if inner else (240, 216, 140) if (x + y) % 7 else (206, 180, 104))
    for tx, ty in ((cx - 10, cy - 10), (cx + 10, cy - 10), (cx - 10, cy + 10), (cx + 10, cy + 10)):
        for dy in range(-3, 2):
            for dx in range(-2, 3):
                put(tx + dx, ty + dy, (252, 230, 160) if dx < 1 else (206, 180, 110))
        for k in range(3):
            for dx in range(-1 + k // 2, 2 - k // 2):
                put(tx + dx, ty - 4 - k, (196, 74, 58))


hagia_sophia(int(640 * MAP), int(418 * MAP))
mosque(int(552 * MAP), int(480 * MAP), 1.0, 6)                  # the Blue Mosque, six minarets
suleymaniye(int(392 * MAP), int(346 * MAP))
topkapi(int(704 * MAP), int(372 * MAP))
grand_bazaar(int(470 * MAP), int(420 * MAP))
mosque(int(1010 * MAP), int(176 * MAP), 0.7, 2, False)          # Yeni Valide, Uskudar
mosque(int(1128 * MAP), int(256 * MAP), 0.6, 2, False)          # Mihrimah Sultan
mosque(int(246 * MAP), int(318 * MAP), 0.7, 2, False)
selimiye(int(950 * MAP), int(452 * MAP))
haydarpasa(int(1010 * MAP), int(606 * MAP))
dolmabahce()
maiden_tower()
GALATA = (int(590 * MAP), int(268 * MAP))
galata_tower(GALATA[0], GALATA[1])

# the Galata Bridge across the Golden Horn's mouth: a roadway, a tram line, railings and the fishermen's rail
bx0, bx1 = int(545 * MAP), int(655 * MAP)
for x in range(bx0, bx1):
    t = (x - bx0) / (bx1 - bx0)
    y = int((338 - 14 * t) * MAP)
    if water[y][x] or water[y + 1][x] or water[y - 1][x]:
        for k in range(-3, 3):
            put(x, y + k, (96, 92, 96) if k in (-2, 1) else (128, 124, 128))
        put(x, y - 3, (230, 226, 218))
        put(x, y + 2, (230, 226, 218))
        if x % 4 == 0:
            put(x, y - 4, (252, 232, 160))
        if x % 12 == 0:
            for k in range(3, 7):
                put(x, y + k, (110, 104, 98))
# ferry piers along the shores
for cx, cy, dx, dy in ((int(700 * MAP), int(300 * MAP), 1, 0), (int(640 * MAP), int(520 * MAP), 0, 1), (int(1000 * MAP), int(300 * MAP), -1, 0),
                       (int(1030 * MAP), int(500 * MAP), -1, 0), (int(1060 * MAP), int(760 * MAP), -1, 0)):
    for k in range(10):
        x, y = cx + dx * k, cy + dy * k
        if 0 <= x < W and 0 <= y < H and water[y][x]:
            put(x, y, STONE_L)
            put(x + (1 if dy else 0), y + (1 if dx else 0), STONE_D)

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
