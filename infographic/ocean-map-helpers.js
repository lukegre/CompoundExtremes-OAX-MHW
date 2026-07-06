// Ocean Compound Extremes Infographic — shared data + pure computation helpers.
// Loaded by the DC's logic class via dynamic import(); the class stays responsible for
// React lifecycle / refs / DOM drawing, this module owns the data + math it draws from.

// ============================== EVENT MARKERS ON THE MAP ==============================
// Add/remove/move a circle by editing this array — nothing else needs to change.
//   key      unique id, used internally for cross-highlighting with the table/ring/etc.
//   name/sub display label under the circle (sub is optional, shown smaller)
//   year     shown next to the name
//   lon/lat  WHERE the circle sits on the map (decimal degrees)
//   dir      which side the text label is placed on: 'N' (above), 'W' (left), 'E' (right),
//            anything else / omitted = below (default)
//   area     MAX extent in M km² — drives circle SIZE (see `rs` scale in ocean-map-draw.js)
//   areaAvg  MEAN extent in M km² — tooltip only
//   dur      duration in months — tooltip only
//   I        compound intensity (p95, normalized) — drives circle COLOR (circleColorScale())
//   mhw/mhwN, oax/oaxN, sev — additional tooltip detail (peak temp/pH, normalized, severity)
// Matched to event_stats.csv (Table 1 events).
export const EVENTS = [
  { key:'blob',  name:'The Blob',           sub:'NE Pacific', year:2015, lon:-142, lat:46,  dir:'S', area:12.6, areaAvg:4.1,  dur:12, I:3.52, mhw:1.40, mhwN:2.55, oax:0.181, oaxN:2.64, sev:13.3 },
  { key:'catl',  name:'Central Atlantic',   sub:'',           year:2023, lon:-20,  lat:-6,  dir:'S', area:12.5, areaAvg:5.4,  dur:14, I:3.44, mhw:0.66, mhwN:2.11, oax:0.126, oaxN:2.91, sev:15.9 },
  { key:'seasia',name:'Southeast Asia',     sub:'',           year:1998, lon:123,  lat:3,   dir:'S', area:7.5,  areaAvg:3.0,  dur:20, I:2.87, mhw:0.88, mhwN:2.05, oax:0.127, oaxN:2.20, sev:14.0 },
  { key:'natl',  name:'North Atlantic',     sub:'',           year:2023, lon:-34,  lat:49,  dir:'N', area:6.9,  areaAvg:3.3,  dur:11, I:3.22, mhw:0.97, mhwN:2.26, oax:0.138, oaxN:2.54, sev:15.3 },
  { key:'spac',  name:'South Pacific',      sub:'',           year:2016, lon:-132, lat:-33, dir:'S', area:4.0,  areaAvg:2.2,  dur:8,  I:3.31, mhw:0.84, mhwN:2.08, oax:0.160, oaxN:2.83, sev:13.2 },
  { key:'gbr',   name:'Great Barrier Reef', sub:'',           year:2022, lon:153,  lat:-16, dir:'E', area:3.3,  areaAvg:2.1,  dur:9,  I:2.76, mhw:0.81, mhwN:2.11, oax:0.094, oaxN:2.04, sev:14.0 },
  { key:'med',   name:'Med. Sea',           sub:'',           year:2003, lon:17,   lat:39,  dir:'N', area:1.3,  areaAvg:0.9,  dur:4,  I:3.52, mhw:1.92, mhwN:2.61, oax:0.369, oaxN:2.49, sev:9.6 },
  { key:'mad',   name:'Madagascar',         sub:'',           year:1987, lon:52,   lat:-22, dir:'S', area:1.0,  areaAvg:0.6,  dur:8,  I:3.53, mhw:0.93, mhwN:2.66, oax:0.122, oaxN:2.52, sev:11.5 },
  { key:'waus',  name:'Western Australia',  sub:'most intense',year:2011,lon:110,  lat:-29, dir:'S', area:0.7,  areaAvg:0.25, dur:6,  I:3.90, mhw:1.88, mhwN:3.00, oax:0.137, oaxN:2.89, sev:11.5 }
];

// Shared illustrative year-level series (relative global compound-event area) + ENSO phase sets,
// used by both the 43-year ring and the El Niño–La Niña bar chart.
export const YEAR_AREA = {1982:0.51,1983:5.50,1984:2.28,1985:0.47,1986:2.54,1987:4.91,1988:11.89,1989:7.84,1990:12.30,1991:4.42,1992:2.41,1993:0.84,1994:3.96,1995:2.68,1996:4.45,1997:11.25,1998:32.01,1999:13.92,2000:4.91,2001:2.49,2002:1.72,2003:2.21,2004:2.51,2005:2.66,2006:1.52,2007:1.50,2008:0.94,2009:1.82,2010:4.99,2011:3.22,2012:1.21,2013:0.41,2014:4.51,2015:17.27,2016:18.10,2017:8.36,2018:6.27,2019:18.58,2020:6.22,2021:5.44,2022:8.60,2023:18.50,2024:35.0};
export const NINO_YEARS = new Set([1982,1983,1987,1988,1991,1992,1997,1998,2015,2016,2023,2024]);
export const NINA_YEARS = new Set([1988,1989,1998,1999,2007,2008,2010,2011]);

