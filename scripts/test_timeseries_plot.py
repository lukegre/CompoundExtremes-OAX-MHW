"""Dummy plot to test the 2x2 sensitivity timeseries figure."""
import sys
sys.path.insert(0, "/home/user/2025_CompoundExtremes_AGUadvances/src")

import numpy as np
import pandas as pd
import xarray as xr
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from compoundx_figs import vis

# --- create synthetic data matching expected CSV structure ---
rng = np.random.default_rng(42)
time = pd.date_range("1982-01", "2020-12", freq="MS")
datasets = ["CMEMS", "ETHZ"]
poly_orders = [3, 4]
thresholds = [0.90, 0.92, 0.95]

rows = []
for ds in datasets:
    for poly in poly_orders:
        for thresh in thresholds:
            # simulate a slowly varying count with noise + trend
            signal = (
                5 * np.sin(np.linspace(0, 4 * np.pi, len(time)))  # multi-year cycle
                + 0.05 * np.arange(len(time))                      # trend
                + rng.normal(0, 2, len(time))                      # noise
                + (1 - thresh) * 200                               # higher threshold -> more events
                + poly * 0.5                                       # slight poly-order offset
            ).clip(0)
            for t, v in zip(time, signal):
                rows.append({
                    "Dataset": ds,
                    "Polynomial order": poly,
                    "Threshold percentile": thresh,
                    "time": t,
                    "num_extremes_timeseries": v,
                    "Baseline": v * 0.8,
                })

df_timeseries = pd.DataFrame(rows)

# --- replicate notebook processing ---
timeseries = (
    df_timeseries.drop(columns=["Baseline"])
    .set_index(["Dataset", "Polynomial order", "Threshold percentile", "time"])
    .drop_duplicates()
    .to_xarray()
    .stack(Experiment=["Dataset", "Polynomial order", "Threshold percentile"])
    .num_extremes_timeseries.sortby("time")
)

# --- replicate new plot cell ---
ts_unstacked = timeseries.unstack("Experiment")

datasets_vals = ts_unstacked["Dataset"].values
poly_orders_vals = ts_unstacked["Polynomial order"].values
threshold_pcts = ts_unstacked["Threshold percentile"].values

fig_ts, axs_ts = plt.subplots(2, 2, figsize=(10, 6), sharex=True, sharey=True)

for _i, (_ds, _poly) in enumerate([(d, p) for d in datasets_vals for p in poly_orders_vals]):
    _ax = axs_ts.flatten()[_i]
    for _threshold in threshold_pcts:
        _line = ts_unstacked.sel({"Dataset": _ds, "Polynomial order": _poly, "Threshold percentile": _threshold})
        vis.line.smooth(_line).plot(ax=_ax, label=f"{_threshold:.0%}")
    _ax.set_title(f"{_ds}, poly={_poly}")
    _ax.legend()

fig_ts.tight_layout()
fig_ts.savefig("/home/user/2025_CompoundExtremes_AGUadvances/scripts/test_output/test_timeseries_2x2.png", dpi=150)
print("Saved to scripts/test_output/test_timeseries_2x2.png")
