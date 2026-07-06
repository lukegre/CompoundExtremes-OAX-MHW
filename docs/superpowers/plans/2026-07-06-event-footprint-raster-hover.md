# Per-event Footprint Raster Hover — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bake a footprint raster PNG for each of the 9 "most extreme" events and swap the map's ocean-field background to that footprint when the user hovers the event's table row or map marker, restoring on mouse-out.

**Architecture:** Reuse the existing baked-PNG-overlay pipeline. A new Python script (`build_event_rasters.py`) renders each event's `mask` field to a transparent, pre-rolled equirectangular PNG using the *same* palette/geometry as `build_annual_rasters.py`, and merges an `events` block into the existing `annual/manifest.json`. The HTML poster gains `_eventUrl()` + `_setEventField()` helpers, wired into the two single-event hover sites, reusing the existing `el.__oceSetField()` crossfade swap.

**Tech Stack:** Python 3 (xarray, numpy, matplotlib, Pillow for tests), vanilla JS / d3 in a `.dc.html` component.

## Global Constraints

- Geometry MUST match the annual pipeline exactly: `ROTATE = 150`, `LAT_MIN, LAT_MAX = -85, 80`, `DPI = 100`, `FIG_W = 14.40`, `FIG_H = FIG_W * (LAT_MAX - LAT_MIN) / 360.0`. Copy these verbatim from `python/build_annual_rasters.py`.
- Palette MUST be the same 7-bin warm scale as the annual fields (no new legend): `LEVELS = [0, 1, 2, 4, 8, 16, 32]`, `COLORS = ["#fce8c8", "#f6c886", "#eda44e", "#e07b2e", "#c8531f", "#a5281a", "#6b1710"]`.
- Event PNGs write to `infographic/annual/events/<key>.png` (9 files).
- The manifest stays a single file: `infographic/annual/manifest.json`, extended with an `events` object `{ "<key>": "events/<key>.png", ... }`. The event script MUST read the existing manifest, add/replace only the `events` key, and write it back — never clobber `total`/`years`/`regionHigh`/`regionLow`/etc. This requires `build_annual_rasters.py` to have been run first (it writes the base manifest); if `manifest.json` is missing, the event script fails loudly telling the user to run the annual script first.
- Cells with `mask == 0` (outside the event footprint) MUST render transparent, so only the footprint is colored.
- Blob-name → event-key mapping (owned by the event script as a literal dict; unknown blob name = hard error):

  | blob (netCDF coord)        | event `key` |
  |----------------------------|-------------|
  | `SE Asia (1998)`           | `seasia`    |
  | `Mediterranean Sea (2003)` | `med`       |
  | `Western Australia (2011)` | `waus`      |
  | `The Blob (2015)`          | `blob`      |
  | `South Pacific (2015)`     | `spac`      |
  | `Madagascar (1987)`        | `mad`       |
  | `Barrier Reef (2022)`      | `gbr`       |
  | `North Atlantic (2023)`    | `natl`      |
  | `Central Atlantic (2023)`  | `catl`      |

---

### Task 1: Bake per-event footprint PNGs + merge manifest

**Files:**
- Create: `infographic/python/build_event_rasters.py`
- Create: `infographic/python/test_build_event_rasters.py`
- Reads: `infographic/uploads/most_extreme_blobs.nc`, `infographic/annual/manifest.json`
- Writes: `infographic/annual/events/<key>.png` (×9), updates `infographic/annual/manifest.json`

**Interfaces:**
- Consumes: nothing from other tasks. Relies on `annual/manifest.json` already existing (produced by the pre-existing `build_annual_rasters.py`).
- Produces: `build()` function with no args; on success `annual/manifest.json` has an `events` dict keyed by the 9 event keys with values `"events/<key>.png"`, and 9 PNG files exist under `annual/events/`. Task 2 consumes `manifest.events` and the `events/<key>.png` paths.

- [ ] **Step 1: Write the failing test**

Create `infographic/python/test_build_event_rasters.py`:

