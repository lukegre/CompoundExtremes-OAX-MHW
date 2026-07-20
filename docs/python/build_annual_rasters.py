"""
Bake the per-year (and total) "number of compound extremes" fields into transparent
filled-contour PNGs that the HTML infographic overlays directly on its map.

Input:
    infographic/uploads/n_extremes_annual.nc
        n_extremes(year, lat, lon)  -- 0.25 deg grid, values ~0..11 per year,
        land encoded as 0 (no NaNs).

Output (written to infographic/annual/):
    total.png                 -- sum over all years  (default map background)
    year_1982.png .. year_2024.png
    region_high.png           -- high-count cells only (spotlight: low-mid latitudes)
    region_low.png            -- low-count cells only  (spotlight: high latitudes)
    manifest.json             -- levels, colors, labels, years, geometry

Why these choices (see docs/superpowers/specs/2026-07-06-annual-extremes-raster-hover-design.md):
  * contourf gives smooth filled-contour edges; saving transparent PNGs lets the map
    overlay them as a single <image> under equirectangular (== PlateCarree, linear lon/lat)
    with NO runtime reprojection.
  * Longitude is pre-rolled by ROTATE so the PNG's x-axis already matches the map's
    Pacific-centered framing (d3 rotate([ROTATE,0])), and the antimeridian seam lands at
    the map's outer edge.
  * Latitude is cropped to the map's visible frame [LAT_MIN, LAT_MAX].
"""

import json
import os

import numpy as np
import xarray as xr
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm

# --- geometry / framing (must match ocean-map-helpers.js ROTATE and draw.js FRAME_LAT_*) ---
ROTATE = 150            # degrees; d3 rotate([ROTATE, 0])
LAT_MIN, LAT_MAX = -85, 80

# --- discrete contourf levels + palette (must match the legend in the .dc.html) ------------
# 7 bins:  [0,1) [1,2) [2,4) [4,8) [8,16) [16,32) [32,inf)
LEVELS = [0, 1, 2, 4, 8, 16, 32]
COLORS = ["#fce8c8", "#f6c886", "#eda44e", "#e07b2e", "#c8531f", "#a5281a", "#6b1710"]
LABELS = ["0-1", "1-2", "2-4", "4-8", "8-16", "16-32", ">32"]

# --- spotlight regions (for the "More common than chance" panel hover) ---------------------
# Both are DATA-DRIVEN point sets over the summed field (extreme-months, 1982-2024):
#   region_high = cells with total >= REGION_HIGH_MIN   (the frequent, low-mid latitude hot band), warm.
#   region_low  = cells with total <  REGION_LOW_MAX    (the rare, "less than chance" cells), blue + HATCHED
#                 so the highlighted points read clearly over the dimming wash.
REGION_HIGH_MIN = 4       # extreme-months; cells at/above this are highlighted as "frequent"
REGION_LOW_MAX = 1        # extreme-months; cells below this are highlighted as "rare / < 1"
REGION_LOW_FILL = (0.231, 0.435, 0.627, 0.22)   # #3b6fa0 @ 0.22 alpha (faint blue wash inside the region)
REGION_LOW_HATCH_COLOR = "#1f4f7a"              # darker blue hatch lines
REGION_LOW_HATCH = "///"

HERE = os.path.dirname(os.path.abspath(__file__))
NC_PATH = os.path.join(HERE, "..", "uploads", "n_extremes_annual.nc")
OUT_DIR = os.path.join(HERE, "..", "annual")

# Output raster resolution. Native lon is 1440 px wide; keep it crisp.
DPI = 100
FIG_W = 14.40           # inches  -> 1440 px wide at DPI=100
FIG_H = FIG_W * (LAT_MAX - LAT_MIN) / 360.0   # keep 1 deg lon == 1 deg lat


def _rolled(field2d, lon):
    """Reorder columns so rotated longitude is monotonic increasing over [-180, 180]."""
    rot = ((lon + ROTATE + 180) % 360) - 180
    order = np.argsort(rot)
    return field2d[:, order], rot[order]


