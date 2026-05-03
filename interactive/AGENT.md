# Interactive Figure 6: Compound Extreme Event Explorer

## Goal
Standalone interactive HTML dashboard replicating Figure 6 with linked behaviours:
1. Hover scatter point → tooltip with event metadata
2. Click scatter point → map updates to show spatial footprint (Choropleth, vector)
3. Event details card updates: key metrics + monthly component Q95 intensity lines
4. Toggle: "All events" vs "Footprint only" to filter scatter

## Data sources
| File | Role |
|------|------|
| `event_stats.csv` | 500 compound extreme events, one row per event (`blob_index`) |
| `ETHZ1v2025_cexTH_shift_poly2_p95.nc` | `blobs` (time×lat×lon blob labels), `intensity_norm`, `mask` (180×360, 1982–2024) |
| `event_footprints.npz` | Precomputed per-event Q95 footprints for 247 qualifying events |
| `figure6-with_annotations.png` | Static reference figure |

### Key columns in event_stats.csv
- **x-axis**: `duration_2sigma_mon_clipped`
- **y-axis**: `cex_intensity_norm_p95`
- **color + size**: `area_max_Mkm2`
- **time**: `month_start_sice_198201` (months since 1982-01)
- **location**: `loc_lat_mode`, `loc_lon_mode`

### 9 highlighted (named) events
| blob_index | Name | Start |
|-----------|------|-------|
| 26 | Madagascar (1987) | 1987-03 |
| 156 | SE Asia (1998) | 1998-01 |
| 222 | Mediterranean Sea (2003) | 2003-05 |
| 289 | Western Australia (2011) | 2010-12 |
| 318 | The Blob (2015) | 2015-04 |
| 350 | South Pacific (2015) | 2016-10 |
| 435 | Great Barrier Reef (2022) | 2022-05 |
| 450 | North Atlantic (2023) | 2023-04 |
| 460 | South Atlantic (2023) | 2023-11 |

## Layout (dark dashboard)
CSS grid, two columns, max-width 1600px:
- **Header bar**: title, subtitle, stat chips
- **Left column** (spans both rows): scatter plot card
- **Right column top**: map card
- **Right column bottom**: event details card (info grid + timeline sparkline)

## Visual theme
| Element | Value |
|---------|-------|
| Body / plot bg | `#111827` |
| Card bg | `#1e2436` |
| Header bg | `#0d1425` |
| Grid lines | `#2a3347` |
| Ocean | `#0a1628` |
| Land | `#2c2c2c` |
| Text main | `#e5e7eb` |
| Text dim | `#9ca3af` |

**Scatter colormap**: `plasma` (dark purple → bright yellow), 10 discrete bins, 0–13 Mkm².

**Map colormap**: `YlOrRd` (yellow → orange → red), vivid on dark background, range 1.6–4.7.

## Scatter styling
- All 500 events plotted; split into 4 Plotly traces for the toggle:
  - **Trace 0**: unnamed, no footprint (toggle-able)
  - **Trace 1**: unnamed, has footprint (always shown)
  - **Trace 2**: named events, fill (always shown)
  - **Trace 3**: named events, black outer ring (always shown)
- Named 9: larger marker (+5 px), white inner ring (2.5 px), black outer ring (1.5 px). **No text labels**.
- Toggle "Footprint only": hides Trace 0 via `Plotly.restyle(..., {visible: 'legendonly'}, [0])`

## Events with map footprint (28 total)
All 9 named events **plus** top 25 by `area_max_Mkm2` from the 247-event precomputed npz.
Union = 28 unique events (all named events fall within the top 25 by area or are explicitly included).

## Preprocessing (`preprocess.py`, run once, generates event_footprints.npz)
For each of the 247 qualifying events (duration > 1 mo, area ≥ 0.5 Mkm²):
1. Select pixels where `blobs == blob_index` across all time steps
2. Compute Q95 of `intensity_norm` over those pixels
3. Save sparse footprint per event

**Critical**: temporal slicing by start/end date was tried first but is wrong — events overlap
in time, contaminating footprints with neighbouring blobs. Must use `blobs == blob_index`.