```python
import json
import os

import numpy as np
from PIL import Image

import build_event_rasters as ber

HERE = os.path.dirname(os.path.abspath(__file__))
EVENTS_DIR = os.path.join(HERE, "..", "annual", "events")
MANIFEST = os.path.join(HERE, "..", "annual", "manifest.json")

EXPECTED_KEYS = {"seasia", "med", "waus", "blob", "spac", "mad", "gbr", "natl", "catl"}


def test_build_writes_nine_pngs_and_merges_manifest():
    # baseline manifest keys that must survive the merge
    with open(MANIFEST) as f:
        before = json.load(f)
    assert "total" in before and "years" in before, "run build_annual_rasters.py first"

    ber.build()

    # 9 PNGs, one per key, all non-empty
    for key in EXPECTED_KEYS:
        p = os.path.join(EVENTS_DIR, f"{key}.png")
        assert os.path.exists(p), f"missing {p}"
        assert os.path.getsize(p) > 0, f"empty {p}"

    # manifest still has the annual fields AND a complete events block
    with open(MANIFEST) as f:
        after = json.load(f)
    assert after["total"] == before["total"]
    assert after["years"] == before["years"]
    assert set(after["events"].keys()) == EXPECTED_KEYS
    for key in EXPECTED_KEYS:
        assert after["events"][key] == f"events/{key}.png"


def test_ocean_outside_footprint_is_transparent():
    ber.build()
    # top-left corner pixel (far from any footprint) must be fully transparent
    im = Image.open(os.path.join(EVENTS_DIR, "blob.png")).convert("RGBA")
    alpha = np.asarray(im)[..., 3]
    assert alpha[0, 0] == 0, "corner pixel should be transparent (mask==0 -> NaN)"
    assert (alpha > 0).any(), "footprint should color at least some pixels"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd infographic/python && python3 -m pytest test_build_event_rasters.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'build_event_rasters'` (and Pillow may need install: `pip install pytest pillow`).

- [ ] **Step 3: Write the bake script**

Create `infographic/python/build_event_rasters.py`:

```python
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
```

- [ ] **Step 4: Ensure the base manifest exists, then run the test**

Run:
```bash
cd infographic/python && python3 build_annual_rasters.py >/dev/null && python3 -m pytest test_build_event_rasters.py -v
```
Expected: PASS (2 passed). If Pillow/pytest missing: `pip install pytest pillow` then re-run.

- [ ] **Step 5: Eyeball one output**

Run: `cd infographic/python && python3 -c "from PIL import Image; im=Image.open('../annual/events/blob.png'); print(im.size, im.mode)"`
Expected: `(1440, 660) RGBA` (width 1440; height = FIG_H*DPI = 165*4 = 660). Open `../annual/events/blob.png` in an image viewer and confirm a single NE-Pacific footprint blob colored on transparent background.

- [ ] **Step 6: Commit**

```bash
git add infographic/python/build_event_rasters.py infographic/python/test_build_event_rasters.py infographic/annual/events infographic/annual/manifest.json
git commit -m "feat: bake per-event footprint rasters + merge into manifest"
```

---

### Task 2: Wire event-footprint swap into hover

**Files:**
- Modify: `infographic/Ocean Compound Extremes Infographic.dc.html`
  - `_load()` preload list (~line 433)
  - add `_eventUrl()` next to `_fieldUrl()` (~line 440)
  - add `_setEventField()` next to `_setMapYear()` (~line 452)
  - `_drawMap()` `onHover` callback (~line 495)
  - `_wireTable()` row listeners (~line 631, 633)

**Interfaces:**
- Consumes from Task 1: `this._manifest.events` (`{key: "events/<key>.png"}`).
- Produces: `_eventUrl(key)` → versioned URL string or null; `_setEventField(key,on)` → swaps map field to the event footprint (on) or restores to `this._curYear` (off) and updates the badge. Called from marker hover and table-row hover only; `_setActive`/`_setActiveYear` remain unchanged (so year-bar hover is unaffected).

- [ ] **Step 1: Add event URLs to the preload list**

In `_load()`, replace the `urls` line (~line 433):

```javascript
      const urls=[dir+m.total, dir+m.regionHigh, dir+m.regionLow, ...m.years.map(y=>H.fieldImageUrl(m,y,dir))].map(u=>this._ver(u));
```

with:

```javascript
      const eventFiles=m.events ? Object.values(m.events) : [];
      const urls=[dir+m.total, dir+m.regionHigh, dir+m.regionLow,
                  ...m.years.map(y=>H.fieldImageUrl(m,y,dir)),
                  ...eventFiles.map(f=>dir+f)].map(u=>this._ver(u));
```

- [ ] **Step 2: Add `_eventUrl()` helper**

Immediately after the `_fieldUrl(year){...}` method (~line 440), add:

```javascript
  _eventUrl(key){
    if(!this._manifest || !this._manifest.events) return null;
    const f=this._manifest.events[key];
    return f ? this._ver('./annual/'+f) : null;
  }
```