// ============================== OCEAN BACKGROUND: PER-YEAR EXTREME-COUNT IMAGES ==============
// The ocean background is no longer computed at runtime. It's a set of pre-baked, transparent
// filled-contour PNGs (one per year + a "total" summed field), rendered offline by
// python/build_annual_rasters.py from uploads/n_extremes_annual.nc and written to ./annual/
// alongside a manifest.json. The map overlays the current field as a single <image> under the
// equirectangular projection (see ocean-map-draw.js). loadManifest() fetches that manifest,
// which carries the discrete contourf levels/colors/labels (for the legend), the list of years,
// and the file-name templates. TO CHANGE THE PALETTE OR LEVELS: edit build_annual_rasters.py and
// re-run it — the manifest + baked PNGs + the legend all follow from it.
export function loadManifest(url='./annual/manifest.json'){
  return fetch(url).then(r=>r.json()).catch(e=>{ console.warn('manifest '+url+' failed to load',e); return null; });
}

// Resolve the image URL for a given year (or the summed total when year is null/undefined).
// dir defaults to the same ./annual/ folder the manifest lives in.
export function fieldImageUrl(manifest, year, dir='./annual/'){
  if(!manifest) return null;
  if(year==null) return dir+manifest.total;
  return dir+manifest.yearFmt.replace('{year}', year);
}

// ============================== MAP ROTATION / FRAMING ==============================
// Degrees applied to the map projection so the Pacific sits centered and the map's edge lands
// at 30°E. The baked field images are pre-rolled by this SAME amount (see build_annual_rasters.py)
// so the overlay lines up pixel-for-pixel with the projected land/borders/circles, and the
// antimeridian seam lands at the map's outer edge. TO RE-CENTER THE MAP: change this number here
// AND in build_annual_rasters.py, then re-bake — everything shares the one rotation.
export const ROTATE = 150;

// Sequential color scale for the event-circle "compound intensity" fill (distinct from the
// discrete ocean-field background colours baked into the ./annual/ images).
// TO ADD A NEW PALETTE OPTION: add a key here AND to the `intensityScale` prop's `options` list
// in the .dc.html's data-props JSON. domain([2.5,4.05]) is the compound-intensity (`I`) range
// across EVENTS above — widen it if you add an event with a more extreme I value.
export function circleColorScale(d3, intensityScale){
  const interp={
    warm:d3.interpolateYlOrRd,
    reds:d3.interpolateReds,
    viridis:d3.interpolateViridis,
    inferno:d3.interpolateInferno,
    magma:d3.interpolateMagma,
    plasma:d3.interpolatePlasma,
    orangeRed:d3.interpolateOrRd,
    yellowOrangeBrown:d3.interpolateYlOrBr,
    turbo:d3.interpolateTurbo,
    spectral:t=>d3.interpolateSpectral(1-t),
    cividis:d3.interpolateCividis
  }[intensityScale||'warm'] || d3.interpolateYlOrRd;
  return d3.scaleSequential(interp).domain([2.5,4.05]);
}

export function tipHtml(e){
  const row=(l,v)=>`<tr><td style="color:#9fb0b8;padding:1px 10px 1px 0;white-space:nowrap">${l}</td><td style="white-space:nowrap">${v}</td></tr>`;
  return `<div style="font-family:'Barlow Condensed',sans-serif;font-weight:700;font-size:15px;line-height:1.2;color:#f2b45a;letter-spacing:.06em">${e.name.toUpperCase()} &middot; ${e.year}</div>`+
    `<div style="height:1px;background:rgba(255,255,255,.2);margin:5px 0"></div>`+
    `<table style="font-size:11.5px;line-height:1.45;color:#e7ecee;border-collapse:collapse">`+
    row('Area', `${e.areaAvg} avg &middot; <b>${e.area} max</b> M km\u00B2`)+
    row('Duration', `${e.dur} months`)+
    row('Compound \u0128', `<b>${e.I.toFixed(2)}</b> (p95)`)+
    row('Heatwave', `${e.mhw.toFixed(2)} \u00B0C &middot; norm ${e.mhwN.toFixed(2)}`)+
    row('Acidification', `${e.oax.toFixed(3)} nmol/kg &middot; norm ${e.oaxN.toFixed(2)}`)+
    row('Severity', `${e.sev.toFixed(1)} unit&middot;mo`)+
    `</table>`;
}