## Map: go.Scattergeo (sparse marker points)
Built in `build_figure.py` at dashboard build time:
1. Load footprints for the 28 map events from npz
2. Apply Gaussian smoothing (σ=1.5°) for gradual edge fade
3. Per-event footprint stored as `{r: [...], c: [...], v: [...]}` sparse arrays in JS (row/col indices + values)
4. On click: `Plotly.restyle(mapDiv, {lat, lon, 'marker.color', text}, [0])` updates the Scattergeo trace

Map projection: **equirectangular** (PlateCarree), rotated `lon=205` → 25°E at left edge.
The displayed latitude range is cropped to `[-70, 70]` so the map fills the wide right-column card rather than leaving large side bands from the full-world 2:1 aspect ratio.

### Map colourbar/layout
- Geo domain uses the full plot domain: `domain=dict(x=[0, 1], y=[0, 1])`
- Plot margin is tight: `margin=dict(l=0, r=42, t=0, b=0)`
- Colourbar is compact and close to the map: `thickness=10`, `len=0.78`, `x=1.01`, `xpad=2`
- Colourbar ticks are reduced to `[1.6, 2.4, 3.2, 4.0, 4.7]` with 9px tick text and 10px title text

### Map interactivity
- **Hover**: shows "Intensity Q95: {value}" tooltip on footprint pixels
- **Zoom limit**: `MAX_MAP_SCALE = 2` — a `plotly_relayout` listener clamps `geo.projection.scale` ≤ 2
- **Snap-to-event removed** — `geo.center` conflicts with `rotation=dict(lon=205)` and range-based centering jumped off-map; feature dropped.
- **Global reset button**: removed along with snapping.

### Unnamed event display
Scatter hover tooltip and event info card header show `"{year} · {duration} mo"` for unnamed events instead of "Event {idx}".

## Monthly timeseries

Rendered as a **multi-line Plotly chart** with three traces showing how each component evolves over the event lifetime:

| Trace | Source file | Variable | Colour |
|-------|------------|----------|--------|
| MHW | `data/v2025/ETHZ1v2025_temperature_Bmean_shift_poly2_p95.nc` | `intensity_norm` | warm orange `#f97316` |
| OAX | `data/v2025/ETHZ1v2025_ph_total_Bmean_shift_poly2_p95.nc` | `intensity_norm` | cool teal `#06b6d4` |
| Compound | existing compound NC `intensity_norm` | `intensity_norm` | yellow `#facc15` |

**Spatial mask per time step**: pixels where `cex_blobs[t] == blob_idx` (same as current). Applied to MHW and OAX arrays at the same pixel locations.

**Metric**: spatial Q95 over masked pixels, per time step (same aggregation as current compound series). Values can be negative if the component is below threshold at those pixels at that time — clip to 0 is an option but show raw first.

**Build-time implementation** (`build_figure.py`):
1. Load two additional NC files into memory: `ds_mhw.intensity_norm.values` and `ds_oax.intensity_norm.values` alongside the existing compound array
2. For each of the 28 map events, compute per-time-step Q95 for all three arrays using the same compound blob mask
3. Store as `{blob_idx: [{label, month, cex, mhw, oax}, ...]}` in JS

**JS rendering** (`renderTimeline`):
- Uses `go.Scatter(mode='lines+markers', line={shape:'spline'})` for smooth curves
- Three traces on one chart, shared x-axis (month labels)
- Legend is vertical and outside the plot on the right
- Y-axis label: "Normalised intensity"
- Y-axis is fixed to `[0, 5]`

**Files needed** (both relative to repo root, not `interactive/`):
- `data/v2025/ETHZ1v2025_temperature_Bmean_shift_poly2_p95.nc`
- `data/v2025/ETHZ1v2025_ph_total_Bmean_shift_poly2_p95.nc`

## Output
`interactive/figure6_interactive.html` — standalone, no server required (~5.7 MB)

## Files
| File | Purpose |
|------|---------|
| `preprocess.py` | Compute per-event footprints from blob NC → `event_footprints.npz` |
| `build_figure.py` | Build full dashboard: scatter + Choropleth map + timeseries → HTML |
| `event_footprints.npz` | Precomputed sparse Q95 footprints for 247 events |
| `event_stats.csv` | Per-event statistics (500 rows) |
| `ETHZ1v2025_cexTH_shift_poly2_p95.nc` | Source spatiotemporal data with blob labels |

## Out of scope
- Time animation through the full NetCDF
- Mobile/responsive layout
- Server-side deployment
