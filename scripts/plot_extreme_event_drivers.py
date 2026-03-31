import warnings
from dataclasses import dataclass
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import xarray as xr
from cartopy import crs, feature
from cartopy.mpl.geoaxes import GeoAxes
from loguru import logger
from matplotlib.axes import Axes
from matplotlib.contour import QuadContourSet
from matplotlib.lines import Line2D

import compoundx_figs as cxf


@dataclass
class EventDataMaps:
    oax: xr.DataArray
    mhw: xr.DataArray
    cex: xr.DataArray

    def sel(self, **kwargs) -> "EventDataMaps":
        return EventDataMaps(
            oax=self.oax.sel(**kwargs),
            mhw=self.mhw.sel(**kwargs),
            cex=self.cex.sel(**kwargs),
        )


@dataclass
class EventData:
    oax: xr.Dataset
    mhw: xr.Dataset
    cex: xr.Dataset
    mask: xr.DataArray
    geo: EventDataMaps
    sensitivities: xr.Dataset
    drivers: xr.DataArray
    xy: tuple[float, float] | None = None
    time_start: pd.Timestamp | None = None
    time_end: pd.Timestamp | None = None

    def __post_init__(self):
        self.time_start, self.time_end = (
            self.mask.any(["lat", "lon"])
            .pipe(lambda x: x.time[x])
            .isel(time=[0, -1])
            .to_index()
            .values
        )


def get_event_data(
    data: cxf.Datasets,
    event_idx: int,
    event_region: dict[str, slice],
    min_duration: int = 3,
    find_most_intense_point_var="oax",
    custom_xy=None,
) -> EventData:
    mask = (
        (data.cex.blobs == event_idx)
        .compute()
        .where(lambda x: x.sum("time") > min_duration, drop=True)
        .fillna(0)
        .astype(bool)
    )

    if custom_xy is None:
        n_periods = sum([c == "." for c in find_most_intense_point_var])
        if n_periods == 1:
            var, metric = find_most_intense_point_var.split(".")
        elif n_periods == 0:
            var = find_most_intense_point_var
            metric = "intensity"
        else:
            raise ValueError("There should be only 1 '.' in 'find_most_intense_point_var'")

        logger.debug(f"Getting most intense point for extreme from {var}.{metric}")
        x, y = get_most_intense_point(data[var][metric], mask)
    else:
        logger.debug(f"Manually setting most intense location to {custom_xy=}")
        x, y = custom_xy

    event_data = data.sel(lat=[y], lon=[x], method="nearest").apply("reset_coords", drop=True)
    event_maps = get_map_data_seasonal(data, event_region)
    event_sensitivity = calc_event_sensitivity(event_data)

    event_drivers = calc_hplus_drivers(
        hplus=event_data.oax.data,
        dic=event_data.aux.dic,
        alk=event_data.aux.talk,
        salinity=event_data.aux.salinity,
        temp=event_data.aux.temperature,
        sensitivities_beta=event_sensitivity.beta,
    )

    return EventData(
        oax=event_data.oax,
        mhw=event_data.mhw,
        cex=event_data.cex,
        mask=mask,
        geo=event_maps,
        sensitivities=event_sensitivity,
        drivers=event_drivers,
        xy=(x, y),
    )


def get_most_intense_point(da: xr.DataArray, mask: xr.DataArray) -> tuple[float, float]:
    coord = da.where(mask, drop=True).mean("time").to_series().idxmax()
    assert isinstance(coord, tuple), "Expected a single point of maximum intensity"
    assert len(coord) == 2, "Expected a single point of maximum intensity"
    y, x = [float(c) for c in coord]  # type: ignore

    return x, y


def get_map_data_seasonal(data: cxf.Datasets, region: dict[str, slice]) -> EventDataMaps:

    def resample_seasonal(ds: xr.Dataset, mask_condition) -> xr.DataArray:
        return (
            ds.intensity_norm.where(mask_condition)
            .sel(region)
            .resample(time="QS-DEC")
            .mean()
            .load()
        )

    return EventDataMaps(
        oax=resample_seasonal(data.oax, lambda x: x > 1),
        mhw=resample_seasonal(data.mhw, lambda x: x > 1),
        cex=resample_seasonal(data.cex, data.cex.mask),
    )


def calc_event_sensitivity(event_data: cxf.Datasets) -> xr.Dataset:

    sensitivities = cxf.calc_sensitivities(
        dic=event_data.aux.dic,
        alk=event_data.aux.talk,
        sal=event_data.aux.salinity,
        temp=event_data.aux.temperature,
        normalize_to_sal=True,
        verbose=False,
    )
    return sensitivities


