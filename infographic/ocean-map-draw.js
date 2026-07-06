// Ocean Compound Extremes Infographic — map drawing (SVG build + interaction wiring).
// Pure-ish: takes already-loaded libs/data/callbacks as arguments so it doesn't need to know
// about React refs, props, or component state — the logic class just wires those up and calls in.
//
// ============================== QUICK GUIDE: WHAT TO CHANGE WHERE ==============================
// Rotation / map framing (which ocean sits center)  -> ROTATE in ocean-map-helpers.js (+ re-bake)
// Ocean background field images + color bins/levels -> python/build_annual_rasters.py (re-bake ./annual/*)
// Which field is shown (a year, or the total)       -> el.__oceSetField(url) — driven by _setMapYear() in .dc.html
// Event circle SIZE (radius vs. area)               -> `rs` scale, a few lines down in drawMap()
// Event circle COLOR (by compound intensity)        -> circleColorScale() in ocean-map-helpers.js
// Event circle FILL OPACITY / stroke                -> the `.oce-c` circle .attr() calls below
// Event label text/position/font                    -> the `lab` text block below (search "label")
// Land fill / country border colors                  -> landColor/borderColor args, set in the .dc.html's _drawMap()
// The event data itself (add/remove/move a marker)  -> EVENTS array in ocean-map-helpers.js
// Tooltip content per event                          -> tipHtml() in ocean-map-helpers.js
// Map SVG canvas size (aspect ratio)                 -> W, H constants below
// =================================================================================================

const WORLD_ATLAS_URL = 'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json';

// ============================== VISIBLE LATITUDE FRAME ==============================
// The visible latitude window. Antarctica IS shown: the frame extends to -85°, and the frame
// clip rect (oce-sphere-clip, below) trims the 110m atlas's coarse near-straight southern edge
// of the Antarctica ring cleanly at the map's bottom edge, so the continent reads as a solid
// landmass running off the bottom of the map. Everything (projection fit, background fill,
// clip mask) is built from this ring instead of the full sphere, so the crop stays consistent
// if you ever change it.
const FRAME_LAT_MIN = -85, FRAME_LAT_MAX = 80;
function frameRing(latMin, latMax, steps = 90) {
  const top = [], bottom = [];
  for (let i = 0; i <= steps; i++) { const lon = -180 + 360 * i / steps; top.push([lon, latMax]); bottom.push([lon, latMin]); }
  bottom.reverse();
  const ring = top.concat(bottom); ring.push(ring[0]);
  return { type: 'Polygon', coordinates: [ring] };
}

// Antarctica's coarse southern ring edge is handled by the frame clip (oce-sphere-clip), so the
// continent renders like any other landmass. Kept only to exclude it from the interior-border
// mesh (it shares no land borders anyway).
const isAntarctica = f => f && (f.id === 10 || f.id === '10' || f.id === '010');

// Fetches + decodes the 110m world country boundaries (TopoJSON), once. Returns both the land
// fill geometry (merged countries, GeoJSON) and the interior country-border mesh (a single
// MultiLineString of shared/interior boundaries only, via topojson.mesh with an a!==b filter —
// this omits the outer coastline so it doesn't double up with the land fill's own outline).
export async function loadWorld(topojson){
  const topo = await fetch(WORLD_ATLAS_URL).then(r => r.json());
  const land = topojson.feature(topo, topo.objects.countries);
  return {
    land,
    borders: topojson.mesh(topo, topo.objects.countries, (a, b) => a !== b && !isAntarctica(a) && !isAntarctica(b))
  };
}