def _save_contourf(field2d, lon_sorted, lat, levels, colors, path, extend="max"):
    """Render one field to a tight, transparent, axis-free equirectangular PNG."""
    cmap = ListedColormap(colors[: len(levels) - 1])
    if extend == "max":
        cmap.set_over(colors[len(levels) - 1])
    norm = BoundaryNorm(levels, cmap.N)

    fig = plt.figure(figsize=(FIG_W, FIG_H), dpi=DPI)
    ax = fig.add_axes([0, 0, 1, 1])   # fill the whole figure, no margins
    ax.set_axis_off()
    ax.contourf(lon_sorted, lat, field2d, levels=levels, cmap=cmap, norm=norm, extend=extend)
    ax.set_xlim(-180, 180)
    ax.set_ylim(LAT_MIN, LAT_MAX)     # lat increases upward -> north at top
    fig.savefig(path, transparent=True, dpi=DPI)
    plt.close(fig)


def _save_hatched(mask_field, lon_sorted, lat, path, fill_rgba, hatch_color, hatch):
    """Render a single masked region (value 1 inside, NaN outside) as a faint fill + hatch pattern.

    Used for the spotlight highlight so the selected cells read clearly (colour + texture) over the
    dimming wash. `mask_field` is 1.0 inside the region and NaN elsewhere.
    """
    plt.rcParams["hatch.color"] = hatch_color
    plt.rcParams["hatch.linewidth"] = 0.7
    fig = plt.figure(figsize=(FIG_W, FIG_H), dpi=DPI)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_axis_off()
    ax.contourf(lon_sorted, lat, mask_field, levels=[0.5, 1.5], colors=[fill_rgba],
                hatches=[hatch], extend="neither")
    ax.set_xlim(-180, 180)
    ax.set_ylim(LAT_MIN, LAT_MAX)
    fig.savefig(path, transparent=True, dpi=DPI)
    plt.close(fig)


def build():
    os.makedirs(OUT_DIR, exist_ok=True)
    ds = xr.open_dataset(NC_PATH, use_cftime=True)
    da = ds["n_extremes"]

    # crop to the visible map frame in latitude
    da = da.sel(lat=slice(LAT_MIN, LAT_MAX))
    lat = da["lat"].to_numpy()
    lon = da["lon"].to_numpy()
    years = [int(y) for y in da["year"].to_numpy()]

    def bake(field2d, name, levels=LEVELS, colors=COLORS, extend="max"):
        rolled, lon_sorted = _rolled(np.asarray(field2d, dtype=float), lon)
        _save_contourf(rolled, lon_sorted, lat, levels, colors, os.path.join(OUT_DIR, name), extend)

    # total (default background)
    total = da.sum("year").to_numpy()
    bake(total, "total.png")
    print(f"total.png  (sum range {total.min():.1f}..{total.max():.1f})")

    # per year
    vals = da.to_numpy()
    for i, yr in enumerate(years):
        bake(vals[i], f"year_{yr}.png")
    print(f"{len(years)} per-year PNGs ({years[0]}..{years[-1]})")

    # spotlight region images (only the highlighted cells drawn; rest transparent)
    # region_high: the frequent, low-mid latitude hot band, data-driven (warm tones).
    high = np.where(total >= REGION_HIGH_MIN, total, np.nan)
    bake(high, "region_high.png", levels=[REGION_HIGH_MIN, 8, 16, 32],
         colors=COLORS[3:], extend="max")
    # region_low: the rare cells (total < 1), highlighted with a faint blue fill + hatching so the
    # actual highlighted points are obvious (data-driven, not a latitude band).
    low = np.where(total < REGION_LOW_MAX, 1.0, np.nan)
    lon_low_rolled, lon_low_sorted = _rolled(low, lon)
    _save_hatched(lon_low_rolled, lon_low_sorted, lat, os.path.join(OUT_DIR, "region_low.png"),
                  REGION_LOW_FILL, REGION_LOW_HATCH_COLOR, REGION_LOW_HATCH)
    print("region_high.png + region_low.png")

    manifest = {
        "levels": LEVELS,
        "colors": COLORS,
        "labels": LABELS,
        "years": years,
        "rotate": ROTATE,
        "latMin": LAT_MIN, "latMax": LAT_MAX,
        "lonMin": -180, "lonMax": 180,
        "total": "total.png",
        "yearFmt": "year_{year}.png",
        "regionHigh": "region_high.png",
        "regionLow": "region_low.png",
        "unit": "extreme-months",
    }
    with open(os.path.join(OUT_DIR, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    print("manifest.json")


if __name__ == "__main__":
    build()