def calc_hplus_drivers(
    hplus: xr.DataArray,
    dic: xr.DataArray,
    alk: xr.DataArray,
    salinity: xr.DataArray,
    temp: xr.DataArray,
    sensitivities_beta: xr.Dataset,
    salinity_norm=34.5,
) -> xr.DataArray:

    drivers = xr.Dataset()
    drivers["dic"] = dic
    drivers["alk"] = alk
    drivers["salt"] = salinity
    drivers["temp"] = temp
    drivers["sdic"] = drivers.dic / drivers.salt * salinity_norm
    drivers["salk"] = drivers.alk / drivers.salt * salinity_norm

    trend = drivers.map(calc_trend, deg=2)
    change = drivers - trend
    beta = sensitivities_beta.to_dataset(dim="driver")

    delta_driver = xr.Dataset()
    delta_driver["sDIC"] = hplus / drivers.sdic * beta["C"] * change.sdic
    delta_driver["sALK"] = hplus / drivers.salk * beta["A"] * change.salk
    delta_driver["TEMP"] = hplus / drivers.temp * beta["T"] * change.temp
    delta_driver["FW"] = hplus / drivers.salt * beta["FW"] * change.salt

    # ∆driver is the response of [H+] to each driver. The change variable
    # is the change in each driver with the second order trend removed.
    # This is equivalent to the shifting baseline.
    delta_driver = (
        delta_driver.to_array(name="seasonal_drivers", dim="driver")
        .sel(driver=["sDIC", "TEMP", "sALK", "FW"])
        .reindex_like(drivers)
        .transpose("driver", "time", "lat", "lon")
    )

    return delta_driver


def calc_trend(da: xr.DataArray, dim="time", deg=2) -> xr.DataArray:
    p = da.polyfit(dim=dim, deg=deg).polyfit_coefficients
    x = da[dim]

    trend = xr.polyval(x, p)
    return trend


# functions for plotting the next figure
def get_climatology(da: xr.DataArray, time_dim_name="time") -> xr.DataArray:
    """returns the monthly climatology at the original length of the time series"""

    t = time_dim_name
    return da.groupby(f"{t}.month").mean(t).sel(month=da[t].dt.month).drop_vars("month")


def make_data_and_thresh_as_anom_without_seasonal_cycle(ds: xr.Dataset) -> xr.Dataset:
    out = xr.Dataset()
    out["threshold"] = ds.magnitude - ds.intensity
    out["magnitude"] = ds.magnitude
    return out


def make_data_and_thresh_as_anom_with_seasonal_cycle(ds: xr.Dataset) -> xr.Dataset:
    trend = calc_trend(ds.climatology, deg=2)
    trend = trend.assign_coords(time=ds.time)

    out = xr.Dataset()
    out["threshold"] = ds.threshold - trend
    out["magnitude"] = ds.data - trend

    return out


def add_vertical_bars(
    ax: Axes, bar_width=6, offset: int = 0, dtype="datetime64[M]", color="#eeeeee", **kwargs
):
    import re
    from warnings import filterwarnings

    from matplotlib.pylab import num2date

    filterwarnings("ignore", category=DeprecationWarning)

    # getting unit from time
    if isinstance(dtype, str):
        time_unit = re.findall(r".*\[(.*)\]", dtype)
        time_unit = time_unit[0] if len(time_unit) > 0 else dtype
        if time_unit != dtype:
            offset = np.timedelta64(offset, time_unit)

    # setting the offset in months
    # getting the x and y limits so that plot ranges don't change
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()

    # make the approach suitable for dates also
    isdate = False
    if isinstance(dtype, str):
        if "datetime" in dtype:
            isdate = True
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning)
        if isdate:
            x0 = np.datetime64(num2date(x0)).astype(dtype)
            x0 = str(x0 + offset)[:10]
            x1 = str(np.datetime64(num2date(x1)).astype(dtype) + bar_width)[:10]
        else:
            x0 = x0 + offset
            x1 = x1 + offset

    # setting the bars widths
    bars = np.arange(x0, x1, bar_width, dtype=dtype)
    # rearrange the bars to bar_start and bar_end pairs
    bars = bars[0::2], bars[1::2]

    props = dict(color=color, zorder=0)
    props.update(kwargs)
    bar_objs = []
    # drawing the bars
    for b0, b1 in zip(*bars):
        bar_objs += (ax.fill_between([b0, b1], [y0 * 5] * 2, [y1 * 5] * 2, **props),)

    ax.set_ylim(y0, y1)

    plt.sca(ax)
    plt.xticks(rotation=0, ha="center")

    return bar_objs


