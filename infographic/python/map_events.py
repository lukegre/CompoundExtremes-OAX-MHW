"""
World map of the largest compound (OAX n MHW) events.

Circle SIZE  = event-maximum area (km^2)
Circle COLOUR = compound intensity (light -> dark = lower -> higher)
Ocean shading = schematic frequency of compound extremes relative to chance
                (high in the low-to-mid latitudes; rare at the poles and in
                the eastern equatorial Pacific).

Run:  python map_events.py
Out:  output/map_events.png  and  output/map_events.svg

Requires cartopy (see requirements.txt). If cartopy is not installed the
script prints an install hint and exits.
"""
import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize

from style import PALETTE, apply_style, INTENSITY_CMAP, FREQ_CMAP, heading_font
from data import EVENTS, INTENSITY_RANGE

OUT = os.path.join(os.path.dirname(__file__), "output")

try:
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
except ImportError:
    raise SystemExit(
        "This script needs cartopy.\n"
        "    pip install cartopy    (or)    conda install -c conda-forge cartopy"
    )


def zonal_frequency_field():
    """A smooth latitude-banded field: high frequency in the low-to-mid
    latitudes, low near the poles and the equator (eastern eq. Pacific)."""
    lat = np.linspace(-90, 90, 361)
    lon = np.linspace(-180, 180, 721)
    LON, LAT = np.meshgrid(lon, lat)
    # two mid-latitude bands (~30 deg N/S) high, poles + equator low
    band = np.exp(-((np.abs(LAT) - 30) / 15) ** 2)          # 0..1 peaked at +/-30
    equator_dip = 1 - 0.7 * np.exp(-(LAT / 9) ** 2)          # suppress equator
    field = band * equator_dip
    # extra suppression over the eastern equatorial Pacific
    epac = np.exp(-((LON + 110) / 35) ** 2) * np.exp(-(LAT / 12) ** 2)
    field = np.clip(field - 0.6 * epac, 0, 1)
    return LON, LAT, field


def main():
    apply_style()
    hf = heading_font()

    proj = ccrs.Robinson(central_longitude=-10)
    fig = plt.figure(figsize=(13, 6.8))
    ax = plt.axes(projection=proj)
    ax.set_global()
    ax.set_facecolor(PALETTE["cream"])
    fig.patch.set_facecolor(PALETTE["cream"])

    # ocean frequency field (schematic)
    LON, LAT, field = zonal_frequency_field()
    ax.pcolormesh(LON, LAT, field, transform=ccrs.PlateCarree(),
                  cmap=FREQ_CMAP, vmin=0, vmax=1, alpha=0.85, shading="auto", zorder=0)

    # land on top
    ax.add_feature(cfeature.LAND, facecolor=PALETTE["land"],
                   edgecolor=PALETTE["land_edge"], linewidth=0.4, zorder=2)
    ax.gridlines(color="white", alpha=0.25, linewidth=0.5, zorder=1)

    # event circles
    norm = Normalize(*INTENSITY_RANGE)
    cmap = plt.get_cmap(INTENSITY_CMAP)
    # marker area proportional to event area (sqrt for visual sizing)
    smax = 5200
    for e in EVENTS:
        s = (np.sqrt(e["area"] / 12.6)) ** 2 * smax + 220
        ax.scatter(e["lon"], e["lat"], s=s, transform=ccrs.PlateCarree(),
                   color=cmap(norm(e["I"])), edgecolor="white", linewidth=1.6,
                   zorder=4, alpha=0.92)
        # value inside big circles
        if e["area"] >= 4:
            ax.text(e["lon"], e["lat"], f"{e['area']:g}", transform=ccrs.PlateCarree(),
                    ha="center", va="center", color="white", zorder=5,
                    fontsize=13, fontweight="bold", family=hf)
        # label
        dy = 10 if e["lat"] >= 0 else -12
        va = "bottom" if e["lat"] >= 0 else "top"
        ax.text(e["lon"], e["lat"] + dy, f"{e['name']}  ({e['year']})",
                transform=ccrs.PlateCarree(), ha="center", va=va, zorder=5,
                fontsize=9, fontweight="bold", color=PALETTE["ink"],
                path_effects=_halo())

    ax.set_title("Where the largest compound extremes struck  ·  1982–2024",
                 fontsize=17, fontweight="bold", family=hf,
                 color=PALETTE["ink"], pad=12, loc="left")

    # intensity colourbar
    sm = ScalarMappable(norm=norm, cmap=cmap)
    cb = fig.colorbar(sm, ax=ax, fraction=0.02, pad=0.02, shrink=0.6)
    cb.set_label("Compound intensity  (lower → higher)", fontsize=9)
    cb.ax.tick_params(labelsize=8)

    os.makedirs(OUT, exist_ok=True)
    fig.savefig(os.path.join(OUT, "map_events.png"), dpi=200, bbox_inches="tight")
    fig.savefig(os.path.join(OUT, "map_events.svg"), bbox_inches="tight")
    print("wrote", os.path.join(OUT, "map_events.png"))


def _halo():
    import matplotlib.patheffects as pe
    return [pe.withStroke(linewidth=2.6, foreground=PALETTE["cream"])]


if __name__ == "__main__":
    main()
