"""Bake the three 2015 definition-hover fields for the interactive infographic map.

Input:
    uploads/num_extremes_2015.nc
        mhw_months(lat, lon)
        oax_months(lat, lon)
        cex_months(lat, lon)

Output:
    assets/img/definition_2015/mhw.png
    assets/img/definition_2015/oax.png
    assets/img/definition_2015/cex.png
    assets/img/definition_2015/manifest.json

The geometry intentionally matches ``build_annual_rasters.py`` and
``ocean-map-draw.js``: a Pacific-centred, equirectangular field cropped to
[-85, 80] latitude. The HTML can therefore swap these transparent images into
the existing map without doing contouring or reprojection in the browser.
"""

import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap
import numpy as np
import xarray as xr


ROTATE = 150
LAT_MIN, LAT_MAX = -85, 80
LEVELS = [0, 1, 2, 4, 8, 16, 32]
LABELS = ["0-1", "1-2", "2-4", "4-8", "8-16", "16-32", ">32"]
OUTLINE_COLOR = "#12222c"
COMPOUND_COLORS = ["#fce8c8", "#f6c886", "#eda44e", "#e07b2e", "#c8531f", "#a5281a", "#6b1710"]

# Each palette follows the colour assigned to that definition in the poster.
FIELDS = {
    "mhw": {
        "variable": "mhw_months",
        "file": "mhw.png",
        "label": "Marine heatwave",
        "shortLabel": "MHW",
        "colors": ["#fbe9e4", "#f5c9bc", "#eba58f", "#df7a5e", "#c94b2a", "#98321f", "#6b1710"],
    },
    "oax": {
        "variable": "oax_months",
        "file": "oax.png",
        "label": "Ocean acidification extreme",
        "shortLabel": "OAX",
        "colors": ["#e4f2f3", "#c4e2e5", "#99ccd1", "#62b1b8", "#1f9aa6", "#177f8a", "#0b4650"],
    },
    "cex": {
        "variable": "cex_months",
        "file": "cex.png",
        "label": "Compound extreme",
        "shortLabel": "OAX ∩ MHW",
        # Match the warm compound palette used by the main map and other widgets.
        "colors": COMPOUND_COLORS,
    },
}

HERE = os.path.dirname(os.path.abspath(__file__))
NC_PATH = os.path.join(HERE, "..", "uploads", "num_extremes_2015.nc")
OUT_DIR = os.path.join(HERE, "..", "assets", "img", "definition_2015")

DPI = 100
FIG_W = 14.40
FIG_H = FIG_W * (LAT_MAX - LAT_MIN) / 360.0


def _rolled(field2d, lon):
    """Reorder columns to match d3.geoEquirectangular().rotate([150, 0])."""
    rotated_lon = ((lon + ROTATE + 180) % 360) - 180
    order = np.argsort(rotated_lon)
    return field2d[:, order], rotated_lon[order]


def _save_field(field2d, lon_sorted, lat, colors, path):
    """Render a transparent filled contour plus a quiet outline of non-zero cells."""
    cmap = ListedColormap(colors[:-1])
    cmap.set_over(colors[-1])
    norm = BoundaryNorm(LEVELS, cmap.N)

    fig = plt.figure(figsize=(FIG_W, FIG_H), dpi=DPI)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_axis_off()
    ax.contourf(
        lon_sorted,
        lat,
        field2d,
        levels=LEVELS,
        cmap=cmap,
        norm=norm,
        extend="max",
    )
    occupied = np.where(np.isfinite(field2d) & (field2d > 0), 1.0, 0.0)
    ax.contour(
        lon_sorted,
        lat,
        occupied,
        levels=[0.5],
        colors=[OUTLINE_COLOR],
        alpha=0.28,
        linewidths=0.45,
    )
    ax.set_xlim(-180, 180)
    ax.set_ylim(LAT_MIN, LAT_MAX)
    fig.savefig(path, transparent=True, dpi=DPI)
    plt.close(fig)


def _save_composite(fields, lon_sorted, lat, path):
    """Render MHW and OAX together, then place compound extremes clearly on top."""
    fig = plt.figure(figsize=(FIG_W, FIG_H), dpi=DPI)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_axis_off()

    for key, alpha in (("mhw", 0.72), ("oax", 0.72), ("cex", 1.0)):
        field2d = fields[key]
        colors = FIELDS[key]["colors"]
        cmap = ListedColormap(colors[:-1])
        cmap.set_over(colors[-1])
        norm = BoundaryNorm(LEVELS, cmap.N)
        ax.contourf(
            lon_sorted,
            lat,
            field2d,
            levels=LEVELS,
            cmap=cmap,
            norm=norm,
            extend="max",
            alpha=alpha,
        )
        occupied = np.where(np.isfinite(field2d) & (field2d > 0), 1.0, 0.0)
        ax.contour(
            lon_sorted,
            lat,
            occupied,
            levels=[0.5],
            colors=[OUTLINE_COLOR],
            alpha=0.18 if key != "cex" else 0.34,
            linewidths=0.4 if key != "cex" else 0.6,
        )

    ax.set_xlim(-180, 180)
    ax.set_ylim(LAT_MIN, LAT_MAX)
    fig.savefig(path, transparent=True, dpi=DPI)
    plt.close(fig)


def build():
    os.makedirs(OUT_DIR, exist_ok=True)
    ds = xr.open_dataset(NC_PATH)
    ds = ds.sel(lat=slice(LAT_MIN, LAT_MAX))
    lat = ds["lat"].to_numpy()
    lon = ds["lon"].to_numpy()

    manifest_fields = {}
    rolled_fields = {}
    for key, config in FIELDS.items():
        values = np.asarray(ds[config["variable"]].to_numpy(), dtype=float)
        rolled, lon_sorted = _rolled(values, lon)
        rolled_fields[key] = rolled
        _save_field(rolled, lon_sorted, lat, config["colors"], os.path.join(OUT_DIR, config["file"]))
        manifest_fields[key] = {k: v for k, v in config.items() if k != "variable"}
        finite = values[np.isfinite(values)]
        print(f"{config['file']}: {finite.size} occupied cells, max {finite.max():.0f} months")

    _save_composite(rolled_fields, lon_sorted, lat, os.path.join(OUT_DIR, "combined.png"))
    manifest_fields["intersection"] = {
        "file": "combined.png",
        "label": "MHW, OAX and compound extremes",
        "shortLabel": "MHW ∩ OAX",
        "colors": COMPOUND_COLORS,
        "composite": True,
    }
    print("combined.png: MHW + OAX + compound extremes")

    manifest = {
        "year": 2015,
        "levels": LEVELS,
        "labels": LABELS,
        "rotate": ROTATE,
        "latMin": LAT_MIN,
        "latMax": LAT_MAX,
        "lonMin": -180,
        "lonMax": 180,
        "unit": "extreme-months",
        "fields": manifest_fields,
    }
    with open(os.path.join(OUT_DIR, "manifest.json"), "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, ensure_ascii=False)
    print("manifest.json")


if __name__ == "__main__":
    build()
