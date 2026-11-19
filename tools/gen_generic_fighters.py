"""Build eight unnamed campaign fighters from the game's original pixel drawing.

Copies Katmata's body pixels and uses his existing pose/arm construction. Replaces
the cap, shirt emblem and props with plain hair and clothing. No filtering or AI
resampling: the original 33x55 pixel anatomy lives in the same 84x63 frames.
Run: python tools/gen_generic_fighters.py
"""
import math
from pathlib import Path
from PIL import Image, ImageDraw
import gen_katmata as base

ROOT = Path(__file__).resolve().parent.parent
# Shirt, trousers, hair, skin; identifiers are asset filenames, never character names.
PALETTES = [
    ((57, 73, 112), (47, 55, 76), (70, 47, 35), (199, 171, 146)),
    ((46, 119, 116), (48, 49, 62), (45, 30, 27), (160, 114, 87)),
    ((169, 127, 61), (84, 67, 50), (73, 53, 39), (220, 180, 145)),
    ((109, 65, 110), (65, 72, 91), (45, 32, 42), (199, 171, 146)),
    ((179, 91, 54), (54, 72, 108), (93, 59, 39), (136, 91, 66)),
    ((219, 214, 190), (54, 78, 61), (57, 38, 26), (204, 153, 116)),
    ((123, 48, 61), (72, 73, 82), (46, 34, 30), (130, 89, 67)),
    ((71, 75, 70), (103, 111, 66), (109, 72, 41), (221, 186, 155)),
]


def shade(color, amount):
    return tuple(max(0, min(255, c + amount)) for c in color)


