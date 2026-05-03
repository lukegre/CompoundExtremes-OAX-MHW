"""
Build Figure 6 as a dark-themed interactive dashboard.
Map uses go.Scattergeo markers (sparse footprint points).
Outputs: figure6_interactive.html (standalone)
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly
import plotly.colors as pc
import plotly.graph_objects as go
import plotly.io as pio
import xarray as xr

HERE = Path(__file__).parent
ROOT = HERE.parent

# ── Colour constants ──────────────────────────────────────────────────────────
DARK_BG    = "#111827"
CARD_BG    = "#1e2436"
HEADER_BG  = "#0d1425"
GRID_COL   = "#2a3347"
TEXT_MAIN  = "#e5e7eb"
TEXT_DIM   = "#9ca3af"
OCEAN_COL  = "#0a1628"
LAND_COL   = "#2c2c2c"
COAST_COL  = "#555555"

SCATTER_CMAP = "plasma"
MAP_CMAP     = "YlOrRd"

# ── Named events ──────────────────────────────────────────────────────────────
named_events: dict[int, str] = {
    156: "SE Asia (1998)",
    222: "Mediterranean Sea (2003)",
    289: "Western Australia (2011)",
    318: "The Blob (2015)",
    350: "South Pacific (2015)",
    26:  "Madagascar (1987)",
    435: "Great Barrier Reef (2022)",
    450: "North Atlantic (2023)",
    460: "South Atlantic (2023)",
}

# ── Event stats ───────────────────────────────────────────────────────────────
df = pd.read_csv(HERE / "event_stats.csv", index_col=0)
base = pd.Timestamp("1982-01-01")
df["date_start"] = [base + pd.DateOffset(months=int(m)) for m in df.month_start_sice_198201]
df["year_start"] = df["date_start"].dt.year

# ── Footprints ────────────────────────────────────────────────────────────────
npz = np.load(HERE / "event_footprints.npz")
lat = npz["lat"]
lon = npz["lon"]
have_fp = set(int(x) for x in npz["blob_indices"])

# Map events: all 9 named + top 25 by area
top25_ids = set(
    df[df.index.isin(have_fp)]
    .sort_values("area_max_Mkm2", ascending=False)
    .head(25).index.tolist()
)
map_event_ids: set[int] = (set(named_events.keys()) | top25_ids) & have_fp
print(f"Map events: {len(map_event_ids)}")

# Sparse footprint store: {blob_idx: {r, c, v arrays}}
footprint_js: dict[str, dict] = {}
for idx in map_event_ids:
    arr = npz[f"fp_{idx}"]
    finite = np.isfinite(arr)
    if not finite.any():
        continue
    r, c = np.where(finite)
    footprint_js[str(idx)] = {
        "r": r.tolist(),
        "c": c.tolist(),
        "v": np.round(arr[finite], 3).tolist(),
    }

# ── Monthly component timeseries from source NC ───────────────────────────────
print("Loading NC files for timeseries…")
ds_cex = xr.open_dataset(HERE / "ETHZ1v2025_cexTH_shift_poly2_p95.nc")
ds_mhw = xr.open_dataset(ROOT / "data/v2025/ETHZ1v2025_temperature_Bmean_shift_poly2_p95.nc")
ds_oax = xr.open_dataset(ROOT / "data/v2025/ETHZ1v2025_ph_total_Bmean_shift_poly2_p95.nc")

blobs_arr     = ds_cex.blobs.values
cex_arr       = ds_cex.intensity_norm.values
mhw_arr       = ds_mhw.intensity_norm.values
oax_arr       = ds_oax.intensity_norm.values
times         = pd.DatetimeIndex(ds_cex.time.values)

if cex_arr.shape != mhw_arr.shape or cex_arr.shape != oax_arr.shape:
    raise ValueError(
        "Component intensity arrays must match compound array shape: "
        f"cex={cex_arr.shape}, mhw={mhw_arr.shape}, oax={oax_arr.shape}"
    )


def spatial_q95(values: np.ndarray) -> float | None:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return None
    return round(float(np.percentile(finite, 95)), 3)

timeseries_js: dict[str, list[dict]] = {}
for idx in map_event_ids:
    presence = (blobs_arr == float(idx))
    t_active = np.where(presence.any(axis=(1, 2)))[0]
    monthly  = []
    for t in t_active:
        mask = presence[t]
        if not mask.any():
            continue
        date = times[t]
        monthly.append({
            "label": date.strftime("%b %Y"),
            "month": int(date.month),
            "cex":   spatial_q95(cex_arr[t][mask]),
            "mhw":   spatial_q95(mhw_arr[t][mask]),
            "oax":   spatial_q95(oax_arr[t][mask]),
        })
    timeseries_js[str(idx)] = monthly
    print(f"  idx={idx}: {len(monthly)} months")
print("Timeseries done.")

# ── Event metadata ────────────────────────────────────────────────────────────
basin_map = {1: "Atlantic", 2: "Pacific", 3: "Indian", 4: "Arctic", 5: "Southern"}
event_meta: dict[str, dict] = {}
for idx, row in df.iterrows():
    event_meta[str(idx)] = {
        "name":      named_events.get(idx, f"{int(row.year_start)} · {round(float(row.duration_2sigma_mon), 1)} mo"),
        "year":      int(row.year_start),
        "duration":  round(float(row.duration_2sigma_mon), 1),
        "intensity": round(float(row.cex_intensity_norm_p95), 3),
        "area":      round(float(row.area_max_Mkm2), 2),
        "basin":     basin_map.get(int(row.loc_basin), "—"),
        "lat":       round(float(row.loc_lat_mode), 1),
        "lon":       round(float(row.loc_lon_mode), 1),
        "has_map":   idx in map_event_ids,
    }

# ── Scatter colour helpers ────────────────────────────────────────────────────
n_bins = 10
vmax   = 13.0
bin_edges  = np.linspace(0, vmax, n_bins + 1)
bin_colors = pc.sample_colorscale(SCATTER_CMAP, [i / (n_bins - 1) for i in range(n_bins)])

def area_to_color(area: float) -> str:
    return bin_colors[int(np.clip(np.digitize(area, bin_edges[1:]), 0, n_bins - 1))]

SIZE_MIN, SIZE_MAX = 4, 24
area_vals = df["area_max_Mkm2"].values
area_norm = (area_vals - area_vals.min()) / (area_vals.max() - area_vals.min())
df["marker_size"] = SIZE_MIN + area_norm * (SIZE_MAX - SIZE_MIN)

def hover_texts(sub: pd.DataFrame) -> list[str]:
    rows = []
    for idx, row in sub.iterrows():
        name  = named_events.get(idx)
        basin = basin_map.get(int(row.loc_basin), str(int(row.loc_basin)))
        header = f"<b>{name}</b>" if name else f"<b>{int(row.year_start)} · {row.duration_2sigma_mon:.1f} mo</b>"
        rows.append(
            f"{header}<br>"
            f"Year: {int(row.year_start)}<br>"
            f"Duration (2σ): {row.duration_2sigma_mon:.1f} mo<br>"
            f"Intensity Q95: {row.cex_intensity_norm_p95:.2f}<br>"
            f"Max area: {row.area_max_Mkm2:.2f} Mkm²<br>"
            f"Basin: {basin}"
            + ("<br><i>Has footprint</i>" if idx in map_event_ids else "")
        )
    return rows

# ── Scatter: 4 traces for toggle ─────────────────────────────────────────────
# Trace 0: unnamed, no footprint  (hidden by "footprint only" toggle)
# Trace 1: unnamed, has footprint
# Trace 2: named events (fill)
# Trace 3: named events (outer ring)
# Trace 4: colorbar dummy

is_named   = df.index.isin(named_events)
has_fp_col = df.index.isin(map_event_ids)
df_no_fp   = df[~is_named & ~has_fp_col].copy()
df_has_fp  = df[~is_named &  has_fp_col].copy()
df_named   = df[ is_named].copy()

scatter_fig = go.Figure()

_dim_line = dict(line=dict(color="rgba(255,255,255,0.15)", width=0.5), opacity=0.85)

scatter_fig.add_trace(go.Scatter(
    x=df_no_fp["duration_2sigma_mon_clipped"].tolist(),
    y=df_no_fp["cex_intensity_norm_p95"].tolist(),
    customdata=df_no_fp.index.tolist(),
    mode="markers",
    marker=dict(size=df_no_fp["marker_size"].tolist(),
                color=[area_to_color(a) for a in df_no_fp["area_max_Mkm2"]],
                **_dim_line),
    hovertemplate="%{text}<extra></extra>",
    text=hover_texts(df_no_fp),
    showlegend=False, name="no_fp",
))

scatter_fig.add_trace(go.Scatter(
    x=df_has_fp["duration_2sigma_mon_clipped"].tolist(),
    y=df_has_fp["cex_intensity_norm_p95"].tolist(),
    customdata=df_has_fp.index.tolist(),
    mode="markers",
    marker=dict(size=df_has_fp["marker_size"].tolist(),
                color=[area_to_color(a) for a in df_has_fp["area_max_Mkm2"]],
                **_dim_line),
    hovertemplate="%{text}<extra></extra>",
    text=hover_texts(df_has_fp),
    showlegend=False, name="has_fp",
))

scatter_fig.add_trace(go.Scatter(
    x=df_named["duration_2sigma_mon_clipped"].tolist(),
    y=df_named["cex_intensity_norm_p95"].tolist(),
    customdata=df_named.index.tolist(),
    mode="markers",
    marker=dict(size=(df_named["marker_size"] + 5).tolist(),
                color=[area_to_color(a) for a in df_named["area_max_Mkm2"]],
                line=dict(color="white", width=2.5)),
    hovertext=hover_texts(df_named),
    hovertemplate="%{hovertext}<extra></extra>",
    showlegend=False, name="named",
))

scatter_fig.add_trace(go.Scatter(
    x=df_named["duration_2sigma_mon_clipped"].tolist(),
    y=df_named["cex_intensity_norm_p95"].tolist(),
    mode="markers",
    marker=dict(size=(df_named["marker_size"] + 5).tolist(),
                color="rgba(0,0,0,0)",
                line=dict(color="black", width=1.5)),
    hoverinfo="skip", showlegend=False,
))

scatter_fig.add_trace(go.Scatter(
    x=[None], y=[None], mode="markers",
    marker=dict(colorscale=SCATTER_CMAP, color=[0], cmin=0, cmax=vmax,
                colorbar=dict(
                    title=dict(text="Max area<br>(Mkm²)", side="right",
                               font=dict(size=11, color=TEXT_MAIN)),
                    thickness=14, len=0.8, y=0.5,
                    tickvals=np.linspace(0, vmax, 6).tolist(),
                    ticktext=[f"{v:.0f}" for v in np.linspace(0, vmax, 6)],
                    tickfont=dict(size=10, color=TEXT_DIM),
                    bgcolor=CARD_BG, bordercolor=GRID_COL, borderwidth=1,
                ), showscale=True),
    showlegend=False, hoverinfo="skip",
))

scatter_fig.update_layout(
    margin=dict(l=55, r=85, t=20, b=55),
    paper_bgcolor=CARD_BG,
    plot_bgcolor=DARK_BG,
    xaxis=dict(
        title=dict(text="Duration [μ + 2σ] (months)", font=dict(size=12, color=TEXT_MAIN)),
        showgrid=True, gridcolor=GRID_COL, zeroline=False,
        tickfont=dict(size=11, color=TEXT_DIM), linecolor=GRID_COL,
    ),
    yaxis=dict(
        title=dict(text="Compound intensity Q95", font=dict(size=12, color=TEXT_MAIN)),
        range=[1.7, 4.73],
        showgrid=True, gridcolor=GRID_COL, zeroline=False,
        tickfont=dict(size=11, color=TEXT_DIM), linecolor=GRID_COL,
    ),
    hoverlabel=dict(bgcolor=CARD_BG, font_size=12, font_color=TEXT_MAIN,
                    bordercolor=GRID_COL),
)

# ── Map figure — Scattergeo ───────────────────────────────────────────────────
map_fig = go.Figure()

map_fig.add_trace(go.Scattergeo(
    lat=[], lon=[],
    mode="markers",
    marker=dict(
        size=3,
        color=[],
        colorscale=MAP_CMAP,
        cmin=1.6, cmax=4.7,
        opacity=0.9,
        line=dict(width=0),
        colorbar=dict(
            title=dict(text="Intensity Q95", side="right",
                       font=dict(size=10, color=TEXT_MAIN)),
            thickness=10, len=0.78, x=1.01, xanchor="left", xpad=2, y=0.5, ypad=0,
            tickvals=[1.6, 2.4, 3.2, 4.0, 4.7],
            tickfont=dict(size=9, color=TEXT_DIM),
            bgcolor=CARD_BG, bordercolor=GRID_COL, borderwidth=1,
        ),
        showscale=True,
    ),
    showlegend=False, name="footprint",
    hovertemplate="Intensity Q95: %{text}<extra></extra>",
    text=[],
))

map_fig.update_layout(
    margin=dict(l=0, r=42, t=0, b=0),
    paper_bgcolor=CARD_BG,
    geo=dict(
        domain=dict(x=[0, 1], y=[0, 1]),
        showland=True, landcolor=LAND_COL,
        showcoastlines=True, coastlinecolor=COAST_COL, coastlinewidth=0.7,
        showocean=True, oceancolor=OCEAN_COL, showlakes=False,
        projection=dict(type="equirectangular", rotation=dict(lon=205)),
        lonaxis=dict(range=[25, 385]),
        lataxis=dict(range=[-70, 70]),
        bgcolor=OCEAN_COL, framecolor=GRID_COL, framewidth=1,
    ),
)

# ── Serialise ─────────────────────────────────────────────────────────────────
scatter_json = pio.to_json(scatter_fig)
map_json     = pio.to_json(map_fig)
plotly_js    = Path(plotly.__file__).parent / "package_data" / "plotly.min.js"

# ── HTML ──────────────────────────────────────────────────────────────────────
html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Compound Extreme Events Dashboard</title>
<script>{plotly_js.read_text()}</script>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    background: {DARK_BG}; color: {TEXT_MAIN}; min-height: 100vh;
  }}
  .header {{
    background: {HEADER_BG};
    padding: 13px 24px;
    display: flex; align-items: center; justify-content: space-between;
    border-bottom: 1px solid #1f2f45;
  }}
  .header-title h1 {{ font-size: 15px; font-weight: 600; color: {TEXT_MAIN}; }}
  .header-title p  {{ font-size: 11px; color: {TEXT_DIM}; margin-top: 3px; }}
  .header-chips {{ display: flex; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }}
  .chip {{
    background: rgba(255,255,255,0.07); border: 1px solid rgba(255,255,255,0.12);
    border-radius: 20px; padding: 3px 11px; font-size: 11.5px;
    white-space: nowrap; color: {TEXT_MAIN};
  }}
  .chip span {{ color: {TEXT_DIM}; margin-right: 4px; }}
  .main {{
    display: grid; grid-template-columns: 1fr 1fr; grid-template-rows: auto auto;
    gap: 12px; padding: 12px; max-width: 1600px; margin: 0 auto;
  }}
  .card {{ background: {CARD_BG}; border-radius: 10px; border: 1px solid #2a3347; overflow: hidden; }}
  .card-header {{
    padding: 9px 14px 7px; border-bottom: 1px solid #2a3347;
    display: flex; align-items: center; gap: 10px;
  }}
  .card-header h2 {{
    font-size: 10.5px; font-weight: 700; color: {TEXT_DIM};
    text-transform: uppercase; letter-spacing: 0.08em; flex-shrink: 0;
  }}
  .card-header .subtitle {{ font-size: 11px; color: #5a6a84; flex: 1; }}
  .toggle-group {{ display: flex; gap: 4px; margin-left: auto; flex-shrink: 0; }}
  .toggle-btn {{
    background: rgba(255,255,255,0.06); border: 1px solid #2a3347;
    border-radius: 6px; color: {TEXT_DIM}; font-size: 10.5px;
    padding: 3px 10px; cursor: pointer; transition: all 0.15s; white-space: nowrap;
  }}
  .toggle-btn:hover  {{ background: rgba(255,255,255,0.12); color: {TEXT_MAIN}; }}
  .toggle-btn.active {{ background: rgba(96,165,250,0.18); border-color: rgba(96,165,250,0.5); color: #93c5fd; }}
  .scatter-card {{ grid-column: 1; grid-row: 1 / 3; }}
  .map-card     {{ grid-column: 2; grid-row: 1; }}
  .info-card    {{ grid-column: 2; grid-row: 2; min-height: 195px; }}
  .info-body {{ padding: 13px 16px; }}
  .info-placeholder {{ color: #3d4f6a; font-size: 13px; text-align: center; padding: 30px 0; }}
  .info-name {{
    font-size: 13.5px; font-weight: 700; color: {TEXT_MAIN};
    margin-bottom: 10px; display: flex; align-items: center; gap: 7px; flex-wrap: wrap;
  }}
  .badge {{ font-size: 10px; font-weight: 600; padding: 2px 7px; border-radius: 9px; }}
  .badge-named  {{ background: rgba(96,165,250,0.15);  color: #60a5fa; border: 1px solid rgba(96,165,250,0.3); }}
  .badge-hasmap {{ background: rgba(52,211,153,0.15);  color: #34d399; border: 1px solid rgba(52,211,153,0.3); }}
  .badge-nomap  {{ background: rgba(251,191,36,0.12);  color: #fbbf24; border: 1px solid rgba(251,191,36,0.25); }}
  .info-grid {{
    display: grid; grid-template-columns: repeat(3, 1fr);
    gap: 8px 14px; margin-bottom: 12px;
  }}
  .info-item label {{
    display: block; font-size: 9.5px; text-transform: uppercase;
    letter-spacing: 0.07em; color: #5a6a84; margin-bottom: 1px;
  }}
  .info-item .val  {{ font-size: 14px; font-weight: 600; color: {TEXT_MAIN}; }}
  .info-item .unit {{ font-size: 10px; color: {TEXT_DIM}; margin-left: 2px; }}
  .timeline-label {{ font-size: 9.5px; text-transform: uppercase; letter-spacing: 0.07em; color: #5a6a84; margin-bottom: 2px; }}
  #scatter-div, #map-div, #timeline-div {{ width: 100%; }}
</style>
</head>
<body>

<div class="header">
  <div class="header-title">
    <h1>Compound Marine Extremes — Spatial Event Explorer</h1>
    <p>Marine heatwaves co-occurring with ocean acidification extremes · 1982–2024</p>
  </div>
  <div class="header-chips">
    <div class="chip"><span>Events</span>{len(df)}</div>
    <div class="chip"><span>Period</span>1982 – 2024</div>
    <div class="chip"><span>With footprint</span>{len(map_event_ids)}</div>
    <div class="chip"><span>Named</span>{len(named_events)}</div>
  </div>
</div>

<div class="main">
  <div class="card scatter-card">
    <div class="card-header">
      <h2>Event space</h2>
      <span class="subtitle">Duration × intensity · sized &amp; coloured by max area</span>
      <div class="toggle-group">
        <button id="btn-all" class="toggle-btn active" onclick="setFilter('all')">All events</button>
        <button id="btn-fp"  class="toggle-btn"        onclick="setFilter('footprint')">Footprint only</button>
      </div>
    </div>
    <div id="scatter-div"></div>
  </div>

  <div class="card map-card">
    <div class="card-header">
      <h2>Spatial footprint</h2>
      <span class="subtitle" id="map-subtitle">click an event above</span>
    </div>
    <div id="map-div"></div>
  </div>

  <div class="card info-card">
    <div class="card-header"><h2>Event details</h2></div>
    <div class="info-body" id="info-body">
      <div class="info-placeholder">← select an event from the scatter plot</div>
    </div>
  </div>
</div>

<script>
var scatterData    = {scatter_json};
var mapData        = {map_json};
var footprints     = {json.dumps(footprint_js)};
var eventMeta      = {json.dumps(event_meta)};
var timeseriesData = {json.dumps(timeseries_js)};
var namedIds       = {json.dumps(list(named_events.keys()))};
var lat            = {json.dumps(lat.tolist())};
var lon            = {json.dumps(lon.tolist())};

var DARK_BG   = "{DARK_BG}";
var CARD_BG   = "{CARD_BG}";
var GRID_COL  = "{GRID_COL}";
var TEXT_DIM  = "{TEXT_DIM}";
var TEXT_MAIN = "{TEXT_MAIN}";

var scatterDiv = document.getElementById('scatter-div');
var mapDiv     = document.getElementById('map-div');

Plotly.newPlot(scatterDiv, scatterData.data,
  Object.assign({{}}, scatterData.layout, {{height: 530, autosize: true}}),
  {{responsive: true, displayModeBar: false}});

Plotly.newPlot(mapDiv, mapData.data,
  Object.assign({{}}, mapData.layout, {{height: 310, autosize: true}}),
  {{responsive: true, displayModeBar: false}});

var MAX_MAP_SCALE = 2;
mapDiv.on('plotly_relayout', function(ev) {{
  var scale = ev['geo.projection.scale'];
  if (scale !== undefined && scale > MAX_MAP_SCALE) {{
    Plotly.relayout(mapDiv, {{'geo.projection.scale': MAX_MAP_SCALE}});
  }}
}});

function setFilter(mode) {{
  var showAll = mode === 'all';
  Plotly.restyle(scatterDiv, {{visible: showAll ? true : 'legendonly'}}, [0]);
  document.getElementById('btn-all').classList.toggle('active',  showAll);
  document.getElementById('btn-fp') .classList.toggle('active', !showAll);
}}

scatterDiv.on('plotly_click', function(data) {{
  var pt      = data.points[0];
  var blobIdx = String(pt.customdata);
  if (!blobIdx || blobIdx === 'undefined') return;

  var meta = eventMeta[blobIdx];
  if (meta) renderInfo(meta, blobIdx);

  var fp = footprints[blobIdx];
  if (fp) {{
    var lats = [], lons = [], vals = [], txts = [];
    for (var i = 0; i < fp.r.length; i++) {{
      lats.push(lat[fp.r[i]]);
      lons.push(lon[fp.c[i]]);
      vals.push(fp.v[i]);
      txts.push(fp.v[i].toFixed(2));
    }}
    Plotly.restyle(mapDiv, {{lat: [lats], lon: [lons], 'marker.color': [vals], text: [txts]}}, [0]);
    document.getElementById('map-subtitle').textContent = meta ? meta.name : 'Event ' + blobIdx;
  }} else {{
    Plotly.restyle(mapDiv, {{lat: [[]], lon: [[]], 'marker.color': [[]], text: [[]]}}, [0]);
    document.getElementById('map-subtitle').textContent =
      (meta ? meta.name : 'Event ' + blobIdx) + ' — no footprint';
  }}
}});

function renderInfo(meta, blobIdx) {{
  var isNamed  = namedIds.indexOf(parseInt(blobIdx)) >= 0;
  var mapBadge = meta.has_map
    ? '<span class="badge badge-hasmap">footprint</span>'
    : '<span class="badge badge-nomap">no footprint</span>';
  var namedBadge = isNamed ? '<span class="badge badge-named">named</span>' : '';

  document.getElementById('info-body').innerHTML =
    '<div class="info-name">' + meta.name + namedBadge + mapBadge + '</div>' +
    '<div class="info-grid">' +
      '<div class="info-item"><label>Year</label><div class="val">' + meta.year + '</div></div>' +
      '<div class="info-item"><label>Duration (2σ)</label><div class="val">' + meta.duration + '<span class="unit">mo</span></div></div>' +
      '<div class="info-item"><label>Intensity Q95</label><div class="val">' + meta.intensity + '</div></div>' +
      '<div class="info-item"><label>Max area</label><div class="val">' + meta.area + '<span class="unit">Mkm²</span></div></div>' +
      '<div class="info-item"><label>Basin</label><div class="val" style="font-size:13px">' + meta.basin + '</div></div>' +
      '<div class="info-item"><label>Location</label><div class="val" style="font-size:12px">' + meta.lat + '°, ' + meta.lon + '°</div></div>' +
    '</div>' +
    '<div class="timeline-label">Monthly normalised intensity Q95</div>' +
    '<div id="timeline-div"></div>';

  renderTimeline(blobIdx);
}}

function renderTimeline(blobIdx) {{
  var ts = timeseriesData[blobIdx];
  if (!ts || ts.length === 0) return;
  var labels = ts.map(function(d) {{ return d.label; }});
  var cex    = ts.map(function(d) {{ return d.cex; }});
  var mhw    = ts.map(function(d) {{ return d.mhw; }});
  var oax    = ts.map(function(d) {{ return d.oax; }});

  function lineTrace(name, values, color) {{
    return {{
      x: labels, y: values, type: 'scatter', mode: 'lines+markers', name: name,
      line: {{ color: color, width: 2, shape: 'spline' }},
      marker: {{ color: color, size: 5, line: {{ width: 0 }} }},
      connectgaps: false,
      hovertemplate: '<b>%{{x}}</b><br>' + name + ': %{{y:.2f}}<extra></extra>',
    }};
  }}

  Plotly.newPlot('timeline-div',
    [
      lineTrace('MHW', mhw, '#f97316'),
      lineTrace('OAX', oax, '#06b6d4'),
      lineTrace('Compound', cex, '#facc15'),
    ],
    {{
      height: 120,
      margin: {{ l: 44, r: 86, t: 4, b: 38 }},
      paper_bgcolor: CARD_BG, plot_bgcolor: DARK_BG,
      xaxis: {{ tickfont: {{ size: 9, color: TEXT_DIM }}, showgrid: false, tickangle: -35, linecolor: GRID_COL }},
      yaxis: {{
        title: {{ text: 'Normalised intensity', font: {{ size: 9, color: TEXT_DIM }}, standoff: 4 }},
        tickfont: {{ size: 9, color: TEXT_DIM }},
        range: [0, 5], fixedrange: true,
        showgrid: true, gridcolor: GRID_COL, zeroline: false, linecolor: GRID_COL
      }},
      legend: {{
        x: 1.02, y: 0.99, xanchor: 'left', yanchor: 'top',
        bgcolor: 'rgba(30,36,54,0.72)', bordercolor: GRID_COL, borderwidth: 1,
        font: {{ size: 9, color: TEXT_MAIN }}, orientation: 'v',
      }},
      hoverlabel: {{ bgcolor: CARD_BG, font: {{ size: 11, color: TEXT_MAIN }}, bordercolor: GRID_COL }},
    }},
    {{ displayModeBar: false, responsive: true }}
  );
}}
</script>
</body>
</html>"""

out = HERE / "figure6_interactive.html"
out.write_text(html)
print(f"Written: {out}  ({out.stat().st_size / 1e6:.1f} MB)")
