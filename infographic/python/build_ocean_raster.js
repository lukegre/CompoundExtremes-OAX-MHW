// Builds ocean_raster.png + ocean_raster.json from a "n_extremes_binned*.csv" file.
//
// This is the exact logic used to (re)generate the raster whenever a new CSV is attached.
// It's written to run via the `run_script` tool (which provides readFile/saveFile/createCanvas
// in a sandboxed browser context) rather than as a standalone Node/Python script — see
// python/build_ocean_raster.py for the original Python version this replaces for this project.
//
// Input CSV format:
//   - first column header is "lat", the rest of the header row is longitude values
//   - each row: [lat, bin_index_at_lon0, bin_index_at_lon1, ...]
//   - bin_index is an integer 0..N (one per BG_COLORS entry in ocean-map-helpers.js),
//     or blank/NaN for no-data (e.g. land, or cells never sampled)
//
// Output:
//   - ocean_raster.png  : W x H grayscale PNG, pixel value = bin_index + 1 (0 = no-data)
//   - ocean_raster.json : grid geometry (origin, step) + bin edges

async function buildOceanRaster(csvPath) {
  const text = await readFile(csvPath);
  const lines = text.split('\n').filter(l => l.trim().length);
  const header = lines[0].split(',');
  const lons = header.slice(1).map(Number);
  const W = lons.length;
  const H = lines.length - 1;
  const lonMin = lons[0], lonStep = lons[1] - lons[0];

  const lats = new Array(H);
  const canvas = createCanvas(W, H);
  const ctx = canvas.getContext('2d');
  const imgData = ctx.createImageData(W, H);

  for (let i = 0; i < H; i++) {
    const parts = lines[i + 1].split(',');
    lats[i] = parseFloat(parts[0]);
    for (let j = 0; j < W; j++) {
      const v = parseFloat(parts[j + 1]);
      // pixel = bin_index + 1, clamped to a byte; blank/NaN cells -> 0 (no-data, stays transparent)
      const pix = isNaN(v) ? 0 : Math.max(0, Math.min(255, Math.round(v) + 1));
      const idx = (i * W + j) * 4;
      imgData.data[idx] = pix;
      imgData.data[idx + 1] = pix;
      imgData.data[idx + 2] = pix;
      imgData.data[idx + 3] = 255;
    }
  }
  ctx.putImageData(imgData, 0, 0);

  const latMin = lats[0], latStep = lats[1] - lats[0];
  await saveFile('ocean_raster.png', canvas);

  const meta = {
    w: W, h: H, lonMin, latMin, lonStep, latStep,
    scale: 1, discrete: true, valueOffset: 1,
    // must match BG_BIN_EDGES in ocean-map-helpers.js
    bins: [0, 0.125, 0.25, 0.5, 1, 2, 4, 8, 16, 32],
  };
  await saveFile('ocean_raster.json', JSON.stringify(meta));

  log(`wrote ocean_raster.png (${W}x${H}) + ocean_raster.json from ${csvPath}`);
}

// Usage (paste into run_script, swapping in the new CSV's project path):
// await buildOceanRaster('uploads/<latest-n_extremes_binned-file>.csv');