- [ ] **Step 3: Add `_setEventField()` method**

Immediately after the `_setMapYear(year){...}` method (~line 452-460), add:

```javascript
  // Swap the map field to a single event's footprint on hover; restore to the
  // currently-selected field (year or total) on mouse-out. Independent of the
  // year-bar swap path (_setMapYear/_setActiveYear), which it must not disturb.
  _setEventField(key,on){
    if(!this._manifest) return;
    const el=this.mapRef.current;
    const badge=this.yearBadgeRef.current;
    if(on){
      const url=this._eventUrl(key);
      if(!url) return;                       // no footprint for this key -> leave field as-is
      if(el && el.__oceSetField) el.__oceSetField(url);
      const ev=this.events.find(e=>e.key===key);
      if(badge && ev) badge.textContent = ev.name.toUpperCase()+' · '+ev.year;
    } else {
      // restore whatever field/badge the current year selection implies
      this._setMapYear(this._curYear==null?null:this._curYear);
    }
  }
```

- [ ] **Step 4: Call `_setEventField` from the marker hover callback**

In `_drawMap()`, change the `onHover` line (~line 495) from:

```javascript
      onHover:(key,on)=>self._setActive(key,on), onTip:(html,ev)=>self._tip(html,ev)
```

to:

```javascript
      onHover:(key,on)=>{ self._setActive(key,on); self._setEventField(key,on); }, onTip:(html,ev)=>self._tip(html,ev)
```

- [ ] **Step 5: Call `_setEventField` from the table-row listeners**

In `_wireTable()` (~line 631-633), change:

```javascript
      row.addEventListener('mouseenter',()=>self._setActive(key,true));
      row.addEventListener('mousemove',ev=>{ if(self.props.showTooltips!==false && e) self._tip(self._tipHtml(e),ev); });
      row.addEventListener('mouseleave',()=>{ self._setActive(key,false); self._tip(null); });
```

to:

```javascript
      row.addEventListener('mouseenter',()=>{ self._setActive(key,true); self._setEventField(key,true); });
      row.addEventListener('mousemove',ev=>{ if(self.props.showTooltips!==false && e) self._tip(self._tipHtml(e),ev); });
      row.addEventListener('mouseleave',()=>{ self._setActive(key,false); self._setEventField(key,false); self._tip(null); });
```

- [ ] **Step 6: Verify the manifest wiring statically**

Run:
```bash
cd infographic && python3 -c "import json; m=json.load(open('annual/manifest.json')); print(sorted(m['events'])); import os; print(all(os.path.exists('annual/'+p) for p in m['events'].values()))"
```
Expected: the 9 keys printed and `True` (every referenced PNG exists).

- [ ] **Step 7: Manual browser verification**

Open `infographic/Ocean Compound Extremes Infographic.dc.html` in a browser. Verify:
1. Default map shows the summed total (badge: `TOTAL · 1982–2024`).
2. Hover a table row (e.g. "The Blob") → map background crossfades to that event's footprint; badge reads `THE BLOB · 2015`; circle + row highlight as before.
3. Mouse-out → background crossfades back to the total; badge returns to `TOTAL · …`.
4. Hover a map **marker** → same footprint swap + badge as its row.
5. Hover an El Niño **year bar** → still swaps to that YEAR's field (unchanged); no event footprint interference.
6. Move directly between two event rows → settles on the second event's footprint.

- [ ] **Step 8: Commit**

```bash
git add "infographic/Ocean Compound Extremes Infographic.dc.html"
git commit -m "feat: swap map background to event footprint on marker/row hover"
```

---

## Self-Review notes

- **Spec coverage:** bake script + blob→key map + 0→transparent + same palette/geometry + manifest merge (Task 1); `_eventUrl`/`_setEventField` + preload + marker/row hover wiring + restore-on-leave (Task 2); year-bar untouched, no tooltip thumbnail, no new legend (out-of-scope respected). All covered.
- **Deviation from spec (intentional):** swap logic lives in a dedicated `_setEventField`, not inside `_setActive`, because `_setActive` is shared with the year-bar path via `_setActiveYear`; folding the swap into `_setActive` would make year-bar hover fight the year-field swap. Behavior for the user is identical to the spec.
- **Type consistency:** `_eventUrl(key)` returns string|null; `_setEventField(key,on)` uses it and `el.__oceSetField(url)` (existing), `this._curYear` (existing), `this.events` (existing). Manifest key `events` matches Task 1's output exactly (`events/<key>.png`).