def smoothen_line(da: xr.DataArray, dim="time", resample_freq="1D", radius=7) -> xr.DataArray:
    """
    Make a low resolution time series and give it smooth corners
    """
    if isinstance(resample_freq, str):
        resampled = da.resample(**{dim: resample_freq})  # first make the data higher resolution
        interpolated = resampled.interpolate(
            kind="linear"
        )  # then interpolate nans to make continuous
        smoothed = interpolated.rolling_exp(
            **{dim: radius, "center": True}
        ).mean()  # make corners smooth with rolling exponential func
        smoothed = smoothed.assign_coords(time=interpolated.time)

    else:
        x0 = da[dim].values[0]
        x1 = da[dim].values[-1] + resample_freq
        xd = resample_freq

        reindexed = da.reindex(time=np.arange(x0, x1, xd))
        interpolated = reindexed.interpolate_na(dim=dim, method="linear")
        smoothed = interpolated.rolling_exp(**{dim: radius, "center": True}).mean()

    return smoothed


def plot_ribbon_with_thick_y0(
    y0: xr.DataArray,
    y1: xr.DataArray,
    ax: Axes | None = None,
    color: str | None = None,
    zorder: int | None = None,
    ribbon_alpha: float = 0.4,
    lw: float = 2.0,
    y1_ls: str = "-",
) -> Axes:

    if ax is None:
        fig, ax = plt.subplots()

    y1_alpha = ribbon_alpha + 0.1 if ribbon_alpha < 1 else 1
    props_y0 = dict(color=color, zorder=zorder, lw=lw * 2)
    props_y1 = dict(zorder=zorder, lw=lw, alpha=y1_alpha, ls=y1_ls)
    props_ribbon = dict(zorder=zorder, lw=0, alpha=ribbon_alpha)

    x = y0.time.values

    line = ax.plot(x, y0, **props_y0)[0]
    ax.plot(x, y1, **props_y1, color=line.get_color())
    ax.fill_between(x, y0, y1, interpolate=True, **props_ribbon, color=line.get_color())

    return ax


def plot_driver_magnitude_ribbon(
    magnitude: xr.DataArray, climatology: xr.DataArray, ax: Axes | None = None
) -> Axes:
    if ax is None:
        fig, ax = plt.subplots(figsize=[7.5, 3])

    keys = magnitude[magnitude.dims[0]].values
    for i, d in enumerate(keys):
        y0 = magnitude.sel(driver=d)
        y1 = climatology.sel(driver=d)
        plot_ribbon_with_thick_y0(y0, y1, ax=ax)

    return ax


def plot_hplus_magnitude(
    magnitude,
    threshold,
    ax: Axes | None = None,
    color="k",
    magnitude_lw=1.4,
    threshold_lw=1.4,
    **kwargs,
) -> Axes:
    if ax is None:
        fig, ax = plt.subplots(figsize=[7.5, 3])

    if magnitude_lw > 0:
        magnitude.plot(ax=ax, color=color, lw=magnitude_lw, ls="-", **kwargs)
    if threshold_lw > 0:
        threshold.plot(ax=ax, color=color, lw=threshold_lw, ls="--", **kwargs)
    x = threshold.time.values

    ax.fill_between(
        x,
        magnitude,
        threshold,
        where=magnitude > threshold,
        interpolate=True,
        color=color,
        zorder=8,
    )

    ax.set_ylabel("")
    ax.set_xlabel("")
    ax.set_title("")

    return ax


