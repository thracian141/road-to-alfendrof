"""Scales the campaign map (assets/campaign_maps/campaign_map1_istanbul.png, 1642 x 958) to the size it is shown at in the
default window, 3 screen pixels a map unit (384 x 224 units), so it is not blurred by the game scaling it down.
    python tools/bake_city_map.py"""
from pathlib import Path

from PIL import Image

root = Path(__file__).resolve().parent.parent / "assets"
src = Image.open(root / "campaign_maps/campaign_map1_istanbul.png").convert("RGB")
src.resize((1152, 672), Image.LANCZOS).save(root / "ui/campaign/the_city.png", optimize=True)
print("wrote", root / "ui/campaign/the_city.png")
