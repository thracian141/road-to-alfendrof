"""Baroness's mounted lancer, drawn at the roster's native pixel scale.

Eight poses at three game ticks each: reach, foreleg contact, support,
fold, gathered suspension, hindleg contact, push, extended suspension.
The drawing is exported at 85% size, with crisp nearest-neighbour pixels.
"""
from PIL import Image, ImageDraw

DRAW_SIZE = (120, 88)
SIZE = tuple(round(n * 0.85) for n in DRAW_SIZE)
FRAMES = 8
SILVER = (212, 216, 226)
MID = (160, 168, 184)
DARK = (98, 104, 122)
DEEP = (58, 60, 76)
COAT = (196, 194, 200)
SHADE = (146, 144, 154)
FAR = (116, 114, 124)
HOOF = (64, 52, 46)
RED = (150, 62, 50)
RED_DARK = (104, 38, 34)
RED_LIGHT = (188, 106, 88)
GOLD = (236, 191, 58)
GOLD_DARK = (189, 149, 33)

# Joint coordinates are plotted independently; planted hooves stay on row 85.
# Hindlegs: stifle, hock, hoof. Forelegs: knee, fetlock, hoof.
HIND = (
    ((37, 66), (24, 76), (14, 84)),
    ((39, 64), (25, 70), (20, 77)),
    ((44, 65), (37, 72), (42, 77)),
    ((46, 66), (45, 75), (52, 82)),
    ((43, 68), (45, 78), (48, 85)),
    ((39, 69), (34, 77), (32, 85)),
    ((35, 68), (26, 77), (22, 85)),
    ((32, 65), (20, 74), (12, 80)),
)
FORE = (
    ((78, 68), (88, 78), (94, 83)),
    ((77, 69), (80, 80), (83, 85)),
    ((68, 70), (66, 81), (68, 85)),
    ((61, 68), (56, 78), (53, 84)),
    ((59, 64), (65, 70), (62, 75)),
    ((64, 63), (73, 67), (68, 72)),
    ((74, 63), (78, 69), (74, 76)),
    ((80, 65), (87, 73), (91, 79)),
)