def plot_drivers_of_oax(
    oax: xr.Dataset,
    drivers: xr.DataArray,
    smoothen_radius_days=14,
    axs: tuple[Axes, Axes] | None = None,
) -> tuple[Axes, Axes]:

    ## DATA ###########################################################################
    # create data for first plot - magnitudes with seasonal cycle
    drivers_clim = get_climatology(drivers)
    w_seascycl = make_data_and_thresh_as_anom_with_seasonal_cycle(oax)

    # create data for second plot - magnitudes
    drivers_mag = drivers - drivers_clim
    wo_seascycl = make_data_and_thresh_as_anom_without_seasonal_cycle(oax)

    # smoothen lines
    def smoothen(x):
        return smoothen_line(x, radius=14)

    arr = drivers, drivers_clim, w_seascycl, drivers_mag, wo_seascycl
    drivers, drivers_clim, w_seascycl, drivers_mag, wo_seascycl = [smoothen(a) for a in arr]

    ## PLOTTING #######################################################################
    if axs is None:
        fig, axs = plt.subplots(2, 1, figsize=[7.5, 5], sharex=True)
    else:
        assert len(axs) == 2, "Must be two subplots in `axs`"
        fig = axs[0].get_figure()

    # first plot with seasonal cycle
    plot_driver_magnitude_ribbon(drivers, drivers_clim, ax=axs[0])
    plot_hplus_magnitude(w_seascycl.magnitude, w_seascycl.threshold, ax=axs[0], threshold_lw=1.4)
    axs[0].set_ylabel("[H$^{{+}}$] detrended (nmol kg$^{{-}1}$)")

    # second plot without seasonal cycle
    axs[1].axhline(0, color="grey", lw=1.4)
    drivers_mag.plot(hue="driver", lw=4, add_legend=False)
    plot_hplus_magnitude(wo_seascycl.magnitude, wo_seascycl.threshold, ax=axs[1], threshold_lw=0)
    axs[1].set_ylabel("[H$^{{+}}$] magnitude (nmol kg$^{{-}1}$)")

    for a in axs:
        plt.sca(a)
        plt.xticks(rotation=0)

    fig.subplots_adjust(left=0.1, right=0.95)

    return axs


def plot_blob_oax_drivers(delta_driver, oax) -> tuple[plt.Figure, tuple[Axes, Axes]]:

    sns.set_palette("colorblind")

    axs = plot_drivers_of_oax(oax, delta_driver, 30)
    fig = axs[0].get_figure()
    assert isinstance(fig, plt.Figure)

    [add_vertical_bars(a, zorder=-1, offset=-2) for a in axs]

    return fig, axs


def get_parent_axes_from_line_obj(line: Line2D) -> Axes | None:

    fig = line.get_figure()
    assert isinstance(fig, plt.Figure)

    subplots = fig.get_axes()

    for ax in subplots:
        if line in ax.get_lines():
            return ax


def annotate_line(line: Line2D, xloc, label: str, **kwargs):
    fig = line.get_figure()
    ax = get_parent_axes_from_line_obj(line)

    assert ax is not None, "Line object must be part of an axes"
    assert isinstance(fig, plt.Figure)

    x, y = line.get_data()
    x = np.array(x)
    y = np.array(y)
    xdif = abs(x - xloc)

    i = int(np.nanargmin(xdif))
    x = x[i]
    y = y[i]

    lw = line.get_lw()
    fw = fig.get_figwidth()
    aw = ax.get_position().width

    if "color" not in kwargs:
        kwargs["color"] = line.get_color()

    text = ax.text(x, y, label, **kwargs)

    return text


def annotate_hplus_driver(line, driver_symbol, x, **props):

    txt = rf"  $\mathbf{{[ H\!^+_{{{driver_symbol}}}\!]}}$  "

    return annotate_line(line, x, txt, **props)


def plot_legend_with_dummy_lines(axs: tuple[Axes, Axes]):
    line = [0, 0], [1, 1]

    labels = {
        "driver": r"$\mathbf{[H^+_{\rm{driver}}]}$",
        "driver_baseline": r"$\mathbf{[H^+_{\rm{driver}}]}$ baseline",
        "hplus": r"$\mathbf{[H^+]}$",
        "hplus_thresh": r"$\mathbf{[H^+]}$ threshold",
        "hplus_mag": r"$\mathbf{[H^+]}$ magnitude",
        "driver_mag": r"$\mathbf{[H^+_{\rm{driver}}]}$ magnitude",
    }

    linesA = [
        axs[0].plot(*line, color="#bbbbbb", lw=4.0, ls="-", label=labels["driver"])[0],
        axs[0].plot(*line, color="#bbbbbb", lw=2.0, ls="-", label=labels["driver_baseline"])[0],
        axs[0].plot(*line, color="#000000", lw=1.5, ls="-", label=labels["hplus"])[0],
        axs[0].plot(*line, color="#000000", lw=1.5, ls="--", label=labels["hplus_thresh"])[0],
    ]

    linesB = [
        axs[1].plot(*line, color="#bbbbbb", lw=4.0, ls="-", label=labels["driver_mag"])[0],
        axs[1].plot(*line, color="#000000", lw=1.5, ls="-", label=labels["hplus_mag"])[0],
    ]

    axs[0].legend(linesA, [str(line.get_label()) for line in linesA], loc=[0.01, -0.01], ncol=4)
    axs[1].legend(linesB, [str(line.get_label()) for line in linesB], loc=[0.01, -0.01], ncol=4)


