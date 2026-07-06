# Per-event footprint rasters on hover — design

**Date:** 2026-07-06
**Component:** `infographic/` — Ocean Compound Extremes Infographic poster.

## Goal

For each "most extreme" event shown in the Top-events table and as a map
marker, bake a standalone footprint raster PNG. When the user hovers an event
(either its table row or its map marker), swap the map's ocean-field background
to that event's footprint, then restore on mouse-out.

## Source data

`infographic/uploads/most_extreme_blobs.nc`

- Dims: `blobs` (9), `lat` (180, 1° grid, −89.5…89.5), `lon` (360, 1° grid, −179.5…179.5).
- Var: `mask(blobs, lat, lon)` — integer **0–9 = number of months each cell spent
  in the compound extreme** during that event. `0` = cell not part of the event.
- Coords `quantile=0.95`, `rolling_period=12`. Mask attrs note OISST source,
  shifting baseline 1982–2024, p95 threshold.

### Blob-name → event-key map

The 9 blobs map 1:1 to the 9 entries in `EVENTS` (ocean-map-helpers.js):

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

The bake script owns this mapping (a literal dict). If a blob name has no
matching key, fail loudly rather than silently skipping.

## Architecture

Reuses the existing baked-PNG-overlay pipeline end-to-end. Two changes:

### 1. Bake script — `python/build_event_rasters.py`

Mirrors `python/build_annual_rasters.py`:

- Same geometry/framing constants: `ROTATE = 150`, `LAT_MIN, LAT_MAX = -85, 80`.
- Same discrete palette as the annual fields (so event footprints read against
  the **existing on-map legend** — no legend changes):
  `LEVELS = [0, 1, 2, 4, 8, 16, 32]`,
  `COLORS = ["#fce8c8","#f6c886","#eda44e","#e07b2e","#c8531f","#a5281a","#6b1710"]`.
- Reuse the same `_rolled()` (longitude pre-roll so the PNG x-axis matches the
  d3 `rotate([ROTATE,0])` framing) and the same transparent, axis-free,
  tight-bbox `contourf` save approach as `_save_contourf()`.
- Per event: select `mask.sel(blobs=<name>)`, **set cells == 0 to NaN** so the
  ocean outside the footprint stays transparent (base ocean tone shows through);
  only the footprint is colored.
- Output:
  - `infographic/annual/events/<key>.png` (9 files).
  - A manifest describing the events (key → filename). Extend the **existing**
    `infographic/annual/manifest.json` with an `events` object
    (`{ "<key>": "events/<key>.png", ... }`) rather than a second manifest file,
    so the HTML loads one manifest. The bake script must read the existing
    manifest, add/replace the `events` block, and write it back (do not clobber
    the annual fields the block lives beside).

Resolution/DPI: reuse the annual script's `DPI`/`FIG_W`/`FIG_H` so the event
PNGs share the annual fields' pixel grid and align exactly.

### 2. Wiring — `Ocean Compound Extremes Infographic.dc.html`

- `_eventUrl(key)` helper: `this._manifest.events[key]` → versioned URL via the
  existing `_ver()`, resolved against the annual dir (same as `_fieldUrl`).
- `_setActive(key, on)` — the single function BOTH the marker hover (`onHover`)
  and the table-row hover (`mouseenter`/`mouseleave` listeners) already call.
  Add to it:
  - on `on`: if an event URL exists, `el.__oceSetField(_eventUrl(key))` (reuses
    the existing crossfade swap) and set the year badge to the event's
    name + year.
  - on `off`: restore the field to `this._curYear` (`_setMapYear` semantics) and
    restore the badge to its `_curYear` text.
  - Existing circle stroke + row-background cross-highlight behavior is
    unchanged.
- Preload: add the event URLs to the `_preload` URL list (line ~433) so the
  first hover swaps instantly.

Marker hover and row hover need NO new listeners — both already route through
`_setActive`.

## Data flow

```
most_extreme_blobs.nc
  └─ build_event_rasters.py ─► annual/events/<key>.png  +  manifest.json{events}
                                        │
HTML loadManifest() ──► manifest.events ─► _eventUrl(key)
                                        │
hover marker/row ─► _setActive(key,true) ─► __oceSetField(eventUrl) + badge
mouse-out ─────────► _setActive(key,false)─► __oceSetField(curYear field) + badge
```

## Error handling / edge cases

- Missing `events` block or missing key in manifest: `_setActive` falls back to
  current behavior (cross-highlight only, no swap) — no thrown errors.
- Hovering a new event while one is already shown: `__oceSetField` no-ops on an
  identical URL and crossfades otherwise; last-hover wins. On mouse-out we
  always restore to `this._curYear`, so rapid enter/leave settles correctly.
- Bake script: unknown blob name → hard error. `0`→NaN so empty ocean is
  transparent, not painted the lightest bin.

## Testing / verification

- Run `python/build_event_rasters.py`; assert 9 PNGs written and each is
  non-empty and transparent outside the footprint (spot-check a corner pixel
  alpha == 0).
- Assert `manifest.json` still contains the annual `total`/`years` keys AND a
  new `events` block with all 9 keys.
- Open the poster: hover each table row and each marker → background swaps to
  that event's footprint and the badge shows the event; mouse-out restores the
  prior field (total or the currently-selected year) and badge.

## Out of scope (YAGNI)

- No tooltip thumbnail (display mode chosen = background swap only).
- No bespoke 0–9 legend; reuse the existing 7-bin warm legend.
- No changes to the annual-field bake or the year-bar behavior.
