"""
El Nino - La Nina connection: relative global compound-event area over time.

Compound area peaks at the end of / just after El Nino events, often during
the following La Nina. The shaded band highlights the recurring peak.

Run:  python elnino_lanina.py
Out:  output/elnino_lanina.png  and  .svg
"""
import os
import matplotlib.pyplot as plt

from style import PALETTE, apply_style, heading_font
from data import enso_area_curves

OUT = os.path.join(os.path.dirname(__file__), "output")


def main():
    apply_style()
    hf = heading_font()
    x, el, la = enso_area_curves()

    fig, ax = plt.subplots(figsize=(6.6, 3.4))

    # peak band
    ax.axvspan(0.78, 0.94, color=PALETTE["peak"], alpha=0.45, lw=0)
    ax.text(0.86, 1.52, "peak compound area", ha="center", fontsize=8.5,
            fontweight="bold", color="#8a7a4f")

    ax.plot(x, el, color=PALETTE["nino_red"], lw=2.4, label="El Niño")
    ax.plot(x, la, color=PALETTE["nina_blue"], lw=2.4, label="La Niña")

    ax.set_xlim(0, 1); ax.set_ylim(0, 1.65)
    ax.set_yticks([0, 0.5, 1.0, 1.5])
    ax.set_xticks([])
    ax.set_xlabel("Time (years) →", fontsize=10, color=PALETTE["muted"])
    ax.set_ylabel("Compound-event area (relative)", fontsize=9.5)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.legend(frameon=False, fontsize=10, loc="upper left")
    ax.set_title("El Niño – La Niña connection", fontsize=15, fontweight="bold",
                 family=hf, color=PALETTE["ink"], loc="left", pad=8)

    os.makedirs(OUT, exist_ok=True)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "elnino_lanina.png"), dpi=200, bbox_inches="tight")
    fig.savefig(os.path.join(OUT, "elnino_lanina.svg"), bbox_inches="tight")
    print("wrote", os.path.join(OUT, "elnino_lanina.png"))


if __name__ == "__main__":
    main()
