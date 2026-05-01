# import dotenv  # isort: skip

# dotenv.load_dotenv()
from typing import Literal

import numpy as np
import xarray as xr
from loguru import logger
from matplotlib import pyplot as plt
from plot_extreme_event_drivers import (
    plot_driver_magnitude_ribbon,
    plot_ribbon_with_thick_y0,
)

from compoundx_figs.io import Datasets


def smooth_interp_monthly_clim(da: xr.DataArray, dim="time") -> xr.DataArray:
    assert da[dim].size == 12, f"{dim} dimension must be monthly climatology"
    assert da[dim].min() == 1, f"{dim} min value must be 1"
    assert da[dim].max() == 12, f"{dim} max value must be 12"

    months = da[dim].values
    da0 = da.assign_coords(**{dim: months - 12})  # type: ignore
    da2 = da.assign_coords(**{dim: months + 12})  # type: ignore
    da_extended = xr.concat(
        objs=[da0, da, da2],
        dim=dim,
    )
    x0 = da_extended[dim].min().values
    x1 = da_extended[dim].max().values
    x = np.arange(x0, x1, 0.05)
    da_interped = da_extended.interp(**{dim: x}, method="cubic")

    da_interped = da_interped.sel(**{dim: slice(-1, 13)})

    return da_interped


def calc_aggregated_extreme_drivers(
    drivers: xr.DataArray, mask: xr.DataArray, area: xr.DataArray
) -> xr.DataArray:
    south = mask.lat < 0
    north = ~south

    def area_weighted_monthly_mean(da):
        return (
            da.weighted(area)
            .mean(["lat", "lon"])
            .groupby("time.month")
            .mean("time")
            .rename(month="time")
        )

    nh_drivers_agg = drivers.where(north & mask).pipe(area_weighted_monthly_mean)
    sh_drivers_agg = (
        drivers.where(south & mask).pipe(area_weighted_monthly_mean).roll(time=6, roll_coords=False)
    )

    drivers_agg = (
        xr.combine_nested([nh_drivers_agg, sh_drivers_agg], concat_dim="hemisphere")
        .mean("hemisphere")
        .drop_sel(driver="FW")
    )

    return drivers_agg


def get_figure_data(
    data: Datasets, drivers: xr.DataArray, region_mask_value: int = 2
) -> dict[str, xr.DataArray]:
    area = data.masks.area

    low_lat = data.masks.regions_HL == region_mask_value
    cex_extreme = data.cex.mask
    oax_extreme = data.oax.mask

    masks = {
        "compound_extreme": low_lat & cex_extreme,
        "not_compound_extreme": low_lat & ~cex_extreme,
        "oax_extreme": low_lat & oax_extreme,
        "not_oax_extreme": low_lat & ~oax_extreme,
    }

    results = {}
    for name, mask in masks.items():
        logger.info(f"{name}: calculating aggregated extreme drivers")
        da = calc_aggregated_extreme_drivers(drivers, mask, area)
        da = smooth_interp_monthly_clim(da)
        results[name] = da.compute()

    return results


def plot_legend_with_dummy_lines(ax, extreme_label: str, **legend_kwargs):
    line = [-99, 99], [99, 99]

    labels = {
        "driver_extreme": r"$\mathbf{[H^+_{\rm{X}}]}$-" + extreme_label,
        "driver_clim": r"$\mathbf{[H^+_{\rm{X}}]}$-clim",
    }

    linesA = [
        ax.plot(*line, color="#bbbbbb", lw=4.0, ls="-", label=labels["driver_extreme"])[0],
        ax.plot(*line, color="#bbbbbb", lw=2.0, ls="-", label=labels["driver_clim"])[0],
    ]

    props = dict(loc=[0.01, -0.01], ncol=4) | legend_kwargs
    ax.legend(linesA, [str(line.get_label()) for line in linesA], **props)


def plot_top_row_axes(
    extreme: xr.DataArray,
    not_extreme: xr.DataArray,
    ax: plt.Axes,
    name: Literal["OAX", "CEX"],
    **kwargs,
):

    hplus_extreme = extreme.sum("driver")
    hplus_not_extreme = not_extreme.sum("driver")

    plot_driver_magnitude_ribbon(extreme, not_extreme, ax=ax)
    plot_ribbon_with_thick_y0(hplus_extreme, hplus_not_extreme, ax=ax, color="k", ribbon_alpha=0.25)

    plot_legend_with_dummy_lines(ax, name, ncol=1, loc="upper left")

    ax.axhline(0, ls="--", lw=0.5, c="k", zorder=-1)
    ax.set_title("")
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_xlim(0, 12)


def plot_bot_row_axes(
    extreme: xr.DataArray,
    not_extreme: xr.DataArray,
    ax: plt.Axes,
    name: Literal["OAX", "CEX"],
    **kwargs,
):
    driver_magnitude = extreme - not_extreme
    hplus_magnitude = driver_magnitude.sum("driver")

    line_props = {"hue": "driver", "add_legend": False, "linewidth": 4}
    driver_magnitude.plot.line(ax=ax, **line_props)  # type: ignore
    hplus_magnitude.plot.line(ax=ax, c="k", **line_props)  # type: ignore

    ax.axhline(0, ls="--", lw=0.5, c="k", zorder=-1)

    ax.set_title("")
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_xlim(0, 12)
    ax.set_xticks(np.arange(1.5, 12, 3))
    ax.set_xticklabels(["Winter", "Spring", "Summer", "Autumn"])
