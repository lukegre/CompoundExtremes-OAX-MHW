# When Ocean Heatwaves Turn Acidic — infographic components

A redesign of the compound marine-heatwave / ocean-acidification infographic,
rebuilt as **editable components** and corrected against the source paper.

> Source: Gregor, L. & Gruber, N. (2025), *Recent history of surface ocean
> acidification extremes that compound marine heatwaves*, **AGU Advances**.
> Data product: OceanSODA-ETHZ, 1982–2024.

---

## 0. File layout

| File | Purpose |
|---|---|
| `Ocean Compound Extremes Infographic - scrolling.html` | The current scrolling infographic. Open directly. |
| `Ocean Compound Extremes Infographic.dc.html` | Earlier fixed-layout snapshot retained for reference. |
| `HOW-TO-ADD-AN-ELEMENT.md` | Guide for adding a new box/panel to the poster. |
| `ocean-infographic-base.css` | Base page styles (fonts, resets) loaded by the poster. |
| `ocean-map-helpers.js` | Map data + pure helpers (events, event-circle color scale, manifest loader, tooltip markup). |
| `ocean-map-draw.js` | Map SVG construction + interaction wiring (equirectangular; ocean field is an `<image>` overlay). |
| `annual/` | **Pre-baked ocean-field images** — `total.png` (default background = extremes summed over all years), `year_<YYYY>.png` (one per year, shown on bar hover), `region_high/low.png` (spotlight masks), and `manifest.json` (levels/colors/labels/years). Rebuilt by `python/build_annual_rasters.py` from `uploads/n_extremes_annual.nc`. |
| `definition_2015/` | **Definition-hover map images** — `mhw.png`, `oax.png`, and `cex.png`, plus their manifest. Rebuilt by `python/build_definition_rasters.py` from `uploads/num_extremes_2015.nc`. |
| `ocean_raster.png` / `ocean_raster.json` | **Legacy.** The old frequency-vs-chance contour grid. No longer used by the current poster — kept only by the `v1 (snapshot)`. Safe to delete once the snapshot is retired. |
| `python/` | Scripts to regenerate the ocean-field images and the standalone chart images (see §2 below). |
| `uploads/` | Source materials only: the AGU paper PDF and `n_extremes_annual.nc` (the per-year field the map images are baked from). Keep this folder pruned. |

---

## 1. The interactive infographic (HTML)

**`Ocean Compound Extremes Infographic - scrolling.html`** — the current full poster. Open it
directly in a browser. It is responsive: a composed poster on wide screens,
and it stacks into a single column on narrow screens / mobile.

Each panel is a self-contained block you can edit independently:

| Panel | Where to edit |
|---|---|
| Title / header | template markup (top) |
| Definition strip (MHW + OAX = compound) | template markup |
| "More common than chance" stat cards | template markup |
| **World frequency map + event circles** | `events` array in the logic class + `_drawMap()` |
| Legend / how-to-read | template markup |
| Donut — size of events | `_drawDonut()` |
| **"A few giants dominate" dot grid** | `_drawDots()` |
| Summer vs winter | template markup |
| El Niño – La Niña line chart | `_drawLine()` |
| 43-year timeline ring | `RING_AREA`-style map inside `_drawRing()` |
| **The mechanism: a tug-of-war** (interactive explorer) | template markup with `data-m="…"` hooks + `_mechInit()` / `_mechUpdate()` / `_mechCalc()` in the logic class |
| **Top events table** | template markup (`<tbody>` rows, `data-key` links each row to its map circle) |

**Interactive touches:** hover one of the three definition cards to compare the
2015 month-count maps for MHW, OAX, and compound extremes; hover a map circle for a tooltip; hover a table row
to highlight its circle on the map; **hover a year's bar** in the El Niño chart to
swap the map's ocean background from the all-years total to that single year's field
of compound-extreme months (the year badge, top-left of the map, tracks which is shown).
The **mechanism** panel is a live explorer. Toggle between low-to-mid-latitude
permanently stratified waters and a combined high-latitude/eastern-equatorial
mixing-upwelling regime; drag the temperature-anomaly slider; or choose an
observed/conceptual preset. Five score cards show temperature, the thermal and
sDIC contributions to [H⁺], the net [H⁺] anomaly, and whether the mechanisms
align. The Blob preset uses Table 1's observed +1.40 °C and +0.18 nmol kg⁻¹
values; conceptual scenarios are labelled as such. Local, season-specific
detrended Q95 thresholds are stated explicitly rather than represented as
universal absolute cutoffs. Wiring lives in the `_mech*` methods, keyed to the
template by `data-m` / `data-preset` attributes under the `mechRef` container.
`_mechCalc()` keeps the observed Blob preset separate from the
manuscript-scale conceptual response used by the slider.

