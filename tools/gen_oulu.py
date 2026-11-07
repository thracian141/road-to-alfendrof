"""Generate the Oulu City Council stage art: the pixel-art backdrop from a photo/painting, the snow floor tile and the
footprint a fighter leaves in the snow.

Requires Python 3 with Pillow:  python tools/gen_oulu.py [picture.png]      (default: tools/oulu_photo.png)
"""
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets/backgrounds/oulu"
OUT.mkdir(parents=True, exist_ok=True)

photo = Image.open(sys.argv[1] if len(sys.argv) > 1 else ROOT / "tools/oulu_photo.png").convert("RGB")

# the backdrop: reduced to 640 px wide and 96 colours, the same treatment as the other photographic stages
size = (640, round(640 * photo.height / photo.width))
backdrop = photo.resize(size, Image.Resampling.BOX).quantize(colors=96).convert("RGB")
backdrop.save(OUT / "near.png")

# the floor is sunlit snow; its top edge takes the shadowed colour along the bottom of the picture, so the two meet softly
edge_pixels = sorted(backdrop.crop((0, size[1] - 6, size[0], size[1])).getdata(), key=sum)
edge = edge_pixels[len(edge_pixels) // 2]
snow = (222, 232, 245)
print("edge colour", edge, "snow colour", snow)


def shade(colour, factor):
    return tuple(max(0, min(255, round(c * factor))) for c in colour)


def mix(a, b, amount):
    return tuple(round(x + (y - x) * amount) for x, y in zip(a, b))


SHADOW = (168, 186, 216)  # the cold blue of snow in shade

# the floor tile: 32 x 40, a shadowed lip, a lit surface, then deeper and bluer snow; a few drifts and sparkles
# (nothing touches the sides, so it tiles)
rng = random.Random(7)
tile = Image.new("RGBA", (32, 40), snow + (255,))
pixels = tile.load()
for y in range(40):
    for x in range(32):
        if y == 0:
            colour = mix(edge, snow, 0.45)
        elif y < 3:
            colour = shade(snow, 1.07)
        elif y < 8:
            colour = mix(snow, SHADOW, 0.10 + 0.04 * (y - 3))
        else:
            colour = mix(snow, SHADOW, 0.35 + 0.35 * (y - 8) / 32)
        pixels[x, y] = colour + (255,)
for _ in range(26):
    pixels[rng.randrange(32), rng.randrange(8, 40)] = mix(snow, SHADOW, 0.75) + (255,)
for _ in range(9):
    pixels[rng.randrange(32), rng.randrange(3, 22)] = (255, 255, 255, 255)
for x in range(32):
    if (x * 7 + 3) % 11 < 3:
        pixels[x, 3] = mix(snow, SHADOW, 0.05) + (255,)
tile.save(OUT / "floor.png")

# the footprint: a dent in the snow with a shaded far side and a lit near rim (10 x 4)
print_img = Image.new("RGBA", (10, 4), (0, 0, 0, 0))
draw = ImageDraw.Draw(print_img)
draw.ellipse((0, 0, 9, 3), fill=mix(snow, SHADOW, 0.6) + (130,))
draw.ellipse((0, 0, 8, 2), fill=mix(snow, SHADOW, 1.0) + (215,))
for x in range(2, 9):
    print_img.putpixel((x, 3), (255, 255, 255, 190))
print_img.save(OUT / "footprint.png")
print("wrote", OUT)
