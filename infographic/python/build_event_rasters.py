"""
Bake per-event compound-extreme footprint fields into transparent filled-contour
PNGs that the infographic overlays on its map when an event is hovered.

Input:
    infographic/uploads/most_extreme_blobs.nc
        mask(blobs, lat, lon)  -- 1 deg grid, integer 0..~9 = number of months
        each cell spent in the compound extreme during that event; 0 = not part
        of the event.

Output (written to infographic/annual/events/):
    <key>.png   -- one per event key (blob -> key map below)
And merges an "events" block into infographic/annual/manifest.json (which must
already exist, produced by build_annual_rasters.py).

Geometry + palette are kept identical to build_annual_rasters.py so the event
footprints align pixel-for-pixel with the map and read against the SAME legend.
"""

import json
import os

import numpy as np
import xarray as xr
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm

# --- geometry / framing (MUST match build_annual_rasters.py) --------------------
ROTATE = 150
LAT_MIN, LAT_MAX = -85, 80

# --- discrete contourf levels + palette (MUST match the annual legend) ----------
LEVELS = [0, 1, 2, 4, 8, 16, 32]
COLORS = ["#fce8c8", "#f6c886", "#eda44e", "#e07b2e", "#c8531f", "#a5281a", "#6b1710"]

# --- blob-name -> event key (matches EVENTS in ocean-map-helpers.js) ------------
BLOB_KEY = {
    "SE Asia (1998)": "seasia",
    "Mediterranean Sea (2003)": "med",
    "Western Australia (2011)": "waus",
    "The Blob (2015)": "blob",
    "South Pacific (2015)": "spac",
    "Madagascar (1987)": "mad",
    "Barrier Reef (2022)": "gbr",
    "North Atlantic (2023)": "natl",
    "Central Atlantic (2023)": "catl",
}

HERE = os.path.dirname(os.path.abspath(__file__))
NC_PATH = os.path.join(HERE, "..", "uploads", "most_extreme_blobs.nc")
ANNUAL_DIR = os.path.join(HERE, "..", "annual")
OUT_DIR = os.path.join(ANNUAL_DIR, "events")
MANIFEST_PATH = os.path.join(ANNUAL_DIR, "manifest.json")

DPI = 100
FIG_W = 14.40
FIG_H = FIG_W * (LAT_MAX - LAT_MIN) / 360.0


def _rolled(field2d, lon):
    """Reorder columns so rotated longitude is monotonic increasing over [-180, 180]."""
    rot = ((lon + ROTATE + 180) % 360) - 180
    order = np.argsort(rot)
    return field2d[:, order], rot[order]


def _save_contourf(field2d, lon_sorted, lat, path):
    """Render one footprint to a tight, transparent, axis-free equirectangular PNG."""
    cmap = ListedColormap(COLORS[: len(LEVELS) - 1])
    cmap.set_over(COLORS[len(LEVELS) - 1])
    norm = BoundaryNorm(LEVELS, cmap.N)

    fig = plt.figure(figsize=(FIG_W, FIG_H), dpi=DPI)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_axis_off()
    # NaNs (mask==0) are not drawn -> transparent ocean outside the footprint.
    ax.contourf(lon_sorted, lat, field2d, levels=LEVELS, cmap=cmap, norm=norm, extend="max")
    ax.set_xlim(-180, 180)
    ax.set_ylim(LAT_MIN, LAT_MAX)
    fig.savefig(path, transparent=True, dpi=DPI)
    plt.close(fig)


def build():
    if not os.path.exists(MANIFEST_PATH):
        raise SystemExit(
            f"{MANIFEST_PATH} not found — run build_annual_rasters.py first "
            "(it writes the base manifest this script merges into)."
        )
    os.makedirs(OUT_DIR, exist_ok=True)

    ds = xr.open_dataset(NC_PATH)
    da = ds["mask"].sel(lat=slice(LAT_MIN, LAT_MAX))
    lat = da["lat"].to_numpy()
    lon = da["lon"].to_numpy()

    events = {}
    for name in [str(b) for b in da["blobs"].to_numpy()]:
        if name not in BLOB_KEY:
            raise SystemExit(f"blob '{name}' has no event key in BLOB_KEY — update the map.")
        key = BLOB_KEY[name]
        field = da.sel(blobs=name).to_numpy().astype(float)
        field[field == 0] = np.nan          # outside footprint -> transparent
        rolled, lon_sorted = _rolled(field, lon)
        _save_contourf(rolled, lon_sorted, lat, os.path.join(OUT_DIR, f"{key}.png"))
        events[key] = f"events/{key}.png"
        print(f"events/{key}.png  ({name})")

    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)
    manifest["events"] = events
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"merged events block ({len(events)} keys) into manifest.json")


if __name__ == "__main__":
    build()
