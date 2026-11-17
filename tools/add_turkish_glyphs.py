"""Adds the Turkish letters Silkscreen lacks to assets/fonts/silkscreen.ttf: S and s with a cedilla, G and g with a breve, I with a
dot, and the dotless i. Needs fontTools:  pip install fonttools
    python tools/add_turkish_glyphs.py
then `python tools/italic_font.py` for the italic copy. Safe to run again. Silkscreen's capitals and small letters are the same
shapes, and a pixel is 125 units, so each mark is drawn on that grid."""
import copy
import pathlib

from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import GlyphComponent

PX = 125
path = pathlib.Path(__file__).resolve().parent.parent / "assets" / "fonts" / "silkscreen.ttf"
font = TTFont(path)
glyf, hmtx, order = font["glyf"], font["hmtx"], font.getGlyphOrder()


def pixels(cells):
    """A glyph made of pixels, each `(column, row)` from the origin."""
    pen = TTGlyphPen(None)
    for x, y in cells:
        x0, y0 = x * PX, y * PX
        pen.moveTo((x0, y0))
        pen.lineTo((x0, y0 + PX))
        pen.lineTo((x0 + PX, y0 + PX))
        pen.lineTo((x0 + PX, y0))
        pen.closePath()
    return pen.glyph()


def composite(base, mark):
    glyph = TTGlyphPen(None).glyph()
    glyph.numberOfContours = -1
    glyph.components = []
    for name in (base, mark):
        part = GlyphComponent()
        part.glyphName, part.x, part.y, part.flags = name, 0, 0, 0x4 | 0x2 | 0x1 | 0x200 * (name == base)
        glyph.components.append(part)
    return glyph


def add(name, glyph, advance, lsb, code=None):
    if name in glyf.keys():
        return
    order.append(name)
    glyf[name] = glyph
    hmtx[name] = (advance, lsb)
    if code is not None:
        for table in font["cmap"].tables:
            if table.isUnicode():
                table.cmap[code] = name


# marks, over the letter: a breve (a small cup) and a dot, one pixel above the capitals
add("uni0306", pixels([(1, 7), (4, 7), (2, 6), (3, 6)]), 0, 125)
add("uni0307", pixels([(1, 6)]), 0, 125)
add("Gbreve", composite("G", "uni0306"), 750, 125, 0x11E)
add("gbreve", composite("g", "uni0306"), 750, 125, 0x11F)
add("Scedilla", composite("S", "uni0327"), 750, 125, 0x15E)
add("scedilla", composite("s", "uni0327"), 750, 125, 0x15F)
add("Idotaccent", composite("I", "uni0307"), 375, 125, 0x130)
add("dotlessi", copy.deepcopy(glyf["i"]), 375, 125, 0x131)
font.setGlyphOrder(order)
for name in glyf.keys():
    glyf[name].recalcBounds(glyf)
font.save(path)
print("wrote", path)
