"""
Shared visual style for the "When Ocean Heatwaves Turn Acidic" infographic charts.
Import this in every chart script so the map, ring and line chart share one palette.

    from style import PALETTE, apply_style, FREQ_CMAP
    apply_style()
"""
import matplotlib as mpl
from matplotlib import font_manager
from matplotlib.colors import LinearSegmentedColormap

# ---- Palette (matches the HTML infographic) -------------------------------
PALETTE = {
    "cream":      "#f4efe3",   # page background
    "panel":      "#faf6ec",   # panel background
    "panel_edge": "#e6ddc7",
    "ink":        "#1e2a30",   # primary text
    "muted":      "#8a836c",   # secondary text
    "orange":     "#e2851c",
    "amber":      "#e6a54e",
    "deep":       "#c8531f",   # deep orange / high intensity
    "teal":       "#1f9aa6",
    "green":      "#5aa469",
    "nino_red":   "#c0392b",   # El Nino line
    "nina_blue":  "#2f6fae",   # La Nina line
    "enso_nino":  "#5a5550",   # El Nino ring band
    "enso_nina":  "#9ec4dc",   # La Nina ring band
    "land":       "#efe7d1",
    "land_edge":  "#cdbf9c",
    "peak":       "#d8c7a8",
}

# Intensity colour scale (light -> dark). Used for the event circles.
INTENSITY_CMAP = "YlOrRd"

# Diverging "frequency relative to chance" scale for the ocean background:
# blue (less than chance) -> cream (equal) -> orange/red (more than chance)
FREQ_CMAP = LinearSegmentedColormap.from_list(
    "freq_vs_chance",
    ["#3b6fa0", "#7ba3c9", "#cfdbe4", "#f0ead9", "#e8c073", "#dd8a34", "#c8531f", "#a5281a"],
)

# Font preference: fall back gracefully if the display fonts aren't installed.
_HEADING = ["Barlow Condensed", "Oswald", "DejaVu Sans Condensed", "DejaVu Sans"]
_BODY = ["Source Sans 3", "Source Sans Pro", "DejaVu Sans"]


def _first_available(candidates):
    installed = {f.name for f in font_manager.fontManager.ttflist}
    for name in candidates:
        if name in installed:
            return name
    return candidates[-1]


def heading_font():
    return _first_available(_HEADING)


def apply_style():
    """Set global matplotlib rcParams to match the infographic."""
    mpl.rcParams.update({
        "font.family":       _first_available(_BODY),
        "font.size":         11,
        "text.color":        PALETTE["ink"],
        "axes.edgecolor":    "#c7bfa6",
        "axes.labelcolor":   PALETTE["ink"],
        "xtick.color":       PALETTE["muted"],
        "ytick.color":       PALETTE["muted"],
        "figure.facecolor":  PALETTE["panel"],
        "axes.facecolor":    PALETTE["panel"],
        "savefig.facecolor": PALETTE["panel"],
        "svg.fonttype":      "none",
    })