**Tweaks** (exposed in the editor's Tweaks panel — code-only changes):
event-circle intensity colour scale (`warm` / `reds` / `viridis`), circle-size
multiplier, circle opacity, ocean-field overlay opacity (`rasterOpacity`), and tooltips
on/off. The map projection is fixed to equirectangular (required for the pre-baked field
images to overlay linearly). The ocean-field palette/levels are baked in — change them in
`python/build_annual_rasters.py` and re-run. Any text or single colour can be edited in place.

---

## 2. Python scripts (regenerate the data charts as images)

In `python/`. Each script is standalone and shares one palette (`style.py`)
and one dataset (`data.py`), so the figures stay visually consistent with the
HTML and with each other.

```bash
cd python
pip install -r requirements.txt
python build_annual_rasters.py   # -> ../annual/*.png + manifest.json (the map's ocean-field images)
python build_definition_rasters.py # -> ../definition_2015/*.png + manifest.json
python map_events.py             # -> output/map_events.png + .svg
python timeline_ring.py          # -> output/timeline_ring.png + .svg
python elnino_lanina.py          # -> output/elnino_lanina.png + .svg
```

- **`build_annual_rasters.py`** — reads `uploads/n_extremes_annual.nc` (per-year
  `n_extremes(year, lat, lon)`, 0.25°) and renders the map's ocean-field overlays with
  `matplotlib.contourf` at levels `[0,1,2,4,8,16,32]` + `>32`: `total.png` (sum over all
  years, the default background), one `year_<YYYY>.png` per year (shown on bar hover), and
  `region_high/low.png` for the "More common than chance" spotlight, plus `manifest.json`.
  Longitude is pre-rolled by `ROTATE` and latitude cropped to the map frame so the PNGs
  overlay the equirectangular map directly. Edit the levels/palette here and re-run to
  restyle the map — the legend in the `.dc.html` must be updated to match.

- **`build_definition_rasters.py`** — reads `uploads/num_extremes_2015.nc` and
  renders the 2015 `mhw_months`, `oax_months`, and `cex_months` fields with the
  same map framing and count bins as the main map. MHW uses red, OAX uses teal,
  and compound extremes use the main map's warm palette. Hovering the emphasized
  intersection symbol composites all three fields, with compound cells drawn on
  top; hovering the Compound card shows only compound extremes. Leaving a
  definition restores the previously selected annual field.

- **`data.py`** — the single source of truth. Event values are transcribed
  from the paper's Table 1 (`area` = event-maximum Mkm², `dur` = Lagrangian
  duration in months, `I` = 95th-percentile compound intensity). Edit here and
  re-run to update any figure.
- **`style.py`** — palette, fonts, and the two colour scales
  (`YlOrRd` intensity; a diverging "frequency vs chance" scale).
- `map_events.py` needs **cartopy** for real coastlines and a Robinson
  projection; the other two need only matplotlib + numpy.

---

## Data notes & corrections

- Event area, duration and intensity now follow **Table 1** of the paper. The
  table lists the **9** labelled events (the earlier version showed a 10th,
  "Subtropical N. Pacific 2014", which is not in Table 1 — removed).
- The size-of-event donut uses paper-accurate buckets (≈75 % < 1 Mkm²,
  16 % 1–2 Mkm², 9 % > 2 Mkm²). The earlier ">50 million km²" bucket was
  dropped — the largest single event is ~12.6 Mkm².
- The world map is a **real projected coastline** (d3-geo equirectangular in the
  HTML; cartopy Robinson in the Python figures), replacing the distorted background.
- The map's ocean background is now the **real gridded field** from
  `uploads/n_extremes_annual.nc`: total compound-extreme months per location over
  1982–2024 by default, or a single year on bar hover (baked by
  `build_annual_rasters.py`). The sum field maxes at ~17.4 months, so the darkest
  legend bins (16–32, >32) rarely paint — the scale keeps that headroom so the total
  and per-year images share one fixed colour scale.
- The 43-year ring's yearly values (`RING_AREA` in `data.py`) remain **schematic**.
