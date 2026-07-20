"""
43-year radial timeline of global compound-event area (1982-2024).

Each wedge is one year; its length encodes the relative global OAX n MHW area
and its colour follows the same warm scale. Two inner rings mark El Nino and
La Nina years. A handful of landmark events are annotated around the outside.

Run:  python timeline_ring.py
Out:  output/timeline_ring.png  and  .svg
"""
import os
import numpy as np
import matplotlib.pyplot as plt

from style import PALETTE, apply_style, heading_font
from data import YEARS, RING_AREA, NINO_YEARS, NINA_YEARS, RING_LABELS

OUT = os.path.join(os.path.dirname(__file__), "output")


def main():
    apply_style()
    hf = heading_font()
    cmap = plt.get_cmap("YlOrRd")

    n = len(YEARS)
    step = 2 * np.pi / n
    # angle per year, starting at the top (12 o'clock), going clockwise
    thetas = np.array([np.pi / 2 - (i + 0.5) * step for i in range(n)])
    areas = np.array([RING_AREA[y] for y in YEARS])

    r_in, band = 1.0, 0.62

    fig = plt.figure(figsize=(7.4, 7.4))
    ax = fig.add_subplot(projection="polar")
    ax.set_facecolor(PALETTE["panel"])
    fig.patch.set_facecolor(PALETTE["panel"])

    # year wedges
    ax.bar(thetas, band * areas + 0.04, width=step * 0.92, bottom=r_in,
           color=[cmap(min(a / 1.15, 1)) for a in areas], edgecolor="none", zorder=3)

    # ENSO rings
    nino = [np.pi / 2 - (i + 0.5) * step for i, y in enumerate(YEARS) if y in NINO_YEARS]
    nina = [np.pi / 2 - (i + 0.5) * step for i, y in enumerate(YEARS) if y in NINA_YEARS]
    ax.bar(nino, 0.055, width=step * 0.92, bottom=r_in - 0.08, color=PALETTE["enso_nino"], zorder=2)
    ax.bar(nina, 0.055, width=step * 0.92, bottom=r_in - 0.16, color=PALETTE["enso_nina"], zorder=2)

    # landmark event annotations
    for yr, label in RING_LABELS:
        i = YEARS.index(yr)
        th = np.pi / 2 - (i + 0.5) * step
        r0 = r_in + band * RING_AREA[yr] + 0.06
        r1 = r_in + band + 0.22
        ax.plot([th, th], [r0, r1], color="#b0a888", lw=1, zorder=4)
        right = np.cos(th) >= 0
        ax.text(th, r1 + 0.03, label, rotation=0, ha="left" if right else "right",
                va="center", fontsize=9.5, fontweight="bold", color=PALETTE["ink"], zorder=5)

    # 1982 marker
    ax.text(np.pi / 2, r_in + band + 0.30, "1982", ha="center", va="bottom",
            fontsize=9.5, fontweight="bold", color=PALETTE["muted"])

    # centre label
    ax.text(0, 0, "GLOBAL\nCOMPOUND\nEVENT AREA", transform=ax.transData,
            ha="center", va="center", fontsize=13, fontweight="bold",
            family=hf, color=PALETTE["ink"])

    # cosmetics
    ax.set_ylim(0, r_in + band + 0.55)
    ax.set_xticks([]); ax.set_yticks([])
    ax.spines["polar"].set_visible(False)
    ax.grid(False)

    fig.suptitle("43 years of compound extremes", x=0.5, y=0.97, fontsize=17,
                 fontweight="bold", family=hf, color=PALETTE["ink"])

    # legend
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=PALETTE["enso_nino"], label="El Niño"),
                       Patch(color=PALETTE["enso_nina"], label="La Niña")],
              loc="lower center", bbox_to_anchor=(0.5, -0.06), ncol=2,
              frameon=False, fontsize=10)

    os.makedirs(OUT, exist_ok=True)
    fig.savefig(os.path.join(OUT, "timeline_ring.png"), dpi=200, bbox_inches="tight")
    fig.savefig(os.path.join(OUT, "timeline_ring.svg"), bbox_inches="tight")
    print("wrote", os.path.join(OUT, "timeline_ring.png"))


if __name__ == "__main__":
    main()