// Builds the full map SVG into `el` and wires hover/tooltip interactions.
//
// opts:
//   d3, topojson       — loaded libraries
//   el                 — mount element (its innerHTML is replaced)
//   world              — GeoJSON land features (from loadWorld)
//   rotate             — rotation in degrees (see ocean-map-helpers ROTATE); the projection is
//                         always geoEquirectangular so the pre-baked (pre-rolled) field images
//                         line up linearly with the projected geometry
//   bgPageColor        — page/paper background color; land + the globe outline match this so only
//                         the field image + event circles stand out
//   fieldImageUrl      — URL of the current ocean-field PNG (a year, or the summed total). Baked
//                         transparent + pre-rolled by `rotate` and cropped to the lat frame, so it
//                         drops straight onto path.bounds(frame). Swap later via el.__oceSetField(url).
//   regionHighUrl / regionLowUrl — pre-baked region-emphasis PNGs for the spotlight (see __oceHighlight)
//   rasterOpacity      — overall opacity of the field-image overlay
//   events             — array of event records (lon/lat/area/I/name/year/sub/dir/key)
//   colorScale         — d3 sequential scale for the event-circle fill (by compound intensity)
//   circleScale        — numeric multiplier on circle radius (tweakable)
//   showTooltips       — boolean
//   tipHtml(event)     — builds tooltip markup for an event
//   onHover(key, on)   — called on enter/leave of an event circle, for cross-highlighting
export function drawMap({
  d3, topojson, el, markersEl, world, rotate, bgPageColor, landColor, borderColor,
  fieldImageUrl, regionHighUrl, regionLowUrl,
  events, colorScale, circleScale, circleOpacity, rasterOpacity, showTooltips, tipHtml, onHover, onTip
}){
  if(!el) return;
  el.innerHTML = '';
  // CHANGE ASPECT RATIO / OVERALL MAP SIZE: these are viewBox units, not pixels — the SVG scales
  // to 100% of its container width, so raising H relative to W makes the map taller in proportion.
  const W = 1000, H = 475;
  const svg = d3.select(el).append('svg')
    .attr('viewBox', `0 0 ${W} ${H}`).attr('width', '100%').attr('height', '100%')
    // fill the parent's full height, scaling up and cropping the horizontal overflow (the faded
    // edges) rather than letterboxing with empty space above/below the map.
    .attr('preserveAspectRatio', 'xMidYMid slice')
    .style('display', 'block').style('border-radius', '4px');

  // PROJECTION: always geoEquirectangular (== PlateCarree). This is what lets the pre-baked field
  // images overlay directly — under equirectangular, screen x/y are linear in lon/lat, so a single
  // <image> stretched to the frame bounds aligns with the projected land/borders/circles. `rotate`
  // (from ROTATE in ocean-map-helpers.js) shifts which longitude sits at center; the field images
  // are pre-rolled by the same amount so they follow.
  const proj = d3.geoEquirectangular().rotate([rotate, 0]);
  const frame = frameRing(FRAME_LAT_MIN, FRAME_LAT_MAX);
  // CHANGE MAP PADDING: the [[8,10],[W-8,H-14]] box is the margin (in viewBox units) the globe is
  // fit inside — shrink these numbers to let the map fill more of its box, grow them to pad more.
  proj.fitExtent([[8, 10], [W - 8, H - 14]], frame);
  const path = d3.geoPath(proj);

  // ocean sphere: flat page-colour fill first (so any cell the field image leaves transparent —
  // e.g. land, or a year with no extremes there — reads as paper, not empty).
  const defs = svg.append('defs');
  svg.append('path').attr('d', path(frame)).attr('fill', bgPageColor);

  // Clip to the visible frame (not the full sphere), inset 1px so the overlay's edge is trimmed
  // cleanly, and land/borders are clipped the same way so nothing (e.g. Antarctica's coarse
  // geometry) can draw past the frame's edge.
  const [[bx0, by0], [bx1, by1]] = path.bounds(frame);
  defs.append('clipPath').attr('id', 'oce-sphere-clip').append('rect')
    .attr('x', bx0 + 1).attr('y', by0 + 1).attr('width', (bx1 - bx0) - 2).attr('height', (by1 - by0) - 2);

  const worldG = svg.append('g').attr('class', 'oce-world');

  // OCEAN FIELD OVERLAY: a single pre-baked, pre-rolled, transparent PNG (a year, or the summed
  // total) stretched to the frame bounds. Under equirectangular the mapping is linear, so
  // preserveAspectRatio='none' aligns it pixel-for-pixel with the projected land/borders/circles.
  // el.__oceSetField(url) swaps the field (driven by _setMapYear() in the .dc.html on bar hover).
  // Two stacked layers let us CROSSFADE between fields (a year <-> the total) instead of snapping:
  // load the new field on the back layer, fade it in while the front fades out, then swap roles.
  // Both layers stay below land/borders in the DOM, so they never cover the coastlines.
  const FIELD_FADE_MS = 300;
  const baseOp = rasterOpacity ?? 0.9;
  const setHref = (sel, url) => sel.attr('href', url).attr('xlink:href', url);
  const mkFieldLayer = () => worldG.append('image')
    .attr('class', 'oce-field')
    .attr('x', bx0).attr('y', by0).attr('width', bx1 - bx0).attr('height', by1 - by0)
    .attr('preserveAspectRatio', 'none')
    .attr('clip-path', 'url(#oce-sphere-clip)')
    .style('pointer-events', 'none')
    .style('transition', `opacity ${FIELD_FADE_MS}ms ease`)
    .attr('opacity', 0);
  const fieldLayers = [mkFieldLayer(), mkFieldLayer()];
  let fieldFront = fieldLayers[0], fieldCurUrl = null;
  if (fieldImageUrl) { setHref(fieldFront, fieldImageUrl); fieldFront.attr('opacity', baseOp); fieldCurUrl = fieldImageUrl; }
  el.__oceSetField = (url) => {
    if (!url || url === fieldCurUrl) return;
    fieldCurUrl = url;
    const back = fieldFront === fieldLayers[0] ? fieldLayers[1] : fieldLayers[0];
    setHref(back, url);
    back.attr('opacity', baseOp);   // fade the new field in
    fieldFront.attr('opacity', 0);  // fade the old field out
    fieldFront = back;
  };

  // land fill + country borders: land is filled with a muted "paper" tone (distinct from the
  // ocean colour bands but quiet enough not to compete with them), with thin interior country
  // boundary lines on top. Both colors are passed in from the component (landColor/borderColor)
  // so they can be restyled without touching this file.
  // Clipped to the same sphere bounds as the contour bands (oce-sphere-clip) — without this,
  // polygons that wrap the pole (Antarctica) after rotation can draw a stray line past the
  // map's visible edge.
  const landG = worldG.append('g').attr('clip-path', 'url(#oce-sphere-clip)');
  landG.append('path').attr('d', path(world.land)).attr('fill', bgPageColor).attr('stroke', borderColor).attr('stroke-width', 0.6);
  if (world.borders) {
    landG.append('path').attr('d', path(world.borders)).attr('fill', 'none').attr('stroke', borderColor).attr('stroke-width', 0.6).attr('stroke-linejoin', 'round');
  }

  // REGION SPOTLIGHT: el.__oceHighlight(mode) dims the whole map under a page-colour wash and
  // shows only the selected pre-baked region image on top, fully saturated.
  //   mode 'high' — high-count cells (low-/mid-latitude hot band) -> regionHighUrl
  //   mode 'min'  — low-count cells (rare high-latitude regions)  -> regionLowUrl
  //   mode null   — restore the normal map
  // The region images are baked transparent + pre-rolled the same as the field image, so they line
  // up exactly. (Driven by the "More common than chance" panel's hover in the .dc.html.)
  {
    const regionUrl = { high: regionHighUrl, min: regionLowUrl };
    const hlG = worldG.append('g').attr('class', 'oce-hl').style('opacity', 0).style('pointer-events', 'none');
    const washRect = hlG.append('rect').attr('x', bx0).attr('y', by0).attr('width', bx1 - bx0).attr('height', by1 - by0)
      .attr('fill', bgPageColor).attr('clip-path', 'url(#oce-sphere-clip)');
    const hlImg = hlG.append('image')
      .attr('x', bx0).attr('y', by0).attr('width', bx1 - bx0).attr('height', by1 - by0)
      .attr('preserveAspectRatio', 'none').attr('clip-path', 'url(#oce-sphere-clip)');
    // el.__oceHighlight(mode, opts) — opts.strength (0..1 wash opacity, default .78),
    // opts.fadeMs (transition duration, default 220).
    el.__oceHighlight = (mode, opts) => {
      const o = opts || {};
      const fadeMs = o.fadeMs == null ? 220 : o.fadeMs;
      hlG.style('transition', `opacity ${fadeMs}ms ease`);
      washRect.attr('opacity', o.strength == null ? 0.78 : o.strength);
      if (el.__oceHlTimer) { clearTimeout(el.__oceHlTimer); el.__oceHlTimer = null; }

      const build = m => { const u = regionUrl[m]; if (u) hlImg.attr('href', u).attr('xlink:href', u); };

      if (!mode || !regionUrl[mode]) { hlG.style('opacity', 0); el.__oceHlMode = null; return; }

      if (el.__oceHlMode && el.__oceHlMode !== mode) {
        // switching between two spotlights: fade the current one out, then the new one in
        hlG.style('opacity', 0);
        el.__oceHlTimer = setTimeout(() => { build(mode); hlG.style('opacity', 1); el.__oceHlMode = mode; el.__oceHlTimer = null; }, fadeMs);
      } else {
        build(mode); hlG.style('opacity', 1); el.__oceHlMode = mode;
      }
    };
  }

  // Keep land + coastlines ABOVE the spotlight wash so continents stay visible when a region is
  // highlighted (the wash only dims the ocean field, not the land). Markers are in a separate
  // overlay SVG, so they already sit on top.
  landG.raise();

  // EVENT CIRCLE SIZE: domain = [min area, max area] across your events (M km²), range = [min
  // radius px, max radius px] at circleScale=1. The `circleScale` prop (Tweaks panel) multiplies
  // the whole thing, so you don't need to touch this unless the underlying data's range changes.
  const rs = d3.scaleSqrt().domain([0.5, 12.6]).range([7, 34]);
  const rF = a => rs(a) * (circleScale || 1);

  // Event markers render into a SEPARATE overlay SVG (markersEl) that sits ABOVE the edge-fade
  // gradients in the DOM, so markers near the map's left/right edges stay fully opaque instead of
  // being dimmed by the fade. The overlay shares the exact viewBox + preserveAspectRatio as the
  // base map so marker positions line up pixel-for-pixel. Falls back to the base svg if no overlay
  // element was supplied. The overlay is click-through except on the marker groups themselves.
  let gcSvg = svg;
  if (markersEl) {
    markersEl.innerHTML = '';
    gcSvg = d3.select(markersEl).append('svg')
      .attr('viewBox', `0 0 ${W} ${H}`).attr('width', '100%').attr('height', '100%')
      .attr('preserveAspectRatio', 'xMidYMid slice')
      .style('display', 'block').style('pointer-events', 'none');
  }
  const gc = gcSvg.append('g');
  events.forEach(e => {
    const p = proj([e.lon, e.lat]); if (!p) return;
    const r = rF(e.area);
    const grp = gc.append('g').attr('transform', `translate(${p[0]},${p[1]})`).style('cursor', 'pointer').style('pointer-events', 'all').attr('data-key', e.key);
    // EVENT CIRCLE FILL/STROKE: fill color comes from colorScale(e.I) — see circleColorScale() in
    // ocean-map-helpers.js (the `intensityScale` prop switches its palette). fill-opacity/stroke
    // here are just the visual finish (white ring around each dot).
    grp.append('circle').attr('class', 'oce-c').attr('r', r).attr('fill', colorScale(e.I)).attr('fill-opacity', circleOpacity ?? 0.9).attr('stroke', '#fff').attr('stroke-width', 1.6);
    // in-circle area number: only shown once the circle is big enough (r>=15) to fit it legibly
    if (r >= 15) {
      grp.append('text').attr('text-anchor', 'middle').attr('dy', '0.02em').attr('font-family', 'Barlow Condensed,sans-serif').attr('font-weight', 700).attr('font-size', r > 22 ? 18 : 14).attr('fill', '#fff').text(e.area);
      grp.append('text').attr('text-anchor', 'middle').attr('dy', '1.15em').attr('font-family', 'Source Sans 3,sans-serif').attr('font-size', 8.5).attr('fill', '#fff').attr('fill-opacity', 0.9).text('M km\u00B2');
    }
    // EVENT LABEL (name + year, placed outside the circle): position is driven by each event's
    // `dir` field in EVENTS (ocean-map-helpers.js) — 'N' puts the label above, 'W'/'E' puts it to
    // the side, anything else (default) puts it below. Adjust the +7/+13 offsets to move labels
    // closer/further from their circle; font sizes are on the two `tspan` lines below.
    const up = e.dir === 'N', left = e.dir === 'W', right = e.dir === 'E';
    let lx = 0, ly = up ? -(r + 7) : (r + 13), anchor = 'middle';
    if (left) { lx = -(r + 7); ly = 4; anchor = 'end'; }
    if (right) { lx = (r + 7); ly = 4; anchor = 'start'; }
    const lab = grp.append('text').attr('text-anchor', anchor).attr('x', lx).attr('y', ly).attr('font-family', 'Source Sans 3,sans-serif').attr('paint-order', 'stroke').attr('stroke', '#eef2f4').attr('stroke-width', 2.6).attr('stroke-linejoin', 'round');
    lab.append('tspan').attr('x', lx).attr('font-weight', 700).attr('font-size', 11.5).attr('fill', '#1e2a30').text(e.name);         // event name line
    lab.append('tspan').attr('x', lx).attr('dy', '1.15em').attr('font-size', 10).attr('font-weight', 600).attr('fill', '#5a6b73').text(e.year + (e.sub ? '  \u00B7 ' + e.sub : ''));  // year + sub-label line

    grp.on('mouseenter', function () { d3.select(this).select('.oce-c').transition().duration(120).attr('r', rF(e.area) + 3); if (onHover) onHover(e.key, true); })
       .on('mousemove', ev => { if (showTooltips !== false && onTip) onTip(tipHtml(e), ev); })
       .on('mouseleave', function () { d3.select(this).select('.oce-c').transition().duration(120).attr('r', rF(e.area)); if (onHover) onHover(e.key, false); if (onTip) onTip(null); });
  });
}
