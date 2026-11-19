"""Copies the native pixel-art map to the legacy UI asset path without resampling.
    python tools/bake_city_map.py"""
from pathlib import Path
from shutil import copyfile

root = Path(__file__).resolve().parent.parent / "assets"
copyfile(root / "campaign_maps/campaign_map1_istanbul.png", root / "ui/campaign/the_city.png")
print("wrote", root / "ui/campaign/the_city.png")