def plot_event_maps(
    data: EventDataMaps, axs: tuple[GeoAxes, GeoAxes, GeoAxes]
) -> tuple[QuadContourSet, QuadContourSet, QuadContourSet]:

    cmaps = ["Oranges", "Blues", "Greens"]
    props_maps: dict[str, Any] = {
        "transform": crs.PlateCarree(),
        "add_colorbar": False,
        "levels": np.linspace(0, 4.5, 10),
    }
    imgs = ()
    data_order = (
        data.mhw,
        data.oax,
        data.cex,
    )
    for _i, _da in enumerate(data_order):
        imgs += plot_map(_da, axs[:3], **(props_maps | {"cmap": cmaps[_i]}))

    [a.coastlines(lw=0.5, zorder=6) for a in axs[:3]]

    cbars = [
        plt.colorbar(imgs[0], ax=axs[0], aspect=15, location="top", pad=0.03),
        plt.colorbar(imgs[3], ax=axs[1], aspect=15, location="top", pad=0.03),
        plt.colorbar(imgs[6], ax=axs[2], aspect=15, location="top", pad=0.03),
    ]

    cbars[0].set_label(r"$\widetilde{I}_{\rm{MHW}}$", size="large", labelpad=10)
    cbars[1].set_label(r"$\widetilde{I}_{\rm{OAX}}$", size="large", labelpad=10)
    cbars[2].set_label(r"$\widetilde{I}_{\rm{OAX\,\cap\,MHW}}$", size="large", labelpad=10)

    [c.set_ticks([0, 1, 2, 3, 4]) for c in cbars]

    return (
        imgs[0],
        imgs[1],
        imgs[2],
    )


def plot_map(
    da: xr.DataArray, axs: tuple[GeoAxes, GeoAxes, GeoAxes], **kwargs
) -> tuple[QuadContourSet, QuadContourSet, QuadContourSet]:

    imgs = ()
    for i in range(3):
        img: QuadContourSet = da[i].plot.contourf(ax=axs[i], **kwargs)  # type: ignore
        img.axes.coastlines(lw=0.5, zorder=5)  # type: ignore
        img.axes.add_feature(feature.LAND, color="#cccccc", zorder=4)  # type: ignore

        (da[i] > 1).plot.contour(ax=axs[i], levels=[0.5, 1.5], linewidths=[1], colors=["w"])  # type: ignore

        img.axes.set_title("")
        imgs += (img,)

    return (
        imgs[0],
        imgs[1],
        imgs[2],
    )


def add_nice_date_labels(axs: tuple[Axes, Axes], dates: pd.DatetimeIndex, format="%b\n%Y"):
    ticks = dates.strftime(format)
    for ax in axs:
        ax.set_xticks(dates)
        ax.set_xticklabels(ticks)
    axs[0].set_xticklabels([])


def create_figure_layout() -> tuple[plt.Figure, tuple[Axes, Axes, Axes, Axes, Axes]]:

    fig = plt.figure(figsize=[7.5, 7])
    axs = np.array(
        [
            plt.subplot2grid((3, 3), (0, 0), projection=crs.PlateCarree()),
            plt.subplot2grid((3, 3), (0, 1), projection=crs.PlateCarree()),
            plt.subplot2grid((3, 3), (0, 2), projection=crs.PlateCarree()),
            plt.subplot2grid((3, 3), (1, 0), colspan=3),
            plt.subplot2grid((3, 3), (2, 0), colspan=3),
        ]
    )

    fig._autoscaleXon = False  # type: ignore
    fig._autoscaleYon = False  # type: ignore

    for axis in axs.flat:
        axis._autoscaleXon = False
        axis._autoscaleYon = False

    axs = tuple(axs.flat)

    return fig, axs


def get_season_abbreviations(dates, format="%b\n%Y") -> list[str]:
    from calendar import month_name

    date_index = pd.DatetimeIndex(pd.to_datetime(dates))

    if len(date_index) > 1:
        diffs = date_index[1:] - date_index[:-1]
        assert all(diff.days in range(89, 93) for diff in diffs), "Time step must be three months"

    seas_abbrevs = []
    for d in date_index:
        if pd.isna(d):
            raise ValueError("`dates` must not contain NaT values")

        months = [((d.month - 1 + offset) % 12) + 1 for offset in range(3)]
        season = "".join(month_name[m][0] for m in months)

        label = d.strftime(format.replace("%b", "\x00")).replace("\x00", season)
        seas_abbrevs.append(label)

    return seas_abbrevs