def body_source(index):
    shirt, pants, hair, skin = PALETTES[index]
    source = base.SRC.copy()
    for y in range(source.height):
        for x in range(source.width):
            r, g, b, a = source.getpixel((x, y))
            if not a:
                continue
            rgb = (r, g, b)
            if y < 7:
                # The original cap's pixel silhouette becomes a short haircut.
                rgb = shade(hair, (r + g + b) // 3 - 120)
            elif rgb in base.SKIN_SET:
                rgb = shade(skin, r - 199)
            elif y >= 34 and b > r + 15:
                rgb = shade(pants, r - 93)
            elif 16 <= y < 34 and (min(r, g, b) > 185 or (12 <= x <= 21 and 19 <= y <= 27)):
                rgb = shade(shirt, max(-25, (r + g + b) // 3 - 225))
            source.putpixel((x, y), (*rgb, a))
    draw = ImageDraw.Draw(source)
    # Discrete hair/clothing details; all drawn on the original pixel grid.
    if index in (1, 5):
        draw.rectangle((8, 3, 11, 7), fill=(*shade(hair, -12), 255))
        if index == 1:
            draw.rectangle((7, 7, 9, 17), fill=(*hair, 255))
    if index == 3:
        draw.rectangle((9, 6, 11, 16), fill=(*hair, 255))
        draw.rectangle((22, 6, 24, 16), fill=(*shade(hair, -10), 255))
    if index == 6:
        for y in range(7):
            for x in range(source.width):
                if source.getpixel((x, y))[3]:
                    source.putpixel((x, y), (*shade(skin, -18 + y * 2), 255))
    if index in (0, 5):
        draw.line((17, 18, 17, 32), fill=(*shade(shirt, 38), 255))
    if index == 7:
        draw.rectangle((23, 40, 26, 43), fill=(*shade(pants, -19), 255))
    return source


def configure(index):
    source = body_source(index)
    # Strip the skin arms using the original mask before recolouring them.
    body = source.copy()
    for arm in (base.BACK_ARM, base.FRONT_ARM):
        for x, y in arm:
            body.putpixel((x, y), (0, 0, 0, 0))
    base.BODY = body
    shirt, _, _, skin = PALETTES[index]
    base.SKIN, base.SKIN_SHADE, base.SKIN_LIGHT = skin, shade(skin, -30), shade(skin, 24)
    base.SLEEVE, base.SLEEVE_SHADE = shirt, shade(shirt, -25)
    return source


def pose(**kwargs):
    return base.Pose().body(**kwargs).arms((13, 23), (29, 21))


def kick(index, extended=False, low=False):
    p = pose(drop=base.CROUCH if low else (), up=(-2, 0))
    # Replace the front leg below the hip with a raised thigh and extending shin.
    d = ImageDraw.Draw(p.canvas)
    d.rectangle((base.OFF_X + 17, base.OFF_Y + 36, base.OFF_X + 32, 62), fill=(0, 0, 0, 0))
    hip = (base.OFF_X + 20, base.OFF_Y + 36)
    knee = (hip[0] + 10, hip[1] - (0 if low else 8))
    foot = (hip[0] + (33 if extended else 13), hip[1] + (11 if low else -9 if extended else 5))
    pants = PALETTES[index][1]
    base.line(p.canvas, hip, knee, shade(pants, -24), 9)
    base.line(p.canvas, knee, foot, shade(pants, -24), 8)
    base.line(p.canvas, hip, knee, pants, 7)
    base.line(p.canvas, knee, foot, pants, 6)
    base.line(p.canvas, (knee[0], knee[1] - 2), (foot[0], foot[1] - 2), shade(pants, 22), 1)
    # Copy the original boot pixels, preserving the game's leather highlights.
    boot = base.SRC.crop((20, 49, 32, 55))
    p.canvas.alpha_composite(boot, (foot[0] - 4, foot[1] - 2))
    return p


def frames(index):
    result = {'idle_0': pose(), 'idle_1': pose(up=(0, 1)), 'crouch': pose(drop=base.CROUCH)}
    for i in range(6):
        t = math.sin(i * math.tau / 6)
        result[f'walk_{i}'] = pose(up=(0, i % 2), boots=((round(t * 4), -int(t > 0)), (-round(t * 4), -int(t < 0))))
    for suffix, hands in [('up', ((8, 13), (28, 12))), ('top', ((4, 18), (32, 16))), ('fall', ((9, 12), (27, 11)))]:
        result[f'jump_{suffix}'] = pose().arms(*hands)
    for i in range(2):
        result[f'hurt_{i}'] = pose(up=(-2 - i, i)).face('hurt')
        for prefix in ('soft', 'crouch_soft', 'air_soft'):
            p = base.Pose().body(drop=base.CROUCH if prefix.startswith('crouch') else (), up=(i, 0))
            p.arms((13, 23), (45 if i else 28, 23 if prefix != 'crouch_soft' else 30), upper=11, fore=11)
            result[f'{prefix}_{i}'] = p
        result[f'crouch_hard_{i}'] = kick(index, bool(i), low=True)
        result[f'air_hard_{i}'] = kick(index, bool(i))
        result[f'speak_{i}'] = pose()
    for i in range(4):
        result[f'hard_{i}'] = kick(index, i in (1, 2))
    result['block'] = base.Pose().body().arms((20, 13), (24, 11), back_bend=1)
    result['ko'] = base.rotated(pose().face('closed'), 90)
    for i in range(6):
        result[f'summon_{i}'] = pose()  # Required base frames; no special move exists.
    result['roll_0'] = pose(drop=base.CROUCH)
    for i in range(1, 9):
        result[f'roll_{i}'] = base.ball(pose(drop=base.CROUCH), -45 * i)
    result['roll_9'] = pose(drop=base.CROUCH[:7])
    return {key: p.canvas for key, p in result.items()}


def character_data(index):
    color = ', '.join(f'{c / 255:.3f}' for c in PALETTES[index][0])
    moves = []
    for air, crouch, label in [(False, False, ''), (False, True, 'Low '), (True, False, 'Air ')]:
        for heavy in (False, True):
            name = label + ('Kick' if heavy else 'Punch')
            y, h = (0, 14) if crouch else ((-8, 32) if air else (18, 18))
            moves.append(f'''        (name: "{name}", button: {'Heavy' if heavy else 'Light'}, crouching: {str(crouch).lower()}, air: {str(air).lower()}, anim: {'Hard' if heavy else 'Soft'}, walk_pct: {100 if air else 0},
         startup: {10 if heavy else 5}, active: 4, recovery: {18 if heavy else 10}, damage: {44 if heavy else 26}, hitstun: {17 if heavy else 12}, blockstun: 8, knockback: {3 if heavy else 2}, hitstop: 4,
         hitbox: (x: 8, y: {y}, w: {38 if heavy else 28}, h: {h}))''')
    return f'''// Unnamed campaign opponent. Generated by tools/gen_generic_fighters.py.
(
    name: "",
    campaign_only: true,
    sprites: Some("generic_{index + 1:02}"),
    color: ({color}),
    walk_speed: 200,
    jump_speed: 1050,
    cpu_range: Some(42),
    meter_gain_pct: Some(0),
    blurbs: ["Punch.", "Kick.", ""],
    moves: [
{',\n'.join(moves)},
    ],
)
'''


def main():
    preview = Image.new('RGBA', (8 * 168, 3 * 150), (44, 47, 57, 255))
    for index in range(8):
        source = configure(index)
        drawings = frames(index)
        folder = ROOT / f'assets/sprites/generic_{index + 1:02}'
        folder.mkdir(parents=True, exist_ok=True)
        for name, img in drawings.items():
            assert img.size == (84, 63)
            img.save(folder / f'{name}.png')
        portrait = Image.new('RGBA', (40, 40), (44, 47, 57, 255))
        portrait.alpha_composite(source.crop((7, 0, 27, 20)).resize((40, 40), Image.Resampling.NEAREST))
        portrait.save(ROOT / f'assets/portraits/generic_{index + 1:02}.png')
        (ROOT / f'assets/characters/generic_{index + 1:02}.ron').write_text(character_data(index), encoding='utf-8')
        for row, name in enumerate(('idle_0', 'soft_1', 'hard_1')):
            preview.alpha_composite(drawings[name].resize((168, 126), Image.Resampling.NEAREST), (index * 168, row * 150 + 12))
    output = ROOT / 'docs/generic-fighters-preview.png'
    preview.save(output)
    print(f'8 fighters, {len(drawings)} frames each; preview: {output}')


if __name__ == '__main__':
    main()