def knight(k):
    k %= FRAMES
    img = Image.new('RGBA', DRAW_SIZE)
    d = ImageDraw.Draw(img)
    bob = (0, 1, 2, 1, -1, 0, -1, -2)[k]
    wave = (0, 1, 2, 1, 0, -1, -2, -1)[k]

    def poly(points, color):
        d.polygon([(x, y + bob) for x, y in points], fill=color)

    def line(points, color, width=1):
        d.line([(x, y + bob) for x, y in points], fill=color, width=width)

    def ellipse(box, color):
        x0, y0, x1, y1 = box
        d.ellipse((x0, y0 + bob, x1, y1 + bob), fill=color)

    def leg(hind, far):
        phase = (k + (1 if far else 0)) % FRAMES
        joints = (HIND if hind else FORE)[phase]
        dx = -4 if far else 0
        hip = (36 if hind else 69, (56 if hind else 55) + bob)
        points = [(hip[0] + dx, hip[1])] + [(x + dx, y) for x, y in joints]
        tone, shadow = (FAR, DARK) if far else (COAT, SHADE)
        for i, width in enumerate((6, 4, 2)):
            d.line(points[i:i + 2], fill=shadow, width=width + 1)
            d.line(points[i:i + 2], fill=tone, width=width)
        x, y = points[1]
        d.ellipse((x - 2, y - 2, x + 2, y + 2), fill=tone)
        x, y = points[-1]
        d.polygon([(x-2, y-2), (x+1, y-2), (x+3, y), (x-2, y)], fill=HOOF)
        if not far:
            d.point((x, y-2), fill=SHADE)

    # Flowing tail and far limbs sit behind the barrel.
    poly([(29, 46), (19, 46), (11, 42+wave), (3, 43+wave),
          (10, 46+wave), (5, 48+wave), (17, 50+wave), (28, 52)], DEEP)
    line([(28, 47), (18, 48), (9, 44+wave)], SHADE, 2)
    leg(True, True)
    leg(False, True)

    # Rounded hindquarters, barrel, and muscular shoulder.
    ellipse((25, 43, 55, 63), SHADE)
    ellipse((37, 43, 76, 62), COAT)
    ellipse((62, 43, 77, 62), SHADE)
    leg(True, False)
    leg(False, False)

    # Red caparison wraps the rounded body, with a scalloped gold hem.
    poly([(27, 45), (35, 42), (61, 42), (72, 47), (73, 60),
          (67, 64), (57, 62), (47, 65), (36, 63), (27, 65), (25, 56)], RED_DARK)
    poly([(28, 46), (36, 44), (61, 44), (70, 48), (69, 60),
          (59, 59), (48, 62), (37, 60), (28, 62)], RED)
    line([(29, 47), (37, 45), (61, 45), (68, 48)], RED_LIGHT)
    for x in (32, 43, 57, 66):
        line([(x, 49), (x-1, 56), (x-2, 60)], RED_DARK)
    line([(27, 64), (36, 62), (47, 64), (57, 61), (67, 63), (72, 60)], GOLD, 2)
    for x, y in ((33, 55), (58, 54), (66, 53)):
        poly([(x, y-2), (x+2, y), (x, y+2), (x-2, y)], GOLD)
        d.point((x, y+bob), fill=GOLD_DARK)

    # Forward-sloping neck; a long horse muzzle, ears and dark mane.
    poly([(63, 46), (70, 36), (77, 31), (82, 34), (82, 43),
          (76, 56), (70, 60), (66, 55)], SHADE)
    poly([(66, 45), (74, 35), (79, 34), (79, 43), (74, 54), (70, 56)], COAT)
    poly([(67, 42), (70, 35), (75, 31), (79, 31), (76, 35),
          (73, 39), (71, 44), (68, 47)], DEEP)
    line([(70, 40), (74, 35), (77, 33)], DARK)
    poly([(76, 34), (76, 28), (79, 30), (81, 35)], SHADE)
    poly([(81, 34), (82, 29), (84, 32), (84, 36)], COAT)
    poly([(77, 34), (84, 34), (88, 38), (97, 44), (97, 48),
          (94, 51), (88, 48), (83, 43), (78, 43), (75, 39)], COAT)
    poly([(84, 42), (90, 46), (96, 46), (96, 49), (94, 50), (88, 47)], SHADE)
    line([(78, 35), (84, 36), (93, 44)], SILVER, 2)
    line([(81, 37), (85, 39)], DEEP)
    d.point((95, 46+bob), fill=HOOF)
    line([(88, 42), (88, 46), (92, 49)], RED_DARK)
    line([(78, 40), (84, 44), (89, 45)], GOLD_DARK)
    # Chest cloth and reins back to the rider's hand.
    line([(66, 48), (72, 53), (78, 48)], RED_DARK, 3)
    line([(66, 48), (72, 53), (78, 48)], GOLD)
    line([(88, 45), (74, 46), (57, 35)], HOOF)

    # Saddle and rider: articulated plate, bent thigh and a boot in the stirrup.
    poly([(39, 40), (56, 39), (62, 43), (58, 47), (40, 47), (36, 44)], HOOF)
    line([(39, 41), (55, 41), (59, 43)], GOLD_DARK)
    poly([(42, 38), (50, 38), (59, 47), (57, 52), (51, 52), (46, 46), (41, 44)], DARK)
    poly([(44, 39), (49, 40), (56, 47), (53, 49), (47, 44)], SILVER)
    ellipse((52, 47, 59, 53), MID)
    poly([(53, 52), (58, 52), (55, 60), (56, 62), (62, 62),
          (62, 65), (51, 65), (50, 61)], DEEP)
    line([(54, 53), (53, 60)], SILVER, 2)
    line([(50, 62), (49, 66), (59, 66), (60, 64)], GOLD_DARK)
    poly([(43, 19), (52, 20), (56, 28), (53, 36), (52, 41),
          (41, 41), (39, 35), (39, 26)], DARK)
    poly([(44, 20), (51, 22), (53, 28), (50, 34), (41, 34), (40, 27)], MID)
    line([(44, 22), (42, 27), (43, 32)], SILVER, 2)
    line([(41, 35), (51, 35)], DEEP)
    line([(41, 38), (51, 38)], SILVER)
    line([(40, 41), (52, 41)], RED_DARK, 2)
    # Helmet silhouette and narrow visor; plume follows the stride.
    poly([(44, 7), (51, 7), (55, 11), (55, 18), (52, 22),
          (44, 21), (41, 17), (41, 11)], DARK)
    poly([(44, 9), (50, 8), (53, 11), (52, 18), (46, 20), (43, 16), (43, 11)], MID)
    line([(45, 10), (44, 15), (46, 18)], SILVER, 2)
    poly([(48, 13), (56, 13), (55, 15), (48, 15)], DEEP)
    line([(49, 17), (54, 17)], SILVER)
    d.point((52, 19+bob), fill=DEEP)
    poly([(48, 8), (48, 4), (43, 3), (37, 5), (31, 7+wave),
          (24, 7+wave), (30, 11+wave), (39, 8), (44, 8)], RED_DARK)
    line([(46, 5), (40, 5), (33, 8+wave), (28, 8+wave)], RED_LIGHT, 2)
    line([(47, 6), (48, 9)], GOLD)
    # Aim down toward a standing fighter from the taller saddle.
    line([(31, 30), (110, 39)], (140, 106, 64), 2)
    line([(31, 29), (110, 38)], (196, 160, 104))
    poly([(107, 36), (117, 39), (108, 41)], DARK)
    line([(108, 37), (117, 39)], SILVER)
    poly([(99, 38), (99, 44), (92, 42+wave), (85, 44+wave), (89, 39+wave), (85, 37)], RED)
    line([(99, 44), (92, 42+wave), (85, 44+wave)], GOLD_DARK)
    poly([(63, 30), (61, 37), (65, 36), (65, 31)], DARK)
    line([(64, 31), (63, 35)], SILVER)
    ellipse((48, 22, 55, 29), SILVER)
    line([(52, 27), (54, 33), (60, 32)], DARK, 5)
    line([(51, 27), (54, 31), (59, 31)], MID, 3)
    ellipse((58, 30, 61, 33), SILVER)
    return img.resize(SIZE, Image.Resampling.NEAREST)
