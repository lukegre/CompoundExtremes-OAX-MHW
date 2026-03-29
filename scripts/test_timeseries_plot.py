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

plt.style.use("/home/user/2025_CompoundExtremes_AGUadvances/scripts/plotting.mplstyle")

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
            signal = (
                5 * np.sin(np.linspace(0, 4 * np.pi, len(time)))
                + 0.05 * np.arange(len(time))
                + rng.normal(0, 2, len(time))
                + (1 - thresh) * 200
                + poly * 0.5
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
_ts = timeseries.unstack("Experiment")
_datasets = _ts["Dataset"].values
_poly_orders = _ts["Polynomial order"].values
_threshold_pcts = _ts["Threshold percentile"].values
_total_ocean_mkm2 = 361.0

fig_ts, axs_ts = plt.subplots(2, 2, figsize=(10, 6), sharex=True, sharey=True)

for _i, (_ds, _poly) in enumerate([(_d, _p) for _d in _datasets for _p in _poly_orders]):
    _ax = axs_ts.flatten()[_i]
    for _threshold in _threshold_pcts:
        _line = _ts.sel({"Dataset": _ds, "Polynomial order": _poly, "Threshold percentile": _threshold})
        vis.line.smooth(_line).plot(ax=_ax, label=f"{_threshold:.0%}", lw=4)
    _ax.set_title("")
    _ax.set_title(f"{_ds}, poly={_poly}", loc="left")
    _ax.set_xlabel("")
    _ax.set_ylabel("")

for _ax_right in axs_ts[:, 1]:
    _ax2 = vis.line.add_secondary_yaxis_with_custom_values(
        _ax_right,
        ticks=[5, 10, 15, 20],
        tick_inverter=lambda x: x / 100 * _total_ocean_mkm2,
    )

axs_ts[0, 0].legend()
vis.line.set_fig_ylabel(axs_ts[:, 0].tolist(), "Area (Mkm$^2$)", x=-0.05)
vis.line.set_fig_ylabel(axs_ts[:, 1].tolist(), "% Ocean area", x=0.97)

fig_ts.savefig("/home/user/2025_CompoundExtremes_AGUadvances/scripts/test_output/test_timeseries_2x2.png", dpi=150)
print("Saved to scripts/test_output/test_timeseries_2x2.png")
