"""
Step 1: encode a lon/lat bin-index CSV grid as a compact grayscale PNG + JSON sidecar.

Input CSV format (as produced by the pipeline that generates n_extremes_binned.csv):
  - first column header is "lat", the rest of the header row is longitude values
  - each row: [lat, bin_index_at_lon0, bin_index_at_lon1, ...]
  - bin_index is an integer 0..7 (8 discrete bins), or NaN for no-data (e.g. land)

Output:
  - ocean_raster.png  : W x H grayscale PNG, pixel value = bin_index + 1 (0 = no-data)
  - ocean_raster.json : grid geometry (origin, step) + bin edges, so the PNG alone
                         doesn't need to encode any geography
"""

import numpy as np
import pandas as pd
from PIL import Image
import json

CSV_PATH = "n_extremes_binned.csv"
BIN_EDGES = [0, 0.125, 0.25, 0.5, 1, 2, 4, 8, 16]  # 8 bins, symmetric in log2 around 1

def build_raster(csv_path=CSV_PATH):
    df = pd.read_csv(csv_path)

    lats = df["lat"].to_numpy()
    lon_cols = df.columns[1:]
    lons = lon_cols.astype(float).to_numpy()

    lon_min, lon_step = lons[0], lons[1] - lons[0]
    lat_min, lat_step = lats[0], lats[1] - lats[0]

    grid = df[lon_cols].to_numpy(dtype=float)  # shape (H, W), values 0..7 or NaN
    H, W = grid.shape

    # Encode: raw bin index -> pixel value (+1 so 0 is reserved for "no data")
    pixels = np.zeros((H, W), dtype=np.uint8)
    valid = ~np.isnan(grid)
    pixels[valid] = np.clip(grid[valid] + 1, 0, 255).astype(np.uint8)

    Image.fromarray(pixels, mode="L").save("ocean_raster.png")

    meta = {
        "w": int(W), "h": int(H),
        "lonMin": float(lon_min), "latMin": float(lat_min),
        "lonStep": float(lon_step), "latStep": float(lat_step),
        "scale": 1, "discrete": True, "valueOffset": 1,
        "bins": BIN_EDGES,
    }
    with open("ocean_raster.json", "w") as f:
        json.dump(meta, f)

    print(f"wrote ocean_raster.png ({W}x{H}) + ocean_raster.json")

if __name__ == "__main__":
    build_raster()
