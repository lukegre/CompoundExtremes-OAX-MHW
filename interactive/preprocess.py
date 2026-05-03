"""
Precompute per-event spatial footprints using blob index labels.

For each qualifying event, selects pixels where blobs == blob_index
across all time steps, then computes Q95 of intensity_norm over those
masked pixels. This gives the correct per-event spatial fingerprint.

Qualifying events: duration_2sigma_mon > 1 AND area_max_Mkm2 >= 0.5
Output: event_footprints.npz
"""

import numpy as np
import pandas as pd
import xarray as xr
from pathlib import Path

HERE = Path(__file__).parent

df = pd.read_csv(HERE / "event_stats.csv", index_col=0)
ds = xr.open_dataset(HERE / "ETHZ1v2025_cexTH_shift_poly2_p95.nc")

lat = ds.lat.values
lon = ds.lon.values

# Filter to qualifying events
mask_filter = (df.duration_2sigma_mon > 1) & (df.area_max_Mkm2 >= 0.5)
df_qual = df[mask_filter].copy()
print(f"Qualifying events: {len(df_qual)} / {len(df)}")

# Load blobs and intensity_norm into memory once (133 MB each)
print("Loading blobs array...")
blobs = ds.blobs.values          # (time, lat, lon) float32
print("Loading intensity_norm array...")
intensity = ds.intensity_norm.values  # (time, lat, lon) float32
print("Arrays loaded.")

footprints: dict[int, np.ndarray] = {}

for blob_idx, row in df_qual.iterrows():
    # Mask: pixels where this blob is present at any time
    blob_mask = blobs == float(blob_idx)   # (time, lat, lon) bool

    if not blob_mask.any():
        print(f"  idx={blob_idx:4d}  NO pixels found — skipping")
        continue

    masked = np.where(blob_mask, intensity, np.nan)  # (time, lat, lon)

    # Q95 over time for each pixel that ever belongs to this blob
    with np.errstate(all="ignore"):
        q95 = np.nanpercentile(masked, 95, axis=0).astype(np.float32)  # (lat, lon)

    # Zero out pixels that never belonged to this blob
    any_blob = blob_mask.any(axis=0)
    q95[~any_blob] = np.nan

    n_valid = int(np.isfinite(q95).sum())
    print(f"  idx={blob_idx:4d}  valid_px={n_valid}")
    footprints[int(blob_idx)] = q95

print(f"\nSaving {len(footprints)} footprints...")
np.savez_compressed(
    HERE / "event_footprints.npz",
    lat=lat,
    lon=lon,
    blob_indices=np.array(list(footprints.keys())),
    **{f"fp_{k}": v for k, v in footprints.items()},
)
print("Done -> event_footprints.npz")
