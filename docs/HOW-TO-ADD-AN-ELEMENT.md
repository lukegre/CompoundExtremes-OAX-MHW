# Ocean Compound Extremes Infographic — Adding a New Element

This page is a single self-contained file: `Ocean Compound Extremes Infographic.dc.html`.
Everything — layout, colors, map, legend — lives inline in that one file. There is no
separate stylesheet or JS bundle to hunt through.

## 1. Structure of the page

The page is built as stacked horizontal "bands," top to bottom:

- **Band 1 — Header + definition + stats.** Three boxes side by side: the dark
  "Global ocean" title card, the cream definition box, and the light-blue "43 years /
  1982–2024" stats box.
- **Band 2 — Map.** The world map with the filled-contour ocean background and the
  event circles on top.
- **Band 3 — Legend + supporting charts.** "Where do they happen?" color legend,
  the year-by-year ring, and the El Niño bar chart.
- **Band 4 — Mechanism + top events.** Left: **"The mechanism: a tug-of-war"** — an
  interactive explorer (regime toggle, heatwave slider, presets, four score cards, an
  ocean cross-section schematic, and a live outcome verdict). Right: the top-events
  table. The explorer's controls are wired imperatively in the logic class: every live
  element carries a `data-m="..."` attribute (or `data-preset="..."` for the presets),
  all inside the `mechRef` container. `_mechInit()` attaches the listeners and
  `_mechUpdate()` re-reads the slider/regime and repaints the cards + SVG on every
  change. To tweak wording or thresholds, edit the `_mech*` methods — not the template
  text, which is only the initial state. Colors and type follow the same palette below.

Each band is a `<div style="display:flex; ...">` row, and each box inside it is a
sibling `<div>` with its own inline `style="..."`. To find a box, search the file for
its visible text (e.g. `grep "Global ocean"`) — everything about that box (background
color, border, padding, border-radius) is in its own `style` attribute right there.

## 2. The design system: colors, type, spacing

- **Palette:** dark navy `#12222c` (header card), cream `#faf6ec` / `#f0ead9` (paper
  background + definition boxes), light blue `#dde8ee` (stats box), and the 7-step warm
  ocean-field scale from `#fce8c8` (pale, few extreme-months) through `#e07b2e` to
  `#6b1710` (dark red, many) — defined in `python/build_annual_rasters.py` and mirrored in
  the map legend. Reuse these — don't introduce new hex values.
- **Type:** `'Barlow Condensed', sans-serif` for headlines/labels (bold, uppercase,
  tight letter-spacing), a plain system sans for body copy.
- **Corners & borders:** boxes use `border-radius: 6px` and a 1px border a shade darker
  than their own fill (e.g. cream box → `#e6ddc7` border).
- **Spacing:** rows use `display:flex; gap:14px` (or similar) rather than margins.

**Rule of thumb:** copy the style attribute of the box most similar to what you're
adding, then change only the properties that need to differ. Don't invent new colors —
pick from the palette above, or a shade of it via `color-mix()`/opacity if you need a
lighter/darker variant.

## 3. Adding a new box/element

1. Decide which band it belongs to (or whether it needs a new band — a new top-level
   flex row after `</div>` that closes the previous band).
2. Copy the nearest existing box's `<div style="...">...</div>` as a starting template.
3. Give it `flex: <n> 1 <basis>px; min-width: <px>` so it behaves like its neighbors
   when the window resizes.
4. If it needs to sit near the map and might overlap it, add `position:relative;
   z-index:1` (the map is `z-index:0`/`auto` by default) so it draws on top — see the
   three Band 1 boxes for the pattern already in use.
5. Keep text content honest — no filler stats or placeholder numbers. If you don't have
   a real figure yet, leave a clearly-marked TODO rather than inventing one.

## 4. The map itself (only touch this if the new element IS map-related)

The map is generated entirely in JS inside the component's logic class
(`class Component extends DCLogic`), not in the template:

- The ocean background is a set of **pre-baked transparent PNGs** in `annual/`
  (`total.png`, `year_<YYYY>.png`, `region_high/low.png`) plus `manifest.json`, rendered
  offline by `python/build_annual_rasters.py` from `uploads/n_extremes_annual.nc`.
- The map projection is **fixed to equirectangular**. `_drawMap()` (via
  `ocean-map-draw.js`) draws the current field as a single `<image>` stretched to the map
  frame — under equirectangular that overlays linearly, so no runtime contouring happens.
- `_setMapYear(year|null)` swaps the overlay (`el.__oceSetField(url)`): a year on bar
  hover, or `null` for the summed total. All images are preloaded on mount.
- Legend swatches/labels in the template must match the `levels`/`colors` in
  `manifest.json` (currently 7 bins: `0,1,2,4,8,16,32,>32`).
- Event circles (the OAX∩MHW markers) are drawn separately in `_drawMap()`, positioned
  by real lon/lat via the same D3 projection.

To restyle or re-bin the ocean field: edit `LEVELS`/`COLORS` in
`python/build_annual_rasters.py`, re-run it, and update the legend swatches/labels in the
template to match. To feed a different dataset, point the script at a new `.nc` with the
same `(year, lat, lon)` shape.

## 5. Checking your work

Open the file directly in a browser — it's self-contained (aside from the two raster
files sitting next to it) and requires no build step. Check that:
- New boxes don't overflow their flex row or get clipped by the map's stacking order.
- Any new numbers/labels are real, not placeholders.
- Colors and fonts match the palette in Section 2 — no new hex values introduced.
